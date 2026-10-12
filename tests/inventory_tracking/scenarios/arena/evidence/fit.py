"""The fitted table of the monster model (combat/sim/monsters.py), written from the TRAIN half of the
evidence and from nothing else:

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.evidence.fit
        [--excel pricing/raw/game-excel]

reads `evidence.json` beside this file and writes `inventory_tracking/combat/data/monsters_fit.json`.
No number of that file is typed by hand: each is a figure of `evidence.json['train']` (or of
`['types'][txt][...]['train']`) or is counted from such figures here, and carries its `n`. The check
half is not read. A type under the evidence's own thresholds (`evidence.json['thresholds']`: 30 s
within reach or 10 sole blows for a melee type, 20 shots for a shooter, 30 s in each cell of whom
a type goes for; OWN_CHANCE times the 20 shots for a shooter's own chance to take life) has no row
and the model uses the pooled one.

What is decided here, not measured (each said where it is used):

- **the chance that a swing takes life is the middle of the evidence's two bounds**: `low` counts the
  drops put on that monster alone, `high` those it shares with other suspects too. A shared drop
  has two suspects or more, so the truth is under `high`; the middle is taken. For a shot the bounds
  are seven times apart (a drop with the missiles of several shooters near is a hit of each), so
  there the chance is counted in points (`shot_row`); with it a shooter in sight takes 0.56 points
  a second where the train half shows 0.42 to 0.70, with the middle of the counts it would take 1.3;
- **the figures with the character standing still** (`stood`) are used for those chances, because the
  model plays the character's moves itself (a blow lands only if the target is still in reach, a
  missile flies to where its target stood): the chance fitted here is what is left: a miss, a block,
  a blow the character's own protection took. They cannot be told apart. A melee type has 16 to 67
  swings with the character standing, too few for a chance of its own, so its chance is that of
  all its whole swings at the character raised by the pooled share of standing over all (`moving`);
- **a swing cut short** lasts a whole number of frames under half the swing, each as likely; the
  pause after a swing is what makes the swings a second come out as measured;
- **the spread of a blow's size** is drawn through the quantiles the evidence gives of the drops put
  on one monster alone (the median, the 90th and 99th percentile, the largest), straight lines in
  the logarithm between them, from the smallest drop the recorder writes (hurts.HURT_LEAST) up;
  the model uses it over its mean, so the mean blow stays the game table's;
- **the reach beyond the body's**: the swings begun at the character per monster-second in each band
  of distance over the same within 3.5 units, never rising with the distance;
- **a death nova twice the size**: the share of the train half's nova drops that are in the evidence's
  list of drops over 300 points, which one ring's points do not reach at any level seen.

Missile speeds are not in the evidence. With the game's tables at hand (`--excel`: monstats `MissA1`
and missiles `Vel`, as pricing/raw/game-excel holds them) each tabled shooter has the speed of its
first attack's missile, and the others the mean of those by shots; without them the speeds of the
file already written are kept.
"""

import argparse
import csv
import itertools
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from inventory_tracking.combat.hurts import HURT_LEAST


HERE = Path(__file__).parent
REPO = HERE.parents[4]
EVIDENCE = HERE / 'evidence.json'
FITTED = REPO / 'inventory_tracking' / 'combat' / 'data' / 'monsters_fit.json'
EXCEL = REPO / 'pricing' / 'raw' / 'game-excel'
GAME_RATE = 25.0  # frames a second (combat/timeline.py)
STRIKE_FRAMES = 16  # the model's swing where no length was measured (sim/monsters.py)
BODY = 3.5  # units: the evidence counts time "in reach" within this (rates.py MODEL_REACH)
FAR = 12.0  # units: a striker further off is no suspect of a drop (hurts.SUSPECT_REACH): the tail ends here
# Times the evidence's 20 shots: a shooter with this many has a chance of its own that a missile takes
# life (a chance of one or two in a hundred is not seen in fewer); the others use the pooled one.
OWN_CHANCE = 10
NOVA_MISSILE = '194'  # missiles.txt `coldunique`, as evidence.json keys the nova drops
NOVA_REACH = ('0-4', '4-8', '8-12')  # the bands of the deaths table in which the nova takes life


