import pytest

from pricing.knowledge.market import normalize_listing
from pricing.knowledge.market_mechanics import apply_mechanics
from tests.pricing.knowledge.test_market import listing


@pytest.mark.parametrize(
    ('name', 'category', 'base'),
    [
        ('The Stone of Jordan', 'uniques', 'Ring'),
        ("Mara's Kaleidoscope", 'uniques', 'Amulet'),
        ('Annihilus', 'uniques', 'Small Charm'),
        ("Gheed's Fortune", 'uniques', 'Grand Charm'),
        ('Hellfire Torch', 'uniques', 'Large Charm'),
        ('Angelic Halo', 'sets', 'Ring'),
    ],
)
def test_named_non_equipment_uses_verified_base_and_impossible_variant_facts(name, category, base):
    from pricing.knowledge.assessment.handlers.definitions import named_definitions

    raw = listing()
    raw['properties'] = [p for p in raw['properties'] if p['property_id'] not in (402, 738, 797)]
    row = normalize_listing(raw, name=name, category=category, source='fixture')
    definition = named_definitions()[row['rarity'], name]
    assert definition['base_name'] == base
    assert row['base_code'] == definition['base_codes'][0]
    assert row['ethereal'] is False
    assert row['sockets'] == 0
    assert row['socket_contents'] == 'empty'
    assert row['facet_basis']['base_code']['generation']
    assert row['observed_at'] is None


@pytest.mark.parametrize('name', ['Shaftstop', 'The Oculus', 'Unknown Unique Ring'])
def test_upgradeable_named_equipment_or_unknown_identity_does_not_infer_original_base(name):
    row = {'name': name, 'category': 'uniques', 'properties': {}}
    apply_mechanics(row)
    assert 'base_code' not in row
    assert 'ethereal' not in row


def test_named_wrong_base_is_preserved_and_rejected_and_normalization_is_idempotent():
    row = {'name': 'The Stone of Jordan', 'category': 'uniques', 'base_code': 'wrong', 'properties': {}}
    apply_mechanics(row)
    assert row['base_code'] == 'wrong'
    assert row['mechanics_conflicts']
    before = list(row['mechanics_conflicts'])
    apply_mechanics(row)
    assert row['mechanics_conflicts'] == before
