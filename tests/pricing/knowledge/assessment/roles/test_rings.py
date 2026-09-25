from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def assess(role_id, values, **changes):
    profile = next(p for p in build()['profiles'] if p['id'] == role_id)
    candidate = replace(
        facts('Ring', 'rare'), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}, **changes
    )
    return assess_roles(candidate, [profile])


@pytest.mark.parametrize(
    ('role_id', 'values', 'essential'),
    [
        ('lightning-starter-ring', {'105:0': 10, '9:0': 20, '39:0': 10, '43:0': 10}, '9:0'),
        ('lightning-ubers-ring', {'105:0': 10, '41:0': 25}, '41:0'),
        ('blizzard-starter-ring', {'0:0': 5, '7:0': 10, '43:0': 10}, '0:0'),
        ('blizzard-mf-ring', {'105:0': 10, '80:0': 10}, '80:0'),
        ('blizzard-set-ring', {'105:0': 10, '80:0': 10}, '80:0'),
    ],
)
def test_rare_ring_candidates_keep_role_stats_and_secondary_maxima_separate(role_id, values, essential):
    result = assess(role_id, values)[0]
    assert result['rule_trace']['truth'] == 'true'
    assert result['status'] == 'partial'
    assert any(p['status'] == 'false' for p in result['preferences'])
    assert assess(role_id, values | {essential: 0})[0]['status'] == 'failed'
    assert assess(role_id, values, rarity='magic') == []
    assert assess(role_id, {}, capture_complete=False)[0]['rule_trace']['truth'] == 'unknown'


@pytest.mark.parametrize('resists', [('39:0', '41:0', '43:0'), ('39:0', '43:0', '45:0')])
def test_nova_tri_resistance_ring_accepts_three_distinct_elements_not_two(resists):
    values = {'105:0': 10, **dict.fromkeys(resists, 10)}
    assert assess('nova-starter-ring', values)[0]['rule_trace']['truth'] == 'true'
    del values[resists[-1]]
    assert assess('nova-starter-ring', values)[0]['status'] == 'failed'
    assert assess('nova-starter-ring', values, capture_complete=False)[0]['status'] == 'partial'
