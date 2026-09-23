import random

import pytest

from terror_zones.routes import evaluate, simulate, zone_kernel


def test_no_population_can_produce_tier_five_before_progression():
    result = evaluate([('tiny', 1)], stop_after=3)
    assert result['mean_t5'] == 0
    assert result['mean_kills'] == 1
    assert result['probability_unlock_t5'] == 0


def test_stop_after_tier_four_differs_from_farming_its_leftovers():
    stop = zone_kernel(500, 4, 4)
    stay = zone_kernel(500, 4, 3)
    assert stop[1] == 0
    assert stay[1] > 0
    assert stay[0] > stop[0]
    assert sum(stay[2]) == pytest.approx(1)


def test_kill_by_kill_route_simulation_matches_exact_expectations():
    zones = [(str(i), n) for i, n in enumerate([67, 102, 113, 178, 199, 223, 501])]
    exact = evaluate(zones, stop_after=3)
    rng = random.Random(234)
    observations = [simulate(zones, 3, rng) for _ in range(3000)]
    assert sum(x[0] for x in observations) / len(observations) == pytest.approx(exact['mean_kills'], rel=0.02)
    assert sum(x[1] for x in observations) / len(observations) == pytest.approx(exact['mean_t5'], abs=0.08)


def test_tier_distribution_and_kills_are_conserved():
    for tier in range(1, 6):
        kills, t5, terminal = zone_kernel(100, tier, 3)
        assert sum(terminal) == pytest.approx(1)
        assert all(p >= 0 for p in terminal)
        assert 0 <= kills <= 100
        assert 0 <= t5 <= kills
        assert not any(terminal[: tier - 1])
