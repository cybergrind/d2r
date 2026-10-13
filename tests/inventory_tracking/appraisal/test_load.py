"""The service's load, once a second into the combat take (appraisal/load.py; rca/2026-10-13/latency-findings.md)."""

import threading

from inventory_tracking.appraisal.load import LoadMeter, main, summary
from inventory_tracking.combat.record import Recorder, Sample
from inventory_tracking.combat.takes import Take
from inventory_tracking.macros.world import World
from tests.inventory_tracking.macros.fakes import player


class Counters:
    """A fake process: CPU seconds of the process and of the main thread, load average, context switches."""

    def __init__(self):
        self.cpu, self.thread, self.load, self.switches = 0.0, 0.0, 4.0, 0


def meter(counters, noted, **extra):
    return LoadMeter(
        lambda kind, **fields: noted.append((kind, fields)),
        cpu=lambda: counters.cpu,
        thread_cpu=lambda: counters.thread,
        loadavg=lambda: (counters.load, 0.0, 0.0),
        switches=lambda: counters.switches,
        **extra,
    )


def test_a_window_says_cpu_load_switches_passes_by_step_and_the_macros_looks():
    counters, noted = Counters(), []
    load = meter(counters, noted)
    assert load.poll(10.0, 'working', True) is None  # the first poll opens the window
    load.passed({'level map': 0.02, 'runes': 0.005}, 0.025)
    load.passed({'level map': 0.3, 'terror probe': 0.1}, 0.4)
    looks = [0.004, 0.006, 0.5]
    worker = threading.Thread(target=lambda: [load.looked(seconds) for seconds in looks])  # the macro's thread
    worker.start()
    worker.join()
    counters.cpu, counters.thread, counters.load, counters.switches = 0.9, 0.4, 35.5, 320
    assert load.poll(10.5, 'working', True) is None  # not a second yet
    fields = load.poll(11.0, 'working', True)

    assert noted == [('load', fields)]
    assert fields == {
        's': 1.0,
        'mode': 'working',
        'cpu': 90.0,
        'main': 40.0,
        'load': 35.5,
        'ctx': 320,
        'passes': 2,
        'pass_ms': {'level map': 320.0, 'runes': 5.0, 'terror probe': 100.0},
        'pass_max': 400.0,
        'looks': 3,
        'look_ms': [6.0, 500.0],
    }
    counters.cpu += 0.1
    second = load.poll(12.0, 'working', True)  # the next window starts empty
    assert (second['passes'], second['looks'], second['look_ms'], second['cpu']) == (0, 0, None, 10.0)


def test_in_town_with_the_macro_idle_nothing_is_noted_but_the_window_still_turns():
    counters, noted = Counters(), []
    load = meter(counters, noted)
    load.poll(0.0, 'town', False)
    load.looked(0.01)
    assert load.poll(1.0, 'town', False) is None
    assert noted == []
    fields = load.poll(2.0, 'level', True)
    assert fields['looks'] == 0  # the town window's look is not carried over


def test_the_load_events_are_in_the_take_and_the_check_reads_them(tmp_path, capsys):
    now = [0.0]
    world = World(True, (), 'cyber1', (388, None), player=player(108, mode=5))
    rec = Recorder(lambda: Sample(world), output=tmp_path, clock=lambda: now[0], stats=lambda at: {})
    counters = Counters()
    load = LoadMeter(
        rec.note,
        cpu=lambda: counters.cpu,
        thread_cpu=lambda: counters.thread,
        loadavg=lambda: (counters.load, 0.0, 0.0),
        switches=lambda: counters.switches,
    )
    rec.step(0.0)
    load.poll(0.0, 'working', True)
    for second in range(1, 4):
        now[0] = float(second)
        load.passed({'level map': 0.6 if second == 2 else 0.01}, 0.6 if second == 2 else 0.01)
        load.looked(0.004)
        load.looked(0.15 if second == 3 else 0.005)
        counters.cpu += 0.5
        load.poll(float(second), 'working', True)
        rec.step(float(second))
    rec.close('test')
    directory = next(tmp_path.iterdir())
    take = Take.load(directory)

    windows = [event for event in take.events if event['event'] == 'load']
    assert [event['t'] for event in windows] == [1.0, 2.0, 3.0]
    assert windows[0]['look_ms'] == [4.5, 5.0]
    line = summary(directory)
    assert line.startswith(f'{directory.name}: 3 s;')
    assert 'starved 2 of 3 s' in line  # a 600 ms pass, a 150 ms look
    assert 'cpu p90 50%' in line
    assert main([str(directory)]) == 0
    assert capsys.readouterr().out.strip() == line


def test_a_take_without_load_events_says_so(tmp_path):
    (tmp_path / 'events.jsonl').write_text('{"t": 0.0, "event": "said", "text": "hi"}\n')
    assert 'no load events' in summary(tmp_path)


def test_the_take_manifest_carries_the_services_switch_interval(tmp_path, monkeypatch):
    import contextlib
    import sys

    from inventory_tracking.combat import record

    class Keyboard:
        def connect(self, exclusive=False):
            return contextlib.nullcontext(None)

    monkeypatch.setattr(record, 'X11Keyboard', Keyboard)
    combat = record.CombatRecorder(None, capture_lock=threading.Lock(), output=tmp_path)
    try:
        assert combat.recorder.manifest()['switch_interval'] == sys.getswitchinterval()
    finally:
        combat.close()
