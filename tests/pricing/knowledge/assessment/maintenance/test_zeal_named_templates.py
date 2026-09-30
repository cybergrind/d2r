from dataclasses import replace

import pytest

from pricing.knowledge.assessment.maintenance.zeal_named_templates import MEMBERS, expand_zeal_named
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base'),
    [
        ('Rune Master', 'Hand Axe'),
        ('Herald of Zakarum', 'Buckler'),
        ('Stormshield', 'Buckler'),
        ("Skullder's Ire", 'Quilted Armor'),
        ("Tal Rasha's Horadric Crest", 'Mask'),
    ],
)
def test_inconsistent_named_base_facts_cannot_qualify_for_named_use(name, base):
    profile = expand_zeal_named(
        {
            'id': 'reviewed',
            'item': name,
            'class': 'Paladin',
            'build': 'zeal-paladin',
            'variant': 'Guide mention',
            'side': 'player',
            'slot': MEMBERS[name]['slot'],
            'source': {},
        }
    )
    item = replace(
        facts(base, MEMBERS[name].get('quality', 'unique'), name),
        sockets=5 if name == 'Rune Master' else 0,
        ethereal=name == 'Rune Master',
    )
    results = assess_roles(item, [profile], {'player_class': 'Paladin'})
    assert all(result['rule_trace']['truth'] == 'false' for result in results)
