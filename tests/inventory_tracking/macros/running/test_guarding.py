"""The stand guard on the runner (macros/guard.py, running/guarding.py): after a stop of the loop's own the character is
not left standing defenceless. 20:48:09 on 2026-10-22, the Arcane Sanctuary (runs/alt-d/20261022T174205Z-825a8a0e):
the loop stopped itself by a Superior Flail ("... lies on the ground: the loop stops here"), attack mode off, and the
character stood 3.5 min under fire (the player: "we're standing without enabled fight under heavy damage")."""

import logging
import threading
from pathlib import Path

import pytest

from inventory_tracking.macros import guard
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.loop import TZ
from inventory_tracking.macros.routines import Dead
from inventory_tracking.macros.runner import LOOP, MacroRunner
from inventory_tracking.macros.running.base import ATTACK


GAME = 'cyberg65'
SANCTUARY = 74
TOWN = 40  # Lut Gholein
FLAIL = 'Superior Flail'
HOLD = 'Superior Flail at (25088, 5474) was not picked up after 2 trips back'
MOST = 2943


class Standing:
    """A runner whose polls read the character in `area` of GAME with `life` (points), mode `mode`, a hostile within
    SIGHT when `near`; its runs recorded, not made."""

    def __init__(self, *, area: int = SANCTUARY) -> None:
        self.area, self.life, self.mode, self.near, self.asked = area, MOST, 1, False, 0
        self.runner = runner = MacroRunner(
            None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent'), display=lambda lines: None,
            place=self.place, staff_in_hand=lambda: None,
        )  # fmt: skip
        self.started: list[str] = []
        runner._start = self.started.append  # type: ignore[method-assign]
        runner._dead = lambda: self.mode in (0, 17)  # type: ignore[method-assign]
        runner.attacker_near = self.attacker_near
        runner.valuable_left = lambda: FLAIL
        runner.loop.on, runner.loop.kind = True, TZ
        runner.loop.seen = (GAME, 0.0)

    def place(self) -> tuple[str, int]:
        runner = self.runner
        runner.where, runner.dead_mode, runner.life_seen = (25088.5, 5474.5), self.mode, (self.life, MOST)
        return GAME, self.area

    def attacker_near(self) -> bool:
        self.asked += 1
        return self.near

    def hold(self) -> None:
        """The 20:48:09 stop: the trip back's stop, the cube tried and the leg made again already (stops.py HOLD)."""
        loop = self.runner.loop
        loop.fetch_again = loop.room_tried = loop.dropped = GAME
        self.runner._loop_stopped(Abort(HOLD))
        assert not loop.on

    def polls(self, *clocks: float) -> None:
        for now in clocks:
            self.runner.poll(now)


@pytest.fixture
def standing():
    played = Standing()
    yield played
    played.runner.close()


def test_a_loop_made_stop_with_hostiles_hitting_fights_back_in_place(standing, caplog):
    runner = standing.runner
    with caplog.at_level(logging.INFO):
        standing.hold()
        assert runner.guard.armed
        assert standing.started == []  # nothing yet: the stop's own run is still ending
        standing.near, standing.life = True, 2900
        standing.polls(10.0)
    assert standing.started == [ATTACK]  # attack mode: the hunt's own fight, with its safety
    assert runner.attack_mode
    assert not runner.attack_declined
    assert runner.guard.fighting
    assert not runner.loop.on  # no leg of the loop: the game is neither left nor saved and exited
    assert not runner.loop.abandon
    assert 'lies on the ground: the loop stops here' in caplog.text
    assert 'Macro: guard: a hostile within 30 after the loop stopped itself: fighting back in place' in caplog.text


def test_a_hit_from_out_of_sight_fights_back_and_the_fight_ends_once_quiet(standing, caplog):
    # The 20:48 stand's blows: 15-50 of 2943, from hostiles 14-23 away; here none is read within SIGHT
    runner = standing.runner
    standing.hold()
    standing.polls(10.0)  # the first look: the life as it stands
    assert standing.started == []
    standing.life = 2900  # 43 down: a hit
    standing.polls(11.0)
    assert standing.started == [ATTACK]
    runner.working, runner.routine = True, ATTACK  # the guard's attack mode works
    with caplog.at_level(logging.INFO):
        standing.polls(12.0, 13.0, 14.0, 15.0)
        assert runner.attack_mode  # under QUIET: the fight goes on
        standing.polls(12.0 + guard.QUIET)
    assert not runner.attack_mode
    assert runner.cancelled.is_set()  # its run cancelled: no key
    assert not runner.guard.fighting
    assert runner.guard.armed  # it keeps watching
    assert "the guard's attack mode off" in caplog.text


