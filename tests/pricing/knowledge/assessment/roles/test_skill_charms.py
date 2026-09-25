from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('role_id', 'key', 'secondary'),
    [
        ('lightning-starter-skiller', '188:9', None),
        ('lightning-standard-life-skiller', '188:9', '7:0'),
        ('lightning-standard-fhr-skiller', '188:9', '99:0'),
        ('nova-standard-life-skiller', '188:9', '7:0'),
        ('blizzard-standard-life-skiller', '188:10', '7:0'),
        ('poison-starter-skiller', '188:17', None),
        ('poison-standard-life-skiller', '188:17', '7:0'),
        ('fury-standard-life-skiller', '188:2', '7:0'),
        ('hammer-standard-life-skiller', '188:24', '7:0'),
        ('hammer-standard-fhr-skiller', '188:24', '99:0'),
    ],
)
def test_skiller_roles_separate_tree_and_secondary_bonus_without_requiring_perfect_life(role_id, key, secondary):
    profile = next(p for p in build()['profiles'] if p['id'] == role_id)
    values = {key: 1}
    if secondary:
        values[secondary] = 20 if secondary == '7:0' else 12
    candidate = replace(
        facts('Grand Charm', 'magic'), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}
    )
    result = assess_roles(candidate, [profile])[0]
    assert result['rule_trace']['truth'] == 'true'
    assert result['status'] == 'partial'
    if secondary == '7:0':
        assert result['preferences'][0]['status'] == 'false'
    wrong = replace(candidate, stats={k: v for k, v in candidate.stats.items() if k != key})
    assert assess_roles(wrong, [profile])[0]['status'] == 'failed'
    assert assess_roles(replace(wrong, capture_complete=False), [profile])[0]['status'] == 'partial'
    assert assess_roles(replace(candidate, rarity='unique'), [profile]) == []
    if secondary:
        plain = replace(candidate, stats={key: candidate.stats[key]})
        assert assess_roles(plain, [profile])[0]['status'] == 'failed'
