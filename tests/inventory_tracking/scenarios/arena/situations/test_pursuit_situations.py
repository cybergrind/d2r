"""The pursuit loop on the recorded situations (rca/2026-10-13/pursuit-v1.md): the same scene and the same
presses played by today's keys and with `BuildSettings.pursuit` on (`Situation.logic('new')`).

What the player asked of the teleport key on 2026-10-13 (kp4-findings.md): repeated presses advance to the
goal, a press does not pause the attack, repeated presses do not kill. Each requirement is one test over
both logics: `today` is `xfail(strict=True)` where today's keys do not meet it (the day they do, the mark
comes off), `new` passes. With the switch off nothing here changes a play: test_situations.py pins those.

Cost: about 150 plays. Each cached family of plays is an `xdist_group` of its own (`-n auto --dist loadgroup`,
tests/inventory_tracking/conftest.py), so the families run on several workers and a play is still made once;
the rest of the file runs together, as a file does.
"""

import functools
import logging
import math
import random
from dataclasses import dataclass
from itertools import pairwise

import pytest

from inventory_tracking.builds.warlock.echoing_strike.hits import CONTACT_RADIUS
from inventory_tracking.builds.warlock.echoing_strike.mechanics import RANGE
from inventory_tracking.macros import goals
from inventory_tracking.macros.build import MoveFacts
from inventory_tracking.macros.hunting import base as hunt_base
from inventory_tracking.macros.runner import TELEPORT
from inventory_tracking.macros.skills import TELEPORT as TELEPORT_SKILL
from inventory_tracking.macros.travel import PRESSED, navigator
from tests.inventory_tracking.scenarios.arena.kp4 import RoutePlay, longest_quiet
from tests.inventory_tracking.scenarios.arena.situations import pocket, vizier
from tests.inventory_tracking.scenarios.arena.situations.pocket import PACK, POCKET
from tests.inventory_tracking.scenarios.arena.situations.situation import (
    FIXTURES,
    Outcome,
    Situation,
    dump,
    held,
    load,
    once,
    open_field,
)
from tests.inventory_tracking.scenarios.arena.situations.stage import Stage
from tests.inventory_tracking.scenarios.arena.situations.vizier import BOSS, SEAL, STALL


Point = tuple[float, float]
SEEDS = (1, 2, 3)
TEN = tuple(range(1, 11))
FIGHT_STAGE = 'fight Grand Vizier of Chaos'
QUIET_MOST = 2.0  # seconds without a strike while a hostile is in reach (test_incident_kp4.py QUIET_MOST)
# Units, centre to centre: the furthest a monster's centre can stand from the character and still be touched
# by a blade, as the arena's hit rule measures it (game.py `Arena.fly`): a blade's furthest point is RANGE
# (22.1) from the cast's origin, and it touches a monster whose centre is within CONTACT_RADIUS of it. Not
# the aim's own `LinePolicy.reach` (RANGE), which is how far a line is laid through a centre: the blades hurt
# the Vizier from 23.6 units in the stall (seed 4 of the held key, measured 2026-10-14).
STRIKE_REACH = RANGE + CONTACT_RADIUS


def left_alone(outcome: Outcome) -> bool:
    """Whether the fight gave the boss up for a while (hunt.py `untouched`: its life did not go down in four
    casts laid through it, so it is no hostile for 20 s). The fight's own rule, as it is with today's keys:
    a play that ends inside those seconds has the character at the boss and the boss alive."""
    boss = next(unit for unit, name in vizier.stored(STALL).bosses if name == BOSS)
    return any('takes no damage' in text and str(boss) in text for _, text in outcome.said)


def at_the_boss(outcome: Outcome) -> bool:
    """The presses brought the character to the boss (57 units off at the start): his centre came within the
    blades' reach of it (STRIKE_REACH, as `Outcome.gaps` measures: the character's place to the boss's at
    every tick while he lived), and he died unless the fight left him alone. In the arena only the
    character's blades take a monster's life (`Arena.fly`; no companion or link deals damage there), so his
    death is the character's kill."""
    assert outcome.gaps[BOSS] is not None
    return outcome.gaps[BOSS][1] <= STRIKE_REACH and (outcome.boss_dead[BOSS] is not None or left_alone(outcome))


