"""The scenes cut from the host's takes (fixtures/, written by build_scenes.py) and the cutter's own parts."""

import random
import shutil
from math import hypot
from pathlib import Path

import pytest

from inventory_tracking.combat.takes import Take
from inventory_tracking.macros.world import LYING_DEAD
from tests.inventory_tracking.scenarios.arena import moments as rules
from tests.inventory_tracking.scenarios.arena.build_scenes import (
    FIXTURES,
    SCENE_FILE,
    belt_keys,
    burst_kind,
    bursts,
    main,
)
from tests.inventory_tracking.scenarios.arena.mobs import Mobs
from tests.inventory_tracking.scenarios.arena.scene import Scene, load


TOWER = Path(__file__).parents[1] / 'battle' / 'fixtures' / 'tower-cellar5-herald'
RECORDING = '20261011T195037Z-25'  # the take the fixture was trimmed from
SCENES = sorted(path for path in FIXTURES.glob('*.json') if SCENE_FILE.fullmatch(path.name))
KINDS = ('death', 'burst', 'potions', 'stuck', 'long', 'burst15', 'fixed')
FIXED = [path for path in SCENES if path.stem.endswith('-fixed')]
BUDGET = 2 * 1024 * 1024  # bytes: the whole set (framework-plan.md, Task 1.8)


@pytest.fixture(scope='module')
def tower() -> Take:
    return Take.load(TOWER)


def test_the_set_is_there_and_within_its_budget():
    assert len(SCENES) >= 20
    assert sum(path.stat().st_size for path in SCENES) < BUDGET
    assert {path.stem.rsplit('-', 1)[1] for path in SCENES} <= set(KINDS)
    assert any(path.stem.endswith('-death') for path in SCENES)
    assert len(FIXED) >= 40


@pytest.mark.parametrize('path', SCENES, ids=lambda path: path.stem)
def test_a_fixture_is_a_sound_scene_whose_monsters_play(path: Path):
    scene = load(path)
    hero = scene.hero
    take, frame, _kind = path.stem.rsplit('-', 2)
    assert scene.name == path.stem
    assert scene.source is not None
    assert (scene.source['take'], scene.source['frame']) == (take, int(frame))
    assert 0 < hero.life <= hero.max_life  # a death scene starts before the death, not at it
    assert scene.ground
    assert {'belt', 'sets', 'slots'} <= set(scene.assumed)
    live = [mob for mob in scene.mobs if mob.owner is None and not mob.ally and mob.mode != LYING_DEAD and mob.life > 0]
    assert live
    assert all(mob.level > 0 and 0 < mob.life <= mob.full for mob in live)
    mobs = Mobs(scene, random.Random(1))
    assert sorted(mobs.live()) == sorted(mob.unit for mob in live)
    companions = [mob.at for mob in scene.mobs if mob.owner is not None or mob.ally]
    for _ in range(50):
        assert mobs.tick(hero.at, companions, hero.sets[hero.hand].resist) >= 0.0


@pytest.mark.parametrize('path', FIXED, ids=lambda path: path.stem)
def test_a_fixed_scene_is_a_fight_with_the_character_alive(path: Path):
    scene = load(path)
    hero = scene.hero
    assert 0 < hero.life <= hero.max_life  # the vitals were read at the frame, not assumed
    near = [
        mob for mob in scene.mobs
        if mob.owner is None and not mob.ally and mob.mode != LYING_DEAD and mob.life > 0
        and hypot(mob.at[0] - hero.at[0], mob.at[1] - hero.at[1]) <= 30.0
    ]  # fmt: skip
    assert len(near) >= 3
    assert scene.ground
    mobs = Mobs(scene, random.Random(2))
    assert mobs.tick(hero.at, [], hero.sets[hero.hand].resist) >= 0.0


def test_the_belt_keys_are_five_to_two_before_the_six(tower):
    assert tower.manifest['keys']['15'] == '6'
    assert belt_keys(tower) == frozenset((10, 11, 12, 13))
    assert belt_keys(Take(TOWER, {'keys': {'38': 'a'}})) == frozenset()
    # The three potions of the take's last seconds ("Drinking (3)" in its log) are found with them.
    assert [m.kind for m in rules.moments(tower, belt_keys=belt_keys(tower))] == ['long', 'potions', 'burst', 'death']


def frames(lives: list[int], most: int = 1000) -> Take:
    """A take of a frame each tenth of a second with the character's life as given."""
    rows = [
        {'t': 10.0 + index / 10, 'n': index, 'p': [1, 1, 25, 0.0, 0.0, 0, 388, life, most, 0, 0], 'm': [], 'x': []}
        for index, life in enumerate(lives)
    ]
    return Take(Path('/nowhere/take'), {'schema': 2}, rows)


