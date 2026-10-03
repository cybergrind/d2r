"""Perfect life-leech interest does not make lower rolls worthless or every roll premium."""

from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


def gloves(leech=10, strength=14, ed=110, heal=6):
    return Item(
        'Vampirebone Gloves',
        'unique',
        "Dracul's Grasp",
        (
            (31, 0, 66 * (100 + ed) // 100),
            (16, 0, ed),
            (60, 0, leech),
            (0, 0, strength),
            (86, 0, heal),
            (135, 0, 25),
            (198, (82 << 6) | 10, 5),
        ),
        complete=True,
    )


@pytest.mark.parametrize(('leech', 'status'), [(7, 'unresolved'), (9, 'unresolved'), (10, 'candidate')])
def test_leech_band_is_separate_from_fixed_life_tap_usefulness(leech, status):
    result = assess_trade_qualification(normalize(gloves(leech).capture()))
    assert result['status'] == status
    assert 'price_estimate' not in result


@pytest.mark.parametrize(('strength', 'ed', 'heal'), [(10, 90, 5), (15, 120, 10)])
def test_other_legal_rolls_do_not_claim_or_require_a_perfect_item(strength, ed, heal):
    result = assess_trade_qualification(normalize(gloves(strength=strength, ed=ed, heal=heal).capture()))
    assert result['status'] == 'candidate'
    assert '10%' in result['reason']


@pytest.mark.parametrize('key', [0, 16, 60, 86])
def test_each_material_roll_must_be_captured(key):
    item = gloves()
    item = replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != key))
    assert assess_trade_qualification(normalize(item.capture())).get('status') != 'candidate'


@pytest.mark.parametrize(
    'changes',
    [
        {'ethereal': True},
        {'ethereal': None},
        {'sockets': None},
        {'sockets': 1},
        {'socket_contents': 'unknown'},
        {'identified': False},
    ],
)
def test_unknown_or_wrong_variant_does_not_inherit_trade_interest(changes):
    assert assess_trade_qualification(normalize(replace(gloves(), **changes).capture())).get('status') != 'candidate'
