"""The fitted table of the monster model (combat/sim/monsters.py), written from the TRAIN half of the
evidence and from nothing else:

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.evidence.fit
        [--excel pricing/raw/game-excel]

reads `evidence.json`, `sparks.json` and `swings.json` beside this file and writes
`inventory_tracking/combat/data/monsters_fit.json`. No number of that file is typed by hand: each is a
figure of `evidence.json['train']` (or of `['types'][txt][...]['train']`), of `sparks.json['train']` or
of `swings.json['train']`, or is counted from such figures here, and carries its `n`. The check half of
none is read. A type under the evidence's own thresholds (`evidence.json['thresholds']`: 30 s within
reach or 10 sole blows for a melee type, 20 shots for a shooter, 30 s in each cell of whom a type goes
for; OWN_CHANCE times the 20 shots for a shooter's own chance to take life; swings.py ENOUGH_SWINGS
swings run out with the character standing for a melee type's own chance) has no row, or no chance of
its own, and the model uses the pooled one.

What is decided here, not measured (each said where it is used):

- **the chance that a swing takes life is the middle of the evidence's two bounds**: `low` counts the
  drops put on that monster alone, `high` those it shares with other suspects too. A shared drop
  has two suspects or more, so the truth is under `high`; the middle is taken. In a pack nearly every
  drop is shared, so there `low` says little and the middle is nearer a half of `high` than the truth
  (SWINGS.md: Doom Knights). For a shot the bounds are seven times apart (a drop with the missiles of
  several shooters near is a hit of each), so there the chance is counted in points (`shot_row`); with
  it a shooter in sight takes 0.56 points a second where the train half shows 0.42 to 0.70, with the
  middle of the counts it would take 1.3;
- **a swing's chance is that of the swings that ran out** (swings.py: the frame after the run shows the
  monster neither staggering nor dead), with the character standing still: the model plays the
  character's moves itself (a blow lands only if the target is still in reach) and, since 2026-10-13,
  what the character's strikes do to a swing (a struck monster staggers and its swing is lost; a dead
  one is gone). What is left in the chance is a miss, a block, a blow the character's own protection
  took: they cannot be told apart. Before, the chance was that of all swings of half their length or
  more (one in six) and a share of swings was cut short by a roll: a character that did not strike
  was then hurt as seldom as one that did (the incident `infector-seal`);
- **the rest after a swing, the frame the blow lands at, a struck monster's stagger** are swings.json's
  figures as they are: the deciles of the gap to the same monster's next swing, the median place of a
  sole drop in its run, the share of the falls of a monster's life of each size that were followed by
  its stagger and the deciles of how long that lasted. `rate` and `cut` stay in a row as rates.py
  counted them over all swings, struck or not; the model no longer plays by them;
- **the spread of a blow's size** is drawn through the quantiles the evidence gives of the drops put
  on one monster alone (the median, the 90th and 99th percentile, the largest), straight lines in
  the logarithm between them, from the smallest drop the recorder writes (hurts.HURT_LEAST) up;
  the model uses it over its mean, so the mean blow stays the game table's;
- **the reach beyond the body's**: the swings begun at the character per monster-second in each band
  of distance over the same within 3.5 units, never rising with the distance;
- **a death nova twice the size**: the share of the train half's nova drops that are in the evidence's
  list of drops over 300 points, which one ring's points do not reach at any level seen;
- **the sparks of a Lightning Enchanted monster** (`sparks`, from sparks.json; SPARKS.md is the
  measurement): who lets them go is every rank that let one go; **a release comes with the time the
  monster is being struck**, at the rate of the window after a hit whose one rate gives the monsters'
  counts of releases best (the least deviance; a chance per hit is written beside it and is the worse
  relation), never sooner after the one before than the least gap seen (`free` is the rate over the
  struck time less that gap after each release: what a frame outside the gap has); a release is the
  commonest count of sparks, a spark lasts the most frames one was seen and turns after the commonest
  run of frames; a spark is in reach of the character within the evidence's own distance for "ended on it"
  and ends on it with the share of those in reach that did; **the chance that it then takes life is
  the middle of the evidence's two bounds, as for a swing**: the arrivals followed by a drop put on
  the owner alone, and those followed by any drop. On the train half both are none of 11, so the
  chance is 0 and the model's sparks take no life: `upper95` is the chance under which the truth
  lies at 95% with that n, written for whoever wants the cautious figure instead. The size of a
  spark that takes life is not fitted (there is none to fit on): it stays the missile's own.

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
SPARKS = HERE / 'sparks.json'
SWINGS = HERE / 'swings.json'
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
MODEL_RANK = {'super unique': 'unique'}  # the evidence's ranks that sim/monsters.py `rank_of` calls otherwise


def middle(low: float | None, high: float | None) -> float | None:
    return None if low is None or high is None else round((low + high) / 2, 4)


def life(found: Mapping[str, Any]) -> dict[str, Any]:
    """The chance that a swing which ran out takes life, from swings.json's figures of such swings (the
    character standing still): the middle of the two bounds, with the swings no other hostile stood by."""
    stood, alone = found['ran_out']['stood'], found['ran_out']['alone']
    return {
        'value': stood['value'],
        'low': stood['low'],
        'high': stood['high'],
        'n': stood['n'],
        'alone': {key: alone[key] for key in ('value', 'n')},
    }


def melee_row(found: Mapping[str, Any], frames: int, mode: str | None, swung: Mapping[str, Any]) -> dict[str, Any]:
    """A row of swings: the length of one, the chance that one which ran out takes life (`swung`: the
    row's part of swings.json), and for the record what rates.py counts over all its swings, struck or
    not: the swings a second in reach and the share of runs under half the usual length."""
    return {
        'name': found['name'],
        'frames': {'value': frames, 'mode': mode},
        'takes_life': life(swung),
        'rate': {'value': found['swings_per_second'], 'n_swings': found['swings'], 'n_seconds': found['seconds']},
        'cut': {'value': found['cut_share'], 'n': found['runs']},
    }


def stagger(swung: Mapping[str, Any]) -> dict[str, Any]:
    """What a struck monster does: by the share of its life a frame's hits took, the chance that it
    staggers, and how long it then stands (the deciles of the spells in that mode)."""
    found = swung['stagger']
    return {
        'mode': swung['recovery']['mode'],
        'parts': found['parts'],
        'bands': [{'from': band['from'], 'chance': band['chance'], 'n': band['n']} for band in found['bands']],
        'recovery': {'knots': found['recovery']['knots'], 'p50': found['recovery']['p50'], 'n': found['recovery']['n']},
    }


def melee(evidence: Mapping[str, Any], swung: Mapping[str, Any]) -> dict[str, Any]:
    least = evidence['thresholds']
    enough = swung['constants']['enough_swings']
    train = swung['train']
    pooled = evidence['train']['melee_all']
    whole = melee_row(pooled, STRIKE_FRAMES, None, train)
    types = {}
    for txt, row in evidence['types'].items():
        found = row['melee']['train']
        if not found or int(txt) in pooled['left_out']:
            continue
        if found['seconds'] < least['enough_seconds'] and found['blows'] < least['enough_blows']:
            continue
        mode = min(found['usual_frames'], key=int)  # the lowest attack mode the type was seen in
        own = train['types'].get(txt)
        types[txt] = melee_row(found, found['usual_frames'][mode], mode, own or train)
        if own is None or own['ran_out']['stood']['n'] < enough:
            types[txt]['takes_life'] = {**whole['takes_life'], 'pooled': True}
    return {
        'pooled': whole,
        'types': dict(sorted(types.items(), key=lambda item: int(item[0]))),
        'idle': sorted(pooled['left_out']),
        'blow': {'share': train['blow']['share'], 'n': train['blow']['n']},
        'rest': {'knots': train['rest']['knots'], 'p50': train['rest']['p50'], 'n': train['rest']['n']},
        'stagger': stagger(train),
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


def shots(evidence: Mapping[str, Any], speed: Mapping[str, float], swung: Mapping[str, Any]) -> dict[str, Any]:
    least = evidence['thresholds']['enough_shots']
    pooled = shot_row(evidence['train']['ranged_all'], None, least)
    fighters = melee(evidence, swung)['types']
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


def commonest(counts: Mapping[str, int]) -> int:
    """The key (a number written as text) with the highest count; of several as common, the least."""
    return min(map(int, counts), key=lambda value: (-counts[str(value)], value))


def sparks(found: Mapping[str, Any]) -> dict[str, Any]:
    """The sparks of a Lightning Enchanted monster, from the train half of sparks.json (the module text
    says what is decided here)."""
    train = found['train']
    relation, flight, life = train['release']['all'], train['flight'], train['life']
    best = min(relation['per_second'], key=lambda row: (row['deviance'], row['window']))
    gap = train['release']['gap']
    # The time a release was free to come in: the struck seconds less the gap after each release.
    free = best['struck_seconds'] - relation['releases'] * gap['least'] / GAME_RATE
    return {
        'missile': found['missile'],
        'ranks': sorted({MODEL_RANK.get(rank, rank) for rank, row in train['by_rank'].items() if row['releases']}),
        'shown': {
            rank: {'releases': row['releases'], 'struck': row['struck'], 'hits': row['hits']}
            for rank, row in train['by_rank'].items()
        },
        'release': {
            'rate': {
                'value': best['value'],
                'free': round(relation['releases'] / free, 4),
                'n': relation['releases'],
                'n_seconds': best['struck_seconds'],
                'n_monsters': relation['monsters'],
            },
            'window': best['window'],
            'deviance': best['deviance'],
            'per_hit': {**relation['per_hit'], 'n_hits': relation['hits']},
            'gap': {'value': gap['least'], 'n': gap['n']},
        },
        'count': {'value': commonest(train['count']['sizes']), 'n': train['count']['n']},
        'flight': {
            'frames': {'value': flight['frames_most'], 'n': flight['sparks']},
            'turn': {'value': flight['turn'], 'n': flight['turns']},
            'stride': {'measured': flight['stride'], 'n': flight['stride_n']},
            'out': {age: {'p50': row['p50'], 'n': row['n']} for age, row in flight['out'].items()},
        },
        'contact': found['constants']['end_on'],
        'meets': train['reach']['meets'],
        'takes_life': {
            'value': middle(life['low'], life['high']),
            'low': life['low'],
            'high': life['high'],
            'n': life['arrivals'],
            'upper95': life['upper95'],
        },
    }


def fit(
    evidence: Mapping[str, Any], speed: Mapping[str, float], sparked: Mapping[str, Any], swung: Mapping[str, Any]
) -> dict[str, Any]:
    train = evidence['train']
    return {
        'about': 'fitted on the train half of tests/inventory_tracking/scenarios/arena/evidence/evidence.json, '
        'sparks.json and swings.json by evidence/fit.py; read by combat/sim/monsters.py. Do not edit by hand.',
        'train': {'takes': train['takes'], 'seconds': train['seconds'], 'drops': train['classes']['n']},
        'thresholds': evidence['thresholds'],
        'melee': {**melee(evidence, swung), 'spread': curve(train['big']['plain|0|sole melee']['drop'])},
        'reach': {'body': BODY, 'tail': tail(evidence)},
        'targets': targets(evidence),
        'shots': shots(evidence, speed, swung),
        'nova': nova(evidence),
        'sparks': sparks(sparked),
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
    parser.add_argument('--sparks', type=Path, default=SPARKS)
    parser.add_argument('--swings', type=Path, default=SWINGS)
    parser.add_argument('--excel', type=Path, default=EXCEL, help="the game's tables (monstats.txt, missiles.txt)")
    parser.add_argument('--out', type=Path, default=FITTED)
    args = parser.parse_args(argv)
    evidence = json.loads(args.evidence.read_text())
    if (args.excel / 'missiles.txt').exists():
        speed = speeds(args.excel, list(evidence['types']))
    else:
        speed = kept_speeds(args.out)
        print(f'{args.excel}: no tables there; the speeds of {args.out.name} are kept')
    found = fit(evidence, speed, json.loads(args.sparks.read_text()), json.loads(args.swings.read_text()))
    args.out.write_text(json.dumps(found, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(f'{args.out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
