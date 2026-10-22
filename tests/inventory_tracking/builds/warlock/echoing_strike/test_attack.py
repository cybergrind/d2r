"""Echoing Strike as the build's attack (builds/warlock/echoing_strike/attack.py): the contract's five
answers, and that a place priced through it is priced as the line sweep was priced before it."""

import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

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
from inventory_tracking.builds.warlock.echoing_strike.mechanics import OUT_FRAMES, cast
from inventory_tracking.builds.warlock.skills import ECHOING_STRIKE
from inventory_tracking.combat import stance
from inventory_tracking.combat.policy import MIN_SCORE, Choice, Foe, Observation
from inventory_tracking.game.records import Monster
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
    aimed = ATTACK.aim(seen)
    assert aimed is not None
    assert aimed.unit in (2, 3)  # two on one line are worth more than the lone one


def test_the_aim_through_named_units_is_the_best_line_laid_through_one_of_them():
    seen = Observation(HERE, {1: foe(8, 0), 2: foe(0, 9), 3: foe(0, 15)})
    through = ATTACK.aim(seen, through=[1])
    assert through == LinePolicy(damage_of=flat).choose(seen, through=[1])
    assert through is not None
    assert through.unit == 1
    best = ATTACK.aim(seen)
    assert best is not None
    assert through.worth < best.worth  # taken whatever another line is worth
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


def wall_at(x):
    """A wall across the aim line `x` units ahead of the character and on (run-2040-findings.md §3.2: blades flew
    8-10 units into a wall at 10.5 in the Outer Steppes)."""
    return lambda point: point[0] >= HERE[0] + x


def test_a_wall_stops_the_blades_who_is_past_it_takes_nothing_and_who_is_before_it_only_the_way_out():
    foes = {1: foe(6, 0), 2: foe(15, 0)}
    free = ATTACK.dealt(HERE, (5006.0, 5000.0), foes)
    walled = ATTACK.dealt(HERE, (5006.0, 5000.0), foes, blocked=wall_at(10.5))
    assert free == {1: 2800.0, 2: 2800.0}
    # the blades die in the wall on the way out: no way back (mechanics.py `cast`, missiles.txt CollideType 3)
    assert walled == {1: 1000.0 * BLADES_A_CAST / 2}


def test_a_wall_behind_the_character_or_beside_the_line_stops_nothing():
    foes = {1: foe(6, 0), 2: foe(15, 0)}
    behind = ATTACK.dealt(HERE, (5006.0, 5000.0), foes, blocked=lambda point: point[0] <= HERE[0] - 2.0)
    beside = ATTACK.dealt(HERE, (5006.0, 5000.0), foes, blocked=lambda point: point[1] >= HERE[1] + 4.0)
    assert behind == beside == {1: 2800.0, 2: 2800.0}


def test_a_place_whose_casts_fly_into_a_wall_is_worth_less_than_one_whose_blades_come_back():
    # The same monsters six units off: from one place a wall stands 10.5 units on along the line, from the other
    # the blades fly free; the line model credited both the same (run-2040-findings.md §3.3 fix 1).
    pack = {1: foe(6, 0, left=30000.0), 2: foe(6, 30, left=30000.0)}
    seen = Observation(HERE, pack, blocked=lambda point: point[0] >= HERE[0] + 10.5 and point[1] < HERE[1] + 20)
    field = stance.Field(seen.blocked, None)
    walled, _ = stance.taken(seen, ATTACK, field, HERE, 0.0)
    free, _ = stance.taken(seen, ATTACK, field, (HERE[0], HERE[1] + 30.0), 0.0)
    assert walled == pytest.approx(free / 2)
    # the sweep of the pursuit loop off keeps the line model its goldens were recorded with
    assert stance.taken(seen, ATTACK, field, HERE, 0.0, walls=False)[0] == free
    one = replace(seen, foes={1: foe(6, 0, left=5000.0)})
    late = stance.falls(one, ATTACK, field, HERE, 0.0, 10.0)
    soon = stance.falls(one, ATTACK, stance.Field(None, None), HERE, 0.0, 10.0)
    assert late[1] > soon[1]  # four casts of the way out against two out and back


