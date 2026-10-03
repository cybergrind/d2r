import pytest

from inventory_tracking.items.metadata import metadata
from pricing.triage.adapters import from_drop


def observation(code, **fields):
    return {
        'item': {'name': 'Example', 'base_code': code, 'rarity': 'unique', 'affixes': [], **fields},
        'source': {},
        'decoded_stats': [],
    }


def test_old_jewelry_capture_uses_verified_nonsocketable_nonethereal_mechanics():
    item = from_drop(observation('rin'))
    assert item['ethereal'] is False
    assert item['sockets'] == 0
    assert item['socket_contents'] == 'empty'


def test_missing_armor_flags_are_not_inferred_from_no_listed_ethereal_sellers():
    item = from_drop(observation('uap'))
    assert item['ethereal'] is None
    assert item['sockets'] is None
    assert item['socket_contents'] is None


def test_explicit_capture_flags_are_not_silently_overwritten():
    item = from_drop(observation('rin', ethereal=True, sockets=1, socket_contents='filled'))
    assert item['ethereal'] is True
    assert item['sockets'] == 1
    assert item['socket_contents'] == 'filled'


@pytest.mark.parametrize('family', ['boot', 'glov', 'belt'])
def test_nonsocketable_equipment_recovers_socket_facts_without_inventing_ethereal(family):
    base = next(b for b in metadata()['bases'].values() if b['type'] == family)
    item = from_drop(observation(base['code']))
    assert base['max_sockets'] == 0
    assert item['sockets'] == 0
    assert item['socket_contents'] == 'empty'
    assert item['ethereal'] is None


def test_nonsocketable_equipment_does_not_hide_conflicting_capture():
    base = next(b for b in metadata()['bases'].values() if b['type'] == 'boot')
    item = from_drop(observation(base['code'], sockets=1, socket_contents='filled'))
    assert item['sockets'] == 1
    assert item['socket_contents'] == 'filled'


@pytest.mark.parametrize(('quantity', 'verdict'), [(1, 'check'), (15, 'slow'), (32, 'slow')])
def test_captured_gem_quantity_reaches_supported_sale_lot(quantity, verdict):
    from pricing.triage.engine import assess

    base = next(b for b in metadata()['bases'].values() if b['name'] == 'Perfect Ruby')
    captured = observation(base['code'], name=base['name'], rarity='normal', quantity=quantity)
    item = from_drop(captured)
    band = {'q1_ist': 0.05, 'quantity': 15, 'sellers': 3, 'liquidity': 'thin', 'observed_at': '2026-10-03'}
    tables = {
        'rules': {'rows': [], 'keep_ist': 0.25},
        'own': {'rows': []},
        'bands': {('gems', 'perfect ruby', 'quantity:15'): band},
    }
    result = assess(item, tables)
    assert item['quantity'] == quantity
    assert result['verdict'] == verdict
    if quantity > 1:
        assert result['decision_ist'] == 0.75


def test_weapon_quantity_is_not_a_sale_lot():
    base = next(b for b in metadata()['bases'].values() if b['type'] == 'jave')
    item = from_drop(observation(base['code'], rarity='magic', quantity=120))
    assert item['quantity'] == 1
