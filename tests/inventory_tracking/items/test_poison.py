import json
from pathlib import Path

from inventory_tracking.items.metadata import decode_stats, item_base


def test_atmas_scarab_poison_matches_tooltip():
    capture = json.loads((Path(__file__).parents[1] / 'fixtures/atma_scarab.json').read_text())
    decoded, _, unresolved = decode_stats(capture['arrays']['arrays'][-1]['stats'], base=item_base(capture['txt_id']))
    assert '+40 Poison Damage over 4 Seconds' in [s['text'] for s in decoded]
    assert not unresolved


def test_multiple_poison_sources_remain_explicit_until_verified():
    stats = [{'id': i, 'layer': 0, 'raw': value} for i, value in [(57, 102), (58, 102), (59, 100), (326, 2)]]
    _, _, unresolved = decode_stats(stats)
    assert unresolved == stats
