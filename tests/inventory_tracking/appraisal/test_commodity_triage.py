from inventory_tracking.appraisal.presentation import ItemAssessment


def test_commodity_triage_price_does_not_conflict_with_legacy_unavailable_line():
    result = {
        'triage': {
            'verdict': 'slow',
            'reason': 'asks',
            'band': {'q1_ist': 1, 'sellers': 3, 'observed_at': '2026-10-03'},
        },
        'assessment': {'contract': {'policy': 'quest_material'}},
        'price_estimate': {'unavailable_reason': 'no_matches'},
        'extraction': {'item': {'name': "Talic's Anguish"}, 'issues': []},
    }
    document = ItemAssessment.from_record({'request_id': 'material', 'state': 'complete', 'result': result})
    assert document.to_osd()[0].text.startswith('SELL (slow) — asks 1 Ist')
    assert 'Material: Talic' in document.to_text()
    assert 'Unit price: unavailable' not in document.to_text()
    assert 'Observed stats:' not in document.to_text()
