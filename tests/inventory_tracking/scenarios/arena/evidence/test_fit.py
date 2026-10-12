"""The fitted table of the monster model (evidence/fit.py) and its check against the check half
(evidence/refit_check.py)."""

import json

import pytest

from tests.inventory_tracking.scenarios.arena.evidence import fit as fitting, refit_check
from tests.inventory_tracking.scenarios.arena.evidence.fit import (
    EVIDENCE,
    FITTED,
    SPARKS,
    SWINGS,
    curve,
    middle,
)


@pytest.fixture(scope='module')
def evidence() -> dict:
    return json.loads(EVIDENCE.read_text())


@pytest.fixture(scope='module')
def sparks() -> dict:
    return json.loads(SPARKS.read_text())


@pytest.fixture(scope='module')
def swings() -> dict:
    return json.loads(SWINGS.read_text())


def test_the_fit_in_the_repository_is_what_the_generator_writes_from_the_train_half(evidence, sparks, swings):
    """Nothing in data/monsters_fit.json is typed by hand: the generator gives the same file again.
    (The missile speeds are the file's own here: the game's tables are not in git.)"""
    written = json.loads(FITTED.read_text())
    assert fitting.fit(evidence, fitting.kept_speeds(FITTED), sparks, swings) == written


def test_the_fit_reads_the_train_half_only(evidence, sparks, swings):
    lone = {key: value for key, value in sparks.items() if key != 'check'}
    swung = {key: value for key, value in swings.items() if key != 'check'}
    without = {key: value for key, value in evidence.items() if key not in ('check', 'all')}
    without['types'] = {
        txt: {part: ({**found, 'check': None} if isinstance(found, dict) and 'check' in found else found)
              for part, found in row.items()}
        for txt, row in evidence['types'].items()
    }  # fmt: skip
    without['big_drops'] = [drop for drop in evidence['big_drops'] if drop['half'] == 'train']
    assert fitting.fit(without, fitting.kept_speeds(FITTED), lone, swung) == json.loads(FITTED.read_text())


def test_the_sparks_are_fitted_on_the_train_half_of_their_own_evidence(sparks):
    """sparks.json's train half and nothing else: a check half made up gives the same fit, and each number
    is one the evidence holds or is counted from it."""
    train = sparks['train']
    found = fitting.sparks(sparks)
    other = {**sparks, 'check': {'by_rank': {'minion': {'releases': 99}}, 'life': {'low': 1.0, 'high': 1.0}}}
    assert fitting.sparks(other) == found
    assert found['ranks'] == ['unique']  # a unique and a super unique let sparks go; the model calls both unique
    assert found['shown']['minion']['releases'] == 0 < found['shown']['minion']['struck']
    relation = train['release']['all']
    best = min(relation['per_second'], key=lambda row: row['deviance'])
    assert best['deviance'] < relation['per_hit']['deviance']  # per second of being struck is the better relation
    assert (found['release']['rate']['value'], found['release']['window']) == (best['value'], best['window'])
    assert found['release']['rate']['n'] == relation['releases']
    assert found['release']['rate']['free'] > best['value']  # the gap after a release is no time to release in
    assert found['release']['gap']['value'] == train['release']['gap']['least']
    assert found['count'] == {'value': 8, 'n': train['releases']}
    assert found['flight']['frames']['value'] == train['flight']['frames_most']
    assert found['meets'] == train['reach']['meets']
    life = train['life']
    assert found['takes_life']['n'] == life['arrivals'] == train['reach']['all']['on_hero']
    assert found['takes_life']['value'] == middle(life['low'], life['high'])
    # None of the train half's arrivals took life: the fit says so, and says how little that proves.
    assert (found['takes_life']['value'], found['takes_life']['upper95']) == (0.0, life['upper95'])
    assert 0.2 < found['takes_life']['upper95'] < 0.3


def test_the_commonest_of_counts_written_as_text():
    assert fitting.commonest({'8': 51}) == 8
    assert fitting.commonest({'4': 2, '8': 233}) == 8
    assert fitting.commonest({'4': 3, '8': 3}) == 4


def test_a_type_under_the_evidences_thresholds_has_no_row(evidence):
    written = json.loads(FITTED.read_text())
    least = evidence['thresholds']
    for txt, row in written['melee']['types'].items():
        found = evidence['types'][txt]['melee']['train']
        assert found['seconds'] >= least['enough_seconds'] or found['blows'] >= least['enough_blows']
        assert row['rate']['n_seconds'] == found['seconds']
    for row in written['shots']['types'].values():
        assert row['rate']['n_shots'] >= least['enough_shots']
        own = not row['takes_life'].get('pooled')
        assert own == (row['rate']['n_shots'] >= fitting.OWN_CHANCE * least['enough_shots'])
    for row in written['targets']['types'].values():
        assert (
            min(row['character_nearer']['n_seconds'], row['companion_nearer']['n_seconds']) >= least['enough_seconds']
        )
    assert written['melee']['idle'] == evidence['train']['melee_all']['left_out']


