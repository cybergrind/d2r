import pytest

from pricing.knowledge.market_mechanics import apply_mechanics


@pytest.mark.parametrize('name', ['Small Charm', 'Large Charm', 'Grand Charm'])
def test_ordinary_charm_catalog_supplies_magic_quality_without_changing_evidence(name):
    row = {'name': name, 'category': 'charms', 'properties': {}, 'observed_at': None}
    apply_mechanics(row)
    assert row['rarity'] == 'magic'
    assert row['facet_basis']['rarity']['kind'] == 'ordinary_charm_catalog'
    assert row['properties'] == {}
    assert row['observed_at'] is None


@pytest.mark.parametrize('quality', ['rare', 'unique', 'normal'])
def test_contradictory_charm_quality_is_retained_and_rejected(quality):
    row = {'name': 'Small Charm', 'category': 'charms', 'rarity': quality, 'properties': {'797': quality}}
    apply_mechanics(row)
    assert row['rarity'] == quality
    assert row['mechanics_conflicts']


def test_crafted_sunder_and_jewel_catalogs_do_not_inherit_magic_quality():
    for name, category in [('Crafted Sunder Charm', 'charms'), ('Jewel', 'jewels'), ('Small Charm', 'unknown')]:
        row = {'name': name, 'category': category, 'properties': {}}
        apply_mechanics(row)
        assert 'rarity' not in row


def test_quality_inference_allows_exact_charm_comparisons_but_does_not_supply_dates():
    from datetime import date

    from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
    from tests.pricing.knowledge.assessment.test_comparables import contract, listing

    expected = contract() | {'name': 'Small Charm', 'rarity': 'magic', 'sockets': 0, 'properties': {'461': 7}}
    rows = []
    for i in range(3):
        row = listing(str(i), name='Small Charm', category='charms', properties={'461': 7}, observed_at=None)
        row.pop('rarity')
        apply_mechanics(row)
        rows.append(row)
    compared = evaluate(expected, rows)
    assert len(compared['accepted']) == 3
    assert price_from_comparables(compared)['estimate_ist'] is None
    for row in rows:
        row['observed_at'] = '2026-09-24'
    assert price_from_comparables(evaluate(expected, rows), today=date(2026, 9, 24))['estimate_ist'] == 2
