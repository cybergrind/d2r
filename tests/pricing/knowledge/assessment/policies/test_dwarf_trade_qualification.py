"""Ordinary mixed-roll demand does not rehabilitate the thin perfect-only cohort."""

import json

import pytest

from pricing.knowledge.assessment.policies.named_tiers import RULES
from pricing.knowledge.assessment.policies.trade_qualification import validate_review


def test_two_perfect_single_item_sellers_cannot_establish_a_dwarf_premium():
    policy = next(row for row in json.loads(RULES.read_bytes())['policies'] if row['name'] == 'Dwarf Star')
    review = policy['trade_qualification']
    perfect = [row for row in review['market_evidence'] if row['properties']['414'] == 15]
    assert len({row['seller_id'] for row in perfect}) == 2
    review['default_status'] = 'unresolved'
    review['default_evidence_ids'] = []
    review['bands'] = [
        {
            'when': {'op': 'stat_at_least', 'key': '35:0', 'value': 15},
            'status': 'premium',
            'reason': 'Perfect MDR',
            'evidence_ids': [row['id'] for row in perfect],
        }
    ]
    with pytest.raises(ValueError, match='Insufficient independent trade band evidence'):
        validate_review(review, ('unique', 'Dwarf Star'), policy['valid_if'])
