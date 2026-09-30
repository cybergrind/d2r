"""A planner's rune payload and mandatory runtime socket condition must agree."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import pin, validate
from tests.pricing.knowledge.assessment.maintenance.test_player_planner_endorsement import records as player_records


@pytest.fixture(scope='module')
def records():
    review, occurrence, role, use = player_records.__wrapped__()
    rune_pin = {**pin('third-parties/d2data/json/gems.json'), 'locator': '/r30'}
    role['source']['corroborating'].append(rune_pin)
    role['must']['all'].extend(
        [
            {'op': 'fact_eq', 'field': 'sockets', 'value': 1},
            {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'filled'},
            {'op': 'socket_runes_equal', 'value': ['Ber Rune']},
        ]
    )
    review['planner_endorsement'].update(
        coverage='player_rune_socket_component', rune_definitions=pin('third-parties/d2data/json/gems.json')
    )
    return review, occurrence, role, use


@pytest.mark.parametrize(
    'change',
    ['retained', 'wrong-rune', 'optional-rune', 'missing-count', 'empty', 'missing-native-pin', 'stale-definitions'],
)
def test_rune_socket_review_requires_actual_payload_and_mandatory_predicates(records, change):
    review, occurrence, role, use = deepcopy(records)
    if change == 'wrong-rune':
        role['must']['all'][-1]['value'] = ['Ist Rune']
    elif change == 'optional-rune':
        role['must']['all'][-1] = {
            'any': [role['must']['all'][-1], {'op': 'fact_eq', 'field': 'identified', 'value': True}]
        }
    elif change == 'missing-count':
        role['must']['all'].pop(-3)
    elif change == 'empty':
        role['must']['all'][-2]['value'] = 'empty'
    elif change == 'missing-native-pin':
        role['source']['corroborating'].pop()
    elif change == 'stale-definitions':
        review['planner_endorsement']['rune_definitions']['sha256'] = '0' * 64
    review['required_predicates'] = deepcopy(role['must']['all'])
    review['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    if change == 'retained':
        assert validate((review, occurrence, role, use))['state'] == 'reviewed'
    else:
        with pytest.raises(ValueError, match=r'[Pp]lanner|[Ss]ocket|[Rr]une|Stale table'):
            validate((review, occurrence, role, use))
