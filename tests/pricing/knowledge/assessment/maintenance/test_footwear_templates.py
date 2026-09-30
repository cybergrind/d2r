from dataclasses import replace

import pytest

from pricing.knowledge.assessment.maintenance.profile_templates import expand_profile
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'quality', 'keys'),
    [
        ("Aldur's Advance", 'Battle Boots', 'set', {'96:0', '7:0', '39:0'}),
        ('Waterwalk', 'Sharkskin Boots', 'unique', {'96:0', '7:0', '2:0', '40:0'}),
        ('Sandstorm Trek', 'Scarabshell Boots', 'unique', {'96:0', '99:0', '0:0', '3:0', '45:0'}),
    ],
)
def test_footwear_native_utility_preserves_durability_and_individual_set_scope(name, base, quality, keys):
    role = expand_profile(
        {
            'id': 'example',
            'template': 'player_footwear',
            'item': name,
            'class': 'Sorceress',
            'side': 'player',
            'build': 'example',
            'variant': 'Main alternatives',
            'slot': 'Boots',
            'source': {},
        }
    )
    item = facts(base, quality, name)

    def truth(candidate):
        rows = assess_roles(candidate, [role], {'player_class': 'Sorceress'})
        return rows[0]['rule_trace']['truth'] if rows else 'false'

    assert truth(item) == 'true'
    assert set(role['important_stats']) == keys
    assert truth(replace(item, ethereal=True)) != 'true'
    if name == 'Sandstorm Trek':
        repaired = replace(item, ethereal=True, stats={'252:0': {'status': 'decoded', 'value': 20, 'raw': 5}})
        assert truth(repaired) == 'true'
    for changes in ({'sockets': 1}, {'identified': False}, {'rarity': 'rare'}, {'name': 'Other'}):
        assert truth(replace(item, **changes)) == 'false'
