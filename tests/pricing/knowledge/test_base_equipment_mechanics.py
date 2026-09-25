import pytest

from pricing.knowledge.market_mechanics import apply_mechanics
from tests.pricing.knowledge.assessment.test_family_contracts import facts
from tests.pricing.knowledge.test_named_equipment_facts import normalized


@pytest.mark.parametrize('quality', ['normal', 'superior', 'magic', 'rare', 'crafted'])
@pytest.mark.parametrize('name', ['Heavy Gloves', 'Battle Boots', 'War Belt'])
def test_exact_base_catalog_name_supplies_zero_socket_facts_for_every_quality(name, quality):
    row = normalized(name, 'base', [{'property_id': 797, 'type': 'string', 'string': quality}])
    assert row['base_code'] == facts(name).base_code
    assert row['sockets'] == 0
    assert row['socket_contents'] == 'empty'
    assert row.get('ethereal') is None
    assert row['rarity'] == quality
    assert '402' not in row['properties']


def test_socketable_base_has_identity_but_keeps_socket_and_ethereal_unknowns():
    row = normalized('Monarch', 'base')
    assert row['base_code'] == facts('Monarch').base_code
    assert row.get('sockets') is None
    assert row['socket_contents'] == 'unknown'
    assert row.get('ethereal') is None


@pytest.mark.parametrize(('name', 'category'), [('Rare Boots', 'base'), ('Heavy Gloves', 'misc')])
def test_generic_name_or_wrong_catalog_does_not_imply_a_specific_base(name, category):
    row = normalized(name, category)
    assert 'base_code' not in row
    assert row.get('sockets') is None


def test_contradictory_base_code_is_preserved_and_blocks_comparison():
    row = {'name': 'Heavy Gloves', 'category': 'base', 'properties': {}, 'base_code': 'unverified'}
    apply_mechanics(row)
    assert row['base_code'] == 'unverified'
    assert row['mechanics_conflicts']
