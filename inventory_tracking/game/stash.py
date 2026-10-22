"""The stash: one object, the single source of truth for what the character's stash holds.

The player, 2026-10-22 ~09:10: "we need some generic approach to check stash - one object that is used everywhere,
updated every time we're in town/after each interaction with stash / no hardcoded, no copies, no stale records / make
sure that we have no places that interact with anything but it". Before it, the loop kept the full stacks in
runs/alt-d/full-stacks.json, written only at a visit's end and read back at a service start: an Eastern Worldstone
Shard at 97 was still "full" from the night before and left on the ground at 08:59:26 on 2026-10-22
(rca/2026-10-22/eastern-shard-findings.md).

- `Stash.read()`: the only way to the game's stash read (game/memory.py `GameMemory.read_stash`). Each whole read is
  recorded with its clock and game and written to the snapshot file (`SNAPSHOT`) for the tools outside the service
  (the watch's games.py and watch.py read it, never write it).
- `Stash.touched()`: an interaction with the stash (the panel opened, a shard used, a transmute). The last read is then
  no longer the stash's state: `current()` is None (unknown) until the next read.
- `Stash.full()`: the classes whose resource-tab stack is at the cap in the current read; empty when unknown. Unknown
  means take: what the loop would leave for a full stack is picked up, the next read decides.
- The runner refreshes it every REFRESH_SECONDS in town (running/watch.py `poll`), and every read of a routine goes
  through it (macros/engine.py `Reads.stash_view`).

The stash's numbers live here and nowhere else: the cap (STACK_MOST) and the player's rulings on stacks (RUNES_AIM,
SHARD_FLOOR, STACK_ROOM); the stat of the personal stash's gold (BANK_STAT). The shared stash's gold is not a
character stat and is read nowhere.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from inventory_tracking.items.metadata import metadata


if TYPE_CHECKING:
    from inventory_tracking.game.records import StashView


__all__ = [
    'BANK_STAT',
    'REFRESH_SECONDS',
    'RUNES_AIM',
    'SHARD_FLOOR',
    'SNAPSHOT',
    'STACK_MOST',
    'STACK_ROOM',
    'Stash',
    'full_of',
    'read_snapshot',
]

# A resource tab's stack at most. Client code, not the game's txt data: misc.txt marks the resource tabs' classes
# `AdvancedStashStackable` 1 with `maxstack` 0 (pricing/raw/game-excel, checked 2026-10-22); the cap was seen in the
# game: the Tal Runes refused at 99 (the player, 2026-10-17), the Western Worldstone Shard used from 99 to 98 at
# 22:27:44 on 2026-10-21
STACK_MOST = 99
# The player's rulings on the stacks, each in this one place:
# - rune stacks over this many are cubed down to it (2026-10-18: "cubed, aim to 80 or lower"; loot/storage.py)
RUNES_AIM = 80
# - a Worldstone Shard is used only from a stack this big (2026-10-20: "any stone with 90+ quantity"; terrorize.py)
SHARD_FLOOR = 90
# - a resource stack keeps this much room (2026-10-18: "at least 20 free slots"; town.py `Needs.stack_room`)
STACK_ROOM = 20
# itemstatcost.txt `goldbank`: the personal stash tab's gold (gamble.py, repair.py, stash.py; verified 2026-10-21,
# gamble.py). The shared stash's gold is no character stat: never read
BANK_STAT = 15

# The runner's read of the stash while the character is in town (running/watch.py `poll`): a hand's use of the stash
# is in the record within this many seconds
REFRESH_SECONDS = 2.0
# runs/alt-d/<SNAPSHOT>: the last read, for the tools outside the service
SNAPSHOT = 'stash.json'
# The snapshot is written when the read changes, and at least this often while reads come (its `at` stays fresh)
SNAPSHOT_SECONDS = 60.0


def full_of(view: StashView | None) -> frozenset[int]:
    """The classes of `view`'s stacks at the cap, the potions left out (a full Rejuvenation stack still takes the
    loop's potions: they are drunk, not stashed); empty for no view."""
    if view is None:
        return frozenset()
    from inventory_tracking.loot.storage import is_potion  # loot/storage.py imports game/records.py, which imports this

    return frozenset(txt for txt, count in view.stacks if count >= STACK_MOST and not is_potion(txt))


