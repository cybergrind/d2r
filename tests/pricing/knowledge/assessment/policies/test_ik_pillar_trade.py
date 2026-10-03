from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


@pytest.mark.parametrize('defense', [118, 123, 128, 288])
def test_pillar_fixed_affixes_do_not_gain_a_defense_or_equipped_set_premium(defense):
    item = Item('War Boots', 'set', "Immortal King's Pillar", ((31, 0, defense),))
    result = assess_trade_qualification(normalize(item.capture()))
    assert result['status'] == 'candidate'
    assert result['material_stats'] == []
    assert 'price_estimate' not in result


@pytest.mark.parametrize(
    'changes',
    [
        {'base': 'Myrmidon Greaves'},
        {'ethereal': True},
        {'ethereal': None},
        {'sockets': 1},
        {'sockets': None},
        {'socket_contents': 'unknown'},
        {'identified': False},
    ],
)
def test_pillar_trade_evidence_does_not_transfer_to_unverified_variants(changes):
    item = replace(Item('War Boots', 'set', "Immortal King's Pillar", ((31, 0, 128),)), **changes)
    assert assess_trade_qualification(normalize(item.capture()))['status'] == 'unresolved'
