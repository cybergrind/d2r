"""Zone navigation's judging and goals (macros/zonenav.py; macros/zone-nav-plan.md §3, §4), on Act 3's graph: a level
done only when judged so, children entered as the run passes, the climb of one floor, the Town Portal for a deep
chain's end."""

import pytest

from inventory_tracking.macros import zonenav
from inventory_tracking.macros.agenda import (
    LEVEL,
    LOOT,
    NEXT_LEVEL,
    PICKUP,
    PLUS,
    PLUS_WAY,
    PORTAL_TO_TOWN,
    TOWN_ROUTINE,
    TRANSIT,
    WALK_OUT,
    WAYPOINT,
)
from inventory_tracking.macros.tzroutine import Itinerary
from inventory_tracking.macros.zonenav import (
    UP_LEVEL,
    VISIT,
    LevelState,
    ZoneView,
    climbs,
    judge,
    next_child,
    own_work,
    produce,
    scripts,
)
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.model import ENTER, FIGHT, LOOT as LOOT_STAGE, STAND, USE, Stage, back, enter
from inventory_tracking.routes.progress import Facts, Progress
from inventory_tracking.routes.zone_graph import Chain, zone_graph


# Act 3's trips as its script plans them (acts/act3.py), the parts the cases use
GRAPH = zone_graph(
    'Act3-Manual',
    (
        Chain(101, (101, 102), frozenset((101, 102))),
        Chain(83, (83, 100), frozenset((83, 100))),
        Chain(81, (81, 82, 98), frozenset((81, 82, 98))),
        Chain(81, (81, 82, 99), frozenset((81, 82, 99))),
        Chain(81, (81, 96), frozenset((81, 96))),
        Chain(81, (81, 97), frozenset((81, 97))),
        Chain(80, (80, 92, 93), frozenset((80, 92, 93))),
        Chain(80, (80, 94), frozenset((80, 94))),
        Chain(80, (80, 95), frozenset((80, 95))),
    ),
)
DONE = LevelState(entered=True, mapped=True, explored=True, runs=1)


def judged(states: dict[int, LevelState], policies: dict[int, str] | None = None):
    return judge(GRAPH, states, lambda area, finished: (policies or {}).get(area, PLUS))


def done(*areas: int) -> dict[int, LevelState]:
    return dict.fromkeys(areas, DONE)


def view(area: int, states: dict[int, LevelState], **kwargs) -> ZoneView:
    return ZoneView(area, area in (75, 103), GRAPH, judged(states), **kwargs)


def kinds(goals) -> list[tuple[str, int | None]]:
    return [(goal.kind, goal.to) for goal in goals]


def test_the_switch_names_the_acts_played_by_the_graph(monkeypatch):
    plan = Itinerary('Act3-Manual + Act5-GlacialTrail', frozenset(), ())
    assert not zonenav.on(plan)
    monkeypatch.setattr(zonenav, 'ACTS', frozenset((3,)))
    assert zonenav.on(plan)
    assert not zonenav.on(Itinerary('Act1-Manual', frozenset(), ()))
    assert not zonenav.on(None)


def test_a_level_left_with_its_map_unread_is_not_done_then_blocked_after_its_tries():
    # The Forgotten Reliquary (28 hostiles) was "done" 0.2 s after arrival, its map not read (09:09:02 on 2026-10-21)
    once = judged({96: LevelState(entered=True, runs=1)})
    assert 96 not in once.finished
    assert kinds(produce(view(96, {96: LevelState(entered=True, runs=1)}))) == [(LEVEL, None)]
    twice = judged({96: LevelState(entered=True, runs=zonenav.MAP_TRIES)})
    assert 'map was never read' in twice.blocked[96]
    assert 96 in twice.finished


