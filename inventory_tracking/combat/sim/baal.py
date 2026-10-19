"""Baal in the Worldstone Chamber (monstats `baalcrab` 544, AI BaalCrab) and his clone (`baalclone` 570,
AI BaalCrabClone) as the arena plays them: his think, casts, missiles, tentacles and clone. sim/casters.py
`Minds` plays him (`BAAL`); this module holds his rules and rows (baal.json, written by `build` below).

His think is read in the client (`ai_d2_ai_135_baalcrab_think` 0x1404B9E80, the clone's 0x1404BA810; it
follows D2MOO's AiBaal.cpp but for teleport and target score): every THINK_FRAMES a target by score (`aim`)
and one weighted draw over 16 acts (`weights`). Sources are tagged [code], [table], [take] (Throne take
20261011T001816Z-131), [probe] (eight Baal kills, rca/2026-10-14/baal-sim.md) and [inferred].
rca/2026-10-14/re/baal-ai.md has the reading; the per-act rules in full: combat/history/sim-baal.md.
"""

import csv
import json
import math
import random
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from inventory_tracking.levels.geometry import Point


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
NOVA_MISSILE, INFERNO_MISSILE, COLD_MAKER, COLD_TRAIL = 555, 554, 589, 590
CLONE = 570  # monstats `baalclone`
CURSE_STATE = 113  # states.txt `defense_curse`

# -- his modes ---------------------------------------------------------------------------------------------------
# S3 and S2 [take]; A1 and A2 [inferred: Diablo's]; SQ his inferno's sequence [table: monseq], held to the stream's end.
MODE_FRAMES = {'S3': 22, 'S2': 24, 'A1': 16, 'A2': 20, 'SQ': 24}
RELEASE = {'S3': 11, 'A1': 8}  # [inferred] half the mode; S2's tentacles at its last frame [take], SQ below
INFERNO_RELEASE = 11  # [table] the do event of seq_baalinferno
INFERNO_GAP = 1  # [take, Diablo's same do-function: one missile a frame though calc3 is 2]
THINK_FRAMES = 25  # [code] the next think at frame + 25 after every think
DELAY = 12  # [table] `aidel(H)`: what the arena's companions of the read AIs wait; his own think is THINK_FRAMES
STEP_PER_VEL = 0.048  # units a frame per point of `Vel` [take, sim/casters.py]
NOVA_MISSILES = 64  # [code] ai_d2_missile_nova_ring: 64 entries of its offset tables
NOVA_STEP = 20 * STEP_PER_VEL  # [table] Vel 20
INFERNO_STEP = 21.0 / 19  # [probe, fitted] units a frame: his inferno reaches 21 units in its 19 frames
INFERNO_SHARE = 0.18  # [probe, fitted] of a missile's points a contact (`rate`), every `NextDelay` 4 frames
TENTACLE_TRIES = (4, 6)  # [code] roll % 3 + 2 + difficulty (Hell 2)
TENTACLE_SPREAD = 9  # [code] roll % 18 - 9 on each axis from his target
TENTACLE_CLASSES = (564, 565)  # [code + D2MOO] the chain's index difficulty + roll % 2: Hell's two, evenly
TENTACLE_SECONDS = 15.0  # [probe] how long a tentacle stands unless killed (its own AI not read)
CLONE_SPREAD = 12  # [code] roll % 24 - 12 on each axis from his target
CLONE_SHARE = 1 / 3  # [code] of his life and of his most life
ROOM = 40  # [table + code] a preset level's rooms are 8 x 8 tiles of 5 sub-tiles
CHAMBER = (15000, 5760)  # [table] level 132's origin in sub-tiles (levels.txt OffsetX 3000, OffsetY 1152, x 5)
PLACE = (15135, 5920)  # [probe] where he stands in the Chamber (boss_lairs.py at (135, 160))
TELEPORT_TRIES = 20  # [code]
REACH = 4.5  # [inferred] his melee: monstats2 MeleeRng 3 plus half his SizeX 3, as Diablo's (sim/diablo.py)
SIZE = 1.0  # [inferred] the size the AI's distance is taken less of, as Diablo's
NEAR, FAR = 25.0, 35.0  # [code] beyond NEAR no nova and teleport 30; beyond FAR no cold missiles and the walk 15
HOME_MEDIUM, HOME_FAR = 75.0, 100.0  # [code] his target that far from his home point
THREAT_FRAMES = 250  # [code] ai_d2_primeevil_threat_add: the threat state lapses 250 frames after the last hit
THREAT_REACH = 50.0  # [code + table] the distance factor's R (`aidist` empty: 50): no threat weight at 50 and beyond
IN_MELEE, IN_SIGHT = 500, 375  # [code] the score's range terms
CURSE_BEST = 60  # [code] a best score above this: the curse's weight 70
PRIME_EVIL_LIFE = 293800.0  # [table] his life in the arena (points_of(544, 132)), for the threat's points
# The acts by the draw's index [code: the jump table 0x1404B9E38]
ACTIONS = (
    'none', IDLE, 'approach', 'circle', 'roam', 'home', 'approach', 'none',
    'curse', 'tentacles', 'smash', 'nova', 'inferno', 'cold', 'teleport', 'clone',
)  # fmt: skip
CLONE_WALKS = (7, 9, 14, 15)  # [code] the clone's draws of these walk (2)


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
    """[table] the damage by kind a skill's missiles carry (missiles.txt `Skill` names it), `<< HitShift / 256`."""
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


