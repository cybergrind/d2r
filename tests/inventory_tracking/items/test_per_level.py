import json
from pathlib import Path

import pytest

from inventory_tracking.items.metadata import decode_stats


@pytest.mark.parametrize(('level', 'expected'), [(62, 93), (91, 136), (99, 148)])
def test_captured_shako_life_and_mana_match_tooltip(level, expected):
    capture = json.loads((Path(__file__).parents[1] / 'fixtures/harlequin_crest.json').read_text())
    stats = [stat for array in capture['arrays']['arrays'] for stat in array['stats'] if stat['id'] in (216, 217)]
    decoded, affixes, unresolved = decode_stats(stats, viewer_level=level)
    assert [row['text'] for row in decoded] == [
        f'+{expected} to Life (Based on Character Level)',
        f'+{expected} to Mana (Based on Character Level)',
    ]
    assert [row['value'] for row in decoded] == [expected, expected]
    assert [row['memory_stat'] for row in decoded] == stats
    for row in decoded:
        formula = row['per_level']
        assert formula['numerator'] / formula['denominator'] == 1.5
    assert not affixes
    assert not unresolved
