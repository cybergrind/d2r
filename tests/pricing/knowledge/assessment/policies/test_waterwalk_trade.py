from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.cases.waterwalk_defense import ITEM


def assess(item):
    return assess_trade_qualification(normalize(item.capture()))


def test_observed_upgraded_cohort_is_candidate_without_claiming_premium():
    result = assess(ITEM)
    assert result['status'] == 'candidate'
    assert '65 life' in result['reason']
    assert '198 defense' in result['reason']


@pytest.mark.parametrize(('stat', 'value'), [(7, 64 * 256), (16, 209), (31, 195), (31, 201)])
def test_unreviewed_rolls_are_unresolved_not_worthless(stat, value):
    item = replace(ITEM, raw_stats=tuple((s, p, value if s == stat else v) for s, p, v in ITEM.raw_stats))
    assert assess(item)['status'] == 'unresolved'


@pytest.mark.parametrize('stat', [7, 16, 31])
def test_missing_material_roll_cannot_qualify(stat):
    item = replace(ITEM, raw_stats=tuple(r for r in ITEM.raw_stats if r[0] != stat), complete=False)
    assert assess(item)['status'] == 'unresolved'


@pytest.mark.parametrize(
    'changes', [{'base': 'Sharkskin Boots'}, {'ethereal': True}, {'sockets': 1}, {'identified': False}]
)
def test_other_variants_do_not_inherit_the_cohort(changes):
    assert assess(replace(ITEM, **changes))['status'] == 'unresolved'


@pytest.mark.parametrize('life', [45, 51, 64, 65])
@pytest.mark.parametrize('ed', [180, 209, 210])
def test_original_boots_retain_ordinary_interest_below_perfect_rolls(life, ed):
    values = {7: life * 256, 16: ed, 31: 40 * (100 + ed) // 100}
    item = replace(
        ITEM, base='Sharkskin Boots', raw_stats=tuple((s, p, values.get(s, v)) for s, p, v in ITEM.raw_stats)
    )
    result = assess(item)
    assert result['status'] == 'candidate'
    assert 'Original boots' in result['reason']
    assert 'below perfect life' in result['reason']