def test_the_casts_land_less_often_toward_the_end_of_the_reach_and_the_engage_ring_is_where_they_fall_off():
    # run-1932-findings.md §4.1: 74-75% of the aimed casts hit within 10 units, 36% at 18-22
    assert ECHOING_STRIKE_ATTACK.lands(4.0) == pytest.approx(1.0, abs=0.01)
    assert ECHOING_STRIKE_ATTACK.lands(9.0) == pytest.approx(1.0, abs=0.05)
    shares = [ECHOING_STRIKE_ATTACK.lands(away) for away in (10.0, 12.0, 14.0, 16.0, 18.0, 20.0, REACH)]
    assert shares == sorted(shares, reverse=True)
    assert ECHOING_STRIKE_ATTACK.lands(REACH) == pytest.approx(0.356 / 0.747, abs=0.01)
    assert 12.0 <= ECHOING_STRIKE_ATTACK.engage <= 14.0  # where the player engages (combat/policy.py)
    assert ECHOING_STRIKE_ATTACK.engage < REACH - 3.0  # inside the ring the approaches planned before (17)


def test_a_place_near_a_clump_is_worth_more_than_one_at_the_edge_of_the_reach():
    # The 22:50:26.9 clump of run-1932 (Bone Mages and Yetis 17 to 22 units off): the same pack, more than the
    # horizon's casts kill, is worth more from 12 units, where the casts land, than from 20, where a third hit nothing
    pack = {unit: Foe(310, (HERE[0] + 20.0 + dx, HERE[1] + dy), 30000.0) for unit, (dx, dy) in
            enumerate(((0, 0), (1.5, 1.0), (-1.0, 1.5), (2.0, -1.5), (0.5, -2.0)))}  # fmt: skip
    seen = Observation(HERE, pack)
    field = stance.Field(None, None)
    far, _ = stance.taken(seen, ATTACK, field, HERE, 0.0, landed=True)
    near, _ = stance.taken(seen, ATTACK, field, (HERE[0] + 8.0, HERE[1]), 0.0, landed=True)
    assert near > 1.5 * far
    # not asked to (the sweep of the pursuit loop off): every cast lands, as the line model had it
    plain = (
        stance.taken(seen, ATTACK, field, HERE, 0.0),
        stance.taken(seen, ATTACK, field, (HERE[0] + 8.0, HERE[1]), 0.0),
    )
    assert plain[0][0] == plain[1][0]


def test_each_monster_takes_by_its_own_type():
    by_type = EchoingStrike(damage_of=lambda txt: float(txt))
    foes = {1: Foe(10, (5008.0, 5000.0), 100.0), 2: Foe(20, (5012.0, 5000.0), 100.0)}
    assert by_type.dealt(HERE, (5008.0, 5000.0), foes) == {1: 10.0 * BLADES_A_CAST, 2: 20.0 * BLADES_A_CAST}


# --- a place priced through the attack is priced as before ---


def old_taken(seen, policy, field, spot, after, *, landed=False, walls=True):
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


@dataclass
class BladesThroughWalls(EchoingStrike):
    """The build's attack as it was priced before its blades stopped at walls (run-2040-findings.md §3.3 fix 1):
    the line model the sweep had, against which the rest of the model is held."""

    def dealt(self, origin, focal, foes, blocked=None):
        return super().dealt(origin, focal, foes)


THROUGH_WALLS = BladesThroughWalls()


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
            assert stance.taken(seen, THROUGH_WALLS, field, spot, after) == before  # the build's line model
            priced += before[0] > 0
    assert priced or not seen.foes


