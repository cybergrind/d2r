"""Duriel's Lair by the true tomb's Orifice (levels/handlers/tal_rasha.py DURIEL, 2026-10-21; macros/acts/act2.py). The
catalogue with the switch on: each tomb's way on is the Orifice's portal into the lair, done where the tomb has no
Orifice (its mark absent), so only the true tomb's run goes in, whichever tomb it is; the lair's run fights Duriel,
loots, and the Town Portal takes the tour back to the tombs left. The switch on since 2026-10-21 ~14:45 (the player:
"after that shard's stack go to 90, let's use act2 shards", "make sure that we're focused on the correct finishing the
act and killing boss"); off: the catalogue as before."""

import pytest

from inventory_tracking.levels.handlers import tal_rasha
from inventory_tracking.levels.model import DURIEL_PORTAL, ORIFICE, LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import object_spots
from inventory_tracking.macros import acts, midgame, tzloop, tzroutine, zonenav
from inventory_tracking.macros.acts import act2
from inventory_tracking.macros.loop import LEAVE, TZ_LEVEL, TZ_LOOT, TZ_NEXT_LEVEL, TZ_PORTAL, TZ_SHARD, TZ_WAYPOINT
from inventory_tracking.macros.teleport import USES
from inventory_tracking.routes import catalog, check, progress as progress_module, tz_routes, zone_graph
from inventory_tracking.routes.catalog import act2 as catalogue
from inventory_tracking.routes.model import USE
from inventory_tracking.routes.progress import Facts, done
from inventory_tracking.routes.tz_groups import installed_active_zones
from tests.inventory_tracking.macros import test_tzloop
from tests.inventory_tracking.macros.test_tzloop import CANYON, LUT_GHOLEIN, NEAREST, TAL_RASHAS, TOMBS, Script


LAIR = 73
TRUE_TOMB = 72  # the fixture's tour order puts it third (NEAREST: 69, 66, 72, ...)
TALRASHA_PRESETS = (460, 461, 462, 463)  # lvlprest 'Act 2 - Tomb Talrasha W/E/S/N'
# The act 2 game's levels after the tombs' tour under zone navigation (test_act2.py's without it): the Arcane
# Sanctuary, the Palace Cellars, the Harem, the sewers, the act's rest (the Lost City's children by the graph: the
# Ancient Tunnels, then the Valley of Snakes and the Claw Viper Temple). The rotation's Catacombs root holding Andariel
# right after the act's boss (zonenav.py ROTATION_BOSSES_FIRST, 2026-10-22), then the rest of the Catacombs from act 1
# (ROTATION_FIRST; the Cathedral's trip: tzroutine.py SKIPPED_TRIPS), then the act's rest
ACT_REST = (35, 36, 37, 32, 33, 34, 74, 52, 53, 54, 51, 50, 48, 49, 47, 42, 56, 57, 60, 43, 62, 63, 64, 44, 65, 45, 58,
            61, 41, 55, 59)  # fmt: skip


def duriel_on(monkeypatch: pytest.MonkeyPatch) -> tuple:
    """The catalogue with the switch on in every module that took it (and their caches cleared)."""
    routes = tuple(catalogue.tombs(True) if route.name == "Tal Rasha's Tombs" else route for route in catalog.ROUTES)
    for module in (catalog, tz_routes, zone_graph, tzroutine, acts.engine, test_tzloop):
        monkeypatch.setattr(module, 'ROUTES', routes)
    monkeypatch.setitem(acts.SCRIPTS, 2, act2.script(True))
    for cached in (tzroutine.itinerary, tzroutine.boss_areas, tzroutine.stand_areas, zone_graph.way, zonenav.graph_of):
        cached.cache_clear()
    return routes


@pytest.fixture(autouse=True)
def caches_cleared():
    yield
    for cached in (tzroutine.itinerary, tzroutine.boss_areas, tzroutine.stand_areas, zone_graph.way, zonenav.graph_of):
        cached.cache_clear()


