"""Farming alerts need item evidence beyond a generic starter possibility."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from inventory_tracking.appraisal.sections import assessment_lines
from inventory_tracking.identify.service import describe, item_summary, result_lines, verdict_for


FIXTURE = Path(__file__).parents[1] / 'fixtures/malevolent_kris_assessment.json'


def test_captured_kris_stays_quiet_but_preserves_alt_d_starter_use():
    result = json.loads(FIXTURE.read_text())['result']
    original = deepcopy(result)
    summary = item_summary(result['extraction'], result)
    batch = {'state': 'complete', 'items': [summary], 'issues': []}

    assert summary['verdict'] == 'vendor'
    assert 'starter-only' in summary['reason']
    assert 'no supported estimate' in summary['reason']
    assert describe(batch) is None
    assert len(result_lines(batch)) == 1
    assert any('Before Spirit' in line and 'conditional' in line for line in assessment_lines(result))
    assert result == original


def conditional_role():
    return {
        'id': 'caster-circlet',
        'build': 'abyss-warlock-build-guide',
        'side': 'player',
        'slot': 'Helmet',
        'role': '+2 skills / 20 FCR circlet',
        'variant': 'Standard',
        'status': 'partial',
        'matched': ['Required role properties are satisfied.'],
        'missing': ['Whole-loadout FCR needs verification.'],
    }


def test_conditional_item_with_positive_evidence_keeps_its_context():
    result = {'assessment': {'roles': [conditional_role()]}}
    verdict, reason = verdict_for(result)
    assert verdict == 'check'
    assert '+2 skills / 20 FCR circlet' in reason
    assert 'Standard' in reason
    assert 'Whole-loadout FCR needs verification.' in reason


def test_partial_status_without_positive_evidence_is_not_an_alert():
    role = conditional_role()
    role['matched'] = []
    assert verdict_for({'assessment': {'roles': [role]}})[0] == 'vendor'


@pytest.mark.parametrize('status', ['matched', 'partial'])
@pytest.mark.parametrize('progression', ['Before Spirit', 'Starter', 'early', 'FoH Starter', 'Holy Bolt Starter'])
def test_starter_role_alone_does_not_trigger_farming_alert(status, progression):
    role = {**conditional_role(), 'status': status, 'variant': progression}
    assert verdict_for({'assessment': {'roles': [role]}})[0] == 'vendor'


def test_starter_suppression_does_not_hide_independent_price_or_endgame_use():
    result = json.loads(FIXTURE.read_text())['result']
    result['price_estimate'] = {'estimate_ist': 2}
    assert verdict_for(result) == ('keep', 'asks ~2 Ist')
    result['price_estimate'] = {'estimate_ist': None}
    result['assessment']['roles'].append(conditional_role())
    verdict, reason = verdict_for(result)
    assert verdict == 'check'
    assert 'circlet' in reason
    assert '+1' not in reason  # the suppressed role is not counted as another reason


def test_presentation_progression_is_used_when_available():
    role = conditional_role()
    result = {
        'assessment': {'roles': [role]},
        'guide_demand': {'role_presentation': {role['id']: {'progression': 'Starter'}}},
    }
    assert verdict_for(result)[0] == 'vendor'
