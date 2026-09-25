from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers.definitions import named_definitions
from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(('base', 'ed'), [('Grand Crown', 198), ('Corona', 200)])
def test_crown_thieves_premium_needs_ethereal_gold_leech_and_defense_roll(base, ed):
    item = replace(
        facts(base, 'unique', 'Crown of Thieves'),
        ethereal=True,
        stats={f'{k}:0': {'status': 'decoded', 'value': v} for k, v in ((79, 100), (60, 12), (16, ed))},
        provenance={
            'capture': {
                'item_identity': {
                    'table': 'unique',
                    'table_id': named_definitions()['unique', 'Crown of Thieves']['table_id'],
                }
            }
        },
    )
    assert assess_tier(item)['tier'] == 'high'
    for key, value in [('79:0', 99), ('60:0', 11), ('16:0', 197), ('79:0', 101), ('60:0', 13), ('16:0', 201)]:
        changed = replace(item, stats={**item.stats, key: {'status': 'decoded', 'value': value}})
        assert assess_tier(changed)['tier'] is None
    assert assess_tier(replace(item, ethereal=False))['tier'] is None
    missing = replace(item, stats={k: v for k, v in item.stats.items() if k != '60:0'})
    assert assess_tier(missing)['status'] == 'conditional'
    if base == 'Corona':
        assert assess_tier(replace(item, provenance={}))['tier'] is None
