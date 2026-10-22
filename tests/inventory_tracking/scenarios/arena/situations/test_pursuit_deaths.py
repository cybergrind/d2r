"""The pursuit-mode Fane deaths of 2026-10-22's round 6 (rca/2026-10-21/death-findings.md, Round 6): each one a look
gap with a one-shotter closing, replayed through the TZ run's pursuit (one KP_1 press, the level wanted as a terror
zone) under the arena's watchdog (driver.py STALL_WALL: a game clock that stands still raises), every fix on.

- fane-death-20, seed 4, on-time looks: Death Mark and the Sigil cast under the strike for 1.0 s with no look while
  the elite Night Lord (3581 a blow) walked in (macros/hunt.py FIGHT_CAST_REACH).
- fane-death-20, drawn, seed 20, on-time looks, the `fast` pace: a walk to a firing spot blind for 1.1 s while the
  x5.75 unique Flesh Hunter ran in (macros/safety.py WALK_REACH).
- fane-death-20, drawn, seeds 14 and 18, late looks, the `fast` pace: Engorge, Death Mark and the Sigil cast back to
  back under the strike, 1.2-1.5 s blind, the unique 21-24 off at the first (FIGHT_CAST_REACH: one cast a look while
  a one-shotter can close in FIGHT_PACE_SECONDS)."""

import pytest

from tests.inventory_tracking.scenarios.arena.situations import fane_death as fd
from tests.inventory_tracking.scenarios.arena.situations.situation import Outcome, once


LATE = 0.02  # the late look's lap (fane_death.late_timer)


def pursued(name: str, seed: int, *, drawn: bool, lap: float | None, fast: bool) -> Outcome:
    situation = fd.stored(name)
    situation = (fd.fast(situation) if fast else situation).logic('new').variant(presses=(once('pickup'),))
    inner = fd.drawing(name) if drawn else None

    def extra(stage, play) -> None:
        play.progress.wanted = lambda area: True  # the level is a terror zone (terror/tracker.py)
        if inner is not None:
            inner(stage, play)

    return fd.play(situation, fd.ALL_ON, seed, lap=lap, extra=extra)  # a hang raises (driver.py `Play.hung`)


@pytest.mark.parametrize(
    ('name', 'seed', 'drawn', 'lap', 'fast'),
    [
        ('fane-death-20', 4, False, None, False),
        ('fane-death-20', 20, True, None, True),
        ('fane-death-20', 14, True, LATE, True),
        ('fane-death-20', 18, True, LATE, True),
    ],
)
def test_the_pursuit_death_seeds_live_and_their_clocks_move(name, seed, drawn, lap, fast) -> None:
    outcome = pursued(name, seed, drawn=drawn, lap=lap, fast=fast)
    assert outcome.dead_at is None
    assert outcome.kills  # it fought, not only fled
