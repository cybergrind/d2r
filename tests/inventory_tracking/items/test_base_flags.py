import json
import struct
from pathlib import Path

import pytest

from inventory_tracking.items.decode import decode_items


def capture():
    return json.loads((Path(__file__).parents[1] / 'fixtures/cryptic_axe.json').read_text())


def test_latest_cryptic_axe_is_nonethereal_with_four_empty_sockets():
    saved = capture()
    item = decode_items(saved['snapshot'], saved['report'])[0]['item']
    assert item['name'] == 'Cryptic Axe'
    assert item['ethereal'] is False
    assert item['sockets'] == item['empty_sockets'] == 4
    assert item['socket_contents'] == 'empty'


@pytest.mark.parametrize(('mutation', 'expected'), [('eth', True), ('truncated', None), ('quality', None)])
def test_flag_decoding_requires_matching_complete_item_data(mutation, expected):
    saved = capture()
    arrays = saved['snapshot']['resources']['items'][0]['resource_stats']
    raw = bytearray.fromhex(arrays['item_data_hex'])
    if mutation == 'eth':
        struct.pack_into('<I', raw, 0x18, struct.unpack_from('<I', raw, 0x18)[0] | 0x00400000)
    elif mutation == 'quality':
        struct.pack_into('<I', raw, 0, 7)
    else:
        raw = raw[:24]
    arrays['item_data_hex'] = raw.hex()
    assert decode_items(saved['snapshot'], saved['report'])[0]['item']['ethereal'] is expected


def test_complete_unsocketed_capture_is_zero_not_unknown():
    saved = capture()
    arrays = saved['snapshot']['resources']['items'][0]['resource_stats']
    raw = bytearray.fromhex(arrays['item_data_hex'])
    struct.pack_into('<I', raw, 0x18, struct.unpack_from('<I', raw, 0x18)[0] & ~0x800)
    arrays['item_data_hex'] = raw.hex()
    for row in arrays['arrays']:
        row['stats'] = [s for s in row['stats'] if s['id'] != 194]
    item = decode_items(saved['snapshot'], saved['report'])[0]['item']
    assert item['sockets'] == item['empty_sockets'] == 0
    assert item['socket_contents'] == 'empty'
