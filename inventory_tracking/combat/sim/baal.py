"""Baal in the Worldstone Chamber (monstats `baalcrab` 544, AI BaalCrab) and his clone (`baalclone` 570, AI
BaalCrabClone) as the arena plays them: his casts, their missiles, the tentacles he raises and the clone he splits
off. sim/casters.py `Minds` plays him (`BAAL`) as it plays Diablo; this module holds his rules and his rows
(baal.json, written by `build` below from the game's tables). rca/2026-10-14/baal-sim.md has the evidence.

**His think is not read.** Every think routine of the AI table from row 101 on (where the act 5 AIs are) lies on a
page of the client that is still encrypted in pricing/raw/re/D2R-decrypted.exe.bndb (2026-10-14: rows 101-135 and
140-154; rca/2026-10-13/re/enc_ranges.txt), as are his skills' do-functions (139 cold missiles, 140 tentacles, 22
nova, 98 teleport). So the think here is no reading of the code: it is the **share of his time in each mode the
probe saw** in eight fights (below), turned into the chance of each act at a think. It says how often he does what,
not when or why; nothing here is a rule of his AI.

Sources, as each number says:

- **[table]** baal.json from pricing/raw/game-excel: his row (skills, modes, levels, `aidel` 12), the skills'
  damage and curse rows, the missiles' speed, range and `Param2`;
- **[take]** the last 3 s of the Throne take 20261011T001816Z-131 (the character came through the portal and the
  recorder ran on): one tentacle cast (S2, 24 frames), one Defense Curse (S3, 22 frames, its marks 147 / 191 /
  142), the tentacle 564 it raised 7.8 units from the character, its swing (A1, 10 frames). The Venom Lord's
  inferno, the same start and do functions (53 / 95) as Baal's: its flames live Param2 + level - 1 frames (7 + 15 -
  1 = 21; the takes 20 at the median, 21 at p90), the rule the client's DiabLight code was read to have (sim/diablo.py
  `missile_life`), so Baal's live 12 + 8 - 1 = 19;
- **[probe]** the alt-d terror probes of eight Baal kills (2026-10-08 to 10-11; rca/2026-10-14/baal-sim.md section
  1): about one look a second of his mode and place, the character's place, life and states, each tentacle and
  clone when first seen and when gone;
- **[inferred]** what neither settles, named where it is chosen.

**His acts** (the think: one draw over `WEIGHTS`, a chance each, at every think; the next think at the act's mode's
end plus `aidel` 12 [table]; his target the nearest body within the frame's radius 35 [code for the four read AIs,
notes-ai.md; that his think uses that search is inferred]):

- *nova* (Baal Nova, S3): NOVA_MISSILES missiles 555 in a ring from where he stands, NOVA_STEP a frame for `Range`
  40 frames (38 units), fire 218..243 a hit [table: EMin 50 + 24 a level to level 8, HitShift 8], one hit a body a
  ring [inferred, as Diablo's ring];
- *inferno* (Baal Inferno, the sequence SQ): from INFERNO_RELEASE frames into it one missile 554 every `calc3` 2
  frames for `calc2` (= Param1) 20 frames [table, read as the Venom Lord's: 5.2 flames a 12-frame cast, take], each
  flying at where his target stands when it is made, 19 frames [take rule above]; magic 400..432 x HitShift 5 / 256
  = 50..54 [table] taken as INFERNO_SHARE of it each NextDelay 4 frames of contact [probe, fitted: a character
  standing 14 to 19 units off lost 87 to 121 in the 1.5 s after a look saw him in SQ];
- *cold missiles* (Baal Cold Missiles, A1): COLD_MISSILES makers 589 in a fan over COLD_FAN at his target, 0.96 a
  frame for 50 frames, cold 83..103 a hit [table], once a body each; the fan is inferred (do-function 139 not read;
  the probe's falls after an A1 look are up to 176, more than one missile's 23 at 75 %); the trail 590 the maker
  drops is not played;
- *tentacles* (Baal Tentacle, S2): at its last frame [take] one tentacle, or two with TENTACLE_SECOND [probe: 36
  tentacles to 26 looks in S2], of the classes 564 or 565 [probe: 25 to 17], TENTACLE_NEAR units from his target in
  a direction of the roll [probe: first seen 4 to 11 units from the character, median 7]; it stands (Velocity 0)
  and strikes what comes within reach as any melee monster of the arena, and is gone TENTACLE_SECONDS after it
  rose [probe: nine of 28 lived 14.0 to 18.1 s, the rest were killed sooner];
- *Defense Curse* (S3): on every body within 12 units of his target for 875 frames [table: ln12, ln34 at level
  10]; its -95 % defence is not played (the arena's melee hits roll by the fit, not by defence);
- *teleport* (Baal Teleport, A1): to TELEPORT_NEAR units from his target, on the line from it to him [probe: two
  jumps of 14 and 18 units, landing 6.4 and 8.2 from the character];
- *walk* and *idle* (WL, NU): the rest of the probe's time.

Blood Mana (Mana Rift) is not cast: the probe never saw its state (114) on the character. He does not stagger [probe:
no look in his hit mode]. Once under CLONE_BELOW of his life he splits off his clone with CLONE_CHANCE [probe: seen
in three of seven kills, 10 to 16 s into fights of 29 to 40 s], CLONE_NEAR units from his target [probe: 6 to 10];
the clone thinks as he does and is gone with him [probe: one of three within 0.5 s of his death] [inferred].
"""

