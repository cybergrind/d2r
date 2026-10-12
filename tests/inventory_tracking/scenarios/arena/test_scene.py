"""Round trip, copy and refusal tests for the arena scene records."""

import json
from pathlib import Path

import pytest

from tests.inventory_tracking.scenarios.arena.scene import Drop, Hero, Mob, Scene, WeaponSet, dump, load


def make_scene() -> Scene:
    """A small scene: two mobs (one a companion), a hero with a belt, two weapon sets, a drop."""
    belt: tuple[int | None, ...] = (1, None, 3, None, None, 7) + (None,) * 10
    return Scene(
        name='arena-test',
        hero=Hero(
            name='Warlock',
            at=(100.0, 200.0),
            area=74,
            life=300.0,
            max_life=350.0,
            mana=120.0,
            max_mana=150.0,
            belt=belt,
            sets=(
                WeaponSet(codes=('ssp', 'ktr'), resist={'fire': 0.5, 'cold': 1.0}, teleport_charges=69),
                WeaponSet(codes=('lbb',), resist={'lightning': 0.25}),
            ),
            hand=1,
            slots=(None, 36, None),
            hex_purge=False,
            ward=None,
            consume=True,
        ),
        mobs=[
            Mob(unit=1, txt=255, at=(110.0, 210.0), level=85, life=500.0, full=900.0, flags=4, mods=(12, 40), tier=2),
            Mob(
                unit=2, txt=290, at=(105.0, 205.0), level=80, life=50.0, full=50.0, owner=None, ally=True, immune=False
            ),
        ],
        ground=[{'w': 2, 'h': 2, 'cells': [1, 1, 0, 1]}],
        doors=[[12, 34, 0]],
        drops=[Drop(unit=9, code='rune', at=(111.0, 211.0), quality=0, gold=0)],
        assumed=('belt',),
        source={'take': 'take-3', 'frame': 1200, 't': 20.5},
    )


def test_a_scene_round_trips_through_its_file(tmp_path: Path) -> None:
    scene = make_scene()
    scene.mobs[1].owner = 1
    path = tmp_path / 'scene.json'
    dump(scene, path)

    loaded = load(path)

    assert loaded == scene
    assert isinstance(loaded.hero.at, tuple)
    assert isinstance(loaded.hero.belt, tuple)
    assert isinstance(loaded.hero.slots, tuple)
    assert isinstance(loaded.hero.sets, tuple)
    assert all(isinstance(s, WeaponSet) for s in loaded.hero.sets)
    assert isinstance(loaded.hero.sets[0].codes, tuple)
    assert isinstance(loaded.mobs[0], Mob)
    assert isinstance(loaded.mobs[0].at, tuple)
    assert isinstance(loaded.mobs[0].mods, tuple)
    assert isinstance(loaded.drops[0], Drop)
    assert isinstance(loaded.drops[0].at, tuple)
    assert isinstance(loaded.assumed, tuple)
    assert loaded.hero.sets[0].teleport_charges == 69
    assert loaded.source == {'take': 'take-3', 'frame': 1200, 't': 20.5}
    assert path.read_text(encoding='utf-8').endswith('}\n')


def test_a_copy_shares_nothing_with_the_scene() -> None:
    scene = make_scene()
    copied = scene.copy()

    copied.mobs.append(Mob(unit=3, txt=1, at=(0.0, 0.0), level=1, life=1.0, full=1.0))
    copied.mobs[0].at = (1.0, 1.0)
    copied.hero.life = 1.0
    copied.ground[0]['cells'][0] = 9
    copied.doors[0][0] = 99

    assert len(scene.mobs) == 2
    assert scene.mobs[0].at == (110.0, 210.0)
    assert scene.hero.life == 300.0
    assert scene.ground == [{'w': 2, 'h': 2, 'cells': [1, 1, 0, 1]}]
    assert scene.doors == [[12, 34, 0]]


def test_an_unknown_key_is_refused_by_name(tmp_path: Path) -> None:
    path = tmp_path / 'scene.json'
    dump(make_scene(), path)
    data = json.loads(path.read_text(encoding='utf-8'))
    data['mobs'][0]['foo'] = 1
    path.write_text(json.dumps(data), encoding='utf-8')

    with pytest.raises(ValueError, match='foo'):
        load(path)


def test_a_missing_field_is_refused_by_name(tmp_path: Path) -> None:
    path = tmp_path / 'scene.json'
    dump(make_scene(), path)
    data = json.loads(path.read_text(encoding='utf-8'))
    del data['mobs'][0]['life']
    path.write_text(json.dumps(data), encoding='utf-8')

    with pytest.raises(ValueError, match="'life'"):
        load(path)
