import json
import struct
from pathlib import Path

import pytest

from inventory_tracking.items.affixes import resolve_charm_ranges
from inventory_tracking.items.metadata import decode_stats, item_base
from inventory_tracking.items.ranges import annotate_roll_ranges


FIXTURE = Path(__file__).parents[1] / 'fixtures/small_charm_vita.json'


def test_captured_charm_uses_its_affix_tiers():
    capture = json.loads(FIXTURE.read_text())
    base = item_base(capture['txt_id'])
    context = resolve_charm_ranges(capture['details'], capture['arrays'], base)
    decoded, _, _ = decode_stats(capture['arrays']['arrays'][-1]['stats'], base=base)
    annotate_roll_ranges(decoded, context)
    life = next(r for r in decoded if r.get('memory_stat', {}).get('id') == 7)
    defense = next(r for r in decoded if r.get('memory_stat', {}).get('id') == 31)
    assert life['text'] == '+20 (5-20) to Life [T1; T1: 16-20]'
    assert life['roll_quality'] == 'perfect'
    assert defense['roll_range']['min'] == 4
    assert defense['roll_range']['max'] == 8


@pytest.mark.parametrize('change', ['unidentified', 'unknown', 'wrong_base', 'extra_affix'])
def test_unverified_charm_affixes_do_not_claim_ranges(change):
    capture = json.loads(FIXTURE.read_text())
    raw = bytearray.fromhex(capture['arrays']['item_data_hex'])
    base = item_base(capture['txt_id'])
    if change == 'unidentified':
        struct.pack_into('<I', raw, 0x18, 0)
    elif change == 'unknown':
        struct.pack_into('<H', raw, 0x48, 65535)
    elif change == 'extra_affix':
        struct.pack_into('<H', raw, 0x4A, 921)
    else:
        base = {**base, 'code': 'invalid'}
    capture['arrays']['item_data_hex'] = raw.hex()
    assert resolve_charm_ranges(capture['details'], capture['arrays'], base) is None


@pytest.mark.parametrize(
    ('name', 'quality', 'tier'),
    [
        ('large_charm_life20', 'normal', (16, 20)),
        ('large_charm_life35', 'perfect', (31, 35)),
    ],
)
def test_large_charm_color_compares_all_spawnable_tiers(name, quality, tier):
    capture = json.loads((FIXTURE.parent / f'{name}.json').read_text())
    base = item_base(capture['txt_id'])
    context = resolve_charm_ranges(capture['details'], capture['arrays'], base)
    decoded, _, _ = decode_stats(capture['arrays']['arrays'][-1]['stats'], base=base)
    annotate_roll_ranges(decoded, context)
    life = next(r for r in decoded if r.get('memory_stat', {}).get('id') == 7)
    assert life['roll_quality'] == quality
    expected_tier = 4 if name.endswith('20') else 1
    assert life['roll_tier'] == expected_tier
    assert f'(6-35) to Life [T{expected_tier}; T1: 31-35]' in life['text']
    assert (life['roll_range']['min'], life['roll_range']['max']) == tier
    assert life['roll_quality_range'] == {'min': 6, 'max': 35, 'scope': 'all spawnable tiers for this charm size'}
