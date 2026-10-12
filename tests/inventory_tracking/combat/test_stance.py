"""Where to stand (combat/stance.py): the step the pickup request asks for."""

import math

import pytest

from inventory_tracking.builds.warlock.echoing_strike.attack import EchoingStrike, LinePolicy
from inventory_tracking.combat.policy import Foe, Observation
from inventory_tracking.combat.stance import (
    CAMP_REACH,
    CAST_SECONDS,
    CROWD_MOST,
    CROWD_UNITS,
    ENGAGE,
    HOP_SECONDS,
    HORIZON,
    KEEP_AWAY,
    RUN_SPEED,
    WALK_LATENCY,
    Field,
    Jump,
    camp,
    closes,
    no_footing,
    taken,
    way,
)


HERE = (5000.5, 5000.5)


def flat(txt):
    return 1000.0


POLICY = EchoingStrike(damage_of=flat)  # the sweep as an attack: a place is priced by an attack


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


# --- a place is priced by the way the character will take there (`Jump`) ---

WARP = Jump(skill=390, seconds=0.35, speed=45.0, reach=26.0, least=8.0, line=True)
BLINK = Jump(skill=54, seconds=0.31, speed=math.inf, reach=26.0, least=8.0, line=False)


def test_a_place_a_jump_reaches_is_priced_by_the_jump_and_names_its_skill():
    seen = Observation(HERE, {1: foe(30, 0)})
    walked, jumped = camp(seen, POLICY), camp(seen, POLICY, jumps=(WARP, BLINK))
    assert walked is not None
    assert jumped is not None
    assert walked.skill is None
    assert jumped.skill == WARP.skill  # the preferred of the two that reach it
    away = math.dist(HERE, jumped.spot)
    assert jumped.seconds == WARP.takes(away) < WALK_LATENCY + away / RUN_SPEED


def test_a_blade_is_not_thrown_through_a_wall_and_a_teleport_goes_over_it():
    wall = box(4, -30, 6, 30)
    seen = Observation(HERE, {1: foe(30, 0)}, blocked=wall)
    assert camp(seen, POLICY, wall, jumps=(WARP,)) is None
    over = camp(seen, POLICY, wall, jumps=(WARP, BLINK))
    assert over is not None
    assert over.skill == BLINK.skill
    assert over.spot[0] > HERE[0] + 6


def test_a_place_nearer_than_a_jumps_least_is_walked_to():
    for east in (23, 24, 26, 30):
        found = camp(Observation(HERE, {1: foe(east, 0)}), POLICY, jumps=(WARP, BLINK))
        assert found is not None
        assert (found.skill is None) == (math.dist(HERE, found.spot) < WARP.least)
        if found.skill is None:
            assert found.seconds == WALK_LATENCY + found.walk / RUN_SPEED


def test_of_two_places_a_jump_makes_as_good_the_one_at_the_distance_a_fight_is_best_begun_from():
    # A teleport takes as long to any place: without this the first place found wins, at the very
    # end of the blades' flight, where a step of the monster's is a miss.
    monster = (HERE[0] + 40, HERE[1])
    found = camp(Observation(HERE, {1: foe(40, 0)}), POLICY, jumps=(BLINK,))
    assert found is not None
    assert abs(math.dist(found.spot, monster) - ENGAGE) <= 3