def test_a_parent_is_cleared_only_when_explored_and_every_child_cleared_or_blocked():
    states = done(81, 82, 98, 99, 96)
    assert 81 in judged(states).explored
    assert 81 not in judged(states).cleared  # the Forgotten Temple not entered
    states[97] = LevelState(entered=True, blocked='no click took its door')
    found = judged(states)
    assert 81 in found.cleared
    assert found.gaps(GRAPH, 81) == (97,)
    assert 'cleared, without [97]' in zonenav.said(GRAPH, found, 81)


def test_a_one_floor_child_is_entered_as_the_run_passes_a_deep_one_only_once_the_parent_is_explored():
    nothing = judged({})
    assert next_child(GRAPH, 81, nothing) == 96  # the temples: one floor
    assert next_child(GRAPH, 80, nothing) == 94  # the Sewers (two floors) last
    temples = judged(done(96, 97))
    assert next_child(GRAPH, 81, temples) is None  # Upper Kurast not explored yet: the Causeway waits
    assert next_child(GRAPH, 81, judged(done(81, 96, 97))) == 82
    assert next_child(GRAPH, 82, judged({})) == 98  # under the Causeway the fanes are one floor again


def test_a_level_crossed_to_its_boss_goes_into_the_boss_child_first():
    graph = zone_graph('Act4-Manual', (Chain(107, (107, 108), frozenset((107, 108)), passes=frozenset((107,))),))
    assert next_child(graph, 107, judge(graph, {}, lambda area, finished: PLUS)) == 108


def test_a_one_floor_child_done_climbs_back_and_a_deep_chains_end_takes_the_portal():
    found = judged(done(96))
    assert climbs(GRAPH, 96, found) == 81
    assert climbs(GRAPH, 96, found, no_back=(96,)) is None  # its way back failed: the Town Portal
    # the Sewers last in the Bazaar: from Level 2 one floor to Level 1 while it has rooms left ...
    assert climbs(GRAPH, 93, judged(done(80, 94, 95, 93) | {92: LevelState(entered=True, mapped=True, runs=1)})) == 92
    # ... none once it and the Bazaar are done: the root is done but for this branch, so no climb through them
    assert climbs(GRAPH, 93, judged(done(80, 94, 95, 92, 93))) is None
    # the Causeway's walk back to Upper Kurast is no floor
    assert climbs(GRAPH, 82, judged(done(82, 98, 99))) == 81


def test_the_goals_in_town_go_to_the_first_root_not_done_and_walk_out_of_a_town_root():
    assert kinds(produce(view(103, done(101, 102)))) == [(WAYPOINT, 83)]
    assert kinds(produce(view(103, {}, visit_due=True))) == [(TOWN_ROUTINE, None)]
    graph = zone_graph('Act4-Manual', (Chain(103, (103, 104, 105), frozenset((104, 105))),))
    town = ZoneView(103, True, graph, judge(graph, {}, lambda area, finished: PLUS))
    assert kinds(produce(town)) == [(WALK_OUT, 104)]


def test_the_goals_in_a_level_its_run_first_then_the_children_then_up_then_the_portal():
    # The run's script ends in the temple's way in, taken as the run passes it (`enter_at`) or after its rooms
    assert kinds(produce(view(81, {81: LevelState(entered=True, mapped=True, runs=0)}))) == [(LEVEL, None)]
    assert kinds(produce(view(81, done(81)))) == [(NEXT_LEVEL, 96)]  # explored: the temple left
    assert kinds(produce(view(96, {96: LevelState(entered=True, mapped=True)}))) == [(LEVEL, None)]
    assert kinds(produce(view(96, done(96)))) == [(UP_LEVEL, 81)]
    visit = produce(view(96, done(96), visit_due=True))
    assert kinds(visit) == [(PORTAL_TO_TOWN, None)]
    assert visit[0].exit == VISIT
    everything = done(*GRAPH.nodes)
    assert kinds(produce(view(95, everything))) == []  # the zone done: the game's end
    assert kinds(produce(view(93, done(101, 102, 83, 100, 81, 82, 98, 99, 96, 97, 80, 94, 95, 92, 93)))) == []
    rest = done(101, 102, 83, 100, 81, 82, 98, 99, 96, 97)
    assert kinds(produce(view(97, rest))) == [(PORTAL_TO_TOWN, None)]  # Upper Kurast done: the Bazaar next
    assert kinds(produce(view(96, done(96), sighted='a rune'))) == [(PICKUP, None), (UP_LEVEL, 81)]


