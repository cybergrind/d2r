from copy import deepcopy

import pytest

from pricing.knowledge.assessment.comparables import evaluate
from tests.pricing.knowledge.assessment.test_comparables import contract, listing


RESISTS = ('427', '428', '426', '401')


def affixed(properties):
    return contract() | {
        'policy': 'affixed',
        'name': 'Ring',
        'rarity': 'rare',
        'family': 'jewelry',
        'sockets': 0,
        'properties': properties,
    }


def ring(properties):
    return listing(name='Ring', rarity='rare', sockets=0, properties=properties)


@pytest.mark.parametrize('reverse', [False, True])
def test_all_resistance_and_four_equal_totals_compare_without_relaxing_rolls(reverse):
    combined, expanded = {'441': 10, '520': 10}, dict.fromkeys(RESISTS, 10) | {'520': 10}
    expected, observed = (expanded, combined) if reverse else (combined, expanded)
    before = deepcopy(observed)
    result = evaluate(affixed(expected), [ring(observed)])
    assert result['summary']['priced_sellers'] == 1
    assert observed == before
    for wrong in (expanded | {'427': 11}, expanded | {'429': 5}, {'441': 9, '520': 10}, {'441': 10}):
        assert evaluate(affixed(expected), [ring(wrong)])['summary']['priced_sellers'] == 0


@pytest.mark.parametrize(
    'properties',
    [
        {'441': 10, '427': 10},
        {'441': True},
        {'441': float('nan')},
        {'441': '10'},
    ],
)
def test_ambiguous_or_invalid_resistance_composition_is_never_a_match_even_to_itself(properties):
    assert evaluate(affixed(properties), [ring(properties)])['summary']['priced_sellers'] == 0


def test_intrinsic_named_resistance_uses_same_canonical_form_without_overwriting_observation():
    expected = affixed({'441': 10}) | {'policy': 'named', 'intrinsic_properties': {'441': 10}}
    assert evaluate(expected, [ring({})])['summary']['priced_sellers'] == 1
    assert evaluate(expected, [ring(dict.fromkeys(RESISTS, 10))])['summary']['priced_sellers'] == 1
    assert evaluate(expected, [ring({'427': 11})])['summary']['priced_sellers'] == 0


def test_equivalent_resistance_rows_can_reach_price_gate_without_merging_different_rolls():
    from datetime import date

    from pricing.knowledge.assessment.comparables import price_from_comparables

    expected = affixed(dict.fromkeys(RESISTS, 10) | {'520': 10})
    rows = [ring({'441': 10, '520': 10}) | {'seller_id': str(i), 'listing_id': str(i), 'ask_ist': i} for i in (1, 2, 3)]
    rows.append(ring({'441': 11, '520': 10}) | {'seller_id': 'premium', 'listing_id': 'premium', 'ask_ist': 20})
    comparisons = evaluate(expected, rows)
    price = price_from_comparables(comparisons, today=date(2026, 9, 24))
    assert price['estimate_ist'] == 2
    assert price['sellers'] == 3
    assert len(comparisons['rejected']) == 1
