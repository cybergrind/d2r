"""The Chaos Sanctuary's monsters as the game's own code plays them: the four AI routines read in the client,
their skills and missiles from the game's tables, the curses as states on whom they land.

sim/monsters.py plays every type by what the takes show of it (a fitted swing, a fitted shot). Four types
had nothing of their own there, and three of them are casters it played as walkers or as pooled shooters:
the Storm Caster (306), the Doom Knight (310), the Oblivion Knight (312) and the Venom Lord (362), and every
row of monstats with the same AI (the seal bosses are such rows with a rank). Here a monster of those AIs
thinks as the client's code does and casts what its row says; `Pack` hands such a walker to `Minds`.

Sources, as each number below says where it is set:

- **[code]** the think routines read in Binary Ninja (rca/2026-10-13/re/notes-ai.md: the frame every routine
  runs in, AI 70 FingerMage, AI 72 DoomKnight; notes-ai-74.md: AI 74 OblivionKnight; notes-mobs.md: AI 89
  Megademon, the target search, the walk helpers), and the damage rules (notes-damage.md: skill and
  missile damage by level, resistances, to-hit);
- **[table]** casters.json, written by build_casters.py from the game's tables (monstats, skills, missiles,
  difficultylevels, states): the AI parameters, skills and their levels, the missiles' speed, range and
  damage, the curses' effects, lengths and radii;
- **[take]** measured on the train half of the Chaos Sanctuary takes (rca/2026-10-13/scripts/casters_measure.py,
  output casters-measure-train.txt): the length of a mode (a cast, a swing), the frame of it a missile is let
  go at, and how far a missile goes in a frame per point of its `Vel` (the code that turns `Vel` into a step
  is in the encrypted missiles parser page). The client's animation data would give the first two; it is
  not on disk;
- **[inferred]** what neither says and a choice had to be made: named where it is made.

**The frame (all four)** [code]. A monster with no target stands and looks again after 10 frames while the
character is within 25, `d - 10` frames to 35, 25 frames beyond. Its target is the nearest of the character
and its companions within the radius (`aidist`, empty for all of them: 35) by the AI's metric, max(|dx|,
|dy|) + min(|dx|, |dy|) / 2 in sub-tiles (the arena's units); none beyond 55 of the character. Sight is
needed only until the monster first had a target; after that it finds the nearest through walls. Chosen
again at every think: no threat, no memory. After an action the next think comes at the end of its mode
plus `aidel` (13 frames, 11 for a Venom Lord); after an idle of n frames, n frames on. A walk is no mode
that ends here: the monster walks on toward its goal and thinks again `aidel` frames after it set out
[inferred: the code schedules the think from the mode's base frame; for a walk that frame is taken as the
start]. Rolls are 0 to 99 from the monster's own generator (the pack's, one per unit, seeded by the
play's seed), "roll < aipN" as the code has it.

**What is not the game's**: a monster's body bars nothing; a missile flies through walls (as the pack's other
missiles) and ends on a body within SHOT_CONTACT of it; melee reach is the pack's REACH for every type;
a monster in its pack does not wake its pack-mates (the game shares the first-sight flag in a pack: the
scene has no packs); the companions take blows and do not die (their life in points is in no take) and
deal nothing; a curse changes the character's resistances only (Decrepify's slower run and attack, and
its halved damage, are not played).
"""

import math
import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any, Protocol

from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.game.layout import MINION_FLAG, SUPER_FLAG, UNIQUE_FLAG
from inventory_tracking.levels.geometry import Point


DATA = Path(__file__).parent / 'casters.json'
# False: every type plays by sim/monsters.py's fit as before 2026-10-13 (the before/after comparisons of
# rca/2026-10-13/sim-casters.md are made by setting it before a play's pack is made).
PLAYED: bool = True
FINGER_MAGE, DOOM_KNIGHT, OBLIVION_KNIGHT, MEGADEMON = 'FingerMage', 'DoomKnight', 'OblivionKnight', 'Megademon'
MINDS = (FINGER_MAGE, DOOM_KNIGHT, OBLIVION_KNIGHT, MEGADEMON)
# Diablo (AI 51) thinks here too, by his own rules and rows (sim/diablo.py, diablo.json). He is not one of MINDS:
# `mind_of` and `row_of` stay the four's (combat/harm.py prices by them and still takes him for an unread boss).
DIABLO = 'Diablo'
# Baal (AI BaalCrab, and his clone's BaalCrabClone) thinks here too, by sim/baal.py: his think as read in the client
# (2026-10-14, rca/2026-10-14/re/baal-ai.md).
BAAL = 'Baal'
BAAL_AWARE = 1020  # [code] ai_d2_ai_baal_target_in_act: every player of the act within 1020 sub-tiles
STAND, WALK, STRIKE, STAGGER, CAST = 'stand', 'walk', 'strike', 'stagger', 'cast'  # sim/monsters.py's, and a cast
SPELL, POISON = 'spell', 'poison'  # the kinds of a blow a caster adds to sim/monsters.py's
# [code] notes-ai.md, the frame: the radius when `aidist` is empty, the player beyond which nobody is a
# target, the idles of a monster with none.
RADIUS = 35
PLAYER_REACH = 55
NEAR_LOOK, FAR_LOOK, LOOK_EDGE = 10, 25, 25
# [take] casters-measure-train.txt: units a missile goes in a frame per point of its `Vel`. The straight
# missiles of the four types: undead bolts 323-326 0.956-0.986 a frame at Vel 20, the bone spirit 0.574 at
# 12, the Venom Lord's flames 0.58 at 12, the Storm Caster's lead 0.283 at 6 (0.047 to 0.049 a point).
STEP_PER_VEL = 0.048
# [take] the frames of a mode (the median run of it in the train half) and the frames into a cast at which
# its missile or its curse is let go (the median first birth after the mode's start).
MODE_FRAMES: dict[tuple[str, str], int] = {
    (FINGER_MAGE, 'A1'): 10, (FINGER_MAGE, 'S1'): 39,
    (DOOM_KNIGHT, 'A1'): 14,
    (OBLIVION_KNIGHT, 'S1'): 21, (OBLIVION_KNIGHT, 'S2'): 21,
    (MEGADEMON, 'A1'): 23, (MEGADEMON, 'S1'): 12,
}  # fmt: skip
RELEASE: dict[tuple[str, str], int] = {
    (FINGER_MAGE, 'S1'): 20,  # the first 177 of 393 casts: 20 at the median
    (OBLIVION_KNIGHT, 'S1'): 15,  # 323-326 and 329: 15 to 16
    (OBLIVION_KNIGHT, 'S2'): 16,  # the curse marks 142, 189, 191: 15 to 16
    (MEGADEMON, 'S1'): 1,  # the first flame: frame 1 to 2
}
# [inferred] A Venom Lord's Inferno lets a flame go every FLAME_GAP frames from its release to the cast's end:
# skills.txt MegademonInferno `calc3` is 2, read as that gap; it gives the 5.2 flames (144 and 145) a cast of
# 12 frames the takes count.
FLAME_GAP = 2
# [take, against a code guess] A flame (megademoninferno, 675: no CollideKill) goes through every body and takes its
# whole points from each once. Not `DamageRate` 82 / 1024 of them a frame of contact (notes-mobs.md's guess): the
# takes' drops put on one Venom Lord's flames alone are 8 to 88 points between two recorded frames (16, median 45,
# fire at 75 %), one to seven flames' whole points, where that rate gives 1 to 4 points a frame of contact (unless
# the client's life messages sum many frames, which the takes cannot rule out: `sf` of the recorder will). The
# rate's use is not read; nothing here uses it.
# [take] the Storm Caster's lead missile (177) drops a trail of 177s where it passed (7.8 a cast, each
# standing 19 frames: Param2 20 of its row); only the lead is played, the trail is taken to hurt nobody
# [inferred: it stands where the lead went, which the lead's own hit already covers].
# The character, as the hit roll needs it [take]: defence (stat 31) 771 and level (stat 12) 94 in the
# `character_stats` of 20261013T093331Z-108 (notes-mobs.md section 4: a Doom Knight hits it 82 %).
DEFENCE, CHARACTER_LEVEL = 771, 94
# [code] notes-damage.md B3: a hit chance is clamped to 5..95 %.
LEAST_HIT, MOST_HIT = 5, 95
# A body a missile ends on or burns: within this of the missile's middle (sim/monsters.py SHOT_CONTACT, what
# the evidence calls a missile ended on the character).
CONTACT = 2.5
# Kinds of damage by missiles.txt `EType` and by the curses' stats.
ELEMENTS = {'fire': 'fire', 'ltng': 'lightning', 'cold': 'cold', 'pois': 'poison', 'mag': 'magic'}
RESIST_STATS = {
    'damageresist': 'physical', 'fireresist': 'fire', 'lightresist': 'lightning', 'coldresist': 'cold',
    'poisonresist': 'poison',
}  # fmt: skip
# [inferred] a Doom Knight's `El1Type` 'rand': one of these, evenly (the code that picks it was not read).
RANDOM_ELEMENTS = ('fire', 'lightning', 'cold', 'poison')
# [inferred] DoomKnightMissile (server do-function 148, not read) sends one of these; the takes have 128, 121,
# 98 and 102 of them (notes-ai-74.md): taken as even.
BOLTS = (323, 324, 325, 326)
BONE_SPIRIT = 329
# [inferred] MonCurseCast (server do-function 112, not read) puts one of these on; the takes' readings of the
# character show 8 Amplify (physical -100), 6 Decrepify (-50) and 6 Lower Resist (-55) begin (evidence/CURSES.md):
# taken as even.
MON_CURSES = ('Amplify Damage', 'Decrepify', 'Lower Resist')
# [inferred] the walk around a target (path kind 5 or 6, order block +0x28 = 3): a leg of this many units
# across the line to the target, the side by the roll.
CIRCLE_STEP = 3.0
STOP = 2.7  # units from a target where a walk to it ends: sim/monsters.py REACH x STOP
REACH = 3.2  # units: within this a monster is "in melee" and its swing lands (sim/monsters.py REACH)
BLOW_SHARE = 0.67  # of a swing's frames: where its blow lands (sim/monsters.py, the fit's `blow.share`)


