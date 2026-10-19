import threading
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from inventory_tracking.game.memory import GameMemory
from inventory_tracking.game.records import Pack
from inventory_tracking.macros import runner as runner_module
from inventory_tracking.macros.actuator import Abort, Cancelled, Flipped
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.loop import RECOVERIES, Dead
from inventory_tracking.macros.runner import MacroRunner
from inventory_tracking.macros.town import Exit
from inventory_tracking.routes.model import Route, level
from inventory_tracking.routes.progress import Progress
from tests.inventory_tracking.macros.fakes import BUILD, KEYS, Game, character_of, player, world


# No key file is read here: every run is given its keys, or none is played by `_execute`.
SAVED_GAMES = Path('/nonexistent/Saved Games')


def make(execute, shown):
    runner = MacroRunner(
        None, capture_lock=threading.Lock(), saved_games=SAVED_GAMES, display=shown.append, execute=execute
    )
    runner.valuable_left = lambda: None  # nothing on the ground (no game to read)
    return runner


def joined(runner: MacroRunner) -> threading.Thread:
    """The thread of the runner's last run, joined (5 s at most)."""
    thread = runner.thread
    assert thread is not None
    thread.join(5)
    return thread


def test_a_stale_request_starts_nothing():
    started = []
    runner = make(lambda cancelled, routine: started.append(routine), [])
    assert not runner.request(10.0, 12.0)
    assert runner.thread is None


def test_loop_town_callback_uses_the_same_shared_visit(monkeypatch):
    play = Game(world(103, player=player(103)))
    run = play.run()
    runner = make(lambda _cancelled, _routine: None, [])
    monkeypatch.setattr(runner, 'choosing', lambda _run: None)
    monkeypatch.setattr(runner_module, 'note_view', lambda *_args: None)
    visited = []
    monkeypatch.setattr(runner, '_shared_town_visit', lambda _run, exit, _gems: visited.append(exit))
    monkeypatch.setattr(runner.loop, 'leg', lambda run, keys, progress, hands, **kwargs: hands.visit(Exit.WAYPOINT))

    runner.perform(run, run.actuator, runner_module.LOOP, KEYS)

    assert visited == [Exit.WAYPOINT]


def test_a_press_during_a_run_cancels_it():
    shown = []

    def execute(cancelled, routine):
        assert cancelled.wait(5)
        raise Cancelled

    runner = make(execute, shown)
    assert runner.request(10.0, 10.1)
    assert runner.request(11.0, 11.1)
    assert not joined(runner).is_alive()
    assert shown == [['Macro stopped: cancelled'], []]


def test_a_crash_is_shown_and_the_next_press_starts_again():
    shown = []
    calls = []

    def execute(cancelled, routine):
        calls.append(routine)
        raise RuntimeError('boom')

    runner = make(execute, shown)
    runner.request(10.0, 10.1)
    joined(runner)
    runner.request(20.0, 20.1, 'teleport')
    joined(runner)
    assert calls == ['prebuff', 'teleport']
    assert shown[0] == ['Macro failed: boom']


def test_the_levels_noted_between_presses_are_what_a_run_is_told():
    places = iter([('cyber32', 102), ('cyber32', 102), ('cyber32', 103)])
    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=SAVED_GAMES, place=lambda: next(places))
    runner.poll(10.0)
    runner.poll(10.2)  # too soon: not read
    runner.poll(11.5)
    runner.poll(13.0)
    assert runner.journey.arrival(20.0) == (102, 7.0)


def test_the_game_and_level_are_noted_for_the_routes_too():
    places = iter([('cyber32', 3), ('cyber32', 9), (None, None)])
    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=SAVED_GAMES, place=lambda: next(places))

    noted = []

    class Noted(Progress):
        def note(self, game: str | None, area: int | None) -> None:
            noted.append((game, area))

    runner.progress = Noted(())
    for now in (10.0, 12.0, 14.0):
        runner.poll(now)
    assert noted == [('cyber32', 3), ('cyber32', 9), (None, None)]


def test_a_level_that_cannot_be_read_does_not_stop_the_service():
    def place():
        raise OSError('gone')

    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=SAVED_GAMES, place=place)
    runner.poll(10.0)
    assert runner.journey.arrival(11.0)[0] is None
    assert not runner.capture_lock.locked()


def test_a_teleport_request_during_a_teleport_step_queues_one_more_step_instead_of_cancelling():
    steps, go_on = [], threading.Event()

    def execute(cancelled, routine):
        steps.append(routine)
        if len(steps) == 1:
            assert go_on.wait(5)
        assert not cancelled.is_set()

    runner = make(execute, [])
    assert runner.request(10.0, 10.1, 'teleport')
    assert runner.request(10.2, 10.3, 'teleport')  # faster than the prebuff throttle, during the step
    assert runner.request(10.4, 10.5, 'teleport')  # still only one more
    go_on.set()
    joined(runner)
    assert steps == ['teleport', 'teleport']


def test_a_press_right_after_a_step_starts_the_next_while_the_card_still_shows(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0.5)
    steps, shown = [], []
    runner = make(lambda cancelled, routine: steps.append(routine), shown)
    runner.request(10.0, 10.1, 'teleport')
    deadline = threading.Event()
    for _ in range(100):
        if not runner.working:
            break
        deadline.wait(0.02)
    assert runner.request(10.3, 10.4, 'teleport')  # the card thread of the first run is still alive
    joined(runner)
    assert steps == ['teleport', 'teleport']


def test_closing_ends_the_card_wait_of_a_run_that_ended(monkeypatch):
    # The card of a run that ended stays CARD_SECONDS (4 s); shutdown must not wait it out.
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 4.0)
    runner = make(lambda cancelled, routine: None, [])
    assert runner.request(10.0, 10.1, 'teleport')
    thread = runner.thread
    assert thread is not None
    started = time.monotonic()
    runner.close()  # joins the run's thread (up to 3 s)
    assert time.monotonic() - started < 1.0
    assert not thread.is_alive()


def test_a_macro_request_during_a_teleport_step_cancels_it():

    def execute(cancelled, routine):
        assert cancelled.wait(5)
        raise Cancelled

    runner = make(execute, [])
    runner.request(10.0, 10.1, 'teleport')
    assert runner.request(10.5, 10.6, 'prebuff')
    joined(runner)
    assert not runner.working


def test_a_seek_request_during_its_own_step_queues_one_more_and_a_teleport_request_cancels():
    steps, go_on, attacking = [], threading.Event(), threading.Event()

    def execute(cancelled, routine):
        steps.append(routine)
        if routine == 'hunt any':  # the mode the seek step leaves on
            attacking.set()
            assert cancelled.wait(5)
            raise Cancelled
        if len(steps) == 1:
            assert go_on.wait(5)
        assert not cancelled.is_set()

    runner = make(execute, [])
    assert runner.request(10.0, 10.1, 'hunt elites')
    assert runner.request(10.2, 10.3, 'hunt elites')  # the same key: one more step
    go_on.set()
    assert attacking.wait(5)
    assert steps == ['hunt elites', 'hunt elites', 'hunt any']
    runner.request(11.0, 11.1, 'hunt any')  # the attack mode toggle: off
    joined(runner)

    def cancelled_step(cancelled, routine):
        assert cancelled.wait(5)
        raise Cancelled

    runner = make(cancelled_step, [])
    assert runner.request(20.0, 20.1, 'hunt elites')
    step = runner.thread
    assert step is not None
    assert runner.request(20.2, 20.3, 'teleport')  # another key cancels
    step.join(5)
    assert not step.is_alive()
    runner.close()


def test_the_toggle_turns_attack_mode_on_and_off():
    # user, 2026-10-10 evening: the toggle turns it off too (the morning's "never off" is withdrawn).
    shown = []

    def execute(cancelled, routine):
        assert routine == 'hunt any'
        assert cancelled.wait(5)
        raise Cancelled

    runner = make(execute, shown)
    assert runner.request(10.0, 10.1, 'hunt any')
    assert runner.attack_mode
    assert runner.working
    assert runner.request(10.5, 10.6, 'hunt any')
    joined(runner)
    assert not runner.attack_mode
    assert not runner.working
    assert ['Macro: Attack mode off'] in shown
    assert runner.request(11.0, 11.1, 'hunt any')  # and on again
    assert runner.attack_mode
    runner.request(11.5, 11.6, 'hunt any')
    joined(runner)


def test_a_seek_request_does_its_step_and_turns_attack_mode_on():
    # user, 2026-10-10 evening: after the seek step the character stood beside the monsters until attack
    # mode was turned on by hand.
    runs, attacking = [], threading.Event()

    def execute(cancelled, routine):
        runs.append(routine)
        if routine == 'hunt any':
            attacking.set()
            assert cancelled.wait(5)
            raise Cancelled
        if len(runs) == 1:
            raise Abort('no level map for this level yet')  # a step that stops still leaves the mode on

    runner = make(execute, [])
    assert runner.request(10.0, 10.1, 'hunt elites')
    assert attacking.wait(5)
    assert runs == ['hunt elites', 'hunt any']
    assert runner.attack_mode
    attacking.clear()
    assert runner.request(11.0, 11.1, 'hunt elites')  # again: the mode pauses for the step and resumes
    assert attacking.wait(5)
    assert runs == ['hunt elites', 'hunt any', 'hunt elites', 'hunt any']
    runner.request(12.0, 12.1, 'hunt any')  # the attack mode toggle: off
    joined(runner)
    assert not runner.attack_mode


def test_a_step_during_attack_mode_pauses_it_and_it_resumes_after():
    runs, resumed = [], threading.Event()

    def execute(cancelled, routine):
        runs.append(routine)
        if routine == 'hunt any':
            if len(runs) > 1:
                resumed.set()
            assert cancelled.wait(5)
            raise Cancelled

    runner = make(execute, [])
    assert runner.request(10.0, 10.1, 'hunt any')
    assert runner.request(10.3, 10.4, 'teleport')  # the mode pauses for the step
    assert resumed.wait(5)
    assert runs == ['hunt any', 'teleport', 'hunt any']
    assert runner.attack_mode
    runner.request(11.0, 11.1, 'prebuff')  # off again
    joined(runner)


