"""Monsters that walk, strike and shoot by themselves: the least a fight needs to answer what the
character does (sim/engine.py replays a take's monsters open loop instead).

Three kinds of numbers: read from the game (data/tables.json: blow points, rank/enchantment/Herald
bonuses, walk chances and speed, enchantment missiles); fitted to one take (Tower Cellar 5, combat/plan.md
2026-10-11: the walk constants below); fitted to the train half of all takes (data/monsters_fit.json,
written by tests/inventory_tracking/scenarios/arena/evidence/fit.py, never by hand: swings, staggers,
targets, spread, reach, shots, novas, sparks). A swing's or shot's chance to take life is one number for a
miss, a block and this character's protection; it is this character's only.

Not modelled: damage that is no blow (poison, burning), fleeing, bodies in the way, walls, a hurt
companion, curses and auras. The model in full, with its measures: combat/history/sim-monsters.md.
"""

import itertools
import json
import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.sim import casters
from inventory_tracking.game.layout import CHAMPION_FLAG, MINION_FLAG, SUPER_FLAG, UNIQUE_FLAG
from inventory_tracking.levels.geometry import Point
from inventory_tracking.takes.timeline import GAME_RATE


FIT = Path(__file__).parent.parent / 'data' / 'monsters_fit.json'
STAND, WALK, STRIKE, STAGGER = 'stand', 'walk', 'strike', 'stagger'
# Units between the middles of a monster and what it strikes (3.1 at the median over all takes); beyond: the
# fit's tail.
REACH = 3.2
STOP = 0.85  # of the reach: where a walk to a target ends
# Frames a walk lasts before the monster thinks again (Tower Cellar 5's median).
WALK_FRAMES = 22
# Frames of a melee attack where the fit has no length for the type; HIT_FRAME: its blow's frame before the fit.
STRIKE_FRAMES = 16
HIT_FRAME = 8
AWARE = 20.0  # units: a target further off is not gone for
# World units a second per point of monstats Velocity (a chasing Blood Clan, Velocity 7, made 7.5 to 8.3).
PACE = 1.1
# World units a second of a type whose walk the takes show far from its monstats row (Devilkin: 14 against 6).
SPEED: dict[int, float] = {21: 14.0}
# By monstats `AI`, from Tower Cellar 5's path records (combat/plan.md): how near its first walk takes the type
# before it charges. CHARACTER_FIRST is the pre-fit targeting, kept only for the evidence report (`_target` decides).
CHARACTER_FIRST = frozenset(('Goatman',))
HOLD = {'Goatman': 7.0, 'Fallen': 6.5}  # units from the target where the approach ends (a Devilkin's stop 12 or 14)
CHARGE = 30  # the chance in 100, at a think held there, to go in (four charges seen: not a measurement)
DEFAULT = {'Velocity': '6', 'aip1(H)': '70', 'aip2(H)': '10', 'aip3(H)': '80', 'aidel(H)': '13'}
PLAIN, MINION, CHAMPION, UNIQUE = 'plain', 'minion', 'champion', 'unique'
STRONG, FIRE, LIGHTNING, COLD = 5, 9, 17, 18  # monumod ids
PHYSICAL = 'physical'
ELEMENTS = {LIGHTNING: 'lightning', FIRE: 'fire', COLD: 'cold'}  # the enchantments that add to a blow
MELEE, SPARK, SHOT, NOVA = 'melee', 'spark', 'shot', 'nova'  # the kinds of a blow
SPARK_MISSILE = 195  # missiles.txt `lightunique`
NEVER = -(10**9)  # the frame of what has not happened yet
# Units within which a shooter shoots: the reach the fit's rate was counted in (shots came from 15 at the median).
SHOT_REACH = 30.0
# Units from where a missile was sent within which it still ends on the character (evidence/rates.py END_ON).
SHOT_CONTACT = 2.5
NOVA_MISSILE = 194  # missiles.txt `coldunique`


@cache
def fitted() -> dict[str, Any]:
    """data/monsters_fit.json: the fit to the train half of the takes."""
    return json.loads(FIT.read_text(encoding='utf-8'))


