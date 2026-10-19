"""The situations layer (situation.py, record.py, stage.py), the Vizier's two recorded moments (vizier.py) and
the player's constructed example (example.py).

The requirements today's keys do not meet are in test_pursuit_situations.py, each a test over both logics:
`today` an `xfail(strict=True)` as in test_incident_kp4.py, `new` (the pursuit loop on) passing.

The example's two long tests share no play with the rest: each is an `xdist_group` of its own (`-n auto
--dist loadgroup`, tests/inventory_tracking/conftest.py), so they run on workers of their own."""

import functools
import math

import pytest

from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.sim import monsters as model
from inventory_tracking.macros.runner import TELEPORT
from tests.inventory_tracking.scenarios.arena import kp4
from tests.inventory_tracking.scenarios.arena.situations import vizier
from tests.inventory_tracking.scenarios.arena.situations.bestiary import TYPES, fidelity
from tests.inventory_tracking.scenarios.arena.situations.example import example, variants
from tests.inventory_tracking.scenarios.arena.situations.situation import (
    FIXTURES,
    Outcome,
    Situation,
    dump,
    east,
    held,
    load,
    north,
    once,
    open_field,
    spelled,
)  # fmt: skip
from tests.inventory_tracking.scenarios.arena.situations.stage import ARENA_AWARE, EVERYONE
from tests.inventory_tracking.scenarios.arena.situations.story import story
from tests.inventory_tracking.scenarios.arena.situations.vizier import BOSS, SEAL, STALL


SEEDS = (1, 2, 3)
BOSS_LINE = 'Grand Vizier of Chaos, attack mode'
SEAL_ONE = 307542651  # the unit of Vizier seal 1 (object class 396) in take 20261013T093331Z-108


@functools.cache
def played(name: str, seed: int) -> Outcome:
    return vizier.stored(name).play(seed=seed)


@functools.cache
def tried(name: str, seed: int) -> Outcome:
    return vizier.experiment(name, seed)


# -- the pieces -----------------------------------------------------------------------------------------


def test_every_type_of_the_bestiary_is_the_monstats_row_of_its_name() -> None:
    rows = tables()['monsters']
    for name, (txt, row_name) in TYPES.items():
        assert rows[str(txt)]['NameStr'] == row_name, name
        assert fidelity(name).plays


def test_presses_are_a_list_a_held_key_or_one_press() -> None:
    assert [(p.at, p.routine) for p in spelled([held('teleport', every=0.5)], 1.6)] == [
        (0.0, TELEPORT), (0.5, TELEPORT), (1.0, TELEPORT), (1.5, TELEPORT),
    ]  # fmt: skip
    assert [(p.at, p.routine) for p in spelled([once('pickup', at=2.0), (1.0, 'teleport')], 5.0)] == [
        (1.0, TELEPORT), (2.0, 'pickup'),
    ]  # fmt: skip


def test_the_awareness_is_put_back_after_a_play() -> None:
    quiet = Situation.on(open_field(30)).pack('Hell Bovine', 1, at=north(25)).aggro(EVERYONE)
    quiet.play(seconds=1.0)
    assert model.AWARE == ARENA_AWARE


@pytest.mark.parametrize('name', [STALL, SEAL])
def test_a_fixture_loads_without_its_take_and_writes_back_the_same(name, tmp_path) -> None:
    path = FIXTURES / f'{name}.json'
    situation = load(path)
    assert situation.source is not None
    assert situation.recorded is not None
    assert situation.scene.ground
    assert situation.scene.mobs
    assert situation.marks
    dump(situation, tmp_path / 'again.json')
    assert (tmp_path / 'again.json').read_text(encoding='utf-8') == path.read_text(encoding='utf-8')


def test_what_was_entered_by_hand_is_named_in_the_fixture() -> None:
    stall, seal = vizier.stored(STALL), vizier.stored(SEAL)
    # schema 3: the presses, the weapon set, the seals and what was open are the session log's
    for key in ('presses', 'hero.hand', 'hero.sets', 'route.opened', 'scene.things', 'scene.ward', 'route.bosses'):
        assert key in stall.assumed, key
    # schema 4: the take's own streams; only what no take holds is left
    assert sorted(seal.assumed) == ['route.bosses', 'scene.immune', 'scene.sets', 'scene.slots']
    assert seal.source is not None
    assert stall.source is not None
    assert seal.source['schema'] == 4
    assert stall.source['schema'] == 3


# -- the stall: the recording again ---------------------------------------------------------------------


