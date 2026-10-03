"""Fixed original IK belts have small trade demand, without an invented roll premium."""

from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


def belt():
    return Item('War Belt', 'set', "Immortal King's Detail", ((31, 0, 89), (0, 0, 25), (39, 0, 28), (41, 0, 31)))


def test_original_belt_is_a_low_value_component_without_a_defense_roll_premium():
    result = assess_trade_qualification(normalize(belt().capture()))
    assert result['status'] == 'candidate'
    assert result['material_stats'] == []
    assert 'Low-value' in result['reason']
    assert 'fixed' in result['reason']
    assert 'other set pieces' in result['reason']
    assert 'price_estimate' not in result


@pytest.mark.parametrize(
    'changes',
    [
        {'ethereal': True},
        {'ethereal': None},
        {'sockets': 1},
        {'sockets': None},
        {'socket_contents': 'unknown'},
        {'identified': False},
        {'base': 'Colossus Girdle'},
    ],
)
def test_unknown_or_upgraded_belts_do_not_borrow_original_market_interest(changes):
    assert assess_trade_qualification(normalize(replace(belt(), **changes).capture())).get('status') != 'candidate'
