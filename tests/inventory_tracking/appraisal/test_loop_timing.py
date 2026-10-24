import logging

import pytest

from inventory_tracking.appraisal.loop_timing import PassTimer


def test_slow_pass_names_its_slowest_steps(caplog):
    now = [0.0]
    timer = PassTimer(0.5, clock=lambda: now[0])
    with timer.step('level map'):
        now[0] += 0.1
    assert timer.finish() == 0.1
    with timer.step('appraisal'):
        now[0] += 0.4
    with timer.step('level map'):
        now[0] += 0.3
    with caplog.at_level(logging.WARNING):
        timer.finish()
    assert 'Slow service pass: 700 ms (appraisal 400, level map 300)' in caplog.text


def test_with_step_cpu_each_step_also_says_the_main_threads_cpu(monkeypatch):
    from inventory_tracking.appraisal import loop_timing

    monkeypatch.setattr(loop_timing, 'STEP_CPU', True)
    now, cpu, told = [0.0], [0.0], []
    timer = PassTimer(
        0.5, clock=lambda: now[0], cpu_clock=lambda: cpu[0], passed=lambda steps, total, cpu: told.append((steps, cpu))
    )
    with timer.step('level map'):
        now[0] += 0.3
        cpu[0] += 0.05  # most of the step waited (the GIL, the game)
    with timer.step('runes'):
        now[0] += 0.1
        cpu[0] += 0.08
    timer.finish()
    ((steps, cpu_steps),) = told
    assert steps == pytest.approx({'level map': 0.3, 'runes': 0.1})
    assert cpu_steps == pytest.approx({'level map': 0.05, 'runes': 0.08})
    timer.finish()
    assert told[-1] == ({}, {})  # the next pass starts empty


def test_without_step_cpu_the_pass_is_told_as_before(monkeypatch):
    from inventory_tracking.appraisal import loop_timing

    monkeypatch.setattr(loop_timing, 'STEP_CPU', False)
    read, told = [], []
    timer = PassTimer(0.5, cpu_clock=lambda: read.append(1) or 0.0, passed=lambda steps, total: told.append(steps))
    with timer.step('macro'):
        pass
    timer.finish()
    assert list(told[0]) == ['macro']
    assert not read  # the CPU clock is not read
