from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_naj_swap_roles_cover_documented_builds_and_preserve_fal_variant():
    profiles = [p for p in build()['profiles'] if p['role'] == 'Teleport-charge weapon swap']
    assert len(profiles) == 14
    assert len({p['build'] for p in profiles}) == 13
    assert all(p['side'] == 'player' and p['slot'] == 'Weapon-Swap' for p in profiles)
    item = facts('Elder Staff', 'set', "Naj's Puzzler")
    results = assess_roles(item, profiles, {'player_class': 'Necromancer', 'player_items': []})
    assert sum(r['status'] == 'partial' for r in results) == 3
    assert all(
        r['status'] == 'failed'
        for r in results
        if r['build'] not in ('poison-nova-necromancer', 'summoner-necromancer-guide')
    )
    fal = next(p for p in profiles if p['id'] == 'poison-naj-fal-swap')
    assert fal['required_rune'] == 'Fal Rune'
    assert fal['source']['locator'] == '/poison-nova-necromancer/variants/4/player/Weapon-Swap/0'
    assert all(any('Teleport charge' in d['label'] for d in p['depends_on']) for p in profiles)
    assert not assess_roles(facts('Elder Staff', 'magic'), profiles)


def test_naj_equipment_checks_use_known_context_without_guessing_socketed_requirements():
    from dataclasses import replace

    profile = next(p for p in build()['profiles'] if p['id'] == 'poison-nova-necromancer-naj-teleport-swap')
    item = facts('Elder Staff', 'set', "Naj's Puzzler")
    context = {'player_class': 'Necromancer', 'player_level': 77, 'player_strength': 44, 'player_dexterity': 37}
    result = assess_roles(item, [profile], context)[0]
    assert result['equipment']['status'] == 'unmet'
    assert 'Player level 77; requires 78.' in result['missing']
    ready = assess_roles(item, [profile], {**context, 'player_level': 78})[0]
    assert ready['equipment']['status'] == 'met'
    assert ready['status'] == 'partial'  # Charge availability is still unverified.
    socketed = replace(item, sockets=1, socket_contents='filled')
    result = assess_roles(socketed, [profile], context)[0]
    assert result['equipment']['status'] == 'unknown'
    assert not result['equipment']['shortfalls']


def test_role_equipment_policy_rejects_malformed_requirements():
    from copy import deepcopy

    import pytest

    from pricing.knowledge.assessment.profiles import validate_profiles

    original = next(p for p in build()['profiles'] if p['id'] == 'poison-nova-necromancer-naj-teleport-swap')
    for value in (True, -1, '78', None):
        profile = deepcopy(original)
        profile['equipment']['requirements']['level'] = value
        with pytest.raises(ValueError, match='equipment requirements'):
            validate_profiles([profile])


def test_teleport_availability_uses_captured_charges_and_retains_price_gap():
    from inventory_tracking.items.metadata import decode_stats
    from pricing.knowledge.assessment.adapters.capture import normalize

    profile = next(p for p in build()['profiles'] if p['id'] == 'poison-nova-necromancer-naj-teleport-swap')
    for remaining, expected in ((0, 'false'), (1, 'true'), (69, 'true')):
        decoded, _, _ = decode_stats([{'id': 204, 'layer': 54 * 64 + 11, 'raw': (69 << 8) | remaining}])
        item = normalize(
            {
                'item': facts('Elder Staff', 'set', "Naj's Puzzler").to_dict(),
                'decoded_stats': decoded,
                'source': {'stat_capture_complete': True},
            }
        )
        role = assess_roles(item, [profile], {'player_class': 'Necromancer'})[0]
        charge = next(d for d in role['dependencies'] if 'Teleport charge' in d['label'])
        assert charge['status'] == expected
        assert item.stats['204:3467']['charges']['maximum'] == 69
        assert 'No verified market mapping for native stat 204:3467.' in item.projection_gaps


def test_magic_rare_teleport_alternatives_require_the_actual_charged_skill():
    from inventory_tracking.items.metadata import decode_stats
    from pricing.knowledge.assessment.adapters.capture import normalize

    profiles = [p for p in build()['profiles'] if p['role'] == 'Affixed Teleport-charge alternative']
    assert len(profiles) == 4
    for base in ('Long Staff', 'Amulet'):
        for rarity in ('magic', 'rare'):
            for skill, remaining, wanted in ((54, 0, 'partial'), (54, 1, 'partial'), (48, 1, 'failed')):
                decoded, _, _ = decode_stats([{'id': 204, 'layer': skill * 64 + 1, 'raw': (20 << 8) | remaining}])
                item = normalize(
                    {
                        'item': facts(base, rarity).to_dict(),
                        'decoded_stats': decoded,
                        'source': {'stat_capture_complete': True},
                    }
                )
                roles = assess_roles(item, profiles, {'player_class': 'Necromancer', 'player_items': []})
                role = next(r for r in roles if r['build'] == 'poison-nova-necromancer')
                assert role['status'] == wanted
