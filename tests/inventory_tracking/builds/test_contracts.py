"""What every build owes the framework (macros/build.py), asked of every build the registry lists
(builds/__init__.py: the characters' layers, the builds and the fallback) and of the tests' own."""

import dataclasses
import itertools
import math

import pytest
from pydantic import ValidationError

from inventory_tracking import builds as registry
from inventory_tracking.combat import stance
from inventory_tracking.combat.policy import Choice, Foe, Observation
from inventory_tracking.game.records import Player, Teleport, World
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.buffs import Buffs, keys_of, phase_keys
from inventory_tracking.macros.build import Build, Intent, JumpSource, Loadout, MoveFacts, NoWay, choose
from inventory_tracking.macros.skills import ACTIONS, skill_name
from inventory_tracking.macros.travel import OWN_MOVE, PLAYER_STEP, SEEK, Step, navigator
from tests.inventory_tracking.builds.dummy import DUMMY
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, KEYS, Game, world


BUILDS = [registry.FALLBACK, DUMMY, *registry.BUILDS]
PHASES = {'prebuff', 'upkeep', 'fight', 'opening'}
ONS = {'self', 'monster', 'corpse', 'ground'}
IDS = [build.name + (' with weapon sets' if build.weapons is not None else '') for build in BUILDS]
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
    OWN_MOVE,
    SEEK,
    PLAYER_STEP,
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


def asked(build: Build):
    """(the set, the facts, a goal, an intent) for every set of the build and everything on the grid:
    with the keys as the grid has them (none of the set's jumps on one), and with every jump of the
    set on a key, at rest and a moment after each was last made."""
    for movement in sets_of(build):
        on_keys = tuple(source.jump.skill for source in movement.sources)
        just = dict.fromkeys(on_keys, 9.9)
        for facts, goal, intent in GRID:
            yield movement, facts, goal, intent
            if on_keys:
                yield movement, dataclasses.replace(facts, slots=on_keys), goal, intent
                yield movement, dataclasses.replace(facts, slots=on_keys, last_used=just), goal, intent


@build_cases
def test_a_movement_set_answers_with_a_step_or_a_reason(build):
    for movement, facts, goal, intent in asked(build):
        leg = movement.leg(facts, goal, intent)
        assert isinstance(leg, Step | NoWay)
        if isinstance(leg, NoWay):
            assert leg.reason.strip()
        else:
            assert all(math.isfinite(c) for c in leg.spot)
            assert math.dist(leg.spot, goal) <= math.dist(facts.here, goal) + 1e-9


@build_cases
def test_a_goal_within_the_stand_off_is_an_arrival_and_a_shunned_end_is_a_block(build):
    for movement, facts, goal, intent in asked(build):
        leg = movement.leg(facts, goal, intent)
        away = math.dist(facts.here, goal)
        if away <= intent.short:
            assert isinstance(leg, NoWay)  # never a step back
            assert leg.arrived
        elif away - intent.short >= 10.0 and intent.shuns(goal):
            assert isinstance(leg, NoWay)  # a move is wanted, and every end of one is shunned
            assert not leg.arrived


@build_cases
def test_eta_is_inf_exactly_where_leg_has_no_way(build):
    for movement, facts, goal, intent in asked(build):
        blocked = isinstance(movement.leg(facts, goal, intent), NoWay)
        eta = movement.eta(facts, goal, intent)
        assert (eta == math.inf) == blocked
        assert blocked or eta >= 0


@build_cases
def test_wait_is_never_negative_and_nothing_for_a_caller_that_does_not_wait(build):
    for movement, facts, goal, intent in asked(build):
        wait = movement.wait(facts, goal, intent)
        assert wait >= 0
        assert intent.may_wait or wait == 0


@build_cases
def test_jumps_are_jumps_of_the_sets_own_sources_in_their_order(build):
    for movement, facts, _, intent in asked(build):
        found = movement.jumps(facts, intent)
        assert isinstance(found, tuple)
        assert all(isinstance(jump, stance.Jump) for jump in found)
        known = [source.jump for source in movement.sources]
        assert [jump for jump in known if jump in found] == list(found)
        assert all(jump.skill in facts.slots for jump in found)  # never by a skill that is on no key


@build_cases
def test_the_sources_of_a_set_are_jump_sources_with_a_delay_that_is_not_negative(build):
    for movement in sets_of(build):
        assert isinstance(movement.sources, tuple)
        assert movement.name.strip()
        for source in movement.sources:
            assert isinstance(source, JumpSource)
            assert isinstance(source.jump, stance.Jump)
            assert source.delay >= 0


