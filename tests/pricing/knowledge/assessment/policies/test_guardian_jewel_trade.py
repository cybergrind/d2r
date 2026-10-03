from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


@pytest.fixture(params=[("Guardian's Light", 357, 358), ("Guardian's Thunder", 330, 334)])
def jewel(request):
    name, damage, pierce = request.param
    return Item(
        'Colossal Jewel', 'unique', name, ((damage, 0, 10), (pierce, 0, 10), (85, 0, 5), (80, 0, 35), (79, 0, 50))
    )


@pytest.mark.parametrize(
    ('damage', 'pierce', 'status'),
    [(5, 5, 'candidate'), (9, 10, 'candidate'), (10, 9, 'candidate'), (10, 10, 'premium')],
)
@pytest.mark.parametrize('secondary', [(3, 15, 25), (5, 35, 50)])
def test_guardian_joint_core_rolls_control_premium(jewel, damage, pierce, status, secondary):
    raw = tuple((s, p, value) for (s, p, _), value in zip(jewel.raw_stats, (damage, pierce, *secondary), strict=True))
    result = assess_trade_qualification(normalize(replace(jewel, raw_stats=raw).capture()))
    assert result['status'] == status
    assert result['material_stats'] == [f'{s}:0' for s, _, _ in jewel.raw_stats]


@pytest.mark.parametrize(('index', 'low', 'high'), [(0, 5, 10), (1, 5, 10), (2, 3, 5), (3, 15, 35), (4, 25, 50)])
def test_guardian_requires_every_legal_modifier(jewel, index, low, high):
    for value in (None, low - 1, high + 1):
        raw = tuple(
            (s, p, value if i == index else v)
            for i, (s, p, v) in enumerate(jewel.raw_stats)
            if i != index or value is not None
        )
        assert assess_trade_qualification(normalize(replace(jewel, raw_stats=raw).capture()))['status'] == 'unresolved'


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
def test_guardian_unknown_or_illegal_variant_stays_unresolved(jewel, changes):
    assert assess_trade_qualification(normalize(replace(jewel, **changes).capture()))['status'] == 'unresolved'
