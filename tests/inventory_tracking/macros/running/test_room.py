"""The no-room routine every activity shares (macros/running/room.py; the player, 2026-10-19: "EVERY loop and activity
should have the same routines for situations when we don't have space: move to cube, if no space after that - go to
town and do town routine"). 20:24:03 that evening (runs/alt-d/20261019T172230Z-8c93dd57): a terror zone cleared by
hand with the KP_1 run left a Magic Kriss, Feral Claws and a Wire Fleece "left on the ground" and stood by a Shael Rune
with no trip to follow."""

import threading
from dataclasses import replace

import pytest

from inventory_tracking.game.records import VALUABLE, Drop, Loot
from inventory_tracking.macros import tzloop
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.agenda import Objective
from inventory_tracking.macros.loop import LK, TOWN, TZ_BACK, TZ_PORTAL, TZ_WAYPOINT, Loop
from inventory_tracking.macros.lootpolicy import trip_for
from inventory_tracking.macros.pickmode import MAGIC
from inventory_tracking.macros.pickup import pick_up
from inventory_tracking.macros.pursuit import FULL, Pursuit
from inventory_tracking.macros.running import room as room_module
from inventory_tracking.macros.running.base import ATTACK, PICKUP
from inventory_tracking.macros.running.room import RESUME_NONE, RESUME_RUN, ROOM, Errand
from inventory_tracking.macros.stops import Remedy
from inventory_tracking.macros.town import Exit
from tests.inventory_tracking.macros.test_hunt import attack_mode, foe, game, hunter, me
from tests.inventory_tracking.macros.test_runner import joined, make
from tests.inventory_tracking.macros.test_tzloop import GAME, Script


FULL_INVENTORY = ('#' * 10,) * 4
ROOMY_CUBE = ('...',) * 4
FLEECE = Drop(81, 5008.0, 5000.0, 'Magic Wire Fleece', VALUABLE, (2, 3), prized=False, source='shown', quality=MAGIC)
# A Kriss (items.txt 41, type knif) magic: an identify candidate, "no game is kept for it" (lootpolicy.py GUARD)
KRISS = Drop(82, 5006.0, 5000.0, 'Magic Kriss', VALUABLE, (1, 3), prized=False, source='shown', txt=41, quality=MAGIC)
SHAEL = Drop(83, 5005.0, 5000.0, 'Shael Rune', VALUABLE, prized=False, source='rune')


def until(done, seconds: float = 3.0) -> None:
    """Wait for the runner's threads until `done()`."""
    event = threading.Event()
    for _ in range(int(seconds / 0.02)):
        if done():
            return
        event.wait(0.02)


def shown(*drops: Drop) -> frozenset[int]:
    return frozenset(d.unit_id for d in drops if d.source == 'shown')


def test_a_trip_is_made_for_what_the_guard_keeps_a_game_for_and_never_for_an_identify_candidate():
    assert trip_for(FLEECE, shown=True)  # shown gear: the loop's guard keeps its game, so a trip
    assert trip_for(SHAEL, shown=False)
    assert not trip_for(KRISS, shown=True)  # a trade good to identify: left, as in the loop
    assert not trip_for(Drop(84, 0.0, 0.0, 'gold', 'gold'), shown=False)


# -- the hunt by hand: the cube, then the trip's ask --------------------------------------------------------------


def by_hand(*drops: Drop, cube=ROOMY_CUBE, trips: bool = True):
    play = game()
    play.loot = Loot(drops=drops, room=FULL_INVENTORY, cube=cube, shown=shown(*drops), life=3000, max_life=3000)
    hunt = hunter(play)
    moved: list[int] = []
    asked: list[Drop] = []
    hunt.room_maker = lambda run: moved.append(1) or 0  # nothing of the loop's to move
    hunt.room_trip = lambda run, drop, world, loot: asked.append(drop) or True
    hunt.can_trip = lambda: trips
    return play, hunt, moved, asked


def test_by_hand_shown_gear_with_no_room_is_stood_by_then_the_cube_then_the_trip_asked_in_the_quiet():
    play, hunt, moved, asked = by_hand(FLEECE)
    run, here = play.run(), (5000.0, 5000.0)
    near = foe(1, 5010.0, 5000.0)
    assert hunt.stay_by(run, here, foes=[near]) == FLEECE  # a hostile in reach: stood by, nothing tried
    assert (moved, asked) == ([], [])
    assert hunt.stay_by(run, here) == FLEECE  # the quiet: the cube tried (no room made), then the trip asked
    assert moved == [1]
    assert asked == [FLEECE]