@pytest.mark.parametrize('path', FIXTURES, ids=lambda path: path.stem)
def test_the_place_chosen_through_the_attack_is_the_one_the_sweep_chose(path, monkeypatch):
    scene = harness.load(path)
    seen = observed(scene)
    sweep = LinePolicy(yields=True)
    ways: list[dict[str, Any]] = [
        {},
        {'hop': True},
        {'jumps': (stance.Jump(1, 0.8, 30.0, 26.0, 8.0, True),)},
        {'gain': 2.0},
    ]
    now = [stance.camp(seen, THROUGH_WALLS, scene.barred, **way) for way in ways]
    monkeypatch.setattr(stance, 'taken', old_taken)  # `camp` as it is, over the old price of a place
    for by_attack, way in zip(now, ways, strict=True):
        # the sweep as an attack only to get past `striker`: the old price asks it as the sweep it is
        assert by_attack == stance.camp(seen, EchoingStrike.of(sweep), scene.barred, **way)


def test_the_recorded_places_are_priced_with_the_blades_stopping_at_their_walls():
    # The stance fixtures' Catacombs and Sanctuary rooms: from most of the places `camp` looks at, some line ends
    # in a wall, and the build's attack prices it so.
    changed = 0
    for path in FIXTURES:
        seen = observed(scene := harness.load(path))
        field = stance.Field(seen.blocked, scene.barred)
        changed += any(
            stance.taken(seen, ECHOING_STRIKE_ATTACK, field, spot, 0.0)
            != stance.taken(seen, THROUGH_WALLS, field, spot, 0.0)
            for spot in spots(seen.origin)
        )
    assert changed >= len(FIXTURES) // 2


def test_some_fixture_has_a_place_worth_going_to():
    found = [stance.camp(observed(harness.load(path)), ECHOING_STRIKE_ATTACK) for path in FIXTURES]
    assert any(place is not None for place in found)


# The player, 2026-10-20 ~15:04: "and overall aim against moving enemies was pretty bad. probably we need to do some
# smart targeting against moving enemies". attack.py LEAD_MOVING: the lines laid where the monsters' velocities have
# them as the blades fly (rca/2026-10-20/leader-not-marked-findings.md, "Moving monsters").


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def tracked(clock, *places_by_look, unit=1):
    """An attack whose motion has seen `unit` at each place, one look every 0.2 s."""
    from inventory_tracking.builds.warlock.echoing_strike.attack import Motion

    attack = EchoingStrike(damage_of=flat, motion=Motion(clock=clock))
    for place in places_by_look:
        attack.motion.note({unit: Foe(310, place, 5000.0)})
        clock.now += 0.2
    clock.now -= 0.2
    return attack


def test_a_standing_monster_gets_no_lead():
    clock = Clock()
    attack = tracked(clock, (5015.0, 5000.0), (5015.0, 5000.0), (5015.1, 5000.0))  # 0.25 units a second
    assert attack.motion.route(1, (5015.1, 5000.0)) is None
    assert tracked(Clock(), (5015.0, 5000.0)).motion.route(1, (5015.0, 5000.0)) is None  # one look: no velocity


def test_a_walking_monster_is_led_by_its_velocity_times_the_frames_to_come():
    from inventory_tracking.takes.timeline import GAME_RATE

    clock = Clock()
    attack = tracked(clock, (5015.0, 4996.0), (5015.0, 4996.8))  # 4 units a second across the line
    velocity = attack.motion.velocity(1)
    assert velocity is not None
    assert velocity == pytest.approx((0.0, 4.0))
    route = attack.motion.route(1, (5015.0, 4996.8))
    assert route is not None
    frames = 17  # the blades' first frame (LIVE_LEAD) and their flight to it
    assert route.after((5015.0, 4996.8), frames) == pytest.approx((5015.0, 4996.8 + 4.0 / GAME_RATE * frames))
    # A sample older than MOTION_SECONDS is forgotten: a unit unseen that long has no velocity
    clock.now += 1.0
    attack.motion.note({})
    assert attack.motion.velocity(1) is None


