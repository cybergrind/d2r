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