@cache
def data() -> dict[str, Any]:
    import json

    return json.loads(DATA.read_text(encoding='utf-8'))


def row_of(txt: int) -> dict[str, str] | None:
    return data()['monsters'].get(str(txt))


def mind_of(txt: int) -> str | None:
    """The AI routine a type of monstats thinks by, when it is one of the four read in the client."""
    row = row_of(txt)
    return row['AI'] if row is not None and row.get('AI') in MINDS else None


def number(row: Mapping[str, str], name: str, default: float = 0.0) -> float:
    found = row.get(name)
    return float(found) if found not in (None, '') else default


def ai_distance(a: Point, b: Point) -> float:
    """[code] notes-ai.md: the AI's distance, max + min / 2 of the two axes."""
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    return max(dx, dy) + min(dx, dy) / 2


def stepped(level: int, steps: Sequence[float]) -> float:
    """[code] notes-damage.md B1: what the per-level columns add at `level` (bands 2-8, 9-16, 17-22, 23-28, 29+)."""
    total = 0.0
    for (first, last), step in zip(((2, 8), (9, 16), (17, 22), (23, 28), (29, 10**6)), steps, strict=True):
        total += step * max(min(level, last) - first + 1, 0)
    return total


def skill_level(row: Mapping[str, str], slot: int) -> int:
    """[table + take] a monster's skill level in Hell: its row's `SkNlvl` and difficultylevels'
    MonsterSkillBonus (7), as the takes' skill records show (notes-mobs.md section 4)."""
    return int(number(row, f'Sk{slot}lvl')) + int(data()['hell']['MonsterSkillBonus'])


def missile_row(missile: int) -> dict[str, str]:
    return data()['missiles'][str(missile)]


def missile_damage(missile: int, level: int) -> dict[str, tuple[float, float]]:
    """[code + table] a missile's damage at `level`: kind -> (least, most) in points. Physical is
    (MinDamage + steps) << HitShift / 256, the element (EMin + steps) << HitShift / 256 (notes-damage.md
    B1); poison is points a frame (it lasts `ELen` frames). An empty HitShift is 0, as the file has it."""
    row = missile_row(missile)
    shift = 2 ** number(row, 'HitShift') / 256
    found: dict[str, tuple[float, float]] = {}
    least = number(row, 'MinDamage') + stepped(level, [number(row, f'MinLevDam{n}') for n in range(1, 6)])
    most = number(row, 'MaxDamage') + stepped(level, [number(row, f'MaxLevDam{n}') for n in range(1, 6)])
    if most > 0:
        found['physical'] = (least * shift, max(most, least) * shift)
    kind = ELEMENTS.get(row.get('EType', ''))
    if kind is not None:
        least = number(row, 'EMin') + stepped(level, [number(row, f'MinELev{n}') for n in range(1, 6)])
        most = number(row, 'EMax') + stepped(level, [number(row, f'MaxELev{n}') for n in range(1, 6)])
        found[kind] = (least * shift, max(most, least) * shift)
    return found


def missile_step(missile: int) -> float:
    """Units a missile goes in a frame: its `Vel` times STEP_PER_VEL [table + take]."""
    return number(missile_row(missile), 'Vel') * STEP_PER_VEL


