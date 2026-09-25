import pytest

from inventory_tracking.items.metadata import decode_stats
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('abyss-warlock-build-guide', 'Starter', 'Warlock', 'Weapon-Swap'),
    ('dragon-talon-assassin', 'Budget', 'Assassin', 'Other'),
    ('echoing-strike-warlock-guide', 'Starter', 'Warlock', 'Weapon-Swap'),
    ('fire-blast-assassin', 'Starter', 'Assassin', 'Weapon-Swap'),
    ('fissure-druid', 'Starter', 'Druid', 'Weapon-Swap'),
    ('fist-of-the-heavens-paladin', 'FoH Starter', 'Paladin', 'Weapon-Swap'),
    ('fist-of-the-heavens-paladin', 'Holy Bolt Starter', 'Paladin', 'Weapon-Swap'),
    ('lightning-sentry-assassin', 'Starter', 'Assassin', 'Weapon-Swap'),
    ('lightning-strike-amazon', 'Starter', 'Amazon', 'Weapon-Swap'),
    ('mirrored-blades-warlock-guide', 'Starter', 'Warlock', 'Weapon-Swap'),
    ('poison-nova-necromancer', 'Starter', 'Necromancer', 'Weapon-Swap'),
    ('summoner-necromancer-guide', 'Starter', 'Necromancer', 'Weapon-Swap'),
    ('smite-paladin', 'Standard', 'Paladin', 'Other'),
]


def profile_for(build_name, variant):
    identifier = f'{build_name}-{variant.lower().replace(" ", "-")}-travel-staff'
    profile = next((p for p in build()['profiles'] if p['id'] == identifier), None)
    assert profile is not None
    return profile


def charged_item(skill=54, remaining=1, base='Long Staff', rarity='magic'):
    decoded, _, _ = decode_stats([{'id': 204, 'layer': skill * 64 + 1, 'raw': (33 << 8) | remaining}])
    return normalize(
        {
            'item': facts(base, rarity).to_dict(),
            'decoded_stats': decoded,
            'source': {'stat_capture_complete': True},
        }
    )


@pytest.mark.parametrize(('build_name', 'variant', 'wearer', 'slot'), CASES)
def test_travel_staff_roles_preserve_variants_and_require_teleport(build_name, variant, wearer, slot):
    profile = profile_for(build_name, variant)
    assert profile['variant'] == variant
    assert profile['slot'] == slot
    context = {'player_class': wearer, 'player_items': []}
    for rarity in ('magic', 'rare'):
        for skill, remaining, charge_status in ((54, 1, 'true'), (54, 0, 'false'), (91, 1, 'false')):
            result = assess_roles(charged_item(skill, remaining, rarity=rarity), [profile], context)[0]
            assert result['status'] == ('partial' if skill == 54 else 'failed')
            assert result['dependencies'][0]['status'] == charge_status
    assert not assess_roles(charged_item(base='Amulet'), [profile], context)
    wrong_wearer = 'Barbarian'  # None of these sources is a Barbarian setup.
    assert assess_roles(charged_item(), [profile], {'player_class': wrong_wearer})[0]['status'] == 'failed'


def test_smite_staff_remains_an_alternative_to_enigma():
    profile = profile_for('smite-paladin', 'Standard')
    for equipment, expected in (([], 'true'), (['Enigma'], 'false'), (None, 'unknown')):
        context = {'player_class': 'Paladin'}
        if equipment is not None:
            context['player_items'] = equipment
        result = assess_roles(charged_item(), [profile], context)[0]
        assert result['dependencies'][1]['status'] == expected
