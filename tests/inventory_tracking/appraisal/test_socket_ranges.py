from dataclasses import replace

import pytest

from inventory_tracking.appraisal.intrinsic_rolls import display_stats
from tests.pricing.knowledge.assessment.item_bank.models import Item, SocketItem


def socket_row(item):
    extraction = item.capture()
    original = next(r for r in extraction['decoded_stats'] if r.get('memory_stat', {}).get('id') == 194)
    before = dict(original)
    rows = display_stats({'extraction': extraction})
    assert original == before
    return next(r for r in rows if r.get('memory_stat', {}).get('id') == 194)


@pytest.mark.parametrize(('count', 'quality'), [(1, 'low'), (2, 'perfect')])
def test_heavens_light_reports_attainable_socket_range(count, quality):
    item = Item('Mighty Scepter', 'unique', "Heaven's Light", ((194, 0, count),), sockets=count, complete=True)
    row = socket_row(item)
    assert row['text'] == f'Sockets: {count} (1-2) — {count} empty'
    assert row['roll_quality'] == quality
    assert row['roll_range']['max'] == 2


@pytest.mark.parametrize('base', ['Jagged Star', 'Devil Star'])
def test_aldur_socket_max_stays_three_after_upgrade(base):
    item = Item(base, 'set', "Aldur's Rhythm", ((194, 0, 3),), sockets=3, complete=True)
    row = socket_row(item)
    assert row['text'] == 'Sockets: 3 (2-3) — 3 empty'
    assert row['roll_quality'] == 'perfect'


def test_contents_are_preserved_when_correcting_socket_range():
    item = Item('Mighty Scepter', 'unique', "Heaven's Light", ((194, 0, 2),), sockets=2, complete=True)
    row = socket_row(replace(item, socket_contents='filled', socket_items=(SocketItem('Shael Rune'),)))
    assert row['text'] == 'Sockets: 2 (1-2) — Shael (1 contents captured)'
    assert row['roll_quality'] == 'perfect'


def test_impossible_socket_count_is_not_colored_perfect():
    item = Item('Mighty Scepter', 'unique', "Heaven's Light", ((194, 0, 3),), sockets=3, complete=True)
    row = socket_row(item)
    assert 'roll_quality' not in row
    assert 'roll_range' not in row
    assert row['text'] == 'Sockets: 3 — 3 empty'
