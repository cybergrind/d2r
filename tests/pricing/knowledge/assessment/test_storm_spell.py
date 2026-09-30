from dataclasses import replace

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def role(name):
    found = [p for p in build()['profiles'] if p.get('names') == [name] and p['id'].endswith('-qualified-equipment')]
    assert len(found) == 1
    return found[0]


def test_stormlash_kick_role_requires_shael_and_does_not_promote_weapon_ed():
    p = role('Stormlash')
    code = next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Shael Rune')
    item = replace(
        facts('Scourge', 'unique', 'Stormlash'),
        sockets=1,
        socket_contents='filled',
        filled_sockets=1,
        empty_sockets=0,
        socket_items=[{'name': 'Shael Rune', 'base_code': code, 'unit_id': 1, 'position': 0}],
    )
    context = {'player_class': 'Assassin'}
    assert assess_roles(item, [p], context)[0]['dependencies'][0]['status'] == 'true'
    assert {'93:0', '136:0', '198:2698'} <= set(p['important_stats'])
    assert not {'17:0', '18:0'} & set(p['important_stats'])
    for patch in ({'socket_items': []}, {'socket_contents': 'empty'}, {'sockets': 0}):
        assert assess_roles(replace(item, **patch), [p], context)[0]['dependencies'][0]['status'] != 'true'
    assert assess_roles(replace(item, ethereal=True), [p], context)[0]['status'] == 'failed'


def test_spellsteel_utility_needs_usable_teleport_or_decrepify_not_an_unrelated_charge():
    p = role('Spellsteel')
    context = {'player_class': 'Amazon'}
    item = facts('Bearded Axe', 'unique', 'Spellsteel')
    for key in ('204:3457', '204:5571'):
        stat = {
            'status': 'decoded',
            'value': 1,
            'unit': 'charges_remaining',
            'charges': {'remaining': 1, 'maximum': 20},
        }
        charged = replace(item, ethereal=True, stats={key: stat})
        assert assess_roles(charged, [p], context)[0]['dependencies'][0]['status'] == 'true'
        for invalid in (
            {},
            {'204:6474': stat},
            {key: {**stat, 'value': 0, 'charges': {'remaining': 0, 'maximum': 20}}},
        ):
            assert assess_roles(replace(charged, stats=invalid), [p], context)[0]['dependencies'][0]['status'] != 'true'
    assert '17:0' not in p['important_stats']
