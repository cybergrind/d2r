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
    PLUS,
    PLUS_WAY,
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
    # TZ leveling before TZ+: on the way to her, and her level
    assert [policy_of(area, trip, plus=False) for area in trip.areas] == [ON_THE_WAY] * 3
    # TZ+ (2026-10-20): each level explored and its groups taken, hers too, then Andariel
    assert [policy_of(area, trip) for area in trip.areas] == [PLUS] * 3
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
    assert [policy_of(area, hole, plus=False) for area in hole.areas] == [COVER] * 3
    assert [policy_of(area, hole) for area in hole.areas] == [PLUS] * 3  # TZ+: the rooms and the groups too
    unknown = Excursion('', 900, (900, 901), frozenset((900, 901)))
    assert policy_of(901, unknown, plus=False) == COVER
    assert policy_of(901, unknown) == PLUS
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
    policy = policy_of(900, unknown.excursions[0], plus=False)
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
    assert policy_of(100, trip, plus=False) == ON_THE_WAY
    assert policy_of(100, trip) == PLUS
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


WORLDSTONE_KEEP = frozenset((128, 129, 130, 131, 132))


def test_the_worldstone_keep_zone_goes_through_the_thrones_waves_and_portal_to_baal_and_his_loot():
    # The player, 2026-10-20 ~09:33: "tz leveling should do baal and trone fight". The zone of 04:30 that day:
    # 'Baal from 129: [129, 130, 131, 132]' (128 skipped)
    from inventory_tracking.routes.model import USE

    plan = itinerary(WORLDSTONE_KEEP)
    assert plan is not None
    trip = next(each for each in plan.excursions if each.route == 'Baal')
    assert (trip.waypoint, trip.areas) == (129, (129, 130, 131, 132))
    assert {131, 132} <= trip.zone
    assert policy_of(131, trip, plus=False) == ON_THE_WAY  # the leaders on the way, then the route's own goals
    assert policy_of(132, trip, plus=False) == ON_THE_WAY
    # TZ+: the Throne stands for the waves (no room explored first), its groups taken; the Chamber is explored
    assert policy_of(131, trip) == PLUS_WAY
    assert policy_of(132, trip) == PLUS
    assert look(131, plan, stage=FIGHT) == [(LEVEL, 131)]  # the waves: the level's run
    assert look(131, plan, stage=FIGHT, worked=((131, 1),)) == [(LEVEL, 131)]  # Lister not dead: the run again
    assert look(131, plan, stage=LOOT_STAGE, worked=((131, 1),)) == [(LOOT, 131)]  # after Lister, his loot
    # Then the portal Baal leaves by: a run of the level, whose stage is the portal's use (hunting/throne.py)
    assert look(131, plan, stage=USE, stage_to=132, worked=((131, 1),)) == [(LEVEL, 131)]
    assert look(132, plan, stage=FIGHT) == [(LEVEL, 132)]  # Baal: the Chamber's run
    assert look(132, plan, stage=LOOT_STAGE, worked=((132, 1),)) == [(LOOT, 132)]
    assert look(132, plan, stage=LEAVE, worked=((132, 1),)) == []  # no goals: the game is left


CANYON, LUT_GHOLEIN = 46, 40
TOMBS = (66, 67, 68, 69, 70, 71, 72)
TAL_RASHAS = frozenset((CANYON, *TOMBS, 73))


def test_the_tal_rashas_zone_is_the_canyon_then_its_seven_tombs_one_trip_touring_them():
    # The player, 00:45 on 2026-10-18: "for canyon of the magi loop: we should go through every tomb one by one";
    # "Canyon first, then tombs"; 2026-10-20 ~14:03: "we need to utilize smaller tombs too"
    plan = itinerary(TAL_RASHAS)
    assert plan is not None
    (trip,) = plan.excursions
    assert (trip.waypoint, trip.areas, trip.hub, trip.tours) == (CANYON, (CANYON, *TOMBS), CANYON, TOMBS)
    assert trip.zone == frozenset((CANYON, *TOMBS))  # Duriel's Lair is no level of the trip
    assert plan.skipped == ((73, 'no catalogue excursion covers it'),)
    assert [policy_of(area, trip, plus=False) for area in trip.areas] == [COVER] * 8  # each: leaders and rooms
    assert [policy_of(area, trip) for area in trip.areas] == [PLUS] * 8  # TZ+: and the groups
    assert not trip.over(frozenset((72,)))  # the catalogue's last tomb done first ends nothing
    assert trip.over(frozenset(TOMBS))


