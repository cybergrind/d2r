"""The input model (presses to casts) and the line-sweep policy (combat/sim/input.py, policy.py)."""

from itertools import pairwise

from inventory_tracking.combat.policy import Foe, virtual_cast
from inventory_tracking.combat.sim.input import BIRTH_LAG, CAST_FRAMES, casts_from_presses
from inventory_tracking.combat.sim.policy import FREE, SLOTS, YIELD, candidate, run_policy
from inventory_tracking.combat.sim.situation import CompanionTrack, MonsterTrack, Situation


def pointer(frame):
    return (5000.0 + frame, 5010.0)


def test_a_tap_casts_at_once_and_a_tap_during_the_cast_queues_one_more():
    casts = casts_from_presses([(10, True), (12, False), (15, True), (17, False)], pointer)
    assert [frame for frame, _ in casts] == [10 + BIRTH_LAG, 10 + CAST_FRAMES + BIRTH_LAG]
    assert casts[0][1] == pointer(9)  # the pointer one frame before the cast start


def test_a_held_button_casts_at_the_cadence_and_a_release_stops_it():
    casts = casts_from_presses([(0, True), (35, False)], pointer, end=60)
    assert [frame for frame, _ in casts] == [5, 14, 23, 32]  # every CAST_FRAMES; a release mid-cast queues nothing


def situation(*monsters, frames=200, modes=None, defiler=None):
    origin = (5000.0, 5000.0)
    player = dict.fromkeys(range(frames + 1), origin)
    companions = {9: CompanionTrack(9, 744, dict.fromkeys(range(frames + 1), defiler))} if defiler else {}
    sit = Situation(0, frames, 108, 2560 / 1418, player, {m.unit: m for m in monsters}, [], 0.0, companions)
    sit.modes = modes or {}
    return sit


def standing(unit, x, y, points=100_000.0, frames=200, txt=310):
    return MonsterTrack(unit, txt, points, dict.fromkeys(range(frames + 1), (x, y)), 1.0, None)


OFF = {'companions': {}, 'link': (0.0, 0, 0.0), 'explosion': (0.0, 0.0), 'mark': (0.0, 0), 'mana': (0.0, 0.0, 0.0)}


def flat(txt):
    return 1000.0


def test_the_policy_prefers_the_line_through_two_monsters_over_a_lone_one():
    lone = standing(1, 5012.0, 5000.0)
    first, second = standing(2, 5000.0, 5008.0), standing(3, 5000.0, 5016.0)
    sit = situation(lone, first, second, frames=BIRTH_LAG + 1)
    outcome = run_policy(sit, candidate(sit, FREE, damage_of=flat), **OFF)
    assert outcome.casts == 1
    frame, focal = outcome.cast_frames[0]
    assert frame == BIRTH_LAG
    assert abs(focal[0] - 5000.0) < 1e-6  # along the line through both
    assert focal[1] > 5008.0


def test_yield_mode_casts_only_when_the_recorded_character_stood_still():
    target = standing(1, 5000.0, 5010.0)
    modes = dict.fromkeys(range(50), 3) | dict.fromkeys(range(50, 201), 1)
    sit = situation(target, modes=modes)
    casts = run_policy(sit, candidate(sit, YIELD, damage_of=flat), **OFF).cast_frames
    assert casts
    assert min(frame for frame, _ in casts) == 50 + BIRTH_LAG
    free = run_policy(sit, candidate(sit, FREE, damage_of=flat), **OFF).cast_frames
    assert min(frame for frame, _ in free) == BIRTH_LAG
    assert len(free) > len(casts)
    births = [frame for frame, _ in free]
    assert [b - a for a, b in pairwise(births)][:3] == [CAST_FRAMES] * 3


def test_slots_mode_casts_exactly_when_the_record_did_with_the_policy_aim():
    from inventory_tracking.combat.sim.situation import Cast

    target = standing(1, 5000.0, 5010.0)
    sit = situation(target)
    sit.casts = [Cast(30, (5020.0, 5020.0), (5020.0, 5020.0)), Cast(80, None, (5020.0, 5020.0))]  # aimed elsewhere
    casts = run_policy(sit, candidate(sit, SLOTS, damage_of=flat), **OFF).cast_frames
    assert [frame for frame, _ in casts] == [30, 80]
    assert all(abs(focal[0] - 5000.0) < 1e-6 for _, focal in casts)  # re-aimed through the monster


def test_a_virtual_cast_caps_each_contact_by_the_points_left_and_spreads_through_the_link():
    monsters = {1: Foe(310, (5000.0, 5010.0), 100_000.0), 2: Foe(310, (5030.0, 5000.0), 100_000.0)}
    plain = virtual_cast((5000.0, 5000.0), (5000.0, 5010.0), monsters, set(), 0.5, flat)
    linked = virtual_cast((5000.0, 5000.0), (5000.0, 5010.0), monsters, {1, 2}, 0.5, flat)
    assert plain == 1000.0 * (1 + 4 * 0.1) * 2
    assert linked == plain * 1.5
    nearly_dead = {1: Foe(310, (5000.0, 5010.0), 150.0), 2: Foe(310, (5030.0, 5000.0), 100_000.0)}
    assert (
        virtual_cast((5000.0, 5000.0), (5000.0, 5010.0), nearly_dead, set(), 0.5, flat) == 150.0
    )  # no overkill credit
    assert (
        virtual_cast((5000.0, 5000.0), (5000.0, 5010.0), nearly_dead, {1, 2}, 0.5, flat) == 150.0 + 500.0
    )  # the duplicates find a corpse


def test_the_policy_spends_mana_and_waits_when_the_pool_is_empty():
    target = standing(1, 5000.0, 5010.0)
    sit = situation(target, frames=100)
    options = dict(OFF, mana=(26.0, 0.0, 13.0))  # two casts' worth, no regeneration
    outcome = run_policy(sit, candidate(sit, FREE, damage_of=flat), **options)
    assert outcome.casts == 2
    assert outcome.casts_refused > 0
    assert outcome.mana_low == 0.0
    regen = dict(OFF, mana=(26.0, 13.0 / 20, 13.0))  # a cast's worth every 20 frames
    assert run_policy(sit, candidate(sit, FREE, damage_of=flat), **regen).casts > 2


def test_the_fitted_mana_regeneration_is_the_least_that_keeps_the_recorded_casts_affordable():
    from inventory_tracking.combat.sim.engine import fitted_mana
    from inventory_tracking.combat.sim.situation import Cast

    sit = situation(standing(1, 5000.0, 5010.0), frames=300)
    sit.casts = [Cast(BIRTH_LAG + 10 * k, None, (5000.0, 5010.0)) for k in range(10)]  # ten casts, one every 10 frames
    pool, regen, cost = fitted_mana(sit, 26.0, 13.0)
    assert (pool, cost) == (26.0, 13.0)
    # Two casts come from the pool; the eight others (104 points) must regenerate over the 90 frames to the last one.
    assert abs(regen - 104.0 / 90) < 1e-9
    assert fitted_mana(sit, 1000.0, 13.0)[1] == 0.0  # the pool alone pays for them
