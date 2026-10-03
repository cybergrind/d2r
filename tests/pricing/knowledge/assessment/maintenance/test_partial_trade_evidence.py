from copy import deepcopy

from pricing.knowledge.assessment.maintenance import trade_partial_evidence


IDENTITY = ('unique', "Mara's Kaleidoscope")


def observation(seller='one', resistance=26, **changes):
    return {
        'id': seller + '-' + str(resistance),
        'name': IDENTITY[1],
        'rarity': 'unique',
        'scope_status': 'verified',
        'amount': 1,
        'unit_policy': 'single_item',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'seller_id': seller,
        'observed_at': '2026-09-18',
        'ask_ist': 3,
        'evidence_kind': 'ask',
        'properties': {'441': resistance},
        **changes,
    }


def test_lower_roll_census_counts_independent_scoped_priced_sellers():
    rows = [
        observation(),
        observation(resistance=25),
        observation('two', ask_ist=None),
        observation('three', amount=2),
        observation('four', scope_status='rejected'),
        observation('five', 30),
        observation('six', observed_at=None),
    ]
    result = trade_partial_evidence.audit_region(rows, IDENTITY)
    assert result['priced_sellers'] == ['one']
    assert result['priced_rows'] == ['one-25', 'one-26']
    assert result['unpriced_rows'] == ['two-26']


def test_reviewed_unknown_region_does_not_survive_new_sufficient_evidence():
    result = trade_partial_evidence.audit_region([observation(str(i)) for i in range(3)], IDENTITY)
    assert result['priced_sellers'] == ['0', '1', '2']
    assert trade_partial_evidence.thin_region(result) is False


def test_unknown_region_cannot_borrow_wrong_bounds_or_identity():
    result = trade_partial_evidence.audit_region([], IDENTITY)
    assert trade_partial_evidence.thin_region(result)
    for changes in ({'maximum': 30}, {'name': 'Nagelring'}, {'minimum': 19}):
        assert not trade_partial_evidence.thin_region({**deepcopy(result), **changes})


def test_shared_resistance_without_aggregate_selector_still_counts_as_evidence():
    row = observation(properties=dict.fromkeys(('427', '428', '426', '401'), 26))
    assert trade_partial_evidence.audit_region([row], IDENTITY)['priced_sellers'] == ['one']


def test_market_census_is_bound_to_the_policy_snapshot(tmp_path):
    import hashlib
    import json

    path = tmp_path / trade_partial_evidence.MARKET
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(observation()) + '\n')
    snapshot = {'path': trade_partial_evidence.MARKET, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    document = {'rows': [{'quality': IDENTITY[0], 'name': IDENTITY[1], 'scope': 'partial'}]}
    policies = {IDENTITY: {'trade_qualification': {'market_snapshot': snapshot}}}
    evidence = trade_partial_evidence.load_evidence(tmp_path, document, policies, {'partial'})
    assert evidence[IDENTITY]['priced_sellers'] == ['one']
    assert evidence[IDENTITY]['market_snapshot'] == snapshot
    path.write_text(json.dumps(observation('new')) + '\n')
    assert trade_partial_evidence.load_evidence(tmp_path, document, policies, {'partial'}) == {}