def test_a_pickup_request_during_attack_mode_asks_for_a_step_and_is_dropped_when_the_mode_says_so():
    # The press inside a fight is a step to a better stand; with nothing on the ground the mode tells
    # the runner that no pickup step (and so no seek step) is to follow the fight.
    from inventory_tracking.macros.hunt import Hunter

    runs, asked = [], threading.Event()
    hunter = Hunter(build=BUILD)

    def execute(cancelled, routine):
        runs.append(routine)
        assert asked.wait(5)
        assert hunter.step_asked.is_set()
        assert hunter.after_fight.is_set()
        assert hunter.unwait is not None
        hunter.unwait()
        assert cancelled.wait(5)
        raise Cancelled

    runner = make(execute, [])
    runner.hunter = hunter
    assert runner.request(10.0, 10.1, 'hunt any')
    assert runner.request(10.3, 10.4, 'pickup')
    assert runner.pending == 'pickup'
    asked.set()
    runner.request(11.0, 11.1, 'hunt any')  # the toggle: the mode off
    joined(runner)
    assert runner.pending is None  # pyrefly: ignore[unnecessary-comparison] the call above changes it
    assert runs == ['hunt any']


def test_a_teleport_or_seek_request_ends_the_sweep_and_a_pickup_request_does_not():
    # Tower Cellar 3, 2026-10-11: the sweep walked the character back between two teleport steps.
    from inventory_tracking.macros.hunt import Hunter

    runner = make(lambda cancelled, routine: None, [])
    runner.hunter = Hunter(build=BUILD)
    for routine, left in (('pickup', 5), ('teleport', 0), ('hunt elites', 0), ('prebuff', 0)):
        runner.hunter.sweep.steps = 5
        runner.last_request = -1e9
        assert runner.request(10.0, 10.1, routine)
        joined(runner)
        assert runner.hunter.sweep.steps == left, routine


def test_a_pickup_request_during_attack_mode_waits_for_the_fight_and_the_mode_resumes_after():
    # user, 2026-10-10: the pickup is queued behind the killing, not put before it.
    from inventory_tracking.macros.hunt import Hunter

    runs, resumed, fight_over = [], threading.Event(), threading.Event()
    hunter = Hunter(build=BUILD)

    def execute(cancelled, routine):
        runs.append(routine)
        if routine == 'hunt any':
            if len(runs) > 1:
                resumed.set()
                assert cancelled.wait(5)
                raise Cancelled
            assert fight_over.wait(5)  # the fight goes on: the press does not cancel it
            assert not cancelled.is_set()
            assert hunter.after_fight.is_set()
            hunter.step_aside()  # nothing left in reach: the mode pauses itself

    runner = make(execute, [])
    runner.hunter = hunter
    assert runner.request(10.0, 10.1, 'hunt any')
    assert runner.request(10.3, 10.4, 'pickup')
    assert runs == ['hunt any']
    fight_over.set()
    assert resumed.wait(5)
    assert runs == ['hunt any', 'pickup', 'hunt any']
    runner.request(11.0, 11.1, 'prebuff')
    joined(runner)


def test_closing_during_a_seek_step_starts_nothing_after_it():
    # review.md, finding 1: the cancelled seek step used to be followed by attack mode on a fresh,
    # unset cancellation, after the service had shut down.
    runs, started = [], threading.Event()

    def execute(cancelled, routine):
        runs.append(routine)
        started.set()
        assert cancelled.wait(5)
        raise Cancelled

    runner = make(execute, [])
    assert runner.request(10.0, 10.1, 'hunt elites')
    assert started.wait(5)
    runner.close()
    joined(runner)
    assert runs == ['hunt elites']
    assert not runner.attack_mode
    assert not runner.request(11.0, 11.1, 'teleport')  # and no request starts another
    assert runs == ['hunt elites']


def test_closing_with_a_pickup_waiting_for_the_fight_drops_it():
    from inventory_tracking.macros.hunt import Hunter

    runs, started = [], threading.Event()

    def execute(cancelled, routine):
        runs.append(routine)
        started.set()
        assert cancelled.wait(5)
        raise Cancelled

    runner = make(execute, [])
    runner.hunter = Hunter(build=BUILD)
    assert runner.request(10.0, 10.1, 'hunt any')
    assert started.wait(5)
    assert runner.request(10.3, 10.4, 'pickup')
    runner.close()
    joined(runner)
    assert runs == ['hunt any']


def test_a_macro_request_ends_attack_mode_and_runs_the_macro():
    # user, 2026-10-10: the macro request must not only stop the mode but run the macro as it does otherwise.
    runs, done = [], threading.Event()

    def execute(cancelled, routine):
        runs.append(routine)
        if routine == 'hunt any':
            assert cancelled.wait(5)
            raise Cancelled
        done.set()

    runner = make(execute, [])
    assert runner.request(10.0, 10.1, 'hunt any')
    assert runner.request(10.5, 10.6, 'prebuff')
    assert done.wait(5)
    joined(runner)
    assert runs == ['hunt any', 'prebuff']
    assert not runner.attack_mode


def test_attack_mode_returning_on_its_own_turns_the_toggle_off():
    shown = []
    runner = make(lambda cancelled, routine: None, shown)
    assert runner.request(10.0, 10.1, 'hunt any')
    joined(runner)
    assert not runner.attack_mode
    assert runner.request(10.5, 10.6, 'hunt any')  # the next press starts the mode again, not "off"
    joined(runner)
    assert runner.generation == 2
    assert ['Macro: Attack mode off'] not in shown


def test_attack_mode_ending_on_its_own_turns_the_toggle_off():
    shown = []
    runner = make(lambda cancelled, routine: (_ for _ in ()).throw(Abort('attack mode off: the game was left')), shown)
    assert runner.request(10.0, 10.1, 'hunt any')
    joined(runner)
    assert not runner.attack_mode
    assert ['Macro stopped: attack mode off: the game was left'] in shown


def test_requests_racing_a_runs_end_never_leave_two_runs_acting():
    # review.md, finding 1: `working` went off before the successor was chosen, so a request and the
    # ending run could each start one. Steps that end at once, under a storm of requests.
    acting, most, runs = [0], [0], [0]
    guard = threading.Lock()

    def execute(cancelled, routine):
        with guard:
            acting[0] += 1
            most[0] = max(most[0], acting[0])
            runs[0] += 1
        cancelled.wait(0.0005)
        with guard:
            acting[0] -= 1
        if cancelled.is_set():
            raise Cancelled

    runner = make(execute, [])
    runner.hunter = Hunter(build=BUILD)
    routines = ('teleport', 'hunt elites', 'hunt any', 'pickup', 'teleport', 'prebuff')

    def press(offset):
        for index in range(300):
            now = 10.0 + offset + index
            runner.request(now, now, routines[(index + offset) % len(routines)])
            time.sleep(0.0003)  # about a run's length: requests land before, during and at the end of runs

    pressers = [threading.Thread(target=press, args=(offset,)) for offset in range(3)]
    for presser in pressers:
        presser.start()
    for presser in pressers:
        presser.join(10)
    runner.close()
    assert runs[0] > 10
    assert most[0] == 1


def test_a_request_after_close_and_a_run_ending_after_close_start_nothing():
    runs, started, release = [], threading.Event(), threading.Event()

    def execute(cancelled, routine):
        runs.append(routine)
        started.set()
        assert release.wait(5)  # still working when the service closes, and deaf to the cancel

    runner = make(execute, [])
    assert runner.request(10.0, 10.1, 'hunt elites')  # attack mode is to follow the step
    assert started.wait(5)
    thread = runner.thread
    assert thread is not None
    closer = threading.Thread(target=runner.close)
    closer.start()
    assert not runner.request(10.3, 10.4, 'teleport')
    release.set()
    closer.join(5)
    thread.join(5)
    assert runs == ['hunt elites']
    assert runner.thread is thread
    assert not runner.working


def test_a_request_while_a_run_hands_over_to_its_successor_waits_for_the_handover():
    # review.md, finding 1: the seek step is over and attack mode is being started after it; a teleport
    # request in that moment must find the mode (and pause it), not an idle runner to start beside it.
    acting, most, runs = [0], [0], []
    guard, handing_over, teleported = threading.Lock(), threading.Event(), threading.Event()

    def execute(cancelled, routine):
        with guard:
            acting[0] += 1
            most[0] = max(most[0], acting[0])
            runs.append(routine)
        try:
            if routine == 'hunt any':
                assert cancelled.wait(5)
                raise Cancelled
            if routine == 'teleport':
                teleported.set()
        finally:
            with guard:
                acting[0] -= 1

    runner = make(execute, [])
    start = runner._start

    def slow_start(routine):
        if routine == 'hunt any':
            handing_over.set()
            time.sleep(0.05)  # the request below arrives in here
        start(routine)

    runner._start = slow_start
    assert runner.request(10.0, 10.1, 'hunt elites')
    assert handing_over.wait(5)
    assert runner.request(10.2, 10.3, 'teleport')
    assert teleported.wait(5)
    runner.close()
    assert runs[:3] == ['hunt elites', 'hunt any', 'teleport']
    assert most[0] == 1


def test_a_game_begun_with_the_staff_in_hand_is_said_once():
    # user, 2026-10-11: "teleport was broken because I exit game without switching to main hand".
    shown = []
    place: tuple[str | None, int | None] = ('game 1', 6)
    held: list[bool | None] = [None]
    runner = MacroRunner(
        None,
        capture_lock=threading.Lock(),
        saved_games=SAVED_GAMES,
        display=shown.append,
        execute=lambda cancelled, routine: None,
        place=lambda: place,
        staff_in_hand=lambda: held[0],
    )
    runner.poll(10.0)
    assert shown == []  # the hands are not readable yet: looked at again
    held[0] = True
    runner.poll(12.0)
    assert len(shown) == 1
    assert 'began with the staff in hand' in shown[0][0]
    assert 'bind it again' in shown[0][0]
    runner.poll(14.0)
    assert len(shown) == 1  # once a game
    place, held[0] = ('game 2', 6), False
    runner.poll(16.0)
    assert len(shown) == 1  # the main weapons in hand: nothing to say
    place, held[0] = ('game 3', 6), True
    runner.poll(18.0)
    assert len(shown) == 2


def test_a_teleport_request_during_a_pickup_stops_it_and_the_step_follows_at_once():
    # Tower Cellar 5, 22:51:00 on 2026-10-11: the press to get out waited behind a pickup that clicked
    # 5 s at a potion among eight monsters, and the character died 0.4 s after it. (The Ring of
    # 17:35:18 that day, whose pickup such a press cancelled, is the teleport step's own business
    # now: it takes a valuable near before it hops, pickup.worth_a_stop.)
    steps, stepped = [], threading.Event()

    def execute(cancelled, routine):
        steps.append(routine)
        if routine == 'pickup':
            assert cancelled.wait(5)  # the pickup is told to stop
            raise Cancelled
        stepped.set()

    runner = make(execute, [])
    assert runner.request(10.0, 10.1, 'pickup')
    assert runner.request(10.2, 10.3, 'teleport')
    assert stepped.wait(5)
    assert steps == ['pickup', 'teleport']


