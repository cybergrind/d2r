"""The replay viewer's export (combat/viz.py) against the schema in combat_viewer/README.md: the ticks
and tracks against the situation, the step series, the simulator's runs, the blades, the walls and
doors, the moments, and the writers."""

import base64
import functools
import itertools
import json
import math
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from inventory_tracking.combat import viz
from inventory_tracking.combat.mechanics.echoing_strike import cast
from inventory_tracking.combat.sim.engine import simulate
from inventory_tracking.combat.sim.policy import compare
from inventory_tracking.combat.sim.situation import Situation, cut
from inventory_tracking.combat.takes import Take
from inventory_tracking.combat.viz_moments import KINDS


FIXTURES = Path(__file__).parent / 'fixtures'
NAMES = ('chaos-manual', 'catacombs-macro')
MODES = ('live', 'yield')
TOP_KEYS = (
    'schema',
    'take',
    'recording',
    'character',
    'started_at',
    'area',
    'area_name',
    'rate',
    'start',
    'end',
    'seconds',
    'late_ticks',
    'scale',
    'origin',
    'bounds',
    'aspect',
    'birth_lag',
    'blade_life',
    'contact_radius',
    'player',
    'pointer',
    'monsters',
    'companions',
    'doors',
    'walls',
    'recorded',
    'gate',
    'runs',
    'moments',
)
SCORE_KEYS = {
    'placement_per_combat_second',
    'placement_points',
    'combat_seconds',
    'life_taken',
    'kills',
    'casts',
    'contacts',
    'blades_walled',
    'gain',
}
MOMENT_KEYS = {'first', 'last', 'kind', 'label', 'value'}


@dataclass(frozen=True)
class Case:
    name: str
    directory: Path
    take: Take
    situation: Situation
    data: dict[str, Any]
    report: dict[str, Any]


@functools.cache
def load(name: str) -> Case:
    """One fixture, cut and exported once per session."""
    directory = FIXTURES / name
    take = Take.load(directory)
    situation = cut(take)
    return Case(name, directory, take, situation, viz.export(take), compare(situation, modes=MODES))


@pytest.fixture(scope='module', params=NAMES)
def case(request) -> Case:
    return load(request.param)


@pytest.fixture(scope='module')
def chaos() -> Case:
    return load('chaos-manual')


def ticks_of(spans: list[list[int]]) -> list[int]:
    return [tick for first, last in spans for tick in range(first, last + 1)]


def keyframe(track: dict[str, Any], tick: int) -> tuple[int, int] | None:
    """The last keyframe at or before `tick`, ignoring the spans."""
    found = None
    keys = track['k']
    for index in range(0, len(keys), 3):
        if keys[index] > tick:
            break
        found = (keys[index + 1], keys[index + 2])
    return found


def position(track: dict[str, Any], tick: int) -> tuple[int, int] | None:
    """The README's rule: the last keyframe at or before the tick, only inside a seen span."""
    if not any(first <= tick <= last for first, last in track['seen']):
        return None
    return keyframe(track, tick)


def at(track: dict[str, Any], tick: int) -> tuple[int, int] | None:
    """The position inside the spans, else the last keyframe before the tick."""
    return position(track, tick) or keyframe(track, tick)


def step_series(data: dict[str, Any]) -> list[tuple[str, list[Any], str]]:
    """Every step series in the file: (where it is, flat list, what its values are)."""
    found = [('player mode', data['player']['mode'], 'mode')]
    found += [(f'recorded life {row["unit"]}', row['recorded']['life'], 'life') for row in data['monsters']]
    found += [('recorded taken', data['recorded']['taken'], 'taken')]
    for run in data['runs']:
        found += [(f'{run["name"]} life {unit}', flat, 'life') for unit, flat in run['life'].items()]
        found.append((f'{run["name"]} taken', run['taken'], 'taken'))
    return found


def pairwise(values: list[Any]) -> list[tuple[Any, Any]]:
    return list(itertools.pairwise(values))


def pairs_of(flat: list[Any]) -> list[tuple[int, Any]]:
    return list(zip(flat[::2], flat[1::2], strict=True))


def decode(blade: list[int], origin: list[int]) -> list[tuple[float, float]]:
    """A packed blade as world points: the way out straight from (x0, y0) to (x1, y1), then the steps back."""
    x0, y0, x1, y1, n = blade[:5]
    points = [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n + 1)] if n else [(x0, y0)]
    x, y = x1, y1
    for index in range(5, len(blade), 2):
        x, y = x + blade[index], y + blade[index + 1]
        points.append((x, y))
    return [(origin[0] + px / 10, origin[1] + py / 10) for px, py in points]


