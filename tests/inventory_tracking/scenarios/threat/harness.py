"""A small battlefield with incoming damage, to score where the fight aims (the production simulator
has none: combat/sim replays recorded monsters and counts only what the blades take).

The decision under test is the game's own: `today` builds macros/world.py records, passes them through
combat/policy.py `observe` and asks combat/controller.py `aim_choice` with `LinePolicy`, as
macros/hunt.py `Hunter.choose` does. The fight never moves the character and never looks at its life
(hunt.py `fight`: it ends only when nothing is in reach, the player moves or the clock runs out), so
`today` only ever casts. When the fight learns to step or to yield, `today` is the one place to rewire.

The model, all of it:

- 25 ticks a second. A cast occupies the character CAST_FRAMES ticks (combat/sim/input.py); its blades'
  damage lands at once (really within 38 frames), per monster what `virtual_cast` gives for that monster
  alone: the emulated blades, the duplicate rule, capped by the life left. No Health Link, Hex Purge,
  Death Mark, mercenary or summons: nothing else kills and nothing else is hit.
- The blades take `damage_table()` points per contact, nothing from an `immune` monster.
- A monster's life is monlvl `HP(H)` at its level times the mean of its `MinHP(H)..MaxHP(H)`; a unique
  has twice that (monumod.txt 'Unique HP % Bonus (Hell)' 100) and hits 66% harder (difficultylevels.txt
  `UniqueDamageBonus`).
- A monster's damage is `table.multiple(txt)` times monlvl `DM(H)` at its level, each second, as a steady
  rate: one mean-strength hit a second that always lands (no defence, block, leech, potion or regeneration).
  A ranged one deals it from anywhere within RANGED_REACH and stands still; a melee one walks straight at
  the character at SPEED_UNITS a second per monstats speed point and deals it within MELEE_REACH. Monsters
  do not block each other, and every one of them goes for the character.
- A monster with `boost` raises the damage of the others within BOOST_RANGE while it lives (an aura, a curse).
- A monster with `blast` deals that many points once, when it dies within BLAST_RADIUS of the character.
  The table only says which corpses explode (monstats `deathDmg`); the points are this file's assumption.
- The character has LIFE points and runs RUN units a second; it cannot cast while it moves.

`Result.taken` is the damage dealt to the character until the field is clear or the horizon, counted on
past its death; `dead_at` is the tick its life ran out.

The reference controllers are the wanted decisions made concrete, not production code: `order` (a scripted
kill order), `step_then` (walk somewhere first), and two prototypes of what the policy lacks: `ThreatAim`
(the line sweep scored by the damage a second it removes, immunity known) and `Survivor` (leave when
standing and fighting on would kill).
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace

from inventory_tracking.combat.controller import aim_choice
from inventory_tracking.combat.mechanics.damage import damage_table
from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.policy import (
    AIM_BEYOND,
    MIN_FOCAL,
    OFFSETS,
    REACH,
    Foe,
    LinePolicy,
    observe,
    virtual_cast,
)
from inventory_tracking.combat.sim.input import CAST_FRAMES
from inventory_tracking.macros.world import LEADER_FLAGS, NO_OWNER, Monster, Player
from inventory_tracking.terror.danger import DANGER
from tests.inventory_tracking.scenarios.threat.table import TERROR_LEVEL, base_damage, multiple, row_of, table


Point = tuple[float, float]
TICKS = 25  # a second
LIFE = 1800.0  # the character's (the takes of 2026-10-10: 1778-1813)
RUN = 18.75  # units a second: the character's run in the take 20261010T162810Z-35
SPEED_UNITS = 1.1  # units a second per monstats speed point (the same take: speed 6 types walk 6.0-7.25)
MELEE_REACH = 3.0  # units within which a melee attacker hits
RANGED_REACH = 30.0  # units within which a ranged attacker hits: about the screen (macros/hunt.py SIGHT)
BOOST_RANGE = 16.0  # units: Might's range at level 1 (terror/data/threats.json auras)
BLAST_RADIUS = 4.0  # units: this file's assumption
BLAST = 450.0  # points of one exploding corpse: this file's assumption (a quarter of the character's life)
UNIQUE_LIFE = 2.0  # monumod.txt 'Unique HP % Bonus (Hell)': +100%
HORIZON = 20 * TICKS
ORIGIN = (5000.0, 5000.0)
UNIQUE_FLAG = 0x08
assert UNIQUE_FLAG & LEADER_FLAGS


@dataclass
class Hostile:
    unit: int
    txt: int
    at: Point
    life: float  # points left
    full: float  # points at full life
    dps: float  # points a second on the character while it reaches
    ranged: bool
    speed: float  # units a second
    elite: bool = False
    immune: bool = False  # the blades take nothing off it
    blast: float = 0.0  # points to the character when it dies within BLAST_RADIUS
    boost: float = 1.0  # factor on the other monsters' damage within BOOST_RANGE while it lives

    @property
    def name(self) -> str:
        return row_of(self.txt)['name']


def hostile(
    unit: int,
    txt: int,
    x: float,
    y: float,
    *,
    level: int = TERROR_LEVEL,
    share: float = 1.0,  # of its life left
    elite: bool = False,
    immune: bool | None = None,  # None: by the type's physical resistance
    life_factor: float | None = None,  # on the plain monster's life (a Herald's, its minions'); None: by `elite`
    damage_factor: float | None = None,
    boost: float = 1.0,
) -> Hostile:
    """A monster of the threat table at monster `level`, `x`, `y` units from the character's first place."""
    row, stats = row_of(txt), tables()['monsters'][str(txt)]
    points = float(tables()['monlvl'][str(level)]['HP(H)']) * (int(stats['MinHP(H)']) + int(stats['MaxHP(H)'])) / 200
    unique_damage = 1 + table()['rules']['hell']['unique_damage_bonus_percent'] / 100
    full = points * (life_factor if life_factor is not None else UNIQUE_LIFE if elite else 1.0)
    dps = (
        multiple(txt)
        * base_damage(level)
        * (damage_factor if damage_factor is not None else unique_damage if elite else 1.0)
    )
    at = (ORIGIN[0] + x, ORIGIN[1] + y)
    immune = row['resist_physical'] >= 100 if immune is None else immune
    blast = BLAST if row['death_damage'] else 0.0
    speed = row['speed'] * SPEED_UNITS
    return Hostile(unit, txt, at, full * share, full, dps, row['ranged'], speed, elite, immune, blast, boost)


