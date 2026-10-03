from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


STATS = (39, 41, 43, 45)


def item(value):
    return Item('Amulet', 'unique', "Mara's Kaleidoscope", tuple((stat, 0, value) for stat in STATS))


@pytest.mark.parametrize(
    ('value', 'status'), [(20, 'unresolved'), (26, 'unresolved'), (27, 'candidate'), (29, 'candidate'), (30, 'premium')]
)
def test_mara_scoped_segments_do_not_call_low_evidence_rolls_worthless(value, status):
    result = assess_trade_qualification(normalize(item(value).capture()))
    assert result['status'] == status
    assert 'price_estimate' not in result
    if 27 <= value < 30:
        assert assess_tier(normalize(item(value).capture()))['tier'] == 'med'


@pytest.mark.parametrize('stat', STATS)
def test_mara_missing_or_unequal_resistance_never_inherits_premium(stat):
    base = item(30)
    for raw in (
        tuple(r for r in base.raw_stats if r[0] != stat),
        tuple((s, p, 29 if s == stat else v) for s, p, v in base.raw_stats),
    ):
        facts = normalize(replace(base, raw_stats=raw).capture())
        assert assess_trade_qualification(facts)['status'] == 'unresolved'
        assert assess_tier(facts)['tier'] is None


@pytest.mark.parametrize(
    'changes', [{'ethereal': True}, {'ethereal': None}, {'sockets': 1}, {'sockets': None}, {'identified': False}]
)
def test_mara_unverified_or_impossible_variant_remains_unresolved(changes):
    assert assess_trade_qualification(replace(normalize(item(30).capture()), **changes))['status'] == 'unresolved'


def test_mara_combined_and_individual_market_resistances_are_not_silently_merged():
    import json

    from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies

    document = json.loads(RULES.read_bytes())
    review = next(r for r in document['policies'] if r['name'] == "Mara's Kaleidoscope")['trade_qualification']
    review['market_evidence'][0]['properties']['427'] = 30
    with pytest.raises(ValueError, match='Ambiguous compound trade evidence'):
        _policies(json.dumps(document).encode())
