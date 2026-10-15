"""The press trace: what is recorded per press, how the runner fills it, and the report."""

import json
import threading
from pathlib import Path

from inventory_tracking.appraisal import service
from inventory_tracking.macros import latency, runner as runner_module
from inventory_tracking.macros.actuator import Abort, Cancelled
from inventory_tracking.macros.latency import Trace
from inventory_tracking.macros.runner import MacroRunner


def make(execute, trace):
    # no key file is read: `execute` stands in for the run that would read one
    return MacroRunner(
        None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent'), execute=execute, trace=trace
    )


def joined(runner: MacroRunner) -> None:
    """Waits for the runner's last run (5 s at most)."""
    assert runner.thread is not None
    runner.thread.join(5)


def records(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_a_press_is_written_with_its_marks_after_the_stamp(tmp_path):
    now = [10.0]
    trace = Trace(tmp_path / latency.FILE, clock=lambda: now[0])
    press = trace.press('teleport', 10.0, 10.004, during=None, spawn_ms=31.0)
    now[0] = 10.02
    press.mark('first_move')
    now[0] = 10.05
    press.mark('first_move')  # the first time counts
    press.mark('first_key')
    trace.close(press, outcome='started')
    trace.close(press, outcome='again')  # written once
    (record,) = records(tmp_path / latency.FILE)
    assert record['routine'] == 'teleport'
    assert record['outcome'] == 'started'
    assert record['spawn_ms'] == 31.0
    assert record['ms'] == {'received': 4.0, 'first_move': 20.0, 'first_key': 50.0}
    assert 'during' not in record


def test_a_started_press_carries_its_runs_marks_and_cost(monkeypatch, tmp_path):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    trace = Trace(tmp_path / latency.FILE)

    def execute(cancelled, routine):
        assert runner.press is not None
        runner.press.mark('first_key')

    runner = make(execute, trace)
    assert runner.request(10.0, 10.01, 'teleport', spawn_ms=30.0)
    joined(runner)
    (record,) = records(tmp_path / latency.FILE)
    assert record['outcome'] == 'started'
    assert record['ended'] == 'done'
    assert record['spawn_ms'] == 30.0
    assert list(record['ms']) == ['received', 'accepted', 'thread', 'first_key', 'done']
    assert {'cpu_ms', 'switches', 'load'} <= set(record)


def test_a_press_during_its_own_step_is_traced_through_the_step_it_queued(monkeypatch, tmp_path):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    trace = Trace(tmp_path / latency.FILE)
    go, inside = threading.Event(), threading.Event()

    def execute(cancelled, routine):
        inside.set()
        assert go.wait(5)

    runner = make(execute, trace)
    runner.request(10.0, 10.0, 'teleport')
    assert inside.wait(5)
    runner.request(10.2, 10.2, 'teleport')
    go.set()
    joined(runner)
    first, second = records(tmp_path / latency.FILE)
    assert (first['outcome'], second['outcome']) == ('started', 'queued behind its own step')
    assert second['during'] == 'teleport'
    assert 'thread' in second['ms']
    assert second['ended'] == 'done'


def test_a_dropped_and_a_cancelling_press_are_recorded_too(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    trace = Trace(tmp_path / latency.FILE)

    def execute(cancelled, routine):
        assert cancelled.wait(5)
        raise Cancelled

    runner = make(execute, trace)
    assert not runner.request(10.0, 12.0, 'teleport')  # two seconds old
    assert 'dropped: 2000 ms old' in caplog.text
    runner.request(20.0, 20.0)
    runner.request(21.0, 21.0, 'teleport')
    joined(runner)
    dropped, cancelling, cancelled = records(tmp_path / latency.FILE)
    assert dropped['outcome'] == 'dropped: too old'
    assert cancelling['outcome'] == 'cancelled prebuff'
    assert cancelling['during'] == 'prebuff'
    assert cancelled['ended'] == 'cancelled'


def test_a_run_that_stops_says_why(monkeypatch, tmp_path):
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    trace = Trace(tmp_path / latency.FILE)

    def execute(cancelled, routine):
        raise Abort('not in a game')

    runner = make(execute, trace)
    runner.request(10.0, 10.0, 'teleport')
    joined(runner)
    assert records(tmp_path / latency.FILE)[0]['ended'] == 'stopped: not in a game'


def test_the_datagram_carries_the_scripts_start_and_the_pass_under_way():
    asked = []

    class Macro:
        def request(self, *args, **notes):
            asked.append((args, notes))
            return True

    assert service.dispatch(b'teleport 10.0 31.5 12.2', 10.1, None, None, macro=Macro(), notes={'pass': 'level map'})
    assert service.dispatch(b'macro 10.0', 10.1, None, None, macro=Macro())
    assert asked == [
        ((10.0, 10.1, 'teleport'), {'pass': 'level map', 'spawn_ms': 31.5, 'spawn_cpu_ms': 12.2}),
        ((10.0, 10.1), {}),
    ]
    assert service.for_macro(b'hunt any 1.0')
    assert not service.for_macro(b'12.5')
    assert not service.for_macro(b'level 1')


def test_the_report_names_each_stage_and_holds_the_budget_against_idle_presses():
    def press(first, during=None):
        ms = {'received': 2.0, 'accepted': 2.5, 'thread': 3.0, 'locked': 3.5, 'ready': 20.0, 'first_move': first}
        return {
            'routine': 'teleport',
            'outcome': 'started',
            'spawn_ms': 30.0,
            'ms': ms,
            **({'during': during} if during else {}),
        }

    text = latency.report(
        [
            press(60.0),
            press(70.0),
            press(400.0, 'teleport'),
            {'routine': 'teleport', 'outcome': 'dropped: too old', 'ms': {}},
        ]
    )
    assert '4 presses' in text
    assert 'dropped' in text
    assert 'teleport, pressed while nothing ran' in text
    assert 'teleport, pressed while teleport ran' in text
    assert 'run setup' in text
    assert 'script start' in text
    assert 'budget p50 80 ms: 70 ms, kept' in text
    assert latency.stages(press(60.0))['run setup'] == 16.5
    assert json.loads(text.splitlines()[-3].strip())['ms']['first_move'] == 400.0


def test_a_press_that_is_over_is_told_to_whoever_notes_it_with_its_outcome():
    told = []
    trace = Trace()
    trace.noted = lambda kind, **fields: told.append((kind, fields['routine'], fields.get('outcome')))
    press = trace.press('teleport', 10.0, 10.0)
    trace.close(press, outcome='dropped: too old')
    trace.close(press, outcome='again')  # written once

    assert told == [('press', 'teleport', 'dropped: too old')]
