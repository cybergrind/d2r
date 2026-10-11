"""Monsters that walk and strike by themselves: the least a fight needs to answer what the character does.

The simulator's engine replays a take's monsters open loop (sim/engine.py): they are where they were,
whatever the character does. Here a melee monster thinks as the client's code does (combat/plan.md,
"where a monster will be", 2026-10-11: the think function read in the client, the classic scheme of
its monstats row):

- when it is free it thinks: with a target within its reach, a roll of 0-99 under `aip3` strikes,
  else it stands `aip2` frames; with the target further off, a roll under `aip1` walks to it, else
  it stands `aip2` frames;
- a target further off than AWARE is none: the monster stands (Tower Cellar 5: beyond 20 units
  the Blood Clan and Devilkin stood 88 to 100% of the frames, within it they walked 60 to 85% of
  them, toward their target);
- a walk goes straight at the target at the monstats `Velocity` times PACE in world units a second,
  for WALK_FRAMES at most or until the target is in reach, then it thinks again;
- a strike takes STRIKE_FRAMES and lands at HIT_FRAME if the target is still in reach then, for a
  roll between the row's `A1MinD(H)` and `A1MaxD(H)`.

The target is the nearest of the character and its companions, as far as the take of Tower Cellar 5
shows (the Blood Clan and Devilkin there struck whatever was next to them).

Fitted to that take, not read from the game (each said where it is set): the reach, the frames of a
walk and of a strike, and the speed of the types whose walk is not their `Velocity` (SPEED). Not
modelled: a ranged monster (it stands), fleeing, hit recovery, bodies in each other's way, walls
(a walk is a straight line).

What a blow is worth, from the tables (data/tables.json; raw points, before the defence, block and
resistances of whoever takes it): the monster level's `DM(H)` times a roll in the row's
`A1MinD(H)..A1MaxD(H)` percent, raised by the rank (difficultylevels `UniqueDamageBonus`,
`ChampionDamageBonus`), by Extra Strong (monumod's constants) and by a Herald's tier (the Terror
Zone's config: the Herald's boost, or its minions'). The bonuses are multiplied here; whether the
game adds them is not known.

An elemental enchantment (Lightning 17, Fire 9, Cold 18; user, 2026-10-12: "do the lightning enchanted
damage") adds to every blow a roll of monumod's "Elemental Min..Max Damage % Bonus" of that blow's
physical points, by rank: 66 to 100 for a unique, 33 to 50 for a champion or a unique's minion (and,
assumed here, for a plain monster a Terror Zone gave the modifier). That the percent is of the
blow is the classic rule, not read from this client.

A Lightning Enchanted monster lets sparks go when it is struck (`Pack.struck`). Measured on the Herald
of Tower Cellar 5 (88 sparks of 11 releases; combat/plan.md, 2026-10-12): 8 to a release, one to each
45 degrees; 0.48 units a frame (missiles.txt `lightunique` Vel 12: 12 units a second); a turn of 45
degrees to either side of its own direction about every 6 frames, so 9.7 units a second outward; gone
after 77 frames, 26 to 31 units out, or on the first body in its way (three of every release ended
0.2 s out on the companions beside the Herald). A release came in a third of the frames the Herald
was seen to lose life in, never less than 0.4 s after the one before. A spark's points are the
missile's `EMin` and per-level columns at the monster's level (assumed to be the missile's level):
2 x level - 1 of lightning.
"""

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.macros.world import MINION_FLAG


