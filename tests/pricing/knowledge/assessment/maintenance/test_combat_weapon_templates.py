from dataclasses import replace

import pytest

from pricing.knowledge.assessment.maintenance.combat_weapon_templates import expand_combat_weapon
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('name', ['Death', 'Breath of the Dying', 'Doom'])
def test_zeal_modes_reject_wrong_class_and_do_not_leak_durability_to_other_words(name):
    row = {
        'id': 'reviewed',
        'item': name,
        'build': 'zeal-paladin',
        'variant': 'Guide mention',
        'source': {},
        'class': 'Paladin',
        'side': 'player',
        'slot': 'Weapon',
    }
    with pytest.raises(ValueError, match='attack mode'):
        expand_combat_weapon({**row, 'class': 'Barbarian'})
    profile = expand_combat_weapon(row)
    item = replace(
        facts('Berserker Axe', name=name),
        runeword=name,
        sockets=6 if name == 'Breath of the Dying' else 5,
        socket_contents='filled',
        ethereal=True,
        stats={'152:0': {'status': 'decoded', 'value': 1}},
    )
    result = assess_roles(item, [profile], {'player_class': 'Paladin'})[0]
    assert result['rule_trace']['truth'] == ('false' if name == 'Doom' else 'true')


def test_death_zeal_and_smite_keep_distinct_physical_stat_priorities():
    row = {'id': 'reviewed', 'item': 'Death', 'class': 'Paladin', 'side': 'player', 'slot': 'Weapon'}
    smite = expand_combat_weapon({**row, 'build': 'smite-paladin'})
    zeal = expand_combat_weapon({**row, 'build': 'zeal-paladin'})
    assert '136:0' in smite['important_stats']
    assert '136:0' in zeal['important_stats']
    for stat in ('17:0', '250:0', '119:0', '62:0'):
        assert stat not in smite['important_stats']
        assert stat in zeal['important_stats']
