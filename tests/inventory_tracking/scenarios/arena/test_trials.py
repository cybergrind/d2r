"""trials.py: the statistics, the judgement and the tables on hand-made results, and `trial` on tiny scenes."""

from dataclasses import replace
from pathlib import Path

from inventory_tracking.macros.runner import ATTACK
from tests.inventory_tracking.scenarios.arena import trials
from tests.inventory_tracking.scenarios.arena.driver import Press
from tests.inventory_tracking.scenarios.arena.result import Result
from tests.inventory_tracking.scenarios.arena.scenes_basic import gloams, one_in_the_open
from tests.inventory_tracking.scenarios.arena.trials import (
    Case,
    Stats,
    Verdict,
    judge,
    report,
    stats,
    summarise,
    table,
    trial,
)


def result(taken: float = 0.0, *, dead: bool = False, cleared: float | None = None, potions: int = 0) -> Result:
    """A hand-made result."""
    return Result('s', 10.0, 5.0 if dead else None, cleared, taken, [], 4, 10.0, [(1.0, 1, 'serve')] * potions)


def make(**more) -> Stats:
    """A Stats with quiet defaults over 100 plays."""
    base = Stats(100, 10, 0.1, 100.0, 90.0, 300.0, 0.15, 0.9, 5.0, 1.0, 10.0, 20.0)
    return replace(base, **more)


def test_stats_percentiles_and_shares() -> None:
    plays = [result(float(n)) for n in range(1, 21)]  # taken 1..20
    plays[0] = result(1.0, dead=True, cleared=4.0)
    plays[1] = result(2.0, cleared=6.0, potions=2)
    s = stats(plays, 100.0)
    assert (s.plays, s.deaths, s.death_share) == (20, 1, 0.05)
    assert s.taken_mean == 10.5
    assert s.taken_p50 == 10.5
    assert abs(s.taken_p95 - 19.05) < 1e-9
    assert abs(s.taken_share_p95 - 0.1905) < 1e-9
    assert s.cleared_share == 0.1
    assert s.clear_p50 == 5.0
    assert s.potions_mean == 0.1
    assert s.casts_mean == 4
    assert s.moved_mean == 10.0


def test_stats_none_clear_when_none_cleared() -> None:
    s = stats([result(5.0), result(7.0)], 50.0)
    assert s.clear_p50 is None
    assert s.cleared_share == 0.0


def test_death_rule_needs_chance_and_two_points() -> None:
    assert judge({'all': make()}, {'all': make(deaths=11, death_share=0.11)})[0].change == 'same'  # chance
    # 1/1000 vs 5/1000 plays: below 2 points despite many plays? 0.4 pts -> no
    small = judge(
        {'all': make(plays=5000, deaths=50, death_share=0.01)}, {'all': make(plays=5000, deaths=70, death_share=0.014)}
    )
    assert small[0].change == 'same'
    assert judge({'all': make()}, {'all': make(deaths=25, death_share=0.25)})[0].change == 'worse'
    assert judge({'all': make(deaths=25, death_share=0.25)}, {'all': make()})[0].change == 'better'


def test_tail_rule_thresholds() -> None:
    base = make(taken_p95=300.0)
    assert judge({'all': base}, {'all': make(taken_p95=329.0)})[0].change == 'same'  # under 10%
    assert judge({'all': base}, {'all': make(taken_p95=331.0)})[0].change == 'worse'
    assert judge({'all': base}, {'all': make(taken_p95=269.0)})[0].change == 'better'
    low = make(taken_p95=100.0)  # 10% but under 20 points
    assert judge({'all': low}, {'all': make(taken_p95=119.0)})[0].change == 'same'
    assert judge({'all': low}, {'all': make(taken_p95=121.0)})[0].change == 'worse'


def test_mean_rule_thresholds() -> None:
    assert judge({'all': make()}, {'all': make(taken_mean=109.0)})[0].change == 'same'
    assert judge({'all': make()}, {'all': make(taken_mean=121.0)})[0].change == 'worse'
    assert judge({'all': make(taken_mean=300.0)}, {'all': make(taken_mean=269.0)})[0].change == 'better'


def test_clear_time_and_cleared_share_rules() -> None:
    assert judge({'all': make(clear_p50=5.0)}, {'all': make(clear_p50=5.4)})[0].change == 'same'
    assert judge({'all': make(clear_p50=5.0)}, {'all': make(clear_p50=5.6)})[0].change == 'worse'
    assert judge({'all': make(clear_p50=2.0)}, {'all': make(clear_p50=2.25)})[0].change == 'same'  # under 0.3 s
    assert judge({'all': make(clear_p50=None)}, {'all': make(clear_p50=5.0)})[0].change == 'same'
    assert judge({'all': make()}, {'all': make(cleared_share=0.86)})[0].change == 'same'
    assert judge({'all': make()}, {'all': make(cleared_share=0.84)})[0].change == 'worse'
    assert judge({'all': make()}, {'all': make(cleared_share=0.96)})[0].change == 'better'


