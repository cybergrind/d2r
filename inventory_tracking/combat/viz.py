"""Takes exported for the replay viewer (combat_viewer/, a Godot project): one JSON file per take
holding what stood where at every game tick, the recorded casts and each policy's casts through
the simulator on the same situation, and the moments where the two differ most.

`python -m inventory_tracking.combat.viz <take directory>` writes `<take>.json` and refreshes
`index.json` beside it; with a directory of takes it exports every take that holds enough full
casts and writes the index of all of them. The files go to `runs/combat/viz/` (git-ignored) unless
`--out` says otherwise. The viewer reads nothing else.

The file's layout is written down once, in combat_viewer/README.md ("The exported file"): this
module and the viewer's `take_data.gd` are both built against it. In short: every coordinate is an
integer, `scale` to a world unit, measured from `origin`; every time is a `Situation` tick; a
position over time is a track (`seen` spans and `k` keyframes), a value over time a step series.

The numbers are the simulator's own (sim/engine.py `simulate`, sim/policy.py `candidate`,
`run_policy`, `policy_score`, the same calls `compare` makes), and the blades are the mechanics'
(`echoing_strike.cast` with the origin, the caster's path and the walls the engine gives it).
"""

import argparse
import base64
import json
import math
import zlib
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any

from inventory_tracking.combat.mechanics.echoing_strike import LIFE, OUT_FRAMES, cast
from inventory_tracking.combat.mechanics.hits import CONTACT_RADIUS
from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.policy import RUN_MODES
from inventory_tracking.combat.sim.engine import Outcome, gate, simulate
from inventory_tracking.combat.sim.input import BIRTH_LAG
from inventory_tracking.combat.sim.policy import LIVE, MODES, YIELD, candidate, policy_score, run_policy
from inventory_tracking.combat.sim.situation import Situation, cut
from inventory_tracking.combat.takes import Take
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.combat.viz_moments import Trace, find_moments
from inventory_tracking.levels.model import Ground, unpack_cells
from inventory_tracking.levels.presets import display_name
from inventory_tracking.native.layout import TILE_UNITS


Point = tuple[float, float]
SCHEMA = 1
SCALE = 10  # file units to a world unit: positions are kept to a tenth
RECORDED = 'recorded'
POLICIES = (LIVE, YIELD)  # the runs beside the recorded one, by default
OUT = Path(__file__).parents[1] / 'runs' / 'combat' / 'viz'
INDEX = 'index.json'
LEAST_CASTS = 5  # as the scoreboard: a take with fewer full casts shows nothing of the aim
UNREAD, FLOOR, LOW, WALL = 0, 1, 2, 3  # a wall cell: no grid, walk and fly, blocks walking only, blocks blades
LABELS = {
    RECORDED: "the player's recorded casts",
    LIVE: "policy 'live': the aim the game's fight runs today",
    YIELD: "policy 'yield': the line sweep, never while the player ran",
    'free': "policy 'free': the line sweep whenever free (the ceiling)",
    'slots': "policy 'slots': the line sweep at the recorded cast ticks",
    'nearest': "policy 'nearest': the elite first, then the nearest (the old macro)",
}


class Frame:
    """The file's coordinates: integers, SCALE to a world unit, from an origin near the play."""

    def __init__(self, points: Iterable[Point]) -> None:
        found = list(points)
        self.origin = (math.floor(min(x for x, _ in found)), math.floor(min(y for _, y in found)))
        self.low = [math.inf, math.inf]
        self.high = [-math.inf, -math.inf]

    def __call__(self, point: Point) -> tuple[int, int]:
        """`point` in file units; the bounds grow to hold it."""
        at = (round((point[0] - self.origin[0]) * SCALE), round((point[1] - self.origin[1]) * SCALE))
        for axis in (0, 1):
            self.low[axis] = min(self.low[axis], at[axis])
            self.high[axis] = max(self.high[axis], at[axis])
        return at

    @property
    def bounds(self) -> list[int]:
        return [int(self.low[0]), int(self.low[1]), int(self.high[0]), int(self.high[1])]


def spans(ticks: Iterable[int]) -> list[list[int]]:
    """Sorted ticks as inclusive [first, last] spans of consecutive ones."""
    out: list[list[int]] = []
    for tick in sorted(ticks):
        if out and tick == out[-1][1] + 1:
            out[-1][1] = tick
        else:
            out.append([tick, tick])
    return out


