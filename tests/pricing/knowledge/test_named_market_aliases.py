from copy import deepcopy

import pytest

from pricing.knowledge.market import normalize_facets, normalize_listing
from tests.pricing.knowledge.test_market import listing


@pytest.mark.parametrize(
    ('name', 'catalog_id'),
    [
        ('Flame Rift', '1363635173'),
        ('Crack of the Heavens', '849307965'),
        ('Cold Rupture', '21102838'),
        ('Rotting Fissure', '1283013862'),
        ('Bone Break', '374110750'),
        ('Black Cleft', '1731212580'),
    ],
)
def test_original_sunder_catalog_alias_resolves_named_mechanics(name, catalog_id):
    raw = listing(item_id=catalog_id)
    raw['properties'] = [p for p in raw['properties'] if p['property_id'] not in (797, 402, 738, 934)]
    row = normalize_listing(raw, name='The ' + name, category='uniques', source='fixture')
    assert row['name'] == name
    assert row['catalog_name'] == 'The ' + name
    assert row['rarity'] == 'unique'
    assert row['base_code']
    assert row['sockets'] == 0
    assert row['ethereal'] is False
    assert row['socket_contents'] == 'empty'
    assert row['facet_basis']['identity']['catalog_id'] == catalog_id
    once = deepcopy(row)
    normalize_facets(row)
    assert row == once
    # Changing the raw catalog identity must invalidate the derived alias facts.
    row['catalog_id'] = 'unknown'
    normalize_facets(row)
    assert row['name'] == 'The ' + name
    assert 'base_code' not in row


@pytest.mark.parametrize('name', ['Renewed Flame Rift', 'Latent Flame Rift', 'The Unverified Item'])
def test_aliases_never_strip_meaningful_variant_names(name):
    row = normalize_listing(listing(item_id='1363635173'), name=name, category='uniques', source='fixture')
    assert row['name'] == name
    assert row.get('catalog_name') is None


def test_alias_requires_both_reviewed_catalog_id_and_unique_category():
    for category, identity in [('uniques', 'unknown'), ('sets', '1363635173')]:
        row = normalize_listing(listing(item_id=identity), name='The Flame Rift', category=category, source='fixture')
        assert row['name'] == 'The Flame Rift'
        assert 'base_code' not in row
