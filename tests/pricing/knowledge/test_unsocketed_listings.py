from datetime import date

import pytest

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from pricing.knowledge.market import normalize_listing
from tests.pricing.knowledge.assessment.test_comparables import contract
from tests.pricing.knowledge.test_market import listing


def normalized(count, contents='omitted', seller='1'):
    raw = listing(id=seller, seller_id=seller)
    raw['properties'] = [p for p in raw['properties'] if p['property_id'] != 402]
    if count is not None:
        raw['properties'].append(
            {
                'property_id': 402,
                'type': 'bool' if type(count) is bool else 'number',
                'bool' if type(count) is bool else 'number': count,
            }
        )
    if contents != 'omitted':
        raw['properties'].append({'property_id': 934, 'type': 'string', 'string': contents})
    return normalize_listing(
        raw, name='Cinquedeas', category='base', source='fixture', observed_at='2026-09-24', currencies={'ist': 1}
    )


@pytest.mark.parametrize('contents', ['omitted', None, ''])
def test_explicit_zero_sockets_establishes_empty_contents(contents):
    row = normalized(0, contents)
    assert row['socket_contents'] == 'empty'
    assert not row.get('mechanics_conflicts')
    if contents == 'omitted':
        assert '934' not in row['properties']
        assert row['facet_basis']['socket_contents']['kind'] == 'explicit_socket_count'


@pytest.mark.parametrize('count', [None, 1, 3, False, -1, 0.5])
def test_nonzero_missing_or_invalid_count_never_infers_empty_contents(count):
    assert normalized(count)['socket_contents'] == 'unknown'


def test_zero_sockets_with_listed_insert_is_preserved_and_rejected():
    row = normalized(0, 'Jewel')
    assert row['properties']['934'] == 'Jewel'
    assert row['socket_contents'] == 'filled'
    assert row['mechanics_conflicts']


def test_three_explicit_unsocketed_asks_reach_price_without_redundant_contents_field():
    expected = contract() | {'rarity': 'normal', 'sockets': 0, 'properties': {}}
    rows = [normalized(0, seller=str(i)) for i in range(3)]
    result = price_from_comparables(evaluate(expected, rows), today=date(2026, 9, 24))
    assert result['estimate_ist'] == 2
    assert result['sellers'] == 3


def test_null_contents_is_unknown_information_not_a_contradictory_insert():
    from pricing.knowledge.market_mechanics import apply_mechanics

    row = {'name': 'Heavy Gloves', 'category': 'base', 'properties': {'402': 0, '934': None}}
    apply_mechanics(row)
    assert row['socket_contents'] == 'empty'
    assert row['properties']['934'] is None
    assert not row.get('mechanics_conflicts')
