from dataclasses import replace

import pytest

from pricing.knowledge.assessment.comparables import reject_reasons
from pricing.knowledge.assessment.handlers import HANDLERS
from tests.pricing.knowledge.assessment.test_socket_survival_comparisons import socketed_item


@pytest.mark.parametrize(
    ('name', 'stat', 'bonus'),
    [
        ('Shael Rune', 93, 20),
        ('Ber Rune', 136, 20),
        ('Um Rune', 135, 25),
        ('Ist Rune', 80, 30),
    ],
)
def test_weapon_runes_compare_destination_effect_and_total_modifiers(name, stat, bonus):
    for quality, handler in [('normal', 'base'), ('magic', 'affixed'), ('rare', 'affixed')]:
        item = socketed_item('Legend Spike', quality, None, [name], {stat: bonus, 17: 0, 18: 0})
        contract, gaps = HANDLERS[handler].contract(item, 'weapon')
        assert contract is not None, gaps
        prop = item.stats[f'{stat}:0']['market_property']
        assert contract.properties[prop] == bonus
        row = {
            **contract.to_dict(),
            'properties': {**contract.properties, '934': name},
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': 'one',
            'ask_ist': 1,
        }
        assert not reject_reasons(contract.to_dict(), row)
        assert reject_reasons(contract.to_dict(), {**row, 'properties': {**row['properties'], prop: bonus + 1}})
        assert reject_reasons(contract.to_dict(), {**row, 'properties': {**row['properties'], '934': 'Jewel'}})


def test_mixed_named_weapon_fillers_preserve_empty_slots_and_innate_rolls():
    bonuses = {93: 20, 136: 20, 135: 25, 80: 30}
    fillers = ['Shael Rune', 'Ber Rune', 'Um Rune', 'Ist Rune']
    item = socketed_item('Ettin Axe', 'unique', 'Rune Master', fillers, bonuses)
    item = replace(item, sockets=5, filled_sockets=4, empty_sockets=1)
    contract, gaps = HANDLERS['named'].contract(item, 'weapon')
    assert contract is not None, gaps
    assert contract.sockets == 5
    assert contract.socket_payload == tuple(fillers)
    assert contract.properties[item.stats['17:0']['market_property']] == 220
    for stat, value in bonuses.items():
        key = f'{stat}:0'
        prop = item.stats[key]['market_property']
        assert prop not in contract.intrinsic_properties
        changed = replace(
            item,
            stats={**item.stats, key: {**item.stats[key], 'raw': value + 1, 'value': value + 1}},
            properties={**item.properties, prop: value + 1},
        )
        assert HANDLERS['named'].contract(changed, 'weapon')[0] is None


def test_ist_weapon_cannot_use_armor_magic_find_bonus():
    item = socketed_item('Legend Spike', 'normal', None, ['Ist Rune'], {80: 25})
    assert HANDLERS['base'].contract(item, 'weapon')[0] is None