def middle(low: float | None, high: float | None) -> float | None:
    return None if low is None or high is None else round((low + high) / 2, 4)


def cut_frames(frames: int) -> float:
    """The mean length of a swing cut short: 1 to under half of it, each as likely."""
    return (1 + max(frames // 2 - 1, 1)) / 2


def rest(rate: float, frames: int, cut: float) -> float:
    """Frames between the end of a swing and the next, so that `rate` swings a second come out."""
    return round(max(GAME_RATE / rate - (1 - cut) * frames - cut * cut_frames(frames), 0.0), 2)


def melee_row(found: Mapping[str, Any], frames: int, mode: str | None, moving: float = 1.0) -> dict[str, Any]:
    """A row of swings. `moving` is 1 for the pooled row, whose chance to take life is that of the
    swings through which the character stood still; a type has too few of those (16 to 67), so its
    chance is that of all its whole swings at the character times `moving`: the pooled chance with
    the character standing over the pooled chance of all."""
    cut = found['cut_share']
    every = middle(found['hit_low'], found['hit_high'])
    stood = middle(found['stood_hit_low'], found['stood_hit_high'])
    assert every is not None
    return {
        'name': found['name'],
        'rate': {'value': found['swings_per_second'], 'n_swings': found['swings'], 'n_seconds': found['seconds']},
        'cut': {'value': cut, 'n': found['runs']},
        'frames': {'value': frames, 'mode': mode},
        'rest': rest(found['swings_per_second'], frames, cut),
        'takes_life': {
            'value': stood if moving == 1.0 else round(every * moving, 4),
            'low': found['hit_low'],
            'high': found['hit_high'],
            'n': found['whole_aimed'],
            'stood': stood,
            'stood_low': found['stood_hit_low'],
            'stood_high': found['stood_hit_high'],
            'n_stood': found['stood'],
        },
    }


def melee(evidence: Mapping[str, Any]) -> dict[str, Any]:
    least = evidence['thresholds']
    pooled = evidence['train']['melee_all']
    whole = melee_row(pooled, STRIKE_FRAMES, None)
    life = whole['takes_life']
    moving = life['value'] / middle(life['low'], life['high'])
    types = {}
    for txt, row in evidence['types'].items():
        found = row['melee']['train']
        if not found or int(txt) in pooled['left_out']:
            continue
        if found['seconds'] < least['enough_seconds'] and found['blows'] < least['enough_blows']:
            continue
        mode = min(found['usual_frames'], key=int)  # the lowest attack mode the type was seen in
        types[txt] = melee_row(found, found['usual_frames'][mode], mode, moving)
    return {
        'pooled': whole,
        'moving': round(moving, 4),
        'types': dict(sorted(types.items(), key=lambda item: int(item[0]))),
        'idle': sorted(pooled['left_out']),
    }


def tail(evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    """By band beyond BODY: the share of thinks that begin a swing at the character from there."""
    bands = evidence['train']['reach_curve']
    body = [band for band in bands if band['to'] <= BODY]
    base = sum(band['whole_aimed'] for band in body) / sum(band['seconds'] for band in body)
    found, share = [], 1.0
    for band in bands:
        if band['from'] < BODY or band['to'] > FAR:
            continue
        share = min(share, band['whole_aimed'] / band['seconds'] / base)
        found.append(
            {'to': band['to'], 'share': round(share, 4), 'n': band['whole_aimed'], 'n_seconds': band['seconds']}
        )
    return found


def cell(seconds: Mapping[str, float]) -> dict[str, Any]:
    named = seconds['hero'] + seconds['friend']
    return {'value': round(seconds['hero'] / named, 4) if named else None, 'n_seconds': round(named, 1)}


def targets(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """The share of the time a monster's path record named the character, of the time it named the
    character or a companion, by which of the two was nearer: pooled over the types the arena plays
    hand to hand (not ranged by the threat table), and per type with enough seconds in both cells."""
    least = evidence['thresholds']['enough_seconds']
    sums = {'hero': {'hero': 0.0, 'friend': 0.0}, 'friend': {'hero': 0.0, 'friend': 0.0}}
    types = {}
    for txt, row in evidence['types'].items():
        found = row['targets']['train']
        if not found or row['model']['shot']['ranged']:
            continue
        for nearer, total in sums.items():
            for whom in total:
                total[whom] += found[nearer]['seconds'][whom]
        cells = {nearer: cell(found[nearer]['seconds']) for nearer in sums}
        if all(c['n_seconds'] >= least for c in cells.values()):
            types[txt] = {'name': row['name'], 'character_nearer': cells['hero'], 'companion_nearer': cells['friend']}
    return {
        'pooled': {'character_nearer': cell(sums['hero']), 'companion_nearer': cell(sums['friend'])},
        'types': dict(sorted(types.items(), key=lambda item: int(item[0]))),
    }


def curve(spread: Mapping[str, Any]) -> dict[str, Any]:
    """A drop's quantiles as knots (share of the drops under it, points over the mean of the curve)."""
    knots = [(0.0, float(HURT_LEAST)), (0.5, float(spread['p50'])), (0.9, float(spread['p90']))]
    if spread['p99'] < spread['max']:
        knots.append((0.99, float(spread['p99'])))
    knots.append((1.0, float(spread['max'])))
    mean = 0.0
    for (u0, low), (u1, high) in itertools.pairwise(knots):
        # The mean of a line in the logarithm from low to high.
        mean += (u1 - u0) * (low if high == low else (high - low) / math.log(high / low))
    return {
        'knots': [[u, round(points / mean, 4)] for u, points in knots],
        'mean_points': round(mean, 1),
        'points': {name: spread[name] for name in ('p50', 'p90', 'p99', 'max')},
        'n': spread['n'],
    }


def speeds(excel: Path, types: Sequence[str]) -> dict[str, float]:
    """World units a second of the missile of each type's first attack, where the tables name one."""

    def table(name: str, key: str) -> dict[str, dict[str, str]]:
        with (excel / name).open(encoding='latin-1') as handle:
            return {row[key]: row for row in csv.DictReader(handle, delimiter='\t')}

    monsters, missiles = table('monstats.txt', '*hcIdx'), table('missiles.txt', 'Missile')
    found = {}
    for txt in types:
        missile = missiles.get(monsters.get(txt, {}).get('MissA1', ''))
        if missile is not None and float(missile['Vel'] or 0) > 0:
            found[txt] = float(missile['Vel'])
    return found


def shot_row(found: Mapping[str, Any], pooled: Mapping[str, Any] | None, least: int) -> dict[str, Any]:
    """A row of shots. The chance that a missile sent at the character takes life is counted in points,
    not in drops: the points put on the shooter alone and half of its even share of the drops it
    shares, over the mean of a hit of one shooter alone (pooled), per shot that flew at where the
    character stood. Counting drops would not do here: a drop with missiles of five shooters near
    is a hit of each in the evidence's upper bound, which is seven times its lower one."""
    row: dict[str, Any] = {
        'name': found['name'],
        'rate': {
            'value': found['shots_per_second'],
            'n_shots': found['shots_in_sight'],
            'n_seconds': found['seconds_in_sight'],
        },
        'aim': {'value': found['at_hero_share'], 'n': found['shots']},
    }
    hit = found['points_sole'] / found['hits'] if pooled is None else pooled['takes_life']['mean_hit']
    if pooled is None or (found['shots_in_sight'] >= OWN_CHANCE * least and found['at_hero_share']):
        points = found['points_sole'] + found['points_shared'] / 2
        row['takes_life'] = {
            'value': round(points / hit / found['shots'] / found['at_hero_share'], 4),
            'points_sole': found['points_sole'],
            'points_shared': found['points_shared'],
            'mean_hit': round(hit, 1),
            'n_hits': found['hits'],
            'n': found['shots'],
        }
    else:
        row['takes_life'] = {**pooled['takes_life'], 'pooled': True}
    return row


def shots(evidence: Mapping[str, Any], speed: Mapping[str, float]) -> dict[str, Any]:
    least = evidence['thresholds']['enough_shots']
    pooled = shot_row(evidence['train']['ranged_all'], None, least)
    fighters = melee(evidence)['types']
    types = {}
    for txt, row in evidence['types'].items():
        found = row['ranged']['train']
        if not found or found['shots_in_sight'] < least:
            continue
        types[txt] = {
            **shot_row(found, pooled, least),
            'table_ranged': bool(found['table_ranged']),
            'melee_too': txt in fighters,
        }
    known = [(types[txt]['rate']['n_shots'], value) for txt, value in speed.items() if txt in types]
    weight = sum(n for n, _value in known)
    pooled['speed'] = {'value': round(sum(n * value for n, value in known) / weight, 2), 'n_shots': weight}
    for txt, row in types.items():
        row['speed'] = {'value': speed[txt]} if txt in speed else {**pooled['speed'], 'pooled': True}
    return {
        'pooled': pooled,
        'types': dict(sorted(types.items(), key=lambda item: int(item[0]))),
        'spread': curve(evidence['train']['ranged_all']['hit']),
    }


def nova(evidence: Mapping[str, Any]) -> dict[str, Any]:
    found = evidence['train']['novas']
    near = [
        row
        for row in found['deaths'].values()
        if 'cold' in row['group'] and row['rank'] == 'elite' and row['away'] in NOVA_REACH
    ]
    others = [row for row in found['deaths'].values() if 'cold' in row['group'] and row['rank'] != 'elite']
    drops = found['drops'][f'{NOVA_MISSILE}|cold']['drop']
    taken = sum(row['nova_n'] for row in near)
    # The nova drops over the evidence's `big` (300 points): more than one ring's points at any level
    # seen (182 through a cold resistance at the cap at level 85).
    big = [
        drop
        for drop in evidence['big_drops']
        if drop['half'] == 'train' and any(s['missile'] == int(NOVA_MISSILE) for s in drop['suspects'])
    ]
    return {
        'missile': int(NOVA_MISSILE),
        'ranks': ['champion', 'unique'],  # the evidence's "elite": a champion, a unique, a super unique
        'takes_life': {
            'value': round(sum(row['nova_n'] for row in near) / sum(row['n'] for row in near), 4),
            'n': sum(row['n'] for row in near),
        },
        'shown': {
            'elite': [sum(row['with_missile'] for row in near), sum(row['n'] for row in near)],
            'others': [sum(row['missiles'].get(NOVA_MISSILE, 0) for row in others), sum(row['n'] for row in others)],
        },
        'double': {'value': round(len(big) / taken, 4), 'n': taken},
        'points': {name: drops[name] for name in ('p50', 'p90', 'max')},
    }


def fit(evidence: Mapping[str, Any], speed: Mapping[str, float]) -> dict[str, Any]:
    train = evidence['train']
    return {
        'about': 'fitted on the train half of tests/inventory_tracking/scenarios/arena/evidence/evidence.json by '
        'evidence/fit.py; read by combat/sim/monsters.py. Do not edit by hand.',
        'train': {'takes': train['takes'], 'seconds': train['seconds'], 'drops': train['classes']['n']},
        'thresholds': evidence['thresholds'],
        'melee': {**melee(evidence), 'spread': curve(train['big']['plain|0|sole melee']['drop'])},
        'reach': {'body': BODY, 'tail': tail(evidence)},
        'targets': targets(evidence),
        'shots': shots(evidence, speed),
        'nova': nova(evidence),
    }


def kept_speeds(path: Path) -> dict[str, float]:
    """The speeds of the file already written: its own, not the pooled ones."""
    if not path.exists():
        return {}
    types = json.loads(path.read_text())['shots']['types']
    return {txt: row['speed']['value'] for txt, row in types.items() if not row['speed'].get('pooled')}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Write the monster model fit from the train half of the evidence.')
    parser.add_argument('--evidence', type=Path, default=EVIDENCE)
    parser.add_argument('--excel', type=Path, default=EXCEL, help="the game's tables (monstats.txt, missiles.txt)")
    parser.add_argument('--out', type=Path, default=FITTED)
    args = parser.parse_args(argv)
    evidence = json.loads(args.evidence.read_text())
    if (args.excel / 'missiles.txt').exists():
        speed = speeds(args.excel, list(evidence['types']))
    else:
        speed = kept_speeds(args.out)
        print(f'{args.excel}: no tables there; the speeds of {args.out.name} are kept')
    args.out.write_text(json.dumps(fit(evidence, speed), indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(f'{args.out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
