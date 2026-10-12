"""Echoing Strike as the build's attack (builds/warlock/echoing_strike/attack.py): the contract's five
answers, and that a place priced through it is priced as the line sweep was priced before it."""

import math
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.builds.warlock.echoing_strike.attack import (
    BLADES_A_CAST,
    ECHOING_STRIKE_ATTACK,
    REACH,
    EchoingStrike,
    LinePolicy,
)
from inventory_tracking.builds.warlock.echoing_strike.damage import link_table
from inventory_tracking.builds.warlock.echoing_strike.hits import CONTACT_RADIUS
from inventory_tracking.builds.warlock.skills import ECHOING_STRIKE
from inventory_tracking.combat import stance
from inventory_tracking.combat.policy import MIN_SCORE, Foe, Observation
from inventory_tracking.macros.world import Monster
from tests.inventory_tracking.scenarios.stance import harness


HERE = (5000.0, 5000.0)
FIXTURES = sorted((Path(harness.__file__).parent / 'fixtures').glob('*.json'))


def flat(txt):
    return 1000.0


ATTACK = EchoingStrike(damage_of=flat)


def foe(dx, dy, left=5000.0, elite=False):
    return Foe(310, (HERE[0] + dx, HERE[1] + dy), left, elite)


def test_it_holds_echoing_strike_and_reaches_as_far_as_the_blades_fly():
    assert ECHOING_STRIKE_ATTACK.skill == ECHOING_STRIKE
    assert ECHOING_STRIKE_ATTACK.reach == REACH


def test_the_attack_of_a_sweep_made_on_its_own_keeps_its_numbers():
    sweep = LinePolicy(yields=False, reach=18.0, damage_of=flat, elite_weight=3.0, lead=4)
    attack = EchoingStrike.of(sweep)
    assert isinstance(attack, EchoingStrike)
    assert (attack.yields, attack.reach, attack.damage_of, attack.elite_weight, attack.lead) == (
        False, 18.0, flat, 3.0, 4,
    )  # fmt: skip
    assert attack.offsets == sweep.offsets
    assert attack.skill == ECHOING_STRIKE


# --- sees ---


def test_it_sees_the_monsters_the_defilers_link_holds_in_a_copy():
    seen = Observation(HERE, {10: foe(8, 0), 11: foe(0, 10), 12: foe(400, 0)}, moving=True, frame=3)
    defiler = Monster(20, 744, 1, 5002.0, 5002.0, 1, ally=True)
    other = Monster(21, 419, 1, 5400.0, 5000.0, 1, ally=True)  # a companion that is no Defiler holds no link
    found = ECHOING_STRIKE_ATTACK.sees(seen, [defiler, other])
    assert found is not seen
    assert (found.linked, found.share) == (frozenset({10, 11}), link_table()[2])
    assert (seen.linked, seen.share) == (frozenset(), 0.0)  # the one given is not changed
    assert replace(found, linked=frozenset(), share=0.0) == seen  # and nothing else differs


def test_without_a_defiler_nothing_is_linked():
    seen = Observation(HERE, {10: foe(8, 0)})
    found = ECHOING_STRIKE_ATTACK.sees(seen, [])
    assert found is not seen
    assert (found.linked, found.share) == (frozenset(), link_table()[2])


# --- aim ---


def test_the_aim_is_the_sweeps_line():
    seen = Observation(HERE, {1: foe(8, 0), 2: foe(0, 9), 3: foe(0, 15)})
    assert ATTACK.aim(seen) == LinePolicy(damage_of=flat)(seen)
    assert ATTACK.aim(seen).unit in (2, 3)  # two on one line are worth more than the lone one


def test_the_aim_through_named_units_is_the_best_line_laid_through_one_of_them():
    seen = Observation(HERE, {1: foe(8, 0), 2: foe(0, 9), 3: foe(0, 15)})
    through = ATTACK.aim(seen, through=[1])
    assert through == LinePolicy(damage_of=flat).choose(seen, through=[1])
    assert through is not None
    assert through.unit == 1
    assert through.worth < ATTACK.aim(seen).worth  # taken whatever another line is worth
    assert ATTACK.aim(seen, through=[99]) is None


def test_it_yields_to_a_moving_player_with_and_without_named_units():
    moving = Observation(HERE, {1: foe(8, 0)}, moving=True)
    assert ATTACK.aim(moving) is None
    assert ATTACK.aim(moving, through=[1]) is None
    free = EchoingStrike(yields=False, damage_of=flat)
    assert free.aim(moving) is not None
    assert free.aim(moving, through=[1]) is not None


def test_a_line_worth_less_than_the_least_score_is_no_cast():
    weak = EchoingStrike(damage_of=lambda txt: MIN_SCORE / 10)
    seen = Observation(HERE, {1: foe(8, 0)})
    assert weak.choose(seen) is not None
    assert weak.aim(seen) is None
    assert weak.aim(seen, through=[1]) is None


# --- dealt ---


def test_a_cast_takes_the_blades_of_one_cast_off_every_monster_on_its_line():
    foes = {1: foe(8, 0), 2: foe(15, CONTACT_RADIUS), 3: foe(15, CONTACT_RADIUS + 0.5), 4: foe(-8, 0), 5: foe(0, 9)}
    dealt = ATTACK.dealt(HERE, (5008.0, 5000.0), foes)
    # 1 on the focal point, 2 further along within the contact radius; 3 off the line, 4 behind, 5 aside
    assert dealt == {1: 1000.0 * BLADES_A_CAST, 2: 1000.0 * BLADES_A_CAST}


def test_what_is_dealt_is_not_capped_by_the_life_left_nor_weighted_for_an_elite():
    foes = {1: foe(8, 0, left=10.0), 2: foe(12, 0, elite=True)}
    assert ATTACK.dealt(HERE, (5008.0, 5000.0), foes) == {1: 2800.0, 2: 2800.0}


