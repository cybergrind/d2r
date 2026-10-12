"""Many scenes played under many seeds, and the distribution that came of it (Stage 4's measuring tool).

The arena's monsters hit with rare, random blows, so one play of a scene proves nothing: another seed can
end dead or untouched. A safety rule is judged by a distribution: many scenes by many seeds, before and
after a change. This module plays the cases (`trial`), says what each set of plays came to (`stats`,
`summarise`, `table`) and sets two trials side by side with rules that are conservative on purpose
(`judge`, `report`).

Case sets: `threat_cases` (the 16 threat scenes), `basic_cases` (the hand-built scenes that make sense to
play) and `fixture_cases` (the scenes cut from recorded battles, whatever `fixtures/` holds when it runs).

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.trials --set all --seeds 30 --jobs 8

Nothing here looks at wall time: the same arguments give the same output byte for byte.
"""

import argparse
import json
import math
import multiprocessing
import re
import sys
import traceback
from collections.abc import Collection, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, fields
from pathlib import Path

from inventory_tracking.config import PLAYER_HEALING
from inventory_tracking.macros.runner import ATTACK, PICKUP
from tests.inventory_tracking.scenarios.arena import scenes_basic, scenes_threat
from tests.inventory_tracking.scenarios.arena.driver import Press, play
from tests.inventory_tracking.scenarios.arena.result import Result
from tests.inventory_tracking.scenarios.arena.scene import Scene, load


FIXTURES = Path(__file__).parent / 'fixtures'
# A fixture scene is `<take>-<frame>-<tick>-<kind>.json` (cut.py); trusted.json, the *.md notes and the
# TRIALS-* saves do not match.
FIXTURE_NAME = re.compile(r'^\d{8}T\d{6}Z-\d+-\d+-(?P<kind>[A-Za-z0-9]+)\.json$')
RESULT_FIELDS = tuple(f.name for f in fields(Result) if f.name != 'said')


@dataclass(frozen=True)
class Case:
    """One scene and how it is played: the presses, the horizon and the kind it is counted under."""

    name: str
    scene: Scene
    presses: tuple[Press, ...]
    seconds: float
    kind: str = ''  # 'threat', 'basic', or the fixture's kind (burst, burst15, potions, death, long, stuck, ...)
    auras: Mapping[int, float] | None = None


@dataclass(frozen=True)
class Stats:
    """What a set of plays came to."""

    plays: int
    deaths: int
    death_share: float  # deaths / plays
    taken_mean: float
    taken_p50: float
    taken_p95: float  # the heavy tail: life lost in the worst twentieth of plays
    taken_share_p95: float  # the same as a share of the character's max life
    cleared_share: float  # plays in which every hostile died
    clear_p50: float | None  # median seconds to clear, over the plays that cleared; None if none did
    potions_mean: float
    casts_mean: float
    moved_mean: float


@dataclass(frozen=True)
class Failure:
    """A play that raised: which case, which seed, and what."""

    case: str
    seed: int
    error: str


# -- playing --------------------------------------------------------------------------------------------


def _one(job: tuple[Case, int, dict]) -> tuple[str, int, Result | None, str]:
    """One play, in whatever process; an exception is returned as text, never raised."""
    case, seed, options = job
    try:
        result = play(case.scene.copy(), case.presses, case.seconds, seed=seed, auras=case.auras, **options)
    except Exception as failure:
        text = ''.join(traceback.format_exception_only(type(failure), failure)).strip()
        return case.name, seed, None, text
    return case.name, seed, result, ''


