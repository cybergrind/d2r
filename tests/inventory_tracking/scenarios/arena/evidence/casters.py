"""The Chaos Sanctuary's types in the takes and in the arena, side by side: what each does and takes by how far
it stands from the character (rca/2026-10-13/sim-casters.md is written from this).

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.evidence.casters [--seeds N] [--jobs N]

For each type of sim/casters.py (Storm Caster 306, Doom Knight 310, Oblivion Knight 312, Venom Lord 362) and
each band of distance to the character (BANDS), over the frames it was alive:

- `seconds` of presence;
- `starts`: a mode begun, a second (A1 a swing, S1 and S2 a cast);
- `births`: missiles let go, by missiles.txt id, a second;
- `lost`: points the character lost, a second. In a take a drop is put on its suspects (evidence/blows.py) and
  split evenly among them, at the suspect's own distance; a drop with no suspect is on nobody (`unowned`). In
  the arena each blow is its monster's (stage.py `Cast.hurts`);
- `hits`: drops (take) or blows that took life (arena), a second, split as the points.

The takes are the Chaos Sanctuary's (area 108) of the `check` half of split.json's rule (scan.half: by the
take's name); `--half train` gives the half the timings were measured on. The arena is the four recorded
scenes (vizier-seal, seal-pack, vizier-stall: whole; cs-run with the recording's presses) played with seeds
1..N. A rate "matches" when the arena's pooled rate lies within the spread of the takes' own rates (the least
and the most of the takes with SPREAD_SECONDS of presence in the band or more).

Caveats said with every table: the takes' drops are falls of 5 points or more between two frames
(hurts.HURT_LEAST), so a stream's small ticks there are summed, under 5 lost; a take's presence is what the
client held (a far monster is not in the frames); the takes' characters fought by hand and macro alike, the
arena's plays are the macro's.
"""

import argparse
import collections
import hashlib
import json
import math
import statistics
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from inventory_tracking.combat.hurts import HURT_LEAST
from inventory_tracking.combat.sim import casters
from inventory_tracking.combat.takes import Take


HERE = Path(__file__).parent
RUNS = Path(__file__).parents[5] / 'inventory_tracking' / 'runs' / 'combat'
CACHE = HERE / 'casters.json'
TYPES = {306: 'Storm Caster', 310: 'Doom Knight', 312: 'Oblivion Knight', 362: 'Venom Lord'}
BANDS = (5, 10, 15, 20, 30, 45)  # upper edges, units; beyond the last: 'far'
MODES = {4: 'A1', 8: 'S1', 9: 'S2'}  # the take's modes a start is counted of
GAP_MOST = 0.2  # seconds: a longer gap between two frames counts this much (a pause of the recorder)
SPREAD_SECONDS = 10.0
SCENES = ('vizier-seal', 'seal-pack', 'vizier-stall', 'cs-run')


def band_of(away: float) -> str:
    for edge in BANDS:
        if away <= edge:
            return str(edge)
    return 'far'


def half_of(name: str) -> str:
    """split.json's rule: the first byte of sha1(name) even is train, odd is check."""
    return 'train' if hashlib.sha1(name.encode()).digest()[0] % 2 == 0 else 'check'


def empty() -> dict[str, Any]:
    return {'seconds': 0.0, 'starts': collections.Counter(), 'births': collections.Counter(), 'lost': 0.0, 'hits': 0.0}


