import json
from pathlib import Path

from inventory_tracking.items.metadata import decode_stats, item_base


def test_atmas_scarab_poison_matches_tooltip():
    capture = json.loads((Path(__file__).parents[1] / 'fixtures/atma_scarab.json').read_text())
    decoded, _, unresolved = decode_stats(capture['arrays']['arrays'][-1]['stats'], base=item_base(capture['txt_id']))
    assert '+40 Poison Damage over 4 Seconds' in [s['text'] for s in decoded]
    assert not unresolved


def test_multiple_poison_sources_preserve_rates_without_inventing_a_combined_tooltip():
    stats = [{'id': i, 'layer': 0, 'raw': value} for i, value in [(57, 102), (58, 102), (59, 100), (326, 2)]]
    rows, facets, unresolved = decode_stats(stats)
    assert not unresolved
    assert not facets
    assert [r['memory_stat'] for r in rows] == stats
    assert [(r['value'], r['unit']) for r in rows] == [
        (102 / 256, 'damage_per_frame'),
        (102 / 256, 'damage_per_frame'),
        (4, 'seconds'),
        (2, 'count'),
    ]
    assert not any('Damage over' in r['text'] for r in rows)
