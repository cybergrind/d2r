"""Total enhancement includes superior quality, but impossible gaps stay unranked."""

from copy import deepcopy

import pytest

from inventory_tracking.appraisal.intrinsic_rolls import display_stats
from tests.pricing.knowledge.assessment.item_bank.models import SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


RECIPES = {
    'Fortitude': ('Archon Plate', ('El', 'Sol', 'Dol', 'Lo'), 16, 200, 215),
    'Enigma': ('Mage Plate', ('Jah', 'Ith', 'Ber'), 16, 0, 15),
    'Flickering Flame': ('Bone Visage', ('Nef', 'Pul', 'Vex'), 16, 30, 45),
    'Melody': ('Matriarchal Bow', ('Shael', 'Ko', 'Nef'), 17, 50, 65),
}


def capture(name, value, quality='superior'):
    base, runes, stat, _, _ = RECIPES[name]
    stats = ((stat, 0, value), (194, 0, len(runes)))
    if stat == 17:
        stats += ((18, 0, value),)
    return {
        'extraction': NativeRunewordItem(
            base,
            quality,
            runeword=name,
            raw_stats=stats,
            sockets=len(runes),
            socket_contents='filled',
            complete=True,
            socket_items=tuple(SocketItem(rune + ' Rune') for rune in runes),
        ).capture()
    }


def enhancement(result, stat):
    return next(
        row
        for row in display_stats(result)
        if row.get('memory_stat', {}).get('id') == stat or any(s['id'] == stat for s in row.get('memory_stats', []))
    )


@pytest.mark.parametrize('name', RECIPES)
def test_fixed_recipe_or_rune_bonus_includes_possible_superior_enhancement(name):
    _, _, stat, low, high = RECIPES[name]
    result = capture(name, high)
    original = deepcopy(result)
    row = enhancement(result, stat)
    assert row['roll_range']['min'] == low
    assert row['roll_range']['max'] == high
    assert row['roll_quality'] == 'perfect'
    assert f'({low}-{high}%)' in row['text']
    assert result == original


@pytest.mark.parametrize('name', RECIPES)
def test_superior_bonus_cannot_be_one_to_four_percent(name):
    _, _, stat, low, _ = RECIPES[name]
    row = enhancement(capture(name, low + 4), stat)
    assert 'roll_range' not in row
    assert 'roll_quality' not in row


@pytest.mark.parametrize('name', RECIPES)
@pytest.mark.parametrize('change', ['unknown-contents', 'wrong-order', 'unknown-quality'])
def test_unverified_enhancement_cannot_receive_a_combined_roll_grade(name, change):
    _, _, stat, _, high = RECIPES[name]
    result = capture(name, high)
    item = result['extraction']['item']
    if change == 'unknown-contents':
        item.update(socket_contents='unknown', socket_items=[])
    elif change == 'wrong-order':
        item['socket_items'].reverse()
    else:
        item['rarity'] = 'unknown'
    row = enhancement(result, stat)
    assert 'roll_range' not in row
    assert 'roll_quality' not in row
