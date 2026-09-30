"""Native report fixtures must establish identity from rune evidence."""

from dataclasses import replace

import pytest

from tests.pricing.knowledge.assessment.item_bank.cases.fortitude_native_ranges import CASES


def test_native_recipe_overrides_fixture_display_name():
    captured = replace(CASES[0].item, name='Untrusted label', runeword='Untrusted label').capture()
    assert captured['item']['runeword'] == 'Fortitude'
    assert captured['source']['item_identity']['method'] == 'captured_recipe'
    assert captured['source']['item_identity']['observed_table_id'] == 65535
    assert any(row.get('roll_range') for row in captured['decoded_stats'])


@pytest.mark.parametrize('failure', ['unidentified', 'reversed', 'missing', 'partial', 'flag'])
def test_incomplete_or_contradictory_recipe_cannot_supply_report_ranges(failure):
    item = CASES[0].item
    changes = {
        'unidentified': {'identified': False},
        'reversed': {'socket_items': tuple(reversed(item.socket_items))},
        'missing': {'socket_items': item.socket_items[:-1]},
        'partial': {'socket_contents': 'unknown'},
        'flag': {'runeword': None},
    }[failure]
    captured = replace(item, **changes).capture()
    assert captured['item']['runeword'] is None
    assert captured['item']['name'] == 'Archon Plate'
    assert 'item_identity' not in captured['source']
    assert not any(row.get('roll_range') for row in captured['decoded_stats'])


@pytest.mark.parametrize(('quality', 'high'), [('normal', 3), ('superior', 3), ('low_quality', 1)])
def test_native_memory_preserves_staffmod_bounds_without_ranking_total(quality, high):
    from tests.pricing.knowledge.assessment.item_bank.cases.memory_caster_swaps import memory

    captured = memory(quality, high).capture()
    row = next(s for s in captured['decoded_stats'] if s.get('memory_stat', {}).get('layer') == 58)
    assert row['value'] == 3 + high
    assert row['staffmod_range']['min'] == 1
    assert row['staffmod_range']['max'] == high
    assert row['text'].count('staffmod range:') == 1
    assert 'roll_quality' not in row