@build_cases
def test_the_navigator_asks_only_a_set_that_applies(build):
    """`leg` is never asked of a set whose `applies` is false: the navigator is the one way to a set."""
    sets = sets_of(build)
    for facts in FACTS:
        movement = navigator(sets, facts)
        applying = [candidate for candidate in sets if candidate.applies(facts)]
        assert movement is (applying[0] if applying else None)


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

    before = dataclasses.replace(inside, foes=dict(inside.foes))
    assert isinstance(attack.sees(inside, ()), Observation)
    assert inside == before  # what it sees is in a copy: the observation given is not changed
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
        assert buff.skill not in buff.also
        assert buff.on in ONS
        assert buff.needs in (None, 'prebuff', 'battle')
        # The shared cast is an aim and a key: it has none for a corpse, and needs to be told whom to aim at. A caster
        # finds its own place (build.py `Buff.target`: the Defiler's summon spot on the ground, Warlock casters.py).
        assert buff.caster is not None or buff.on != 'corpse'
        assert buff.target is not None or buff.caster is not None or buff.on not in ('monster', 'ground')


@build_cases
def test_every_caster_a_build_holds_is_named_by_a_row(build):
    assert set(build.casters) == {buff.caster for buff in build.buffs if buff.caster is not None}
    assert all(callable(caster) for caster in build.casters.values())


@build_cases
def test_every_skill_a_buff_plan_names_resolves_through_the_fakes_key_table(build):
    """The row's own skill, the ones its caster presses (`also`) and the swap for a weapon set: each
    has a key in the fakes' table, and each skill is on a skill key of the fakes' character."""
    if not build.buffs:
        pytest.skip(f'{build.name} has no buffs')
    for buff in build.buffs:
        for skill in keys_of(buff):
            assert skill in KEYS, f'{skill_name(skill)} of the {buff.phase} row of {skill_name(buff.skill)}'
            assert skill in ACTIONS or skill in HUNT_SLOTS
        assert set(keys_of(buff)) >= {buff.skill, *buff.also}
    for phase in PHASES:
        assert set(phase_keys(build.buffs, phase)) <= set(KEYS)


@build_cases
def test_the_executor_asks_every_row_of_a_build_without_a_fight(build):
    """Each row answers with facts that hold no hostile, no prey and no cast: due or not, never an error."""
    if not build.buffs:
        pytest.skip(f'{build.name} has no buffs')
    play = Game(world(slots=HUNT_SLOTS))
    buffs, run = Buffs(build), play.run()
    for buff in build.buffs:
        found = buffs.due(run, buff, buffs.facts(run, play.world))
        assert found is None or found.row is buff


@build_cases
def test_settings_are_frozen(build):
    with pytest.raises(ValidationError):
        build.settings.caution = 1.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        build.name = 'other'  # pyrefly: ignore[read-only]


def world_of(name: str) -> World:
    player = Player(unit_id=1, name=name, mode=1, area=1, x=0.0, y=0.0, consume=None)
    return World(in_game=True, open_panels=(), game_name='game', slots=(0, None), player=player)


def test_every_registered_build_is_asked():
    assert len(set(IDS)) == len(IDS) == len(registry.BUILDS) + 2
    assert all(any(build is listed for build in BUILDS) for listed in (*registry.BUILDS, registry.FALLBACK))


@build_cases
def test_a_build_is_nobodys_with_no_character_in_the_world(build):
    """A loading screen, the lobby: `applies` is false, and `choose` gives the fallback without asking."""
    for found in (world_of('Dummy'), world(slots=HUNT_SLOTS)):
        nobody = dataclasses.replace(found, player=None)
        assert build.applies(nobody) is False
        fallback = dataclasses.replace(build, name='fallback')
        assert choose([build], nobody, fallback) is fallback


@build_cases
def test_the_weapon_sets_of_a_build_are_a_loadout_of_base_codes_or_none(build):
    if build.weapons is None:
        return
    assert isinstance(build.weapons, Loadout)
    for codes in (build.weapons.prebuff, build.weapons.battle):
        assert isinstance(codes, frozenset)
        assert codes
        assert all(isinstance(code, str) and len(code) == 3 for code in codes)


@build_cases
def test_choose_takes_this_build_when_it_applies_and_the_fallback_otherwise(build):
    fallback = dataclasses.replace(build, name='fallback', applies=lambda world: False)
    for name in ('Dummy', 'Someone'):
        world = world_of(name)
        picked = choose([build], world, fallback)
        assert picked is (build if build.applies(world) else fallback)
    assert choose([], world_of('Dummy'), fallback) is fallback
