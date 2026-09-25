from dataclasses import replace

import pytest

from pricing.knowledge.assessment.comparables import reject_reasons
from pricing.knowledge.assessment.handlers import HANDLERS
from tests.pricing.knowledge.assessment.test_socket_survival_comparisons import socketed_item


@pytest.mark.parametrize(
    ('base', 'quality', 'name', 'count', 'handler'),
    [
        ('Monarch', 'normal', None, 4, 'base'),
        ('Monarch', 'magic', None, 4, 'affixed'),
        ('Monarch', 'rare', None, 2, 'affixed'),
        ('Round Shield', 'unique', "Moser's Blessed Circle", 2, 'named'),
        ('Vortex Shield', 'set', "Griswold's Honor", 3, 'named'),
    ],
)
def test_ist_shield_comparisons_preserve_exact_total_and_socket_contents(base, quality, name, count, handler):
    item = socketed_item(base, quality, name, ['Ist Rune'] * count, {80: 25 * count})
    contract, gaps = HANDLERS[handler].contract(item, 'shield')
    assert contract is not None, gaps
    prop = item.stats['80:0']['market_property']
    assert contract.properties[prop] == 25 * count
    assert contract.socket_payload == ('Ist Rune',) * count
    listing = {
        **contract.to_dict(),
        'properties': {**contract.properties, '934': ', '.join(contract.socket_payload)},
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'one',
        'ask_ist': 1,
    }
    assert not reject_reasons(contract.to_dict(), listing)
    for payload in (None, 'Jewel', 'Ist Rune', ', '.join(['Perfect Topaz'] * count)):
        assert reject_reasons(contract.to_dict(), {**listing, 'properties': {**listing['properties'], '934': payload}})
    assert reject_reasons(contract.to_dict(), {**listing, 'socket_contents': 'empty'})
    assert reject_reasons(contract.to_dict(), {**listing, 'properties': {**listing['properties'], prop: 30 * count}})
    assert HANDLERS[handler].contract(replace(item, socket_items=[]), 'shield')[0] is None


def test_weapon_magic_find_amount_cannot_be_used_for_ist_in_a_plain_shield():
    good = socketed_item('Monarch', 'normal', None, ['Ist Rune'] * 4, {80: 100})
    assert HANDLERS['base'].contract(good, 'shield')[0] is not None
    wrong = socketed_item('Monarch', 'normal', None, ['Ist Rune'] * 4, {80: 120})
    assert HANDLERS['base'].contract(wrong, 'shield')[0] is None
