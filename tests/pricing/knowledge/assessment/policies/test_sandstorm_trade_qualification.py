from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


def item(strength=15, vitality=15, defense=170, poison=70, ethereal=True):
    return Item(
        'Scarabshell Boots',
        'unique',
        'Sandstorm Trek',
        ((0, 0, strength), (3, 0, vitality), (16, 0, defense), (45, 0, poison)),
        ethereal=ethereal,
    )


@pytest.mark.parametrize(
    ('strength', 'vitality', 'status'),
    [(10, 10, 'candidate'), (14, 15, 'candidate'), (15, 14, 'candidate'), (15, 15, 'premium')],
)
def test_trek_premium_requires_both_attributes_on_verified_ethereal_boots(strength, vitality, status):
    result = assess_trade_qualification(normalize(item(strength, vitality).capture()))
    assert result['status'] == status
    assert result['material_stats'] == ['0:0', '3:0', '16:0', '45:0']
    assert 'price_estimate' not in result


@pytest.mark.parametrize('ethereal', [False, None])
def test_trek_nonethereal_or_unknown_never_borrows_ethereal_premium(ethereal):
    facts = normalize(item(ethereal=ethereal).capture())
    assert assess_trade_qualification(facts)['status'] == 'unresolved'
    assert assess_tier(facts)['tier'] != 'high'


@pytest.mark.parametrize(('stat', 'lo', 'hi'), [(0, 10, 15), (3, 10, 15), (16, 140, 170), (45, 40, 70)])
def test_trek_all_variable_rolls_must_be_known_and_legal(stat, lo, hi):
    base = item()
    for value in (None, lo - 1, hi + 1):
        raw = tuple((s, p, value if s == stat else v) for s, p, v in base.raw_stats if s != stat or value is not None)
        facts = normalize(replace(base, raw_stats=raw).capture())
        assert assess_trade_qualification(facts)['status'] == 'unresolved'
        assert assess_tier(facts)['tier'] is None


@pytest.mark.parametrize(
    'changes', [{'identified': False}, {'sockets': 1}, {'sockets': None}, {'socket_contents': 'unknown'}]
)
def test_trek_unknown_or_impossible_variant_remains_unresolved(changes):
    assert assess_trade_qualification(replace(normalize(item().capture()), **changes))['status'] == 'unresolved'