def plain(tally: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    return {
        key: {name: (dict(value) if isinstance(value, Mapping) else value) for name, value in row.items()}
        for key, row in tally.items()
    }


def take_tally(directory: Path) -> dict[str, Any]:
    """One take's tally: (type, band) -> the row (module text), and what nobody is named for."""
    from tests.inventory_tracking.scenarios.arena.evidence import blows

    take = Take.load(directory)
    tally: dict[str, dict[str, Any]] = collections.defaultdict(empty)
    if take.schema < 2 or not take.frames:
        return {'take': directory.name, 'tally': {}, 'unowned': 0.0, 'seconds': 0.0}
    moments = list(blows.walk(take))
    last: dict[int, int] = {}
    born: set[tuple[int, float]] = set()
    txt_of: dict[int, int] = {}
    where: dict[int, str] = {}
    total = 0.0
    for index, moment in enumerate(moments):
        if moment.hero is None:
            continue
        nxt = moments[index + 1].t if index + 1 < len(moments) else moment.t + 0.04
        dt = min(max(nxt - moment.t, 0.0), GAP_MOST)
        total += dt
        here = moment.hero.at
        for foe in moment.foes:
            if foe.txt not in TYPES:
                continue
            txt_of[foe.unit] = foe.txt
            band = band_of(math.dist(here, foe.at))
            where[foe.unit] = band
            row = tally[f'{foe.txt}:{band}']
            row['seconds'] += dt
            if last.get(foe.unit) != foe.mode and foe.mode in MODES:
                row['starts'][MODES[foe.mode]] += 1
            last[foe.unit] = foe.mode
        for flight in moment.flying:
            if flight.key in born or flight.owner not in txt_of or flight.owner not in where:
                continue
            born.add(flight.key)
            tally[f'{txt_of[flight.owner]}:{where[flight.owner]}']['births'][str(flight.txt)] += 1
    unowned = 0.0
    for drop in blows.blows(take, None, moments):
        named = [suspect for suspect in drop['by'] if suspect.get('txt') in TYPES]
        if not drop['by']:
            unowned += drop['lost']
        for suspect in named:
            row = tally[f'{suspect["txt"]}:{band_of(suspect["away"])}']
            row['lost'] += drop['lost'] / len(drop['by'])
            row['hits'] += 1 / len(drop['by'])
    return {'take': directory.name, 'tally': plain(tally), 'unowned': unowned, 'seconds': total}


class Sampler:
    """The arena's side of a tally, taken at every game tick of a play (installed on the stage's `play_tick`)."""

    def __init__(self) -> None:
        self.tally: dict[str, dict[str, Any]] = collections.defaultdict(empty)
        self.stage: Any = None
        self.casts = self.births = self.hurts = 0
        self.until: dict[int, int] = {}
        self.where: dict[int, str] = {}

    def __call__(self, stage: Any, play: Any) -> None:
        if self.stage is not None:
            return
        self.stage = stage
        inner = stage.play_tick

        def tick() -> None:
            inner()
            self.sample(stage)

        stage.play_tick = tick

    def sample(self, stage: Any) -> None:
        pack = stage.cast.pack
        minds = pack.minds
        here = stage.here
        for unit, walker in pack.walkers.items():
            if walker.txt not in TYPES:
                continue
            band = self.where[unit] = band_of(math.dist(here, walker.at))
            row = self.tally[f'{walker.txt}:{band}']
            row['seconds'] += 1 / casters_rate()
            if walker.doing == casters.STRIKE and self.until.get(unit) != walker.until:
                row['starts']['A1'] += 1
            self.until[unit] = walker.until
        for _frame, unit, txt, skill, _aim in minds.casts[self.casts :]:
            mode = casters.data()['monsters'][str(txt)]
            slot = next((n for n in range(1, 9) if mode.get(f'Skill{n}') == skill), 1)
            self.tally[f'{txt}:{self.where.get(unit, "far")}']['starts'][mode.get(f'Sk{slot}mode', 'S1')] += 1
        self.casts = len(minds.casts)
        for _frame, unit, txt, missile, _at, _to, _ends in minds.births[self.births :]:
            self.tally[f'{txt}:{self.where.get(unit, "far")}']['births'][str(missile)] += 1
        self.births = len(minds.births)
        # As a take sees them: the tick's fall of life is a drop when it is HURT_LEAST or more, and it is put on
        # its monsters by their share of it (a take splits it evenly among its suspects; here who took what is known).
        fresh = [hurt for hurt in stage.cast.hurts[self.hurts :] if hurt.points > 0]
        self.hurts = len(stage.cast.hurts)
        total = sum(hurt.points for hurt in fresh)
        units = {hurt.unit for hurt in fresh if hurt.txt in TYPES}
        for hurt in fresh:
            if hurt.txt not in TYPES:
                continue
            row = self.tally[f'{hurt.txt}:{self.where.get(hurt.unit, "far")}']
            row['all'] = row.get('all', 0.0) + hurt.points
            if total >= HURT_LEAST:
                row['lost'] += hurt.points
        if total >= HURT_LEAST:
            for unit in units:
                txt = pack.walkers[unit].txt if unit in pack.walkers else next(h.txt for h in fresh if h.unit == unit)
                self.tally[f'{txt}:{self.where.get(unit, "far")}']['hits'] += 1 / len(units)


def casters_rate() -> float:
    from inventory_tracking.combat.timeline import GAME_RATE

    return GAME_RATE


def arena_tally(job: tuple[str, int, bool]) -> dict[str, Any]:
    """One play of a scene: its tally and its totals. `played` False: the casters as before (casters.PLAYED)."""
    from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, load

    name, seed, played = job
    casters.PLAYED = played
    sampler = Sampler()
    import time

    began = time.perf_counter()
    outcome = load(FIXTURES / f'{name}.json').play(seed=seed, each_tick=sampler)
    return {
        'scene': name,
        'seed': seed,
        'played': played,
        'tally': plain(sampler.tally),
        'taken': outcome.taken,
        'low': outcome.low,
        'dead_at': outcome.dead_at,
        'kills': len(outcome.kills),
        'seconds': outcome.seconds,
        'cost': time.perf_counter() - began,
        'by': {f'{who} {kind}': points for (who, kind), points in outcome.taken_by().items()},
    }


def pooled(tallies: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = collections.defaultdict(empty)
    for tally in tallies:
        for key, row in tally.items():
            into = found[key]
            into['seconds'] += row['seconds']
            into['lost'] += row['lost']
            into['hits'] += row['hits']
            into['all'] = into.get('all', 0.0) + row.get('all', row['lost'])
            into['starts'].update(row['starts'])
            into['births'].update(row['births'])
    return found


def rates(row: Mapping[str, Any]) -> dict[str, float]:
    seconds = row['seconds'] or 1e-9
    found = {'lost': row['lost'] / seconds, 'hits': row['hits'] / seconds, 'all': row.get('all', row['lost']) / seconds}
    for mode, count in row['starts'].items():
        found[mode] = count / seconds
    for missile, count in row['births'].items():
        found[f'm{missile}'] = count / seconds
    return found


def spread(tallies: Sequence[Mapping[str, Any]], key: str, what: str) -> tuple[float, float] | None:
    """The least and the most of the takes' own rates of `what` in `key`, of the takes with SPREAD_SECONDS there."""
    found = [rates(t[key]).get(what, 0.0) for t in tallies if key in t and t[key]['seconds'] >= SPREAD_SECONDS]
    return (min(found), max(found)) if len(found) >= 2 else None


def gather_takes(half: str, jobs: int) -> list[dict[str, Any]]:
    dirs = [path for path in sorted(RUNS.glob('*-108')) if half_of(path.name) == half]
    with ProcessPoolExecutor(jobs) as pool:
        return [found for found in pool.map(take_tally, dirs) if found['tally']]


def gather_arena(
    seeds: int, jobs: int, scenes: Sequence[str] = SCENES, played: Sequence[bool] = (False, True)
) -> list[dict[str, Any]]:
    work = [(scene, seed, mode) for mode in played for scene in scenes for seed in range(1, seeds + 1)]
    work.sort(key=lambda job: job[0] != 'cs-run')  # the long plays first
    with ProcessPoolExecutor(jobs) as pool:
        return list(pool.map(arena_tally, work))


WHAT = {
    306: ('lost', 'all', 'hits', 'S1', 'A1'),
    310: ('lost', 'all', 'hits', 'A1'),
    312: ('lost', 'all', 'hits', 'S1', 'S2', 'm329', 'bolts'),
    362: ('lost', 'all', 'hits', 'S1', 'A1', 'flames'),
}


def merged(found: dict[str, float]) -> dict[str, float]:
    """Rates under the names the two sides share: the four bolts as one, the flames (the client's 144 and 145,
    the server's 675) as one."""
    found = dict(found)
    found['bolts'] = sum(found.pop(f'm{m}', 0.0) for m in (323, 324, 325, 326))
    found['flames'] = sum(found.pop(f'm{m}', 0.0) for m in (144, 145, 675))
    return found


def render(takes: Sequence[Mapping[str, Any]], plays: Sequence[Mapping[str, Any]], half: str) -> str:
    lines: list[str] = []
    take_tallies = [t['tally'] for t in takes]
    take_pool = pooled(take_tallies)
    seconds = sum(t['seconds'] for t in takes)
    unowned = sum(t['unowned'] for t in takes)
    lines.append(
        f'Takes: {len(takes)} of the {half} half, {seconds:,.0f} s; points lost on nobody (no suspect): {unowned:,.0f}.'
    )
    for played, label in ((False, 'before'), (True, 'after')):
        mine = [p for p in plays if p['played'] == played]
        if not mine:
            continue
        arena_pool = pooled(p['tally'] for p in mine)
        lines.append(f'\n### Arena {label}: {len(mine)} plays\n')
        for txt, name in TYPES.items():
            what = WHAT[txt]
            lines.append(
                f"\n**{name} ({txt})**, a second of presence (take pooled [the takes' least..most] / arena):\n"
            )
            lines.append('| band | take s | arena s | ' + ' | '.join(what) + ' |')
            lines.append('| --- | ---: | ---: | ' + ' | '.join('---' for _ in what) + ' |')
            for edge in (*map(str, BANDS), 'far'):
                key = f'{txt}:{edge}'
                if key not in take_pool and key not in arena_pool:
                    continue
                t_row = take_pool.get(key, empty())
                a_row = arena_pool.get(key, empty())
                t_rates, a_rates = merged(rates(t_row)), merged(rates(a_row))
                cells = []
                for item in what:
                    low_high = None if item in ('bolts', 'flames') else spread(take_tallies, key, item)
                    mark = ''
                    if low_high is not None and a_row['seconds'] >= SPREAD_SECONDS:
                        mark = ' ok' if low_high[0] <= a_rates.get(item, 0.0) <= low_high[1] else ' **out**'
                    band = '' if low_high is None else f' [{low_high[0]:.2f}..{low_high[1]:.2f}]'
                    cells.append(f'{t_rates.get(item, 0.0):.2f}{band} / {a_rates.get(item, 0.0):.2f}{mark}')
                label_band = f'<= {edge}' if edge != 'far' else '> 45'
                lines.append(
                    f'| {label_band} | {t_row["seconds"]:.0f} | {a_row["seconds"]:.0f} | ' + ' | '.join(cells) + ' |'
                )
    lines.append('\n### Scenes\n')
    lines.append('| scene | model | life lost least / median / most | least life | deaths | kills | cost a play, s |')
    lines.append('| --- | --- | ---: | ---: | ---: | ---: | ---: |')
    for scene in SCENES:
        for played, label in ((False, 'before'), (True, 'after')):
            mine = [p for p in plays if p['scene'] == scene and p['played'] == played]
            if not mine:
                continue
            taken = [p['taken'] for p in mine]
            low = [p['low'] for p in mine]
            deaths = sum(1 for p in mine if p['dead_at'] is not None)
            kills, cost = statistics.median(p['kills'] for p in mine), statistics.median(p['cost'] for p in mine)
            lines.append(
                f'| {scene} | {label} | {min(taken):.0f} / {statistics.median(taken):.0f} / {max(taken):.0f} | '
                f'{statistics.median(low):.0f} | {deaths}/{len(mine)} | {kills:.0f} | {cost:.1f} |'
            )
    lines.append('\n### Life lost by who, mean a play\n')
    for scene in SCENES:
        for played, label in ((False, 'before'), (True, 'after')):
            mine = [p for p in plays if p['scene'] == scene and p['played'] == played]
            if not mine:
                continue
            by: collections.Counter[str] = collections.Counter()
            for p in mine:
                by.update(p['by'])
            top = ', '.join(f'{k} {v / len(mine):.0f}' for k, v in by.most_common(8))
            lines.append(f'- {scene} {label}: {top}')
    return '\n'.join(lines) + '\n'


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--seeds', type=int, default=6)
    parser.add_argument('--jobs', type=int, default=14)
    parser.add_argument('--half', default='check')
    parser.add_argument('--scenes', default=','.join(SCENES))
    parser.add_argument('--after-only', action='store_true')
    parser.add_argument('--out', type=Path, default=None)
    args = parser.parse_args(argv)
    cached = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    takes = cached.get(args.half)
    if takes is None:
        takes = gather_takes(args.half, args.jobs)
        cached[args.half] = takes
        CACHE.write_text(json.dumps(cached) + '\n')
    plays = gather_arena(args.seeds, args.jobs, args.scenes.split(','), (True,) if args.after_only else (False, True))
    text = render(takes, plays, args.half)
    if args.out is not None:
        args.out.write_text(text)
        args.out.with_suffix('.plays.json').write_text(json.dumps(plays) + '\n')
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
