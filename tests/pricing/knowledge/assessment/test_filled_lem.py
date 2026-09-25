from dataclasses import replace

import pytest

from pricing.knowledge.assessment.comparables import reject_reasons
from pricing.knowledge.assessment.handlers import HANDLERS
from tests.pricing.knowledge.assessment.test_socket_survival_comparisons import socketed_item


@pytest.mark.parametrize(('quality', 'handler'), [('normal', 'base'), ('magic', 'affixed'), ('rare', 'affixed')])
@pytest.mark.parametrize(
    ('base', 'family', 'bonus'),
    [('Crystal Sword', 'weapon', 75), ('Mask', 'helm', 50), ('Mage Plate', 'armor', 50), ('Monarch', 'shield', 50)],
)
def test_lem_recipient_bonus_keeps_total_and_exact_contents(quality, handler, base, family, bonus):
    bonuses = {79: 2 * bonus, **({17: 0, 18: 0} if family == 'weapon' else {})}
    item = socketed_item(base, quality, None, ['Lem Rune'] * 2, bonuses)
    contract, gaps = HANDLERS[handler].contract(item, family)
    assert contract is not None, gaps
    prop = item.stats['79:0']['market_property']
    assert contract.properties[prop] == 2 * bonus
    assert contract.socket_payload == ('Lem Rune', 'Lem Rune')
    listing = {
        **contract.to_dict(),
        'properties': {**contract.properties, '934': 'Lem Rune, Lem Rune'},
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'one',
        'ask_ist': 1,
    }
    assert not reject_reasons(contract.to_dict(), listing)
    for changed in (
        {**listing, 'socket_contents': 'empty'},
        {**listing, 'properties': {**listing['properties'], '934': 'Lem Rune'}},
        {**listing, 'properties': {**listing['properties'], prop: 2 * bonus + 1}},
    ):
        assert reject_reasons(contract.to_dict(), changed)
    assert HANDLERS[handler].contract(replace(item, socket_items=[]), family)[0] is None


@pytest.mark.parametrize(
    ('base', 'name', 'quality', 'family', 'count', 'bonus', 'innate'),
    [
        ('Grand Crown', 'Crown of Thieves', 'unique', 'helm', 1, 50, 80),
        ('Ornate Armor', "Griswold's Heart", 'set', 'armor', 3, 50, 0),
        ('Ettin Axe', 'Rune Master', 'unique', 'weapon', 3, 75, 0),
    ],
)
def test_named_lem_items_keep_gold_roll_and_validate_native_bounds(base, name, quality, family, count, bonus, innate):
    item = socketed_item(base, quality, name, ['Lem Rune'] * count, {79: count * bonus})
    contract, gaps = HANDLERS['named'].contract(item, family)
    assert contract is not None, gaps
    prop = item.stats['79:0']['market_property']
    assert contract.properties[prop] == innate + count * bonus
    wrong_total = innate + count * bonus + 100
    wrong = replace(
        item,
        stats={**item.stats, '79:0': {**item.stats['79:0'], 'raw': wrong_total, 'value': wrong_total}},
        properties={**item.properties, prop: wrong_total},
    )
    assert HANDLERS['named'].contract(wrong, family)[0] is None


def test_lem_weapon_does_not_accept_the_armor_bonus():
    for base, family, bonus in [('Crystal Sword', 'weapon', 50), ('Monarch', 'shield', 75)]:
        item = socketed_item(base, 'normal', None, ['Lem Rune'], {79: bonus, 17: 0, 18: 0})
        assert HANDLERS['base'].contract(item, family)[0] is None
