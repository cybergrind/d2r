from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('abyss-starter-crafted-belt', {105: 5, 99: 10, 9: 20, 27: 10, 39: 10, 41: 10, 43: 10}),
    ('echoing-starter-crafted-belt', {105: 5, 99: 10, 9: 20, 27: 10, 39: 10}),
    ('fire-starter-crafted-belt', {105: 5, 99: 10, 9: 20, 39: 10}),
    ('fissure-starter-crafted-belt', {105: 10, 0: 9, 9: 20, 27: 10, 39: 10, 41: 10, 43: 10}),
    ('lightning-starter-crafted-belt', {105: 10, 99: 17, 9: 40, 27: 10, 41: 30}),
    ('nova-starter-crafted-belt', {105: 10, 9: 20, 27: 10, 39: 30, 41: 30, 43: 30}),
    ('summoner-starter-crafted-belt', {105: 10, 7: 60, 9: 20, 27: 10, 43: 30}),
    ('smite-starter-crafted-belt', {99: 24, 60: 3, 135: 10, 7: 20}),
]


@pytest.mark.parametrize(('role_id', 'values'), CASES)
def test_crafted_belt_preserves_recipe_role_and_source_roll_preferences(role_id, values):
    profile = next(p for p in build()['profiles'] if p['id'] == role_id)
    item = replace(
        facts('Sharkskin Belt', 'crafted'),
        stats={f'{k}:0': {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    result = assess_roles(item, [profile])[0]
    assert result['status'] == 'partial'
    assert result['rule_trace']['truth'] == 'true'
    assert all(p['status'] == 'true' for p in result['preferences'])
    key = '135:0' if role_id.startswith('smite') else '105:0'
    missing = replace(item, stats={k: v for k, v in item.stats.items() if k != key})
    assert assess_roles(missing, [profile])[0]['status'] == 'failed'
    assert assess_roles(replace(missing, capture_complete=False), [profile])[0]['rule_trace']['truth'] == 'unknown'
    assert assess_roles(replace(item, rarity='rare'), [profile]) == []
    if role_id.startswith('smite'):
        assert any('Life Tap' in s for s in result['missing'])
