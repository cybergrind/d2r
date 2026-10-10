import json
import struct
from pathlib import Path

import pytest

from inventory_tracking.hover.selection import resolve_selection


BASE = 0x140000000


def sample():
    return json.loads((Path(__file__).parents[1] / 'fixtures/hover_material_widget.json').read_text())


def widget_change(s, offset, value, *, stable=True):
    block = next(b for b in s['after']['native']['blocks'] if b['label'] == 'mouse_widget')
    raw = bytearray.fromhex(block['after_hex'])
    struct.pack_into('<Q', raw, offset, value)
    block['after_hex'] = raw.hex()
    if stable:
        block['raw_hex'] = raw.hex()


def test_saved_material_stash_widget_resolves_native_item_pointer():
    result = resolve_selection(sample(), BASE)
    assert result['status'] == 'candidate'
    assert result['item']['unit_id'] == 1776519725
    assert result['container'] == {'page': 4, 'name': 'Materials stash'}
    assert result['materials'] is True


def test_empty_and_changed_material_widget_pointers():
    s = sample()
    widget_change(s, 0x608, 0)
    assert resolve_selection(s, BASE)['status'] == 'no_item'
    s = sample()
    widget_change(s, 0x608, 0, stable=False)
    assert resolve_selection(s, BASE)['status'] == 'unavailable'
    s = sample()
    widget_change(s, 0x608, 123)
    assert resolve_selection(s, BASE)['status'] == 'unavailable'


@pytest.mark.parametrize(('field', 'value'), [('owner_id', 42), ('inventory_page', 0), ('x', 1)])
def test_material_widget_does_not_bypass_item_location_validation(field, value):
    s = sample()
    s['snapshot']['groups']['items']['units'][0]['details'][field] = value
    assert resolve_selection(s, BASE)['status'] == 'unavailable'


def test_material_widget_requires_native_getter_and_matching_item_code():
    s = sample()
    s['after']['widgets']['mouse']['methods']['0xc0'] += 1
    assert resolve_selection(s, BASE)['status'] == 'unavailable'
    s = sample()
    s['snapshot']['groups']['items']['units'][0]['txt_id'] -= 1
    assert resolve_selection(s, BASE)['status'] == 'unavailable'


def test_selected_material_uses_ownerless_stack_decoder():
    from inventory_tracking.appraisal.capture import selected_observation
    from inventory_tracking.native.layout import SUPPORTED_SHA256

    s = sample()
    snapshot = s['snapshot']
    item = snapshot['groups']['items']['units'][0]
    snapshot['resources'] = {
        'complete': True,
        'items': [
            item
            | {
                'resource_stats': {
                    'complete': True,
                    'stack_count': 15,
                    'arrays': [{'header_offset': 0xE8, 'stats': []}],
                }
            }
        ],
    }
    report = {
        'state': 'complete',
        'game': {
            'identity': snapshot['identity'],
            'executable_fingerprint': {'sha256': SUPPORTED_SHA256},
        },
    }
    observation = selected_observation(
        snapshot,
        report,
        item['unit_id'],
        inventory_page=4,
        selection_sample=s,
        image_base=BASE,
    )
    assert observation['item']['base_code'] == 'ua4'
    assert observation['item']['quantity'] == 15
    assert 'Quantity: 15' in [stat['text'] for stat in observation['decoded_stats']]
    from pricing.triage.adapters import from_drop

    assert from_drop(observation)['quantity'] == 15
    assert observation['source']['container']['name'] == 'Materials stash'


def test_production_material_capture_does_not_read_an_inventory_grid():
    from inventory_tracking.hover.native import collect_native

    s = sample()
    records = s['after']['native']['blocks']
    blocks = {r['address']: bytes.fromhex(r['raw_hex']) for r in records}
    widget = s['after']['widgets']['mouse']
    widget['raw_hex'] = blocks[widget['address']].hex()

    def read(address, size):
        assert len(blocks[address]) == size
        return blocks[address]

    result = collect_native(read, BASE, s['after'], s['snapshot'])
    assert not result['errors']
    assert result['stable']
    assert not any('grid' in r['label'] or 'cells' in r['label'] for r in result['blocks'])
