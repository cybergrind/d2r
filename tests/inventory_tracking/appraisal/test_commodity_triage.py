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


def test_high_single_seller_ask_is_reference_not_a_conflicting_vendor_price():
    from inventory_tracking.appraisal.triage import headline
    from pricing.triage.engine import assess

    band = {'q1_ist': 300, 'median_ist': 300, 'sellers': 1, 'liquidity': 'none', 'observed_at': '2026-10-03'}
    tables = {
        'rules': {'rows': [], 'keep_ist': 0.25},
        'own': {'rows': []},
        'bands': {('gems', 'amethyst', 'name'): band},
    }
    item = {'category': 'gems', 'name': 'Amethyst'}
    result = assess(item, tables)
    assert result['verdict'] == 'vendor'
    assert result['band'] == band
    assert 'insufficient price evidence' in headline(result)
    assert 'reference asks 300 Ist' in headline(result)
    assert '2026-10-03' in headline(result)
    band.update(sellers=3, liquidity='thin')
    assert headline(assess(item, tables)).startswith('SELL (slow) — asks 300 Ist')
    band['q1_ist'] = 0.1
    assert headline(assess(item, tables)).startswith('VENDOR — asks 0.1 Ist')
