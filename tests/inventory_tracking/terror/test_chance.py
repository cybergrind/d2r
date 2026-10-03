"""Herald odds per the game code (D2R.exe, 2026-10-03; terror/plan.md item 6): level completion
= populated rooms share x kills / monsters spawned, the group's weighted mean, not floored,
minus the completion stored at the group's last Herald; each kill rolls after it is counted."""

import pytest

from inventory_tracking.terror.chance import Level, Odds, breakpoint, group_completion, odds
from terror_zones.diagnostic import hazard


def level(weight=1, *, killed=0, spawned=0, rooms=(0, None), prior=100):
    populated, total = rooms
    return Level(weight, killed=killed, spawned=spawned, populated=populated, rooms=total, prior=prior)


def test_level_completion_is_the_room_share_times_the_kill_share():
    # Half the rooms populated, 30 of the 60 monsters there dead: 0.5 x 0.5 = 25%.
    explored = level(killed=30, spawned=60, rooms=(20, 40))

    assert explored.completion() == pytest.approx(0.25)
    assert explored.population == 120  # the game's own extrapolation: 60 / 0.5
    assert group_completion([explored]) == pytest.approx(25.0)


def test_completion_is_not_floored():
    assert group_completion([level(killed=358, spawned=511, rooms=(40, 40))]) == pytest.approx(70.06, abs=0.01)


def test_a_level_without_room_data_or_monsters_falls_back_to_its_prior():
    assert level(killed=10, prior=100).completion() == pytest.approx(0.1)  # no room count
    assert level(killed=0, spawned=0, rooms=(5, 40), prior=80).population == 80  # rooms loaded, none seen
    assert level(spawned=0, rooms=(0, 40)).completion() == 0  # unvisited: no share yet
    assert level(killed=10, spawned=5, rooms=(40, 40)).population == 10  # never below the kills


CATACOMBS = (0.5, 1, 2, 2, 2, 1)  # Inner Cloister, Cathedral, Catacombs 1-4 (game zone_completion_weight)


def test_group_completion_is_the_weighted_mean_of_its_levels():
    # The article's example: Catacombs 2, 3 and 4 cleared = (2 + 2 + 1) / 8.5 = 58.8%.
    cleared = (0, 0, 0, 1, 1, 1)
    levels = [
        level(w, killed=50 * c, spawned=50 * c, rooms=(10 * c, 10)) for w, c in zip(CATACOMBS, cleared, strict=True)
    ]

    assert group_completion(levels) == pytest.approx(500 / 8.5)


@pytest.mark.parametrize(('tier', 'point'), [(1, 51.99), (2, 42.57), (3, 42.57), (4, 30.05), (5, 5.71)])
def test_breakpoint_is_where_the_curve_turns_positive(tier, point):
    assert breakpoint(tier) == pytest.approx(point, abs=0.01)
    assert hazard(tier, breakpoint(tier) - 0.01) == 0
    assert hazard(tier, breakpoint(tier) + 0.01) > 0


def test_each_kill_rolls_after_it_is_counted():
    # 51 of 100 dead: the next kill makes 52% and rolls there.
    result = odds(1, [level(killed=51, spawned=100, rooms=(10, 10))])

    assert result.completion == pytest.approx(51.0)
    assert result.next_kill == pytest.approx(hazard(1, 52))
    assert result.kills_to_breakpoint == 0


def test_chance_over_the_mobs_left_combines_each_kill_at_its_own_completion():
    result = odds(1, [level(killed=98, spawned=100, rooms=(10, 10))])

    assert result.remaining == 2
    assert result.over_remaining == pytest.approx(1 - (1 - hazard(1, 99)) * (1 - hazard(1, 100)))


def test_after_a_herald_progress_counts_from_the_completion_stored_then():
    # Tier 1 spawned at 55%; 75% now is 20% of progress for Tier 2, and clearing reaches 45%:
    # the kill that makes 98% (43% of progress) is the first past 42.57%.
    result = odds(2, [level(killed=75, spawned=100, rooms=(10, 10))], offset=55.0)

    assert result == Odds(
        tier=2,
        completion=pytest.approx(20.0),
        breakpoint=pytest.approx(42.57, abs=0.01),
        kills_to_breakpoint=22,
        reachable=pytest.approx(45.0),
        remaining=25,
        next_kill=0.0,
        over_remaining=pytest.approx(1 - (1 - hazard(2, 43)) * (1 - hazard(2, 44)) * (1 - hazard(2, 45))),
    )


def test_a_breakpoint_beyond_the_mobs_left_is_out_of_reach():
    result = odds(2, [level(killed=80, spawned=100, rooms=(10, 10))], offset=60.0)

    assert result.kills_to_breakpoint is None
    assert result.reachable == pytest.approx(40.0)


def test_kills_ahead_are_taken_in_the_current_level_first():
    # Two explored levels of 100, weight 3 and 1: 70 kills in the heavy one reach 52.5% (T1).
    heavy, light = level(3, spawned=100, rooms=(10, 10)), level(1, spawned=100, rooms=(10, 10))

    in_heavy = odds(1, [heavy, light], current=0)
    in_light = odds(1, [heavy, light], current=1)

    assert in_heavy.kills_to_breakpoint == 69  # the 70th kill rolls at 52.5%
    assert in_light.kills_to_breakpoint == 100 + 35  # 25% from the light level, then the 36th heavy kill: 52%
    assert in_heavy.over_remaining > in_light.over_remaining
    assert in_heavy.reachable == pytest.approx(100.0)