def trial(
    cases: Sequence[Case],
    seeds: Sequence[int],
    *,
    jobs: int = 1,
    errors: list[Failure] | None = None,
    **play_options,
) -> dict[str, list[Result]]:
    """Play every case once per seed with `driver.play`; results by case name, in seed order.

    `jobs` > 1 plays them in a process pool (the plays are independent and deterministic per seed), with
    the same results as `jobs=1`. `play_options` go to `driver.play` for every play. A play that raises is
    not hidden: with `errors` given the failure is appended to it and the case (every seed of it) is left
    out of the result; with `errors` None the first failure is raised after all have been played."""
    work = [(case, seed, play_options) for case in cases for seed in seeds]
    if jobs > 1 and len(work) > 1:
        context = multiprocessing.get_context('spawn')
        with ProcessPoolExecutor(max_workers=jobs, mp_context=context) as pool:
            done = list(pool.map(_one, work, chunksize=1))
    else:
        done = [_one(job) for job in work]
    failures = [Failure(name, seed, text) for name, seed, result, text in done if result is None]
    if failures and errors is None:
        first = failures[0]
        raise RuntimeError(f'{len(failures)} plays raised; first: {first.case} seed {first.seed}: {first.error}')
    if errors is not None:
        errors.extend(failures)
    broken = {failure.case for failure in failures}
    found: dict[str, list[Result]] = {case.name: [] for case in cases if case.name not in broken}
    for name, _seed, result, _text in done:
        if result is not None and name in found:
            found[name].append(result)
    return found


# -- what the plays came to -----------------------------------------------------------------------------


def _percentile(values: Sequence[float], share: float) -> float:
    """The `share` quantile of `values` by linear interpolation between order statistics."""
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = share * (len(ordered) - 1)
    low = math.floor(rank)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def _stats(results: Sequence[Result], lives: Sequence[float]) -> Stats:
    """`stats` with the max life of each play given (a pooled set mixes characters)."""
    count = len(results)
    if count == 0:
        raise ValueError('no plays to count')
    taken = [r.taken for r in results]
    shares = [r.taken / life for r, life in zip(results, lives, strict=True)]
    deaths = sum(1 for r in results if r.dead_at is not None)
    clears = [r.cleared_at for r in results if r.cleared_at is not None]
    return Stats(
        plays=count,
        deaths=deaths,
        death_share=deaths / count,
        taken_mean=sum(taken) / count,
        taken_p50=_percentile(taken, 0.5),
        taken_p95=_percentile(taken, 0.95),
        taken_share_p95=_percentile(shares, 0.95),
        cleared_share=len(clears) / count,
        clear_p50=_percentile(clears, 0.5) if clears else None,
        potions_mean=sum(len(r.potions) for r in results) / count,
        casts_mean=sum(r.casts for r in results) / count,
        moved_mean=sum(r.moved for r in results) / count,
    )


def stats(results: Sequence[Result], max_life: float) -> Stats:
    """What `results` (plays of one character, `max_life`) came to."""
    return _stats(results, [max_life] * len(results))


def summarise(trials: Mapping[str, Sequence[Result]], cases: Sequence[Case]) -> dict[str, Stats]:
    """Stats per case name, per kind (key 'kind:<kind>') and over everything (key 'all'). Cases without
    results (they raised) are left out."""
    return _summarise(trials, {case.name: (case.kind, case.scene.hero.max_life) for case in cases})


def _summarise(trials: Mapping[str, Sequence[Result]], meta: Mapping[str, tuple[str, float]]) -> dict[str, Stats]:
    """`summarise` with each case's (kind, max life) given, which is also what a saved trial holds."""
    summary: dict[str, Stats] = {}
    groups: dict[str, tuple[list[Result], list[float]]] = {'all': ([], [])}
    for name, results in trials.items():
        if not results:
            continue
        kind, life = meta[name]
        summary[name] = stats(results, life)
        for key in ('all', f'kind:{kind}'):
            pooled = groups.setdefault(key, ([], []))
            pooled[0].extend(results)
            pooled[1].extend([life] * len(results))
    pooled_stats = {key: _stats(*pair) for key, pair in groups.items() if pair[0]}
    return {**pooled_stats, **summary}


def _order(keys: Sequence[str]) -> list[str]:
    """'all' first, then the kinds, then the cases, each group in the order given."""
    return (
        [k for k in keys if k == 'all']
        + [k for k in keys if k.startswith('kind:')]
        + [k for k in keys if k != 'all' and not k.startswith('kind:')]
    )