def test_top_level_keys_and_constants_match_the_schema(case):
    data = case.data
    assert set(TOP_KEYS) <= set(data)
    assert data['schema'] == viz.SCHEMA
    assert data['scale'] == 10
    assert data['rate'] == 25.0
    assert data['take'] == case.name


def test_runs_are_recorded_then_the_policies_in_order(case):
    runs = case.data['runs']
    assert runs[0]['name'] == 'recorded'
    assert runs[0]['policy'] is False
    assert [run['name'] for run in runs[1:]] == ['live', 'yield']
    assert all(run['policy'] is True for run in runs[1:])
    for run in runs:
        assert {'casts', 'life', 'deaths', 'taken', 'score', 'label'} <= set(run)
        assert set(run['score']) >= SCORE_KEYS


def test_gains_are_null_for_the_recorded_run_and_floats_for_policies(case):
    runs = case.data['runs']
    assert runs[0]['score']['gain'] is None
    for run in runs[1:]:
        assert isinstance(run['score']['gain'], float)


def test_moments_are_keyed_by_the_policies(case):
    assert set(case.data['moments']) == set(MODES)


def test_the_export_is_plain_json_data_and_round_trips(case):
    def plain(value):
        assert value is None or isinstance(value, (str, bool, int, float, list, dict))
        if isinstance(value, float):
            assert math.isfinite(value)
        if isinstance(value, dict):
            assert all(isinstance(key, str) for key in value)
            for item in value.values():
                plain(item)
        if isinstance(value, list):
            for item in value:
                plain(item)

    plain(case.data)
    assert json.loads(viz.dumps(case.data)) == json.loads(json.dumps(case.data))


def test_tick_bounds_and_spans_line_up_with_the_situation(case):
    data, situation = case.data, case.situation
    assert data['start'] == situation.start
    assert data['end'] == situation.end
    assert sorted(ticks_of(data['player']['seen'])) == sorted(situation.player)
    rows = {row['unit']: row for row in data['monsters']}
    assert len(data['monsters']) == len(situation.monsters) == len(rows)
    for unit, found in situation.monsters.items():
        row = rows[unit]
        assert row['txt'] == found.txt
        assert row['elite'] == found.elite
        assert sorted(ticks_of(row['seen'])) == sorted(found.path)
        assert row['recorded']['death'] == found.recorded_death
    companions = {row['unit']: row for row in data['companions']}
    assert set(companions) == set(situation.companions)
    for unit, found in situation.companions.items():
        assert companions[unit]['txt'] == found.txt
        assert sorted(ticks_of(companions[unit]['seen'])) == sorted(found.path)
    assert [cast_row['t'] for cast_row in data['runs'][0]['casts']] == sorted(c.frame for c in situation.casts)


def test_tracks_decode_to_the_recorded_positions_and_stop_outside_the_spans(case):
    data, situation = case.data, case.situation
    ox, oy = data['origin']
    tracks = [('player', data['player'], situation.player)]
    tracks += [
        (f'monster {found.unit}', next(row for row in data['monsters'] if row['unit'] == unit), found.path)
        for unit, found in situation.monsters.items()
    ]
    for label, track, path in tracks:
        for tick, point in path.items():
            want = (round((point[0] - ox) * 10), round((point[1] - oy) * 10))
            assert position(track, tick) == want, label
        for _, last in track['seen']:
            assert position(track, last + 1) is None, label


def test_step_series_are_well_formed(case):
    data = case.data
    for label, flat, _ in step_series(data):
        assert len(flat) % 2 == 0, label
        pairs = pairs_of(flat)
        ticks = [tick for tick, _ in pairs]
        assert all(a < b for a, b in pairwise(ticks)), label
        assert all(data['start'] <= tick <= data['end'] for tick in ticks), label
        values = [value for _, value in pairs]
        assert all(a != b for a, b in pairwise(values)), label


def test_life_values_are_thousandths_and_taken_only_grows(case):
    for label, flat, kind in step_series(case.data):
        values = [value for _, value in pairs_of(flat)]
        if kind == 'life':
            assert all(isinstance(value, int) and 0 <= value <= 1000 for value in values), label
        if kind == 'taken':
            assert all(a <= b for a, b in pairwise(values)), label