def _name(txt: int) -> str:
    return metadata()['bases'].get(str(txt), {}).get('name', f'item {txt}')


class Stash:
    """The character's stash as last read: the single source of truth (module docstring). Thread-safe: the service's
    poll and the routine's worker both read through it."""

    def __init__(
        self,
        reader: Callable[[], StashView | None] | None = None,
        *,
        snapshot: Path | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._reader = reader
        self.snapshot = snapshot
        self.clock = clock
        self._lock = threading.Lock()
        self.view: StashView | None = None  # the last whole read
        self.read_at: float | None = None  # its clock
        self.game: str | None = None  # the game it was read in, when told
        self.touched_at: float | None = None  # the last interaction's clock
        self._written: tuple[object, float] | None = None  # (what the snapshot holds, its clock)

    @property
    def attached(self) -> bool:
        return self._reader is not None

    def attach(self, reader: Callable[[], StashView | None] | None) -> None:
        """The game's read from now on (a routine's memory, the poll's); None: none (the record is kept)."""
        self._reader = reader

    def read(self, reader: Callable[[], StashView | None] | None = None, game: str | None = None) -> StashView | None:
        """The stash read now (by `reader`, else the attached read), recorded when whole; None unread (the record is
        kept: an unread moment is no change)."""
        source = reader if reader is not None else self._reader
        if source is None:
            return None
        view = source()
        if view is None:
            return None
        with self._lock:
            self.view, self.read_at = view, self.clock()
            if game is not None:
                self.game = game
        self._write(view)
        return view

    def touched(self) -> None:
        """An interaction with the stash: the last read no longer tells it until the next."""
        with self._lock:
            self.touched_at = self.clock()

    def current(self) -> StashView | None:
        """The last read while no interaction followed it; None: unknown (never read, or touched since)."""
        with self._lock:
            if self.read_at is None or (self.touched_at is not None and self.touched_at > self.read_at):
                return None
            return self.view

    def fresh(self) -> StashView | None:
        """The stash read now, else the current record; None: unknown."""
        return self.read() or self.current()

    def full(self) -> frozenset[int]:
        """The classes at the cap in the current record (`full_of`); empty when unknown: unknown means take."""
        return full_of(self.current())

    def count(self, txt: int) -> int | None:
        """The current record's stack of class `txt`; None unknown."""
        view = self.current()
        return view.count(txt) if view is not None else None

    def said(self) -> str:
        view = self.current()
        return view.said() if view is not None else 'unknown'

    def _write(self, view: StashView) -> None:
        if self.snapshot is None:
            return
        body = _snapshot_body(view, self.game)
        now = self.clock()
        if self._written is not None and self._written[0] == body and now - self._written[1] < SNAPSHOT_SECONDS:
            return
        record = {'at': datetime.now().isoformat(timespec='seconds'), **body}
        try:
            temporary = self.snapshot.with_suffix('.tmp')
            temporary.write_text(json.dumps(record, indent=1) + '\n')
            os.replace(temporary, self.snapshot)
        except OSError:
            return
        self._written = (body, now)


def _snapshot_body(view: StashView, game: str | None) -> dict:
    full = sorted(full_of(view))
    return {
        'game': game,
        'stacks': {str(txt): count for txt, count in view.stacks},
        'full': full,
        'full_names': [_name(txt) for txt in full],
        'pages_free': {str(page.index): page.free for page in view.pages},
    }


def read_snapshot(path: Path) -> dict | None:
    """The snapshot file as the service last wrote it; None when missing or unreadable (for the tools)."""
    try:
        found = json.loads(path.read_text())
    except OSError, ValueError:
        return None
    return found if isinstance(found, dict) else None
