from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.cases.protector_trade import ITEM


@pytest.mark.parametrize(('ed', 'pierce'), [(30, 5), (50, 10), (30, 10), (50, 5)])
def test_protector_complete_legal_core_is_ordinary_not_automatically_premium(ed, pierce):
    raw = ((17, 0, ed), (18, 0, ed), (366, 0, pierce), (85, 0, 5), (80, 0, 35), (79, 0, 50))
    assert assess_trade_qualification(normalize(replace(ITEM, raw_stats=raw).capture()))['status'] == 'candidate'


@pytest.mark.parametrize(
    ('stat', 'values'),
    [
        (17, (None, 29, 51, 30)),
        (18, (None, 29, 51, 30)),
        (366, (None, 4, 11)),
        (85, (None, 2, 6)),
        (80, (None, 14, 36)),
        (79, (None, 24, 51)),
    ],
)
def test_protector_requires_all_legal_stats_and_matching_ed_components(stat, values):
    for value in values:
        raw = tuple((s, p, value if s == stat else v) for s, p, v in ITEM.raw_stats if s != stat or value is not None)
        assert assess_trade_qualification(normalize(replace(ITEM, raw_stats=raw).capture()))['status'] == 'unresolved'
