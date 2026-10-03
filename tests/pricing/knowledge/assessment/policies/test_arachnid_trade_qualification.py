from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.named_baselines import assess_tier
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


def item(ed=120):
    raw = () if ed is None else ((16, 0, ed),)
    return Item('Spiderweb Sash', 'unique', 'Arachnid Mesh', raw)


@pytest.mark.parametrize('ed', [90, 109, 110, 119, 120])
def test_only_the_supported_perfect_segment_receives_a_premium_trade_label(ed):
    facts = normalize(item(ed).capture())
    result = assess_trade_qualification(facts)
    assert result['status'] == ('premium' if ed == 120 else 'unresolved')
    assert assess_tier(facts)['tier'] == ('high' if ed == 120 else 'med')
    assert 'price_estimate' not in result


@pytest.mark.parametrize('ed', [None, 89, 121])
def test_missing_or_impossible_ed_cannot_qualify(ed):
    facts = normalize(item(ed).capture())
    assert assess_trade_qualification(facts)['status'] == 'unresolved'
    assert assess_tier(facts)['tier'] != 'high'


@pytest.mark.parametrize(
    'changes',
    [
        {'ethereal': True},
        {'ethereal': None},
        {'identified': False},
        {'sockets': None},
        {'sockets': 1},
        {'socket_contents': 'unknown'},
        {'socket_contents': 'filled'},
    ],
)
def test_capture_variant_uncertainty_never_inherits_a_listing_inference(changes):
    facts = normalize(replace(item(), **changes).capture())
    assert assess_trade_qualification(facts)['status'] == 'unresolved'
    assert assess_tier(facts)['tier'] != 'high'


@pytest.mark.parametrize(
    'change', ['unknown-mode', 'no-proof', 'bonus-only', 'contradiction', 'bulk', 'ladder', 'thin', 'unsupported-lower']
)
def test_published_trade_evidence_must_prove_each_segment(change):
    import json

    from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies

    document = json.loads(RULES.read_bytes())
    policy = next(r for r in document['policies'] if r['name'] == 'Arachnid Mesh')
    review = policy['trade_qualification']
    row = review['market_evidence'][0]
    if change == 'unknown-mode':
        review['ethereal_inference'] = 'default_missing_false'
    elif change == 'no-proof':
        review.pop('ethereal_inference')
    elif change == 'bonus-only':
        row['properties']['399'] = row['properties'].pop('1855')
    elif change == 'contradiction':
        row['ethereal'] = True
    elif change == 'bulk':
        row['amount'] = 2
    elif change == 'ladder':
        row['properties']['800'] = True
    elif change == 'thin':
        for other in review['market_evidence']:
            other['seller_id'] = 'one seller'
    else:
        row['properties']['425'] = 119
        row['properties']['1855'] = 137
    with pytest.raises(ValueError, match=r'trade|Trade'):
        _policies(json.dumps(document).encode())


def test_conflicting_captured_base_cannot_inherit_the_named_trade_rule():
    facts = normalize(item().capture())
    wrong = replace(facts, base_name='Demonhide Sash', base_code='zlb')
    assert assess_trade_qualification(wrong)['status'] == 'unresolved'
    assert assess_tier(wrong)['tier'] != 'high'
