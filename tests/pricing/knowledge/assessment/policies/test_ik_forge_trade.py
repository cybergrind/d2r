"""Fixed IK gloves are a small trade component, not a defense-roll premium."""

from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


@pytest.mark.parametrize('defense', [108, 111, 118, 228, 238])
def test_original_gloves_keep_trade_interest_across_defense_and_partial_set_totals(defense):
    item = Item('War Gauntlets', 'set', "Immortal King's Forge", ((31, 0, defense), (0, 0, 20), (2, 0, 20)))
    result = assess_trade_qualification(normalize(item.capture()))
    assert result['status'] == 'candidate'
    assert result['material_stats'] == []
    assert 'Low-value' in result['reason']
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
        {'base': 'Ogre Gauntlets'},
    ],
)
def test_unknown_or_upgraded_gloves_do_not_borrow_original_market_interest(changes):
    item = replace(Item('War Gauntlets', 'set', "Immortal King's Forge"), **changes)
    assert assess_trade_qualification(normalize(item.capture())).get('status') != 'candidate'