def test_the_switch_is_on_and_off_the_catalogue_is_as_before():
    assert tal_rasha.DURIEL is True
    assert catalogue.tombs() == catalogue.tombs(True)
    assert any(script.area == LAIR for script in catalogue.tombs().scripts)
    assert LAIR not in catalog.EXEMPT
    assert act2.script(True) == act2.SCRIPT
    assert tal_rasha.orifice() == tal_rasha.orifice(True)
    route = catalogue.tombs(False)
    assert all(script.area != LAIR for script in route.scripts)
    assert all(stage.kind != USE for script in route.scripts for stage in script.stages)
    assert tal_rasha.orifice(False).use == 0
    assert tal_rasha.orifice(False).thing == 0


def test_the_orifice_is_placed_by_each_talrasha_layout_and_its_mark_clicks_the_portal():
    # The installed game's TombXTalrasha.ds1 files, one per turn (levels/data/preset_objects.json, rebuilt 2026-10-21)
    for preset in TALRASHA_PRESETS:
        assert len(object_spots(preset, None, ORIFICE)) == 1
    spec = tal_rasha.orifice(True)
    assert (spec.thing, spec.use, spec.each, spec.optional) == (ORIFICE, DURIEL_PORTAL, True, True)
    use = USES[DURIEL_PORTAL]
    assert use.leaves
    assert use.near >= 14  # the portal stands 13 west and 3 south of the Orifice (D2MOO A2Q6.cpp): 13.3 units


def test_a_tomb_without_the_talrasha_room_has_no_orifice_and_the_true_one_has_it_on_the_object():
    handler = tal_rasha.handlers(True)[0]
    here = Location(TRUE_TOMB, 0, 1000, 1000)
    other = LevelSnapshot(here, (Room(470, 190, 190, 16, 16, 0),))  # a Kaa tomb
    assert 'Orifice' in handler.guide(other).absent
    true = LevelSnapshot(here, (Room(463, 190, 190, 16, 16, 0),))
    guidance = handler.guide(true)
    orifice = [poi for poi in guidance.pois if poi.label == 'Orifice']
    assert len(orifice) == 1
    assert orifice[0].use == DURIEL_PORTAL
    assert orifice[0].spot == (190 + 18 / 5, 190 + 58 / 5)  # TombNTalrasha.ds1's (18, 58), in tiles
    assert 'Orifice' not in guidance.absent


def test_the_orifices_portal_stage_is_done_where_the_tomb_has_none():
    route = catalogue.tombs(True)
    tomb = next(script for script in route.scripts if script.area == 66)
    way_in, way_back = tomb.stages
    assert (way_in.kind, way_in.mark, way_in.to) == (USE, 'Orifice', LAIR)
    assert way_back.back
    assert done(66, way_in, Facts()) is False
    assert done(66, way_in, Facts(finished=frozenset({(66, 'Orifice')}))) is True  # Progress.absent
    assert done(66, way_in, Facts(entered=frozenset({LAIR}))) is True
    tracker = progress_module.Progress([route])
    tracker.note('g', 66)
    step = tracker.step(66)
    assert step is not None
    assert step.stage == way_in
    tracker.absent(66, 'Orifice')
    step = tracker.step(66)
    assert step is not None
    assert step.stage == way_back


def test_the_catalogue_with_the_switch_on_is_sound(monkeypatch):
    routes = duriel_on(monkeypatch)
    on = tal_rasha.handlers(True)[0]
    known = check.handler_for
    monkeypatch.setattr(check, 'handler_for', lambda area: on if area in on.areas else known(area))
    exempt = {area: why for area, why in catalog.EXEMPT.items() if area != LAIR}
    assert check.problems(routes, exempt) == []


def test_the_tal_rashas_zone_tours_the_tombs_then_the_lair(monkeypatch):
    duriel_on(monkeypatch)
    zone = next(zone for zone in installed_active_zones() if zone.name == 'Act2-TalRashas')
    plan = tzroutine.itinerary(frozenset(zone.core))
    assert plan is not None
    [trip] = plan.excursions
    assert trip.areas == (CANYON, *TOMBS, LAIR)
    assert (trip.hub, trip.tours) == (CANYON, TOMBS)
    assert plan.skipped == ()
    # Duriel's trip, the act's boss's (tzroutine.py BOSS_FIRST) is the same tour
    found = tz_routes.route_excursion(zone, "Tal Rasha's Tombs", LAIR)
    assert found is not None
    assert not found.blockers
    assert (found.waypoint, found.terminal) == (CANYON, LAIR)


