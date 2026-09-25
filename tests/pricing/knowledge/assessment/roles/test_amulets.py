from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def assess(role_id, quality, values, **changes):
    profile = next(p for p in build()['profiles'] if p['id'] == role_id)
    candidate = replace(
        facts('Amulet', quality), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}, **changes
    )
    return assess_roles(candidate, [profile])


@pytest.mark.parametrize(
    ('role_id', 'key', 'skills', 'fcr'),
    [
        ('lightning-starter-amulet', '188:9', 3, 0),
        ('nova-starter-amulet', '188:9', 1, 10),
        ('blizzard-starter-amulet', '188:10', 1, 10),
        ('enchant-budget-amulet', '188:8', 3, 10),
        ('enchant-prebuff-amulet', '188:8', 3, 10),
    ],
)
def test_magic_amulets_preserve_class_tree_cast_rate_and_variant(role_id, key, skills, fcr):
    values = {key: skills, '105:0': fcr}
    result = assess(role_id, 'magic', values)[0]
    assert result['status'] == 'partial'
    assert result['rule_trace']['truth'] == 'true'
    assert assess(role_id, 'rare', values) == []
    assert assess(role_id, 'magic', {'188:0': skills, '105:0': fcr})[0]['status'] == 'failed'
    assert assess(role_id, 'magic', {}, capture_complete=False)[0]['rule_trace']['truth'] == 'unknown'
    if fcr:
        assert assess(role_id, 'magic', values | {'105:0': fcr - 1})[0]['status'] == 'failed'


@pytest.mark.parametrize(
    ('role_id', 'fcr'),
    [
        ('nova-standard-amulet', 10),
        ('nova-mf-amulet', 10),
        ('nova-hydra-amulet', 10),
        ('enchant-standard-amulet', 15),
        ('enchant-mf-amulet', 15),
    ],
)
def test_crafted_amulet_minimum_fit_is_separate_from_planner_maxima(role_id, fcr):
    values = {'83:1': 2, '105:0': fcr}
    result = assess(role_id, 'crafted', values)[0]
    assert result['rule_trace']['truth'] == 'true'
    assert result['status'] == 'partial'
    assert any(p['status'] == 'false' for p in result['preferences'])
    assert assess(role_id, 'crafted', values | {'83:1': 1})[0]['status'] == 'failed'
    assert assess(role_id, 'magic', values) == []
    assert assess(role_id, 'crafted', values, ethereal=True)[0]['status'] == 'failed'