def test_plays_floor() -> None:
    few = make(plays=29)
    verdict = judge({'all': few}, {'all': make(deaths=60, death_share=0.6)})[0]
    assert (verdict.change, verdict.why) == ('same', 'too few plays')
    assert judge({'all': make(plays=30)}, {'all': make(plays=30, deaths=15, death_share=0.5)})[0].change == 'worse'
    assert judge({'a': make()}, {'b': make()}) == []


def test_mixed() -> None:
    after = make(deaths=1, death_share=0.01, clear_p50=9.0)
    verdict = judge({'all': make(deaths=25, death_share=0.25)}, {'all': after})[0]
    assert verdict.change == 'mixed'
    assert 'deaths 25.0% -> 1.0%' in verdict.why
    assert 'clear p50 5.0s -> 9.0s' in verdict.why


def test_ordering() -> None:
    worse = make(deaths=40, death_share=0.4)
    better = make(deaths=0, death_share=0.0)
    before = {'case1': make(), 'kind:b': make(), 'all': make(), 'case2': make(), 'case3': make(), 'kind:a': make()}
    after = {'case1': make(), 'kind:b': better, 'all': better, 'case2': worse, 'case3': better, 'kind:a': worse}
    keys = [(v.key, v.change) for v in judge(before, after)]
    assert keys == [
        ('all', 'better'),
        ('kind:a', 'worse'),
        ('kind:b', 'better'),
        ('case2', 'worse'),
        ('case3', 'better'),
        ('case1', 'same'),
    ]


def tiny_cases() -> list[Case]:
    attack = (Press(0.0, ATTACK),)
    return [
        Case('open', one_in_the_open(), attack, 3.0, 'basic'),
        Case('gloams', gloams(), attack, 3.0, 'other'),
    ]


def test_trial_is_deterministic_and_parallel_equal() -> None:
    cases, seeds = tiny_cases(), [1, 2, 3]
    serial = trial(cases, seeds)
    assert list(serial) == ['open', 'gloams']
    assert all(len(v) == 3 for v in serial.values())
    assert trial(cases, seeds) == serial
    assert trial(cases, seeds, jobs=2) == serial


def test_trial_records_a_failing_play() -> None:
    bad = Case('bad', one_in_the_open(), (Press(0.0, 'nonsense'),), 1.0, 'basic')
    errors: list[trials.Failure] = []
    found = trial([bad, *tiny_cases()[:1]], [1], errors=errors)
    assert list(found) == ['open']
    assert [(e.case, e.seed) for e in errors] == [('bad', 1)]


def test_summarise_adds_kind_and_all() -> None:
    cases = tiny_cases()
    summary = summarise(trial(cases, [1, 2, 3]), cases)
    assert set(summary) == {'all', 'kind:basic', 'kind:other', 'open', 'gloams'}
    assert summary['all'].plays == 6
    assert summary['kind:basic'].plays == 3


def test_table_is_stable() -> None:
    summary = {'all': make(plays=60), 'kind:burst': make(clear_p50=None), 'x': make(deaths=3, death_share=0.03)}
    assert table(summary) == (
        'key         plays  dead%  taken  p50  p95  p95%life  clear%  clr p50  pots  casts  moved\n'
        '----------  -----  -----  -----  ---  ---  --------  ------  -------  ----  -----  -----\n'
        'all            60   10.0    100   90  300        15      90      5.0   1.0     10     20\n'
        'kind:burst    100   10.0    100   90  300        15      90        -   1.0     10     20\n'
        'x             100    3.0    100   90  300        15      90      5.0   1.0     10     20'
    )


def test_report_is_stable() -> None:
    old, new = make(), make(deaths=25, death_share=0.25)
    text = report([Verdict('all', old, new, 'worse', 'deaths 10.0% -> 25.0%'), Verdict('x', old, old, 'same', 'n')])
    assert text == 'worse   all  deaths 10.0% -> 25.0%\nsame    x    n\n1 worse, 0 mixed, 0 better, 1 same'


def test_saved_json_round_trips(tmp_path: Path) -> None:
    cases = tiny_cases()
    found = trial(cases, [1, 2])
    path = tmp_path / 'saved.json'
    trials.save(found, [1, 2], path, cases)
    back = trials.load_trials(path)
    assert summarise(back, cases) == summarise(found, cases)
    assert trials.summarise_saved(path) == summarise(found, cases)
    assert all(
        a.potions == b.potions and a.kills == b.kills for n in found for a, b in zip(found[n], back[n], strict=True)
    )


def test_case_sets_are_built() -> None:
    assert len(trials.threat_cases()) == 16
    assert {c.kind for c in trials.basic_cases()} == {'basic'}
    kinds = {c.kind for c in trials.fixture_cases()}
    assert kinds
    assert all(c.presses[1].at == 0.3 for c in trials.fixture_cases({'burst'}))
    assert 'TRIALS-base' not in {c.name for c in trials.fixture_cases()}
