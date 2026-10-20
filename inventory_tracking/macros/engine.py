"""One macro run: read the world, act, and go on only when the game shows the result.

A routine is a plain function of a `Run`. It acts through `run.actuator` and moves forward with
`run.expect(...)`, which polls memory until a predicate holds or raises `Abort`. Pauses pace
the input; they never stand in for evidence. A second hotkey press sets `cancelled`.
"""

import math
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from threading import Event
from typing import TYPE_CHECKING

from inventory_tracking.game.records import (
    Carried,
    Loot,
    Monster,
    Pack,
    StashView,
    Stocked,
    Teleport,
    Thing,
    Warp,
    Wear,
    World,
)
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.actuator import Abort, Actuator, Cancelled, Flipped
from inventory_tracking.macros.timing import Pace
from inventory_tracking.models import PotionType


if TYPE_CHECKING:
    from inventory_tracking.automation.ledger import PotionLedger
    from inventory_tracking.macros.build import Build  # build.py is above this module
    from inventory_tracking.macros.pad import PadActs


POLL = 0.03


class Reads:
    """A run's optional game reads, None where the run has no reader (tests, harnesses, no memory)."""

    def __init__(self, run: Run) -> None:
        self._run = run

    def carried(self) -> Pack | None:
        read = self._run.carried
        return read() if read is not None else None

    def teleport(self) -> Teleport | None:
        read = self._run.teleport
        return read() if read is not None else None

    def stash_view(self) -> StashView | None:
        read = self._run.stash_view
        return read() if read is not None else None

    def loot(self) -> Loot | None:
        read = self._run.loot
        return read() if read is not None else None

    def wear(self) -> Wear | None:
        read = self._run.wear
        return read() if read is not None else None

    def own_teleport(self) -> bool | None:
        read = self._run.own_teleport
        return read() if read is not None else None

    def worn_skills(self) -> frozenset[int] | None:
        read = self._run.worn_skills
        return read() if read is not None else None

    def hovered(self) -> tuple[int, int] | None:
        read = self._run.hovered
        return read() if read is not None else None

    def ground(self) -> Ground | None:
        read = self._run.ground
        return read() if read is not None else None

    def unit_states(self, monster: Monster) -> bytes | None:
        read = self._run.unit_states
        return read(monster) if read is not None else None


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
        self.reads = Reads(self)
        # The build played (macros/build.py); re-chosen at the first look showing the character (runner.py `choosing`)
        self.build = build
        self.actuator = actuator
        self.pace = pace
        self.clock = clock
        self.cancelled = cancelled or Event()
        self.say = say
        self.keys: dict[int, str] = {}
        self.hands = hands  # base codes of the weapon set in hand (world.GameMemory.hands)
        self.teleport = teleport  # the worn Teleport staff (world.GameMemory.teleport)
        self.loot = loot  # drops, belt and life for the pickup step (world.GameMemory.loot)
        self.prebuff_hands: frozenset[str] = frozenset()  # the set the buffs are cast with
        self.battle_hands: frozenset[str] = frozenset()  # the main set: fought with, and held when a game is left
        self.hovered: Callable[[], tuple[int, int] | None] | None = None  # world.GameMemory.hovered
        # Whether Teleport is the character's own (Enigma), not charges; None unread
        self.own_teleport: Callable[[], bool | None] | None = None  # world.GameMemory.own_teleport
        # Skills worn items give (the Sling's Town Portal, portal.py `portal_source`); None unread
        self.worn_skills: Callable[[], frozenset[int] | None] | None = None
        self.wear: Callable[[], Wear | None] | None = None  # the most worn item (world.GameMemory.wear)
        self.cta: Callable[[], bool | None] | None = None  # a Call to Arms worn in either set (world.GameMemory.cta)
        # Done with the other weapon set at an arrival's input check (routines.py `took_input`; cta.py `cast_in_hand`)
        self.arrival_swap: Callable[[], object] | None = None
        # skill -> clock of its last cast that took, kept across runs (buffs.py `Buffs.took_of`); None: per run
        self.lasting: dict[int, float] | None = None
        # last skill key tapped, the right skill before it, when, and whether a key was held (routines.press_skill)
        self.quick: tuple[int, int | None, float, bool] | None = None
        # Whether a look since that key showed its skill on the right button, so the next key waits only for the
        # button back (routines.quick_cast_over); fight looks see it 0.08-0.16 s after the key (2026-10-14).
        self.quick_shown = False
        self.hover_note: Callable[[], str] | None = None  # the record it read last, whole (world.GameMemory.hover_note)
        # the monsters lying dead as (unit id, x, y), world units (world.GameMemory.corpses): Engorge needs one
        self.corpses: Callable[[], tuple[tuple[int, float, float], ...]] | None = None
        # A monster's state words raw (game/layout.py STATE_RUN; world.GameMemory.states), None unread: whether a
        # cast on it shows (macros/buffs.py `Buffs.settle`; the player, 2026-10-20: "ok, recast")
        self.unit_states: Callable[[Monster], bytes | None] | None = None
        # missiles in flight as (owner unit, class, x, y), priced by combat/threats (world.GameMemory.flights)
        self.flights: Callable[[frozenset[int]], tuple[tuple[int, int, float, float], ...]] | None = None
        # when the healer (`make osd`) last gave the mercenary a potion of a kind (automation/ledger.py `given_at`)
        self.given: Callable[[PotionType], float | None] | None = None
        # The healer's ledger: the drinker claims a potion before its key so the healer stands off
        self.ledger: PotionLedger | None = None
        self.warps: Callable[[], tuple[Warp, ...]] | None = None  # the doors loaded (world.GameMemory.warps)
        # the current level's walkable ground (the level guide's map); None unknown
        self.ground: Callable[[], Ground | None] | None = None
        self.things: Callable[[], tuple[Thing, ...]] | None = None  # a mark's objects (world.GameMemory.things)
        self.containers: Callable[[], tuple[Thing, ...]] | None = None  # chests and the like (GameMemory.containers)
        self.carried: Callable[[], Pack | None] | None = None  # the inventory's items, the cube's rows (GameMemory)
        # Whether a carried item is the player's by its stats (loop.py `players_item`): never sold nor dropped
        self.players_item: Callable[[Carried], bool] | None = None
        # Why a carried item is kept whatever the appraisal says (macros/keepers.py); never sold
        self.kept_item: Callable[[Carried], str | None] | None = None
        self.stock: Callable[[int], tuple[Stocked, ...]] | None = None  # a vendor's stock (GameMemory.stock)
        # the stash's pages and resource stacks, None unread (world.GameMemory.stash_view)
        self.stash_view: Callable[[], StashView | None] | None = None
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
        # the warning of a level run standing by a valuable with no room; the loop's watchdog acts on this call, not
        # the text (runner.py `_stand_by`)
        self.stand_by: Callable[[str], None] = lambda text: self.warn(text)
        # on `clock`: the press this run answers is not worth an input after it (runner.EXPIRES)
        self.deadline = math.inf
        self.light = 0  # above 0 the looks at the game leave the monsters and doors out (`lightly`)
        self.hurry: Callable[[], None] | None = None  # asks the service to read the level now (teleport.card_for)
        # The pad back end in controller mode (macros/pad.py); None: keys and mouse
        self.pad: PadActs | None = None
        # The loot's field routine (loot/api.py `settle`: identify the items picked for it and put down the ones that
        # fail, M4 of loot/design.md), given the site's name; None: no field routine (running/execution.py)
        self.field: Callable[[str], object] | None = None

    def world(self) -> World:
        if self.cancelled.is_set():
            raise Cancelled
        try:
            world = self.read()
        except (OSError, ValueError) as exc:
            raise Abort(f'the game could not be read ({exc})') from exc
        if self.pad is not None:
            world = self.pad.seen(world)  # the skills on the pad's records stand for the skills on keys
        if self.quick is not None and not self.quick_shown:
            self.quick_shown = world.player is not None and world.player.right_skill == self.quick[0]
        if self.observe is not None:
            self.observe(world)
        return world

    def stops(self, stop: BaseException) -> bool:
        """Whether an act's Abort ends the run regardless of its caller: cancelled, or the input mode flipped
        (`Flipped`: the runner replays the request)."""
        return self.cancelled.is_set() or isinstance(stop, Flipped)

    @contextmanager
    def lightly(self) -> Generator[None]:
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
        """The first world in which `predicate` holds, polled; `Abort` after `timeout` seconds."""
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
        except Abort as stop:
            if self.stops(stop):
                raise
            return None

    def pause(self, kind: str) -> None:
        if self.cancelled.is_set():
            raise Cancelled
        self.pace.pause(kind)


def protected(run: Run, item: Carried) -> str | None:
    """Why `item` is never sold, dropped or put down; None when the loop may give it up. Every give-up asks this
    first ("we shouldn't sell our own equipment or valuable items", the player, 2026-10-17)."""
    if run.players_item is not None and run.players_item(item):
        return "the player's by its stats"
    if run.kept_item is not None and (why := run.kept_item(item)):
        return f'kept by its stats ({why})'
    return None
