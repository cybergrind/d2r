import pytest

from inventory_tracking.items.metadata import decode_stats
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('fissure-druid', 'starter', 91, 'Druid', 'Other'),
    ('fissure-druid', 'ubers', 91, 'Druid', 'Weapon-Swap'),
    ('lightning-sorceress', 'starter', 91, 'Sorceress', 'Weapon-Swap'),
    ('lightning-sorceress', 'ubers', 91, 'Sorceress', 'Weapon-Swap'),
    ('lightning-strike-amazon', 'starter', 91, 'Amazon', 'Weapon-Swap'),
    ('lightning-strike-amazon', 'ubers', 91, 'Amazon', 'Weapon-Swap'),
    ('dragon-talon-assassin', 'budget', 82, 'Assassin', 'Weapon-Swap'),
    ('dream-paladin', 'ubers', 82, 'Paladin', 'Weapon-Swap'),
]


def profile_for(build_name, variant, skill):
    profile = next((p for p in build()['profiles'] if p['id'] == f'{build_name}-{variant}-charges-{skill}'), None)
    assert profile is not None
    return profile


def wand(skill, count, rarity='magic'):
    decoded, _, _ = decode_stats([{'id': 204, 'layer': skill * 64 + 1, 'raw': (60 << 8) | count}])
    return normalize(
        {
            'item': facts('Bone Wand', rarity).to_dict(),
            'decoded_stats': decoded,
            'source': {'stat_capture_complete': True},
        }
    )


@pytest.mark.parametrize(('build_name', 'variant', 'skill', 'wearer', 'slot'), CASES)
def test_curse_wands_preserve_setup_and_distinguish_recharge_from_wrong_skill(build_name, variant, skill, wearer, slot):
    profile = profile_for(build_name, variant, skill)
    assert profile['slot'] == slot
    assert profile['variant'].lower() == variant
    context = {'player_class': wearer, 'player_items': [], 'mercenary_items': ['Infinity']}
    for rarity in ('magic', 'rare'):
        for observed, count, expected in ((skill, 1, 'true'), (skill, 0, 'false'), (54, 1, 'false')):
            result = assess_roles(wand(observed, count, rarity), [profile], context)[0]
            assert result['dependencies'][0]['status'] == expected
            assert result['status'] == ('partial' if observed == skill else 'failed')


def test_dream_life_tap_is_conditional_on_other_sources_and_unknown_loadout():
    profile = profile_for('dream-paladin', 'ubers', 82)
    for equipment, expected in (
        ([], 'true'),
        (['Last Wish'], 'false'),
        (["Dracul's Grasp"], 'false'),
        (None, 'unknown'),
    ):
        context = {'player_class': 'Paladin'}
        if equipment is not None:
            context['player_items'] = equipment
        result = assess_roles(wand(82, 1), [profile], context)[0]
        assert result['dependencies'][1]['status'] == expected


def test_lightning_ubers_preserves_infinity_dependency_and_mephisto_exception():
    profile = profile_for('lightning-sorceress', 'ubers', 91)
    for mercenary, expected in ((['Infinity'], 'true'), (['Plague'], 'false')):
        result = assess_roles(wand(91, 1), [profile], {'player_class': 'Sorceress', 'mercenary_items': mercenary})[0]
        assert result['dependencies'][1]['status'] == expected
    assert any('Mephisto' in condition for condition in profile['conditions'])
