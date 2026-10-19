"""The Terror Zone leveling routine (macros/tzroutine.py): any zone's itinerary, each area's policy, and the game-level
goals derived from the facts; the navigation controller (macros/navigation.py)."""

from inventory_tracking.macros.agenda import (
    COVER,
    ERRAND,
    FULL_CLEAR,
    LEVEL,
    LOOT,
    NEXT_LEVEL,
    ON_THE_WAY,
    PICKUP,
    PORTAL_TO_TOWN,
    TOWN_ROUTINE,
    WAYPOINT,
    Agenda,
    Leader,
    LevelView,
    Objective,
)
from inventory_tracking.macros.movement import HOPS, WALKS, WARPS
from inventory_tracking.macros.navigation import Abilities, means
from inventory_tracking.macros.travel import LOOPED, LOOPED_TELEPORT
from inventory_tracking.macros.tzroutine import (
    RUNS_AN_AREA,
    Excursion,
    GameView,
    Itinerary,
    itinerary,
    policy_of,
    produce,
)
from inventory_tracking.macros.world import Teleport
from inventory_tracking.routes.model import ENTER, FIGHT, LEAVE, LOOT as LOOT_STAGE


def aimed(agenda: Agenda, seen: LevelView) -> Objective:
    """The level run's target, which the test expects there to be."""
    found = agenda.in_level(seen)
    assert found is not None
    return found


CATACOMBS = frozenset((32, 33, 34, 35, 36, 37))
ROGUE_ENCAMPMENT, FORTRESS = 1, 103


def test_the_catacombs_zone_is_one_excursion_from_the_inner_cloister_to_andariel():
    plan = itinerary(CATACOMBS)
    assert plan is not None
    assert plan.zone == 'Act1-Catacombs'
    (trip,) = plan.excursions
    assert (trip.route, trip.waypoint, trip.areas) == ('Andariel', 32, (32, 33, 34, 35, 36, 37))
    assert [policy_of(area, trip) for area in trip.areas] == [ON_THE_WAY] * 6  # on the way to her, and her level
    assert policy_of(35, trip, full_clear=True) == FULL_CLEAR  # Full clear TZ: the Herald hunt


def test_a_zone_of_two_excursions_and_one_with_a_blocked_way_and_an_unknown_one():
    burial = itinerary(frozenset((17, 18, 19)))
    assert burial is not None
    assert [(trip.waypoint, trip.areas) for trip in burial.excursions] == [(3, (3, 17, 18)), (3, (3, 17, 19))]
    assert burial.excursions[0].zone == frozenset((17, 18))  # the Cold Plains are crossed, not worked
    moor = itinerary(frozenset((2, 8)))
    assert moor is not None
    assert moor.excursions == ()  # out of the Rogue Encampment by a border: no stage walks it yet
    assert {area for area, _ in moor.skipped} == {2, 8}
    assert itinerary(frozenset((999,))) is None  # no installed zone: nothing to plan


def test_a_level_with_no_boss_ahead_is_covered_and_one_no_route_knows_too():
    tower = itinerary(frozenset((6, 11, 15, 20, 21, 22, 23, 24, 25)))
    assert tower is not None
    hole = next(trip for trip in tower.excursions if trip.route == 'Hole')
    assert [policy_of(area, hole) for area in hole.areas] == [COVER] * 3
    unknown = Excursion('', 900, (900, 901), frozenset((900, 901)))
    assert policy_of(901, unknown) == COVER
    assert policy_of(901, None) == COVER


def look(area: int, plan: Itinerary, **changes) -> list[tuple[str, int | None]]:
    return [
        (goal.kind, goal.to if goal.to is not None else goal.area)
        for goal in produce(GameView(area, area in (1, 40, 75, 103, 109), plan, **changes))
    ]


def test_a_catacombs_game_from_town_through_each_level_to_andariel_and_her_loot_then_no_goals():
    plan = itinerary(CATACOMBS)
    assert plan is not None
    assert look(ROGUE_ENCAMPMENT, plan) == [(WAYPOINT, 32)]
    assert look(32, plan, stage=ENTER, stage_to=33) == [(LEVEL, 32)]  # elites first: the area's run
    assert look(32, plan, stage=ENTER, stage_to=33, worked=((32, 1),)) == [(NEXT_LEVEL, 33)]
    assert look(36, plan, stage=ENTER, stage_to=37, worked=((36, 1),)) == [(NEXT_LEVEL, 37)]
    assert look(37, plan, stage=FIGHT) == [(LEVEL, 37)]
    assert look(37, plan, stage=FIGHT, worked=((37, 1),)) == [(LEVEL, 37)]  # her fight not done: run again
    assert look(37, plan, stage=FIGHT, worked=((37, RUNS_AN_AREA),)) == []  # not for ever
    assert look(37, plan, stage=LOOT_STAGE, worked=((37, 1),)) == [(LOOT, 37)]
    assert look(37, plan, stage=LEAVE, worked=((37, 1),)) == []  # no goals: the agenda's next is LEAVE_GAME


