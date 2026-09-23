import json
from pathlib import Path

import pytest

from inventory_tracking.items.decode import decode_items
from inventory_tracking.items.modifiers import owned_defense_modifiers


@pytest.fixture
def capture():
    return json.loads((Path(__file__).parents[1] / 'fixtures/guardian_angel.json').read_text())


def decode(capture):
    row = capture['snapshot']['resources']['items'][0]
    arrays = row['resource_stats']
    arrays['defense_modifiers'] = owned_defense_modifiers(arrays['stat_diagnostics'], row)
    return decode_items(
        capture['snapshot'], capture['report'], inventory_page=4, inventory_owner_id=row['details']['owner_id']
    )[0]


def test_guardian_angel_matches_tooltip(capture):
    result = decode(capture)
    texts = [r['text'] for r in result['decoded_stats']]
    assert '+187% (180-200%) Enhanced Defense' in texts
    assert '+227 to Attack Rating against Demons (Based on Character Level)' in texts
    assert not result['unresolved_stats']
    assert result['source']['viewer_context']['level'] == 91
    defense = next(r for r in result['decoded_stats'] if r.get('memory_stat', {}).get('id') == 16)
    assert defense['origin'] == 'owned_modifier_list'
    assert defense['roll_quality'] == 'normal'
    assert any(r.get('presentation') == 'internal' for r in result['decoded_stats'])


def test_existing_total_defense_modifier_is_not_added_twice(capture):
    arrays = capture['snapshot']['resources']['items'][0]['resource_stats']
    arrays['arrays'][-1]['stats'].append({'id': 16, 'layer': 0, 'raw': 190})
    texts = [r['text'] for r in decode(capture)['decoded_stats']]
    assert [t for t in texts if 'Enhanced Defense' in t] == ['+190% (180-200%) Enhanced Defense']


def test_missing_viewer_level_keeps_per_level_stat_unresolved(capture):
    for p in capture['snapshot']['groups']['players']['units']:
        p['details']['full_stats'] = [s for s in p['details']['full_stats'] if s['id'] != 12]
    result = decode(capture)
    assert [s['id'] for s in result['unresolved_stats']] == [245]


def test_wrong_modifier_owner_does_not_supply_defense(capture):
    row = capture['snapshot']['resources']['items'][0]
    assert owned_defense_modifiers(row['resource_stats']['stat_diagnostics'], {**row, 'address': 1}) == []


def test_publication_rejects_changed_viewer_level(capture, monkeypatch):
    from inventory_tracking.appraisal import capture as capture_module

    item = capture['snapshot']['resources']['items'][0]
    token = capture['snapshot']['identity']
    worker = capture_module.AppraisalCapture(1, {'identity': token}, {})
    frozen = {'identity': token, 'selection': {'item': item}, 'observation': decode(capture)}
    monkeypatch.setattr(capture_module, 'game_focused', lambda _: True)
    monkeypatch.setattr(capture_module, 'identity', lambda _: token)
    monkeypatch.setattr(worker, 'selection', lambda: ({'snapshot': capture['snapshot']}, {'item': item}))
    for player in capture['snapshot']['groups']['players']['units']:
        for stat in player['details']['full_stats']:
            if stat['id'] == 12:
                stat['raw'] = 92
    assert worker.still_selected(frozen) is False