LOGICS = [
    pytest.param('today', marks=pytest.mark.xfail(strict=True, reason="today's keys: kp4-findings.md §2")),
    'new',
]


@dataclass
class Watch:
    """A play watched at every tick: where the character stood, the seconds left to `goal` by the navigator's
    own measure (`MovementSet.eta` within PRESSED, from the arena's facts), whether a hostile stood within
    the strike's reach, and the route's stage."""

    outcome: Outcome
    presses: list[float]
    rows: list[tuple[float, Point, float, bool, str | None]]

    def eta_at(self, at: float) -> float:
        return next((eta for when, _, eta, _, _ in self.rows if when >= at - 1e-6), self.rows[-1][2])

    def quiet(self, stage: str | None = None) -> float:
        """The longest time without a strike's beginning while a hostile was in reach (and the route at `stage`)."""
        reached = [(at, near and (stage is None or staged == stage)) for at, _, _, near, staged in self.rows]
        return longest_quiet(self.outcome.strikes, reached, self.outcome.seconds)


def watched(
    situation: Situation, presses: list | None, seed: int, goal: Point | None = None, seconds: float | None = None
) -> Watch:
    rows: list[tuple[float, Point, float, bool, str | None]] = []

    def look(arena: Stage, play: RoutePlay) -> None:
        here, now = arena.here, arena.clock.now
        eta = math.nan
        if goal is not None:
            rect = arena.keys.focused_window_rect()
            slots = arena.world.slots
            facts = MoveFacts(
                here, now, slots, arena.staff if TELEPORT_SKILL in slots else None, arena.ground, arena.world.doors,
                rect[2] / rect[3], area=arena.scene.hero.area, rooms=play.level.rooms,
            )  # fmt: skip
            movement = navigator(play.build.movement, facts)
            assert movement is not None
            eta = movement.eta(facts, goal, PRESSED)
        reach = play.build.attack.reach
        near = any(math.dist(here, arena.mobs.mobs[unit].at) <= reach for unit in arena.mobs.live())
        rows.append((now, here, eta, near, play.stage()))

    outcome = situation.play(presses, seconds, seed, keep=True, each_tick=look)
    at = [press.at for press in outcome.presses_ if press.routine == TELEPORT]  # type: ignore[attr-defined]
    return Watch(outcome, at, rows)


@functools.cache
def stall(name: str, logic: str, seed: int) -> Outcome:
    situation, presses = vizier.experiments()[name]
    return situation.logic(logic).play(presses, seed=seed)  # type: ignore[arg-type]


@functools.cache
def near_boss(distance: float, way: str, logic: str, seed: int) -> Watch:
    situation, presses = vizier.distanced(distance)[way]
    return watched(situation.logic(logic), presses, seed)  # type: ignore[arg-type]


@functools.cache
def in_pocket(logic: str, key: bool, seed: int) -> Watch:
    base = pocket.stored(POCKET)
    return watched(base.logic(logic), [held('teleport', every=0.3)] if key else None, seed, pocket.seal_place(base))


@functools.cache
def sealed(logic: str, seed: int) -> Outcome:
    """The seal moment as recorded, played once for the tests that read it: 'today' is the stored situation as
    it is (the switch off), 'new' its copy with the pursuit loop on."""
    base = vizier.stored(SEAL)
    return (base.logic('new') if logic == 'new' else base).play(seed=seed)