def test_by_hand_with_no_trip_possible_the_run_goes_on_from_shown_gear_as_ruled_before():
    # 2026-10-12, "allow moving when the item isn't very valuable": with no trip to follow a stand (trips spent, the
    # loop on) the old rule stands, or the run would stand by it for ever
    play, hunt, _moved, asked = by_hand(FLEECE, trips=False)
    assert hunt.stay_by(play.run(), (5000.0, 5000.0)) is None
    assert asked == []
    hunt.can_trip, hunt.looping = (lambda: True), (lambda: True)  # the loop on: its stops make the room
    assert hunt.stay_by(play.run(), (5000.0, 5000.0)) is None
    assert asked == []


def test_by_hand_an_identify_candidate_with_no_room_gets_the_cube_but_no_stand_and_no_trip():
    play, hunt, moved, asked = by_hand(KRISS)
    assert hunt.stay_by(play.run(), (5000.0, 5000.0)) is None
    assert moved == [1]  # the cube's room tried once for it
    assert asked == []
    assert hunt.stay_by(play.run(), (5000.0, 5000.0)) is None
    assert moved == [1]


def test_by_hand_room_made_in_the_cube_ends_the_stand_and_asks_no_trip():
    play, hunt, moved, asked = by_hand(SHAEL)
    hunt.room_maker = lambda run: moved.append(1) or 3
    assert hunt.stay_by(play.run(), (5000.0, 5000.0)) is None  # the next look takes it as a side drop
    assert (moved, asked) == ([1], [])


def test_by_hand_a_full_cube_is_no_try_and_the_trip_is_asked_at_once():
    play, hunt, moved, asked = by_hand(SHAEL, cube=('###',) * 4)
    assert hunt.stay_by(play.run(), (5000.0, 5000.0)) == SHAEL
    assert (moved, asked) == ([], [SHAEL])


def test_by_hand_the_sweep_stays_by_a_low_rune_with_no_room_and_asks_for_the_trip():
    # test_hunt's `test_by_hand_the_sweep_goes_on_from_a_low_rune_with_no_room` is the same with no trip possible
    play = game(foe(11, 5050.0, 5000.0))
    hunt = hunter(play)
    rune = Drop(61, 4990.0, 5000.0, 'El Rune', VALUABLE, (1, 1), prized=False, source='rune')
    play.loot = replace(play.loot, drops=(rune,), room=('####', '####'), cube=('###',) * 4)
    hunt.pick = lambda: None
    asked: list[Drop] = []
    hunt.room_trip = lambda run, drop, world, loot: asked.append(drop) or False
    hunt.can_trip = lambda: True
    hunt.sweep.steps, hunt.sweep.until = 6, 100.0
    attack_mode(play, hunt, until=4.0)
    assert 'Staying by El Rune: the inventory has no room for it' in play.said
    assert rune in asked


# -- the press by hand -----------------------------------------------------------------------------------------------


def test_a_press_by_hand_stops_for_shown_gear_with_no_room_only_when_a_trip_may_follow():
    play = game()
    play.loot = Loot(drops=(FLEECE,), room=FULL_INVENTORY, shown=shown(FLEECE))
    assert not pick_up(play.run(), None, None, lambda: None)  # no trip: the press goes on, as ruled 2026-10-12
    with pytest.raises(Abort, match='no room for Magic Wire Fleece') as stop:
        pick_up(play.run(), None, None, lambda: None, trips=True)
    assert stop.value.cause == 'room'


# -- the runner: the trip's ask, ROOM, and the activity again --------------------------------------------------------


def runner_by_hand(routines: list[str], done: bool = True):
    def execute(cancelled, routine):
        routines.append(routine)
        if routine == ROOM and done and runner.errand is not None:
            runner.errand.done = True  # as `_room_errand` ends a trip made

    runner = make(execute, [])
    play = game()
    hunt = runner.hunter = hunter(play)
    runner.build = hunt.build
    runner.journey.game, runner.area_seen = 'cyber32', 101
    return runner, play, hunt


def loot_of(*drops: Drop, life: int = 3000) -> Loot:
    return Loot(drops=drops, room=FULL_INVENTORY, shown=shown(*drops), life=life, max_life=3000)


def test_the_trip_is_due_by_hand_in_the_quiet_and_never_with_the_loop_on_a_hostile_near_or_life_low():
    runner, play, hunt = runner_by_hand([])
    run = play.run()
    assert runner._room_trip_possible()
    assert not runner._room_trip_due(run, KRISS, play.world, loot_of(KRISS))  # an identify candidate
    near = replace(play.world, monsters=(foe(1, 5020.0, 5000.0),))
    assert not runner._room_trip_due(run, FLEECE, near, loot_of(FLEECE))  # "we must not die"
    assert not runner._room_trip_due(run, FLEECE, play.world, loot_of(FLEECE, life=500))
    runner.loop.on = True
    assert not runner._room_trip_due(run, FLEECE, play.world, loot_of(FLEECE))  # the loop's own stops
    assert not runner._room_trip_possible()
    runner.loop.on = False
    hunt.post(Pursuit(PICKUP, 0.0, advance=False, leash=FULL, area=101))
    runner.attack_mode = True
    assert runner._room_trip_due(run, FLEECE, play.world, loot_of(FLEECE))
    assert runner.errand == Errand(FLEECE.unit_id, FLEECE.label, RESUME_RUN)
    assert not runner.attack_mode
    assert runner.cancelled.is_set()  # the run ends at its next look
    assert not runner._room_trip_possible()  # one at a time
    runner.close()


