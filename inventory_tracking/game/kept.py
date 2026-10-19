"""What a runner keeps across its presses: the belt's history and the items the player put down (moved from
macros/world.py).
"""

import math
import threading
from dataclasses import replace

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Loot
from inventory_tracking.tracking.belt import BeltColumns, remember


class BeltKept:
    """The belt's history across the presses of a runner: `see` folds a look at the belt into it
    (tracking/belt.py `remember`) and hands the loot on with it. A loot of no known game is passed as read."""

    def __init__(self) -> None:
        self.columns = BeltColumns()

    def see(self, loot: Loot) -> Loot:
        if loot.game is None:
            return loot
        self.columns = remember(self.columns, loot.belt, loot.game)
        return replace(loot, columns=self.columns)


class PutDown:
    """The items the player put down this game, kept across the presses of a runner as `BeltKept` keeps the
    belt: a ground item whose unit id the character carried this game (`Loot.carried`) was put down by the
    player, who has looked at it, and is not the macro's to pick up, stand by or warn about again (the player,
    2026-10-14: "we tried to pickup crystal sword that I've checked and dropped"; rca/2026-10-14/run-0025-findings.md
    §3, P1). The game streams it out and back in with a new unit id at the same place (00:29:04.9 and 00:30:35.9
    that game), so it is remembered by its class and place, within NEAR, for the rest of the game. `see` takes it
    out of a look's drops, so no reader of the loot names it (`choose`, a level run's side drop, `stay_by`,
    `worth_a_stop`, the "Inventory full" warning); `at` answers the HUD's ground marks (loot/watch.py). Said once a
    place. A drop the player wants back is picked up by hand. A loot of no known game is passed as read; the
    next game forgets. Read by the runner's thread and the service's, hence the lock."""

    NEAR = 1.0  # world units: the same place (an item's position is whole units)
    KEPT = 4000  # the carried unit ids kept at most in a game (a full stash and inventory hold under 600 items)

    def __init__(self) -> None:
        self.game: tuple[str, int] | None = None
        self.carried: set[int] = set()
        self.places: list[tuple[int | None, float, float]] = []  # (class, x, y) of each item put down
        # The units the macro itself put down to take back (macros/cube.py `transmute`'s parked gems): not the
        # player's, so picked up again and kept in the game's guard (runner `_valuable_left`)
        self.parked: set[int] = set()
        self.lock = threading.Lock()

    def park(self, unit_id: int) -> None:
        """`unit_id` is put down by the macro to be picked up again: never taken for the player's."""
        with self.lock:
            self.parked.add(unit_id)

    def see(self, loot: Loot) -> Loot:
        if loot.game is None:
            return loot
        with self.lock:
            if loot.game != self.game:
                self.game, self.carried, self.places = loot.game, set(), []
            if len(self.carried) > self.KEPT:
                self.carried.clear()
            # The drops are tested against the items carried in earlier looks only: one `Loot` reads the drops
            # first and the grids last, so an item the macro picks up between the two is in both
            # (rca/2026-10-14/run-0305-findings.md §5.3: the Amulet "put down" while it was being picked up).
            kinds = dict(loot.classes)
            kept = []
            for drop in loot.drops:
                kind = kinds.get(drop.unit_id)
                if self._at(drop.x, drop.y, kind):
                    continue
                if drop.unit_id in self.carried and drop.unit_id not in self.parked:
                    self.places.append((kind, drop.x, drop.y))
                    LOG.info(
                        'Macro: put down: %s at (%.0f, %.0f), unit %d, was carried this game: the player put it '
                        'down; not picked up, stood by or warned about again this game',
                        drop.label, drop.x, drop.y, drop.unit_id,
                    )  # fmt: skip
                    continue
                kept.append(drop)
            self.carried |= loot.carried
        return loot if len(kept) == len(loot.drops) else replace(loot, drops=tuple(kept))

    def at(self, x: float, y: float, class_id: int | None = None) -> bool:
        """Whether an item the player put down this game lies at (x, y): of `class_id`, or of any class (None)."""
        with self.lock:
            return self._at(x, y, class_id)

    def _at(self, x: float, y: float, class_id: int | None) -> bool:
        return any(
            math.dist((x, y), (px, py)) <= self.NEAR and (class_id is None or kind is None or kind == class_id)
            for kind, px, py in self.places
        )