def test_the_act_2_plan_has_no_duriel_step_skipped_with_the_switch_on(monkeypatch, caplog):
    duriel_on(monkeypatch)
    from tests.inventory_tracking.macros.acts.harness import plan_of, trips_of

    with caplog.at_level('INFO'):
        plan = plan_of(monkeypatch, 2)
    assert trips_of(plan)[0] == ("Tal Rasha's Tombs", CANYON, (CANYON, *TOMBS, LAIR))
    said = [record.getMessage() for record in caplog.records]
    assert not any(line.startswith('Macro: act: act 2 step') for line in said)
    assert LAIR not in dict(plan.skipped)


def canyon_game(monkeypatch: pytest.MonkeyPatch, true_tomb: int = TRUE_TOMB) -> Script:
    """The rotation's Act2-TalRashas game from Lut Gholein (test_tzloop.py's Canyon game) with the switch on: the tour
    through the nearest entrance not entered; a tomb's run notes the Orifice absent but in `true_tomb`, whose run ends
    through the portal into the lair; a tomb's way on is its way back; the lair's run kills Duriel."""
    duriel_on(monkeypatch)
    game = Script(LUT_GHOLEIN, monkeypatch, zone=TAL_RASHAS)

    def on_run(area: int) -> None:
        if area in TOMBS and area != true_tomb:
            game.progress.absent(area, 'Orifice')  # card_goal.py `absent`: the level's rooms hold no Talrasha room
        if area == true_tomb:
            # The run's last route stage, the Orifice's `use`: through its portal (as the Stony Field's run goes
            # through the Cairn Stones into Tristram, the Tristram TZ of 13:33 on 2026-10-20)
            game.go('portal', LAIR)
        if area == LAIR:
            game.killed.add('Duriel')

    def door() -> None:
        here = game.area
        step = game.progress.step(here)
        if here in TOMBS and step is not None and step.stage.to == LAIR:
            game.go('portal', LAIR)
        elif here != CANYON:
            game.go('back', CANYON)
        else:
            used = {place for _, _, place in game.progress.facts.used}
            tomb = next(level for level in NEAREST if (float(level), 0.0) not in used)
            game.progress.used(CANYON, 'Tomb', (float(tomb), 0.0), ())
            game.go('tomb', tomb)

    game.on_run = on_run
    game.door = door
    return game


def test_a_canyon_game_goes_into_the_lair_from_the_true_tomb_kills_duriel_and_tours_the_rest(monkeypatch):
    game = canyon_game(monkeypatch)
    legs = [game.leg() for _ in range(60) if game.play.world.in_game]
    legs = legs[: legs.index(LEAVE) + 1]

    third = NEAREST.index(TRUE_TOMB)
    assert [area for what, area in game.calls if what == 'tomb'] == list(NEAREST)
    assert game.runs == [CANYON, *NEAREST[: third + 1], LAIR, *NEAREST[third + 1 :]]
    assert game.calls[game.calls.index(('tomb', TRUE_TOMB)) + 1] == ('portal', LAIR)  # into the lair, no way back
    after = game.calls[game.calls.index(('portal', LAIR)) + 1 :]
    assert after[:2] == [('portal', LUT_GHOLEIN), ('waypoint', CANYON)]  # home, then the tour's hub again
    assert 'Duriel' in game.killed
    assert legs[0] == TZ_WAYPOINT
    assert TZ_LOOT in legs  # Duriel's drops
    assert TZ_PORTAL in legs
    assert legs.count(TZ_LEVEL) == 1 + len(TOMBS) + 1
    assert TZ_NEXT_LEVEL in legs
    assert set(TOMBS) <= game.loop.agenda.finished


def test_a_true_tomb_toured_last_leaves_the_game_from_the_lair(monkeypatch):
    game = canyon_game(monkeypatch, true_tomb=NEAREST[-1])
    legs = [game.leg() for _ in range(60) if game.play.world.in_game]
    legs = legs[: legs.index(LEAVE) + 1]

    assert game.runs == [CANYON, *NEAREST, LAIR]
    assert game.calls[-1] == ('portal', LAIR)  # no Town Portal after: no tomb is left, Save and Exit from the lair
    assert legs[-1] == LEAVE
    assert 'Save and Exit' in game.play.said


