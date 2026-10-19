"""How a swing ends, and what a struck monster does, in the takes: SWINGS.md and swings.json.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.evidence.swings [--jobs N]

reads every take of `split.json` and writes `SWINGS.md` and `swings.json` beside this file. Nothing here
is fitted: `fit.py` reads `swings.json`'s train half, `refit_check.py` its check half. `--render` writes
SWINGS.md again from swings.json.

Why. rates.py counts a swing as whole when its run of frames lasted half the type's usual length, and
the share of whole swings that takes life came out at one in six. That share is two things in one: most
swings at the character do not run out at all, because the character strikes the monster meanwhile
and it staggers or dies; a swing that does run out takes life two or three times as often. A character
that does not strike for two seconds (the incident `infector-seal`: Doom Knights landed 11 of 14 swings
that ran out) is hurt by every monster in reach at that higher share, which one chance per swing cannot
give. So the swings are told apart here by how they ended.

What a take is tallied into (`tally`), of the hostiles the threat table does not call ranged, within
sim/monsters.py AWARE of the character:

- `runs`: every run of frames in one attack mode (hurts.ATTACK_MODES) begun within hurts.SUSPECT_REACH:
  its length, the distance and the path record's target at its start, whether its first frame was seen
  begun (`begun`), how far the character moved meanwhile, how many hostiles stood within hurts.BESIDE of
  the character (`crowd`), the monster's mode in the frame after (`then`; DEAD when it lay dead, None
  when it was not seen), whether its life fell during the run (`struck`), the drops of the character's
  life in the run's frames and the rates.HIT_AFTER after (how far into the run, blows.py's class, the
  number of suspects, whether this monster is one), and the frames to the same monster's next run
  (`rest`) with the distance that one began at;
- `falls`: every fall of a monster's life between two frames, by its size in PARTS of the most life
  (a frame holds a monster's life in 128ths), the mode before, the first other mode within
  STAGGER_AFTER frames (SAME for none) and whether it stood within rates.MODEL_REACH of the character;
- `entered`: every change of mode, with or without a fall of life in that frame;
- `spells`: the lengths of the runs in a mode that is no attack, seen from their first frame to their last;
- `near`: frames stood within rates.MODEL_REACH, and the deaths there.

What is decided here, not measured:

- **the mode of a struck monster** is not typed in: it is the mode most often entered in the frame of a
  fall of life (`recovery`, with the counts);
- **a swing ran out** when the frame after its run shows the monster in any mode but that one, and
  alive: `staggered`, `died` and `unseen` are the other three ends;
- **a drop is put on a swing** as rates.py does it (`low`: blows.py called the monster its sole suspect;
  `high`: it is one of the suspects), a run counted once however long;
- **a rest** is the gap to the same monster's next run when both began within hurts.BESIDE of the
  character, the first aimed at it and run out, and the gap is REST_MOST frames or less: a longer one
  is a walk or a lost target, not a rest. `after_stagger` is the same gap after a swing that ended in
  a stagger (twice REST_MOST at most): the stagger and whatever follows it;
- **where in a swing the blow lands**: the drops put on a monster alone, in runs seen from their first
  frame that ran out: the frames from the run's start to the frame before the drop showed, over the
  run's length.

**The check half is not unseen here.** The split was made on 2026-10-12 at take 20261012T170305Z-116
and extended on 2026-10-13 to the takes recorded since by its own rule (scan.half). That put the
Chaos Sanctuary takes in the check half, the incident's own (20261012T182157Z-108) among them, and
those were looked at swing by swing before this measurement was shaped: that a swing is to be told
by its end, and that a struck monster's stagger is what ends most, was first seen in the Doom
Knights' runs of the check half and in one River of Flame take of the train half
(20261012T182040Z-107), and only then counted over the train half. The numbers the fit takes are
the train half's; the check half's rows of the Doom Knight, and the agreement of the two halves on
how swings end, are not the test they would be on takes nobody had read.

What a take cannot say: whether a swing that ran out and took no life missed, was blocked or was
taken whole by the character's protection (as before: one chance for all three); what staggers a
monster beside the size of the fall (the frames show the sum of the hits between two of them).
"""

import argparse
import itertools
import json
import math
import os
import statistics
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from multiprocessing import get_context
from pathlib import Path
from typing import Any

