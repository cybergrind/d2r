from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def infinity(base):
    return replace(
        facts(base, name='Infinity'),
        runeword='Infinity',
        sockets=4,
        socket_contents='filled',
        stats={
            '151:123': {'status': 'decoded', 'value': 12},
            '334:0': {'status': 'decoded', 'value': 55},
            '17:0': {'status': 'decoded', 'value': 300},
        },
    )


def test_infinity_roles_separate_wearer_pierce_from_mercenary_weapon_damage():
    profiles = build()['profiles']
    roles = {r['id']: r for r in assess_roles(infinity('Scythe'), profiles)}
    player = roles['nova-standard-infinity-player']
    merc = roles['nova-hybrid-infinity-merc']
    assert player['side'] == 'player'
    assert merc['side'] == 'merc'
    assert [r['value'] for r in player['important_rolls']] == [55]
    assert [r['value'] for r in merc['important_rolls']] == [300]
    assert player['status'] == 'partial'  # Whole loadout/requirements remain unverified.
    assert merc['status'] == 'partial'
    assert 'lightning-strike-infinity-player' not in roles


def test_amazon_spear_role_is_independent_of_nova_role_and_requires_real_aura():
    profiles = build()['profiles']
    item = infinity('Matriarchal Spear')
    roles = {r['id']: r for r in assess_roles(item, profiles)}
    assert 'lightning-strike-infinity-player' in roles
    assert 'nova-standard-infinity-player' not in roles
    changed = replace(item, stats={'151:123': {'status': 'decoded', 'value': 0}})
    role = next(r for r in assess_roles(changed, profiles) if r['id'] == 'lightning-strike-infinity-player')
    assert role['status'] == 'failed'
