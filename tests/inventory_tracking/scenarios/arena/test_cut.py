"""A frame of a take as an arena scene (cut.py): what comes from the take, what from the defaults, what is refused."""

import json
import math
import random
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.builds.characters import CHARACTERS
from inventory_tracking.builds.warlock.skills import ECHOING_STRIKE
from inventory_tracking.combat.mechanics.tables import area_level, points_of, tables
from inventory_tracking.combat.takes import Take
from inventory_tracking.levels.model import Walkable
from inventory_tracking.macros.rotation import ELITE_LIFE
from inventory_tracking.macros.world import LYING_DEAD, NO_OWNER
from inventory_tracking.native.layout import HEALING_POTIONS, REJUVENATION_POTIONS
from tests.inventory_tracking.scenarios.arena.cut import (
    ALWAYS_ASSUMED,
    CORPSE_RANGE,
    DEFAULT_HERO,
    MAIN,
    STAFF,
    Refused,
    cut,
    hand_of,
    near,
)
from tests.inventory_tracking.scenarios.arena.mobs import Mobs
from tests.inventory_tracking.scenarios.arena.scene import dump, load
from tests.inventory_tracking.scenarios.stance.build_fixtures import ground_near, level_grids


# Tower Cellar 5, 2026-10-11 22:50 (scenarios/battle/tower_cellar5.py): frames 0 to 700 of the take
# 20261011T195037Z-25 with its level file, the fight with a tier 2 Herald the character died in.
TOWER = Path(__file__).parents[1] / 'battle' / 'fixtures' / 'tower-cellar5-herald'
BEFORE = 493  # the frame 3 s before the death (moments.py places the death there)
HERALD, MINION_OF_IT = 2960229440, 92505634  # the elite Blood Clan and one of its nine
BLOOD_CLAN, DEVILKIN, MERCENARY = 55, 21, 338  # txt ids, as the take's rows have them
AREA = 25
HERE = (5020.0, 5020.0)
GRID = {'x': 1000, 'y': 1000, 'width': 8, 'height': 8, 'cells': '', 'flight': ''}  # world 5000 to 5040


@pytest.fixture(scope='module')
def tower() -> Take:
    return Take.load(TOWER)


def made(tmp_path: Path, *, p=None, m=(), schema=2, level=True, area=AREA, units=(), events=(), **manifest) -> Take:
    """A take of one frame in a directory of its own, with a level file of one grid round HERE."""
    if level:
        (tmp_path / 'level.json').write_text(json.dumps({'area': area, 'rooms': [], 'ground': [GRID]}))
    if p is None:
        p = [1, 1, AREA, *HERE, 0, 388, 900, 1800, 400, 500]
    frame = {'t': 100.0, 'n': 0, 'p': p, 'm': list(m), 'x': [], 'd': [[7, 13, 0, 5010.0, 5010.0]]}
    return Take(tmp_path, {'schema': schema, 'character': 'Someone', **manifest}, [frame], list(events), list(units))


def monster(unit: int, dx: float = 5.0, *, mode: int = 1, life: int = 64, most: int = 128, flags: int = 0) -> list:
    return [unit, BLOOD_CLAN, mode, HERE[0] + dx, HERE[1], life, most, flags, NO_OWNER, 0]


def test_the_hero_is_the_frames_and_the_rest_the_defaults(tower):
    scene = cut(tower, BEFORE, defaults=DEFAULT_HERO)
    hero = scene.hero
    assert (hero.at, hero.area) == ((12592.74, 11108.99), AREA)
    assert (hero.life, hero.max_life, hero.mana, hero.max_mana) == (995.0, 1783.0, 503.0, 503.0)
    assert hero.name == tower.manifest['character']
    assert (hero.left_skill, hero.right_skill) == (0, ECHOING_STRIKE)  # the mouse buttons, as the frame has them
    assert (hero.belt, hero.sets, hero.slots) == (DEFAULT_HERO.belt, DEFAULT_HERO.sets, DEFAULT_HERO.slots)
    assert scene.name == 'tower-cellar5-herald-493'
    assert scene.source == {'take': 'tower-cellar5-herald', 'frame': BEFORE, 't': 20.042}
    assert scene.drops == []
    # The take is of 19:50 UTC, before the resistances were recorded: the set in hand is not known.
    assert scene.assumed == tuple(sorted((*ALWAYS_ASSUMED, 'hand')))