def inferno_frames(skill_row: Mapping[str, str] | None = None) -> int:
    """[table + code] the frames from the sequence's start to the stream's end: `calc2` par1 (20)."""
    found = skill_row or data()['skills'][INFERNO]
    return int(number(found, 'Param1'))


def inferno_births(start: int = 0) -> list[int]:
    """The frames of a cast begun at `start` its missiles are made at: from the do event to the stream's end."""
    return list(range(start + INFERNO_RELEASE, start + inferno_frames() + 1, INFERNO_GAP))


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


def trail_step() -> float:
    return number(missile(COLD_TRAIL), 'Vel') * STEP_PER_VEL


def trail_life() -> int:
    return int(number(missile(COLD_TRAIL), 'Range'))


def every(missile_id: int) -> int:
    return max(int(number(missile(missile_id), 'NextDelay')), 1)


def cold_missiles(origin: Point, heading: float) -> list[tuple[int, Point, Point, float, int]]:
    """[code + D2MOO] the missiles of one cast of his cold missiles let go from `origin` at `heading`: (frames after
    the release it is made, where, its (dx, dy), its step, its life). The maker first; then, each frame it enters a new
    sub-tile, two trails from where it is, one each way across its line."""
    dx, dy = math.cos(heading), math.sin(heading)
    step, life = cold_step(), cold_life()
    found: list[tuple[int, Point, Point, float, int]] = [(0, origin, (dx, dy), step, life)]
    side, side_life = trail_step(), trail_life()
    cell = (math.floor(origin[0]), math.floor(origin[1]))
    for frame in range(1, life):
        at = (origin[0] + dx * step * frame, origin[1] + dy * step * frame)
        now = (math.floor(at[0]), math.floor(at[1]))
        if now != cell:
            cell = now
            found.append((frame, at, (-dy, dx), side, side_life))
            found.append((frame, at, (dy, -dx), side, side_life))
    return found


def ring_headings() -> list[float]:
    return [math.tau * k / NOVA_MISSILES for k in range(NOVA_MISSILES)]


def curse_reach_and_frames(level: int) -> tuple[float, int]:
    """[table] Defense Curse's radius (`ln12`) and length (`ln34`) at `level`."""
    found = data()['skills'][CURSE]
    p = [number(found, f'Param{n}') for n in range(1, 7)]
    return p[0] + p[1] * (level - 1), int(p[2] + p[3] * (level - 1))


