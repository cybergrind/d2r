"""sparks.py on takes made by hand (synthetic.py): what a take's sparks are tallied into, what tallies
measure, and the report from them."""

import math

import pytest

from inventory_tracking.combat.hurts import LIGHTNING
from inventory_tracking.combat.sim.monsters import UNIQUE_FLAG
from inventory_tracking.macros.world import HERALD_TIER_STAT, MINION_FLAG
from inventory_tracking.terror.monsters import LEVEL_STAT
from tests.inventory_tracking.scenarios.arena.evidence import blows, sparks
from tests.inventory_tracking.scenarios.arena.evidence.blows import SOLE_RANGED
from tests.inventory_tracking.scenarios.arena.evidence.synthetic import (
    MELEE_TXT,
    RATE,
    born,
    flying,
    frame,
    monster,
    take,
    write,
)


LEADER, MINION, PLAIN = 7, 8, 9
HERO_AT, LEADER_AT = (100.0, 100.0), (110.0, 100.0)
RELEASE, FRAMES = 3, 20
STEPS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))  # a unit a frame, one to each 45 degrees
WEST = 4  # the spark that flies at the character
ENDS = RELEASE + 8  # the frame the west spark is last seen in, two units from the character


def spark_take(name='20261011T120000Z-25', hurt=0, struck=(2, 3), released=True):
    """A Lightning Enchanted unique ten units east of the character that loses life in the frames `struck`
    and lets eight sparks go at RELEASE (`released`), one of which ends on the character, which loses
    `hurt` points in the frame after; a minion with the enchantment that is struck and lets none go; a
    monster without it that is struck too."""
    frames, firsts = [], []
    for index in range(FRAMES):
        foes = [
            monster(LEADER, at=LEADER_AT, flags=UNIQUE_FLAG),
            monster(MINION, at=(120.0, 110.0), flags=MINION_FLAG),
            monster(PLAIN, at=(125.0, 90.0)),
        ]
        foes[0][5] = 128 - 8 * sum(index >= hit for hit in struck)
        foes[1][5] = 128 if index < 2 else 100
        foes[2][5] = 128 if index < 5 else 64
        flights = []
        for number, (dx, dy) in enumerate(STEPS):
            age = index - RELEASE
            if not released or age < 0 or (number == WEST and index > ENDS):
                continue
            flights.append(flying(50 + number, sparks.SPARK, (LEADER_AT[0] + dx * age, LEADER_AT[1] + dy * age)))
        frames.append(frame(index, 1000 - (hurt if index > ENDS else 0), foes, flights, at=HERO_AT))
    if released:
        firsts = [born(RELEASE, 50 + number, sparks.SPARK, LEADER) for number in range(len(STEPS))]
    units = [
        {'unit': LEADER, 'txt': MELEE_TXT, 'mods': [LIGHTNING], 'stats': {str(LEVEL_STAT): 80}},
        {'unit': MINION, 'txt': MELEE_TXT, 'mods': [LIGHTNING], 'stats': {str(LEVEL_STAT): 80}},
        {'unit': PLAIN, 'txt': MELEE_TXT, 'mods': [], 'stats': {str(LEVEL_STAT): 80, str(HERALD_TIER_STAT): 0}},
    ]
    return take(frames, missiles=firsts, units=units, name=name)


def tallied(found):
    moments = list(blows.walk(found))
    rows = blows.blows(found, None, moments)
    return sparks.tally(found.directory.name, moments, rows, blows.Roster(found))


def test_the_missile_is_the_one_the_model_lets_go():
    assert sparks.SPARK == sparks.SPARK_MISSILE
    assert sparks.tables()['missiles'][str(sparks.SPARK)]['Missile'] == 'lightunique'


def test_a_take_is_tallied_into_its_charged_monsters_with_their_hits():
    found = tallied(spark_take())
    assert found['seconds'] == pytest.approx((FRAMES - 1) / RATE)
    monsters = {m['unit']: m for m in found['monsters']}
    assert set(monsters) == {LEADER, MINION}  # the one without the enchantment is not watched
    leader, minion = monsters[LEADER], monsters[MINION]
    assert (leader['rank'], leader['level'], leader['tier'], leader['mods']) == ('unique', 80, 0, [LIGHTNING])
    assert [hit[:3] for hit in leader['hits']] == [[2, 8, 10.0], [3, 8, 10.0]]
    assert (minion['rank'], [hit[:2] for hit in minion['hits']]) == ('minion', [[2, 28]])
    assert leader['seconds'] == leader['near'] == pytest.approx((FRAMES - 1) / RATE)