def track(path: Mapping[int, Point], frame: Frame) -> dict[str, Any]:
    """A position over time: `seen` holds the spans of ticks it was there, `k` a keyframe (tick, x, y,
    flat) at the start of every span and wherever the position changed; between keyframes it stands."""
    keys: list[int] = []
    last: tuple[int, int] | None = None
    before = None
    for tick in sorted(path):
        at = frame(path[tick])
        if at != last or before != tick - 1:
            keys.extend((tick, *at))
            last = at
        before = tick
    return {'seen': spans(path), 'k': keys}


def steps(values: Iterable[tuple[int, Any]]) -> list[Any]:
    """(tick, value) pairs in tick order as a flat step series: an entry only where the value changes."""
    out: list[Any] = []
    for tick, value in values:
        if not out or out[-1] != value:
            if len(out) >= 2 and out[-2] == tick:
                out[-1] = value
            else:
                out.extend((tick, value))
    return out


def walls(ground: Ground | None, frame: Frame) -> dict[str, Any] | None:
    """The level's grids as one picture, a byte a cell (a world unit), row by row: UNREAD where no room
    was read, FLOOR, LOW (blocks walking, a blade flies over it), WALL (stops a blade). Deflated, base64."""
    if ground is None or not len(ground):
        return None
    left = min(grid.x for grid in ground.grids) * TILE_UNITS
    top = min(grid.y for grid in ground.grids) * TILE_UNITS
    width = max(grid.x + grid.width for grid in ground.grids) * TILE_UNITS - left
    height = max(grid.y + grid.height for grid in ground.grids) * TILE_UNITS - top
    cells = bytearray(width * height)
    for grid in ground.grids:
        columns, rows = grid.width * TILE_UNITS, grid.height * TILE_UNITS
        walk = unpack_cells(grid.cells, columns * rows)
        fly = unpack_cells(grid.flight, columns * rows) if grid.flight else None
        if walk is None:
            continue
        for row in range(rows):
            base = (grid.y * TILE_UNITS - top + row) * width + grid.x * TILE_UNITS - left
            for column in range(columns):
                index = row * columns + column
                if fly is not None and fly[index] == '0':
                    cells[base + column] = WALL
                else:
                    cells[base + column] = FLOOR if walk[index] == '1' else LOW
    x, y = frame((left, top))
    frame((left + width, top + height))
    return {
        'x': x,
        'y': y,
        'w': width,
        'h': height,
        'flight': any(grid.flight for grid in ground.grids),
        'cells': base64.b64encode(zlib.compress(bytes(cells), 9)).decode(),
    }


def doors(situation: Situation, frame: Frame) -> list[dict[str, Any]]:
    """Each door unit: where it stands, its half extent (levels/doors.py `radius`), the spans of ticks it
    was seen and the spans it stood closed."""
    seen: dict[int, list[int]] = {}
    closed: dict[int, list[int]] = {}
    last: dict[int, Any] = {}
    for tick, found in situation.doors.items():
        for door in found:
            seen.setdefault(door.unit_id, []).append(tick)
            if door.closed:
                closed.setdefault(door.unit_id, []).append(tick)
            last[door.unit_id] = door
    out = []
    for unit in sorted(seen):
        door = last[unit]
        x, y = frame((door.x, door.y))
        out.append(
            {
                'unit': unit,
                'txt': door.txt_id,
                'x': x,
                'y': y,
                'r': round(door.radius * SCALE),
                'seen': spans(seen[unit]),
                'closed': spans(closed.get(unit, ())),
            }
        )
    return out


def monster_name(txt: int) -> str:
    return tables()['monsters'].get(str(txt), {}).get('NameStr') or f'monster {txt}'


def permille(points: float, full: float) -> int:
    """Life `points` in thousandths of `full`; a monster with any life left has at least one (zero is dead)."""
    if not full or points <= 0.0:
        return 0
    return max(1, round(1000 * min(points, full) / full))


