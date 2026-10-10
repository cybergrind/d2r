import threading
import time

from inventory_tracking.macros import runner as runner_module
from inventory_tracking.macros.actuator import Abort, Cancelled
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.runner import MacroRunner


def make(execute, shown):
    return MacroRunner(None, capture_lock=threading.Lock(), saved_games=None, display=shown.append, execute=execute)


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
    runner.thread.join(5)
    assert not runner.thread.is_alive()
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
    runner.thread.join(5)
    runner.request(20.0, 20.1, 'teleport')
    runner.thread.join(5)
    assert calls == ['prebuff', 'teleport']
    assert shown[0] == ['Macro failed: boom']


def test_the_levels_noted_between_presses_are_what_a_run_is_told():
    places = iter([('cyber32', 102), ('cyber32', 102), ('cyber32', 103)])
    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=None, place=lambda: next(places))
    runner.poll(10.0)
    runner.poll(10.2)  # too soon: not read
    runner.poll(11.5)
    runner.poll(13.0)
    assert runner.journey.arrival(20.0) == (102, 7.0)


def test_a_level_that_cannot_be_read_does_not_stop_the_service():
    def place():
        raise OSError('gone')

    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=None, place=place)
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
    runner.thread.join(5)
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
    runner.thread.join(5)
    assert steps == ['teleport', 'teleport']


def test_a_macro_request_during_a_teleport_step_cancels_it():
    def execute(cancelled, routine):
        assert cancelled.wait(5)
        raise Cancelled

    runner = make(execute, [])
    runner.request(10.0, 10.1, 'teleport')
    assert runner.request(10.5, 10.6, 'prebuff')
    runner.thread.join(5)
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
    runner.thread.join(5)

    def cancelled_step(cancelled, routine):
        assert cancelled.wait(5)
        raise Cancelled

    runner = make(cancelled_step, [])
    assert runner.request(20.0, 20.1, 'hunt elites')
    step = runner.thread
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
    runner.thread.join(5)
    assert not runner.attack_mode
    assert not runner.working
    assert ['Macro: Attack mode off'] in shown
    assert runner.request(11.0, 11.1, 'hunt any')  # and on again
    assert runner.attack_mode
    runner.request(11.5, 11.6, 'hunt any')
    runner.thread.join(5)


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
    runner.thread.join(5)
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
    runner.thread.join(5)


def test_a_pickup_request_during_attack_mode_waits_for_the_fight_and_the_mode_resumes_after(monkeypatch):
    # user, 2026-10-10: the pickup is queued behind the killing, not put before it.
    from inventory_tracking.macros.hunt import Hunter

    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    runs, resumed, fight_over = [], threading.Event(), threading.Event()
    hunter = Hunter()

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
    runner.thread.join(5)


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
    runner.thread.join(5)
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
    runner.hunter = Hunter()
    assert runner.request(10.0, 10.1, 'hunt any')
    assert started.wait(5)
    assert runner.request(10.3, 10.4, 'pickup')
    runner.close()
    runner.thread.join(5)
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
    runner.thread.join(5)
    assert runs == ['hunt any', 'prebuff']
    assert not runner.attack_mode


def test_attack_mode_returning_on_its_own_turns_the_toggle_off(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    shown = []
    runner = make(lambda cancelled, routine: None, shown)
    assert runner.request(10.0, 10.1, 'hunt any')
    runner.thread.join(5)
    assert not runner.attack_mode
    assert runner.request(10.5, 10.6, 'hunt any')  # the next press starts the mode again, not "off"
    runner.thread.join(5)
    assert runner.generation == 2
    assert ['Macro: Attack mode off'] not in shown


def test_attack_mode_ending_on_its_own_turns_the_toggle_off(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    shown = []
    runner = make(lambda cancelled, routine: (_ for _ in ()).throw(Abort('attack mode off: the game was left')), shown)
    assert runner.request(10.0, 10.1, 'hunt any')
    runner.thread.join(5)
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
    runner.hunter = Hunter()
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
