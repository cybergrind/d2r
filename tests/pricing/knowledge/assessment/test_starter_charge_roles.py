import pytest

from inventory_tracking.items.metadata import decode_stats
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('build_name', 'skill', 'base', 'wearer'),
    [
        ('blizzard-sorceress', 91, 'Yew Wand', 'Sorceress'),
        ('fire-warlock-guide', 91, 'Wand', 'Warlock'),
        ('lightning-fury-amazon-guide', 91, 'Bone Wand', 'Amazon'),
        ('smite-paladin', 82, 'Wand', 'Paladin'),
        ('fire-warlock-guide', 54, 'Gothic Staff', 'Warlock'),
        ('lightning-fury-amazon-guide', 54, 'Long Staff', 'Amazon'),
    ],
)
def test_starter_charge_roles_use_the_right_spell_and_allow_recharging(build_name, skill, base, wearer):
    profile = next((p for p in build()['profiles'] if p['id'] == f'{build_name}-starter-charges-{skill}'), None)
    assert profile is not None
    for rarity in ('magic', 'rare'):
        for observed_skill, count, expected in ((skill, 1, 'true'), (skill, 0, 'false'), (48, 1, 'false')):
            decoded, _, _ = decode_stats([{'id': 204, 'layer': observed_skill * 64 + 1, 'raw': (60 << 8) | count}])
            item = normalize(
                {
                    'item': facts(base, rarity).to_dict(),
                    'decoded_stats': decoded,
                    'source': {'stat_capture_complete': True},
                }
            )
            role = assess_roles(item, [profile], {'player_class': wearer, 'mercenary_items': []})[0]
            assert role['dependencies'][0]['status'] == expected
            assert role['status'] == ('partial' if observed_skill == skill else 'failed')
    if build_name == 'fire-warlock-guide' and skill == 91:
        assert profile['slot'] == 'Other'  # Inventory utility, not the Teleport weapon-swap slot.
