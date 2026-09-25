from dataclasses import replace

from pricing.knowledge.assessment.handlers.definitions import named_definitions
from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_upgraded_ethereal_shaftstop_premium_requires_identity_and_perfect_ed():
    item = replace(
        facts('Boneweave', 'unique', 'Shaftstop'),
        ethereal=True,
        stats={'16:0': {'status': 'decoded', 'value': 220}},
        provenance={
            'capture': {
                'item_identity': {
                    'table': 'unique',
                    'table_id': named_definitions()['unique', 'Shaftstop']['table_id'],
                }
            }
        },
    )
    assert assess_tier(item)['tier'] == 'high'
    for changed in (
        replace(item, provenance={}),
        replace(item, ethereal=False),
        replace(item, stats={'16:0': {'status': 'decoded', 'value': 219}}),
        replace(item, base_code=facts('Mesh Armor').base_code),
    ):
        assert assess_tier(changed)['tier'] is None