def test_the_loot_stage_of_a_level_not_done_is_its_loot_goal():
    states = {83: LevelState(entered=True, mapped=True, runs=1, work=True)}
    assert kinds(produce(view(83, states, stage=LOOT_STAGE))) == [(LOOT, None)]


def test_a_way_on_policy_needs_its_route_work_done_not_every_room():
    states = {102: LevelState(entered=True, mapped=True, runs=1)}
    assert 102 in judged(states, {102: PLUS_WAY}).explored
    assert 102 not in judged(states, {102: PLUS}).explored
    assert 102 not in judged({102: LevelState(entered=True, mapped=True, work=True)}, {102: PLUS_WAY}).explored
    # Entered with no run yet: its run first (the Halls of Pain and of Anguish were explored on arrival, never run)
    assert 102 not in judged({102: LevelState(entered=True, mapped=True)}, {102: PLUS_WAY}).explored
    assert 100 in judged({100: LevelState(entered=True)}, {100: TRANSIT}).explored


def test_a_level_whose_runs_ran_out_is_explored_and_said_so():
    states = {96: LevelState(entered=True, mapped=True, runs=zonenav.runs_allowed(GRAPH.nodes[96]))}
    found = judged(states)
    assert 96 in found.cleared
    assert 96 in found.exhausted
    assert 'rooms left unseen' in zonenav.said(GRAPH, found, 96)


def base_of(area: int):
    progress = Progress(ROUTES)
    return progress.scripts.get(area)


def test_the_scripts_hold_own_work_the_next_childs_way_in_and_the_way_back():
    found = scripts(GRAPH, judged({}), base_of)
    uk = found[81][1]
    assert [(stage.kind, stage.mark, stage.to) for stage in uk.stages] == [(ENTER, 'Forgotten Reliquary', 96)]
    temple = found[96][1]
    assert [(stage.kind, stage.to, stage.back) for stage in temple.stages] == [(ENTER, 81, True)]
    travincal = found[83][1]
    assert [stage.kind for stage in travincal.stages] == [FIGHT, LOOT_STAGE, ENTER]
    durance = found[102][1]
    assert [stage.kind for stage in durance.stages] == [STAND, FIGHT, LOOT_STAGE, ENTER]  # back up to Level 2
    assert durance.stages[-1].back
    ended = scripts(GRAPH, judged(done(101)), base_of)[102][1]
    assert ended.stages[-1].kind == USE  # Level 2 done: Mephisto's Red portal ends the root
    assert ended.stages[-1].to == 103


def test_own_work_is_the_fights_stands_and_objects_not_done():
    found = base_of(102)
    assert found is not None
    _, script = found
    assert own_work(script, Facts(), frozenset())
    stood = Facts(stood=frozenset({(102, 'Red portal')}), looted=frozenset({102}))
    assert not own_work(script, stood, frozenset({'Mephisto'}))
    assert own_work(script, stood, None)  # the dead unknown: the fight counts as left


@pytest.mark.parametrize(
    ('area', 'levels'),
    [
        (81, {81, 82, 96, 97}),
        (96, {96, 81}),
        (82, {82, 81, 98, 99}),
        (98, {98, 82}),
        (92, {92, 80, 93}),
        (93, {93, 92}),
    ],
)
def test_a_run_may_cross_into_its_parent_and_children_only(area, levels):
    # Its own only ended Upper Kurast's run "Kurast Causeway leads off the trip" 30 times in 3 s, and the repeat guard
    # left the game (13:48:00 on 2026-10-21): the open passage to a child, or back up to the parent, is crossed by the
    # run toward its route stage's goal
    assert zonenav.allowed(GRAPH, area) == frozenset(levels)
    assert zonenav.allowed(GRAPH, 75) is None


