from dataclasses import replace

import pytest

from inventory_tracking.appraisal.intrinsic_rolls import display_stats
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


def item(defense=166, mana=50):
    return Item('Troll Belt', 'set', "Trang-Oul's Girth", ((31, 0, defense), (9, 0, mana * 256)), complete=True)


@pytest.mark.parametrize(
    ('defense', 'mana', 'status'),
    [
        (134, 25, 'candidate'),
        (159, 49, 'candidate'),
        (134, 50, 'premium'),
        (166, 50, 'premium'),
        (100, 50, 'unresolved'),
        (133, 50, 'unresolved'),
        (167, 50, 'unresolved'),
    ],
)
def test_girth_uses_total_defense_and_decoded_mana(defense, mana, status):
    result = assess_trade_qualification(normalize(item(defense, mana).capture()))
    assert result['status'] == status
    assert 'price_estimate' not in result


@pytest.mark.parametrize(
    'changes',
    [
        {'complete': False},
        {'ethereal': True},
        {'ethereal': None},
        {'sockets': 1},
        {'sockets': None},
        {'socket_contents': 'unknown'},
        {'identified': False},
    ],
)
def test_girth_unverified_capture_or_variant_cannot_qualify(changes):
    assert assess_trade_qualification(normalize(replace(item(), **changes).capture()))['status'] == 'unresolved'


def test_girth_total_defense_range_is_displayed_without_claiming_exact_bonus_roll():
    rows = display_stats({'extraction': item().capture(), 'assessment': {}})
    row = next(r for r in rows if r.get('memory_stat', {}).get('id') == 31)
    assert row['text'] == 'Defense: 166 (134-166)'
    assert row['roll_quality'] == 'perfect'


@pytest.mark.parametrize('stat', [16, 214, 215])
def test_girth_other_defense_contributions_cannot_borrow_total_range(stat):
    specimen = replace(item(), raw_stats=(*item().raw_stats, (stat, 0, 1)))
    assert assess_trade_qualification(normalize(specimen.capture()))['status'] == 'unresolved'


@pytest.mark.parametrize('change', ['missing-total', 'conflicting-bonus', 'wrong-identity'])
def test_girth_market_evidence_requires_explicit_consistent_total_defense(change):
    import json

    from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies

    document = json.loads(RULES.read_bytes())
    review = next(r for r in document['policies'] if r['name'] == "Trang-Oul's Girth")['trade_qualification']
    row = review['market_evidence'][0]
    if change == 'missing-total':
        row['properties'].pop('1855')
    elif change == 'conflicting-bonus':
        row['properties']['399'] = row['properties']['1855']
    else:
        row['base_code'] = 'invalid-base'
    with pytest.raises(ValueError, match='Unverified trade evidence variant or material roll'):
        _policies(json.dumps(document).encode())


@pytest.mark.parametrize(('mana', 'tier'), [(24, None), (25, 'low'), (49, 'low'), (50, 'med'), (51, None)])
def test_girth_tier_uses_complete_total_defense_and_legal_mana(mana, tier):
    assert assess_tier(normalize(item(mana=mana).capture()))['tier'] == tier
