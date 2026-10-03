"""An explicit barter ask can support interest without pretending to be Ist."""

import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.policies.named_tiers import RULES
from pricing.knowledge.assessment.policies.trade_qualification import validate_review


def review():
    parent = next(r for r in json.loads(RULES.read_bytes())['policies'] if r['name'] == 'War Traveler')
    return deepcopy(parent['trade_qualification']), parent['valid_if']


def test_explicit_reviewed_barter_supports_candidate_not_numerical_price():
    rule, validity = review()
    validate_review(rule, ('unique', 'War Traveler'), validity)
    barter = next(r for r in rule['market_evidence'] if r['id'] in rule['barter_evidence_ids'])
    assert barter['ask_ist'] is None


@pytest.mark.parametrize('mutation', ['not-reviewed', 'empty', 'zero', 'boolean', 'missing-item', 'premium'])
def test_invalid_barter_cannot_supply_a_third_seller(mutation):
    rule, validity = review()
    barter = next(r for r in rule['market_evidence'] if r['id'] in rule['barter_evidence_ids'])
    if mutation == 'not-reviewed':
        rule['barter_evidence_ids'] = []
    elif mutation == 'empty':
        barter['prices'] = []
    elif mutation == 'zero':
        barter['prices'][0]['quantity'] = 0
    elif mutation == 'boolean':
        barter['prices'][0]['quantity'] = True
    elif mutation == 'missing-item':
        barter['prices'][0].pop('item_id')
    else:
        rule['bands'][0]['status'] = 'premium'
    with pytest.raises(ValueError, match=r'barter|scoped trade'):
        validate_review(rule, ('unique', 'War Traveler'), validity)
