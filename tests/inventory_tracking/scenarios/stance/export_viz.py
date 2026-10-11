"""The stance replays (harness.py) as files for the Godot viewer (combat_viewer/README.md, "The exported file").

One file per moment, one run per strategy: the first rule (as `recorded`, the viewer's first run), no step,
the production step, the follow-on steps, and the same with a teleport. The monsters stand still; the
character's own track and moves differ per run (the optional `player` and `moves` fields of a run).

    uv run --offline python -m tests.inventory_tracking.scenarios.stance.export_viz [--out DIR] [fixture.json ...]
"""

import argparse
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from inventory_tracking.combat.mechanics.echoing_strike import LIFE, OUT_FRAMES
from inventory_tracking.combat.mechanics.hits import CONTACT_RADIUS
from inventory_tracking.combat.policy import LinePolicy
from inventory_tracking.combat.sim.input import BIRTH_LAG
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.combat.viz import (
    INDEX,
    RECORDED,
    SCALE,
    SCHEMA,
    Frame,
    dumps,
    entry,
    monster_name,
    permille,
    running_total,
    steps,
    walls,
    write_index,
)
from inventory_tracking.levels.presets import display_name
from inventory_tracking.macros.view import Viewport

from .first_rule import stand
from .harness import (
    ASPECT,
    WALK_LATENCY_FRAMES,
    Move,
    Result,
    Scene,
    Strategy,
    Trace,
    View,
    load,
    play,
    production,
    stay,
)


Point = tuple[float, float]
FIXTURES = Path(__file__).parent / 'fixtures'
OUT = Path(__file__).parents[4] / 'inventory_tracking' / 'runs' / 'combat' / 'viz-stance'
SECONDS = 15.0
LINGER = 40  # frames after the fight is cleared, so the blades finish flying
CHARACTER = 'CybergrindAA'
MARGIN = 150  # file units around everything drawn


def first(view: View) -> Move | None:
    """The first rule (first_rule.py): one step at most, to the spot `stand` finds."""
    if view.moves_made >= 1:
        return None
    found = stand(view.seen, LinePolicy(yields=True), view.barred, Viewport(ASPECT).reachable_focal)
    return None if found is None else Move(found.spot)


RUNS: tuple[tuple[str, str, Callable[[], Strategy]], ...] = (
    (RECORDED, 'the first rule (2026-10-10): 12 units, twice the line', lambda: first),
    ('stay', 'no step: cast from where the character stood', lambda: stay),
    ('step', 'camp: one step to the best place', production),
    ('follow', 'camp, and up to two more steps when nothing is in reach', lambda: production(follow=2)),
    ('hop', 'camp with a teleport allowed, and two more steps', lambda: production(follow=2, hop=True)),
)


def grow(frame: Frame, x: float, y: float) -> None:
    """Make the frame's bounds hold a point already in file units."""
    frame.low[0], frame.high[0] = min(frame.low[0], x), max(frame.high[0], x)
    frame.low[1], frame.high[1] = min(frame.low[1], y), max(frame.high[1], y)


def pack(paths: Sequence[Sequence[Point]], frame: Frame) -> list[list[int]]:
    """Blade paths as the file's BLADE: [x0, y0, x1, y1, n, dx, dy, ...] (viz.py `blades`, from paths)."""
    packed = []
    for path in paths:
        out = min(len(path) - 1, OUT_FRAMES)
        points = [frame(point) for point in path]
        blade = [*points[0], *points[out], out]
        for before, after in zip(points[out:], points[out + 1 :], strict=False):
            blade.extend((after[0] - before[0], after[1] - before[1]))
        packed.append(blade)
    return packed


def walk_track(trace: Trace, origin: Point, end: int, frame: Frame) -> dict[str, Any]:
    """The character over the run: at the origin from tick 0, a keyframe a tick along each walk's straight
    line (from the end of the walk's latency to its arrival), one keyframe at a hop's arrival."""
    keys: list[int] = [0, *frame(origin)]
    for move in trace.moves:
        if move.hop:
            keys.extend((move.arrives, *frame(move.to)))
            continue
        begin = min(move.started + WALK_LATENCY_FRAMES, move.arrives)
        for tick in range(begin, move.arrives + 1):
            share = 1.0 if move.arrives == begin else (tick - begin) / (move.arrives - begin)
            at = (
                move.start[0] + (move.to[0] - move.start[0]) * share,
                move.start[1] + (move.to[1] - move.start[1]) * share,
            )
            keys.extend((tick, *frame(at)))
    return {'seen': [[0, end]], 'k': keys}


