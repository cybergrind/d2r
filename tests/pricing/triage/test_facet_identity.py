from pricing.triage.engine import assess
from tests.pricing.triage.test_bands import listing
from tests.pricing.triage.test_named_bands import tables


def test_rainbow_facets_do_not_pool_elements_or_trigger_variants():
    variants = [
        ({'750': 5, '735': 5, '782': 100}, 10),
        ({'750': 3, '735': 3, '782': 100}, 0.5),
        ({'750': 5, '735': 5, '787': 100}, 4),
        ({'747': 5, '609': 5, '781': 100}, 1),
    ]
    rows = [
        listing(i * 3 + j, price)
        | {'name': 'Rainbow Facet', 'ethereal': False, 'properties': listing(i)['properties'] | props}
        for i, (props, price) in enumerate(variants)
        for j in range(3)
    ]
    data = tables(rows)
    item = {'category': 'uniques', 'name': 'Rainbow Facet', 'ethereal': False}
    for props, price in variants:
        result = assess(item | {'properties': props}, data)
        assert result['decision_ist'] == price
    for props in ({'750': 5, '735': 5}, {'783': 5, '723': 5, '784': 100}):
        result = assess(item | {'properties': props}, data)
        assert result['verdict'] == 'check'
        assert result['decision_ist'] is None


def test_facet_native_trigger_has_same_identity_as_market_fields():
    from pricing.triage.named_cohorts import value

    fire = {'properties': {'750': 5, '735': 5}, 'native_rolls': {'197:3615': 100}}
    assert value(fire, 'rainbow_variant', []) == 394
    assert value({'properties': {'750': 5, '735': 5, '782': 100}}, 'rainbow_variant', []) == 394
    assert value(fire | {'native_rolls': {'197:3614': 100}}, 'rainbow_variant', []) is None
    conflict = {'properties': {'750': 5, '735': 5, '782': 100}, 'native_rolls': {'197:3614': 100}}
    assert value(conflict, 'rainbow_variant', []) is None
    mixed = {'properties': {'750': 5, '735': 5, '782': 100, '747': 4, '609': 4}}
    assert value(mixed, 'rainbow_variant', []) is None


def test_reviewed_catalog_can_supply_unlisted_fixed_trigger_but_mismatch_cannot():
    from pricing.triage.adapters import from_listing
    from pricing.triage.named_cohorts import value

    basis = {
        'kind': 'reviewed_facet_catalog_variant',
        'table_id': 399,
        'catalog_id': '2188191106',
        'catalog_name': 'Rainbow Facet: Poison Level-up',
    }
    row = {
        'name': 'Rainbow Facet',
        'category': 'uniques',
        'catalog_id': basis['catalog_id'],
        'catalog_name': basis['catalog_name'],
        'facet_basis': {'identity': basis},
        'properties': {'783': 5, '723': 5},
    }
    assert value(from_listing(row), 'rainbow_variant', []) == 399
    assert value(from_listing(row | {'catalog_id': 'wrong'}), 'rainbow_variant', []) is None
