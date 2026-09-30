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
    captured['input_format'] = 'decoded_observation'
    ledger = merge_replays({}, {'example': captured}, {'capture.json': 'capture-hash'})
    assert len(ledger['captures']) == 1
    record = ledger['captures'][0]
    assert record['facts']['sockets'] is None
    assert record['facts']['ethereal'] is None
    assert {g['dimension'] for g in record['gaps']} == {'capture', 'market_mapping', 'desirability', 'market'}
    assert record['capture_sha256'] == 'capture-hash'
    assert record['input_format'] == 'decoded_observation'
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


def test_final_handler_mapping_resolution_does_not_hide_other_price_gaps():
    captured = replay()
    captured['assessment'].update(contract=None, price_gaps=['sockets unknown', 'Runeword damage roll missing'])
    result = merge_replays({}, {'item': captured}, {'capture.json': 'capture-hash'})
    gaps = result['captures'][0]['gaps']
    assert not any(g['dimension'] == 'market_mapping' for g in gaps)
    assert {'dimension': 'capture', 'state': 'pending', 'reason': 'sockets unknown'} in gaps
    assert {'dimension': 'market', 'state': 'pending', 'reason': 'Runeword damage roll missing'} in gaps
    assert result['captures'][0]['facts']['projection_gaps'] == ['charge mapping missing']


def test_unresolved_final_mapping_and_legacy_mapping_remain_work():
    for diagnostics in ({}, {'contract': None, 'price_gaps': ['charge mapping missing']}, {'price_gaps': []}):
        captured = replay()
        captured['assessment'].update(diagnostics)
        result = merge_replays({}, {'item': captured}, {'capture.json': 'capture-hash'})
        assert any(g['dimension'] == 'market_mapping' for g in result['captures'][0]['gaps'])


def test_executed_contract_removes_only_resolved_mapping_tasks():
    captured = replay()
    captured['assessment'].update(contract={'policy': 'affixed'}, price_gaps=[])
    captured['price_estimate']['unavailable_reason'] = 'insufficient_sellers'
    result = merge_replays({}, {'item': captured}, {'capture.json': 'capture-hash'})
    assert {g['dimension'] for g in result['captures'][0]['gaps']} == {'capture', 'desirability', 'market'}
