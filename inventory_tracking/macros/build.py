"""What a build is to the framework: the contracts it fills and the one object the framework asks.

The framework (macros/, combat/) knows no class, skill or item by name; a build imports it and fills
these contracts (architecture.md 4.0). This module imports nothing from a build: `Attack`,
`MovementSet` (made of `JumpSource`s, answering `Step` or `NoWay`), `Buff` (cast by macros/buffs.py
or a named caster), `Tactic`, `Shield`, `Draw`, and `Build`, which bundles them with `Loadout` and
`BuildSettings`; `choose` picks the first build that applies.

Every decision here is pure. Reading the game and acting stay in macros/ (travel.py, teleport.py,
routines.py). `Step` lives here so travel.py can import this module and not the reverse.
"""

import math
from collections.abc import Callable, Collection, Hashable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Literal, Protocol

from inventory_tracking.combat.harm import SafetySettings
from inventory_tracking.combat.policy import Choice, Foe, Observation, Point
from inventory_tracking.combat.sim.guard import GuardRule
from inventory_tracking.combat.stance import Camp, Jump
from inventory_tracking.combat.survival import DrinkSettings
from inventory_tracking.config import Config
from inventory_tracking.game.records import Monster, Teleport, World
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.model import Ground, Room
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import LoadTrace
from inventory_tracking.terror.danger import Pack


def nowhere(spot: Point) -> bool:
    """No place is shunned."""
    return False


PAD_SLACK = 2.0  # units a controller-mode landing may be off a jump's fixed reach (`JumpSource.pad_jump`)


@dataclass(frozen=True)
class MoveFacts:
    """What a move is chosen from, read once by the caller, so a set can be asked without the run or world."""

    here: Point  # world units
    now: float  # the run's clock
    slots: tuple[int | None, ...]  # skill id by slot (`World.slots`)
    # The worn staff with Teleport charges, in hand or not; None: no staff, or unreadable
    staff: Teleport | None
    ground: Ground | None  # walkable and flyable cells; None: not known
    doors: tuple[Door, ...]  # a closed door bars a walk and a thrown jump
    aspect: float  # window width / height: what is in view
    last_used: Mapping[int, float] = field(default_factory=dict)  # skill -> clock of its last jump
    failed: Mapping[int, float] = field(default_factory=dict)  # skill -> clock a jump by it last moved nothing
    # Level and rooms (tiles) a wall-crossing set routes over with `Intent.routed`; 0/(): ground only.
    area: int = 0
    rooms: tuple[Room, ...] = ()
    # Ways a set said lead nowhere (`NoWay.distrust`) -> clock; the caller's memory, so the set tries its next way.
    distrusted: Mapping[Hashable, float] = field(default_factory=dict)
    # Controller mode (macros/pad.py): jumps land at the source's fixed reach; `slots` are the pad's records.
    pad: bool = False

    def since_used(self, skill: int) -> float:
        """Seconds since the last jump by `skill`; inf when none."""
        return self.now - self.last_used.get(skill, -math.inf)

    def since_failed(self, skill: int) -> float:
        """Seconds since a jump by `skill` last moved nothing; inf when none."""
        return self.now - self.failed.get(skill, -math.inf)


@dataclass(frozen=True)
class Intent:
    """What a kind of caller allows a move to spend, wait for and trust; one named constant per caller."""

    name: str
    # Fewest staff charges a jump is still made with (0: spent to the last)
    reserve: int
    may_swap: bool  # the weapon set may be changed for the move
    may_wait: bool  # a casting delay about to end may be waited out (`MovementSet.wait`)
    distrust: float  # seconds a way that moved nothing is left alone
    # Under this many charges a free jump comes before a charged one (still made where nothing else leads);
    # inf: always, 0: never
    sparing: float = 0.0
    walks_under: float = 0.0  # under this many charges a walk too comes before a charged jump
    short: float = 0.0  # units short of the goal the move is to end (a stand-off)
    shot: bool = False  # a short walk has to end with a clear shot at the goal
    shuns: Callable[[Point], bool] = nowhere  # places not to end a move at
    # Walk the way round a wall, not the straight stride: asked after a blocked stride with no hop left
    detour: bool = False
    # Wait out a casting delay without asking whether the freed way leads toward the goal
    waits_blind: bool = False
    # The goal is a destination however far: the set answers with the next move of its own route. Off: the
    # goal is a spot within one move's reach.
    routed: bool = False
    # Units of straight line under which no Teleport hop is made: a free jump goes after its delay (0: off).
    # Charges were spent on the last 14-20 units to a chest during Blade Warp's delay (2026-10-17 12:45).
    hop_from: float = 0.0


