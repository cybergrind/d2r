"""Mutation checks prove the bank asserts actual native and displayed output."""

from copy import deepcopy
from datetime import date

import pytest

from pricing.knowledge.__main__ import DEFAULT_DATABASE
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.item_bank.cases.main_skill_charms import CASES
from tests.pricing.knowledge.assessment.item_bank.report_checks import assert_report_checks


@pytest.fixture(scope='module')
def appraisal():
    case = next(c for c in CASES if c.id == 'main-skill-charms/lightning-sorceress/plain/minimum')
    result = retrieve_draft(case.item.capture(), DEFAULT_DATABASE, loadout=case.context, as_of=date(2026, 9, 27))
    return result, case.report_checks


def test_independent_native_contract_matches_actual_appraisal(appraisal):
    assert_report_checks(*appraisal)


@pytest.mark.parametrize(
    'change', ['value', 'range', 'tier', 'tone', 'marker', 'price', 'full_report', 'truth', 'absent']
)
def test_contract_detects_wrong_expected_output(appraisal, change):
    result, original = appraisal
    checks = deepcopy(original)
    if change == 'value':
        checks['stats'][0]['data']['value'] = 2
    elif change == 'range':
        checks['stats'][0]['data']['roll_range']['max'] = 2
    elif change == 'tier':
        checks['stats'][0]['data']['roll_tier'] = 2
    elif change == 'tone':
        checks['stats'][0]['line']['tone'] = 'perfect'
    elif change == 'marker':
        checks['stats'][0]['line']['spans'][0]['tone'] = 'stat_supporting'
    elif change == 'price':
        checks['price']['estimate_ist'] = 1
    elif change == 'full_report':
        checks['osd'] = []
    elif change == 'truth':
        checks['truth'] = 'unknown'
    else:
        checks['absent_stats'] = ['188:9']
    with pytest.raises(AssertionError):
        assert_report_checks(result, checks)


def test_stat_body_contract_checks_real_text_color_and_own_contribution(appraisal):
    result, original = appraisal
    checks = deepcopy(original)
    checks.pop('osd')
    stat = checks['stats'][0]
    stat['body'] = stat.pop('line')['spans'][-1]
    stat['priority'] = 'desirable'
    assert_report_checks(result, checks)
    for field, value in [('text', '+2 Lightning Skills'), ('tone', 'perfect')]:
        changed = deepcopy(checks)
        changed['stats'][0]['body'][field] = value
        with pytest.raises(AssertionError):
            assert_report_checks(result, changed)
    changed = deepcopy(checks)
    changed['stats'][0]['priority'] = 'supporting'
    with pytest.raises(AssertionError):
        assert_report_checks(result, changed)
