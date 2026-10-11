"""The incoming-damage model itself (harness.py): its few rules, and that `today` is the game's decision."""

import math

import pytest

from inventory_tracking.combat.controller import aim_choice
from inventory_tracking.combat.mechanics.damage import damage_table
from inventory_tracking.combat.policy import DUPLICATE, LinePolicy, observe
from tests.inventory_tracking.scenarios.threat.harness import (
    BLAST,
    LIFE,
    MELEE_REACH,
    ORIGIN,
    RUN,
    TICKS,
    Cast,
    Move,
    Scene,
    View,
    hostile,
    in_reach,
    leave,
    order,
    records,
    run,
    today,
)
from tests.inventory_tracking.scenarios.threat.table import TERROR_LEVEL, base_damage


HELL_BOVINE, GLOAM, GHOST, UNDEAD_SOUL_KILLER, VENOM_LORD = 391, 118, 631, 691, 362


def test_today_is_the_line_the_games_policy_picks_over_the_memory_records():
    scene = Scene(
        'two lines',
        39,
        [hostile(1, HELL_BOVINE, 12.0, 0.0), hostile(2, HELL_BOVINE, 0.0, 8.0), hostile(3, HELL_BOVINE, 0.0, 16.0)],
    )
    player, monsters = records(scene)
    choice = aim_choice(LinePolicy(), observe(player, monsters, ()), in_reach(scene))
    assert choice is not None
    assert today(View(scene, LIFE, True, 0)) == Cast(choice.focal, choice.unit)
    assert choice.unit in (2, 3)  # the line through two
    assert today(View(scene, LIFE, False, 0)) is None  # mid cast


def test_a_ranged_monster_hurts_from_where_it_stands_and_a_melee_one_only_in_contact():
    still = lambda view: None  # noqa: E731
    gloam = run(Scene('gloam', 77, [hostile(1, GLOAM, 20.0, 0.0)]), still, TICKS)
    assert gloam.taken == pytest.approx(1.9 * 0.25 * 5.0 * base_damage(TERROR_LEVEL))  # a second of its rate
    cow = run(Scene('cow', 39, [hostile(1, HELL_BOVINE, 14.0, 0.0)]), still, 4 * TICKS)
    arrival = math.ceil((14.0 - MELEE_REACH) / (5 * 1.1) * TICKS)  # monstats speed 5
    assert cow.taken_by(arrival - 2) == 0
    assert cow.taken == pytest.approx((4 * TICKS - arrival) / TICKS * 1.8 * base_damage(TERROR_LEVEL), rel=0.05)


def test_a_cast_takes_the_emulated_blades_points_and_nothing_off_an_immune_monster():
    scene = Scene('cow and ghost', 124, [hostile(1, VENOM_LORD, 10.0, 0.0), hostile(2, GHOST, 0.0, 10.0)])
    lord = scene.hostiles[0]
    casts = math.ceil(lord.full / (2 * (1 + 4 * DUPLICATE) * damage_table()(VENOM_LORD)))  # five blades out and back
    assert run(scene, order(1), 9 * (casts - 1)).kills == []
    assert run(scene, order(1), 9 * (casts - 1) + 1).kills == [1]
    ghost = run(scene, order(2), 10 * TICKS)
    assert 2 not in ghost.kills
    assert len(ghost.casts) > 20


def test_a_corpse_explodes_on_the_character_only_within_its_radius():
    near = run(Scene('near', 131, [hostile(1, UNDEAD_SOUL_KILLER, 1.5, 0.0)]), today, 1)
    far = run(Scene('far', 131, [hostile(1, UNDEAD_SOUL_KILLER, 8.0, 0.0)]), today, 1)
    assert (near.kills, near.blasts) == ([1], BLAST)
    assert (far.kills, far.blasts) == ([1], 0.0)


def test_the_character_runs_at_its_recorded_speed_and_does_not_cast_meanwhile():
    scene = Scene('cow', 39, [hostile(1, HELL_BOVINE, 6.0, 0.0)])
    gone = run(scene, lambda view: Move((ORIGIN[0] - 100.0, ORIGIN[1])), TICKS)
    assert gone.moved == pytest.approx(RUN)
    assert gone.casts == []
    assert run(scene, leave, 3 * TICKS).taken == 0  # a Hell Bovine never catches a running character


def test_the_death_is_the_tick_the_damage_reaches_the_life_and_the_count_goes_on():
    scene = Scene('gloams', 77, [hostile(n, GLOAM, 20.0, float(n)) for n in range(4)], life=500.0)
    result = run(scene, lambda view: None, 2 * TICKS)
    assert result.dead_at == math.ceil(500.0 / (4 * 1.9 * 0.25 * 5.0 * base_damage(TERROR_LEVEL)) * TICKS) - 1
    assert result.taken > 500.0
    assert not result.alive