def test_attack_mode_stays_out_a_moment_after_a_teleport_step_and_a_press_in_it_goes_at_once(monkeypatch):
    # 21:26 on 2026-10-11: the next press of a player travelling came 40 to 700 ms after the step
    # before, found the mode running again and waited for it and its strike: half took over 250 ms.
    monkeypatch.setattr(runner_module, 'TRAVEL_QUIET', 30.0)
    runs, first, second = [], threading.Event(), threading.Event()

    def execute(cancelled, routine):
        runs.append(routine)
        if routine == 'hunt any':
            assert cancelled.wait(5)
            raise Cancelled
        (second if first.is_set() else first).set()

    runner = make(execute, [])
    assert runner.request(10.0, 10.1, 'hunt any')
    assert runner.request(10.3, 10.4, 'teleport')
    assert first.wait(5)
    time.sleep(0.05)  # the step is over: the mode is to follow, and holds back
    assert runs == ['hunt any', 'teleport']
    assert runner.request(10.6, 10.7, 'teleport')  # in the quiet: no mode ran, the step goes
    assert second.wait(5)
    assert runs == ['hunt any', 'teleport', 'teleport']
    runner.close()


def test_attack_mode_resumes_at_once_after_a_seek_step(monkeypatch):
    monkeypatch.setattr(runner_module, 'TRAVEL_QUIET', 30.0)
    runs, resumed = [], threading.Event()

    def execute(cancelled, routine):
        runs.append(routine)
        if routine == 'hunt any':
            resumed.set()
            assert cancelled.wait(5)
            raise Cancelled

    runner = make(execute, [])
    assert runner.request(10.0, 10.1, 'hunt elites')
    assert resumed.wait(5)
    assert runs == ['hunt elites', 'hunt any']
    runner.close()


# --- the build a run plays: chosen at the run's first look that shows the character, and handed down ---


def building(play, hunter=None, builds=None, fallback=None):
    """A runner with the registry and a run of `play` as `_execute` makes it: with the build the
    runner played last, the fallback at first. (`_execute` itself needs the game's process.)"""
    from inventory_tracking import builds as registry

    shown = []
    runner = MacroRunner(
        None,
        capture_lock=threading.Lock(),
        saved_games=SAVED_GAMES,
        display=shown.append,
        execute=lambda cancelled, routine: None,
        builds=registry.BUILDS if builds is None else builds,
        fallback=registry.FALLBACK if fallback is None else fallback,
    )
    runner.hunter = hunter
    play.build = runner.build
    return runner, play.run(), shown


def looks(play):
    """Counts the looks at the game."""
    seen, read = [], play.read

    def counted():
        seen.append(play.clock.now)
        return read()

    play.read = counted
    return seen


def someone(**changes):
    """A character no build knows by name, with no Echoing Strike anywhere."""
    from tests.inventory_tracking.macros.fakes import SLOTS, player, world

    found = world(area=101, slots=SLOTS)
    return replace(found, player=replace(player(101, name='Someone'), **changes))


def test_the_build_is_chosen_at_the_runs_first_look_and_costs_no_look_of_its_own():
    from inventory_tracking import builds as registry
    from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, Game, world

    play = Game(world(area=101, slots=HUNT_SLOTS))
    seen = looks(play)
    hunter = Hunter(build=registry.FALLBACK)
    runner, run, _ = building(play, hunter)
    assert run.build is registry.FALLBACK
    runner.choosing(run)
    assert seen == []  # no look for the choice
    assert run.build is registry.FALLBACK
    assert hunter.build is registry.FALLBACK
    run.world()
    assert len(seen) == 1  # the routine's own look, and by it:
    assert run.build is runner.build is hunter.build is BUILD
    assert hunter.travel.sets == BUILD.movement
    run.world()
    run.world()
    assert len(seen) == 3  # one read a look, as before


def test_a_look_that_shows_no_character_chooses_nothing_and_the_first_that_does_chooses():
    from inventory_tracking import builds as registry
    from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, Game, world

    start = world(area=101, slots=HUNT_SLOTS)
    play = Game(replace(start, player=None))  # the game is loading
    runner, run, _ = building(play)
    runner.choosing(run)
    run.world()
    assert run.build is registry.FALLBACK
    play.world = start
    run.world()
    assert run.build is runner.build is BUILD


def test_the_hunt_keeps_its_memory_while_the_build_stays_and_starts_anew_with_another_character():
    from inventory_tracking import builds as registry
    from inventory_tracking.builds.generic import GENERIC
    from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, Game, world

    play = Game(world(area=101, slots=HUNT_SLOTS))
    hunter = Hunter(build=registry.FALLBACK)
    runner, run, _ = building(play, hunter)
    runner.choosing(run)
    run.world()
    buffs, travel, sweep = hunter.buffs, hunter.travel, hunter.sweep
    buffs.cast_at[1, None] = 5.0
    assert runner.build is not None
    # the next run, the same character: its build is the one the runner played last from the start
    again = play.run()
    again.build = runner.build
    runner.choosing(again)
    again.world()
    assert hunter.buffs is buffs
    assert hunter.travel is travel
    assert hunter.buffs.cast_at == {(1, None): 5.0}
    # another character in the next game
    play.world = someone()
    other = play.run()
    other.build = runner.build
    assert other.build is BUILD  # until this run has seen the character
    runner.choosing(other)
    other.world()
    assert other.build is runner.build is hunter.build is GENERIC
    assert hunter.buffs is not buffs
    assert hunter.buffs.cast_at == {}
    assert hunter.travel.sets == GENERIC.movement
    assert hunter.sweep is sweep  # what is not the build's stays


def test_a_runner_given_no_build_stops_with_that_said():
    from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, Game, world

    play = Game(world(area=101, slots=HUNT_SLOTS))
    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=SAVED_GAMES)
    assert runner.build is None
    with pytest.raises(Abort, match='no build to play: the runner was given none'):
        runner._execute(threading.Event(), 'pickup')
    run = play.run()
    with pytest.raises(Abort, match='no build to play: the runner was given none'):
        runner.perform(run, run.actuator, 'pickup', None)


def test_the_pickup_step_jumps_by_the_chosen_builds_own_jump():
    from tests.inventory_tracking.macros import test_pickup as drops

    play = drops.game(drops.PILE)
    hunter = Hunter(lambda: drops.LEVEL, build=BUILD)
    runner, run, _ = building(play, hunter)
    assert run.build is not BUILD
    runner.perform(run, run.actuator, 'pickup', drops.keys)
    assert run.build is BUILD
    assert play.pressed() == ['w']  # Blade Warp onto the pile: the Warlock's
    assert play.picked == ['7200 gold']


def test_at_a_routes_end_the_pickup_step_seeks_nothing_and_the_press_after_leaves_the_game():
    # Chaos Sanctuary, 23:18:27 on 2026-10-12: Diablo dead, nothing to pick up, and the pickup key went by
    # Blade Warp for "the remembered monster", three presses running (user: "no mobs around, so we can exit").
    from inventory_tracking.routes.model import fight, leave, loot
    from inventory_tracking.routes.progress import Progress
    from tests.inventory_tracking.macros import test_pickup as drops

    play = drops.game()
    area = play.character.area
    route = Route('Countess', (6,), (level(area, fight('The Countess', 'Countess'), loot(), leave()),))
    remembered = lambda level: [(900, play.character.x + 60.0, play.character.y, False)]  # ruff: ignore[lambda-assignment]
    runner, run, _ = building(play, Hunter(lambda: drops.LEVEL, remembered, build=BUILD))
    runner.progress = progress = Progress(
        [route], frozenset(('fight', 'loot', 'leave')), dead=lambda: frozenset({'The Countess'})
    )
    progress.note('cyber32', area)
    runner.attack_mode = True

    def keys(world, skills=None):  # as `_execute` gives them: every key for the prebuff, else the skills asked for
        return dict(KEYS) if skills is None else {skill: KEYS[skill] for skill in skills}

    runner.perform(run, run.actuator, 'pickup', keys)
    assert play.pressed() == []  # no step toward what is remembered
    assert play.said[-1] == 'Countess: nothing to pick up; the next press leaves the game'
    runner.perform(play.run(), run.actuator, 'pickup', keys)
    assert play.pressed()[0] == 'Escape'
    assert runner.attack_mode is False  # pyrefly: ignore[unnecessary-comparison] the call above changes it


def at_a_door(away: float):
    """A two-level route at its door (`enter` Next level) with nothing to pick up; the card's mark `away` units east
    of the character. The route's step and the seek step only say they were taken."""
    from inventory_tracking.levels.model import Target
    from inventory_tracking.macros.route import PERFORMED
    from inventory_tracking.native.layout import TILE_UNITS
    from inventory_tracking.routes.model import enter, fight, leave, loot
    from inventory_tracking.routes.progress import Progress
    from tests.inventory_tracking.macros import test_pickup as drops

    play = drops.game()
    area, x, y = play.character.area, play.character.x, play.character.y
    route = Route(
        'Radament',
        (6,),
        (level(area, enter('Next level', area + 1)), level(area + 1, fight('Radament'), loot(), leave())),
    )
    hunter = Hunter(lambda: drops.LEVEL, build=BUILD)
    runner, run, _ = building(play, hunter)
    runner.progress = progress = Progress([route], PERFORMED, dead=lambda: frozenset())
    progress.note('cyber32', area)
    door = Target(area, drops.LEVEL.rooms, ((x + away) / TILE_UNITS, y / TILE_UNITS), 'Next level', 'stairs', True)
    runner.target = lambda: door
    runner.attack_mode = True
    steps: list[str] = []
    runner.staged = lambda run_, key_names, plain: steps.append('the route')  # type: ignore[method-assign]
    hunter.step = lambda run_, key_names: steps.append('a seek')  # type: ignore[method-assign]
    return steps, runner, run


def test_at_a_door_on_the_route_the_pickup_press_takes_the_routes_step_not_a_seek():
    # Sewers Level 2, 19:33:38-54 on 2026-10-15 (rca/2026-10-15/kp1-door-findings.md): a terror-zone full clear ended
    # "at Next level: going through takes a press"; each of nine KP_1 presses was handed to the pickup routine ("the
    # route's own step takes the press"), which found nothing to pick up, sought, and stopped on "the level is explored
    # and nothing is left to hunt". The player clicked the stairs. U13: a change of level waits for a press, and that
    # press is the next one.
    steps, runner, run = at_a_door(3.0)

    runner.perform(run, run.actuator, 'pickup', lambda world, skills=None: dict(KEYS))
    assert steps == ['the route']


