"""The regression harness (combat/scoreboard.py) on two cuts of real play checked in as fixtures:
`chaos-manual`, 20 s of the player's own Chaos Sanctuary play (take 20261009T212147Z-108, frames
2750-3250), and `catacombs-macro`, 17 s of attack mode in the Catacombs (take 20261010T114636Z-37,
frames 1-420, with the level's walls). The numbers are pinned: a change of the model moves them, and
the test says so before a plan table does."""

import json
from pathlib import Path

import pytest

from inventory_tracking.combat.scoreboard import build, changes, lines
from inventory_tracking.combat.sim.engine import curves, gate, score, simulate, verdict
from inventory_tracking.combat.sim.policy import YIELD, candidate, policy_score, run_policy
from inventory_tracking.combat.sim.situation import MonsterTrack, Situation, cut, describe
from inventory_tracking.combat.takes import Take, trim


FIXTURES = Path(__file__).parent / 'fixtures'
OFF = {'companions': {}, 'link': (0.0, 0, 0.0), 'explosion': (0.0, 0.0), 'mark': (0.0, 0), 'mana': (0.0, 0.0, 0.0)}


@pytest.fixture(scope='module')
def board():
    return build(FIXTURES, write=False)


def test_the_fixture_takes_pass_the_gate_with_their_pinned_numbers(board):
    chaos, catacombs = board['takes']['chaos-manual'], board['takes']['catacombs-macro']
    assert chaos['passes'], chaos['gate']['fails']
    assert catacombs['passes'], catacombs['gate']['fails']
    assert chaos['situation']['casts'] == PINNED['chaos casts']
    assert chaos['gate']['damage_ratio'] == PINNED['chaos ratio']
    assert chaos['gate']['life_explained_at_recorded_kill'] == PINNED['chaos explained']
    assert chaos['gate']['life_curves']['away']['bias'] == PINNED['chaos bias']
    assert catacombs['situation']['walls']
    assert catacombs['gate']['damage_ratio'] == PINNED['catacombs ratio']


def test_the_line_sweep_beats_the_recorded_casts_on_both_fixtures_without_a_cast_into_a_run(board):
    for name in ('chaos-manual', 'catacombs-macro'):
        found = board['takes'][name]['policies']
        assert found['yield']['gain'] == PINNED[f'{name} yield']
        assert found['yield']['gain'] > 0.03
        assert found['yield']['casts_while_recorded_running'] == 0
        assert found['live']['casts_while_recorded_running'] == 0  # what the game runs yields too
        assert found['free']['gain'] >= found['yield']['gain'] - 0.01
    # The player's own play: the sweep's aim alone (the recorded cast frames) and its lines whenever free
    # both beat the hunt's nearest-monster rule casting whenever free.
    chaos = board['takes']['chaos-manual']['policies']
    assert chaos['slots']['gain'] > 0
    assert chaos['free']['gain'] > chaos['nearest']['gain']


def test_the_policys_first_casts_on_the_chaos_fixture_are_pinned():
    situation = cut(Take.load(FIXTURES / 'chaos-manual'))
    outcome = run_policy(situation, candidate(situation, YIELD))
    first = [(frame, round(x, 1), round(y, 1)) for frame, (x, y) in outcome.cast_frames[:3]]
    assert first == PINNED['chaos first casts']


def test_the_scoreboard_marks_fit_and_held_out_takes_and_prints_a_line_per_take(board, monkeypatch):
    # By the recording a fixture was cut from, not its directory's name (review.md, finding 4): the Chaos
    # fixture is a cut of a take the numbers were fitted on.
    assert {name: found['side'] for name, found in board['takes'].items()} == {
        'chaos-manual': 'fit',
        'catacombs-macro': 'holdout',
    }
    assert board['totals']['takes'] == board['totals']['passing'] == 2
    assert board['totals']['yield_gain_on_passing']['least'] > 0.03
    text = lines(board)
    assert text[0].startswith('catacombs-macro')
    assert ' pass ' in text[0]
    import inventory_tracking.combat.scoreboard as module

    monkeypatch.setattr(module, 'fit_takes', lambda: frozenset(('20261010T114636Z-37',)))
    sides = {name: found['side'] for name, found in build(FIXTURES, policies=False, write=False)['takes'].items()}
    assert sides == {'chaos-manual': 'holdout', 'catacombs-macro': 'fit'}


