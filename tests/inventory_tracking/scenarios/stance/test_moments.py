"""The step on the 39 moments cut from the Tower runs of 2026-10-10 night (fixtures/, build_fixtures.py):
each is a press of the pickup request with hostiles near, with what the first rule answered and
what the game then did. The harness replays them with the monsters standing still (in the game they
came to the character: the recorded fights ended in 3.0 s at the median with no step at all), so
its seconds are worth comparing with each other, not with the recorded ones.

Measured 2026-10-11, 15 s a moment, "cleared" = every hostile that stood within 30 units dead:

| strategy                                   | cleared | seconds in all | points in the first 3 s |
| no step                                    |  8      | 476            | 155k |
| the first rule (12 units, twice the line)  | 26      | 255            | 316k |
| `camp`, one step                           | 29      | 226            | 397k |
| `camp`, and two more when nothing in reach | 34      | 181            | 397k |
| the same with a teleport allowed           | 36      | 162            | n/a  |

The best single walk found by trying every place cleared 29 as well, in 58 s where `camp` took 70
on the 28 moments both cleared. HORIZON 2 cleared 26, 4 as many as 3; CAMP_GAIN 1.1 to 1.5, KEEP_AWAY
4 and CAMP_GRID 2 changed the seconds by under 1%.

Tried and dropped: no step while what is in reach dies within two casts. It cleared LEFT_FOR_MORE
(30 with one step) and took 12% less in the first 3 s with the follow-on steps (349k), in 187 s.
"""

from functools import cache
from pathlib import Path

import pytest

from .harness import Result, load, play, production, stay


FIXTURES = sorted((Path(__file__).parent / 'fixtures').glob('*.json'))
SECONDS = 15.0
STRATEGIES = {'stay': lambda: stay, 'step': production, 'follow': lambda: production(follow=2)}
# The moments one step does not clear and the follow-on steps do: the pack stood in two places.
TWO_PLACES = 5
# The one moment a step leaves what stood near alive: two monsters in reach, and a pack of more points
# a walk of 22 away, which it goes to and takes 20,265 points from in 15 s (staying takes the two).
LEFT_FOR_MORE = '20261010T205557Z-22-235616'


@cache
def outcome(path: Path, strategy: str) -> Result:
    return play(load(path), STRATEGIES[strategy](), seconds=SECONDS)


def cleared(strategy: str) -> set[str]:
    return {path.stem for path in FIXTURES if outcome(path, strategy).cleared}


def seconds(strategy: str) -> float:
    spent = (outcome(path, strategy).seconds for path in FIXTURES)
    return sum(SECONDS if took is None else took for took in spent)


def test_one_step_clears_most_moments_and_the_follow_on_steps_the_packs_in_two_places():
    still, step, follow = cleared('stay'), cleared('step'), cleared('follow')
    assert len(FIXTURES) == 39
    assert len(still) == 8
    assert len(step) == 29
    assert len(follow) == 29 + TWO_PLACES
    assert still - step == {LEFT_FOR_MORE}
    assert step <= follow


def test_the_seconds_in_all():
    assert seconds('stay') == pytest.approx(476, abs=2)
    assert seconds('step') == pytest.approx(226, abs=3)
    assert seconds('follow') == pytest.approx(181, abs=3)


@pytest.mark.parametrize('path', FIXTURES, ids=lambda path: path.stem[-9:])
def test_no_moment_is_slower_for_the_follow_on_steps(path):
    step, follow = outcome(path, 'step'), outcome(path, 'follow')
    if step.seconds is not None:
        assert follow.seconds is not None
        assert follow.seconds <= step.seconds + 0.5


def test_where_staying_clears_a_step_costs_little():
    for path in FIXTURES:
        still, step = outcome(path, 'stay'), outcome(path, 'step')
        if still.seconds is not None and path.stem != LEFT_FOR_MORE:
            assert step.seconds is not None
            assert step.seconds <= still.seconds + 0.6, path.stem
