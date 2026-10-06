import threading

from inventory_tracking.macros import runner as runner_module
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.runner import MacroRunner


def make(execute, shown):
    return MacroRunner(None, capture_lock=threading.Lock(), saved_games=None, display=shown.append, execute=execute)


def test_a_stale_request_starts_nothing():
    started = []
    runner = make(started.append, [])
    assert not runner.request(10.0, 12.0)
    assert runner.thread is None


def test_a_press_during_a_run_cancels_it(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    shown = []

    def execute(cancelled):
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

    def execute(cancelled):
        calls.append(1)
        raise RuntimeError('boom')

    runner = make(execute, shown)
    runner.request(10.0, 10.1)
    runner.thread.join(5)
    runner.request(20.0, 20.1)
    runner.thread.join(5)
    assert len(calls) == 2
    assert shown[0] == ['Macro failed: boom']