def test_a_valuable_on_the_ground_comes_first_and_the_visit_only_when_due():
    plan = itinerary(CATACOMBS)
    assert plan is not None
    assert look(37, plan, stage=LEAVE, worked=((37, 1),), sighted='Ist Rune at (1, 2)') == [(PICKUP, 37)]
    assert look(ROGUE_ENCAMPMENT, plan, visit_due=True) == [(WAYPOINT, FORTRESS)]
    due = produce(GameView(FORTRESS, True, plan, visit_due=True))
    assert [(goal.kind, goal.exit, goal.tier) for goal in due] == [(TOWN_ROUTINE, 'waypoint', ERRAND)]
    assert look(FORTRESS, plan) == [(WAYPOINT, 32)]  # (the zone's waypoint from any act's town)


def test_an_excursion_over_goes_to_the_next_by_the_portal_and_the_last_one_has_no_goals():
    burial = itinerary(frozenset((17, 18, 19)))
    assert burial is not None
    assert look(17, burial, stage=ENTER, stage_to=18, worked=((17, 1),)) == [(NEXT_LEVEL, 18)]
    assert look(18, burial, stage=LEAVE, worked=((18, 1),)) == [(PORTAL_TO_TOWN, 18)]
    assert look(3, burial, finished=frozenset((17, 18))) == [(NEXT_LEVEL, 17)]  # the second's way: crossed
    assert look(19, burial, stage=LEAVE, worked=((19, 1),), finished=frozenset((17, 18))) == []


def test_an_unknown_terror_zone_level_is_explored_for_its_elites_and_its_end_is_the_runs():
    # A level no route knows: COVER (explore to coverage, kill every elite found, nearest first), its end when the run
    # finds nothing more, the excursion's end there
    unknown = Itinerary('Act9-Nowhere', frozenset((900,)), (Excursion('', 900, (900,), frozenset((900,))),))
    assert look(900, unknown) == [(LEVEL, 900)]
    assert look(900, unknown, worked=((900, 1),)) == []
    agenda = Agenda()
    agenda.begin('g')
    here, room = (5000.0, 5000.0), ((5300.0, 5300.0), 'an unexplored room')
    policy = policy_of(900, unknown.excursions[0])
    champion = Leader(1, (5200.0, 5000.0), 'a champion')
    assert aimed(agenda, LevelView(900, here, (champion,), frontier=lambda: room, policy=policy)).unit == 1
    explore = agenda.in_level(LevelView(900, here, frontier=lambda: room, policy=policy))
    assert explore is not None
    assert explore.place == room[0]
    assert agenda.in_level(LevelView(900, here, frontier=lambda: None, policy=policy)) is None


def test_the_navigation_controller_chooses_teleport_blade_warp_or_the_walk_by_what_is_in_hand():
    # The player, 2026-10-19: "navigation controller, that knows our abilities/equipment (enigma? teleport charges in
    # staff, blade warp, walking, something else, regular sorc teleport)"
    own = means(Abilities(own_teleport=True, staff=None, free_jump='Blade Warp'))
    assert (own.kind, own.intent) == (HOPS, LOOPED_TELEPORT)  # Enigma, a Sorceress: every move
    staff = Teleport(40, 69, False)
    paid = means(Abilities(own_teleport=False, staff=staff, pays=True, free_jump='Blade Warp'))
    assert (paid.kind, paid.intent) == (HOPS, LOOPED_TELEPORT)
    kept = means(Abilities(own_teleport=False, staff=staff, pays=False, free_jump='Blade Warp'))
    assert (kept.kind, kept.intent) == (WARPS, LOOPED)  # the gold does not pay: Blade Warp, the charges kept
    low = means(Abilities(own_teleport=False, staff=Teleport(5, 69, False), pays=True, free_jump='Blade Warp'))
    assert low.kind == WARPS  # the last LOW_CHARGES are the player's own steps'
    walk = means(Abilities(own_teleport=False, staff=Teleport(5, 69, False), pays=True))
    assert (walk.kind, walk.intent) == (WALKS, LOOPED)
    assert means(Abilities()).kind == WALKS
