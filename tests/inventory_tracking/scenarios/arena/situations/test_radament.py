"""Radament in Sewers Level 3 (radament.py; rca/2026-10-22/walled-boss-findings.md §2): with the fixes off the route's
boss fight stands out of his stand-in's radius and he is seldom killed; with them on he is killed in every seed and the
character dies in none."""

import pytest

from tests.inventory_tracking.scenarios.arena.game import MANA_SHOWN
from tests.inventory_tracking.scenarios.arena.situations.radament import HOLDS, played, stored


def test_the_situation_holds_radament_still_shows_the_mana_and_plays_the_pursuit():
    situation = stored()
    assert situation.pursuit
    assert situation.speeds is not None
    assert situation.speeds[229] == HOLDS
    assert MANA_SHOWN in situation.rules
    assert situation.bosses == ((881231773, 'Radament'),)


@pytest.mark.slow
def test_off_the_fight_stalls_on_he_dies_in_every_seed_and_nobody_else_does():
    seeds = range(1, 21)
    off = [played(False, seed) for seed in seeds]
    on = [played(True, seed) for seed in seeds]
    assert sum(p.radament_at is not None for p in off) <= 4  # 2026-10-22: 2 of 24
    assert all(p.radament_at is not None for p in on)
    assert not any(p.dead for p in on)
