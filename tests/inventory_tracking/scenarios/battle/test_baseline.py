"""Tower Cellar 5: what the same fight gives once the macro strikes all the time it could have.

Two things kept the strikes from the Herald (macros/plan.md, 2026-10-12): the sweep's stop for a potion
(4.9 s, to the death) and the keys under the held strike waiting for a free instant. Both are changed
(hunt.GATHER_CLEAR, rotation.Rotation.key). The replay is open loop and cannot show what a fight fought
on would have done, so the moment is played in the stance harness (baseline.py), its Herald fitted to
the recorded strikes.
"""

import functools

import pytest

from tests.inventory_tracking.scenarios.battle import baseline, tower_cellar5 as battle
from tests.inventory_tracking.scenarios.battle.replay import Replay
from tests.inventory_tracking.scenarios.stance import harness


HERALD = 2960229440
ARRIVED = 13.5  # seconds into the take: the Herald and its nine are in sight, 17 units off
STOPPED = 18.2  # the sweep stops for the potion; no strike after 18.6 s
TO_DEATH = battle.DEATH - ARRIVED
# The strike input held, from the take's cast events: 13.7 to 14.84, 14.9 to 15.69, 16.6 to 18.57 s.
RECORDED = [(13.7, 14.84), (14.9, 15.69), (16.6, 18.57)]
SEEN = {17.1: 126, 19.0: 92, battle.DEATH: 82}  # the Herald's life in the take's frames, of 128


@functools.cache
def scenes() -> tuple[harness.Scene, harness.Scene, float]:
    replay = Replay(battle.FIXTURE, battle.script())
    arrival, stop = baseline.scene_at(replay, ARRIVED), baseline.scene_at(replay, STOPPED)
    # The Herald's full life: what makes the recorded strikes take the 36/128 they took by 19.0 s.
    full = baseline.fitted_life(arrival, HERALD, baseline.striking_in(RECORDED, ARRIVED), 19.0 - ARRIVED, 36 / 128)
    return baseline.with_life(arrival, HERALD, full), baseline.with_life(stop, HERALD, full), full


def test_the_herald_has_eleven_times_the_life_the_model_gives_an_elite():
    _, _, full = scenes()
    replay = Replay(battle.FIXTURE, battle.script())
    modelled = next(body.points for body in baseline.scene_at(replay, ARRIVED).bodies if body.unit == HERALD)
    assert full / modelled == pytest.approx(11.2, abs=0.6)  # 105,800 points against 9,473


def test_with_the_recorded_strikes_the_model_leaves_the_herald_what_the_game_left_it():
    arrival, _, full = scenes()
    trace = baseline.play(arrival, baseline.striking_in(RECORDED, ARRIVED), TO_DEATH)
    assert baseline.dead_at(trace, HERALD) is None
    assert baseline.left(trace, HERALD, TO_DEATH, full) == pytest.approx(SEEN[battle.DEATH], abs=6)  # 84 against 82


@pytest.mark.xfail(
    strict=True,
    reason='the model takes 28/128 off the Herald by 17.1 s where the game took 2/128: it stood 17 units off '
    'behind its pack, and the harness lets the blades through to it; the fit holds the total, not the shape',
)
def test_the_model_takes_the_heralds_life_when_the_game_did():
    arrival, _, full = scenes()
    trace = baseline.play(arrival, baseline.striking_in(RECORDED, ARRIVED), TO_DEATH)
    assert baseline.left(trace, HERALD, 17.1 - ARRIVED, full) == pytest.approx(SEEN[17.1], abs=6)


def test_striking_all_the_time_kills_the_herald_ten_seconds_after_it_came():
    # The new baseline: with nothing but strikes from the Herald's arrival it dies 10.4 s on, 0.8 s
    # after the moment the character died; in the game it was at 82/128 then and never close.
    arrival, _, full = scenes()
    trace = baseline.play(arrival, harness.stay, 30.0)
    assert baseline.dead_at(trace, HERALD) == pytest.approx(10.4, abs=0.6)
    assert baseline.left(trace, HERALD, TO_DEATH, full) <= 20  # 12/128 where the game had 82/128


def test_fighting_on_from_the_potion_stop_alone_does_not_kill_the_herald_before_the_death():
    # Today's rule leaves the potion and the fight goes on (test_tower_cellar5.py). From that moment
    # (the Herald at 111/128, 12.7 units off) the model needs 8.8 s, and the death was 4.9 s away.
    # At the rate the game showed in its last 1.5 s of strikes (34/128) it would have been 4 s: the
    # Herald dead at the moment the character died. Damage alone does not settle this fight: where
    # the character stands while it deals it does.
    _, stop, full = scenes()
    trace = baseline.play(stop, harness.stay, 30.0)
    assert baseline.dead_at(trace, HERALD) == pytest.approx(8.8, abs=0.6)
    assert baseline.left(trace, HERALD, battle.DEATH - STOPPED, full) == pytest.approx(51, abs=8)
