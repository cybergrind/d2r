import pytest

from pricing.knowledge.market import normalize_listing
from tests.pricing.knowledge.test_market import listing


def normalized(name, category, additions=()):
    raw = listing()
    raw['properties'] = [p for p in raw['properties'] if p['property_id'] not in (402, 738, 797, 934)] + list(additions)
    return normalize_listing(raw, name=name, category=category, source='fixture')


def test_named_set_equipment_is_nonethereal_but_socketable_helm_stays_unknown():
    row = normalized("Sazabi's Mental Sheath", 'sets')
    assert row['ethereal'] is False
    assert row.get('sockets') is None
    assert row['socket_contents'] == 'unknown'
    assert '738' not in row['properties']
    assert row['facet_basis']['ethereal']['kind'] == 'set_quality_mechanics'


@pytest.mark.parametrize('name', ['War Traveler', 'Bloodfist', 'Goldwrap'])
def test_named_gloves_boots_belts_cannot_have_sockets_but_can_be_ethereal(name):
    row = normalized(name, 'uniques')
    assert row['sockets'] == 0
    assert row['socket_contents'] == 'empty'
    assert row.get('ethereal') is None
    assert '402' not in row['properties']


def test_set_boots_combine_only_proven_facts():
    row = normalized("Aldur's Advance", 'sets')
    assert row['ethereal'] is False
    assert row['sockets'] == 0
    assert row['socket_contents'] == 'empty'
    assert 'base_code' not in row  # Battle/Mirrored Boots remain distinct.


@pytest.mark.parametrize(
    ('name', 'category', 'key', 'kind', 'value'),
    [
        ("Aldur's Advance", 'sets', 738, 'bool', True),
        ('War Traveler', 'uniques', 402, 'number', 1),
        ('Bloodfist', 'uniques', 934, 'string', 'Jewel'),
    ],
)
def test_impossible_seller_facets_are_preserved_and_rejected(name, category, key, kind, value):
    row = normalized(name, category, [{'property_id': key, 'type': kind, kind: value}])
    assert row['properties'][str(key)] == value
    assert row['mechanics_conflicts']


def test_unknown_set_name_does_not_gain_inferred_facets():
    row = normalized('Unknown Set Armor', 'sets')
    assert row.get('ethereal') is None
    assert row.get('sockets') is None
