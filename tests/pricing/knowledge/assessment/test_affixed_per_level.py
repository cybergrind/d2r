from dataclasses import replace
from datetime import date

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables, reject_reasons
from pricing.knowledge.assessment.handlers import HANDLERS
from pricing.knowledge.assessment.maintenance.replay import replay
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def weapon(level=91):
    return replace(
        facts('Long Sword', 'rare'),
        properties={'510': 0},
        stats={
            **{f'{s}:0': {'status': 'decoded', 'value': 0} for s in (17, 18)},
            **{
                f'{s}:0': {
                    'status': 'decoded',
                    'raw': raw,
                    'value': raw * level // divisor,
                    'viewer_level': level,
                    'per_level': {'numerator': raw, 'denominator': divisor},
                }
                for s, raw, divisor in ((218, 4, 8), (224, 33, 2))
            },
        },
        projection_gaps=[f'No verified market mapping for native stat {s}:0.' for s in (218, 224)],
    )


def test_fractional_coefficients_compare_independently_of_viewer_level():
    contract, gaps = HANDLERS['affixed'].contract(weapon(), 'weapon')
    assert contract is not None, gaps
    assert contract.properties == {'510': 0, '535': 0.5, '536': 16.5}
    other, gaps = HANDLERS['affixed'].contract(weapon(20), 'weapon')
    assert other is not None, gaps
    assert other.properties == contract.properties
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
            'ask_ist': 2,
        }
        for i in range(3)
    ]
    assert price_from_comparables(evaluate(payload, rows), today=date(2026, 9, 25))['estimate_ist'] == 2
    assert reject_reasons(payload, {**rows[0], 'properties': {'510': 0, '535': 45, '536': 1501}})
    assert reject_reasons(payload, {**rows[0], 'properties': {'510': 0, '535': 0.75, '536': 16.5}})


def test_bad_formula_or_conflicting_total_cannot_form_contract():
    item = weapon()
    for change in ({'raw': 5}, {'viewer_level': 0}, {'value': 46}, {'per_level': {'numerator': 4, 'denominator': 4}}):
        changed = replace(item, projection_gaps=[], stats={**item.stats, '218:0': {**item.stats['218:0'], **change}})
        assert HANDLERS['affixed'].contract(changed, 'weapon')[0] is None
    assert HANDLERS['affixed'].contract(replace(item, properties={'510': 0, '535': 45}), 'weapon')[0] is None


def test_saved_dread_edge_resolves_per_level_fields():
    result = replay('dread_edge')['assessment']
    assert 'No verified market mapping for native stat 218:0.' not in result['price_gaps']
    assert 'No verified market mapping for native stat 224:0.' not in result['price_gaps']
