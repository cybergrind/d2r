import json
from pathlib import Path

import pytest

from inventory_tracking.hover.selection import resolve_selection


FIXTURE = Path(__file__).parents[1] / 'fixtures/hover_native_sequence.json'


def samples():
    return json.loads(FIXTURE.read_text())


def test_actual_host_sequence_resolves_ring_empty_potion_ring():
    results = [resolve_selection(s, 0x140000000) for s in samples()]
    assert [r['status'] for r in results] == ['candidate', 'no_item', 'candidate', 'candidate']
    assert [r.get('item', {}).get('unit_id') for r in results] == [71604348, None, 1114609378, 71604348]
    assert not any(r['validated'] for r in results)


@pytest.mark.parametrize(
    ('label', 'offset'), [('mouse_gate_and_position', 3), ('mouse_cells_90', 24), ('mouse_widget', 0x70)]
)
def test_changing_selection_input_abstains(label, offset):
    sample = samples()[3]
    block = next(b for b in sample['after']['native']['blocks'] if b['label'] == label)
    raw = bytearray.fromhex(block['after_hex'])
    raw[offset] ^= 1
    block['after_hex'] = raw.hex()
    assert resolve_selection(sample, 0x140000000)['status'] == 'unavailable'


def test_carried_item_and_special_layout_are_not_guessed():
    for label, offset in [('mouse_inventory_90', 0x40), ('mouse_widget', 0x52)]:
        sample = samples()[3]
        block = next(b for b in sample['after']['native']['blocks'] if b['label'] == label)
        raw = bytearray.fromhex(block['raw_hex'])
        raw[offset] = 1
        block['raw_hex'] = block['after_hex'] = raw.hex()
        assert resolve_selection(sample, 0x140000000)['status'] == 'unavailable'


def test_pointer_match_without_owner_match_is_rejected():
    sample = samples()[3]
    next(u for u in sample['snapshot']['groups']['items']['units'] if u['unit_id'] == 71604348)['details'][
        'owner_id'
    ] = 999
    assert resolve_selection(sample, 0x140000000)['status'] == 'unavailable'


def test_host_closed_inventory_and_carried_item_controls_abstain():
    path = FIXTURE.with_name('hover_native_controls.json')
    controls = json.loads(path.read_text())
    results = [resolve_selection(sample, 0x140000000) for sample in controls]
    assert [r['status'] for r in results] == ['unavailable', 'unavailable']
    assert [r['reason'] for r in results] == ['Unsupported focus state', 'Carried item unsupported']
    assert all('item' not in r for r in results)


def test_host_cube_sequence_preserves_container_provenance():
    samples = json.loads(FIXTURE.with_name('hover_cube_sequence.json').read_text())
    results = [resolve_selection(s, 0x140000000) for s in samples]
    assert [r.get('item', {}).get('unit_id') for r in results] == [3885838183, None, 3014701145, 3885838183]
    assert [r['status'] for r in results] == ['candidate', 'no_item', 'candidate', 'candidate']
    assert all(r['container'] == {'page': 3, 'name': 'Horadric Cube'} for r in results)


def test_host_cube_controls_reject_closed_and_carried_then_recover():
    samples = json.loads(FIXTURE.with_name('hover_cube_controls.json').read_text())
    results = [resolve_selection(s, 0x140000000) for s in samples]
    assert [r['status'] for r in results] == ['candidate', 'unavailable', 'candidate', 'unavailable', 'candidate']
    assert results[1]['reason'] == 'Unsupported focus state'
    assert results[3]['reason'] == 'Carried item unsupported'
    assert all('item' not in results[i] for i in (1, 3))
    for i in (0, 2, 4):
        assert results[i]['item']['unit_id'] == 3885838183
        assert results[i]['container'] == {'page': 3, 'name': 'Horadric Cube'}


@pytest.mark.parametrize('page', [1, 2, 5, 255])
def test_unverified_container_pages_are_rejected(page):
    sample = samples()[3]
    block = next(b for b in sample['after']['native']['blocks'] if b['label'] == 'mouse_widget')
    raw = bytearray.fromhex(block['raw_hex'])
    raw[0x630] = page
    block['raw_hex'] = block['after_hex'] = raw.hex()
    assert resolve_selection(sample, 0x140000000)['reason'] == 'Unsupported inventory container'


def test_host_personal_and_shared_stash_sequence():
    samples = json.loads(FIXTURE.with_name('hover_stash_sequence.json').read_text())
    results = [resolve_selection(s, 0x140000000) for s in samples]
    assert [r['status'] for r in results] == ['candidate', 'no_item', 'candidate', 'candidate']
    assert [r.get('item', {}).get('unit_id') for r in results] == [3996387037, None, 985832484, 3996387037]
    assert [r['container']['name'] for r in results] == [
        'Personal stash',
        'Personal stash',
        'Shared stash',
        'Personal stash',
    ]
    assert results[2]['owner_id'] == 142258002


def test_host_equipment_and_shop_getters_resolve_distinct_items():
    samples = json.loads(FIXTURE.with_name('hover_panels_sequence.json').read_text())
    results = [resolve_selection(s, 0x140000000) for s in samples]
    assert [r['status'] for r in results] == ['candidate'] * 4
    assert [r['item']['unit_id'] for r in results] == [848037454, 2029165619, 606745366, 44446050]
    assert [r['owner_type'] for r in results] == [0, 0, 1, 1]
    assert [r['container']['name'] for r in results] == ['Equipped items'] * 2 + ['Shop inventory'] * 2
    # Reject a pointer that disagrees with the native slot, even if its ID matches.
    samples[0]['snapshot']['groups']['items']['units'][0]['details']['body_location'] = 4
    assert resolve_selection(samples[0], 0x140000000)['reason'] == 'Equipment slot mismatch'
    samples[2]['snapshot']['groups']['items']['units'][0]['details']['owner_id'] = 284532388
    assert resolve_selection(samples[2], 0x140000000)['reason'] == 'Item ownership/location mismatch'
