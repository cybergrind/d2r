from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def role(stats, **changes):
    profile = next(p for p in build()['profiles'] if p['id'] == 'abyss-starter-dagger')
    candidate = replace(facts('Cinquedeas', 'rare'), stats=stats, **changes)
    return assess_roles(candidate, [profile])[0]


def test_known_native_skill_does_not_require_presentation_text():
    result = role({'188:58': {'status': 'decoded', 'value': 2}})
    assert result['status'] == 'partial'  # Still needs whole-loadout conditions.
    assert result['skill_trace']['truth'] == 'true'
    assert result['matched']


@pytest.mark.parametrize(
    'row',
    [
        {'status': 'unresolved', 'value': 2},
        {'status': 'decoded', 'value': '2'},
        {'status': 'decoded', 'value': float('nan')},
        {'status': 'decoded', 'value': True},
    ],
)
def test_unknown_skill_evidence_is_not_failed_or_matched(row):
    result = role({'188:58': row})
    assert result['status'] == 'partial'
    assert result['failed'] == []
    assert result['skill_trace']['truth'] == 'unknown'


def test_conflicting_native_skill_cannot_count_as_known_positive():
    result = role(
        {'188:58': {'status': 'decoded', 'value': 2, 'text': '+2 Chaos'}}, gaps=['Duplicate native stat 188:58.']
    )
    assert not result['matched']
    assert result['skill_trace']['truth'] == 'unknown'


def test_complete_absence_fails_but_incomplete_absence_is_unknown():
    assert role({})['status'] == 'failed'
    assert role({}, capture_complete=False)['status'] == 'partial'


@pytest.mark.parametrize(
    ('stats', 'complete'), [({}, True), ({}, False), ({'107:402': {'status': 'decoded', 'value': 1}}, True)]
)
def test_identical_typed_skill_gate_does_not_duplicate_report_restrictions(stats, complete):
    from copy import deepcopy

    profile = next(p for p in build()['profiles'] if p['id'] == 'abyss-starter-dagger')
    old = deepcopy(profile)
    old.pop('must')
    item = replace(facts('Cinquedeas', 'rare'), stats=stats, capture_complete=complete)
    before = assess_roles(item, [old])[0]
    after = assess_roles(item, [profile])[0]
    for key in ('status', 'matched', 'missing', 'failed'):
        assert after[key] == before[key]
    assert after['rule_trace'] == after['skill_trace']


def test_distinct_required_gate_keeps_its_failure_alongside_skill_failure():
    from copy import deepcopy

    profile = deepcopy(next(p for p in build()['profiles'] if p['id'] == 'abyss-starter-dagger'))
    profile['must'] = {'all': [profile['must'], {'op': 'fact_eq', 'field': 'sockets', 'value': 2}]}
    result = assess_roles(facts('Cinquedeas', 'rare'), [profile])[0]
    assert result['failed'] == [
        'Required role properties are not satisfied.',
        'No captured bonus to the skills used by this role.',
    ]