def test_the_swings_are_fitted_on_the_train_half_of_their_own_evidence(evidence, swings):
    """swings.json's train half and nothing else: a check half made up gives the same fit, and each number
    is one the evidence holds."""
    train = swings['train']
    found = fitting.melee(evidence, swings)
    made_up = {
        'ran_out': {'stood': {'value': 0.99, 'low': 0.99, 'high': 0.99, 'n': 999}},
        'types': {'310': {'ran_out': {'stood': {'value': 0.99, 'n': 999}}}},
        'rest': {'knots': [99] * 11},
    }
    assert fitting.melee(evidence, {**swings, 'check': made_up}) == found
    life = found['pooled']['takes_life']
    stood = train['ran_out']['stood']
    assert (life['value'], life['low'], life['high'], life['n']) == (
        stood['value'],
        stood['low'],
        stood['high'],
        stood['n'],
    )
    assert life['value'] == middle(stood['low'], stood['high'])
    assert life['alone'] == {'value': train['ran_out']['alone']['value'], 'n': train['ran_out']['alone']['n']}
    assert found['blow'] == {'share': train['blow']['share'], 'n': train['blow']['n']}
    assert found['rest']['knots'] == train['rest']['knots']
    assert found['stagger']['mode'] == train['recovery']['mode']
    assert [band['chance'] for band in found['stagger']['bands']] == [
        band['chance'] for band in train['stagger']['bands']
    ]
    assert found['stagger']['recovery']['knots'] == train['stagger']['recovery']['knots']


def test_a_type_has_a_chance_of_its_own_only_with_enough_swings_that_ran_out(evidence, swings):
    enough = swings['constants']['enough_swings']
    found = fitting.melee(evidence, swings)
    for txt, row in found['types'].items():
        own = swings['train']['types'].get(txt, {'ran_out': {'stood': {'n': 0}}})['ran_out']['stood']
        if own['n'] >= enough:
            assert (row['takes_life']['value'], row['takes_life']['n']) == (own['value'], own['n'])
        else:
            assert row['takes_life'] == {**found['pooled']['takes_life'], 'pooled': True}
    # No row of the Chaos Sanctuary's Doom Knights: the train half holds two of their swings (SWINGS.md).
    doom_knight = next(txt for txt, row in swings['check']['types'].items() if row['name'] == 'Doom Knight')
    assert doom_knight not in found['types']
    assert swings['train']['types'][doom_knight]['ran_out']['stood']['n'] < enough


def test_the_middle_of_two_bounds_and_the_curve_through_a_drops_quantiles():
    assert middle(0.1, 0.3) == 0.2
    assert middle(None, 0.3) is None
    found = curve({'n': 10, 'p50': 50, 'p90': 100, 'p99': 200, 'max': 200})
    assert [share for share, _factor in found['knots']] == [0.0, 0.5, 0.9, 1.0]  # the 99th is the largest: once
    assert found['knots'][1][1] * found['mean_points'] == pytest.approx(50, rel=0.001)
    assert found['knots'][0][1] * found['mean_points'] == pytest.approx(5, rel=0.01)  # hurts.HURT_LEAST
    assert curve({'n': 500, 'p50': 50, 'p90': 100, 'p99': 200, 'max': 300})['knots'][3][0] == 0.99


# --- the check half ---------------------------------------------------------------------------------------


@pytest.fixture(scope='module')
def rows(evidence) -> list[refit_check.Row]:
    return refit_check.check(evidence, 600.0)


def named(rows, *words: str) -> refit_check.Row:
    return next(row for row in rows if all(word in row.what for word in words))


def test_a_row_is_judged_by_after_over_measured():
    row = refit_check.Row('melee', 'x', 100.0, 3.0, 2.0)
    assert (row.ratio, row.outside) == (1.5, False)
    assert refit_check.Row('melee', 'x', 100.0, 5.0, 2.0).outside
    assert refit_check.Row('melee', 'x', 100.0, 0.9, 2.0).outside
    assert refit_check.Row('melee', 'x', 100.0, 1.0, 0.0).ratio is None  # nothing measured: not judged
    assert refit_check.Row('death', 'x', 0.0, 0.02, None).outside is False


def test_the_check_names_every_mechanism_and_says_what_the_model_was_before(rows):
    assert {row.mechanism for row in rows} == {
        'melee',
        'swing',
        'target',
        'ranged',
        'nova',
        'size',
        'big',
        'death',
        'sparks',
    }
    life = named(rows, 'pooled row', 'life a second in reach')
    assert life.before > 50 > life.after > 1  # every swing landed before the refit
    shots = named(rows, 'pooled row', 'shots a second')
    assert shots.before == 1.0
    assert shots.after == pytest.approx(0.43, abs=0.05)
    assert named(rows, 'share that takes life', 'Cold Enchanted').before == 0.0
    text = '\n'.join(refit_check.table(rows))
    assert text.count('\n') == len(rows) + 1
    assert '| mechanism | what | before | after | measured (check) | after / measured | note |' in text


