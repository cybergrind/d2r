"""Diablo (monstats `diablo`, txt 243, AI 51 "Diablo") as the client's code plays him: his think, his red lightning
stream, his fire ring and fire wall, his swings. sim/casters.py `Minds` plays him (`DIABLO`) as it plays the four
Chaos Sanctuary casters; this module holds his rules and his rows (diablo.json, written by `build` below from the
game's tables).

Sources (rca/2026-10-13/re/notes-ai-diablo.md has the addresses and the decompiled reading; rca/2026-10-13/diablo.md
the checks against the takes):

- **[code]** read in Binary Ninja: the think `ai_d2_ai_51_think` (0x14047EC70), its weight table
  `ai_d2_ai_51_decide` (0x14047DD70), the target search `ai_d2_ai_51_find_target` (0x14047E880) and its score
  (0x14047D4A0), the lightning's start and do functions (srvstfunc 53 0x140470950, srvdofunc 152 0x140470F60) and
  the aim (0x1403AD6B0: each missile goes at where the target stands when it is made);
- **[table]** diablo.json from pricing/raw/game-excel: his row, his skills, their missiles;
- **[take]** measured on the 19 recorded Diablo fights (rca/2026-10-13/scripts/diablo_takes.py, diablo-takes.txt;
  diablo_releases in diablo.md section 2): a mode's frames, the frame of it a missile is let go at, how many, how
  fast they go;
- **[inferred]** what neither settles, named where it is chosen.

**The think** [code]. No target search radius to speak of (anyone in the act within 1020 sub-tiles) and no sight
needed to notice. Each think draws one of 17 actions with the weights of `weights` (a sum, one roll uniform over it)
from three tables: the target in melee, out of melee in sight, out of melee out of sight; then changed by the
target's resistances (he favours the element it resists less: fire raw stat against lightning), the distance (no
lightning at all beyond LIGHTNING_RANGE: the run and the wall take its place), how many candidates he has, his and
the target's distance from his home. After an action he thinks again at its mode's end plus `aidel` (12 in Hell).

**The red lightning** (DiabLight, mode SC) [code + take]: the cast puts state 12 `inferno` on him and an end frame
40 frames on (Param1); from the do frame on (10 frames into SC [take]) one missile 172 a frame [take: 38 to 39 a
cast], each **aimed at where the target stands at that frame** (it follows the target), flying STREAM_STEP a frame
[take: 0.88] for Param2 + level - 1 frames (39 at level 10 [code + take]), through every body (Pierce). A missile
takes its points x `DamageRate` / 1024 (82) **each frame a body is within CONTACT of it** [take-checked: a standing
character loses 16 points a frame of the stream at 75 % lightning resistance, the table's 34 raw a hit x 0.08 x
about 6 missiles in contact]. Points at level 10 (Sk1lvl 3 + 7): physical 24.3..26.3, lightning 42.3..52.5
(HitShift 6) [table + code].
"""

import csv
import json
import math
import random
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any


Point = tuple[float, float]
DATA = Path(__file__).parent / 'diablo.json'
SOURCE = Path(__file__).parents[3] / 'pricing' / 'raw' / 'game-excel'
AI = 'Diablo'  # monstats `AI` of his rows (diablo 243, diabloclone 333)