def test_the_lead_is_capped_in_speed_and_in_length():
    from inventory_tracking.builds.warlock.echoing_strike.attack import LEAD_MOST, MOST_SPEED

    clock = Clock()
    attack = tracked(clock, (5010.0, 5000.0), (5018.0, 5000.0))  # 40 units a second: a misread
    assert attack.motion.velocity(1) == pytest.approx((MOST_SPEED, 0.0))
    route = attack.motion.route(1, (5018.0, 5000.0))
    assert route is not None
    assert route.after((5018.0, 5000.0), 1000) == pytest.approx((5018.0 + LEAD_MOST, 5000.0))  # turns drag no further


def test_with_lead_moving_the_line_goes_through_where_the_monster_will_be(monkeypatch):
    from inventory_tracking.builds.warlock.echoing_strike import attack as module

    clock = Clock()
    attack = tracked(clock, (5015.0, 4995.0), (5015.0, 4996.0))  # 5 units a second across the line
    seen = Observation(HERE, {1: Foe(310, (5015.0, 4996.0), 5000.0)})
    monkeypatch.setattr(module, 'LEAD_MOVING', False)
    standing = attack.aim(attack.sees(seen, []))
    assert standing is not None
    assert math.atan2(standing.focal[1] - HERE[1], standing.focal[0] - HERE[0]) == pytest.approx(
        math.atan2(-4.0, 15.0), abs=0.01
    )
    monkeypatch.setattr(module, 'LEAD_MOVING', True)
    looked = attack.sees(seen, [])
    route = looked.foes[1].route
    assert route is not None
    led = attack.aim(looked)
    assert led is not None
    away = math.dist(HERE, (5015.0, 4996.0))
    frames = module.LIVE_LEAD + min(round(away / module.SPEED), module.OUT_FRAMES)
    ahead = route.after((5015.0, 4996.0), frames)
    bearing = math.atan2(ahead[1] - HERE[1], ahead[0] - HERE[0])
    assert math.atan2(led.focal[1] - HERE[1], led.focal[0] - HERE[0]) == pytest.approx(bearing, abs=0.01)
    assert seen.foes[1].route is None  # the look's own observation is left as it was


def test_with_lead_moving_a_line_is_worth_what_it_takes_off_every_monster_where_it_will_be(monkeypatch):
    from inventory_tracking.builds.warlock.echoing_strike import attack as module

    monkeypatch.setattr(module, 'LEAD_MOVING', True)
    clock = Clock()
    attack = tracked(clock, (5015.0, 4994.8), (5015.0, 4996.0), unit=2)  # 6 units a second toward the line
    standing, walking = Foe(310, (5015.0, 5000.0), 5000.0), Foe(310, (5015.0, 4996.0), 5000.0)
    attack.motion.note({1: standing})
    seen = attack.sees(Observation(HERE, {1: standing, 2: walking}), [])
    assert seen.foes[1].route is None
    assert seen.foes[2].route is not None
    through = attack.choose(seen, through={1})
    assert through is not None
    # The walker crosses the line through the standing one as the blades fly: both are on it
    assert through.worth > 1.5 * BLADES_A_CAST * 1000.0
    monkeypatch.setattr(module, 'LEAD_MOVING', False)
    unled = attack.choose(Observation(HERE, {1: standing, 2: walking}), through={1})
    assert unled is not None
    assert unled.worth < through.worth


# The leader focus (the player, 2026-10-20: "pack leader/herald first"): a line laid through a leader worth
# `LinePolicy.focus` of the best line is cast instead of it. These play HOLD_LEADER off (the share rule they pin;
# the hold's own tests follow them).
@pytest.fixture
def no_hold(monkeypatch):
    from inventory_tracking.builds.warlock.echoing_strike import attack

    monkeypatch.setattr(attack, 'HOLD_LEADER', False)


def pack_and_leader(beside: bool) -> Observation:
    """Three minions on one bearing (one line takes all three) and a leader on another, alone or with one beside it."""
    foes = {1: foe(8.0, 0.0), 2: foe(10.0, 0.0), 3: foe(12.0, 0.0), 9: foe(0.0, 10.0, elite=True)}
    if beside:
        foes[4] = foe(0.0, 12.0)
    return Observation(HERE, foes)


