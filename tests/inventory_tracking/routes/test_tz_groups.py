"""The live active-zone choice follows the installed game table, not a rotation guess."""

from dataclasses import replace

from inventory_tracking.routes.tz_groups import installed_active_zones, match_active_zone
from inventory_tracking.routes.tz_routes import route_inventory


def test_installed_table_has_all_34_distinct_active_combinations():
    zones = installed_active_zones()
    assert len(zones) == 34
    assert len({zone.name for zone in zones}) == len(zones)
    assert len({zone.areas for zone in zones}) == len(zones)
    assert next(zone for zone in zones if zone.name == 'Act1-Tower').areas == (6, 11, 15, 20, 21, 22, 23, 24, 25)
    assert next(zone for zone in zones if zone.name == 'Act5-WorldstoneKeep').areas == (128, 129, 130, 131, 132)
    for zone in zones:
        matched = match_active_zone(frozenset(zone.areas))
        assert matched is not None
        assert matched.name == zone.name


def test_town_memory_matches_one_group_and_allows_only_unreported_no_herald_transit():
    tower = match_active_zone(frozenset((6, 11, 15, 21, 22, 23, 24, 25)))
    assert tower is not None
    assert tower.name == 'Act1-Tower'
    assert tower.unreported == (20,)
    assert match_active_zone(frozenset((6, 11, 15, 20, 21, 22, 23, 24, 25))) == replace(tower, unreported=())
    assert match_active_zone(frozenset((6, 11, 15))) is None  # partial read
    assert match_active_zone(frozenset((3, 9, 13, 6))) is None  # mixed groups


def test_route_inventory_covers_every_installed_level_and_reports_real_blockers():
    caps = route_inventory()
    expected = {area for zone in installed_active_zones() for area in zone.areas}
    assert set(caps) == expected
    assert [caps[area].route for area in (20, 45, 50, 132)] == ['Countess', 'Claw Viper Temple', 'Summoner', 'Baal']
    assert caps[73].status == 'unavailable'
    assert caps[73].reason == 'no route script'
    assert {area for area in expected if caps[area].status == 'unavailable'} == {73, 111, 112, 117}