from inventory_tracking.combat.sim.monsters import AWARE
from inventory_tracking.takes.hurts import ATTACK_MODES, BESIDE, SUSPECT_REACH
from inventory_tracking.takes.takes import MonsterRow, Take
from inventory_tracking.takes.timeline import GAME_RATE
from tests.inventory_tracking.scenarios.arena.evidence import blows, scan
from tests.inventory_tracking.scenarios.arena.evidence.blows import HERO, SOLE_MELEE, Moment, name_of, rank_of
from tests.inventory_tracking.scenarios.arena.evidence.rates import HIT_AFTER, MODEL_REACH, MOVED, melee_type


HERE = Path(__file__).parent
SPLIT = HERE / 'split.json'
DEAD, SAME = 'dead', 'same'
RAN_OUT, STAGGERED, DIED, UNSEEN = 'ran out', 'staggered', 'died', 'unseen'
ENDS = (RAN_OUT, STAGGERED, DIED, UNSEEN)
PARTS = 16  # a fall of life is binned by how many of these parts of the most life it took
MOST = 4  # the last bin: this many parts or more
STAGGER_AFTER = 2  # frames after a fall of life in which the monster's mode is looked at
REST_MOST = 50  # frames: a longer gap between two swings is not a rest
ENOUGH_SWINGS = 30  # swings run out with the character standing: a type with this many has a chance of its own
QUANTILES = tuple(step / 10 for step in range(11))


