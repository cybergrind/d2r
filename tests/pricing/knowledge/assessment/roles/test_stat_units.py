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


def test_correct_rate_can_match_but_absence_cannot_supply_a_typed_zero():
    item = replace(
        facts('Flying Axe', 'rare'), stats={'253:0': {'status': 'decoded', 'value': 10, 'unit': 'replenishment_rate'}}
    )
    assert evaluate(RULE, item).truth == 'true'
    assert evaluate({**RULE, 'value': 11}, item).truth == 'false'
    assert evaluate({**RULE, 'value': 0, 'absent_is_zero': True}, replace(item, stats={})).truth == 'unknown'


@pytest.mark.parametrize('unit', ['', True, 10, [], 'invented_unit'])
def test_invalid_stat_units_are_rejected(unit):
    with pytest.raises(ValueError, match='unit'):
        validate({**RULE, 'unit': unit})
