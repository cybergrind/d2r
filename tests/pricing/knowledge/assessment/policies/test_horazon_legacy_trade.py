from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


ITEM = Item(
    'Mirrored Boots', 'set', "Horazon's Legacy", ((31, 0, 68), (0, 0, 15), (2, 0, 15), (37, 0, 30)), complete=True
)


@pytest.mark.parametrize('values', [(59, 10, 10, 20), (68, 15, 15, 30), (64, 13, 14, 27)])
def test_horazon_complete_legal_rolls_are_ordinary_candidates(values):
    raw = tuple((s, p, v) for (s, p, _), v in zip(ITEM.raw_stats, values, strict=True))
    assert assess_trade_qualification(normalize(replace(ITEM, raw_stats=raw).capture()))['status'] == 'candidate'


@pytest.mark.parametrize(
    ('stat', 'values'), [(31, (None, 58, 69, 368)), (0, (None, 9, 16)), (2, (None, 9, 16, 35)), (37, (None, 19, 31))]
)
def test_horazon_requires_legal_native_defense_and_each_variable_affix(stat, values):
    for value in values:
        raw = tuple((s, p, value if s == stat else v) for s, p, v in ITEM.raw_stats if s != stat or value is not None)
        assert assess_trade_qualification(normalize(replace(ITEM, raw_stats=raw).capture()))['status'] == 'unresolved'


@pytest.mark.parametrize('changes', [{'complete': False}, {'ethereal': True}, {'sockets': 1}])
def test_horazon_cannot_borrow_incomplete_or_other_variant(changes):
    assert assess_trade_qualification(normalize(replace(ITEM, **changes).capture()))['status'] == 'unresolved'


def test_horazon_cannot_borrow_a_different_boot_base():
    other = normalize(Item('Battle Boots', 'normal').capture()).base_code
    facts = replace(normalize(ITEM.capture()), base_code=other)
    assert assess_trade_qualification(facts)['status'] == 'unresolved'


@pytest.mark.parametrize('stat', [16, 214, 215])
def test_horazon_additional_defense_contribution_cannot_borrow_plain_base_range(stat):
    specimen = replace(ITEM, raw_stats=(*ITEM.raw_stats, (stat, 0, 1)))
    assert assess_trade_qualification(normalize(specimen.capture()))['status'] == 'unresolved'


def test_horazon_conditional_walk_speed_does_not_change_trade_qualification():
    specimen = replace(ITEM, raw_stats=(*ITEM.raw_stats, (96, 0, 40)))
    assert assess_trade_qualification(normalize(specimen.capture()))['status'] == 'candidate'


def test_trade_defense_gap_does_not_erase_the_independent_named_tier():
    from pricing.knowledge.assessment.policies.named_tiers import assess_tier

    facts = normalize(replace(ITEM, raw_stats=(), complete=False).capture())
    assert assess_tier(facts)['tier'] == 'low'
    assert assess_trade_qualification(facts)['status'] == 'unresolved'


@pytest.mark.parametrize('change', ['missing-total', 'flat-bonus', 'enhanced-defense', 'wrong-base', 'wrong-mode'])
def test_horazon_market_requires_explicit_unmodified_total_defense(change):
    import json

    from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies

    document = json.loads(RULES.read_bytes())
    review = next(p for p in document['policies'] if p['name'] == "Horazon's Legacy")['trade_qualification']
    row = review['market_evidence'][0]
    if change == 'missing-total':
        row['properties'].pop('1855')
    if change == 'flat-bonus':
        row['properties']['399'] = row['properties']['1855']
    if change == 'enhanced-defense':
        row['properties']['425'] = 1
    if change == 'wrong-base':
        row['base_code'] = 'unverified'
    if change == 'wrong-mode':
        review['base_defense'] = 'unverified'
    with pytest.raises(ValueError, match=r'base-defense|trade evidence'):
        _policies(json.dumps(document).encode())
