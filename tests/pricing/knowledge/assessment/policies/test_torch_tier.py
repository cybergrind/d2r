from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def torch(class_id, attributes, resistance):
    values = {**dict.fromkeys((0, 1, 2, 3), attributes), **dict.fromkeys((39, 41, 43, 45), resistance)}
    stats = {f'{k}:0': {'status': 'decoded', 'value': v} for k, v in values.items()}
    stats[f'83:{class_id}'] = {'status': 'decoded', 'value': 3}
    return replace(facts('Large Charm', 'unique', 'Hellfire Torch'), stats=stats)


@pytest.mark.parametrize('class_id', range(8))
def test_torch_premium_tiers_preserve_class_and_observed_roll_buckets(class_id):
    perfect = assess_tier(torch(class_id, 20, 20))
    assert perfect['tier'] == 'high'
    near = assess_tier(torch(class_id, 18, 19))
    assert near['tier'] == ('high' if class_id in (0, 1, 5, 6, 7) else None)
    assert assess_tier(torch(class_id, 10, 10))['tier'] is None


def test_torch_missing_or_conflicting_class_cannot_resolve_a_tier():
    item = torch(1, 20, 20)
    for changed in (
        replace(item, stats={k: v for k, v in item.stats.items() if not k.startswith('83:')}),
        replace(item, stats={**item.stats, '83:0': {'status': 'decoded', 'value': 3}}),
        replace(item, ethereal=True),
        replace(item, sockets=1),
        torch(1, 21, 20),
    ):
        assert assess_tier(changed)['tier'] is None
    missing_roll = replace(item, stats={k: v for k, v in item.stats.items() if k != '45:0'})
    assert assess_tier(missing_roll)['status'] == 'conditional'