def monsters(situation: Situation, frame: Frame) -> list[dict[str, Any]]:
    """Each hostile: its recorded path while alive, its type, and its life as the take recorded it (a
    step series of thousandths of its full points, from the recorded drops) with the recorded kill."""
    out = []
    for unit in sorted(situation.monsters):
        found = situation.monsters[unit]
        left = found.life_at_start * found.points
        life = []
        for tick, lost in sorted(situation.drops.get(unit, ())):
            left -= lost
            life.append((tick, permille(left, found.points)))
        out.append(
            {
                'unit': unit,
                'txt': found.txt,
                'name': monster_name(found.txt),
                'elite': found.elite,
                'points': round(found.points),
                'life0': permille(found.life_at_start * found.points, found.points),
                **track(found.path, frame),
                'recorded': {'death': found.recorded_death, 'life': steps(life)},
            }
        )
    return out


def blades(situation: Situation, birth: int, focal: Point, frame: Frame) -> tuple[list[list[int]], list[list[Point]]]:
    """The five blades of a cast as the engine flies them, packed and as world points. A packed blade
    is [x0, y0, x1, y1, n, dx, dy, ...]: it flies straight from (x0, y0) at the birth tick to (x1, y1)
    `n` ticks later (the way out, cut short by a wall), then each (dx, dy) is its step in the next
    tick (the way back to the caster)."""
    origin = situation.player_at(birth)
    paths = cast(origin, focal, lambda k: situation.player_at(birth + k), situation.blocked_at(birth))
    packed = []
    for path in paths:
        out = min(len(path) - 1, OUT_FRAMES)
        points = [frame(point) for point in path]
        blade = [*points[0], *points[out], out]
        for before, after in zip(points[out:], points[out + 1 :], strict=False):
            blade.extend((after[0] - before[0], after[1] - before[1]))
        packed.append(blade)
    return packed, paths


def touched(situation: Situation, outcome: Outcome, birth: int, paths: Sequence[Sequence[Point]]) -> int:
    """The monsters a cast's blades come within the contact radius of while they live in this run."""
    found: set[int] = set()
    for path in paths:
        for k, position in enumerate(path):
            tick = birth + k
            for unit, monster in situation.monsters.items():
                where = monster.path.get(tick)
                if where is None or unit in found or outcome.deaths.get(unit, tick) < tick:
                    continue
                if math.dist(position, where) <= CONTACT_RADIUS:
                    found.add(unit)
    return len(found)


def life_taken(situation: Situation, outcome: Outcome) -> tuple[dict[int, list[tuple[int, float]]], dict[int, float]]:
    """From the blows the simulation dealt: each monster's life left after every tick it was hurt in,
    and the life taken per tick over all monsters (a blow takes no more than the monster has left, so
    the sum is the engine's `effective_damage`)."""
    left_by: dict[int, list[tuple[int, float]]] = {}
    taken: dict[int, float] = {}
    for unit, blows in outcome.dealt_by.items():
        monster = situation.monsters[unit]
        left = monster.life_at_start * monster.points
        series: list[tuple[int, float]] = []
        for tick, dealt in blows:
            taken[tick] = taken.get(tick, 0.0) + min(dealt, max(left, 0.0))
            left -= dealt
            if series and series[-1][0] == tick:
                series[-1] = (tick, left)
            else:
                series.append((tick, left))
        left_by[unit] = series
    return left_by, taken


def running_total(taken: Mapping[int, float]) -> list[int]:
    """Life taken per tick as a step series of the total so far, in whole points."""
    total = 0.0
    out = []
    for tick in sorted(taken):
        total += taken[tick]
        out.append((tick, round(total)))
    return steps(out)


def run(
    situation: Situation, name: str, outcome: Outcome, frame: Frame, base: float | None
) -> tuple[dict[str, Any], Trace]:
    """One run for the file (casts with their blades, life curves, deaths, the life taken so far and
    the score), and its trace for the moments. `base` is the recorded run's placement per combat
    second, None for the recorded run itself."""
    casts = []
    counts = []
    for birth, focal in sorted(outcome.cast_frames):
        packed, paths = blades(situation, birth, focal, frame)
        count = touched(situation, outcome, birth, paths)
        counts.append((birth, count))
        casts.append(
            {'t': birth, 'o': list(frame(situation.player_at(birth))), 'f': list(frame(focal)), 'n': count, 'b': packed}
        )
    left_by, taken = life_taken(situation, outcome)
    full = policy_score(situation, outcome)
    score = {
        'placement_per_combat_second': full['placement_per_combat_second'],
        'placement_points': full['placement_points'],
        'combat_seconds': full['combat_seconds'],
        'life_taken': full['damage_points'],
        'kills': full['kills'],
        'casts': full['casts'],
        'contacts': full['contacts'],
        'blades_walled': full['blades_walled'],
        'gain': None if base is None or not base else round(full['placement_per_combat_second'] / base - 1, 3),
    }
    found = {
        'name': name,
        'label': LABELS.get(name, f"policy '{name}'"),
        'policy': name != RECORDED,
        'casts': casts,
        'life': {
            str(unit): steps((tick, permille(left, situation.monsters[unit].points)) for tick, left in series)
            for unit, series in sorted(left_by.items())
        },
        'deaths': {str(unit): tick for unit, tick in sorted(outcome.deaths.items())},
        'taken': running_total(taken),
        'score': score,
    }
    return found, Trace(name, sorted(taken.items()), counts, dict(outcome.deaths))


