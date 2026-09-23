import json
from pathlib import Path

from inventory_tracking.items.decode import decode_items


def test_insight_captured_bonuses_and_ranges():
    saved = json.loads((Path(__file__).parents[1] / 'fixtures/insight_bill.json').read_text())
    result = decode_items(saved['snapshot'], saved['report'], inventory_page=4)[0]
    assert result['item']['name'] == 'Insight'
    rows = result['decoded_stats']
    assert 'Level 12 (12-17) Meditation Aura When Equipped' in [r['text'] for r in rows]
    assert '+5 (1-6) to Critical Strike' in [r['text'] for r in rows]
    assert not result['unresolved_stats']
    assert next(r for r in rows if r.get('memory_stat', {}).get('id') == 151)['roll_quality'] == 'low'
    # The saved capture does NOT contain 230 ED. Never manufacture it from totals.
    assert not any(r.get('name') == 'item_damage_percent' for r in rows)
    assert any('percentage was not captured' in note for note in result['review'])
