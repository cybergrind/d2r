import json
from pathlib import Path

import pytest

from inventory_tracking.items.decode import decode_items
from inventory_tracking.items.metadata import decode_stats


def test_captured_dire_song_matches_tooltip():
    capture = json.loads((Path(__file__).parents[1] / 'fixtures/dire_song.json').read_text())
    row = capture['snapshot']['resources']['items'][0]
    result = decode_items(
        capture['snapshot'], capture['report'], inventory_page=4, inventory_owner_id=row['details']['owner_id']
    )[0]
    assert result['item']['name'] == 'Dire Song'
    texts = [r['text'] for r in result['decoded_stats']]
    assert '+1 (1-2) to Cold Skills (Sorceress Only) [T2; T1: 2-2]' in texts
    assert 'Level 7 Nova (47/56 Charges)' in texts
    assert any(t.startswith('+24 (') and 'to Mana' in t for t in texts)
    assert not result['unresolved_stats']


@pytest.mark.parametrize('layer', [3, 7, 11, 63, 65535])
def test_invalid_skill_tab_layers_are_not_guessed(layer):
    stat = {'id': 188, 'layer': layer, 'raw': 1}
    _, facets, unresolved = decode_stats([stat])
    assert unresolved == [stat]
    assert not facets


def test_charge_rows_expose_remaining_and_maximum_without_market_scalar_projection():
    for remaining in (0, 47):
        decoded, facets, unresolved = decode_stats([{'id': 204, 'layer': 48 * 64 + 7, 'raw': (56 << 8) | remaining}])
        assert not unresolved
        assert decoded[0]['value'] == remaining
        assert decoded[0]['unit'] == 'charges_remaining'
        assert decoded[0]['charges'] == {'remaining': remaining, 'maximum': 56}
        assert not facets
