"""The service loop's poll and the run's stand by a valuable with no room (macros/running/watch.py `poll`,
`stood_after_cube`). The Canyon of the Magi, 14:03:35 on 2026-10-20 (runs/alt-d/20261020T105107Z-e9d9dd94): the cube
made room for a Unique Razor Bow at 14:02:56, then the run stood 45 s by a magic Ring with no room, nothing more done,
until the still watchdog left the game with the Ring on the ground (rca/2026-10-20/stand-after-fight-findings.md)."""

import logging
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.loop import TZ
from inventory_tracking.macros.runner import MacroRunner
from inventory_tracking.macros.running.base import MAKE_ROOM_AFTER


GAME = 'cyberg15'
RING = 'Inventory full: Ring here — make room (the cube has room for it)'
RING_UNIT = 4054583999


def stood(*, left: str | None, foe: bool = False, room_tried: str | None = GAME, working: bool = True):
    """A runner whose polls read the character in the Canyon of the Magi (area 46), the loop on, its level run standing
    by the Ring since the clock 100 (`_stand_by`); `left` what the guard keeps the game for, `foe` a hostile within
    SIGHT. Its stops are recorded, not made."""
    runner = MacroRunner(
        None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent'), display=lambda lines: None,
        place=lambda: (GAME, 46),
    )  # fmt: skip
    stops: list[object] = []
    runner.valuable_left = lambda: left
    runner.attacker_near = lambda: foe
    runner._loop_stopped = stops.append  # type: ignore[method-assign]
    runner.loop.on, runner.loop.kind, runner.loop.room_tried = True, TZ, room_tried
    runner.attack_mode, runner.working = True, working
    runner.hunter = cast(
        Hunter,
        SimpleNamespace(
            warned=RING_UNIT,
            waived=set(),
            score=SimpleNamespace(killed=0),
            waves=SimpleNamespace(due=lambda now: False),
        ),
    )
    runner.warning, runner.standing = (RING, 100.0), True
    return runner, stops


def test_a_stand_after_the_games_cube_with_a_valuable_kept_takes_the_next_room_rule_at_once(caplog):
    # 01:24:02 on 2026-10-20: a Grand Charm's stand got its room package only from the watchdog, 40 s on
    runner, stops = stood(left='Grand Charm')
    with caplog.at_level(logging.INFO):
        runner.poll(100.0 + MAKE_ROOM_AFTER + 1)
    assert len(stops) == 1
    stop = stops[0]
    assert isinstance(stop, Abort)
    assert stop.cause == 'room'  # the room rules (stops.py ROOM_CAUSES), as the watchdog's 'stall'
    assert str(stop) == f'{RING}: the cube was tried in this game'
    assert not runner.attack_mode
    assert runner.cancelled.is_set()
    assert not runner.standing  # answered once
    assert not runner.loop.make_room  # no second cube
    runner.poll(100.0 + MAKE_ROOM_AFTER + 3)
    assert len(stops) == 1


def test_a_stand_after_the_games_cube_by_an_identify_candidate_gives_it_up_and_the_run_goes_on(caplog):
    # 14:03:35 on 2026-10-20: the magic Ring (an identify candidate: the guard keeps no game for it) stood by 45 s,
    # then the game left by the watchdog
    runner, stops = stood(left=None)
    with caplog.at_level(logging.INFO):
        runner.poll(100.0 + MAKE_ROOM_AFTER + 1)
    assert stops == []  # the game is not left
    assert runner.attack_mode  # the level run goes on
    assert not runner.cancelled.is_set()
    assert runner.hunter is not None
    assert RING_UNIT in runner.hunter.waived  # the hunt's stand (hunting/choice.py `stay_by`) gives it up
    assert not runner.standing
    assert f'Macro: loop: {RING}: the cube was tried in this game and no game is kept for it: the run goes on' in (
        caplog.text
    )


def test_a_stand_after_the_games_cube_waits_while_a_hostile_is_near_and_says_so_once(caplog):
    runner, stops = stood(left='Grand Charm', foe=True)
    with caplog.at_level(logging.INFO):
        runner.poll(100.0 + MAKE_ROOM_AFTER + 1)
        runner.poll(100.0 + MAKE_ROOM_AFTER + 3)
    assert stops == []
    assert runner.attack_mode  # the fight goes on: no Town Portal in it
    assert runner.standing
    said = 'the cube was tried in this game; Grand Charm lies on the ground: the next room rule once no hostile is'
    assert caplog.text.count(said) == 1
    runner.attacker_near = lambda: False
    runner.poll(100.0 + MAKE_ROOM_AFTER + 5)
    assert len(stops) == 1


def test_the_first_stand_of_a_game_still_makes_room_in_the_cube(caplog):
    # 14:02:56 on 2026-10-20: "Inventory full: Unique Razor Bow here — make room: room is made in the cube"
    runner, stops = stood(left='Unique Razor Bow', room_tried=None)
    with caplog.at_level(logging.INFO):
        runner.poll(100.0 + MAKE_ROOM_AFTER + 1)
    assert (runner.loop.make_room, runner.loop.room_tried) == (True, GAME)
    assert stops == []
    assert not runner.attack_mode
    assert f'Macro: loop: {RING}: room is made in the cube' in caplog.text


def test_a_stand_is_answered_only_after_make_room_after():
    runner, stops = stood(left='Grand Charm')
    runner.poll(100.0 + MAKE_ROOM_AFTER - 1)
    assert stops == []
    assert runner.standing
    assert runner.attack_mode


def test_a_plain_warning_is_no_stand():
    runner, stops = stood(left=None)
    runner.standing = False  # a warning of another kind (`_warn`)
    runner.poll(100.0 + MAKE_ROOM_AFTER + 1)
    assert stops == []
    assert runner.hunter is not None
    assert runner.hunter.waived == set()


def test_the_stand_the_cube_answered_is_not_answered_again_on_the_next_poll():
    # 14:02:56 on 2026-10-20: the cube's room for the Razor Bow; the stand's warning stays while the loop's cube leg
    # and pickup run, and no trip may follow it a second later
    runner, stops = stood(left='Unique Razor Bow', room_tried=None)
    runner.poll(100.0 + MAKE_ROOM_AFTER + 1)
    assert runner.loop.room_tried == GAME
    runner.attack_mode = True
    runner.poll(100.0 + MAKE_ROOM_AFTER + 3)
    assert stops == []
    assert runner.attack_mode
    assert runner.hunter is not None
    assert runner.hunter.waived == set()
    # A later stand (another valuable, `_stand_by` anew) is answered
    runner.warning, runner.standing = (RING, 200.0), True
    runner.poll(200.0 + MAKE_ROOM_AFTER + 1)
    assert len(stops) == 1


def test_a_stand_a_stop_answered_is_left_to_the_watchdog():
    # A leg's stop (the CUBE remedy of `_loop_stopped`, say) sets the game's cube tried under a stand still warned
    runner, stops = stood(left='Grand Charm')
    runner.stand_answered = 101.0  # `_loop_stopped` at the clock 101
    runner.poll(100.0 + MAKE_ROOM_AFTER + 1)
    assert stops == []
    assert runner.attack_mode


def test_a_stop_answers_the_stand():
    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent'), display=lambda _: None)
    runner.valuable_left = lambda: None
    runner._dead = lambda: False  # type: ignore[method-assign]
    before = runner.stand_answered
    runner._loop_stopped(Abort('Grand Charm is 40 away', cause='room'))
    assert runner.stand_answered > before
    runner.close()
