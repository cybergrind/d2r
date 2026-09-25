from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_ormus_comparisons import ormus


@pytest.mark.parametrize('skill', [48, 49, 52, 56, 59])
def test_reviewed_ormus_skill_has_medium_tier_without_market_projection(skill):
    item = replace(ormus(skill), properties={})
    assert assess_tier(item)['tier'] == 'med'
    assert assess_tier(replace(item, ethereal=True))['tier'] is None


def test_ormus_tier_does_not_guess_other_skills_or_conflicting_element_rolls():
    item = ormus(59)
    for other in (
        ormus(),
        ormus(36),
        ormus(59, 4),
        replace(item, capture_complete=False),
        replace(item, stats=dict(item.stats) | {'107:48': {'status': 'decoded', 'value': 3}}),
        replace(item, stats=dict(item.stats) | {'331:0': {'status': 'decoded', 'value': 20}}),
    ):
        assert assess_tier(other)['tier'] is None
