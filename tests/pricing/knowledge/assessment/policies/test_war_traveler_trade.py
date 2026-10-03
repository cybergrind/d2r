"""Perfect MF is a reviewed candidate; unreviewed lower rolls are not worthless."""

from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


def item(mf=50, ed=174, thorns=6):
    return Item('Battle Boots', 'unique', 'War Traveler', ((80, 0, mf), (16, 0, ed), (78, 0, thorns)))


@pytest.mark.parametrize('ed', [150, 174, 190])
def test_perfect_mf_candidate_does_not_require_perfect_defense(ed):
    result = assess_trade_qualification(normalize(item(ed=ed).capture()))
    assert result['status'] == 'candidate'
    assert result['material_stats'] == ['80:0', '16:0', '78:0']


@pytest.mark.parametrize('mf', [30, 44, 45, 49])
def test_lower_mf_is_unreviewed_not_use_only_or_worthless(mf):
    assert assess_trade_qualification(normalize(item(mf=mf).capture()))['status'] == 'unresolved'


@pytest.mark.parametrize(
    'changes',
    [
        {'ethereal': True},
        {'ethereal': None},
        {'sockets': None},
        {'sockets': 1},
        {'socket_contents': 'unknown'},
        {'identified': False},
        {'stats': {}},
    ],
)
def test_unknown_or_different_variants_do_not_inherit_fifty_mf_trade_interest(changes):
    assert assess_trade_qualification(replace(normalize(item().capture()), **changes)).get('status') != 'candidate'


@pytest.mark.parametrize(('mf', 'ed', 'thorns'), [(51, 174, 6), (50, 149, 6), (50, 191, 6), (50, 174, 4)])
def test_material_rolls_must_be_legal(mf, ed, thorns):
    assert assess_trade_qualification(normalize(item(mf, ed, thorns).capture())).get('status') != 'candidate'
