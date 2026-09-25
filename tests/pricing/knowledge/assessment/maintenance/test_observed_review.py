from copy import deepcopy

from pricing.knowledge.assessment.maintenance.observed_review import merge_replays


def replay():
    return {
        'source': 'capture.json',
        'assessment': {
            'family': 'weapon',
            'quality_policy': 'affixed',
            'facts': {
                'name': 'Rare',
                'base_code': 'verified-code',
                'rarity': 'rare',
                'ethereal': None,
                'sockets': None,
                'gaps': ['sockets unknown'],
                'projection_gaps': ['charge mapping missing'],
                'stats': {},
            },
            'coverage_gaps': ['No reviewed use'],
            'roles': [],
        },
        'price_estimate': {'estimate_ist': None, 'unavailable_reason': 'no_matches'},
    }


def test_observed_gaps_keep_facts_and_independent_reasons_and_are_idempotent():
    captured = replay()
    ledger = merge_replays({}, {'example': captured}, {'capture.json': 'capture-hash'})
    assert len(ledger['captures']) == 1
    record = ledger['captures'][0]
    assert record['facts']['sockets'] is None
    assert record['facts']['ethereal'] is None
    assert {g['dimension'] for g in record['gaps']} == {'capture', 'market_mapping', 'desirability', 'market'}
    assert record['capture_sha256'] == 'capture-hash'
    assert merge_replays(ledger, {'duplicate-label': captured}, {'capture.json': 'capture-hash'}) == ledger
    assert all(g['state'] == 'pending' for g in record['gaps'])


def test_replay_resolution_retains_history_and_unseen_captures():
    captured = replay()
    ledger = merge_replays({}, {'example': captured}, {'capture.json': 'capture-hash'})
    fixed = deepcopy(captured)
    fixed['assessment']['facts']['gaps'] = []
    fixed['assessment']['facts']['projection_gaps'] = []
    fixed['assessment']['coverage_gaps'] = []
    fixed['price_estimate'] = {'estimate_ist': 1}
    updated = merge_replays(ledger, {'example': fixed}, {'capture.json': 'capture-hash'})
    assert updated['captures'][0]['gaps'] == []
    assert len(updated['captures'][0]['history']) == 2
    assert updated['captures'][0]['history'][0]['gaps'] == ledger['captures'][0]['gaps']
    assert merge_replays(updated, {}, {}) == updated