def aimed(attack: EchoingStrike, seen: Observation) -> Choice:
    found = attack.aim(seen)
    assert found is not None
    return found


def test_with_no_focus_the_best_line_goes_through_the_pack_not_its_leader(no_hold):
    assert aimed(ATTACK, pack_and_leader(beside=True)).unit in {1, 2, 3}


def test_with_the_focus_a_line_through_the_leader_worth_its_share_of_the_best_is_cast_instead(no_hold):
    focused = replace(ATTACK, focus=0.85)
    # The leader and one beside it: 2 x 2,800 x ELITE_WEIGHT + 2,800 against the pack's 3 x 2,800: more than 85%
    seen = pack_and_leader(beside=True)
    best = aimed(ATTACK, seen)
    found = aimed(focused, seen)
    assert found.unit == 9
    assert found.worth >= 0.85 * best.worth
    # The leader alone: 2 x 2,800 against 8,400, 67%: the pack's line stands
    assert aimed(focused, pack_and_leader(beside=False)).unit in {1, 2, 3}
    # A best line laid through a leader already is kept, and none is looked for with no leader
    assert aimed(focused, Observation(HERE, {9: foe(10.0, 0.0, elite=True), 1: foe(0.0, 10.0)})).unit == 9
    assert aimed(focused, Observation(HERE, {1: foe(10.0, 0.0)})).unit == 1


def test_focus_leaders_puts_the_share_on_the_games_attack(monkeypatch, no_hold):
    from inventory_tracking.builds.warlock.echoing_strike import attack

    seen = pack_and_leader(beside=True)
    monkeypatch.setattr(attack, 'FOCUS_LEADERS', False)
    assert aimed(ATTACK, seen).unit in {1, 2, 3}
    monkeypatch.setattr(attack, 'FOCUS_LEADERS', True)
    assert aimed(ATTACK, seen).unit == 9


# The leader held (HOLD_LEADER; the player, 2026-10-21 ~18:58: "we're not focusing and delivering good damage ...
# targeted at wrong location => spread projectiles => low dps"; rca/2026-10-21/herald-aiming-findings.md): a leader
# in reach is struck until it dies, the focal point on it, a Herald first, the same one kept while it is seen.
def holding() -> EchoingStrike:
    """A sweep of its own with the hold on: its `held` is not the game's attack's."""
    return EchoingStrike(damage_of=flat, hold=True)


def blades_on(origin, focal, at) -> int:
    """How many of the five blades of a cast at `focal` come within the contact radius of `at` on the way out."""
    return sum(
        any(math.dist(point, at) <= CONTACT_RADIUS for point in path[: OUT_FRAMES + 1])
        for path in cast(origin, focal, lambda frame: origin)
    )


def test_the_hold_strikes_a_leader_in_reach_through_its_body_whatever_its_pack_is_worth():
    seen = pack_and_leader(beside=False)  # the pack's line takes 3 x 2,800, the leader's 2 x 2,800: 67%
    attack = holding()
    found = aimed(attack, seen)
    leader = seen.foes[9].at
    assert found.unit == 9
    assert attack.held.unit == 9
    assert 0.0 <= math.dist(HERE, found.focal) - math.dist(HERE, leader) <= 1.0  # on it or one unit past
    assert blades_on(HERE, found.focal, leader) == 5  # the five meet on it


