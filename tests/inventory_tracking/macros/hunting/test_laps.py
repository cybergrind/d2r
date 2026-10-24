"""The act queue's laps and the staff read once a judge (macros/hunting/laps.py, 2026-10-23)."""

from types import SimpleNamespace

import pytest

from inventory_tracking.macros.hunting import base
from inventory_tracking.macros.hunting.laps import LapBook, loot_once, staff_once


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_the_staff_is_read_once_within_the_block_and_as_before_outside(monkeypatch):
    monkeypatch.setattr(base, 'STAFF_ONCE', True)
    reads = []
    run = SimpleNamespace(teleport=lambda: reads.append(1) or len(reads))
    read = run.teleport

    with staff_once(run):
        assert [run.teleport(), run.teleport(), run.teleport()] == [1, 1, 1]
    assert run.teleport is read
    assert run.teleport() == 2


def test_with_the_switch_off_the_staff_is_read_at_each_ask(monkeypatch):
    monkeypatch.setattr(base, 'STAFF_ONCE', False)
    reads = []
    run = SimpleNamespace(teleport=lambda: reads.append(1) or len(reads))

    with staff_once(run):
        assert [run.teleport(), run.teleport()] == [1, 2]


def test_a_staff_read_that_raises_is_not_kept(monkeypatch):
    monkeypatch.setattr(base, 'STAFF_ONCE', True)
    calls = []

    def read():
        calls.append(1)
        if len(calls) == 1:
            raise OSError('short read')
        return 'staff'

    run = SimpleNamespace(teleport=read)
    with staff_once(run):
        with pytest.raises(OSError, match='short read'):
            run.teleport()
        assert run.teleport() == 'staff'
        assert run.teleport() == 'staff'
    assert len(calls) == 2


@pytest.mark.parametrize('on', [True, False])
def test_the_loot_is_read_once_a_judge_with_the_switch_on(monkeypatch, on):
    monkeypatch.setattr(base, 'LOOT_ONCE', on)
    reads = []
    run = SimpleNamespace(loot=lambda: reads.append(1) or len(reads), teleport=lambda: 'staff')
    read = run.loot

    with loot_once(run):
        found = [run.loot(), run.loot(), run.loot()]
    assert found == ([1, 1, 1] if on else [1, 2, 3])
    assert run.loot is read  # the pursue's own read after the judge is fresh
    assert run.teleport() == 'staff'  # the other readers as they were


def test_with_no_loot_reader_the_block_leaves_it_none(monkeypatch):
    monkeypatch.setattr(base, 'LOOT_ONCE', True)
    run = SimpleNamespace(loot=None)

    with loot_once(run):
        assert run.loot is None
    assert run.loot is None


def test_an_act_over_the_line_is_said_with_its_parts_and_the_reads_put_back(monkeypatch):
    monkeypatch.setattr(base, 'ACT_LAPS_OVER', 0.15)
    monkeypatch.setattr(base, 'ACT_CPU', False)  # the line without the judge's CPU (ACT_CPU on 2026-10-24)
    clock, lines = Clock(), []
    book = LapBook(clock=clock, said=lines.append)
    run = SimpleNamespace(loot=lambda: clock.__setattr__('now', clock.now + 0.008), read=None, teleport=None)
    loot = run.loot

    book.begin(None)
    book.reads(run)
    clock.now += 0.1
    run.loot()  # a read in the judge: 8 ms
    clock.now += 0.012
    book.lap('judge')
    assert book.current is not None
    book.current.priced = 0.02
    run.loot()  # pursue's read after it
    book.lap('loot')
    clock.now += 0.002
    book.lap('stale')
    clock.now += 0.01
    book.lap('make')
    book.current.by = 'Teleport'
    clock.now += 0.03

    parts = book.close(lambda since: (since + 0.012, since + 0.035))

    assert parts is not None
    assert round(1000 * parts['judge']) == 120
    assert round(1000 * parts['judge reads']) == 8
    assert round(1000 * parts['judge rest']) == 92
    assert round(1000 * parts['loot']) == 8
    assert round(1000 * parts['make']) == 12
    assert round(1000 * parts['aim']) == 23
    assert round(1000 * parts['input']) == 152
    assert run.loot is loot  # the readers put back
    assert round(1000 * parts['reads: judge loot']) == 8  # each reader apart, by phase
    assert parts['count: after loot'] == 1
    assert lines == [
        'act queue: Teleport 152 ms from the look to its first input: judge 120 (priced 20, reads 8, the rest 92), '
        'loot 8, stale 2, advance 10, make 12; aim to the press 23; reads 16 in 2'
    ]


