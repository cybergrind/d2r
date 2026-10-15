"""calibrate.py: the parts of a calibration on data whose answer is known, one real take that is in
git, and that the host's report covers the fixtures. The calibration of the fixtures themselves is
run on the host (the recordings are not in git): `python -m ...arena.calibrate`."""

import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.combat.sim.monsters import MELEE, spread as size_factor
from inventory_tracking.combat.takes import Take
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.macros.world import FULL_REJUVENATION, LYING_DEAD, NO_OWNER
from tests.inventory_tracking.scenarios.arena.build_scenes import FIXTURES, SCENE_FILE
from tests.inventory_tracking.scenarios.arena.calibrate import (
    BEYOND_NOTE,
    BIG,
    MIN_TAKEN,
    MOSTLY_NOTE,
    REPORT,
    STRANGER_REACH,
    VERDICTS,
    WINDOW,
    Fit,
    Replay,
    Row,
    attributed,
    big_falls,
    big_table,
    calibrate,
    compare,
    dominant,
    heaviest,
    life_lost,
    main,
    play,
    pooled,
    recorded,
    spread,
    type_name,
)
from tests.inventory_tracking.scenarios.arena.evidence.sure import sure
from tests.inventory_tracking.scenarios.arena.mobs import Mobs
from tests.inventory_tracking.scenarios.arena.scene import Scene, load
from tests.inventory_tracking.scenarios.arena.scenes_basic import (
    AREA,
    BELT,
    HELL_BOVINE,
    HERE,
    LIFE,
    RETURNED_ARCHER,
    hero,
    mob,
)


TICKS = round(WINDOW * GAME_RATE)
# Tower Cellar 5, 2026-10-11: frames 0 to 700 of the take the death scene was cut from, in git
# (scenarios/battle/fixtures; test_cut.py cuts the same frame of it).
TOWER = Path(__file__).parents[1] / 'battle' / 'fixtures' / 'tower-cellar5-herald'
DEATH = '20261011T195037Z-25-493-death'
SIX = 15  # the key code of `6` in the takes' manifests; the belt keys are the four from five before it


# --- the life lost ------------------------------------------------------------------------------------


def test_the_life_lost_is_the_sum_of_the_falls():
    assert life_lost([(1000, 1800), (900, 1800), (900, 1800), (850, 1800)]) == 150


def test_a_potion_between_two_blows_hides_nothing():
    assert life_lost([(1000, 1800), (700, 1800), (1300, 1800), (1100, 1800)]) == 500


def test_a_frame_not_read_is_skipped_and_the_fall_across_it_counted():
    # The recorder's failed read is life 0 of 0: not a fall to nothing and a rise back.
    assert life_lost([(1000, 1800), (0, 0), None, (930, 1800)]) == 70
    assert life_lost([None, (0, 0)]) == 0
    assert life_lost([]) == 0


def test_a_fall_of_the_most_life_is_not_a_blow():
    # Consume ran out: 1475 of 1813 becomes 1283 of 1576, the same share (20261011T001816Z-131).
    assert life_lost([(1475, 1813), (1283, 1576)]) <= 1
    # ... and a blow in the same tick is what fell beyond the share.
    assert life_lost([(1800, 1800), (1500, 1600)]) == 100
    # At a death the whole life was the blow's (Tower Cellar 5: 1051 of 1783 to 0 of 1540).
    assert life_lost([(1051, 1783), (0, 1540)]) == 1051


# --- the ratios and the verdict -----------------------------------------------------------------------


def fit(taken_take=400.0, taken_arena=400.0, kills_take=4, kills_arena=4, seconds=WINDOW) -> Fit:
    return Fit('a scene', seconds, taken_take, taken_arena, kills_take, kills_arena)


def test_both_ratios_within_the_bounds_are_trust():
    assert fit().trusted
    assert fit(taken_arena=800.0, kills_arena=2).trusted  # the bounds themselves are within
    assert (fit(taken_arena=800.0).taken_ratio, fit(kills_arena=2).kills_ratio) == (2.0, 0.5)


