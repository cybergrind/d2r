from dataclasses import replace

import pytest

from pricing.knowledge.assessment.comparables import reject_reasons
from pricing.knowledge.assessment.handlers import HANDLERS
from tests.pricing.knowledge.assessment.test_socket_survival_comparisons import socketed_item


@pytest.mark.parametrize(
    ('base', 'quality', 'name', 'family', 'handler', 'bonuses'),
    [
        ('Sallet', 'unique', 'Rockstopper', 'helm', 'named', {152: 1}),
        ('Mage Plate', 'normal', None, 'armor', 'base', {152: 1}),
        ('Monarch', 'magic', None, 'shield', 'affixed', {152: 1}),
        ('Legend Spike', 'rare', None, 'weapon', 'affixed', {152: 1, 17: 100, 18: 100}),
        ('Ettin Axe', 'unique', 'Rune Master', 'weapon', 'named', {152: 1}),
    ],
)
def test_zod_indestructibility_is_exact_and_preserves_ethereal_variant(base, quality, name, family, handler, bonuses):
    item = replace(socketed_item(base, quality, name, ['Zod Rune'], bonuses), ethereal=True)
    if name == 'Rune Master':
        item = replace(item, sockets=3, filled_sockets=1, empty_sockets=2)
    contract, gaps = HANDLERS[handler].contract(item, family)
    assert contract is not None, gaps
    assert contract.socket_payload == ('Zod Rune',)
    row = {
        **contract.to_dict(),
        'properties': {**contract.properties, '432': True, '934': 'Zod Rune'},
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'one',
        'ask_ist': 1,
    }
    assert not reject_reasons(contract.to_dict(), row)
    assert reject_reasons(contract.to_dict(), {**row, 'ethereal': False})
    assert reject_reasons(contract.to_dict(), {**row, 'properties': {**row['properties'], '432': False}})
    assert reject_reasons(contract.to_dict(), {**row, 'properties': {**row['properties'], '934': 'Jewel'}})


def test_weapon_zod_support_does_not_apply_armor_effects_to_other_runes():
    item = socketed_item('Legend Spike', 'rare', None, ['Shael Rune'], {99: 20, 17: 100, 18: 100})
    assert HANDLERS['affixed'].contract(item, 'weapon')[0] is None
    zod = socketed_item('Legend Spike', 'rare', None, ['Zod Rune'], {152: 1, 17: 100, 18: 100})
    for value in (0, 2):
        invalid = replace(
            zod,
            stats={**zod.stats, '152:0': {**zod.stats['152:0'], 'raw': value, 'value': value}},
            properties={**zod.properties, '432': value},
        )
        assert HANDLERS['affixed'].contract(invalid, 'weapon')[0] is None