def test_a_lighter_burst_is_found_at_a_lower_share_and_the_rule_is_put_back():
    take = frames([1000] * 40 + [800] * 40)  # a fifth of the life in one frame
    assert [m for m in rules.moments(take) if m.kind == 'burst'] == []
    found = bursts(take, 0.15)
    assert [(m.kind, m.frame, m.at) for m in found] == [('burst', 10, 4.0)]  # placed moments.py LEAD before it
    assert bursts(take, 0.25) == []
    assert rules.BURST_SHARE == 0.3
    assert (burst_kind(rules.BURST_SHARE), burst_kind(0.15)) == ('burst', 'burst15')


def host(tmp_path: Path) -> tuple[Path, Path]:
    """The Tower Cellar fixture laid out as the host has a take and its session: runs/combat/<take>/
    and runs/alt-d/<session>/probe.log."""
    root, session = tmp_path / 'combat', tmp_path / 'alt-d' / '20261011T193238Z-a000e98b'
    shutil.copytree(TOWER, root / RECORDING)
    session.mkdir(parents=True)
    shutil.move(root / RECORDING / 'probe.log', session / 'probe.log')
    return root, session.parent


def run(root: Path, probe: Path, out: Path, *more: str) -> dict[str, Scene]:
    assert main(['--root', str(root), '--probe', str(probe), '--out', str(out), *more]) == 0
    return {path.stem: load(path) for path in sorted(out.glob('*.json'))}


def test_the_cli_cuts_a_scene_for_each_kind_of_moment_of_a_take(tmp_path, capsys):
    root, probe = host(tmp_path)
    scenes = run(root, probe, tmp_path / 'out', '--burst-share', '0.3', '0.15')
    # The burst is the death's own frame (the blow that killed), so it is cut once, as the death.
    assert sorted(scenes) == [
        f'{RECORDING}-{frame}-{kind}' for frame, kind in ((2, 'long'), (295, 'stuck'), (373, 'potions'), (493, 'death'))
    ]
    assert scenes[f'{RECORDING}-493-death'].hero.life == 995.0
    assert scenes[f'{RECORDING}-493-death'].source == {'take': RECORDING, 'frame': 493, 't': 20.042}
    printed = capsys.readouterr().out
    assert 'the frame of a death scene 1' in printed
    assert '4 scenes' in printed


def test_the_cli_gives_the_same_files_again_and_clears_what_it_wrote_before(tmp_path):
    root, probe = host(tmp_path)
    out = tmp_path / 'out'
    run(root, probe, out)
    first = {path.name: path.read_bytes() for path in out.iterdir()}
    (out / 'notes.json').write_text('{}')  # not a scene's name: left alone
    (out / '20260101T000000Z-1-5-long.json').write_text('{}')  # a scene of a take that is gone
    assert main(['--root', str(root), '--probe', str(probe), '--out', str(out)]) == 0
    assert {path.name: path.read_bytes() for path in out.iterdir() if path.name != 'notes.json'} == first
    assert (out / 'notes.json').exists()


def test_the_cli_counts_what_cut_refuses_and_keeps_to_its_limits(tmp_path, capsys):
    root, probe = host(tmp_path)
    (root / RECORDING / 'level.json.gz').unlink()
    assert run(root, probe, tmp_path / 'out') == {}
    assert 'no level file 1' in capsys.readouterr().out
    shutil.copy(TOWER / 'level.json.gz', root / RECORDING / 'level.json.gz')
    assert sorted(run(root, probe, tmp_path / 'out', '--per-kind', '0')) == [f'{RECORDING}-493-death']  # deaths: all
    assert run(root, probe, tmp_path / 'out', '--since', '20261012') == {}
    assert len(run(root, tmp_path / 'no-sessions', tmp_path / 'out')) == 3  # no log: no stuck


def test_the_cli_adds_fixed_scenes_and_keep_leaves_the_others_alone(tmp_path):
    root, probe = host(tmp_path)
    out = tmp_path / 'out'
    plain = run(root, probe, out)
    before = {path.name: path.read_bytes() for path in out.iterdir()}
    again = run(root, probe, tmp_path / 'again', '--fixed', '0')
    assert sorted(again) == sorted(plain)  # --fixed 0 is today's behaviour
    both = run(root, probe, tmp_path / 'both', '--fixed', '3')
    assert {name: path for name, path in both.items() if not name.endswith('-fixed')}.keys() == plain.keys()
    assert all(
        (tmp_path / 'both' / f'{name}.json').read_bytes() == before[f'{name}.json'] for name in plain
    )  # the other kinds come out byte for byte the same
    added = [name for name in both if name.endswith('-fixed')]
    assert added
    assert all(scene.source['take'] == RECORDING for scene in (both[name] for name in added))
    assert not set(added) & {name.rsplit('-', 1)[0] + '-fixed' for name in plain}  # a frame is cut once
    # --keep adds only the fixed ones to a directory and leaves its files as they are.
    assert main(['--root', str(root), '--probe', str(probe), '--out', str(out), '--fixed', '3', '--keep']) == 0
    after = {path.name: path.read_bytes() for path in out.iterdir()}
    assert {name: data for name, data in after.items() if name in before} == before
    assert sorted(set(after) - set(before)) == sorted(f'{name}.json' for name in added)
