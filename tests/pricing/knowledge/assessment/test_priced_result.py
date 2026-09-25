from datetime import date

import pytest

from pricing.knowledge.assessment.comparison_requests import evaluate_request_results
from pricing.knowledge.assessment.engine import assess_result
from tests.pricing.knowledge.assessment.policies.test_market_tiers import cohort


def test_priced_result_resolves_current_tier_and_detaches_reports():
    from pricing.knowledge.assessment.adapters.priced import legacy_priced_payload
    from pricing.knowledge.assessment.pricing import finalize_assessment

    extraction, rows = cohort('atma_scarab', [1, 1, 1])
    assessment = assess_result(extraction, profiles=[])
    comparisons = evaluate_request_results(
        assessment.comparison_requests, {"atma's scarab": rows}, today=date(2026, 9, 25)
    )
    priced = finalize_assessment(assessment, comparisons, today=date(2026, 9, 25))
    assert priced.assessment.trade_tier['tier'] == 'med'
    assert assessment.trade_tier['status'] == 'pending_review'
    assert priced.price_estimate['estimate_ist'] == 1
    assert priced.current.is_current
    with pytest.raises(TypeError):
        priced.price_estimate['estimate_ist'] = 999
    report = legacy_priced_payload(priced)
    report['assessment']['trade_tier']['tier'] = 'trash'
    report['price_estimate']['notes'].append('external mutation')
    assert priced.assessment.trade_tier['tier'] == 'med'
    assert 'external mutation' not in priced.price_estimate['notes']
    assert priced.assessment.generation == assessment.generation


def test_no_contract_diagnostics_are_included_without_mutating_initial_assessment():
    from pricing.knowledge.assessment.adapters.priced import legacy_priced_payload
    from pricing.knowledge.assessment.pricing import finalize_assessment
    from tests.pricing.knowledge.assessment.test_prepared_base_prices import armor

    item = armor()
    item['source'] = {}
    assessment = assess_result(item, profiles=[])
    priced = finalize_assessment(assessment, (), today=date(2026, 9, 25))
    assert priced.current is None
    assert priced.price_estimate['estimate_ist'] is None
    assert all(gap in priced.price_estimate['notes'] for gap in assessment.price_gaps)
    assert priced.assessment is not None
    report = legacy_priced_payload(priced)
    assert report['assessment']['comparison_results'] == []
    assert report['assessment']['comparisons']['accepted'] == []


def test_finalization_does_not_promote_prepared_quote_to_current_price():
    from pricing.knowledge.assessment.pricing import finalize_assessment
    from tests.pricing.knowledge.assessment.test_comparison_requests import row
    from tests.pricing.knowledge.assessment.test_prepared_base_prices import armor

    assessment = assess_result(armor(), profiles=[])
    prepared = next(r for r in assessment.comparison_requests if r.preparation)
    rows = [{**row(10, str(i)), **prepared.to_dict()['contract']} for i in range(3)]
    comparisons = evaluate_request_results(
        assessment.comparison_requests, {'mage plate': rows}, today=date(2026, 9, 24)
    )
    priced = finalize_assessment(assessment, comparisons, today=date(2026, 9, 24))
    assert priced.price_estimate['estimate_ist'] is None
    assert priced.current.state == 'observed'
    assert any(
        r.outcome_ask_estimate and r.outcome_ask_estimate['estimate_ist'] == 1 for r in priced.comparison_results
    )
    assert priced.assessment.trade_tier == assessment.trade_tier
