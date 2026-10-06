import json
from pathlib import Path

import pytest

from pricing.triage.engine import assess


def tables():
    return {
        'bands': {},
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': json.loads(Path('pricing/data/triage/own.json').read_text()),
    }


@pytest.mark.parametrize(
    'item',
    [
        {'category': 'uniques', 'name': 'Harlequin Crest', 'ethereal': False},
        {'category': 'magic', 'family': 'amul', 'ethereal': False, 'properties': {'1862': 2, '520': 10}},
        {
            'category': 'base',
            'name': 'Giant Thresher',
            'rarity': 'normal',
            'ethereal': True,
            'sockets': 4,
            'empty_sockets': True,
        },
    ],
)
def test_guide_self_use_items_have_actionable_slot_reason(item):
    result = assess(item, tables())
    assert result['verdict'] == 'self'
    assert 'Echoing' in result['reason'] or 'mercenary' in result['reason']
    assert result['own_use']['slot']


@pytest.mark.parametrize(
    'item',
    [
        {'category': 'uniques', 'name': 'Harlequin Crest', 'ethereal': True},
        {'category': 'magic', 'family': 'amul', 'ethereal': False, 'properties': {'1862': 1, '520': 10}},
        {
            'category': 'base',
            'name': 'Giant Thresher',
            'rarity': 'normal',
            'ethereal': False,
            'sockets': 4,
            'empty_sockets': True,
        },
        {'category': 'uniques', 'name': 'Bloodfist', 'ethereal': False},
    ],
)
def test_wrong_roll_variant_and_generic_leveling_are_not_self_use(item):
    assert assess(item, tables())['verdict'] != 'self'


def test_priced_sell_takes_priority_over_self_use():
    data = tables()
    data['bands']['uniques', 'harlequin crest', 'name'] = {
        'q1_ist': 1,
        'median_ist': 1,
        'sellers': 10,
        'liquidity': 'liquid',
        'bucket': 'name',
    }
    result = assess({'category': 'uniques', 'name': 'Harlequin Crest', 'ethereal': False}, data)
    assert result['verdict'] == 'sell'


def test_paid_pattern_check_remains_trade_review_with_own_use_attached():
    data = tables()
    data['rules']['rows'] = [{'category': 'magic', 'pattern': {'properties': {'1862': 2, '520': 10}}}]
    item = {'category': 'magic', 'family': 'amul', 'properties': {'1862': 2, '520': 10}}
    result = assess(item, data)
    assert result['verdict'] == 'check'
    assert result['own_use']['slot'] == 'amulet'


@pytest.mark.parametrize(
    'spec',
    [
        {'base': 'Amulet', 'rarity': 'magic', 'item_level': 90},
        {'base': 'Wyrmhide Boots', 'rarity': 'magic', 'item_level': 90},
        {'base': 'Monarch', 'rarity': 'normal', 'sockets': 4},
        {'base': 'Small Charm', 'rarity': 'magic', 'stats': {'7:0': 20}},
        {'base': 'Corona', 'name': 'Crown of Ages', 'rarity': 'unique'},
        {'base': 'Demonhead', 'name': 'Cure', 'category': 'runewords', 'sockets': 3, 'socket_contents': 'filled'},
        {'base': 'War Staff', 'name': 'Obsession', 'category': 'runewords', 'sockets': 6, 'socket_contents': 'filled'},
    ],
)
def test_current_guide_crafting_bases_and_endgame_variants_qualify(spec):
    from pricing.triage.guide_cases import item_from_spec

    item = item_from_spec({'rarity': 'normal', 'sockets': 0, 'ethereal': False, **spec})
    result = assess(item, tables())
    assert result['own_use']
    assert result['own_use']['source']


@pytest.mark.parametrize(
    'spec',
    [
        {'base': 'Amulet', 'rarity': 'magic', 'item_level': 40},
        {'base': 'Amulet', 'rarity': 'magic'},
        {'base': 'Wyrmhide Boots', 'rarity': 'rare', 'item_level': 90},
        {'base': 'Monarch', 'rarity': 'normal', 'sockets': 4, 'ethereal': True},
        {'base': 'Monarch', 'rarity': 'normal', 'sockets': 3},
        {'base': 'Small Charm', 'rarity': 'magic', 'stats': {'7:0': 5}},
        {'base': 'Corona', 'name': 'Crown of Ages', 'rarity': 'unique', 'ethereal': True},
        {'base': 'Demonhead', 'name': 'Cure', 'category': 'runewords', 'sockets': 2, 'socket_contents': 'filled'},
        {'base': 'War Staff', 'name': 'Obsession', 'category': 'runewords', 'sockets': 6, 'socket_contents': 'empty'},
        {'base': 'Cap', 'name': 'Lore', 'category': 'runewords', 'sockets': 2, 'socket_contents': 'filled'},
        {
            'base': 'Quilted Armor',
            'name': 'Stealth',
            'category': 'runewords',
            'sockets': 2,
            'socket_contents': 'filled',
        },
    ],
)
def test_own_use_does_not_expand_to_wrong_facets_or_generic_leveling(spec):
    from pricing.triage.guide_cases import item_from_spec

    item = item_from_spec({'rarity': 'normal', 'sockets': 0, 'ethereal': False, **spec})
    assert not assess(item, tables())['own_use']
