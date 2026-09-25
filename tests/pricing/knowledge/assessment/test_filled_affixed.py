from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import decode_stats, metadata
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.comparables import reject_reasons
from pricing.knowledge.assessment.handlers import HANDLERS
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def filled_armor(rarity, innate=0, count=2, base='Cap'):
    gem = next(b for b in metadata()['bases'].values() if b['name'] == 'Perfect Topaz')
    decoded, affixes, unresolved = decode_stats(
        [
            {'id': 31, 'layer': 0, 'raw': 12},
            {'id': 80, 'layer': 0, 'raw': 24 * count + innate},
            *([{'id': 16, 'layer': 0, 'raw': 15}] if rarity == 'superior' else []),
        ]
    )
    assert not unresolved
    item = replace(
        facts(base, rarity),
        sockets=count,
        socket_contents='filled',
        filled_sockets=count,
        empty_sockets=0,
        socket_items=[
            {'base_code': gem['code'], 'name': gem['name'], 'unit_id': i + 1, 'position': i} for i in range(count)
        ],
    ).to_dict()
    item['affixes'] = affixes
    return normalize({'item': item, 'decoded_stats': decoded, 'source': {'stat_capture_complete': True}})


@pytest.mark.parametrize(
    ('rarity', 'innate'), [('normal', 0), ('superior', 0), ('magic', 15), ('rare', 10), ('crafted', 10)]
)
def test_filled_armor_compares_actual_total_quality_and_payload(rarity, innate):
    item = filled_armor(rarity, innate, base='Helm' if rarity == 'crafted' else 'Cap')
    handler = HANDLERS['base' if rarity in ('normal', 'superior') else 'affixed']
    contract, gaps = handler.contract(item, 'helm')
    assert contract is not None, gaps
    assert contract.socket_payload == ('Perfect Topaz', 'Perfect Topaz')
    assert contract.properties[item.stats['80:0']['market_property']] == 48 + innate
    row = {
        **contract.to_dict(),
        'properties': {**contract.properties, '934': 'Perfect Topaz, Perfect Topaz'},
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'one',
        'ask_ist': 1,
    }
    assert not reject_reasons(contract.to_dict(), row)
    assert reject_reasons(contract.to_dict(), {**row, 'rarity': 'unique'})
    assert reject_reasons(contract.to_dict(), {**row, 'properties': {**row['properties'], '934': 'Jewel'}})
    assert (
        handler.contract(
            replace(item, filled_sockets=None, empty_sockets=None, socket_items=item.socket_items[:1]), 'helm'
        )[0]
        is None
    )


def test_base_magic_find_and_socket_capacity_must_be_explained():
    assert HANDLERS['base'].contract(filled_armor('normal', 1), 'helm')[0] is None
    assert HANDLERS['affixed'].contract(filled_armor('magic', -1), 'helm')[0] is None
    for rarity, handler in [('normal', 'base'), ('magic', 'affixed')]:
        assert HANDLERS[handler].contract(filled_armor(rarity, count=3), 'helm')[0] is None
        assert HANDLERS[handler].contract(filled_armor(rarity), 'shield')[0] is None


def test_body_armor_keeps_defense_and_other_modifiers_in_filled_comparison():
    item = filled_armor('rare', 10, base='Gothic Plate')
    item = replace(item, properties={**item.properties, '427': 20})
    contract, gaps = HANDLERS['affixed'].contract(item, 'armor')
    assert contract is not None, gaps
    assert contract.properties['1855'] == 12
    assert contract.properties['427'] == 20
    row = {
        **contract.to_dict(),
        'properties': {**contract.properties, '934': 'Perfect Topaz, Perfect Topaz'},
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': 'one',
        'ask_ist': 1,
    }
    assert not reject_reasons(contract.to_dict(), row)
    for prop in ('1855', '427', item.stats['80:0']['market_property']):
        assert reject_reasons(contract.to_dict(), {**row, 'properties': {**row['properties'], prop: 99}})
