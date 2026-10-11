"""Checks on the stance moment fixtures written by build_fixtures.py."""

import json
from pathlib import Path

import pytest


FIXTURES = Path(__file__).resolve().parent / 'fixtures'
FILES = sorted(FIXTURES.glob('*.json'))
REQUIRED = {
    'name',
    'log_time',
    'take',
    'area',
    'in_fight',
    'logged',
    'player',
    'hostiles',
    'companions',
    'doors',
    'ground',
    'after',
}
AFTER = {'player_at', 'alive_at', 'cleared_seconds', 'casts'}


def test_at_least_fifteen_fixtures():
    assert len(FILES) >= 15


@pytest.mark.parametrize('path', FILES, ids=lambda p: p.name)
def test_fixture_shape(path: Path):
    fixture = json.loads(path.read_text(encoding='utf-8'))
    assert fixture.keys() >= REQUIRED
    assert fixture['after'].keys() >= AFTER
    assert fixture['name'] == path.stem
    assert {'in_reach', 'near', 'decision'} <= fixture['logged'].keys()
    assert len(fixture['player']) == 2


@pytest.mark.parametrize('path', FILES, ids=lambda p: p.name)
def test_fixture_has_hostiles_with_life_in_range(path: Path):
    fixture = json.loads(path.read_text(encoding='utf-8'))
    assert fixture['hostiles'], 'a moment has at least one hostile in reach'
    for hostile in fixture['hostiles']:
        assert 0 < hostile['life'] <= 1


@pytest.mark.parametrize('path', FILES, ids=lambda p: p.name)
def test_fixture_has_ground(path: Path):
    fixture = json.loads(path.read_text(encoding='utf-8'))
    assert fixture['ground']
