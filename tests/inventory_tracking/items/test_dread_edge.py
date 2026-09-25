import json
from pathlib import Path

from inventory_tracking.items.decode import decode_items


def test_dread_edge_preserves_level_formula_and_warlock_skills():
    saved = json.loads((Path(__file__).parents[1] / 'fixtures/dread_edge.json').read_text())
    row = saved['snapshot']['resources']['items'][0]
    result = decode_items(
        saved['snapshot'], saved['report'], inventory_page=4, inventory_owner_id=row['details']['owner_id']
    )[0]
    assert not result['unresolved_stats']
    tab = next(r for r in result['decoded_stats'] if r.get('memory_stat', {}).get('id') == 188)
    assert tab['value'] == 2
    assert 'Eldritch Skills (Warlock Only)' in tab['text']
    damage = next(r for r in result['decoded_stats'] if r.get('memory_stat', {}).get('id') == 218)
    assert damage['value'] == saved['tooltip_truth']['max_damage_at_91']
    assert damage['per_level'] == {'numerator': 4, 'denominator': 8}
    assert result['item']['identified'] is True
    assert result['item']['item_type'] == 'knif'
