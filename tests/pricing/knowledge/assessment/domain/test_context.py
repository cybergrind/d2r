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