@dataclass
class Scene:
    name: str
    area: int  # the level the character is in: what `observe` takes the monsters' points from
    hostiles: list[Hostile]
    life: float = LIFE
    origin: Point = ORIGIN

    def copy(self) -> Scene:
        return replace(self, hostiles=[replace(h) for h in self.hostiles])


@dataclass(frozen=True)
class Cast:
    focal: Point
    unit: int  # the monster the line was laid through


@dataclass(frozen=True)
class Move:
    to: Point


Action = Cast | Move | None


@dataclass
class View:
    """What a controller is shown each tick."""

    scene: Scene  # the live monsters where they stand, the character's place
    life: float  # the character's points left
    ready: bool  # a cast may start this tick
    tick: int

    @property
    def here(self) -> Point:
        return self.scene.origin

    @property
    def live(self) -> list[Hostile]:
        return self.scene.hostiles


Controller = Callable[[View], Action]


@dataclass
class Result:
    taken: float = 0.0  # points dealt to the character, counted on past its death
    dead_at: int | None = None  # the tick its life ran out
    cleared_at: int | None = None  # the tick the last monster died
    kills: list[int] = field(default_factory=list)  # unit ids in the order they died
    casts: list[int] = field(default_factory=list)  # the monster each cast's line went through
    blasts: float = 0.0  # points of `taken` that came from exploding corpses
    moved: float = 0.0  # units the character went
    curve: list[float] = field(default_factory=list)  # `taken` after each tick

    @property
    def alive(self) -> bool:
        return self.dead_at is None

    @property
    def first(self) -> int | None:
        return self.casts[0] if self.casts else None

    def taken_by(self, tick: int) -> float:
        return self.curve[min(tick, len(self.curve) - 1)] if self.curve else 0.0


def engaged(h: Hostile, here: Point) -> bool:
    """Whether the monster's damage lands on the character where both stand."""
    return math.dist(h.at, here) <= (RANGED_REACH if h.ranged else MELEE_REACH)


def rate(h: Hostile, live: Sequence[Hostile]) -> float:
    """The monster's points a second, raised by the live boosters near it."""
    factor = 1.0
    for other in live:
        if other.unit != h.unit and other.boost != 1.0 and math.dist(other.at, h.at) <= BOOST_RANGE:
            factor *= other.boost
    return h.dps * factor


def incoming(scene: Scene) -> float:
    """Points a second on the character where everything stands."""
    return sum(rate(h, scene.hostiles) for h in scene.hostiles if engaged(h, scene.origin))


def blades(origin: Point, focal: Point, h: Hostile, damage_of: Callable[[int], float]) -> float:
    """Points one cast at `focal` would take off this monster were it not immune (alone: no link here)."""
    return virtual_cast(origin, focal, {h.unit: Foe(h.txt, h.at, h.life)}, frozenset(), 0.0, damage_of)


