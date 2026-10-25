"""KP_6 presses with the kind picker (runner.py `_judge_loop_taps`, macros/kindpick.py; the player, 2026-10-20: "pop
some kind of dialogue to chose the mode on 3 clicks"): three open it, one moves, two choose, three close, a wait
closes; the loop's on/off is never touched; with no HUD three presses cycle as before."""

import threading
import time
from pathlib import Path

import pytest

from inventory_tracking.macros import kindpick
from inventory_tracking.macros.actuator import Cancelled
from inventory_tracking.macros.kindpick import entries
from inventory_tracking.macros.loop import ANDARIEL, LK, RECOVERY_PAUSE, coming_kinds
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


# rca/2026-10-23/loop-no-legs.md: loop on, off, the picker open/choose/close, on (00:41:42-00:41:58 on 2026-10-23)


def legs_runner(display, made):
    """A runner whose loop legs wait for their cancel (the TZ waypoint leg the player turned off)."""

    def execute(cancelled, routine):
        made.append(routine)
        assert cancelled.wait(5)
        raise Cancelled

    runner = MacroRunner(
        None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent/Saved Games'), display=display,
        execute=execute,
    )  # fmt: skip
    runner.valuable_left = lambda: None
    runner.picker_publish = lambda widgets: None
    runner.hud_up = lambda: True
    return runner


def on_off_pick_on(runner, made):
    press(runner, 10.0)  # on: the first leg
    until(lambda: made == ['loop'])
    press(runner, 20.0)  # off: the leg cancelled, its card raises
    until(lambda: runner.thread is not None and not runner.thread.is_alive())
    press(runner, 30.0, 30.01, 30.02)  # the picker
    until(lambda: runner.picker is not None)
    press(runner, 40.0, 40.01)  # Andariel's neighbour chosen
    until(lambda: runner.picker is None)
    press(runner, 50.0)  # on again


@pytest.fixture
def quick(monkeypatch, fast):
    patch_runner(monkeypatch, 'DOUBLE', 0.05)
    patch_runner(monkeypatch, 'CARD_SECONDS', 0.0)


@pytest.mark.parametrize('error', [FileNotFoundError, RuntimeError])
def test_a_card_that_raises_at_the_legs_stop_still_hands_over_and_the_next_on_makes_a_leg(error, caplog, quick):
    # The 00:41:44 race made the "Macro stopped: cancelled" card raise FileNotFoundError (two writers of the layer's
    # one temporary file); any raise at a run's end must still hand the runner over
    made: list[str] = []

    def display(lines):
        if lines == ['Macro stopped: cancelled']:
            raise error('macro.tmp -> macro.json')

    runner = legs_runner(display, made)
    with caplog.at_level('INFO'):
        on_off_pick_on(runner, made)
        until(lambda: made == ['loop', 'loop'])  # the KP_6 on made a leg
    assert runner.loop.on
    assert runner.working
    assert runner.routine == 'loop'
    press(runner, 60.0)
    until(lambda: not runner.loop.on and not runner.working)
    runner.close()


def test_with_the_switch_off_the_legs_stop_that_raises_leaves_the_loop_on_without_legs(monkeypatch, quick):
    # The defect as played: `working` stays on with no thread, every on says "Loop on" and nothing runs
    patch_runner(monkeypatch, 'HANDOVER', False)
    monkeypatch.setattr(threading, 'excepthook', lambda args: None)  # the dead thread's traceback (serve's stderr)
    made: list[str] = []

    def display(lines):
        if lines == ['Macro stopped: cancelled']:
            raise FileNotFoundError('macro.tmp -> macro.json')

    runner = legs_runner(display, made)
    on_off_pick_on(runner, made)
    until(lambda: runner.loop.on)
    time.sleep(0.3)
    assert made == ['loop']  # no leg
    assert runner.working
    assert runner.routine == 'loop'
    assert runner.thread is not None
    assert not runner.thread.is_alive()
    runner.loop.on = False
    runner.close()


def test_a_kp6_on_finding_working_with_its_thread_gone_says_so_and_makes_the_leg(caplog, quick):
    made: list[str] = []
    runner = legs_runner(lambda lines: None, made)
    dead = threading.Thread(target=lambda: None)
    dead.start()
    dead.join()
    runner.thread, runner.working, runner.routine = dead, True, 'loop'  # a run that died without handing over
    with caplog.at_level('INFO'):
        press(runner, 10.0)
        until(lambda: made == ['loop'])
    assert 'Macro: the loop run ended without handing over (its thread gone): the runner is free' in logged(caplog)
    press(runner, 20.0)
    until(lambda: not runner.working)
    runner.close()


def test_a_kp6_on_during_a_run_says_which_run_its_first_leg_follows(caplog, quick):
    made: list[str] = []
    runner = legs_runner(lambda lines: None, made)
    runner.working, runner.routine = True, 'pickup'  # a step of the player's (no thread of this runner's)
    with caplog.at_level('INFO'):
        runner._toggle_loop()
    assert 'Macro: loop on: its first leg follows the pickup run working now' in logged(caplog)
    runner.loop.on = runner.working = False
    runner.close()


def test_the_card_is_written_by_one_thread_at_a_time(tmp_path):
    # The HUD layer's writer (hud/scene.py `publish_layer`) shares one temporary file: two at once raise
    from inventory_tracking.hud.scene import publish_layer

    errors: list[OSError] = []
    runner = MacroRunner(
        None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent/Saved Games'),
        display=lambda lines: publish_layer(tmp_path, 'macro', []), execute=lambda cancelled, routine: None,
    )  # fmt: skip

    def write():
        for _ in range(300):
            try:
                runner._show(['Macro: Loop off'])
            except OSError as error:
                errors.append(error)

    writers = [threading.Thread(target=write) for _ in range(3)]
    for writer in writers:
        writer.start()
    for writer in writers:
        writer.join()
    assert errors == []
    runner.close()


# KIND_ENDS_ZONE_WAIT (2026-10-25 ~12:10, the player: "why andariel loop is not working?"): Andariel picked after the
# Moo Moo Farm turn still waited "1292 s before the next leg (the next terror zone)"


def test_another_kind_picked_ends_the_zone_wait_to_the_recoveries_pause(fast):
    runner = make([], [])
    runner.loop.cooling = time.monotonic() + 1500.0  # tzloop.py `zone_wait`: the next terror zone
    now = time.monotonic()
    assert runner.choose_kind(now, now, 'lk')
    assert runner.loop.kind == LK
    assert runner.loop.cooling <= time.monotonic() + RECOVERY_PAUSE
    runner.close()


def test_the_same_kind_picked_keeps_the_zone_wait(fast):
    runner = make([], [])
    kind = runner.loop.kind
    runner.loop.cooling = until_at = time.monotonic() + 1500.0
    runner._switch_kind(kind, 'picked')
    assert runner.loop.cooling == until_at
    runner.close()


def test_with_the_switch_off_another_kind_keeps_the_zone_wait(fast, monkeypatch):
    patch_runner(monkeypatch, 'KIND_ENDS_ZONE_WAIT', False)
    runner = make([], [])
    runner.loop.cooling = until_at = time.monotonic() + 1500.0
    now = time.monotonic()
    assert runner.choose_kind(now, now, 'lk')
    assert runner.loop.cooling == until_at
    runner.close()
