from dataclasses import replace

import pytest

from pricing.knowledge.assessment.maintenance.profile_templates import expand_profile
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'quality', 'keys'),
    [
        ('Rockfleece', 'Field Plate', 'unique', {'36:0', '34:0', '0:0'}),
        ('Lionheart', 'Mage Plate', 'normal', {'17:0', '18:0', '7:0', '0:0', '2:0', '39:0', '41:0', '43:0', '45:0'}),
        ('Temper', 'Crown', 'normal', {'39:0', '142:0', '76:0', '99:0'}),
        ('Cure', 'Crown', 'normal', {'151:109', '45:0', '110:0', '76:0', '99:0'}),
    ],
)
def test_merc_survival_template_qualifies_identity_not_perfect_rolls(name, base, quality, keys):
    role = expand_profile(
        {
            'id': 'example',
            'template': 'merc_survival',
            'item': name,
            'class': 'Druid',
            'side': 'merc',
            'build': 'fissure-druid',
            'variant': 'Early alternatives',
            'slot': 'Helmet' if base == 'Crown' else 'Body Armor',
            'source': {'review': 'Native mechanics and guide survival alternatives'},
        }
    )
    item = facts(base, quality, name)
    if quality == 'normal':
        item = replace(item, runeword=name, sockets=3, socket_contents='filled')

    def truth(candidate, context=None):
        rows = assess_roles(candidate, [role], context or {'player_class': 'Druid'})
        return rows[0]['rule_trace']['truth'] if rows else 'false'

    assert set(role['important_stats']) == keys
    assert '3:0' not in keys  # mercenary vitality is not the same as flat life
    for ethereal in (True, False, None):
        assert truth(replace(item, ethereal=ethereal)) == 'true'
    for changes in ({'identified': False}, {'rarity': 'magic'}, {'item_type': 'weap'}, {'name': 'Other'}):
        assert truth(replace(item, **changes)) == 'false'
    assert truth(item, {'player_class': 'Sorceress'}) == 'false'
    if quality == 'normal':
        for changes in ({'runeword': None}, {'sockets': 2}, {'socket_contents': 'empty'}):
            assert truth(replace(item, **changes)) != 'true'
    if name == 'Cure':
        assert any('Prayer' in c for c in role['conditions'])


@pytest.mark.parametrize(
    ('name', 'base', 'slot'),
    [
        ('Cure', 'Cap', 'Helmet'),
        ('Temper', 'Cap', 'Helmet'),
        ('Lionheart', 'Quilted Armor', 'Body Armor'),
    ],
)
def test_claimed_runeword_cannot_override_the_native_socket_capacity(name, base, slot):
    role = expand_profile(
        {
            'id': 'test',
            'template': 'merc_survival',
            'item': name,
            'class': 'Druid',
            'build': 'test',
            'variant': 'early',
            'side': 'merc',
            'slot': slot,
            'source': {},
        }
    )
    item = replace(facts(base, name=name), runeword=name, sockets=3, socket_contents='filled')
    result = assess_roles(item, [role], {'player_class': 'Druid'})
    assert result[0]['rule_trace']['truth'] == 'false'
