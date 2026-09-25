from dataclasses import replace

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_guardian_angel_ethereal_perfect_original_base_has_reviewed_premium():
    item = replace(
        facts('Templar Coat', 'unique', 'Guardian Angel'),
        ethereal=True,
        stats={'16:0': {'status': 'decoded', 'value': 200}},
    )
    assert assess_tier(item)['tier'] == 'high'
    for changed in (
        replace(item, ethereal=False),
        replace(item, ethereal=None),
        replace(item, stats={'16:0': {'status': 'decoded', 'value': 199}}),
        replace(item, stats={'16:0': {'status': 'decoded', 'value': 201}}),
        replace(item, base_code=facts('Hellforge Plate').base_code),
    ):
        assert assess_tier(changed)['tier'] is None
    assert assess_tier(replace(item, stats={}))['status'] == 'conditional'
