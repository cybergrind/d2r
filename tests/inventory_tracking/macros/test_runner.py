import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.macros import runner as runner_module
from inventory_tracking.macros.actuator import Abort, Cancelled, Flipped
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.runner import MacroRunner
from tests.inventory_tracking.macros.fakes import BUILD, KEYS, character_of


# No key file is read here: every run is given its keys, or none is played by `_execute`.
SAVED_GAMES = Path('/nonexistent/Saved Games')


def make(execute, shown):
    return MacroRunner(
        None, capture_lock=threading.Lock(), saved_games=SAVED_GAMES, display=shown.append, execute=execute
    )


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


def test_a_press_during_a_run_cancels_it(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    shown = []

    def execute(cancelled, routine):
        assert cancelled.wait(5)
        raise Cancelled

    runner = make(execute, shown)
    assert runner.request(10.0, 10.1)
    assert runner.request(11.0, 11.1)
    assert not joined(runner).is_alive()
    assert shown == [['Macro stopped: cancelled'], []]


def test_a_crash_is_shown_and_the_next_press_starts_again(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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
    from inventory_tracking.routes.progress import Progress

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


def test_a_teleport_request_during_a_teleport_step_queues_one_more_step_instead_of_cancelling(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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


def test_closing_ends_the_card_wait_of_a_run_that_ended():
    # The card of a run that ended stays CARD_SECONDS (4 s); shutdown must not wait it out.
    runner = make(lambda cancelled, routine: None, [])
    assert runner.request(10.0, 10.1, 'teleport')
    thread = runner.thread
    assert thread is not None
    started = time.monotonic()
    runner.close()  # joins the run's thread (up to 3 s)
    assert time.monotonic() - started < 1.0
    assert not thread.is_alive()


def test_a_macro_request_during_a_teleport_step_cancels_it(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)

    def execute(cancelled, routine):
        assert cancelled.wait(5)
        raise Cancelled

    runner = make(execute, [])
    runner.request(10.0, 10.1, 'teleport')
    assert runner.request(10.5, 10.6, 'prebuff')
    joined(runner)
    assert not runner.working


def test_a_seek_request_during_its_own_step_queues_one_more_and_a_teleport_request_cancels(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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


def test_the_toggle_turns_attack_mode_on_and_off(monkeypatch):
    # user, 2026-10-10 evening: the toggle turns it off too (the morning's "never off" is withdrawn).
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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


def test_a_seek_request_does_its_step_and_turns_attack_mode_on(monkeypatch):
    # user, 2026-10-10 evening: after the seek step the character stood beside the monsters until attack
    # mode was turned on by hand.
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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


def test_a_step_during_attack_mode_pauses_it_and_it_resumes_after(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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


def test_a_pickup_request_during_attack_mode_asks_for_a_step_and_is_dropped_when_the_mode_says_so(monkeypatch):
    # The press inside a fight is a step to a better stand; with nothing on the ground the mode tells
    # the runner that no pickup step (and so no seek step) is to follow the fight.
    from inventory_tracking.macros.hunt import Hunter

    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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


def test_a_teleport_or_seek_request_ends_the_sweep_and_a_pickup_request_does_not(monkeypatch):
    # Tower Cellar 3, 2026-10-11: the sweep walked the character back between two teleport steps.
    from inventory_tracking.macros.hunt import Hunter

    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    runner = make(lambda cancelled, routine: None, [])
    runner.hunter = Hunter(build=BUILD)
    for routine, left in (('pickup', 5), ('teleport', 0), ('hunt elites', 0), ('prebuff', 0)):
        runner.hunter.sweep.steps = 5
        runner.last_request = -1e9
        assert runner.request(10.0, 10.1, routine)
        joined(runner)
        assert runner.hunter.sweep.steps == left, routine


def test_a_pickup_request_during_attack_mode_waits_for_the_fight_and_the_mode_resumes_after(monkeypatch):
    # user, 2026-10-10: the pickup is queued behind the killing, not put before it.
    from inventory_tracking.macros.hunt import Hunter

    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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


def test_closing_during_a_seek_step_starts_nothing_after_it(monkeypatch):
    # review.md, finding 1: the cancelled seek step used to be followed by attack mode on a fresh,
    # unset cancellation, after the service had shut down.
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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


def test_closing_with_a_pickup_waiting_for_the_fight_drops_it(monkeypatch):
    from inventory_tracking.macros.hunt import Hunter

    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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


def test_a_macro_request_ends_attack_mode_and_runs_the_macro(monkeypatch):
    # user, 2026-10-10: the macro request must not only stop the mode but run the macro as it does otherwise.
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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


def test_attack_mode_returning_on_its_own_turns_the_toggle_off(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    shown = []
    runner = make(lambda cancelled, routine: None, shown)
    assert runner.request(10.0, 10.1, 'hunt any')
    joined(runner)
    assert not runner.attack_mode
    assert runner.request(10.5, 10.6, 'hunt any')  # the next press starts the mode again, not "off"
    joined(runner)
    assert runner.generation == 2
    assert ['Macro: Attack mode off'] not in shown


def test_attack_mode_ending_on_its_own_turns_the_toggle_off(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    shown = []
    runner = make(lambda cancelled, routine: (_ for _ in ()).throw(Abort('attack mode off: the game was left')), shown)
    assert runner.request(10.0, 10.1, 'hunt any')
    joined(runner)
    assert not runner.attack_mode
    assert ['Macro stopped: attack mode off: the game was left'] in shown


def test_requests_racing_a_runs_end_never_leave_two_runs_acting(monkeypatch):
    # review.md, finding 1: `working` went off before the successor was chosen, so a request and the
    # ending run could each start one. Steps that end at once, under a storm of requests.
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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


def test_a_request_after_close_and_a_run_ending_after_close_start_nothing(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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


def test_a_request_while_a_run_hands_over_to_its_successor_waits_for_the_handover(monkeypatch):
    # review.md, finding 1: the seek step is over and attack mode is being started after it; a teleport
    # request in that moment must find the mode (and pause it), not an idle runner to start beside it.
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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


def test_a_teleport_request_during_a_pickup_stops_it_and_the_step_follows_at_once(monkeypatch):
    # Tower Cellar 5, 22:51:00 on 2026-10-11: the press to get out waited behind a pickup that clicked
    # 5 s at a potion among eight monsters, and the character died 0.4 s after it. (The Ring of
    # 17:35:18 that day, whose pickup such a press cancelled, is the teleport step's own business
    # now: it takes a valuable near before it hops, pickup.worth_a_stop.)
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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
    from inventory_tracking.routes.model import Route, fight, leave, level, loot
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
    from inventory_tracking.routes.model import Route, enter, fight, leave, level, loot
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


def test_a_flip_under_a_step_ends_it_and_the_same_request_starts_again(monkeypatch, caplog):
    """KP_5 (the service's pad hotkey) flipped the game to controller mode under a run by the keys: the run could not
    act, and the pursuit looped 57 times in 7 s. Now the flip ends the run and the request is made again once, in
    the new mode (`play_by` chooses it at the run's start), said once."""
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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


def test_a_flip_under_attack_mode_keeps_it_on_and_starts_it_again(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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


def test_a_mode_that_keeps_flipping_stops_the_run(monkeypatch, caplog):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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


def test_the_loop_key_starts_a_leg_and_each_leg_is_followed_by_the_next_until_one_stops(monkeypatch):
    # routes/lower-kurast-loop-plan.md phase 4: KP_6 on; a leg's stop ends the loop, saying why
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    shown, made = [], []

    def execute(cancelled, routine):
        made.append(routine)
        if len(made) == 3:
            raise Abort('the character is dead')

    runner = make(execute, shown)
    assert runner.request(10.0, 10.1, 'loop')
    assert runner.loop.on
    deadline = time.monotonic() + 5
    while len(made) < 3 and time.monotonic() < deadline:
        time.sleep(0.01)
    joined(runner)
    assert made == ['loop'] * 3
    assert not runner.loop.on
    assert ['Loop stopped: the character is dead'] in shown
    runner.close()


def test_the_level_run_a_leg_asks_for_is_followed_by_the_next_leg(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    shown, made = [], []

    def execute(cancelled, routine):
        made.append(routine)
        if made == ['loop']:
            runner.attack_mode = True  # the chests' leg: the KP_1 level run follows as attack mode
        elif len(made) == 3:
            raise Abort('enough')

    runner = make(execute, shown)
    assert runner.request(10.0, 10.1, 'loop')
    deadline = time.monotonic() + 5
    while len(made) < 3 and time.monotonic() < deadline:
        time.sleep(0.01)
    joined(runner)
    assert made == ['loop', 'hunt any', 'loop']
    runner.close()


def test_the_loop_key_again_stops_the_leg_working_and_nothing_follows(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
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
