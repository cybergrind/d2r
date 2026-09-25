from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def anni(attributes, resistance, experience):
    values = {**dict.fromkeys((0, 1, 2, 3), attributes), **dict.fromkeys((39, 41, 43, 45), resistance), 85: experience}
    return replace(
        facts('Small Charm', 'unique', 'Annihilus'),
        stats={f'{k}:0': {'status': 'decoded', 'value': v} for k, v in values.items()},
    )


@pytest.mark.parametrize(
    ('attributes', 'resistance', 'experience', 'tier'),
    [
        (20, 20, 10, 'high'),
        (19, 19, 5, 'high'),
        (20, 18, 10, 'low'),
        (10, 10, 5, 'low'),
    ],
)
def test_annihilus_tier_uses_both_rolls_without_turning_research_bands_into_price(
    attributes, resistance, experience, tier
):
    result = assess_tier(anni(attributes, resistance, experience))
    assert result['tier'] == tier
    assert result['source']['date'] == '2026-09-18'


def test_annihilus_missing_roll_or_impossible_state_cannot_claim_premium():
    item = anni(20, 20, 10)
    missing = replace(item, stats={k: v for k, v in item.stats.items() if k != '45:0'})
    assert assess_tier(missing)['tier'] is None
    for changed in (anni(21, 20, 10), anni(20, 20, 11), replace(item, ethereal=True), replace(item, sockets=1)):
        assert assess_tier(changed)['status'] == 'pending_review'
