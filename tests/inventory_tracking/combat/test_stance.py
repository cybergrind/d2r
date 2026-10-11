"""Where to stand (combat/stance.py): the step the pickup request asks for."""

import math

from inventory_tracking.combat.policy import Foe, LinePolicy, Observation
from inventory_tracking.combat.stance import (
    CAMP_REACH,
    CAST_SECONDS,
    HOP_SECONDS,
    HORIZON,
    KEEP_AWAY,
    RUN_SPEED,
    WALK_LATENCY,
    Field,
    camp,
    no_footing,
    taken,
    way,
)


HERE = (5000.5, 5000.5)


def flat(txt):
    return 1000.0


POLICY = LinePolicy(damage_of=flat)


def foe(dx, dy, left=5000.0, elite=False):
    return Foe(310, (HERE[0] + dx, HERE[1] + dy), left, elite)


def box(x0, y0, x1, y1):
    return lambda p: HERE[0] + x0 <= p[0] <= HERE[0] + x1 and HERE[1] + y0 <= p[1] <= HERE[1] + y1


def test_a_monster_in_reach_with_a_clear_line_is_no_reason_to_step():
    assert camp(Observation(HERE, {1: foe(18, 0)}), POLICY) is None


def test_a_monster_past_the_blades_is_stepped_toward():
    found = camp(Observation(HERE, {1: foe(30, 0)}), POLICY)
    assert found is not None
    assert found.here == 0.0
    assert math.dist(found.spot, (HERE[0] + 30, HERE[1])) <= POLICY.reach
    assert found.seconds == WALK_LATENCY + found.walk / RUN_SPEED
    assert found.casts == 2  # 5,000 points at 2,800 a cast


def test_a_pack_that_dies_as_fast_from_here_is_not_walked_to():
    # Two monsters of one cast each on two lines: two casts from here, one from behind them after a walk.
    pair = {1: foe(12, -4, left=2000.0), 2: foe(12, 4, left=2000.0)}
    assert camp(Observation(HERE, pair), POLICY) is None


def test_a_big_pack_in_a_row_is_walked_to_its_end_where_one_line_takes_it_all():
    row = {unit: foe(9, 2 * unit, left=6000.0) for unit in range(8)}
    seen = Observation(HERE, row)
    found = camp(seen, POLICY)
    assert found is not None
    assert abs(found.spot[0] - (HERE[0] + 9)) <= 4.0  # near the row's own line, off its end
    assert found.spot[1] < HERE[1]
    assert 3 <= found.casts <= 5  # 6,000 points at 2,800 a cast: three with all eight on one line
    here, never = taken(seen, POLICY, Field(None, None), HERE, 0.0)
    assert never == 0  # from here the horizon ends first
    assert found.worth > here == found.here


def test_the_pack_behind_a_corner_is_walked_round_to():
    # A wall east of the character, open at its north end: no straight walk has a shot, the way round has.
    wall = box(4, -6, 6, 40)
    pack = {unit: foe(14, 4 + 2 * unit) for unit in range(4)}
    seen = Observation(HERE, pack, blocked=wall)
    assert POLICY.choose(seen) is None
    found = camp(seen, POLICY, barred=wall)
    assert found is not None
    assert not wall(found.spot)
    assert found.walk >= math.dist(HERE, found.spot)
    assert found.walk > math.dist(HERE, found.spot) or way(wall, HERE, found.spot)


def test_no_place_when_no_way_leads_to_a_shot_and_a_hop_when_that_is_allowed():
    wall = box(4, -60, 6, 60)
    seen = Observation(HERE, {1: foe(14, 0)}, blocked=wall)
    assert camp(seen, POLICY, barred=wall) is None
    found = camp(seen, POLICY, barred=wall, hop=True)
    assert found is not None
    assert found.hop
    assert found.seconds == HOP_SECONDS
    assert found.spot[0] > HERE[0] + 6


def test_no_place_next_to_a_monster_and_none_the_window_does_not_show():
    crowd = {unit: foe(30 + 2 * unit, 0) for unit in range(4)}
    seen = Observation(HERE, crowd)
    found = camp(seen, POLICY)
    assert found is not None
    assert all(math.dist(found.spot, f.at) >= KEEP_AWAY for f in crowd.values())
    assert camp(seen, POLICY, shown=lambda spot: spot[0] < HERE[0]) is None


def test_a_place_further_than_the_reach_is_not_looked_at():
    assert camp(Observation(HERE, {1: foe(CAMP_REACH + POLICY.reach + 5, 0)}), POLICY) is None


def test_being_done_sooner_is_worth_more_and_not_being_done_adds_nothing():
    seen = Observation(HERE, {1: foe(10, 0, left=2000.0)})
    field = Field(None, None)
    now, casts = taken(seen, POLICY, field, HERE, 0.0)
    later, _ = taken(seen, POLICY, field, HERE, 1.0)
    assert casts == 1
    assert now == 2000.0 * (1 + (HORIZON - CAST_SECONDS) / HORIZON)
    assert later == 2000.0 * (1 + (HORIZON - 1.0 - CAST_SECONDS) / HORIZON)
    tough = Observation(HERE, {1: foe(10, 0, left=100_000.0)})
    worth, never = taken(tough, POLICY, field, HERE, 0.0)
    assert never == 0
    assert worth == 2800.0 * int(HORIZON / CAST_SECONDS)


def test_the_ways_go_round_what_bars_them_and_cut_no_corner():
    wall = box(2, -3, 3, 3)
    ways = Field(None, wall).ways(HERE, 12.0)
    east = (math.floor(HERE[0]) + 6, math.floor(HERE[1]))
    assert ways[east] > 6.5  # round the wall's end, not through it
    assert (math.floor(HERE[0]) + 2, math.floor(HERE[1])) not in ways


class Grid:
    def __init__(self, walk):
        self.walk = walk

    def __len__(self):
        return 1

    def walkable(self, x, y):
        return self.walk(x, y)


class Door:
    closed = True

    def blocks(self, point):
        return point[0] > 10


def test_footing_is_what_the_grids_show_walkable_and_no_closed_door():
    assert no_footing(None) is None
    barred = no_footing(Grid(lambda x, y: None if x < 0 else x < 5))
    assert barred is not None
    assert [barred((x, 0.0)) for x in (-1.0, 2.0, 7.0)] == [True, False, True]
    door = no_footing(None, [Door()])
    assert door is not None
    assert door((11.0, 0.0))
    assert not door((9.0, 0.0))
