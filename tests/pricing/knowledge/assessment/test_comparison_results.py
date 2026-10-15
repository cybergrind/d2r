from dataclasses import FrozenInstanceError
from datetime import date
from typing import Any

import pytest

from pricing.knowledge.assessment.domain.comparison_requests import ComparisonRequest
from tests.pricing.knowledge.assessment.test_comparison_requests import contract, row


def test_comparison_result_detaches_evidence_and_report_mutations():
    from pricing.knowledge.assessment.adapters.comparisons import legacy_comparison
    from pricing.knowledge.assessment.comparison_requests import evaluate_request_results

    rows = [row(10, str(i)) for i in range(3)]
    (result,) = evaluate_request_results(
        [ComparisonRequest('current', 'exact', contract(10))], {'ring': rows}, today=date(2026, 9, 24)
    )
    assert result.is_current
    assert result.price_estimate['estimate_ist'] == 1
    before = legacy_comparison(result)
    rows[0]['properties']['520'] = 20
    rows[0]['ask_ist'] = 100
    assert legacy_comparison(result) == before
    with pytest.raises(FrozenInstanceError):
        result.state = 'prepared'  # pyrefly: ignore[read-only]  # proves the result is frozen
    with pytest.raises(TypeError):
        result.comparisons['accepted'][0]['properties']['520'] = 99
    output: dict[str, Any] = legacy_comparison(result)
    output['price_estimate']['notes'].append('caller mutation')
    output['comparisons']['accepted'].clear()
    assert legacy_comparison(result) == before


def test_prepared_result_retains_separate_immutable_outcome_estimate():
    from pricing.knowledge.assessment.adapters.comparisons import legacy_comparison
    from pricing.knowledge.assessment.comparison_requests import evaluate_request_results
    from pricing.knowledge.assessment.engine import assess_result
    from tests.pricing.knowledge.assessment.test_prepared_base_prices import armor

    request = next(r for r in assess_result(armor(), profiles=[]).comparison_requests if r.preparation)
    serialized: dict[str, Any] = request.to_dict()
    rows = [{**row(10, str(i)), **serialized['contract']} for i in range(3)]
    (result,) = evaluate_request_results([request], {'mage plate': rows}, today=date(2026, 9, 24))
    assert not result.is_current
    assert result.price_estimate['estimate_ist'] is None
    assert result.outcome_ask_estimate is not None
    assert result.outcome_ask_estimate['estimate_ist'] == 1
    assert result.preparation is not None
    with pytest.raises(TypeError):
        result.preparation['resources'][0]['quantity'] = 20
    report: dict[str, Any] = legacy_comparison(result)
    report['outcome_ask_estimate']['estimate_ist'] = 999
    assert result.outcome_ask_estimate['estimate_ist'] == 1
