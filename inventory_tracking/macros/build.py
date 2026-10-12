"""What a build is to the framework: the contracts it fills, and the one object the framework asks.

The framework (macros/, combat/) owns the loop and knows no class, skill or item by name; a build
imports the framework and fills it, and is handed to it (architecture.md 4.0). This module is the
whole of what the framework may ask of a build, and it imports nothing from a build:

- `Attack`: where to cast, what a cast takes off whom, how far it hurts, the skill the fight holds.
- `MovementSet`: a combination of ways to move (a jump of one kind or another, a walk) with its own
  route logic, asked for the next move toward a goal from `MoveFacts` and within an `Intent`. It
  answers with a `Step` or with `NoWay` and the reason, never with silence.
- `Buff`: one row of the buff plan, cast by the shared executor or by a caster the build names.
- `Tactic`: what a kind of pack adds to the one price of a place.
- `Build`: those, the weapon sets and the numbers (`BuildSettings`), with `applies` to say whose it
  is; `choose` takes the first build that applies.

Every decision here is pure: facts in, an answer out. Reading the game and making the move, the cast
or the swap stay in macros/ (travel.py `Travel.make`, teleport.py, routines.py).

`Step`, the order for one move, is defined here and not in travel.py, which makes it: travel.py
chooses a move from `MoveFacts`, so it imports this module, and this module has to import nothing of it.
"""

import math
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

from inventory_tracking.combat.policy import Choice, Foe, Observation, Point
from inventory_tracking.combat.stance import Camp, Jump
from inventory_tracking.config import Config
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.routines import Loadout
from inventory_tracking.macros.world import Monster, Teleport, World
from inventory_tracking.terror.danger import Pack


def nowhere(spot: Point) -> bool:
    """No place is shunned."""
    return False


@dataclass(frozen=True)
class MoveFacts:
    """What a choice of a move is made from: the character's place and what it can move by now, read
    once by the caller. Exactly what `Travel.jumps`, `stride` and `around` read from the run and the
    world today, so that they can be asked without either."""

    here: Point  # where the character stands, world units
    now: float  # the run's clock
    slots: tuple[int | None, ...]  # skill id by slot (`World.slots`): what is on a key
    # The worn staff with Teleport charges, in hand or not, and what it has left; None: no staff (Teleport,
    # if it is in a slot, is a skill of the character's own) or the staff could not be read
    staff: Teleport | None
    ground: Ground | None  # the walkable and flyable cells of the level; None: not known
    doors: tuple[Door, ...]  # the doors around the character: a closed one bars a walk and a thrown jump
    aspect: float  # the window's width over its height: what is in view, and so can be aimed at
    last_used: Mapping[int, float] = field(default_factory=dict)  # skill -> clock time it was last jumped by
    failed: Mapping[int, float] = field(default_factory=dict)  # skill -> clock time a jump by it last moved nothing

    def since_used(self, skill: int) -> float:
        """Seconds since the last jump by `skill`; inf when there was none."""
        return self.now - self.last_used.get(skill, -math.inf)

    def since_failed(self, skill: int) -> float:
        """Seconds since a jump by `skill` last moved nothing; inf when none did."""
        return self.now - self.failed.get(skill, -math.inf)


@dataclass(frozen=True)
class Intent:
    """What the caller of a move allows: one named constant per kind of caller (the player's own
    step, the seek step, a move the mode makes by itself). The ways to move are the same for all of
    them; what differs is what may be spent, waited for and trusted."""

    name: str
    reserve: int  # charges of the staff this caller never spends: with as many or fewer left, no jump by them
    may_swap: bool  # whether the weapon set may be changed for the move
    may_wait: bool  # whether a casting delay about to end is worth waiting out (`MovementSet.wait`)
    distrust: float  # seconds a way that moved nothing is left alone
    # With fewer charges than this a jump that costs none comes before one that costs a charge, which is
    # still made where no other leads; inf: always before it, 0: never
    sparing: float = 0.0
    walks_under: float = 0.0  # with fewer charges than this a walk too comes before a jump that costs one
    short: float = 0.0  # units short of the goal the move is to end (a stand-off from a hostile)
    shot: bool = False  # a short walk has to end with a clear shot at the goal
    shuns: Callable[[Point], bool] = nowhere  # places not to end a move at


