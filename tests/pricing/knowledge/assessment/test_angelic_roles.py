from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


BUILDS = [
    ('double-throw-barbarian-guide', 'Barbarian', 2),
    ('strafe-amazon', 'Amazon', 2),
    ('echoing-strike-warlock-guide', 'Warlock', 1),
    ('dragon-talon-assassin', 'Assassin', 1),
    ('berserk-barbarian', 'Barbarian', 1),
]


@pytest.mark.parametrize(('build_id', 'character', 'rings'), BUILDS)
@pytest.mark.parametrize(('name', 'base'), [('Angelic Halo', 'Ring'), ('Angelic Wings', 'Amulet')])
def test_angelic_attack_rating_pair_requires_player_companions(build_id, character, rings, name, base):
    suffix = 'ring' if base == 'Ring' else 'amulet'
    profile = next((p for p in build()['profiles'] if p['id'] == f'{build_id}-angelic-{suffix}'), None)
    assert profile is not None
    item = facts(base, 'set', name)
    items = ['Angelic Wings'] + ['Angelic Halo'] * rings
    context = {'player_class': character, 'player_items': items}
    role = assess_roles(item, [profile], context)[0]
    assert all(d['status'] == 'true' for d in role['dependencies'])
    assert role['status'] == 'partial'  # Remaining gear and equip requirements are not established.
    assert not role['important_rolls']  # Do not invent equipped set bonus stats on a hover.
    other = 'Angelic Wings' if base == 'Ring' else 'Angelic Halo'
    absent = {**context, 'player_items': [v for v in items if v != other], 'mercenary_items': items}
    assert any(d['status'] == 'false' for d in assess_roles(item, [profile], absent)[0]['dependencies'])
    unknown = assess_roles(item, [profile], {'player_class': character})[0]
    assert all(d['status'] == 'unknown' for d in unknown['dependencies'])
    if rings == 2:
        single = assess_roles(item, [profile], {**context, 'player_items': ['Angelic Wings', 'Angelic Halo']})[0]
        assert any(d['status'] == 'false' for d in single['dependencies'])
    assert assess_roles(item, [profile], {**context, 'player_class': 'Sorceress'})[0]['status'] == 'failed'
    assert not assess_roles(replace(item, rarity='unique'), [profile], context)
    assert not assess_roles(replace(item, name='Other set item'), [profile], context)
