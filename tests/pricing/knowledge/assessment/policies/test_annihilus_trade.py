from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from pricing.knowledge.assessment.policies.trade_rolls import market_mapping, valid_market_compounds
from tests.pricing.knowledge.assessment.item_bank.models import Item


ATTRIBUTES = (0, 1, 2, 3)
RESISTANCES = (39, 41, 43, 45)


def item(attributes=20, resistance=20, experience=10):
    return Item(
        'Small Charm',
        'unique',
        'Annihilus',
        (
            (127, 0, 1),
            *((s, 0, attributes) for s in ATTRIBUTES),
            *((s, 0, resistance) for s in RESISTANCES),
            (85, 0, experience),
        ),
    )


@pytest.mark.parametrize(
    ('attributes', 'resistance', 'experience', 'status'),
    [
        (10, 10, 5, 'candidate'),
        (18, 20, 10, 'candidate'),
        (20, 18, 10, 'candidate'),
        (19, 19, 5, 'premium'),
        (20, 20, 9, 'premium'),
        (20, 20, 10, 'premium'),
    ],
)
def test_annihilus_attributes_and_resistance_both_gate_premium(attributes, resistance, experience, status):
    result = assess_trade_qualification(normalize(item(attributes, resistance, experience).capture()))
    assert result['status'] == status
    if (attributes, resistance, experience) == (20, 20, 10):
        assert result['reason'] == '19+ attributes and resistances: higher asking segment.'


@pytest.mark.parametrize('stat', [*ATTRIBUTES, *RESISTANCES])
def test_annihilus_mixed_members_cannot_claim_high_tier_or_trade(stat):
    specimen = item()
    raw = tuple((s, p, 19 if s == stat else v) for s, p, v in specimen.raw_stats)
    facts = normalize(replace(specimen, raw_stats=raw).capture())
    assert assess_trade_qualification(facts)['status'] == 'unresolved'
    assert assess_tier(facts)['tier'] is None


def test_two_independent_market_groups_have_separate_native_mappings():
    review = {
        'compound_stats': ['all_attributes', 'all_resistances'],
        'material_stats': [*(f'{s}:0' for s in (*ATTRIBUTES, *RESISTANCES)), '85:0'],
        'market_stat_properties': {'85:0': '776'},
    }
    assert market_mapping(review) == {
        **dict.fromkeys((f'{s}:0' for s in ATTRIBUTES), '727'),
        **dict.fromkeys((f'{s}:0' for s in RESISTANCES), '441'),
        '85:0': '776',
    }
    assert valid_market_compounds(review, {'727': 19, '441': 20, '776': 10})
    for scalar in ('437', '421', '429', '582', '427', '428', '426', '401'):
        assert not valid_market_compounds(review, {'727': 20, '441': 20, scalar: 20, '776': 10})
