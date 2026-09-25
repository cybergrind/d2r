import json
from pathlib import Path

from inventory_tracking.items.decode import decode_items
from pricing.knowledge.assessment.engine import assess


def test_saved_insight_fixed_poison_is_verified_but_missing_ed_still_blocks_price():
    saved = json.loads((Path(__file__).parents[3] / 'inventory_tracking/fixtures/insight_bill.json').read_text())
    extraction = decode_items(saved['snapshot'], saved['report'], inventory_page=4)[0]
    result = assess(extraction, profiles=[])
    assert not any(f'native stat {key}:0' in gap for key in (57, 58, 59, 326) for gap in result['price_gaps'])
    assert result['contract'] is None
    assert 'Runeword roll 17 was not captured.' in result['price_gaps']
    poison = next(r for r in extraction['decoded_stats'] if r.get('name') == 'poison_damage')
    for key in (57, 58, 59, 326):
        changed = {**poison, 'native_values': {**poison['native_values'], f'{key}:0': {'value': 999, 'unit': 'count'}}}
        modified = {**extraction, 'decoded_stats': [changed if r is poison else r for r in extraction['decoded_stats']]}
        assert any('native stat 57:0' in gap for gap in assess(modified, profiles=[])['price_gaps'])


def test_saved_insight_fire_rune_endpoints_are_intrinsic_only_when_both_match():
    from dataclasses import replace

    from pricing.knowledge.assessment.adapters.capture import normalize
    from pricing.knowledge.assessment.handlers.runeword import definitions, intrinsic_properties

    saved = json.loads((Path(__file__).parents[3] / 'inventory_tracking/fixtures/insight_bill.json').read_text())
    facts = normalize(decode_items(saved['snapshot'], saved['report'], inventory_page=4)[0])
    definition = definitions()['Insight']
    fixed = intrinsic_properties(facts, definition, 'weapon')
    assert fixed['458'] == 5
    assert fixed['459'] == 30
    for key in ('48:0', '49:0'):
        missing = replace(facts, stats={k: v for k, v in facts.stats.items() if k != key})
        assert not {'458', '459'} & intrinsic_properties(missing, definition, 'weapon').keys()
        changed = replace(facts, stats={**facts.stats, key: {**facts.stats[key], 'value': 999}})
        assert not {'458', '459'} & intrinsic_properties(changed, definition, 'weapon').keys()
