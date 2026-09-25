from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('role_id', 'values'),
    [
        ('lightning-standard-sc-mf-res', {80: 7, 39: 5, 41: 5, 43: 5, 45: 5}),
        ('lightning-standard-sc-fhr-res', {99: 5, 39: 5, 41: 5, 43: 5, 45: 5}),
        ('lightning-ubers-sc-life-res', {6: 20, 39: 5, 41: 5, 43: 5, 45: 5}),
        ('nova-mf-sc-mana-mf', {9: 17, 80: 7}),
        ('nova-standard-sc-light-mf', {41: 11, 80: 7}),
        ('nova-hydra-sc-fire-mf', {39: 11, 80: 7}),
        ('blizzard-standard-sc-life-cold', {6: 20, 43: 11}),
    ],
)
def test_small_charm_combination_preserves_roll_targets_and_cannot_use_another_charm_size(role_id, values):
    profile = next(p for p in build()['profiles'] if p['id'] == role_id)
    item = replace(
        facts('Small Charm', 'magic'), stats={f'{k}:0': {'status': 'decoded', 'value': v} for k, v in values.items()}
    )
    role = assess_roles(item, [profile])[0]
    assert role['status'] == 'partial'
    assert role['rule_trace']['truth'] == 'true'
    assert all(p['status'] == 'true' for p in role['preferences'])
    for key in item.stats:
        missing = replace(item, stats={k: v for k, v in item.stats.items() if k != key})
        assert assess_roles(missing, [profile])[0]['status'] == 'failed'
    assert (
        assess_roles(replace(item, stats={}, capture_complete=False), [profile])[0]['rule_trace']['truth'] == 'unknown'
    )
    assert assess_roles(replace(item, item_type='mcha'), [profile]) == []
    assert assess_roles(replace(item, rarity='unique'), [profile]) == []
