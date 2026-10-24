"""The arena's watchdog (driver.py STALL_WALL, SLOW_RATIO; 2026-10-22, the player: "maybe you could use more targetted
approach with tight timeouts?"): game time must advance. A run whose game clock stands still is called hung in
seconds with every thread's stack, not after WALL_LIMIT's two minutes.

The 2026-10-22 hangs: fane-death-24, seeds 5, 8, 4 and 12 through the TZ run's pursuit, ran past 120 s of wall time.
Two loops on one clock: every Battle Orders ask between looks appended a stat 25 read (macros/safety.py RAISE_KEEP,
`kept_percent`), and the strike bout yielded at once to a look that chose the bout again (BOUT_REACH,
BOUT_REACH_EVERY)."""

import threading
import time
from types import SimpleNamespace
from typing import Any

import pytest

from tests.inventory_tracking.scenarios.arena import driver
from tests.inventory_tracking.scenarios.arena.situations import fane_death as fd
from tests.inventory_tracking.scenarios.arena.situations.situation import once


def test_a_run_whose_game_clock_stands_still_is_called_hung_in_seconds(tmp_path, monkeypatch) -> None:
    """`Driver.settle` with a run's thread spinning and the arena's clock still: an error naming the stall within
    STALL_WALL and a stack dump of every thread, the play ended."""
    monkeypatch.setattr(driver, 'STALL_WALL', 0.3)
    monkeypatch.setattr(driver, 'STALL_DUMP', tmp_path / 'stall.txt')
    stop = threading.Event()
    spinning = threading.Thread(target=stop.wait, name='macro', daemon=True)
    spinning.start()
    ended: list[bool] = []
    play: Any = SimpleNamespace(
        runner=SimpleNamespace(lock=threading.Lock(), thread=spinning, working=True),
        arena=SimpleNamespace(clock=SimpleNamespace(now=3.5)),
        end=lambda: ended.append(True),
        ended=False,
        seconds=60.0,
    )
    play.hung = lambda why: driver.Play.hung(play, why)
    began = time.monotonic()
    try:
        with pytest.raises(RuntimeError, match=r'the game clock stood at 3\.50 s'):
            driver.Play.settle(play)
    finally:
        stop.set()
    assert time.monotonic() - began < 2.0
    assert ended == [True]
    dump = (tmp_path / 'stall.txt').read_text()
    assert 'hung at game 3.50 s' in dump
    assert 'macro' in dump


def test_the_pursuit_fight_that_hung_moves_its_game_clock() -> None:
    """fane-death-24, drawn, seed 5, on-time looks, through the TZ run's pursuit (one KP_1 press, the level wanted as a
    terror zone): it ran past WALL_LIMIT on 2026-10-22; now it plays to its end under the watchdog, alive."""
    situation = fd.stored('fane-death-24').logic('new').variant(presses=(once('pickup'),))
    inner = fd.drawing('fane-death-24')

    def extra(stage, play) -> None:
        play.progress.wanted = lambda area: True
        inner(stage, play)

    outcome = fd.play(situation, fd.ALL_ON, 5, lap=None, extra=extra)  # a hang raises (`Play.hung`)
    assert outcome.dead_at is None
