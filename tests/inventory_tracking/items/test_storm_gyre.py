import json
from pathlib import Path

from inventory_tracking.items.decode import decode_items
from inventory_tracking.items.metadata import decode_stats


def test_storm_gyre_flee_and_fcr_match_tooltip():
    saved = json.loads((Path(__file__).parents[1] / 'fixtures/storm_gyre.json').read_text())
    result = decode_items(saved['snapshot'], saved['report'], inventory_page=3)[0]
    assert result['item']['name'] == 'Storm Gyre'
    assert result['item']['ethereal'] is True
    assert not result['unresolved_stats']
    flee = next(r for r in result['decoded_stats'] if r.get('memory_stat', {}).get('id') == 112)
    assert flee['value'] == 100
    assert '100%' in flee['text']
    fcr = next(r for r in result['decoded_stats'] if r.get('memory_stat', {}).get('id') == 105)
    assert fcr['roll_quality_range'] == {'min': 10, 'max': 20, 'scope': 'all eligible tiers for this base and rarity'}
    assert fcr['roll_quality'] == 'perfect'


def test_flee_decoding_scales_without_creating_a_market_property():
    rows, facets, unresolved = decode_stats([{'id': 112, 'layer': 0, 'raw': 64}])
    assert rows[0]['text'] == 'Hit Causes Monster to Flee +50%'
    assert not facets
    assert not unresolved
    assert decode_stats([{'id': 112, 'layer': 1, 'raw': 128}])[2]
