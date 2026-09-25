from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('base', 'key', 'role_id'),
    [
        ('Circlet', '83:2', 'poison-nova-standard-circlet'),
        ('Coronet', '83:3', 'foh-tribrid-circlet'),
        ('Tiara', '83:7', 'abyss-standard-circlet'),
        ('Diadem', '83:4', 'berserk-mobility-circlet'),
    ],
)
def test_circlet_class_skill_and_fcr_select_build_role(base, key, role_id):
    item = replace(
        facts(base, 'rare'), stats={key: {'status': 'decoded', 'value': 2}, '105:0': {'status': 'decoded', 'value': 20}}
    )
    profiles = build()['profiles']
    roles = {r['id']: r for r in assess_roles(item, profiles)}
    assert roles[role_id]['status'] == 'partial'
    assert all(r['status'] == 'failed' for k, r in roles.items() if k.endswith('-circlet') and k != role_id)
    assert any(p['label'] == '2 sockets' and p['status'] == 'false' for p in roles[role_id]['preferences'])
    slower = replace(item, stats={**item.stats, '105:0': {'status': 'decoded', 'value': 10}})
    assert next(r for r in assess_roles(slower, profiles) if r['id'] == role_id)['status'] == 'failed'
    assert not any(r['id'] == role_id for r in assess_roles(replace(item, rarity='magic'), profiles))


def test_incomplete_circlet_capture_stays_conditional_not_confirmed():
    item = replace(facts('Diadem', 'rare'), capture_complete=False, stats={'105:0': {'status': 'decoded', 'value': 20}})
    role = next(r for r in assess_roles(item, build()['profiles']) if r['id'] == 'poison-nova-standard-circlet')
    assert role['status'] == 'partial'
    assert role['rule_trace']['truth'] == 'unknown'


def test_magic_fire_circlet_keeps_standard_and_prebuff_roles_separate():
    item = replace(facts('Diadem', 'magic'), stats={'188:8': {'status': 'decoded', 'value': 3}})
    roles = {r['id']: r for r in assess_roles(item, build()['profiles'])}
    assert roles['enchant-standard-circlet']['variant'] == 'Standard'
    assert roles['enchant-prebuff-circlet']['variant'] == 'Max Enchant'
    assert roles['enchant-standard-circlet']['status'] == 'partial'
    assert roles['enchant-prebuff-circlet']['status'] == 'partial'
    wrong_tree = replace(item, stats={'188:9': {'status': 'decoded', 'value': 3}})
    assert all(
        r['status'] == 'failed'
        for r in assess_roles(wrong_tree, build()['profiles'])
        if r['id'].startswith('enchant-') and r['id'].endswith('-circlet')
    )
