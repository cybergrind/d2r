from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


def item(ar=449, defense=350, resistance=35):
    return Item(
        'Amulet',
        'unique',
        'Metalgrid',
        ((19, 0, ar), (31, 0, defense), *((s, 0, resistance) for s in (39, 41, 43, 45))),
    )


@pytest.mark.parametrize(
    ('ar', 'resistance', 'status'),
    [(400, 25, 'candidate'), (449, 35, 'candidate'), (450, 34, 'candidate'), (450, 35, 'candidate')],
)
def test_metalgrid_supported_ordinary_segment_does_not_invent_collector_premium(ar, resistance, status):
    result = assess_trade_qualification(normalize(item(ar=ar, resistance=resistance).capture()))
    assert result['status'] == status
    assert 'price_estimate' not in result


@pytest.mark.parametrize('stat', [19, 31, 39, 41, 43, 45])
def test_metalgrid_every_material_component_is_required(stat):
    base = item()
    raw = tuple(r for r in base.raw_stats if r[0] != stat)
    assert assess_trade_qualification(normalize(replace(base, raw_stats=raw).capture()))['status'] == 'unresolved'


@pytest.mark.parametrize('stat', [39, 41, 43, 45])
def test_metalgrid_unequal_resistance_components_cannot_inherit_a_tier(stat):
    base = item()
    raw = tuple((s, p, 34 if s == stat else v) for s, p, v in base.raw_stats)
    facts = normalize(replace(base, raw_stats=raw).capture())
    assert assess_trade_qualification(facts)['status'] == 'unresolved'
    assert assess_tier(facts)['tier'] is None
