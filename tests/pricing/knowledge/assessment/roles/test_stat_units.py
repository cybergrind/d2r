from dataclasses import replace

import pytest

from pricing.knowledge.assessment.roles.predicates import evaluate, validate
from tests.pricing.knowledge.assessment.test_family_contracts import facts


RULE = {'op': 'stat_at_least', 'key': '253:0', 'value': 10, 'unit': 'replenishment_rate'}


@pytest.mark.parametrize('unit', [None, 'seconds', 'quantity'])
def test_replenishment_comparison_requires_rate_units_even_under_negation(unit):
    item = replace(facts('Flying Axe', 'rare'), stats={'253:0': {'status': 'decoded', 'value': 10, 'unit': unit}})
    assert evaluate(RULE, item).truth == 'unknown'
    assert evaluate({'not': RULE}, item).truth == 'unknown'


def test_correct_rate_matches_and_only_complete_absence_can_supply_zero():
    item = replace(
        facts('Flying Axe', 'rare'), stats={'253:0': {'status': 'decoded', 'value': 10, 'unit': 'replenishment_rate'}}
    )
    assert evaluate(RULE, item).truth == 'true'
    assert evaluate({**RULE, 'value': 11}, item).truth == 'false'
    zero_rule = {**RULE, 'value': 0, 'absent_is_zero': True}
    absent = replace(item, stats={}, capture_complete=True, gaps=())
    assert evaluate(zero_rule, absent).truth == 'true'
    assert evaluate(zero_rule, replace(absent, capture_complete=False)).truth == 'unknown'
    assert evaluate(zero_rule, replace(absent, gaps=('Unresolved stat capture',))).truth == 'unknown'
    assert evaluate({**zero_rule, 'absent_is_zero': False}, absent).truth == 'unknown'


@pytest.mark.parametrize('unit', ['', True, 10, [], 'invented_unit'])
def test_invalid_stat_units_are_rejected(unit):
    with pytest.raises(ValueError, match='unit'):
        validate({**RULE, 'unit': unit})