def test_the_players_kp6_off_arms_no_guard(standing):
    runner = standing.runner
    runner._toggle_loop()  # the player's KP_6: "PLAYER: loop off"
    assert not runner.loop.on
    assert not runner.guard.armed
    standing.near, standing.life = True, 2500
    standing.polls(10.0, 11.0, 12.0)
    assert standing.started == []
    assert not runner.attack_mode
    assert standing.asked == 0  # not even a look at the hostiles


def test_the_players_kp6_after_the_stop_ends_the_guard_and_its_fight_for_the_first_leg(standing):
    runner = standing.runner
    standing.hold()
    standing.near = True
    standing.polls(10.0)
    assert standing.started == [ATTACK]
    runner.working, runner.routine = True, ATTACK
    runner._toggle_loop()  # the player turns the loop on again
    assert runner.loop.on
    assert not runner.guard.armed
    assert not runner.attack_mode  # the guard's mode off: its run's end is followed by the loop's first leg
    assert runner.cancelled.is_set()
    runner.working = False
    assert runner._follow(ATTACK)
    assert standing.started[-1] == LOOP


def test_the_players_attack_key_takes_the_mode_over(standing):
    runner = standing.runner
    standing.hold()
    runner.request(10.0, 10.0, ATTACK)  # the player's KP_3
    assert not runner.guard.armed
    standing.near = True
    standing.polls(11.0)
    assert standing.started == [ATTACK]  # the player's toggle's, not the guard's
    assert not runner.guard.fighting


def test_dead_nothing_at_all(standing, caplog):
    runner = standing.runner
    standing.mode = 0  # dead at the stop
    with caplog.at_level(logging.INFO):
        standing.hold()
    assert not runner.guard.armed
    standing.near = True
    standing.polls(10.0, 11.0)
    assert standing.started == []
    assert standing.asked == 0
    assert not runner.attack_mode


def test_a_death_under_the_guard_ends_it_and_presses_nothing(standing):
    runner = standing.runner
    standing.hold()
    standing.near = True
    standing.polls(10.0)
    assert standing.started == [ATTACK]
    runner.working, runner.routine = True, ATTACK
    standing.mode, asked = 17, standing.asked
    standing.polls(11.0, 12.0)
    assert not runner.guard.armed
    assert standing.started == [ATTACK]  # nothing more started
    assert standing.asked == asked  # no read of the hostiles either
    assert not runner.attack_mode  # its run cancelled
    assert runner.cancelled.is_set()


def test_a_dead_stop_arms_nothing():
    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent'))
    runner.loop.on = True
    runner._stop_loop(Dead('the character is dead'))
    assert not runner.guard.armed
    runner.close()


def test_in_town_nothing():
    played = Standing(area=TOWN)
    runner = played.runner
    try:
        played.hold()
        assert runner.guard.armed
        played.near, played.life = True, 2000
        played.polls(10.0, 11.0, 12.0)
        assert played.started == []
        assert played.asked == 0
        assert not runner.attack_mode
    finally:
        runner.close()


def test_another_game_ends_the_guard(standing):
    runner = standing.runner
    standing.hold()
    standing.polls(10.0)
    assert runner.guard.game == GAME
    runner.place = lambda: ('cyberg66', SANCTUARY)
    standing.polls(11.0)
    assert not runner.guard.armed


def test_the_switch_off_arms_nothing(standing, monkeypatch):
    monkeypatch.setattr(guard, 'GUARD', False)
    standing.hold()
    standing.near = True
    standing.polls(10.0, 11.0)
    assert not standing.runner.guard.armed
    assert standing.started == []


def test_a_run_working_is_not_interrupted(standing):
    # The player's own step (a KP_1 pickup by hand) works: the guard waits for its end
    runner = standing.runner
    standing.hold()
    runner.working, runner.routine = True, 'pickup'
    standing.near = True
    standing.polls(10.0)
    assert standing.started == []
    assert not runner.attack_mode
    runner.working = False
    standing.polls(11.0)
    assert standing.started == [ATTACK]