# -- the think [code] -------------------------------------------------------------------------------------------
# The 17 actions of `ai_d2_ai_51_decide` (0x14047DD70), by the index the weighted roll returns and the case of
# `ai_d2_ai_51_think` (0x14047EC70) that acts on it. The skills are monstats slots: 1 DiabLight (SC), 2 DiabCold
# (S2), 3 DiabFire (S1), 4 DiabWall (S3), 5 DiabRun (sequence), 6 PrimeFirewall (S3), 7 DiabPrison (S3).
NONE, WALK_AT, SWING, SMASH, POSE, LIGHTNING, FIRE, COLD, WALL, PRISON, RUN, IDLE, CIRCLE, FIREWALL, HOME = range(15)
PORTAL_PRISON, ROAM = 15, 16
ACTIONS = (
    'none', 'walk at', 'A1', 'A2', 'S4', 'lightning', 'fire ring', 'cold', 'fire wall', 'prison', 'run', 'idle',
    'circle', 'prime firewall', 'home', 'prison a portal', 'roam',
)  # fmt: skip
SLOTS = {LIGHTNING: 1, COLD: 2, FIRE: 3, WALL: 4, RUN: 5, FIREWALL: 6, PRISON: 7}
# The weights, as the client's 16-byte constants load them (index 0..16):
IN_MELEE = (0, 0, 40, 70, 0, 40, 24, 40, 15, 0, 0, 0, 0, 0, 0, 0, 0)  # 0x141814200, 0x141814130, 0x1418132A0
SEEN = (0, 0, 0, 0, 0, 25, 25, 0, 15, 20, 10, 0, 20, 0, 0, 0, 0)  # 0x1418136C0, 0x141813660, 0x1418132C0
UNSEEN = (0, 0, 0, 0, 5, 0, 25, 0, 25, 40, 0, 0, 25, 0, 0, 0, 0)  # 0x1418136A0, 0x141813400, 0x1418132D0
LIGHTNING_RANGE = 25  # sub-tiles (the target's distance less its size): beyond, no lightning (0x14047E43F)
FAR_SCORE = 60  # the target's score beyond which the prison's weight is 30 (0x14047E4AA)
HOME_FAR, HOME_FARTHER = 85, 105  # sub-tiles from his home point (0x14047E065, 0x14047E070)
LOW_LIFE = 20  # percent: a target below it draws A1 at 50 (0x14047E2A0)
IDLE_FRAMES = 4  # Hell's idle (case 11: 12 / 8 / 4 by difficulty, 0x14047F4BE)
MISSING_SKILL_IDLE = 2  # a case whose skill slot is empty idles this long (0x14047F088)
AWARE = 1020  # sub-tiles: the target search's limit (callback 0x14047E790), all of the act in practice
WALK_PACE = 1.2  # order block +0x24 = 20: a walk at the target's spot at +20 % (case 1)
HOME_PACE = 1.5  # +0x24 = 50 (case 14)
ROAM_STEP = 5  # `ai_d2_ai_walk_random`(game, unit, 5) (case 16)

# -- his target [code + take] -------------------------------------------------------------------------------------
# The search scores every player and pet of the act (0x14047D4A0: in melee 100, in sight 75, life under 20 % +300,
# its resistances, skills and damage) and takes the best. The score's terms are not all read; the takes' path
# records name the character in 426 of the 518 frames of his casts where they name someone (82 %), a companion in 92.
CHARACTER_SHARE = 0.82  # [take] a think's target is the character with this chance, else the nearest companion
# [take] mobs.py RAW_RESISTS, the main set: fire 90 against lightning 79 after Hell's penalty (stats 39 / 41 of
# the hurt events: 190 / 179). Only their order matters to him.
CHARACTER_RESISTS = {'fire': 90.0, 'lightning': 79.0}
SIZE = 1.0  # [inferred] the target's size per axis the distance is taken less of (players' size not read)
REACH = 4.5  # [inferred] his melee range: monstats2 MeleeRng 3 plus half his SizeX 3

# -- his modes and missiles [take unless said] ----------------------------------------------------------------------
MODE_FRAMES = {'SC': 47, 'S1': 33, 'S2': 20, 'S3': 29, 'S4': 20, 'A1': 16, 'A2': 20, 'seq_diablorun': 77}
# S2, S4 and A2: none or too few in the takes [inferred 20]. The run's 77 is the median of 3.
RELEASE = {'SC': 10, 'S1': 16, 'S3': 17}  # frames into the mode of its first missile (14, 7 and 6 casts)
STREAM_MISSILES = 39  # one a frame from the release: 38 to 39 a whole cast (Param1 40 frames from the start [code])
STREAM_STEP = 0.88  # units a frame (572 missiles: 0.79..0.94); Vel 20 x STEP_PER_VEL would say 0.96
RING_MISSILES = 64  # DiabFire: missiles 176 a cast, all 7 casts
RING_STEP = 30 * 0.048  # Vel 30 x sim/casters.py STEP_PER_VEL [table + take]
WALL_MAKERS_PER_LEVEL = 1  # DiabWall calc1 `lvl`: makers a cast = its level (10 at level 10: 6 of 6 casts) [code]
WALL_STEP = 0.55  # a maker's net way a frame (60 makers)
WALL_LIFE = 76  # a maker's frames (Range 80)
WALL_FAN = math.radians(40)  # the makers leave within 0..40 degrees of the line to the target (-1..40 seen)
FLAME_LIFE = 34  # a flame 180 stands this long (2,502 flames; Range 36)
FLAME_SHARE = 0.3  # [take, fitted] of a flame's table points a frame of contact (`rate`)
RUN_PACE = 2.0  # [inferred] the charge's speed, times his walk (DiabRun calc1 `Velocity %` 20 not read further)
LIGHTNING_MISSILE, RING_MISSILE, WALL_MAKER, WALL_FLAME = 172, 176, 179, 180