import csv
import json
import math
import random
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any


Point = tuple[float, float]
DATA = Path(__file__).parent / 'baal.json'
SOURCE = Path(__file__).parents[3] / 'pricing' / 'raw' / 'game-excel'
AIS = ('BaalCrab', 'BaalCrabClone')  # monstats `AI` of his rows and his clone's
TENTACLE_AI = 'BaalTentacle'
NOVA, INFERNO, TENTACLES, COLD, TELEPORT, CURSE = (
    'Baal Nova', 'Baal Inferno', 'Baal Tentacle', 'Baal Cold Missiles', 'Baal Teleport', 'Defense Curse',
)  # fmt: skip
CLONE_TELEPORT = 'Baal Clone Teleport'
WALK, IDLE = 'walk', 'idle'
# missiles.txt ids (baal.json `missiles`, checked by name in the tests)
NOVA_MISSILE, INFERNO_MISSILE, COLD_MAKER = 555, 554, 589
CLONE = 570  # monstats `baalclone`
CURSE_STATE = 113  # states.txt `defense_curse`

# -- his modes [take unless said] ------------------------------------------------------------------------------
# S3 22 (his Defense Curse, and the throne's Baal 37 times 21 to 22), S2 24 (his tentacle cast). A1 and the
# inferno's sequence: none in a take [inferred: A1 as Diablo's 16; SQ the stream's 20 frames after its first
# missile, a wind-up and a recovery as Diablo's SC has round his 40].
MODE_FRAMES = {'S3': 22, 'S2': 24, 'A1': 16, 'SQ': 40, 'S1': 16}
RELEASE = {'S3': 11, 'A1': 8}  # [inferred] half the mode; S2's tentacle at its last frame [take], SQ below
INFERNO_RELEASE = 2  # [take, the Venom Lord's same do-function: its first flame at frame 1 to 2 of the cast]
WALK_FRAMES = 12  # a walk: his next think `aidel` after he set out (sim/casters.py, every read AI)
IDLE_FRAMES = 10  # [inferred] the frame's short look (sim/casters.py NEAR_LOOK)

