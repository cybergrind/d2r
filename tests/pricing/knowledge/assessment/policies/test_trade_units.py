import copy
import json

import pytest

from pricing.knowledge.assessment.policies.named_tiers import RULES
from pricing.knowledge.assessment.policies.trade_qualification import validate_review


@pytest.mark.parametrize(
    'changes',
    [
        {'unit_policy': 'ambiguous', 'amount': 2},
        {'unit_policy': 'single_item', 'amount': 2},
        {'unit_policy': 'single_item', 'amount': True},
        {'unit_policy': None, 'amount': 1},
    ],
)
def test_trade_segments_require_explicit_single_item_asks(changes):
    policy = next(p for p in json.loads(RULES.read_bytes())['policies'] if p['name'] == 'Raven Frost')
    review = copy.deepcopy(policy['trade_qualification'])
    review['market_evidence'][0].update(changes)
    with pytest.raises(ValueError, match='scoped trade qualification evidence'):
        validate_review(review, ('unique', 'Raven Frost'), policy['valid_if'])
