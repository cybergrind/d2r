"""Native affix identity must survive capture and distinguish equal stat totals."""

import json
import struct
from pathlib import Path

import pytest

from inventory_tracking.items.affixes import resolve_affix_ranges
from inventory_tracking.items.metadata import item_base, metadata
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.roles.predicates import evaluate, validate


def native_id(table, record):
    return next(
        int(key) for key, row in metadata()['affixes'][table].items() if row['source']['record_key'] == str(record)
    )


def charm(prefix=253, suffix=678):
    base = next(row for row in metadata()['bases'].values() if row['name'] == 'Grand Charm')
    raw = bytearray(96)
    struct.pack_into('<I', raw, 0, 4)
    struct.pack_into('<I', raw, 0x18, 0x10)
    struct.pack_into('<H', raw, 0x48, native_id('prefix', prefix))
    if suffix:
        struct.pack_into('<H', raw, 0x4E, native_id('suffix', suffix))
    context = resolve_affix_ranges({'quality': 4}, {'item_data_hex': raw.hex()}, base)
    return base, raw, context


def extraction(base, native):
    return {
        'item': {'base_code': base['code'], 'rarity': 'magic', 'identified': True},
        'source': {'native_affixes': native},
        'decoded_stats': [],
    }


def test_same_maximum_damage_does_not_prove_maiming_suffix():
    base, _, context = charm()
    rule = {'op': 'affix_present', 'table': 'suffix', 'value': native_id('suffix', 678)}
    assert evaluate(rule, normalize(extraction(base, context['native_affixes']))).truth == 'true'
    _, _, plain = charm(suffix=None)
    assert evaluate(rule, normalize(extraction(base, plain['native_affixes']))).truth == 'false'
    assert evaluate(rule, normalize(extraction(base, None))).truth == 'unknown'


@pytest.mark.parametrize(
    ('filename', 'prefix', 'suffix'), [('large_charm_life20', 403, 343), ('large_charm_life35', 362, 346)]
)
def test_saved_capture_retains_native_affix_identity(filename, prefix, suffix):
    path = Path('tests/inventory_tracking/fixtures') / (filename + '.json')
    saved = json.loads(path.read_text())
    context = resolve_affix_ranges(saved['details'], saved['arrays'], item_base(saved['txt_id']))
    assert context['native_affixes'] == {
        'prefix': [native_id('prefix', prefix)],
        'suffix': [native_id('suffix', suffix)],
        'auto': [],
    }


@pytest.mark.parametrize('damage', ['extra', 'wrong-base', 'unknown', 'unidentified'])
def test_unverified_affix_identity_stays_unknown(damage):
    base, raw, _ = charm()
    if damage == 'extra':
        struct.pack_into('<H', raw, 0x4A, native_id('prefix', 253))
    elif damage == 'unknown':
        struct.pack_into('<H', raw, 0x4E, 65535)
    elif damage == 'unidentified':
        struct.pack_into('<I', raw, 0x18, 0)
    else:
        base = next(row for row in metadata()['bases'].values() if row['name'] == 'Small Charm')
    assert resolve_affix_ranges({'quality': 4}, {'item_data_hex': raw.hex()}, base) is None


@pytest.mark.parametrize(
    'native',
    [
        {'prefix': [], 'suffix': [65535], 'auto': []},
        {'prefix': [], 'suffix': [True], 'auto': []},
        {'prefix': [], 'suffix': [], 'auto': []},
        {'prefix': [], 'suffix': [678]},
    ],
)
def test_malformed_or_incompatible_identity_is_not_known_absence(native):
    base, _, _ = charm()
    rule = {'op': 'affix_present', 'table': 'suffix', 'value': native_id('suffix', 678)}
    assert evaluate(rule, normalize(extraction(base, native))).truth == 'unknown'


@pytest.mark.parametrize(
    'rule',
    [
        {'op': 'affix_present', 'table': 'bad', 'value': 678},
        {'op': 'affix_present', 'table': 'suffix', 'value': True},
        {'op': 'affix_present', 'table': 'suffix', 'value': 0},
    ],
)
def test_affix_predicate_rejects_invalid_schema(rule):
    with pytest.raises(ValueError, match='Invalid native affix'):
        validate(rule)


def test_native_affixes_flow_through_snapshot_decoding_and_fact_normalization():
    from pricing.knowledge.assessment.maintenance.replay import decode_snapshot

    saved = json.loads(Path('tests/pricing/knowledge/assessment/fixtures/replays/large_charm_life20.json').read_text())
    decoded = decode_snapshot(saved)
    native = decoded['source']['native_affixes']
    assert native['prefix'] == [native_id('prefix', 403)]
    assert native['suffix'] == [native_id('suffix', 343)]
    facts = normalize(decoded)
    assert facts.to_dict()['native_affixes'] == native
    with pytest.raises(TypeError, match='does not support item assignment'):
        facts.native_affixes['prefix'] = ()
