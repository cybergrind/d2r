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


def test_exact_base_name_supplies_native_shield_metadata_when_code_is_absent():
    from inventory_tracking.items.metadata import metadata

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Sacred Rondache')
    row = listing(1) | {'name': base['name'], 'category': 'base', 'rarity': 'normal', 'sockets': 4}
    row['properties'].update({'510': 65, '423': 121, '399': 150})
    item = from_listing(row)
    assert item['base_code'] == base['code']
    assert item['base_ed'] == 0
    assert item['base_modifiers'] == {'510': 65, '423': 121}
    # Do not use a named unique's display title or repair an explicit unknown code.
    assert from_listing(row | {'base_code': 'unverified'})['base_code'] == 'unverified'
    assert from_listing(row | {'name': 'Unknown Shield'})['base_code'] is None
    assert from_listing(row | {'name': 'HoZ', 'category': 'uniques', 'rarity': 'unique'})['base_code'] is None
    assert from_listing(row | {'base_name': 'Sacred Targe'})['base_code'] is None
    duplicates = [b for b in metadata()['bases'].values() if b['name'] == 'Ancient Shield']
    assert len(duplicates) > 1
    assert from_listing(row | {'name': 'Ancient Shield'})['base_code'] is None
