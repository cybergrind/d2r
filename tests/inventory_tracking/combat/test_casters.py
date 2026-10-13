"""sim/casters.py: the Chaos Sanctuary's types as the client's code and the game's tables play them."""

import math

import pytest

from inventory_tracking.combat.sim import casters
from inventory_tracking.combat.sim.casters import (
    CAST,
    DOOM_KNIGHT,
    FINGER_MAGE,
    MEGADEMON,
    OBLIVION_KNIGHT,
    SPELL,
    STRIKE,
    ai_distance,
    curse,
    curse_radius,
    doom_knight,
    hit_chance,
    megademon,
    mind_for,
    mind_of,
    missile_damage,
    missile_step,
    oblivion_knight,
    resisted,
    row_of,
    skill_calc,
)
from inventory_tracking.combat.sim.monsters import MELEE, Pack, Walker


STORM_CASTER, DOOM, OBLIVION, VENOM_LORD = 306, 310, 312, 362


def test_the_four_ais_are_the_rows_the_client_was_read_for():
    assert {txt: mind_of(txt) for txt in (STORM_CASTER, DOOM, OBLIVION, VENOM_LORD)} == {
        STORM_CASTER: FINGER_MAGE, DOOM: DOOM_KNIGHT, OBLIVION: OBLIVION_KNIGHT, VENOM_LORD: MEGADEMON,
    }  # fmt: skip
    assert mind_of(21) is None  # a Devilkin keeps the fit
    # notes-ai.md, notes-ai-74.md, notes-mobs.md: the Hell rows the routines were matched on
    assert [row_of(STORM_CASTER)[f'aip{n}(H)'] for n in range(1, 9)] == ['60', '95', '70', '50', '26', '5', '40', '8']
    assert [row_of(OBLIVION)[f'aip{n}(H)'] for n in range(1, 9)] == ['8', '27', '200', '50', '90', '30', '30', '11']
    assert [row_of(VENOM_LORD)[f'aip{n}(H)'] for n in range(1, 7)] == ['90', '65', '97', '70', '70', '45']


def test_skill_levels_are_the_row_and_hells_bonus_as_the_takes_show():
    # notes-mobs.md section 4: the skill records hold 12 (306), 15 (362), 10 (312's bolt), 9 (its bone spirit)
    assert mind_for(STORM_CASTER).level[1] == 12
    assert mind_for(VENOM_LORD).level[1] == 15
    assert (mind_for(OBLIVION).level[1], mind_for(OBLIVION).level[3], mind_for(OBLIVION).level[6]) == (10, 9, 10)


@pytest.mark.parametrize(
    ('missile', 'level', 'expected'),
    [
        (177, 12, {'physical': (12.5, 15.5), 'fire': (38.0, 41.0)}),  # notes-mobs.md: fingermagespider
        (675, 15, {'fire': (45.0, 62.0)}),  # megademoninferno
        (329, 9, {'magic': (82.0, 87.0)}),  # monbonespirit
        (326, 10, {'physical': (97.0, 101.0)}),
        (324, 10, {'fire': (121.0, 130.0)}),
    ],
)
def test_a_missiles_points_by_level_follow_the_rows_breakpoints(missile, level, expected):
    assert missile_damage(missile, level) == pytest.approx(expected)


def test_poison_of_the_bolt_is_points_a_frame_with_its_hitshift_empty():
    # undeadmissile1: EMin 10 + 7 x 12 + 2 x 14 = 122, HitShift empty: 122 / 256 a frame, for ELen 350 frames
    assert missile_damage(323, 10)['poison'][0] == pytest.approx(122 / 256)


def test_a_missile_goes_its_vel_times_the_measured_step():
    assert missile_step(323) == pytest.approx(0.96)
    assert missile_step(177) == pytest.approx(0.288)


def test_the_curses_at_level_ten_are_the_takes_readings():
    lower = curse('Lower Resist', 10, 0)
    assert lower.resists == {'fire': -55, 'lightning': -55, 'cold': -55, 'poison': -55}  # dm56: -55 seen
    assert curse('Amplify Damage', 10, 0).resists == {'physical': -100}
    decrepify = curse('Decrepify', 10, 100)
    assert decrepify.resists == {'physical': -50}
    assert decrepify.until == 100 + 235  # ln34: 100 + 15 x 9
    assert curse_radius('Decrepify', 10) == 6
    assert curse_radius('MonCurseCast', 10) == 12
    caster = casters.data()['skills']['MonCurseCast']
    assert skill_calc(caster, caster['auralencalc'], 10) == 840


def test_a_curse_moves_the_resistance_before_the_cap():
    shares = {'fire': 0.25, 'physical': 0.9}
    raw = {'fire': 90.0}
    assert resisted(shares, curse('Lower Resist', 10, 0), raw)['fire'] == pytest.approx(0.65)
    assert resisted(shares, curse('Lower Resist', 10, 0))['fire'] == pytest.approx(0.80)  # with no raw: the cap
    assert resisted(shares, curse('Amplify Damage', 10, 0))['physical'] == pytest.approx(1.9)
    assert resisted(shares, None) == shares


