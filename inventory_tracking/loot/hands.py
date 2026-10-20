"""The live hands of the loot layer's field routine (loot/design.md §2.2 `LootHands`; loot/api.py `FieldHands`):
adapters over code that exists, reads through the run, input only through its actuator.

- `identify`: the Tome's clicks (macros/junk.py `identify`: the inventory opened, the tome right clicked, the item
  clicked, its identified flag checked in memory, the panels closed after).
- `appraise`: the identify worker's read and KB lookup made now (identify/service.py `IdentifyWorker.appraise`,
  read-only), its read and result taken from the shadow's book (loot/shadow.py `BOOK`, which the worker notes into).
- `drop`: macros/cube.py `drop_item` (the protected items refused there too: engine.py `protected`); `reject`:
  game/kept.py `PutDown.reject`.
- `cubed` / `take_out` / `put_back`: the cube's items, out into the inventory (cube.py `unpack`) and back (cube.py
  `stash_only`), for the field identify of the cube's items (loot/api.py, 2026-10-20 ~13:28).
- `unquiet`: no hostile within SIGHT (macros/hunting/base.py), life not under the healer's floor (macros/stops.py
  `low_life`, as running/room.py `unsafe`), no valuable the loop could pick up now on the ground, out of town, alive,
  mouse mode, no panel open (but the visit's own, `visit`).
- `visit`: one opening of the inventory for a whole field visit (loot/api.py ONE_OPENING): the acts inside it leave
  the inventory and the cube open when they end normally (cube.py `held_shut`), the visit's end closes them once,
  through a cancel too; an act that fails closes them at once as before, and the next act opens them again.
"""

import math
from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import contextmanager

from inventory_tracking.game.kept import PutDown
from inventory_tracking.game.records import VALUABLE, Carried, Loot, Pack, has_room
from inventory_tracking.loot.facts import ItemFacts
from inventory_tracking.loot.shadow import BOOK, Appraised, Book
from inventory_tracking.loot.value import CollectionCopies, OwnedCopies
from inventory_tracking.macros.cube import KEPT, close, drop_item, loot, stash_only, unpack
from inventory_tracking.macros.engine import Run, protected
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
        cain_ahead: Callable[[], bool] = lambda: False,
    ) -> None:
        self.run, self.inventory_key, self.own, self.appraiser = run, inventory_key, own, appraise
        self.cain_ahead = cain_ahead  # a town visit is due: Cain identifies the inventory and the cube at once there
        self.put_down, self.book, self.owned = put_down, book, owned or CollectionCopies()
        # The panels a field visit holds open (`visit`); None outside a visit: every act closes its own
        self.holding: set[str] | None = None

    @contextmanager
    def visit(self) -> Generator[None]:
        """One opening of the inventory for the field visit inside it (loot/api.py ONE_OPENING): the acts leave the
        panels they opened open, and the visit's end closes them once, through a failure, the player's hand or a
        cancel too (cube.py `close`). A visit inside a visit is the outer one's."""
        if self.holding is not None:
            yield
            return
        self.holding = set()
        try:
            yield
        finally:
            held, self.holding = self.holding, None
            if held:
                close(self.run, tuple(panel for panel in ('inventory', 'cube') if panel in held))

    def _held(self, panels: tuple[str, ...]) -> bool:
        """Whether the act about to open `panels` leaves them open (a visit holds them): noted held at once, so a
        failure that closes them (`held_shut`) is followed by `_shut`."""
        if self.holding is None:
            return False
        self.holding.update(panels)
        return True

    def _shut(self) -> None:
        """An act inside a visit failed: it closed every panel (cube.py `held_shut`), none is held now."""
        if self.holding is not None:
            self.holding.clear()

    def game(self) -> str | None:
        world = self.run.world()
        return world.game_name if world.in_game and world.game_name else None

    def carried(self) -> Pack | None:
        return self.run.reads.carried()

    def loops(self, pack: Pack) -> Sequence[Carried]:
        own = self.own(pack)
        return loot(pack, own) if own is not None else []

    def cubed(self, pack: Pack) -> Sequence[Carried]:
        """The cube's items (the loop's: macros/volatile.py), none before the loop told the player's cells, none
        protected (the player's by its stats: engine.py `protected`)."""
        if self.own(pack) is None:
            return []
        return [item for item in pack.in_cube if item.txt not in KEPT and protected(self.run, item) is None]

    def take_out(self, items: Sequence[Carried]) -> list[int]:
        key = self.inventory_key()
        if key is None or not items:
            return []
        try:
            unpack(self.run, key, items, keep_open=self._held(('inventory', 'cube')))  # Ctrl + click, two tries
        except BaseException:
            self._shut()
            raise
        pack = self.carried()
        carried = {item.unit_id for item in pack.items} if pack is not None else set()
        return [item.unit_id for item in items if item.unit_id in carried]

    def put_back(self, units: Sequence[int]) -> int:
        key = self.inventory_key()
        pack = self.carried()
        own = self.own(pack) if pack is not None else None
        if key is None or own is None or not units:
            return 0
        wanted = frozenset(units)
        try:
            return stash_only(self.run, key, own, lambda item: item.unit_id in wanted,
                              keep_open=self._held(('inventory', 'cube')))  # fmt: skip
        except BaseException:
            self._shut()
            raise

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
        # Town is quiet: the tome there too, unless a visit is due and Cain identifies all at once (the player,
        # 2026-10-20: "we picked up magic ring and haven't id'ed it"; "when we visit cain it identifies all items across
        # cube + inventory, so, in most cases this is preferrable way to identify items when in town")
        if player.in_town and self.cain_ahead():
            return 'in town: Cain identifies them at the visit due'
        # The panels the field visit holds open itself are no hand (`visit`); any other still waits
        panels = [panel for panel in world.open_panels if panel not in (self.holding or ())]
        if panels:
            return f'{", ".join(panels)} open'
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
        try:
            return identify(self.run, key, items, keep_open=self._held(('inventory',)))
        except BaseException:
            self._shut()
            raise

    def appraise(self, units: Sequence[int]) -> Mapping[int, Appraised]:
        self.appraiser(list(units))  # the worker's read, noted into the book
        return {unit: entry for unit in units if (entry := self.book.get(unit)) is not None}

    def copies(self, facts: ItemFacts) -> Sequence[ItemFacts] | None:
        return self.owned.copies(facts)

    def drop(self, item: Carried, why: str) -> bool:
        key = self.inventory_key()
        if key is None:
            return False
        try:
            return drop_item(self.run, key, item, why, keep_open=self._held(('inventory',)))
        except BaseException:
            self._shut()
            raise

    def reject(self, item: Carried, why: str) -> None:
        self.put_down.reject(item.unit_id, why)
