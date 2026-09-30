import json
from pathlib import Path

import pytest

from inventory_tracking.appraisal.presentation import ItemAssessment
from inventory_tracking.presentation import Tone
from pricing.knowledge.assessment.engine import assess


@pytest.mark.parametrize(
    ('stem', 'tier', 'tone'),
    [
        ('guardian_angel_tier', 'low', Tone.TIER_LOW),
        ('griswold_heart_tier', 'low', Tone.TIER_LOW),
        ('socketed_shako_tier', 'med', Tone.TIER_MED),
    ],
)
def test_reported_live_tier_failures_in_terminal_and_overlay(stem, tier, tone):
    saved = json.loads((Path(__file__).parents[1] / 'fixtures' / f'{stem}.json').read_bytes())
    extraction = saved['extraction']
    assessment = assess(extraction, profiles=[])
    assert assessment['trade_tier']['tier'] == tier
    document = ItemAssessment.from_record(
        {
            'request_id': stem,
            'state': 'complete',
            'result': {'extraction': extraction, 'assessment': assessment, 'decision': {'price_status': 'unknown'}},
        }
    )
    label = 'mid' if tier == 'med' else tier
    line = next(line for line in document.to_osd() if line.text.startswith('Trade tier:'))
    assert line.text.startswith(f'Trade tier: {label}')
    assert line.tone == tone
    assert line.text in document.to_text()
    assert 'cached asks' not in line.text
    assert '2026-' not in line.text
