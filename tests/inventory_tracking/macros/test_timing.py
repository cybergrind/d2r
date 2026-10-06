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