def test_the_stall_is_kp4s_replay_line_for_line() -> None:
    """The same scene through kp4.py and through the situations layer: one play, so what `Cast` adds to
    `Mobs` (stage.py) changes no roll."""
    kept = kp4.stored(kp4.BOSS_AWAY)
    assert kept is not None
    scene, marks, _ = kept
    told, lines = kp4.played(scene, marks, kp4.BOSS_AWAY, 3)
    outcome = played(STALL, 3)
    assert outcome.said == lines
    assert (outcome.taken, outcome.moved, len(outcome.strikes)) == (told.taken, told.moved, len(told.strikes))


def test_the_stall_reproduces_the_recording() -> None:
    situation = vizier.stored(STALL)
    truth = situation.recorded
    assert truth is not None
    assert len(situation.presses) == 48
    assert truth['moved'] == 0.0
    assert truth['gaps'][BOSS] == [57.4, 57.4, 57.4]
    assert truth['boss_dead'][BOSS] is None
    for seed in SEEDS:
        outcome = played(STALL, seed)
        assert outcome.said_count(BOSS_LINE) == 48
        assert outcome.said_count('Attack mode paused') == 47
        assert outcome.moved == 0.0
        assert outcome.gaps[BOSS] == (57.4, 57.4, 57.4)
        assert outcome.boss_dead[BOSS] is None
        assert outcome.stage == 'fight Grand Vizier of Chaos'
        assert not outcome.said_count('Teleport')
        assert not outcome.said_count('Blade Warp')
        assert not outcome.dead


# -- the stall as a base for experiments ----------------------------------------------------------------


@pytest.mark.parametrize('name', list(vizier.experiments()))
def test_an_experiment_plays_and_the_character_lives(name) -> None:
    outcome = tried(name, 1)
    assert outcome.gaps[BOSS] is not None
    assert not outcome.dead


def test_attack_mode_alone_never_goes_to_a_boss_out_of_its_reach() -> None:
    outcome = tried('(c) attack mode alone', 1)
    assert outcome.moved == 0.0
    assert outcome.boss_dead[BOSS] is None


def test_the_seek_key_goes_for_the_boss_and_kills_it() -> None:
    """What the stage lacks, the seek key has: pressed every second it hops to the Vizier and he dies."""
    name = next(name for name in vizier.experiments() if name.startswith('(b) the seek key every'))
    for seed in SEEDS:
        outcome = tried(name, seed)
        assert outcome.boss_dead[BOSS] is not None
        assert outcome.stage != 'fight Grand Vizier of Chaos'


def test_a_pack_made_aware_comes_into_its_own_reach_and_no_nearer() -> None:
    """A Storm Caster thinks by the client's AI 70 (sim/casters.py, 2026-10-13): aware of the character from any
    distance it still comes only from under aip7 (40) and casts from under aip5 (26); the Vizier at 57.4 stands
    (before, as a fitted shooter, it closed to its shot's reach: 29.8)."""
    outcome = tried('(e) aware at any distance, recorded presses', 1)
    assert outcome.gaps[BOSS] == (57.4, 57.4, 57.4)
    assert tried("(e) aware within 35 (the game's radius), recorded presses", 1).gaps[BOSS] == (57.4, 57.4, 57.4)


@pytest.mark.parametrize(('distance', 'dies'), [(12, True), (25, False)])
def test_attack_mode_alone_kills_the_pack_only_within_the_strikes_reach(distance, dies) -> None:
    """In the 14 other recorded games the Vizier appeared 5 to 40 units off and died. Attack mode alone kills
    him where the character stands when he is within the strike's reach, and stands still when he is not
    (pinned as it is today, not asked for)."""
    situation, presses = vizier.distanced(distance)['attack mode alone']
    outcome = situation.play(presses, seed=1)
    assert outcome.gaps[BOSS] is not None
    assert outcome.gaps[BOSS][0] == pytest.approx(distance, abs=0.2)
    assert (outcome.boss_dead[BOSS] is not None) == dies
    assert outcome.moved == 0.0


# The two requirements today's keys do not meet at the stall (repeated presses bring the character to the
# boss; a held key does not keep attack mode from killing a boss in reach) are in test_pursuit_situations.py,
# each over both logics: `today` a strict expected failure, `new` (the pursuit loop on) passing.


# -- the seal: a pack that appears ----------------------------------------------------------------------


