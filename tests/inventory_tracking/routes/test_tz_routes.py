"""A current TZ group's route is derived from catalog edges, including blockers."""

from inventory_tracking.routes.tz_groups import installed_active_zones
from inventory_tracking.routes.tz_routes import RouteExcursion, ZoneRoutePlan, route_leg, zone_route_plan


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
    blood_moor = route_leg(2)
    abaddon = route_leg(125)
    tomb = route_leg(66)
    assert blood_moor is not None
    assert abaddon is not None
    assert tomb is not None
    assert blood_moor.hops[0].kind == 'connector'
    assert 'town or waypoint connector' in blood_moor.blockers[0]
    assert 'red portal' in ' '.join(abaddon.blockers)
    assert any(hop.kind == 'tour' for hop in tomb.hops)
    assert 'tour' in ' '.join(tomb.blockers)


def test_every_installed_group_has_complete_leg_audit_without_claiming_all_are_playable():
    plans = [zone_route_plan(zone) for zone in installed_active_zones()]
    assert len(plans) == 34
    assert all(set(plan.legs) | {area for area, _ in plan.missing} == set(plan.zone.areas) for plan in plans)
    assert [(area, reason) for plan in plans for area, reason in plan.missing] == [(73, 'no route script')]
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
