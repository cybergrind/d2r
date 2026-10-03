import pytest

from pricing.knowledge.definition_store import catalog
from pricing.knowledge.market import normalize_listing
from pricing.knowledge.market_named_defense import defense_conflict
from tests.pricing.knowledge.test_market import listing


def aldur_listing(tier, defense, *, property_id=1855):
    raw = listing()
    raw['properties'] = [p for p in raw['properties'] if p['property_id'] not in (797, 738, 402, 934, 930, 1855, 399)]
    if tier is not None:
        raw['properties'].append({'property_id': 930, 'type': 'string', 'string': tier})
    if defense is not None:
        raw['properties'].append({'property_id': property_id, 'type': 'number', 'number': defense})
    return normalize_listing(raw, name="Aldur's Advance", category='sets', source='fixture')


@pytest.mark.parametrize(('tier', 'defense'), [('Elite', 40), ('Elite', 58), ('Exceptional', 38)])
def test_aldur_explicit_base_rejects_total_defense_below_native_minimum(tier, defense):
    row = aldur_listing(tier, defense)
    assert any('defense' in reason.lower() for reason in row.get('mechanics_conflicts', ()))
    assert row['properties']['1855'] == defense
    assert row['facet_basis']['base_code']['tier'] == tier


@pytest.mark.parametrize(('tier', 'defense'), [('Elite', 59), ('Elite', 68), ('Exceptional', 39), ('Exceptional', 47)])
def test_aldur_valid_defense_endpoints_are_not_conflicts(tier, defense):
    assert not aldur_listing(tier, defense).get('mechanics_conflicts')


@pytest.mark.parametrize(
    ('tier', 'defense', 'property_id'), [('Elite', None, 1855), ('Elite', 40, 399), (None, 40, 1855)]
)
def test_aldur_unknown_base_or_total_is_not_fabricated(tier, defense, property_id):
    row = aldur_listing(tier, defense, property_id=property_id)
    assert not row.get('mechanics_conflicts')
    if tier is None:
        assert row.get('base_code') is None
    if property_id == 399:
        assert '1855' not in row['properties']


def test_changed_native_defense_effect_requires_review():
    definition = catalog().named_variants['set', "Aldur's Advance"][0]
    variants = [{**definition, 'game_definition': {**definition['game_definition'], 'prop8': 'ac%'}}]
    row = aldur_listing('Elite', 59)
    assert 'review' in defense_conflict(row, variants)


def test_defense_check_does_not_treat_set_totals_as_intrinsic_upper_bounds():
    assert not aldur_listing('Exceptional', 197).get('mechanics_conflicts')
