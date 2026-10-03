from pricing.triage.adapters import from_listing
from pricing.triage.replay import listing_score
from tests.pricing.triage.test_bands import listing


def test_known_base_name_resolves_family_without_a_listing_type_field():
    row = listing(1)
    row.update(name='Small Charm', category='charms', rarity='magic')
    item = from_listing(row)
    assert item['family'] == 'scha'
    assert item['category'] == 'magic'


def test_listing_score_groups_rare_equipment_by_actual_quality():
    row = listing(1)
    row.update(name='Archon Plate', category='base', rarity='rare')
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': []}, 'own': {'rows': []}}
    result = listing_score([row], tables)
    assert result['categories']['rare']['valuable'] == 1
    assert 'base' not in result['categories']


def test_unknown_name_does_not_get_a_guessed_family():
    assert from_listing(listing(1))['family'] is None
