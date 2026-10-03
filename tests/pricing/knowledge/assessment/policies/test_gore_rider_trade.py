"""Fixed combat utility can retain asking interest below a perfect defense roll."""

from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


def boots(ed=160):
    return Item('War Boots', 'unique', 'Gore Rider', ((31, 0, 54 * (100 + ed) // 100), (16, 0, ed)))


@pytest.mark.parametrize('ed', [160, 164, 182, 199, 200])
def test_original_low_defense_is_not_confused_with_low_combat_modifiers(ed):
    result = assess_trade_qualification(normalize(boots(ed).capture()))
    assert result['status'] == 'candidate'
    assert 'fixed' in result['reason']
    assert 'price_estimate' not in result


@pytest.mark.parametrize('ed', [159, 201])
def test_impossible_roll_does_not_qualify(ed):
    assert assess_trade_qualification(normalize(boots(ed).capture())).get('status') != 'candidate'


@pytest.mark.parametrize(
    'changes',
    [
        {'base': 'Myrmidon Greaves'},
        {'ethereal': True},
        {'ethereal': None},
        {'sockets': None},
        {'sockets': 1},
        {'socket_contents': 'unknown'},
        {'identified': False},
        {'raw_stats': ()},
    ],
)
def test_unknown_or_upgraded_variant_needs_its_own_review(changes):
    assert assess_trade_qualification(normalize(replace(boots(), **changes).capture())).get('status') != 'candidate'


@pytest.mark.parametrize('defense', [186, 195, 207, 213])
def test_upgraded_perfect_ed_does_not_require_perfect_rerolled_base(defense):
    item = replace(boots(200), base='Myrmidon Greaves', raw_stats=((31, 0, defense), (16, 0, 200)))
    result = assess_trade_qualification(normalize(item.capture()))
    assert result['status'] == 'candidate'
    assert '200%' in result['reason']
    assert 'base defense' in result['reason']


@pytest.mark.parametrize('ed', [160, 196, 199])
def test_lower_ed_upgraded_interest_is_unreviewed_not_inherited_from_original(ed):
    item = replace(boots(ed), base='Myrmidon Greaves', raw_stats=((31, 0, 71 * (100 + ed) // 100), (16, 0, ed)))
    result = assess_trade_qualification(normalize(item.capture()))
    assert result['status'] == 'unresolved'
    assert 'upgraded' in result['reason']