# -- what he does how often [probe] -----------------------------------------------------------------------------
# Looks at him in each mode over the eight kills (214 looks, one about every second, from his first sight to his
# death). The time a mode takes up over its frames is how often he begins it; after each act `aidel` 12 frames
# stand (NU), so the idle is what NU has left over.
LOOKS = {'NU': 79, 'A1': 38, 'S3': 36, 'S2': 26, 'SQ': 20, 'WL': 9, 'A2': 2}
DELAY = 12  # [table] `aidel(H)`
CURSE_SHARE = 0.2  # [probe, fitted] of his S3 acts the curse (it lasts 35 s; the curse was on in 77 % of the looks)
TELEPORT_SHARE = 0.03  # [probe] of his A1 acts the teleport: two jumps in 270 s of fights, the A1 looks 38
NOVA_MISSILES = 64  # [inferred] a ring's missiles, as Diablo's ring (sim/diablo.py RING_MISSILES, take)
STEP_PER_VEL = 0.048  # units a frame per point of `Vel` [take, sim/casters.py]
NOVA_STEP = 20 * STEP_PER_VEL  # [table] Vel 20
INFERNO_STEP = 21.0 / 19  # [probe, fitted] units a frame: his inferno reaches 21 units in its 19 frames (Vel 20 to
# MaxVel 40 with Accel 250 is between 18 and 36; the probe: falls of 87 to 121 at 14 to 19 units, 27 to 47 at 20 to 23)
INFERNO_SHARE = 0.18  # [probe, fitted] of a missile's points a contact (`rate`), every `NextDelay` 4 frames: a
# character standing 14 to 21 units off takes 94 a stream (each missile once), the probe's median fall of 94
COLD_MISSILES = 5  # [inferred] makers a cast
COLD_FAN = math.radians(40)  # [inferred] the fan they leave in, centred on the line to his target
TENTACLE_CLASSES = ((564, 25), (565, 17))  # [probe] the classes the probe saw, with how many
TENTACLE_SECOND = 0.4  # [probe] the chance a cast raises a second tentacle (36 to 26)
TENTACLE_NEAR = (4.0, 11.0)  # [probe] units from his target a tentacle rises
TENTACLE_SECONDS = 15.0  # [probe] how long a tentacle stands unless killed
TELEPORT_NEAR = 7.0  # [probe] units from his target he lands at
CLONE_BELOW = 0.65  # [probe, fitted] of his life: the clone came 25 to 44 % into the fight
CLONE_CHANCE = 0.5  # [probe] three kills in seven saw it (and one fight not won)
CLONE_NEAR = 8.0  # [probe] units from his target the clone appears
# Whom he aims at. None: the nearest body (the frame's search of the four read AIs, notes-ai.md), which in the arena,
# whose companions stand still by the character's first place, is a companion in 94 % or more of his thinks. A number:
# the character with that chance, else the nearest companion: Diablo's rule (sim/diablo.py CHARACTER_SHARE 0.82, his
# take). Neither is read of Baal; rca/2026-10-14/baal-sim.md section 5 plays both.
CHARACTER_SHARE: float | None = None


@cache
def data() -> dict[str, Any]:
    return json.loads(DATA.read_text(encoding='utf-8'))


def row(txt: int) -> dict[str, str] | None:
    return data()['monsters'].get(str(txt))


def is_baal(txt: int) -> bool:
    """A row of his AI or his clone's (544 `baalcrab`, 570 `baalclone`)."""
    found = row(txt)
    return found is not None and found.get('AI') in AIS


@cache
def casts_baals(txt: int) -> bool:
    """A row whose skills are his (the threat model is keyed on these, not on a name): any monstats row with Baal
    Inferno or Baal Nova, Uber Baal (709) among them."""
    return str(txt) in data()['casters']


def skill_level(txt: int, slot: int) -> int:
    """[table] SkNlvl + Hell's MonsterSkillBonus (7)."""
    found = row(txt) or data()['casters'].get(str(txt)) or {}
    return int(float(found.get(f'Sk{slot}lvl') or 0)) + int(data()['hell']['MonsterSkillBonus'])


def level_of(skill: str, txt: int = 544) -> int:
    found = row(txt) or data()['casters'].get(str(txt)) or {}
    slot = next((n for n in range(1, 9) if found.get(f'Skill{n}') == skill), 0)
    return skill_level(txt, slot) if slot else 1 + int(data()['hell']['MonsterSkillBonus'])


def _stepped(level: int, steps: list[float]) -> float:
    from inventory_tracking.combat.sim.casters import stepped

    return stepped(level, steps)


