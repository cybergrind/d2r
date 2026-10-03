from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


ITEM = Item('Amulet', 'unique', 'Entropy Locket', ((357, 0, 10), (105, 0, 10), (41, 0, 40), (77, 0, 15), (35, 0, 12)))


@pytest.mark.parametrize(
    'raw',
    [
        ITEM.raw_stats,
        ((357, 0, 5), (105, 0, 5), (41, 0, 25), (77, 0, 10), (35, 0, 8)),
        ((357, 0, 9), (105, 0, 7), (41, 0, 34), (77, 0, 12), (35, 0, 8)),
    ],
)
def test_entropy_legal_rolls_qualify_without_an_invented_perfect_premium(raw):
    result = assess_trade_qualification(normalize(replace(ITEM, raw_stats=raw).capture()))
    assert result['status'] == 'candidate'
    assert 'price_estimate' not in result


@pytest.mark.parametrize(('stat', 'low', 'high'), [(357, 5, 10), (105, 5, 10), (41, 25, 40), (77, 10, 15), (35, 8, 12)])
def test_entropy_each_material_roll_must_be_present_and_legal(stat, low, high):
    for value in (None, low - 1, high + 1):
        raw = tuple((s, p, value if s == stat else v) for s, p, v in ITEM.raw_stats if s != stat or value is not None)
        assert assess_trade_qualification(normalize(replace(ITEM, raw_stats=raw).capture()))['status'] == 'unresolved'


@pytest.mark.parametrize(
    'changes',
    [
        {'ethereal': True},
        {'ethereal': None},
        {'sockets': 1},
        {'sockets': None},
        {'socket_contents': 'unknown'},
        {'identified': False},
    ],
)
def test_entropy_unverified_variant_cannot_qualify(changes):
    assert assess_trade_qualification(normalize(replace(ITEM, **changes).capture()))['status'] == 'unresolved'
