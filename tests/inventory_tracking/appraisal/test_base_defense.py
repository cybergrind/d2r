from dataclasses import replace

import pytest

from inventory_tracking.appraisal.intrinsic_rolls import display_stats
from tests.pricing.knowledge.assessment.item_bank.models import Item


ITEM = Item(
    'Mirrored Boots', 'set', "Horazon's Legacy", ((31, 0, 68), (0, 0, 15), (2, 0, 15), (37, 0, 30)), complete=True
)


def defense_row(extraction):
    rows = display_stats({'extraction': extraction, 'assessment': {}})
    return next(r for r in rows if r.get('memory_stat', {}).get('id') == 31)


def test_horazon_defense_range_is_displayed_independently_of_conditional_walk_speed():
    specimen = replace(ITEM, raw_stats=(*ITEM.raw_stats, (96, 0, 40)))
    row = defense_row(specimen.capture())
    assert row['text'] == 'Defense: 68 (59-68)'
    assert row['roll_quality'] == 'perfect'


@pytest.mark.parametrize('change', ['incomplete', 'enhanced', 'inconsistent-raw'])
def test_unverified_defense_cannot_borrow_plain_base_roll_range(change):
    specimen = replace(ITEM, complete=False) if change == 'incomplete' else ITEM
    if change == 'enhanced':
        specimen = replace(specimen, raw_stats=(*specimen.raw_stats, (16, 0, 1)))
    extraction = specimen.capture()
    if change == 'inconsistent-raw':
        row = next(r for r in extraction['decoded_stats'] if r.get('memory_stat', {}).get('id') == 31)
        row['memory_stat']['raw'] = 67
    assert '(59-68)' not in defense_row(extraction)['text']
