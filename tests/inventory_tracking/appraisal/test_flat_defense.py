from copy import deepcopy
from dataclasses import replace

import pytest

from inventory_tracking.appraisal.intrinsic_rolls import display_stats
from tests.pricing.knowledge.assessment.item_bank.models import Item, SocketItem


def giant(value=350):
    return Item(
        'Bone Visage',
        'unique',
        'Giant Skull',
        ((31, 0, value), (194, 0, 2)),
        sockets=2,
        named_table_id=379,
        complete=True,
    )


def shown(item):
    result = {'extraction': item.capture(), 'assessment': {}}
    before = deepcopy(result)
    rows = display_stats(result)
    assert result == before
    return next(r for r in rows if r.get('memory_stat', {}).get('id') == 31)


@pytest.mark.parametrize(('value', 'quality'), [(350, 'low'), (400, 'normal'), (477, 'perfect')])
def test_giant_skull_total_defense_range(value, quality):
    row = shown(giant(value))
    assert row['text'] == f'Defense: {value} (350-477)'
    assert row['roll_quality'] == quality


@pytest.mark.parametrize(
    ('name', 'base', 'table', 'value', 'low', 'high'),
    [
        ("Griffon's Eye", 'Diadem', 336, 260, 150, 260),
        ("Kira's Guardian", 'Tiara', 357, 170, 90, 170),
        ("Ormus' Robes", 'Dusk Shroud', 358, 487, 371, 487),
        ('Steelrend', 'Ogre Gauntlets', 391, 281, 232, 281),
    ],
)
def test_other_flat_defense_uniques(name, base, table, value, low, high):
    item = Item(base, 'unique', name, ((31, 0, value),), named_table_id=table, complete=True)
    assert shown(item)['text'] == f'Defense: {value} ({low}-{high})'


def test_verified_shael_payload_does_not_change_defense_range():
    item = replace(
        giant(),
        socket_contents='filled',
        socket_items=(SocketItem('Shael Rune'), SocketItem('Shael Rune')),
        raw_stats=(*giant().raw_stats, (99, 0, 40)),
    )
    assert shown(item)['text'] == 'Defense: 350 (350-477)'


@pytest.mark.parametrize(
    'change', ['incomplete', 'unknown-contents', 'ethereal', 'unknown-ethereal', 'enhanced', 'invalid-total']
)
def test_unproven_defense_totals_are_not_graded(change):
    item = giant()
    if change == 'incomplete':
        item = replace(item, complete=False)
    elif change == 'unknown-contents':
        item = replace(item, socket_contents='unknown')
    elif change == 'ethereal':
        item = replace(item, ethereal=True)
    elif change == 'unknown-ethereal':
        item = replace(item, ethereal=None)
    elif change == 'enhanced':
        item = replace(item, raw_stats=(*item.raw_stats, (16, 0, 15)))
    else:
        item = giant(999)
    row = shown(item)
    assert 'roll_quality' not in row
    assert '350-477' not in row['text']


@pytest.mark.parametrize(
    ('base', 'value', 'interval'), [('Studded Leather', 60, '57-60'), ('Wire Fleece', 506, '400-506')]
)
def test_upgraded_base_has_its_own_total_range(base, value, interval):
    item = Item(base, 'unique', 'Twitchthroe', ((31, 0, value),), named_table_id=82, complete=True)
    assert shown(item)['text'] == f'Defense: {value} ({interval})'


def test_unknown_defense_jewel_cannot_borrow_empty_range():
    item = replace(
        giant(),
        socket_contents='filled',
        socket_items=(SocketItem('Jewel', ((31, 0, 10),)),),
        raw_stats=((31, 0, 360), (194, 0, 2)),
    )
    row = shown(item)
    assert '350-477' not in row['text']
    assert 'roll_quality' not in row


def test_conflicting_raw_defense_is_not_graded():
    result = {'extraction': giant().capture(), 'assessment': {}}
    row = next(r for r in result['extraction']['decoded_stats'] if r.get('memory_stat', {}).get('id') == 31)
    row['memory_stat']['raw'] = 999
    displayed = next(r for r in display_stats(result) if r.get('memory_stat', {}).get('id') == 31)
    assert '350-477' not in displayed['text']


def test_native_ethereal_applies_multiplier_to_base_not_flat_bonus():
    item = replace(giant(555), ethereal=True)
    row = shown(item)
    assert row['text'] == 'Defense: 555 (400-555)'
    assert row['roll_quality'] == 'perfect'


def test_ethereal_upgraded_base_requires_separate_mechanics_proof():
    item = Item(
        'Wire Fleece', 'unique', 'Twitchthroe', ((31, 0, 746),), named_table_id=82, complete=True, ethereal=True
    )
    assert 'roll_range' not in shown(item)


def test_ethereal_integer_rounding_gap_is_not_a_legal_roll():
    # Helm15..18 -> base22,24,25,27; fixed+10 cannot yield33.
    item = Item('Helm', 'unique', 'Coif of Glory', ((31, 0, 33),), named_table_id=73, complete=True, ethereal=True)
    assert 'roll_quality' not in shown(item)


@pytest.mark.parametrize(
    ('name', 'base', 'table', 'value', 'sockets'),
    [
        ("Griffon's Eye", 'Diadem', 336, 260, 2),
        ('Steelrend', 'Ogre Gauntlets', 391, 281, 1),
    ],
)
def test_illegal_socket_capacity_does_not_establish_defense_roll(name, base, table, value, sockets):
    item = Item(
        base, 'unique', name, ((31, 0, value), (194, 0, sockets)), named_table_id=table, complete=True, sockets=sockets
    )
    assert 'roll_quality' not in shown(item)
