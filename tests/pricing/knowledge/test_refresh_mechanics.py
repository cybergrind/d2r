import pytest

from pricing.knowledge.market import normalize_listing
from pricing.knowledge.refresh import reconcile_listing_properties
from tests.pricing.knowledge.test_market import listing


@pytest.mark.parametrize(('name', 'category', 'zero'), [('Annihilus', 'uniques', False), ('Cinquedeas', 'base', True)])
def test_publication_reconciliation_keeps_proven_empty_socket_contents(name, category, zero):
    raw = listing()
    raw['properties'] = [p for p in raw['properties'] if p['property_id'] not in (402, 797)]
    if zero:
        raw['properties'].append({'property_id': 402, 'type': 'number', 'number': 0})
    row = normalize_listing(raw, name=name, category=category, source='fixture')
    assert row['socket_contents'] == 'empty'
    original_properties = dict(row['properties'])
    reconcile_listing_properties(row)
    assert row['socket_contents'] == 'empty'
    assert row['properties'] == original_properties
    assert '934' not in row['properties']


def test_reconciliation_replaces_and_removes_old_explicit_variant_facets():
    raw = listing()
    row = normalize_listing(raw, name='Cinquedeas', category='base', source='fixture')
    row['raw_properties'] = [p for p in raw['properties'] if p['property_id'] not in (797, 402, 738)]
    row['raw_properties'].append({'property_id': 797, 'type': 'string', 'string': 'rare'})
    reconcile_listing_properties(row)
    assert row['rarity'] == 'rare'
    assert row.get('ethereal') is None
    assert row.get('sockets') is None
    assert row['socket_contents'] == 'unknown'


def test_reconciliation_drops_previous_runeword_base_when_selector_disappears():
    from inventory_tracking.items.metadata import metadata

    row = normalize_listing(listing(), name='Spirit', category='runewords', source='fixture')
    row['base_code'] = next(b['code'] for b in metadata()['bases'].values() if b['name'] == 'Monarch')
    row['base_selector_properties'] = ['12345']
    row['facet_basis'] = {'ethereal': {'kind': 'old'}}
    row['socket_contents_basis'] = 'identified_completed_recipe'
    reconcile_listing_properties(row)
    assert row.get('base_code') is None
    assert row.get('base_selector_properties') is None
    assert row.get('socket_contents_basis') is None
    assert row.get('facet_basis', {}).get('ethereal') is None


def test_crafted_reconciliation_is_idempotent_and_preserves_price_and_date_evidence():
    from copy import deepcopy

    from tests.pricing.knowledge.test_crafted_market import crafted

    row = crafted('Blood Amulet')
    row['observed_at'] = '2026-09-24T10:00:00+00:00'
    expected = deepcopy(row)
    reconcile_listing_properties(row)
    reconcile_listing_properties(row)
    assert row == expected
    row['raw_properties'].append({'property_id': 738, 'type': 'bool', 'bool': True})
    reconcile_listing_properties(row)
    assert row['mechanics_conflicts']
    row['raw_properties'][-1]['bool'] = False
    reconcile_listing_properties(row)
    assert not row.get('mechanics_conflicts')
    assert row['ethereal'] is False
    assert row['name'] == 'Amulet'
    assert row['catalog_name'] == 'Blood Amulet'
    assert row['observed_at'] == expected['observed_at']
    assert row['conversion'] == expected['conversion']
    assert row['ask_ist'] == expected['ask_ist']
