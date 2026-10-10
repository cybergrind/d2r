import threading

from inventory_tracking.macros import runner as runner_module
from inventory_tracking.macros.actuator import Abort
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
        raise Abort('cancelled')

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


def test_win_t_during_a_teleport_step_queues_one_more_step_instead_of_cancelling(monkeypatch):
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


def test_win_x_during_a_teleport_step_cancels_it():
    def execute(cancelled, routine):
        assert cancelled.wait(5)
        raise Abort('cancelled')

    runner = make(execute, [])
    runner.request(10.0, 10.1, 'teleport')
    assert runner.request(10.5, 10.6, 'prebuff')
    runner.thread.join(5)
    assert not runner.working


def test_kp_2_during_its_own_step_queues_one_more_and_kp_4_cancels(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    steps, go_on, attacking = [], threading.Event(), threading.Event()

    def execute(cancelled, routine):
        steps.append(routine)
        if routine == 'hunt any':  # the mode KP_2 leaves on
            attacking.set()
            assert cancelled.wait(5)
            raise Abort('cancelled')
        if len(steps) == 1:
            assert go_on.wait(5)
        assert not cancelled.is_set()

    runner = make(execute, [])
    assert runner.request(10.0, 10.1, 'hunt elites')
    assert runner.request(10.2, 10.3, 'hunt elites')  # the same key: one more step
    go_on.set()
    assert attacking.wait(5)
    assert steps == ['hunt elites', 'hunt elites', 'hunt any']
    runner.request(11.0, 11.1, 'hunt any')  # KP_3: off
    runner.thread.join(5)

    def cancelled_step(cancelled, routine):
        assert cancelled.wait(5)
        raise Abort('cancelled')

    runner = make(cancelled_step, [])
    assert runner.request(20.0, 20.1, 'hunt elites')
    step = runner.thread
    assert runner.request(20.2, 20.3, 'teleport')  # another key cancels
    step.join(5)
    assert not step.is_alive()
    runner.close()


def test_kp_3_toggles_attack_mode_on_and_off(monkeypatch):
    # user, 2026-10-10 evening: KP_3 toggles (the morning's "never off" is withdrawn).
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    shown = []

    def execute(cancelled, routine):
        assert routine == 'hunt any'
        assert cancelled.wait(5)
        raise Abort('cancelled')

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


def test_kp_2_does_its_step_and_turns_attack_mode_on(monkeypatch):
    # user, 2026-10-10 evening: after KP_2 the character stood beside the monsters until KP_3 was pressed.
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    runs, attacking = [], threading.Event()

    def execute(cancelled, routine):
        runs.append(routine)
        if routine == 'hunt any':
            attacking.set()
            assert cancelled.wait(5)
            raise Abort('cancelled')
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
    runner.request(12.0, 12.1, 'hunt any')  # KP_3: off
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
            raise Abort('cancelled')

    runner = make(execute, [])
    assert runner.request(10.0, 10.1, 'hunt any')
    assert runner.request(10.3, 10.4, 'teleport')  # the mode pauses for the step
    assert resumed.wait(5)
    assert runs == ['hunt any', 'teleport', 'hunt any']
    assert runner.attack_mode
    runner.request(11.0, 11.1, 'prebuff')  # off again
    runner.thread.join(5)


def test_win_x_ends_attack_mode_and_runs_the_macro(monkeypatch):
    # user, 2026-10-10: Win+X must not only stop the mode but run the macro as it does otherwise.
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    runs, done = [], threading.Event()

    def execute(cancelled, routine):
        runs.append(routine)
        if routine == 'hunt any':
            assert cancelled.wait(5)
            raise Abort('cancelled')
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
    runner = make(lambda cancelled, routine: (_ for _ in ()).throw(Abort('attack mode off: you attacked')), shown)
    assert runner.request(10.0, 10.1, 'hunt any')
    runner.thread.join(5)
    assert not runner.attack_mode
    assert ['Macro stopped: attack mode off: you attacked'] in shown