# The families of plays, one `xdist_group` each (`--dist loadgroup`; a test not marked runs with its file).
SEAL_PLAYS = pytest.mark.xdist_group('pursuit: the seal')
STALL_RECORDED = pytest.mark.xdist_group('pursuit: the stall as recorded')
STALL_ATTACK_HELD = pytest.mark.xdist_group('pursuit: the stall, attack on and the key held')
STALL_HELD = pytest.mark.xdist_group('pursuit: the stall, the key held')
NEAR_BOSS = pytest.mark.xdist_group('pursuit: near the boss')
IN_POCKET = pytest.mark.xdist_group('pursuit: the pocket watched')


# -- the fixtures ---------------------------------------------------------------------------------------


@pytest.mark.parametrize('name', [POCKET, PACK])
def test_a_fixture_loads_without_its_take_and_writes_back_the_same(name, tmp_path) -> None:
    path = FIXTURES / f'{name}.json'
    situation = load(path)
    assert situation.source is not None
    assert situation.marks
    assert not situation.pursuit  # which logic plays it is a variant's, never the fixture's
    dump(situation, tmp_path / 'again.json')
    assert (tmp_path / 'again.json').read_text(encoding='utf-8') == path.read_text(encoding='utf-8')


def test_the_pocket_is_the_takes_moment() -> None:
    base = pocket.stored(POCKET)
    assert base.source is not None
    assert base.recorded is not None
    assert base.source['schema'] == 4
    assert base.attack
    assert len(base.presses) == 26
    assert {routine for _, routine in base.presses} == {TELEPORT}
    assert base.scene.hero.sets[1].teleport_charges == 0
    assert math.dist(base.scene.hero.at, pocket.seal_place(base)) > 250
    hostile = [mob for mob in base.scene.mobs if mob.owner is None and not mob.ally and mob.life > 0]
    assert not [mob for mob in hostile if math.dist(mob.at, base.scene.hero.at) < 60]
    assert f'scene.things.{pocket.SEAL}' in base.assumed  # the seal was never in the take's sight
    assert base.recorded['moved'] > 250  # 12 Blade Warps and 4 walks, and nowhere


def test_the_logic_is_one_switch_and_off_unless_asked() -> None:
    base = vizier.stored(STALL)
    assert not base.pursuit
    assert base.logic('new').pursuit
    assert not base.logic('new').logic('today').pursuit
    assert base.logic('today').play(seed=2) == base.play(seed=2)


# -- repeated presses advance to the goal ---------------------------------------------------------------


@STALL_RECORDED
@pytest.mark.parametrize('logic', LOGICS)
def test_repeated_presses_bring_the_character_to_the_boss_and_he_dies(logic) -> None:
    """The stall as recorded: 48 presses with the route at a fight whose boss stands 57 units off."""
    for seed in SEEDS:
        outcome = stall('as recorded (48 presses)', logic, seed)
        assert at_the_boss(outcome), seed
    assert stall('as recorded (48 presses)', logic, 1).boss_dead[BOSS] is not None
    assert stall('as recorded (48 presses)', logic, 1).stage != FIGHT_STAGE


@NEAR_BOSS
@pytest.mark.parametrize('logic', LOGICS)
@pytest.mark.parametrize('distance', [25, 40, 57.4])
def test_attack_mode_alone_goes_to_a_boss_out_of_its_reach(logic, distance) -> None:
    """No press at all: the route's stage is the fight, so the boss is where the mode goes (25 units is on
    the screen; at 57.4 the recorded stall stood for 25 s)."""
    watch = near_boss(distance, 'attack mode alone', logic, 1)
    assert watch.outcome.gaps[BOSS] is not None
    assert watch.outcome.gaps[BOSS][0] == pytest.approx(distance, abs=0.2)
    assert watch.outcome.boss_dead[BOSS] is not None
    assert watch.outcome.moved > 0.0