def test_a_jump_keeps_clear_of_where_the_melee_monsters_will_be_when_it_lands():
    # The cow runs of 2026-10-12 (user: "jumping into their groups too aggressively"): a landing 6 units
    # from the nearest cow when chosen had it at the character by the first cast.
    herd = {unit: Foe(391, (HERE[0] + 30 + 2 * (unit % 4), HERE[1] + 2 * (unit // 4)), 5000.0) for unit in range(12)}
    seen = Observation(HERE, herd)
    jumped = camp(seen, POLICY, jumps=(BLINK,))
    assert jumped is not None
    assert jumped.skill == BLINK.skill
    # A Hell Bovine closes 5.5 units a second: over the jump's 0.31 s and a cast, 3.7 units on top of KEEP_AWAY.
    nearest = min(math.dist(jumped.spot, cow.at) for cow in herd.values())
    assert nearest >= KEEP_AWAY + 5.5 * (0.31 + 0.36) - 1e-6
    # Archers do not come: a place KEEP_AWAY from them will do, for a few of them.
    archers = {unit: Foe(160, cow.at, cow.left) for unit, cow in list(herd.items())[:CROWD_MOST]}
    by_archers = camp(Observation(HERE, archers), POLICY, jumps=(BLINK,))
    assert by_archers is not None
    assert KEEP_AWAY <= min(math.dist(by_archers.spot, foe.at) for foe in archers.values()) < nearest


def test_no_place_is_chosen_in_the_middle_of_a_pack_unless_the_character_stands_in_one():
    # Drifter Cavern, 09:55:34 on 2026-10-12: a walk into four Hell Temptresses, 1,592 points lost in 6 s.
    pack = {unit: Foe(160, (HERE[0] + 30 + 2 * (unit % 4), HERE[1] + 2 * (unit // 4)), 5000.0) for unit in range(12)}
    found = camp(Observation(HERE, pack), POLICY, jumps=(BLINK,))
    assert found is not None
    assert sum(math.dist(found.spot, foe.at) <= CROWD_UNITS for foe in pack.values()) <= CROWD_MOST
    # In the pack already, a place among as many is no worse than where it stands.
    inside = (HERE[0] + 33.5, HERE[1] + 8.5)
    around = sum(math.dist(inside, foe.at) <= CROWD_UNITS for foe in pack.values())
    assert around > CROWD_MOST
    moved = camp(Observation(inside, pack), POLICY, gain=0.0)
    assert moved is None or sum(math.dist(moved.spot, foe.at) <= CROWD_UNITS for foe in pack.values()) <= around


def test_what_a_melee_monster_closes_is_capped_and_one_far_off_does_not_come():
    cow, gloam = Foe(391, (HERE[0] + 10.0, HERE[1]), 5000.0), Foe(118, (HERE[0] + 13.0, HERE[1]), 5000.0)
    assert closes(cow, HERE, 0.5)  # 10 - 5.5 x (0.5 + 0.36) = 5.3: within KEEP_AWAY by the first cast
    assert not closes(cow, HERE, 0.0)  # 10 - 5.5 x 0.36 = 8.0
    assert not closes(Foe(118, (HERE[0] + 21.0, HERE[1]), 5000.0), HERE, 2.0)  # too far off to come for it
    assert not closes(gloam, HERE, 2.0)  # 16.5 a second, but CLOSING_MOST units at the most: 13 - 6 = 7
    assert closes(Foe(118, (HERE[0] + 11.9, HERE[1]), 5000.0), HERE, 2.0)
    assert not closes(Foe(160, (HERE[0] + 6.5, HERE[1]), 5000.0), HERE, 2.0)  # an archer stays where it is
    assert closes(Foe(160, (HERE[0] + 5.0, HERE[1]), 5000.0), HERE, 0.0)  # within KEEP_AWAY: whatever it is


# --- the price of a place is the attack's cast, whatever the attack ---


class Bolt:
    """An attack that is no line: a cast takes 300 points off the one monster it is aimed at."""

    reach = 10.0

    def dealt(self, origin, focal, foes):
        return {unit: 300.0 for unit, found in foes.items() if found.at == focal}


def test_a_place_is_priced_by_what_the_attack_given_deals_capped_and_weighted_here():
    seen = Observation(HERE, {1: foe(8, 0, left=450.0), 2: foe(9, 0, left=450.0, elite=True), 3: foe(15, 0)})
    worth, casts = taken(seen, Bolt(), Field(None, None), HERE, 0.0)
    # 3 is out of this attack's reach. A point off the elite counts twice: 600 off it, then 300 off the
    # other (the elite's last 150 are worth no more), the elite's 150 as 300, the other's last 150.
    assert casts == 4
    assert worth == (600.0 + 300.0 + 300.0 + 150.0) * (1 + (HORIZON - 4 * CAST_SECONDS) / HORIZON)


def test_a_place_is_chosen_for_the_attack_given():
    # 14 away: within the blades' reach, out of the bolt's, which so has a place worth going to.
    seen = Observation(HERE, {1: foe(14, 0)})
    assert camp(seen, POLICY) is None
    found = camp(seen, Bolt())
    assert found is not None
    assert math.dist(found.spot, seen.foes[1].at) <= Bolt.reach


def test_a_place_is_priced_by_an_attack_and_not_by_a_bare_sweep():
    seen = Observation(HERE, {1: foe(8, 0, left=1e9), 2: foe(12, 0, left=1e9)})  # nothing capped by the life left
    field = Field(None, None)
    sweep = LinePolicy(damage_of=flat)
    with pytest.raises(TypeError, match='a place is priced by an attack'):
        taken(seen, sweep, field, HERE, 0.0)
    with pytest.raises(TypeError, match='a place is priced by an attack'):
        camp(seen, sweep)
    # The attack made of the sweep on the build's side prices with the sweep's own numbers
    assert taken(seen, EchoingStrike.of(sweep), field, HERE, 0.0) == taken(seen, POLICY, field, HERE, 0.0)
    assert taken(seen, POLICY, field, HERE, 0.0) != taken(seen, EchoingStrike(), field, HERE, 0.0)