def dealt(origin: Point, focal: Point, h: Hostile, damage_of: Callable[[int], float]) -> float:
    """Points one cast at `focal` takes off this monster."""
    return 0.0 if h.immune else blades(origin, focal, h, damage_of)


def run(scene: Scene, controller: Controller, horizon: int = HORIZON) -> Result:
    scene = scene.copy()
    result = Result()
    damage_of = damage_table()
    ready_at = 0
    for tick in range(horizon):
        if not scene.hostiles:
            result.cleared_at = tick
            break
        action = controller(View(scene, scene.life - result.taken, tick >= ready_at, tick))
        if isinstance(action, Move):
            gap = math.dist(scene.origin, action.to)
            step = min(RUN / TICKS, gap)
            if gap > 0:
                scene.origin = (
                    scene.origin[0] + (action.to[0] - scene.origin[0]) / gap * step,
                    scene.origin[1] + (action.to[1] - scene.origin[1]) / gap * step,
                )
                result.moved += step
            ready_at = max(ready_at, tick + 1)
        elif isinstance(action, Cast) and tick >= ready_at:
            ready_at = tick + CAST_FRAMES
            result.casts.append(action.unit)
            for h in scene.hostiles:
                h.life -= dealt(scene.origin, action.focal, h, damage_of)
            for h in [h for h in scene.hostiles if h.life <= 0]:
                result.kills.append(h.unit)
                if h.blast and math.dist(h.at, scene.origin) <= BLAST_RADIUS:
                    result.taken += h.blast
                    result.blasts += h.blast
            scene.hostiles = [h for h in scene.hostiles if h.life > 0]
        for h in scene.hostiles:
            gap = math.dist(h.at, scene.origin)
            if engaged(h, scene.origin):
                result.taken += rate(h, scene.hostiles) / TICKS
            elif not h.ranged and gap > 0:
                step = min(h.speed / TICKS, gap - MELEE_REACH * 0.8)
                h.at = (
                    h.at[0] + (scene.origin[0] - h.at[0]) / gap * step,
                    h.at[1] + (scene.origin[1] - h.at[1]) / gap * step,
                )
        if result.dead_at is None and result.taken >= scene.life:
            result.dead_at = tick
        result.curve.append(result.taken)
    return result


# --- the game's decision ---------------------------------------------------------------------------------


def records(scene: Scene) -> tuple[Player, list[Monster]]:
    """The scene as the memory read gives it (macros/world.py): the life as a share of 128."""
    player = Player(1, 'scenario', 1, scene.area, scene.origin[0], scene.origin[1], None)
    monsters = [
        Monster(
            h.unit, h.txt, 1, h.at[0], h.at[1], NO_OWNER, UNIQUE_FLAG if h.elite else 0, False,
            max(round(128 * h.life / h.full), 1), 128,
        )
        for h in scene.hostiles
    ]  # fmt: skip
    return player, monsters


def in_reach(scene: Scene) -> list[int]:
    return [h.unit for h in scene.hostiles if 0 < math.dist(h.at, scene.origin) <= REACH]


def today(view: View) -> Action:
    """Where the fight casts now: `Hunter.choose` without the window (any focal point can be aimed at)."""
    if not view.ready:
        return None
    reachable = in_reach(view.scene)
    if not reachable:
        return None  # attack mode waits: nothing is in reach
    player, monsters = records(view.scene)
    choice = aim_choice(LinePolicy(), observe(player, monsters, ()), reachable)
    return Cast(choice.focal, choice.unit) if choice is not None else None


# --- the wanted decisions --------------------------------------------------------------------------------


def straight_at(here: Point, h: Hostile) -> Cast:
    away = math.dist(here, h.at) or 1.0
    reach = max(MIN_FOCAL, min(away + AIM_BEYOND, REACH - 1))
    return Cast((here[0] + (h.at[0] - here[0]) / away * reach, here[1] + (h.at[1] - here[1]) / away * reach), h.unit)


def order(*units: int, then: Controller = today) -> Controller:
    """Cast straight at the first of `units` alive and in reach; with none left, `then` decides."""

    def controller(view: View) -> Action:
        if not view.ready:
            return None
        for unit in units:
            found = next((h for h in view.live if h.unit == unit), None)
            if found is not None and math.dist(found.at, view.here) <= REACH:
                return straight_at(view.here, found)
        return then(view)

    return controller


