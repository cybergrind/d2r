"""What every build owes the framework (macros/build.py), asked of each build in BUILDS: add a build by appending."""

import dataclasses
import itertools
import math

import pytest
from pydantic import ValidationError

from inventory_tracking.builds.generic import GENERIC
from inventory_tracking.combat import stance
from inventory_tracking.combat.policy import Choice, Foe, Observation
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.build import Build, Intent, MoveFacts, NoWay, choose
from inventory_tracking.macros.travel import Step
from inventory_tracking.macros.world import Player, Teleport, World
from tests.inventory_tracking.builds.dummy import DUMMY


BUILDS = [GENERIC, DUMMY]
PHASES = {'prebuff', 'upkeep', 'fight', 'opening'}
IDS = [build.name for build in BUILDS]
build_cases = pytest.mark.parametrize('build', BUILDS, ids=IDS)

STAFFS = [None, *(Teleport(n, 69, True) for n in (69, 15, 14, 10, 9, 0)), Teleport(69, 69, False)]
GROUNDS = [None, Ground(())]
DISTANCES = (0.0, 1.5, 10.0, 30.0, 80.0)
DIRECTIONS = ((1.0, 0.0), (0.6, 0.8))
HERE = (100.0, 200.0)
INTENTS = [
    Intent('plain', reserve=10, may_swap=False, may_wait=False, distrust=30.0),
    Intent('short', reserve=10, may_swap=False, may_wait=False, distrust=30.0, short=14.0),
    Intent('shunning', reserve=10, may_swap=False, may_wait=False, distrust=30.0, shuns=lambda spot: True),
]
FACTS = [
    MoveFacts(here=HERE, now=10.0, slots=(7, None), staff=staff, ground=ground, doors=(), aspect=1.8)
    for staff in STAFFS
    for ground in GROUNDS
]
GOALS = [(HERE[0] + d * ux, HERE[1] + d * uy) for d in DISTANCES for ux, uy in DIRECTIONS]
GRID = list(itertools.product(FACTS, GOALS, INTENTS))


def sets_of(build: Build):
    if not build.movement:
        pytest.skip(f'{build.name} has no movement sets yet')
    return build.movement


@build_cases
def test_a_movement_set_answers_with_a_step_or_a_reason(build):
    for movement in sets_of(build):
        for facts, goal, intent in GRID:
            leg = movement.leg(facts, goal, intent)
            assert isinstance(leg, Step | NoWay)
            if isinstance(leg, NoWay):
                assert leg.reason.strip()
            else:
                assert all(math.isfinite(c) for c in leg.spot)
                assert math.dist(leg.spot, goal) <= math.dist(facts.here, goal) + 1e-9


@build_cases
def test_eta_is_inf_exactly_where_leg_has_no_way(build):
    for movement in sets_of(build):
        for facts, goal, intent in GRID:
            blocked = isinstance(movement.leg(facts, goal, intent), NoWay)
            eta = movement.eta(facts, goal, intent)
            assert (eta == math.inf) == blocked
            assert blocked or eta >= 0


@build_cases
def test_wait_is_never_negative(build):
    for movement in sets_of(build):
        assert all(movement.wait(facts, goal, intent) >= 0 for facts, goal, intent in GRID)


@build_cases
def test_jumps_are_jumps(build):
    for movement in sets_of(build):
        for facts, _, intent in GRID:
            found = movement.jumps(facts, intent)
            assert isinstance(found, tuple)
            assert all(isinstance(jump, stance.Jump) for jump in found)


def seen_with(*foes: tuple[int, tuple[float, float]]) -> Observation:
    return Observation(origin=(0.0, 0.0), foes={unit: Foe(txt=1, at=at, left=500.0) for unit, at in foes})


@build_cases
def test_an_attack_aims_only_within_its_reach_and_deals_to_foes_it_was_given(build):
    attack = build.attack
    if attack is None:
        pytest.skip(f'{build.name} has no attack of its own')
    near, far = attack.reach / 2, attack.reach * 2
    inside = seen_with((1, (near, 0.0)))
    assert isinstance(attack.aim(inside), Choice)
    assert attack.aim(seen_with((1, (far, 0.0)))) is None

    two = seen_with((1, (near, 0.0)), (2, (0.0, near + 1.0)))
    for unit in (1, 2):
        choice = attack.aim(two, through=[unit])
        assert choice is None or choice.unit == unit
    assert attack.aim(two, through=[99]) is None

    assert isinstance(attack.sees(inside, ()), Observation)
    foes = two.foes
    for focal in ((near, 0.0), (0.0, near + 1.0), (-50.0, 0.0)):
        dealt = attack.dealt((0.0, 0.0), focal, foes)
        assert set(dealt) <= set(foes)
        assert all(points >= 0 for points in dealt.values())
    assert attack.dealt((0.0, 0.0), (0.0, 0.0), {}) == {}


@build_cases
def test_every_buff_names_a_skill_a_phase_and_an_existing_caster(build):
    if not build.buffs:
        pytest.skip(f'{build.name} has no buffs')
    for buff in build.buffs:
        assert isinstance(buff.skill, int)
        assert buff.phase in PHASES
        assert buff.caster is None or buff.caster in build.casters
        assert all(isinstance(skill, int) for skill in buff.also)


@build_cases
def test_settings_are_frozen(build):
    with pytest.raises(ValidationError):
        build.settings.caution = 1.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        build.name = 'other'  # pyrefly: ignore[read-only]


def world_of(name: str) -> World:
    player = Player(unit_id=1, name=name, mode=1, area=1, x=0.0, y=0.0, consume=None)
    return World(in_game=True, open_panels=(), game_name='game', slots=(0, None), player=player)


@build_cases
def test_choose_takes_this_build_when_it_applies_and_the_fallback_otherwise(build):
    fallback = dataclasses.replace(build, name='fallback', applies=lambda world: False)
    for name in ('Dummy', 'Someone'):
        world = world_of(name)
        picked = choose([build], world, fallback)
        assert picked is (build if build.applies(world) else fallback)
    assert choose([], world_of('Dummy'), fallback) is fallback
