import json
from pathlib import Path

import pytest

from inventory_tracking.items.identity import IDENTIFIED_FLAG, SOCKETED_FLAG
from inventory_tracking.items.sockets import infer_nonsocketable
from pricing.knowledge.assessment.maintenance.replay import replay


@pytest.mark.parametrize('stem', ['atma_scarab', 'large_charm_life20', 'large_charm_life35'])
def test_nonsocketable_saved_item_no_longer_needs_child_scan(stem):
    result = replay(stem)
    item = result['extraction']['item']
    assert (item['sockets'], item['socket_contents']) == (0, 'empty')
    assert result['extraction']['source']['socket_mechanics'] == 'item_type_cannot_socket'
    assert not any('socket' in gap.lower() for gap in result['assessment']['price_gaps'])


@pytest.mark.parametrize(
    'kind',
    [
        'amul',
        'ring',
        'scha',
        'mcha',
        'lcha',
        'jewl',
        'cjwl',
        'csch',
        'glov',
        'boot',
        'belt',
        'jave',
        'ajav',
        'tkni',
        'taxe',
    ],
)
def test_inferred_types_have_explicit_zero_capacity_in_pinned_source(kind):
    source = Path(__file__).resolve().parents[3] / 'third-parties/d2data/json/itemtypes.json'
    row = next(r for r in json.loads(source.read_text()).values() if r.get('Code') == kind)
    assert [row[f'MaxSockets{i}'] for i in (1, 2, 3)] == [0, 0, 0]
    item = {'item_type': kind}
    assert infer_nonsocketable(item, [], {}, IDENTIFIED_FLAG)
    assert item['sockets'] == 0


@pytest.mark.parametrize(
    ('kind', 'stats', 'arrays', 'flags'),
    [
        ('swor', [], {}, IDENTIFIED_FLAG),
        ('amul', [], {}, None),
        ('amul', [], {}, IDENTIFIED_FLAG | SOCKETED_FLAG),
        ('amul', [{'id': 194, 'raw': 1}], {}, IDENTIFIED_FLAG),
        ('amul', [], {'socket_items': {'children': [{'unit': {}}]}}, IDENTIFIED_FLAG),
    ],
)
def test_contradictory_or_unknown_socket_evidence_is_not_overwritten(kind, stats, arrays, flags):
    item = {'item_type': kind, 'sockets': None, 'socket_contents': None}
    assert not infer_nonsocketable(item, stats, arrays, flags)
    assert item['sockets'] is None


@pytest.mark.parametrize('kind', ['axe', 'spea', 'h2h', 'helm', 'tors'])
def test_socketable_neighbors_never_inherit_throwing_or_accessory_rule(kind):
    item = {'item_type': kind}
    assert not infer_nonsocketable(item, [], {}, IDENTIFIED_FLAG)
    assert 'sockets' not in item