def export(take: Take, policies: Sequence[str] = POLICIES) -> dict[str, Any]:
    """The take as the viewer's file (combat_viewer/README.md): the situation per tick, the recorded
    run, a run per policy, and each policy's moments against the recorded run."""
    situation = cut(take)
    frame = Frame(situation.player.values())
    recorded_casts = [(c.frame, c.fitted) for c in situation.casts]
    manual = simulate(situation, recorded_casts)
    base = policy_score(situation, manual)['placement_per_combat_second']
    recorded, recorded_trace = run(situation, RECORDED, manual, frame, None)
    runs = [recorded]
    moments = {}
    elites = frozenset(unit for unit, monster in situation.monsters.items() if monster.elite)
    for mode in policies:
        outcome = run_policy(situation, candidate(situation, mode))
        found, trace = run(situation, mode, outcome, frame, base)
        runs.append(found)
        moments[mode] = [
            {**asdict(moment), 'value': round(moment.value, 2)}
            for moment in find_moments(situation.start, situation.end, recorded_trace, trace, elites=elites)
        ]
    drops: dict[int, float] = {}
    for found_drops in situation.drops.values():
        for tick, lost in found_drops:
            drops[tick] = drops.get(tick, 0.0) + lost
    report = gate(situation, manual)
    data = {
        'schema': SCHEMA,
        'take': take.directory.name,
        'recording': take.recording,
        'area': situation.area,
        'area_name': display_name(situation.area),
        'character': take.manifest.get('character'),
        'started_at': take.manifest.get('started_at'),
        'rate': GAME_RATE,
        'start': situation.start,
        'end': situation.end,
        'seconds': round(situation.seconds, 1),
        'late_ticks': situation.late_ticks,
        'scale': SCALE,
        'origin': list(frame.origin),
        'aspect': round(situation.aspect, 4),
        'birth_lag': BIRTH_LAG,
        'blade_life': LIFE,
        'contact_radius': round(CONTACT_RADIUS * SCALE),
        'player': {
            **track(situation.player, frame),
            'mode': steps(sorted(situation.modes.items())),
            'run': spans(tick for tick, mode in situation.modes.items() if mode in RUN_MODES),
        },
        'pointer': track(situation.pointer, frame),
        'monsters': monsters(situation, frame),
        'companions': [
            {'unit': unit, 'txt': found.txt, 'name': monster_name(found.txt), **track(found.path, frame)}
            for unit, found in sorted(situation.companions.items())
        ],
        'doors': doors(situation, frame),
        'walls': walls(situation.ground, frame),
        'recorded': {
            'kills': sum(1 for monster in situation.monsters.values() if monster.recorded_death is not None),
            'life_taken': round(situation.recorded_damage),
            'taken': running_total(drops),
        },
        'gate': {'passes': not report['fails'], 'fails': report['fails'], 'damage_ratio': report['damage_ratio']},
        'runs': runs,
        'moments': moments,
    }
    data['bounds'] = frame.bounds
    return data


def entry(data: Mapping[str, Any], file: str, size: int) -> dict[str, Any]:
    """A take's line in the index: what the viewer's list shows."""
    return {
        'take': data['take'],
        'file': file,
        'bytes': size,
        'area': data['area'],
        'area_name': data['area_name'],
        'started_at': data['started_at'],
        'seconds': data['seconds'],
        'ticks': data['end'] - data['start'] + 1,
        'monsters': len(data['monsters']),
        'recorded_kills': data['recorded']['kills'],
        'gate_passes': data['gate']['passes'],
        'runs': {found['name']: found['score'] for found in data['runs']},
        'moments': {name: len(found) for name, found in data['moments'].items()},
    }