@pytest.mark.parametrize('true_tomb', catalogue.TOMBS)
def test_under_zone_navigation_the_lair_is_entered_from_the_true_tomb_only(monkeypatch, true_tomb):
    # routes/zone_graph.py (2026-10-21): the lair is the tour's side level (`Node.side`), under the Canyon, entered by
    # the true tomb's Orifice only, judged by its own policy once the tour is over (tzroutine.py `trip_of`). The whole
    # Shard: Act 2 game for each place of the true tomb (harness.py `ZoneWalk`: the other tombs read without the
    # Orifice; the true tomb's run ends through its portal): the shard, every level of the act script once, Duriel
    # killed once, the lair entered by that portal alone, the game left at the end
    from tests.inventory_tracking.macros.acts.harness import ActGame
    from tests.inventory_tracking.macros.acts.test_act2 import tomb_entrances

    monkeypatch.setattr(zonenav, 'ACTS', frozenset({2}))  # zone navigation on for act 2, as live (pinned off in tests)
    # The order of before 2026-10-23: the Canyon's tombs all toured before the rotation (zonenav.py ROTATION_ANY_ACT
    # puts the rotation right after Duriel, the tombs left after it: test_rotation_zone.py)
    monkeypatch.setattr(zonenav, 'ROTATION_ANY_ACT', False)
    act = ActGame(2, monkeypatch, true_tomb=true_tomb)
    tomb_entrances(act)
    walk = act.play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.legs[0] == TZ_SHARD
    assert walk.shard == [2]
    third = NEAREST.index(true_tomb) + 1
    assert walk.runs == [CANYON, *NEAREST[:third], LAIR, *NEAREST[third:], *ACT_REST]  # each level once
    assert [move for move in walk.moves if move[1] == LAIR] == [('portal', LAIR)]  # no other way in
    into = walk.moves.index(('portal', LAIR))
    assert walk.moves[into - 1] == ('tomb', true_tomb)  # from the true tomb, whichever it is
    # Home by the Town Portal; the Canyon's waypoint again while a tomb is left, else on to the Arcane Sanctuary
    assert walk.moves[into + 1 : into + 3] == [('portal', LUT_GHOLEIN), ('waypoint', CANYON if third < 7 else 35)]
    assert walk.kills.count('Duriel') == 1
    assert walk.kills[0] == 'Duriel'
    assert walk.kills[1] == 'Andariel'  # the rotation's boss right after the act's (zonenav.py ROTATION_BOSSES_FIRST)
    assert walk.legs[-1] == LEAVE


def test_tombs_turned_under_the_game_are_cleared_not_blocked_and_duriel_is_killed(monkeypatch, caplog):
    # cyberg65 2026-10-22 19:52-19:59 (rca/2026-10-22/tombs-findings.md): a Shard: Act 1 game rotated into
    # Act2-TalRashas, the zone no longer terrorized as the Canyon's run ended, kept for Duriel (tzloop.py BOSS_ZONES).
    # Each tomb was worked on the way (one run), "cleared" by the zone, then "blocked: entered and left unfinished" back
    # in the Canyon: the hub's rule read the agenda's tour flag (`explored`, never set on a way on) and not the zone's
    # verdict. A finished tomb is never blocked; the tour goes on to the true tomb and Duriel
    import logging

    from tests.inventory_tracking.macros.acts.harness import ZoneWalk, crossing
    from tests.inventory_tracking.macros.acts.test_bosses import TAL_RASHAS, TOWER

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(zonenav, 'ROTATION', True)
    walk = crossing(ZoneWalk(monkeypatch, TAL_RASHAS))
    game = walk.game
    game.progress.wanted = lambda level: level in game.zone  # the tracker's read, as it turns

    def on_run(area: int) -> None:
        if area == CANYON:
            game.zone = TOWER  # the Tal Rasha rotation turned: its tombs kept for Duriel
        elif area in TOMBS:
            # Worked on the way (agenda.py ON_THE_WAY: Duriel alive under it), as live: the run reads the tomb's map
            # but tours no rooms, so runner.py `_zone_seen` notes it mapped, never explored
            game.unmapped.add(area)
            game.loop.agenda.mapped.add(area)

    walk.on_run = on_run
    played = walk.play()

    assert played.stopped is None, (played.stopped, played.where)
    assert 'Macro: zone: turned and kept in the plan for their bosses: Act2-TalRashas (Duriel' in caplog.text
    assert 'entered and left unfinished' not in caplog.text
    assert 'Duriel' in played.kills
    assert all(played.runs.count(tomb) <= 1 for tomb in TOMBS)


