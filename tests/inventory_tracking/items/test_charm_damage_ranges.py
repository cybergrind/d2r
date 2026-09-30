"""Flat charm damage is a rolled modifier; weapon totals need separate treatment."""

import struct

import pytest

from inventory_tracking.items.affixes import resolve_affix_ranges
from inventory_tracking.items.metadata import decode_stats, metadata
from inventory_tracking.items.ranges import annotate_roll_ranges
from pricing.knowledge.definitions import scalar_ranges


def test_flat_damage_property_functions_require_explicit_affix_context():
    record = {'prop1': 'dmg-min', 'min1': 2, 'max1': 3, 'prop2': 'dmg-max', 'min2': 7, 'max2': 10}
    properties = {'dmg-min': {'func1': 5}, 'dmg-max': {'func1': 6}}
    assert scalar_ranges(record, properties, {}) == {}
    ranges = scalar_ranges(record, properties, {}, affix_flat_damage=True)
    assert ranges['21']['min'] == 2
    assert ranges['22']['max'] == 10
    assert ranges['23']['min'] == ranges['159']['min'] == 2
    assert ranges['24']['max'] == ranges['160']['max'] == 10


@pytest.mark.parametrize(
    ('suffix_record', 'value', 'bounds'), [(None, 10, (7, 10)), (678, 10, (10, 14)), (678, 14, (10, 14))]
)
def test_native_charm_damage_ranges_include_verified_contributions(suffix_record, value, bounds):
    meta = metadata()
    base = next(row for row in meta['bases'].values() if row['name'] == 'Grand Charm')
    raw = bytearray(96)
    struct.pack_into('<I', raw, 0, 4)
    struct.pack_into('<I', raw, 0x18, 0x10)
    for table, record, offset in (('prefix', 253, 0x48), ('suffix', suffix_record, 0x4E)):
        if record is not None:
            ident = next(
                int(key)
                for key, entry in meta['affixes'][table].items()
                if entry['source']['record_key'] == str(record)
            )
            struct.pack_into('<H', raw, offset, ident)
    context = resolve_affix_ranges({'quality': 4}, {'item_data_hex': raw.hex()}, base)
    decoded, _, _ = decode_stats([{'id': 22, 'layer': 0, 'raw': value}], base=base)
    annotate_roll_ranges(decoded, context)
    maximum = next(row for row in decoded if row.get('memory_stat', {}).get('id') == 22)
    assert (maximum['roll_range']['min'], maximum['roll_range']['max']) == bounds
    assert maximum['roll_quality_range']['max'] == bounds[1]
    assert maximum['roll_quality'] == ('perfect' if value == bounds[1] else 'normal')