def test_away_from_the_routes_door_the_pickup_press_is_still_a_seek():
    steps, runner, run = at_a_door(400.0)

    runner.perform(run, run.actuator, 'pickup', lambda world, skills=None: dict(KEYS))
    assert steps == ['a seek']
    from inventory_tracking.builds.generic import GENERIC
    from tests.inventory_tracking.macros import test_pickup as drops

    play = drops.game(drops.PILE)
    play.world = someone()
    runner, run, _ = building(play, Hunter(lambda: drops.LEVEL, build=BUILD))
    runner.perform(run, run.actuator, 'pickup', drops.keys)
    assert runner.hunter is not None
    assert run.build is runner.hunter.build is GENERIC
    assert play.pressed() == []  # no jump of its own that spares the staff
    assert any(event[0] == 'click' for event in play.keys.events)
    assert play.picked == ['7200 gold']
    assert play.said[-1] == '7200 gold: picked up'


def test_the_teleport_step_of_a_character_no_build_claims_hops_by_the_staff():
    from inventory_tracking.builds.generic import GENERIC
    from tests.inventory_tracking.macros import test_teleport as steps

    play = steps.game()
    play.world = replace(someone(), player=replace(character_of(someone()), area=109))
    runner, run, _ = building(play)
    runner.target = lambda: steps.target((1003.0, 1000.0))
    runner.perform(run, run.actuator, 'teleport', steps.keys)
    assert run.build is GENERIC
    assert play.pressed() == ['t']
    assert play.staff is not None
    assert play.staff.charges == 9
    assert play.said[-2].startswith('Teleport toward Next level')


def test_with_a_pack_by_the_seal_the_teleport_step_goes_there():
    # The rule of 2026-10-13 night ("N monsters by <mark>: the fight first") is withdrawn: in the game of 09:06
    # the key mashed by the first Vizier seal left the character 7 s with no strike (rca/2026-10-13). The
    # press hops toward the mark whatever stands by it, as before, and does not turn attack mode on.
    from tests.inventory_tracking.macros import test_hunt as hunts

    for count in (2, 5):
        play = hunts.game(*hunts.pack(count))
        runner, run, _ = building(play, hunts.hunter(play))
        runner.target = lambda: hunts.seal()
        runner.perform(run, run.actuator, 'teleport', hunts.keys)
        assert play.pressed() == [hunts.KEYS[hunts.BLADE_WARP]]  # the hop, and no swap of the weapons
        assert play.said[0].startswith('Blade Warp toward the seal')
        assert not any('the fight first' in said for said in play.said)
        assert runner.attack_mode is False


def test_the_teleport_step_of_the_warlock_is_the_step_it_was():
    from tests.inventory_tracking.macros import test_teleport as steps

    play, alone = steps.game(), steps.game()
    runner, run, _ = building(play)
    runner.target = lambda: steps.target((1003.0, 1000.0))
    runner.perform(run, run.actuator, 'teleport', steps.keys)
    steps.step_toward(alone.run(), steps.target((1003.0, 1000.0)), steps.keys)
    assert run.build is BUILD
    assert play.keys.events == alone.keys.events
    assert play.said == alone.said


def test_attack_mode_of_a_character_no_build_claims_stops_with_the_reason_and_presses_nothing():
    from inventory_tracking import builds as registry
    from inventory_tracking.levels.model import Level
    from tests.inventory_tracking.macros.fakes import Game

    play = Game(someone())
    hunter = Hunter(lambda: Level(101, ()), build=registry.FALLBACK)
    runner, run, _ = building(play, hunter)
    with pytest.raises(Abort, match=r'attack mode off: the build \(generic\) has no attack of its own'):
        runner.perform(run, run.actuator, 'hunt any', lambda world, skills=(): {})
    assert play.said == ['Attack mode on']
    assert play.keys.events == []


def test_attack_mode_is_played_by_the_build_chosen_at_its_first_look():
    from inventory_tracking import builds as registry
    from inventory_tracking.levels.model import Level
    from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, KEYS, Game, world

    start = world(area=101, slots=HUNT_SLOTS)
    play = Game(replace(start, player=replace(character_of(start), consume=True)))
    hunter = Hunter(lambda: Level(101, ()), build=registry.FALLBACK)  # as the service makes it, before any game
    runner, run, _ = building(play, hunter)
    play.arrivals.append((1.0, run.cancelled.set))
    with pytest.raises(Cancelled):
        runner.perform(run, run.actuator, 'hunt any', lambda world, skills=(): {skill: KEYS[skill] for skill in skills})
    assert hunter.build is BUILD
    assert hunter.pick == runner._pick
    assert play.said[0] == 'Attack mode on'
    assert not any('no attack' in line for line in play.said)


def test_the_macro_request_prebuffs_by_the_chosen_build_and_asks_for_its_keys():
    from inventory_tracking.macros.routines import prebuff_keys
    from tests.inventory_tracking.macros.fakes import KEYS, Game, world

    play, asked = Game(world()), []
    runner, run, _ = building(play)
    run.keys = {}

    def key_names(found, skills=None):
        # as `_execute`: no skills named are the prebuff's of the build the run plays
        asked.append(prebuff_keys(run.build) if skills is None else skills)
        return dict(KEYS)

    runner.perform(run, run.actuator, 'prebuff', key_names)
    assert run.build is BUILD
    assert BUILD.weapons is not None
    assert asked[0] == prebuff_keys(BUILD)
    assert play.pressed() == ['q', '6', 'q', 'g', 'r']
    assert run.prebuff_hands == BUILD.weapons.prebuff
    assert run.battle_hands == BUILD.weapons.battle
    assert play.said[-1] == 'Prebuff done'


@pytest.mark.parametrize('strike', [False, True])
def test_the_macro_request_of_a_character_without_weapon_sets_stops_as_it_did(strike):
    from inventory_tracking.builds.generic import GENERIC
    from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
    from inventory_tracking.builds.warlock.skills import ECHOING_STRIKE
    from tests.inventory_tracking.macros.fakes import KEYS, Game

    play = Game(someone(right_skill=ECHOING_STRIKE) if strike else someone())
    runner, run, _ = building(play)
    with pytest.raises(Abort, match=r'^no macro for Someone$'):
        runner.perform(run, run.actuator, 'prebuff', lambda found, skills=None: dict(KEYS))
    assert run.build is (ECHOING_STRIKE_BUILD if strike else GENERIC)
    assert play.keys.events == []


def test_the_macro_request_of_a_build_with_nothing_to_prebuff_stops_with_the_reason():
    from inventory_tracking.builds.characters import played_by
    from inventory_tracking.builds.generic import GENERIC
    from tests.inventory_tracking.macros.fakes import KEYS, Game, world

    plain = played_by(GENERIC, 'CybergrindAA')  # weapon sets, and no buff plan
    play = Game(world())
    runner, run, _ = building(play, builds=(plain,), fallback=GENERIC)
    with pytest.raises(Abort, match=r'nothing to prebuff: the build \(generic\) has no prebuff of its own'):
        runner.perform(run, run.actuator, 'prebuff', lambda found, skills=None: dict(KEYS))
    assert run.build is plain
    assert play.pressed() == []


def test_a_warning_stays_on_the_card_above_what_is_said_until_it_is_taken_back():
    # user, 2026-10-12: "we should give an active warning that must be visible to the user": a line the
    # next thing said wipes is not one (Drifter Cavern, 20:00 that day).
    shown = []
    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=SAVED_GAMES, display=shown.append)
    runner._warn('Inventory full: Superior Old Book left on the ground')
    runner._say('Walking 16 toward the monster')
    runner._show([])
    assert shown[-3:] == [
        ['Macro: Inventory full: Superior Old Book left on the ground'],
        ['Macro: Inventory full: Superior Old Book left on the ground', 'Macro: Walking 16 toward the monster'],
        ['Macro: Inventory full: Superior Old Book left on the ground'],
    ]
    runner._warn(None)
    runner._say('Attack mode on')
    assert shown[-2:] == [[], ['Macro: Attack mode on']]


def test_a_warning_not_given_again_leaves_the_card_after_a_while(monkeypatch):
    shown = []
    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=SAVED_GAMES, display=shown.append)
    runner._warn('Inventory full: Magic Kriss left on the ground')
    assert runner.warning is not None
    given = runner.warning[1]
    monkeypatch.setattr(runner_module.time, 'monotonic', lambda: given + runner_module.WARNING_SECONDS + 1)
    runner._say('Attack mode on')
    assert shown[-1] == ['Macro: Attack mode on']


def test_every_run_is_given_the_builds_weapon_sets_not_only_the_prebuff_and_attack_mode():
    from inventory_tracking import builds
    from tests.inventory_tracking.macros.fakes import Game, world

    build = next(build for build in builds.BUILDS if build.weapons is not None)
    assert build.weapons is not None
    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=SAVED_GAMES)
    run = Game(world()).run()
    run.prebuff_hands = run.battle_hands = frozenset()

    runner.wear(run, build)

    assert run.battle_hands == build.weapons.battle
    assert run.prebuff_hands == build.weapons.prebuff


# -- a flip of the game's input mode under a run (rca/2026-10-14/run-1904-findings.md §3.2) -------------------------


def test_a_flip_under_a_step_ends_it_and_the_same_request_starts_again(caplog):
    """KP_5 (the service's pad hotkey) flipped the game to controller mode under a run by the keys: the run could not
    act, and the pursuit looped 57 times in 7 s. Now the flip ends the run and the request is made again once, in
    the new mode (`play_by` chooses it at the run's start), said once."""
    shown, runs, done = [], [], threading.Event()

    def execute(cancelled, routine):
        runs.append(routine)
        if len(runs) == 1:
            raise Flipped('the game left keyboard mode (a pad was touched)')
        done.set()

    runner = make(execute, shown)
    with caplog.at_level('INFO'):
        assert runner.request(10.0, 10.1, 'teleport')
        assert done.wait(5)
        joined(runner)
    assert runs == ['teleport', 'teleport']
    flips = [r.getMessage() for r in caplog.records if r.getMessage().startswith('Macro: input mode flipped')]
    assert flips == [
        'Macro: input mode flipped under teleport (the game left keyboard mode (a pad was touched)): the run ends '
        'and the same request starts again'
    ]
    assert not any(line and line[0].startswith('Macro stopped') for line in shown)