def test_a_held_leader_is_kept_until_it_is_gone_and_a_herald_takes_over_from_any_other():
    attack = holding()
    far = foe(0.0, 14.0, elite=True)
    assert aimed(attack, Observation(HERE, {1: foe(8.0, 0.0), 7: far})).unit == 7
    # A leader nearer than the held one: the held one still
    assert aimed(attack, Observation(HERE, {1: foe(8.0, 0.0), 7: far, 8: foe(-6.0, 0.0, elite=True)})).unit == 7
    # The held one gone: the nearest leader, held from here
    assert aimed(attack, Observation(HERE, {1: foe(8.0, 0.0), 8: foe(-6.0, 0.0, elite=True)})).unit == 8
    assert attack.held.unit == 8
    # A Herald in reach takes it over from a leader that is none, and keeps it against a nearer leader
    herald = replace(foe(0.0, -16.0, elite=True), tier=5)
    minion = replace(foe(0.0, -12.0), tier=5)  # a Herald's minion carries the tier, not the rank
    assert not minion.herald
    seen = Observation(HERE, {8: foe(-6.0, 0.0, elite=True), 5: herald, 6: minion})
    assert aimed(attack, seen).unit == 5
    assert aimed(attack, Observation(HERE, {8: foe(-6.0, 0.0, elite=True), 5: herald, 9: foe(4.0, 0.0, elite=True)}))
    assert attack.held.unit == 5


def test_a_held_leader_with_no_line_to_it_now_is_struck_round_and_kept():
    attack = holding()
    leader, pack = foe(12.0, 0.0, elite=True), {1: foe(0.0, 8.0), 2: foe(0.0, 10.0)}
    assert aimed(attack, Observation(HERE, {9: leader, **pack})).unit == 9
    # A wall between: no blade reaches it, the pack's line is cast and the leader stays held
    walled = Observation(HERE, {9: leader, **pack}, blocked=wall_at(6.0))
    assert aimed(attack, walled).unit in {1, 2}
    assert attack.held.unit == 9
    assert aimed(attack, Observation(HERE, {9: leader, **pack})).unit == 9


def test_a_leader_out_of_the_blades_reach_is_no_hold():
    attack = holding()
    seen = Observation(HERE, {1: foe(8.0, 0.0), 9: foe(0.0, REACH + 2.0, elite=True)})
    assert aimed(attack, seen).unit == 1
    assert attack.held.unit is None


def test_the_units_named_first_go_before_the_held_leader():
    # A boss, a bound summoner, what bars the goal, the dolls (macros/hunt.py `choose`, `aim_choice`'s `first`)
    attack = holding()
    seen = pack_and_leader(beside=False)
    assert aimed(attack, seen).unit == 9
    named = attack.aim(seen, through=[1])
    assert named is not None
    assert named.unit == 1


# The take of 2026-10-21 18:54:42.84 (inventory_tracking/runs/combat/20261021T155355Z-128, Worldstone Keep 1): the
# tier 5 Herald (a Vile Witch, 4013196991) 13.5 units off, its pack about the character: (unit, txt, place, life of
# 128, type flags, Herald tier)
MOMENT_HERE = (12618.5, 10520.52)
MOMENT = (
    (3120801425, 638, (12628.5, 10505.5), 105, 16, 5),
    (3762071834, 638, (12626.5, 10506.5), 64, 16, 5),
    (1409781027, 638, (12620.15, 10501.15), 128, 16, 5),
    (1719712164, 638, (12612.5, 10516.5), 103, 16, 5),
    (3766063669, 638, (12617.5, 10514.5), 102, 16, 5),
    (4013196991, 638, (12628.5, 10511.5), 89, 8, 5),
    (2819562054, 638, (12627.5, 10504.5), 17, 16, 5),
    (3439440712, 638, (12628.5, 10513.5), 12, 16, 5),
    (859847890, 638, (12617.53, 10505.21), 119, 16, 5),
    (3789981911, 638, (12624.5, 10492.5), 111, 16, 5),
    (3885638495, 638, (12614.91, 10515.18), 100, 16, 5),
    (429923945, 638, (12625.14, 10511.62), 108, 16, 5),
)
MOMENT_HERALD = 4013196991


def moment() -> Observation:
    from inventory_tracking.combat.mechanics.life import foe_points, leader

    foes = {
        unit: Foe(txt, at, foe_points(txt, 128, flags, tier) * life / 128, leader(flags), tier=tier)
        for unit, txt, at, life, flags, tier in MOMENT
    }
    return Observation(MOMENT_HERE, foes)


