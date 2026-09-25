from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('suffix', 'name', 'base', 'sockets', 'companion'),
    [
        ('standard-fortitude', 'Fortitude', 'Sacred Armor', 4, 'Infinity'),
        ('magic-find-fortitude', 'Fortitude', 'Sacred Armor', 4, 'Infinity'),
        ('ubers-chains-of-honor', 'Chains of Honor', 'Archon Plate', 4, 'Flickering Flame'),
        ('ubers-flickering-flame', 'Flickering Flame', 'Bone Visage', 3, 'Chains of Honor'),
    ],
)
def test_endgame_merc_roles_require_recipe_and_preserve_companion_dependencies(suffix, name, base, sockets, companion):
    rule = next((r for r in build()['profiles'] if r['id'] == f'fissure-merc-{suffix}'), None)
    assert rule is not None
    item = replace(facts(base, name=name), runeword=name, sockets=sockets, socket_contents='filled')
    context = {
        'player_class': 'Druid',
        'mercenary_type': 'Act 2 Might',
        'mercenary_items': ['Infinity', 'Chains of Honor', 'Flickering Flame'],
    }
    result = assess_roles(item, [rule], context)[0]
    assert result['rule_trace']['truth'] == 'true'
    assert all(d['status'] == 'true' for d in result['dependencies'])
    assert any(companion in d['label'] for d in result['dependencies'])
    assert result['status'] == 'partial'  # Wearer requirements and full loadout still need review.
    assert assess_roles(replace(item, ethereal=True), [rule], context)[0]['preferences'][0]['status'] == 'true'
    absent = assess_roles(item, [rule], {'player_class': 'Druid'})[0]
    assert all(d['status'] == 'unknown' for d in absent['dependencies'])
    wrong = assess_roles(item, [rule], {**context, 'mercenary_items': []})[0]
    assert any(d['status'] == 'false' for d in wrong['dependencies'])
    for changed in (replace(item, socket_contents='empty'), replace(item, sockets=2), replace(item, runeword='Spirit')):
        assert assess_roles(changed, [rule], context)[0]['status'] == 'failed'
    assert assess_roles(item, [rule], {**context, 'player_class': 'Sorceress'})[0]['status'] == 'failed'


def test_standard_merc_aura_conflict_is_preserved_and_not_carried_to_ubers():
    profiles = build()['profiles']
    for suffix, name, base, sockets, accepted in (
        ('standard-fortitude', 'Fortitude', 'Sacred Armor', 4, 'true'),
        ('ubers-flickering-flame', 'Flickering Flame', 'Bone Visage', 3, 'false'),
    ):
        rule = next((r for r in profiles if r['id'] == f'fissure-merc-{suffix}'), None)
        assert rule is not None
        item = replace(facts(base, name=name), runeword=name, sockets=sockets, socket_contents='filled')
        role = assess_roles(item, [rule], {'player_class': 'Druid', 'mercenary_type': 'Act 2 Holy Freeze'})[0]
        assert role['dependencies'][0]['status'] == accepted


def test_merc_equipment_roles_do_not_accept_weapon_fortitude_or_class_helms():
    profiles = build()['profiles']
    for suffix, name, base, sockets in (
        ('standard-fortitude', 'Fortitude', 'Phase Blade', 4),
        ('ubers-flickering-flame', 'Flickering Flame', 'Antlers', 3),
    ):
        rule = next(r for r in profiles if r['id'] == f'fissure-merc-{suffix}')
        item = replace(facts(base, name=name), runeword=name, sockets=sockets, socket_contents='filled')
        assert not assess_roles(item, [rule], {'player_class': 'Druid'})