def skill_points(skill: str, level: int) -> dict[str, tuple[float, float]]:
    """[table] the damage a skill's missiles carry (their `Skill` column names it: missiles.txt has none of its own),
    by kind: the element (EMin + EMinLevN steps) << HitShift / 256, physical (MinDam + MinLevDamN) the same."""
    from inventory_tracking.combat.sim.casters import ELEMENTS

    found_row = data()['skills'][skill]

    def number(name: str) -> float:
        value = found_row.get(name)
        return float(value) if value not in (None, '') else 0.0

    shift = 2 ** number('HitShift') / 256
    found: dict[str, tuple[float, float]] = {}
    least = number('MinDam') + _stepped(level, [number(f'MinLevDam{n}') for n in range(1, 6)])
    most = number('MaxDam') + _stepped(level, [number(f'MaxLevDam{n}') for n in range(1, 6)])
    if most > 0:
        found['physical'] = (least * shift, max(most, least) * shift)
    kind = ELEMENTS.get(found_row.get('EType', ''))
    if kind is not None:
        least = number('EMin') + _stepped(level, [number(f'EMinLev{n}') for n in range(1, 6)])
        most = number('EMax') + _stepped(level, [number(f'EMaxLev{n}') for n in range(1, 6)])
        found[kind] = (least * shift, max(most, least) * shift)
    return found


def mean_points(skill: str, level: int) -> dict[str, float]:
    return {kind: (low + high) / 2 for kind, (low, high) in skill_points(skill, level).items()}


def missile(missile_id: int) -> dict[str, str]:
    return data()['missiles'][str(missile_id)]


def number(found: Mapping[str, str], name: str) -> float:
    value = found.get(name)
    return float(value) if value not in (None, '') else 0.0


def inferno_life(level: int) -> int:
    """[take rule] Param2 + level - 1 frames: 19 at level 8."""
    return int(number(missile(INFERNO_MISSILE), 'Param2')) + level - 1


def inferno_frames(skill_row: Mapping[str, str] | None = None) -> tuple[int, int]:
    """[table] (frames the stream lasts, frames between two missiles): `calc2` par1 (20) and `calc3` (2)."""
    found = skill_row or data()['skills'][INFERNO]
    return int(number(found, 'Param1')), int(found.get('calc3') or 2)


def inferno_births(start: int = 0) -> list[int]:
    """The frames of a cast begun at `start` its missiles are made at."""
    length, gap = inferno_frames()
    first = start + INFERNO_RELEASE
    return list(range(first, first + length, gap))


def inferno_reach(level: int = 8) -> float:
    return INFERNO_STEP * inferno_life(level)


def nova_life() -> int:
    return int(number(missile(NOVA_MISSILE), 'Range'))


def nova_reach() -> float:
    return NOVA_STEP * nova_life()


def cold_step() -> float:
    return number(missile(COLD_MAKER), 'Vel') * STEP_PER_VEL


def cold_life() -> int:
    return int(number(missile(COLD_MAKER), 'Range'))


def every(missile_id: int) -> int:
    return max(int(number(missile(missile_id), 'NextDelay')), 1)


def cold_headings(toward: float) -> list[float]:
    if COLD_MISSILES <= 1:
        return [toward]
    return [toward - COLD_FAN / 2 + COLD_FAN * k / (COLD_MISSILES - 1) for k in range(COLD_MISSILES)]


def ring_headings() -> list[float]:
    return [math.tau * k / NOVA_MISSILES for k in range(NOVA_MISSILES)]


def curse_reach_and_frames(level: int) -> tuple[float, int]:
    """[table] Defense Curse's radius (`ln12`) and length (`ln34`) at `level`."""
    found = data()['skills'][CURSE]
    p = [number(found, f'Param{n}') for n in range(1, 7)]
    return p[0] + p[1] * (level - 1), int(p[2] + p[3] * (level - 1))


# -- the think [probe] -------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Act:
    name: str
    skill: str  # '' for a walk or an idle
    mode: str


ACTS = (
    Act('nova', NOVA, 'S3'),
    Act('curse', CURSE, 'S3'),
    Act('inferno', INFERNO, 'SQ'),
    Act('cold', COLD, 'A1'),
    Act('teleport', TELEPORT, 'A1'),
    Act('tentacles', TENTACLES, 'S2'),
    Act(WALK, '', 'WL'),
    Act(IDLE, '', 'NU'),
)


