from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


def item(pierce=5, energy=15, mf=20):
    return Item('Ring', 'unique', 'Sling', ((358, 0, pierce), (1, 0, energy), (80, 0, mf)))


@pytest.mark.parametrize(('pierce', 'status'), [(3, 'candidate'), (4, 'candidate'), (5, 'premium')])
@pytest.mark.parametrize(('energy', 'mf'), [(10, 10), (15, 20)])
def test_sling_trade_threshold_uses_magic_pierce_with_legal_secondary_rolls(pierce, status, energy, mf):
    result = assess_trade_qualification(normalize(item(pierce, energy, mf).capture()))
    assert result['status'] == status
    assert 'price_estimate' not in result


@pytest.mark.parametrize(('stat', 'invalid'), [(358, 2), (358, 6), (1, 9), (1, 16), (80, 9), (80, 21)])
def test_sling_impossible_and_missing_rolls_do_not_qualify(stat, invalid):
    specimen = item()
    for raw in (
        tuple((s, p, invalid if s == stat else v) for s, p, v in specimen.raw_stats),
        tuple(row for row in specimen.raw_stats if row[0] != stat),
    ):
        assert (
            assess_trade_qualification(normalize(replace(specimen, raw_stats=raw).capture()))['status'] == 'unresolved'
        )


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
def test_sling_unknown_or_impossible_variant_cannot_qualify(changes):
    assert assess_trade_qualification(normalize(replace(item(), **changes).capture()))['status'] == 'unresolved'