Point = tuple[float, float]
STAND, WALK, STRIKE = 'stand', 'walk', 'strike'
# Units between the middles of a monster and what it strikes. Tower Cellar 5: Blood Clan minions
# struck from 3.2 units, Devilkin from 1.8 at the median and 2.8 at the most.
REACH = 3.2
STOP = 0.85  # of the reach: where a walk to a target ends
# Frames a walk lasts before the monster thinks again (the take: a Blood Clan's walk 22 frames at the
# median, a Devilkin's 17).
WALK_FRAMES = 22
STRIKE_FRAMES = 16  # a melee attack's animation; the blow lands at HIT_FRAME (classic: about the middle)
HIT_FRAME = 8
AWARE = 20.0  # units: a target further off is not gone for
# World units a second per point of monstats Velocity: a chasing Blood Clan (Velocity 7) made 7.5
# to 8.3 in the take; the threat scenarios had 1.1 from another take (speed 6 types at 6.0 to 7.25).
PACE = 1.1
# World units a second of a type whose walk the take shows far from its monstats row (Devilkin:
# 14.0 at the median against a Velocity of 6, toward its target and away from it alike).
SPEED: dict[int, float] = {21: 14.0}
# By AI (monstats `AI`), from the path records of that take (the target unit and the stop distance the
# client writes into them, combat/plan.md): whom the type goes for, and how near its first walk
# takes it before it charges. A Blood Clan's record named the character in 1061 of 1136 samples and
# held a stop distance of 14 (7 units here) for 762 of 1184, 5 for the rest; a Devilkin's named the
# demon in 342 and the character in 184.
CHARACTER_FIRST = frozenset(('Goatman',))
HOLD = {'Goatman': 7.0, 'Fallen': 6.5}  # units from the target where the approach ends (a Devilkin's stop 12 or 14)
CHARGE = 30  # the chance in 100, at a think held there, to go in (four charges seen: not a measurement)
DEFAULT = {'Velocity': '6', 'aip1(H)': '70', 'aip2(H)': '10', 'aip3(H)': '80', 'aidel(H)': '13'}
SUPER_FLAG, CHAMPION_FLAG, UNIQUE_FLAG = 0x02, 0x04, 0x08  # the type flags of a monster (macros/world.py TYPE_FLAGS)
PLAIN, MINION, CHAMPION, UNIQUE = 'plain', 'minion', 'champion', 'unique'
STRONG, FIRE, LIGHTNING, COLD = 5, 9, 17, 18  # monumod ids
PHYSICAL = 'physical'
ELEMENTS = {LIGHTNING: 'lightning', FIRE: 'fire', COLD: 'cold'}  # the enchantments that add to a blow
MELEE, SPARK = 'melee', 'spark'
SPARK_MISSILE = 195  # missiles.txt `lightunique`
SPARKS = 8  # to a release, one to each 45 degrees
SPARK_FRAMES = 77  # a spark's life (the take: 3.07 to 3.11 s; the missile's Range of 98 is not what was seen)
SPARK_TURN = 6  # frames between two turns
SPARK_CONTACT = 2.0  # units from a body's middle at which a spark ends on it (one ended 2.1 from the character)
SPARK_GAP = 10  # frames at least between two releases (the take: never under 0.41 s)
SPARK_CHANCE = 33  # in 100, at a frame the monster is struck in (7 of the Herald's 21 hit frames, 11 releases in all)


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


def spark_points(level: int) -> float:
    """A spark's lightning points at missile `level`: `EMin` and the per-level columns of its band
    (levels 2-8, 9-16, 17-22, 23-28, 29 and up), as skills and missiles count them."""
    row = tables()['missiles'][str(SPARK_MISSILE)]
    points = float(row['EMin'])
    for column, (first, last) in enumerate(((2, 8), (9, 16), (17, 22), (23, 28), (29, level)), 1):
        points += float(row.get(f'MinELev{column}', 0)) * max(min(level, last) - first + 1, 0)
    return points


