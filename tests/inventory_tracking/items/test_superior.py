import json
from pathlib import Path

from inventory_tracking.items.decode import decode_items


def test_saved_superior_phase_blade_shows_single_tier_rolls():
    saved = json.loads((Path(__file__).parents[1] / 'fixtures/superior_phase_blade.json').read_text())
    result = decode_items(saved['snapshot'], saved['report'], inventory_page=3)[0]
    texts = [r['text'] for r in result['decoded_stats']]
    assert '+14% (5-15%) Enhanced Damage [T1; T1: 5-15%]' in texts
    assert '+2 (1-3) to Attack Rating [T1; T1: 1-3]' in texts


def test_superior_socket_contributions_are_not_ranked_as_base_rolls():
    saved = json.loads((Path(__file__).parents[1] / 'fixtures/superior_phase_blade.json').read_text())
    arrays = saved['snapshot']['resources']['items'][0]['resource_stats']
    arrays.pop('socket_items')
    result = decode_items(saved['snapshot'], saved['report'], inventory_page=3)[0]
    assert not any('roll_tier' in r for r in result['decoded_stats'])