def test_a_killed_monster_life_ends_at_zero_on_its_death_tick(case):
    for run in case.data['runs']:
        for unit, tick in run['deaths'].items():
            assert pairs_of(run['life'][unit])[-1] == (tick, 0), (run['name'], unit)


def test_the_recorded_run_is_the_simulator_on_the_recorded_casts(case):
    situation = case.situation
    recorded = case.data['runs'][0]
    outcome = simulate(situation, [(c.frame, c.fitted) for c in situation.casts])
    assert recorded['score']['casts'] == len(situation.casts)
    assert recorded['deaths'] == {str(unit): tick for unit, tick in outcome.deaths.items()}
    last = pairs_of(recorded['taken'])[-1][1] if recorded['taken'] else 0
    assert abs(last - round(outcome.effective_damage)) <= 1
    assert recorded['score']['kills'] == len(outcome.deaths)


def test_the_policy_scores_are_the_compare_report(case):
    report = case.report
    runs = {run['name']: run for run in case.data['runs']}
    assert (
        runs['recorded']['score']['placement_per_combat_second']
        == (report['manual']['score']['placement_per_combat_second'])
    )
    for name in MODES:
        score = runs[name]['score']
        assert score['gain'] == report[name]['gain']
        assert score['casts'] == report[name]['casts']
        assert score['placement_per_combat_second'] == report[name]['score']['placement_per_combat_second']


def test_every_cast_has_five_blades_within_the_blade_life(case):
    life = case.data['blade_life']
    assert life == 38
    for run in case.data['runs']:
        for cast_row in run['casts']:
            assert len(cast_row['b']) == 5
            for blade in cast_row['b']:
                assert len(blade) >= 5
                assert len(blade) % 2 == 1
                n = blade[4]
                assert 0 <= n <= 19
                if n < 19:
                    assert len(blade) == 5
                assert n + 1 + (len(blade) - 5) // 2 <= life


def test_each_cast_counts_touched_monsters_and_starts_at_the_caster(case):
    player = case.data['player']
    for run in case.data['runs']:
        for cast_row in run['casts']:
            assert isinstance(cast_row['n'], int)
            assert cast_row['n'] >= 0
            assert tuple(cast_row['o']) == at(player, cast_row['t'])


def test_the_first_recorded_cast_of_chaos_matches_the_echoing_strike_mechanic(chaos):
    situation = chaos.situation
    first = situation.casts[0]
    birth = first.frame
    row = chaos.data['runs'][0]['casts'][0]
    assert row['t'] == birth
    origin = situation.player_at(birth)
    paths = cast(origin, first.fitted, lambda k: situation.player_at(birth + k))
    assert len(row['b']) == len(paths)
    for blade, path in zip(row['b'], paths, strict=True):
        decoded = decode(blade, chaos.data['origin'])
        assert len(decoded) == len(path)
        for got, want in zip(decoded, path, strict=True):
            assert math.dist(got, want) <= 0.11


def test_moments_are_sorted_inside_the_take_and_typed(case):
    start, end = case.data['start'], case.data['end']
    for name in MODES:
        moments = case.data['moments'][name]
        keys = [(moment['first'], moment['last'], moment['kind']) for moment in moments]
        assert keys == sorted(keys), name
        for moment in moments:
            assert set(moment) == MOMENT_KEYS
            assert start <= moment['first'] <= moment['last'] <= end
            assert moment['kind'] in KINDS
            assert isinstance(moment['label'], str)
            assert moment['label']
            assert isinstance(moment['value'], (int, float))
            assert not isinstance(moment['value'], bool)
    assert case.data['moments']['live']


def test_chaos_manual_has_no_walls_and_no_doors(chaos):
    assert chaos.data['walls'] is None
    assert chaos.data['doors'] == []


