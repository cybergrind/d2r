"""Monsters that walk, strike and shoot by themselves: the least a fight needs to answer what the
character does.

The simulator's engine replays a take's monsters open loop (sim/engine.py): they are where they were,
whatever the character does. Here a monster moves as the client's code does and hurts as the takes
show. Three kinds of numbers are in it, and each is said where it is set:

- **read from the game** (data/tables.json): a blow's points, the bonuses of rank, enchantment and
  Herald tier, the walk's chances and speed, the missiles of the enchantments;
- **fitted to one take** (Tower Cellar 5, combat/plan.md 2026-10-11): how a monster walks (the
  constants below);
- **fitted to the train half of all takes** (data/monsters_fit.json, written by
  tests/inventory_tracking/scenarios/arena/evidence/fit.py from that directory's evidence.json,
  sparks.json and swings.json and never by hand; EVIDENCE.md, SPARKS.md and SWINGS.md there are the
  measurements): how long a swing is and how long the rest after it, where in it the blow lands, how
  often a swing that ran out takes life, what a struck monster does, whom a monster goes for, how its
  blows are spread in size, how far it reaches, how a shooter shoots, the nova of a death, the sparks
  of a Lightning Enchanted one. Every number there has its n; a type with too little of its own (the
  evidence's thresholds: 30 s in reach or 10 blows alone for a row; 30 swings run out for a chance of
  its own; 20 shots) uses the pooled row. 332 takes, 9,828 s, one character.

**Walking** (the think function read in the client, the classic scheme of the monstats row): free,
with its target out of reach, a roll of 0-99 under `aip1` walks to it, else it stands `aip2` frames;
a target further off than AWARE is none (Tower Cellar 5: beyond 20 units the Blood Clan and Devilkin
stood 88 to 100% of the frames). A walk goes straight at the target at the monstats `Velocity` times
PACE in world units a second, for WALK_FRAMES at most or until the target is in reach.

**Whom it goes for** (fitted, `targets`): the character or the nearest of its companions. The path
records name the character 0.92 of the time when it is the nearer of the two and 0.51 when a
companion is (the types fought hand to hand, 4,696 and 5,184 s; 16 types have their own pair). How
long a monster keeps to one target is not measured: here each monster has one roll for its life, and
goes for the character when that roll is under the share of the case it is in, so the shares come out
over a pack and no monster wavers. (Before: the nearest of all, the character first for a Goatman.)

**Swinging** (fitted, `melee`; SWINGS.md): with its target within the swing's reach a monster swings.
A swing lasts the usual length of the type's attack runs (10 to 24 frames by type; STRIKE_FRAMES
where not measured), its blow lands two thirds of the way through it (0.67: the median place of 22
drops put on one monster alone) and after it the monster rests before it thinks again: 15 frames at
the median of 50 rests, drawn through their deciles (8 to 36). So a monster nobody strikes swings
every 1.3 s or so. The row's `aip3` and `aip2` do not decide how often it swings in reach: their
classic meaning gives a Blood Hawk 0.03 swings a second where the takes show 1.5. `aidel` is read
and still not used.

**A struck monster staggers** (fitted, `melee.stagger`; `Pack.struck` is told what share of its most
life a hit took). The hits between two steps are one fall of its life, as a take's frames show them,
and the monster staggers with the chance of a fall of that size: 0.06 under a sixteenth of its life,
0.24 to two sixteenths, 0.69 and 0.72 to three and four, 0.93 above (4,066, 697, 635, 320 and 3,217
falls on the train half). It then stands for the frames the takes show (10 at the median of 1,573
spells, drawn through their deciles) and rests as after a swing before it thinks again (the gap
from a staggered swing to the same monster's next was 29 frames at the median of 16: the stagger
and that rest). **A swing whose blow has not landed when the monster staggers is lost.** A dead
monster is gone with its swing (`died`, `remove`). On the train half 0.23 of the swings at the
character ran out, 0.35 ended in a stagger and 0.24 in the monster's death (0.17 not seen to
their end): what the character does to the monsters decides most of what they do to it. Before
2026-10-13 a share of swings (0.29) was cut short by a roll, whatever the character did. A shooter
does not stagger here (not measured), and how long a monster of each type staggers is one curve.

**A swing is not a hit** (fitted, `takes_life`). A swing lands if the monster has not staggered and
the target is still within the swing's reach, and on the character it takes life only with a
chance: 0.30 pooled (0.15 to 0.44 of 98 swings that ran out at a character standing still; 0.37 of
the 23 with no other hostile beside it), a Devilkin's own 0.16 (38); no other type has the 30 such
swings for a chance of its own. That chance is **one number for several things a take cannot tell
apart**: the miss of the to-hit roll, a block, and a blow that whatever protects the character took
whole. It was measured on one character and is that character's; another build would need its own.
Neither the character's leaving nor its strikes are in it: here a blow already fails when the
target has left the reach or the monster has staggered, so a change of how the character moves or
strikes is answered by the model, not by this chance. (Before 2026-10-13 it was 0.16 of every
swing of half its length or more, with the strikes folded in: a character that did not strike for
two seconds was hurt as seldom as one that did, and a recorded fight showed four times the loss,
tests/.../arena/fixtures/incidents/INCIDENTS.md.) The bounds are wide: the low one counts the drops
put on that monster alone, the high one those it shares with other suspects, and the middle is
used; **in a pack hardly any drop is one monster's alone, so there the middle is too low** by an
amount the takes do not give (the Chaos Sanctuary's Doom Knights: 0.00 to 0.76 of 21 on the check
half, 11 of 14 by hand in the recorded fight, 1 such swing on the train half). A blow on a
companion always lands (nothing was measured there, and nothing here hurts a companion).

**Reach** (REACH for the body of the blows, fitted `reach.tail` beyond): the takes show swings begun
at the character from further off, ever fewer: 0.41 of the rate within 3.5 units at 3.5 to 4 units,
0.16 to 5, 0.05 to 6, 0.02 to 12 (18 to 68 swings a band). At each think a monster's reach is drawn
from that curve; the blow lands if the target is within it. One curve for all: the takes hold 1
blow of a unique alone on the train half, too few for a rank's own. Beyond 6 units the curve is in
part the casts of types that are not called ranged (a shaman's): an upper bound there.

**What a blow is worth**, from the tables (raw points, before the resistances of whoever takes it):
the monster level's `DM(H)` times a roll in the row's `A1MinD(H)..A1MaxD(H)` percent, raised by the
rank (difficultylevels `UniqueDamageBonus`, `ChampionDamageBonus`), by Extra Strong (monumod's
constants) and by a Herald's tier (the Terror Zone's config). The bonuses are multiplied here;
whether the game adds them is not known. An elemental enchantment (Lightning 17, Fire 9, Cold 18)
adds a roll of monumod's "Elemental Min..Max Damage % Bonus" of the blow's physical points, by rank.
**Its spread is fitted** (`melee.spread`, `shots.spread`): the table's roll is within a quarter of its
mean, the drops one monster dealt alone are not (49 of plain monsters: 56 at the median, 118 at the
90th percentile, 320 the largest, against a heaviest blow of 86 to 102 by the tables; 28 shots: 37,
254, 449). So the roll is multiplied by a factor drawn through those quantiles over their mean (0.08
to 5.0 for a strike, 0.06 to 5.1 for a shot): the mean blow stays the table's, one blow in ten is
over 1.8 times it. What makes the large ones (a curse, an aura, two blows between two frames) is
not known; the small ones may be blows partly absorbed.

**Shooting** (fitted, `shots`; the cycle was tests/.../arena/mobs.py's, one landed shot a second): a
monster given a shot (`Pack(shots=...)`) stands and shoots at what it has within SHOT_REACH in sight.
A shot every 1 / rate seconds (0.43 a second pooled over 2,282 shots; 22 types their own, 0.18 to
0.72), the gap drawn evenly from half to one and a half of that. Its mark is the character with the
measured share (0.62: the missiles that flew at where it stood), else the nearest companion. The
missile flies to where its mark stood at the monstats `MissA1` missile's `Vel` in units a second
(written into the fit from the game's tables; a type without one: 20.6, the mean by shots) and ends
on the character if it is within SHOT_CONTACT of that place then: **walking or teleporting out of a
shot is the flight time, not a factor**. A missile that arrives under the character takes life with
the measured chance, 0.023 pooled (three types with 390 to 600 shots have their own): the points the
takes put on a shooter alone and half of its share of the drops it shares, in hits of the mean size
(79 points, 28 hits), per shot that flew at the character (2,657 shots, 0.62 of them). It folds what
a swing's chance folds, and the bodies and walls a missile ends on. It is counted in points because
the counts of drops bound it only between 0.02 and 0.14. A shooter's path record does not say whom
it shoots at (0.17 of 4,514), so the missiles are what the mark is fitted on.

**A death's nova** (read and fitted, `nova`): a champion or unique carrying Cold Enchanted lets a ring
of `coldunique` (194) go when it dies (37 of 37 such deaths on the train half showed it, 0 of 373 of
plain monsters and minions carrying it). It spreads at the missile's `Vel` for its `Range` frames
(13.4 units; the furthest corpse of a nova drop was 11.7 off) and takes the missile's cold points at
the monster's level (729 at level 85: 182 through a cold resistance at the cap, the takes' median
174 of 15) when it passes the character, with the measured chance (0.70 of 37 deaths within 12
units), twice the points one time in five (5 of the train half's 26 nova drops are over 300 points,
which one ring does not reach at any level seen). A Fire Enchanted death's
explosion is in the takes at a median under 10 points and is not modelled; a Lightning Enchanted
death shows nothing.

**Sparks** (read and fitted, `sparks`; SPARKS.md beside the evidence is the measurement: 51 releases
and 408 sparks on the train half). A Lightning Enchanted unique or super unique lets sparks of
`lightunique` (195) go when it is struck (`Pack.struck`); its minions and a plain monster carrying
the enchantment let none go (0 releases of 296 minions seen struck, 51 of 31 of the 67 leaders).
A release comes with the time the monster is being struck, not with each hit: a hit stands for the
frames since the hit before, 10 at most, and a second of that time brings 0.95 releases (51 in
53.8 s; a chance per hit, 0.25 of 205, gives the monsters' counts worse, and hits a few frames apart
do not each bring one), never sooner than 5 frames after the one before (the least of 20 gaps). Why
a release comes the takes do not say, and a Herald's hits are mostly too small to be seen in them.
Eight sparks to a release (51 of 51), one to each 45 degrees and not at whoever struck; each flies
at the missile's `Vel` (12 units a second: 0.48 a frame, the takes' 0.483) along its own direction
or 45 degrees to either side of it, choosing again every 6 frames (the commonest run of 1,774),
which puts it 28 units out after 70 frames (27.2 at the median of 78), and is gone after 77 frames
(the most of 408) or on the first body it meets. The character is in its reach within 2.5 units
(what the evidence calls ended on it), and of the sparks that came that near 0.39 ended on it (11
of 28): the others fly on past it. **A spark that ends on the character takes life with the fitted
chance, and that chance is 0**: none of the 11 was followed by a drop, nor by a point less of life,
so the truth is under 0.24 at 95% (`upper95`) and the size of a spark's blow is not measured at all.
It stays the missile's by the tables (`EMin` and the per-level columns at the monster's level:
2 x level - 1), taken only if the chance is ever set above 0. Like a swing's, the chance is one
number for a miss, a block, a spark of next to no points (the level its missile is cast at may not
be the monster's) and this character's own protection. A spark on a companion always lands (as a
swing: not measured, and nothing here hurts a companion). Before the fit (one take, Tower Cellar 5)
any monster with the enchantment released, with a chance of a third at each frame it was struck in,
and every spark within 2 units of the character took its points.

Not modelled: damage that is no blow (poison, burning: a third of the life the takes lost has no
suspect at all), fleeing, bodies in each other's way, walls (a walk is a straight line and a shot
needs no line here: tests/.../arena/mobs.py adds both), a hurt companion, curses and auras.
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
# Units between the middles of a monster and what it strikes. Tower Cellar 5: Blood Clan minions
# struck from 3.2 units, Devilkin from 1.8 at the median and 2.8 at the most; over all takes the blows
# of one melee monster alone came from 3.1 at the median (50 on the train half). Further: the fit's tail.
REACH = 3.2
STOP = 0.85  # of the reach: where a walk to a target ends
# Frames a walk lasts before the monster thinks again (the take: a Blood Clan's walk 22 frames at the
# median, a Devilkin's 17).
WALK_FRAMES = 22
# A melee attack's animation where the fit has no length for the type, and the frame of it the blow
# landed at before the fit (now the fitted share of whatever length the swing has: frame 11 of 16).
STRIKE_FRAMES = 16
HIT_FRAME = 8
AWARE = 20.0  # units: a target further off is not gone for
# World units a second per point of monstats Velocity: a chasing Blood Clan (Velocity 7) made 7.5
# to 8.3 in the take; the threat scenarios had 1.1 from another take (speed 6 types at 6.0 to 7.25).
PACE = 1.1
# World units a second of a type whose walk the take shows far from its monstats row (Devilkin:
# 14.0 at the median against a Velocity of 6, toward its target and away from it alike).
SPEED: dict[int, float] = {21: 14.0}
# By AI (monstats `AI`), from the path records of Tower Cellar 5 (the stop distance the client writes
# into them, combat/plan.md): how near its first walk takes the type before it charges. A Blood
# Clan's record held a stop distance of 14 (7 units here) for 762 of 1184, 5 for the rest.
# Before the fit a type of these AIs went for the character whenever it was within AWARE, and every other for
# the nearest of all. The pack no longer plays by it (`_target`: the takes' shares); it stays as what
# the evidence's report lays the takes against.
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
# Units within which a shooter shoots: the reach the fit's shots a second were counted in (seconds in
# sight within 30 units). The shots at the character came from 15.0 units at the median, 23.2 at the
# 90th percentile and 33.0 at the 99th (1,659 on the train half), so few are lost beyond it.
SHOT_REACH = 30.0
# Units from where a missile was sent within which the character is still under it when it arrives:
# what the evidence calls a missile ended on the character (evidence/rates.py END_ON).
SHOT_CONTACT = 2.5
NOVA_MISSILE = 194  # missiles.txt `coldunique`


@cache
def fitted() -> dict[str, Any]:
    """data/monsters_fit.json: what the train half of the takes gives (the module text)."""
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
    """Whether the takes show the type shooting and not fighting hand to hand: it has a row of shots
    and none of swings (a Dark Stalker has both: the missiles are its enchantment's, it strikes)."""
    row = fitted()['shots']['types'].get(str(txt))
    return row is not None and not row['melee_too']


def idle(txt: int) -> bool:
    """A type the takes show standing in reach without ever striking."""
    return txt in fitted()['melee']['idle']


def favour(txt: int) -> tuple[float, float]:
    """The share of the time a type goes for the character and not for a companion: when the character
    is the nearer of the two, and when a companion is."""
    found = fitted()['targets']
    row = found['types'].get(str(txt), found['pooled'])
    return row['character_nearer']['value'], row['companion_nearer']['value']


def spread(kind: str, roll: float) -> float:
    """The factor on a blow of `kind` (MELEE or SHOT) at `roll` of 0 to 1: the fitted quantiles of the
    drops one monster dealt alone, over their mean; between two of them a straight line in the logarithm."""
    knots = fitted()['shots' if kind == SHOT else 'melee']['spread']['knots']
    for (low, least), (high, most) in itertools.pairwise(knots):
        if roll <= high:
            return least * (most / least) ** ((roll - low) / (high - low))
    return knots[-1][1]


def drawn(knots: Sequence[float], roll: float) -> float:
    """The value at `roll` of 0 to 1 of what was measured as `knots`, its quantiles at even steps (the
    least, the deciles, the most): a straight line between two of them."""
    place = roll * (len(knots) - 1)
    low = min(int(place), len(knots) - 2)
    return knots[low] + (knots[low + 1] - knots[low]) * (place - low)


def stagger_chance(share: float) -> float:
    """The chance that a monster staggers when a frame's hits took `share` of its most life."""
    found = fitted()['melee']['stagger']
    return found['bands'][min(int(share * found['parts']), len(found['bands']) - 1)]['chance']


def reach_of(roll: float) -> float:
    """The reach of a swing at `roll` of 0 to 1: the body's for most, further for the share of each
    band of the fit's tail."""
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
    """Monsters thinking, walking, striking and shooting frame by frame. `targets` at each step are the
    character first, then its companions, where they stand at that frame. `shots` (unit -> the parts of
    its shot in raw points by kind of damage) names the shooters: what a type shoots is whoever builds
    the pack's to say, how it shoots is the fit's."""

    def __init__(
        self, walkers: Sequence[Walker], seed: int = 1, shots: Mapping[int, Mapping[str, float]] | None = None
    ) -> None:
        self.walkers = {walker.unit: walker for walker in walkers}
        # One generator per monster, as the game rolls with the unit's own seed: a monster's rolls
        # do not depend on how many others are alive.
        self.rolls = {walker.unit: random.Random(seed * 1_000_003 + walker.unit) for walker in walkers}
        self.shots = {unit: dict(parts) for unit, parts in (shots or {}).items() if unit in self.walkers}
        self.sparks: list[Spark] = []
        self.arrived = 0  # the sparks that have ended on the character, whether or not they took life
        self.flying: list[Missile] = []
        self.novas: list[Nova] = []
        # The walkers of a read AI (`Walker.mind`), their missiles and curses. AWARE as it is when the pack is
        # made: beyond the code's radius it says every monster knows of the character (stage.py `awareness`).
        self.minds = casters.Minds(self, aware=AWARE)
        # The shooters that have had a target within their reach: these come after it. One that
        # never had stands, as a melee monster does beyond AWARE (an assumption, not a measurement).
        self.awake: set[int] = set()
        for walker in walkers:
            roll = self.rolls[walker.unit]
            walker.favour = roll.random()
            if walker.unit in self.shots:
                # Each starts its cycle at a frame of its own, or a pack of archers would shoot as one.
                walker.until = roll.randrange(max(round(self._gap(walker)), 1))

    def remove(self, unit: int) -> None:
        """Take a monster out with nothing left behind but what it already let go."""
        self.walkers.pop(unit, None)

    def died(self, unit: int, frame: int) -> bool:
        """The monster died at `frame`: it is gone (its sparks and missiles fly on), and one whose
        death lets a nova go lets it go. True: a nova spreads."""
        walker = self.walkers.pop(unit, None)
        if walker is None or not walker.traits.nova:
            return False
        found, roll = fitted()['nova'], self.rolls[unit]
        points = nova_points(walker.traits.level) * (2 if roll.random() < found['double']['value'] else 1)
        self.novas.append(Nova(unit, walker.at, frame, points, roll.random() < found['takes_life']['value']))
        return True

    def struck(self, unit: int, frame: int, share: float = 0.0) -> int:
        """The monster was struck at `frame` by a hit that took `share` of its most life: the sparks it
        let go (0 for one that lets none go, and most times for one that does). The share is kept
        for the next step, where the hits since the last one are one fall of life and the monster
        may stagger (`_reel`); a caller that gives none staggers nothing.

        For the sparks a hit stands for the time the monster was being struck since the hit before:
        the frames between them, the fit's window at most, and the window for a first hit. Each
        second of that time brings the fitted releases, so many hits in one frame or a few apart
        are no more than the time they span."""
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
        """The monster is stunned at `frame` for `frames` (sim/guard.py has when): what it was doing is over (a
        swing's blow not yet landed and a cast not yet let go are lost, as in a stagger), it does nothing until
        the stun is over and then thinks at once. A new stun sets the end anew, as the game's does."""
        walker = self.walkers.get(unit)
        if walker is None or frames <= 0:
            return
        walker.stunned = frame + frames
        walker.doing, walker.until, walker.lands = STAND, walker.stunned, -1
        if walker.mind is not None:
            self.minds.lost(walker)

    @staticmethod
    def _met(spark: Spark, targets: Sequence[Point], found: Mapping[str, Any]) -> int:
        """The index of the target the spark ends on now, -1 for none: the first it is in reach of. The
        character it ends on only with the fitted chance, rolled the first time it comes that near;
        else it flies on past it."""
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
        """A frame of the sparks: each a stride on, ending on the first target it meets. One that ends
        on the character takes life with the fitted chance; on a companion always (as a swing)."""
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
        """A frame of the shots in the air: one that arrives takes life if its target is still within
        SHOT_CONTACT of where it was sent (and its roll said so)."""
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
        """A blow's parts: `parts` and `physical` with what the enchantments add to it, all times the
        fitted spread of a blow's size."""
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
        """The hits on the walker since the last step, as one fall of its life: with the fitted chance
        of a fall of that size it staggers for the fitted frames, and a swing whose blow has not
        landed is lost. After the stagger it rests as after a swing (`step`). A shooter does not
        stagger (the takes' staggers are tallied of the melee types), nor one that staggers already."""
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
                # Over it: the rest of a swing before it thinks again (the module text has the measure).
                rest = round(drawn(fitted()['melee']['rest']['knots'], self.rolls[walker.unit].random()))
                walker.doing, walker.until = STAND, frame + max(rest, 1)
            elif frame >= walker.until:
                self._think(walker, frame, targets)
        return blows

    def _target(self, walker: Walker, targets: Sequence[Point]) -> int:
        """Whom the walker goes for: the character, or the nearest of its companions, by the fitted
        share of the case (which of the two is nearer) and the walker's own roll. One of them
        beyond AWARE gives way to the other within it."""
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
        """One stride of `stride` units toward `goal`, ending `stop` from it; False: there is no way (here
        there always is one)."""
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
        """A frame of a shooter: free, it lets a missile go at its mark if it has it in reach and in
        sight, and without them comes a stride nearer once it has had a target in reach."""
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
