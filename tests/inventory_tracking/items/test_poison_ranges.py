import struct

import pytest

from inventory_tracking.items.affixes import resolve_affix_ranges
from inventory_tracking.items.metadata import decode_stats, metadata
from inventory_tracking.items.ranges import annotate_roll_ranges


def annotated(prefix=None, suffix='of Pestilence', *, rate=52, frames=125):
    meta = metadata()
    base = next(b for b in meta['bases'].values() if b['name'] == 'Small Charm')
    raw = bytearray(96)
    struct.pack_into('<I', raw, 0, 4)
    struct.pack_into('<I', raw, 0x18, 0x10)
    for table, name, offset in (('prefix', prefix, 0x48), ('suffix', suffix, 0x4E)):
        if name:
            entry = next(
                e for e in meta['affixes'][table].values() if e['name'] == name and base['code'] in e['base_codes']
            )
            struct.pack_into('<H', raw, offset, entry['table_id'])
    context = resolve_affix_ranges({'quality': 4}, {'item_data_hex': raw.hex()}, base)
    stats = [{'id': stat, 'layer': 0, 'raw': value} for stat, value in ((57, rate), (58, rate), (59, frames), (326, 1))]
    decoded, _, _ = decode_stats(stats, base=base)
    annotate_roll_ranges(decoded, context)
    return decoded[0]


def test_poison_suffix_has_size_wide_range_tier_and_best_duration():
    row = annotated()
    assert row['text'] == '+25 (6-50) Poison Damage over 5 Seconds [Suffix T2; T1: 50 over 6 Seconds]'
    assert row['roll_tier'] == 2
    assert row['roll_quality'] != 'perfect'


def test_verified_two_affix_poison_uses_combined_rate_and_duration():
    row = annotated('Pestilent', 'of Anthrax', rate=385, frames=300)
    assert row['roll_quality'] == 'perfect'
    assert row['roll_tier'] == 1
    assert '451' in row['text']
    assert '12 Seconds' in row['text']
    assert row['roll_range']['max'] == 451


@pytest.mark.parametrize(('rate', 'frames'), [(53, 125), (52, 100)])
def test_poison_totals_inconsistent_with_captured_affix_are_not_annotated(rate, frames):
    assert 'roll_range' not in annotated(rate=rate, frames=frames)