@cache
def rates() -> dict[str, float]:
    """His acts a second: a mode's share of the looks over its frames (`LOOKS`, `MODE_FRAMES`), split between the
    acts of that mode; the idle's from the NU share the acts' `aidel` leaves."""
    total = sum(LOOKS.values())
    share = {mode: count / total for mode, count in LOOKS.items()}
    begun = {mode: share[mode] * 25 / MODE_FRAMES[mode] for mode in ('S3', 'S2', 'A1', 'SQ')}
    found = {
        'nova': begun['S3'] * (1 - CURSE_SHARE),
        'curse': begun['S3'] * CURSE_SHARE,
        'inferno': begun['SQ'],
        'cold': begun['A1'] * (1 - TELEPORT_SHARE),
        'teleport': begun['A1'] * TELEPORT_SHARE,
        'tentacles': begun['S2'],
        WALK: share['WL'] * 25 / WALK_FRAMES,
    }
    casting = sum(rate for name, rate in found.items() if name != WALK)
    found[IDLE] = max(share['NU'] - casting * DELAY / 25, 0.0) * 25 / IDLE_FRAMES
    return found


@cache
def weights() -> tuple[float, ...]:
    """The chance of each of ACTS at a think: its rate over all of them."""
    found = rates()
    total = sum(found.values())
    return tuple(found[act.name] / total for act in ACTS)


def choose(roll: random.Random) -> Act:
    pick, running = roll.random(), 0.0
    for act, weight in zip(ACTS, weights(), strict=True):
        running += weight
        if pick < running:
            return act
    return ACTS[-1]


def tentacle_class(roll: random.Random) -> int:
    total = sum(n for _, n in TENTACLE_CLASSES)
    pick = roll.random() * total
    for txt, n in TENTACLE_CLASSES:
        pick -= n
        if pick < 0:
            return txt
    return TENTACLE_CLASSES[-1][0]


def around(at: Point, near: float, roll: random.Random) -> Point:
    turn = roll.uniform(0, math.tau)
    return (at[0] + near * math.cos(turn), at[1] + near * math.sin(turn))


# -- played by sim/casters.py `Minds` ------------------------------------------------------------------------------
# `minds` is a Minds, `walker` a sim/monsters.py Walker with its `mind` (`Mind.ai` BAAL); not typed here, as sim/
# casters.py imports this module and this one it.

RELEASE_OF = {'nova': RELEASE['S3'], 'curse': 1, 'cold': RELEASE['A1'], 'teleport': RELEASE['A1']}
# [take] the curse's marks (147, 191, 142) the frame after S3 began; the tentacle at S2's last frame


def think(minds: Any, walker: Any, frame: int, targets: Any, index: int) -> None:
    """One think: his clone once he is low enough (Baal himself, not the clone), then one act of the draw at the
    nearest body (`index`, the frame's target search) or by CHARACTER_SHARE."""
    from inventory_tracking.combat.sim import casters

    mind = walker.mind
    rolls = minds.host.rolls[walker.unit]
    if CHARACTER_SHARE is not None:
        index = 0
        if len(targets) > 1 and rolls.random() >= CHARACTER_SHARE:
            index = min(range(1, len(targets)), key=lambda other: math.dist(walker.at, targets[other]))
    body = targets[index]
    if mind.row.get('AI') == AIS[0] and not mind.split and walker.health < CLONE_BELOW:
        mind.split = True
        if rolls.random() < CLONE_CHANCE:
            minds.summon(walker, CLONE, around(body, CLONE_NEAR, rolls), frame, None)
    act = choose(rolls)
    minds.thoughts.append((frame, walker.unit, act.name, index))
    if act.name == WALK:
        minds._set_walk(walker, frame, goal=body, held=casters.STOP)
        return
    if act.name == IDLE:
        minds._idle(walker, frame, IDLE_FRAMES)
        return
    skill = act.skill
    if act.name == 'teleport' and not any(mind.row.get(f'Skill{n}') == skill for n in range(1, 9)):
        skill = CLONE_TELEPORT  # the clone's own
    slot = next((n for n in range(1, 9) if mind.row.get(f'Skill{n}') == skill), 0)
    if not slot:
        minds._idle(walker, frame, IDLE_FRAMES)
        return
    frames = MODE_FRAMES[act.mode]
    mind.skill, mind.mode, mind.slot, mind.target = skill, act.mode, slot, index
    if act.name == 'inferno':
        mind.releases = inferno_births(frame)
    elif act.name == 'tentacles':
        mind.releases = [frame + frames - 1]
    else:
        mind.releases = [frame + RELEASE_OF[act.name]]
    walker.doing, walker.until, walker.lands, walker.aim = casters.CAST, frame + frames + mind.delay, -1, index
    minds.casts.append((frame, walker.unit, walker.txt, skill, body))


