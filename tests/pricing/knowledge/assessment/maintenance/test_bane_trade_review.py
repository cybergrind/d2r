from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance import trade_normal_belt
from pricing.knowledge.assessment.maintenance.trade_reviews import review_dimensions
from tests.pricing.knowledge.assessment.item_bank.cases.bane_authority_trade import CASES
from tests.pricing.knowledge.assessment.maintenance.test_fixed_armor_trade_reviews import inputs
from tests.pricing.knowledge.assessment.maintenance.test_scalar_trade_reviews import data


IDENTITY = ('set', "Bane's Authority")


def test_bane_completion_requires_all_native_reports_and_current_execution():
    document, context = data(IDENTITY, CASES)
    document['rows'][0]['scope'] = 'native_fixed_normal_belt'
    states, accepted = review_dimensions(document, **context)
    assert states[IDENTITY]['state'] == 'reviewed', states[IDENTITY]
    assert accepted
    changed = deepcopy(context)
    next(iter(changed['receipts'].values()))['generation'] = 'stale'
    assert review_dimensions(document, **changed)[0][IDENTITY]['state'] == 'pending'


@pytest.mark.parametrize(
    'label',
    [
        'original',
        'partial-set-energy',
        'exceptional',
        'elite',
        'unknown-ethereal',
        'unknown-sockets',
        'unknown-contents',
        'cast-low',
        'cast-high',
        'life-low',
        'life-high',
        'missing-fixed-bonuses',
    ],
)
def test_missing_native_boundary_cannot_close_the_bane_review(label):
    document, context = data(IDENTITY, CASES)
    review = document['rows'][0]
    review['scope'] = 'native_fixed_normal_belt'
    del review['cases']['bane-authority-trade/' + label]
    states, accepted = review_dimensions(document, **context)
    assert states[IDENTITY]['state'] == 'pending'
    assert not accepted


@pytest.mark.parametrize(
    'change', ['life-shift', 'fixed-life', 'conditional-defense', 'missing-upper-guard', 'roll-layer']
)
def test_changed_native_bane_mechanics_or_rule_are_not_certified(change):
    policy, definitions, stats = inputs(IDENTITY)
    assert trade_normal_belt.specification(policy, definitions, stats) is not None
    if change == 'life-shift':
        stats['7']['shift'] = 0
    elif change == 'fixed-life':
        definitions[0]['game_definition']['max2'] = 21
    elif change == 'conditional-defense':
        definitions[0]['game_definition']['aprop2a'] = 'ac'
    elif change == 'roll-layer':
        definitions[0]['roll_ranges']['7']['layer'] = 1
    else:
        policy['trade_qualification']['valid_if']['all'].pop()
    assert trade_normal_belt.specification(policy, definitions, stats) is None