def test_after_the_trip_the_kp1_run_is_posted_again_and_attack_mode_follows():
    routines: list[str] = []
    runner, _play, hunt = runner_by_hand(routines)
    runner.errand = Errand(FLEECE.unit_id, FLEECE.label, RESUME_RUN)
    hunt.waived.add(FLEECE.unit_id)
    seen: list[bool] = []
    original = runner.execute

    def execute(cancelled, routine):
        original(cancelled, routine)
        if routine == ATTACK:
            seen.append(hunt.leashed)

    runner.execute = execute
    with runner.lock:
        assert runner._follow(ATTACK)  # the run cancelled for it ended: ROOM follows
    until(lambda: len(routines) >= 2)
    assert routines[:2] == [ROOM, ATTACK]
    assert seen == [True]  # the level run posted again, as a KP_1 press posts it
    assert FLEECE.unit_id not in hunt.waived
    assert runner.errand is None
    runner.close()


def test_a_press_that_came_first_drops_the_trip_and_a_stopped_trip_does_not_resume():
    routines: list[str] = []
    runner, _play, _hunt = runner_by_hand(routines, done=False)
    runner.errand = Errand(FLEECE.unit_id, FLEECE.label, RESUME_NONE)
    with runner.lock:
        runner.queue.put(PICKUP)
        assert runner._follow(ATTACK)
    assert runner.errand is None  # the player's press wins
    runner.close()
    routines.clear()
    runner, _play, _hunt = runner_by_hand(routines, done=False)
    runner.errand = Errand(FLEECE.unit_id, FLEECE.label, RESUME_RUN)
    with runner.lock:
        assert runner._follow(ATTACK)
    joined(runner)
    assert routines[0] == ROOM
    assert not runner.attack_mode  # a trip that stopped (not done): nothing more is pressed
    runner.close()


def test_a_room_stop_of_a_press_by_hand_becomes_its_errand():
    runner, _play, _hunt = runner_by_hand([])
    stop = Abort('inventory full: no room for Shael Rune', cause='room')
    with runner.lock:
        assert runner._room_after_press(stop, PICKUP)
    assert runner.errand == Errand(None, str(stop), RESUME_NONE)
    with runner.lock:
        assert not runner._room_after_press(stop, PICKUP)  # one at a time
    runner.close()


# -- ROOM: the cube, then the trip, then the valuable --------------------------------------------------------------


def errand_runner(monkeypatch, drops: tuple[Drop, ...], *, cube_room: bool = False, world_changes=None):
    runner, play, _hunt = runner_by_hand([])
    play.loot = loot_of(*drops)
    if world_changes:
        play.world = replace(play.world, **world_changes)
    run = play.run()
    calls: list[tuple] = []

    def cube(run) -> int:
        calls.append(('cube',))
        if cube_room:
            play.loot = replace(play.loot, room=('.' * 10,) * 4)
        return 2

    monkeypatch.setattr(runner, '_room_in_cube', cube)
    monkeypatch.setattr(runner, '_loop_hands', lambda run, key_names: None)
    monkeypatch.setattr(
        room_module.tzloop, 'errand', lambda loop, run, keys, progress, hands, game, area: calls.append(('trip', area))
    )
    monkeypatch.setattr(
        room_module, 'pick_up', lambda run, level, keys, otherwise, threat, unit: calls.append(('pick', unit))
    )
    return runner, run, calls


def test_room_made_in_the_cube_takes_the_valuable_with_no_trip(monkeypatch):
    runner, run, calls = errand_runner(monkeypatch, (SHAEL,), cube_room=True)
    runner.errand = Errand(None, 'inventory full', RESUME_NONE)
    runner._room_errand(run, None)
    assert calls == [('cube',), ('pick', SHAEL.unit_id)]
    assert runner.errand.done


def test_no_room_after_the_cube_is_the_room_package_from_the_level_then_the_valuable(monkeypatch):
    runner, run, calls = errand_runner(monkeypatch, (FLEECE,))
    runner.errand = Errand(FLEECE.unit_id, FLEECE.label, RESUME_NONE)
    runner._room_errand(run, None)
    assert calls == [('cube',), ('trip', 101), ('pick', FLEECE.unit_id)]
    assert runner.errand.done
    runner.errand = Errand(FLEECE.unit_id, FLEECE.label, RESUME_RUN)
    calls.clear()
    runner._room_errand(run, None)
    assert calls == [('cube',), ('trip', 101)]  # the run takes it as its side drop


