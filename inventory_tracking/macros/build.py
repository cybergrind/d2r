"""What a build is to the framework: the contracts it fills, and the one object the framework asks.

The framework (macros/, combat/) owns the loop and knows no class, skill or item by name; a build
imports the framework and fills it, and is handed to it (architecture.md 4.0). This module is the
whole of what the framework may ask of a build, and it imports nothing from a build:

- `Attack`: where to cast, what a cast takes off whom, how far it hurts, the skill the fight holds.
- `MovementSet`: a combination of ways to move (a jump of one kind or another, a walk) with its own
  route logic, asked for the next move toward a goal from `MoveFacts` and within an `Intent`. It
  answers with a `Step` or with `NoWay` and the reason, never with silence. The jumps it is made of
  are `JumpSource`s: a skill, what a jump by it takes, and when it can be made.
- `Buff`: one row of the buff plan, cast by the shared executor (macros/buffs.py) or by a caster the
  build names, which is called with a `Casting` and answers with a `Tried`.
- `Tactic`: what a kind of pack adds to the one price of a place.
- `Build`: those, the weapon sets (`Loadout`) and the numbers (`BuildSettings`), with `applies` to say
  whose it is; `choose` takes the first build that applies.

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
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import LoadTrace
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
    # The fewest charges of the staff a jump by them is still made with: with `reserve` left it is, with
    # one fewer it is not (0: they are spent to the last)
    reserve: int
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
    # The move asked for is along the walked way round a wall, not the straight stride: asked by the
    # caller after a stride was blocked, and only by one that has no hop left to make instead
    detour: bool = False
    # A casting delay is waited out without asking whether the way it frees leads toward the goal: the
    # caller has looked at the line itself, or takes what comes after the wait
    waits_blind: bool = False


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


def anyhow(facts: MoveFacts, intent: Intent) -> bool:
    """Nothing of its own bars the jump."""
    return True


@dataclass(frozen=True)
class JumpSource:
    """One skill a character jumps by, as a movement set is made of it: the jump as a place is priced
    by it, the skill's casting delay, and its own test of whether it can be made (charges left and the
    staff in hand, for a jump from a staff)."""

    jump: Jump
    delay: float = 0.0  # seconds between two jumps by the skill (its casting delay); 0.0: none
    usable: Callable[[MoveFacts, Intent], bool] = anyhow  # what only this source asks of the facts

    def ready(self, facts: MoveFacts, intent: Intent) -> bool:
        """Whether a jump by it can be made now: the skill on a key, not one that moved nothing less
        than `intent.distrust` seconds ago, its casting delay over, and its own test passed."""
        skill = self.jump.skill
        return (
            skill in facts.slots
            and facts.since_failed(skill) > intent.distrust
            and (not self.delay or facts.since_used(skill) >= self.delay)
            and self.usable(facts, intent)
        )

    def cooling(self, facts: MoveFacts) -> float:
        """Seconds of its casting delay still to run: more than 0 only while one runs, and never
        more than the delay."""
        left = self.delay - facts.since_used(self.jump.skill)
        return left if 0 < left <= self.delay else 0.0


class MovementSet(Protocol):
    """A combination of ways to move and how it uses them (architecture.md 4.3: `Charged`, `Empty`,
    a walker). The navigator asks the first set that `applies`, anew at each arbitration and never in
    the middle of a step. Every method is pure and reads nothing but its arguments.

    `leg`, `eta`, `jumps` and `wait` are asked only of a set whose `applies` holds for the same facts:
    the navigator (travel.py `navigator`) is the one way to a set, and what a set answers for facts
    that are not its own is not defined."""

    @property
    def name(self) -> str:
        """What the set is called in the log."""
        ...

    @property
    def sources(self) -> tuple[JumpSource, ...]:
        """The jumps the set is made of, the preferred first, whether or not one can be made now:
        `jumps` answers with those of them that can. What the framework reads off them without the
        facts: the casts that end with the character somewhere else, the skills that have a casting
        delay, and the build's own jump that spares the staff. Empty: the set only walks."""
        ...

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
        link they hold between monsters, a mark): a copy, the one given is never changed; or `seen`
        itself when there is nothing to add. Asked once for each observation the fight builds from
        the game, before `aim` or a place is priced; never by the simulator, which builds its own."""
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


def in_front() -> bool:
    """The game's window is taken to be in front."""
    return True