@pytest.mark.parametrize(
    'found',
    [fit(taken_arena=801.0), fit(taken_arena=199.0), fit(kills_arena=9), fit(kills_arena=1), fit(taken_arena=0.0)],
)
def test_a_ratio_outside_the_bounds_is_none(found: Fit):
    assert not found.trusted


def test_a_take_that_barely_hurt_gives_no_ratio_and_no_trust():
    found = fit(taken_take=MIN_TAKEN - 1, taken_arena=MIN_TAKEN - 1)
    assert found.taken_ratio is None
    assert not found.trusted
    assert fit(taken_take=MIN_TAKEN, taken_arena=MIN_TAKEN).trusted


def test_no_kills_in_either_agree_and_kills_only_in_the_arena_do_not():
    assert fit(kills_take=0, kills_arena=0).kills_ratio == 1.0
    assert fit(kills_take=0, kills_arena=0).trusted
    ratio = fit(kills_take=0, kills_arena=2).kills_ratio
    assert ratio is not None
    assert math.isinf(ratio)
    assert not fit(kills_take=0, kills_arena=2).trusted
    assert fit(kills_take=3, kills_arena=0).kills_ratio == 0.0
    assert fit(seconds=0.0).kills_ratio is None


# --- like with like: the take's drops that have a suspect -------------------------------------------------


def test_the_verdict_goes_by_the_drops_with_a_suspect_where_the_take_was_attributed():
    raw = fit(taken_take=400.0, taken_arena=150.0)
    assert (raw.taken_blamed, raw.blamed_ratio, raw.life_ratio) == (None, None, raw.taken_ratio)
    assert not raw.trusted  # 0.375 of all the take lost
    like = replace(raw, taken_blamed=200.0)  # half of what the take lost was no blow
    assert (like.taken_ratio, like.blamed_ratio, like.life_ratio) == (0.375, 0.75, 0.75)
    assert like.trusted


def test_a_take_whose_blows_barely_hurt_gives_no_ratio_of_like_with_like():
    found = replace(fit(taken_take=400.0, taken_arena=100.0), taken_blamed=MIN_TAKEN - 1)
    assert found.taken_ratio == 0.25
    assert found.blamed_ratio is None
    assert found.life_ratio is None
    assert not found.trusted


def test_pooled_like_with_like_is_over_the_drops_with_a_suspect():
    fits = [replace(fit(100.0, 300.0), taken_blamed=50.0), replace(fit(0.0, 100.0), taken_blamed=0.0)]
    assert pooled(fits) == 4.0
    assert pooled(fits, True) == 8.0
    assert pooled([fit(0.0, 100.0)], True) is None  # not attributed: nothing to pool over


# --- a recording made by hand -------------------------------------------------------------------------

UNIT, STRANGER, CHARACTER = 7, 8, 1
FAR = (HERE[0] + 100.0, HERE[1])  # beyond what a monster goes for: it stands, in the take and in the arena


def far_scene(life: float = 1000.0) -> Scene:
    """One Hell Bovine a hundred units off: nothing happens in the arena."""
    scene = Scene('20261012T000000Z-101-0-burst', hero(life), [mob(UNIT, HELL_BOVINE, 100.0, 0.0)], [], [])
    scene.source = {'take': '20261012T000000Z-101', 'frame': 0, 't': 0.0}
    return scene


