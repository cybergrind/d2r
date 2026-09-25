from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def helm(fire=8, magic=8, ed=200):
    return replace(
        facts('Death Mask', 'unique', "Hellwarden's Will"),
        stats={f'{s}:0': {'status': 'decoded', 'value': v} for s, v in [(333, fire), (358, magic), (16, ed)]},
    )


@pytest.mark.parametrize(('fire', 'magic', 'tier'), [(8, 8, 'high'), (8, 5, 'med'), (5, 8, 'med'), (5, 5, 'med')])
def test_hellwarden_tier_uses_both_enemy_resistance_rolls(fire, magic, tier):
    result = assess_tier(helm(fire, magic))
    assert result['status'] == 'reviewed'
    assert result['tier'] == tier
    assert result['source']['date'] == '2026-09-18'
    assert 'estimate_ist' not in result


def test_hellwarden_unknown_or_unsupported_variants_are_not_perfect():
    assert assess_tier(replace(helm(), stats={}))['status'] == 'conditional'
    for item in [
        helm(9, 8),
        helm(8, 4),
        helm(ed=216),
        replace(helm(), ethereal=True),
        replace(helm(), socket_contents='filled'),
    ]:
        assert assess_tier(item)['tier'] is None