def test_a_flip_under_attack_mode_keeps_it_on_and_starts_it_again():
    runs, again = [], threading.Event()

    def execute(cancelled, routine):
        runs.append(routine)
        if len(runs) == 1:
            raise Flipped('the game is in keyboard mode now')
        again.set()
        assert cancelled.wait(5)
        raise Cancelled

    runner = make(execute, [])
    assert runner.request(10.0, 10.1, 'hunt any')
    assert again.wait(5)
    assert runs == ['hunt any', 'hunt any']
    assert runner.attack_mode
    runner.request(11.0, 11.1, 'hunt any')  # off
    joined(runner)
    assert not runner.attack_mode


def test_a_mode_that_keeps_flipping_stops_the_run(caplog):
    shown, runs = [], []

    def execute(cancelled, routine):
        runs.append(routine)
        raise Flipped('the input mode is switching')

    runner = make(execute, shown)
    with caplog.at_level('INFO'):
        assert runner.request(10.0, 10.1, 'teleport')
        ends = time.monotonic() + 5
        while ['Macro stopped: the input mode is switching'] not in shown and time.monotonic() < ends:
            time.sleep(0.01)
        joined(runner)
    assert runs == ['teleport'] * (runner_module.FLIPS_AGAIN + 1)
    assert ['Macro stopped: the input mode is switching'] in shown
    assert 'restarts in 10 s, the run stops' in caplog.text


def test_the_run_made_again_after_a_flip_waits_for_the_flip_to_be_over():
    from inventory_tracking.macros.pad import PadPlay
    from inventory_tracking.models import InputMode
    from tests.inventory_tracking.macros.fakes import SLOTS, Game, world

    modes = iter([InputMode(False, True, True), InputMode(False, True, True), InputMode(True)])
    last = [InputMode(True)]

    def mode():
        last[0] = next(modes, last[0])
        return last[0]

    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=SAVED_GAMES)
    runner.pad_play = PadPlay(lambda: None, mode, lambda: None, lambda: ())
    run = Game(world(slots=SLOTS)).run()
    runner.settling = True
    runner.play_by(run, run.actuator, 'pickup')
    assert run.pad is not None  # played by the pad once the flip to controller mode was over
    assert not runner.settling


def test_the_loop_key_starts_a_leg_and_each_leg_is_followed_by_the_next_until_one_stops():
    # routes/lower-kurast-loop-plan.md phase 4: KP_6 on; the character's death ends the loop, saying why
    shown, made = [], []

    def execute(cancelled, routine):
        made.append(routine)
        if len(made) == 3:
            raise Dead('the character is dead')

    runner = make(execute, shown)
    assert runner.request(10.0, 10.1, 'loop')
    assert not runner.loop.on  # a single press is judged once the double press's window is over (phase 7)
    deadline = time.monotonic() + 5
    while len(made) < 3 and time.monotonic() < deadline:
        time.sleep(0.01)
    joined(runner)
    assert made == ['loop'] * 3
    assert not runner.loop.on
    assert ['Loop stopped: the character is dead'] in shown
    runner.close()


def test_the_level_run_a_leg_asks_for_is_followed_by_the_next_leg():
    shown, made = [], []

    def execute(cancelled, routine):
        made.append(routine)
        if made == ['loop']:
            runner.attack_mode = True  # the chests' leg: the KP_1 level run follows as attack mode
        elif len(made) == 3:
            raise Dead('enough')

    runner = make(execute, shown)
    assert runner.request(10.0, 10.1, 'loop')
    deadline = time.monotonic() + 5
    while len(made) < 3 and time.monotonic() < deadline:
        time.sleep(0.01)
    joined(runner)
    assert made == ['loop', 'hunt any', 'loop']
    runner.close()


def test_a_legs_stop_leaves_the_game_and_the_loop_goes_on_past_the_recoveries_after_a_pause(monkeypatch):
    # The player, 2026-10-17: "we should try to not stuck in some weird situation without being able to fix it from
    # agent": a leg's stop is recovered from by leaving the game (macros/loop.py `recover`); 2026-10-18: "fully
    # prevent us from stopping": past RECOVERIES the next leg waits RECOVERY_PAUSE, and the loop stays on
    from inventory_tracking.macros import loop as loop_module

    monkeypatch.setattr(loop_module, 'RECOVERY_PAUSE', 0.05)
    shown, made, abandon = [], [], []

    def execute(cancelled, routine):
        made.append(routine)
        abandon.append(runner.loop.abandon)
        raise Abort('the stash did not open with the inventory')

    runner = make(execute, shown)
    assert runner.request(10.0, 10.1, 'loop')
    deadline = time.monotonic() + 5
    while len(made) < RECOVERIES + 3 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert runner.loop.on  # past the recoveries too
    assert runner.loop.cooling > 0
    runner.loop.stop()
    deadline = time.monotonic() + 5
    while runner.working and time.monotonic() < deadline:  # the leg under way ends: no new one with the loop off
        time.sleep(0.01)
    assert not runner.working
    assert made[: RECOVERIES + 3] == ['loop'] * (RECOVERIES + 3)
    assert abandon[: RECOVERIES + 1] == [False] + [True] * RECOVERIES  # each leg after a stop leaves the game
    assert ['Loop stopped: the stash did not open with the inventory'] not in shown
    runner.close()


def test_a_game_with_a_valuable_on_the_ground_is_never_left_the_loop_stops_instead():
    # The player, 01:21 on 2026-10-17: "you we're killed the game while having valuable pickup on the ground!!! that
    # is the exact thing we want ot avoid": the loop left a game with a Flawless Diamond on the ground, the inventory
    # full ("inventory full: no room for Flawless Diamond", 01:20:39)
    shown, made = [], []

    def execute(cancelled, routine):
        made.append(routine)
        raise Abort('inventory full: no room for Flawless Diamond', cause='room')

    runner = make(execute, shown)
    runner.valuable_left = lambda: 'Flawless Diamond'
    assert runner.request(10.0, 10.1, 'loop')
    deadline = time.monotonic() + 5
    while runner.loop.on or not made:
        if time.monotonic() > deadline:
            break
        time.sleep(0.01)
    joined(runner)
    assert made == ['loop']
    assert not runner.loop.abandon
    assert not runner.loop.on
    assert [
        'Loop stopped: inventory full: no room for Flawless Diamond; Flawless Diamond lies on the ground: '
        'the loop stops here'
    ] in shown
    runner.close()


def test_a_valuable_with_no_room_makes_room_in_the_cube_then_drops_an_item_once_a_game_then_the_loop_stops():
    # 04:32:26 on 2026-10-17: "the character has not moved for 45 s; Grand Charm lies on the ground: the loop stops
    # here": the first time in a game the loop's items go into the cube at the next leg and the loop goes on; the
    # second, an item taken only to identify is dropped for it (21:00:03); the third, the loop stops for the player
    shown, made, room = [], [], []

    def execute(cancelled, routine):
        made.append(routine)
        room.append((runner.loop.make_room, runner.loop.drop_room))
        runner.loop.seen = ('cyber1', 0.0)  # the service's poll saw the game
        raise Abort('the character has not moved for 45 s', cause='stall')

    runner = make(execute, shown)
    runner.valuable_left = lambda: 'Grand Charm'
    assert runner.request(10.0, 10.1, 'loop')
    deadline = time.monotonic() + 5
    while len(made) < 3 and time.monotonic() < deadline:
        time.sleep(0.01)
    joined(runner)
    assert made == ['loop', 'loop', 'loop']
    assert room == [(False, False), (True, False), (True, True)]  # the cube first, then a drop (this leg acts on none)
    assert not runner.loop.on  # the same game again: the loop stops for the player
    assert runner.loop.room_tried == runner.loop.dropped == 'cyber1'
    runner.close()


def test_the_loop_key_again_stops_the_leg_working_and_nothing_follows():
    shown, made = [], []

    def execute(cancelled, routine):
        made.append(routine)
        assert cancelled.wait(5)
        raise Cancelled

    runner = make(execute, shown)
    assert runner.request(10.0, 10.1, 'loop')
    assert runner.request(10.5, 10.6, 'loop')
    joined(runner)
    assert not runner.loop.on
    assert not runner.working
    assert made == ['loop']
    assert ['Macro: Loop off'] in shown
    runner.close()


def test_a_double_press_of_the_loop_key_switches_its_pickup_mode_and_leaves_the_loop_as_it_was():
    # routes/lower-kurast-loop-plan.md phase 7 (the player, 2026-10-16): "show mode (switch with double KP_6 click)"
    from inventory_tracking.macros.pickmode import SURE, TRADE

    shown, made = [], []
    runner = make(lambda cancelled, routine: made.append(routine), shown)
    assert runner.pickup_mode == SURE  # the default: only the sure valuables
    assert runner.request(10.0, 10.0, 'loop')
    assert runner.request(10.2, 10.2, 'loop')
    deadline = time.monotonic() + 2
    while runner.pickup_mode == SURE and time.monotonic() < deadline:
        time.sleep(0.01)
    assert runner.pickup_mode == TRADE  # the trade goods too (the player, 2026-10-18)
    assert not runner.loop.on
    assert made == []
    assert ['Macro: Loop pickup: sure and trade goods'] in shown

    for at in (20.0, 20.1, 20.2, 20.3):  # a mashed key: nothing
        assert runner.request(at, at, 'loop')
    deadline = time.monotonic() + 2
    while ['Macro: KP_6 pressed 4 times together: nothing switched'] not in shown and time.monotonic() < deadline:
        time.sleep(0.01)
    assert ['Macro: KP_6 pressed 4 times together: nothing switched'] in shown
    assert runner.pickup_mode == TRADE
    assert not runner.loop.on
    runner.close()


def test_three_presses_of_the_loop_key_switch_its_run_and_a_restart_keeps_it():
    # The player, 2026-10-18: "rebuild loop start to accept what type of run we're going to run"
    from inventory_tracking.macros.loop import ANDARIEL, LK

    shown, made = [], []
    runner = make(lambda cancelled, routine: made.append(routine), shown)
    assert runner.loop.kind == LK
    for at in (10.0, 10.1, 10.2):
        assert runner.request(at, at, 'loop')
    deadline = time.monotonic() + 2
    while runner.loop.kind == LK and time.monotonic() < deadline:
        time.sleep(0.01)
    assert runner.loop.kind == ANDARIEL
    assert runner.loop.chosen  # no place overrides it
    assert ['Macro: Loop run: Andariel'] in shown
    assert not runner.loop.on
    assert runner.resume_state()['loop_kind'] == 'andariel'
    runner.close()

    after = make(lambda cancelled, routine: None, [])
    after.resume({'loop': False, 'loop_kind': 'andariel'})
    assert after.loop.kind == ANDARIEL
    assert after.loop.chosen
    after.close()