def test_the_sparks_first_seen_together_are_one_release_of_their_owner():
    found = tallied(spark_take())
    (release,) = found['releases']
    assert (release['frame'], release['owner'], release['known'], release['charged']) == (RELEASE, LEADER, 1, 1)
    assert (release['rank'], release['level'], release['tier']) == ('unique', 80, 0)
    assert (release['away'], release['to_hero'], release['since'], release['hero_dead']) == (10.0, 180.0, 0, 0)
    assert len(release['sparks']) == len(STEPS)
    assert sorted(spark['course'] for spark in release['sparks']) == [
        0.0,
        45.0,
        90.0,
        135.0,
        180.0,
        225.0,
        270.0,
        315.0,
    ]
    west = next(spark for spark in release['sparks'] if spark['course'] == 180.0)
    assert (west['frames'], west['end_hero'], west['closest'], west['cut'], west['out']) == (9, 2.0, 2.0, 0, 8.0)
    assert west['stride'] == 1.0
    assert west['runs'] == west['bends'] == []  # it flew straight
    east = next(spark for spark in release['sparks'] if spark['course'] == 0.0)
    assert (east['frames'], east['cut'], east['end_hero']) == (FRAMES - RELEASE, 1, 26.0)  # in flight at the take's end
    assert (east['drop'], west['drop'], west['fell']) == (None, None, 0)
    assert found['drops'] == []


def test_a_drop_after_a_sparks_end_is_laid_to_it_with_what_blows_made_of_it():
    found = tallied(spark_take(hurt=40))
    west = next(spark for spark in found['releases'][0]['sparks'] if spark['course'] == 180.0)
    assert west['drop'] == [1, 40, SOLE_RANGED, 1, 1, 1, None]  # a frame on, 40 points, its owner the one suspect
    assert west['fell'] == 40
    (drop,) = found['drops']
    assert (drop['lost'], drop['class'], drop['sole'], drop['sparks'], drop['rank']) == (
        40,
        SOLE_RANGED,
        1,
        1,
        'unique',
    )
    assert (drop['level'], drop['tier']) == (80, 0)


def test_time_being_struck_is_the_windows_after_the_hits_merged():
    assert sparks.struck_frames([], 10) == 0
    assert sparks.struck_frames([5], 10) == 10
    assert sparks.struck_frames([5, 6, 7], 10) == 12  # hits in a row: the frames they span and one window
    assert sparks.struck_frames([5, 40], 10) == 20  # apart: a window each
    assert sparks.struck_frames([5, 12], 10) == 17


def test_the_deviance_is_least_for_the_rate_that_gives_the_counts():
    pairs = [(1.0, 1), (2.0, 2), (4.0, 4)]
    assert sparks.deviance(pairs, 1.0) == 0.0
    assert sparks.deviance(pairs, 0.5) > 0 < sparks.deviance(pairs, 2.0)
    assert sparks.deviance([(1.0, 0), (1.0, 2)], 1.0) > sparks.deviance([(1.0, 1), (1.0, 1)], 1.0)


def test_none_of_n_bounds_the_chance_and_bands_have_names():
    assert sparks.upper(11) == pytest.approx(1 - 0.05 ** (1 / 11), abs=0.001)
    assert sparks.upper(0) is None
    assert [sparks.band_of(since) for since in (0, 3, 9, 10, 400, None)] == [
        '0', '1-4', '5-9', '10-24', '25+', 'no hit seen before',
    ]  # fmt: skip
    assert [sparks.level_band(level) for level in (70, 75, 84, 85, 99, None)] == [
        'under 75', '75-84', '75-84', '85 and up', '85 and up', 'not known',
    ]  # fmt: skip
    assert (sparks.bearing((0, 0), (0, 5)), sparks.turned(350, 10)) == (90.0, 20)
    assert sparks.runs_mode({6: 3, 4: 3, 5: 1}) == 4


