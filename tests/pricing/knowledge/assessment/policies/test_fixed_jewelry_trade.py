from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


ITEMS = [
    Item('Ring', 'unique', 'The Stone of Jordan'),
    Item('Amulet', 'set', "Tal Rasha's Adjudication"),
    Item('Amulet', 'unique', "Highlord's Wrath"),
]


@pytest.mark.parametrize('item', ITEMS)
def test_fixed_named_jewelry_has_trade_demand_without_a_random_roll_threshold(item):
    result = assess_trade_qualification(normalize(item.capture()))
    assert result['status'] == 'candidate'
    assert result['material_stats'] == []
    assert 'fixed' in result['reason'].lower()
    assert 'price_estimate' not in result


@pytest.mark.parametrize('item', ITEMS)
@pytest.mark.parametrize(
    'changes',
    [
        {'identified': False},
        {'ethereal': None},
        {'ethereal': True},
        {'sockets': None},
        {'sockets': 1},
        {'socket_contents': 'unknown'},
    ],
)
def test_fixed_trade_identity_still_requires_verified_legal_variant(item, changes):
    assert assess_trade_qualification(replace(normalize(item.capture()), **changes))['status'] == 'unresolved'


@pytest.mark.parametrize('item', ITEMS)
def test_fixed_jewelry_review_agrees_with_native_roll_definitions(item):
    from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition

    definition, gaps = resolve_named_definition(normalize(item.capture()))
    assert not gaps
    assert definition['roll_ranges']
    assert all(row['min'] == row['max'] for row in definition['roll_ranges'].values())
    assert not definition.get('variable_per_level_effects')
    assert not definition.get('base_defense_range')
    assert not definition.get('native_socket_range')
    if item.rarity == 'set':
        # The 3-32 lightning damage endpoints are a fixed damage interval.
        assert definition['fixed_elemental_effects'] == (
            {'kind': 'lightning', 'slot': 4, 'minimum_damage': 3, 'maximum_damage': 32},
        )
