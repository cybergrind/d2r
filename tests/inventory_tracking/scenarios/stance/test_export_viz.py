"""The stance replays as viewer files (export_viz.py)."""

import json
from functools import cache
from pathlib import Path

import pytest

from .export_viz import RUNS, export, main
from .harness import Trace, load, play, production, stay


FIXTURES = sorted((Path(__file__).parent / 'fixtures').glob('*.json'))
FEW = FIXTURES[:3]
TOP = ('schema', 'take', 'recording', 'character', 'started_at', 'area', 'area_name', 'rate', 'start', 'end', 'seconds')
TOP += ('late_ticks', 'scale', 'origin', 'bounds', 'aspect', 'birth_lag', 'blade_life', 'contact_radius', 'player')
TOP += ('pointer', 'monsters', 'companions', 'doors', 'walls', 'recorded', 'gate', 'runs', 'moments')
RUN = ('name', 'label', 'policy', 'casts', 'life', 'deaths', 'taken', 'score', 'player', 'moves')


@cache
def exported(path: Path) -> dict:
    return export(path)


@pytest.mark.parametrize('path', FEW, ids=lambda path: path.stem[-9:])
def test_a_trace_does_not_change_the_results(path):
    for strategy in (stay, production(follow=2)):
        plain = play(load(path), strategy, seconds=15.0)
        traced = play(load(path), strategy, seconds=15.0, trace=Trace())
        assert traced == plain


def test_the_file_has_the_contract_s_fields():
    data = exported(FEW[0])
    assert all(key in data for key in TOP)
    assert [run['name'] for run in data['runs']] == [name for name, _, _ in RUNS]
    assert data['runs'][0]['policy'] is False
    assert data['pointer'] == {'seen': [], 'k': []}
    assert set(data['moments']) == {name for name, _, _ in RUNS[1:]}
    for run in data['runs']:
        assert all(key in run for key in RUN)
        for cast in run['casts']:
            assert len(cast['b']) == 5
            assert data['start'] <= cast['t'] <= data['end']
        ticks = run['player']['k'][0::3]
        assert ticks == sorted(ticks)
        assert data['start'] <= ticks[0]
        assert ticks[-1] <= data['end']
    json.dumps(data)


def test_following_kills_at_least_as_much_as_staying():
    for path in FEW:
        runs = {run['name']: run for run in exported(path)['runs']}
        assert runs['follow']['score']['kills'] >= runs['stay']['score']['kills']


def test_a_walk_s_track_ends_at_where_the_move_goes():
    for path in FEW:
        for run in exported(path)['runs']:
            for move in run['moves']:
                keys = run['player']['k']
                at = [(keys[i + 1], keys[i + 2]) for i in range(0, len(keys), 3) if keys[i] == move['t1']]
                assert at, 'a keyframe at the arrival'
                assert at[-1] == tuple(move['to'])


def test_writing_fixtures_makes_the_files_and_the_index(tmp_path):
    main([*map(str, FIXTURES[:2]), '--out', str(tmp_path)])
    assert all((tmp_path / f'{path.stem}.json').exists() for path in FIXTURES[:2])
    index = json.loads((tmp_path / 'index.json').read_text())
    assert [row['take'] for row in index['takes']] == sorted(path.stem for path in FIXTURES[:2])
