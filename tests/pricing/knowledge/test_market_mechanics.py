import pytest

from pricing.knowledge.market import normalize_listing
from tests.pricing.knowledge.test_market import listing


def normalize(name, category='misc', additions=()):
    raw = listing()
    raw['properties'] = [p for p in raw['properties'] if p['property_id'] not in (402, 738)] + list(additions)
    return normalize_listing(raw, name=name, category=category, source='fixture')


@pytest.mark.parametrize(
    ('name', 'category'),
    [
        ('Ring', 'misc'),
        ('Amulet', 'misc'),
        ('Grand Charm', 'charms'),
        ('Small Charm', 'charms'),
        ('Large Charm', 'charms'),
        ('Jewel', 'jewels'),
    ],
)
def test_nonsocketable_catalog_identity_provides_impossible_variant_facets(name, category):
    row = normalize(name, category)
    assert row['sockets'] == 0
    assert row['socket_contents'] == 'empty'
    assert row['ethereal'] is False
    assert row['facet_basis']['sockets']['kind'] == 'base_mechanics'
    assert '402' not in row['properties']  # Preserve what the seller actually supplied.
    assert row['observed_at'] is None


@pytest.mark.parametrize(
    ('name', 'category'),
    [('Monarch', 'base'), ('Ring', 'unknown'), ('Unknown Ring', 'misc'), ('Harlequin Crest', 'uniques')],
)
def test_other_catalogs_keep_unknown_facets(name, category):
    row = normalize(name, category)
    assert 'sockets' not in row
    assert 'ethereal' not in row
    assert row['socket_contents'] == 'unknown'


@pytest.mark.parametrize(
    ('key', 'kind', 'value'),
    [(402, 'number', 1), (738, 'bool', True), (402, 'string', 'bad'), (934, 'string', 'Jewel')],
)
def test_explicit_contradictions_are_not_overwritten_by_mechanics(key, kind, value):
    row = normalize('Ring', additions=[{'property_id': key, 'type': kind, kind: value}])
    assert row.get('mechanics_conflicts')
    assert row['properties'][str(key)] == value


def test_mechanics_cannot_promote_contradictory_listing_to_comparable():
    from pricing.knowledge.assessment.comparables import evaluate
    from tests.pricing.knowledge.assessment.test_comparables import contract

    row = normalize('Ring', additions=[{'property_id': 738, 'type': 'bool', 'bool': True}])
    expected = contract() | {'name': 'Ring', 'ethereal': True, 'sockets': 0, 'rarity': 'normal', 'properties': {}}
    assert evaluate(expected, [row])['summary']['priced_sellers'] == 0


def test_dated_magic_amulet_can_reach_exact_price_path_without_impossible_flags():
    from datetime import date

    from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
    from tests.pricing.knowledge.assessment.test_comparables import contract

    rows = []
    for seller in ('1', '2', '3'):
        raw = listing(id=seller, seller_id=seller)
        raw['properties'] = [p for p in raw['properties'] if p['property_id'] not in (402, 738, 797)]
        raw['properties'] += [
            {'property_id': 797, 'type': 'string', 'string': 'magic'},
            {'property_id': 520, 'type': 'number', 'number': 10},
        ]
        rows.append(
            normalize_listing(
                raw, name='Amulet', category='misc', source='fixture', observed_at='2026-09-24', currencies={'ist': 1}
            )
        )
    expected = contract() | {
        'policy': 'affixed',
        'name': 'Amulet',
        'family': 'jewelry',
        'rarity': 'magic',
        'sockets': 0,
        'properties': {'520': 10},
    }
    result = price_from_comparables(evaluate(expected, rows), today=date(2026, 9, 24))
    assert result['estimate_ist'] == 2
