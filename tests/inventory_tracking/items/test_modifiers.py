import json
from pathlib import Path

import pytest

from inventory_tracking.items.decode import decode_items
from inventory_tracking.items.modifiers import owned_damage_modifiers


ROOT = Path(__file__).parents[1] / 'fixtures'


def test_captured_crowbill_local_damage_is_shown_once():
    evidence = json.loads((ROOT / 'crowbill_modifiers.json').read_text())
    capture = json.loads((ROOT / 'tancred_crowbill.json').read_text())
    extra = owned_damage_modifiers(evidence['diagnostics'], evidence['item'])
    assert [s['raw'] for s in extra] == [80, 80]
    capture['snapshot']['resources']['items'][0]['resource_stats']['damage_modifiers'] = extra
    item = decode_items(capture['snapshot'], capture['report'])[0]
    assert [s['text'] for s in item['decoded_stats'] if 'Enhanced Damage' in s['text']] == ['+80% Enhanced Damage']
    damage = next(a for a in item['item']['affixes'] if a['property_id'] == '510')
    assert damage['origin'] == 'owned_modifier_list'
    assert 'descriptor_offset' not in damage
    assert not any('not captured' in note for note in item['review'])


@pytest.mark.parametrize('failure', ['owner', 'unstable', 'truncated_chain'])
def test_unverified_modifier_lists_are_not_used(failure):
    evidence = json.loads((ROOT / 'crowbill_modifiers.json').read_text())
    if failure == 'owner':
        evidence['item']['address'] += 16
    elif failure == 'unstable':
        evidence['diagnostics']['stable'] = False
    else:
        evidence['diagnostics']['chains'][-1]['lists'] = []
    assert owned_damage_modifiers(evidence['diagnostics'], evidence['item']) == []