def less_size(a: Point, b: Point, size: float = SIZE) -> float:
    """[code] the AI's distance less the size: max + min / 2 of the axes, each less `size` (not below 0)."""
    dx, dy = max(abs(a[0] - b[0]) - size, 0.0), max(abs(a[1] - b[1]) - size, 0.0)
    return max(dx, dy) + min(dx, dy) / 2


def ai_distance(a: Point, b: Point) -> float:
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    return max(dx, dy) + min(dx, dy) / 2


def distance_factor(distance: float, reach: float = THREAT_REACH) -> float:
    """[code] ai_d2_ai_distance_factor in percent: 100 near, 25 at half the reach, 0 at it."""
    c = 100 * (reach - min(distance, reach)) / reach
    return min(max(c * 100 / (295 - 2 * c), 0.0), 100.0)


# -- the think [code] ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Sight:
    """What his roll weighs of his target (ai_d2_ai_baal_decide)."""

    melee: bool
    seen: bool
    away: float
    life: float = 1.0
    target_life: float = 1.0
    chilled: bool = False
    candidates: int = 1
    best: float = 0.0
    clones: int = 0
    medium: bool = False
    far: bool = False
    area_skill: bool = False
    players: int = 1


def weights(sight: Sight) -> list[int]:
    """[code] the 16 weights of his roll in Hell (ai_d2_ai_baal_decide 0x1404B8760 and _in_sight 0x1404B8540)."""
    lost = 100 - round(sight.life * 100)
    if sight.melee:
        w = [0, 50, 0, 0, 0, 0, 0, 0, 20, 30, 150, 10, 10, 70, 40, 0]
        if sight.target_life * 100 < 33:
            w[10] = 200
        w[1] += lost
        if sight.chilled:
            w[8] = w[13] = w[11] = 0
        if not sight.seen:
            w[11] = w[13] = 0
        return w
    if not sight.seen:
        w = [0, 100, 20, 20, 20, 0, 20, 0, 80, 70, 0, 0, 0, 0, 0, 0]
        w[1] += lost
        if sight.candidates < 2:
            w[2], w[10] = 45, 25
        if sight.medium:
            w[2] = w[6] = 0
            w[3] = 35
            w[11] = w[13] = 25
        if sight.far:
            w[5] = 60
        return w
    w = [0, 100 + lost, 5, 5, 5, 0, 5, 0, 40, 40, 0, 70, 80, 60, 20, max(10 * (2 - sight.clones), 0)]
    if sight.away > FAR:
        w[6], w[13] = 15, 0
    if sight.away > NEAR:
        w[14], w[11] = 30, 0
    if sight.candidates < 2:
        w[11] -= 10
    elif sight.candidates > 3:
        w[13] += 25
    if sight.best > CURSE_BEST:
        w[8] = 70
    if sight.candidates < 2 and sight.players < 2:
        w[8] = 0
    if sight.area_skill and not sight.medium:
        w[11] += 10
        w[14] += 15
        w[6] += 30
    elif sight.medium:
        w[2], w[3] = 0, 25
        w[14] += 35
        w[6] += 25
    if sight.far:
        w[5] = 60
    return w


def choose(found: Sequence[int], roll: random.Random) -> int:
    """[code] ai_d2_ai_pick_weighted16: the roll over the sum, the first index whose running sum passes it; 1 when
    none does. A negative weight counts as it is."""
    total = sum(found)
    pick = roll.randrange(total) if total > 0 else 0
    running = 0
    for index, weight in enumerate(found):
        running += weight
        if pick < running:
            return index
    return 1


def chances(sight: Sight) -> dict[str, float]:
    """The chance of each act at a think (the draw's weights by name), for a model that prices what is to come."""
    found = weights(sight)
    total = sum(w for w in found if w > 0) or 1
    named: dict[str, float] = {}
    for index, weight in enumerate(found):
        if weight > 0:
            named[ACTIONS[index]] = named.get(ACTIONS[index], 0.0) + weight / total
    return named


