from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def roles(name):
    selected = [p for p in build()['profiles'] if p.get('names') == [name] and p['id'].endswith('-qualified-equipment')]
    assert selected
    return selected


def test_marrowwalk_requires_available_bone_prison_not_life_tap_or_passive_skill():
    profile = roles('Marrowwalk')[0]
    item = replace(
        facts('Boneweave Boots', 'unique', 'Marrowwalk'),
        stats={
            '204:5665': {
                'status': 'decoded',
                'value': 1,
                'unit': 'charges_remaining',
                'charges': {'remaining': 1, 'maximum': 13},
            }
        },
    )
    context = {'player_class': 'Sorceress'}
    assert assess_roles(item, [profile], context)[0]['dependencies'][0]['status'] == 'true'
    for stats in (
        {},
        {'107:88': {'status': 'decoded', 'value': 33}},
        {'204:5260': item.stats['204:5665']},
        {'204:5665': {**item.stats['204:5665'], 'value': 0, 'charges': {'remaining': 0, 'maximum': 13}}},
    ):
        assert assess_roles(replace(item, stats=stats), [profile], context)[0]['dependencies'][0]['status'] != 'true'
    assert assess_roles(replace(item, ethereal=True), [profile], context)[0]['status'] == 'failed'


@pytest.mark.parametrize(
    ('name', 'base'), [("Immortal King's Forge", 'War Gauntlets'), ("Immortal King's Pillar", 'War Boots')]
)
def test_ik_three_piece_use_requires_two_distinct_compatible_companions(name, base):
    selected = roles(name)
    assert len(selected) == 2
    item = facts(base, 'set', name)
    other = "Immortal King's Pillar" if name.endswith('Forge') else "Immortal King's Forge"
    for profile in selected:
        context = {'player_class': 'Barbarian', 'player_items': [other, "Immortal King's Detail"]}
        assert assess_roles(item, [profile], context)[0]['dependencies'][0]['status'] == 'true'
        for companions in ([], [other, other], [name, other], ["Immortal King's Stone Crusher", other]):
            result = assess_roles(item, [profile], {**context, 'player_items': companions})[0]
            assert result['dependencies'][0]['status'] == 'false'
        assert assess_roles(item, [profile], {'player_class': 'Barbarian'})[0]['dependencies'][0]['status'] == 'unknown'


def test_berserk_rune_master_requires_five_verified_ist_children():
    profile = roles('Rune Master')[0]
    code = next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Ist Rune')
    children = [{'name': 'Ist Rune', 'base_code': code, 'unit_id': i + 1, 'position': i} for i in range(5)]
    item = replace(
        facts('Ettin Axe', 'unique', 'Rune Master'),
        sockets=5,
        socket_contents='filled',
        filled_sockets=5,
        empty_sockets=0,
        socket_items=children,
    )
    context = {'player_class': 'Barbarian'}
    assert assess_roles(item, [profile], context)[0]['dependencies'][0]['status'] == 'true'
    assert '17:0' not in profile['important_stats']
    for changes in (
        {'socket_items': children[:4]},
        {'socket_items': [children[0]] * 5},
        {'socket_contents': 'empty'},
        {'sockets': 4},
    ):
        assert assess_roles(replace(item, **changes), [profile], context)[0]['dependencies'][0]['status'] != 'true'