@dataclass(frozen=True)
class Step:
    """One move: where to, and by what skill (None: one click's walk); `camp` is the place decision it came from."""

    spot: Point
    skill: int | None = None
    camp: Camp | None = None

    @property
    def needs(self) -> Literal['battle', 'travel'] | None:
        return None  # legacy legs have no priced weapon commitment

    @property
    def seconds(self) -> float:
        return 0.0

    @classmethod
    def to(cls, place: Camp) -> Step:
        """The move to a place, by the jump it was chosen for."""
        return cls(place.spot, place.skill, place)


@dataclass(frozen=True)
class PricedStep(Step):
    """A safety-authorized leg. Legacy Step serialization stays byte-identical."""

    needs: Literal['battle', 'travel'] | None = None
    seconds: float = 0.0


@dataclass(frozen=True)
class NoWay:
    """A movement set's answer when it has no move, with a non-empty reason. `arrived`: already there
    (a goal nearer than `Intent.short` too, never a step back); else blocked, and the caller may ask another set."""

    reason: str
    arrived: bool = False
    # A way that gave nothing while the set has another: the caller remembers it (`MoveFacts.distrusted`)
    # and asks again at once. None: final for these facts.
    distrust: Hashable | None = None

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError('a movement set that has no way says why')


Leg = Step | NoWay  # a movement set never answers with None


def anyhow(facts: MoveFacts, intent: Intent) -> bool:
    """Nothing of its own bars the jump."""
    return True


@dataclass(frozen=True)
class JumpSource:
    """One skill a character jumps by: the priced jump, its casting delay and its own usability test
    (charges and staff in hand, for a staff jump)."""

    jump: Jump
    delay: float = 0.0  # casting delay, seconds; 0: none
    # Seconds after key-down before a clear delay state means the delay is over (travel.py `Travel.left`)
    cleared: float = 0.0
    usable: Callable[[MoveFacts, Intent], bool] = anyhow
    # Controller-mode reach: the fixed `defaultTargetDistance` (macros/pad.py). None: not used in controller mode.
    pad_reach: float | None = None
    # The jump brings the companions along (Blade Warp, the player 2026-10-14), so it can pull one out of
    # danger (combat/escort.py).
    brings: bool = False

    def pad_jump(self) -> Jump | None:
        """The jump as controller mode makes it: one length, give or take PAD_SLACK; None without a fixed reach."""
        if self.pad_reach is None:
            return None
        return replace(self.jump, reach=self.pad_reach + PAD_SLACK, least=self.pad_reach - PAD_SLACK)

    def ready(self, facts: MoveFacts, intent: Intent) -> bool:
        """On a key, not distrusted, its delay over and its own test passed."""
        skill = self.jump.skill
        return (
            skill in facts.slots
            and facts.since_failed(skill) > intent.distrust
            and (not self.delay or facts.since_used(skill) >= self.delay)
            and self.usable(facts, intent)
        )

    def cooling(self, facts: MoveFacts) -> float:
        """Seconds of the casting delay still to run, in [0, delay]."""
        left = self.delay - facts.since_used(self.jump.skill)
        return left if 0 < left <= self.delay else 0.0