@dataclass(frozen=True)
class Traits:
    """How a monster type moves and strikes."""

    speed: float  # world units a frame
    walks: int  # aip1: the chance in 100 to walk to a target out of reach
    idles: int  # aip2: frames it stands when the roll fails
    strikes: int  # aip3: the chance in 100 to strike a target in reach
    delay: int  # aidel: frames between two thinks
    damage: tuple[float, float]  # a blow's least and most physical points
    melee: bool
    ai: str = ''
    level: int = 0
    rank: str = PLAIN
    # What its enchantments add to a blow: (element, least, most) as shares of the blow's physical points
    elements: tuple[tuple[str, float, float], ...] = ()
    sparks: bool = False  # Lightning Enchanted: struck, it lets sparks go

    @classmethod
    def of(cls, txt: int, level: int | None = None, flags: int = 0, mods: Sequence[int] = (), tier: int = 0) -> Traits:
        """The traits of a monster of `txt` at monster `level` (None: its row's), with its type `flags`,
        its enchantments `mods` and, for a Herald or one of its minions, the `tier`."""
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
            sparks=LIGHTNING in mods,
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
    until: int = 0  # the frame its present action is over
    goal: Point | None = None  # where a walk goes
    aim: int = -1  # the index of the target it strikes
    charging: bool = False  # past its hold: going in to strike
    level: int | None = None  # the monster's level; None: its row's
    flags: int = 0  # the type flags: unique, champion, minion
    mods: tuple[int, ...] = ()  # its enchantments (monumod ids)
    tier: int = 0  # the tier of the Herald it is or follows; 0: none
    sparked: int = -SPARK_GAP  # the frame of its last release of sparks
    traits: Traits = field(init=False)

    def __post_init__(self) -> None:
        self.traits = Traits.of(self.txt, self.level, self.flags, self.mods, self.tier)

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


@dataclass(frozen=True)
class Blow:
    """What a strike or a spark takes, in raw points: `parts` by kind of damage ('physical', 'lightning',
    'fire', 'cold'), `damage` their sum. Whoever takes it cuts each part by its own resistance."""

    frame: int
    unit: int  # who struck, or whose spark it was
    target: int  # the index of the target struck (0: the character)
    damage: float
    kind: str = MELEE  # or SPARK
    parts: Mapping[str, float] = field(default_factory=dict)

    def taken(self, resists: Mapping[str, float]) -> float:
        """The points left of the blow for one with `resists` (kind of damage -> the share stopped, 0 to 1)."""
        parts = self.parts or {PHYSICAL: self.damage}
        return sum(points * (1 - resists.get(kind, 0.0)) for kind, points in parts.items())