def per_tick(taken: Sequence[tuple[int, float]]) -> dict[int, float]:
    """The running totals (frame, total so far) as the life taken per tick, for viz.py `running_total`."""
    out: dict[int, float] = {}
    before = 0.0
    for tick, total in taken:
        out[tick] = out.get(tick, 0.0) + total - before
        before = total
    return out


def run_data(
    name: str, label: str, scene: Scene, trace: Trace, result: Result, frame: Frame, end: int
) -> dict[str, Any]:
    casts = [
        {
            't': c.frame + BIRTH_LAG,
            'o': list(frame(c.origin)),
            'f': list(frame(c.focal)),
            'n': len(c.touched),
            'b': pack(c.paths, frame),
        }
        for c in trace.casts
    ]
    points = {b.unit: b.points for b in scene.bodies}
    series: dict[int, list[tuple[int, int]]] = {}
    for tick, unit, left in trace.life:
        series.setdefault(unit, []).append((tick, permille(left, points[unit])))
    moves = [
        {
            't0': m.started,
            't1': m.arrives,
            'from': list(frame(m.start)),
            'to': list(frame(m.to)),
            'hop': m.hop,
            'walk': round(m.walk * SCALE),
        }
        for m in trace.moves
    ]
    seconds = result.seconds if result.seconds is not None else SECONDS
    score = {
        'placement_per_combat_second': round(result.taken / seconds) if seconds else 0,
        'placement_points': round(result.taken),
        'combat_seconds': round(seconds, 1),
        'life_taken': round(result.taken),
        'kills': len(trace.deaths),
        'casts': len(casts),
        'contacts': sum(c['n'] for c in casts),
        'blades_walled': 0,
        'gain': None,
    }
    return {
        'name': name,
        'label': label,
        'policy': name != RECORDED,
        'casts': casts,
        'life': {str(unit): steps(rows) for unit, rows in sorted(series.items())},
        'deaths': {str(unit): tick for unit, tick in sorted(trace.deaths.items())},
        'taken': running_total(per_tick(trace.taken)),
        'score': score,
        'player': walk_track(trace, scene.origin, end, frame),
        'moves': moves,
    }


def still(at: Point, end: int, frame: Frame) -> dict[str, Any]:
    """A thing that stands where it is over the whole span: one keyframe."""
    return {'seen': [[0, end]], 'k': [0, *frame(at)]}


def door_rows(scene: Scene, end: int, frame: Frame) -> list[dict[str, Any]]:
    rows = []
    for door in scene.doors:
        x, y = frame((door.x, door.y))
        rows.append(
            {
                'unit': door.unit_id,
                'txt': door.txt_id,
                'x': x,
                'y': y,
                'r': round(door.radius * SCALE),
                'seen': [[0, end]],
                'closed': [[0, end]] if door.closed else [],
            }
        )
    return rows


def sentence(name: str, mine: float | None, theirs: float | None) -> tuple[str, str, float]:
    """The moment of run `name` against the first rule: (kind, label, seconds apart)."""
    span = f'{SECONDS:.0f}'
    if mine is None and theirs is None:
        return 'recorded_ahead', f'{name} and the first rule did not clear in {span} s', 0.0
    if mine is None:
        assert theirs is not None
        return 'recorded_ahead', f'{name} did not clear in {span} s, the first rule in {theirs:.1f} s', SECONDS - theirs
    if theirs is None:
        return 'policy_ahead', f'{name} cleared in {mine:.1f} s, the first rule did not in {span} s', SECONDS - mine
    kind = 'recorded_ahead' if mine > theirs else 'policy_ahead'
    return kind, f'{name} cleared in {mine:.1f} s, the first rule in {theirs:.1f} s', abs(theirs - mine)


