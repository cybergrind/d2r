from dataclasses import replace

import pytest

from pricing.knowledge.assessment.maintenance.profile_templates import expand_profile
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_build_specific_amazon_skill_review_cannot_be_assigned_to_another_class():
    with pytest.raises(ValueError, match='wrong player class'):
        expand_profile(
            {
                'id': 'bad',
                'template': 'named_player_utility',
                'item': "Thundergod's Vigor",
                'class': 'Sorceress',
                'build': 'lightning-fury-amazon-guide',
                'variant': 'Main alternatives',
                'side': 'player',
                'slot': 'Belts',
                'source': {},
            }
        )


@pytest.mark.parametrize(
    ('name', 'base', 'slot'),
    [
        ("Bul-Kathos' Wedding Band", 'Ring', 'Rings'),
        ("Skullder's Ire", 'Russet Armor', 'Body Armor'),
        ('Wizardspike', 'Bone Knife', 'Weapon-Swap'),
    ],
)
def test_named_utility_requires_native_identity_and_valid_durability(name, base, slot):
    role = expand_profile(
        {
            'id': 'example',
            'template': 'named_player_utility',
            'item': name,
            'class': 'Sorceress',
            'build': 'blizzard-sorceress',
            'variant': 'Main alternatives',
            'side': 'player',
            'slot': slot,
            'source': {},
        }
    )
    item = facts(base, 'unique', name)

    def truth(candidate):
        rows = assess_roles(candidate, [role], {'player_class': 'Sorceress'})
        return rows[0]['rule_trace']['truth'] if rows else 'false'

    assert truth(item) == 'true'
    assert truth(replace(item, rarity='rare')) == 'false'
    assert truth(replace(item, base_code=facts('Hand Axe').base_code)) == 'false'
    assert truth(replace(item, identified=False)) == 'false'
    assert truth(replace(item, ethereal=True)) != 'true'
    if name == "Skullder's Ire":
        assert truth(replace(item, ethereal=True, stats={'252:0': {'status': 'decoded', 'value': 5}})) == 'true'
        assert truth(replace(item, base_code=facts('Balrog Skin').base_code)) == 'true'
    if name == "Bul-Kathos' Wedding Band":
        assert '60:0' not in role['important_stats']  # Spell damage does not leech.
        assert truth(replace(item, sockets=1)) == 'false'
    if name == 'Wizardspike':
        assert '105:0' in role['important_stats']
        assert '93:0' not in role['important_stats']  # Casting utility is not attack speed.
