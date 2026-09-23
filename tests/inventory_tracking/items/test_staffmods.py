import json
from pathlib import Path

import pytest

from inventory_tracking.items.decode import decode_items


@pytest.mark.parametrize(
    ('fixture', 'page', 'expected'),
    [
        ('greater_claws', 0, '+2 (1-3) to Blades of Ice (Assassin Only)'),
        ('storm_gyre', 3, '+1 (1-3) to Meteor (Sorceress Only)'),
    ],
)
def test_saved_staffmods_have_ranges_without_affix_tiers(fixture, page, expected):
    saved = json.loads((Path(__file__).parents[1] / f'fixtures/{fixture}.json').read_text())
    result = decode_items(saved['snapshot'], saved['report'], inventory_page=page)[0]
    row = next(r for r in result['decoded_stats'] if r.get('memory_stat', {}).get('id') == 107)
    assert row['text'] == expected
    assert 'roll_tier' not in row
    assert row['roll_quality'] == ('low' if fixture == 'storm_gyre' else 'normal')


def test_maximum_staffmod_is_green_and_does_not_create_market_facets():
    saved = json.loads((Path(__file__).parents[1] / 'fixtures/greater_claws.json').read_text())
    arrays = saved['snapshot']['resources']['items'][0]['resource_stats']['arrays']
    for array in arrays:
        for stat in array['stats']:
            if stat['id'] == 107:
                stat['raw'] = 3
    result = decode_items(saved['snapshot'], saved['report'])[0]
    row = next(r for r in result['decoded_stats'] if r.get('memory_stat', {}).get('id') == 107)
    assert row['roll_quality'] == 'perfect'
    assert '+3 (1-3)' in row['text']
    assert not any(a.get('memory_stat', {}).get('id') == 107 for a in result['item']['affixes'])


def test_runeword_total_shows_staffmod_bounds_without_ranking_the_total():
    import struct

    from inventory_tracking.items.staffmods import annotate_staffmods

    saved = json.loads((Path(__file__).parents[1] / 'fixtures/greater_claws.json').read_text())
    item = saved['snapshot']['resources']['items'][0]
    arrays = item['resource_stats']
    result = decode_items(saved['snapshot'], saved['report'])[0]
    row = next(r for r in result['decoded_stats'] if r.get('memory_stat', {}).get('id') == 107)
    row = {k: v for k, v in row.items() if not k.startswith('roll_')}
    row['text'] = '+2 to Blades of Ice (Assassin Only)'
    raw = bytearray.fromhex(arrays['item_data_hex'])
    struct.pack_into('<I', raw, 0x18, struct.unpack_from('<I', raw, 0x18)[0] | 0x04000000)
    arrays['item_data_hex'] = raw.hex()
    annotate_staffmods([row], item['details'], arrays, {'type': 'h2h2'})
    assert 'staffmod range: 1-3; total contributions unverified' in row['text']
    assert 'roll_quality' not in row
