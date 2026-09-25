from dataclasses import replace

from pricing.knowledge.assessment.roles.predicates import Truth, evaluate
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_charge_skill_predicate_distinguishes_absent_empty_available_and_unknown():
    item = facts('Amulet', 'rare')
    rule = {'op': 'charge_skill', 'skill_id': 54, 'value': 1}
    assert evaluate(rule, item).truth == Truth.FALSE
    assert evaluate(rule, replace(item, capture_complete=False)).truth == Truth.UNKNOWN
    for level in (1, 3, 11):
        for count in (0, 1):
            row = {
                'status': 'decoded',
                'value': count,
                'unit': 'charges_remaining',
                'charges': {'remaining': count, 'maximum': 20},
            }
            charged = replace(item, stats={f'204:{54 * 64 + level}': row})
            assert evaluate(rule, charged).truth == (Truth.TRUE if count else Truth.FALSE)
            assert evaluate({**rule, 'value': 0}, charged).truth == Truth.TRUE
    wrong = replace(item, stats={'204:3079': row})  # Nova is not Teleport.
    assert evaluate(rule, wrong).truth == Truth.FALSE
    malformed = replace(item, stats={'204:3457': {**row, 'unit': 'skill_level'}})
    assert evaluate(rule, malformed).truth == Truth.UNKNOWN
