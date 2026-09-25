from dataclasses import replace
from datetime import date

import pytest

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables, reject_reasons
from pricing.knowledge.assessment.handlers import HANDLERS
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def charm(rate=205, frames=125, count=1):
    values = {
        57: (rate, rate / 256, 'damage_per_frame'),
        58: (rate, rate / 256, 'damage_per_frame'),
        59: (frames, frames / 25, 'seconds'),
        326: (count, count, 'count'),
    }
    return replace(
        facts('Small Charm', 'magic'),
        properties={},
        stats={
            f'{s}:0': {'status': 'decoded', 'raw': raw, 'value': value, 'unit': unit}
            for s, (raw, value, unit) in values.items()
        },
        projection_gaps=[f'No verified market mapping for native stat {s}:0.' for s in values],
    )


@pytest.mark.parametrize(('rate', 'frames', 'total'), [(205, 125, 100), (385, 300, 451)])
def test_unique_poison_total_can_compare_verified_rate_and_duration(rate, frames, total):
    contract, gaps = HANDLERS['affixed'].contract(charm(rate, frames), 'charm')
    assert contract is not None, gaps
    assert contract.properties == {'589': total}
    assert '589' not in contract.intrinsic_properties
    payload = contract.to_dict()
    rows = [
        {
            **payload,
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'observed_at': '2026-09-25',
            'ask_ist': 1,
        }
        for i in range(3)
    ]
    assert price_from_comparables(evaluate(payload, rows), today=date(2026, 9, 25))['estimate_ist'] == 1
    assert reject_reasons(payload, {**rows[0], 'properties': {'589': 50}})


@pytest.mark.parametrize('item', [charm(128, 100), charm(86, 150), charm(205, 125, 2), charm(204, 125)])
def test_equal_totals_different_durations_and_unverified_sources_are_rejected(item):
    assert HANDLERS['affixed'].contract(item, 'charm')[0] is None


def test_malformed_poison_is_rejected_without_relying_on_adapter_warnings():
    item = charm()
    changed = replace(
        item,
        projection_gaps=[],
        properties={'589': 100},
        stats={**item.stats, '59:0': {**item.stats['59:0'], 'value': 6}},
    )
    assert HANDLERS['affixed'].contract(changed, 'charm')[0] is None
    changed = replace(item, properties={'589': 99})
    assert HANDLERS['affixed'].contract(changed, 'charm')[0] is None


def test_ordinary_weapon_poison_is_not_blocked_by_another_bases_automods():
    poison = charm(rate=31, frames=50)
    item = replace(
        facts('Axe', 'rare'),
        stats={**poison.stats, **{f'{s}:0': {'status': 'decoded', 'value': 0} for s in (17, 18)}},
        properties={'510': 0},
        projection_gaps=poison.projection_gaps,
    )
    contract, gaps = HANDLERS['affixed'].contract(item, 'weapon')
    assert contract is not None, gaps
    assert contract.properties == {'510': 0, '589': 6}
