"""Read complete candidate market evidence from the offline index.

Scope, freshness and modifier decisions belong to the comparison policy.
"""

import json

from pricing.knowledge.index import _connect
from pricing.knowledge.names import normalize_name


def market_rows(database, name):
    with _connect(database) as connection:
        return [
            json.loads(r[0])
            for r in connection.execute(
                "SELECT payload FROM evidence WHERE kind='market' AND normalized_name=? ORDER BY id",
                (normalize_name(name),),
            )
        ]


def compare_requests(database, requests, *, today=None):
    from pricing.knowledge.assessment.adapters.comparisons import legacy_comparisons

    return legacy_comparisons(compare_request_results(database, requests, today=today))


def compare_request_results(database, requests, *, today=None):
    """Read each eligible name once for independent observed and outcome cohorts."""
    from pricing.knowledge.assessment.comparison_requests import evaluate_request_results

    names = {}
    for request in requests:
        if request.state == 'observed' or request.preparation is not None:
            name = request.contract['name']
            names.setdefault(normalize_name(name), name)
    rows = {key: market_rows(database, name) for key, name in names.items()}
    return evaluate_request_results(requests, rows, today=today)