def test_the_canyons_run_then_each_tomb_by_the_nearest_entrance_its_run_and_its_way_back_until_the_last():
    plan = itinerary(TAL_RASHAS)
    assert plan is not None
    assert look(LUT_GHOLEIN, plan) == [(WAYPOINT, CANYON)]
    assert look(CANYON, plan, stage=ENTER) == [(LEVEL, CANYON)]  # the Canyon first
    (on,) = produce(GameView(CANYON, False, plan, ENTER, 0, ((CANYON, 1),)))
    # No tomb named ahead: the press goes through the nearest entrance not yet entered
    assert (on.kind, on.to, on.label) == (NEXT_LEVEL, None, "on into the nearest Tal Rasha's Tomb not entered (7 of 7 "
                                          'left)')  # fmt: skip
    (run,) = produce(GameView(69, False, plan, ENTER, CANYON))
    assert (run.kind, run.label) == (LEVEL, "the Tal Rasha's Tomb 4 run (toured level 1 of 7)")
    assert look(69, plan, stage=ENTER, stage_to=CANYON, worked=((69, 1),)) == [(NEXT_LEVEL, CANYON)]  # its way back
    done = frozenset((69, 66))
    (on,) = produce(GameView(CANYON, False, plan, ENTER, 0, ((CANYON, 3),), finished=done))
    assert on.label.endswith('(5 of 7 left)')
    last = frozenset(TOMBS) - {70}
    assert look(70, plan, stage=ENTER, stage_to=CANYON, finished=last) == [(LEVEL, 70)]
    # The last tomb's run over: no way back, no goals: the game is left there (its valuables first)
    assert look(70, plan, stage=ENTER, stage_to=CANYON, worked=((70, 1),), finished=last) == []
    assert look(70, plan, stage=ENTER, stage_to=CANYON, worked=((70, 1),), finished=last, sighted='Ber Rune') == [
        (PICKUP, 70)
    ]
    assert look(CANYON, plan, stage=LOOT_STAGE, worked=((CANYON, 8),), finished=frozenset(TOMBS)) == []


def test_a_town_trip_mid_tour_comes_back_to_the_tombs_not_done_and_never_redoes_one():
    plan = itinerary(TAL_RASHAS)
    assert plan is not None
    done = frozenset((69, 66, 72))
    assert look(LUT_GHOLEIN, plan, finished=done) == [(WAYPOINT, CANYON)]  # the trip is not over
    assert look(CANYON, plan, stage=ENTER, worked=((CANYON, 4),), finished=done) == [(NEXT_LEVEL, CANYON)]
    # A tomb done and entered again (its entrance not seen gone through): no second run, no way back to it
    assert look(69, plan, stage=ENTER, stage_to=CANYON, finished=done) == []
    assert look(69, plan, stage=ENTER, stage_to=CANYON, worked=((69, 1),), finished=done) == []


def test_a_tour_whose_canyon_runs_are_spent_ends_never_a_stuck_tour():
    from inventory_tracking.macros.tzroutine import RUNS_A_TOURED_LEVEL

    plan = itinerary(TAL_RASHAS)
    assert plan is not None
    spent = 1 + RUNS_A_TOURED_LEVEL * len(TOMBS)
    assert look(CANYON, plan, stage=ENTER, worked=((CANYON, spent),)) == [(NEXT_LEVEL, CANYON)]
    assert look(CANYON, plan, stage=ENTER, worked=((CANYON, spent + 1),)) == []  # the game is left


def test_tz_plus_explores_the_levels_on_the_way_to_a_boss_that_tz_leveling_left_at_the_way_on(monkeypatch):
    # rca/2026-10-20/tz-level-leave-findings.md: under ON_THE_WAY the Outer Steppes were left at the way on with about
    # half their rooms read (19 visits 16:48-18:55), so a Herald could never come there
    from inventory_tracking.macros import tzroutine

    steppes = itinerary(frozenset((104, 105)))
    assert steppes is not None
    (trip,) = steppes.excursions
    assert trip.route == 'Izual'
    assert [policy_of(area, trip, plus=False) for area in (104, 105)] == [ON_THE_WAY, ON_THE_WAY]
    assert [policy_of(area, trip) for area in (104, 105)] == [PLUS, PLUS]
    # The switch: TZ leveling as before
    monkeypatch.setattr(tzroutine, 'TZ_PLUS', False)
    assert [policy_of(area, trip) for area in (104, 105)] == [ON_THE_WAY, ON_THE_WAY]
    assert policy_of(104, trip, full_clear=True) == FULL_CLEAR  # Full clear TZ is its own kind


def test_tz_plus_a_big_level_keeps_its_ways_exploring_rule_and_takes_only_its_big_groups():
    # The player, ~18:50: "we don't want to clear very large levels with 300 mobs or so"
    from inventory_tracking.macros.agenda import BIG_LEVEL
    from inventory_tracking.terror.zones import level_population

    jungle = itinerary(frozenset((78, 86, 87, 88, 89, 90, 91)))
    assert jungle is not None
    dungeon = next(trip for trip in jungle.excursions if trip.route == 'Flayer Dungeon')
    pit = next(trip for trip in jungle.excursions if trip.route == 'Swampy Pit')
    assert (level_population(78) or 0) >= BIG_LEVEL  # Flayer Jungle, 475
    assert policy_of(78, dungeon) == PLUS_WAY  # on the way to the Flayer Dungeon's boss: no room tour of the jungle
    assert policy_of(78, pit) == PLUS  # no boss ahead: explored as before (COVER), its big groups
    assert [policy_of(area, dungeon) for area in (88, 89, 91)] == [PLUS] * 3
    assert (level_population(117) or 0) >= BIG_LEVEL  # Frozen Tundra, 374