def rates(distance: float = 16.0, candidates: int = 4, life: float = 0.5, struck: bool = True) -> dict[str, float]:
    """His acts a second for a character `distance` units off, in sight, out of melee, with `candidates` bodies about,
    his life share `life`, `struck`: the character hitting him (best score over 60)."""
    sight = Sight(
        melee=distance <= REACH, seen=True, away=less_size((0.0, 0.0), (distance, 0.0)), life=life,
        candidates=candidates, best=CURSE_BEST + 1 if struck else 0.0,
    )  # fmt: skip
    return {name: chance * 25 / THINK_FRAMES for name, chance in chances(sight).items()}


def tentacle_class(roll: random.Random) -> int:
    return roll.choice(TENTACLE_CLASSES)


def room_of(at: Point, home: Point) -> tuple[float, float]:
    """[table + code] the corner of the 40 x 40 room `at` stands in, the rooms laid from the Chamber's origin as his
    place `home` stands in it (the arena's ground keeps the game's axes)."""
    origin = (home[0] - (PLACE[0] - CHAMBER[0]), home[1] - (PLACE[1] - CHAMBER[1]))
    return (
        origin[0] + math.floor((at[0] - origin[0]) / ROOM) * ROOM,
        origin[1] + math.floor((at[1] - origin[1]) / ROOM) * ROOM,
    )


def teleport_spot(at: Point, home: Point, roll: random.Random, footing: Any) -> Point | None:
    """[code] a random point of his room, 1 to 39 sub-tiles in from its corner on each axis, where he can stand: 20
    tries, else None."""
    corner = room_of(at, home)
    for _ in range(TELEPORT_TRIES):
        spot = (corner[0] + 1 + roll.randrange(ROOM - 1), corner[1] + 1 + roll.randrange(ROOM - 1))
        if footing(spot):
            return spot
    return None


# -- whom he aims at [code] ------------------------------------------------------------------------------------------


def aim(walker: Any, targets: Sequence[Point], frame: int, sees: Any) -> tuple[int, float]:
    """[code] ai_d2_ai_baal_find_target: (his target's index, the best score), by the parts of
    ai_d2_ai_baal_target_score the arena knows; the character (scored first, keeps a tie) adds its threat times the
    distance factor. The rest of the score is taken as equal for all [inferred]."""
    mind = walker.mind
    best, chosen = -1.0, 0
    for index, body in enumerate(targets):
        d = math.dist(walker.at, body)
        score = (IN_MELEE if d <= REACH else IN_SIGHT if sees(walker, body) else 0) / 22
        if index == 0:
            score += mind.threat * distance_factor(ai_distance(walker.at, body)) / 100
        score = max(score, 1.0)
        if score > best:
            best, chosen = score, index
    return chosen, best


def _threat(walker: Any, frame: int) -> None:
    """[code] the character's threat state on him: the points it took off him since the state began, gone
    THREAT_FRAMES after its last hit. The arena's strikes on him are the character's alone."""
    mind = walker.mind
    if walker.struck < 0 or frame - walker.struck > THREAT_FRAMES:
        mind.threat = 0.0
    else:
        share = CLONE_SHARE if walker.txt == CLONE else 1.0
        mind.threat += max(mind.seen_health - walker.health, 0.0) * PRIME_EVIL_LIFE * share
    mind.seen_health = walker.health


# -- played by sim/casters.py `Minds` ------------------------------------------------------------------------------
# `minds` is a Minds, `walker` a sim/monsters.py Walker with its `mind` (`Mind.ai` BAAL); not typed here, as sim/
# casters.py imports this module and this one it.