def table(summary: Mapping[str, Stats]) -> str:
    """A fixed-width table, one row per key ('all' first, then kinds, then cases)."""
    headers = [
        'key',
        'plays',
        'dead%',
        'taken',
        'p50',
        'p95',
        'p95%life',
        'clear%',
        'clr p50',
        'pots',
        'casts',
        'moved',
    ]
    rows = []
    for key in _order(list(summary)):
        s = summary[key]
        rows.append(
            [
                key,
                str(s.plays),
                f'{100 * s.death_share:.1f}',
                f'{s.taken_mean:.0f}',
                f'{s.taken_p50:.0f}',
                f'{s.taken_p95:.0f}',
                f'{100 * s.taken_share_p95:.0f}',
                f'{100 * s.cleared_share:.0f}',
                '-' if s.clear_p50 is None else f'{s.clear_p50:.1f}',
                f'{s.potions_mean:.1f}',
                f'{s.casts_mean:.0f}',
                f'{s.moved_mean:.0f}',
            ]
        )
    widths = [max(len(row[i]) for row in [headers, *rows]) for i in range(len(headers))]

    def line(cells: Sequence[str]) -> str:
        parts = [c.ljust(w) if i == 0 else c.rjust(w) for i, (c, w) in enumerate(zip(cells, widths, strict=True))]
        return '  '.join(parts).rstrip()

    return '\n'.join([line(headers), line(['-' * w for w in widths]), *(line(r) for r in rows)])


# -- before and after -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Verdict:
    """What changed for one key between two trials."""

    key: str
    before: Stats
    after: Stats
    change: str  # 'better' | 'worse' | 'same' | 'mixed'
    why: str  # the numbers that decided it, one line


def _death_differs(before: Stats, after: Stats) -> bool:
    """Two-proportion z test (pooled, continuity correction) at the two-sided 5% level (|z| >= 1.96)."""
    n1, n2 = before.plays, after.plays
    pooled = (before.deaths + after.deaths) / (n1 + n2)
    spread = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if spread == 0:
        return False
    gap = abs(before.death_share - after.death_share)
    gap = max(0.0, gap - 0.5 * (1 / n1 + 1 / n2))
    return gap / spread >= 1.96


def _moved(old: float, new: float, relative: float, absolute: float) -> int:
    """-1 if `new` is lower than `old` by at least `relative` of old and `absolute` units, 1 if higher, else 0."""
    gap = new - old
    if abs(gap) >= absolute and abs(gap) >= relative * abs(old):
        return 1 if gap > 0 else -1
    return 0


def _counted(old: Stats, new: Stats) -> tuple[list[str], list[str]]:
    """The differences that count between two Stats, as (improvements, worsenings), each a short phrase."""
    good: list[str] = []
    bad: list[str] = []

    def note(sign: int, text: str, lower_is_good: bool = True) -> None:
        if sign != 0:
            (good if (sign < 0) == lower_is_good else bad).append(text)

    if _death_differs(old, new) and abs(new.death_share - old.death_share) >= 0.02:
        sign = -1 if new.death_share < old.death_share else 1
        note(sign, f'deaths {100 * old.death_share:.1f}% -> {100 * new.death_share:.1f}%')
    note(_moved(old.taken_p95, new.taken_p95, 0.10, 20), f'p95 {old.taken_p95:.0f} -> {new.taken_p95:.0f}')
    note(_moved(old.taken_mean, new.taken_mean, 0.10, 20), f'taken {old.taken_mean:.0f} -> {new.taken_mean:.0f}')
    if old.clear_p50 is not None and new.clear_p50 is not None:
        note(_moved(old.clear_p50, new.clear_p50, 0.10, 0.3), f'clear p50 {old.clear_p50:.1f}s -> {new.clear_p50:.1f}s')
    if abs(new.cleared_share - old.cleared_share) >= 0.05:
        sign = -1 if new.cleared_share < old.cleared_share else 1
        note(sign, f'cleared {100 * old.cleared_share:.0f}% -> {100 * new.cleared_share:.0f}%', lower_is_good=False)
    return good, bad


