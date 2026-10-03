import json
import struct
from pathlib import Path

import pytest

from inventory_tracking.items.decode import decode_items
from inventory_tracking.items.identity import FLAGS_OFFSET, SOCKETED_FLAG


@pytest.mark.parametrize('with_child_scan', [True, False])
def test_saved_superior_phase_blade_shows_single_tier_rolls(with_child_scan):
    saved = json.loads((Path(__file__).parents[1] / 'fixtures/superior_phase_blade.json').read_text())
    if not with_child_scan:
        saved['snapshot']['resources']['items'][0]['resource_stats'].pop('socket_items')
    result = decode_items(saved['snapshot'], saved['report'], inventory_page=3)[0]
    texts = [r['text'] for r in result['decoded_stats']]
    assert '+14% (5-15%) Enhanced Damage [T1; T1: 5-15%]' in texts
    assert '+2 (1-3) to Attack Rating [T1; T1: 1-3]' in texts


def test_superior_socket_contributions_are_not_ranked_as_base_rolls():
    saved = json.loads((Path(__file__).parents[1] / 'fixtures/superior_phase_blade.json').read_text())
    arrays = saved['snapshot']['resources']['items'][0]['resource_stats']
    arrays.pop('socket_items')
    raw = bytearray.fromhex(arrays['item_data_hex'])
    struct.pack_into('<I', raw, FLAGS_OFFSET, struct.unpack_from('<I', raw, FLAGS_OFFSET)[0] | SOCKETED_FLAG)
    arrays['item_data_hex'] = raw.hex()
    totals = next(row for row in arrays['arrays'] if row['header_offset'] == 0xE8)
    totals['stats'].append({'id': 194, 'layer': 0, 'raw': 1})
    result = decode_items(saved['snapshot'], saved['report'], inventory_page=3)[0]
    assert result['item']['sockets'] == 1
    assert result['item']['socket_contents'] is None
    assert not any('roll_tier' in r for r in result['decoded_stats'])
