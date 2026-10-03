from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.cases.caster_stormshield import RAW
from tests.pricing.knowledge.assessment.item_bank.models import Item


ITEM = Item('Monarch', 'unique', 'Stormshield', ((31, 0, 133), *RAW), complete=True, named_table_id=253)


@pytest.mark.parametrize('defense', [133, 140, 148])
def test_ordinary_defense_is_a_candidate_without_a_premium_claim(defense):
    item = replace(ITEM, raw_stats=((31, 0, defense), *RAW))
    result = assess_trade_qualification(normalize(item.capture()))
    assert result['status'] == 'candidate'
    assert result['assessment_scope'] == 'underlying_item'
    assert 'premium' not in result['reason'].lower()


@pytest.mark.parametrize(
    'changes',
    [
        {'identified': False},
        {'ethereal': True},
        {'ethereal': None},
        {'complete': False},
        {'sockets': None},
        {'sockets': 2},
        {'socket_contents': 'filled'},
        {'raw_stats': ((31, 0, 132), *RAW)},
        {'raw_stats': ((31, 0, 149), *RAW)},
        {'raw_stats': tuple(r for r in ITEM.raw_stats if r[0] != 36)},
        {'raw_stats': tuple(r for r in ITEM.raw_stats if r[0] != 214)},
    ],
)
def test_unverified_or_invalid_native_benefits_do_not_qualify(changes):
    assert assess_trade_qualification(normalize(replace(ITEM, **changes).capture()))['status'] == 'unresolved'


@pytest.mark.parametrize('contents', ['filled', 'unknown', None])
def test_insert_uncertainty_is_separate_from_underlying_item_value(contents):
    item = replace(ITEM, sockets=1, socket_contents=contents, raw_stats=((31, 0, 200), *RAW, (194, 0, 1)))
    result = assess_trade_qualification(normalize(item.capture()))
    assert result['status'] == 'candidate'
    assert result['reason'].endswith('Assess inserts separately.')


@pytest.mark.parametrize(
    'corruption', ['seller', 'scope', 'defense', 'bonus', 'unit', 'status', 'date', 'native', 'hardcore']
)
def test_review_requires_independent_scoped_native_evidence(corruption):
    import hashlib
    import json

    from pricing.knowledge.assessment.policies import stormshield_trade as policy

    review = json.loads(policy.RULES.read_bytes())
    guides = policy.GUIDES.read_bytes()
    rows = [json.loads(line) for line in policy.MARKET.read_bytes().splitlines()]
    selected = [r for r in rows if r['id'] in review['evidence_ids']]
    native = tuple(p.read_bytes() for p in policy.NATIVE)
    if corruption == 'native':
        native = (b'{}', *native[1:])
    elif corruption == 'hardcore':
        review['guide_variants']['/lightning-sorceress/variants/3']['name'] = 'Hardcore'
    elif corruption == 'seller':
        selected[0]['seller_id'] = selected[1]['seller_id']
    elif corruption == 'scope':
        selected[0]['properties']['800'] = True
    elif corruption == 'defense':
        selected[0]['properties']['1855'] = 148
    elif corruption == 'bonus':
        selected[0]['properties']['436'] = 151
    elif corruption == 'unit':
        selected[0]['amount'] = 2
    elif corruption == 'status':
        selected[0]['listing_status']['completed'] = True
    elif corruption == 'date':
        selected[0]['observed_at'] = 'not-a-date'
    market = b'\n'.join(json.dumps(r).encode() for r in rows)
    review['market_sha256'] = hashlib.sha256(market).hexdigest()
    with pytest.raises(ValueError, match=r'Stormshield|isoformat'):
        policy.validate(json.dumps(review).encode(), guides, market, native)