def swing_of(txt: int) -> Mapping[str, Any]:
    """The fit of a type's swings: its own row, or the pooled one."""
    found = fitted()['melee']
    return found['types'].get(str(txt), found['pooled'])


def shooter_of(txt: int) -> Mapping[str, Any]:
    """The fit of a type's shots: its own row, or the pooled one."""
    found = fitted()['shots']
    return found['types'].get(str(txt), found['pooled'])


def shoots(txt: int) -> bool:
    """Whether the takes show the type shooting and not fighting hand to hand (a fit row of shots, none of swings)."""
    row = fitted()['shots']['types'].get(str(txt))
    return row is not None and not row['melee_too']


def idle(txt: int) -> bool:
    """A type the takes show standing in reach without ever striking."""
    return txt in fitted()['melee']['idle']


def favour(txt: int) -> tuple[float, float]:
    """The share of the time a type goes for the character over a companion: (character nearer, companion nearer)."""
    found = fitted()['targets']
    row = found['types'].get(str(txt), found['pooled'])
    return row['character_nearer']['value'], row['companion_nearer']['value']


def spread(kind: str, roll: float) -> float:
    """The size factor on a blow of `kind` (MELEE or SHOT) at `roll` in 0..1: the fitted quantiles over their mean,
    log-linear between knots."""
    knots = fitted()['shots' if kind == SHOT else 'melee']['spread']['knots']
    for (low, least), (high, most) in itertools.pairwise(knots):
        if roll <= high:
            return least * (most / least) ** ((roll - low) / (high - low))
    return knots[-1][1]


def drawn(knots: Sequence[float], roll: float) -> float:
    """The value at `roll` in 0..1 of a measure given as evenly spaced quantiles `knots`, linear between them."""
    place = roll * (len(knots) - 1)
    low = min(int(place), len(knots) - 2)
    return knots[low] + (knots[low + 1] - knots[low]) * (place - low)


def stagger_chance(share: float) -> float:
    """The chance that a monster staggers when a frame's hits took `share` of its most life."""
    found = fitted()['melee']['stagger']
    return found['bands'][min(int(share * found['parts']), len(found['bands']) - 1)]['chance']


def reach_of(roll: float) -> float:
    """The reach of a swing at `roll` in 0..1: REACH, or a band of the fit's tail."""
    reach = REACH
    for band in fitted()['reach']['tail']:
        if roll < band['share']:
            reach = band['to']
    return reach


def rank_of(flags: int) -> str:
    if flags & MINION_FLAG:
        return MINION
    if flags & CHAMPION_FLAG:
        return CHAMPION
    return UNIQUE if flags & (UNIQUE_FLAG | SUPER_FLAG) else PLAIN


def boost(rank: str, mods: Sequence[int], tier: int) -> float:
    """The factor on a blow's physical points of the monster's rank, Extra Strong and its Herald's tier."""
    unique = tables()['unique']
    factor = 1.0
    if rank == UNIQUE:
        factor *= 1 + unique['unique_damage'][0] / 100
    elif rank == CHAMPION:
        factor *= 1 + unique['champion_rank_damage'][0] / 100
    if STRONG in mods:
        factor *= 1 + unique['minion_strong_damage' if rank in (MINION, PLAIN) else 'strong_damage'][0] / 100
    herald = tables()['heralds'].get(str(tier))
    if herald is not None:
        factor *= 1 + herald['minion_damage' if rank in (MINION, PLAIN) else 'damage'] / 100
    return factor


def missile_points(missile: int, level: int, column: str = 'Min') -> float:
    """A missile's elemental points at missile `level`: `EMin` (or `EMax`) and the per-level columns
    of its band (levels 2-8, 9-16, 17-22, 23-28, 29 and up), as skills and missiles count them."""
    row = tables()['missiles'][str(missile)]
    points = float(row[f'E{column}'])
    for band, (first, last) in enumerate(((2, 8), (9, 16), (17, 22), (23, 28), (29, level)), 1):
        points += float(row.get(f'{column}ELev{band}', 0)) * max(min(level, last) - first + 1, 0)
    return points