def tally(take_name: str, moments: Sequence[Moment], rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The counts of one take (the module text) from its moments and its blows (`rows` of blows.py)."""
    drops: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        drops[row['frame']].append(row)
    tracks: dict[int, list[tuple[int, MonsterRow, float]]] = defaultdict(list)
    fell: dict[int, int] = {}  # unit -> the first frame it lay dead in
    for moment in moments:
        if moment.hero is None:
            continue
        for monster in moment.foes:
            away = math.dist(monster.at, moment.hero.at)
            if melee_type(monster.txt) and away <= AWARE:
                tracks[monster.unit].append((moment.index, monster, away))
        for corpse in moment.fallen:
            fell.setdefault(corpse.unit, moment.index)
    runs: list[dict[str, Any]] = []
    falls: Counter[str] = Counter()
    entered: Counter[str] = Counter()
    spells: Counter[str] = Counter()
    near = deaths = 0
    for unit, track in tracks.items():
        mine: list[dict[str, Any]] = []
        first = 0  # where the stretch of one mode in consecutive frames began
        for place, (index, monster, away) in enumerate(track):
            near += away <= MODEL_REACH
            joined = place > 0 and track[place - 1][0] == index - 1
            before = track[place - 1][1] if joined else None
            if before is not None and monster.life < before.life:
                soon = track[place : place + STAGGER_AFTER + 1]
                later = [row.mode for at, row, _away in soon if at <= index + STAGGER_AFTER]
                then = next((mode for mode in later if mode != before.mode), SAME)
                parts = min((before.life - monster.life) * PARTS // max(before.max_life, 1), MOST)
                falls[f'{parts}|{before.mode}|{then}|{int(track[place - 1][2] <= MODEL_REACH)}'] += 1
            if before is not None and monster.mode != before.mode:
                entered[f'{monster.mode}|{int(monster.life < before.life)}'] += 1
            if before is not None and monster.mode == before.mode:
                continue
            _close(track, first, place, joined, fell.get(unit), mine, spells)
            first = place
        _close(track, first, len(track), False, fell.get(unit), mine, spells)
        last_at, _row, last_away = track[-1]
        deaths += fell.get(unit) == last_at + 1 and last_away <= MODEL_REACH
        for run, after in zip(mine, [*mine[1:], None], strict=False):
            start, last = run.pop('start'), run.pop('last')
            hero, end = moments[start].hero, moments[last].hero
            assert hero is not None
            assert end is not None
            run['aim'] = moments[start].aims.get(unit)
            run['moved'] = round(math.dist(hero.at, end.at), 1)
            run['crowd'] = sum(math.dist(foe.at, hero.at) <= BESIDE for foe in moments[start].foes)
            run['drops'] = [
                [frame - start, row['class'], len(row['by']), int(any(s['unit'] == unit for s in row['by']))]
                for frame in range(start + 1, last + HIT_AFTER + 1)
                for row in drops.get(frame, ())
            ]
            run['rest'] = None if after is None else after['start'] - last - 1
            run['next_away'] = None if after is None else after['away']
        runs += [run for run in mine if run['away'] <= SUSPECT_REACH]
    return {
        'take': take_name,
        'runs': runs,
        'falls': dict(falls),
        'entered': dict(entered),
        'spells': dict(spells),
        'near': near,
        'deaths': deaths,
    }


def _close(
    track: Sequence[tuple[int, MonsterRow, float]],
    first: int,
    end: int,
    joined: bool,
    fell: int | None,
    runs: list[dict[str, Any]],
    spells: Counter[str],
) -> None:
    """The stretch track[first:end] of one mode in consecutive frames is over: a run if the mode is an
    attack, else a spell if it was seen from its first frame to its last. `joined`: the frame after is
    the track's next."""
    if end <= first:
        return
    start, monster, away = track[first]
    last = track[end - 1][0]
    begun = first > 0 and track[first - 1][0] == start - 1
    if monster.mode not in ATTACK_MODES:
        if begun and joined:
            spells[f'{monster.mode}|{end - first}'] += 1
        return
    then: Any = track[end][1].mode if joined else (DEAD if fell == last + 1 else None)
    lives = [row.life for _at, row, _away in track[first : end + joined]]
    runs.append(
        {
            'unit': monster.unit,
            'txt': monster.txt,
            'rank': rank_of(monster.flags),
            'mode': monster.mode,
            'start': start,
            'last': last,
            'frames': end - first,
            'away': round(away, 1),
            'begun': int(begun),
            'then': then,
            'struck': int(any(later < sooner for sooner, later in itertools.pairwise(lives))),
        }
    )


def read(directory: Path) -> dict[str, Any]:
    """One take's tally; `skipped` says why there is none (as scan.read)."""
    name = directory.name
    try:
        take = Take.load(directory)
    except (OSError, ValueError) as exc:
        return {'take': name, 'skipped': f'not read ({exc})'}
    if take.schema < 2 or not take.frames:
        return {'take': name, 'skipped': 'schema 1 or no frames'}
    moments = list(blows.walk(take))
    return tally(name, moments, blows.blows(take, None, moments))


def gather(directories: Sequence[Path], jobs: int | None = None) -> list[dict[str, Any]]:
    """`read` of every take in `jobs` processes, in the order given."""
    jobs = jobs or min(os.cpu_count() or 1, 16)
    if jobs <= 1 or len(directories) <= 1:
        return [read(directory) for directory in directories]
    with get_context('fork').Pool(jobs) as pool:
        return list(pool.imap(read, directories, chunksize=2))


# ---------------------------------------------------------------------------------------------------
# What a set of takes measures.


def quantile(values: Sequence[float], share: float) -> float | None:
    found = sorted(values)
    return found[min(int(share * len(found)), len(found) - 1)] if found else None


def ratio(part: float, whole: float, digits: int = 3) -> float | None:
    return round(part / whole, digits) if whole else None


def rounded(value: float | None, digits: int = 3) -> float | None:
    return None if value is None else round(value, digits)


def middle(low: float | None, high: float | None) -> float | None:
    return None if low is None or high is None else round((low + high) / 2, 4)


def recovery_of(tallies: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The mode of a struck monster: the one most often entered in the frame of a fall of life."""
    struck: Counter[int] = Counter()
    every: Counter[int] = Counter()
    for one in tallies:
        for key, count in one['entered'].items():
            mode, with_fall = map(int, key.split('|'))
            every[mode] += count
            if with_fall:
                struck[mode] += count
    if not struck:
        return {'mode': None, 'entered': 0, 'with_fall': 0}
    mode = min(struck, key=lambda found: (-struck[found], found))
    return {'mode': mode, 'entered': every[mode], 'with_fall': struck[mode]}


def end_of(run: Mapping[str, Any], recovery: int | None) -> str:
    then = run['then']
    if then is None:
        return UNSEEN
    if then == DEAD:
        return DIED
    return STAGGERED if then == recovery else RAN_OUT


def chance(runs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Of `runs`, the share with a drop put on the monster alone (`low`) and with one that names it
    (`high`), and their middle."""
    low = sum(any(kind == SOLE_MELEE and named for _at, kind, _n, named in run['drops']) for run in runs)
    high = sum(any(named for _at, _kind, _n, named in run['drops']) for run in runs)
    found = {'n': len(runs), 'low': ratio(low, len(runs)), 'high': ratio(high, len(runs))}
    return {**found, 'value': middle(found['low'], found['high'])}


def at_hero(runs: Sequence[Mapping[str, Any]], reach: float = MODEL_REACH) -> list[Mapping[str, Any]]:
    return [run for run in runs if run['aim'] == HERO and run['away'] <= reach]


def stood(runs: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [run for run in runs if run['moved'] < MOVED]


def swinging(runs: Sequence[Mapping[str, Any]], recovery: int | None) -> dict[str, Any]:
    """What the runs of one type, or of all, say: how the swings at the character within
    rates.MODEL_REACH ended, and of those that ran out the share that took life."""
    near = at_hero(runs)
    ends = {end: [run for run in near if end_of(run, recovery) == end] for end in ENDS}
    out = ends[RAN_OUT]
    gaps = {
        end: [
            run['rest']
            for run in at_hero(runs, BESIDE)
            if end_of(run, recovery) == end and run['rest'] is not None and run['next_away'] <= BESIDE
        ]
        for end in (RAN_OUT, STAGGERED)
    }
    rests = gaps[RAN_OUT]
    short = [rest for rest in rests if rest <= REST_MOST]
    reeled = [gap for gap in gaps[STAGGERED] if gap <= 2 * REST_MOST]
    return {
        'runs': len(near),
        'ends': {end: {**chance(found), 'struck': sum(run['struck'] for run in found)} for end, found in ends.items()},
        'ran_out': {
            'stood': chance(stood(out)),
            'all': chance(out),
            'alone': chance([run for run in stood(out) if run['crowd'] <= 1]),
            'frames': quantile([run['frames'] for run in out], 0.5),
        },
        'rest': {
            'n': len(short),
            'longer': len(rests) - len(short),
            'p50': quantile(short, 0.5),
            'mean': round(statistics.mean(short), 2) if short else None,
            'knots': [quantile(short, share) for share in QUANTILES] if short else [],
        },
        # From a swing that ended in a stagger to the same monster's next: the stagger and what follows it.
        'after_stagger': {'n': len(reeled), 'p50': quantile(reeled, 0.5)},
    }


def measure(tallies: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """What the takes of `tallies` measure (the module text says what each part is)."""
    recovery = recovery_of(tallies)
    mode = recovery['mode']
    runs = [run for one in tallies for run in one['runs']]
    bands: list[dict[str, Any]] = [{'from': parts, 'n': 0, 'staggered': 0} for parts in range(MOST + 1)]
    near_falls = [0] * (MOST + 1)
    for one in tallies:
        for key, count in one['falls'].items():
            parts, before, then, near = key.split('|')
            if before == str(mode):
                continue  # struck again while it staggers: no new stagger to see
            bands[int(parts)]['n'] += count
            bands[int(parts)]['staggered'] += count * (then == str(mode))
            near_falls[int(parts)] += count * int(near)
    for band in bands:
        band['chance'] = ratio(band['staggered'], band['n'])
    lengths = [
        int(key.split('|')[1])
        for one in tallies
        for key, count in one['spells'].items()
        if key.split('|')[0] == str(mode)
        for _ in range(count)
    ]
    landed = [
        (at - 1) / run['frames']
        for run in at_hero(runs, SUSPECT_REACH)
        if run['begun'] and end_of(run, mode) == RAN_OUT
        for at, kind, _n, named in run['drops']
        if kind == SOLE_MELEE and named
    ]
    by_type: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for run in runs:
        by_type[run['txt']].append(run)
    return {
        'takes': len(tallies),
        'recovery': recovery,
        **swinging(runs, mode),
        'blow': {
            'n': len(landed),
            'share': rounded(quantile(landed, 0.5)),
            'p10': rounded(quantile(landed, 0.1)),
            'p90': rounded(quantile(landed, 0.9)),
        },
        'stagger': {
            'parts': PARTS,
            'bands': bands,
            'recovery': {
                'n': len(lengths),
                'p50': quantile(lengths, 0.5),
                'knots': [quantile(lengths, share) for share in QUANTILES] if lengths else [],
            },
        },
        'struck': {
            'seconds': round(sum(one['near'] for one in tallies) / GAME_RATE, 1),
            'falls': near_falls,
            'deaths': sum(one['deaths'] for one in tallies),
        },
        'types': {
            str(txt): {'name': name_of(txt), **swinging(found, mode)}
            for txt, found in sorted(by_type.items())
            if at_hero(found)
        },
    }


# ---------------------------------------------------------------------------------------------------
# SWINGS.md


def show(value: Any, digits: int = 2) -> str:
    if value is None:
        return '-'
    return f'{value:.{digits}f}' if isinstance(value, float) else str(value)


def table(headers: Sequence[str], lines: Sequence[Sequence[Any]]) -> list[str]:
    body = [' | '.join(show(cell) for cell in line) for line in lines]
    return ['| ' + ' | '.join(headers) + ' |', '|' + ' --- |' * len(headers), *(f'| {line} |' for line in body), '']


def took(found: Mapping[str, Any]) -> str:
    """A chance with its bounds and its n."""
    if not found['n']:
        return '-'
    return f'{show(found["value"])} ({show(found["low"])} to {show(found["high"])} of {found["n"]})'


def render(found: Mapping[str, Any]) -> str:
    train, check = found[scan.TRAIN], found[scan.CHECK]
    mode = train['recovery']
    lines = [
        '# How a swing ends, and what a struck monster does',
        '',
        'Generated by `tests/inventory_tracking/scenarios/arena/evidence/swings.py` from the takes of `split.json`; '
        'do not edit by hand. `swings.json` beside this file holds the same numbers; the method, and what a take '
        'cannot say, is in the module text of `swings.py`. Fit on train (`fit.py`), judge on check (`refit_check.py`).',
        '',
        f'Train {train["takes"]} takes, check {check["takes"]}. A chance is written as the middle of its two bounds '
        '(the drops put on the monster alone, and those that name it among others) of n swings.',
        '',
        '**The check half is not unseen here**: the Chaos Sanctuary takes recorded after the split of 2026-10-12 fell '
        "into it by the split's own rule, and their Doom Knights were read swing by swing (the incident "
        "`infector-seal` is one of those takes) before this measurement was shaped. The fit takes the train half's "
        'numbers only.',
        '',
        '## The mode of a struck monster',
        '',
        f'Mode {mode["mode"]} is the mode most often entered in the frame of a fall of life: {mode["with_fall"]:,} of '
        f'its {mode["entered"]:,} entries on the train half come with one (check: {check["recovery"]["with_fall"]:,} '
        f'of {check["recovery"]["entered"]:,} of mode {check["recovery"]["mode"]}).',
        '',
        '## How the swings at the character end',
        '',
        f'Runs in an attack mode aimed at the character and begun within {MODEL_REACH} units of it, by the frame '
        'after the run. `struck`: the runs during which the life of the monster fell.',
        '',
    ]
    rows = []
    for end in ENDS:
        a, b = train['ends'][end], check['ends'][end]
        rows.append(
            [
                end,
                a['n'],
                ratio(a['n'], train['runs'], 2),
                took(a),
                a['struck'],
                b['n'],
                ratio(b['n'], check['runs'], 2),
                took(b),
            ]
        )
    lines += table(
        ['end', 'train n', 'share', 'takes life', 'struck', 'check n', 'share', 'takes life'],
        rows,
    )
    lines += ['## A swing that ran out', '']
    rows = [
        [what, took(train['ran_out'][part]), took(check['ran_out'][part])]
        for what, part in (
            ('the character standing still', 'stood'),
            ('the same, no other hostile beside it', 'alone'),
            ('whatever the character did', 'all'),
        )
    ]
    lines += table(['takes life', 'train', 'check'], rows)
    lines += [
        f'The blow lands {show(train["blow"]["share"])} of the way through the run (train: the median of '
        f'{train["blow"]["n"]} drops put on one monster alone, {show(train["blow"]["p10"])} to '
        f'{show(train["blow"]["p90"])} at the 10th and 90th percentile; check: {show(check["blow"]["share"])} of '
        f'{check["blow"]["n"]}).',
        '',
        f'The rest before the same monster swings again: {show(train["rest"]["p50"])} frames at the median of '
        f'{train["rest"]["n"]} (train; deciles {train["rest"]["knots"]}; {train["rest"]["longer"]} gaps over '
        f'{REST_MOST} frames left out), {show(check["rest"]["p50"])} of {check["rest"]["n"]} (check).',
        '',
        f"From a swing that ended in a stagger to the same monster's next swing: "
        f'{show(train["after_stagger"]["p50"])} frames at the median of {train["after_stagger"]["n"]} (train), '
        f'{show(check["after_stagger"]["p50"])} of {check["after_stagger"]["n"]} (check): the stagger and a rest.',
        '',
        '## A struck monster',
        '',
        f"Falls of a monster's life between two frames, by the share of its most life the fall took, and how many "
        f'were followed by mode {mode["mode"]} within {STAGGER_AFTER} frames (a monster already in it is not counted).',
        '',
    ]
    rows = []
    for a, b in zip(train['stagger']['bands'], check['stagger']['bands'], strict=True):
        edge = f'{a["from"]}/{PARTS}' + (' and more' if a['from'] == MOST else f' to {a["from"] + 1}/{PARTS}')
        rows.append([edge, a['n'], a['chance'], b['n'], b['chance']])
    lines += table(['fall', 'train n', 'staggers', 'check n', 'staggers'], rows)
    a, b = train['stagger']['recovery'], check['stagger']['recovery']
    lines += [
        f'It stays in that mode {show(a["p50"])} frames at the median of {a["n"]:,} spells (train; deciles '
        f'{a["knots"]}), {show(b["p50"])} of {b["n"]:,} (check).',
        '',
        f'How often: within {MODEL_REACH} units of the character a monster stood {train["struck"]["seconds"]:,.0f} s '
        f'on the train half and lost life {sum(train["struck"]["falls"]):,} times there '
        f'({train["struck"]["falls"]} by the size of the fall), and {train["struck"]["deaths"]:,} died there; check: '
        f'{check["struck"]["seconds"]:,.0f} s, {check["struck"]["falls"]}, {check["struck"]["deaths"]:,} deaths.',
        '',
        '## By type',
        '',
        f'Types with {ENOUGH_SWINGS} swings run out with the character standing on the train half have a chance of '
        'their own in the fit; every other uses the pooled one. All types with a swing at the character on either '
        'half are listed, so that what is missing can be read off.',
        '',
    ]
    rows = []
    for txt in sorted({*train['types'], *check['types']}, key=int):
        a, b = train['types'].get(txt), check['types'].get(txt)
        one = a or b
        assert one is not None
        rows.append(
            [
                f'{one["name"]} ({txt})',
                a['runs'] if a else 0,
                a['ends'][RAN_OUT]['n'] if a else 0,
                took(a['ran_out']['stood']) if a else '-',
                a['ran_out']['frames'] if a else None,
                b['runs'] if b else 0,
                b['ends'][RAN_OUT]['n'] if b else 0,
                took(b['ran_out']['stood']) if b else '-',
            ]
        )
    lines += table(
        ['type', 'train swings', 'ran out', 'ran out, stood: takes life', 'frames', 'check swings', 'ran out',
         'ran out, stood: takes life'],
        rows,
    )  # fmt: skip
    return '\n'.join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='How a swing ends and what a struck monster does, from all takes.')
    parser.add_argument('--root', type=Path, default=scan.ROOT, help='the directory of the takes')
    parser.add_argument('--jobs', type=int, help='worker processes (default: the cores, 16 at most)')
    parser.add_argument('--out', type=Path, default=HERE, help='where SWINGS.md and swings.json go')
    parser.add_argument('--split', type=Path, default=SPLIT, help='the halves (split.json)')
    parser.add_argument('--render', action='store_true', help='write SWINGS.md again from swings.json, reading no take')
    args = parser.parse_args(argv)
    path = args.out / 'swings.json'
    if args.render:
        found = json.loads(path.read_text())
    else:
        split = json.loads(args.split.read_text())
        found = {
            'about': 'tests/inventory_tracking/scenarios/arena/evidence/swings.py: see SWINGS.md; fit on train, '
            'judge on check',
            'split': args.split.name,
            'constants': {
                'reach': MODEL_REACH,
                'parts': PARTS,
                'stagger_after': STAGGER_AFTER,
                'rest_most': REST_MOST,
                'enough_swings': ENOUGH_SWINGS,
            },
        }
        for half in (scan.TRAIN, scan.CHECK):
            read_takes = gather([args.root / name for name in split[half]], args.jobs)
            found[half] = measure([one for one in read_takes if 'skipped' not in one])
        path.write_text(json.dumps(found, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    (args.out / 'SWINGS.md').write_text(render(found), encoding='utf-8')
    print(f'{args.out / "SWINGS.md"}, swings.json written', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
