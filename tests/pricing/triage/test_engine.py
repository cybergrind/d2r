from datetime import date

from pricing.triage.engine import assess


def test_threshold_liquidity_staleness_and_own_use_are_separate():
    item = {'category': 'uniques', 'name': 'Example', 'properties': {}}
    tables = {
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': {'rows': []},
        'bands': {
            ('uniques', 'example', 'name'): {
                'median_ist': 0.25,
                'liquidity': 'liquid',
                'observed_at': '2026-08-01',
                'sellers': 10,
            }
        },
    }
    result = assess(item, tables, today=date(2026, 10, 3))
    assert result['verdict'] == 'sell'
    assert result['stale'] is True
    tables['bands'][('uniques', 'example', 'name')]['liquidity'] = 'thin'
    assert assess(item, tables)['verdict'] == 'slow'
    tables['bands'][('uniques', 'example', 'name')]['median_ist'] = 0.24
    assert assess(item, tables)['verdict'] == 'vendor'
    tables['own']['rows'] = [{'category': 'uniques', 'name': 'Example', 'conditions': {}}]
    assert assess(item, tables)['verdict'] == 'self'


def test_required_property_unknown_does_not_match_premium_bucket():
    tables = {
        'rules': {
            'keep_ist': 0.25,
            'rows': [
                {
                    'category': 'uniques',
                    'name': 'Example',
                    'bucket': 'perfect',
                    'premium': True,
                    'properties': {'425': {'min': 120}},
                }
            ],
        },
        'own': {'rows': []},
        'bands': {},
    }
    item = {'category': 'uniques', 'name': 'Example', 'properties': {}}
    assert assess(item, tables)['verdict'] == 'vendor'
    assert assess({**item, 'properties': {'425': 120}}, tables)['verdict'] == 'sell'


def test_bulk_band_is_only_used_for_that_quantity():
    tables = {
        'rules': {'keep_ist': 0.25, 'rows': []},
        'own': {'rows': []},
        'bands': {
            ('runes', 'example', 'quantity:40'): {
                'median_ist': 0.5,
                'liquidity': 'thin',
                'observed_at': '2026-10-03',
            },
        },
    }
    item = {'category': 'runes', 'name': 'Example', 'quantity': 1}
    assert assess(item, tables)['band'] is None
    assert assess({**item, 'quantity': 40}, tables)['verdict'] == 'slow'
    assert assess({**item, 'quantity': 20}, tables)['band'] is None