def test_a_childs_way_in_is_gone_into_as_the_run_passes_it_only_under_the_switches(monkeypatch):
    plan = Itinerary('Act3-Manual', frozenset(), ())
    door = (5040.0, 5000.0)
    into = enter('Forgotten Reliquary', 96)
    assert zonenav.enter_at(plan, into, door) is None  # zone navigation off
    monkeypatch.setattr(zonenav, 'ACTS', frozenset((3,)))
    assert zonenav.enter_at(plan, into, door) == door
    assert zonenav.enter_at(plan, back('Upper Kurast', 81), door) is None  # the way back is the run's end, no detour
    assert zonenav.enter_at(plan, Stage(FIGHT, 'Council', boss='Ismail Vilehand'), door) is None
    assert zonenav.enter_at(plan, None, door) is None
    monkeypatch.setattr(zonenav, 'ENTER_PASSING', False)
    assert zonenav.enter_at(plan, into, door) is None


def test_a_root_cleared_walks_into_the_next_roots_levels_across_a_border_only_under_the_switch(monkeypatch):
    # Stage 3 (WALK_ROOTS): Travincal done, the next root Upper Kurast's Causeway joins it (routes/links.py BORDERS)
    found = judged(done(101, 102, 83, 100))
    assert kinds(produce(view(83, done(101, 102, 83, 100)))) == [(PORTAL_TO_TOWN, None)]  # off: the portal
    monkeypatch.setattr(zonenav, 'WALK_ROOTS', True)
    assert zonenav.walk_to(GRAPH, 83, found) == 82
    walk = produce(view(83, done(101, 102, 83, 100)))
    assert kinds(walk) == [(NEXT_LEVEL, 82)]
    assert walk[0].exit == zonenav.WALK
    script = scripts(GRAPH, found, base_of)[83][1]
    assert (script.stages[-1].kind, script.stages[-1].to) == (ENTER, 82)
    assert zonenav.walk_to(GRAPH, 83, found, no_walk=((83, 82),)) is None  # failed once: the portal
    assert zonenav.walk_to(GRAPH, 102, judged(done(101, 102))) is None  # Durance 3 joins no level of root 83 but 100
    assert zonenav.walk_to(GRAPH, 79, judged(done(*GRAPH.nodes))) is None  # nothing left


def test_the_time_budget_skips_the_smallest_children_first_and_never_where_the_character_is(monkeypatch):
    found = judged(done(101, 102, 83, 100))
    assert zonenav.over_budget(GRAPH, found, 1.0, (81,)) == ()  # off
    monkeypatch.setattr(zonenav, 'TIME_BUDGET', True)
    total = zonenav.left_seconds(GRAPH, found)
    assert zonenav.over_budget(GRAPH, found, total + 1, (81,)) == ()  # it fits
    skipped = zonenav.over_budget(GRAPH, found, total - 1, (81,))
    assert len(skipped) == 1
    smallest = min(
        (level for level in GRAPH.nodes if GRAPH.nodes[level].parent is not None and level not in found.finished),
        key=lambda level: (sum(zonenav.level_population(each) or 0 for each in GRAPH.subtree(level)), level),
    )  # by population, the lower level number on a tie
    assert skipped == (smallest,)
    everything = zonenav.over_budget(GRAPH, found, 0.0, (96,))
    assert 96 not in everything  # where the character is
    assert not set(everything) & {81, 80}  # roots are never skipped
    assert zonenav.over_budget(GRAPH, found, 0.0, (96,), protected=(98,)).count(82) == 0  # a route fight under it


# The Black Marsh's two deep children as Act 1's trips plan them (acts/act1.py): the Countess's tower and the Hole
MARSH = zone_graph(
    'Act1-Manual',
    (
        Chain(6, (6, 20, 21, 22, 23, 24, 25), frozenset((6, 20, 21, 22, 23, 24, 25))),
        Chain(6, (6, 11, 15), frozenset((6, 11, 15))),
    ),
)


