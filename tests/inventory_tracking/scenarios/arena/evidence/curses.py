"""The curses monsters put on the character in the takes: CURSES.md and curses.json.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.evidence.curses [--jobs N] [--no-cache]

reads every take of `split.json` and every take recorded since (named after the split's last), and
writes `CURSES.md` and `curses.json` beside this file. The takes come in four groups: `train` and
`check` are split.json's halves, `since_train` and `since_check` the takes recorded since, put in a
half by the split's own rule (scan.half: by the take's name). Nothing here is fitted, and **nothing
is fitted from it yet**: on the train half no curse was read to begin or to end, and one reading in
all shows one (CURSES.md says how many each group holds). `--render` writes CURSES.md again from curses.json.

What shows a curse. The recorder writes the character's resistances with each `hurt` event (the stat
list's own numbers, record.RESIST_STATS: physical, fire, lightning, cold, poison) since 2026-10-11
22:53 UTC, and once into the manifest at the take's start. **Nothing else in a take holds them**: a
frame's row has the life and the mana and no other stat, and no state of the character. So the
resistances are known only at the moments the character lost life, and a curse that came and went
between two drops was never seen. A reading is laid against the character's own levels (`levels`):

- the physical resistance against the highest seen in any take;
- the four elemental ones against the highest seen with the same weapons. Another set of weapons moves
  the four by different amounts, so which set is held shows in their differences (`shape`: fire,
  lightning and cold less the poison one), and a fall of all four alike under that set's highest is no
  swap. A shape seen with one level only says nothing (an aura that leaves the poison one alone gives
  such a shape: one reading in the takes).

The state of a reading is those two falls (`state`): 'physical -50', 'elemental -55', both, or none.
Which curse a fall is, is not in a take; the sizes are those of the game's tables for Amplify Damage
(100) and, by the readings beside Oblivion Knights only, of their two curse skills.

Who curses. The types whose monstats AI is one of SKILLS' (the bundled tables name the AI of each type;
the skills of an AI and the mode it uses them in are monstats' `Skill1-8` and `Sk1-8mode`, which are
not bundled: SKILLS restates them, and a test lays it against a d2data checkout where there is one).
Both AIs curse in the mode `S2` (CAST_MODE), and an Oblivion Knight does nothing else in it, so each
run of its frames in that mode is a cast of a curse, seen in every take whether or not the resistances
were read. A Succubus witch also shoots in it: her casts are an upper bound. A unique with the
enchantment `curse` (CURSED) puts Amplify Damage on what it hits: such a one near is noted.

What a take is tallied into (`tally`, cached per take):

- `samples`: the readings, each with the index of the frame it was read at;
- `near`: seconds cursers of each AI stood at each distance from the character (BANDS);
- `casts`: each cast of a curser: its frame, the unit, the type, how far the character was;
- `stretches`: the runs of frames in which some curser was within RANGE of the character;
- `spans`: of each two readings in a row, who was near between them: the nearest a curser came, its
  type, the casts within RANGE, the nearest a unique with the curse enchantment came.

What cannot be had, and what stands in:

- **when a curse landed**: between two readings, `gap` seconds apart. With it, how long a curser had
  been within RANGE by then: at least `near_for`, at most `near_for_most`;
- **how long a curse lasts**: a run of readings in one state lasted at least from its first to its
  last (`least`) and at most from the reading before to the one after (`most`; None where the take
  begins or ends in it). A curse cast again while it is on is one run;
- **whether a cast reached the character**: a cast is laid against the reading before it and the first
  within AFTER frames after it (`landing`), by how far the curser was. Most casts have no such reading.
"""

import argparse
import bisect
import hashlib
import inspect
import itertools
import json
import math
import os
import sys
import time
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from multiprocessing import get_context
from pathlib import Path
from typing import Any

from inventory_tracking.combat.hurts import ATTACK_MODES, COLD, FIRE, Sightings, enchantments
from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.takes import Take
from inventory_tracking.combat.timeline import GAME_RATE
from tests.inventory_tracking.scenarios.arena.evidence import blows, scan
from tests.inventory_tracking.scenarios.arena.evidence.blows import Moment, Readings, Roster, name_of
from tests.inventory_tracking.scenarios.arena.evidence.rates import STEP, quantile


