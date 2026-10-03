from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


def item(mf=40, gold=160, discount=15):
    return Item('Grand Charm', 'unique', "Gheed's Fortune", ((80, 0, mf), (79, 0, gold), (87, 0, discount)))


@pytest.mark.parametrize(
    ('mf', 'gold', 'discount', 'status'),
    [
        (20, 80, 10, 'candidate'),
        (38, 160, 15, 'candidate'),
        (39, 160, 15, 'candidate'),
        (40, 80, 10, 'premium'),
        (40, 160, 15, 'premium'),
    ],
)
def test_gheed_reviewed_mf_segment_requires_all_three_legal_rolls(mf, gold, discount, status):
    facts = normalize(item(mf, gold, discount).capture())
    result = assess_trade_qualification(facts)
    assert result['status'] == status
    assert result['material_stats'] == ['80:0', '79:0', '87:0']
    assert assess_tier(facts)['tier'] == ('high' if status == 'premium' else 'med')
    assert 'price_estimate' not in result


@pytest.mark.parametrize(('key', 'lo', 'hi'), [(80, 20, 40), (79, 80, 160), (87, 10, 15)])
def test_gheed_missing_or_impossible_rolls_cannot_qualify(key, lo, hi):
    base = item()
    for value in (None, lo - 1, hi + 1):
        raw = tuple((s, p, value if s == key else v) for s, p, v in base.raw_stats if s != key or value is not None)
        facts = normalize(replace(base, raw_stats=raw).capture())
        assert assess_trade_qualification(facts)['status'] == 'unresolved'
        assert assess_tier(facts)['tier'] is None


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
def test_gheed_unknown_or_illegal_variants_stay_unresolved(changes):
    assert assess_trade_qualification(replace(normalize(item().capture()), **changes))['status'] == 'unresolved'
