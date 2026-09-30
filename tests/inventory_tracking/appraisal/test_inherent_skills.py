from copy import deepcopy
from dataclasses import replace

import pytest

from inventory_tracking.appraisal.intrinsic_rolls import display_stats
from tests.pricing.knowledge.assessment.item_bank.cases.mist_strafe import CASES
from tests.pricing.knowledge.assessment.item_bank.models import Item, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


def skill_row(result):
    return next(r for r in display_stats(result) if r.get('memory_stat', {}).get('id') == 188)


@pytest.mark.parametrize('include_stat', [False, True])
def test_missing_item_context_preserves_rows_without_inventing_inherent_ranges(include_stat):
    rows = (
        [{'memory_stat': {'id': 188, 'layer': 0, 'raw': 3}, 'value': 3, 'text': '+3 to skills'}] if include_stat else []
    )
    result = {'extraction': {'decoded_stats': rows}}
    original = deepcopy(result)
    assert display_stats(result) == rows
    assert result == original


@pytest.mark.parametrize(('value', 'rank'), [(1, 'low'), (2, 'normal'), (3, 'perfect')])
def test_mist_inherent_bow_skills_do_not_include_all_skills(value, rank):
    item = CASES[0].item
    item = replace(
        item, raw_stats=tuple((sid, layer, value if sid == 188 else raw) for sid, layer, raw in item.raw_stats)
    )
    result = {'extraction': item.capture()}
    original = deepcopy(result)
    row = skill_row(result)
    assert row['text'] == f'+{value} (1-3) to Bow and Crossbow Skills (Amazon Only)'
    assert row['roll_quality'] == rank
    assert result == original


@pytest.mark.parametrize('change', ['unidentified', 'unknown-contents', 'wrong-order', 'impossible-total'])
def test_unverified_inherent_runeword_total_is_not_ranked(change):
    result = {'extraction': CASES[0].item.capture()}
    item = result['extraction']['item']
    if change == 'unidentified':
        item['identified'] = False
    elif change == 'unknown-contents':
        item.update(socket_contents='unknown', socket_items=[])
    elif change == 'wrong-order':
        item['socket_items'].reverse()
    else:
        row = next(r for r in result['extraction']['decoded_stats'] if r.get('memory_stat', {}).get('id') == 188)
        row.update(value=4, text='+4 to Bow and Crossbow Skills (Amazon Only)')
        row['memory_stat']['raw'] = 4
    assert 'roll_range' not in skill_row(result)


@pytest.mark.parametrize('quality', ['normal', 'superior', 'low_quality', 'magic', 'rare'])
def test_plain_amazon_base_range_does_not_guess_random_affix_contributions(quality):
    item = Item('Matriarchal Javelin', quality, raw_stats=((188, 2, 3),), complete=True)
    row = skill_row({'extraction': item.capture()})
    assert ('roll_range' in row) is (quality in ('normal', 'superior', 'low_quality'))


@pytest.mark.parametrize(('value', 'rank'), [(4, 'low'), (5, 'normal'), (6, 'perfect')])
def test_melody_combines_same_tab_recipe_and_base_but_not_other_skills(value, rank):
    item = NativeRunewordItem(
        'Matriarchal Bow',
        'normal',
        runeword='Melody',
        raw_stats=((188, 0, value), (107, 9, 3), (194, 0, 3)),
        sockets=3,
        socket_contents='filled',
        complete=True,
        socket_items=tuple(SocketItem(rune + ' Rune') for rune in ('Shael', 'Ko', 'Nef')),
    )
    row = skill_row({'extraction': item.capture()})
    assert row['text'] == f'+{value} (4-6) to Bow and Crossbow Skills (Amazon Only)'
    assert row['roll_quality'] == rank