class Pack:
    """Monsters thinking, walking and striking frame by frame. `targets` at each step are the
    character first, then its companions, where they stand at that frame."""

    def __init__(self, walkers: Sequence[Walker], seed: int = 1) -> None:
        self.walkers = {walker.unit: walker for walker in walkers}
        # One generator per monster, as the game rolls with the unit's own seed: a monster's rolls
        # do not depend on how many others are alive.
        self.rolls = {walker.unit: random.Random(seed * 1_000_003 + walker.unit) for walker in walkers}
        self.sparks: list[Spark] = []

    def remove(self, unit: int) -> None:
        self.walkers.pop(unit, None)  # its sparks fly on

    def struck(self, unit: int, frame: int) -> int:
        """The monster was struck at `frame`: the sparks it let go (0 for one not Lightning Enchanted, and
        most times for one that is)."""
        walker = self.walkers.get(unit)
        if walker is None or not walker.traits.sparks or frame - walker.sparked < SPARK_GAP:
            return 0
        roll = self.rolls[unit]
        if roll.randrange(100) >= SPARK_CHANCE:
            return 0
        walker.sparked = frame
        points = spark_points(walker.traits.level)
        for step in range(SPARKS):
            course = step * math.tau / SPARKS
            turns = random.Random(roll.getrandbits(32))
            self.sparks.append(Spark(unit, walker.x, walker.y, course, frame, points, course, turns))
        return SPARKS

    def _fly(self, frame: int, targets: Sequence[Point]) -> list[Blow]:
        """A frame of the sparks: each a stride on, ending on the first target it touches."""
        stride = float(tables()['missiles'][str(SPARK_MISSILE)]['Vel']) / GAME_RATE
        blows, flying = [], []
        for spark in self.sparks:
            age = frame - spark.born
            if age >= SPARK_FRAMES:
                continue
            if age and age % SPARK_TURN == 0:
                spark.heading = spark.course + spark.turns.choice((-1, 0, 1)) * math.tau / SPARKS
            spark.x += math.cos(spark.heading) * stride
            spark.y += math.sin(spark.heading) * stride
            at = (spark.x, spark.y)
            met = next((index for index, body in enumerate(targets) if math.dist(at, body) <= SPARK_CONTACT), -1)
            if met < 0:
                flying.append(spark)
            else:
                blows.append(Blow(frame, spark.unit, met, spark.points, SPARK, {ELEMENTS[LIGHTNING]: spark.points}))
        self.sparks = flying
        return blows

    def _blow(self, walker: Walker, frame: int) -> Blow:
        roll = self.rolls[walker.unit]
        parts = {PHYSICAL: roll.uniform(*walker.traits.damage)}
        for element, least, most in walker.traits.elements:
            parts[element] = parts.get(element, 0.0) + parts[PHYSICAL] * roll.uniform(least, most)
        return Blow(frame, walker.unit, walker.aim, sum(parts.values()), MELEE, parts)

    def step(self, frame: int, targets: Sequence[Point]) -> list[Blow]:
        blows: list[Blow] = self._fly(frame, targets)
        for walker in self.walkers.values():
            if not walker.traits.melee or not targets:
                continue  # a ranged monster stands (not modelled)
            if walker.doing == WALK:
                self._walk(walker, targets)
            elif walker.doing == STRIKE and frame == walker.until - (STRIKE_FRAMES - HIT_FRAME):
                target = targets[walker.aim] if 0 <= walker.aim < len(targets) else None
                if target is not None and math.dist(walker.at, target) <= REACH:
                    blows.append(self._blow(walker, frame))
            if frame >= walker.until:
                self._think(walker, frame, targets)
        return blows

    def _nearest(self, walker: Walker, targets: Sequence[Point]) -> int:
        if walker.traits.ai in CHARACTER_FIRST and math.dist(walker.at, targets[0]) <= AWARE:
            return 0
        return min(range(len(targets)), key=lambda index: math.dist(walker.at, targets[index]))

    def _stop(self, walker: Walker) -> float:
        """Units from its target at which the walker's walk ends: its hold, or striking distance."""
        hold = HOLD.get(walker.traits.ai, 0.0)
        return REACH * STOP if walker.charging or not hold else hold

    def _think(self, walker: Walker, frame: int, targets: Sequence[Point]) -> None:
        traits, roll = walker.traits, self.rolls[walker.unit].randrange(100)
        aim = self._nearest(walker, targets)
        away = math.dist(walker.at, targets[aim])
        if away <= REACH:
            if roll < traits.strikes:
                walker.doing, walker.until, walker.aim = STRIKE, frame + STRIKE_FRAMES, aim
            else:
                walker.doing, walker.until = STAND, frame + max(traits.idles, 1)
        elif away > AWARE:
            walker.charging = False
            walker.doing, walker.until = STAND, frame + max(traits.idles, 1)
        elif not walker.charging and away <= HOLD.get(traits.ai, 0.0) + 0.5 and roll >= CHARGE:
            walker.doing, walker.until = STAND, frame + max(traits.idles, 1)  # held off: not this time
        elif roll < traits.walks:
            walker.charging = walker.charging or away <= HOLD.get(traits.ai, 0.0) + 0.5
            walker.doing, walker.until, walker.aim = WALK, frame + WALK_FRAMES, aim
        else:
            walker.doing, walker.until = STAND, frame + max(traits.idles, 1)

    def _walk(self, walker: Walker, targets: Sequence[Point]) -> None:
        target = targets[walker.aim] if 0 <= walker.aim < len(targets) else targets[self._nearest(walker, targets)]
        away = math.dist(walker.at, target)
        left = away - self._stop(walker)
        if left <= 0:
            walker.until = 0  # there: it thinks at once
            return
        stride = min(walker.traits.speed, left)
        walker.x += (target[0] - walker.x) / away * stride
        walker.y += (target[1] - walker.y) / away * stride