@dataclass(frozen=True)
class BuffFacts:
    """What a buff's conditions are asked with: the world, the clock, the fight as the mode sees it
    and the executor's memory of what was cast when. The executor remembers a cast on or under a unit
    under that unit and under None, so `since(skill)` is the last cast of the skill on anything."""

    world: World
    now: float
    foes: tuple[Monster, ...] = ()  # the hostiles the mode goes for
    reachable: tuple[Monster, ...] = ()  # those of them in the attack's reach with a clear shot
    prey: Monster | None = None  # the one the strike is aimed through; None outside a fight
    # (skill, the unit it was cast on or under; None: on no unit) -> clock time of the last cast
    cast_at: Mapping[tuple[int, int | None], float] = field(default_factory=dict)
    # Whether the game's window is in front. A question to the display, so it is asked only by a row that
    # cares, and only when the row gets that far.
    focused: Callable[[], bool] = in_front
    # The monsters lying dead as (unit id, x, y), world units (`Run.corpses`); None: they cannot be read
    corpses: Callable[[], tuple[tuple[int, float, float], ...]] | None = None

    def since(self, skill: int, unit: int | None = None) -> float:
        """Seconds since `skill` was last cast (on or under `unit`); inf when it never was."""
        return self.now - self.cast_at.get((skill, unit), -math.inf)


def always(facts: BuffFacts, target: Monster | None) -> bool:
    """Every cast that is due pays."""
    return True


def whenever(facts: BuffFacts) -> bool:
    """Due at every look: the row's state, its phase or its caster says the rest."""
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
    # The other skills its caster presses, before its own: they too have to be on keys, and their keys are asked
    # for first (macros/buffs.py `keys_of`: the order a missing one is named in)
    also: tuple[int, ...] = ()


@dataclass(frozen=True)
class Tried:
    """A caster's answer: what the executor is to remember of the try, and what the loop that asked
    has to put right after it. The executor's memory is one clock time per skill and unit, and a row's
    `due` reads only that, so a caster that made no cast says when the row is asked again by the time
    it has the try counted as a cast at (`again`)."""

    # The clock time the row counts as last cast at: now, for a cast that was made. None: nothing is
    # remembered, and the row is asked again at the next look.
    at: float | None = None
    cast: bool = False  # a cast was made: one more that the row's `state` has to show (the executor's rule)
    # The pointer or a key was touched: under a held strike the loop puts its aim back and takes the strike
    # up again. False: nothing was done, and the loop goes on as if the row had not been due.
    touched: bool = True

    @classmethod
    def again(cls, now: float, every: float, seconds: float, *, touched: bool = True) -> Tried:
        """No cast, and the row asked again in `seconds`: for a row that is due once its last cast is
        `every` seconds old, the try counts as a cast made `every - seconds` ago."""
        return cls(now - every + seconds, touched=touched)


class Executor(Protocol):
    """What a caster may ask of the executor that called it (macros/buffs.py `Buffs`)."""

    def key(self, run: Run, skill: int) -> None:
        """The skill's key pressed at once, a held strike let go for it."""
        ...

    def remember(self, row: Buff, at: float, unit: int | None = None) -> None:
        """The row counted as cast at `at` from now on, before the caster has answered: for a try
        that is to count from its start even when it is stopped half way."""
        ...

    def shared(self, cast: Casting) -> Tried:
        """The cast as the executor makes it for the row's `on` (aim and key), for a caster that only
        adds to it."""
        ...


@dataclass(frozen=True)
class Casting:
    """What a caster is called with: the row that is due, where it was found due, and the executor."""

    run: Run
    row: Buff
    buffs: Executor
    # The world the row was found due in. None in the prebuff phase, which casts every row of its own
    # and looks at no world before the first of them.
    world: World | None = None
    target: Monster | None = None  # whom the row's `target` named
    aspect: float | None = None  # the window's width over its height, where the caller has it (a fight)
    # The key per skill for the character in the game (skills.py `skill_keys`), as the runner gives it.
    # None: the keys are in `run.keys` already (a routine looked them up before its first cast).
    key_names: Callable[..., dict[int, str]] | None = None
    # The load of a game just made, when the prebuff follows one: the first cast may have to wait for
    # the game to take input (routines.py LOAD_LIMIT), and its success ends the trace.
    fresh: LoadTrace | None = None


Caster = Callable[[Casting], Tried]


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


@dataclass(frozen=True)
class Loadout:
    """A character's weapon sets by what they are for, as base codes of what is held."""

    prebuff: frozenset[str]  # the set the buffs are cast with
    battle: frozenset[str]  # the main set: the one to fight with, and to leave a game with


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
    # Which weapon set is for what, a character's own (the layer of a character gives it). None: the hands
    # are left as they are in a fight, and the macro request, which needs them, is not for this character.
    weapons: Loadout | None = None
    casters: Mapping[str, Caster] = field(default_factory=dict)  # the casts that are more than a key
    settings: BuildSettings = field(default_factory=BuildSettings)


def choose(builds: Sequence[Build], world: World, fallback: Build) -> Build:
    """The first of `builds` that applies to the character in the game, else `fallback`: also with no
    character in the world (a loading screen, the lobby), where no build is asked whether it applies."""
    if world.player is None:
        return fallback
    return next((build for build in builds if build.applies(world)), fallback)