def test_a_level_whose_child_is_deep_runs_first_with_no_way_back_then_goes_down(monkeypatch):
    # 23:18:58 on 2026-10-21: the Forgotten Tower (one room) entered, its script "back to Black Marsh" (the Hole
    # left), a walk onto the way out that did not move for 46 s (rca/2026-10-21/tower-stall-findings.md)
    entered = judge(MARSH, {6: DONE, 20: LevelState(entered=True)}, lambda area, finished: PLUS)
    assert 6 in entered.explored
    assert 20 not in entered.explored
    assert next_child(MARSH, 20, entered) is None  # the cellar waits for the tower's own run
    assert scripts(MARSH, entered, base_of)[20][1].stages == ()  # no way back up: the run's tour, then the verdict
    assert kinds(produce(ZoneView(20, False, MARSH, entered))) == [(LEVEL, None)]
    explored = judge(MARSH, {6: DONE, 20: DONE}, lambda area, finished: PLUS)
    down = scripts(MARSH, explored, base_of)[20][1].stages
    assert [(stage.kind, stage.to, stage.back) for stage in down] == [(ENTER, 21, False)]
    assert kinds(produce(ZoneView(20, False, MARSH, explored))) == [(NEXT_LEVEL, 21)]
    # A one-floor child under it is gone into as the run passes, as before (the Hole's Level 2)
    hole = scripts(MARSH, judge(MARSH, {6: DONE, 11: LevelState(entered=True)}, lambda a, f: PLUS), base_of)[11][1]
    assert [(stage.kind, stage.to) for stage in hole.stages] == [(ENTER, 15)]
    monkeypatch.setattr(zonenav, 'DEEP_AFTER_RUN', False)
    before = scripts(MARSH, entered, base_of)[20][1].stages
    assert [(stage.kind, stage.to, stage.back) for stage in before] == [(ENTER, 6, True)]  # the climb, as before


# The Worldstone Keep's trip as act 5's script plans it (acts/act5.py): the Keep 2 waypoint down to the Chamber
KEEP = zone_graph('Act5-Manual', (Chain(129, (129, 130, 131, 132), frozenset((129, 130, 131, 132))),))


def test_the_thrones_way_into_the_chamber_stays_the_routes_use_of_the_portal_under_the_switch(monkeypatch):
    # Games 4-6 at 09:13, 09:21, 09:27 on 2026-10-22 (rca/2026-10-22/baal-skipped-findings.md): the zone's `enter` held
    # neither portal gate (hunting/throne.py `wave_goal`, running/legs.py `throne_shut` read the route's `use`), the
    # press came with Lister's minions alive, the three tries burnt in 0.12 s and the game was left with Baal alive
    keep = judge(KEEP, done(129, 130), lambda area, finished: PLUS)
    throne = scripts(KEEP, keep, base_of)[131][1]
    assert [stage.kind for stage in throne.stages] == [STAND, FIGHT, LOOT_STAGE, USE]
    assert (throne.stages[-1].mark, throne.stages[-1].to) == ('Worldstone Chamber', 132)
    keep_3 = scripts(KEEP, keep, base_of)[130][1]
    assert keep_3.stages[-1].kind == ENTER  # every other way in as before
    monkeypatch.setattr(zonenav, 'PORTAL_USES', False)
    throne = scripts(KEEP, keep, base_of)[131][1]
    assert throne.stages[-1].kind == ENTER
    assert zonenav.enter_at(Itinerary('Act5-Manual', frozenset(), ()), throne.stages[-1], (0.0, 0.0)) is None


# --- the game's bosses (zonenav.py BOSSES_HOLD, ROTATION_BOSSES_FIRST, `boss_reach`; 2026-10-22) ---


