from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers import HANDLERS
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('value', [float('inf'), float('-inf'), float('nan'), True])
def test_invalid_defense_cannot_make_a_base_comparison_contract(value):
    item = replace(facts('Mage Plate'), stats={'31:0': {'status': 'decoded', 'value': value}})
    contract, gaps = HANDLERS['base'].contract(item, 'armor')
    assert contract is None
    assert gaps


@pytest.mark.parametrize('value', [float('inf'), float('-inf'), float('nan')])
def test_nonfinite_affix_cannot_make_a_comparison_contract(value):
    item = replace(facts('Ring', 'rare'), properties={'105': value})
    contract, gaps = HANDLERS['affixed'].contract(item, 'jewelry')
    assert contract is None
    assert any('finite' in gap.lower() for gap in gaps)


def test_nonfinite_named_projection_is_rejected_before_contract():
    item = replace(
        facts('Heavy Gloves', 'unique', 'Bloodfist'),
        stats={'16:0': {'status': 'decoded', 'value': 15}, '31:0': {'status': 'decoded', 'value': 20}},
        properties={'510': float('inf')},
    )
    contract, gaps = HANDLERS['named'].contract(item, 'accessory')
    assert contract is None
    assert any('finite' in gap.lower() for gap in gaps)


def test_legacy_contract_with_infinite_modifiers_cannot_publish_a_price():
    from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
    from tests.pricing.knowledge.assessment.test_comparables import contract, listing

    corrupted = {**contract(), 'properties': {'510': float('inf')}}
    rows = [listing(str(i), properties={'510': float('inf')}) for i in range(3)]
    compared = evaluate(corrupted, rows)
    assert len(compared['rejected']) == 3
    assert price_from_comparables(compared)['estimate_ist'] is None