@cache
def data() -> dict[str, Any]:
    return json.loads(DATA.read_text(encoding='utf-8'))


def row(txt: int) -> dict[str, str] | None:
    return data()['monsters'].get(str(txt))


def is_diablo(txt: int) -> bool:
    found = row(txt)
    return found is not None and found.get('AI') == AI


@dataclass(frozen=True)
class Sight:
    """What one think of his weighs, as the code reads it of his target and himself."""

    melee: bool  # the target within his melee range (`ai_d2_unit_in_melee_range`)
    seen: bool  # no wall between them (`ai_d2_unit_sight_blocked`, mask 4)
    away: float  # the AI distance less the target's size (`ai_d2_ai_distance_to_unit_less_size`)
    fire: float = CHARACTER_RESISTS['fire']  # the target's fire resistance (stat 39)
    lightning: float = CHARACTER_RESISTS['lightning']  # and lightning (stat 41)
    candidates: int = 3  # the units his search scored (players and their pets)
    score: float = 0.0  # the chosen one's score (0x14047D4A0); over FAR_SCORE the prison weighs 30
    low_life: bool = False  # the target under LOW_LIFE percent
    chilled: bool = False  # the target under state 11 `cold`
    far_home: bool = False  # the target farther than HOME_FAR from his home, he within it (var_ec)
    farther_home: bool = False  # farther than HOME_FARTHER (var_e8)
    area_caster: bool = False  # the target holds Meteor, Blizzard, a Fire Wall over 3, an Immolation Arrow over 7
    prison_ok: bool = True  # 0x14048C040 (game, unit, 199 DiabPrison, target) said 0 [inferred: not read]


def weights(sight: Sight) -> list[int]:
    """The 17 weights of one think (0x14047DD70), modifier by modifier as the code applies them."""
    w = list(IN_MELEE if sight.melee else SEEN if sight.seen else UNSEEN)
    prison = 0  # in melee the prison stays 0 (its weight is the table's, 0)
    if sight.melee:  # 0x14047E25C
        if sight.low_life:
            w[SWING] = 50
        if sight.chilled:
            w[COLD] = w[WALL] = 0
        if sight.fire > sight.lightning:
            w[FIRE] = 14
        elif sight.fire < sight.lightning:
            w[FIRE] += 10
        if not sight.seen:
            w[LIGHTNING] = w[FIRE] = 0
    elif sight.seen:  # 0x14047E405
        wall = 15
        if sight.away > LIGHTNING_RANGE:
            w[RUN], wall, w[WALL], w[LIGHTNING] = 20, 10, 10, 0
        if sight.fire > sight.lightning:
            base = fire = w[FIRE] = 15
            w[WALL] = wall - 10
        elif sight.fire == sight.lightning:
            base, fire = 25, w[FIRE]
        else:
            base = fire = w[FIRE] = 35
            w[WALL] = wall + 10
        if sight.candidates < 2:
            fire = w[FIRE] = base - 10
        elif sight.candidates > 3:
            fire = w[FIRE] = fire + 5
        prison = 30 if sight.score > FAR_SCORE else SEEN[PRISON]
        if sight.candidates < 2:
            prison = 0  # [inferred] 0x1403A40D0's count (var_bc) taken under 2 with a lone target
        if sight.area_caster and not sight.far_home:
            w[FIRE] = fire + 10
            w[RUN], w[FIREWALL] = 30, 15
        elif sight.far_home:
            w[CIRCLE], w[RUN], w[FIREWALL] = 10, 0, 15
            prison = prison or 10
        if sight.farther_home:
            prison, w[HOME] = 20, 60
    else:  # 0x14047E366
        prison = UNSEEN[PRISON]
        if sight.candidates < 2:
            w[FIRE] = prison = 0
            w[WALK_AT], w[WALL] = 25, 20
        if sight.area_caster and not sight.far_home:
            w[FIREWALL] = 15
        elif sight.far_home:
            w[WALK_AT], w[CIRCLE], w[FIREWALL] = 0, 15, 25
            if sight.candidates < 2:
                prison = 15
        if sight.farther_home:
            w[HOME] = 60
    w[PRISON] = prison if sight.prison_ok else 0  # 0x14047E565
    return w