def release(minds: Any, walker: Any, frame: int, targets: Any) -> None:
    """What a frame of his cast lets go: a missile of the inferno at where his target stands now, the nova's ring,
    the cold missiles' fan, the tentacles, the curse, the teleport."""
    from inventory_tracking.combat.sim import casters

    mind = walker.mind
    index = mind.target
    body = targets[index]
    rolls = minds.host.rolls[walker.unit]
    level = mind.level.get(mind.slot, 1)
    skill = mind.skill
    toward = math.atan2(body[1] - walker.y, body[0] - walker.x)

    def made(missile_id: int, heading: float, step: float, life: int, points: Mapping[str, float], **more: Any) -> Any:
        return casters.Bolt(
            walker.unit, walker.txt, missile_id, walker.x, walker.y, math.cos(heading), math.sin(heading), step,
            frame, frame + life, dict(points), kills=False, aim=index, origin=walker.at, **more,
        )  # fmt: skip

    def rolled(name: str) -> dict[str, float]:
        return {kind: rolls.uniform(low, high) for kind, (low, high) in skill_points(name, level).items()}

    if skill == INFERNO:
        bolt = made(
            INFERNO_MISSILE, toward, INFERNO_STEP, inferno_life(level), rolled(INFERNO), rate=INFERNO_SHARE,
            every=every(INFERNO_MISSILE),
        )  # fmt: skip
        minds.bolts.append(bolt)
        minds.births.append((frame, walker.unit, walker.txt, INFERNO_MISSILE, walker.at, body, bolt.ends))
    elif skill == NOVA:
        once: set[int] = set()  # [inferred] one hit a body a ring, as Diablo's
        points = rolled(NOVA)
        for heading in ring_headings():
            minds.bolts.append(made(NOVA_MISSILE, heading, NOVA_STEP, nova_life(), points, struck=once))
        minds.births.append((frame, walker.unit, walker.txt, NOVA_MISSILE, walker.at, body, frame + nova_life()))
    elif skill == COLD:
        for heading in cold_headings(toward):
            minds.bolts.append(made(COLD_MAKER, heading, cold_step(), cold_life(), rolled(COLD)))
        minds.births.append((frame, walker.unit, walker.txt, COLD_MAKER, walker.at, body, frame + cold_life()))
    elif skill == TENTACLES:
        for _ in range(1 + (rolls.random() < TENTACLE_SECOND)):
            place = around(body, rolls.uniform(*TENTACLE_NEAR), rolls)
            if minds.host._footing(place):
                minds.summon(walker, tentacle_class(rolls), place, frame, round(TENTACLE_SECONDS * 25))
    elif skill == CURSE:
        radius, frames = curse_reach_and_frames(level)
        hexed = casters.Curse(CURSE, CURSE_STATE, frame + frames, {})
        hit = tuple(i for i, other in enumerate(targets) if math.dist(other, body) <= radius)
        for i in hit:
            minds.hexes[i] = hexed
        minds.cursed.append((frame, walker.unit, CURSE, hit))
        minds.flown.append((frame, frame + 10, walker.at, body, index == 0, False))
    elif skill in (TELEPORT, CLONE_TELEPORT):
        gap = math.dist(body, walker.at) or 1.0
        place = (
            body[0] + (walker.x - body[0]) / gap * TELEPORT_NEAR,
            body[1] + (walker.y - body[1]) / gap * TELEPORT_NEAR,
        )
        if gap > TELEPORT_NEAR and minds.host._footing(place):
            walker.x, walker.y = place


# -- baal.json ---------------------------------------------------------------------------------------------------

