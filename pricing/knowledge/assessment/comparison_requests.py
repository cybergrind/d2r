"""Pure request-set evaluation: keep observed prices separate from prepared-outcome ask references."""

import json
from datetime import UTC, datetime

from pricing.knowledge.assessment.adapters.comparisons import legacy_comparisons
from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from pricing.knowledge.assessment.domain.comparison_results import ComparisonResult
from pricing.knowledge.names import normalize_name


def evaluate_requests(requests, rows_by_name, *, today=None):
    return legacy_comparisons(evaluate_request_results(requests, rows_by_name, today=today))


def evaluate_request_results(requests, rows_by_name, *, today=None):
    today = today or datetime.now(UTC).date()
    grouped = {}
    seen = set()
    for request in requests:
        if request.request_id in seen:
            raise ValueError('Duplicate comparison request ID')
        seen.add(request.request_id)
        data = request.to_dict()
        key = (
            request.segment_id,
            request.state,
            request.policy_version,
            json.dumps(data.get('preparation'), sort_keys=True, allow_nan=False),
            json.dumps(data['contract'], sort_keys=True, allow_nan=False),
        )
        group = grouped.setdefault(key, {**data, 'request_ids': [], 'role_ids': []})
        group['request_ids'].append(request.request_id)
        group['role_ids'] = list(dict.fromkeys([*group['role_ids'], *request.role_ids]))
    results = []
    for group in grouped.values():
        observed = group['state'] == 'observed'
        contract = group['contract'] if observed else None
        rows = rows_by_name.get(normalize_name(contract['name']), ()) if observed else ()
        comparisons = evaluate(contract, rows)
        price = price_from_comparables(comparisons, today=today)
        if not observed:
            price['unavailable_reason'] = 'hypothetical'
        result = {**group, 'comparisons': comparisons, 'price_estimate': price}
        if not observed and group.get('preparation'):
            outcome_rows = rows_by_name.get(normalize_name(group['contract']['name']), ())
            outcome = evaluate(group['contract'], outcome_rows)
            result['outcome_comparisons'] = outcome
            result['outcome_ask_estimate'] = price_from_comparables(outcome, today=today)
        results.append(ComparisonResult(**result))
    return tuple(results)
