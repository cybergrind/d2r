from pricing.triage.adapters import from_listing
from pricing.triage.engine import assess
from pricing.triage.import_affixed_rules import affixed_rules
from tests.pricing.knowledge.test_crafted_market import crafted


def test_verified_craft_recipe_routes_family_without_inventing_base():
    row = crafted('Blood Gloves')
    row['properties'].update({'462': 3, '567': 10, '418': 20, '457': 20})
    item = from_listing(row)
    assert item['family'] == 'glov'
    assert item['base_code'] is None
    assert item['base_name'] is None
    tables = {'bands': {}, 'rules': {'rows': affixed_rules(), 'keep_ist': 0.25}, 'own': {'rows': []}}
    assert assess(item, tables)['verdict'] == 'check'
    assert from_listing(crafted('Blood Gloves', item_id='unverified'))['family'] is None


def test_unresolved_crafted_weapon_recipe_does_not_guess_family():
    assert from_listing(crafted('Safety Weapon'))['family'] is None
