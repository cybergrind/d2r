"""The Terror Zone leveling routine (macros/tzroutine.py): any zone's itinerary, each area's policy, and the game-level
goals derived from the facts; the navigation controller (macros/navigation.py)."""

from inventory_tracking.game.records import Teleport
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
    TRANSIT,
    WALK_OUT,
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
from inventory_tracking.routes.model import ENTER, FIGHT, LEAVE, LOOT as LOOT_STAGE


def aimed(agenda: Agenda, seen: LevelView) -> Objective:
    """The level run's target, which the test expects there to be."""
    found = agenda.in_level(seen)
    assert found is not None
    return found


CATACOMBS = frozenset((32, 33, 34, 35, 36, 37))
ROGUE_ENCAMPMENT, FORTRESS = 1, 103


def test_the_catacombs_zone_is_one_excursion_from_catacombs_2_to_andariel():
    # The player, 2026-10-20 ~08:24: "cat2 -> cat 3 -> cat 4 -> andy" (Inner Cloister and the Cathedral have no handler)
    plan = itinerary(CATACOMBS)
    assert plan is not None
    assert plan.zone == 'Act1-Catacombs'
    (trip,) = plan.excursions
    assert (trip.route, trip.waypoint, trip.areas) == ('Andariel', 35, (35, 36, 37))
    assert {area for area, _ in plan.skipped} == {32, 33, 34}
    assert [policy_of(area, trip) for area in trip.areas] == [ON_THE_WAY] * 3  # on the way to her, and her level
    assert policy_of(35, trip, full_clear=True) == FULL_CLEAR  # Full clear TZ: the Herald hunt


def test_a_zone_of_two_excursions_and_one_with_a_blocked_way_and_an_unknown_one():
    burial = itinerary(frozenset((17, 18, 19)))
    assert burial is not None
    assert [(trip.waypoint, trip.areas) for trip in burial.excursions] == [(3, (3, 17, 18)), (3, (3, 17, 19))]
    assert burial.excursions[0].zone == frozenset((17, 18))  # the Cold Plains are crossed, not worked
    cows = itinerary(frozenset((39,)))
    assert cows is not None
    assert cows.excursions == ()  # only the red portal the player opens with Wirt's Leg leads in
    assert {area for area, _ in cows.skipped} == {39}
    assert itinerary(frozenset((999,))) is None  # no installed zone: nothing to plan


def test_a_level_with_no_boss_ahead_is_covered_and_one_no_route_knows_too():
    tower = itinerary(frozenset((6, 11, 15, 20, 21, 22, 23, 24, 25)))
    assert tower is not None
    hole = next(trip for trip in tower.excursions if trip.route == 'Hole')
    assert [policy_of(area, hole) for area in hole.areas] == [COVER] * 3
    unknown = Excursion('', 900, (900, 901), frozenset((900, 901)))
    assert policy_of(901, unknown) == COVER
    assert policy_of(901, None) == TRANSIT  # no excursion under way: the way on only


def look(area: int, plan: Itinerary, **changes) -> list[tuple[str, int | None]]:
    return [
        (goal.kind, goal.to if goal.to is not None else goal.area)
        for goal in produce(GameView(area, area in (1, 40, 75, 103, 109), plan, **changes))
    ]


def test_a_catacombs_game_from_town_through_each_level_to_andariel_and_her_loot_then_no_goals():
    plan = itinerary(CATACOMBS)
    assert plan is not None
    assert look(ROGUE_ENCAMPMENT, plan) == [(WAYPOINT, 35)]
    assert look(35, plan, stage=ENTER, stage_to=36) == [(LEVEL, 35)]  # elites first: the area's run
    assert look(35, plan, stage=ENTER, stage_to=36, worked=((35, 1),)) == [(NEXT_LEVEL, 36)]
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
    assert look(FORTRESS, plan) == [(WAYPOINT, 35)]  # (the zone's waypoint from any act's town)


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


def test_a_crossed_level_is_crossed_and_a_routes_way_to_a_town_ends_the_excursion():
    # rca/2026-10-19/tz-coverage-findings.md F3 (Travincal's Council on the Durance trip: "next level" with its loot
    # left) and F4 (the Red portal to the Fortress as a level run: the trip unfinished, made again)
    from inventory_tracking.routes.model import STAND, USE

    durance = itinerary(frozenset((100, 101, 102)))
    assert durance is not None
    assert look(83, durance, stage=ENTER, stage_to=100) == [(NEXT_LEVEL, 100)]  # crossed: its way on only
    assert look(102, durance, stage=STAND) == [(LEVEL, 102)]
    assert look(102, durance, stage=USE, stage_to=FORTRESS, worked=((102, 2),)) == [(LEVEL, FORTRESS)]
    (home,) = produce(GameView(102, False, durance, USE, FORTRESS, ((102, 2),)))
    assert (home.kind, home.to, home.label) == (LEVEL, FORTRESS, 'to The Pandemonium Fortress by the route: the '
                                                'excursion ends')  # fmt: skip
    assert look(FORTRESS, durance, finished=frozenset((102,))) == []  # the Fortress: Save and Exit there
    # A portal into the trip's next level stays the level's work (Tristram)
    tristram = itinerary(frozenset((4, 38)))
    assert tristram is not None
    assert look(4, tristram, stage=USE, stage_to=38, worked=((4, 1),)) == [(LEVEL, 4)]