def frames(lives, *, dies_at: int | None = None, stranger_at: int | None = None, at=HERE) -> list[dict]:
    """A take's frames, one a game tick: `lives` is (life, most life) by tick; the scene's monster lies
    dead from `dies_at`; a hostile the scene does not hold stands beside the character from `stranger_at`."""
    found = []
    for tick, (life, most) in enumerate(lives):
        mode = LYING_DEAD if dies_at is not None and tick >= dies_at else 1
        monsters = [[UNIT, HELL_BOVINE, mode, *FAR, 0 if mode == LYING_DEAD else 128, 128, 0, NO_OWNER, 0]]
        if stranger_at is not None and tick >= stranger_at:
            monsters.append([STRANGER, HELL_BOVINE, 1, at[0] + 2.0, at[1], 128, 128, 0, NO_OWNER, 0])
        found.append(
            {
                't': 1000.0 + tick / GAME_RATE, 'n': tick + 1, 'late': 0,
                'p': [CHARACTER, 0 if life <= 0 and most else 1, AREA, *at, 0, 388, life, most, 100, 100],
                'm': monsters, 'x': [], 'd': [], 'in': [0, 0, 0, None, None, []],
            }
        )  # fmt: skip
    return found


def take_of(rows: list[dict], events: list[dict] | None = None) -> Take:
    manifest = {'schema': 2, 'rate': GAME_RATE, 'area': AREA, 'character': 'x', 'keys': {str(SIX): '6'}}
    return Take(Path('20261012T000000Z-101'), manifest, rows, events or [])


def steady(ticks: int = TICKS + 25, life: int = 1000) -> list[tuple[int, int]]:
    return [(life, 1800)] * (ticks + 1)


def test_a_made_recording_gives_the_answer_it_was_made_with():
    lives = steady()
    for tick in range(10, len(lives)):
        lives[tick] = (900, 1800)  # a blow of 100
    for tick in range(20, len(lives)):
        lives[tick] = (1200, 1800)  # a potion
    for tick in range(30, len(lives)):
        lives[tick] = (1150, 1800)  # a blow of 50
    lives[40] = (0, 0)  # not read
    for tick in range(41, len(lives)):
        lives[tick] = (1080, 1800)  # a blow of 70 behind the frame not read
    for tick in range(50, len(lives)):
        lives[tick] = (960, 1600)  # the most life fell and the life with it: no blow
    kill = {'t': 1000.0 + 60 / GAME_RATE, 'event': 'kill', 'unit': UNIT, 'txt': HELL_BOVINE}
    found = calibrate(far_scene(), take_of(frames(lives, dies_at=60), [kill]))
    assert found.scene == '20261012T000000Z-101-0-burst'
    assert found.seconds == WINDOW
    assert found.taken_take == 220
    assert (found.taken_arena, found.kills_arena) == (0, 0)
    assert found.kills_take == 1
    assert (found.taken_ratio, found.kills_ratio) == (0.0, 0.0)
    assert not found.trusted


def test_a_quiet_recording_and_a_quiet_arena_have_nothing_to_measure():
    found = calibrate(far_scene(), take_of(frames(steady())))
    assert (found.taken_take, found.taken_arena, found.kills_take, found.kills_arena) == (0, 0, 0, 0)
    assert found.taken_ratio is None
    assert not found.trusted
    assert any('no ratio' in note for note in found.notes)


def test_the_window_ends_where_the_recording_leaves_the_scene():
    lives = steady()
    for tick in range(120, len(lives)):
        lives[tick] = (500, 1800)  # the stranger's blow: not the scene's to explain
    replay = recorded(far_scene(), take_of(frames(lives, stranger_at=100)))
    assert replay.ticks == 99
    assert replay.left_at == 100
    assert life_lost(replay.vitals) == 0
    assert any(f'within {STRANGER_REACH:.0f} of the character at 4.0 s' in note for note in replay.notes)
    stayed = recorded(far_scene(), take_of(frames(lives, stranger_at=100)), leave=False)
    assert (stayed.ticks, stayed.left_at) == (TICKS, 100)
    assert life_lost(stayed.vitals) == 500


def test_the_window_ends_at_the_characters_death_with_the_blow_that_killed():
    lives = steady()
    for tick in range(50, len(lives)):
        lives[tick] = (0, 1800)
    replay = recorded(far_scene(), take_of(frames(lives)))
    assert (replay.ticks, replay.dead_at) == (50, 50)
    assert life_lost(replay.vitals) == 1000
    assert any('died in the take at 2.0 s' in note for note in replay.notes)