class MovementSet(Protocol):
    """A combination of ways to move (architecture.md 4.3). The navigator (travel.py `navigator`) asks the
    first set that `applies`, anew at each arbitration, and asks the other methods only for facts it applies
    to. Every method is pure."""

    @property
    def name(self) -> str:
        """Its name in the log."""
        ...

    @property
    def sources(self) -> tuple[JumpSource, ...]:
        """Its jumps, preferred first, ready or not (`jumps` gives the ready ones). Empty: walks only."""
        ...

    def applies(self, facts: MoveFacts) -> bool:
        """Whether this is the character's situation (staff, skills on keys)."""
        ...

    def leg(self, facts: MoveFacts, goal: Point, intent: Intent) -> Leg:
        """The next move toward `goal`: one jump or one click's walk, onto footing and in view; or `NoWay`.
        The caller makes it (`Travel.make`) and asks again."""
        ...

    def eta(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Seconds to reach `goal`; inf exactly where `leg` has no way. With `intent.routed` every move `leg`
        gives shortens it (0.0 on arrival)."""
        ...

    def jumps(self, facts: MoveFacts, intent: Intent) -> tuple[Jump, ...]:
        """The jumps usable now, preferred first: for pricing places (combat/stance.py `camp`) and for
        `Travel.make` when a step's jump is gone."""
        ...

    def wait(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Seconds to sleep before asking `leg` (a delay about to free a good way); 0.0 without `intent.may_wait`."""
        ...


class Attack(Protocol):
    """How a build deals damage, as far as the framework knows; its geometry, damage table and timing
    stay behind these members."""

    skill: int  # the strike whose input the fight holds
    reach: float  # units: farther, or without a clear line, is out of reach
    engage: float  # units from a monster a stand is best at (<= reach): macros/sight.py, combat/stance.py

    def lands(self, away: float) -> float:
        """Share of casts that hit a monster `away` units off, relative to close in (combat/stance.py `taken`)."""
        ...

    def sees(self, seen: Observation, companions: Sequence[Monster]) -> Observation:
        """A copy of `seen` with what the attack reads off the character's own units (links, marks), or
        `seen` itself. Asked once per observation built from the game, never by the simulator."""
        ...

    def aim(self, seen: Observation, through: Collection[int] = ()) -> Choice | None:
        """Where to cast now, or None. With `through`, only a cast through one of those units (the fight
        asks for priority kills first). On None the framework aims straight at what is in reach
        (combat/controller.py `aim_choice`). Asked every DECIDE_SECONDS; itself a `Policy`."""
        ...

    def dealt(
        self, origin: Point, focal: Point, foes: Mapping[int, Foe], blocked: Callable[[Point], bool] | None = None
    ) -> Mapping[int, float]:
        """Points one cast from `origin` at `focal` takes off each foe by unit id, uncapped and unweighted;
        omitted units take nothing. Called per place and hostile when pricing, so it must be cheap.
        `blocked`: cells the missiles stop at (None: none); every given foe has a clear line from `origin`."""
        ...


def in_front() -> bool:
    """The game's window is taken to be in front."""
    return True


@dataclass(frozen=True)
class BuffFacts:
    """What a buff's conditions are asked with. A cast on a unit is remembered under that unit and under
    None, so `since(skill)` is the last cast on anything."""

    world: World
    now: float
    foes: tuple[Monster, ...] = ()  # the hostiles the mode goes for
    reachable: tuple[Monster, ...] = ()  # those in the attack's reach with a clear shot
    prey: Monster | None = None  # the one the strike aims through; None outside a fight
    # (skill, unit cast on or under; None: no unit) -> clock of the last cast
    cast_at: Mapping[tuple[int, int | None], float] = field(default_factory=dict)
    focused: Callable[[], bool] = in_front  # the window is in front; a display query, asked lazily
    # Corpses as (unit id, x, y), world units (`Run.corpses`); None: unreadable
    corpses: Callable[[], tuple[tuple[int, float, float], ...]] | None = None
    cta: bool | None = None  # a Call to Arms is worn in either set (`Run.cta`); None: not known
    # The safety's price of the build's `Draw` per hostile at its last look (macros/safety.py `Safety.weigh`);
    # None: no fresh look, the row goes by its own rule
    draws: Mapping[int, DrawPrice] | None = None
    ahead: float = 0.0  # seconds of fight expected with no quiet (macros/hunt.py BOSS_AHEAD); 0: none known
    took: Mapping[int, float] = field(default_factory=dict)  # skill -> clock of its last cast that took
    # This row's buff (`Buff.lasts`) would end before the fight ahead does (macros/buffs.py `lapsing`)
    lapsing: bool = False
    # Life lost within HURT_SECONDS (macros/buffs.py `Buffs.hurt`), asked lazily; None: unknown, taken as hurt
    hurt: Callable[[], bool] | None = None
    # (skill, unit) -> the casts in a row on that unit that did not show on it (macros/buffs.py `Buffs.settle`): a
    # Herald pack's mark goes on another member after one (combat/pack.py MARK_ANY_MEMBER)
    missed: Mapping[tuple[int, int], int] = field(default_factory=dict)
    # Clock of the last move the safety chose to rebuff Battle Orders clear of the hostiles (macros/cta.py REBUFF,
    # macros/safety.py `Safety.rebuffed_at`): its landing casts it though the character was just hurt
    rebuffed: float = -math.inf
    # Clock that rebuff retreat landed (macros/safety.py `Safety.landed`): the Death Mark again after it
    # (builds/warlock/mark.py REMARK_AFTER_REBUFF)
    rebuff_landed: float = -math.inf
    # Why the safety's last look bars Battle Orders cast in place (macros/safety.py CAST_REACH); None: not barred
    cast_barred: str | None = None
    # A monster's state words read raw (`Run.reads.unit_states`), asked lazily; None: not read
    states: Callable[[Monster], bytes | None] | None = None

    def since(self, skill: int, unit: int | None = None) -> float:
        """Seconds since `skill` was last cast (on or under `unit`); inf when never."""
        return self.now - self.cast_at.get((skill, unit), -math.inf)

    def left(self, skill: int, lasts: float) -> float | None:
        """Seconds left of the last cast of `skill` that took; None when none is known."""
        took = self.took.get(skill)
        return None if took is None else lasts - (self.now - took)


def always(facts: BuffFacts, target: Monster | None) -> bool:
    """Every cast that is due pays."""
    return True


def whenever(facts: BuffFacts) -> bool:
    """Due at every look: the row's state, phase or caster says the rest."""
    return True


@dataclass(frozen=True)
class Buff:
    """One row of a build's buff plan (architecture.md 4.2): cast with one aim and one key by the shared
    executor when its phase has come, `due` holds and `worth` agrees, or by the named `caster`."""

    skill: int
    # prebuff: game start; upkeep: no hostile in reach; fight: under the held strike; opening: before the first
    phase: Literal['prebuff', 'upkeep', 'fight', 'opening']
    due: Callable[[BuffFacts], bool]
    on: Literal['self', 'monster', 'corpse', 'ground'] = 'self'  # what the pointer is put on
    target: Callable[[BuffFacts], Monster | None] | None = None  # None: nobody, or the caster finds its own
    # The buff as shown on the character: True on, False missing, None unreadable; cast only while missing
    state: Callable[[World], bool | None] | None = None
    needs: Literal['prebuff', 'battle'] | None = None  # weapon set to cast with; None: what is in hand
    worth: Callable[[BuffFacts, Monster | None], bool] = always
    # Log line when `worth` refuses a target, once per target (the player, 2026-10-14: "I'm not sure if
    # death mark is used")
    refused: Callable[[BuffFacts, Monster], str | None] | None = None
    # Monsters `target` passes over that the log should name, once each (rca/2026-10-14/run-0305-findings.md §2)
    passed: Callable[[BuffFacts], Sequence[tuple[Monster, str]]] | None = None
    # Log line at each cast on a target (the player, 2026-10-14: the log is how they see a cast and why)
    said: Callable[[BuffFacts, Monster], str | None] | None = None
    # Log line at a cast on a target, said once per target (the player, 2026-10-20: why Death Mark went on a magic
    # immune monster, a reason that holds at every mark again)
    told: Callable[[BuffFacts, Monster], str | None] | None = None
    caster: str | None = None  # a name in `Build.casters`; None: the shared executor
    # Other skills its caster presses first; they must be on keys too (macros/buffs.py `keys_of`)
    also: tuple[int, ...] = ()
    # Seconds a cast lasts for a buff that ends by itself (Consume: 300); drives `BuffFacts.lapsing`
    # (rca/2026-10-14/run-1214-findings.md §3.4)
    lasts: float | None = None
    # A shown buff cast again before it ends (Battle Orders: macros/cta.py `renew_orders`, 2026-10-22): asked with the
    # facts and the seconds left of its last cast that took (None: none known, as after a restart), it gives the
    # reason to cast again now, or None. With it, `lasts` drives `BuffFacts.lapsing` by this rule alone, and a lapsing
    # row is due though its `state` shows (macros/buffs.py `lapsing`, `Buffs.missing`).
    renew: Callable[[BuffFacts, float | None], str | None] | None = None
    # A cast on a monster checked on it (the player, 2026-10-20 ~18:45: "ok, recast"): whether a monster's state
    # words (game/layout.py STATE_RUN, raw: `Run.unit_states`) show this row's cast on it. A cast not shown
    # `shows_within` s after its key is cast again, `recasts` times at most a monster (macros/buffs.py `Buffs.settle`).
    # None: not checked.
    shows: Callable[[bytes], bool] | None = None
    shows_within: float = 0.0
    recasts: int = 0


@dataclass(frozen=True)
class Tried:
    """A caster's answer: what the executor remembers of the try and what the asking loop must restore.
    The executor keeps one clock per skill and unit, so a caster that made no cast schedules the next ask
    through `again`."""

    at: float | None = None  # clock the row counts as last cast at; None: nothing remembered, asked next look
    cast: bool = False  # a cast was made, which the row's `state` has to show
    # The pointer or a key was touched: under a held strike the loop restores aim and strike
    touched: bool = True

    @classmethod
    def again(cls, now: float, every: float, seconds: float, *, touched: bool = True) -> Tried:
        """No cast, and the row (due every `every` s) asked again in `seconds`."""
        return cls(now - every + seconds, touched=touched)


class Executor(Protocol):
    """What a caster may ask of the executor that called it (macros/buffs.py `Buffs`)."""

    def key(self, run: Run, skill: int) -> None:
        """Press the skill's key at once, letting go of a held strike."""
        ...

    def remember(self, row: Buff, at: float, unit: int | None = None) -> None:
        """Count the row as cast at `at` now, so an interrupted try still counts from its start."""
        ...

    def shared(self, cast: Casting) -> Tried:
        """The shared aim-and-key cast for the row's `on`, for a caster that only adds to it."""
        ...


@dataclass(frozen=True)
class Casting:
    """What a caster is called with: the due row, where it was found due, and the executor."""

    run: Run
    row: Buff
    buffs: Executor
    world: World | None = None  # None in the prebuff phase, which reads no world first
    target: Monster | None = None
    aspect: float | None = None  # window width / height, where the caller has it
    # Key per skill (skills.py `skill_keys`); None: already in `run.keys`
    key_names: Callable[..., dict[int, str]] | None = None
    # The load of a just-made game: the first cast may wait for input (routines.py LOAD_LIMIT) and ends the trace
    fresh: LoadTrace | None = None


Caster = Callable[[Casting], Tried]


class Tactic(Protocol):
    """What one kind of enemy adds to the price of a place (architecture.md 4.4). All applying tactics
    contribute: bars united, distances intersected, highest caution. A tactic owns no loop."""

    name: str

    def applies(self, pack: Pack) -> bool:
        """Whether this pack is of its kind."""
        ...

    def caution(self, base: float) -> float:
        """The caution to fight this pack with, from the base one."""
        ...

    def bars(self, spot: Point, pack: Pack) -> bool:
        """Whether `spot` is never stood at with this pack about."""
        ...

    def keep(self, pack: Pack) -> tuple[float, float]:
        """(least, most) units wanted between the character and the pack."""
        ...

    def opens(self) -> tuple[int, ...]:
        """Skills to cast before the first strike (`opening` buff rows)."""
        ...


@dataclass(frozen=True)
class Shield:
    """A guard the build keeps on the character (combat/sim/guard.py `GuardRule`) and `shown`: True up,
    False down, None unreadable. The safety price credits it only while shown up."""

    rule: GuardRule
    shown: Callable[[World], bool | None]


def no_gain(seen: Observation, unit: int, sent: Sequence[int]) -> float:
    """A draw adds nothing but where the companions stand."""
    return 0.0


def any_fits(seen: Observation, unit: int) -> bool:
    """Every hostile may be drawn onto."""
    return True


@dataclass(frozen=True)
class Draw:
    """A cast that sends the companions onto one hostile, which with its neighbours then goes for the
    nearest body (rca/2026-10-13/re-findings.md, "Target and awareness"). The player, 2026-10-14: "a very
    effective mechanism that allow to distract/re-aggro enemies". macros/safety.py `Safety.weigh` prices it
    each look against holding and the retreat; its buff row reads `BuffFacts.draws`."""

    skill: int
    sends: Callable[[World, Monster], bool]  # a companion it sends; with none it is not cast
    reach: float  # units: a companion farther from the hostile is not sent
    beside: float  # units from the hostile a sent companion lands, on its own side
    seconds: float  # the cast's time, the strike paused
    lasts: float  # seconds the companions hold the hostile at most
    # Fight seconds it saves besides the harm, from the observation, the hostile and the sent companions' classes
    gain: Callable[[Observation, int, Sequence[int]], float] = no_gain
    fits: Callable[[Observation, int], bool] = any_fits
    arrives: float = 0.0  # seconds from the key until the companions land
    # Measured: hostiles within `pack` units of the target turn to the companions, and share `turns` of their
    # blows leaves the character. 0: nothing known to turn (saved life not priced).
    pack: float = 0.0
    turns: float = 0.0


@dataclass(frozen=True)
class DrawPrice:
    """A `Draw` onto one hostile, priced at a look in the arbiter's seconds (T + kappa x H,
    rca/2026-10-13/architecture-goals-navigation.md §2.6)."""

    unit: int
    life: float  # life saved over `span`: mean harm holding without it less with it
    seconds: float  # that life at the look's price of life
    gain: float  # fight seconds saved besides (`Draw.gain`)
    cost: float  # the cast's seconds
    span: float  # seconds priced: the companions' hold, or the fight's clear time if less
    pressed: bool = False  # holding without it was over the look's life budget

    @property
    def worth(self) -> float:
        """Net seconds saved; positive pays."""
        return self.seconds + self.gain - self.cost

    def line(self) -> str:
        """The price in words, for the log."""
        return (
            f'saves {self.life:.0f} life over {self.span:.1f}s ({self.seconds:.2f}s at the price of life) and '
            f"{self.gain:.2f}s of the fight, against the cast's {self.cost:.2f}s: {self.worth:+.2f}s"
        )


@dataclass(frozen=True)
class Loadout:
    """A character's weapon sets by purpose, as base codes of what is held."""

    prebuff: frozenset[str]  # the set buffs are cast with
    battle: frozenset[str]  # the set to fight with and to leave a game with


class BuildSettings(Config):
    """A build's numbers: frozen, changed only by `with_overrides`."""

    drink: DrinkSettings = DrinkSettings()  # combat/survival.py
    safety: SafetySettings = SafetySettings()
    # The pursuit loop (macros/pursuit.py, rca/2026-10-13/pursuit-v1.md): in attack mode a teleport press
    # names a goal the mode goes to itself. Off: every key is its own routine. On by default, as `make serve` plays
    # (config.py `macro_pursuit`; the player, 2026-10-19, batch E: the arena plays as the live loop does).
    pursuit: bool = True
    # A level run's fight offers a better place to the safety every FOLLOW_CHECK (macros/hunt.py `fight`,
    # run-1932-findings.md "Fixes: positioning"). Off: it holds unless the safety prices a move itself.
    fight_look: bool = True


@dataclass(frozen=True)
class Build:
    """The one object the framework asks. Layers (class, build, character) are the layer below with
    changes (`dataclasses.replace`)."""

    name: str
    applies: Callable[[World], bool]  # whose it is: the character, the skills on its keys
    attack: Attack | None  # None: the build does not fight on its own
    movement: tuple[MovementSet, ...]  # the first that applies is asked
    buffs: tuple[Buff, ...] = ()  # in cast order
    tactics: tuple[Tactic, ...] = ()
    # Weapon sets by purpose, a character's own. None: hands left as they are; the macro request needs them.
    weapons: Loadout | None = None
    casters: Mapping[str, Caster] = field(default_factory=dict)  # casts that are more than a key
    settings: BuildSettings = field(default_factory=BuildSettings)
    shield: Shield | None = None
    draw: Draw | None = None
    # skill -> its icon in the right-skill selection (macros/skillpanel.py `Place`), for putting the strike back
    # on the right button in keyboard mode; a skill without one is not selected by the macro.
    skill_icons: Mapping[int, tuple[float, float]] = field(default_factory=dict)


def choose(builds: Sequence[Build], world: World, fallback: Build) -> Build:
    """The first of `builds` that applies, else `fallback` (also with no character in the world)."""
    if world.player is None:
        return fallback
    return next((build for build in builds if build.applies(world)), fallback)