def test_a_script_is_held_to_its_trip_with_no_walk_across_into_a_level_off_it():
    # F5: the River of Flame's run walked the open passage into the non-terror Chaos Sanctuary and explored it
    from inventory_tracking.macros.tzroutine import kept_to
    from inventory_tracking.routes.catalog import ROUTES

    def script(route: str, area: int):
        return next(s for r in ROUTES if r.name == route for s in r.scripts if s.area == area)

    river, sanctuary = itinerary(frozenset((106, 107))), itinerary(frozenset((108,)))
    jail = itinerary(frozenset((28, 29, 30, 31)))
    assert river is not None
    assert sanctuary is not None
    assert jail is not None
    assert kept_to(script('Diablo', 107), river.excursions[0]).stages == ()
    # The Chaos Sanctuary zone's trip crosses the River (not terrorized): its way into the sanctuary only
    assert kept_to(script('Diablo', 107), sanctuary.excursions[0]) is script('Diablo', 107)
    # No door into a level off the trip either (the Inner Cloister after the Jail)
    assert kept_to(script('Andariel', 31), jail.excursions[0]).stages == ()
    # Travincal crossed on the Durance trip: no Council, no loot, the Durance's door
    durance = itinerary(frozenset((100, 101, 102)))
    assert durance is not None
    crossed = kept_to(script('Mephisto', 83), durance.excursions[0])
    assert [stage.text() for stage in crossed.stages] == ['enter Durance of Hate']
    # Durance 3's Red portal to the Fortress is kept: the excursion's end
    assert kept_to(script('Mephisto', 102), durance.excursions[0]) is script('Mephisto', 102)


def test_a_level_not_terrorized_is_transit_for_both_kinds_and_its_run_takes_only_the_drops():
    durance = itinerary(frozenset((100, 101, 102)))
    assert durance is not None
    (trip,) = durance.excursions
    assert policy_of(83, trip) == TRANSIT
    assert policy_of(83, trip, full_clear=True) == TRANSIT  # Full clear TZ too
    assert policy_of(108, None) == TRANSIT  # off the itinerary (the Chaos Sanctuary from the River)
    assert policy_of(100, trip) == ON_THE_WAY
    agenda = Agenda()
    agenda.begin('g')
    here = (5000.0, 5000.0)
    council = Leader(1, (5030.0, 5000.0), 'Ismail Vilehand')
    room = ((5300.0, 5300.0), 'an unexplored room')
    assert agenda.in_level(LevelView(83, here, (council,), frontier=lambda: room, policy=TRANSIT)) is None
    rune = Objective(PICKUP, 'Ist Rune', 3, 83, (5010.0, 5000.0))
    assert agenda.in_level(LevelView(83, here, side=rune, policy=TRANSIT)) == rune  # drops first, always


def test_a_trip_from_the_town_it_stands_in_walks_out_and_one_from_another_town_takes_the_waypoint():
    # rca/2026-10-19/town-exit-findings.md: a waypoint to the town the character stood in was the goal before
    moor, waste, steppes = (itinerary(frozenset(zone)) for zone in ((2, 8), (41, 55, 59), (104, 105)))
    assert moor is not None
    assert waste is not None
    assert steppes is not None
    assert [(trip.waypoint, trip.areas) for trip in moor.excursions] == [(1, (1, 2, 8))]
    assert look(ROGUE_ENCAMPMENT, moor) == [(WALK_OUT, 2)]
    assert look(FORTRESS, moor) == [(WAYPOINT, 1)]  # to its town first
    assert look(40, waste) == [(WALK_OUT, 41)]
    assert look(FORTRESS, steppes) == [(WALK_OUT, 104)]
    assert look(ROGUE_ENCAMPMENT, moor, visit_due=True) == [(WAYPOINT, FORTRESS)]  # the visit first
    (out,) = produce(GameView(ROGUE_ENCAMPMENT, True, moor))
    assert (out.label, out.area) == ('out of Rogue Encampment into Blood Moor', ROGUE_ENCAMPMENT)
    # Out in the field the trip goes on as any: Blood Moor's run, on to the Den of Evil, Corpsefire
    assert look(2, moor, stage=ENTER, stage_to=8) == [(LEVEL, 2)]
    assert look(2, moor, stage=ENTER, stage_to=8, worked=((2, 1),)) == [(NEXT_LEVEL, 8)]
    assert look(8, moor, stage=FIGHT) == [(LEVEL, 8)]
