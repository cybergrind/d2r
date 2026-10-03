from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


ITEM = Item(
    'Colossal Jewel', 'unique', "Defender's Fire", ((329, 0, 10), (333, 0, 10), (85, 0, 5), (80, 0, 35), (79, 0, 50))
)


@pytest.mark.parametrize(
    ('damage', 'pierce', 'status'),
    [(5, 5, 'candidate'), (10, 9, 'candidate'), (9, 10, 'candidate'), (10, 10, 'premium')],
)
def test_defender_fire_requires_both_core_rolls_for_premium(damage, pierce, status):
    raw = ((329, 0, damage), (333, 0, pierce), (85, 0, 3), (80, 0, 15), (79, 0, 25))
    result = assess_trade_qualification(normalize(replace(ITEM, raw_stats=raw).capture()))
    assert result['status'] == status
    assert 'price_estimate' not in result


@pytest.mark.parametrize(('stat', 'low', 'high'), [(329, 5, 10), (333, 5, 10), (85, 3, 5), (80, 15, 35), (79, 25, 50)])
def test_defender_fire_requires_each_legal_material_roll(stat, low, high):
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
def test_defender_fire_unverified_variant_does_not_qualify(changes):
    assert assess_trade_qualification(normalize(replace(ITEM, **changes).capture()))['status'] == 'unresolved'
