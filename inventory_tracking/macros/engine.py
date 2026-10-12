"""One macro run: read the world, act, and go on only when the game shows the result.

A routine is a plain function of a `Run`. It acts through `run.actuator` and moves forward with
`run.expect(...)`, which polls memory until a predicate holds or raises `Abort`. Pauses pace
the input; they never stand in for evidence. A second hotkey press sets `cancelled`.
"""

import math
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from threading import Event
from typing import TYPE_CHECKING

from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.actuator import Abort, Actuator, Cancelled
from inventory_tracking.macros.timing import Pace
from inventory_tracking.macros.world import Loot, Teleport, Thing, Warp, World


if TYPE_CHECKING:
    from inventory_tracking.macros.build import Build  # build.py is above this module


POLL = 0.03


class Run:
    def __init__(
        self,
        read: Callable[[], World],
        actuator: Actuator,
        pace: Pace,
        *,
        clock: Callable[[], float] = time.monotonic,
        cancelled: Event | None = None,
        say: Callable[[str], None] = lambda text: None,
        hands: Callable[[], tuple[str, ...]] | None = None,
        teleport: Callable[[], Teleport | None] | None = None,
        loot: Callable[[], Loot] | None = None,
        build: Build,
    ) -> None:
        self.read = read
        # The build the run plays (macros/build.py): what the character moves by, casts before a game and holds.
        # The runner's, chosen again at the run's first look that shows the character (runner.py `choosing`);
        # until that look, the one it played before.
        self.build = build
        self.actuator = actuator
        self.pace = pace
        self.clock = clock
        self.cancelled = cancelled or Event()
        self.say = say
        self.keys: dict[int, str] = {}
        self.hands = hands  # base codes of the weapon set in hand (world.GameMemory.hands)
        self.teleport = teleport  # the worn Teleport staff (world.GameMemory.teleport)
        self.loot = loot  # the drops, the belt and the life the pickup step decides on (world.GameMemory.loot)
        self.prebuff_hands: frozenset[str] = frozenset()  # the set the buffs are cast with
        self.battle_hands: frozenset[str] = frozenset()  # the main set: fought with, and held when a game is left
        self.hovered: Callable[[], tuple[int, int] | None] | None = None  # world.GameMemory.hovered
        # the skill key tapped last, the right-button skill before it, when, and whether the macro held a
        # key or button then (routines.press_skill)
        self.quick: tuple[int, int | None, float, bool] | None = None
        self.hover_note: Callable[[], str] | None = None  # the record it read last, whole (world.GameMemory.hover_note)
        # the monsters lying dead as (unit id, x, y), world units (world.GameMemory.corpses): Engorge needs one
        self.corpses: Callable[[], tuple[tuple[int, float, float], ...]] | None = None
        self.warps: Callable[[], tuple[Warp, ...]] | None = None  # the doors loaded (world.GameMemory.warps)
        # the walkable ground of the level the character is on, None while not known (the level guide's map)
        self.ground: Callable[[], Ground | None] | None = None
        self.things: Callable[[], tuple[Thing, ...]] | None = None  # a mark's objects (world.GameMemory.things)
        self.containers: Callable[[], tuple[Thing, ...]] | None = None  # chests and the like (GameMemory.containers)
        # research: every object unit shown, raw (world.GameMemory.objects)
        self.objects: Callable[[], list[dict]] | None = None
        self.research: Callable[..., list[str]] | None = None  # world.GameMemory.hover_candidates
        # (level before this one, seconds since it was left), journey.Journey.arrival
        self.arrival: Callable[[], tuple[int | None, float]] | None = None
        # where the super uniques seen on a level were last seen, world units (terror.tracker.ZoneTracker.supers)
        self.supers: Callable[[int], list[tuple[float, float]]] | None = None
        # whether the route is at its end on a level (routes/progress.py `Progress.ending`); None: no routes
        self.ending: Callable[[int], bool] | None = None
        self.observe: Callable[[World], None] | None = None  # sees every world read
        self.mark: Callable[[str], None] = lambda name: None  # a moment of the press's trace (latency.py)
        # a warning that stays on the card until it is taken back with None (runner.py `_warn`)
        self.warn: Callable[[str | None], None] = lambda text: None
        # on `clock`: the press this run answers is not worth an input after it (runner.EXPIRES)
        self.deadline = math.inf
        self.light = 0  # above 0 the looks at the game leave the monsters and doors out (`lightly`)
        self.hurry: Callable[[], None] | None = None  # asks the service to read the level now (teleport.card_for)

    def world(self) -> World:
        if self.cancelled.is_set():
            raise Cancelled
        try:
            world = self.read()
        except (OSError, ValueError) as exc:
            raise Abort(f'the game could not be read ({exc})') from exc
        if self.observe is not None:
            self.observe(world)
        return world

    @contextmanager
    def lightly(self) -> Iterator[None]:
        """Within the block the game is looked at without its monsters and doors (world.GameMemory.world)."""
        self.light += 1
        try:
            yield
        finally:
            self.light -= 1

    def in_time(self, what: str) -> None:
        """Stop when `what` would come too long after the press that asked for it."""
        late = self.clock() - self.deadline
        if late > 0:
            raise Abort(f'{what} dropped: {late * 1000:.0f} ms too long after its key')

    def expect(self, what: str, predicate: Callable[[World], bool], timeout: float, poll: float = POLL) -> World:
        """The first world in which `predicate` holds, looked for every `poll` seconds; `Abort` when
        none comes in `timeout` seconds."""
        deadline = self.clock() + timeout
        while True:
            world = self.world()
            if predicate(world):
                return world
            if self.clock() >= deadline:
                raise Abort(f'{what}: not seen in {timeout:g}s')
            self.pace.sleep(poll)

    def seen(self, predicate: Callable[[World], bool], timeout: float, poll: float = POLL) -> World | None:
        """As `expect`, for evidence that is welcome but not required."""
        try:
            return self.expect('', predicate, timeout, poll)
        except Abort:
            if self.cancelled.is_set():
                raise
            return None

    def pause(self, kind: str) -> None:
        if self.cancelled.is_set():
            raise Cancelled
        self.pace.pause(kind)