def test_a_level_with_a_boss_alive_is_not_cleared_on_one_run_but_its_runs_for_it_are_bounded():
    # Durance 3 "tz+ on the way" judged explored once one run was made, Maffer Dragonhand alive (11 games,
    # rca/2026-10-22/boss-audit-findings.md §4 cause 4): BOSS_RUNS more runs for him, then the zone goes on and the
    # game's end stops the loop naming him (tzloop.py BOSS_STAYS)
    node = GRAPH.nodes[102]
    allowed = zonenav.runs_allowed(node)
    once = LevelState(entered=True, mapped=True, explored=True, runs=1, bosses=1)
    assert not zonenav.fully_explored(node, once, PLUS_WAY)
    assert 102 not in judged({101: DONE, 102: once}).cleared
    spent = LevelState(entered=True, mapped=True, explored=True, runs=allowed + zonenav.BOSS_RUNS, bosses=1)
    assert zonenav.fully_explored(node, spent, PLUS_WAY)
    found = judged({101: DONE, 102: spent})
    assert 102 in found.cleared
    assert 102 in found.bosses  # said, the level done for the navigation: the stop is the game's end
    assert zonenav.fully_explored(node, LevelState(entered=True, mapped=True, explored=True, runs=1), PLUS_WAY)
    # Blocked with its boss alive: finished for the navigation (it went back in until the repeat guard left the game)
    blocked = judged({101: DONE, 102: LevelState(entered=True, blocked='no click took its door', bosses=1)})
    assert 102 in blocked.finished


def test_without_bosses_hold_one_run_is_enough_as_before(monkeypatch):
    monkeypatch.setattr(zonenav, 'BOSSES_HOLD', False)
    once = LevelState(entered=True, mapped=True, explored=True, runs=1, bosses=1)
    assert zonenav.fully_explored(GRAPH.nodes[102], once, PLUS_WAY)


def test_a_rotations_boss_root_comes_right_after_the_shard_acts_boss_from_any_act():
    # Duriel was never killed in 16 TZ games: the Tal Rasha rotation's tombs root last behind the shard acts' 16 roots
    # from the Fortress, the zone turned before it (cyberr14 10-21 21:40, cyberr15 22:26)
    from inventory_tracking.macros.tzroutine import itinerary
    from inventory_tracking.routes.tz_groups import installed_active_zones, manual_zone

    tal_rashas = next(zone for zone in installed_active_zones() if zone.name == 'Act2-TalRashas')
    act3, act5 = manual_zone(3), manual_zone(5)
    assert act3 is not None
    assert act5 is not None
    plan = itinerary(act3.core | act5.core | tal_rashas.core, (3, 5))
    assert plan is not None
    graph = zonenav.graph_of(plan)
    assert graph.roots[-1] == 46  # the Canyon last, as before
    fortress = 103
    ordered = zonenav.play_order(graph, plan, fortress, {73})  # Duriel alive in the ledger
    mephisto = next(root for root in graph.roots if 102 in graph.subtree(root))
    assert ordered.roots[0] == mephisto  # the shard act's boss first ("we want to kill act boss first")
    assert ordered.roots[1] == 46  # then the rotation's tombs, Duriel's Lair under the Canyon
    assert sorted(ordered.roots) == sorted(graph.roots)
    assert zonenav.play_order(graph, plan, fortress) is graph  # no boss alive there: as before


def test_a_tomb_holds_duriels_lair_and_a_level_off_the_graph_only_itself():
    from inventory_tracking.macros.tzroutine import itinerary
    from inventory_tracking.routes.tz_groups import installed_active_zones

    tal_rashas = next(zone for zone in installed_active_zones() if zone.name == 'Act2-TalRashas')
    plan = itinerary(tal_rashas.core)
    assert plan is not None
    graph = zonenav.graph_of(plan)
    assert 73 in zonenav.boss_reach(graph, 66)  # each tomb is a way into the Lair (`Node.sources`)
    assert 73 in zonenav.boss_reach(graph, 46)
    assert zonenav.boss_reach(graph, 999) == frozenset((999,))