def test_the_window_ends_with_the_take():
    replay = recorded(far_scene(), take_of(frames(steady(100))))
    assert replay.ticks == 100
    assert any('the take ends or leaves the level at 4.0 s' in note for note in replay.notes)


def test_the_belt_keys_of_the_take_are_the_replays_drinks():
    press = {'t': 1000.0 + 25 / GAME_RATE, 'event': 'keys', 'down': [SIX - 5 + 2, SIX], 'up': []}
    late = {'t': 1000.0 + (TICKS + 10) / GAME_RATE, 'event': 'keys', 'down': [SIX - 5], 'up': []}
    replay = recorded(far_scene(), take_of(frames(steady()), [press, late]))
    assert replay.drinks == [(25, 3)]  # the third column; `6` is no belt key, the late one is past the window
    unnamed = take_of(frames(steady()), [press])
    unnamed.manifest.pop('keys')
    replay = recorded(far_scene(), unnamed)
    assert replay.drinks == []
    assert any('belt keys are not known' in note for note in replay.notes)


def test_where_the_character_stood_is_the_replays_place_tick_by_tick():
    rows = frames(steady())
    for tick, row in enumerate(rows):
        row['p'][3] = HERE[0] + tick * 0.1
    replay = recorded(far_scene(), take_of(rows))
    assert len(replay.hero) == TICKS + 1
    assert replay.hero[0] == HERE
    assert replay.hero[100] == pytest.approx((HERE[0] + 10.0, HERE[1]))


def test_a_scene_without_a_source_is_refused():
    scene = far_scene()
    scene.source = None
    with pytest.raises(ValueError, match='without a source'):
        recorded(scene, take_of(frames(steady())))


# --- the arena over a replay --------------------------------------------------------------------------


def contact(life: float = 1e6, **more) -> Scene:
    """A Hell Bovine in contact with a character no blow kills."""
    scene = Scene('contact', hero(), [mob(UNIT, HELL_BOVINE, 1.5, 0.0, **more)], [], [])
    scene.hero = replace(scene.hero, life=life, max_life=max(life, LIFE))
    return scene


def standing(ticks: int = 100, at=HERE, **more) -> Replay:
    return Replay(ticks, [at] * (ticks + 1), [None] * (ticks + 1), **more)


def test_a_monster_in_contact_strikes_the_character_where_the_replay_has_it():
    played = play(contact(), standing(), seed=5)
    assert played.blows
    assert {(txt, kind) for _tick, txt, kind, _points in played.blows} == {(HELL_BOVINE, 'melee')}
    assert life_lost(played.samples) == pytest.approx(sum(points for *_blow, points in played.blows))
    assert life_lost(played.samples) == pytest.approx(played.taken)
    assert len(played.life) == 101
    assert (played.kills, played.dead_at, played.deaths) == ({}, None, 0)


def test_the_character_is_put_where_the_recording_has_it_not_walked_there():
    away = (HERE[0] + 300.0, HERE[1])
    replay = standing()
    replay.hero = [HERE, *[away] * 100]
    assert play(contact(), replay).blows == []


def test_a_replayed_cast_takes_the_monsters_life_and_it_dies():
    scene = contact()
    scene.mobs[0].life = 1.0
    target = scene.mobs[0].at
    idle = play(scene, standing())
    assert idle.kills == {}
    played = play(scene, standing(casts=[(5, target)]))
    assert list(played.kills) == [UNIT]
    assert 5 <= played.kills[UNIT] <= 30
    # A cast whose blades were in the air before the scene's frame still lands.
    assert list(play(scene, standing(casts=[(-3, target)])).kills) == [UNIT]