def think(minds: Any, walker: Any, frame: int, targets: Any, index: int) -> None:
    """One think [code]: his target by the score (`index`, the frame's nearest, is not his rule), the draw, the act;
    the next think THINK_FRAMES on whatever the act."""
    from inventory_tracking.combat.sim import casters

    del index
    mind = walker.mind
    host = minds.host
    rolls = host.rolls[walker.unit]
    if mind.home is None:
        mind.home = walker.at
    _threat(walker, frame)
    index, best = aim(walker, targets, frame, host._sees)
    body = targets[index]
    clone = mind.row.get('AI') == AIS[1]
    sight = Sight(
        melee=math.dist(walker.at, body) <= REACH,
        seen=host._sees(walker, body),
        away=less_size(walker.at, body),
        life=walker.health,
        candidates=len(targets),
        best=best,
        clones=mind.clones,
        medium=ai_distance(body, mind.home) > HOME_MEDIUM,
        far=ai_distance(body, mind.home) > HOME_FAR,
    )
    action = choose(weights(sight), rolls)
    if clone and action in CLONE_WALKS:
        action = 2
    act = ACTIONS[action]
    minds.thoughts.append((frame, walker.unit, act, index))
    until = frame + THINK_FRAMES
    if act == 'approach':
        gap = math.dist(walker.at, body) or 1.0
        reach = min(gap, 12.0)  # [code] up to 12 toward the target
        goal = (walker.x + (body[0] - walker.x) / gap * reach, walker.y + (body[1] - walker.y) / gap * reach)
        minds._set_walk(walker, frame, goal=goal, held=casters.STOP)
    elif act == 'circle':
        side = 1 if rolls.randrange(256) < 0x80 else -1
        minds._set_walk(walker, frame, goal=casters.turned(body, walker.at, casters.CIRCLE_STEP, side))
    elif act == 'roam':
        # [code + D2MOO WalkCloseToUnit] 16 on one axis, up to 16 on the other, the signs by the roll
        first, other = 16, rolls.randrange(16)
        dx, dy = (first, other) if rolls.getrandbits(1) else (other, first)
        dx, dy = dx * rolls.choice((-1, 1)), dy * rolls.choice((-1, 1))
        minds._set_walk(walker, frame, goal=(walker.x + dx, walker.y + dy))
    elif act == 'home':
        minds._set_walk(walker, frame, goal=mind.home)
    elif act == 'smash':
        mind.mode, mind.target = 'A2', index
        walker.doing, walker.aim = casters.STRIKE, index
        walker.lands = frame + max(round(casters.BLOW_SHARE * MODE_FRAMES['A2']), 1)
    elif act in ('nova', 'inferno', 'cold', 'curse', 'tentacles', 'teleport'):
        _cast(minds, walker, frame, targets, index, act)
    elif act == 'clone':
        _clone(minds, walker, frame, body)
        minds._idle(walker, frame, THINK_FRAMES)
    else:
        minds._idle(walker, frame, THINK_FRAMES)
    walker.until = until


SKILL_OF = {'nova': NOVA, 'inferno': INFERNO, 'cold': COLD, 'curse': CURSE, 'tentacles': TENTACLES}
ACT_MODE = {'nova': 'S3', 'inferno': 'SQ', 'cold': 'A1', 'curse': 'S3', 'tentacles': 'S2', 'teleport': 'A1'}


def _cast(minds: Any, walker: Any, frame: int, targets: Any, index: int, act: str) -> None:
    from inventory_tracking.combat.sim import casters

    mind = walker.mind
    skill = SKILL_OF.get(act, TELEPORT)
    if act == 'teleport':
        if not any(mind.row.get(f'Skill{n}') == skill for n in range(1, 9)):
            skill = CLONE_TELEPORT  # the clone's own (it never draws it: CLONE_WALKS)
        spot = teleport_spot(walker.at, mind.home or walker.at, minds.host.rolls[walker.unit], minds.host._footing)
        if spot is None:
            minds._idle(walker, frame, THINK_FRAMES)  # [code] no spot in 20 tries: action 0, an idle
            return
        mind.goal = spot
    slot = next((n for n in range(1, 9) if mind.row.get(f'Skill{n}') == skill), 0)
    if not slot:
        minds._idle(walker, frame, THINK_FRAMES)
        return
    mode = ACT_MODE[act]
    mind.skill, mind.mode, mind.slot, mind.target = skill, mode, slot, index
    if act == 'inferno':
        mind.releases = inferno_births(frame)
    elif act == 'tentacles':
        mind.releases = [frame + MODE_FRAMES['S2'] - 1]
    elif act == 'curse':
        mind.releases = [frame + 1]  # [take] the curse's marks the frame after S3 began
    else:
        mind.releases = [frame + RELEASE[mode]]
    walker.doing, walker.lands, walker.aim = casters.CAST, -1, index
    minds.casts.append((frame, walker.unit, walker.txt, skill, targets[index]))


