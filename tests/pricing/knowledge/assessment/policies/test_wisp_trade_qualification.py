import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.cases.wisp_trade import CASES


@pytest.mark.parametrize('case', CASES, ids=lambda case: case.id)
def test_wisp_trade_roll_boundaries_and_unknown_variants(case):
    result = assess_trade_qualification(normalize(case.item.capture()))
    assert result['status'] == case.trade_checks['qualification']['status']
    if result['status'] != 'unresolved':
        assert result['material_stats'] == ['144:0', '80:0']
    assert 'price_estimate' not in result
