from inventory_tracking.appraisal.triage import headline, tone
from inventory_tracking.identify.service import result_lines
from inventory_tracking.presentation import Tone


def test_unmeasured_slow_headline_and_identify_card_are_neutral():
    triage = {
        'verdict': 'slow',
        'reason': 'demand unmeasured',
        'decision_ist': 0.5,
        'band': {'q1_ist': 0.5, 'sellers': 5, 'observed_at': '2026-10-04'},
    }
    assert tone(triage) == Tone.DEFAULT
    assert 'demand unmeasured' in headline(triage)
    rows = result_lines({'state': 'complete', 'items': [{'verdict': 'slow', 'triage': triage}], 'issues': []})
    assert all(r.tone == Tone.DEFAULT for r in rows)
    assert any('demand unmeasured' in r.text for r in rows)
    assert tone(triage | {'reason': 'sub-1-Ist equipment; demand supported'}) == Tone.TIER_MED
