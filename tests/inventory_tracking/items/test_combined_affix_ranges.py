"""Totals of native affixes retain their joint bounds and legal tier combinations."""

import struct

import pytest

from inventory_tracking.items.affixes import resolve_affix_ranges
from inventory_tracking.items.identity import FLAGS_OFFSET, IDENTIFIED_FLAG, ITEM_DATA_SIZE, SOCKETED_FLAG
from inventory_tracking.items.metadata import decode_stats, metadata
from inventory_tracking.items.ranges import annotate_roll_ranges


def capture(*, element=39, quality=6, base_name='Ring'):
    meta = metadata()
    base = next(row for row in meta['bases'].values() if row['name'] == base_name)
    raw = bytearray(ITEM_DATA_SIZE)
    struct.pack_into('<I', raw, 0, quality)
    struct.pack_into('<I', raw, FLAGS_OFFSET, IDENTIFIED_FLAG)
    for table, records, offset in (
        ('prefix', (281, 334 if base_name == 'Ring' else 329, {39: 372, 41: 392, 43: 353, 45: 412}[element]), 0x48),
        ('suffix', (174, 286, 331), 0x4E),
    ):
        for index, record in enumerate(records):
            ident = next(int(k) for k, e in meta['affixes'][table].items() if e['source']['record_key'] == str(record))
            struct.pack_into('<H', raw, offset + index * 2, ident)
    return {'quality': quality}, {'item_data_hex': raw.hex()}, base


@pytest.mark.parametrize('element', [39, 41, 43, 45])
@pytest.mark.parametrize(('mf', 'resistance', 'quality'), [(25, 41, 'perfect'), (10, 29, 'normal')])
def test_ring_combined_affixes_have_roll_ranges(element, mf, resistance, quality):
    details, arrays, base = capture(element=element)
    context = resolve_affix_ranges(details, arrays, base)
    decoded, _, _ = decode_stats(
        [
            {'id': 80, 'layer': 0, 'raw': mf},
            {'id': element, 'layer': 0, 'raw': resistance},
        ],
        base=base,
    )
    annotate_roll_ranges(decoded, context)
    by_id = {row['memory_stat']['id']: row for row in decoded}
    for stat, bounds, envelope in ((80, (10, 25), (10, 25)), (element, (29, 41), (8, 41))):
        row = by_id[stat]
        assert (row['roll_range']['min'], row['roll_range']['max']) == bounds
        assert row['roll_quality_range']['min'] == envelope[0]
        assert row['roll_quality_range']['max'] == envelope[1]
        assert row['roll_quality'] == ('low' if stat == 80 and mf == 10 else quality)
        assert row['roll_tier'] == 1
        assert len(row['roll_range']['source']) == 2
    assert not any(f'stat {element}.' in reason or 'stat 80.' in reason for reason in context['review'])


@pytest.mark.parametrize('socket_evidence', ['flag', 'children', 'socket-stat'])
def test_uncertain_socket_contributions_do_not_get_combined_ranges(socket_evidence):
    details, arrays, base = capture(base_name='Circlet')
    if socket_evidence == 'flag':
        raw = bytearray.fromhex(arrays['item_data_hex'])
        struct.pack_into('<I', raw, FLAGS_OFFSET, IDENTIFIED_FLAG | SOCKETED_FLAG)
        arrays['item_data_hex'] = raw.hex()
    elif socket_evidence == 'children':
        arrays['socket_items'] = {'complete': True, 'children': [{'position': 0}]}
    else:
        arrays['arrays'] = [{'header_offset': 0xE8, 'stats': [{'id': 194, 'layer': 0, 'raw': 1}]}]
    context = resolve_affix_ranges(details, arrays, base)
    assert '80' not in context['roll_ranges']
    assert '39' not in context['roll_ranges']


def test_illegal_magic_six_affix_capture_is_not_combined():
    details, arrays, base = capture(quality=4)
    assert resolve_affix_ranges(details, arrays, base) is None


def test_outside_joint_bounds_is_not_a_roll():
    details, arrays, base = capture()
    context = resolve_affix_ranges(details, arrays, base)
    decoded, _, _ = decode_stats([{'id': 80, 'layer': 0, 'raw': 26}], base=base)
    annotate_roll_ranges(decoded, context)
    assert 'roll_range' not in decoded[0]


def test_verified_empty_sockets_allow_combined_ranges():
    details, arrays, base = capture(base_name='Circlet')
    raw = bytearray.fromhex(arrays['item_data_hex'])
    struct.pack_into('<I', raw, FLAGS_OFFSET, IDENTIFIED_FLAG | SOCKETED_FLAG)
    arrays.update(item_data_hex=raw.hex(), socket_items={'complete': True, 'children': []})
    assert resolve_affix_ranges(details, arrays, base)['roll_ranges']['80']['max'] == 25


