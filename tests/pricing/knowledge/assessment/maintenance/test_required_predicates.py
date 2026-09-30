"""Required source evidence may live in must or in required dependencies."""

import pytest


PAYLOAD = {'op': 'socket_gems_equal', 'value': ['Perfect Topaz'] * 4}
EFFECT = {'op': 'stat_at_least', 'key': '80:0', 'value': 96, 'absent_is_zero': True}
EXPECTED = {'all': [PAYLOAD, EFFECT]}


@pytest.mark.parametrize(
    'role',
    [
        {'must': EXPECTED},
        {'must': {'all': [PAYLOAD, EFFECT]}},
        {'must': PAYLOAD, 'depends_on': [{'when': EFFECT}]},
        {'must': {}, 'depends_on': [{'when': EXPECTED}]},
    ],
)
def test_required_payload_can_be_factored_without_losing_the_requirement(role):
    from pricing.knowledge.assessment.maintenance.source_matching import role_requires

    assert role_requires(role, EXPECTED)


@pytest.mark.parametrize(
    'role',
    [
        {'must': {'any': [PAYLOAD, EFFECT]}},
        {'must': {}, 'depends_on': [{'when': EXPECTED, 'required': False}]},
        {'must': PAYLOAD},
        {'must': {'any': []}},
    ],
)
def test_optional_or_alternative_payload_does_not_prove_a_required_configuration(role):
    from pricing.knowledge.assessment.maintenance.source_matching import role_requires

    assert not role_requires(role, EXPECTED)


def test_native_topaz_source_accepts_payload_as_a_mandatory_item_predicate():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.socketed_table_pattern import validate_pattern
    from tests.pricing.knowledge.assessment.maintenance.test_socketed_table_pattern import pattern_inputs

    review, role, occurrence, parser = pattern_inputs()
    role['must']['all'].append(role.pop('depends_on')[0]['when'])
    validate_pattern(review, role, occurrence, parser, 107, lambda pin: json.loads(Path(pin['path']).read_text()))