def test_a_death_in_the_arena_is_noted_and_the_rest_of_the_window_still_measured(monkeypatch):
    sure(monkeypatch)  # every swing lands: 50 points of life do not last the window
    scene = contact(50.0)
    scene.hero = replace(scene.hero, life=50.0, max_life=LIFE)
    replay = standing(200)
    played = play(scene, replay)
    assert played.dead_at is not None
    assert played.deaths >= 1
    assert len(played.life) == 201  # played on to the window's end
    assert life_lost(played.samples) > 50
    found = compare(scene, replay, played)
    assert found.seconds == 8.0
    assert any('died in the arena' in note for note in found.notes)


def test_a_replayed_belt_key_is_drunk_from_the_scenes_belt():
    scene = contact()
    scene.hero = replace(scene.hero, life=100.0, max_life=LIFE)
    scene.mobs[0].at = FAR
    column = BELT.index(FULL_REJUVENATION) + 1  # scenes_basic.py BELT: the third column
    played = play(scene, standing(drinks=[(10, column)]))
    assert played.life[9][0] == 100.0
    assert played.life[10][0] == LIFE


def test_the_hand_follows_the_replay(monkeypatch):
    sure(monkeypatch)  # every shot lands, with the same rolls under either set
    scene = Scene('archer', hero(), [mob(UNIT, RETURNED_ARCHER, 10.0, 0.0)], [], [])
    scene.hero = replace(scene.hero, life=1e6, max_life=1e6)
    main_set = sum(points for *_blow, points in play(scene, standing(200)).blows)
    staff = sum(points for *_blow, points in play(scene, standing(200, hands=[(1, 1)])).blows)
    assert staff > main_set > 0  # the staff's set lets more of the cold through (scenes_basic.py STAFF)


def test_the_fits_factor_scales_every_blow():
    whole, half = play(contact(), standing()), play(contact(), standing(), damage_scale=0.5)
    assert half.taken == pytest.approx(whole.taken / 2)
    assert life_lost(half.samples) == pytest.approx(life_lost(whole.samples) / 2)


def test_a_play_is_the_same_twice_and_another_with_another_seed():
    assert play(contact(), standing()).blows == play(contact(), standing()).blows
    assert play(contact(), standing(), seed=4).blows != play(contact(), standing(), seed=5).blows


def test_the_heaviest_blow_is_the_top_roll_of_the_scenes_monsters_at_the_top_of_the_fitted_spread():
    scene = contact()
    # Since the refit a blow is the table's roll times a factor drawn through the takes' quantiles
    # (sim.monsters `spread`): its top is 5.0 times the mean of the drops one monster dealt alone.
    top = Mobs._walker(scene.mobs[0]).traits.damage[1] * size_factor(MELEE, 1.0)
    assert size_factor(MELEE, 1.0) == pytest.approx(4.994)
    assert heaviest(scene) == pytest.approx(top)
    blows = [points for seed in range(1, 9) for *_blow, points in play(scene, standing(2000), seed=seed).blows]
    assert len(blows) > 20
    assert max(blows) <= heaviest(scene)


def test_the_drops_of_a_replay_are_classed_by_the_rows_given_and_the_unblamed_ones_noted():
    scene, replay = contact(), standing()
    replay.vitals = [*[(LIFE, LIFE)] * 10, *[(LIFE - 300.0, LIFE)] * 10, *[(LIFE - 400.0, LIFE)] * (TICKS - 19)]
    played = play(scene, replay)
    assert compare(scene, replay, played).taken_blamed is None  # not attributed: the raw comparison only
    replay.classed = [(10, 300.0, 'unknown'), (20, 100.0, 'sole melee')]
    found = compare(scene, replay, played)
    assert (found.taken_take, found.taken_blamed) == (400.0, 100.0)
    assert any(note.startswith(MOSTLY_NOTE) for note in found.notes)
    replay.classed = [(10, 300.0, 'several'), (20, 100.0, 'unknown')]
    found = compare(scene, replay, played)
    assert found.taken_blamed == 300.0
    assert not any(note.startswith(MOSTLY_NOTE) for note in found.notes)