def test_a_hostile_by_the_character_stops_the_trip_saying_where_the_valuable_lies(monkeypatch):
    runner, run, calls = errand_runner(monkeypatch, (FLEECE,), world_changes={'monsters': (foe(1, 5020.0, 5000.0),)})
    warned: list[str | None] = []
    run.warn = warned.append
    runner.errand = Errand(FLEECE.unit_id, FLEECE.label, RESUME_RUN)
    with pytest.raises(Abort, match='no trip to town for room now: 1 hostiles within 30'):
        runner._room_errand(run, None)
    assert ('trip', 101) not in calls
    assert not runner.errand.done
    assert warned[-1] is not None
    assert 'Magic Wire Fleece lies on the ground' in warned[-1]


def test_a_dead_character_takes_no_action_at_all(monkeypatch):
    # The player, 2026-10-19: "if we died - we MUST not take ANY other actions"
    from inventory_tracking.macros.routines import DEAD

    dead = replace(me(game().world), mode=min(DEAD))
    runner, run, calls = errand_runner(monkeypatch, (FLEECE,), world_changes={'player': dead})
    runner.errand = Errand(FLEECE.unit_id, FLEECE.label, RESUME_NONE)
    runner._room_errand(run, None)
    assert calls == []
    assert not runner.errand.done


# -- the package itself: one run by hand, the loop's legs for Lower Kurast -----------------------------------------


def test_the_errand_makes_the_room_package_in_one_run_on_an_agenda_of_its_own(monkeypatch):
    game_ = Script(36, monkeypatch)
    loop = Loop(prebuffed=GAME)  # off: an activity by hand
    exits: list[Exit] = []
    hands = game_.hands(visit=exits.append)
    tzloop.errand(loop, game_.play.run(), lambda world, skills=None: {}, game_.progress, hands, GAME, 36)
    assert [call for call in game_.calls if call[0] != 'prebuff'] == [
        ('portal', 1),
        ('waypoint', 103),
        ('waypoint', 1),
        ('through', 36),
    ]
    assert exits == [Exit.PORTAL]
    assert (loop.trips, loop.returned, loop.agenda.stack) == (1, GAME, [])


def test_lower_kurast_trips_by_the_room_package_after_the_cube_and_its_legs_go_on(monkeypatch):
    runner, _play, _hunt = runner_by_hand([])
    loop = runner.loop
    loop.on, loop.kind, loop.seen, loop.carrying = True, LK, (GAME, 0.0), True
    runner.area_seen = 79
    runner.valuable_left = lambda: 'Ist Rune'
    stop = Abort('inventory full: no room for Ist Rune', cause='room')
    runner._loop_stopped(stop)
    assert loop.make_room  # the cube first
    runner._loop_stopped(stop)
    assert loop.on
    assert loop.agenda.stack[-1].label == 'Town Portal for room'
    assert not loop.drop_room  # no item dropped for it any more: the trip comes first
    runner.close()

    game_ = Script(79, monkeypatch)
    game_.loop.kind = LK
    game_.loop.agenda.begin(game_.loop.observe(game_.play.world))
    tzloop.trip(game_.loop, GAME, 79)
    exits: list[Exit] = []
    legs = [game_.leg(visit=exits.append) for _ in range(5)]
    assert legs == [TZ_PORTAL, TZ_WAYPOINT, TOWN, TZ_WAYPOINT, TZ_BACK]
    assert [call for call in game_.calls if call[0] != 'prebuff'] == [
        ('portal', 75),
        ('waypoint', 103),
        ('waypoint', 75),
        ('through', 79),
    ]
    assert exits == [Exit.PORTAL]
    assert game_.leg(visit=exits.append) not in (TZ_PORTAL, TZ_WAYPOINT, TOWN, TZ_BACK)  # Lower Kurast's own legs
    assert game_.loop.agenda.stack == []  # its RESUME ended the package


def test_a_package_left_from_another_game_is_dropped_for_lower_kurast(monkeypatch):
    game_ = Script(79, monkeypatch)
    game_.loop.kind = LK
    game_.loop.agenda.begin('another game')
    game_.loop.agenda.push(Objective('portal to town', 'Town Portal for room', 0, 79, to=75))
    game_.loop.observe(game_.play.world)
    assert tzloop.packaged(game_.play.world, game_.loop) is None


def test_the_remedy_for_a_packaged_kind_is_the_package():
    from inventory_tracking.macros.stops import Stopped, decide

    stop = Stopped('room', True, 'Ring', GAME, cubed=True, packaged=True, trips=False)
    assert decide(stop) is Remedy.PACKAGE
