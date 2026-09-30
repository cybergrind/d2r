from dataclasses import FrozenInstanceError

import pytest

from pricing.knowledge.assessment.domain.context import AssessmentContext
from pricing.knowledge.assessment.roles.predicates import evaluate
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_loadout_snapshot_cannot_change_when_caller_mutates_equipment():
    items = ['Companion']
    context = AssessmentContext.from_input({'player_items': items})
    items.clear()
    rule = {'op': 'context_contains', 'field': 'player_items', 'value': 'Companion'}
    assert evaluate(rule, facts('Amulet'), context).truth == 'true'
    with pytest.raises(FrozenInstanceError):
        context.player_items = ()
    assert AssessmentContext.from_input(context) is context


def test_empty_equipment_proves_absence_while_missing_or_malformed_does_not():
    rule = {'op': 'context_contains', 'field': 'mercenary_items', 'value': 'Companion'}
    item = facts('Amulet')
    assert evaluate(rule, item, AssessmentContext(mercenary_items=())).truth == 'false'
    for value in (None, {}, [], {'mercenary_items': None}, {'mercenary_items': ['Companion', {}]}):
        assert evaluate(rule, item, value).truth == 'unknown'


def test_swap_items_are_distinct_from_main_and_mercenary_equipment():
    rule = {'op': 'context_contains', 'field': 'player_swap_items', 'value': 'Spirit'}
    item = facts('Crystal Sword')
    from pricing.knowledge.assessment.roles.predicates import validate

    validate(rule)
    assert evaluate(rule, item, {'player_items': ['Spirit'], 'mercenary_items': ['Spirit']}).truth == 'unknown'
    assert evaluate(rule, item, {'player_items': ['Spirit'], 'player_swap_items': []}).truth == 'false'
    gear = ['Spirit']
    context = AssessmentContext.from_input({'player_swap_items': gear})
    gear.clear()
    assert evaluate(rule, item, context).truth == 'true'
    for invalid in (None, 'Spirit', ['Spirit', None], {'Spirit': 1}):
        assert evaluate(rule, item, {'player_swap_items': invalid}).truth == 'unknown'
    with pytest.raises(ValueError, match='Use membership'):
        validate({**rule, 'op': 'context_eq'})
    count_rule = {**rule, 'op': 'context_count_at_least', 'count': 2}
    validate(count_rule)
    assert evaluate(count_rule, item, {'player_swap_items': ['Spirit', 'Spirit']}).truth == 'true'
    assert evaluate(count_rule, item, {'player_swap_items': {'Spirit'}}).truth == 'unknown'
