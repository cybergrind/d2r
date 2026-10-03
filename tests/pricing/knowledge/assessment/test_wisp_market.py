"""Wisp's legacy listing field must not become a global flat/percent alias."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.comparables import reject_reasons


def pair():
    contract = {
        'policy': 'named',
        'name': 'Wisp Projector',
        'rarity': 'unique',
        'base_code': 'rin',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': {'1866': 20, '461': 20},
    }
    row = {
        **contract,
        'catalog_id': '3269425307',
        'properties': {'689': 20, '461': 20},
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'amount': 1,
        'seller_id': 'seller',
        'ask_ist': 1,
    }
    return contract, row


def test_wisp_legacy_absorb_compares_as_native_percent_without_mutation():
    contract, row = pair()
    original = deepcopy(row)
    assert reject_reasons(contract, row) == []
    assert row == original


@pytest.mark.parametrize('value', [9, 21, True, 20.5, '20', float('nan')])
def test_wisp_legacy_absorb_rejects_invalid_native_values(value):
    contract, row = pair()
    contract['properties']['1866'] = value
    row['properties']['689'] = value
    assert reject_reasons(contract, row)


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('catalog_id', 'wrong'),
        ('catalog_id', None),
        ('name', 'Dwarf Star'),
        ('rarity', 'magic'),
        ('base_code', 'amu'),
        ('ethereal', True),
        ('ethereal', None),
        ('sockets', 1),
        ('socket_contents', 'filled'),
    ],
)
def test_wisp_alias_requires_exact_identity_and_native_variant(field, value):
    contract, row = pair()
    row[field] = value
    assert reject_reasons(contract, row)


@pytest.mark.parametrize('other', [19, 20])
def test_wisp_dual_absorb_fields_are_not_silently_collapsed(other):
    contract, row = pair()
    row['properties']['1866'] = other
    assert reject_reasons(contract, row)


def test_non_wisp_flat_absorb_cannot_match_percentage():
    contract, row = pair()
    contract['name'] = row['name'] = 'Other item'
    assert reject_reasons(contract, row)


def test_wisp_other_roll_and_extra_modifiers_still_require_exact_match():
    contract, row = pair()
    row['properties']['461'] = 19
    assert reject_reasons(contract, row)
    row['properties']['461'] = 20
    row['properties']['unknown'] = 1
    assert reject_reasons(contract, row)


def test_native_definition_changes_prevent_alias(monkeypatch):
    from pricing.knowledge.assessment.mechanics import wisp
    from pricing.knowledge.definition_store import catalog

    definition = dict(catalog().named['unique', 'Wisp Projector'])
    definition['game_definition'] = dict(definition['game_definition'], prop1='abs-ltng')
    original = wisp.native_definition
    monkeypatch.setattr(wisp, 'native_definition', lambda _: original(definition))
    contract, row = pair()
    assert 'Changed native Wisp definition.' in reject_reasons(contract, row)


def test_complete_native_wisp_matches_cached_rows_with_and_without_fixed_skills():
    import json
    from datetime import date
    from pathlib import Path

    from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
    from pricing.knowledge.assessment.maintenance.fixed_jewelry_market_review import native_jewelry_contract

    # Native skill IDs verified against the local decoder metadata; charges use
    # the game's packed remaining/capacity representation, not passive bonuses.
    raw = [{'id': 198, 'layer': 49 * 64 + 16, 'raw': 10}]
    raw += [
        {'id': 204, 'layer': skill * 64 + level, 'raw': (capacity << 8) + capacity}
        for skill, level, capacity in [(226, 2, 15), (236, 5, 13), (246, 7, 11)]
    ]
    contract = native_jewelry_contract('Wisp Projector', {144: 20, 80: 20}, extra_raw=raw)
    rows = [
        json.loads(line)
        for line in Path('pricing/data/appraisal-market.jsonl').read_text().splitlines()
        if 'Wisp Projector' in line
    ]
    result = evaluate(contract, rows)
    assert {r['listing_id'] for r in result['accepted']} == {'1002449066094', '1002503704430'}
    assert any('725' not in r['properties'] for r in result['accepted'])
    assert any('725' in r['properties'] for r in result['accepted'])
    assert result['summary']['priced_sellers'] == 2
    price = price_from_comparables(result, today=date(2026, 10, 2))
    assert price['unavailable_reason'] == 'thin'
    changed = deepcopy(result['accepted'][0])
    changed['properties']['725'] = 3
    assert reject_reasons(contract, changed)


def test_wisp_trade_evidence_uses_same_percent_projection():
    from pricing.knowledge.assessment.policies.trade_evidence import validate_segments

    _, row = pair()
    row['id'] = 'wisp'
    guard = {
        'all': [
            {'op': 'stat_at_least', 'key': '144:0', 'value': 20},
            {'op': 'stat_at_least', 'key': '80:0', 'value': 20},
        ]
    }
    review = {
        'material_stats': ['144:0', '80:0'],
        'market_stat_properties': {'144:0': '1866', '80:0': '461'},
        'valid_if': guard,
        'bands': [],
        'default_evidence_ids': ['wisp'],
        'market_evidence': [row],
    }
    validate_segments(review, guard)
    row['properties']['689'] = 19
    with pytest.raises(ValueError, match='variant or material roll'):
        validate_segments(review, guard)
