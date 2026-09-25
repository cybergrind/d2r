import pytest

from tests.pricing.knowledge.test_named_equipment_facts import normalized


@pytest.mark.parametrize(
    ('name', 'category'),
    [
        ("Titan's Revenge", 'uniques'),
        ('Thunderstroke', 'uniques'),
        ('Warshrike', 'uniques'),
        ('Lacerator', 'uniques'),
        ('Wraith Flight', 'uniques'),
        ('Matriarchal Javelin', 'base'),
        ('Winged Knife', 'base'),
        ('Winged Axe', 'base'),
        ('Ghost Glaive', 'base'),
    ],
)
def test_throwing_weapons_have_zero_sockets_without_listing_default(name, category):
    row = normalized(name, category)
    assert row['sockets'] == 0
    assert row['socket_contents'] == 'empty'
    assert '402' not in row['properties']
    assert '934' not in row['properties']
    if name != 'Wraith Flight':
        assert row.get('ethereal') is None


def test_explicit_socket_claim_conflicts_instead_of_being_silently_overwritten():
    row = normalized(
        'Thunderstroke',
        'uniques',
        [
            {'property_id': 402, 'type': 'number', 'number': 1},
            {'property_id': 934, 'type': 'string', 'string': 'Jewel'},
        ],
    )
    assert row['sockets'] == 1
    assert row['socket_contents'] == 'filled'
    assert row['mechanics_conflicts']


@pytest.mark.parametrize('name', ['Matriarchal Spear', 'Berserker Axe', 'Legend Spike'])
def test_nearby_socketable_weapon_families_stay_unknown(name):
    row = normalized(name, 'base')
    assert row.get('sockets') is None
    assert row['socket_contents'] == 'unknown'