def judge(before: Mapping[str, Stats], after: Mapping[str, Stats], *, plays_floor: int = 30) -> list[Verdict]:
    """Say, per key, whether `after` is better or worse than `before`. Simple and conservative:

    - Only keys present in both, with at least `plays_floor` plays on each side, are compared; the rest
      are 'same' with why 'too few plays'.
    - Deaths count only if the death shares differ beyond chance (two-proportion z test with pooled
      variance and a continuity correction, |z| >= 1.96, about 5% two-sided) AND by at least 2 percentage
      points.
    - `taken_p95` and `taken_mean` count only if they differ by at least 10% of the before value AND at
      least 20 points of life.
    - `clear_p50` counts if it differs by at least 10% AND 0.3 s (only when both sides cleared some play);
      `cleared_share` if it differs by at least 5 percentage points.
    - Lower deaths, taken and clear time are good; a higher cleared share is good.
    - 'better': something counted improves and nothing counted worsens; 'worse': the mirror; 'mixed':
      something counted improves and something worsens (`why` lists both); 'same': nothing counts.

    Order: 'all' first, then kinds, then cases; within each group worse, mixed, better, same."""
    verdicts = []
    for key in _order([k for k in before if k in after]):
        old, new = before[key], after[key]
        if min(old.plays, new.plays) < plays_floor:
            verdicts.append(Verdict(key, old, new, 'same', 'too few plays'))
            continue
        good, bad = _counted(old, new)
        if good and bad:
            change, why = 'mixed', f'better: {"; ".join(good)} | worse: {"; ".join(bad)}'
        elif good:
            change, why = 'better', '; '.join(good)
        elif bad:
            change, why = 'worse', '; '.join(bad)
        else:
            change, why = 'same', 'nothing beyond the thresholds'
        verdicts.append(Verdict(key, old, new, change, why))
    rank = {'worse': 0, 'mixed': 1, 'better': 2, 'same': 3}
    group = {'all': 0}
    return sorted(
        verdicts, key=lambda v: (group.get(v.key, 1 if v.key.startswith('kind:') else 2), rank[v.change])
    )  # sorted is stable: the order within a group and change stays the order of `before`


def report(verdicts: Sequence[Verdict]) -> str:
    """One line per verdict: the change, the key and the numbers that decided it, then a count line."""
    width = max((len(v.key) for v in verdicts), default=3)
    lines = [f'{v.change:<6}  {v.key.ljust(width)}  {v.why}'.rstrip() for v in verdicts]
    counts = {c: sum(1 for v in verdicts if v.change == c) for c in ('worse', 'mixed', 'better', 'same')}
    lines.append(', '.join(f'{n} {c}' for c, n in counts.items()))
    return '\n'.join(lines)


# -- case sets ------------------------------------------------------------------------------------------


def threat_cases() -> list[Case]:
    """The 16 threat scenes with their horizons and auras; ATTACK pressed at 0."""
    scenes, until, given = scenes_threat.threat_scenes(), scenes_threat.horizons(), scenes_threat.auras()
    return [
        Case(name, scene, (Press(0.0, ATTACK),), until[name], 'threat', given.get(name))
        for name, scene in scenes.items()
    ]


def basic_cases() -> list[Case]:
    """The hand-built scenes of scenes_basic.py that make sense to play.

    Chosen: the four fights (one in the open 10 s, a pack at low life 10 s, two gloams 15 s) and the archer
    behind a wall (20 s) with ATTACK at 0; the three that need a step (one out of reach, a bovine behind a
    wall, an archer at a gap) with ATTACK at 0 and one PICKUP at 0.5 (which starts the mode's own moving),
    20 s; the potion on the ground with PICKUP at 0, 5 s. `afoot` is a helper, not a scene."""
    attack = (Press(0.0, ATTACK),)
    step = (Press(0.0, ATTACK), Press(0.5, PICKUP))
    plan = [
        (scenes_basic.one_in_the_open, attack, 10.0),
        (scenes_basic.pack_at_low_life, attack, 10.0),
        (scenes_basic.archer_behind_a_wall, attack, 20.0),
        (scenes_basic.gloams, attack, 15.0),
        (scenes_basic.potion_on_the_ground, (Press(0.0, PICKUP),), 5.0),
        (scenes_basic.one_out_of_reach, step, 20.0),
        (scenes_basic.bovine_behind_a_wall, step, 20.0),
        (scenes_basic.archer_at_a_gap, step, 20.0),
    ]
    cases = []
    for build, presses, seconds in plan:
        scene = build()
        cases.append(Case(scene.name, scene, presses, seconds, 'basic'))
    return cases