def skill_calc(skill: Mapping[str, str], calc: str, level: int) -> float:
    """[table] the skills' `ln12`, `ln34`, `ln56` (Param1 + Param2 x (level - 1), and so on) and `dm56`
    (Param5 + (Param6 - Param5) x (110 x level / (level + 6)) / 100, in whole numbers), `par5`, `-par5`,
    `-dm56`."""
    sign = -1 if calc.startswith('-') else 1
    name = calc.lstrip('-')
    params = [number(skill, f'Param{n}') for n in range(1, 9)]
    if name.startswith('ln'):
        first, per = int(name[2]) - 1, int(name[3]) - 1
        return sign * (params[first] + params[per] * (level - 1))
    if name.startswith('dm'):
        low, high = params[int(name[2]) - 1], params[int(name[3]) - 1]
        return sign * (low + (high - low) * (110 * level // (level + 6)) // 100)
    if name.startswith('par'):
        return sign * params[int(name[3:]) - 1]
    raise ValueError(f'calc {calc!r} is not read here')


@dataclass(frozen=True)
class Curse:
    """A curse on a body: its skill, the state it is, the frame it is gone at, and what it does to the
    resistances (kind -> percent points, negative)."""

    skill: str
    state: int
    until: int
    resists: Mapping[str, float]


def curse(name: str, level: int, frame: int, length: float | None = None) -> Curse:
    """[table] the curse of skills.txt row `name` at `level`, cast at `frame`: its target state, its
    resistance stats (`aurastatN` by `aurastatcalcN`) and its length (`auralencalc`) unless `length` says."""
    skill = data()['skills'][name]
    resists: dict[str, float] = {}
    for n in range(1, 5):
        kind = RESIST_STATS.get(skill.get(f'aurastat{n}', ''))
        if kind is not None:
            resists[kind] = skill_calc(skill, skill[f'aurastatcalc{n}'], level)
    frames = skill_calc(skill, skill['auralencalc'], level) if length is None else length
    return Curse(name, int(data()['states'][skill['auratargetstate']]), frame + int(frames), resists)


def curse_radius(name: str, level: int) -> float:
    """[table] units around the cursed target within which every body takes the curse (`aurarangecalc`)."""
    skill = data()['skills'][name]
    return skill_calc(skill, skill['aurarangecalc'], level)


@dataclass
class Bolt:
    """A caster's missile in the air: it goes `step` a frame along (dx, dy) or, homing, toward its target,
    until `ends`. One that `kills` (missiles.txt `CollideKill`) ends on the first body within CONTACT and
    takes its points there; any other (the Venom Lord's flames) goes through every body and takes its
    points from each once."""

    unit: int
    txt: int  # the caster's type
    missile: int
    x: float
    y: float
    dx: float
    dy: float
    step: float
    born: int
    ends: int
    parts: dict[str, float]  # raw points by kind; poison: points a frame
    poison: int = 0  # frames a poison part lasts
    kills: bool = True
    homing: int = -1  # the index of the target it steers to; -1: straight
    struck: set[int] = field(default_factory=set)  # the bodies it has taken from
    aim: int = -1  # the index of whom it was let go at
    origin: Point = (0.0, 0.0)
    # A stream's missile (Diablo's lightning, his wall's flames): it takes `rate` of its points from every body
    # within CONTACT, each frame, and goes on; 0: as above.
    rate: float = 0.0
    every: int = 1  # such a missile takes from one body at most once in this many frames (missiles.txt NextDelay)
    hit_at: dict[int, int] = field(default_factory=dict)  # the body's index -> the frame it last took from it
    trail: int = 0  # a missile it leaves where it is each frame (his wall's maker: a flame); 0: none
    trail_life: int = 0  # the frames such a trail stands
    trail_parts: dict[str, float] = field(default_factory=dict)
    trail_rate: float = 1.0  # the trail's `rate`
    # A maker that sheds missiles across its line (Baal's cold maker, sim/baal.py): each frame it enters a new sub-tile,
    # two of class `sides`, one each way, `side_step` a frame for `side_life` frames, with its points and its `struck`
    # (a body the cast took from is not taken from again); 0: none.
    sides: int = 0
    side_step: float = 0.0
    side_life: int = 0

    @property
    def at(self) -> Point:
        return (self.x, self.y)


@dataclass(frozen=True)
class Summon:
    """A monster a cast raises (Baal's tentacles and clone, sim/baal.py), for whoever holds the pack to put into the
    play: its class, where, the frame it rose at, the frames it stands unless killed (None: until its summoner dies)
    and a seed for its own rolls (drawn from the summoner's)."""

    unit: int  # the summoner
    txt: int
    at: Point
    frame: int
    lasts: int | None
    seed: int
    share: float = 0.0  # of its summoner's most life the life it rises with (Baal's clone: his life / 3); 0: its own
    most: float = 0.0  # of its summoner's most life its own most life; 0: its own row's


@dataclass
class Mind:
    """What a monster of a read AI keeps between thinks (control +0x44 / +0x48 in the code), and the
    cast under way."""

    ai: str
    row: dict[str, str]
    woke: bool = False  # it has had a target: it finds the next through walls
    cool: int = 0  # a frame: an Oblivion Knight's curse, a Venom Lord's Inferno not before it
    fleeing: bool = False  # a Storm Caster running from low life
    counted: int = 0  # its thinks since it began to flee
    inferno: bool = False  # a Venom Lord's state 12 after a cast
    skill: str = ''  # the skill of the cast under way
    slot: int = 0  # its slot in the row (Skill1..)
    mode: str = ''  # its mode (A1, S1, S2)
    target: int = -1  # the index of whom the cast or swing is at
    releases: list[int] = field(default_factory=list)  # frames the cast lets go at
    goal: Point | None = None  # a walk's end
    follow: int = -1  # a walk toward a body: its index (the goal moves with it)
    pace: float = 1.0  # a walk's speed, times the type's
    held: float = STOP  # where a walk toward a body ends
    level: dict[int, int] = field(default_factory=dict)  # skill slot -> its level
    home: Point | None = None  # where it first thought (Diablo's home point stand-in, sim/diablo.py)
    threat: float = 0.0  # Baal: the points the character took off him while its threat state holds (sim/baal.py)
    seen_health: float = 1.0  # Baal: his life share at his last think
    clones: int = 0  # Baal: the clones he made (control +0x48)

    def aip(self, n: int) -> float:
        return number(self.row, f'aip{n}(H)')

    @property
    def delay(self) -> int:
        """[table + code] `aidel` of Hell, 15 when the column is empty."""
        return int(number(self.row, 'aidel(H)', 15))

    @property
    def radius(self) -> float:
        if self.ai == DIABLO:
            from inventory_tracking.combat.sim import diablo

            return float(diablo.AWARE)
        if self.ai == BAAL:
            return float(BAAL_AWARE)
        return number(self.row, 'aidist(H)') or RADIUS

    @property
    def staggers(self) -> bool:
        """[take] Diablo never shows the hit mode (mode 3) in 163 s of the takes: he does not stagger. [probe] Nor
        Baal in 214 looks of eight fights (sim/baal.py)."""
        return self.ai not in (DIABLO, BAAL)

    def skill_of(self, slot: int) -> str:
        return self.row.get(f'Skill{slot}', '')


def mind_for(txt: int) -> Mind | None:
    if PLAYED:
        from inventory_tracking.combat.sim import diablo

        if diablo.is_diablo(txt):
            found = diablo.row(txt)
            assert found is not None
            mind = Mind(DIABLO, found, woke=True)  # [code] no sight needed to find a target (sim/diablo.py)
            mind.level = {slot: diablo.skill_level(txt, slot) for slot in range(1, 9) if found.get(f'Skill{slot}')}
            return mind
        from inventory_tracking.combat.sim import baal

        if baal.is_baal(txt):
            found = baal.row(txt)
            assert found is not None
            mind = Mind(BAAL, found, woke=True)  # [inferred] he knows of whoever enters his chamber
            mind.level = {slot: baal.skill_level(txt, slot) for slot in range(1, 9) if found.get(f'Skill{slot}')}
            return mind
    row = row_of(txt) if PLAYED else None
    if row is None or row.get('AI') not in MINDS:
        return None
    mind = Mind(row['AI'], row)
    mind.level = {slot: skill_level(row, slot) for slot in range(1, 9) if row.get(f'Skill{slot}')}
    return mind


def speed_of(row: Mapping[str, str]) -> float:
    """[take + table] units a frame a monster walks: `Velocity` x 75 / 1600 (stat 67 is 75 for every hostile
    at first sight in the take: notes-mobs.md section 2, exact on five classes)."""
    return number(row, 'Velocity') * 75 / 1600


def hit_chance(row: Mapping[str, str], level: int, defence: float = DEFENCE, against: int = CHARACTER_LEVEL) -> float:
    """[code + table] a swing's chance to hit the character (notes-damage.md B3): AR = A1TH(H) x monlvl
    TH(H) / 100; AR / (AR + DEF) x 2 x level / (level + the character's), clamped to 5..95 %."""
    rating = number(row, 'A1TH(H)') * float(tables()['monlvl'].get(str(level), {}).get('TH(H)', 0)) / 100
    chance = 100.0 if rating + defence <= 0 else rating * 100 / (rating + defence)
    chance = chance * 2 * level / (level + against)
    return min(max(chance, LEAST_HIT), MOST_HIT) / 100


# -- the decisions of one think, as the code reads ------------------------------------------------------------

Act = tuple[Any, ...]  # ('attack', target) | ('cast', slot, target) | ('walk', ...) | ('idle', frames)


def finger_mage(
    mind: Mind, roll: Callable[[], int], d: float, melee: bool, life: float, led: bool, marked: bool
) -> Act:
    """AI 70 (notes-ai.md, `ai_d2_ai_70_think`): a Storm Caster. `life` its share of life, `led` its pack's
    leader alive, `marked` the target carries state 84 `fingermagecurse`. Returns the action; the flee's
    start and end are kept in `mind`."""
    if mind.fleeing:
        mind.counted += 1
        if life * 100 > mind.aip(3) or roll() < 25 or mind.counted > mind.aip(6):
            mind.fleeing = False
            return ('idle', 15)
        return ('idle', 15) if d >= 14 else ('flee', 14, 1 + clamp_bonus(mind.row) / 100)
    if not led and life * 100 < mind.aip(4):
        mind.fleeing, mind.counted = True, 0
        return ('flee', 9, 1 + clamp_bonus(mind.row) / 100)
    if melee:
        if roll() < mind.aip(1):
            return ('attack',)
        if roll() < mind.aip(2):
            return ('cast', 1)
        return ('circle',)
    if d < mind.aip(5):
        if roll() < mind.aip(2):
            return ('cast', 1)
        return ('approach',) if marked else ('idle', int(mind.aip(8)))
    if d >= mind.aip(7):
        return ('idle', 15)
    return ('approach',)


def clamp_bonus(row: Mapping[str, str]) -> float:
    """[code] the flee's speed bonus: clamp(Run x 100 / Velocity - 100, 0, 120) percent."""
    velocity = number(row, 'Velocity')
    return min(max(number(row, 'Run') * 100 / velocity - 100, 0.0), 120.0) if velocity else 0.0


def doom_knight(mind: Mind, roll: Callable[[], int], melee: bool) -> Act:
    """AI 72 (notes-ai.md): in melee roll < aip1 attack, else idle aip2; else roll < aip3 walk, else idle aip4."""
    if melee:
        return ('attack',) if roll() < mind.aip(1) else ('idle', int(mind.aip(2)))
    return ('approach',) if roll() < mind.aip(3) else ('idle', int(mind.aip(4)))


def megademon(mind: Mind, roll: Callable[[], int], d: float, melee: bool, frame: int) -> Act:
    """AI 89 (notes-mobs.md section 1): a Venom Lord. The cast range is its Skill1's level."""
    if not melee and d < mind.level.get(1, 0):
        if mind.inferno:
            mind.inferno = False
        elif frame > mind.cool and roll() < mind.aip(1):
            return ('cast', 1)
    elif melee:
        if frame > mind.cool and roll() < mind.aip(2):
            return ('cast', 1)
        if roll() < mind.aip(3):
            return ('attack',)
        return ('circle',) if roll() < mind.aip(5) else ('idle', 5)
    return ('approach',) if roll() < mind.aip(4) else ('idle', 10)


def oblivion_knight(
    mind: Mind,
    roll: Callable[[], int],
    d: float,
    cursed: bool,
    knight: bool,
    seen: bool,
    e: float,
    frame: int,
) -> Act:
    """AI 74 (notes-ai-74.md, the decision table). `cursed`: the target carries Decrepify's state; `knight`:
    a Doom Knight stands farther from the target than this one (A2); `seen`, `e`: a visible enemy and its
    distance. A retreat that finds no way is told back by the caller as ('cornered',)."""
    if d < mind.aip(1):
        if mind.skill_of(4) and not cursed:
            mind.cool = frame + int(mind.aip(3))
            return ('cast', 4)
        if knight:
            return ('hide',)
        return ('retreat', 10, 1.5)  # order block +0x24 = 50: the speed bonus
    if seen and e < mind.aip(2):
        if mind.skill_of(6) and frame > mind.cool and roll() < mind.aip(4):
            mind.cool = frame + int(mind.aip(3))
            return ('cast', 6)
        if roll() < mind.aip(5):
            if mind.skill_of(3) and roll() < mind.aip(6):
                return ('cast', 3, 'seen')
            if mind.skill_of(1):
                return ('cast', 1, 'seen')
    if d > mind.aip(8) and roll() < mind.aip(7):
        return ('near', 6)
    return ('circle',) if roll() < 70 else ('idle', 10)


def turned(around: Point, at: Point, step: float, side: int) -> Point:
    """A point `step` units across the line from `around` to `at`, on `side` (+1 or -1), at the same distance."""
    dx, dy = at[0] - around[0], at[1] - around[1]
    gap = math.hypot(dx, dy) or 1.0
    angle = math.atan2(dy, dx) + side * step / gap
    return (around[0] + math.cos(angle) * gap, around[1] + math.sin(angle) * gap)


def away_from(origin: Point, at: Point, distance: float) -> Point:
    """The point `distance` units from `origin` on the line from it through `at` (straight on when they meet)."""
    dx, dy = at[0] - origin[0], at[1] - origin[1]
    gap = math.hypot(dx, dy)
    if gap < 1e-6:
        dx, dy, gap = 1.0, 0.0, 1.0
    return (origin[0] + dx / gap * distance, origin[1] + dy / gap * distance)


def bolt_parts(missile: int, level: int, rolls: random.Random) -> dict[str, float]:
    """A missile's points by kind, rolled when it is made (notes-damage.md B1: fixed at creation), each
    in [least, most) as the game's roll."""
    return {kind: rolls.uniform(least, most) for kind, (least, most) in missile_damage(missile, level).items()}


def landing_parts(
    row: Mapping[str, str], damage: tuple[float, float], level: int, rolls: random.Random
) -> dict[str, float]:
    """A swing's points [table]: the physical roll (sim/monsters.py `Traits.damage`, rank and all) and, when
    the row's elemental add is on A1, its chance of `El1MinD..El1MaxD(H)` x DM(H) / 100 of its type."""
    parts = {'physical': rolls.uniform(*damage)}
    if row.get('El1Mode') == 'A1' and rolls.random() * 100 < number(row, 'El1Pct(H)'):
        scale = float(tables()['monlvl'].get(str(level), {}).get('DM(H)', 0)) / 100
        kind = row.get('El1Type', '')
        kind = rolls.choice(RANDOM_ELEMENTS) if kind == 'rand' else ELEMENTS.get(kind, kind)
        points = rolls.uniform(number(row, 'El1MinD(H)'), number(row, 'El1MaxD(H)')) * scale
        parts[kind] = parts.get(kind, 0.0) + points
    return parts


def resisted(
    share: Mapping[str, float], hexed: Curse | None, raw: Mapping[str, float] | None = None
) -> dict[str, float]:
    """The share of each kind of damage that reaches the character under a curse [code, notes-damage.md B2]:
    the resistance in percent (`raw`: before the cap, Hell's penalty taken off; else what `share` says)
    plus the curse's change, then capped at 75 (physical 50) and floored at -100."""
    found = dict(share)
    if hexed is None:
        return found
    for kind, change in hexed.resists.items():
        before = (raw or {}).get(kind, (1 - found.get(kind, 1.0)) * 100)
        cap = 50.0 if kind == 'physical' else 75.0
        found[kind] = 1 - min(max(before + change, -100.0), cap) / 100
    return found


# -- the minds in a pack ------------------------------------------------------------------------------------------


class Host(Protocol):
    """What `Minds` needs of the pack it plays in (sim/monsters.py `Pack`): the walkers, their rolls, a stride
    toward a point (walls or none), the first-sight test, footing at a point, and how a blow is made."""

    walkers: dict[int, Any]
    rolls: dict[int, random.Random]

    def _go(self, walker: Any, goal: Point, stride: float, stop: float) -> bool: ...
    def _sees(self, walker: Any, target: Point) -> bool: ...
    def _footing(self, spot: Point) -> bool: ...
    def _made(self, frame: int, unit: int, target: int, parts: Mapping[str, float], kind: str, missile: int) -> Any: ...


class Minds:
    """The walkers of a pack that think by a read AI (`walker.mind`), their missiles in the air, the curses on
    the character and its companions (by their index in the targets: 0 the character), a poison on them, the
    Storm Casters' marks. `aware` beyond RADIUS: every such monster knows of the character within it from the
    first frame (a situation's "aware of everyone", stage.py); else the code's radius and first sight."""

    def __init__(self, host: Host, aware: float = 0.0, defence: float = DEFENCE, level: int = CHARACTER_LEVEL) -> None:
        self.host = host
        self.aware = aware
        self.defence, self.level = defence, level
        self.bolts: list[Bolt] = []
        self.hexes: dict[int, Curse] = {}
        self.poisons: dict[int, tuple[float, int, int]] = {}  # target -> (points a frame, until, the caster)
        self.marks: dict[int, int] = {}  # target -> the frame its `fingermagecurse` is gone at
        # What was cast, for the checks and the viewer: (frame, unit, type, skill, the aim) and every missile let
        # go: (frame, unit, type, missile, from, toward, the frame it is gone at).
        self.casts: list[tuple[int, int, int, str, Point]] = []
        self.births: list[tuple[int, int, int, int, Point, Point, int]] = []
        self.cursed: list[tuple[int, int, str, tuple[int, ...]]] = []  # (frame, unit, curse, the targets it fell on)
        # Every missile when it is gone, for a viewer: (frame let go, frame gone, from, where it ended, let go at the
        # character, it took from the character).
        self.flown: list[tuple[int, int, Point, Point, bool, bool]] = []
        # The character's resistances by kind (percent, Hell's penalty off) for a think that weighs them (Diablo's);
        # empty: sim/diablo.py's stand-in. Diablo's thinks as drawn: (frame, unit, action, the target's index).
        self.resists: dict[str, float] = {}
        self.thoughts: list[tuple[int, int, str, int]] = []
        # What casts raised since the holder of the pack last took them (`Summon`; sim/baal.py's tentacles and clone).
        self.summons: list[Summon] = []

    # -- a frame ---------------------------------------------------------------------------------------------

    def hex_on(self, index: int, frame: int) -> Curse | None:
        found = self.hexes.get(index)
        if found is not None and frame >= found.until:
            del self.hexes[index]
            return None
        return found

    def fly(self, frame: int, targets: Sequence[Point]) -> list[Any]:
        """The missiles a frame on, what they burn or end on, and the poisons' frame."""
        blows: list[Any] = []
        flying = []
        spawned: list[Bolt] = []  # the trails left this frame: they stand from the next
        for bolt in self.bolts:
            if frame >= bolt.ends:
                self._gone(bolt, frame)
                continue
            if 0 <= bolt.homing < len(targets):
                goal = targets[bolt.homing]
                gap = math.dist(bolt.at, goal)
                if gap > 1e-6:
                    bolt.dx, bolt.dy = (goal[0] - bolt.x) / gap, (goal[1] - bolt.y) / gap
            cell = (math.floor(bolt.x), math.floor(bolt.y))
            bolt.x += bolt.dx * bolt.step
            bolt.y += bolt.dy * bolt.step
            if bolt.sides and (math.floor(bolt.x), math.floor(bolt.y)) != cell:
                for dx, dy in ((-bolt.dy, bolt.dx), (bolt.dy, -bolt.dx)):
                    spawned.append(
                        Bolt(
                            bolt.unit, bolt.txt, bolt.sides, bolt.x, bolt.y, dx, dy, bolt.side_step, frame,
                            frame + bolt.side_life, dict(bolt.parts), kills=False, struck=bolt.struck, aim=bolt.aim,
                            origin=bolt.at,
                        )
                    )  # fmt: skip
            near = sorted((math.dist(bolt.at, body), index) for index, body in enumerate(targets))
            near = [(gap, index) for gap, index in near if gap <= CONTACT]
            if bolt.trail:
                spawned.append(
                    Bolt(
                        bolt.unit, bolt.txt, bolt.trail, bolt.x, bolt.y, 0.0, 0.0, 0.0, frame, frame + bolt.trail_life,
                        dict(bolt.trail_parts), kills=False, aim=bolt.aim, origin=bolt.at, rate=bolt.trail_rate,
                    )
                )  # fmt: skip
            if bolt.rate > 0:
                for _gap, index in near:
                    if frame - bolt.hit_at.get(index, frame - bolt.every) < bolt.every:
                        continue
                    bolt.hit_at[index] = frame
                    bolt.struck.add(index)
                    blows.append(
                        self.host._made(
                            frame,
                            bolt.unit,
                            index,
                            {k: v * bolt.rate for k, v in bolt.parts.items()},
                            SPELL,
                            bolt.missile,
                        )
                    )
                flying.append(bolt)
                continue
            if bolt.kills and near:
                bolt.struck.add(near[0][1])
                blows += self._struck(bolt, near[0][1], frame)
                self._gone(bolt, frame)
                continue
            for _gap, index in near:
                if index not in bolt.struck:
                    bolt.struck.add(index)
                    blows += self._struck(bolt, index, frame)
            flying.append(bolt)
        self.bolts = flying + spawned
        for index, (rate, until, unit) in list(self.poisons.items()):
            if frame >= until or index >= len(targets):
                del self.poisons[index]
                continue
            blows.append(self.host._made(frame, unit, index, {'poison': rate}, POISON, 0))
        return blows

    def _gone(self, bolt: Bolt, frame: int) -> None:
        if bolt.step <= 0:
            return  # a standing trail (a wall's flame): its maker's flight is the viewer's line
        self.flown.append((bolt.born, frame, bolt.origin, bolt.at, bolt.aim == 0, 0 in bolt.struck))

    def _struck(self, bolt: Bolt, index: int, frame: int) -> list[Any]:
        """A missile ends on body `index`: its points, a poison begun (a weaker one than a poison already on
        is lost, notes-damage.md A4), a Storm Caster's mark."""
        parts = dict(bolt.parts)
        rate = parts.pop('poison', 0.0)
        if rate and bolt.poison:
            held = self.poisons.get(index)
            if held is None or rate >= held[0]:
                self.poisons[index] = (rate, frame + bolt.poison, bolt.unit)
        if bolt.missile == FINGER_MISSILE:
            skill = data()['skills']['FingerMageSpider']
            walker = self.host.walkers.get(bolt.unit)
            level = walker.mind.level.get(1, 1) if walker is not None and walker.mind else 1
            self.marks[index] = frame + int(skill_calc(skill, skill['auralencalc'], level))
        return [self.host._made(frame, bolt.unit, index, parts, SPELL, bolt.missile)] if parts else []

    def act(self, walker: Any, frame: int, targets: Sequence[Point]) -> list[Any]:
        """A frame of one walker of a read AI: its swing lands, its cast lets go, its walk goes on, and when
        its action is over it thinks."""
        mind: Mind = walker.mind
        blows: list[Any] = []
        if walker.doing == STRIKE and frame == walker.lands:
            blows += self._land(walker, frame, targets)
        if walker.doing == CAST and frame in mind.releases:
            self._release(walker, frame, targets)
        if walker.doing == WALK:
            self._walk(walker, targets)
        if walker.doing == STAGGER:
            if frame >= walker.until:
                # After a hit's recovery the monster thinks again after `aidel` (notes-mobs.md section 2).
                walker.doing, walker.until = STAND, frame + mind.delay
            return blows
        if frame >= walker.until:
            self._think(walker, frame, targets)
        return blows

    def lost(self, walker: Any) -> None:
        """A stagger: the swing's blow and the cast's missiles not yet let go are lost."""
        walker.mind.releases = []

    # -- thinking --------------------------------------------------------------------------------------------

    def _candidates(self, walker: Any, targets: Sequence[Point]) -> list[tuple[float, int]]:
        """[code] the target search: (AI distance, index) of every body within the radius, in sight until
        the monster first had a target; nobody when the character is beyond PLAYER_REACH."""
        mind: Mind = walker.mind
        here = walker.at
        if not targets or ai_distance(here, targets[0]) >= max(PLAYER_REACH, self.aware, mind.radius):
            return []
        everyone = self.aware > mind.radius
        radius = self.aware if everyone else mind.radius
        found = []
        for index, body in enumerate(targets):
            away = ai_distance(here, body)
            if away < radius and (mind.woke or everyone or self.host._sees(walker, body)):
                found.append((away, index))
        return sorted(found)

    def _think(self, walker: Any, frame: int, targets: Sequence[Point]) -> None:
        mind: Mind = walker.mind
        rolls = self.host.rolls[walker.unit]
        found = self._candidates(walker, targets)
        if not found:
            away = ai_distance(walker.at, targets[0]) if targets else float(FAR_LOOK)
            look = NEAR_LOOK if away < LOOK_EDGE else int(away - 10) if away < RADIUS else FAR_LOOK
            self._idle(walker, frame, max(look, 1))
            return
        mind.woke = True
        if mind.ai == DIABLO:
            self._diablo(walker, frame, targets)
            return
        if mind.ai == BAAL:
            from inventory_tracking.combat.sim import baal

            baal.think(self, walker, frame, targets, found[0][1])
            return
        d, index = found[0]
        body = targets[index]
        melee = math.dist(walker.at, body) <= REACH

        def roll() -> int:
            return rolls.randrange(100)

        if mind.ai == DOOM_KNIGHT:
            act = doom_knight(mind, roll, melee)
        elif mind.ai == MEGADEMON:
            act = megademon(mind, roll, d, melee, frame)
        elif mind.ai == FINGER_MAGE:
            marked = self.marks.get(index, -1) > frame
            act = finger_mage(mind, roll, d, melee, walker.health, self._led(walker), marked)
        else:
            act = self._oblivion(walker, frame, targets, index, d, roll)
        self._do(walker, act, index, frame, targets)

    def _diablo(self, walker: Any, frame: int, targets: Sequence[Point]) -> None:
        """Diablo's think (sim/diablo.py): his target, what the code weighs of it, one draw over the weights."""
        from inventory_tracking.combat.sim import diablo

        mind: Mind = walker.mind
        rolls = self.host.rolls[walker.unit]
        if mind.home is None:
            mind.home = walker.at
        index = 0
        if len(targets) > 1 and rolls.random() >= diablo.CHARACTER_SHARE:
            index = min(range(1, len(targets)), key=lambda at: math.dist(walker.at, targets[at]))
        body = targets[index]
        resists = self.resists or diablo.CHARACTER_RESISTS
        home = mind.home
        sight = diablo.Sight(
            melee=math.dist(walker.at, body) <= diablo.REACH,
            seen=self.host._sees(walker, body),
            away=diablo.less_size(walker.at, body),
            fire=resists.get('fire', 0.0) if index == 0 else 0.0,
            lightning=resists.get('lightning', 0.0) if index == 0 else 0.0,
            candidates=len(targets),
            far_home=ai_distance(walker.at, home) <= diablo.HOME_FAR < ai_distance(body, home),
            farther_home=ai_distance(body, home) > diablo.HOME_FARTHER,
        )
        action = diablo.choose(diablo.weights(sight), rolls)
        self.thoughts.append((frame, walker.unit, diablo.ACTIONS[action], index))
        slot = diablo.SLOTS.get(action)
        if slot is not None:
            if not mind.skill_of(slot):
                self._idle(walker, frame, diablo.MISSING_SKILL_IDLE)
            elif action == diablo.RUN:
                mind.skill, mind.mode, mind.slot, mind.target = mind.skill_of(slot), 'seq_diablorun', slot, index
                self._set_walk(walker, frame, follow=index, pace=diablo.RUN_PACE, held=diablo.REACH)
                walker.until = frame + diablo.MODE_FRAMES['seq_diablorun'] + mind.delay
                self.casts.append((frame, walker.unit, walker.txt, mind.skill, body))
            else:
                self._cast(walker, slot, index, frame, targets)
            return
        if action in (diablo.SWING, diablo.SMASH):
            self._do(walker, ('attack', 'A1' if action == diablo.SWING else 'A2'), index, frame, targets)
        elif action == diablo.WALK_AT:
            self._set_walk(walker, frame, goal=body, pace=diablo.WALK_PACE, held=STOP)
        elif action == diablo.CIRCLE:
            self._do(walker, ('circle',), index, frame, targets)
        elif action == diablo.HOME:
            self._set_walk(walker, frame, goal=home, pace=diablo.HOME_PACE)
        elif action == diablo.ROAM:
            step = diablo.ROAM_STEP
            self._set_walk(
                walker, frame, goal=(walker.x + rolls.uniform(-step, step), walker.y + rolls.uniform(-step, step))
            )
        elif action == diablo.POSE:
            walker.doing, walker.until, walker.lands = CAST, frame + diablo.MODE_FRAMES['S4'] + mind.delay, -1
            mind.releases = []
        else:
            self._idle(walker, frame, diablo.IDLE_FRAMES)

    def _led(self, walker: Any) -> bool:
        """[inferred] a minion's leader stands while a unique of its AI lives in the pack (the scene does not
        say whose minion it is); a monster of no rank has none."""
        if not walker.flags & MINION_FLAG:
            return False
        return any(
            other.mind is not None and other.mind.ai == walker.mind.ai and other.flags & LEADERS
            for other in self.host.walkers.values()
        )

    def _oblivion(
        self, walker: Any, frame: int, targets: Sequence[Point], index: int, d: float, roll: Callable[[], int]
    ) -> Act:
        mind: Mind = walker.mind
        body = targets[index]
        hexed = self.hex_on(index, frame)
        cursed = hexed is not None and hexed.state == data()['states']['decrepify']
        knight = self._knight(walker)
        hiding = knight is not None and math.dist(knight.at, body) ** 2 > d * d
        seen = [
            (ai_distance(walker.at, other), at)
            for at, other in enumerate(targets)
            if ai_distance(walker.at, other) <= 48 and self.host._sees(walker, other)
        ]
        e, mind.target = min(seen) if seen else (float('inf'), -1)
        act = oblivion_knight(mind, roll, d, cursed, hiding, bool(seen), e, frame)
        if act[0] == 'hide':
            assert knight is not None
            mind.goal = knight.at
        return act

    def _knight(self, walker: Any) -> Any:
        """[code] the nearest live Doom Knight (BaseId doomknight1) within 50 units (notes-ai-74.md, the scan)."""
        best, found = 2500.0, None
        for other in self.host.walkers.values():
            row = row_of(other.txt)
            if other is walker or row is None or row.get('BaseId') != 'doomknight1':
                continue
            gap = (other.x - walker.x) ** 2 + (other.y - walker.y) ** 2
            if gap <= best:
                best, found = gap, other
        return found

    # -- what a think decided ----------------------------------------------------------------------------------

    def _idle(self, walker: Any, frame: int, frames: int) -> None:
        walker.doing, walker.until, walker.lands = STAND, frame + max(frames, 1), -1
        walker.mind.releases = []

    def _set_walk(
        self,
        walker: Any,
        frame: int,
        *,
        goal: Point | None = None,
        follow: int = -1,
        pace: float = 1.0,
        held: float = 0.5,
    ) -> None:
        mind: Mind = walker.mind
        mind.goal, mind.follow, mind.pace, mind.held = goal, follow, pace, held
        walker.doing, walker.until, walker.lands = WALK, frame + mind.delay, -1
        mind.releases = []

    def _do(self, walker: Any, act: Act, index: int, frame: int, targets: Sequence[Point]) -> None:
        mind: Mind = walker.mind
        rolls = self.host.rolls[walker.unit]
        body = targets[index]
        kind = act[0]
        if kind == 'idle':
            self._idle(walker, frame, int(act[1]))
        elif kind == 'attack':
            mode = str(act[1]) if len(act) > 1 else 'A1'
            mind.mode = mode
            frames = MODE_FRAMES[mind.ai, mode] if mind.ai != DIABLO else self._diablo_frames(mode)
            walker.doing, walker.aim, mind.target = STRIKE, index, index
            walker.lands = frame + max(round(BLOW_SHARE * frames), 1)
            walker.until = frame + frames + mind.delay
        elif kind == 'cast':
            self._cast(walker, int(act[1]), mind.target if len(act) > 2 else index, frame, targets)
        elif kind == 'approach':
            self._set_walk(walker, frame, follow=index, held=STOP)
        elif kind == 'circle':
            side = 1 if rolls.randrange(256) < 0x80 else -1
            self._set_walk(walker, frame, goal=turned(body, walker.at, CIRCLE_STEP, side))
        elif kind in ('flee', 'retreat'):
            goal = away_from(body, walker.at, float(act[1]))
            if kind == 'retreat' and not self.host._footing(goal):
                # A3 found no way out: A4, the bone spirit at the target, or B (here: idle) without one.
                if mind.skill_of(3):
                    self._cast(walker, 3, index, frame, targets)
                else:
                    self._idle(walker, frame, 10)
                return
            self._set_walk(walker, frame, goal=goal, pace=float(act[2]))
        elif kind == 'hide':
            self._set_walk(walker, frame, goal=mind.goal)
        elif kind == 'near':
            step = int(act[1])
            axis, sign, other = rolls.randrange(2), rolls.choice((-1, 1)), rolls.randrange(step) * rolls.choice((-1, 1))
            offset = (sign * step, other) if axis == 0 else (other, sign * step)
            self._set_walk(walker, frame, goal=(body[0] + offset[0], body[1] + offset[1]))
        else:
            raise ValueError(f'no such act {act!r}')

    @staticmethod
    def _diablo_frames(mode: str) -> int:
        from inventory_tracking.combat.sim import diablo

        return diablo.MODE_FRAMES.get(mode, 20)

    def _cast(self, walker: Any, slot: int, index: int, frame: int, targets: Sequence[Point]) -> None:
        mind: Mind = walker.mind
        mode = mind.row.get(f'Sk{slot}mode', 'S1')
        mind.skill, mind.mode, mind.slot, mind.target = mind.skill_of(slot), mode, slot, index
        if mind.ai == DIABLO:
            from inventory_tracking.combat.sim import diablo

            frames = diablo.MODE_FRAMES.get(mode, 20)
            mind.releases = diablo.releases(mind.skill, frame, mind.level.get(slot, 1))
            walker.doing, walker.until, walker.lands, walker.aim = CAST, frame + frames + mind.delay, -1, index
            self.casts.append((frame, walker.unit, walker.txt, mind.skill, targets[index]))
            return
        frames = MODE_FRAMES[mind.ai, mode]
        first = frame + RELEASE[mind.ai, mode]
        if mind.ai == MEGADEMON:
            mind.releases = list(range(first, frame + frames, FLAME_GAP))
            mind.cool, mind.inferno = frame + int(mind.aip(6)), True
        else:
            mind.releases = [min(first, frame + frames - 1)]
        walker.doing, walker.until, walker.lands, walker.aim = CAST, frame + frames + mind.delay, -1, index
        self.casts.append(
            (frame, walker.unit, walker.txt, mind.skill, targets[index] if index < len(targets) else walker.at)
        )

    # -- what a frame does -------------------------------------------------------------------------------------

    def _walk(self, walker: Any, targets: Sequence[Point]) -> None:
        mind: Mind = walker.mind
        if mind.follow >= 0:
            if mind.follow >= len(targets):
                walker.doing = STAND
                return
            goal = targets[mind.follow]
        elif mind.goal is not None:
            goal = mind.goal
        else:
            walker.doing = STAND
            return
        if math.dist(walker.at, goal) <= mind.held:
            walker.doing = STAND  # there: it waits for its next think
            return
        if not self.host._go(walker, goal, speed_of(mind.row) * mind.pace, mind.held):
            walker.doing = STAND

    def _land(self, walker: Any, frame: int, targets: Sequence[Point]) -> list[Any]:
        """A swing's blow: on the character with the hit chance, on a companion always (it takes nothing here)."""
        mind: Mind = walker.mind
        index = walker.aim
        if not 0 <= index < len(targets) or math.dist(walker.at, targets[index]) > REACH:
            return []
        rolls = self.host.rolls[walker.unit]
        level = walker.traits.level
        row, damage = mind.row, walker.traits.damage
        if mind.mode == 'A2':
            # [table] the second attack: its own to-hit and its damage, by the ratio of the rows' A2 to A1 maxima.
            scale = number(row, 'A2MaxD(H)') / max(number(row, 'A1MaxD(H)'), 1.0)
            row, damage = (
                {**row, 'A1TH(H)': row.get('A2TH(H)', row.get('A1TH(H)', '0'))},
                (damage[0] * scale, damage[1] * scale),
            )
        if index == 0 and rolls.random() >= hit_chance(row, level, self.defence, self.level):
            return []
        parts = landing_parts(row, damage, level, rolls)
        for element, least, most in walker.traits.elements:
            parts[element] = parts.get(element, 0.0) + parts['physical'] * rolls.uniform(least, most)
        return [self.host._made(frame, walker.unit, index, parts, MELEE_KIND, 0)]

    def _release(self, walker: Any, frame: int, targets: Sequence[Point]) -> None:
        """The cast lets go: a missile, a flame of the stream, or a curse on whom it falls on."""
        mind: Mind = walker.mind
        rolls = self.host.rolls[walker.unit]
        index = mind.target
        if not 0 <= index < len(targets):
            return
        body = targets[index]
        level = mind.level.get(mind.slot, 1)
        skill = mind.skill
        if skill in ('Decrepify', 'MonCurseCast'):
            # The curse's mark, from the caster to its target, for a viewer (the client draws 189 and others).
            self.flown.append((frame, frame + 10, walker.at, body, index == 0, False))
        if skill == 'Decrepify':
            self._curse(walker, frame, targets, body, 'Decrepify', level, None, curse_radius('Decrepify', level))
        elif skill == 'MonCurseCast':
            caster = data()['skills']['MonCurseCast']
            length = skill_calc(caster, caster['auralencalc'], level)
            chosen = rolls.choice(MON_CURSES)
            self._curse(walker, frame, targets, body, chosen, level, length, curse_radius('MonCurseCast', level))
        elif skill == 'DoomKnightMissile':
            self._shoot(walker, frame, rolls.choice(BOLTS), level, body, index)
        elif skill == 'MonBoneSpirit':
            self._shoot(walker, frame, BONE_SPIRIT, level, body, index, homing=index)
        elif skill == 'FingerMageSpider':
            self._shoot(walker, frame, FINGER_MISSILE, level, body, index)
        elif skill == 'MegademonInferno':
            self._shoot(walker, frame, int(missile_by_name(data()['skills'][skill]['srvmissilea'])), level, body, index)
        elif mind.ai == DIABLO:
            self._diablo_release(walker, frame, skill, level, body, index)
        elif mind.ai == BAAL:
            from inventory_tracking.combat.sim import baal

            baal.release(self, walker, frame, targets)

    def _diablo_release(self, walker: Any, frame: int, skill: str, level: int, body: Point, index: int) -> None:
        """Diablo's missiles (sim/diablo.py): a missile of the stream at where his target stands now, the ring of
        fire, the fire wall's makers."""
        from inventory_tracking.combat.sim import diablo

        rolls = self.host.rolls[walker.unit]

        def made(missile: int, heading: float, step: float, life: int, **more: Any) -> Bolt:
            parts = {kind: rolls.uniform(least, most) for kind, (least, most) in diablo.points(missile, level).items()}
            return Bolt(
                walker.unit, walker.txt, missile, walker.x, walker.y, math.cos(heading), math.sin(heading), step,
                frame, frame + life, parts, kills=False, aim=index, origin=walker.at, **more,
            )  # fmt: skip

        toward = math.atan2(body[1] - walker.y, body[0] - walker.x)
        if skill == 'DiabLight':
            life = diablo.missile_life(level)
            bolt = made(
                diablo.LIGHTNING_MISSILE,
                toward,
                diablo.STREAM_STEP,
                life,
                rate=diablo.rate(diablo.LIGHTNING_MISSILE),
                every=diablo.every(diablo.LIGHTNING_MISSILE),
            )
            self.bolts.append(bolt)
            self.births.append((frame, walker.unit, walker.txt, bolt.missile, walker.at, body, bolt.ends))
        elif skill == 'DiabFire':
            once: set[int] = set()  # [take] one hit a body a ring: every missile of the cast shares it
            row = diablo.data()['missiles'][str(diablo.RING_MISSILE)]
            for heading in diablo.ring_headings():
                bolt = made(diablo.RING_MISSILE, heading, diablo.RING_STEP, int(number(row, 'Range')), struck=once)
                self.bolts.append(bolt)
            self.births.append((frame, walker.unit, walker.txt, diablo.RING_MISSILE, walker.at, body, frame + 50))
        elif skill == 'DiabWall':
            flame = {
                kind: rolls.uniform(least, most)
                for kind, (least, most) in diablo.points(diablo.WALL_FLAME, level).items()
            }
            for heading in diablo.wall_headings(toward, level * diablo.WALL_MAKERS_PER_LEVEL):
                bolt = made(
                    diablo.WALL_MAKER, heading, diablo.WALL_STEP, diablo.WALL_LIFE, trail=diablo.WALL_FLAME,
                    trail_life=diablo.FLAME_LIFE,
                    trail_rate=diablo.rate(diablo.WALL_FLAME), trail_parts=dict(flame),
                )  # fmt: skip
                bolt.parts = {}
                self.bolts.append(bolt)
            self.births.append(
                (frame, walker.unit, walker.txt, diablo.WALL_MAKER, walker.at, body, frame + diablo.WALL_LIFE)
            )

    def summon(
        self, walker: Any, txt: int, at: Point, frame: int, lasts: int | None, share: float = 0.0, most: float = 0.0
    ) -> None:
        """A monster raised by `walker`'s cast (`Summon`), its seed from the walker's own rolls."""
        seed = self.host.rolls[walker.unit].getrandbits(32)
        self.summons.append(Summon(walker.unit, txt, at, frame, lasts, seed, share, most))

    def _shoot(
        self, walker: Any, frame: int, missile: int, level: int, toward: Point, aim: int, *, homing: int = -1
    ) -> None:
        row = missile_row(missile)
        rolls = self.host.rolls[walker.unit]
        dx, dy = toward[0] - walker.x, toward[1] - walker.y
        gap = math.hypot(dx, dy) or 1.0
        ends = frame + int(number(row, 'Range'))
        parts = bolt_parts(missile, level, rolls)
        self.bolts.append(
            Bolt(
                walker.unit, walker.txt, missile, walker.x, walker.y, dx / gap, dy / gap, missile_step(missile),
                frame, ends, parts, int(number(row, 'ELen')) if 'poison' in parts else 0,
                bool(number(row, 'CollideKill')), homing, aim=aim, origin=walker.at,
            )
        )  # fmt: skip
        self.births.append((frame, walker.unit, walker.txt, missile, walker.at, toward, ends))

    def _curse(
        self,
        walker: Any,
        frame: int,
        targets: Sequence[Point],
        at: Point,
        name: str,
        level: int,
        length: float | None,
        radius: float,
    ) -> None:
        """A curse on every body within `radius` of `at`: it takes the place of any curse there (one at a time)."""
        hexed = curse(name, level, frame, length)
        hit = tuple(index for index, body in enumerate(targets) if math.dist(body, at) <= radius)
        for index in hit:
            self.hexes[index] = hexed
        self.cursed.append((frame, walker.unit, name, hit))


@cache
def missile_by_name(name: str) -> str:
    return next(key for key, row in data()['missiles'].items() if row['Missile'] == name)


FINGER_MISSILE = 177  # missiles.txt `fingermagespider`: the Storm Caster's lead
MELEE_KIND = 'melee'  # sim/monsters.py MELEE
LEADERS = SUPER_FLAG | UNIQUE_FLAG