def spark_points(level: int) -> float:
    """A spark's lightning points at missile `level`."""
    return missile_points(SPARK_MISSILE, level)


def nova_points(level: int) -> float:
    """The cold points of a death's nova at missile `level`: the middle of the missile's least and most."""
    return (missile_points(NOVA_MISSILE, level) + missile_points(NOVA_MISSILE, level, 'Max')) / 2


def nova_reach() -> float:
    """Units a death's nova spreads: the missile's `Range` frames at its `Vel`."""
    row = tables()['missiles'][str(NOVA_MISSILE)]
    return float(row['Range']) * float(row['Vel']) / GAME_RATE


@dataclass(frozen=True)
class Traits:
    """How a monster type moves and strikes."""

    speed: float  # world units a frame
    walks: int  # aip1: the chance in 100 to walk to a target out of reach
    idles: int  # aip2: frames it stands when the roll fails
    strikes: int  # aip3: read, and since the fit not what decides a swing in reach
    delay: int  # aidel: read, not used
    damage: tuple[float, float]  # a blow's least and most physical points
    melee: bool
    ai: str = ''
    level: int = 0
    rank: str = PLAIN
    # What its enchantments add to a blow: (element, least, most) as shares of the blow's physical points
    elements: tuple[tuple[str, float, float], ...] = ()
    sparks: bool = False  # Lightning Enchanted and of a rank that lets sparks go when struck
    nova: bool = False  # Cold Enchanted and of a rank whose death lets the nova go

    @classmethod
    def of(cls, txt: int, level: int | None = None, flags: int = 0, mods: Sequence[int] = (), tier: int = 0) -> Traits:
        """The traits of monster type `txt` at `level` (None: its row's), with type `flags`, enchantments `mods`
        and Herald `tier`."""
        row = {**DEFAULT, **tables()['monsters'].get(str(txt), {})}

        def number(name: str, default: float = 0.0) -> float:
            return float(row.get(name) or default)

        level = level or int(number('Level(H)', 1))
        rank = rank_of(flags)
        base = float(tables()['monlvl'].get(str(level), {}).get('DM(H)', 0)) / 100 * boost(rank, mods, tier)
        least, most = tables()['unique'][f'{UNIQUE if rank == UNIQUE else MINION}_element']
        return cls(
            level=level,
            rank=rank,
            elements=tuple((ELEMENTS[mod], least / 100, most / 100) for mod in mods if mod in ELEMENTS),
            sparks=LIGHTNING in mods and rank in fitted()['sparks']['ranks'],
            nova=COLD in mods and rank in fitted()['nova']['ranks'],
            speed=SPEED.get(txt, number('Velocity') * PACE) / GAME_RATE,
            walks=int(number('aip1(H)')),
            idles=int(number('aip2(H)')),
            strikes=int(number('aip3(H)')),
            delay=int(number('aidel(H)', 13)),
            damage=(base * number('A1MinD(H)'), base * number('A1MaxD(H)')),
            melee=row.get('isMelee') == '1',
            ai=str(row.get('AI') or ''),
        )


