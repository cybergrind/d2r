from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('hammer-starter-belt', 'magic', {99: 24, 39: 30}),
    ('blizzard-starter-belt', 'magic', {99: 24, 39: 30}),
    ('wake-starter-belt', 'magic', {99: 24, 39: 30}),
    ('foh-starter-belt', 'magic', {7: 100, 43: 30}),
    ('holybolt-starter-belt', 'magic', {7: 100, 43: 30}),
    ('fury-starter-belt', 'magic', {7: 90, 39: 25}),
    ('poison-starter-belt', 'magic', {7: 80, 39: 25}),
    ('goldfind-budget-belt', 'rare', {99: 24, 43: 25, 41: 25, 79: 80}),
]


@pytest.mark.parametrize(('role_id', 'quality', 'values'), CASES)
def test_belt_role_requires_combination_and_preserves_cited_roll_targets(role_id, quality, values):
    profile = next(p for p in build()['profiles'] if p['id'] == role_id)
    item = replace(
        facts('Sharkskin Belt', quality),
        stats={f'{stat}:0': {'status': 'decoded', 'value': value} for stat, value in values.items()},
    )
    result = assess_roles(item, [profile])[0]
    assert result['rule_trace']['truth'] == 'true'
    assert result['status'] == 'partial'
    assert all(p['status'] == 'true' for p in result['preferences'])
    assert result['side'] == 'player'
    for key in item.stats:
        without = replace(item, stats={k: v for k, v in item.stats.items() if k != key})
        assert assess_roles(without, [profile])[0]['status'] == 'failed'
    incomplete = replace(item, stats={}, capture_complete=False)
    assert assess_roles(incomplete, [profile])[0]['rule_trace']['truth'] == 'unknown'
    assert assess_roles(replace(item, rarity='unique'), [profile]) == []
    assert assess_roles(replace(item, item_type='boot'), [profile]) == []
    weak = replace(item, stats={k: {'status': 'decoded', 'value': 1} for k in item.stats})
    assert all(p['status'] == 'false' for p in assess_roles(weak, [profile])[0]['preferences'])