def test_the_loops_pickup_mode_filters_the_drops_only_with_the_loop_on():
    from inventory_tracking.game.records import VALUABLE, Drop, Loot
    from inventory_tracking.macros.pickmode import REGULAR

    runner = make(lambda cancelled, routine: None, [])
    blade = Drop(1, 0.0, 0.0, 'Magic Blade', VALUABLE, prized=False, source='shown', txt=0, quality=4)
    loot = Loot(drops=(blade,))
    assert runner._picked(loot) == loot  # the loop off: KP_1 and the rest take what they always did
    assert runner.run_badge is None
    runner.loop.on = True
    assert runner._picked(loot).drops == ()  # the loop's default: the sure valuables only
    assert runner.run_badge == 'LOOP SURE'  # on the HUD beside attack mode
    runner.pickup_mode = REGULAR
    assert runner._picked(loot) == loot
    assert runner.run_badge == 'LOOP ALL'
    from inventory_tracking.macros.loop import ANDARIEL

    runner.loop.kind = ANDARIEL
    assert runner.run_badge == 'LOOP ALL ANDARIEL'
    runner.close()


class _Memory:
    where, where_area = (5695.0, 2857.0), 79


class _Run:
    def __init__(self, x: float, y: float, area: int):
        self.player = type('P', (), {'x': x, 'y': y, 'area': area})()

    def world(self):
        return type('W', (), {'player': self.player})()


def test_the_loop_goes_back_for_a_valuable_it_saw_and_no_press_picked_up(monkeypatch):
    # The Flawless Emerald of 08:58:34 on 2026-10-17 (routes/lower-kurast-loop-plan.md §14): seen in a flight, 104
    # units off when the run ended and no longer read; the "what is left" press found nothing, Town Portal followed
    from inventory_tracking.game.records import VALUABLE, Drop, Loot
    from inventory_tracking.macros.pickup import FETCH_HOPS

    gone_to = []
    monkeypatch.setattr(
        runner_module, 'approach', lambda run, found, level, keys, hops: gone_to.append((found.label, hops))
    )
    runner = make(lambda cancelled, routine: None, [])
    emerald = Loot(drops=(Drop(41, 5798.0, 2870.0, 'Flawless Emerald', VALUABLE),), game=('g', 7))
    runner._sighted(cast(GameMemory, _Memory()), emerald)  # the loop off: nothing is noted
    assert runner.sightings.left() is None
    runner.loop.on = True
    runner._sighted(cast(GameMemory, _Memory()), emerald)
    runner._sighted(cast(GameMemory, _Memory()), Loot(game=('g', 7)))  # out of the read
    assert runner.sightings.left() == 'Flawless Emerald at (5798, 2870)'
    assert not runner._fetch(cast(Run, _Run(0.0, 0.0, 75)), None, KEYS)  # not in its level: no trip
    assert runner._fetch(cast(Run, _Run(5695.0, 2857.0, 79)), None, KEYS)
    assert gone_to == [('Flawless Emerald', FETCH_HOPS)]  # the whole way (a Flawless Topaz 92 short, 13:15:37)
    runner.close()


def test_a_full_stash_stack_skips_its_rune_but_never_a_gem():
    # 15:19:42 on 2026-10-17: a Flawless Amethyst, its stash stack at 99, was left on the ground twice (the player:
    # "we just left flawlest amethyst and left the game. something is wrong"); the ruling was the runes'
    from inventory_tracking.game.records import VALUABLE, Drop, Loot
    from inventory_tracking.macros.pickmode import REGULAR

    runner = make(lambda cancelled, routine: None, [])
    runner.loop.on, runner.pickup_mode = True, REGULAR
    amethyst = Drop(1, 0.0, 0.0, 'Flawless Amethyst', VALUABLE, source='material', txt=575)
    tal = Drop(2, 0.0, 0.0, 'Tal Rune', VALUABLE, source='rune', txt=631)
    runner.loop.full = {575, 631}
    assert runner._picked(Loot(drops=(amethyst, tal))).drops == (amethyst,)
    assert runner.loop.sold_full == {631}
    runner.close()


def test_a_terror_zones_run_ended_at_a_door_goes_through_and_runs_the_next_level_with_no_press(monkeypatch):
    # The player, 00:27 on 2026-10-18: "yes, go to next level without press"
    from types import SimpleNamespace

    from inventory_tracking.macros.runmode import TERROR, Mode

    monkeypatch.setattr(runner_module, 'ONWARD_PAUSE', 0.0)
    places = iter([('cyber32', 36), ('cyber32', 37), ('cyber32', 38), ('cyber32', 39)])
    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=SAVED_GAMES, place=lambda: next(places))
    pressed: list[str] = []
    monkeypatch.setattr(runner, '_press', pressed.append)
    hunter = SimpleNamespace(mode=Mode(True, TERROR), bearings=SimpleNamespace(terror=lambda area: area < 38))
    monkeypatch.setattr(runner, 'hunter', hunter)
    runner.attack_mode = True

    def presses(n: int) -> list[str]:
        deadline = time.monotonic() + 2.0
        while len(pressed) < n and time.monotonic() < deadline:
            time.sleep(0.01)
        return pressed

    runner.poll(10.0)  # in level 36
    runner._run_over('at Next level: going through takes a press')
    assert presses(1) == ['teleport']  # the door
    runner.poll(12.0)  # level 37 entered, the zone's
    assert presses(2) == ['teleport', 'pickup']
    runner._run_over('at Next level: going through takes a press')
    runner.poll(14.0)  # level 38: not the zone's: no run pressed
    time.sleep(0.05)
    assert pressed == ['teleport', 'pickup', 'teleport']
    runner._run_over('nothing is left to go to on this level')  # no door: nothing pressed
    hunter.mode = Mode(True)  # nor out of a terror zone
    runner._run_over('at Next level: going through takes a press')
    time.sleep(0.05)
    assert pressed == ['teleport', 'pickup', 'teleport']


def test_a_restart_keeps_the_valuables_seen_and_still_on_the_ground():
    # 13:18 on 2026-10-18: a restart forgot a Flawless Topaz 94 units off, and the game was left with it on the ground
    import json

    from inventory_tracking.game.records import VALUABLE, Drop, Loot

    runner = make(lambda cancelled, routine: None, [])
    runner.loop.on = True
    topaz = Loot(drops=(Drop(41, 22628.0, 6700.0, 'Flawless Topaz', VALUABLE),), game=('cyber9', 7))
    runner._sighted(cast(GameMemory, _Memory()), topaz)
    runner.sightings.items[41].tries = 2  # its trips back spent (15:53:19 on 2026-10-18: a Ring)
    state = json.loads(json.dumps(runner.resume_state()))  # as appraisal/service.py `write_resume` keeps it
    runner.close()

    after = make(lambda cancelled, routine: None, [])
    after.resume(state)
    assert after.sightings.left() == 'Flawless Topaz at (22628, 6700)'
    assert after.sightings.items[41].tries == 0  # a restart is made for a fix: its trips back begin again
    assert after.sightings.game == ('cyber9', 7)
    after.resume({'loop': False, 'sightings': {'items': [{'bad': 1}]}})  # a malformed state is none
    after.close()


def andariel_room_runner(carrying: bool):
    from inventory_tracking.macros.loop import ANDARIEL

    runner = make(lambda cancelled, routine: None, [])
    runner.loop.on, runner.loop.kind, runner.loop.seen = True, ANDARIEL, ('cyberr60', 0.0)
    runner.loop.carrying = carrying
    runner.valuable_left = lambda: 'Flawless Topaz at (22540, 9550)'
    runner.loop.room_tried = runner.loop.fetch_again = 'cyberr60'  # the cube tried, the leg made again
    return runner


def test_in_the_loop_a_chipped_gem_with_no_room_is_held_the_cube_then_a_trip_to_town_then_taken():
    # The player, 2026-10-18 17:50, on Q1: "we should stop and clear inventory with our designated town routine": the
    # loop's press holds a plain valuable with no room (cause 'room'), the guard keeps the game for it, the room rules
    # make room in the cube first, then a trip to town and back through the portal, and the press after takes it
    from dataclasses import replace

    from inventory_tracking.game.records import VALUABLE, Drop, Loot
    from inventory_tracking.macros import lootpolicy
    from inventory_tracking.macros.loop import ANDARIEL, CATACOMBS_4, TRIP, next_leg
    from inventory_tracking.macros.pickup import pick_up
    from tests.inventory_tracking.macros.fakes import Game, world

    gem = Drop(74, 5008.0, 5003.0, 'Chipped Amethyst', VALUABLE, (1, 1), prized=False, source='material')
    full, roomy = ('##########',) * 4, ('#########.',) + ('##########',) * 3
    play = Game(world(area=CATACOMBS_4))
    play.loot = Loot((gem,), room=full, game=('cyber32', 1))
    assert lootpolicy.verdict(gem, lootpolicy.GUARD, room=False, shown=False).hold  # the game is kept for it

    def press() -> bool:  # runner.py `take_one`'s press
        return pick_up(play.run(), None, lambda _world, skills: KEYS, lambda: None, looped=True)

    runner = make(lambda cancelled, routine: None, [])
    loop = runner.loop
    loop.on, loop.kind, loop.seen, loop.carrying = True, ANDARIEL, ('cyber32', 0.0), True
    runner.valuable_left = lambda: 'Chipped Amethyst'
    with pytest.raises(Abort) as held:
        press()
    runner._loop_stopped(held.value)
    assert (loop.make_room, loop.room_tried, loop.trip_due) == (True, 'cyber32', False)  # the cube first
    loop.make_room = False  # (the next leg's: the cube took nothing that made room for it)
    with pytest.raises(Abort) as again:
        press()
    runner._loop_stopped(again.value)
    assert loop.trip_due  # a trip to town, not a drop
    assert loop.on
    assert not loop.drop_room
    assert next_leg(play.world, None, loop) == TRIP
    play.loot = replace(play.loot, room=roomy)  # back through the portal, the visit made room
    assert press()
    assert play.picked == ['Chipped Amethyst']
    runner.close()