@dataclass
class Walker:
    unit: int
    txt: int
    x: float
    y: float
    doing: str = STAND
    until: int = 0  # the frame its present action (a swing with the rest after it, a shot's gap) is over
    goal: Point | None = None  # where a walk goes
    aim: int = -1  # the index of the target it strikes
    charging: bool = False  # past its hold: going in to strike
    level: int | None = None  # the monster's level; None: its row's
    flags: int = 0  # the type flags: unique, champion, minion
    mods: tuple[int, ...] = ()  # its enchantments (monumod ids)
    tier: int = 0  # the tier of the Herald it is or follows; 0: none
    sparked: int = NEVER  # the frame of its last release of sparks
    struck: int = NEVER  # the frame it was last struck at (`Pack.struck`)
    fell: float = 0.0  # the share of its most life the hits since the last step took (`Pack.struck`)
    reach: float = REACH  # of the swing it is in
    lands: int = -1  # the frame that swing's blow lands at; -1: none (no swing, or one lost to a stagger)
    favour: float = 0.0  # its one roll for whom it goes for (`Pack` draws it)
    mark: int = -1  # a shooter's: the index of the target of its next shot; -1: not chosen yet
    health: float = 1.0  # the share of its most life it has (`Pack.struck` takes the hits off)
    stunned: int = NEVER  # the frame a stun on it is over at (`Pack.stun`); it does nothing before
    traits: Traits = field(init=False)
    # A type of the four AIs read in the client thinks by them (sim/casters.py); None: by the fit, as below.
    mind: casters.Mind | None = field(init=False)

    def __post_init__(self) -> None:
        self.traits = Traits.of(self.txt, self.level, self.flags, self.mods, self.tier)
        self.mind = casters.mind_for(self.txt)

    @property
    def at(self) -> Point:
        return (self.x, self.y)


@dataclass
class Spark:
    """One spark of a Lightning Enchanted monster's release, weaving outward."""

    unit: int  # the monster that let it go
    x: float
    y: float
    course: float  # radians: its own direction; it flies along it or 45 degrees to either side
    born: int
    points: float
    heading: float
    turns: random.Random  # its own rolls: another spark ending early changes nothing for this one
    passed: bool = False  # it came within reach of the character and did not end on it: it flies on


@dataclass(frozen=True)
class Missile:
    """A shot in the air: it ends at `lands` where its target stood when it was let go."""

    unit: int  # the shooter
    target: int  # the index of the target it was sent at (0: the character)
    at: Point  # where that target stood
    lands: int  # the frame it arrives at
    takes: bool  # rolled when it was let go: arriving on its target, it takes life
    parts: Mapping[str, float]


@dataclass(frozen=True)
class Nova:
    """The ring a death let go, spreading from the corpse."""

    unit: int
    at: Point
    born: int
    points: float  # cold
    takes: bool  # rolled at the death: passing the character, it takes life


@dataclass(frozen=True)
class Blow:
    """What a strike, a shot, a spark or a nova takes, in raw points: `parts` by kind of damage
    ('physical', 'lightning', 'fire', 'cold'), `damage` their sum. Whoever takes it cuts each part by
    its own resistance."""

    frame: int
    unit: int  # who struck, or whose missile it was
    target: int  # the index of the target struck (0: the character)
    damage: float
    kind: str = MELEE  # or SPARK, SHOT, NOVA, and a caster's (sim/casters.py SPELL, POISON)
    parts: Mapping[str, float] = field(default_factory=dict)
    missile: int = 0  # missiles.txt id of a caster's missile that dealt it; 0: none

    def taken(self, resists: Mapping[str, float]) -> float:
        """The points left of the blow for one with `resists` (kind of damage -> the share stopped, 0 to 1)."""
        parts = self.parts or {PHYSICAL: self.damage}
        return sum(points * (1 - resists.get(kind, 0.0)) for kind, points in parts.items())


