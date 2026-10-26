"""The act script engine (macros/acts/engine.py), the registry (macros/acts/__init__.py) and the act kinds
(loop.py ACT_KINDS): the player, 2026-10-20 ~22:50: "could you implement shards run for every act ... we probably can
separate some high level architecture into reusable framework"."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from inventory_tracking.macros import actloop, acts, tzloop, tzroutine
from inventory_tracking.macros.acts.engine import AFTER, WORKED, ActPlan, ActScript, Rest, Trip, act_trips, check
from inventory_tracking.macros.loop import ACT4, ACT_KINDS, TZ_KINDS, coming_kinds, loop_kinds
from inventory_tracking.routes.tz_groups import manual_zone
from tests.inventory_tracking.macros.acts.harness import plan_of, trips_of


TESTS = Path(__file__).parent


def zone(act: int):
    found = manual_zone(act)
    assert found is not None
    return found


@pytest.mark.parametrize('act', range(1, 6))
def test_every_act_has_a_sound_script_and_a_ready_one_has_its_test(act):
    script = acts.script_of(act)
    assert script is not None
    assert check(script, act) == []
    if script.ready:
        assert (TESTS / f'test_act{act}.py').exists()


def test_one_kind_per_act_on_actloop_with_its_shard():
    assert list(ACT_KINDS) == ['act1', 'act2', 'act3', 'act4', 'act5']
    assert [actloop.act_of(kind) for kind in ACT_KINDS.values()] == [1, 2, 3, 4, 5]
    assert [kind.word for kind in ACT_KINDS.values()] == ['ACT1', 'ACT2', 'ACT3', 'ACT4', 'ACT5']
    assert {kind.name for kind in ACT_KINDS.values()} == {f'Shard: Act {act}' for act in range(1, 6)}
    assert set(ACT_KINDS) <= TZ_KINDS
    assert all(kind.agenda and kind.packaged for kind in ACT_KINDS.values())
    # act 1's 37 levels have their own cap (loop.py ACT_SECONDS), the others the shared one
    assert [kind.game_seconds for kind in ACT_KINDS.values()] == [3900.0, 2700.0, 3600.0, 2700.0, 3600.0]
    assert ACT_KINDS['act4'] is ACT4


def test_an_act_kind_is_offered_once_its_script_is_ready(monkeypatch):
    offered = {key for key in loop_kinds() if key in ACT_KINDS}  # the shard act kinds (not act2tz: test_act2_alone)
    assert offered == {f'act{act}' for act in range(1, 6) if acts.ready(act)}
    assert 'act4' in offered
    assert [coming.key for coming in coming_kinds()] == sorted({*ACT_KINDS} - offered)
    one = acts.script_of(1)
    assert one is not None
    monkeypatch.setitem(acts.SCRIPTS, 1, ActScript(1, one.steps, ready=False))
    assert 'act1' not in loop_kinds()
    assert 'act1' in [coming.key for coming in coming_kinds()]
    monkeypatch.setitem(acts.SCRIPTS, 1, ActScript(1, one.steps, ready=True))
    assert 'act1' in loop_kinds()
    assert 'act1' not in [coming.key for coming in coming_kinds()]
    monkeypatch.setattr(actloop, 'ENABLED', False)
    assert not any(key.startswith('act') for key in loop_kinds())
    monkeypatch.setattr(actloop, 'ENABLED', True)
    monkeypatch.setattr(tzloop, 'ENABLED', False)
    assert not any(key.startswith('act') for key in loop_kinds())


def test_a_script_not_ready_leaves_the_act_to_the_generic_boss_first_order(monkeypatch):
    monkeypatch.setitem(acts.SCRIPTS, 3, ActScript(3, (), ready=False))
    tzroutine.itinerary.cache_clear()
    generic = tzroutine.itinerary(zone(3).core)
    assert generic is not None
    monkeypatch.setitem(acts.SCRIPTS, 3, ActScript(3, (Rest(levels=(76, 77)),), ready=False))
    tzroutine.itinerary.cache_clear()
    assert tzroutine.itinerary(zone(3).core) == generic
    scripted = plan_of(monkeypatch, 3)  # the same script, forced ready: its order
    assert trips_of(scripted)[0][2][-1] in (76, 77)


@pytest.mark.parametrize('switch', ['ACT_SCRIPTS', 'BOSS_FIRST', 'BOSS_NEAREST'])
def test_the_switches_turn_the_scripts_off(monkeypatch, switch):
    monkeypatch.setitem(acts.SCRIPTS, 4, ActScript(4, (Rest(zone='Act4_OuterSteppes'),), ready=True))
    monkeypatch.setattr(tzroutine, switch, False)
    assert tzroutine._scripted(4, zone(4)) is None


def test_a_missing_step_is_skipped_and_said_and_its_levels_fall_to_the_rest(caplog):
    script = ActScript(
        2,
        (
            Trip('Duriel', 73, missing="no route into Duriel's Lair yet (the Orifice)"),
            Trip('No such route', 74),
            Rest(zone='Act2-ArcaneSanctuary'),
        ),
    )
    with caplog.at_level('INFO'):
        trips, uncovered = act_trips(script, zone(2))
    said = "Macro: act: act 2 step 1 (Duriel to 73): no route into Duriel's Lair yet (the Orifice): skipped"
    assert said in caplog.text
    assert "Macro: act: act 2 step 2 (No such route to 74): no catalogue route 'No such route': skipped" in caplog.text
    # The tombs' route reaches the Lair (levels/handlers/tal_rasha.py DURIEL, on since 2026-10-21), from no step here:
    # the Rest's zone plays the tour, the Lair on it
    assert 73 not in uncovered
    first, _ = trips[0]
    assert first.route == 'Summoner'  # the Arcane Sanctuary's rest came first, then the act's rest
    covered = {area for trip, _ in trips for area in trip.covers}
    assert covered | set(uncovered) >= set(zone(2).areas)


def test_a_trip_crossed_after_works_its_way_right_after_and_one_worked_on_the_way_does_not():
    after, _ = act_trips(ActScript(3, (Trip('Mephisto', 102, crossed=AFTER),)), zone(3))
    assert [(trip.route, trip.waypoint, trip.terminal) for trip, _ in after[:2]] == [
        ('Mephisto', 101, 102),
        ('Mephisto', 101, 101),  # Durance 2 after him
    ]
    assert after[0][1] == frozenset((101,))
    worked, _ = act_trips(ActScript(3, (Trip('Mephisto', 102, waypoint=101, crossed=WORKED),)), zone(3))
    assert worked[0][1] == frozenset()
    assert all(trip.terminal != 101 for trip, _ in worked[1:3])


def test_a_trip_from_a_named_waypoint_and_a_path_none():
    trips, _ = act_trips(ActScript(1, (Trip('Andariel', 37, waypoint=32, crossed=WORKED),)), zone(1))
    first, passes = trips[0]
    assert (first.waypoint, first.terminal, passes) == (32, 37, frozenset())


def test_a_trip_with_no_path_from_its_waypoint_is_said(caplog):
    with caplog.at_level('INFO'):
        trips, _ = act_trips(ActScript(1, (Trip('Andariel', 37, waypoint=6),)), zone(1))
    assert "route 'Andariel' has no path from waypoint 6 to 37: skipped" in caplog.text
    assert trips  # the act's rest planned all the same


def test_an_act_file_may_declare_its_own_step():
    @dataclass(frozen=True)
    class Countess:
        label: str = 'the Countess, the Tower worked on the way'

        def plan(self, act: ActPlan) -> None:
            trip = act.route_trip('Countess', 25)
            if trip is not None:
                act.add(trip)

    trips, _ = act_trips(ActScript(1, (Countess(),)), zone(1))
    first, passes = trips[0]
    assert (first.route, first.waypoint, first.terminal, passes) == ('Countess', 6, 25, frozenset())
    assert not any(trip.route == 'Countess' for trip, _ in trips[1:])  # its levels worked: not planned again


def test_a_trip_to_a_toured_level_tours_them_all_one_by_one(monkeypatch):
    # The player, 2026-10-20 ~22:50: "act2 shard -> canyon of the magic -> toms ... -> duriel -> rest of tombs"
    tombs = (66, 67, 68, 69, 70, 71, 72)
    monkeypatch.setitem(acts.SCRIPTS, 2, ActScript(2, (Trip("Tal Rasha's Tombs", 66, crossed=WORKED),)))
    plan = plan_of(monkeypatch, 2)
    first = plan.excursions[0]
    assert (first.route, first.waypoint, first.hub, first.tours) == ("Tal Rasha's Tombs", 46, 46, tombs)
    # Duriel's Lair on the tour since 2026-10-21 (levels/handlers/tal_rasha.py DURIEL): the true tomb's Orifice
    assert first.areas == (46, *tombs, 73)
    assert 73 not in dict(plan.skipped)