def test_catacombs_walls_are_the_level_map_byte_for_byte():
    case = load('catacombs-macro')
    walls = case.data['walls']
    assert {'x', 'y', 'w', 'h', 'flight', 'cells'} <= set(walls)
    grid = zlib.decompress(base64.b64decode(walls['cells']))
    width, height = walls['w'], walls['h']
    assert len(grid) == width * height
    values = set(grid)
    assert values <= {0, 1, 2, 3}
    assert 1 in values
    assert 2 in values or 3 in values
    ground = case.situation.ground
    ox, oy = case.data['origin']
    total = width * height
    stride = max(1, total // 200)
    for index in range(0, total, stride)[:200]:
        row, column = divmod(index, width)
        wx = ox + walls['x'] / 10 + column + 0.5
        wy = oy + walls['y'] / 10 + row + 0.5
        walk = ground.walkable(wx, wy)
        fly = ground.flyable(wx, wy)
        if walk is None:
            want = 0
        elif walk and fly is not False:
            want = 1
        elif fly is False:
            want = 3
        else:
            want = 2
        assert grid[index] == want, (row, column)


def test_catacombs_doors_match_the_situation_doors():
    case = load('catacombs-macro')
    data, situation = case.data, case.situation
    doors = data['doors']
    assert doors
    by_unit = {door['unit']: door for door in doors}
    for door in doors:
        assert set(door) == {'unit', 'txt', 'x', 'y', 'r', 'seen', 'closed'}
        for first, last in door['closed']:
            assert any(seen_first <= first and last <= seen_last for seen_first, seen_last in door['seen'])
    for tick, found in situation.doors.items():
        for door in found:
            closed = any(first <= tick <= last for first, last in by_unit[door.unit_id]['closed'])
            assert closed == door.closed, (tick, door.unit_id)


def test_bounds_hold_every_keyframe_and_cast_point(case):
    data = case.data
    x0, y0, x1, y1 = data['bounds']
    assert all(isinstance(value, int) for value in data['bounds'])
    assert x0 <= x1
    assert y0 <= y1
    tracks = [data['player'], *data['monsters'], *data['companions']]
    points = []
    for track in tracks:
        points += [(track['k'][index + 1], track['k'][index + 2]) for index in range(0, len(track['k']), 3)]
    for run in data['runs']:
        for cast_row in run['casts']:
            points += [tuple(cast_row['f']), tuple(cast_row['o'])]
    for x, y in points:
        assert x0 <= x <= x1
        assert y0 <= y <= y1


def test_export_is_deterministic(case):
    first = viz.dumps(viz.export(Take.load(case.directory)))
    second = viz.dumps(viz.export(Take.load(case.directory)))
    assert first == second


def test_write_puts_the_export_in_the_named_file(case, tmp_path):
    entry = viz.write(case.directory, tmp_path)
    file = tmp_path / f'{case.name}.json'
    assert json.loads(file.read_text()) == json.loads(json.dumps(case.data))
    assert entry['take'] == case.name
    assert entry['file'] == f'{case.name}.json'
    assert entry['bytes'] == file.stat().st_size
    assert entry['area'] == case.data['area']
    assert entry['seconds'] == case.data['seconds']
    assert entry['ticks'] == case.data['end'] - case.data['start'] + 1
    assert set(entry['runs']) == {'recorded', 'live', 'yield'}
    assert set(entry['moments']) == set(MODES)


def test_write_all_exports_both_fixtures_and_indexes_them_by_name(tmp_path):
    left_out = viz.write_all(FIXTURES, tmp_path, jobs=1)
    assert left_out == {}
    index = json.loads((tmp_path / viz.INDEX).read_text())
    assert index['schema'] == viz.SCHEMA
    assert [row['take'] for row in index['takes']] == sorted(NAMES)
    for name in NAMES:
        assert (tmp_path / f'{name}.json').exists()


def test_main_writes_the_take_and_its_index(chaos, tmp_path):
    assert viz.main([str(chaos.directory), '--out', str(tmp_path)]) == 0
    assert (tmp_path / 'chaos-manual.json').exists()
    index = json.loads((tmp_path / viz.INDEX).read_text())
    assert [row['take'] for row in index['takes']] == ['chaos-manual']


def test_write_index_merge_keeps_takes_already_listed(tmp_path):
    viz.write_index(tmp_path, [{'take': 'alpha'}])
    viz.write_index(tmp_path, [{'take': 'beta'}], merge=True)
    assert [row['take'] for row in json.loads((tmp_path / viz.INDEX).read_text())['takes']] == ['alpha', 'beta']
    viz.write_index(tmp_path, [{'take': 'beta'}])
    assert [row['take'] for row in json.loads((tmp_path / viz.INDEX).read_text())['takes']] == ['beta']


def test_spans_group_sorted_ticks_into_inclusive_runs():
    assert viz.spans([5, 1, 2, 3, 9, 10]) == [[1, 3], [5, 5], [9, 10]]


def test_steps_keep_only_the_changes_and_the_last_value_at_a_tick():
    assert viz.steps([(1, 4), (2, 4), (3, 5), (3, 6), (7, 6)]) == [1, 4, 3, 6]
    assert viz.steps([]) == []