def test_a_pursue_with_no_move_or_no_input_is_not_counted():
    clock, lines = Clock(), []
    book = LapBook(clock=clock, said=lines.append)
    book.begin(None)
    book.lap('judge')
    assert book.close(lambda since: (since, since)) is None  # no make: a Hold
    book.begin(None)
    book.lap('make')
    assert book.close(lambda since: (None, None)) is None  # nothing sent
    assert book.done == []
    assert lines == []


def test_the_parts_are_summed_up_once_a_minute(monkeypatch):
    monkeypatch.setattr(base, 'ACT_LAPS_OVER', 10.0)
    clock, lines = Clock(), []
    book = LapBook(clock=clock, said=lines.append)
    for _ in range(3):
        book.begin(None)
        clock.now += 0.05
        book.lap('judge')
        book.lap('make')
        book.close(lambda since: (since + 0.01, since + 0.02))
        clock.now += 30.0
    assert len(lines) == 1
    assert lines[0].startswith('act queue (p50/p90 ms over 3 acts): input 60/60, judge 50/50')


def test_the_minute_line_says_what_the_reads_are(monkeypatch):
    monkeypatch.setattr(base, 'ACT_LAPS_OVER', 10.0)
    clock, lines = Clock(), []
    book = LapBook(clock=clock, said=lines.append)

    def read(seconds):
        return lambda: clock.__setattr__('now', clock.now + seconds)

    run = SimpleNamespace(loot=read(0.005), teleport=read(0.002))
    for _ in range(3):
        book.begin(None)
        book.reads(run)
        run.loot()
        run.loot()
        run.teleport()
        book.lap('judge')
        book.lap('make')
        book.close(lambda since: (since + 0.01, since + 0.02))
        clock.now += 30.0
    assert lines[0].endswith('; reads per act (mean ms, count): judge loot 10.0 (2.0), judge teleport 2.0 (1.0)')


def test_with_act_cpu_the_judges_own_cpu_is_said_beside_its_wall(monkeypatch):
    # 2026-10-24 (realtime-4): a judge of 300 ms wall and 30 ms CPU waited for the GIL
    monkeypatch.setattr(base, 'ACT_LAPS_OVER', 0.15)
    monkeypatch.setattr(base, 'ACT_CPU', True)
    clock, cpu, lines = Clock(), [5.0], []
    book = LapBook(clock=clock, said=lines.append, cpu_clock=lambda: cpu[0])

    book.begin(None)
    clock.now += 0.3
    cpu[0] += 0.03
    book.lap('judge')
    book.lap('make')
    parts = book.close(lambda since: (since + 0.01, since + 0.02))

    assert parts is not None
    assert round(1000 * parts['judge cpu']) == 30
    assert 'judge 300 (cpu 30; priced 0,' in lines[0]


def test_without_act_cpu_no_cpu_clock_is_read(monkeypatch):
    monkeypatch.setattr(base, 'ACT_CPU', False)
    read: list[int] = []
    clock = Clock()
    book = LapBook(clock=clock, said=lambda text: None, cpu_clock=lambda: read.append(1) or 0.0)
    book.begin(None)
    book.lap('judge')
    book.lap('make')
    parts = book.close(lambda since: (since + 0.2, None))
    assert parts is not None
    assert 'judge cpu' not in parts
    assert not read