@pytest.mark.parametrize(
    'defect', ['same-group', 'missing-pool', 'wrong-stat', 'wrong-property', 'missing-tier', 'bad-bounds']
)
def test_invalid_contributors_cannot_produce_joint_ranges(defect):
    from copy import deepcopy

    from inventory_tracking.items.combined_affix_ranges import combined_scalar_ranges

    meta = metadata()
    entries = [
        deepcopy(next(e for e in meta['affixes'][table].values() if e['source']['record_key'] == record))
        for table, record in (('prefix', '281'), ('suffix', '286'))
    ]
    pools = [deepcopy(meta['affix_pools'][e['rare_range_pools']['rin']['80']]) for e in entries]
    if defect == 'same-group':
        entries[1]['affix_table'] = entries[0]['affix_table']
        entries[1]['game_definition']['group'] = entries[0]['game_definition']['group']
    elif defect == 'missing-pool':
        pools[1] = {}
    elif defect == 'wrong-stat':
        entries[1]['roll_ranges']['80']['stat_id'] = 79
    elif defect == 'wrong-property':
        entries[1]['roll_ranges']['80']['property'] = 'gold%'
    elif defect == 'missing-tier':
        pools[1]['tiers'] = [{'min': 1, 'max': 2}]
    else:
        entries[1]['roll_ranges']['80']['min'] = 30
    assert combined_scalar_ranges(entries, lambda e, _: pools[entries.index(e)]) == {}


def test_lower_resistance_tiers_compare_with_best_joint_tier():
    details, arrays, base = capture()
    raw = bytearray.fromhex(arrays['item_data_hex'])
    meta = metadata()
    for offset, record in ((0x4A, '333'), (0x4C, '601')):
        ident = next(int(k) for k, e in meta['affixes']['prefix'].items() if e['source']['record_key'] == record)
        struct.pack_into('<H', raw, offset, ident)
    arrays['item_data_hex'] = raw.hex()
    context = resolve_affix_ranges(details, arrays, base)
    decoded, _, _ = decode_stats([{'id': 39, 'layer': 0, 'raw': 17}], base=base)
    annotate_roll_ranges(decoded, context)
    row = decoded[0]
    assert (row['roll_range']['min'], row['roll_range']['max']) == (8, 17)
    assert row['roll_quality_range']['max'] == 41
    assert row['roll_quality'] != 'perfect'
    assert row['roll_tier'] == 6
    assert '[T6; T1: 29-41%]' in row['text']


@pytest.mark.parametrize(('total', 'auto_record', 'tier'), [(4, 6, 3), (5, 7, 2), (6, 8, 1)])
def test_inherent_and_magic_skill_tab_bonuses_use_joint_maximum(total, auto_record, tier):
    meta = metadata()
    base = next(b for b in meta['bases'].values() if b['name'] == 'Matriarchal Javelin')
    raw = bytearray(ITEM_DATA_SIZE)
    struct.pack_into('<I', raw, 0, 4)
    struct.pack_into('<I', raw, FLAGS_OFFSET, IDENTIFIED_FLAG)
    for table, record, offset in (('prefix', 441, 0x48), ('auto', auto_record, 0x46)):
        ident = next(int(k) for k, e in meta['affixes'][table].items() if e['source']['record_key'] == str(record))
        struct.pack_into('<H', raw, offset, ident)
    context = resolve_affix_ranges({'quality': 4}, {'item_data_hex': raw.hex()}, base)
    decoded, _, _ = decode_stats([{'id': 188, 'layer': 2, 'raw': total}], base=base)
    annotate_roll_ranges(decoded, context)
    row = decoded[0]
    assert (row['roll_quality_range']['min'], row['roll_quality_range']['max']) == (2, 6)
    assert row['roll_range']['min'] == row['roll_range']['max'] == total
    assert row['roll_range']['layer'] == 2
    assert row['roll_tier'] == tier
    assert row['roll_quality'] == ('perfect' if total == 6 else 'normal')


@pytest.mark.parametrize('defect', ['different-layer', 'wrong-stat', 'different-key'])
def test_joint_skill_tabs_never_mix_parameters(defect):
    from copy import deepcopy

    from inventory_tracking.items.combined_affix_ranges import combined_scalar_ranges

    meta = metadata()
    entries = [
        deepcopy(next(e for e in meta['affixes'][table].values() if e['source']['record_key'] == record))
        for table, record in (('prefix', '441'), ('auto', '8'))
    ]
    if defect == 'different-layer':
        entries[1]['roll_ranges']['188:2']['layer'] = 0
    elif defect == 'wrong-stat':
        entries[1]['roll_ranges']['188:2']['stat_id'] = 83
    else:
        row = entries[1]['roll_ranges'].pop('188:2')
        row['layer'] = 0
        entries[1]['roll_ranges']['188:0'] = row
    assert combined_scalar_ranges(entries, lambda e, key: meta['affix_pools'][e['range_pools']['amf'][key]]) == {}