def choose(found: Sequence[int], roll: random.Random) -> int:
    """The action a think takes: one draw uniform over the weights' sum (the unit's generator), the first index
    whose running sum passes it; IDLE when every weight is 0 (0x14047E651)."""
    total = sum(found)
    if total <= 0:
        return IDLE
    pick = roll.randrange(total)
    running = 0
    for index, weight in enumerate(found):
        running += weight
        if pick < running:
            return index
    return IDLE


def less_size(a: Point, b: Point, size: float = SIZE) -> float:
    """[code] the AI's distance less the target's size: max + min / 2 of the axes, each less `size` (not below 0)."""
    dx, dy = max(abs(a[0] - b[0]) - size, 0.0), max(abs(a[1] - b[1]) - size, 0.0)
    return max(dx, dy) + min(dx, dy) / 2


# -- his missiles' points [code + table] --------------------------------------------------------------------------


def skill_level(txt: int, slot: int) -> int:
    """[table + take] SkNlvl + Hell's MonsterSkillBonus (7), as for the casters (notes-mobs.md section 4)."""
    found = row(txt) or {}
    return int(float(found.get(f'Sk{slot}lvl') or 0)) + int(data()['hell']['MonsterSkillBonus'])


def missile_life(level: int) -> int:
    """[code 0x140470BB0] the stream missile's life: DiabLight `calc1` is 0, so Param2 of the missile (30, its
    `Baseline Range`) + level - 1 frames: 39 at level 10 (the takes: 39 at the median)."""
    return int(float(data()['missiles'][str(LIGHTNING_MISSILE)].get('Param2') or 0)) + level - 1


def rate(missile: int) -> float:
    """A missile that takes from every body in contact each frame: the share of its points a frame. The lightning:
    `DamageRate` / 1024 [code: notes-mobs.md B3, take-checked with `every`]. The wall's flames: FLAME_SHARE of their
    table points a frame [take, fitted: a character standing on a wall lost 2 to 4.5 points a frame at 75 % fire
    (20261013T184953Z-108's hurt events); whole points over the CONTACT flames make 11, the rate's 41 / 1024 a 25th
    of that; the hit of 180 and DiabWall's do-function 102 are not read]. 0: whole points once (the ring)."""
    if missile == LIGHTNING_MISSILE:
        return float(data()['missiles'][str(missile)]['DamageRate']) / 1024
    return FLAME_SHARE if missile == WALL_FLAME else 0.0


def every(missile: int) -> int:
    """[table + take] the frames a stream missile waits before it takes from the same body again: missiles.txt
    `NextDelay` (3 for the lightning; its parser slot is on an encrypted page, notes-damage.md). The takes agree:
    a character standing in the stream had 220 missile-frames within CONTACT a cast and lost 170 to 312 points
    (five casts), against 201 by this rule and 603 if every frame took."""
    found = data()['missiles'].get(str(missile), {})
    return max(int(float(found.get('NextDelay') or 1)), 1)


def points(missile: int, level: int) -> dict[str, tuple[float, float]]:
    """A missile's damage at `level`, by kind (sim/casters.py `missile_damage`'s rule on diablo.json's rows)."""
    from inventory_tracking.combat.sim.casters import ELEMENTS, number, stepped

    found_row = data()['missiles'][str(missile)]
    shift = 2 ** number(found_row, 'HitShift') / 256
    found: dict[str, tuple[float, float]] = {}
    least = number(found_row, 'MinDamage') + stepped(level, [number(found_row, f'MinLevDam{n}') for n in range(1, 6)])
    most = number(found_row, 'MaxDamage') + stepped(level, [number(found_row, f'MaxLevDam{n}') for n in range(1, 6)])
    if most > 0:
        found['physical'] = (least * shift, max(most, least) * shift)
    kind = ELEMENTS.get(found_row.get('EType', ''))
    if kind is not None:
        least = number(found_row, 'EMin') + stepped(level, [number(found_row, f'MinELev{n}') for n in range(1, 6)])
        most = number(found_row, 'EMax') + stepped(level, [number(found_row, f'MaxELev{n}') for n in range(1, 6)])
        found[kind] = (least * shift, max(most, least) * shift)
    return found