def test_a_name_given_is_the_scenes(tower):
    assert cut(tower, BEFORE, defaults=DEFAULT_HERO, name='the death').name == 'the death'


def test_a_hostile_has_its_units_level_enchantments_and_tier_and_its_share_of_the_types_points(tower):
    mobs = {mob.unit: mob for mob in cut(tower, BEFORE, defaults=DEFAULT_HERO).mobs}
    herald, minion = mobs[HERALD], mobs[MINION_OF_IT]
    boosts = tables()['heralds']['2']
    assert (herald.txt, herald.level, herald.tier, herald.mods, herald.flags) == (BLOOD_CLAN, 75, 2, (30, 28, 17), 8)
    assert herald.level != area_level(AREA)  # the unit's own (stat 12), not the area's 79
    assert herald.full == points_of(BLOOD_CLAN, AREA) * ELITE_LIFE * (1 + boosts['life'] / 100)
    assert herald.life == pytest.approx(herald.full * 92 / 128, abs=0.1)  # 92 of 128 in the frame
    assert (minion.tier, minion.mods, minion.flags) == (2, (28, 17), 16)
    assert minion.full == points_of(BLOOD_CLAN, AREA) * (1 + boosts['minion_life'] / 100)
    assert not {herald.owner, minion.owner, herald.ally, minion.ally} - {None, False}


def test_companions_are_kept_with_the_rows_own_numbers(tower):
    mobs = cut(tower, BEFORE, defaults=DEFAULT_HERO).mobs
    mercenary = next(mob for mob in mobs if mob.txt == MERCENARY)
    assert mercenary.owner == tower.frames[BEFORE]['p'][0]
    assert mercenary.ally
    assert (mercenary.life, mercenary.full, mercenary.level) == (128.0, 2367.0, 0)
    assert sum(1 for mob in mobs if mob.ally) == 3  # the mercenary and two allies no unit owns


def test_corpses_near_the_character_are_kept_as_recorded(tower):
    scene = cut(tower, BEFORE, defaults=DEFAULT_HERO)
    corpses = [mob for mob in scene.mobs if mob.mode == LYING_DEAD]
    assert len(corpses) == 21
    assert all(mob.life == 0.0 and mob.full > 0 for mob in corpses)
    assert all(math.dist(mob.at, scene.hero.at) <= CORPSE_RANGE for mob in corpses)
    assert Mobs(scene, random.Random(1)).corpses()  # what Engorge is cast on


def test_the_ground_is_what_the_stance_cutter_keeps_and_a_smaller_reach_keeps_less(tower):
    scene = cut(tower, BEFORE, defaults=DEFAULT_HERO)
    assert scene.ground == ground_near(level_grids(tower), scene.hero.at)
    assert len(scene.ground) == len(scene.rooms) == 11
    assert all('masks' not in grid and Walkable(**grid).cells for grid in scene.ground)
    small = cut(tower, BEFORE, defaults=DEFAULT_HERO, reach=20.0)
    assert len(small.ground) == 4
    assert len(small.mobs) < len(scene.mobs)
    assert near([GRID], (5100.1, 5020.0), 60.0) == []
    assert near([GRID], (5100.0, 5020.0), 60.0) == [GRID]