class Pack:
    """Monsters thinking, walking, striking and shooting frame by frame. `targets` at each step: the character,
    then its companions. `shots` (unit -> raw points by kind of damage) names the shooters; how they shoot is the
    fit's."""

    def __init__(
        self, walkers: Sequence[Walker], seed: int = 1, shots: Mapping[int, Mapping[str, float]] | None = None
    ) -> None:
        self.walkers = {walker.unit: walker for walker in walkers}
        # One generator per monster (the game rolls with the unit's own seed): rolls do not depend on the others.
        self.rolls = {walker.unit: random.Random(seed * 1_000_003 + walker.unit) for walker in walkers}
        self.shots = {unit: dict(parts) for unit, parts in (shots or {}).items() if unit in self.walkers}
        self.sparks: list[Spark] = []
        self.arrived = 0  # the sparks that have ended on the character, whether or not they took life
        self.flying: list[Missile] = []
        self.novas: list[Nova] = []
        # The walkers of a read AI (`Walker.mind`); AWARE as of now (stage.py `awareness` widens it).
        self.minds = casters.Minds(self, aware=AWARE)
        # Shooters that have had a target within reach come after it; the others stand (an assumption).
        self.awake: set[int] = set()
        for walker in walkers:
            roll = self.rolls[walker.unit]
            walker.favour = roll.random()
            if walker.unit in self.shots:
                # Each starts its cycle at its own frame, or a pack of archers would shoot as one.
                walker.until = roll.randrange(max(round(self._gap(walker)), 1))

    def remove(self, unit: int) -> None:
        """Take a monster out with nothing left behind but what it already let go."""
        self.walkers.pop(unit, None)

    def died(self, unit: int, frame: int) -> bool:
        """The monster died at `frame`: gone (its missiles fly on); True when its death lets a nova go."""
        walker = self.walkers.pop(unit, None)
        if walker is None or not walker.traits.nova:
            return False
        found, roll = fitted()['nova'], self.rolls[unit]
        points = nova_points(walker.traits.level) * (2 if roll.random() < found['double']['value'] else 1)
        self.novas.append(Nova(unit, walker.at, frame, points, roll.random() < found['takes_life']['value']))
        return True

    def struck(self, unit: int, frame: int, share: float = 0.0) -> int:
        """The monster was struck at `frame` by a hit that took `share` of its most life; returns the sparks let go.
        The share is summed until the next step, where it may stagger the monster (`_reel`). For sparks a hit
        stands for the frames since the hit before (the fit's window at most): releases come with time struck,
        not with the count of hits."""
        walker = self.walkers.get(unit)
        if walker is None:
            return 0
        walker.fell += share
        walker.health -= share
        if not walker.traits.sparks:
            return 0
        found = fitted()['sparks']
        release = found['release']
        # The gap after a release is no time a release can come in (the fit's `free` rate is over the rest).
        spent = min(frame - max(walker.struck, walker.sparked + release['gap']['value']), release['window'])
        walker.struck = frame
        if spent <= 0:
            return 0
        roll = self.rolls[unit]
        if roll.random() >= release['rate']['free'] * spent / GAME_RATE:
            return 0
        walker.sparked = frame
        points, count = spark_points(walker.traits.level), found['count']['value']
        for step in range(count):
            course = step * math.tau / count
            turns = random.Random(roll.getrandbits(32))
            self.sparks.append(Spark(unit, walker.x, walker.y, course, frame, points, course, turns))
        return count

    def stun(self, unit: int, frame: int, frames: int) -> None:
        """Stun the monster at `frame` for `frames` (sim/guard.py has when): a pending blow or cast is lost, it does
        nothing until the end and then thinks at once. A new stun resets the end, as the game's does."""
        walker = self.walkers.get(unit)
        if walker is None or frames <= 0:
            return
        walker.stunned = frame + frames
        walker.doing, walker.until, walker.lands = STAND, walker.stunned, -1
        if walker.mind is not None:
            self.minds.lost(walker)

    @staticmethod
    def _met(spark: Spark, targets: Sequence[Point], found: Mapping[str, Any]) -> int:
        """The index of the target the spark ends on now, -1 for none. On the character only with the fitted chance,
        rolled once when it first comes near; else it flies on past."""
        for index, body in enumerate(targets):
            if math.dist((spark.x, spark.y), body) > found['contact']:
                continue
            if index:
                return index
            if not spark.passed:
                if spark.turns.random() < found['meets']['value']:
                    return 0
                spark.passed = True
        return -1

    def _fly(self, frame: int, targets: Sequence[Point]) -> list[Blow]:
        """A frame of the sparks: each a stride on; one ending on the character takes life with the fitted chance,
        on a companion always."""
        found = fitted()['sparks']
        stride = float(tables()['missiles'][str(SPARK_MISSILE)]['Vel']) / GAME_RATE
        frames, turn = found['flight']['frames']['value'], found['flight']['turn']['value']
        blows, flying = [], []
        for spark in self.sparks:
            age = frame - spark.born
            if age >= frames:
                continue
            if age and age % turn == 0:
                spark.heading = spark.course + spark.turns.choice((-1, 0, 1)) * math.tau / found['count']['value']
            spark.x += math.cos(spark.heading) * stride
            spark.y += math.sin(spark.heading) * stride
            met = self._met(spark, targets, found)
            self.arrived += met == 0
            if met < 0:
                flying.append(spark)
            elif met or spark.turns.random() < found['takes_life']['value']:
                blows.append(Blow(frame, spark.unit, met, spark.points, SPARK, {ELEMENTS[LIGHTNING]: spark.points}))
        self.sparks = flying
        return blows

    def _land(self, frame: int, targets: Sequence[Point]) -> list[Blow]:
        """A frame of the shots in the air: one arriving takes life if its roll said so and its target is still
        within SHOT_CONTACT of where it was sent."""
        blows, flying = [], []
        for missile in self.flying:
            if frame < missile.lands:
                flying.append(missile)
            elif (
                missile.takes
                and missile.target < len(targets)
                and math.dist(targets[missile.target], missile.at) <= SHOT_CONTACT
            ):
                blows.append(
                    Blow(frame, missile.unit, missile.target, sum(missile.parts.values()), SHOT, missile.parts)
                )
        self.flying = flying
        return blows

    def _burst(self, frame: int, targets: Sequence[Point]) -> list[Blow]:
        """A frame of the novas: each ring a stride wider, taking its points when it passes the character."""
        stride = float(tables()['missiles'][str(NOVA_MISSILE)]['Vel']) / GAME_RATE
        blows, spreading = [], []
        for nova in self.novas:
            radius = stride * (frame - nova.born)
            if radius > nova_reach():
                continue
            if math.dist(nova.at, targets[0]) > radius:
                spreading.append(nova)
            elif nova.takes:
                blows.append(Blow(frame, nova.unit, 0, nova.points, NOVA, {ELEMENTS[COLD]: nova.points}))
        self.novas = spreading
        return blows

    def _sized(self, walker: Walker, physical: float, kind: str, parts: Mapping[str, float]) -> dict[str, float]:
        """A blow's parts: `parts`, `physical` and the enchantments' share, all times the fitted size spread."""
        roll = self.rolls[walker.unit]
        found = {**parts, PHYSICAL: physical} if physical or not parts else dict(parts)
        for element, least, most in walker.traits.elements:
            found[element] = found.get(element, 0.0) + physical * roll.uniform(least, most)
        factor = spread(kind, roll.random())
        return {name: points * factor for name, points in found.items()}

    def _blow(self, walker: Walker, frame: int) -> Blow:
        parts = self._sized(walker, self.rolls[walker.unit].uniform(*walker.traits.damage), MELEE, {})
        return Blow(frame, walker.unit, walker.aim, sum(parts.values()), MELEE, parts)

    def _reel(self, walker: Walker, frame: int) -> None:
        """The hits since the last step as one fall of life: with the fitted chance for its size the walker staggers
        for the fitted frames and loses an unlanded swing. Shooters do not stagger (only melee types were fitted)."""
        share, walker.fell = walker.fell, 0.0
        if frame < walker.stunned:
            return  # stunned: a hit's reaction does not end the stun (sim/guard.py)
        if walker.doing == STAGGER or (walker.mind is None and (walker.unit in self.shots or not walker.traits.melee)):
            return
        if walker.mind is not None and not walker.mind.staggers:
            return  # a mind that shows no hit mode in the takes (Diablo, sim/casters.py `Mind.staggers`)
        roll = self.rolls[walker.unit]
        if roll.random() < stagger_chance(share):
            frames = round(drawn(fitted()['melee']['stagger']['recovery']['knots'], roll.random()))
            walker.doing, walker.until, walker.lands = STAGGER, frame + max(frames, 1), -1
            if walker.mind is not None:
                self.minds.lost(walker)  # a cast not let go is lost as a swing is (the game's hit recovery)

    def step(self, frame: int, targets: Sequence[Point]) -> list[Blow]:
        for walker in self.walkers.values():
            if walker.fell > 0:
                self._reel(walker, frame)
        blows: list[Blow] = self._fly(frame, targets)
        if not targets:
            return blows
        blows += self._land(frame, targets)
        blows += self._burst(frame, targets)
        blows += self.minds.fly(frame, targets)
        for walker in self.walkers.values():
            if frame < walker.stunned:
                continue  # stunned: it does nothing (sim/guard.py)
            if walker.mind is not None:
                blows += self.minds.act(walker, frame, targets)
                continue
            if walker.unit in self.shots:
                self._shoot(walker, frame, targets)
                continue
            if not walker.traits.melee:
                continue  # neither given a shot nor a fighter by its row: it stands
            if walker.doing == WALK:
                self._walk(walker, targets)
            elif walker.doing == STRIKE and frame == walker.lands:
                target = targets[walker.aim] if 0 <= walker.aim < len(targets) else None
                # On the character a swing takes life with the fitted chance; on a companion always.
                if target is not None and math.dist(walker.at, target) <= walker.reach and (
                    walker.aim or self.rolls[walker.unit].random() < swing_of(walker.txt)['takes_life']['value']
                ):  # fmt: skip
                    blows.append(self._blow(walker, frame))
            if frame >= walker.until and walker.doing == STAGGER:
                # Over it: the rest of a swing before it thinks again.
                rest = round(drawn(fitted()['melee']['rest']['knots'], self.rolls[walker.unit].random()))
                walker.doing, walker.until = STAND, frame + max(rest, 1)
            elif frame >= walker.until:
                self._think(walker, frame, targets)
        return blows

    def _target(self, walker: Walker, targets: Sequence[Point]) -> int:
        """Whom the walker goes for (index into targets): the character or the nearest companion, by the fitted
        share and its own roll; one beyond AWARE yields to the other within it."""
        if len(targets) < 2:
            return 0
        mate = min(range(1, len(targets)), key=lambda index: math.dist(walker.at, targets[index]))
        to_hero, to_mate = math.dist(walker.at, targets[0]), math.dist(walker.at, targets[mate])
        near, far = favour(walker.txt)
        hero = walker.favour < (near if to_hero <= to_mate else far)
        if (to_hero if hero else to_mate) > AWARE >= (to_mate if hero else to_hero):
            hero = not hero
        return 0 if hero else mate

    def _stop(self, walker: Walker) -> float:
        """Units from its target at which the walker's walk ends: its hold, or striking distance."""
        hold = HOLD.get(walker.traits.ai, 0.0)
        return REACH * STOP if walker.charging or not hold else hold

    def _stand(self, walker: Walker, frame: int) -> None:
        walker.doing, walker.until, walker.lands = STAND, frame + max(walker.traits.idles, 1), -1

    def _think(self, walker: Walker, frame: int, targets: Sequence[Point]) -> None:
        traits, rolls = walker.traits, self.rolls[walker.unit]
        roll = rolls.randrange(100)
        aim = self._target(walker, targets)
        away = math.dist(walker.at, targets[aim])
        reach = reach_of(rolls.random())
        if idle(walker.txt):
            self._stand(walker, frame)
        elif away <= reach:
            found, frames = fitted()['melee'], swing_of(walker.txt)['frames']['value']
            walker.lands = frame + max(round(found['blow']['share'] * frames), 1)
            rest = round(drawn(found['rest']['knots'], rolls.random()))
            walker.doing, walker.until, walker.aim, walker.reach = STRIKE, frame + frames + rest, aim, reach
        elif away > AWARE:
            walker.charging = False
            self._stand(walker, frame)
        elif not walker.charging and away <= HOLD.get(traits.ai, 0.0) + 0.5 and roll >= CHARGE:
            self._stand(walker, frame)  # held off: not this time
        elif roll < traits.walks:
            walker.charging = walker.charging or away <= HOLD.get(traits.ai, 0.0) + 0.5
            walker.doing, walker.until, walker.aim, walker.lands = WALK, frame + WALK_FRAMES, aim, -1
        else:
            self._stand(walker, frame)

    def _walk(self, walker: Walker, targets: Sequence[Point]) -> None:
        target = targets[walker.aim] if 0 <= walker.aim < len(targets) else targets[self._target(walker, targets)]
        away = math.dist(walker.at, target)
        left = away - self._stop(walker)
        if left <= 0:
            walker.until = 0  # there: it thinks at once
            return
        stride = min(walker.traits.speed, left)
        walker.x += (target[0] - walker.x) / away * stride
        walker.y += (target[1] - walker.y) / away * stride

    # -- what sim/casters.py `Minds` asks of the pack ---------------------------------------------

    def _go(self, walker: Walker, goal: Point, stride: float, stop: float) -> bool:
        """One stride toward `goal`, ending `stop` from it; False: no way (never here)."""
        away = math.dist(walker.at, goal)
        step = min(stride, away - stop)
        if step > 0:
            walker.x += (goal[0] - walker.x) / away * step
            walker.y += (goal[1] - walker.y) / away * step
        return True

    def _sees(self, walker: Walker, target: Point) -> bool:
        """Whether the walker has a line of sight to `target`: here always (no walls here)."""
        return True

    def _footing(self, spot: Point) -> bool:
        """Whether one can stand at `spot`: here everywhere."""
        return True

    def _made(self, frame: int, unit: int, target: int, parts: Mapping[str, float], kind: str, missile: int) -> Blow:
        return Blow(frame, unit, target, sum(parts.values()), kind, dict(parts), missile)

    # -- shooters --------------------------------------------------------------------------------

    def _gap(self, walker: Walker) -> float:
        """Frames from one shot of the walker to its next, at the fitted rate."""
        return GAME_RATE / shooter_of(walker.txt)['rate']['value']

    def _sighted(self, walker: Walker, target: Point) -> bool:
        """Whether the walker can shoot at `target`: here, within SHOT_REACH (no walls here)."""
        return math.dist(walker.at, target) <= SHOT_REACH

    def _closer(self, walker: Walker, target: Point) -> bool:
        """One stride toward `target`; False: there is no way (here there always is one)."""
        away = math.dist(walker.at, target)
        stride = min(walker.traits.speed, away)
        if stride > 0:
            walker.x += (target[0] - walker.x) / away * stride
            walker.y += (target[1] - walker.y) / away * stride
        return True

    def _shoot(self, walker: Walker, frame: int, targets: Sequence[Point]) -> None:
        """A frame of a shooter: free, it shoots at its mark in reach and sight, else comes a stride nearer once
        awake."""
        if frame < walker.until:
            return
        found, roll = shooter_of(walker.txt), self.rolls[walker.unit]
        if not 0 <= walker.mark < len(targets):
            # The character with the fitted share, else the nearest companion; alone, the character.
            hero = len(targets) < 2 or roll.random() < found['aim']['value']
            walker.mark = (
                0 if hero else min(range(1, len(targets)), key=lambda index: math.dist(walker.at, targets[index]))
            )
        target = targets[walker.mark]
        away = math.dist(walker.at, target)
        if away <= SHOT_REACH:
            self.awake.add(walker.unit)
        if not self._sighted(walker, target):
            walker.doing = WALK if walker.unit in self.awake and self._closer(walker, target) else STAND
            return
        takes = walker.mark != 0 or roll.random() < found['takes_life']['value']
        parts = dict(self.shots[walker.unit])
        parts = self._sized(walker, parts.pop(PHYSICAL, 0.0), SHOT, parts)
        flight = max(math.ceil(away / (found['speed']['value'] / GAME_RATE)), 1)
        self.flying.append(Missile(walker.unit, walker.mark, target, frame + flight, takes, parts))
        walker.doing, walker.aim, walker.mark = STRIKE, walker.mark, -1
        walker.until = frame + max(round(roll.uniform(0.5, 1.5) * self._gap(walker)), 1)
