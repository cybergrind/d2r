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


@pytest.mark.parametrize('failure', [None, 'owner', 'percent', 'duplicate', 'amount', 'unstable'])
def test_owned_flat_damage_proof_requires_unique_local_plus_one_without_ed(failure):
    from inventory_tracking.items.modifiers import owned_flat_damage_modifiers

    capture = json.loads((ROOT / 'superior_phase_blade.json').read_text())
    item = capture['snapshot']['resources']['items'][0]
    diagnostics = item['resource_stats']['stat_diagnostics']
    chain = next(row for row in diagnostics['chains'] if row['head_offset'] == 0xD0)
    flat = {'id': 22, 'layer': 0, 'raw': 1}
    chain['lists'][0]['stats'] = [flat]
    if failure == 'owner':
        item['address'] += 16
    elif failure == 'percent':
        chain['lists'][0]['stats'].append({'id': 17, 'layer': 0, 'raw': 5})
    elif failure == 'duplicate':
        chain['lists'][0]['stats'].append(dict(flat))
    elif failure == 'amount':
        flat['raw'] = 2
    elif failure == 'unstable':
        diagnostics['stable'] = False
    assert owned_flat_damage_modifiers(diagnostics, item) == ([] if failure else [flat])
    decoded = decode_items(capture['snapshot'], capture['report'], inventory_page=item['details']['inventory_page'])[0]
    assert decoded['source'].get('superior_flat_damage', []) == ([] if failure else [flat])