def test_the_line_goes_on_past_the_focal_point_and_starts_at_the_character():
    foes = {1: foe(20, 0)}
    assert ATTACK.dealt(HERE, (5004.0, 5000.0), foes) == {1: 2800.0}
    assert ATTACK.dealt(HERE, HERE, foes) == {}  # a focal point under the character is no line
    assert ATTACK.dealt(HERE, (5004.0, 5000.0), {1: Foe(310, HERE, 100.0)}) == {}  # nor is a monster on it ahead
    assert ATTACK.dealt(HERE, (5004.0, 5000.0), {}) == {}


def test_each_monster_takes_by_its_own_type():
    by_type = EchoingStrike(damage_of=lambda txt: float(txt))
    foes = {1: Foe(10, (5008.0, 5000.0), 100.0), 2: Foe(20, (5012.0, 5000.0), 100.0)}
    assert by_type.dealt(HERE, (5008.0, 5000.0), foes) == {1: 10.0 * BLADES_A_CAST, 2: 20.0 * BLADES_A_CAST}


# --- a place priced through the attack is priced as before ---


def old_taken(seen, policy, field, spot, after):
    """combat/stance.py `taken` as it was before the attack was the build's (commit bdda973), kept
    here word for word as the number to match: the line model and BLADES_A_CAST inside the framework,
    the elite's weight the policy's."""
    near = []
    for unit, foe in seen.foes.items():
        dx, dy = foe.at[0] - spot[0], foe.at[1] - spot[1]
        away = math.hypot(dx, dy)
        if 0 < away <= policy.reach and field.clear(spot, foe.at):
            near.append((unit, foe, dx, dy, away))
    if not near:
        return 0.0, 0
    lines = []
    for _, _, tx, ty, away in near:
        ux, uy = tx / away, ty / away
        lines.append(
            [
                k
                for k, (_, _, dx, dy, _) in enumerate(near)
                if dx * ux + dy * uy > 0 and abs(dx * uy - dy * ux) <= CONTACT_RADIUS
            ]
        )
    left = [foe.left for _, foe, *_ in near]
    blow = [policy.damage_of(foe.txt) * 2.8 for _, foe, *_ in near]
    weight = [policy.elite_weight if foe.elite else 1.0 for _, foe, *_ in near]
    clock, casts, total = after, 0, 0.0
    done = False
    while clock + stance.CAST_SECONDS <= stance.HORIZON:
        best, line = 0.0, None
        for on in lines:
            points = sum(min(blow[k], left[k]) * weight[k] for k in on if left[k] > 0)
            if points > best:
                best, line = points, on
        if line is None:
            done = True
            break
        clock += stance.CAST_SECONDS
        casts += 1
        total += best
        for k in line:
            left[k] = max(0.0, left[k] - blow[k])
    done = done or not any(points > 0 for points in left)
    return total * (1 + (stance.HORIZON - clock) / stance.HORIZON if done else 1.0), casts if done else 0


def observed(scene: harness.Scene) -> Observation:
    """The fixture's first look, as the stance harness gives it to a strategy (`harness.play`)."""
    foes = {b.unit: Foe(b.txt, b.at, b.points * b.life, b.elite) for b in scene.bodies}
    return Observation(scene.origin, foes, blocked=scene.blocked)


def spots(origin):
    """The places `camp` looks at from `origin`, and the origin itself."""
    count = int(stance.CAMP_REACH // stance.CAMP_GRID)
    yield origin
    for i in range(-count, count + 1):
        for j in range(-count, count + 1):
            yield (
                math.floor(origin[0]) + i * stance.CAMP_GRID + 0.5,
                math.floor(origin[1]) + j * stance.CAMP_GRID + 0.5,
            )


def test_the_fixtures_are_all_there():
    assert len(FIXTURES) == 39


@pytest.mark.parametrize('path', FIXTURES, ids=lambda path: path.stem)
def test_a_place_is_worth_through_the_attack_what_it_was_worth_through_the_sweep(path):
    scene = harness.load(path)
    seen = observed(scene)
    sweep = LinePolicy(yields=True)
    field = stance.Field(seen.blocked, scene.barred)
    priced = 0
    for spot in spots(seen.origin):
        for after in (0.0, 0.8, 1.5):
            before = old_taken(seen, sweep, field, spot, after)
            assert stance.taken(seen, ECHOING_STRIKE_ATTACK, field, spot, after) == before  # the build's attack
            priced += before[0] > 0
    assert priced or not seen.foes


@pytest.mark.parametrize('path', FIXTURES, ids=lambda path: path.stem)
def test_the_place_chosen_through_the_attack_is_the_one_the_sweep_chose(path, monkeypatch):
    scene = harness.load(path)
    seen = observed(scene)
    sweep = LinePolicy(yields=True)
    ways = [{}, {'hop': True}, {'jumps': (stance.Jump(1, 0.8, 30.0, 26.0, 8.0, True),)}, {'gain': 2.0}]
    now = [stance.camp(seen, ECHOING_STRIKE_ATTACK, scene.barred, **way) for way in ways]
    monkeypatch.setattr(stance, 'taken', old_taken)  # `camp` as it is, over the old price of a place
    for by_attack, way in zip(now, ways, strict=True):
        # the sweep as an attack only to get past `striker`: the old price asks it as the sweep it is
        assert by_attack == stance.camp(seen, EchoingStrike.of(sweep), scene.barred, **way)


def test_some_fixture_has_a_place_worth_going_to():
    found = [stance.camp(observed(harness.load(path)), ECHOING_STRIKE_ATTACK) for path in FIXTURES]
    assert any(place is not None for place in found)