def test_by_hand_the_press_still_moves_on_from_a_chipped_gem_with_no_room():
    # Outside the loop nothing changed with the ruling: KP_1's press goes on to its seek step
    from inventory_tracking.game.records import VALUABLE, Drop, Loot
    from inventory_tracking.macros.pickup import pick_up
    from tests.inventory_tracking.macros.fakes import Game, world

    gem = Drop(74, 5008.0, 5003.0, 'Chipped Amethyst', VALUABLE, (1, 1), prized=False, source='material')
    play = Game(world(area=101))
    play.loot = Loot((gem,), room=('##########',) * 4)
    went_on = []
    assert not pick_up(play.run(), None, lambda _world, skills: KEYS, lambda: went_on.append(True))
    assert went_on == [True]
    assert play.picked == []


def test_a_room_stop_on_andariels_level_is_a_trip_only_with_something_the_visit_takes_away():
    # 13:38:17 on 2026-10-18: only the player's charms carried, the Fortress did nothing and the trip came straight back
    runner = andariel_room_runner(carrying=True)
    runner._loop_stopped(Abort('the character has not moved for 45 s', cause='stall'))
    assert runner.loop.trip_due
    runner.close()
    runner = andariel_room_runner(carrying=False)
    runner._loop_stopped(Abort('the character has not moved for 45 s', cause='stall'))
    assert not runner.loop.trip_due
    assert runner.loop.drop_room  # the next room rule
    runner.close()


def test_a_stop_for_another_cause_than_room_is_no_trip_nor_drop():
    # 13:15:40 on 2026-10-18: "Flawless Topaz is 94 away" (a trip back cut short) bought a trip to town that could not
    # help: the guard stops the loop for the valuable
    runner = andariel_room_runner(carrying=True)
    runner._loop_stopped(Abort('Flawless Topaz is 94 away'))
    assert not runner.loop.trip_due
    assert not runner.loop.drop_room
    assert not runner.loop.on
    runner.close()


def test_the_return_from_a_trip_gives_the_sightings_their_trips_back_again_once(monkeypatch):
    from types import SimpleNamespace
    from typing import Any, cast

    runner = andariel_room_runner(carrying=True)
    again = []
    monkeypatch.setattr(runner.sightings, 'again', lambda: again.append(1))
    monkeypatch.setattr(runner.sightings, 'fetch', lambda *a: False)
    run = cast(Any, SimpleNamespace(world=lambda: SimpleNamespace(player=SimpleNamespace(x=1.0, y=2.0, area=37))))
    runner._fetch(run, None, None)
    assert again == []  # no trip this game
    runner.loop.trip = runner.loop.returned = 'cyberr60'
    runner._fetch(run, None, None)
    runner._fetch(run, None, None)
    assert again == [1]
    # The player, 2026-10-18 16:50: "one game can do several trips to the town": each return gives them again, once
    runner.loop.trips, runner.loop.returned = 2, None  # the second trip: on its way
    runner._fetch(run, None, None)
    assert again == [1]
    runner.loop.returned = 'cyberr60'  # back through the portal
    runner._fetch(run, None, None)
    runner._fetch(run, None, None)
    assert again == [1, 1]
    runner.close()


def test_a_game_makes_another_trip_for_room_after_one_that_made_room():
    # The player, 2026-10-18 16:50: "one game can do several trips to the town"
    runner = andariel_room_runner(carrying=True)
    loop = runner.loop
    loop.trip = loop.returned = 'cyberr60'
    loop.trips, loop.trip_gained = 1, 6  # the first trip is back, 6 cells more room
    runner._loop_stopped(Abort('the character has not moved for 45 s', cause='stall'))
    assert loop.trip_due
    assert loop.on
    runner.close()


@pytest.mark.parametrize(
    ('trips', 'returned', 'gained'),
    [(1, None, 6), (1, 'cyberr60', 0), (3, 'cyberr60', 6)],
    ids=['the last one not back yet', 'the last one made no room', 'TRIPS_A_GAME made'],
)
def test_no_trip_for_room_while_one_is_on_its_way_after_one_that_made_no_room_or_past_the_bound(
    trips, returned, gained
):
    # A trip that cannot help is not made again and again: the drop rule, then the guard's stop
    from inventory_tracking.macros.loop import TRIPS_A_GAME

    assert TRIPS_A_GAME == 3
    runner = andariel_room_runner(carrying=True)
    loop = runner.loop
    loop.trip, loop.returned, loop.trips, loop.trip_gained = 'cyberr60', returned, trips, gained
    runner._loop_stopped(Abort('the character has not moved for 45 s', cause='stall'))
    assert not loop.trip_due
    assert loop.drop_room
    runner.close()


def test_a_full_stash_after_a_town_visit_stops_the_loop_in_town(caplog):
    # The player, 2026-10-18 16:50: "if stash is full - we need to stop loop": no recovery, no game left, whatever
    # the level holds (the loop stands in town: nothing is left behind by it)
    runner = andariel_room_runner(carrying=True)
    caplog.set_level('INFO')
    runner._loop_stopped(Abort('the stash is full: Ber Rune, Battle Boots', cause='stash'))
    assert not runner.loop.on
    assert not runner.loop.abandon
    assert not runner.loop.trip_due
    assert not runner.loop.make_room
    assert not runner.loop.drop_room
    assert 'Macro: loop stopped: the stash is full: Ber Rune, Battle Boots' in caplog.text
    runner.close()


def gheeds_runner(rows_free: bool = True):
    from inventory_tracking.game.records import Carried
    from inventory_tracking.macros.charms import GHEEDS_FORTUNE, UNIQUE, grand_charm
    from inventory_tracking.macros.loop import ANDARIEL

    runner = make(lambda cancelled, routine: None, [])
    runner.loop.on, runner.loop.kind, runner.loop.seen = True, ANDARIEL, ('cyberr48', 0.0)
    theirs = Carried(1, grand_charm(), 0, 0, (1, 3), quality=UNIQUE, unique=GHEEDS_FORTUNE)
    filler = tuple(Carried(10 + x, 999, x, 0, (1, 4)) for x in range(1, 10 if not rows_free else 5))
    runner.loop.own = frozenset({(theirs.txt, 0, 0), *((i.txt, i.x, i.y) for i in filler)})
    runner.carried_now = lambda: Pack((theirs, *filler))
    runner.valuable_left = lambda: "Unique Grand Charm (Gheed's Fortune?) at (22543, 9556)"
    return runner


@pytest.mark.parametrize(
    'why',
    [
        "Unique Grand Charm (Gheed's Fortune?) was under the pointer at 3 aims and no click picked it up",
        'the character has not moved for 45 s',  # 13:37:31 on 2026-10-18: the stand-by, then room, a trip, a drop
    ],
)
def test_a_unique_grand_charm_left_with_the_players_gheeds_carried_is_the_swap_before_any_room_rule(why):
    runner = gheeds_runner()
    runner._loop_stopped(Abort(why))
    assert runner.loop.swap_due
    assert not runner.loop.make_room
    assert not runner.loop.trip_due
    assert not runner.loop.drop_room
    assert runner.loop.on
    runner.loop.swap_due, runner.loop.swap = False, 'cyberr48'  # once a game
    runner._loop_stopped(Abort(why))
    assert not runner.loop.swap_due
    runner.close()


@pytest.mark.parametrize('stop', ['stall', 'refused'])
def test_with_no_1x3_free_the_cube_first_then_the_gheeds_swap_is_the_trip_to_town_all_the_same(stop):
    # The player, 2026-10-18 16:50: "refused grand charm - should cause a trip": with no block for it the room rules
    # passed a refusal by (not room), and the loop stood by the charm; the swap needs no 1 x 3 free: the player's
    # charm goes onto a shared page, and its own block takes the new one
    runner = gheeds_runner(rows_free=False)
    why = Abort('the character has not moved for 45 s', cause='stall') if stop == 'stall' else refused_charm()
    runner._loop_stopped(why)
    assert not runner.loop.swap_due
    assert runner.loop.make_room  # the cube first: a block may come of it
    assert runner.loop.room_tried == 'cyberr48'
    runner.loop.make_room = False  # (the next leg's)
    runner._loop_stopped(why)
    assert runner.loop.swap_due
    assert not runner.loop.trip_due
    assert not runner.loop.drop_room
    assert runner.loop.on
    runner.close()


def test_a_refusal_with_no_1x3_free_outside_the_loops_routine_makes_room_then_asks_the_swap():
    runner = gheeds_runner(rows_free=False)
    assert runner._carry_one(refused_charm())  # the level run ends: the cube's move, then the run again
    assert runner.loop.make_room
    assert not runner.loop.swap_due
    assert runner._carry_one(refused_charm())
    assert runner.loop.swap_due
    runner.close()


def test_the_new_gheeds_still_not_taken_with_the_players_parked_fetches_theirs_back_first():
    from inventory_tracking.macros.charms import Parked
    from inventory_tracking.macros.loop import CHOOSE, PICK

    runner = gheeds_runner()
    runner.loop.swap, runner.loop.parked, runner.loop.gheed = 'cyberr48', Parked(1, 2, (620, 0, 0), 30), PICK
    runner._loop_stopped(Abort('the character has not moved for 45 s', cause='stall'))
    assert runner.loop.gheed == CHOOSE
    assert runner.loop.on
    state = runner.resume_state()
    assert state['gheeds'] == {'unit': 1, 'page': 2, 'cell': [620, 0, 0], 'magic_find': 30}
    runner.close()
    after = make(lambda cancelled, routine: None, [])
    after.resume(state)
    assert after.loop.parked == Parked(1, 2, (620, 0, 0), 30)
    after.close()


def refused_charm():
    from inventory_tracking.game.records import VALUABLE, Drop
    from inventory_tracking.macros.charms import UNIQUE, grand_charm
    from inventory_tracking.macros.pickup import Refused

    charm = Drop(60, 22543.0, 9556.0, "Unique Grand Charm (Gheed's Fortune?)", VALUABLE, (1, 3), txt=grand_charm(),
                 quality=UNIQUE)  # fmt: skip
    return Refused(charm, f"{charm.label} was refused by the game: another Gheed's Fortune is carried")


def test_a_refused_click_is_the_gheeds_swap_whatever_valuable_the_ground_names_first(caplog):
    # The refusal names its charm (macros/pickup.py `Refused`): the ground's first valuable may be another
    runner = gheeds_runner()
    runner.valuable_left = lambda: 'Flawless Topaz'
    caplog.set_level('INFO')
    runner._loop_stopped(refused_charm())
    assert runner.loop.swap_due
    assert not runner.loop.make_room
    assert "another Gheed's Fortune is carried; Unique Grand Charm (Gheed's Fortune?) with the player's" in caplog.text
    runner.close()


def test_a_refusal_outside_the_loops_routine_asks_the_swap_only_with_the_loop_on():
    runner = gheeds_runner()
    assert runner._carry_one(refused_charm())
    assert runner.loop.swap_due
    runner.loop.swap_due = False
    runner.loop.on = False
    assert not runner._carry_one(refused_charm())
    assert not runner.loop.swap_due
    runner.close()


