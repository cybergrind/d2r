import logging

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