def test_the_seal_moment_is_the_takes_own() -> None:
    seal = vizier.stored(SEAL)
    truth = seal.recorded
    assert truth is not None
    assert seal.attack
    assert seal.presses
    assert not seal.opened
    assert [1.64, SEAL_ONE] in truth['opened']  # the seal's change of mode, 73.65 s into the take
    assert truth['boss_dead'][BOSS] == pytest.approx(12.77, abs=0.05)
    spawn = next(spawn for spawn in seal.spawns if spawn.after == SEAL_ONE)
    assert spawn.delay == pytest.approx(0.95, abs=0.05)
    assert len(spawn.mobs) == 6
    assert any(mob.unit == seal.bosses[0][0] for mob in spawn.mobs)


def test_the_pack_appears_after_the_arenas_own_opening_of_the_seal() -> None:
    seal = vizier.stored(SEAL)
    # Since the casters think by the client's code (sim/casters.py, 2026-10-13) the arena's own play does not open
    # the seal within the window in every seed (it did before): the pack is looked at where it was opened, early
    # enough for it to appear in the window (with the ward played, seed 2 opens it at 15.1 s of 16).
    opened_in = [
        outcome
        for outcome in (played(SEAL, seed) for seed in SEEDS)
        if SEAL_ONE in outcome.opened and outcome.opened[SEAL_ONE] + 1.0 <= outcome.seconds
    ]
    assert len(opened_in) >= len(SEEDS) // 2
    for outcome in opened_in:
        opened = outcome.opened[SEAL_ONE]
        (at, _label, count), *_ = [row for row in outcome.appeared if 'Storm Caster' in row[1]]
        assert count == 6
        assert at == pytest.approx(opened + 0.95, abs=0.06)
        assert outcome.gaps[BOSS] is not None  # he was there and seen
        assert outcome.hostiles > len(
            [mob for mob in seal.scene.mobs if mob.owner is None and not mob.ally and mob.life > 0]
        )
        assert not outcome.dead


def test_a_scripted_spawn_at_a_second_puts_a_pack_into_a_built_situation() -> None:
    built = Situation.on(open_field(40)).attack_mode(True)
    built.spawn('Hell Bovine', 4, at=east(8), at_second=1.0)
    outcome = built.play(seconds=6.0, seed=1)
    assert outcome.appeared == [(pytest.approx(1.0, abs=0.05), '4 Hell Bovine', 4)]
    assert outcome.hostiles == 4
    assert outcome.strikes
    assert outcome.strikes[0] > 1.0


# -- the constructed example ----------------------------------------------------------------------------


def test_the_example_reads_as_the_player_said_it() -> None:
    built = example()
    hero = built.scene.hero
    assert hero.life == pytest.approx(0.30 * hero.max_life)
    assert built.attack
    assert len(built.scene.drops) == 1
    packs = {}
    for mob in built.scene.mobs:
        packs.setdefault(mob.txt, []).append(math.dist(mob.at, hero.at))
    assert len(packs) == 4
    assert all(min(found) >= 13 and max(found) <= 23 for found in packs.values())


@pytest.mark.xdist_group('situations: the example to a death')
def test_the_character_can_die_in_the_example_and_the_story_says_how() -> None:
    situation, presses = variants()['attack on']
    trials = situation.trials(range(1, 9), presses)
    dead = [play for play in trials.outcomes if play.dead]
    print(f'\nfour packs at 30% life, attack on: {len(dead)} of {len(trials.outcomes)} seeds die')
    assert dead, 'no seed of eight dies at 30% life'
    told = story(dead[0])
    assert 'attack mode on' in told.splitlines()[0]
    assert 'DIES' in told
    assert dead[0].killers
    assert dead[0].hurts
    assert dead[0].life[-1][1] == 0.0


@functools.cache
def variant_played(name: str) -> Outcome:
    situation, presses = variants()[name]
    return situation.play(presses, seconds=3.0, seed=4)


@pytest.mark.xdist_group("situations: the example's variants")
def test_every_variant_of_the_example_runs() -> None:
    for name in variants():
        assert variant_played(name).hostiles == 24, name


# The variants that press the pickup key and the teleport key beside the attack mode: between them every routine the
# arena plays, and so every memory of the production code a play could leave to the next (driver.py `fresh`).
PRESSED = ('attack on + pickup key at 0.5 s', 'attack on + KP_4 held (every 0.3 s) toward a mark beyond the Souls')