HERE = Path(__file__).parent
SPLIT = HERE / 'split.json'
CACHE = scan.CACHE / 'curses'
DUMP = scan.REPO / 'third-parties' / 'd2data' / 'json'  # the game's tables whole, where checked out
# monstats: the skills an AI's types use in the mode `S2` (the same for every type of the AI).
SKILLS: dict[str, dict[str, str]] = {
    'OblivionKnight': {'Decrepify': 'S2', 'MonCurseCast': 'S2'},
    'SuccubusWitch': {
        'Amplify Damage': 'S2',
        'Weaken': 'S2',
        'Defense Curse': 'S2',
        'Blood Mana': 'S2',
        'SuccubusBolt': 'S2',
    },
}
CURSERS: dict[int, str] = {
    int(txt): row['AI'] for txt, row in tables()['monsters'].items() if row.get('AI') in SKILLS
}  # txt -> its AI
# Monster modes run death, neutral, walk, get hit, attack 1, attack 2, block, cast, skill 1, skill 2
# (third-parties/d2go npc_mode.go; hurts.ATTACK_MODES holds 7 to 11 as cast and skills 1-4).
CAST_MODE = 9
assert CAST_MODE in ATTACK_MODES
CURSED = 7  # monumod `curse`, between hurts' `strong` 5, `fire` 9 and `cold` 18 of the same table
assert FIRE == CURSED + 2 < COLD
RANGE = 20.0  # units: a curser this near counts as near (sim/monsters.py AWARE); the bands say how near
BANDS = (0.0, 5.0, 10.0, 15.0, RANGE, 30.0, 40.0)  # units from a curser to the character
AFTER = 75  # frames after a cast in which a reading is taken to show what it did (3 s)
NONE = 'none'
LANDING = ('casts', 'read', 'cursed', 'clean_before', 'cursed_after_clean')  # what a cast is counted into
SINCE = 'since'
GROUPS = (scan.TRAIN, scan.CHECK, f'{SINCE}_{scan.TRAIN}', f'{SINCE}_{scan.CHECK}')
_SEEN: Sightings = {}


def table_skills() -> dict[str, dict[str, str]]:
    """SKILLS as the game's monstats gives it (DUMP): of each AI the skills its types use in `S2`."""
    found: dict[str, dict[str, str]] = {}
    for row in json.loads((DUMP / 'monstats.json').read_text()).values():
        if row.get('AI') not in SKILLS or row.get('*hcIdx') is None:
            continue
        mine = {row[f'Skill{slot}']: row[f'Sk{slot}mode'] for slot in range(1, 9) if row.get(f'Sk{slot}mode') == 'S2'}
        assert found.setdefault(row['AI'], mine) == mine, f'{row["Id"]}: other skills than its AI has elsewhere'
    return found


def band_of(away: float) -> int | None:
    """The index of the band of BANDS `away` is in; None beyond the last."""
    return next((index for index, edge in enumerate(BANDS[1:]) if away <= edge), None)