def test_the_big_drops_are_counted_on_both_sides():
    scene, replay = contact(), standing()
    replay.classed = [(10, BIG, 'several'), (20, BIG + 50, 'unknown'), (30, BIG - 1, 'sole melee')]
    played = play(scene, replay)
    played.life = [(1800.0, 1800.0), (1800.0 - BIG, 1800.0), (1800.0 - BIG - 299.0, 1800.0), (1800.0, 1800.0)]
    assert big_falls(played) == 1
    text = '\n'.join(big_table([Row(scene, [fit()], replay, played, [1])]))
    assert '| the takes, all | 2 |' in text
    assert '| the takes, with a suspect | 1 |' in text
    assert '| the arena, mean of 1 seeds | 1.0 |' in text


def test_a_drop_of_the_take_beyond_any_blow_of_the_arena_is_noted():
    scene, replay = contact(), standing()
    replay.drops = [(10, heaviest(scene) * 3, None)]
    noted = compare(scene, replay, play(scene, replay)).notes
    assert any(note.startswith(BEYOND_NOTE) for note in noted)
    replay.drops = [(10, heaviest(scene), None)]
    assert not any(note.startswith(BEYOND_NOTE) for note in compare(scene, replay, play(scene, replay)).notes)


# --- a real take ----------------------------------------------------------------------------------------


@pytest.fixture(scope='module')
def tower() -> Take:
    return Take.load(TOWER)


def test_the_death_scene_against_its_take(tower: Take):
    scene = load(FIXTURES / f'{DEATH}.json')
    replay = recorded(scene, tower)
    # The take: a potion at 1.16 s, 57 points lost at 1.12 s, and one drop of 1051 at 3.0 s that killed.
    assert (replay.ticks, replay.dead_at) == (76, 76)
    assert replay.drinks == [(29, 4)]
    assert [(tick, points) for tick, points, _txt in replay.drops] == [(28, 57.0), (75, 1051.0)]
    found = compare(scene, replay, play(scene, replay))
    assert found.seconds == pytest.approx(3.04)
    assert found.taken_take == 1108
    assert (found.kills_take, found.kills_arena) == (0, 0)
    assert any('died in the take at 3.0 s' in note for note in found.notes)
    # Before the refit of the monsters no monster of the scene dealt in the arena what killed the
    # character in the take (370 at most: the note of a blow the arena cannot deal). Since it, the
    # Herald's blow at the top of the fitted spread is over the 1,051 points, so the note is gone;
    # how seldom that blow comes is CALIBRATION.md's and evidence/refit_check.py's to say.
    assert heaviest(scene) >= 1051
    assert not any(note.startswith(BEYOND_NOTE) for note in found.notes)
    assert calibrate(scene, tower) == found
    # Like with like: both drops of the window have a suspect in the take.
    rows = attributed(tower)
    like = calibrate(scene, tower, rows=rows)
    assert like.taken_blamed == 1108
    classed = recorded(scene, tower, rows=rows).classed
    assert classed is not None
    assert [group for _tick, _points, group in classed] == ['several', 'several']


def test_the_cli_writes_the_report_and_the_verdicts(tower: Take, tmp_path: Path):
    root, fixtures = tmp_path / 'takes', tmp_path / 'fixtures'
    root.mkdir()
    fixtures.mkdir()
    (root / '20261011T195037Z-25').symlink_to(TOWER, target_is_directory=True)
    (fixtures / f'{DEATH}.json').write_text((FIXTURES / f'{DEATH}.json').read_text())
    probes = tmp_path / 'probes'  # no probe logs: the take's own `mods` are all the enchantments known
    probes.mkdir()
    assert main(['--root', str(root), '--fixtures', str(fixtures), '--seeds', '2', '--probes', str(probes)]) == 0
    text = (fixtures / REPORT.name).read_text()
    assert f'| {DEATH} | death | ' in text
    assert f'## The death: {DEATH}' in text
    assert '| 3.00 | 1051 |' in text
    assert '### Like with like' in text
    assert '## The big drops' in text
    # Not trusted: the arena takes far less in these three seconds than the 1,108 points of the take.
    assert json.loads((fixtures / VERDICTS.name).read_text()) == {DEATH: False}


