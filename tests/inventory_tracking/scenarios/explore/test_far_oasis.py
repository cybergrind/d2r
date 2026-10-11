"""The Far Oasis of 02:16 on 2026-10-11 explored with nothing to fight, from where that run came in
(user: "too many back-and-forward iterations"). In the run the rule of the day went west along the
middle, east along the south, eight hops back to the middle from the south-east corner, and at the
end fourteen hops across the whole map for a strip of three rooms it had passed two rooms from.

Measured 2026-10-11, hops and rooms seen of 96 (aims beside the skill bar off, as under test; with
them 53/90 against 46/96):

| from                      | the nearest room | the tour |
| where the run came in     | 62 hops, 89      | 49, 96   |
| its south-east corner     | 57 hops, 94      | 46, 96   |
| its north-west            | 52 hops, 89      | 49, 96   |

The nearest-room rule never saw the rooms no teleport lands in; the tour stands beside them.
"""

from functools import cache

from .harness import Replay, load
from .nearest_rule import nearest_rule


CAME_IN = (4941.5, 5701.5)


@cache
def explored(rule: str) -> tuple[int, int, int]:
    """(hops, rooms seen, rooms) from where the run came in."""
    replay = Replay(load('far-oasis-20261010T231634Z'), CAME_IN)
    hops = replay.hops(nearest_rule(replay) if rule == 'nearest' else None)
    return hops, len(replay.explored), len(replay.bounds)


def test_the_tour_sees_every_room():
    hops, seen, rooms = explored('tour')
    assert (seen, rooms) == (96, 96)
    assert hops <= 49


def test_the_tour_takes_a_fifth_fewer_hops_than_the_nearest_room_and_sees_more():
    nearest, seen, _ = explored('nearest')
    assert seen == 89
    assert explored('tour')[0] <= 0.8 * nearest