def test_tallies_measure_who_lets_sparks_go_and_when():
    found = sparks.measure([tallied(spark_take()), tallied(spark_take('20261011T130000Z-25', released=False))])
    assert (found['takes'], found['takes_with_sparks'], found['releases'], found['sparks']) == (2, 1, 1, 8)
    leaders, minions = found['by_rank']['unique'], found['by_rank']['minion']
    assert (leaders['monsters'], leaders['struck'], leaders['hits'], leaders['releases'], leaders['releasers']) == (
        2, 2, 4, 1, 1,
    )  # fmt: skip
    assert (minions['monsters'], minions['struck'], minions['releases']) == (2, 2, 0)
    relation = found['release']['all']  # the leaders only: a minion lets none go however it is struck
    assert (relation['monsters'], relation['hits'], relation['releases']) == (2, 4, 1)
    assert relation['per_hit']['value'] == 0.25
    ten = next(row for row in relation['per_second'] if row['window'] == 10)
    assert ten['struck_seconds'] == pytest.approx(2 * 11 / RATE)  # two hits a frame apart: eleven frames each
    assert ten['value'] == pytest.approx(1 / (22 / RATE), abs=0.001)
    assert found['release']['since'] == {'0': 1}
    assert found['release']['by_gap']['first'] == [2, 0]  # the release came with the second hit
    assert found['release']['by_gap']['1-4'] == [2, 1]
    assert found['count'] == {'n': 1, 'sizes': {'8': 1}}


def test_tallies_measure_how_sparks_fly_and_what_ends_on_the_character():
    found = sparks.measure([tallied(spark_take()), tallied(spark_take('20261011T130000Z-25', hurt=40))])
    flight = found['flight']
    assert (flight['sparks'], flight['frames_most']) == (16, FRAMES - RELEASE)
    assert flight['stride'] == pytest.approx((1 + math.sqrt(2)) / 2, abs=0.001)  # the median of straight and diagonal
    assert flight['on_45'] == {'n': 16, 'share': 1.0}
    assert flight['toward'] == {'n': 16, 'share': 0.125}  # one of eight flies at the character
    band = next(band for band in found['reach']['bands'] if band['from'] == 8.0)
    assert (band['releases'], band['sparks'], band['within'], band['on_hero'], band['per_release']) == (
        2,
        16,
        2,
        2,
        1.0,
    )
    assert found['reach']['all']['on_hero'] == 2
    assert found['reach']['meets'] == {'value': 1.0, 'n': 2}
    life = found['life']
    assert (life['arrivals'], life['sole'], life['any'], life['fell'], life['points_sole']) == (2, 1, 1, 1, [40])
    assert (life['low'], life['high'], life['upper95']) == (0.5, 0.5, None)
    assert life['by_rank'].keys() == {'unique'}
    assert [(drop['lost'], drop['ended']) for drop in found['drops_near']] == [(40, 1)]


def test_no_arrival_taking_life_gives_the_chance_its_upper_bound():
    life = sparks.measure([tallied(spark_take())])['life']
    assert (life['arrivals'], life['low'], life['high']) == (1, 0.0, 0.0)
    assert life['upper95'] == sparks.upper(1) == 0.95


def test_takes_are_gathered_from_disk_and_the_report_is_written_from_two_halves(tmp_path):
    first = write(spark_take('20261011T120000Z-25'), tmp_path)
    second = write(spark_take('20261011T130000Z-25', hurt=40), tmp_path)
    train, check = (sparks.gather([path], cache=None, probes=(), jobs=1, progress=False) for path in (first, second))
    assert train[0]['releases'][0]['owner'] == LEADER
    cached = sparks.gather([first], cache=tmp_path / 'cache', probes=(), jobs=1, progress=False)
    assert sparks.gather([first], cache=tmp_path / 'cache', probes=(), jobs=1, progress=False) == cached == train
    text = sparks.render({'train': sparks.measure(train), 'check': sparks.measure(check)})
    assert '| unique | 1 (1) | 2 | 1 of 1 | 8 | 1 (1) | 2 | 1 of 1 | 8 |' in text
    assert '| minion | 1 (1) | 1 | 0 of 0 | 0 | 1 (1) | 1 | 0 of 0 | 0 |' in text
    assert '| sparks that ended on the character | 1 | 1 |' in text
    assert '| followed within 3 frames by a drop put on their owner alone | 0 | 1 |' in text
    # One monster: every window gives its count, and the shortest is taken (two hits a frame apart: six frames).
    best = sparks.best(sparks.measure(train)['release']['all'])
    assert (best['window'], best['deviance']) == (sparks.WINDOWS[0], 0.0)
    assert math.isclose(best['value'], 1 / (6 / RATE), abs_tol=0.001)
