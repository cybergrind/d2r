import json
import struct
from pathlib import Path

import pytest

from inventory_tracking.hover.selection import resolve_selection
from inventory_tracking.native.layout import HIRELING_CLASS_ID
from inventory_tracking.tracking.state import select_player


BASE = 0x140000000


def merc_sample():
    # Model merc ownership on the host-verified equipment widget/grid fixture.
    path = Path(__file__).parents[1] / 'fixtures/hover_panels_sequence.json'
    sample = json.loads(path.read_text())[0]
    native = sample['after']['native']
    player_id, _ = select_player(sample['snapshot']['groups']['players']['units'])
    owner = native['owners'][0]
    owner.update(type=1, unit_id=123456)
    merc = {
        'address': owner['address'],
        'type': 1,
        'unit_id': 123456,
        'txt_id': HIRELING_CLASS_ID,
        'identity_stable': True,
        'details': {'monster_data_u32': [0] * 21 + [player_id]},
    }
    sample['snapshot']['groups']['monsters'] = {'complete': True, 'units': [merc]}
    for block in native['blocks']:
        raw = bytearray.fromhex(block['raw_hex'])
        if block['label'] == 'mouse_widget':
            struct.pack_into('<II', raw, 0x5C4, 123456, 1)
        if block['address'] == owner['address']:
            struct.pack_into('<I', raw, 0, 1)
            struct.pack_into('<I', raw, 8, 123456)
        block['raw_hex'] = block['after_hex'] = raw.hex()
    result = resolve_selection(json.loads(path.read_text())[0], BASE)
    selected = next(
        i for i in sample['snapshot']['groups']['items']['units'] if i['unit_id'] == result['item']['unit_id']
    )
    selected['details']['owner_id'] = 0xFFFFFFFF
    return sample


def test_merc_equipment_uses_native_slot_and_local_player_association():
    result = resolve_selection(merc_sample(), BASE)
    assert result['status'] == 'candidate', result
    assert result['container'] == {'page': 255, 'name': 'Mercenary equipment'}
    assert result['owner_type'] == 1
    assert result['owner_id'] == 123456


@pytest.mark.parametrize('failure', ['foreign', 'unstable', 'incomplete', 'duplicate'])
def test_other_or_unverified_monsters_cannot_be_merc_owners(failure):
    sample = merc_sample()
    group = sample['snapshot']['groups']['monsters']
    merc = group['units'][0]
    if failure == 'foreign':
        merc['details']['monster_data_u32'][21] += 1
    elif failure == 'unstable':
        merc['identity_stable'] = False
    elif failure == 'incomplete':
        group['complete'] = False
    else:
        group['units'].append(dict(merc))
    assert resolve_selection(sample, BASE)['status'] == 'unavailable'