# Game cyberg65 on 2026-10-22 (rca/2026-10-22/tombs-policy-findings.md): a Shard: Act 1 game rotated into
# Act2-TalRashas, the zone turned as the Canyon's run ended, and the tombs were worked on the way for Duriel (one run
# each, never toured), the true tomb the fifth, Duriel killed at 19:59:56. The rule of before the 20:04 fix blocked the
# false tombs "entered and left unfinished" (19:54-19:58). At 21:40:32 an Eastern shard over the limit terrorized act 2
# (actloop.py OVERFLOW): every act 2 level owed under the act's policy, which tours the rooms. The tombs' state of the
# way on (and the old blocks, carried by the game's record over the 20:26-21:38 restarts) read as their verdict: the
# act's tombs unplayed
COLD_TRUE_TOMB = 71  # the fixture's tour order puts it fifth (NEAREST_TOMBS: 69, 66, 72, 67, 71, ...), as live


def worked_on_the_way_then_owed(monkeypatch, restart: bool):
    """The turned tombs' game up to Duriel's death and the Town Portal home, then act 2 terrorized by an overflow
    shard; with `restart` the game's record kept by a service of before POLICY_NOW (no policies, the old rule's blocks
    on the false tombs) and taken up by a new loop. (walk, the tombs entered on the way, the runs made before)."""
    from inventory_tracking.macros.agenda import TOWNS
    from tests.inventory_tracking.macros.acts.harness import NEAREST_TOMBS, ZoneWalk, crossing
    from tests.inventory_tracking.macros.acts.test_bosses import TAL_RASHAS, TOWER
    from tests.inventory_tracking.macros.acts.test_rotation_zone import restarted

    monkeypatch.setattr(zonenav, 'ROTATION', True)
    monkeypatch.setattr(zonenav, 'ACTS', frozenset({2}))  # act 2 by the zone's graph, as live
    walk = crossing(ZoneWalk(monkeypatch, TAL_RASHAS, true_tomb=COLD_TRUE_TOMB))
    game = walk.game
    game.loop.records = game.book
    game.progress.wanted = lambda level: level in game.zone

    def on_run(area: int) -> None:
        if area == CANYON and 2 not in game.loop.agenda.acts:
            game.zone = TOWER  # the Tal Rasha rotation turned: its tombs kept for Duriel
        if area not in {CANYON, *TOMBS, LAIR}:
            return
        if 2 in game.loop.agenda.acts:
            game.unmapped.discard(area)  # under the act's policy: its rooms toured
        else:
            game.unmapped.add(area)  # worked on the way (19:52:14 on): the map read, no room toured
            game.loop.agenda.mapped.add(area)

    walk.on_run = on_run
    before = walk.play(until=lambda played: 'Duriel' in played.killed and played.area in TOWNS)
    assert before.stopped is None, (before.stopped, before.where)
    agenda = game.loop.agenda
    on_the_way = sorted(set(TOMBS) & agenda.entered)
    assert on_the_way == sorted(NEAREST_TOMBS[: NEAREST_TOMBS.index(COLD_TRUE_TOMB) + 1])
    # The Eastern shard over the limit at the town stop (actloop.py OVERFLOW): act 2 planned whatever the client reads
    agenda.acts, agenda.overflow = (2,), {2: 'used'}
    # Its levels read terrorized from here, as live (tzloop.py MANUAL_TURNED: one read not terrorized is finished)
    from inventory_tracking.routes.tz_groups import manual_zone

    act2 = manual_zone(2)
    assert act2 is not None
    game.zone = game.zone | frozenset(act2.areas)
    if restart:
        false_tombs = [tomb for tomb in on_the_way if tomb != COLD_TRUE_TOMB]
        for tomb in false_tombs:
            agenda.blocked[tomb] = tzloop.LEFT_UNFINISHED  # the hub's rule of before the 20:04 fix
        midgame.keep(game.loop, game.progress)
        key = midgame.key_of(game.loop.game_id)
        assert key is not None
        part = game.book.record(key)['loop']
        part['agenda'] = {name: value for name, value in part['agenda'].items() if name != 'worked_under'}
        game.book.record_note(key, 'loop', part)  # as a service of before POLICY_NOW kept it
        restarted(walk, game.loop.store)
        game.progress.wanted = lambda level: level in game.zone
    return walk, on_the_way, len(before.runs)


