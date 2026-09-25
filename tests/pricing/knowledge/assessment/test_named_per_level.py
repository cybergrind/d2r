import json
from pathlib import Path

from inventory_tracking.items.decode import decode_items
from pricing.knowledge.assessment.engine import assess


def guardian():
    saved = json.loads((Path(__file__).parents[3] / 'inventory_tracking/fixtures/guardian_angel.json').read_text())
    row = saved['snapshot']['resources']['items'][0]
    return decode_items(
        saved['snapshot'],
        saved['report'],
        inventory_page=row['details']['inventory_page'],
        inventory_owner_id=row['details']['owner_id'],
    )[0]


def test_saved_guardian_fixed_per_level_coefficient_is_not_a_market_roll():
    result = assess(guardian(), profiles=[])
    assert not any('native stat 245:0' in gap for gap in result['price_gaps'])
    # This fixture still lacks reliable socket occupancy; no price is invented.
    assert result['contract'] is None
    assert any('socket' in gap.lower() for gap in result['price_gaps'])


def test_per_level_native_and_display_evidence_must_agree():
    extraction = guardian()
    original = next(r for r in extraction['decoded_stats'] if r.get('memory_stat', {}).get('id') == 245)
    changed = [
        {**original, 'value': 999},
        {**original, 'viewer_level': None},
        {**original, 'memory_stat': {**original['memory_stat'], 'raw': 6}},
        {**original, 'per_level': {'numerator': 5, 'denominator': 8}},
    ]
    for replacement in [*changed, None]:
        modified = {
            **extraction,
            'decoded_stats': [
                replacement if r is original else r
                for r in extraction['decoded_stats']
                if r is not original or replacement is not None
            ],
        }
        result = assess(modified, profiles=[])
        assert any('per-level' in gap for gap in result['price_gaps'])


def test_saved_shako_fixed_coefficients_are_independent_of_viewer_level():
    from inventory_tracking.items.metadata import decode_stats
    from pricing.knowledge.assessment.adapters.capture import normalize
    from pricing.knowledge.assessment.mechanics.per_level import fixed_per_level_keys
    from pricing.knowledge.definition_store import catalog
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    saved = json.loads((Path(__file__).parents[3] / 'inventory_tracking/fixtures/harlequin_crest.json').read_text())
    stats = [r for a in saved['arrays']['arrays'] for r in a['stats'] if r['id'] in (216, 217)]
    for level in (62, 91, 99):
        decoded, _, _ = decode_stats(stats, viewer_level=level)
        item = normalize(
            {
                'item': facts('Shako', 'unique', 'Harlequin Crest').to_dict(),
                'decoded_stats': decoded,
                'source': {'stat_capture_complete': True},
            }
        )
        assert fixed_per_level_keys(item, catalog().named['unique', 'Harlequin Crest']) == ({'216:0', '217:0'}, [])