def _clone(minds: Any, walker: Any, frame: int, body: Point) -> None:
    """[code] ai_d2_ai_baal_spawn_clone: nothing while a clone of his lives; else one at his target + (-12..11) on
    each axis with a third of his life."""
    mind = walker.mind
    if any(other.txt == CLONE and other.health > 0 for other in minds.host.walkers.values()):
        return
    rolls = minds.host.rolls[walker.unit]
    at = (
        body[0] + rolls.randrange(2 * CLONE_SPREAD) - CLONE_SPREAD,
        body[1] + rolls.randrange(2 * CLONE_SPREAD) - CLONE_SPREAD,
    )
    if not minds.host._footing(at):
        return
    minds.summon(walker, CLONE, at, frame, None, share=walker.health * CLONE_SHARE, most=CLONE_SHARE)
    mind.clones += 1


def release(minds: Any, walker: Any, frame: int, targets: Any) -> None:
    """What a frame of his cast lets go: a missile of the inferno at where his target stands now, the nova's ring,
    the cold missiles' maker, the tentacles, the curse, the teleport."""
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
        # [code] one maker at his target's point, shedding the trails across its line as it goes (Bolt `sides`)
        bolt = made(
            COLD_MAKER, toward, cold_step(), cold_life(), rolled(COLD), sides=COLD_TRAIL, side_step=trail_step(),
            side_life=trail_life(),
        )  # fmt: skip
        minds.bolts.append(bolt)
        minds.births.append((frame, walker.unit, walker.txt, COLD_MAKER, walker.at, body, frame + cold_life()))
    elif skill == TENTACLES:
        txt = tentacle_class(rolls)
        for _ in range(rolls.randint(*TENTACLE_TRIES)):
            place = (
                body[0] + rolls.randrange(2 * TENTACLE_SPREAD) - TENTACLE_SPREAD,
                body[1] + rolls.randrange(2 * TENTACLE_SPREAD) - TENTACLE_SPREAD,
            )
            if minds.host._footing(place):
                minds.summon(walker, txt, place, frame, round(TENTACLE_SECONDS * 25))
    elif skill == CURSE:
        radius, frames = curse_reach_and_frames(level)
        hexed = casters.Curse(CURSE, CURSE_STATE, frame + frames, {})
        hit = tuple(i for i, other in enumerate(targets) if math.dist(other, body) <= radius)
        for i in hit:
            minds.hexes[i] = hexed
        minds.cursed.append((frame, walker.unit, CURSE, hit))
        minds.flown.append((frame, frame + 10, walker.at, body, index == 0, False))
    elif skill in (TELEPORT, CLONE_TELEPORT) and mind.goal is not None:
        walker.x, walker.y = mind.goal
        mind.goal = None


# -- baal.json ---------------------------------------------------------------------------------------------------

MONSTER_FIELDS = (
    'Id', '*hcIdx', 'BaseId', 'NameStr', 'AI', 'Velocity', 'Run', 'Level(H)', 'aidel(H)',
    *(f'aip{n}(H)' for n in range(1, 9)),
    *(f'Skill{n}' for n in range(1, 9)), *(f'Sk{n}mode' for n in range(1, 9)), *(f'Sk{n}lvl' for n in range(1, 9)),
    'A1MinD(H)', 'A1MaxD(H)', 'A1TH(H)', 'A2MinD(H)', 'A2MaxD(H)', 'A2TH(H)',
    'ResFi(H)', 'ResLi(H)', 'ResCo(H)', 'ResPo(H)', 'ResMa(H)', 'ResDm(H)',
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
    pick = lambda found, fields: {name: found[name] for name in fields if found.get(name)}  # ruff: ignore[lambda-assignment]
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