@pytest.mark.parametrize('restart', [False, True], ids=['same-service', 'restarted'])
@pytest.mark.parametrize('on', [True, False], ids=['policy-now', 'off'])
def test_tombs_worked_on_the_way_then_owed_by_an_overflow_shard_are_played_under_the_acts_policy(
    monkeypatch, caplog, on, restart
):
    caplog.set_level('INFO')
    monkeypatch.setattr(tzloop, 'POLICY_NOW', on)
    monkeypatch.setattr(midgame, 'POLICY_UNKNOWN', on)
    walk, on_the_way, ran = worked_on_the_way_then_owed(monkeypatch, restart)
    caplog.clear()
    played = walk.play(legs=600)
    after = played.runs[ran:]
    agenda = walk.game.loop.agenda

    if not on:
        # The defect: back in the Canyon the tombs of the way on are blocked "entered and left unfinished" (the hub's
        # rule judging their way on's state under the act's touring policy; restarted, the old rule's blocks are kept
        # too), never played again; the true tomb blocked, Duriel's Lair is never reached and the loop goes between
        # the Town Portal and the Canyon's waypoint until it stops
        assert 'entered and left unfinished' in caplog.text
        assert not set(on_the_way) & set(after)
        assert played.stopped == 'TZ Town Portal again and again in cyber32: nothing came of it'
        return
    assert played.stopped is None, (played.stopped, played.where)
    assert played.legs[-1] == LEAVE
    assert 'entered and left unfinished' not in caplog.text
    assert set(TOMBS) | {CANYON, LAIR} <= set(after)  # every tomb under the act's policy, the Canyon and the lair too
    assert all(after.count(tomb) == 1 for tomb in TOMBS)
    for tomb in on_the_way:
        assert f"Tal Rasha's Tomb ({tomb}) was worked" in caplog.text
        assert agenda.worked_under[tomb] in zonenav.TOURING
    assert not set(TOMBS) & agenda.blocked.keys()
    assert played.kills.count('Duriel') == 1  # dead already: never fought again
    if restart:
        assert 'the record kept no policy' in caplog.text
        assert 'taken up after a restart' in caplog.text


def test_a_tomb_judged_afresh_then_left_unfinished_under_the_acts_policy_is_blocked(monkeypatch, caplog):
    # The hub's rule for what it is meant for: entered again under the act's policy, its run cut short (back in the
    # Canyon by its waypoint, a trip to town and back) and which mark leads back is not known: blocked, said, the tour
    # goes on with the others, and the block stays (no second judging afresh: its policy has not changed)
    caplog.set_level('INFO')
    walk, on_the_way, ran = worked_on_the_way_then_owed(monkeypatch, restart=False)
    game, first = walk.game, NEAREST[0]
    assert first in on_the_way
    worked = walk.on_run
    cut: list[int] = []

    def on_run(area: int) -> None:
        worked(area)
        if area == first and not cut:
            cut.append(area)
            game.unmapped.add(area)  # its rooms not all seen
            game.go('waypoint', CANYON)

    walk.on_run = on_run
    caplog.clear()
    played = walk.play(legs=600)
    after = played.runs[ran:]

    assert played.stopped is None, (played.stopped, played.where)
    assert played.legs[-1] == LEAVE
    assert game.loop.agenda.blocked[first] == tzloop.LEFT_UNFINISHED
    assert f"Tal Rasha's Tomb ({first}) blocked: entered and left unfinished" in caplog.text
    assert caplog.text.count(f"Tal Rasha's Tomb ({first}) was worked") == 1
    assert after.count(first) == 1
    assert set(TOMBS) - {first} <= set(after)
