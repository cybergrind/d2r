"""A source witness can choose equipment alternatives, never unrelated requirements."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.planner_equipment_branch import equipment_branch


ETH = {'op': 'fact_eq', 'field': 'ethereal', 'value': True}
NONETH = {**ETH, 'value': False}


def test_nested_witness_keeps_conjunctions_and_does_not_mutate_the_rule():
    required = {'op': 'fact_eq', 'field': 'identified', 'value': True}
    rule = {'all': [required, {'any': [{'all': [ETH, {'any': [ETH, NONETH]}]}, NONETH]}]}
    original = deepcopy(rule)
    result = equipment_branch(rule, {'/all/1': 0, '/all/1/any/0/all/1': 0})
    assert result == {'all': [required, {'all': [ETH, ETH]}]}
    assert rule == original


@pytest.mark.parametrize(
    'other',
    [
        {'op': 'context_eq', 'field': 'mercenary_type', 'value': 'Act 2 Might'},
        {'op': 'fact_eq', 'field': 'identified', 'value': True},
        {'op': 'fact_eq', 'field': 'sockets', 'value': 4},
        {'op': 'fact_eq', 'field': 'ethereal', 'value': 1},
        {'all': []},
        {**ETH, 'unreviewed': True},
    ],
)
def test_witness_cannot_select_away_wearer_recipe_or_identification_rules(other):
    with pytest.raises(ValueError, match='base/ethereal'):
        equipment_branch({'any': [ETH, other]}, {'': 0})