@NEAR_BOSS
def test_attack_mode_alone_does_not_go_to_a_boss_beyond_its_sight(caplog) -> None:
    """The player's ruling of 2026-10-15 ("only nearby"; run-2040-findings.md §5: Izual 342 units off was attack mode's
    goal after a level run ended): the same pack beyond twice the fight's sight is not gone to without a press, and
    that is said once in the log."""
    far = hunt_base.ALONE_BOSS_UNITS + 15.0
    situation, presses = vizier.distanced(far)['attack mode alone']
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        outcome = situation.logic('new').play(presses, seed=1)  # type: ignore[arg-type]
    assert outcome.gaps[BOSS] is not None
    assert outcome.gaps[BOSS][0] == pytest.approx(far, abs=0.2)
    assert outcome.moved == 0.0
    assert outcome.boss_dead[BOSS] is None
    assert caplog.text.count('Macro: attack mode: Grand Vizier of Chaos is 75 away') == 1
    assert caplog.text.count('not gone to without a press') == 1


@IN_POCKET
@pytest.mark.parametrize('logic', ['today', 'new'])  # today's keys too since the navigation classes (2026-10-15)
@pytest.mark.parametrize('key', [False, True], ids=['recorded presses', 'the key held'])
def test_the_character_leaves_the_pocket_and_reaches_the_seal(logic, key) -> None:
    for seed in SEEDS:
        watch = in_pocket(logic, key, seed)
        seal = pocket.seal_place(pocket.stored(POCKET))
        assert min(math.dist(here, seal) for _, here, _, _, _ in watch.rows) <= goals.USE_NEAR
        assert math.dist(watch.rows[-1][1], pocket.A) > pocket.POCKET_UNITS
        assert watch.outcome.stage != f'use {pocket.SEAL}'  # the seal is opened: the route goes on


@IN_POCKET
@pytest.mark.parametrize('key', [False, True], ids=['recorded presses', 'the key held'])
def test_in_the_pocket_the_way_left_never_grows_between_two_presses(key) -> None:
    """Progress by the navigator's own measure (`MovementSet.eta`, here the walked way at the pace of the
    means in hand): from one press to the next it never rises. On 13:05 the walked way went 318, 325, 312,
    333, 308, 314 while the straight line fell."""
    base = pocket.stored(POCKET)
    seal = next(prop.unit for prop in base.scene.things if math.dist(prop.at, pocket.seal_place(base)) < 1)
    for seed in SEEDS:
        watch = in_pocket('new', key, seed)
        opened = watch.outcome.opened[seal]  # from then on the key's goal is the next seal
        etas = [watch.eta_at(at) for at in watch.presses if at < opened]
        assert etas[0] > 10.0  # 318 units on foot and by Blade Warp
        assert all(later <= earlier + 1e-9 for earlier, later in pairwise(etas)), etas
        assert etas[-1] < 1.5  # the last press before the seal opens finds it a move away


@IN_POCKET
def test_today_too_the_way_left_in_the_pocket_never_grows() -> None:
    """The recording's defect (the way left 318, 325, 312, 333, 308, 314) is gone from today's keys too: with the
    staff empty their teleport step goes by the navigation class in hand (hunting/moves.py `class_step`: the walked way,
    a Blade Warp over a clear line; rca/2026-10-14/navigation-classes.md), not toward a Teleport landing."""
    base = pocket.stored(POCKET)
    seal = next(prop.unit for prop in base.scene.things if math.dist(prop.at, pocket.seal_place(base)) < 1)
    watch = in_pocket('today', False, 1)
    opened = watch.outcome.opened[seal]
    assert opened is not None
    etas = [watch.eta_at(at) for at in watch.presses if at < opened]
    assert etas[0] > 10.0
    assert all(later <= earlier + 1e-9 for earlier, later in pairwise(etas)), etas


# -- a press does not pause the attack ------------------------------------------------------------------


@NEAR_BOSS
@pytest.mark.parametrize('logic', LOGICS)
def test_a_held_key_does_not_keep_attack_mode_from_killing_a_boss_in_reach(logic) -> None:
    """The Vizier 12 units off, attack mode on, the key held at 0.3 s: he dies as with the mode alone, and
    while the route is at his fight no QUIET_MOST seconds pass without a strike with a hostile in reach."""
    watch = near_boss(12, 'attack on + KP_4 every 0.3 s', logic, 1)
    assert watch.outcome.boss_dead[BOSS] is not None
    assert watch.quiet(FIGHT_STAGE) <= QUIET_MOST


