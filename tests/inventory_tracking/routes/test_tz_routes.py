"""A current TZ group's route is derived from catalog edges, including blockers."""

from inventory_tracking.routes.tz_groups import installed_active_zones, manual_zone
from inventory_tracking.routes.tz_routes import (
    RouteExcursion,
    ZoneRoutePlan,
    nearest_excursion,
    route_inventory,
    route_leg,
    zone_route_plan,
)
from inventory_tracking.terror.zones import GROUPS


def test_cave_and_tower_legs_use_catalog_hops_and_explicit_branch_names():
    cave = route_leg(13)
    assert cave is not None
    assert cave.route == 'Cave'
    assert cave.waypoint == 3
    assert [(hop.source, hop.destination) for hop in cave.hops] == [(3, 9), (9, 13)]
    assert cave.blockers == ()

    hole = route_leg(15)
    countess = route_leg(25)
    assert hole is not None
    assert countess is not None
    assert [(hop.source, hop.destination) for hop in hole.hops] == [(6, 11), (11, 15)]
    assert [(hop.source, hop.destination) for hop in countess.hops] == [
        (6, 20),
        (20, 21),
        (21, 22),
        (22, 23),
        (23, 24),
        (24, 25),
    ]
    assert hole.hops[0].route == 'Hole'
    assert countess.hops[0].route == 'Countess'


def test_implicit_town_start_pending_portal_and_tomb_tour_are_explicit_blockers():
    sewers = route_leg(47)  # Lut Gholein's trapdoor into the Sewers: no route stage walks to it
    abaddon = route_leg(125)
    tomb = route_leg(66)
    assert sewers is not None
    assert abaddon is not None
    assert tomb is not None
    assert (sewers.hops[0].source, sewers.hops[0].kind) == (40, 'connector')
    assert 'town or waypoint connector' in sewers.blockers[0]
    assert 'red portal' in ' '.join(abaddon.blockers)
    assert any(hop.kind == 'tour' for hop in tomb.hops)
    assert 'tour' in ' '.join(tomb.blockers)


def test_every_installed_group_has_complete_leg_audit_without_claiming_all_are_playable():
    plans = [zone_route_plan(zone) for zone in installed_active_zones()]
    assert len(plans) == 34
    assert all(set(plan.legs) | {area for area, _ in plan.missing} == set(plan.zone.areas) for plan in plans)
    # Duriel's Lair has its script since 2026-10-21 (levels/handlers/tal_rasha.py DURIEL): no level is missing one
    assert [(area, reason) for plan in plans for area, reason in plan.missing] == []
    assert all(plan.blockers for plan in plans)  # every route still needs at least one played check or handler


def test_tower_group_excursions_cover_both_branches_from_black_marsh():
    tower = next(zone for zone in installed_active_zones() if zone.name == 'Act1-Tower')
    plan = zone_route_plan(tower)

    assert [(trip.route, trip.waypoint, trip.terminal, trip.covers) for trip in plan.excursions] == [
        ('Countess', 6, 25, (6, 20, 21, 22, 23, 24, 25)),
        ('Hole', 6, 15, (6, 11, 15)),
    ]
    assert plan.uncovered == ()


def test_jail_group_uses_the_outer_cloister_waypoint_to_cover_all_levels_in_one_trip():
    jail = next(zone for zone in installed_active_zones() if zone.name == 'Act1-Jail')
    plan = zone_route_plan(jail)

    assert [(trip.waypoint, trip.terminal, trip.covers) for trip in plan.excursions] == [
        (27, 31, (28, 29, 30, 31)),
    ]


def test_catacombs_group_avoids_unterrorized_barracks_transit_when_coverage_is_equal():
    catacombs = next(zone for zone in installed_active_zones() if zone.name == 'Act1-Catacombs')
    plan = zone_route_plan(catacombs)

    assert [(trip.waypoint, trip.terminal, trip.covers) for trip in plan.excursions] == [
        (32, 37, (32, 33, 34, 35, 36, 37)),
    ]


def test_a_plan_with_a_blocked_excursion_is_not_ready_even_if_individual_legs_are_clear():
    zone = next(zone for zone in installed_active_zones() if zone.name == 'Act1-Tower')
    trip = RouteExcursion('Countess', 6, 25, (), (6, 25), ('missing entrance handler',))
    plan = ZoneRoutePlan(zone, {}, (), (), (trip,), ())

    assert not plan.ready


def test_route_inventory_covers_every_herald_group_level_conservatively():
    inventory = route_inventory()
    herald_areas = {area for group in GROUPS for area in group.areas}
    assert set(inventory) - herald_areas == {20, 45, 50, 73, 132}
    assert all(capability.status != 'ready' for capability in inventory.values())
    assert all(capability.entry and capability.exit for capability in inventory.values())