def test_the_tz_leveling_kinds_hud_word_is_tz_plus_while_tz_plus_is_on():
    from inventory_tracking.macros import tzroutine
    from inventory_tracking.macros.loop import TZ, TZ_CLEAR

    assert TZ.word == ('TZ+' if tzroutine.TZ_PLUS else 'TZ')
    assert TZ_CLEAR.word == 'TZC'


# A whole act terrorized by a Worldstone Shard, with the rotation (the player, 2026-10-20 ~19:00: "for TZ/TZ+ modes we
# want to know how to handle whole terrorized act (when we terrorized it manually with stone)"; ~18:50: "we want to
# kill act boss first for possible statue drop")
ACT4 = frozenset((104, 105, 106, 107, 108))


def trips_of(plan: Itinerary | None) -> list[tuple[str, int, tuple[int, ...]]]:
    assert plan is not None
    return [(trip.route, trip.waypoint, trip.areas) for trip in plan.excursions]


def test_a_terrorized_act_4_is_diablo_first_then_the_steppes_and_the_plains():
    plan = itinerary(ACT4)
    assert plan is not None
    assert plan.zone == 'Act4-Manual'
    assert plan.areas == ACT4
    assert trips_of(plan) == [('Diablo', 106, (106, 107, 108)), ('Izual', 103, (103, 104, 105))]
    assert plan.skipped == ()
    assert look(FORTRESS, plan) == [(WAYPOINT, 106)]  # the boss's trip first
    assert look(108, plan, stage=FIGHT) == [(LEVEL, 108)]
    assert look(108, plan, stage=LEAVE, worked=((108, 1),)) == [(PORTAL_TO_TOWN, 108)]  # the next trip after Diablo
    assert look(FORTRESS, plan, finished=frozenset((106, 107, 108))) == [(WALK_OUT, 104)]
    assert look(105, plan, stage=LEAVE, worked=((105, 1),), finished=frozenset((106, 107, 108))) == []  # the game ends
    # Every level of the act is worked (TZ+), none crossed
    diablo, izual = plan.excursions
    assert [policy_of(area, diablo) for area in (106, 107, 108)] == [PLUS, PLUS, PLUS]
    assert [policy_of(area, izual) for area in (104, 105)] == [PLUS, PLUS]


def test_a_terrorized_act_and_the_rotation_in_another_act_are_one_itinerary_the_act_first():
    plan = itinerary(ACT4 | CATACOMBS)
    assert plan is not None
    assert plan.zone == 'Act4-Manual + Act1-Catacombs'
    assert plan.areas == ACT4 | CATACOMBS
    assert trips_of(plan) == [
        ('Diablo', 106, (106, 107, 108)),
        ('Izual', 103, (103, 104, 105)),
        ('Andariel', 35, (35, 36, 37)),
    ]
    assert {area for area, _ in plan.skipped} == {32, 33, 34}  # as the Catacombs zone alone
    assert look(105, plan, stage=LEAVE, worked=((105, 1),), finished=frozenset((106, 107, 108))) == [
        (PORTAL_TO_TOWN, 105)
    ]
    assert look(FORTRESS, plan, finished=frozenset((106, 107, 108, 105))) == [(WAYPOINT, 35)]


def test_a_terrorized_act_1_holds_the_catacombs_rotation_and_andariel_comes_first():
    from inventory_tracking.routes.tz_groups import manual_zone

    act1 = manual_zone(1)
    assert act1 is not None
    plan = itinerary(act1.core)
    assert plan is not None
    assert plan.zone == 'Act1-Manual'
    first, rest = plan.excursions[0], plan.excursions[1]
    assert (first.route, first.waypoint, first.areas) == ('Andariel', 35, (35, 36, 37))
    # The levels before her waypoint are a trip of their own (the Outer Cloister's, through the Jail and the Cathedral)
    assert (rest.route, rest.waypoint, rest.areas) == ('Andariel', 27, (27, 28, 29, 30, 31, 32, 33, 34))
    covered = {area for trip in plan.excursions for area in trip.zone}
    assert covered == set(act1.areas)  # every level of the act, the Forgotten Tower too
    assert plan.skipped == ()


def test_a_partly_read_act_plays_its_groups_read_and_never_stops_the_loop():
    plan = itinerary(frozenset((104, 105, 106, 107)))
    assert plan is not None
    assert plan.zone == 'Act4_OuterSteppes + Act4-RiverOfFlame'
    assert trips_of(plan) == [('Izual', 103, (103, 104, 105)), ('Diablo', 106, (106, 107))]
    assert 108 not in plan.areas  # not read: crossed, never worked


def test_manual_zones_off_is_the_one_rotating_zone_as_before(monkeypatch):
    from inventory_tracking.macros import tzroutine

    monkeypatch.setattr(tzroutine, 'MANUAL_ZONES', False)
    tzroutine.itinerary.cache_clear()
    try:
        assert itinerary(ACT4) is None
        assert trips_of(itinerary(frozenset((104, 105)))) == [('Izual', 103, (103, 104, 105))]
    finally:
        tzroutine.itinerary.cache_clear()
