from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


def item(mf=30, ar=75):
    return Item('Ring', 'unique', 'Nagelring', ((80, 0, mf), (19, 0, ar)))


@pytest.mark.parametrize(
    ('mf', 'ar', 'status'),
    [
        (15, 50, 'unresolved'),
        (29, 75, 'unresolved'),
        (30, 50, 'candidate'),
        (30, 74, 'candidate'),
        (30, 75, 'candidate'),
    ],
)
def test_nagel_maximum_mf_is_an_ordinary_candidate_not_an_automatic_premium(mf, ar, status):
    result = assess_trade_qualification(normalize(item(mf, ar).capture()))
    assert result['status'] == status
    assert 'price_estimate' not in result
    if status == 'candidate':
        assert result['material_stats'] == ['80:0', '19:0']


@pytest.mark.parametrize(('key', 'lo', 'hi'), [(80, 15, 30), (19, 50, 75)])
def test_nagel_both_rolls_must_be_known_and_legal(key, lo, hi):
    for value in (None, lo - 1, hi + 1):
        raw = tuple((s, p, value if s == key else v) for s, p, v in item().raw_stats if s != key or value is not None)
        assert assess_trade_qualification(normalize(replace(item(), raw_stats=raw).capture()))['status'] == 'unresolved'


@pytest.mark.parametrize(
    'changes',
    [
        {'identified': False},
        {'ethereal': True},
        {'ethereal': None},
        {'sockets': 1},
        {'sockets': None},
        {'socket_contents': 'unknown'},
    ],
)
def test_nagel_unknown_or_impossible_variants_stay_unresolved(changes):
    assert assess_trade_qualification(replace(normalize(item().capture()), **changes))['status'] == 'unresolved'