def test_the_scoreboard_says_what_changed_since_the_one_before(board):
    before = json.loads(json.dumps(board))
    before['takes']['chaos-manual']['passes'] = False
    before['takes']['catacombs-macro']['policies']['yield']['gain'] -= 0.05
    found = changes(before, board['takes'])
    assert found[0].startswith('catacombs-macro: yield gain')
    assert found[1] == 'chaos-manual: passes now'
    assert changes(None, board['takes']) == []
    assert changes(board, board['takes']) == []


def test_a_take_with_too_few_casts_is_skipped(tmp_path):
    take = Take.load(FIXTURES / 'chaos-manual')
    trim(take, 2750, 2760, tmp_path / 'short')
    found = build(tmp_path, policies=False)
    assert 'skipped' in found['takes']['short']
    assert (tmp_path / 'scoreboard.json').exists()


def test_a_trimmed_take_keeps_its_window_and_reads_back(tmp_path):
    take = Take.load(FIXTURES / 'catacombs-macro')
    small = Take.load(trim(take, 100, 200, tmp_path / 'cut'))
    assert [small.frames[0]['n'], small.frames[-1]['n']] == [100, 200]
    assert small.manifest['trimmed'] == {
        'take': 'catacombs-macro',
        'frames': [100, 200],
        'recording': '20261010T114636Z-37',
    }
    assert small.recording == take.recording == '20261010T114636Z-37'  # through a trim of a trim
    smaller = Take.load(trim(small, 120, 150, tmp_path / 'renamed'))
    assert smaller.recording == '20261010T114636Z-37'
    assert Take(tmp_path / 'my-notes', {}).recording is None  # says nothing of where it came from
    assert Take(tmp_path / '20261009T212147Z-108', {}).recording == '20261009T212147Z-108'
    assert all(small.frames[0]['t'] <= event['t'] <= small.frames[-1]['t'] for event in small.events)
    assert describe(cut(small))['walls']  # the level map came along


# --- the life taken, not the blows (review.md, finding 3) ---


def test_a_finishing_blow_scores_the_life_it_took_not_its_size():
    situation = lone(100.0, None, [])
    weak = simulate(situation, [(0, (5000.0, 5010.0))], lambda txt: 100.0, **OFF)
    strong = simulate(situation, [(0, (5000.0, 5010.0))], lambda txt: 1000.0, **OFF)
    assert strong.total_damage > weak.total_damage  # the blows differ, and stay on record
    assert strong.effective_damage == weak.effective_damage == 100.0  # the monster had 100 to lose
    for outcome in (weak, strong):
        found = policy_score(situation, outcome)
        assert found['damage_points'] == found['placement_points'] == 100
    assert score(situation, strong)['raw_damage_points'] == round(strong.total_damage)


def test_a_marked_finishing_blow_takes_no_more_than_the_life_left():
    situation = lone(100.0, None, [])
    situation.marks = [(0, 1)]
    marked = simulate(situation, [(0, (5000.0, 5010.0))], lambda txt: 90.0, **{**OFF, 'mark': (0.5, 500)})
    assert marked.effective_damage == 100.0  # 135 struck with the mark, 100 there to take


# --- the two-sided gate ---


def lone(points, death, drops, frames=100):
    """One monster standing at (5000, 5010), the character at (5000, 5000), no companion."""
    track = MonsterTrack(1, 310, points, dict.fromkeys(range(frames + 1), (5000.0, 5010.0)), 1.0, death)
    player = dict.fromkeys(range(frames + 1), (5000.0, 5000.0))
    return Situation(0, frames, 108, 2560 / 1418, player, {1: track}, [], sum(p for _, p in drops), drops={1: drops})


def test_a_simulation_that_deals_what_the_record_shows_a_little_earlier_has_no_bias():
    situation = lone(1000.0, 30, [(20, 500.0), (30, 500.0)])
    outcome = simulate(situation, [(0, (5000.0, 5010.0))], lambda txt: 250.0, **OFF)  # contacts around frames 8 and 30
    found = curves(situation, outcome)['away']
    assert found['monsters'] == 1
    assert found['ahead'] < 0.05
    assert found['behind'] < 0.35
    assert curves(situation, outcome)['near']['monsters'] == 0


