"""Native capture reports use the ordinary/seasonal ranges they actually observe."""

import struct
from pathlib import Path

import pytest

from inventory_tracking.items.identity import identity_issues, resolve_identity
from inventory_tracking.items.ranges import annotate_roll_ranges
from pricing.knowledge.definitions import build_definitions


@pytest.fixture(scope='module')
def bane():
    data = build_definitions(Path(__file__).resolve().parents[3])
    return next(r for r in data['rows'] if r['rarity'] == 'unique' and r['table_id'] == 54)


def capture(stats, *, complete=True, socketed=False):
    raw = bytearray(0x60)
    struct.pack_into('<I', raw, 0, 7)
    struct.pack_into('<I', raw, 0x18, 0x10 | (0x800 if socketed else 0))
    struct.pack_into('<I', raw, 0x34, 54)
    return {
        'item_data_hex': raw.hex(),
        'complete': complete,
        'arrays': [{'header_offset': 0xE8, 'stats': [{'id': k, 'layer': 0, 'raw': v} for k, v in stats.items()]}],
    }


def install(monkeypatch, bane):
    monkeypatch.setattr('inventory_tracking.items.identity.metadata', lambda: {'identities': {'unique': {'54': bane}}})


def test_ordinary_bane_ash_retains_its_enhanced_damage_range(monkeypatch, bane):
    install(monkeypatch, bane)
    identity = resolve_identity({'quality': 7}, capture({93: 20}), {'code': bane['base_code']})
    assert identity['definition_variant'] == 'ordinary'
    row = {
        'status': 'decoded',
        'value': 55,
        'memory_stat': {'id': 17, 'layer': 0},
        'label': '+{{value}}% Enhanced Damage',
        'text': '+55% Enhanced Damage',
    }
    annotate_roll_ranges([row], identity)
    assert row['roll_range']['min'] == 50
    assert row['roll_range']['max'] == 60
    assert row['text'] == '+55% (50-60%) Enhanced Damage'
    assert '105' not in identity['roll_ranges']


def test_seasonal_bane_ash_does_not_require_removed_enhanced_damage(monkeypatch, bane):
    install(monkeypatch, bane)
    identity = resolve_identity({'quality': 7}, capture({105: 20}), {'code': bane['base_code']})
    assert identity['definition_variant'] == 'seasonal'
    assert identity['mode_eligibility'] == 'ladder_only'
    assert not identity['enhanced_damage_expected']
    assert not identity_issues(identity, [])


@pytest.mark.parametrize('kwargs', [{'complete': False}, {'socketed': True}])
def test_partial_or_socketed_capture_retains_the_reviewed_non_ladder_default(monkeypatch, bane, kwargs):
    install(monkeypatch, bane)
    identity = resolve_identity({'quality': 7}, capture({93: 20}, **kwargs), {'code': bane['base_code']})
    assert identity['name'] == 'Bane Ash'
    assert identity['definition_variant'] == 'ordinary'
    assert identity['variant_basis'] == 'non_ladder_scope'
    assert identity['roll_ranges']['17']['min'] == 50


@pytest.mark.parametrize(
    'descriptors',
    [
        None,
        [None],
        [{'header_offset': 0xE8, 'stats': None}],
        [{'header_offset': 0xE8, 'stats': [None]}],
        [{'header_offset': 0xE8, 'stats': [{'raw': 20}]}],
        [{'header_offset': 0xE8, 'stats': [{'id': '93', 'layer': 0, 'raw': 20}]}],
    ],
)
def test_malformed_capture_does_not_establish_an_observed_version(monkeypatch, bane, descriptors):
    install(monkeypatch, bane)
    arrays = capture({93: 20})
    arrays['arrays'] = descriptors
    identity = resolve_identity({'quality': 7}, arrays, {'code': bane['base_code']})
    assert identity['definition_variant'] == 'ordinary'
    assert identity['variant_basis'] == 'non_ladder_scope'
    assert 'mode_eligibility' not in identity


def test_malformed_cast_rate_cannot_prove_ordinary_manald():
    from inventory_tracking.items.seasonal_identity import resolve_seasonal_identity

    data = build_definitions(Path(__file__).resolve().parents[3])
    manald = next(row for row in data['rows'] if row['rarity'] == 'unique' and row['table_id'] == 121)
    arrays = {'complete': True, 'arrays': [{'header_offset': 0xE8, 'stats': [{'id': '105', 'layer': 0, 'raw': 10}]}]}
    result = resolve_seasonal_identity(manald, arrays, socketed=False)
    assert result['definition_variant'] == 'ordinary'
    assert result['variant_basis'] == 'non_ladder_scope'
    assert '105' not in result['roll_ranges']


def test_conflicting_complete_modifiers_do_not_select_either_version(monkeypatch, bane):
    install(monkeypatch, bane)
    identity = resolve_identity({'quality': 7}, capture({93: 20, 105: 20}), {'code': bane['base_code']})
    assert identity['definition_variant'] == 'unresolved'
    assert '17' not in identity['roll_ranges']
    assert any('version' in note.lower() for note in identity_issues(identity, []))
