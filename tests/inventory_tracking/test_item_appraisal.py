import copy
import json
from pathlib import Path

import pytest

from inventory_tracking.item_appraisal import decode_rings


@pytest.fixture
def capture():
    return json.loads((Path(__file__).parent / 'fixtures/appraisal_ring.json').read_text())


def test_captured_ring_decodes_scaled_stamina_and_fcr(capture):
    rows = decode_rings(capture['snapshot'], capture['report'])
    assert len(rows) == 1
    item = rows[0]['item']
    assert item['name'] == 'Ring'
    assert item['rarity'] == 'magic'
    assert {a['property_id']: a['value'] for a in item['affixes']} == {'452': 11, '520': 10}
    assert item['requirements'] == {}
    assert rows[0]['appraisal_ready'] is False
    assert rows[0]['source']['unit_id'] == 438836750
    assert rows[0]['source']['snapshot_only'] is True


@pytest.mark.parametrize('failure', ['build', 'unstable', 'arrays', 'owner'])
def test_untrusted_capture_cannot_produce_item_facts(capture, failure):
    if failure == 'build':
        capture['report']['game']['executable_fingerprint']['sha256'] = 'different'
    elif failure == 'unstable':
        capture['snapshot']['status'] = 'stale'
    elif failure == 'arrays':
        capture['snapshot']['resources']['items'][0]['resource_stats']['complete'] = False
    else:
        capture['snapshot']['resources']['items'][0]['details']['owner_id'] = -1
    with pytest.raises(ValueError, match=r'Unsupported|stale|missing|No owned'):
        decode_rings(capture['snapshot'], capture['report'])


def test_unknown_stats_remain_explicit_and_duplicate_stats_are_not_summed(capture):
    stats = capture['snapshot']['resources']['items'][0]['resource_stats']['arrays'][2]['stats']
    stats.append({'id': 999, 'layer': 3, 'raw': 25})
    stats.append(copy.deepcopy(stats[0]))
    result = decode_rings(capture['snapshot'], capture['report'])[0]
    assert [a['property_id'] for a in result['item']['affixes']] == ['520']
    assert len(result['unresolved_stats']) == 3
    assert result['appraisal_ready'] is False


def test_nonzero_layer_and_fractional_stamina_are_not_guessed(capture):
    stats = capture['snapshot']['resources']['items'][0]['resource_stats']['arrays'][2]['stats']
    stats[0]['raw'] += 1
    stats[1]['layer'] = 1
    assert decode_rings(capture['snapshot'], capture['report'])[0]['item']['affixes'] == []
