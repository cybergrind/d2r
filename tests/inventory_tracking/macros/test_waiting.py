"""What waits for the run working now: taken by priority, dropped when it has waited too long."""

import threading
import time
from pathlib import Path

import pytest

from inventory_tracking.macros import runner as runner_module
from inventory_tracking.macros.actuator import Abort, Cancelled
from inventory_tracking.macros.latency import Trace
from inventory_tracking.macros.runner import EXPIRES, PRIORITY, MacroRunner
from inventory_tracking.macros.waiting import Waiting


def test_the_first_to_go_is_the_one_of_highest_priority_not_the_one_asked_first():
    now = [100.0]
    queue = Waiting(PRIORITY, Trace(), clock=lambda: now[0])
    queue.put('pickup')
    queue.put('hunt elites', 101.5)
    queue.put('teleport', 101.0)
    assert queue.first() == 'teleport'
    assert queue.take('teleport') == (101.0, None)
    assert queue.first() == 'hunt elites'


def test_what_waited_too_long_is_dropped_and_said(caplog):
    # user, 2026-10-12: "teleporting after 2 seconds is way too late and better not to perform"
    now = [100.0]
    trace = Trace(clock=lambda: now[0])
    queue = Waiting(PRIORITY, trace, clock=lambda: now[0])
    press = trace.press('teleport', 100.0, 100.0)
    queue.put('teleport', 101.0, press)
    queue.put('pickup')  # waits for a fight: no limit
    now[0] = 101.3
    assert queue.first() == 'pickup'
    assert 'teleport dropped: it waited 300 ms too long' in caplog.text
    assert press.closed
    assert press.notes['ended'] == 'expired'


def test_a_second_press_of_a_routine_takes_the_place_of_the_first():
    trace = Trace()
    queue = Waiting(PRIORITY, trace)
    first, second = trace.press('teleport', 1.0, 1.0), trace.press('teleport', 1.2, 1.2)
    queue.put('teleport', press=first)
    queue.put('teleport', press=second)
    assert first.notes['ended'] == 'another press took its place'
    assert queue.take('teleport')[1] is second


def make(execute):
    return MacroRunner(None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent'), execute=execute)


def test_a_teleport_step_that_waited_past_its_limit_behind_a_step_is_not_made(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    monkeypatch.setitem(runner_module.EXPIRES, 'teleport', 0.05)
    runs, go, inside = [], threading.Event(), threading.Event()

    def execute(cancelled, routine):
        runs.append(routine)
        inside.set()
        assert go.wait(5)

    runner = make(execute)
    assert runner.request(10.0, 10.0, 'teleport')
    assert inside.wait(5)
    assert runner.request(10.2, 10.2, 'teleport')  # queued behind the step, which takes long
    time.sleep(0.15)
    go.set()
    assert runner.thread is not None
    runner.thread.join(5)
    assert runs == ['teleport']
    assert runner.trace.closed[-1].notes['ended'] == 'expired'


def test_a_teleport_key_pressed_after_a_seek_key_during_attack_mode_goes_first_and_the_seek_step_after(monkeypatch):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    runs, both, done = [], threading.Event(), threading.Event()

    def execute(cancelled, routine):
        runs.append(routine)
        if routine == 'hunt any':
            if len(runs) == 1:
                assert both.wait(5)  # the mode is slow to stop: both keys come meanwhile
            else:
                done.set()
                assert cancelled.wait(5)
            raise Cancelled

    runner = make(execute)
    assert runner.request(10.0, 10.0, 'hunt any')
    assert runner.request(10.1, 10.1, 'hunt elites')
    assert runner.request(10.2, 10.2, 'teleport')
    both.set()
    assert done.wait(5)
    assert runs == ['hunt any', 'teleport', 'hunt elites', 'hunt any']
    runner.close()


def test_a_pickup_that_waits_is_given_up_when_the_player_moves_on(monkeypatch):
    # As the sweep: a teleport step is not followed by a walk back for what lay there.
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    go = threading.Event()

    def execute(cancelled, routine):
        assert go.wait(5)

    runner = make(execute)
    runner.request(10.0, 10.0, 'teleport')
    runner._pick()
    assert runner.pending == 'pickup'
    runner.request(10.1, 10.1, 'teleport')
    assert runner.pending == 'teleport'
    assert 'pickup' not in runner.queue.entries
    go.set()
    runner.close()


def test_a_hop_is_not_made_long_after_its_key():
    # The step began in time and then waited (for a cast to end, for the level card): the key is not pressed.
    from inventory_tracking.macros.teleport import step_toward
    from tests.inventory_tracking.macros.test_teleport import game, keys, target

    play = game()
    run = play.run()
    run.deadline = run.clock() - 0.3
    with pytest.raises(Abort, match='dropped: 300 ms too long after its key'):
        step_toward(run, target((1003.0, 1000.0)), keys)
    assert play.pressed() == []


def test_every_routine_a_key_asks_for_has_a_place_in_the_order():
    assert set(EXPIRES) <= set(PRIORITY)
    assert PRIORITY[0] == 'teleport'
