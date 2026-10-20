"""What a runner keeps across its presses: the belt's history and the items the player put down."""

import math
import threading
from dataclasses import replace

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Loot
from inventory_tracking.tracking.belt import BeltColumns, remember


class BeltKept:
    """The belt's history across a runner's presses: `see` folds a look in (tracking/belt.py `remember`) and hands
    the loot on with it. A loot of no known game is passed as read."""

    def __init__(self) -> None:
        self.columns = BeltColumns()

    def see(self, loot: Loot) -> Loot:
        if loot.game is None or not loot.belt_read:
            return loot  # a partial belt would teach the columns wrong kinds
        self.columns = remember(self.columns, loot.belt, loot.game)
        return replace(loot, columns=self.columns)


class PutDown:
    """The items the player put down this game: a ground item whose unit id the character carried this game was
    put down by the player and is not the macro's to pick up, stand by or warn about again (the player, 2026-10-14:
    "we tried to pickup crystal sword that I've checked and dropped"; rca/2026-10-14/run-0025-findings.md §3).
    The game streams it back with a new unit id, so it is remembered by class and place (within NEAR) for the
    game. `see` drops it from a look's drops; `at` answers the HUD's ground marks (loot/watch.py). Shared by the
    runner's and the service's threads, hence the lock."""

    NEAR = 1.0  # world units: the same place (an item's position is whole units)
    KEPT = 4000  # the carried unit ids kept at most in a game (a full stash and inventory hold under 600 items)

    def __init__(self) -> None:
        self.game: tuple[str, int] | None = None
        self.carried: set[int] = set()
        self.places: list[tuple[int | None, float, float]] = []  # (class, x, y) of each item put down
        # Units the macro itself put down to take back (macros/cube.py `transmute`'s parked gems): not the player's.
        self.parked: set[int] = set()
        # Units the loop put down for good (loot/api.py `Field`, the field drop of M4, 2026-10-20): never picked up
        # again this game, and said as the loop's own, not the player's (unit id -> why)
        self.rejected: dict[int, str] = {}
        self.lock = threading.Lock()

    def reject(self, unit_id: int, why: str) -> None:
        """The loop put `unit_id` down for good (the field drop, loot/api.py): never picked up, stood by or warned about
        again this game, whatever unit id it is streamed back with (its place is kept at the first look that shows it),
        and logged as the loop's own put-down (design.md Q5: the game, PutDown's scope)."""
        with self.lock:
            self.parked.discard(unit_id)
            self.rejected[unit_id] = why
            self.carried.add(unit_id)

    def park(self, unit_id: int) -> None:
        """`unit_id` is put down by the macro to be picked up again: never taken for the player's."""
        with self.lock:
            self.parked.add(unit_id)

    def see(self, loot: Loot) -> Loot:
        if loot.game is None:
            return loot
        with self.lock:
            if loot.game != self.game:
                if self.game is not None:
                    self.rejected = {}  # another game's (a reject before the first look of a game is this one's)
                self.game, self.carried, self.places = loot.game, set(), []
            if len(self.carried) > self.KEPT:
                self.carried.clear()
            # Tested against earlier looks' carried items only: a `Loot` reads drops before grids, so an item picked
            # up between the two is in both (rca/2026-10-14/run-0305-findings.md §5.3).
            kinds = dict(loot.classes)
            kept = []
            for drop in loot.drops:
                kind = kinds.get(drop.unit_id)
                if self._at(drop.x, drop.y, kind):
                    continue
                if drop.unit_id in self.rejected:
                    self.places.append((kind, drop.x, drop.y))
                    LOG.info(
                        "Macro: put down: %s at (%.0f, %.0f), unit %d, the loop's own field drop (%s): not picked up, "
                        'stood by or warned about again this game',
                        drop.label, drop.x, drop.y, drop.unit_id, self.rejected[drop.unit_id],
                    )  # fmt: skip
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
