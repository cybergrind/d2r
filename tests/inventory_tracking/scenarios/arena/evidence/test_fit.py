"""The fitted table of the monster model (evidence/fit.py) and its check against the check half
(evidence/refit_check.py)."""

import json

import pytest

from tests.inventory_tracking.scenarios.arena.evidence import fit as fitting, refit_check
from tests.inventory_tracking.scenarios.arena.evidence.fit import EVIDENCE, FITTED, curve, cut_frames, middle, rest


@pytest.fixture(scope='module')
def evidence() -> dict:
    return json.loads(EVIDENCE.read_text())


def test_the_fit_in_the_repository_is_what_the_generator_writes_from_the_train_half(evidence):
    """Nothing in data/monsters_fit.json is typed by hand: the generator gives the same file again.
    (The missile speeds are the file's own here: the game's tables are not in git.)"""
    written = json.loads(FITTED.read_text())
    assert fitting.fit(evidence, fitting.kept_speeds(FITTED)) == written


def test_the_fit_reads_the_train_half_only(evidence):
    without = {key: value for key, value in evidence.items() if key not in ('check', 'all')}
    without['types'] = {
        txt: {part: ({**found, 'check': None} if isinstance(found, dict) and 'check' in found else found)
              for part, found in row.items()}
        for txt, row in evidence['types'].items()
    }  # fmt: skip
    without['big_drops'] = [drop for drop in evidence['big_drops'] if drop['half'] == 'train']
    assert fitting.fit(without, fitting.kept_speeds(FITTED)) == json.loads(FITTED.read_text())


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


def test_the_rest_after_a_swing_makes_the_measured_rate():
    # 1.0 swings a second of 16 frames, none cut: 25 frames a swing, 9 of them rest.
    assert rest(1.0, 16, 0.0) == 9.0
    # Half of them cut short to 1 to 7 frames (4 at the mean): 10 frames of swing a cycle, 15 of rest.
    assert cut_frames(16) == 4.0
    assert rest(1.0, 16, 0.5) == 15.0
    assert rest(5.0, 16, 0.0) == 0.0  # never under nothing


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
    assert {row.mechanism for row in rows} == {'melee', 'target', 'ranged', 'nova', 'size', 'big', 'death'}
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
        ('pooled row', 'cut short'),
        ('pooled row', 'whole swings that takes life'),
        ('pooled row', 'life a second in reach'),
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


def test_the_check_is_the_same_twice(evidence):
    first, second = refit_check.melee_rows(evidence, 200.0)[0], refit_check.melee_rows(evidence, 200.0)[0]
    assert first == second
