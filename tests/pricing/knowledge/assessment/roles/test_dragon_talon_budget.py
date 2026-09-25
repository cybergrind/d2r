from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def profile(suffix):
    result = next((p for p in build()['profiles'] if p['id'] == f'dragon-talon-budget-{suffix}'), None)
    assert result is not None
    return result


def test_goblin_toe_needs_elite_upgrade_without_losing_existing_crushing_blow_utility():
    rule = profile('goblin-toe')
    item = replace(
        facts('Light Plated Boots', 'unique', 'Goblin Toe'), stats={'136:0': {'status': 'decoded', 'value': 25}}
    )
    context = {'player_class': 'Assassin'}
    role = assess_roles(item, [rule], context)[0]
    assert role['rule_trace']['truth'] == 'true'
    assert role['dependencies'][0]['status'] == 'false'
    upgraded = replace(item, base_name='Mirrored Boots', base_code=facts('Mirrored Boots').base_code)
    assert assess_roles(upgraded, [rule], context)[0]['dependencies'][0]['status'] == 'true'
    assert assess_roles(replace(item, ethereal=True), [rule], context)[0]['status'] == 'failed'
    assert assess_roles(item, [rule], {'player_class': 'Sorceress'})[0]['status'] == 'failed'


@pytest.mark.parametrize(
    ('suffix', 'name', 'base'),
    [
        ('hexfire-merc', 'Hexfire', 'Shamshir'),
        ('ormus-merc', "Ormus' Robes", 'Dusk Shroud'),
        ('lidless-merc', 'Lidless Wall', 'Grim Shield'),
    ],
)
def test_fire_iron_wolf_candidates_require_matching_socket_payload_and_context(suffix, name, base):
    rule = profile(suffix)
    item = facts(base, 'unique', name)
    role = assess_roles(item, [rule])[0]
    assert role['status'] == 'partial'
    assert any('Mercenary type' in m for m in role['missing'])
    fire = {f'{key}:0': {'status': 'decoded', 'value': 3} for key in (329, 333)}
    socketed = replace(
        item,
        sockets=1,
        socket_contents='filled',
        socket_items=[{'name': 'Rainbow Facet', 'item_type': 'jewl', 'stats_complete': True, 'stats': fire}],
    )
    context = {'mercenary_type': 'Act 3 Fire'}
    role = assess_roles(socketed, [rule], context)[0]
    assert all(d['status'] == 'true' for d in role['dependencies'])
    assert any('will not survive' in m for m in role['missing'])
    wrong_element = replace(
        socketed,
        socket_items=[
            {
                'name': 'Rainbow Facet',
                'item_type': 'jewl',
                'stats_complete': True,
                'stats': {'330:0': {'status': 'decoded', 'value': 5}},
            }
        ],
    )
    assert any(d['status'] != 'true' for d in assess_roles(wrong_element, [rule], context)[0]['dependencies'])
    totals_only = replace(socketed, socket_items=[], stats=fire)
    assert any(d['status'] != 'true' for d in assess_roles(totals_only, [rule], context)[0]['dependencies'])
    if suffix == 'lidless-merc':
        assert any('Spirit Monarch' in m for m in role['missing'])