@NEAR_BOSS
def test_a_held_key_costs_the_fight_at_the_boss_nothing() -> None:
    """The same fight with the key held and without it: the boss dies no later than a strike's worth after."""
    for seed in SEEDS:
        alone = near_boss(12, 'attack mode alone', 'new', seed).outcome.boss_dead[BOSS]
        key = near_boss(12, 'attack on + KP_4 every 0.3 s', 'new', seed).outcome.boss_dead[BOSS]
        assert alone is not None
        assert key is not None
        assert key <= alone + QUIET_MOST


@STALL_ATTACK_HELD
def test_a_posted_press_cancels_nothing() -> None:
    """With attack mode working the press is posted: the mode is not paused for it, however often."""
    outcome = stall('(a) attack mode on + KP_4 held, every 0.3 s', 'new', 1)
    assert not outcome.said_count('Attack mode paused')
    assert outcome.said_count('Attack mode on') == 1
    assert stall('(a) attack mode on + KP_4 held, every 0.3 s', 'today', 1).said_count('Attack mode paused') > 20


# -- repeated presses do not kill, and the toggle stays the player's ------------------------------------


@pytest.mark.parametrize(
    'name',
    [
        pytest.param('as recorded (48 presses)', marks=STALL_RECORDED),
        pytest.param('(a) KP_4 held, every 0.3 s', marks=STALL_HELD),
        pytest.param('(a) attack mode on + KP_4 held, every 0.3 s', marks=STALL_ATTACK_HELD),
        '(c) attack mode alone',
    ],
)
def test_the_character_lives_through_the_stall_by_the_new_logic(name) -> None:
    killed = 0
    for seed in TEN:
        outcome = stall(name, 'new', seed)
        assert not outcome.dead, seed
        assert at_the_boss(outcome), seed
        killed += outcome.boss_dead[BOSS] is not None
    assert killed >= 8  # with today's keys: none of ten


def through(name: str) -> tuple[Situation, list | None]:
    """The other three situations the character lives through: the situation by the new logic, its presses."""
    if name == PACK:
        return pocket.pack_variants()[2][1], None
    presses = [held('teleport', every=0.3)] if name == f'{POCKET}, held' else None
    return pocket.stored(POCKET).logic('new'), presses


# One part a situation: each is ten plays (the seal's are the same ten as the test below plays, read from `sealed`).
@pytest.mark.parametrize(
    'name',
    [
        pytest.param(SEAL, marks=SEAL_PLAYS),
        pytest.param(f'{POCKET}, recorded', marks=pytest.mark.xdist_group('pursuit: the pocket, recorded')),
        pytest.param(f'{POCKET}, held', marks=pytest.mark.xdist_group('pursuit: the pocket, the key held')),
        pytest.param(PACK, marks=pytest.mark.xdist_group('pursuit: the pack')),
    ],
)
def test_the_character_lives_through_the_seal_the_pocket_and_the_pack_by_the_new_logic(name) -> None:
    if name == SEAL:
        outcomes = (sealed('new', seed) for seed in TEN)
    else:
        situation, presses = through(name)
        outcomes = (situation.play(presses, seed=seed) for seed in TEN)
    for seed, outcome in zip(TEN, outcomes, strict=True):
        assert not outcome.dead, (name, seed)


@SEAL_PLAYS
def test_the_seal_is_opened_and_the_vizier_killed_by_the_new_logic() -> None:
    """The seal moment as recorded, 16 s: the seal is opened in every seed, and the Vizier dies within the
    window in more of them than with today's keys (5 of 10: the arena's fight takes the character elsewhere
    before the pack appears, rca/2026-10-13/situations.md §3). Since the casters think by the client's code
    (sim/casters.py, 2026-10-13) the new logic kills him in 6 of 10 (7 before)."""
    new = [sealed('new', seed) for seed in TEN]
    today = [sealed('today', seed) for seed in TEN]
    assert all(outcome.opened for outcome in new)
    killed = sum(1 for outcome in new if outcome.boss_dead[BOSS] is not None)
    assert killed >= 6
    assert killed >= sum(1 for outcome in today if outcome.boss_dead[BOSS] is not None)