def test_a_doom_knights_swing_hits_the_character_82_percent():
    assert hit_chance(row_of(DOOM), 82) == pytest.approx(0.825, abs=0.005)  # notes-mobs.md section 4


def test_the_ai_distance_is_max_plus_half_min():
    assert ai_distance((0, 0), (10, 4)) == 12
    assert ai_distance((0, 0), (0, 7)) == 7


def rolls(*values):
    found = iter(values)
    return lambda: next(found)


def test_the_doom_knight_always_swings_in_melee_and_mostly_walks_out_of_it():
    mind = mind_for(DOOM)
    assert doom_knight(mind, rolls(99), melee=True) == ('attack',)
    assert doom_knight(mind, rolls(89), melee=False) == ('approach',)
    assert doom_knight(mind, rolls(90), melee=False) == ('idle', 10)


def test_the_venom_lord_casts_under_its_skill_level_and_cools_off():
    mind = mind_for(VENOM_LORD)
    assert megademon(mind, rolls(89), d=14, melee=False, frame=100) == ('cast', 1)
    mind.cool = 200
    assert megademon(mind, rolls(10), d=14, melee=False, frame=150) == ('approach',)
    assert megademon(mind, rolls(10), d=15, melee=False, frame=300) == ('approach',)  # 15 is not under 15


def test_the_oblivion_knight_decrepifies_within_eight_and_retreats_when_it_is_on():
    mind = mind_for(OBLIVION)
    act = oblivion_knight(mind, rolls(), d=5, cursed=False, knight=False, seen=True, e=5, frame=10)
    assert act == ('cast', 4)
    assert mind.cool == 210
    assert oblivion_knight(mind, rolls(), d=5, cursed=True, knight=False, seen=True, e=5, frame=20)[0] == 'retreat'
    assert oblivion_knight(mind, rolls(), d=5, cursed=True, knight=True, seen=True, e=5, frame=20) == ('hide',)
    # Beyond 8 with the cool-off running: no curse roll; 90 % a missile, of those 30 % the bone spirit.
    assert oblivion_knight(mind, rolls(10, 20), d=15, cursed=True, knight=False, seen=True, e=15, frame=50) == (
        'cast', 3, 'seen',
    )  # fmt: skip
    assert oblivion_knight(mind, rolls(10, 50), d=15, cursed=True, knight=False, seen=True, e=15, frame=50) == (
        'cast', 1, 'seen',
    )  # fmt: skip
    # The cool-off over: half the thinks curse.
    assert oblivion_knight(mind, rolls(49), d=15, cursed=False, knight=False, seen=True, e=15, frame=300) == ('cast', 6)


def played(txt, away, frames, *, companions=()):
    walker = Walker(1, txt, 100.0 + away, 100.0)
    pack = Pack([walker], seed=3)
    blows = []
    for frame in range(frames):
        blows += pack.step(frame, [(100.0, 100.0), *companions])
    return walker, pack, blows


def test_a_storm_caster_within_its_range_casts_about_every_two_seconds_and_its_lead_lands():
    walker, pack, blows = played(STORM_CASTER, 15.0, 25 * 20)
    casts = [cast for cast in pack.minds.casts if cast[3] == 'FingerMageSpider']
    assert 0.35 <= len(casts) / 20 <= 0.5  # cs-patterns.txt: 0.39 to 0.47 a second; 39 + 13 frames a cast
    assert walker.doing in (CAST, 'stand', 'walk')
    spells = [blow for blow in blows if blow.kind == SPELL and blow.target == 0]
    assert spells
    assert all(blow.missile == 177 for blow in spells)
    assert set(spells[0].parts) == {'physical', 'fire'}


def test_nobody_beyond_the_radius_is_a_target():
    walker, pack, blows = played(STORM_CASTER, 40.0, 25 * 5)
    assert pack.minds.casts == []
    assert blows == []
    assert walker.at == (140.0, 100.0)


def test_the_nearest_body_is_the_target_a_companion_too():
    _walker, _pack, blows = played(DOOM, 2.0, 25 * 5, companions=[(102.5, 100.0)])
    assert blows
    assert {blow.target for blow in blows if blow.kind == MELEE} == {1}


def test_a_venom_lords_flames_burn_whom_they_pass_once_each():
    _walker, pack, blows = played(VENOM_LORD, 8.0, 25 * 4)
    flames = [blow for blow in blows if blow.missile == 675]
    born = [birth for birth in pack.minds.births if birth[3] == 675]
    assert born
    assert len(flames) == len([b for b in born if b[0] < 25 * 4 - 15])  # each flame once, all through
    assert all(45 <= blow.damage <= 62 for blow in flames)


def test_a_doom_knight_comes_and_swings():
    walker, _pack, blows = played(DOOM, 12.0, 25 * 6)
    assert math.dist(walker.at, (100.0, 100.0)) < 3.2
    assert any(blow.kind == MELEE for blow in blows)
    assert walker.doing in (STRIKE, 'stand', 'walk', 'stagger')


def test_the_old_model_comes_back_with_played_off(monkeypatch):
    monkeypatch.setattr(casters, 'PLAYED', False)
    assert Walker(1, VENOM_LORD, 0.0, 0.0).mind is None
