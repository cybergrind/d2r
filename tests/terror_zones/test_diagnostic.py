import random

import pytest

from terror_zones.diagnostic import first_spawn, hazard, simulate_zone


def test_article_probability_example_and_negative_clamping():
    assert hazard(1, 70) == pytest.approx(0.017645254, abs=1e-8)
    assert hazard(1, 50) == 0
    assert hazard(2, 30) == 0


def test_depleted_cows_cannot_spawn_tier_two_in_article_model():
    result = first_spawn(511, 2, remaining=158)
    assert result['spawn_probability'] == 0
    assert result['conditional_mean_kills'] is None
    assert result['expected_kills_until_spawn_or_exhaustion'] == 158


def test_last_monster_roll_and_failure_mass_are_preserved():
    result = first_spawn(2, 5)
    p = hazard(5, 50)
    assert result['spawn_probability'] == pytest.approx(p)
    assert result['conditional_mean_kills'] == pytest.approx(2)
    assert result['expected_kills_until_spawn_or_exhaustion'] == 2


def test_simulation_matches_exact_first_spawn_probability():
    rng = random.Random(123)
    trials = 10000
    successes = sum(bool(simulate_zone(67, 1, rng)) for _ in range(trials))
    assert successes / trials == pytest.approx(first_spawn(67, 1)['spawn_probability'], abs=0.02)


def test_success_resets_progress_and_only_advances_one_tier():
    class LowestRoll(random.Random):
        def random(self) -> float:
            return 0.0

    events = simulate_zone(511, 1, LowestRoll())
    assert [tier for _, tier in events] == [1, 2]
    assert events[0][0] > 511 * 0.51
    assert events[1][0] - events[0][0] > 511 * 0.42


@pytest.mark.parametrize(('total', 'tier', 'remaining'), [(0, 1, None), (5, 6, None), (5, 1, 6), (5, 1, -1)])
def test_invalid_inputs(total, tier, remaining):
    with pytest.raises(ValueError, match='positive total'):
        first_spawn(total, tier, remaining)