def test_a_scene_goes_to_json_and_back_and_its_monsters_play(tower, tmp_path):
    scene = cut(tower, BEFORE, defaults=DEFAULT_HERO)
    dump(scene, tmp_path / 'scene.json')
    assert load(tmp_path / 'scene.json') == scene
    mobs = Mobs(scene, random.Random(1))
    assert len(mobs.live()) == 11
    for _ in range(50):
        mobs.tick(scene.hero.at, [], scene.hero.sets[scene.hero.hand].resist)


def test_doors_are_the_frames_rows(tmp_path):
    scene = cut(made(tmp_path, m=[monster(5)]), 0, defaults=DEFAULT_HERO)
    assert scene.doors == [[7, 13, 0, 5010.0, 5010.0]]
    assert (scene.hero.name, scene.hero.mana, scene.hero.max_mana) == ('Someone', 400.0, 500.0)


def test_a_monster_far_off_without_a_place_or_out_of_life_is_left_out(tmp_path):
    rows = [monster(1), monster(2, 61.0), monster(3, life=0), [4, BLOOD_CLAN, 1, 0.0, 0.0, 128, 128, 0, NO_OWNER, 0]]
    rows += [monster(5, 39.0, mode=LYING_DEAD, life=0), monster(6, 41.0, mode=LYING_DEAD, life=0)]
    scene = cut(made(tmp_path, m=rows), 0, defaults=DEFAULT_HERO)
    assert [mob.unit for mob in scene.mobs] == [1, 5]


def test_what_the_units_do_not_say_is_assumed_and_named(tmp_path):
    scene = cut(made(tmp_path, m=[monster(1)]), 0, defaults=DEFAULT_HERO)
    assert {'level', 'mods', 'tier', 'hand'} <= set(scene.assumed)
    assert (scene.mobs[0].level, scene.mobs[0].mods, scene.mobs[0].tier) == (area_level(AREA), (), 0)
    assert scene.mobs[0].life == pytest.approx(points_of(BLOOD_CLAN, AREA) / 2, abs=0.1)


def test_a_units_row_gives_level_tier_and_enchantments(tmp_path):
    unit = {'unit': 1, 'txt': BLOOD_CLAN, 'stats': {'12': 88, '367': 3}, 'mods': [5, 17]}
    scene = cut(made(tmp_path, m=[monster(1)], units=[unit]), 0, defaults=DEFAULT_HERO)
    assert (scene.mobs[0].level, scene.mobs[0].tier, scene.mobs[0].mods) == (88, 3, (5, 17))
    assert not {'level', 'mods', 'tier'} & set(scene.assumed)


def test_enchantments_from_the_probe_log_are_taken_where_the_take_has_none(tmp_path):
    unit = {'unit': 1, 'txt': BLOOD_CLAN, 'stats': {'12': 88}}
    take = made(tmp_path, m=[monster(1), monster(2)], units=[unit, {**unit, 'unit': 2}])
    scene = cut(take, 0, defaults=DEFAULT_HERO, mods={1: (9,), 2: ()})
    assert [mob.mods for mob in scene.mobs] == [(9,), ()]
    assert 'mods' not in scene.assumed
    assert 'mods' in cut(take, 0, defaults=DEFAULT_HERO, mods={1: (9,)}).assumed  # unit 2 is in neither


def test_a_life_share_not_read_is_full_life_and_assumed(tmp_path):
    scene = cut(made(tmp_path, m=[monster(1, life=0, most=0)]), 0, defaults=DEFAULT_HERO)
    assert scene.mobs[0].life == scene.mobs[0].full
    assert 'life' in scene.assumed