def test_the_toggle_off_stays_off_under_presses() -> None:
    """Attack mode on, the toggle at 1.0 s turns it off, then the key is held: the character still goes to
    the boss, the mode is not turned back on by any press, and nothing is struck."""
    base = vizier.stored(STALL).variant(attack=True).logic('new')
    presses = [once('attack', at=1.0), held('teleport', every=0.3, since=1.2)]
    for seed in SEEDS:
        outcome = base.play(presses, seed=seed)
        assert outcome.said_count('Attack mode on') == 1
        assert outcome.said_count('Attack mode off') == 1
        assert not [at for at in outcome.strikes if at > 1.5]
        assert outcome.gaps[BOSS] is not None
        assert outcome.gaps[BOSS][1] < 30.0  # the key still takes the character there
        assert outcome.said_count('attack mode is off')


@STALL_RECORDED
def test_a_press_with_the_mode_never_touched_turns_it_on_for_a_fight() -> None:
    """The stall began with the mode off and never toggled: the route's fight stage wants it, as before."""
    outcome = stall('as recorded (48 presses)', 'new', 1)
    assert outcome.said_count('Attack mode on') == 1


# -- liveness: never silence ----------------------------------------------------------------------------


WINDOW = 5  # presses: at 0.3 s apart, 1.5 s, more than one Blade Warp from its key to the next one's landing
MOVES = ('Blade Warp', 'Teleport', 'Walking', 'Swap Weapons')  # what the macro says of a move it makes


def scene(seed: int) -> tuple[Situation, Point]:
    """An open field with a mark for the key to go to, a pack somewhere and the staff as it may be."""
    rng = random.Random(seed)
    turn, away = rng.uniform(0, 2 * math.pi), rng.uniform(25, 50)
    offset = (round(away * math.cos(turn), 1), round(away * math.sin(turn), 1))
    built = (
        Situation.on(open_field(60), name=f'liveness {seed}')
        .hero(charges=rng.choice((0, 5, 30)), weapons=rng.choice(('main', 'staff')))
        .mark('the goal', at=offset)
        .attack_mode(rng.random() < 0.5)
    )
    if rng.random() < 0.7:
        pack = (round(rng.uniform(-40, 40), 1), round(rng.uniform(-40, 40), 1))
        built.pack('Hell Bovine', rng.randint(2, 6), at=pack, spread=4)
    return built.logic('new'), built.spot(offset)


@pytest.mark.parametrize('seed', range(1, 13))
def test_a_held_key_always_shortens_the_way_or_says_why_not(seed) -> None:
    """For any scene: within WINDOW presses of a held key either the navigator's `eta` to the goal has
    fallen or the macro has said something that is not a move (a reason, a fight, an arrival). Never silence."""
    built, goal = scene(seed)
    watch = watched(built, [held('teleport', every=0.3)], seed, goal, seconds=8.0)
    said = watch.outcome.said
    presses = [at for at in watch.presses if at <= watch.rows[-1][0] - 0.3 * WINDOW]
    for at in presses:
        until = at + 0.3 * WINDOW
        before, after = watch.eta_at(at), watch.eta_at(until)
        where = next(here for when, here, _, _, _ in watch.rows if when >= at - 1e-6)
        if math.dist(where, goal) <= goals.PLACE_NEAR:
            break  # there: the key has nothing more to ask
        lines = [text.removeprefix('Macro: ') for when, text in said if at <= when <= until]
        spoken = [text for text in lines if not text.startswith(MOVES)]
        assert after < before or spoken, (seed, at, before, after)
    assert not watch.outcome.dead