def test_the_pickup_steps_refusal_during_the_loop_ends_attack_mode_and_the_swap_leg_follows():
    # The pickup step attack mode asked for met the carry-one refusal: no leg of the mode's follows, the loop's does
    made: list[str] = []
    looped = threading.Event()

    def execute(cancelled, routine):
        made.append(routine)
        if routine == 'pickup':
            raise refused_charm()
        runner.loop.on = False  # the loop's leg (the swap's): nothing after it here
        looped.set()

    runner = gheeds_runner()
    runner.execute = execute
    runner.attack_mode = True
    assert runner.request(10.0, 10.1, 'pickup')
    assert looped.wait(5)
    joined(runner)
    assert made == ['pickup', 'loop']
    assert runner.loop.swap_due
    assert not runner.attack_mode
    runner.close()


def test_the_runner_forgets_the_level_runs_give_ups_at_gheed_stash():
    runner = gheeds_runner()
    forgot: list[bool] = []

    class Hunter:
        def forget_given_up(self) -> None:
            forgot.append(True)

    runner.hunter = Hunter()  # type: ignore[assignment]
    assert runner.loop.forget is not None
    runner.loop.forget()
    assert forgot == [True]
    runner.hunter = None
    runner.close()


def test_a_trip_back_lifts_the_pickups_give_up_and_moves_to_a_valuable_within_a_click(monkeypatch):
    # 15:53:05 on 2026-10-18: a set Ring 5 away under the pointer, 11 clicks from one place took nothing; both trips
    # back found it given up by the pickup (SHUNNED), went nowhere in 0.2 s, and the loop stopped for it
    from types import SimpleNamespace
    from typing import Any, cast

    from inventory_tracking.macros.sightings import Sighting

    gone, moved = [], []
    monkeypatch.setattr(runner_module, 'approach', lambda run, found, level, keys, hops: gone.append(found.label))
    monkeypatch.setattr(
        runner_module, 'moved_in_hand', lambda run, found, level, aspect, keys, why: moved.append((found.label, aspect))
    )
    runner = make(lambda cancelled, routine: None, [])
    ring = Sighting(1235397469, 'Ring', 22553.0, 9560.0, 37, 0.0)
    runner_module.SHUNNED[ring.unit_id] = 1e9

    def run_at(x: float, y: float) -> Any:
        keys = SimpleNamespace(focused_window_rect=lambda: (0, 0, 2560, 1440))
        player = SimpleNamespace(x=x, y=y, area=37)
        return cast(
            Any, SimpleNamespace(world=lambda: SimpleNamespace(player=player), actuator=SimpleNamespace(keys=keys))
        )

    runner._go_back(run_at(22556.3, 9564.3), ring, object(), KEYS)
    assert ring.unit_id not in runner_module.SHUNNED  # the press after tries it again
    assert gone == ['Ring']
    assert moved == [('Ring', 2560 / 1440)]  # 5 away: to it first, the clicks from another footing
    runner._go_back(run_at(22554.0, 9561.0), ring, object(), KEYS)
    assert len(moved) == 1  # at it: clicked from there
    runner._go_back(run_at(22556.3, 9564.3), ring, None, KEYS)
    assert len(moved) == 1  # no level map: no move
    runner.close()


def test_classify_never_reads_the_words():
    from inventory_tracking.macros.runner import classify

    assert classify(Abort('inventory full: no room for Grand Charm')) == 'other'
    assert classify(Abort('the character has not moved for 45 s')) == 'other'
    assert classify(Flipped('inventory full: no room for Grand Charm')) == 'other'
    assert classify(RuntimeError('no room in the inventory')) == 'other'


def test_classify_tells_the_hand_and_the_refusal_by_their_type_and_a_named_cause_first():
    from inventory_tracking.macros.actuator import Hand
    from inventory_tracking.macros.runner import classify
    from inventory_tracking.macros.stops import ROOM_CAUSES

    assert classify(Hand('the mouse was moved')) == 'hand'
    assert classify(Hand('a key was pressed (key code 30)')) == 'hand'
    assert classify(refused_charm()) == 'refused'
    assert classify(Dead('the character is dead')) == 'other'
    assert classify(Cancelled()) == 'other'
    # The raise's cause wins over its words
    assert classify(Abort('inventory full: no room for Grand Charm', cause='room')) == 'room'
    assert classify(Abort('the character has not moved for 45 s', cause='stall')) == 'stall'
    assert classify(Abort('Grand Charm is 40 away', cause='room')) == 'room'
    assert classify(Abort('inventory full: no room for Grand Charm', cause='other')) == 'other'
    # Ruling pending (rca/2026-10-18/arch-loop-orchestration.md §5): the stand is answered as a lack of room
    assert 'stall' in ROOM_CAUSES


def test_a_named_stand_takes_the_room_rule():
    # The watchdog names its stand 'stall' (04:32:26 on 2026-10-17: "the character has not moved for 45 s; Grand
    # Charm lies on the ground")
    runner = make(lambda cancelled, routine: None, [])
    runner.loop.on, runner.loop.seen = True, ('cyber32', 0.0)
    runner.valuable_left = lambda: 'Grand Charm'
    runner._loop_stopped(Abort('the character has not moved for 45 s', cause='stall'))
    assert runner.loop.make_room
    assert runner.loop.room_tried == 'cyber32'
    runner.close()


def test_a_named_room_cause_takes_the_room_rules_whatever_the_words():
    runner = make(lambda cancelled, routine: None, [])
    runner.loop.on, runner.loop.seen = True, ('cyber32', 0.0)
    runner.valuable_left = lambda: 'Grand Charm'
    runner.loop.room_tried = 'cyber32'  # the cube tried: the next room rule
    runner._loop_stopped(Abort('Grand Charm is 40 away', cause='room'))
    assert runner.loop.drop_room
    assert runner.loop.fetch_again is None
    runner.close()


def test_a_farming_visit_short_of_its_contract_hands_it_to_the_loop_and_does_not_stop(monkeypatch):
    """The loop's visit as it was through 2026-10-18 (84.6 kills an hour): a miss is the loop's to weigh (a trip, the
    next visit), never a stop of its own (the stop at every miss stood the loop on 2026-10-19)."""
    from inventory_tracking.macros.town import Contract

    play = Game(world(103, player=player(103)))
    runner = make(lambda _cancelled, _routine: None, [])
    runner.loop.own = frozenset()
    short = Contract(0, False, 0, 0, 11, 'from the Sling', 0, misses=('block 2x4 taken',))
    monkeypatch.setattr(
        runner_module,
        'visit',
        lambda *a, **k: SimpleNamespace(full=frozenset(), repair_failed=False, contract=short),
    )
    assert runner._shared_town_visit(play.run(), Exit.PORTAL) == short
    runner.close()


def test_shared_town_visit_accepts_explicitly_deferred_cube_keeper(monkeypatch):
    from inventory_tracking.macros.town import Contract

    play = Game(world(103, player=player(103)))
    runner = make(lambda _cancelled, _routine: None, [])
    runner.loop.own = frozenset()
    done = Contract(1, True, 1, 0, 12, 'from the Sling', 0, deferred=('set Boots',))
    monkeypatch.setattr(
        runner_module,
        'visit',
        lambda *a, **k: SimpleNamespace(
            full=frozenset(),
            repair_failed=False,
            contract=done,
        ),
    )
    assert runner._shared_town_visit(play.run(), Exit.PORTAL) == done


def test_any_stop_with_the_character_dead_stops_the_loop_and_leaves_no_game():
    # The player, 2026-10-19: "if we died - we MUST not take ANY other actions, no reviving, no save/exits, nothing at
    # all": a watchdog's stop or a leg's with the character dead is no recovery (whose next leg is Save and Exit)
    runner = andariel_room_runner(carrying=True)
    runner._dead = lambda: True
    runner._loop_stopped(Abort('the character has not moved for 45 s', cause='stall'))
    assert not runner.loop.on
    assert not runner.loop.abandon
    assert not runner.loop.trip_due
    runner.close()
    runner = andariel_room_runner(carrying=True)
    runner._dead = lambda: False
    runner._loop_stopped(Abort('the character has not moved for 45 s', cause='stall'))
    assert runner.loop.on  # alive: the room rules as before
    runner.close()


def beset_runner(lives, *, attack_mode=False, left=None):
    """A runner whose polls read the character standing at the Frozen River door (area 113) with `lives`, the loop on
    and outside a fight unless `attack_mode` (rca/2026-10-19/near-death-findings.md)."""
    looks = iter(lives)
    shown: list = []
    runner = MacroRunner(
        None, capture_lock=threading.Lock(), saved_games=SAVED_GAMES, display=shown.append, place=lambda: place()
    )

    def place():
        runner.where, runner.life_seen = (10212.5, 5359.5), (next(looks), 3134)
        return 'cyber13', 113

    runner.valuable_left = lambda: left
    runner.loop.on, runner.attack_mode = True, attack_mode
    return runner, shown


def test_a_character_hit_standing_outside_a_fight_leaves_the_game_at_once(caplog):
    # The player, 2026-10-19: "we stood still while under attack and almost died, only user intervented and helped to
    # kill attackers ... we must not die or we lose exp and our gear"
    runner, shown = beset_runner([3119, 3119, 2986, 2789])
    with caplog.at_level('INFO'):
        for now in (10.0, 11.0, 12.0, 13.0):
            runner.poll(now)
    assert runner.loop.abandon  # the next leg is Save and Exit
    assert runner.loop.on
    assert 'the character is hit standing outside a fight (life 2789/3134): the game is left at once' in caplog.text
    assert shown[-1] == ['Loop: the character is hit standing outside a fight (life 2789/3134): leaving the game']
    runner.close()


def test_hit_standing_the_game_is_left_even_with_a_valuable_on_the_ground():
    runner, _ = beset_runner([3119, 2789], left='Flawless Topaz')
    for now in (10.0, 11.0):
        runner.poll(now)
    assert runner.loop.abandon
    assert not runner.loop.make_room
    assert runner.loop.fetch_again is None
    runner.close()


def test_a_fights_losses_are_not_a_stand_under_attack():
    runner, _ = beset_runner([3119, 2789, 2500], attack_mode=True)
    for now in (10.0, 11.0):
        runner.poll(now)
    runner.attack_mode = False  # the fight over, the character where it fought
    runner.poll(12.0)
    assert not runner.loop.abandon
    runner.close()