def fixture_cases(kinds: Collection[str] | None = None, *, seconds: float = 10.0) -> list[Case]:
    """Every scene in fixtures/ (files named `<take>-<frame>-<tick>-<kind>.json`; anything else, such as
    trusted.json or TRIALS-*.json, is skipped), optionally only some kinds. Each is played with attack
    mode on at 0 and one pickup press at 0.3 s: the pickup press with nothing to pick up is the mode's own
    step (driver.py `Play.execute`: `hunter.step`, after which the mode resumes), as test_moves.py does."""
    cases = []
    for path in sorted(FIXTURES.glob('*.json')):
        found = FIXTURE_NAME.match(path.name)
        if found is None or (kinds is not None and found['kind'] not in kinds):
            continue
        cases.append(Case(path.stem, load(path), (Press(0.0, ATTACK), Press(0.3, PICKUP)), seconds, found['kind']))
    return cases


# -- saving ---------------------------------------------------------------------------------------------


def save(trials: Mapping[str, Sequence[Result]], seeds: Sequence[int], path: Path, cases: Sequence[Case] = ()) -> None:
    """Write the per-play results (every Result field but `said`) as compact JSON, per case in seed order,
    with each case's kind and max life so that the file can be summarised without the scenes."""
    data = {
        'seeds': list(seeds),
        'cases': {name: [[getattr(r, f) for f in RESULT_FIELDS] for r in results] for name, results in trials.items()},
        'fields': list(RESULT_FIELDS),
        'meta': {c.name: [c.kind, c.scene.hero.max_life] for c in cases if c.name in trials},
    }
    path.write_text(json.dumps(data, separators=(',', ':')) + '\n', encoding='utf-8')


def load_trials(path: Path) -> dict[str, list[Result]]:
    """Read back what `save` wrote."""
    data = json.loads(path.read_text(encoding='utf-8'))
    names = data['fields']
    out: dict[str, list[Result]] = {}
    for name, rows in data['cases'].items():
        out[name] = []
        for row in rows:
            values = dict(zip(names, row, strict=True))
            values['potions'] = [tuple(p) for p in values['potions']]
            out[name].append(Result(**values))
    return out


def summarise_saved(path: Path) -> dict[str, Stats]:
    """The summary of a saved trial, from the kinds and max lives it holds."""
    data = json.loads(path.read_text(encoding='utf-8'))
    meta = {name: (kind, life) for name, (kind, life) in data['meta'].items()}
    return _summarise(load_trials(path), meta)


# -- command line ---------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    """Run a trial from the command line; print its table (and the judgement against a saved one)."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--set', choices=('threat', 'basic', 'fixtures', 'all'), default='all')
    parser.add_argument('--kinds', nargs='*', default=None, help='fixture kinds to play (default: all)')
    parser.add_argument('--seeds', type=int, default=30, help='seeds 1..N')
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--seconds', type=float, default=10.0, help='length of a fixture play')
    parser.add_argument('--save', type=Path, default=None)
    parser.add_argument('--against', type=Path, default=None)
    parser.add_argument('--osd', action='store_true', help='run the standalone healer beside the macro')
    parser.add_argument('--instant-moves', action='store_true')
    args = parser.parse_args(argv)
    cases: list[Case] = []
    if args.set in ('threat', 'all'):
        cases += threat_cases()
    if args.set in ('basic', 'all'):
        cases += basic_cases()
    if args.set in ('fixtures', 'all'):
        cases += fixture_cases(args.kinds, seconds=args.seconds)
    seeds = list(range(1, args.seeds + 1))
    options: dict = {'instant_moves': args.instant_moves}
    if args.osd:
        options['osd'] = PLAYER_HEALING
    errors: list[Failure] = []
    trials = trial(cases, seeds, jobs=args.jobs, errors=errors, **options)
    summary = summarise(trials, cases)
    print(table(summary))
    if errors:
        print(f'\n{len(errors)} plays raised; their cases are left out of the summary:')
        for failure in errors:
            print(f'  {failure.case} seed {failure.seed}: {failure.error}')
    if args.save is not None:
        save(trials, seeds, args.save, cases)
    if args.against is not None:
        before = summarise_saved(args.against)
        print()
        print(report(judge(before, summary)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