def test_a_take_that_is_not_there_fails_the_cli_and_writes_nothing(tmp_path: Path):
    fixtures = tmp_path / 'fixtures'
    fixtures.mkdir()
    (fixtures / f'{DEATH}.json').write_text((FIXTURES / f'{DEATH}.json').read_text())
    assert main(['--root', str(tmp_path / 'none'), '--fixtures', str(fixtures), '--probes', str(tmp_path)]) == 1
    assert not (fixtures / REPORT.name).exists()


# --- the report's parts ---------------------------------------------------------------------------------


def test_the_spread_is_the_count_the_ends_and_the_quartiles():
    assert spread([]) == '0 | - | - | - | - | -'
    assert spread([2.0]) == '1 | 2.00 | 2.00 | 2.00 | 2.00 | 2.00'
    assert spread([4.0, 0.0, 1.0, 2.0, 3.0]) == '5 | 0.00 | 1.00 | 2.00 | 3.00 | 4.00'


def test_pooled_is_all_the_arenas_points_over_all_the_takes():
    assert pooled([fit(100.0, 300.0), fit(0.0, 100.0)]) == 4.0
    assert pooled([fit(0.0, 100.0)]) is None


def test_the_dominant_type_is_the_one_most_hostiles_are_of_and_is_named_by_the_tables():
    mobs = [mob(1, RETURNED_ARCHER, 5, 0), mob(2, HELL_BOVINE, 6, 0), mob(3, HELL_BOVINE, 7, 0)]
    mobs.append(mob(4, RETURNED_ARCHER, 8, 0, life=0.0, mode=LYING_DEAD))  # a corpse is no hostile
    scene = Scene('mixed', hero(), mobs, [], [])
    assert dominant(scene) == HELL_BOVINE
    assert type_name(HELL_BOVINE) == f'Hell Bovine ({HELL_BOVINE})'
    assert type_name(10**6) == 'type 1000000'


def test_a_row_is_trusted_only_with_every_seed_and_no_blow_beyond_the_arena():
    scene = contact()
    good, bad = fit(), fit(taken_arena=2000.0)
    beyond = replace(good, notes=(f'{BEYOND_NOTE}: a drop of 1051 points in the take, at most 370 a blow',))
    replay, played = standing(), play(scene, standing(1))
    assert Row(scene, [good, good], replay, played).trusted
    assert not Row(scene, [good, bad], replay, played).trusted
    assert good.trusted
    assert not bad.trusted
    assert beyond.trusted  # the bare rule of the two ratios
    assert not Row(scene, [beyond, beyond], replay, played).trusted


# --- the host's report ----------------------------------------------------------------------------------


def test_the_calibration_report_is_current():
    """The report and the verdicts written on the host name every fixture cut from a recording. (The
    calibration itself is not run again here: the recordings are not in git.)"""
    assert REPORT.exists(), 'run: uv run --offline python -m tests.inventory_tracking.scenarios.arena.calibrate'
    text = REPORT.read_text(encoding='utf-8')
    verdicts = json.loads(VERDICTS.read_text(encoding='utf-8'))
    sourced = [
        path.stem
        for path in sorted(FIXTURES.glob('*.json'))
        if SCENE_FILE.fullmatch(path.name) and json.loads(path.read_text(encoding='utf-8')).get('source')
    ]
    assert sourced
    missing = [name for name in sourced if f'| {name} |' not in text]
    assert not missing, f'not in {REPORT.name}: {missing}'
    assert sorted(verdicts) == sourced
    assert all(isinstance(verdict, bool) for verdict in verdicts.values())
    assert '## What this says' in text