MONSTER_FIELDS = (
    'Id', '*hcIdx', 'BaseId', 'NameStr', 'AI', 'Velocity', 'Run', 'Level(H)', 'aidel(H)',
    *(f'aip{n}(H)' for n in range(1, 9)),
    *(f'Skill{n}' for n in range(1, 9)), *(f'Sk{n}mode' for n in range(1, 9)), *(f'Sk{n}lvl' for n in range(1, 9)),
    'A1MinD(H)', 'A1MaxD(H)', 'A1TH(H)', 'ResFi(H)', 'ResLi(H)', 'ResCo(H)', 'ResPo(H)', 'ResMa(H)', 'ResDm(H)',
)  # fmt: skip
SKILL_FIELDS = (
    'skill', 'srvstfunc', 'srvdofunc', 'srvmissilea', 'monanim', 'calc1', 'calc2', 'calc3',
    *(f'Param{n}' for n in range(1, 7)), 'MinDam', 'MaxDam', *(f'MinLevDam{n}' for n in range(1, 6)),
    *(f'MaxLevDam{n}' for n in range(1, 6)), 'HitShift', 'EType', 'EMin', 'EMax',
    *(f'EMinLev{n}' for n in range(1, 6)), *(f'EMaxLev{n}' for n in range(1, 6)), 'ELen', 'ELevLen1',
    'auratargetstate', 'auralencalc', 'aurarangecalc', 'aurastat1', 'aurastatcalc1',
)  # fmt: skip
MISSILE_FIELDS = (
    'Missile', '*ID', 'Vel', 'MaxVel', 'Accel', 'Range', 'Size', 'Pierce', 'CollideKill', 'LastCollide', 'NextHit',
    'NextDelay', 'DamageRate', 'HitShift', 'Param1', 'Param2', 'pSrvHitFunc', 'sHitPar1', 'Skill', 'SubMissile1',
)  # fmt: skip
CASTER_SKILLS = (INFERNO, NOVA)


def _rows(source: Path, name: str) -> list[dict[str, str]]:
    with (source / f'{name}.txt').open(newline='', encoding='utf-8', errors='replace') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def build(source: Path = SOURCE) -> dict[str, Any]:
    """baal.json: the monstats rows of his AI, his clone's and his tentacles', every row that casts his skills, the
    skills, their server missiles and sub-missiles, Hell's skill bonus."""
    pick = lambda found, fields: {name: found[name] for name in fields if found.get(name)}  # noqa: E731
    monstats = _rows(source, 'monstats')
    monsters = {r['*hcIdx']: pick(r, MONSTER_FIELDS) for r in monstats if r['AI'] in (*AIS, TENTACLE_AI)}
    casters = {
        r['*hcIdx']: pick(r, MONSTER_FIELDS)
        for r in monstats
        if any(r.get(f'Skill{n}') in CASTER_SKILLS for n in range(1, 9))
    }
    named = {r['skill']: r for r in _rows(source, 'skills')}
    rows = (*monsters.values(), *casters.values())
    wanted = {m[f'Skill{n}'] for m in rows for n in range(1, 9) if m.get(f'Skill{n}')}
    skills = {name: pick(named[name], SKILL_FIELDS) for name in sorted(wanted) if name in named}
    by_name = {r['Missile']: r for r in _rows(source, 'missiles')}
    names = {s.get('srvmissilea') for s in skills.values()}
    names |= {by_name[n].get('SubMissile1') for n in list(names) if n in by_name}
    missiles = {by_name[n]['*ID']: pick(by_name[n], MISSILE_FIELDS) for n in sorted(filter(None, names))}
    hell = next(r for r in _rows(source, 'difficultylevels') if r['Name'] == 'Hell')
    return {
        'source': 'pricing/raw/game-excel (monstats, skills, missiles, difficultylevels); combat/sim/baal.py build',
        'monsters': monsters,
        'casters': casters,
        'skills': skills,
        'missiles': missiles,
        'hell': {'MonsterSkillBonus': hell['MonsterSkillBonus']},
    }


if __name__ == '__main__':
    built = build(Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCE)
    DATA.write_text(json.dumps(built, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(
        f'{DATA}: {len(built["monsters"])} monsters, {len(built["casters"])} casters, {len(built["skills"])} skills, '
        f'{len(built["missiles"])} missiles'
    )