@pytest.mark.xdist_group("situations: the example's variants")
def test_the_example_plays_the_same_twice() -> None:
    """The arena is deterministic for a seed: a second play of the same situation, presses and seed is the first.
    One test for the harness (`Situation.play`: `Stage` and `RoutePlay` over driver.py `Play`, every roll from the
    seed); the per-scene repeats of the Vizier's moments, the Chaos Sanctuary run, the teleport key's moments, the
    incidents and the threat scenes were merged into it (rca/2026-10-19/cleanup/tests.md P5). Ten plays of one seed by
    driver.py's `play` are test_driver.py's."""
    assert all(name in variants() for name in PRESSED)
    for name in PRESSED:
        situation, presses = variants()[name]
        assert situation.play(presses, seconds=3.0, seed=4) == variant_played(name), name


# -- the viewer's files ---------------------------------------------------------------------------------


def test_the_catalog_lists_the_fixtures_and_the_example_with_their_variants() -> None:
    from tests.inventory_tracking.scenarios.arena.situations.catalog import catalog

    found = catalog()
    assert [(entry.name, entry.kind) for entry in found.values()] == [
        (STALL, 'recorded'), (SEAL, 'recorded'), ('pocket', 'recorded'), ('seal-pack', 'recorded'),
        ('four-packs', 'constructed'), ('cs-run', 'recorded'), ('diablo-fight', 'recorded'),
        ('baal-fight', 'constructed'), ('throne-waves', 'recorded'), ('ancients-way', 'recorded'),
    ]  # fmt: skip
    # the same scene and presses by today's keys and by the pursuit loop, side by side (Tab in the viewer)
    for name in (STALL, SEAL, 'pocket', 'seal-pack', 'diablo-fight', 'baal-fight', 'throne-waves', 'ancients-way'):
        labels = [label for label, _, _ in found[name].variants()]
        pairs = [label for label in labels if label.endswith(': today')]
        assert pairs
        assert all(labels[labels.index(label) + 1] == label.removesuffix('today') + 'new' for label in pairs)
        logic = {label: situation.pursuit for label, situation, _ in found[name].variants()}
        assert all(logic[label] == label.endswith(': new') for label in labels)
    assert all(entry.fixture is None or (FIXTURES / entry.fixture).exists() for entry in found.values())
    assert found['four-packs'].variants()[0][0] == 'attack on'


def test_a_situation_exports_as_the_viewers_file_with_a_debug_track_a_run(tmp_path, monkeypatch) -> None:
    from inventory_tracking.builds.warlock import mark as mark_module
    from tests.inventory_tracking.scenarios.arena.situations import export_viz

    # The death this export is checked with came after a Death Mark on the doll, cast with no demon out: since
    # 2026-10-14 the skill is not cast without one (builds/warlock/mark.py), and the strike alone outlives the blast.
    # The mark as it was, for a run that dies.
    monkeypatch.setattr(mark_module, 'why_not', lambda facts, monster: None)
    from tests.inventory_tracking.scenarios.arena.situations.catalog import Entry

    def two() -> list:
        base = example()
        return [('attack on', base, []), ('attack off', base.variant(attack=False, seconds=4.0), [])]

    row = export_viz.write(Entry('two', 'constructed', 'a test', two), tmp_path, seed=3)
    data = __import__('json').loads((tmp_path / row['file']).read_text())
    assert data['schema'] == 1
    assert [run['name'] for run in data['runs']] == [
        'recorded',
        '1. attack on',
        '2. attack off',
    ]
    first, off = data['runs'][1], data['runs'][2]
    assert first['casts']
    assert first['tracks']
    assert first['player']['k']
    debug = first['debug']
    assert debug['death'] is not None
    assert 'Undead Stygian Doll blast' in debug['death']['cause']
    assert debug['lines'][0][1] == 'Attack mode on'
    assert debug['presses'][0][1] == 'KP_3 attack mode'
    assert debug['life'][:2] == [0, 535]  # the scene's life at tick 0
    assert debug['tasks'][0][0] == 0
    assert first['summary']['died']['at'] == pytest.approx(1.88, abs=0.05)
    assert off['summary']['died'] is None
    assert debug['tasks'][0][1]['attack'] is True
    assert debug['tasks'][0][1]['what'] == 'attack mode'
    assert off['debug']['tasks'][0][1] == {
        'attack': False,
        'routine': None,
        'working': False,
        'what': 'idle',
        'sweep': 0,
    }
    assert {item['kind'] for item in first['objects']} == {'drop', 'mark'}
    assert len(data['monsters']) == 24
    assert all(str(m['unit']) in first['tracks'] for m in data['monsters'])
