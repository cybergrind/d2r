import pytest

from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions
from tests.pricing.knowledge.assessment.item_bank.cases.annihilus_trade import CASES
from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import PATH, data


IDENTITY = ('unique', 'Annihilus')


@pytest.mark.parametrize(
    'omit',
    [
        None,
        'roll-18-20-10',
        'roll-20-18-10',
        'roll-19-19-5',
        'roll-20-20-10',
        'component-85-None',
        'unequal-1-10',
        'unequal-45-10',
        'unknown-sockets',
    ],
)
def test_annihilus_review_requires_independent_axes_and_native_members(omit):
    doc, context = data(IDENTITY, CASES)
    doc['rows'][0]['scope'] = 'compound_named_charm'
    if omit:
        del doc['rows'][0]['cases']['annihilus-trade/' + omit]
        if omit == 'roll-20-20-10':
            del doc['rows'][0]['cases']['annihilus-trade/complete-perfect-thin-price']
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == ('pending' if omit else 'reviewed')
    assert accepted == (set() if omit else {PATH})


@pytest.mark.parametrize('scope', ['scalar_named_charm', 'compound_named_jewelry', 'compound_colossal_jewel'])
def test_small_charm_compounds_cannot_borrow_existing_family_scopes(scope):
    doc, context = data(IDENTITY, CASES)
    doc['rows'][0]['scope'] = scope
    rows, accepted = review_dimensions(doc, **context)
    assert rows[IDENTITY]['state'] == 'pending'
    assert not accepted
