import json
from pathlib import Path

from pricing.knowledge.recommendations import build_recommendations


def test_sigon_boot_and_belt_leveling_advice_keeps_native_piece_counts_and_strength():
    data = Path('pricing/data')
    result = build_recommendations(
        json.loads((data / 'appraisal-leveling-candidates-2026-09-23.json').read_text()),
        json.loads((data / 'appraisal-item-facts.json').read_text()),
        json.loads((data / 'appraisal-utility.json').read_text()),
    )
    rows = {r['name']: r for r in result['rows'] if r['source_id'] == 'mrllamasc-transcript'}
    boots = rows["Sigon's Sabot"]
    belt = rows["Sigon's Wrap"]
    assert boots['priority'] == 3
    assert belt['priority'] == 3
    assert any('3 pieces' in c and 'magic find' in c for c in boots['conditions'])
    assert any('2 pieces' in c and 'attack rating' in c for c in boots['conditions'])
    assert any('70 Strength' in c for c in boots['conditions'])
    assert any('60 Strength' in c for c in belt['conditions'])
    assert 'Life' in belt['reason']
    assert boots['review'].startswith('2026-09-26:')
    assert belt['source_date'] == '2025-04-24'
