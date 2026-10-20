"""The live hands of the loot layer's field routine (loot/design.md §2.2 `LootHands`; loot/api.py `FieldHands`):
adapters over code that exists, reads through the run, input only through its actuator.

- `identify`: the Tome's clicks (macros/junk.py `identify`: the inventory opened, the tome right clicked, the item
  clicked, its identified flag checked in memory, the panels closed after).
- `appraise`: the identify worker's read and KB lookup made now (identify/service.py `IdentifyWorker.appraise`,
  read-only), its read and result taken from the shadow's book (loot/shadow.py `BOOK`, which the worker notes into).
- `drop`: macros/cube.py `drop_item` (the protected items refused there too: engine.py `protected`); `reject`:
  game/kept.py `PutDown.reject`.
- `unquiet`: no hostile within SIGHT (macros/hunting/base.py), life not under the healer's floor (macros/stops.py
  `low_life`, as running/room.py `unsafe`), no valuable the loop could pick up now on the ground, out of town, alive,
  mouse mode, no panel open.
"""

import math
from collections.abc import Callable, Mapping, Sequence

from inventory_tracking.game.kept import PutDown
from inventory_tracking.game.records import VALUABLE, Carried, Loot, Pack, has_room
from inventory_tracking.loot.facts import ItemFacts
from inventory_tracking.loot.shadow import BOOK, Appraised, Book
from inventory_tracking.loot.value import CollectionCopies, OwnedCopies
from inventory_tracking.macros.cube import drop_item, loot
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.hunting.base import SIGHT, hostiles
from inventory_tracking.macros.junk import identify
from inventory_tracking.macros.lootpolicy import GUARD, verdict
from inventory_tracking.macros.routines import DEAD
from inventory_tracking.macros.stops import low_life


__all__ = ['GameHands', 'waiting_valuable']

Cells = frozenset[tuple[int, int, int]]


def waiting_valuable(found: Loot) -> str | None:
    """A valuable of the pickup on the ground the loop could take now (room for it, held by the guard), None with
    none: the field identify waits for it ("no valuable left on the ground unpicked"). One with no room does not
    hold it: the routine may make that room."""
    for drop in found.drops:
        if drop.kind != VALUABLE or not has_room(found.room, drop.size):
            continue
        if verdict(drop, GUARD, room=True, shown=drop.unit_id in found.shown, looped=True).hold:
            return drop.label
    return None


class GameHands:
    """`FieldHands` over a run. `inventory_key()`: the key that opens the inventory (None unbound); `own(pack)`: the
    player's cells (macros/loop.py `Loop.own`), None not told yet (then nothing is the loop's); `appraise(units)`: the
    identify worker's (runner.py `MacroRunner.appraise`)."""

    def __init__(
        self,
        run: Run,
        *,
        inventory_key: Callable[[], str | None],
        own: Callable[[Pack], Cells | None],
        appraise: Callable[[list[int]], Mapping[int, str]],
        put_down: PutDown,
        book: Book = BOOK,
        owned: OwnedCopies | None = None,
    ) -> None:
        self.run, self.inventory_key, self.own, self.appraiser = run, inventory_key, own, appraise
        self.put_down, self.book, self.owned = put_down, book, owned or CollectionCopies()

    def game(self) -> str | None:
        world = self.run.world()
        return world.game_name if world.in_game and world.game_name else None

    def carried(self) -> Pack | None:
        return self.run.reads.carried()

    def loops(self, pack: Pack) -> Sequence[Carried]:
        own = self.own(pack)
        return loot(pack, own) if own is not None else []

    def unquiet(self) -> str | None:
        run = self.run
        if run.pad is not None:
            return 'controller mode (Cain in town)'
        world = run.world()
        player = world.player
        if player is None or not world.in_game:
            return 'no character read'
        if player.mode in DEAD:
            return 'the character is dead'
        if player.in_town:
            return 'in town (Cain)'
        if world.open_panels:
            return f'{", ".join(world.open_panels)} open'
        near = sum(1 for m in hostiles(world) if math.dist((m.x, m.y), (player.x, player.y)) <= SIGHT)
        if near:
            return f'{near} hostiles within {SIGHT:.0f}'
        found = run.loot() if run.loot is not None else None
        if found is None:
            return 'the ground not read'
        if found.max_life and low_life((found.life, found.max_life)):
            return f'life low ({found.life}/{found.max_life})'
        if (label := waiting_valuable(found)) is not None:
            return f'{label} lies on the ground'
        return None

    def identify(self, items: Sequence[Carried]) -> list[Carried]:
        key = self.inventory_key()
        if key is None:
            return []
        return identify(self.run, key, items)

    def appraise(self, units: Sequence[int]) -> Mapping[int, Appraised]:
        self.appraiser(list(units))  # the worker's read, noted into the book
        return {unit: entry for unit in units if (entry := self.book.get(unit)) is not None}

    def copies(self, facts: ItemFacts) -> Sequence[ItemFacts] | None:
        return self.owned.copies(facts)

    def drop(self, item: Carried, why: str) -> bool:
        key = self.inventory_key()
        return key is not None and drop_item(self.run, key, item, why)

    def reject(self, item: Carried, why: str) -> None:
        self.put_down.reject(item.unit_id, why)