def test_in_the_takes_herald_fight_the_line_goes_through_the_herald_with_the_blades_meeting_on_it(monkeypatch):
    from inventory_tracking.builds.warlock.echoing_strike import attack

    herald = next(at for unit, _, at, *_ in MOMENT if unit == MOMENT_HERALD)
    monkeypatch.setattr(attack, 'HOLD_LEADER', False)
    best = aimed(EchoingStrike(), moment())
    # The sweep's line then (Health Link left out): through a minion, the focal point 3 units short of it, the blades
    # crossing there and fanning out over the pack, two of the five on the Herald's edge
    assert best.unit != MOMENT_HERALD
    assert blades_on(MOMENT_HERE, best.focal, herald) == 2
    found = aimed(EchoingStrike(hold=True), moment())
    assert found.unit == MOMENT_HERALD
    assert blades_on(MOMENT_HERE, found.focal, herald) == 5


def test_hold_leader_puts_the_hold_on_the_games_attack(monkeypatch):
    from inventory_tracking.builds.warlock.echoing_strike import attack

    monkeypatch.setattr(attack, 'HOLD_LEADER', False)
    assert aimed(EchoingStrike(damage_of=flat), pack_and_leader(beside=False)).unit in {1, 2, 3}
    monkeypatch.setattr(attack, 'HOLD_LEADER', True)
    game = EchoingStrike(damage_of=flat)
    assert aimed(game, pack_and_leader(beside=False)).unit == 9
    assert game.held.unit == 9  # the copy the switch makes holds it in the attack's own `held`


def test_a_leader_immune_to_the_blades_is_held_too():
    # The player, 2026-10-21 ~20:15: "we still need to focus physical immune mobs, and magical immune"; "we need to do
    # the best aiming when we're trying to focus mob" (the 18:35 Gloam Herald stood at physical 110)
    from inventory_tracking.game.layout import COLD_RESIST, MAGIC_RESIST, PHYSICAL_RESIST

    pack = {1: foe(8.0, 0.0), 2: foe(10.0, 0.0), 3: foe(12.0, 0.0)}
    for immune in (PHYSICAL_RESIST, MAGIC_RESIST, COLD_RESIST):
        attack = holding()
        stone = replace(foe(0.0, 10.0, elite=True), tier=5, immune_to=frozenset({immune}))
        assert aimed(attack, Observation(HERE, {9: stone, **pack})).unit == 9
        assert attack.held.unit == 9


@pytest.mark.parametrize('away', [10.0, 14.0, 18.0, 21.5])
def test_the_held_line_meets_on_an_immune_leader_at_every_bearing_through_the_screen(away):
    # The 18:35 Gloam Herald (physical 110) kept at 18 by manaburn.CASTER_RANGE: the line from there still meets on
    # it. The window shows less than the blades fly (game/view.py `reachable_focal`): toward the screen's bottom the
    # focal point is drawn in (14.8 for a leader 21.5 off), and the five blades still pass within the contact radius
    from inventory_tracking.game.layout import PHYSICAL_RESIST
    from inventory_tracking.game.view import Viewport

    view = Viewport(2560 / 1418)
    for degrees in range(0, 360, 30):
        angle = math.radians(degrees)
        at = (HERE[0] + away * math.cos(angle), HERE[1] + away * math.sin(angle))
        gloam = Foe(310, at, 1e6, True, tier=5, immune_to=frozenset({PHYSICAL_RESIST}))
        minion = Foe(310, (at[0] + 3.0, at[1] + 2.0), 5000.0, tier=5)
        seen = Observation(HERE, {9: gloam, 1: minion}, aimable=lambda focal: view.reachable_focal(HERE, focal))
        found = aimed(holding(), seen)
        assert found.unit == 9, degrees
        assert blades_on(HERE, found.focal, at) == 5, degrees
