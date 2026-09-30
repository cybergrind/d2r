from copy import deepcopy
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.roles.predicates import evaluate, validate
from tests.pricing.knowledge.assessment.test_family_contracts import facts


THRESHOLDS = {'99:0': 7, '39:0': 15, '41:0': 15, '43:0': 15, '45:0': 15}
RULE = {'op': 'socket_jewel_matches', 'stats': THRESHOLDS, 'count': 2}


def jewel(unit_id, position, **overrides):
    return {
        'unit_id': unit_id,
        'position': position,
        'name': 'Scintillating Jewel of Truth',
        'item_type': 'jewl',
        'stats_complete': True,
        'stats': {k: {'status': 'decoded', 'value': v} for k, v in THRESHOLDS.items()},
        **overrides,
    }


def helmet(children, sockets=2):
    return replace(
        facts('Corona', 'unique', 'Crown of Ages'), sockets=sockets, socket_contents='filled', socket_items=children
    )


def test_two_jewels_require_two_distinct_compound_matches():
    first, second = jewel(100, 0), jewel(101, 1)
    assert evaluate(RULE, helmet([first, second])).truth == 'true'
    second['stats']['39:0']['value'] = 14
    assert evaluate(RULE, helmet([first, second])).truth == 'false'
    first['stats']['99:0']['value'] = 0
    second['stats']['39:0']['value'] = 30
    second['stats']['99:0']['value'] = 14
    # Even sufficient parent sums cannot substitute for two qualifying jewels.
    item = replace(
        helmet([first, second]), stats={k: {'status': 'decoded', 'value': 2 * v} for k, v in THRESHOLDS.items()}
    )
    assert evaluate(RULE, item).truth == 'false'


@pytest.mark.parametrize('mode', ['duplicate_id', 'duplicate_position', 'unknown_id', 'unknown_stats', 'missing_child'])
def test_counted_jewels_do_not_overstate_partial_or_duplicate_capture(mode):
    children = [jewel(100, 0), jewel(101, 1)]
    if mode == 'duplicate_id':
        children[1]['unit_id'] = 100
    elif mode == 'duplicate_position':
        children[1]['position'] = 0
    elif mode == 'unknown_id':
        del children[1]['unit_id']
    elif mode == 'unknown_stats':
        children[1]['stats_complete'] = False
        del children[1]['stats']['99:0']
    else:
        children.pop()
    assert evaluate(RULE, helmet(children)).truth == 'unknown'


def test_counted_jewels_can_prove_subset_without_guessing_remaining_socket():
    item = helmet([jewel(100, 0), jewel(101, 1)], sockets=3)
    assert evaluate(RULE, item).truth == 'true'
    assert evaluate({**RULE, 'count': 3}, item).truth == 'unknown'
    assert evaluate(RULE, replace(item, socket_contents='empty')).truth == 'unknown'


@pytest.mark.parametrize('count', [0, -1, 7, True, 1.5, '2', None])
def test_jewel_count_requires_a_bounded_integer(count):
    with pytest.raises(ValueError, match='count'):
        validate({**RULE, 'count': count})


def test_single_jewel_legacy_predicate_keeps_its_result_shape():
    rule = deepcopy(RULE)
    del rule['count']
    child = jewel(100, 0)
    del child['unit_id']
    del child['position']
    result = evaluate(rule, helmet([child], sockets=1))
    assert result.truth == 'true'
    assert result.observed == THRESHOLDS


@pytest.mark.parametrize('item_type', ['jewl', 'cjwl'])
def test_compound_jewel_matching_accepts_both_native_jewel_families(item_type):
    child = jewel(100, 0, item_type=item_type)
    assert evaluate({**RULE, 'count': 1}, helmet([child], sockets=1)).truth == 'true'
    child['stats']['39:0']['value'] = 14
    assert evaluate({**RULE, 'count': 1}, helmet([child], sockets=1)).truth == 'false'