def test_a_trip_that_can_be_played_comes_before_a_blocked_one_covering_more():
    # 2026-10-19 19:54: TZ leveling left every game in Act2-ArcaneSanctuary; the trip from Lut Gholein (its walk to the
    # Harem unscripted) covered all six levels and left none to the Palace Cellar waypoint's
    zone = next(zone for zone in installed_active_zones() if zone.name == 'Act2-ArcaneSanctuary')
    plan = zone_route_plan(zone)

    assert [(trip.waypoint, trip.terminal, trip.covers, bool(trip.blockers)) for trip in plan.excursions] == [
        (52, 74, (52, 53, 54, 74), False),
        (40, 51, (50, 51), True),
    ]


def test_the_zones_with_no_playable_excursion_are_known_and_stop_the_tz_loop():
    # 2026-10-19 (rca/2026-10-19/tz-coverage-findings.md F1): macros/tzloop.py `choose` stops the loop in town (cause
    # 'idle') for these rather than make games. Moo Moo Farm is entered only by the red portal the player opens with
    # Wirt's Leg. A zone added here, or one leaving it, is a change to say
    unplayable = {
        zone.name
        for zone in installed_active_zones()
        if all(trip.blockers for trip in zone_route_plan(zone).excursions)
    }
    assert unplayable == {'Act1-MooMooFarm'}


def test_the_zones_entered_from_a_town_on_foot_are_one_trip_from_the_town():
    # The towns' walks out (catalog alternate town scripts; rca/2026-10-19/town-exit-findings.md): the town's way out
    # is a route stage, no connector
    trips = {
        zone.name: [(trip.waypoint, [(hop.source, hop.destination, hop.kind) for hop in trip.hops], trip.blockers)
                    for trip in zone_route_plan(zone).excursions]
        for zone in installed_active_zones()
        if zone.name in ('Act1-BloodMoor', 'Act2-RockyWaste', 'Act4_OuterSteppes')
    }  # fmt: skip
    assert trips == {
        'Act1-BloodMoor': [(1, [(1, 2, 'stage'), (2, 8, 'stage')], ())],
        'Act2-RockyWaste': [(40, [(40, 41, 'stage'), (41, 55, 'stage'), (55, 59, 'stage')], ())],
        'Act4_OuterSteppes': [(103, [(103, 104, 'stage'), (104, 105, 'stage')], ())],
    }


def test_the_tal_rashas_zone_is_one_trip_touring_the_canyon_and_its_seven_tombs():
    # 14:00:21 on 2026-10-20 the tombs were skipped ('tour 46→66 cannot designate one entrance') and the Canyon alone
    # was played. The player, 2026-10-20 ~14:03: "we need to utilize smaller tombs too - it gives a great ext/hour
    # rate". A trip touring them all needs no entrance designated: the tour reads the level on arrival
    zone = next(zone for zone in installed_active_zones() if zone.name == 'Act2-TalRashas')
    plan = zone_route_plan(zone)

    (trip,) = plan.excursions
    assert (trip.route, trip.waypoint, trip.terminal, trip.blockers) == ("Tal Rasha's Tombs", 46, 73, ())
    # Duriel's Lair last (levels/handlers/tal_rasha.py DURIEL, on since 2026-10-21): the audit's hop names the last
    # tomb's Orifice `use`; played, the lair is the tour's side level, entered from whichever tomb holds the Orifice
    # (routes/zone_graph.py `Node.side`, tests/inventory_tracking/macros/acts/test_act2_duriel.py)
    assert trip.covers == (46, 66, 67, 68, 69, 70, 71, 72, 73)
    assert [(hop.source, hop.kind) for hop in trip.hops] == [(46, 'tour')] * 7 + [(72, 'stage')]
    assert plan.uncovered == ()
    # One tomb alone is still no leg: which entrance leads into it is not in the room data
    tomb = route_leg(69)
    assert tomb is not None
    assert 'cannot designate one entrance' in ' '.join(tomb.blockers)


def test_the_nearest_excursion_to_a_boss_starts_at_the_waypoint_nearest_it():
    # The player, 2026-10-20 ~21:27: "we must go river of flame -> CS -> kill diablo" (not from the City of the Damned)
    act4 = manual_zone(4)
    assert act4 is not None
    diablo = nearest_excursion(act4, 108)
    assert diablo is not None
    assert (diablo.route, diablo.waypoint, diablo.terminal, diablo.covers, diablo.blockers) == (
        'Diablo',
        107,
        108,
        (107, 108),
        (),
    )
    act3 = manual_zone(3)
    assert act3 is not None
    mephisto = nearest_excursion(act3, 102)
    assert mephisto is not None
    assert (mephisto.waypoint, mephisto.terminal) == (101, 102)
    assert nearest_excursion(act4, 999) is None