def step_then(to: Point, then: Controller = today) -> Controller:
    """Run to `to` (relative to ORIGIN) first, then `then` decides."""
    goal = (ORIGIN[0] + to[0], ORIGIN[1] + to[1])
    arrived = False

    def controller(view: View) -> Action:
        nonlocal arrived
        if not arrived and math.dist(view.here, goal) > 0.1:
            return Move(goal)
        arrived = True
        return then(view)

    return controller


def wait_until(ready: Callable[[View], bool], then: Controller = today) -> Controller:
    """Hold the cast until `ready` says so (once), then `then` decides."""
    go = False

    def controller(view: View) -> Action:
        nonlocal go
        go = go or ready(view)
        return then(view) if go else None

    return controller


@dataclass
class ThreatAim:
    """The line sweep with what it lacks today: every line `LinePolicy` would try, scored by the damage a
    second it takes off the character: each monster's rate times the share of its remaining life the cast
    takes (a kill removes it all), a melee attacker not yet in contact counting `DANGER.melee` of its
    rate, a corpse that would explode on the character counting against the line. With `weights` off the
    score is today's points (an elite's twice); with `immunity` off an immune monster is believed to bleed.
    Ties go to the line worth more points."""

    weights: bool = True
    immunity: bool = True
    blast: bool = True

    def __call__(self, view: View) -> Action:
        if not view.ready:
            return None
        here, live = view.here, view.live
        damage_of = damage_table()
        best: tuple[float, float, Cast] | None = None
        for target in live:
            away = math.dist(target.at, here)
            if not 0 < away <= REACH:
                continue
            for offset in OFFSETS:
                reach = max(MIN_FOCAL, min(away + offset, REACH - 1))
                focal = (
                    here[0] + (target.at[0] - here[0]) / away * reach,
                    here[1] + (target.at[1] - here[1]) / away * reach,
                )
                score = points = 0.0
                for h in live:
                    taken = 0.0 if h.immune and self.immunity else blades(here, focal, h, damage_of)
                    points += taken * (2.0 if h.elite else 1.0)
                    if not self.weights:
                        continue
                    weight = rate(h, live) * (1.0 if engaged(h, here) else DANGER.melee)
                    score += weight * min(taken / h.life, 1.0)
                    if self.blast and h.blast and taken >= h.life and math.dist(h.at, here) <= BLAST_RADIUS:
                        score -= h.blast
                found = (score if self.weights else points, points, Cast(focal, target.unit))
                if best is None or found[:2] > best[:2]:
                    best = found
        return best[2] if best is not None and best[1] > 0 else None


DIE_SECONDS = 2.0  # the fight is looked this far ahead
FLEE_TICKS = CAST_FRAMES  # between two looks while leaving


def leave(view: View) -> Action:
    """Run for the widest gap between the monsters and keep going: the fight is given up."""
    return Move(widest_gap(view.here, [h for h in view.live if math.dist(h.at, view.here) <= RANGED_REACH]))


def widest_gap(here: Point, hostiles: Sequence[Hostile]) -> Point:
    """A point a long run away in the middle of the widest gap between the monsters' bearings."""
    bearings = sorted(math.atan2(h.at[1] - here[1], h.at[0] - here[0]) for h in hostiles)
    if not bearings:
        return here
    gaps = [(b - a, a) for a, b in zip(bearings, [*bearings[1:], bearings[0] + 2 * math.pi], strict=True)]
    width, start = max(gaps)
    angle = start + width / 2
    return (here[0] + math.cos(angle) * 100.0, here[1] + math.sin(angle) * 100.0)


@dataclass
class Survivor:
    """Leave when standing and fighting on would kill: before each cast the fight is played ahead
    DIE_SECONDS with `inner` in this model (what the policy would need: the character's life, each
    monster's rate and reach, and the time its own kills take). If the character is dead by then, it runs
    for the widest gap between the monsters and looks again every FLEE_TICKS; else `inner` casts. Out of
    everything's reach it stands: alive, the field not cleared (the fight yielded)."""

    inner: Controller = today
    look_at: int = 0  # the tick of the next look while leaving
    goal: Point | None = None

    def __call__(self, view: View) -> Action:
        if self.goal is not None and view.tick < self.look_at:
            return Move(self.goal)
        if self.goal is None and not view.ready:
            return None
        near = [h for h in view.live if math.dist(h.at, view.here) <= RANGED_REACH]
        worst = sum(rate(h, view.live) for h in near)  # were every one of them in contact
        if worst and view.life / worst < 2 * DIE_SECONDS:
            ahead = run(replace(view.scene.copy(), life=view.life), self.inner, int(DIE_SECONDS * TICKS))
            if not ahead.alive:
                self.goal, self.look_at = widest_gap(view.here, near), view.tick + FLEE_TICKS
                return Move(self.goal)
        self.goal = None
        return self.inner(view)
