import random

import pytest

from inventory_tracking.macros.routines import prebuff
from inventory_tracking.macros.timing import HOLD, PAUSES, Pace
from tests.inventory_tracking.macros.fakes import Game, world


@pytest.mark.parametrize('kind', sorted(PAUSES))
def test_pauses_stay_in_their_range_and_vary(kind):
    slept = []
    pace = Pace(random.Random(3), slept.append)
    for _ in range(200):
        pace.pause(kind)
    low, high = PAUSES[kind]
    assert low <= min(slept)
    assert max(slept) <= high
    assert len({round(value, 4) for value in slept}) > 150
    assert sum(slept) / len(slept) < (low + high) / 2  # mostly the quick half


def test_no_pause_is_long():
    assert max(high for _, high in PAUSES.values()) < 1
    assert HOLD[1] < 0.15


def test_a_whole_prebuff_spends_under_three_seconds_on_pauses_and_differs_between_runs():
    # The scripted game shows no cast for Purge and Ward, so 2 x 0.8 s of looking for one is taken off.
    spent = []
    for seed in (1, 2):
        game = Game(world())
        prebuff(game.run(seed))
        spent.append(game.clock.now - 1.6)
    assert all(1 < seconds < 3 for seconds in spent)
    assert spent[0] != spent[1]


class FakeTime:
    """A clock that only moves when `sleep` is called; every sleep is recorded."""

    def __init__(self):
        self.now = 0.0
        self.calls = []

    def sleep(self, seconds):
        self.calls.append(seconds)
        self.now += seconds


def test_plain_sleep_outside_watched_is_one_sleep_and_no_look():
    # Outside a watch a pause is the plain sleep it always was: no look, no slicing.
    fake = FakeTime()
    pace = Pace(random.Random(1), fake.sleep)
    pace.sleep(0.5)
    assert fake.calls == [0.5]


def test_watched_sleep_is_cut_into_slices_each_preceded_by_a_look():
    # The attack mode looks at the mouse before every slice, so a long wait never goes unwatched.
    fake = FakeTime()
    pace = Pace(random.Random(1), fake.sleep)
    looks = []
    with pace.watched(lambda: looks.append(1), 0.01, lambda: fake.now):
        pace.sleep(0.05)
    assert all(seconds <= 0.01 + 1e-9 for seconds in fake.calls)
    assert sum(fake.calls) == pytest.approx(0.05)
    assert len(looks) == len(fake.calls) + 1


def test_a_sleep_shorter_than_a_slice_still_looks_before_and_after():
    # Even a short pause is looked at on both sides, so a click just before or after the pause is seen.
    fake = FakeTime()
    pace = Pace(random.Random(1), fake.sleep)
    looks = []
    with pace.watched(lambda: looks.append(1), 0.01, lambda: fake.now):
        pace.sleep(0.004)
    assert fake.calls == [pytest.approx(0.004)]
    assert len(looks) == 2


def test_a_zero_sleep_inside_watched_looks_once_and_sleeps_not():
    # A zero pause still gives the watch one look, and no time is slept.
    fake = FakeTime()
    pace = Pace(random.Random(1), fake.sleep)
    looks = []
    with pace.watched(lambda: looks.append(1), 0.01, lambda: fake.now):
        pace.sleep(0)
    assert looks == [1]
    assert fake.calls == []


@pytest.mark.parametrize('pause', ['key', 'hold', 'pointer_step'])
def test_every_kind_of_pause_is_watched(pause):
    # Key holds and pointer steps wait through the same pace, so they are watched as well as routine waits.
    fake = FakeTime()
    pace = Pace(random.Random(1), fake.sleep)
    looks = []
    with pace.watched(lambda: looks.append(1), 0.01, lambda: fake.now):
        if pause == 'hold':
            pace.hold()
        elif pause == 'pointer_step':
            pace.pointer_step()
        else:
            pace.pause(pause)
    assert len(looks) >= 2


def test_pace_is_plain_again_after_the_block_even_when_it_raises():
    # A failure inside a watch must not leave the look behind for every later pause.
    fake = FakeTime()
    pace = Pace(random.Random(1), fake.sleep)
    looks = []
    with pytest.raises(RuntimeError), pace.watched(lambda: looks.append(1), 0.01, lambda: fake.now):
        raise RuntimeError
    looks_before = len(looks)
    fake.calls.clear()
    pace.sleep(0.5)
    assert fake.calls == [0.5]
    assert len(looks) == looks_before


def test_a_nested_watch_restores_the_outer_one_after_it_exits():
    # Attack mode inside a routine: the inner watch must hand the sleeps back to the outer look.
    fake = FakeTime()
    pace = Pace(random.Random(1), fake.sleep)
    outer, inner = [], []
    with pace.watched(lambda: outer.append(1), 0.01, lambda: fake.now):
        with pace.watched(lambda: inner.append(1), 0.01, lambda: fake.now):
            pace.sleep(0.02)
        inner_looks = len(inner)
        outer_looks = len(outer)
        pace.sleep(0.02)
    assert inner_looks > 0
    assert outer_looks == 0
    assert len(inner) == inner_looks
    assert len(outer) > 0


def test_a_look_that_raises_stops_the_sleep_at_once():
    # A click seen by the look ends the wait: the rest of the second must not be slept.
    fake = FakeTime()
    pace = Pace(random.Random(1), fake.sleep)
    calls = []

    def look():
        calls.append(1)
        if len(calls) == 3:
            raise RuntimeError('clicked')

    with pytest.raises(RuntimeError, match='clicked'), pace.watched(look, 0.01, lambda: fake.now):
        pace.sleep(1.0)
    assert fake.now < 0.1
