import pytest

from pricing.knowledge.assessment.domain.context import AssessmentContext
from pricing.knowledge.assessment.roles.predicates import evaluate, validate
from tests.pricing.knowledge.assessment.test_family_contracts import facts


RULE = {'op': 'context_count_at_least', 'field': 'player_items', 'value': 'Angelic Halo', 'count': 2}


def test_duplicate_rings_survive_immutable_loadout_and_count_dependency():
    rings = ['Angelic Halo', 'Angelic Halo', 'Angelic Wings']
    context = AssessmentContext(player_items=rings)
    rings.clear()
    result = evaluate(RULE, facts('Ring'), context)
    assert result.truth == 'true'
    assert result.observed == 2
    assert evaluate(RULE, facts('Ring'), {'player_items': ['Angelic Halo']}).truth == 'false'
    assert evaluate(RULE, facts('Ring'), {'player_items': []}).truth == 'false'


def test_membership_only_loadouts_cannot_prove_duplicate_count():
    item = facts('Ring')
    assert evaluate(RULE, item, {'player_items': {'Angelic Halo'}}).truth == 'unknown'
    assert evaluate(RULE, item, {'player_items': set()}).truth == 'false'
    assert evaluate({**RULE, 'count': 1}, item, {'player_items': {'Angelic Halo'}}).truth == 'true'
    for context in ({}, {'player_items': None}, {'player_items': ['Angelic Halo', {}]}):
        assert evaluate(RULE, item, context).truth == 'unknown'


@pytest.mark.parametrize(
    'patch', [{'count': 0}, {'count': True}, {'count': 1.5}, {'field': 'player_class'}, {'value': ''}]
)
def test_item_count_predicate_rejects_invalid_authoring(patch):
    with pytest.raises(ValueError, match='Invalid item count predicate'):
        validate({**RULE, **patch})