def test_the_set_in_hand_is_the_one_the_resistances_read_fit(tmp_path):
    # combat/plan.md 2026-10-12 02:10: the staff's set reads fire 154, lightning 108, cold 118; the main 190/179/189.
    staff = {'36': 10, '39': 154, '41': 108, '43': 118, '45': 124}
    take = made(tmp_path, m=[monster(1)], character_stats=staff)
    scene = cut(take, 0, defaults=DEFAULT_HERO)
    assert scene.hero.hand == DEFAULT_HERO.sets.index(STAFF)
    assert 'hand' not in scene.assumed
    # A `hurt` up to the frame is a later reading than the take's start; one after the frame is not looked at.
    hurt = {'t': 99.0, 'event': 'hurt', 'resists': [10, 190, 179, 189, 195]}
    swapped = replace(take, events=[hurt, {**hurt, 't': 101.0, 'resists': [10, 154, 108, 118, 124]}])
    assert cut(swapped, 0, defaults=DEFAULT_HERO).hero.hand == DEFAULT_HERO.sets.index(MAIN)
    # Since schema 3 a frame holds the resistances where they change: the frame's is the reading at it.
    framed = replace(take, frames=[{**take.frames[0], 'r': [10, 190, 179, 189, 195]}, *take.frames[1:]])
    assert cut(framed, 0, defaults=DEFAULT_HERO).hero.hand == DEFAULT_HERO.sets.index(MAIN)
    # Amplify Damage and the rest raised (Outer Cloister, 2026-10-12 01:31): still the main set.
    assert hand_of([-90, 190, 179, 189, 195], DEFAULT_HERO.sets) == DEFAULT_HERO.sets.index(MAIN)


@pytest.mark.parametrize(
    ('changes', 'frame', 'reason'),
    [
        ({}, 1, 'no such frame'),
        ({'p': []}, 0, 'no character row'),
        ({'schema': 1, 'p': [1, 1, AREA, *HERE, 0, 388]}, 0, 'no vitals (schema 1)'),
        ({'schema': 1}, 0, 'no vitals (schema 1)'),  # vitals of the wrong stats (takes.py SCHEMAS)
        ({'p': [1, 1, AREA, *HERE, 0, 388, 0, 0, 0, 0]}, 0, 'vitals not read'),
        ({'p': [1, 1, AREA, *HERE, 0, 388, 0, 1800, 0, 500]}, 0, 'the character is dead'),
        ({'p': [1, 17, AREA, *HERE, 0, 388, 5, 1800, 0, 500]}, 0, 'the character is dead'),
        ({'level': False}, 0, 'no level file'),
        ({'area': AREA + 1}, 0, 'another area'),
        ({'p': [1, 1, AREA, 9000.0, 9000.0, 0, 388, 900, 1800, 400, 500]}, 0, 'no ground near'),
    ],
)
def test_a_frame_that_cannot_make_a_sound_scene_is_refused_with_the_reason(tmp_path, changes, frame, reason):
    with pytest.raises(ValueError, match=tmp_path.name) as refusal:
        cut(made(tmp_path, m=[monster(1)], **changes), frame, defaults=DEFAULT_HERO)
    assert isinstance(refusal.value, Refused)
    assert refusal.value.reason == reason


def test_the_default_hero_is_the_character_the_repo_knows():
    hero = DEFAULT_HERO
    assert hero.name in CHARACTERS
    assert frozenset(hero.sets[0].codes) == CHARACTERS[hero.name].battle
    assert len(hero.belt) == 16
    assert set(hero.belt[:2]) <= REJUVENATION_POTIONS
    assert set(hero.belt[2:4]) <= HEALING_POTIONS
    assert [found.teleport_charges for found in hero.sets] == [None, 69]
    assert ECHOING_STRIKE in hero.slots
    assert hero.hand == 0
    # macros/hunt.py `Hunter.tough`: the main set at the cap, the teleport set lightning 8 and cold 18 in Hell.
    # physical 10 since 2026-10-12: the manifests of 13 takes with this set in hand (evidence/EVIDENCE.md, section 11)
    assert MAIN.resist == {'fire': 0.25, 'cold': 0.25, 'lightning': 0.25, 'physical': 0.9}
    assert (STAFF.resist['lightning'], STAFF.resist['cold']) == (0.92, 0.82)
    assert (STAFF.resist['fire'], STAFF.resist['physical']) == (0.46, 0.9)  # combat/plan.md: fire 54, physical 10
