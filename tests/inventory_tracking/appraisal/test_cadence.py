"""The service loop's cadence table (appraisal/cadence.py; rca/2026-10-13/latency-findings.md, fix 1)."""

import sys

import pytest

from inventory_tracking.appraisal import loop_timing, service
from inventory_tracking.appraisal.cadence import Mode, Schedule, cadences, mode_of
from inventory_tracking.appraisal.loop_timing import PassTimer
from inventory_tracking.config import APPRAISAL


TOWN_AREA, CHAOS = 103, 108


def table():
    return cadences(shop=1.0, identify=1.0, stash=0.5, runes=0.5, terror=0.25)


class Watcher:
    poll_interval = 99.0


def test_the_mode_is_working_while_the_macro_works_out_of_town_and_else_town_or_level_by_the_area():
    # Attack mode stays on through a town visit (it naps there): the stash, the vendors and Cain keep their pace.
    assert mode_of(True, TOWN_AREA) is Mode.TOWN
    assert mode_of(True, CHAOS) is Mode.WORKING
    assert mode_of(True, None) is Mode.WORKING  # the level not read yet with a run acting
    assert mode_of(False, TOWN_AREA) is Mode.TOWN
    assert mode_of(False, None) is Mode.TOWN  # the menu, or not read yet
    assert mode_of(False, CHAOS) is Mode.LEVEL


def test_town_keeps_every_configured_interval():
    state = {'working': False, 'area': TOWN_AREA}
    schedule = Schedule(table(), working=lambda: state['working'], area=lambda: state['area'])
    assert schedule.update() is Mode.TOWN
    paced = {}
    for step, configured in (('shop', 1.0), ('identify', 1.0), ('stash', 0.5), ('runes', 0.5), ('terror probe', 0.25)):
        watcher = Watcher()
        assert schedule.paced(step, watcher)
        paced[step] = watcher.poll_interval
        assert watcher.poll_interval == configured
    assert schedule.seconds('level map') == 0.0  # the level map's walls every poll


def test_a_level_drops_the_stash_and_slows_the_ground_and_monster_reads():
    state = {'working': False, 'area': CHAOS}
    schedule = Schedule(table(), working=lambda: state['working'], area=lambda: state['area'])
    assert schedule.update() is Mode.LEVEL
    assert not schedule.paced('stash', Watcher())
    assert schedule.seconds('runes') == 1.0
    assert schedule.seconds('terror probe') == 0.5
    assert schedule.seconds('level map') == 0.0
    assert schedule.seconds('shop') == 1.0  # the shop worker backs off by itself outside town


def test_while_the_macro_works_only_what_it_needs_is_read_and_seldom():
    state = {'working': True, 'area': CHAOS}
    schedule = Schedule(table(), working=lambda: state['working'], area=lambda: state['area'])
    assert schedule.update() is Mode.WORKING
    for step in ('shop', 'identify', 'stash'):
        watcher = Watcher()
        assert not schedule.paced(step, watcher)
        assert watcher.poll_interval == 99.0  # untouched
    assert schedule.seconds('level map') == 2.0
    assert schedule.seconds('runes') == 2.0
    assert schedule.seconds('terror probe') == 1.0
    state['working'] = False  # the run ended: the level's pace again at the next pass
    assert schedule.update() is Mode.LEVEL
    assert schedule.seconds('level map') == 0.0


def test_a_configured_interval_slower_than_the_table_is_kept():
    slow = cadences(shop=1.0, identify=1.0, stash=0.5, runes=3.0, terror=2.0)
    assert slow['runes'].working == 3.0
    assert slow['runes'].level == 3.0
    assert slow['terror probe'].working == 2.0


def test_the_table_is_said_in_one_line():
    schedule = Schedule(table(), working=lambda: False, area=lambda: None)
    said = schedule.describe()
    assert 'stash 0.5 s / off / off' in said
    assert 'level map each poll / each poll / 2 s' in said


def test_the_pass_timer_tells_its_sink_every_pass(monkeypatch):
    monkeypatch.setattr(loop_timing, 'STEP_CPU', False)  # the sink as before STEP_CPU (on 2026-10-24)
    now, told = [0.0], []
    timer = PassTimer(0.5, clock=lambda: now[0], passed=lambda steps, total: told.append((dict(steps), total)))
    with timer.step('level map'):
        now[0] += 0.1
    timer.finish()
    timer.finish()
    assert told == [({'level map': 0.1}, 0.1), ({}, 0)]


def test_the_service_sets_the_switch_interval_before_anything_else(monkeypatch):
    class Started(Exception):
        pass

    def stop():
        raise Started

    monkeypatch.setattr(service, 'controller_settings', stop)
    before = sys.getswitchinterval()
    try:
        sys.setswitchinterval(0.005)
        with pytest.raises(Started):
            service.run_service(object(), None, {})
        assert sys.getswitchinterval() == pytest.approx(APPRAISAL.switch_interval)
    finally:
        sys.setswitchinterval(before)
    assert APPRAISAL.switch_interval == 0.0005