def test_a_simulation_that_deals_too_much_runs_ahead_and_one_that_deals_too_little_runs_behind():
    slow_record = lone(100_000.0, None, [(80, 1000.0)])
    eager = simulate(slow_record, [(0, (5000.0, 5010.0))], lambda txt: 50_000.0, **OFF)
    found = curves(slow_record, eager)['away']
    assert found['bias'] > 0.5
    assert found['behind'] == 0
    quick_record = lone(100_000.0, None, [(9, 60_000.0)])
    meek = simulate(quick_record, [(0, (5000.0, 5010.0))], lambda txt: 100.0, **OFF)
    found = curves(quick_record, meek)['away']
    assert found['bias'] < -0.5
    assert found['ahead'] == 0


def test_the_verdict_fails_on_too_much_as_well_as_too_little():
    report = {
        'life_explained_at_recorded_kill': {'median': 1.0, 'mean': 0.9},
        'damage_ratio': 1.0,
        'life_curves': {'away': {'monsters': 20, 'ahead': 0.3, 'behind': 0.05, 'bias': 0.25}},
    }
    assert verdict(report) == ['blades run ahead by 0.25']
    report['life_curves']['away'].update(ahead=0.05, behind=0.3, bias=-0.25)
    assert verdict(report) == ['blades run behind by 0.25']
    report['life_curves']['away'].update(monsters=3)  # too few to say
    assert verdict(report) == []
    report['damage_ratio'] = 1.3
    report['life_explained_at_recorded_kill']['mean'] = 0.7
    assert verdict(report) == ['life explained 1.0 / 0.7', 'damage ratio 1.3']
    report['life_explained_at_recorded_kill'] = {'median': None, 'mean': None}
    assert verdict(report) == ['no recorded kills']


def test_a_monster_a_companion_stood_beside_is_on_the_near_side():
    from inventory_tracking.combat.sim.situation import CompanionTrack

    situation = lone(1000.0, 30, [(20, 1000.0)])
    situation.companions = {9: CompanionTrack(9, 338, {10: (5000.0, 5014.0)})}
    outcome = simulate(situation, [(0, (5000.0, 5010.0))], lambda txt: 250.0, **OFF)
    found = curves(situation, outcome)
    assert (found['away']['monsters'], found['near']['monsters']) == (0, 1)
    assert 'life_curves' in gate(situation, outcome)


def test_with_mortal_off_a_monster_lives_as_long_as_the_record_shows_it():
    situation = lone(1000.0, None, [])
    outcome = simulate(
        situation, [(0, (5000.0, 5010.0)), (40, (5000.0, 5010.0))], lambda txt: 900.0, mortal=False, **OFF
    )
    assert outcome.deaths == {}
    assert outcome.blade_damage > 2 * 900.0  # the second cast still finds it
    mortal = simulate(situation, [(0, (5000.0, 5010.0)), (40, (5000.0, 5010.0))], lambda txt: 900.0, **OFF)
    assert list(mortal.deaths) == [1]


PINNED: dict = {
    'chaos casts': 29,
    'chaos ratio': 0.87,  # the life taken over the life lost on record; 0.92 while the blows were counted
    'chaos explained': {'median': 1.0, 'mean': 0.87},
    'chaos bias': 0.003,  # 0.002 before the frames were game ticks
    'catacombs ratio': 0.96,  # 1.01 with the blows; 0.94 before the frames were game ticks
    'chaos-manual yield': 0.099,  # 0.131 with the blows: a third of the gain was overkill
    # 0.181 with the blows; 0.087 while five late samples cut the recorded blades' flights short (in game
    # ticks the recorded casts hit 4% more); 0.042 while the policy saw the doors of five frames later
    'catacombs-macro yield': 0.038,  # half of the 0.181 was
    'chaos first casts': [(2755, 7758.1, 5302.0), (2764, 7753.6, 5297.2), (2787, 7759.0, 5281.7)],
}