def tally(take_name: str, moments: Sequence[Moment], readings: Readings, roster: Roster) -> dict[str, Any]:
    """One take's readings and cursers (the module text)."""
    clocks = [moment.t for moment in moments]
    first = [] if readings.first is None or not moments else [(moments[0].t, readings.first)]
    samples: list[list[Any]] = [
        [max(bisect.bisect_right(clocks, clock) - 1, 0), [*resists]] for clock, resists in [*first, *readings.later]
    ]
    cursed = {unit for unit in roster.units if CURSED in (roster.mods(unit) or ())}
    near = {ai: [0.0] * (len(BANDS) - 1) for ai in SKILLS}
    casts: list[list[Any]] = []
    stretches: list[list[int]] = []
    # Per frame: the nearest curser (distance, type), the nearest unique with the curse enchantment.
    closest: list[tuple[float, int] | None] = []
    hexed: list[float | None] = []
    casting: set[int] = set()
    units: set[int] = set()
    seconds = 0.0
    for position, moment in enumerate(moments):
        step = min(moments[position + 1].t - moment.t, STEP) if position + 1 < len(moments) else 0.0
        hero = moment.hero
        if hero is not None:
            seconds += step
        nearest: tuple[float, int] | None = None
        curse: float | None = None
        now: set[int] = set()
        for monster in moment.foes:
            away = None if hero is None else math.dist(monster.at, hero.at)
            if monster.unit in cursed and away is not None and (curse is None or away < curse):
                curse = away
            ai = CURSERS.get(monster.txt)
            if ai is None:
                continue
            units.add(monster.unit)
            if monster.mode == CAST_MODE:
                now.add(monster.unit)
                if monster.unit not in casting:
                    casts.append([moment.index, monster.unit, monster.txt, None if away is None else round(away, 1)])
            if away is None:
                continue
            band = band_of(away)
            if band is not None:
                near[ai][band] += step
            if nearest is None or away < nearest[0]:
                nearest = (away, monster.txt)
        casting = now
        closest.append(nearest)
        hexed.append(curse)
        if nearest is not None and nearest[0] <= RANGE:
            if stretches and stretches[-1][1] == moment.index - 1:
                stretches[-1][1] = moment.index
            else:
                stretches.append([moment.index, moment.index])
    spans = []
    for (start, _before), (end, _after) in itertools.pairwise(samples):
        seen = [found for found in closest[start : end + 1] if found is not None]
        cursers = min(seen, default=None)
        curses = [away for away in hexed[start : end + 1] if away is not None]
        spans.append(
            {
                'nearest': None if cursers is None else round(cursers[0], 1),
                'txt': None if cursers is None else cursers[1],
                'casts': sum(start <= cast[0] <= end and cast[3] is not None and cast[3] <= RANGE for cast in casts),
                'cursed': round(min(curses), 1) if curses else None,
            }
        )
    return {
        'take': take_name,
        'area': next((moment.hero.area for moment in moments if moment.hero is not None), None),
        'seconds': round(seconds, 2),
        'samples': samples,
        'cursers': len(units),
        'near': {ai: [round(spent, 2) for spent in bands] for ai, bands in near.items()},
        'casts': casts,
        'stretches': stretches,
        'spans': spans,
    }


# ---------------------------------------------------------------------------------------------------
# All takes, once each (as sparks.py).


def stamp() -> str:
    """A hash of the code that makes a take's cache file: blows.py and this module's `tally`."""
    digest = hashlib.sha1((HERE / 'blows.py').read_bytes())
    digest.update(inspect.getsource(tally).encode())
    digest.update(repr((sorted(CURSERS.items()), CAST_MODE, CURSED, RANGE, BANDS)).encode())
    return digest.hexdigest()[:12]


def read(directory: Path, seen: Sightings) -> dict[str, Any]:
    """One take's tally; `skipped` says why there is none."""
    name = directory.name
    try:
        take = Take.load(directory)
    except (OSError, ValueError) as exc:
        return {'take': name, 'skipped': f'not read ({exc})'}
    if take.schema < 2 or not take.frames:
        return {'take': name, 'skipped': 'schema 1 or no frames'}
    return tally(name, list(blows.walk(take)), Readings(take), Roster(take, enchantments(seen, take)))


def _work(job: tuple[Path, Path | None, str]) -> dict[str, Any]:
    directory, cache, mark = job
    if cache is None:
        return read(directory, _SEEN)
    path = cache / f'{directory.name}.{mark}.json'
    if path.exists():
        return json.loads(path.read_text())
    found = read(directory, _SEEN)
    for old in cache.glob(f'{directory.name}.*.json'):
        old.unlink()
    path.write_text(json.dumps(found, separators=(',', ':')))
    return found


def gather(
    directories: Sequence[Path],
    *,
    cache: Path | None = CACHE,
    probes: Iterable[Path] | None = None,
    jobs: int | None = None,
    progress: bool = True,
) -> list[dict[str, Any]]:
    """`read` of every take, from the cache where it holds one, in `jobs` processes (as scan.scan)."""
    global _SEEN  # the workers inherit it by fork
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
    logs = sorted(scan.PROBES.glob('*/terror-probe.jsonl')) if probes is None else sorted(probes)
    began = time.monotonic()
    _SEEN = scan.probe_sightings(logs, None if cache is None else cache.parent)
    work = [(directory, cache, stamp()) for directory in directories]
    jobs = jobs or min(os.cpu_count() or 1, 16)
    if jobs <= 1 or len(work) <= 1:
        return [_work(job) for job in work]
    found = []
    with get_context('fork').Pool(jobs) as pool:
        for done, result in enumerate(pool.imap(_work, work, chunksize=2), 1):
            found.append(result)
            if progress and (done % 100 == 0 or done == len(work)):
                print(f'{done}/{len(work)} takes, {time.monotonic() - began:.0f} s', file=sys.stderr)
    return found


