from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def role(stats, **changes):
    profile = next(p for p in build()['profiles'] if p['id'] == 'echoing-starter-dagger')
    candidate = replace(facts('Cinquedeas', 'rare'), stats=stats, **changes)
    return assess_roles(candidate, [profile])[0]


def test_known_native_skill_does_not_require_presentation_text():
    result = role({'188:57': {'status': 'decoded', 'value': 2}})
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
    result = role({'188:57': row})
    assert result['status'] == 'partial'
    assert result['failed'] == []
    assert result['skill_trace']['truth'] == 'unknown'


def test_conflicting_native_skill_cannot_count_as_known_positive():
    result = role(
        {'188:57': {'status': 'decoded', 'value': 2, 'text': '+2 Eldritch'}}, gaps=['Duplicate native stat 188:57.']
    )
    assert not result['matched']
    assert result['skill_trace']['truth'] == 'unknown'


def test_complete_absence_fails_but_incomplete_absence_is_unknown():
    assert role({})['status'] == 'failed'
    assert role({}, capture_complete=False)['status'] == 'partial'
