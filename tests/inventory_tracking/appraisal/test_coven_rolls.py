"""Coven's variable MF is a recipe roll plus a verified helmet Ist bonus."""

from dataclasses import replace

import pytest

from inventory_tracking.appraisal.runeword_rolls import display_runeword_rolls
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.mechanics.runeword_rolls import variable_roll_gaps
from pricing.knowledge.definition_store import catalog
from tests.pricing.knowledge.assessment.item_bank.models import SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


def coven(total):
    return NativeRunewordItem(
        'Diadem',
        'normal',
        'Coven',
        ((80, 0, total), (16, 0, 30), (86, 0, 1), (194, 0, 3)),
        sockets=3,
        socket_contents='filled',
        runeword='Coven',
        socket_items=tuple(SocketItem(name) for name in ('Ist Rune', 'Ral Rune', 'Io Rune')),
    ).capture()


@pytest.mark.parametrize(('total', 'quality'), [(26, 'low'), (35, 'normal'), (40, 'perfect')])
def test_coven_magic_find_ranks_total_with_fixed_ist(total, quality):
    row = next(r for r in display_runeword_rolls(coven(total)) if r['memory_stat']['id'] == 80)
    assert row['roll_range']['min'] == 26
    assert row['roll_range']['max'] == 40
    assert row['roll_quality'] == quality
    assert '(26-40%)' in row['text']


@pytest.mark.parametrize('total', [25, 41, 30.5])
def test_impossible_magic_find_total_blocks_comparison(total):
    capture = coven(26)
    facts = normalize(capture)
    # Fractional value is an adversarial normalized input; native capture is integer.
    facts = replace(facts, stats={**facts.stats, '80:0': {**facts.stats['80:0'], 'value': total}})
    gaps = variable_roll_gaps(facts, catalog().runewords['Coven'], 'helm')
    assert any('80:0' in gap and '26-40' in gap for gap in gaps)


def test_unverified_ist_cannot_grade_recipe_only_magic_find():
    capture = coven(10)
    capture['item']['socket_contents'] = 'unknown'
    row = next(r for r in display_runeword_rolls(capture) if r['memory_stat']['id'] == 80)
    assert 'roll_range' not in row
    assert 'roll_quality' not in row


@pytest.mark.parametrize(('total', 'invalid'), [(12, False), (25, False), (11, True), (26, True), (12.5, True)])
def test_dream_magic_find_has_no_ist_offset(total, invalid):
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    item = replace(facts('Bone Visage'), stats={'80:0': {'status': 'decoded', 'value': total}})
    gaps = variable_roll_gaps(item, catalog().runewords['Dream'], 'helm')
    assert any('80:0' in gap and '12-25' in gap for gap in gaps) is invalid
