from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


SET_CASES = [
    (slug, name, base, cls, members)
    for slug, cls, members in [
        (
            'strafe-amazon',
            'Amazon',
            [("Sigon's Visor", 'Great Helm'), ("Sigon's Gage", 'Gauntlets'), ("Sigon's Sabot", 'Greaves')],
        ),
        (
            'double-throw-barbarian-guide',
            'Barbarian',
            [("Sigon's Visor", 'Great Helm'), ("Sigon's Gage", 'Gauntlets'), ("Sigon's Sabot", 'Greaves')],
        ),
        (
            'berserk-barbarian',
            'Barbarian',
            [("Sigon's Gage", 'Gauntlets'), ("Sigon's Wrap", 'Plated Belt'), ("Sigon's Sabot", 'Greaves')],
        ),
        ('enchant-sorceress', 'Sorceress', [("Death's Hand", 'Leather Gloves'), ("Death's Guard", 'Sash')]),
    ]
    for name, base in members
]


@pytest.mark.parametrize(('slug', 'name', 'base', 'character', 'members'), SET_CASES)
def test_starter_set_companions_remain_specific_to_build_and_wearer(slug, name, base, character, members):
    profiles = build()['profiles']
    profile = next((p for p in profiles if p['id'] == f'{slug}-starter-set-{name}'), None)
    assert profile is not None
    item = facts(base, 'set', name)
    names = [n for n, _ in members]
    context = {'player_class': character, 'player_items': names}
    role = assess_roles(item, [profile], context)[0]
    assert all(d['status'] == 'true' for d in role['dependencies'] if not d['label'].startswith('Socket'))
    assert role['status'] == 'partial'
    for companion in set(names) - {name}:
        changed = {**context, 'player_items': [n for n in names if n != companion], 'mercenary_items': names}
        assert any(d['status'] == 'false' for d in assess_roles(item, [profile], changed)[0]['dependencies'])
    assert all(
        d['status'] == 'unknown'
        for d in assess_roles(item, [profile], {'player_class': character})[0]['dependencies']
        if not d['label'].startswith('Socket')
    )
    assert not assess_roles(replace(item, name='Unrelated piece'), [profile], context)
    if name == "Sigon's Visor" and slug == 'strafe-amazon':
        assert any('Ort Rune' in m for m in role['missing'])
        socketed = replace(item, sockets=1, socket_contents='filled', socket_items=[{'name': 'Ort Rune'}])
        assert 'Setup socket: Ort Rune' in assess_roles(socketed, [profile], context)[0]['matched']
    if name == "Sigon's Visor" and slug == 'double-throw-barbarian-guide':
        assert any('15% Increased Attack Speed' in m for m in role['missing'])


@pytest.mark.parametrize(
    ('slug', 'character'), [('strafe-amazon', 'Amazon'), ('double-throw-barbarian-guide', 'Barbarian')]
)
def test_deaths_guard_upgrade_is_preparation_not_loss_of_cbf_utility(slug, character):
    profile = next((p for p in build()['profiles'] if p['id'] == f'{slug}-deaths-guard-upgrade'), None)
    assert profile is not None
    item = replace(facts('Sash', 'set', "Death's Guard"), stats={'153:0': {'status': 'decoded', 'value': 1}})
    context = {'player_class': character}
    normal = assess_roles(item, [profile], context)[0]
    assert normal['rule_trace']['truth'] == 'true'
    assert normal['dependencies'][0]['status'] == 'false'
    upgraded = replace(item, base_code=facts('Demonhide Sash').base_code, base_name='Demonhide Sash')
    assert assess_roles(upgraded, [profile], context)[0]['dependencies'][0]['status'] == 'true'
    assert assess_roles(replace(item, stats={}), [profile], context)[0]['status'] == 'failed'
