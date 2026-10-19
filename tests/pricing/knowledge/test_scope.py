import pytest

from pricing.knowledge import market, scope
from tests.pricing.scope_cases import CASES, IDS, raw_properties


@pytest.mark.parametrize(('properties', 'status'), [(p, s) for _, p, s in CASES], ids=IDS)
def test_scope_decisions(properties, status):
    listing = {'properties': raw_properties(properties)}
    assert scope.scope_status(scope.property_values(listing['properties'])) == status
    assert scope.listing_scope(listing) == status
    assert scope.in_scope(listing) is (status == 'verified')


def test_listing_without_properties_is_unknown():
    assert scope.listing_scope({}) == 'unknown'
    assert scope.listing_scope({'properties': None}) == 'unknown'


@pytest.mark.parametrize(('properties', 'status'), [(p, s) for _, p, s in CASES], ids=IDS)
def test_kb_rows_carry_the_shared_decision(properties, status):
    assert market.scope_status is scope.scope_status
    row = market.normalize_listing(
        {'id': 1, 'amount': 1, 'properties': raw_properties(properties)},
        name='Greater Talons',
        category='base',
        source='fixture',
        currencies={'ist': 1},
    )
    assert row['scope_status'] == status
