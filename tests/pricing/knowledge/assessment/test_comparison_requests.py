from datetime import date

from pricing.knowledge.assessment.comparison_requests import evaluate_requests
from pricing.knowledge.assessment.domain.comparison_requests import ComparisonRequest


def contract(value):
    return {
        'version': 1,
        'policy': 'affixed',
        'family': 'jewelry',
        'name': 'Ring',
        'rarity': 'rare',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': {'520': value},
    }


def row(value, seller):
    return {
        **contract(value),
        'scope_status': 'verified',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'seller_id': seller,
        'listing_id': seller,
        'ask_ist': 1,
        'observed_at': '2026-09-24',
    }


def test_different_segments_and_modifier_cohorts_never_pool_sellers():
    requests = [
        ComparisonRequest('one', 'fcr10', contract(10), ('role-a',)),
        ComparisonRequest('two', 'fcr20', contract(20), ('role-b',)),
    ]
    results = evaluate_requests(requests, {'ring': [row(10, 'a'), row(20, 'b'), row(20, 'c')]}, today=date(2026, 9, 24))
    assert len(results) == 2
    assert [r['price_estimate']['sellers'] for r in results] == [1, 2]
    assert all(r['price_estimate']['estimate_ist'] is None for r in results)


def test_identical_requests_merge_role_references_but_distinct_segments_do_not():
    requests = [
        ComparisonRequest('one', 'exact', contract(10), ('role-a',)),
        ComparisonRequest('two', 'exact', contract(10), ('role-b',)),
        ComparisonRequest('three', 'other', contract(10), ('role-c',)),
    ]
    results = evaluate_requests(requests, {'ring': [row(10, str(i)) for i in range(3)]}, today=date(2026, 9, 24))
    assert len(results) == 2
    assert results[0]['request_ids'] == ['one', 'two']
    assert results[0]['role_ids'] == ['role-a', 'role-b']
    assert results[1]['role_ids'] == ['role-c']
    assert [r['price_estimate']['estimate_ist'] for r in results] == [1, 1]


def test_hypothetical_preparation_never_receives_current_item_price():
    request = ComparisonRequest('socketed', 'prepared', contract(10), (), state='prepared')
    result = evaluate_requests([request], {'ring': [row(10, str(i)) for i in range(3)]}, today=date(2026, 9, 24))[0]
    assert result['price_estimate']['estimate_ist'] is None
    assert result['price_estimate']['unavailable_reason'] == 'hypothetical'
    assert result['comparisons']['accepted'] == []


def test_request_detaches_mutable_contract_and_roles():
    source = contract(10)
    roles = ['one']
    request = ComparisonRequest('one', 'exact', source, roles)
    source['properties']['520'] = 20
    roles.append('two')
    assert request.to_dict()['contract']['properties']['520'] == 10
    assert request.role_ids == ('one',)


def test_repository_fetches_each_observed_name_once_and_skips_prepared(monkeypatch):
    from pricing.knowledge.assessment import market_repository

    calls = []

    def fetch(database, name):
        calls.append(name)
        return [row(10, str(i)) for i in range(3)]

    monkeypatch.setattr(market_repository, 'market_rows', fetch)
    requests = [
        ComparisonRequest('current', 'exact', contract(10)),
        ComparisonRequest('role', 'other', {**contract(10), 'name': 'ring'}),
        ComparisonRequest('prepared', 'after_socketing', {**contract(10), 'name': 'Amulet'}, state='prepared'),
    ]
    results = market_repository.compare_requests(None, requests, today=date(2026, 9, 24))
    assert calls == ['Ring']
    assert [r['price_estimate']['estimate_ist'] for r in results] == [1, 1, None]


def test_duplicate_request_ids_are_rejected_instead_of_overwriting_results():
    import pytest

    requests = [ComparisonRequest('same', 'a', contract(10)), ComparisonRequest('same', 'b', contract(20))]
    with pytest.raises(ValueError, match='Duplicate comparison request ID'):
        evaluate_requests(requests, {})