def test_the_pooled_mechanisms_are_within_a_factor_of_two_of_the_check_half(rows):
    """The rows with the most data behind them. (The run with the default length and every row
    outside the band is in the refit's report; this is the floor that must not give way.)"""
    for words in (
        ('pooled row', 'swings a second'),
        ('pooled row', 'share of swings that runs out'),
        ('pooled row', 'swings run out that takes life'),
        ('pooled row', 'life a second in reach'),
        ('frames of rest',),
        ('where in a swing the blow lands',),
        ('4/16 or more', 'staggers'),
        ('0/16 to 1/16', 'staggers'),
        ('frames a stagger lasts',),
        ('pooled', 'the character nearer'),
        ('pooled', 'a companion nearer'),
        ('pooled row', 'shots a second'),
        ('Cold Enchanted', 'share that takes life'),
        ('points of a nova, median',),
        ('points of a strike', 'median'),
        ('points of a strike', '90th'),
    ):
        row = named(rows, *words)
        assert row.ratio is not None, row.what
        assert not row.outside, (row.what, row.ratio)


def test_the_model_can_deal_the_blow_of_the_recorded_death(rows):
    row = named(rows, 'Herald of the death scene')
    assert row.before == 0.0
    assert 0.0 < row.after < 0.1  # seldom, but no longer never
    assert 'reach up to 12 units' in row.note


def test_the_spark_rows_say_what_the_model_was_and_is(rows):
    rate = named(rows, 'no Herald')
    assert rate.before > 2 > rate.after > 0.5  # a third of the struck frames before; the fitted rate now
    assert not rate.outside
    reach = named(rows, 'sparks ending on the character per release')
    assert reach.before > reach.after > 0
    assert not reach.outside
    assert not named(rows, 'in reach of the character that end on it').outside
    assert not named(rows, 'units out of a spark').outside
    life = named(rows, 'sparks ending on the character that takes life')
    assert (life.before, life.after) == (1.0, 0.0)  # every spark took its points; none does
    assert 'train: 0 of 11' in life.note
    toll = named(rows, 'median distance: life a second')
    assert toll.before > 10
    assert toll.after == 0.0
    assert named(rows, 'points of a spark').ratio is None  # no spark took life: nothing to judge the size by


def test_the_check_is_the_same_twice(evidence):
    first, second = refit_check.melee_rows(evidence, 200.0)[0], refit_check.melee_rows(evidence, 200.0)[0]
    assert first == second


def test_the_swing_rows_say_what_the_model_was_and_is(rows):
    rest = named(rows, 'frames of rest')
    assert (rest.before, rest.after) == (10.47, 15)  # a rest that made the measured rate; the measured rest
    assert named(rows, 'where in a swing the blow lands').before == 0.5
    assert named(rows, '4/16 or more', 'staggers').before == 0.0  # nothing staggered
    out = named(rows, 'pooled row', 'share of swings that runs out')
    assert out.before == 1.0 > out.after > 0.2  # struck as the check half's were, most swings do not run out
    # The Chaos Sanctuary's Doom Knights play by the pooled chance: the check half saw 20 of their swings
    # run out or more, the train half one (the row says what is missing).
    doom = named(rows, 'Doom Knight', 'no chance of its own')
    assert (doom.before, doom.after) == (0.161, pytest.approx(0.296))
    assert 'train: 1 such swings, 30 needed' in doom.note


def test_a_monster_played_with_the_ends_of_a_halfs_swings_loses_those_swings():
    """refit_check.play with a half's `ends`: without them every swing runs out; with them the share that
    staggered or died does not (but for the staggers the model's own roll refuses), and takes less life."""

    def devilkin():
        return refit_check.fighter(1, 21, (refit_check.BESIDE, 0.0), 85)

    def ends(ran_out: int, staggered: int, died: int) -> dict:
        return {'ran out': {'n': ran_out}, 'staggered': {'n': staggered}, 'died': {'n': died}}

    calm = refit_check.play(devilkin(), 400.0, 3)
    assert calm.whole >= calm.begun - 1
    assert calm.landed == len(calm.blows)
    reeling = refit_check.play(devilkin(), 400.0, 3, ends=ends(50, 50, 0))
    assert reeling.whole / reeling.begun == pytest.approx(0.5 + 0.5 * 0.07, abs=0.06)  # 0.93 of such hits stagger
    dying = refit_check.play(devilkin(), 400.0, 3, ends=ends(25, 0, 75))
    assert dying.whole / dying.begun == pytest.approx(0.25, abs=0.05)
    assert len(dying.blows) / dying.begun < len(calm.blows) / calm.begun