def export(path: str | Path) -> dict[str, Any]:
    """One fixture as the viewer's file: a run per strategy over the same still monsters."""
    fixture = json.loads(Path(path).read_text())
    scene = load(path)
    played = []
    for name, label, make in RUNS:
        trace = Trace()
        result = play(scene, make(), seconds=SECONDS, trace=trace, linger=LINGER)
        played.append((name, label, trace, result))
    end = max(trace.end_frame for _, _, trace, _ in played)
    frame = Frame([(round(scene.origin[0]), round(scene.origin[1]))])
    ground = walls(scene.ground, frame)
    for body in scene.bodies:
        frame(body.at)
    for companion in fixture.get('companions', ()):
        frame(companion['at'])
    runs = [run_data(name, label, scene, trace, result, frame, end) for name, label, trace, result in played]
    base = runs[0]['score']['placement_per_combat_second']
    for found in runs[1:]:
        score = found['score']
        score['gain'] = round(score['placement_per_combat_second'] / base - 1, 3) if base else None
    for found in runs:  # everything drawn: the blades' ends and the character's tracks
        for cast in found['casts']:
            for blade in cast['b']:
                grow(frame, blade[0], blade[1])
                grow(frame, blade[2], blade[3])
        keys = found['player']['k']
        for x, y in zip(keys[1::3], keys[2::3], strict=True):
            grow(frame, x, y)
    monsters = [
        {
            'unit': b.unit,
            'txt': b.txt,
            'name': monster_name(b.txt),
            'elite': b.elite,
            'points': round(b.points),
            'life0': permille(b.points * b.life, b.points),
            **still(b.at, end, frame),
            'recorded': {'death': None, 'life': []},
        }
        for b in scene.bodies
    ]
    companions = [
        {'unit': c['unit'], 'txt': c['txt'], 'name': monster_name(c['txt']), **still(c['at'], end, frame)}
        for c in fixture.get('companions', ())
    ]
    recorded = runs[0]
    seconds = {name: result.seconds for name, _, _, result in played}
    moments = {}
    for name in seconds:
        if name != RECORDED:
            kind, label, value = sentence(name, seconds[name], seconds[RECORDED])
            moments[name] = [{'first': 0, 'last': end, 'kind': kind, 'label': label, 'value': round(value, 2)}]
    walks = [[m['t0'] + WALK_LATENCY_FRAMES, m['t1']] for m in recorded['moves'] if not m['hop']]
    low_x, low_y, high_x, high_y = frame.bounds
    return {
        'schema': SCHEMA,
        'take': scene.name,
        'recording': fixture.get('take'),
        'character': CHARACTER,
        'started_at': fixture.get('log_time'),
        'area': scene.area,
        'area_name': display_name(scene.area),
        'rate': GAME_RATE,
        'start': 0,
        'end': end,
        'seconds': round(end / GAME_RATE, 1),
        'late_ticks': 0,
        'scale': SCALE,
        'origin': list(frame.origin),
        'bounds': [low_x - MARGIN, low_y - MARGIN, high_x + MARGIN, high_y + MARGIN],
        'aspect': round(ASPECT, 4),
        'birth_lag': BIRTH_LAG,
        'blade_life': LIFE,
        'contact_radius': round(CONTACT_RADIUS * SCALE),
        'player': {**recorded['player'], 'mode': [0, 1], 'run': walks},
        'pointer': {'seen': [], 'k': []},
        'monsters': monsters,
        'companions': companions,
        'doors': door_rows(scene, end, frame),
        'walls': ground,
        'recorded': {
            'kills': recorded['score']['kills'],
            'life_taken': recorded['score']['life_taken'],
            'taken': recorded['taken'],
        },
        'gate': {'passes': True, 'fails': [], 'damage_ratio': 1.0},
        'runs': runs,
        'moments': moments,
    }


def write(path: str | Path, out: Path) -> dict[str, Any]:
    """Export one fixture to `out`; its index entry."""
    data = export(path)
    out.mkdir(parents=True, exist_ok=True)
    text = dumps(data)
    file = f'{Path(path).stem}.json'
    (out / file).write_text(text)
    return entry(data, file, len(text.encode()))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n\n')[0])
    parser.add_argument('fixtures', nargs='*', type=Path, help='fixture files (default: all of fixtures/)')
    parser.add_argument('--out', type=Path, default=OUT, help=f'where the files go (default: {OUT})')
    args = parser.parse_args(argv)
    paths = args.fixtures or sorted(FIXTURES.glob('*.json'))
    rows = []
    for path in paths:
        found = write(path, args.out)
        rows.append(found)
        gains = ' '.join(f'{n} {s["gain"]:+.0%}' for n, s in found['runs'].items() if s['gain'] is not None)
        print(f'{found["take"]:30} {found["bytes"] / 1e3:7.0f} kB  {gains}')
    write_index(args.out, rows, merge=True)
    print(f'{len(rows)} files in {args.out / INDEX}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
