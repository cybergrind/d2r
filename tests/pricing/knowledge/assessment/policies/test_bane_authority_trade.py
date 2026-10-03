from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


def specimen():
    return Item('Light Belt', 'set', "Bane's Authority", ((105, 0, 10), (7, 0, 20 * 256), (31, 0, 3)))


def test_original_bane_belt_is_an_ordinary_candidate_without_a_roll_premium():
    result = assess_trade_qualification(normalize(specimen().capture()))
    assert result['status'] == 'candidate'
    assert 'fixed' in result['reason']
    assert 'price_estimate' not in result

    from pricing.knowledge.assessment.engine import assess_result

    assessed = assess_result(specimen().capture(), profiles=[])
    assert assessed.trade_tier['tier'] == 'low'
    assert assessed.trade_qualification['status'] == 'candidate'


@pytest.mark.parametrize(
    'changes',
    [
        {'base': 'Sharkskin Belt'},
        {'base': 'Vampirefang Belt'},
        {'ethereal': True},
        {'ethereal': None},
        {'sockets': None},
        {'socket_contents': 'unknown'},
        {'identified': False},
        {'raw_stats': ()},
    ],
)
def test_bane_review_does_not_transfer_to_unknown_or_upgraded_variants(changes):
    item = replace(specimen(), **changes)
    assert assess_trade_qualification(normalize(item.capture()))['status'] == 'unresolved'


@pytest.mark.parametrize(('cast', 'life'), [(9, 20), (11, 20), (10, 19), (10, 21)])
def test_bane_candidate_requires_its_fixed_native_bonuses(cast, life):
    item = replace(specimen(), raw_stats=((105, 0, cast), (7, 0, life * 256), (31, 0, 3)))
    assert assess_trade_qualification(normalize(item.capture()))['status'] == 'unresolved'
