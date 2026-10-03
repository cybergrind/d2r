import json
import struct
from copy import deepcopy
from pathlib import Path

import pytest

from inventory_tracking.items.decode import decode_items
from inventory_tracking.items.identity import RUNEWORD_FLAG, SOCKETED_FLAG
from inventory_tracking.items.sockets import infer_unsocketed


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


@pytest.mark.parametrize('stem', ['dire_song', 'guardian_angel', 'tancred_crowbill'])
def test_saved_unsocketed_item_does_not_require_child_scan(stem):
    saved = json.loads((Path(__file__).parents[1] / f'fixtures/{stem}.json').read_text())
    details = saved['snapshot']['resources']['items'][0]['details']
    result = decode_items(
        saved['snapshot'],
        saved['report'],
        inventory_page=details['inventory_page'],
        inventory_owner_id=details['owner_id'],
    )[0]
    assert result['item']['sockets'] == 0
    assert result['item']['empty_sockets'] == 0
    assert result['item']['socket_contents'] == 'empty'
    assert result['source']['socket_mechanics'] == 'unsocketed_flags_and_complete_stats'


@pytest.mark.parametrize(
    'conflict',
    [
        'flags_missing',
        'socketed',
        'runeword',
        'incomplete',
        'no_totals',
        'two_totals',
        'stat_count',
        'total_count',
        'child',
        'existing_count',
        'existing_payload',
    ],
)
def test_unsocketed_inference_preserves_unknown_or_contradictory_evidence(conflict):
    arrays = {'complete': True, 'arrays': [{'header_offset': 0xE8, 'stats': []}]}
    item = {'sockets': None, 'socket_contents': None}
    flags, stats = 0x10, []
    if conflict == 'flags_missing':
        flags = None
    elif conflict in ('socketed', 'runeword'):
        flags |= SOCKETED_FLAG if conflict == 'socketed' else RUNEWORD_FLAG
    elif conflict == 'incomplete':
        arrays['complete'] = False
    elif conflict == 'no_totals':
        arrays['arrays'] = []
    elif conflict == 'two_totals':
        arrays['arrays'] *= 2
    elif conflict == 'stat_count':
        stats = [{'id': 194, 'raw': 3}]
    elif conflict == 'total_count':
        arrays['arrays'][0]['stats'] = [{'id': 194, 'raw': 3}]
    elif conflict == 'child':
        arrays['socket_items'] = {'children': [{'position': 0}]}
    elif conflict == 'existing_count':
        item['sockets'] = 3
    elif conflict == 'existing_payload':
        item['socket_contents'] = 'filled'
    before = deepcopy(item)
    assert not infer_unsocketed(item, stats, arrays, flags)
    assert item == before
