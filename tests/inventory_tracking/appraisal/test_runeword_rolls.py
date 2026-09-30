from copy import deepcopy
from dataclasses import replace

import pytest

from inventory_tracking.appraisal.intrinsic_rolls import display_stats
from tests.pricing.knowledge.assessment.item_bank.cases.premium_phase_blade_words import CASES


def last_wish(value):
    item = next(c.item for c in CASES if c.id == 'premium-phase-blade/smite-paladin/last-wish/normal/minimum-roll')
    stats = tuple((sid, layer, value if sid == 136 else raw) for sid, layer, raw in item.raw_stats)
    return {'extraction': replace(item, raw_stats=stats).capture()}


def crushing(result):
    return next(row for row in display_stats(result) if row.get('memory_stat', {}).get('id') == 136)


@pytest.mark.parametrize(('value', 'quality'), [(60, 'low'), (65, 'normal'), (70, 'perfect')])
def test_last_wish_total_includes_ber_bonus(value, quality):
    result = last_wish(value)
    original = deepcopy(result)
    row = crushing(result)
    assert row['text'] == f'+{value}% (60-70%) Chance of Crushing Blow'
    assert row['roll_quality'] == quality
    assert result == original


@pytest.mark.parametrize('value', [40, 50, 59, 71])
def test_impossible_recipe_total_is_not_a_ranked_roll(value):
    row = crushing(last_wish(value))
    assert 'roll_range' not in row
    assert 'roll_quality' not in row


@pytest.mark.parametrize('change', ['unknown', 'empty', 'wrong_order', 'wrong_base'])
@pytest.mark.parametrize('value', [50, 70])
def test_unverified_recipe_does_not_supply_combined_range(change, value):
    result = last_wish(value)
    item = result['extraction']['item']
    if change in ('unknown', 'empty'):
        item.update(socket_contents=change, socket_items=[])
    elif change == 'wrong_order':
        item['socket_items'].reverse()
    else:
        item['base_code'] = 'invalid'
    assert 'roll_range' not in crushing(result)
    assert 'roll_quality' not in crushing(result)


@pytest.mark.parametrize(
    ('quality', 'value', 'maximum', 'rank'),
    [
        ('normal', 330, 370, 'low'),
        ('normal', 370, 370, 'perfect'),
        ('superior', 370, 385, 'normal'),
        ('superior', 385, 385, 'perfect'),
    ],
)
def test_doom_combined_ed_includes_ohm_and_possible_superior_bonus(quality, value, maximum, rank):
    from tests.pricing.knowledge.assessment.item_bank.cases.plague_doom_casters import CASES as DOOM_CASES

    item = next(c.item for c in DOOM_CASES if f'/Doom/Berserker Axe/{quality}/minimum-roll' in c.id)
    item = replace(
        item, raw_stats=tuple((sid, layer, value if sid in (17, 18) else raw) for sid, layer, raw in item.raw_stats)
    )
    result = {'extraction': item.capture()}
    original = deepcopy(result)
    row = next(row for row in display_stats(result) if any(s['id'] == 17 for s in row.get('memory_stats', [])))
    assert row['text'] == f'+{value}% (330-{maximum}%) Enhanced Damage'
    assert row['roll_quality'] == rank
    assert result == original


@pytest.mark.parametrize('change', ['unknown', 'wrong_order', 'wrong_base'])
def test_unverified_doom_total_cannot_borrow_recipe_color(change):
    from tests.pricing.knowledge.assessment.item_bank.cases.plague_doom_casters import CASES as DOOM_CASES

    item = next(c.item for c in DOOM_CASES if '/Doom/Berserker Axe/normal/minimum-roll' in c.id)
    item = replace(
        item, raw_stats=tuple((sid, layer, 300 if sid in (17, 18) else raw) for sid, layer, raw in item.raw_stats)
    )
    result = {'extraction': item.capture()}
    captured = result['extraction']['item']
    if change == 'unknown':
        captured.update(socket_contents='unknown', socket_items=[])
    elif change == 'wrong_order':
        captured['socket_items'].reverse()
    else:
        captured['base_code'] = 'invalid'
    row = next(row for row in display_stats(result) if any(s['id'] == 17 for s in row.get('memory_stats', [])))
    assert 'roll_range' not in row
    assert 'roll_quality' not in row


@pytest.mark.parametrize(('value', 'rank'), [(320, 'normal'), (335, 'perfect')])
def test_superior_plague_total_includes_base_ed_without_rune_ed(value, rank):
    from tests.pricing.knowledge.assessment.item_bank.cases.plague_doom_casters import CASES as WORD_CASES

    item = next(c.item for c in WORD_CASES if '/Plague/Cryptic Sword/superior/minimum-roll' in c.id)
    item = replace(
        item, raw_stats=tuple((sid, layer, value if sid in (17, 18) else raw) for sid, layer, raw in item.raw_stats)
    )
    row = next(
        row
        for row in display_stats({'extraction': item.capture()})
        if any(s['id'] == 17 for s in row.get('memory_stats', []))
    )
    assert row['text'] == f'+{value}% (220-335%) Enhanced Damage'
    assert row['roll_quality'] == rank
