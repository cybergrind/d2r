"""Explicit advice must not masquerade as a missing setup requirement."""

from copy import deepcopy
from dataclasses import replace

import pytest

from inventory_tracking.appraisal.build_use_summary import build_use_summary, detail_lines
from pricing.knowledge.assessment.profiles import assess_roles, validate_profiles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def profile():
    return {
        'id': 'charm',
        'build': 'lightning-sorceress',
        'variant': 'Main alternatives',
        'side': 'player',
        'slot': 'Charms',
        'role': 'Lightning skiller',
        'review_status': 'reviewed_candidate_rule',
        'types': ['lcha'],
        'qualities': ['magic'],
        'source': {'path': 'guide', 'locator': '/charm', 'sha256': 'source'},
        'must': {'op': 'stat_at_least', 'key': '188:9', 'value': 1, 'absent_is_zero': True},
        'advisory_conditions': ['Keep the charm in the active inventory for its bonuses.'],
    }


def test_satisfied_item_keeps_advice_without_false_missing_requirements():
    item = replace(facts('Grand Charm', 'magic'), stats={'188:9': {'status': 'decoded', 'value': 1}})
    role = assess_roles(item, [profile()])[0]
    assert role['status'] == 'matched'
    assert role['missing'] == []
    assert role['advisory_conditions'] == profile()['advisory_conditions']
    summary = build_use_summary([role])
    assert any('1 confirmed / 0 conditional' in line for line in summary.lines)
    assert '    Note: Keep the charm in the active inventory for its bonuses.' in detail_lines(summary)


@pytest.mark.parametrize(('complete', 'status'), [(True, 'failed'), (False, 'partial')])
def test_advice_never_overrides_failed_or_unknown_native_requirements(complete, status):
    item = replace(facts('Grand Charm', 'magic'), capture_complete=complete)
    assert assess_roles(item, [profile()])[0]['status'] == status


def test_existing_conditions_remain_blocking_until_explicitly_reviewed_as_advice():
    row = profile()
    row['conditions'] = ['Verify the companion item.']
    item = replace(facts('Grand Charm', 'magic'), stats={'188:9': {'status': 'decoded', 'value': 1}})
    role = assess_roles(item, [row])[0]
    assert role['status'] == 'partial'
    assert role['missing'] == ['Verify the companion item.']


@pytest.mark.parametrize('advice', ['text', [''], [None], ['same', 'same']])
def test_invalid_advice_is_rejected(advice):
    row = deepcopy(profile())
    row['advisory_conditions'] = advice
    with pytest.raises(ValueError, match='advisory'):
        validate_profiles([row])