@dataclass(frozen=True)
class Step:
    """A move of the mode's own: where to, and by what (a skill the character jumps by; None: one
    click's walk). `camp` is the place decision it came from, when one was made."""

    spot: Point
    skill: int | None = None
    camp: Camp | None = None

    @classmethod
    def to(cls, place: Camp) -> Step:
        """The move to a place, by the way the place was chosen for."""
        return cls(place.spot, place.skill, place)


@dataclass(frozen=True)
class NoWay:
    """A movement set's answer when it has no move: why, for the log and the player. Never empty.
    `arrived` tells the two kinds apart: the character is as near the goal as the move was to end (a
    goal nearer than `Intent.short` too: never a step back), where the caller stops; or nothing leads
    on, where the caller may ask another set."""

    reason: str
    arrived: bool = False  # there already: no move is wanted. False: blocked, a move is wanted and none was found

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError('a movement set that has no way says why')


Leg = Step | NoWay  # the next move, or the reason there is none: a movement set never answers with None


class MovementSet(Protocol):
    """A combination of ways to move and how it uses them (architecture.md 4.3: `Charged`, `Empty`,
    a walker). The navigator asks the first set that `applies`, anew at each arbitration and never in
    the middle of a step. Every method is pure and reads nothing but its arguments."""

    name: str

    def applies(self, facts: MoveFacts) -> bool:
        """Whether this is the character's situation now (the staff and what it holds, the skills on keys)."""
        ...

    def leg(self, facts: MoveFacts, goal: Point, intent: Intent) -> Leg:
        """The next move toward `goal` within `intent`: one jump or one click's walk, onto footing and
        in view; or `NoWay` with the reason. Asked once per move; the caller makes the step
        (`Travel.make`) and asks again from where the character then stands."""
        ...

    def eta(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Seconds to stand at `goal` by this set's ways, without moving; inf exactly where `leg` has no way."""
        ...

    def jumps(self, facts: MoveFacts, intent: Intent) -> tuple[Jump, ...]:
        """The skills a place can be jumped to by now within `intent`, the preferred first. Asked
        when a place to stand is priced (combat/stance.py `camp(jumps=)`: each place by the first jump
        that reaches it), and by `Travel.make` when the jump a step names can no longer be made."""
        ...

    def wait(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Seconds to let pass before `leg` is asked: a casting delay about to end on a way worth
        having toward `goal`. 0.0: ask now, and always so when `intent.may_wait` is off. The caller
        sleeps, reads the game again and asks `leg` with the new facts."""
        ...


class Attack(Protocol):
    """How a build deals damage, as far as the framework has to know: it holds one input for `skill`,
    fights what stands within `reach`, keeps the pointer where `aim` says and prices a place to stand
    by what `dealt` takes from there. Everything else of the model (its geometry, its damage table,
    its timing) stays behind these."""

    skill: int  # the strike: the skill whose input the fight holds (a mouse button that has it, else its key)
    reach: float  # units: a hostile further off, or with no clear line, is not in reach of a cast

    def sees(self, seen: Observation, companions: Sequence[Monster]) -> Observation:
        """The observation with what this attack reads off the character's own units filled in (a
        link they hold between monsters, a mark); `seen` itself when there is nothing. Asked once for
        each observation the fight builds from the game, before `aim` or a place is priced; never by
        the simulator, which builds its own."""
        ...

    def aim(self, seen: Observation, through: Collection[int] = ()) -> Choice | None:
        """Where to cast now, or None when no cast is worth making (and while the player is moving,
        if the attack yields the pointer). With `through`, only a cast laid through one of those
        units, or None: the fight asks that first for the monsters to kill before the rest (a boss in
        reach) and without `through` after. On None the framework aims straight at what is in reach
        (combat/controller.py `aim_choice`), so a monster in reach is never left standing. Asked every
        DECIDE_SECONDS of a fight; `attack.aim` is itself a `Policy`."""
        ...

    def dealt(self, origin: Point, focal: Point, foes: Mapping[int, Foe]) -> Mapping[int, float]:
        """The points one cast from `origin` at `focal` takes off each of `foes` (by unit id) where
        they stand: not capped by what a monster has left and not weighted, which the caller does. A
        unit left out takes nothing. Asked when a place is priced (combat/stance.py `taken`): for
        every place looked at, once per hostile in reach of it with `focal` on that hostile and `foes`
        the hostiles in reach, so it has to be cheap; and for whether a monster outlives so many casts."""
        ...


@dataclass(frozen=True)
class BuffFacts:
    """What a buff's conditions are asked with: the world, the clock, the fight as the mode sees it
    and the executor's memory of what was cast when."""

    world: World
    now: float
    foes: tuple[Monster, ...] = ()  # the hostiles the mode goes for
    reachable: tuple[Monster, ...] = ()  # those of them in the attack's reach with a clear shot
    prey: Monster | None = None  # the one the strike is aimed through; None outside a fight
    # (skill, the unit it was cast on or under; None: on no unit) -> clock time of the last cast
    cast_at: Mapping[tuple[int, int | None], float] = field(default_factory=dict)

    def since(self, skill: int, unit: int | None = None) -> float:
        """Seconds since `skill` was last cast (on or under `unit`); inf when it never was."""
        return self.now - self.cast_at.get((skill, unit), -math.inf)


def always(facts: BuffFacts, target: Monster | None) -> bool:
    """Every cast that is due pays."""
    return True


@dataclass(frozen=True)
class Buff:
    """One row of a build's buff plan (architecture.md 4.2). The shared executor casts it with one
    aim and one key when its phase has come, `due` holds and `worth` agrees; a cast that is more than
    that is made by the caster the row names."""

    skill: int
    # prebuff: a game's start; upkeep: no hostile in reach; fight: under the held strike; opening: before the first
    phase: Literal['prebuff', 'upkeep', 'fight', 'opening']
    due: Callable[[BuffFacts], bool]  # whether it is wanted now: so long since the last, a target that fits
    on: Literal['self', 'monster', 'corpse', 'ground'] = 'self'  # what the pointer is put on for the key
    # Whom it is cast on, or under ('ground'); None: on nobody (the character itself, or the caster finds its own)
    target: Callable[[BuffFacts], Monster | None] | None = None
    # What the game shows of it on the character: True on, False missing, None unreadable. With it the row is
    # cast only while it reads missing, and the executor's rule for a cast the state does not show applies.
    state: Callable[[World], bool | None] | None = None
    needs: Literal['prebuff', 'battle'] | None = None  # the weapon set it is cast with; None: what is in hand
    worth: Callable[[BuffFacts, Monster | None], bool] = always  # whether the cast pays, the target known
    caster: str | None = None  # a name in `Build.casters`; None: aim and key, the shared one
    also: tuple[int, ...] = ()  # the other skills its caster presses: they too have to be on keys


class Tactic(Protocol):
    """What one kind of enemy adds to the price of a place (architecture.md 4.4). Every tactic whose
    pack is in the fight contributes: the bars are united, the distances intersected, the highest
    caution holds. A tactic owns no loop."""

    name: str

    def applies(self, pack: Pack) -> bool:
        """Whether this pack is of its kind."""
        ...

    def caution(self, base: float) -> float:
        """The caution to fight this pack with, from the one the threat and the pressure gave."""
        ...

    def bars(self, spot: Point, pack: Pack) -> bool:
        """Whether `spot` is a place never stood at with this pack about."""
        ...

    def keep(self, pack: Pack) -> tuple[float, float]:
        """(least, most) units wanted between the character and the pack."""
        ...

    def opens(self) -> tuple[int, ...]:
        """The skills wanted cast before the first strike (rows of the buff plan's `opening` phase)."""
        ...


class BuildSettings(Config):
    """A build's numbers: frozen, changed only by `with_overrides`. Empty until a stage has a number
    that differs by build (the caution's curve, the charge rule's count, the drinking marks)."""


@dataclass(frozen=True)
class Build:
    """One object the framework asks. A layer above another (a class, a build of it, a character) is
    the one below with changes (`dataclasses.replace`)."""

    name: str
    applies: Callable[[World], bool]  # whose it is: the character, the skills on its keys
    attack: Attack | None  # None: the build does not fight on its own
    movement: tuple[MovementSet, ...]  # the first that applies is the one asked
    buffs: tuple[Buff, ...] = ()  # in the order they are cast
    tactics: tuple[Tactic, ...] = ()
    weapons: Loadout | None = None  # which weapon set is for what; None: the hands are left as they are
    casters: Mapping[str, Callable[..., object]] = field(default_factory=dict)  # the casts that are more than a key
    settings: BuildSettings = field(default_factory=BuildSettings)


def choose(builds: Sequence[Build], world: World, fallback: Build) -> Build:
    """The first of `builds` that applies to the character in the game, else `fallback`."""
    return next((build for build in builds if build.applies(world)), fallback)
