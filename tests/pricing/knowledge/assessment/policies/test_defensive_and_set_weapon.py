from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.policies.test_remaining_rolls import item


def test_stormshield_usefulness_does_not_imply_high_trade_tier_or_defense_premium():
    candidate = item('Monarch', 'Stormshield', {})
    assert assess_tier(candidate)['tier'] == 'low'
    assert assess_tier(replace(candidate, stats={'31:0': {'status': 'decoded', 'value': 500}}))['tier'] == 'low'
    assert assess_tier(replace(candidate, socket_contents='filled'))['tier'] is None
    assert assess_tier(replace(candidate, ethereal=True))['tier'] is None


@pytest.mark.parametrize('cb', [35, 38, 40])
def test_ik_maul_requires_original_two_empty_sockets_and_valid_crushing_blow(cb):
    candidate = replace(item('Ogre Maul', "Immortal King's Stone Crusher", {'136:0': cb}), rarity='set', sockets=2)
    result = assess_tier(candidate)
    assert result['tier'] == 'low'
    assert bool(result['reasons']) is (cb == 40)
    for other in (
        replace(candidate, sockets=0),
        replace(candidate, sockets=None),
        replace(candidate, socket_contents='filled'),
        replace(candidate, stats={}),
        replace(candidate, stats={'136:0': {'status': 'decoded', 'value': 41}}),
    ):
        assert assess_tier(other)['tier'] is None
