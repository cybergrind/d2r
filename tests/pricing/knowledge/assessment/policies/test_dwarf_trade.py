import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


@pytest.mark.parametrize('mdr', [12, 13, 14, 15])
def test_fixed_gold_find_and_absorb_have_ordinary_demand_without_perfect_mdr(mdr):
    item = Item(
        'Ring',
        'unique',
        'Dwarf Star',
        ((35, 0, mdr), (79, 0, 100), (142, 0, 15), (7, 0, 40 * 256), (11, 0, 40 * 256), (28, 0, 15)),
        complete=True,
    )
    result = assess_trade_qualification(normalize(item.capture()))
    assert result['status'] == 'candidate'
    assert 'premium' not in result['reason'].lower() or 'no separate' in result['reason'].lower()
