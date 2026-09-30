from contextlib import nullcontext
from datetime import date

import pytest
from dirty_equals import Contains, IsPartialDict

from inventory_tracking.appraisal.build_use_summary import build_use_summary, detail_lines
from inventory_tracking.appraisal.text import format_appraisal
from pricing.knowledge.__main__ import DEFAULT_DATABASE
from pricing.knowledge.pipeline import retrieve_draft
from pricing.knowledge.publication import current_generation
from pricing.knowledge.published_runtime import load_runtime, published_snapshot
from tests.pricing.knowledge.assessment.item_bank.cases import CASES


@pytest.fixture(scope='module')
def runtime(request):
    if request.config.getoption('--item-bank-staged'):
        return None
    return load_runtime(current_generation('pricing/data/generations'))


@pytest.mark.parametrize('case', CASES, ids=lambda case: case.id)
def test_constructed_item_through_published_appraisal(runtime, case):
    with published_snapshot(runtime) if runtime else nullcontext():
        result = retrieve_draft(
            case.item.capture(),
            runtime.database if runtime else DEFAULT_DATABASE,
            loadout=case.context,
            as_of=date(2026, 9, 27),
        )
        text = format_appraisal({'state': 'complete', 'request_id': case.id, 'result': result})
    assert result == IsPartialDict(offline=True, **case.expected)
    if case.report_contains:
        assert text == Contains(*case.report_contains)
    if case.detail_contains:
        summary = build_use_summary(result['assessment'].get('roles', []), result.get('guide_demand'))
        assert '\n'.join(detail_lines(summary)) == Contains(*case.detail_contains)
    actual_roles = {role['id'] for role in result['assessment'].get('roles', [])}
    assert not actual_roles.intersection(case.absent_roles)
    for snippet in case.report_absent:
        assert snippet not in text
    for key in case.absent_annotations:
        assert key not in result['assessment'].get('stat_evaluation', {}).get('annotations', {})

    for configuration in case.absent_configurations:
        for annotation in result['assessment'].get('stat_evaluation', {}).get('annotations', {}).values():
            assert configuration not in annotation['configuration_ids']

    annotations = result['assessment'].get('stat_evaluation', {}).get('annotations', {})
    for key, configurations in case.absent_stat_configurations.items():
        actual = annotations.get(key, {}).get('configuration_ids', [])
        assert not set(configurations).intersection(actual), (key, configurations, actual)
