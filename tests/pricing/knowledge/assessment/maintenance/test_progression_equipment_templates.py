from dataclasses import replace

import pytest

from pricing.knowledge.assessment.maintenance.profile_templates import expand_profile
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'slot', 'sockets', 'invalid_base'),
    [
        ('Lore', 'Cap', 'Helmets', 2, 'Quilted Armor'),
        ('Stealth', 'Quilted Armor', 'Body Armor', 2, 'Cap'),
        ("Ancients' Pledge", 'Large Shield', 'Off-Hand', 3, 'Buckler'),
        ('Ground', 'Crown', 'Helmets', 3, 'Cap'),
    ],
)
def test_progression_recipe_requires_legal_completed_durable_equipment(name, base, slot, sockets, invalid_base):
    role = expand_profile(
        {
            'id': 'example',
            'template': 'player_progression_equipment',
            'item': name,
            'class': 'Sorceress',
            'build': 'example',
            'variant': 'Main alternatives',
            'side': 'player',
            'slot': slot,
            'source': {},
        }
    )
    item = replace(facts(base, name=name), runeword=name, sockets=sockets, socket_contents='filled')

    def truth(candidate):
        rows = assess_roles(candidate, [role], {'player_class': 'Sorceress'})
        return rows[0]['rule_trace']['truth'] if rows else 'false'

    assert truth(item) == 'true'
    for changes in (
        {'sockets': sockets - 1},
        {'socket_contents': 'empty'},
        {'ethereal': True},
        {'rarity': 'magic'},
        {'base_code': facts(invalid_base).base_code},
    ):
        assert truth(replace(item, **changes)) == 'false'
    assert truth(replace(item, sockets=None)) != 'true'
    assert truth(replace(item, runeword=None)) != 'true'


def test_lore_accepts_druid_pelts_only_for_druid_wearers():
    row = {
        'id': 'example',
        'template': 'player_progression_equipment',
        'item': 'Lore',
        'class': 'Druid',
        'build': 'fissure-druid',
        'variant': 'Main alternatives',
        'side': 'player',
        'slot': 'Helmets',
        'source': {},
    }
    item = replace(facts('Wolf Head', name='Lore'), runeword='Lore', sockets=2, socket_contents='filled')
    for class_name, expected in [('Druid', 'true'), ('Sorceress', 'false')]:
        role = expand_profile({**row, 'class': class_name})
        result = assess_roles(item, [role], {'player_class': class_name})
        assert (result[0]['rule_trace']['truth'] if result else 'false') == expected
