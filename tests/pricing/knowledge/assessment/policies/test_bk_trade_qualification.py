from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


@pytest.mark.parametrize(
    ('leech', 'status'), [(3, 'candidate'), (4, 'candidate'), (5, 'premium'), (2, 'unresolved'), (6, 'unresolved')]
)
def test_bk_trade_requires_legal_leech_and_reserves_premium_for_five(leech, status):
    facts = normalize(Item('Ring', 'unique', "Bul-Kathos' Wedding Band", ((60, 0, leech),)).capture())
    result = assess_trade_qualification(facts)
    assert result['status'] == status
    assert 'price_estimate' not in result


@pytest.mark.parametrize(
    'changes',
    [{'ethereal': True}, {'ethereal': None}, {'sockets': 1}, {'sockets': None}, {'identified': False}, {'stats': {}}],
)
def test_bk_missing_or_impossible_variant_never_inherits_trade_candidate(changes):
    facts = normalize(Item('Ring', 'unique', "Bul-Kathos' Wedding Band", ((60, 0, 5),)).capture())
    assert assess_trade_qualification(replace(facts, **changes))['status'] == 'unresolved'