# ---------------------------------------------------------------------------------------------------
# What a set of takes measures.


def shape(resists: Sequence[int]) -> str:
    """Which weapons a reading was taken with: fire, lightning and cold less the poison one."""
    return ','.join(str(value - resists[4]) for value in resists[1:4])


def levels(tallies: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The character's own levels over all `tallies`: the highest physical resistance read, and of each
    shape the highest poison one. One character's, and no fit: every group is read against the same."""
    physical: int | None = None
    sets: dict[str, int] = {}
    for one in tallies:
        for _frame, resists in one['samples']:
            physical = resists[0] if physical is None else max(physical, resists[0])
            sets[shape(resists)] = max(sets.get(shape(resists), resists[4]), resists[4])
    return {'physical': physical, 'sets': sets}


def state(resists: Sequence[int], known: Mapping[str, Any]) -> str:
    """The falls of a reading under the character's levels: NONE, 'physical -50', 'elemental -55' or both."""
    physical = resists[0] - known['physical']
    elemental = resists[4] - known['sets'][shape(resists)]
    parts = [f'{name} {fall}' for name, fall in (('physical', physical), ('elemental', elemental)) if fall]
    return ' + '.join(parts) or NONE


def spread(values: Sequence[float]) -> dict[str, Any]:
    return {
        'n': len(values),
        'p50': quantile(values, 0.5),
        'p90': quantile(values, 0.9),
        'max': max(values, default=None),
    }


def measure(tallies: Sequence[Mapping[str, Any]], known: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """What `tallies` show of the curses, read against the levels `known` (None: their own)."""
    known = levels(tallies) if known is None else known
    states: Counter[str] = Counter()
    onsets: list[dict[str, Any]] = []
    offsets: list[dict[str, Any]] = []
    spells: list[dict[str, Any]] = []
    gaps: list[float] = []
    near = {ai: [0.0] * (len(BANDS) - 1) for ai in SKILLS}
    cast = {ai: [0] * (len(BANDS) - 1) for ai in SKILLS}
    landing = [dict.fromkeys(LANDING, 0) for _ in BANDS[1:]]
    near_sampled = 0.0
    for one in tallies:
        samples = [(frame, state(resists, known), shape(resists)) for frame, resists in one['samples']]
        states.update(found for _frame, found, _shape in samples)
        for ai, bands in one['near'].items():
            near[ai] = [total + spent for total, spent in zip(near[ai], bands, strict=True)]
        frames = [frame for frame, _state, _shape in samples]
        if samples:
            near_sampled += sum(last - first for first, last in one['stretches']) / GAME_RATE
        for frame, _unit, txt, away in one['casts']:
            band = None if away is None else band_of(away)
            if band is None:
                continue
            cast[CURSERS[txt]][band] += 1
            row = landing[band]
            row['casts'] += 1
            at = bisect.bisect_right(frames, frame)
            before = samples[at - 1][1] if at else None
            after = samples[at][1] if at < len(samples) and samples[at][0] <= frame + AFTER else None
            row['read'] += after is not None
            row['cursed'] += after not in (None, NONE)
            row['clean_before'] += after is not None and before == NONE
            row['cursed_after_clean'] += after not in (None, NONE) and before == NONE
        run = 0  # the index of the first reading of the run of one state the walk is in
        for index, ((start, before, set_before), (end, after, set_after)) in enumerate(itertools.pairwise(samples)):
            gap = (end - start) / GAME_RATE
            gaps.append(gap)
            if before == after:
                continue
            span = one['spans'][index]
            stretch = next((s for s in reversed(one['stretches']) if s[0] <= end), None)
            there = stretch is not None and stretch[1] >= start
            row = {
                'take': one['take'],
                't': round(end / GAME_RATE, 1),
                'gap': gap,
                'from': before,
                'to': after,
                'swap': int(set_before != set_after),
                'casts': span['casts'],
                'nearest': span['nearest'],
                'txt': span['txt'],
                'name': None if span['txt'] is None else name_of(span['txt']),
                'cursed': span['cursed'],
                'near_for': max(start - stretch[0], 0) / GAME_RATE if there else None,
                'near_for_most': (end - stretch[0]) / GAME_RATE if there else None,
            }
            (offsets if after == NONE else onsets).append(row)
            if before != NONE:
                spells.append(spell(one['take'], samples, run, index, index + 1))
            run = index + 1
        if samples and samples[-1][1] != NONE:
            spells.append(spell(one['take'], samples, run, len(samples) - 1, None))
    sources: dict[str, dict[str, int]] = {}
    for onset in onsets:
        row = sources.setdefault(onset['to'], {'n': 0, 'cast': 0, 'curser': 0, 'cursed': 0, 'nobody': 0})
        row['n'] += 1
        if onset['casts']:
            row['cast'] += 1
        elif onset['nearest'] is not None and onset['nearest'] <= RANGE:
            row['curser'] += 1
        elif onset['cursed'] is not None and onset['cursed'] <= RANGE:
            row['cursed'] += 1
        else:
            row['nobody'] += 1
    by_curser = [onset for onset in onsets if onset['casts'] or (onset['nearest'] or RANGE + 1) <= RANGE]
    return {
        'takes': len(tallies),
        'seconds': round(sum(one['seconds'] for one in tallies), 1),
        'sampled_takes': sum(bool(one['samples']) for one in tallies),
        'samples': sum(len(one['samples']) for one in tallies),
        'gaps': spread(gaps),
        'curser_takes': sum(bool(one['cursers']) for one in tallies),
        'curser_sampled_takes': sum(bool(one['cursers'] and one['samples']) for one in tallies),
        'cursers': sum(one['cursers'] for one in tallies),
        'states': dict(sorted(states.items())),
        'onsets': onsets,
        'offsets': offsets,
        'sources': dict(sorted(sources.items())),
        'spells': spells,
        'near_sampled': round(near_sampled, 1),
        'onsets_by_curser': len(by_curser),
        'casting': {
            ai: [
                {
                    'from': BANDS[band],
                    'to': BANDS[band + 1],
                    'casts': cast[ai][band],
                    'seconds': round(near[ai][band], 1),
                    'rate': round(cast[ai][band] / near[ai][band], 4) if near[ai][band] else None,
                }
                for band in range(len(BANDS) - 1)
            ]
            for ai in SKILLS
        },
        'landing': [{'from': BANDS[band], 'to': BANDS[band + 1], **landing[band]} for band in range(len(landing))],
    }


def spell(
    take: str, samples: Sequence[tuple[int, str, str]], first: int, last: int, after: int | None
) -> dict[str, Any]:
    """A run of readings in one state, `first` to `last`: at least that long, at most from the reading
    before it to the reading `after` it (None where the take begins or ends in it)."""
    most = None if after is None or not first else (samples[after][0] - samples[first - 1][0]) / GAME_RATE
    return {
        'take': take,
        'state': samples[first][1],
        'readings': last - first + 1,
        'least': (samples[last][0] - samples[first][0]) / GAME_RATE,
        'most': most,
    }


# ---------------------------------------------------------------------------------------------------
# The report.


def show(value: Any, digits: int = 1) -> str:
    if value is None:
        return '-'
    return f'{value:.{digits}f}' if isinstance(value, float) else str(value)


def table(head: Sequence[str], rows: Iterable[Sequence[Any]]) -> list[str]:
    out = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    out += ['| ' + ' | '.join(show(cell) if not isinstance(cell, str) else cell for cell in row) + ' |' for row in rows]
    return [*out, '']


def render(found: Mapping[str, Any]) -> str:
    """CURSES.md from curses.json's content: `levels` and `groups` (name -> `measure`)."""
    groups = found['groups']
    names = [name for name in GROUPS if name in groups]
    known = found['levels']

    def per_group(what: str, get) -> list[Any]:
        return [what, *(get(groups[name]) for name in names)]

    def casts_within(group: Mapping[str, Any], ai: str) -> str:
        rows = [row for row in group['casting'][ai] if row['to'] <= RANGE]
        casts, seconds = sum(row['casts'] for row in rows), sum(row['seconds'] for row in rows)
        return f'{casts} in {seconds:.0f} s' + (f' ({casts / seconds:.3f}/s)' if seconds else '')

    out = [
        '# The curses monsters put on the character in the takes',
        '',
        'Generated by `uv run --offline python -m tests.inventory_tracking.scenarios.arena.evidence.curses`; do not '
        'edit by hand. `curses.json` beside this file holds the same numbers and every row; the method, and what a '
        'take cannot say, is in the module text of `curses.py`. `train` and `check` are the halves of `split.json`; '
        '`since_train` and `since_check` are the takes recorded since, put in a half by the same rule. **No number '
        'of the model is fitted from this**: the first table says why (the `train` column).',
        '',
        f"The character's own levels, over all groups: physical {known['physical']}; the poison resistance by set "
        f'of weapons (fire, lightning, cold less poison): '
        + '; '.join(f'({key}) {value}' for key, value in sorted(known['sets'].items(), key=lambda item: -item[1]))
        + '.',
        '',
        '## What the groups hold',
        '',
        *table(
            ['', *names],
            [
                per_group('takes', lambda g: g['takes']),
                per_group('seconds', lambda g: f'{g["seconds"]:,.0f}'),
                per_group('takes with a reading of the resistances', lambda g: g['sampled_takes']),
                per_group('readings', lambda g: g['samples']),
                per_group('seconds between two readings, median', lambda g: g['gaps']['p50']),
                per_group('... 90th percentile', lambda g: g['gaps']['p90']),
                per_group('takes with a curser type', lambda g: g['curser_takes']),
                per_group('... and readings', lambda g: g['curser_sampled_takes']),
                per_group('cursers seen', lambda g: g['cursers']),
                per_group(
                    f'seconds a curser was within {RANGE:.0f} units, takes with readings', lambda g: g['near_sampled']
                ),
                per_group('curses read to begin', lambda g: len(g['onsets'])),
                per_group('... with a curser near or casting', lambda g: g['onsets_by_curser']),
                per_group('curses read to end', lambda g: len(g['offsets'])),
            ],
        ),
        '## The state of the readings',
        '',
        *table(
            ['state', *names],
            [
                [label, *(groups[name]['states'].get(label, 0) for name in names)]
                for label in sorted({label for name in names for label in groups[name]['states']})
            ],
        ),
        '## Curses read to begin, by who was near between the two readings',
        '',
        f'`cast`: a curser was seen to cast within {RANGE:.0f} units between the two readings; `curser`: one was that '
        'near and no cast was seen; `cursed`: none, but a unique with the curse enchantment was that near; `nobody`: '
        'none of them (the curse came from what the take does not show, or before the take).',
        '',
        *table(
            ['group', 'to', 'n', 'cast', 'curser', 'cursed', 'nobody'],
            [
                [name, label, row['n'], row['cast'], row['curser'], row['cursed'], row['nobody']]
                for name in names
                for label, row in groups[name]['sources'].items()
            ],
        ),
        '### Each of them',
        '',
        '`gap`: seconds between the two readings; `near for`: how long a curser had been within range without a break, '
        'at the reading before and at the reading that shows the curse (the curse landed between).',
        '',
        *table(
            ['group', 'take', 't', 'from', 'to', 'gap', 'swap', 'casts', 'nearest curser', 'near for', 'cursed unique'],
            [
                [
                    name,
                    onset['take'],
                    onset['t'],
                    onset['from'],
                    onset['to'],
                    onset['gap'],
                    onset['swap'],
                    onset['casts'],
                    '-' if onset['nearest'] is None else f'{onset["nearest"]} ({onset["name"]})',
                    '-' if onset['near_for'] is None else f'{onset["near_for"]:.1f} to {onset["near_for_most"]:.1f}',
                    onset['cursed'],
                ]
                for name in names
                for onset in groups[name]['onsets']
            ],
        ),
        '## How long a state was read',
        '',
        'A run of readings in one state: at least from its first to its last reading, at most from the reading before '
        'it to the one after (`-`: the take begins or ends in it).',
        '',
        *table(
            ['group', 'take', 'state', 'readings', 'at least, s', 'at most, s'],
            [
                [name, row['take'], row['state'], row['readings'], row['least'], row['most']]
                for name in names
                for row in groups[name]['spells']
            ],
        ),
        '## Casts of a curser, from the frames (every take, read or not)',
        '',
        f'Within {RANGE:.0f} units of the character:',
        '',
        *table(['AI', *names], [[ai, *(casts_within(groups[name], ai) for name in names)] for ai in SKILLS]),
        'By distance (casts, seconds a curser stood there, casts a second):',
        '',
        *table(
            ['group', 'AI', *(f'{low:.0f}-{high:.0f}' for low, high in itertools.pairwise(BANDS))],
            [
                [name, ai, *(f'{row["casts"]} / {row["seconds"]:.0f} s' for row in groups[name]['casting'][ai])]
                for name in names
                for ai in SKILLS
                if any(row['seconds'] for row in groups[name]['casting'][ai])
            ],
        ),
        f'## A cast against the readings around it (the first within {AFTER} frames after)',
        '',
        '`read`: casts with such a reading; `cursed`: of those, the reading shows a curse; `clean before`: of those '
        'read, the reading before the cast showed none; `then cursed`: of those, the reading after shows one.',
        '',
        *table(
            ['group', 'units', 'casts', 'read', 'cursed', 'clean before', 'then cursed'],
            [
                [
                    name,
                    f'{row["from"]:.0f}-{row["to"]:.0f}',
                    row['casts'],
                    row['read'],
                    row['cursed'],
                    row['clean_before'],
                    row['cursed_after_clean'],
                ]
                for name in names
                for row in groups[name]['landing']
                if row['casts']
            ],
        ),
    ]
    return '\n'.join(out)


def grouped(root: Path, split: Mapping[str, Any]) -> dict[str, list[Path]]:
    """The take directories of each group: split.json's halves, and the takes under `root` named after
    the split's last, by the split's rule."""
    found = {half: [root / name for name in split[half]] for half in (scan.TRAIN, scan.CHECK)}
    last = max([*split[scan.TRAIN], *split[scan.CHECK]], default='')
    for directory in scan.takes_under(root):
        if directory.name > last:
            found.setdefault(f'{SINCE}_{scan.half(directory.name)}', []).append(directory)
    return found


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='The curses monsters put on the character, from all takes.')
    parser.add_argument('--root', type=Path, default=scan.ROOT, help='the directory of the takes')
    parser.add_argument('--split', type=Path, default=SPLIT, help='the halves (split.json)')
    parser.add_argument('--jobs', type=int, help='worker processes (default: the cores, 16 at most)')
    parser.add_argument('--no-cache', action='store_true', help='read every take again')
    parser.add_argument('--cache', type=Path, default=CACHE, help='where per-take results go')
    parser.add_argument('--out', type=Path, default=HERE, help='where CURSES.md and curses.json go')
    parser.add_argument('--render', action='store_true', help='write CURSES.md again from curses.json, reading no take')
    args = parser.parse_args(argv)
    path = args.out / 'curses.json'
    if args.render:
        found = json.loads(path.read_text())
    else:
        cache = None if args.no_cache else args.cache
        read_groups = {
            name: [one for one in gather(directories, cache=cache, jobs=args.jobs) if 'skipped' not in one]
            for name, directories in grouped(args.root, json.loads(args.split.read_text())).items()
        }
        known = levels([one for tallies in read_groups.values() for one in tallies])
        found = {
            'about': 'tests/inventory_tracking/scenarios/arena/evidence/curses.py: see CURSES.md; nothing is fitted '
            'from it (on the train half no curse was read to begin)',
            'split': args.split.name,
            'constants': {'range': RANGE, 'bands': BANDS, 'after': AFTER, 'cast_mode': CAST_MODE, 'cursed': CURSED},
            'cursers': {str(txt): ai for txt, ai in sorted(CURSERS.items())},
            'skills': SKILLS,
            'levels': known,
            'groups': {name: measure(tallies, known) for name, tallies in read_groups.items()},
        }
        path.write_text(json.dumps(found, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    (args.out / 'CURSES.md').write_text(render(found), encoding='utf-8')
    print(f'{args.out / "CURSES.md"}, curses.json written', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
