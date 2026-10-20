"""KP_6 presses with the kind picker (runner.py `_judge_loop_taps`, macros/kindpick.py; the player, 2026-10-20: "pop
some kind of dialogue to chose the mode on 3 clicks"): three open it, one moves, two choose, three close, a wait
closes; the loop's on/off is never touched; with no HUD three presses cycle as before."""

import threading
import time
from pathlib import Path

import pytest

from inventory_tracking.macros import kindpick
from inventory_tracking.macros.kindpick import entries
from inventory_tracking.macros.loop import ANDARIEL, LK, coming_kinds
from inventory_tracking.macros.pickmode import MOST, SURE
from inventory_tracking.macros.runner import MacroRunner
from tests.inventory_tracking.macros.fakes import patch_runner


def make(shown, published, *, hud=True):
    runner = MacroRunner(
        None,
        capture_lock=threading.Lock(),
        saved_games=Path('/nonexistent/Saved Games'),
        display=shown.append,
        execute=lambda cancelled, routine: pytest.fail(f'no run starts: {routine}'),
    )
    runner.valuable_left = lambda: None
    runner.picker_publish = published.append
    runner.hud_up = lambda: hud
    return runner


def press(runner, *ats):
    for at in ats:
        assert runner.request(at, at, 'loop')


def until(condition, seconds=3.0):
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert condition()


def names(published):
    """The rows of the last picker card published, highlighted ones marked `>`."""
    (widget,) = published[-1]
    return [('>' if row['highlighted'] else '') + row['name'] for row in widget.payload['rows']]


def logged(caplog):
    return [record.getMessage() for record in caplog.records]


@pytest.fixture
def fast(monkeypatch):
    patch_runner(monkeypatch, 'PICKER_TICK', 0.05)


def test_three_presses_open_it_one_moves_two_choose_and_the_loop_stays_off(caplog, fast):
    shown, published = [], []
    runner = make(shown, published)
    order = [row.kind for row in entries() if row.kind is not None]
    after = order[(order.index(ANDARIEL) + 1) % len(order)]
    then = order[(order.index(ANDARIEL) + 2) % len(order)]
    with caplog.at_level('INFO'):
        press(runner, 10.0, 10.1, 10.2)
        until(lambda: runner.picker is not None)
        assert runner.loop.kind == ANDARIEL  # nothing switched by opening it
        until(lambda: bool(published))
        assert f'>{after.name}' in names(published)
        assert 'Shard: Act 4' in names(published)  # the act loop, offered
        coming = [kind.name for kind in coming_kinds()]  # the act kinds whose scripts are not ready, shown last
        assert names(published)[len(names(published)) - len(coming) :] == coming

        press(runner, 20.0)  # one: the highlight moves
        until(lambda: runner.picker is not None and runner.picker.highlighted.kind == then)
        assert not runner.loop.on  # a single press in the picker is no toggle

        press(runner, 30.0, 30.1)  # two: chosen
        until(lambda: runner.picker is None)
    assert runner.loop.kind == then
    assert runner.loop.chosen
    assert not runner.loop.on
    assert published[-1] == []  # the card taken down
    assert [f'Macro: Loop run: {then.name}'] in shown  # tools/logwords.py KIND
    assert f'Macro: loop kind: {then.name} (picked)' in logged(caplog)
    assert runner.resume_state()['loop_kind'] == then.key
    runner.close()


def test_no_press_for_pick_seconds_closes_it_with_nothing_changed(monkeypatch, caplog, fast):
    monkeypatch.setattr(kindpick, 'PICK_SECONDS', 0.4)
    shown, published = [], []
    runner = make(shown, published)
    with caplog.at_level('INFO'):
        press(runner, 10.0, 10.1, 10.2)
        until(lambda: runner.picker is not None)
        until(lambda: runner.picker is None)
    assert runner.loop.kind == ANDARIEL
    assert not runner.loop.chosen
    assert published[-1] == []
    assert sum(1 for widgets in published if widgets) >= 3  # republished inside the HUD's lease while open
    assert 'Macro: loop kind picker closed: no press, nothing changed' in logged(caplog)
    runner.close()


def test_three_presses_in_the_picker_close_it_and_the_loop_on_stays_on(fast):
    shown, published = [], []
    runner = make(shown, published)
    runner.loop.on = True  # the loop running: opening, moving and closing the picker leave it on
    press(runner, 10.0, 10.1, 10.2)
    until(lambda: runner.picker is not None)
    picker = runner.picker
    assert picker is not None
    first = picker.highlight
    press(runner, 20.0)
    until(lambda: runner.picker is not None and runner.picker.highlight != first)
    assert runner.loop.on
    press(runner, 30.0, 30.1, 30.2)
    until(lambda: runner.picker is None)
    assert runner.loop.on
    assert runner.loop.kind == ANDARIEL
    assert published[-1] == []
    runner.loop.on = False
    runner.close()


def test_a_fourth_press_in_the_picker_changes_nothing_and_keeps_it_open(caplog, fast):
    shown, published = [], []
    runner = make(shown, published)
    with caplog.at_level('INFO'):
        press(runner, 10.0, 10.1, 10.2)
        until(lambda: runner.picker is not None)
        picker = runner.picker
        assert picker is not None
        highlighted = picker.highlighted
        press(runner, 20.0, 20.1, 20.2, 20.3)
        until(lambda: any('pressed 4 times together, nothing changed' in line for line in logged(caplog)))
    assert runner.picker is not None
    assert runner.picker.highlighted == highlighted
    assert runner.loop.kind == ANDARIEL
    runner.close()
    assert runner.picker is None  # the service's close takes it down
    assert published[-1] == []


def test_with_the_picker_closed_two_presses_still_switch_the_pickup_level_and_four_nothing(fast):
    shown, published = [], []
    runner = make(shown, published)
    press(runner, 10.0, 10.2)
    until(lambda: runner.pickup_mode == MOST)
    assert runner.picker is None
    press(runner, 20.0, 20.1, 20.2, 20.3)
    until(lambda: ['Macro: KP_6 pressed 4 times together: nothing switched'] in shown)
    assert runner.picker is None
    assert published == []
    assert runner.pickup_mode == MOST
    assert runner.pickup_mode != SURE
    runner.close()


def test_with_no_hud_three_presses_cycle_the_kind_as_before_and_say_so(caplog, fast):
    shown, published = [], []
    runner = make(shown, published, hud=False)
    with caplog.at_level('INFO'):
        press(runner, 10.0, 10.1, 10.2)
        until(lambda: runner.loop.kind != ANDARIEL)
    assert runner.picker is None
    assert published == []
    name = runner.loop.kind.name
    assert f'Macro: loop kind: {name} (cycled: no HUD for the picker)' in logged(caplog)
    assert [f'Macro: Loop run: {name}'] in shown
    runner.close()


def test_a_kind_request_closes_the_picker_and_takes(fast):
    shown, published = [], []
    runner = make(shown, published)
    press(runner, 10.0, 10.1, 10.2)
    until(lambda: runner.picker is not None)
    now = time.monotonic()
    assert runner.choose_kind(now, now, 'lk')
    assert runner.picker is None
    assert runner.loop.kind == LK
    assert published[-1] == []
    runner.close()
