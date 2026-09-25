"""Hit Blinds Target / Freezes target: description function 12 hides the +1 suffix."""

import pytest

from inventory_tracking.items.build_metadata import stat_label
from inventory_tracking.items.metadata import decode_stats


@pytest.mark.parametrize(
    ('stat_id', 'raw', 'text', 'property_id'),
    [
        (113, 1, 'Hit Blinds Target', '568'),
        (113, 3, 'Hit Blinds Target +3', '568'),
        (134, 1, 'Freezes target', '570'),
        (134, 3, 'Freezes target +3', '570'),
    ],
)
def test_deathspade_style_hit_effects_decode_with_market_facets(stat_id, raw, text, property_id):
    stat = {'id': stat_id, 'layer': 0, 'raw': raw}
    rows, affixes, unresolved = decode_stats([stat])
    assert not unresolved
    assert rows[0]['status'] == 'decoded'
    assert rows[0]['text'] == text
    assert rows[0]['value'] == raw
    assert [(a['property_id'], a['value']) for a in affixes] == [(property_id, raw)]


@pytest.mark.parametrize('stat', [{'id': 113, 'layer': 0, 'raw': 0}, {'id': 134, 'layer': 2, 'raw': 1}])
def test_hit_effects_without_a_positive_level_stay_unresolved(stat):
    rows, affixes, unresolved = decode_stats([stat])
    assert unresolved == [stat]
    assert rows[0]['status'] == 'unresolved'
    assert not affixes


def test_description_function_12_labels_carry_the_market_level_suffix():
    row = {'*ID': 113, 'descfunc': 12}
    assert stat_label(row, 'Hit Blinds Target') == 'Hit Blinds Target +{{value}}'
    assert stat_label({**row, 'Encode': 2}, 'Hit Blinds Target') is None
    assert stat_label({**row, 'descfunc': 5}, 'Hit Causes Monster to Flee %+d%%') is None