def releases(skill: str, frame: int, level: int) -> list[int]:
    """The frames a cast of `skill` begun at `frame` lets missiles go at."""
    mode = mode_of(skill)
    first = frame + RELEASE.get(mode, MODE_FRAMES.get(mode, 20) // 2)
    if skill == 'DiabLight':
        return list(range(first, first + STREAM_MISSILES))
    if skill in ('DiabFire', 'DiabWall'):
        return [first]
    return []


def mode_of(skill: str) -> str:
    found = row(243) or {}
    slot = next((n for n in range(1, 9) if found.get(f'Skill{n}') == skill), 0)
    return found.get(f'Sk{slot}mode', 'S1') if slot else 'S1'


def wall_headings(toward: float, makers: int) -> list[float]:
    """[take] the makers' headings: spread evenly over WALL_FAN from the line to the target (one side, as the takes
    show them: -1..40 degrees)."""
    if makers <= 1:
        return [toward]
    return [toward + WALL_FAN * k / (makers - 1) for k in range(makers)]


def ring_headings(count: int = RING_MISSILES) -> list[float]:
    return [math.tau * k / count for k in range(count)]


# -- diablo.json --------------------------------------------------------------------------------------------------

MONSTER_FIELDS = (
    'Id', '*hcIdx', 'BaseId', 'NameStr', 'AI', 'Velocity', 'Run', 'Level(H)', 'aidel(H)',
    *(f'Skill{n}' for n in range(1, 9)), *(f'Sk{n}mode' for n in range(1, 9)), *(f'Sk{n}lvl' for n in range(1, 9)),
    'A1MinD(H)', 'A1MaxD(H)', 'A1TH(H)', 'A2MinD(H)', 'A2MaxD(H)', 'A2TH(H)', 'ResFi(H)', 'ResLi(H)', 'ResCo(H)',
)  # fmt: skip
SKILL_FIELDS = (
    'skill', '*Id', 'srvstfunc', 'srvdofunc', 'srvmissilea', 'monanim', 'calc1', 'calc2', 'calc3',
    *(f'Param{n}' for n in range(1, 7)), 'MinDam', 'MaxDam', *(f'MinLevDam{n}' for n in range(1, 6)),
    *(f'MaxLevDam{n}' for n in range(1, 6)), 'HitShift', 'EType', 'EMin', 'EMax',
)  # fmt: skip
MISSILE_FIELDS = (
    'Missile', '*ID', 'Vel', 'Range', 'Size', 'Pierce', 'CollideKill', 'LastCollide', 'NextHit', 'NextDelay',
    'DamageRate', 'HitShift', 'MinDamage', *(f'MinLevDam{n}' for n in range(1, 6)), 'MaxDamage',
    *(f'MaxLevDam{n}' for n in range(1, 6)), 'EType', 'EMin', *(f'MinELev{n}' for n in range(1, 6)), 'EMax',
    *(f'MaxELev{n}' for n in range(1, 6)), 'Param1', 'Param2', 'SubMissile1',
)  # fmt: skip


def _rows(source: Path, name: str) -> list[dict[str, str]]:
    with (source / f'{name}.txt').open(newline='', encoding='utf-8', errors='replace') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def build(source: Path = SOURCE) -> dict[str, Any]:
    """diablo.json: the monstats rows of AI `Diablo`, their skills, the skills' server missiles and sub-missiles,
    Hell's skill bonus."""
    pick = lambda found, fields: {name: found[name] for name in fields if found.get(name)}  # ruff: ignore[lambda-assignment]
    monsters = {r['*hcIdx']: pick(r, MONSTER_FIELDS) for r in _rows(source, 'monstats') if r['AI'] == AI}
    named = {r['skill']: r for r in _rows(source, 'skills')}
    wanted = {m[f'Skill{n}'] for m in monsters.values() for n in range(1, 9) if m.get(f'Skill{n}')}
    skills = {name: pick(named[name], SKILL_FIELDS) for name in sorted(wanted) if name in named}
    by_name = {r['Missile']: r for r in _rows(source, 'missiles')}
    names = {s.get('srvmissilea') for s in skills.values()}
    names |= {by_name[n].get('SubMissile1') for n in list(names) if n in by_name}
    missiles = {by_name[n]['*ID']: pick(by_name[n], MISSILE_FIELDS) for n in sorted(filter(None, names))}
    hell = next(r for r in _rows(source, 'difficultylevels') if r['Name'] == 'Hell')
    return {
        'source': 'pricing/raw/game-excel (monstats, skills, missiles, difficultylevels); combat/sim/diablo.py build',
        'monsters': monsters,
        'skills': skills,
        'missiles': missiles,
        'hell': {'MonsterSkillBonus': hell['MonsterSkillBonus']},
    }


if __name__ == '__main__':
    built = build(Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCE)
    DATA.write_text(json.dumps(built, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(
        f'{DATA}: {len(built["monsters"])} monsters, {len(built["skills"])} skills, {len(built["missiles"])} missiles'
    )
