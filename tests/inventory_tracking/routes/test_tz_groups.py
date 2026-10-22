"""The live active-zone choice follows the installed game table, not a rotation guess."""

from dataclasses import replace

from inventory_tracking.routes.tz_groups import (
    installed_active_zones,
    installed_manual_zones,
    manual_zone,
    match_active_zone,
    match_zones,
)
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
    # Duriel's Lair: the tombs' route's, entered by the true tomb's Orifice (levels/handlers/tal_rasha.py DURIEL, on
    # since 2026-10-21; before, 'unavailable', 'no route script')
    lair = caps[73]
    assert (lair.route, lair.waypoint, lair.target) == ("Tal Rasha's Tombs", 46, 'boss')
    assert lair.status == 'needs-played-check'
    assert (lair.entry, lair.exit) == ('use Orifice', 'leave')
    assert {area for area in expected if caps[area].status == 'unavailable'} == {111, 112, 117}


# A whole act terrorized by a Worldstone Shard (the player, 2026-10-20 ~19:00: "for TZ/TZ+ modes we want to know how to
# handle whole terrorized act (when we terrorized it manually with stone)"; rca/2026-10-20/act-terrorize-findings.md §4)
ACT4 = frozenset((104, 105, 106, 107, 108))
CATACOMBS = frozenset((32, 33, 34, 35, 36, 37))


def test_the_five_manual_zones_are_the_installed_acts_and_their_cores_have_herald_groups():
    acts = installed_manual_zones()
    assert [zone.name for zone in acts] == [f'Act{act}-Manual' for act in range(1, 6)]
    assert [len(zone.areas) for zone in acts] == [37, 34, 27, 5, 22]
    assert acts[3].areas == (104, 105, 106, 107, 108)
    # The levels with no Herald group: terrorized, but the tracker cannot read them (terror/tracker.py `terrorized`)
    assert [sorted(set(zone.areas) - zone.core) for zone in acts] == [[20], [45, 50, 73], [], [], [132]]
    assert manual_zone(4) == acts[3]
    assert manual_zone(6) is None


def test_a_terrorized_act_alone_is_its_manual_zone():
    (act,) = match_zones(ACT4)
    assert act.name == 'Act4-Manual'
    assert act.unreported == ()


def test_a_terrorized_act_and_the_rotation_elsewhere_are_both_matched_the_act_first():
    act, rotation = match_zones(ACT4 | CATACOMBS)
    assert (act.name, rotation.name) == ('Act4-Manual', 'Act1-Catacombs')


def test_the_rotation_inside_the_terrorized_act_is_the_act():
    act1 = installed_manual_zones()[0]
    (act,) = match_zones(act1.core)
    assert act.name == 'Act1-Manual'
    assert act.unreported == (20,)  # the Forgotten Tower: no Herald group, never read
    assert act.core >= CATACOMBS


def test_a_partly_read_act_is_not_an_act_and_its_wholly_read_groups_are_played_meanwhile():
    # The act's groups come one by one when the client's list does not hold it (its plain monsters' votes): no act
    # until every group is read, and no stop while it is read ("no terror zone is read" stopped the loop before)
    (steppes,) = match_zones(frozenset((104, 105)))
    assert steppes.name == 'Act4_OuterSteppes'  # the rotation alone, as today
    read = match_zones(frozenset((104, 105, 106, 107)))
    assert [zone.name for zone in read] == ['Act4_OuterSteppes', 'Act4-RiverOfFlame']
    act1 = installed_manual_zones()[0]
    read = match_zones(act1.core - {2, 8})  # Blood Moor and the Den of Evil not read yet
    assert 'Act1-Manual' not in [zone.name for zone in read]
    assert 'Act1-BloodMoor' not in [zone.name for zone in read]
    assert {'Act1-Catacombs', 'Act1-Tower', 'Act1-Jail'} <= {zone.name for zone in read}


def test_nothing_read_or_only_stray_levels_match_nothing():
    assert match_zones(frozenset()) == ()
    assert match_zones(frozenset((6, 11))) == ()  # part of one group's levels: no group read
    # A stray level beside a group wholly read: the group, the stray left out
    assert [zone.name for zone in match_zones(frozenset((3, 9, 13, 6)))] == ['Act1-ColdPlains']