def dumps(data: Any) -> str:
    return json.dumps(data, separators=(',', ':'))


def write(directory: Path, out: Path = OUT, policies: Sequence[str] = POLICIES) -> dict[str, Any] | None:
    """Export the take in `directory` to `out`; its index entry, or None when it holds too few casts."""
    take = Take.load(directory)
    data = export(take, policies)
    if len(data['runs'][0]['casts']) < LEAST_CASTS:
        return None
    out.mkdir(parents=True, exist_ok=True)
    text = dumps(data)
    file = f'{directory.name}.json'
    (out / file).write_text(text)
    return entry(data, file, len(text.encode()))


def write_index(out: Path, entries: Iterable[Mapping[str, Any]], *, merge: bool = False) -> Path:
    """`index.json` in `out` listing `entries` by take name; with `merge` the takes already listed stay."""
    target = out / INDEX
    found = {}
    if merge and target.exists():
        found = {row['take']: row for row in json.loads(target.read_text())['takes']}
    found.update({row['take']: row for row in entries})
    target.write_text(json.dumps({'schema': SCHEMA, 'takes': [found[name] for name in sorted(found)]}, indent=1))
    return target


def is_take(path: Path) -> bool:
    return (path / 'frames.jsonl').exists() or (path / 'frames.jsonl.gz').exists()


def _write(job: tuple[Path, Path, tuple[str, ...]]) -> tuple[str, dict[str, Any] | None, str | None]:
    """One take of `write_all`, in a worker: (name, index entry, why it was left out)."""
    directory, out, policies = job
    try:
        found = write(directory, out, policies)
    except Exception as error:  # one unreadable take must not stop the rest; it is named
        return directory.name, None, f'{type(error).__name__}: {error}'
    return directory.name, found, None if found else f'fewer than {LEAST_CASTS} full casts'


def write_all(takes: Path, out: Path = OUT, policies: Sequence[str] = POLICIES, jobs: int = 1) -> dict[str, str]:
    """Export every take under `takes` and write the index of them; returns what was left out and why."""
    paths = sorted(path for path in takes.iterdir() if path.is_dir() and is_take(path))
    work = [(path, out, tuple(policies)) for path in paths]
    out.mkdir(parents=True, exist_ok=True)
    if jobs > 1:
        with ProcessPoolExecutor(jobs) as pool:
            results = list(pool.map(_write, work))
    else:
        results = [_write(job) for job in work]
    write_index(out, [found for _, found, _ in results if found])
    return {name: why for name, _, why in results if why}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n\n')[0])
    parser.add_argument('path', type=Path, help='a take directory, or a directory of takes (every take in it)')
    parser.add_argument('--out', type=Path, default=OUT, help=f'where the files go (default: {OUT})')
    parser.add_argument(
        '--policies',
        default=','.join(POLICIES),
        help=f'the policy runs beside the recorded one, comma separated, of {", ".join(MODES)}',
    )
    parser.add_argument('--jobs', type=int, default=4, help='takes exported at once (a directory of takes)')
    args = parser.parse_args(argv)
    policies = tuple(name for name in args.policies.split(',') if name)
    unknown = [name for name in policies if name not in MODES]
    if unknown:
        parser.error(f'unknown policies: {", ".join(unknown)}')
    if is_take(args.path):
        found = write(args.path, args.out, policies)
        if found is None:
            print(f'{args.path.name}: fewer than {LEAST_CASTS} full casts, nothing written')
            return 1
        write_index(args.out, [found], merge=True)
        print(f'{args.out / found["file"]}: {found["bytes"] / 1e6:.2f} MB')
        return 0
    left_out = write_all(args.path, args.out, policies, args.jobs)
    index = json.loads((args.out / INDEX).read_text())['takes']
    for row in index:
        gains = ' '.join(f'{name} {score["gain"]:+.0%}' for name, score in row['runs'].items() if score['gain'])
        print(f'{row["take"]:24} {row["area_name"]:18} {row["seconds"]:6.1f} s {row["bytes"] / 1e6:5.2f} MB  {gains}')
    for name, why in left_out.items():
        print(f'{name:24} left out: {why}')
    print(f'{len(index)} takes in {args.out / INDEX}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
