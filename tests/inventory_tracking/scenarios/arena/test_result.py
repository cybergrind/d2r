"""Tests for the arena play record and its scorecard and comparison report."""

import pytest

from tests.inventory_tracking.scenarios.arena.result import Result, compare, scorecard


def _r(scene: str, **kwargs) -> Result:
    """A result with quiet defaults; keyword arguments override them."""
    base = {
        'seconds': 30.0,
        'dead_at': None,
        'cleared_at': None,
        'taken': 0.0,
        'kills': [],
        'casts': 0,
        'moved': 0.0,
    }
    base.update(kwargs)
    return Result(scene=scene, **base)


@pytest.mark.parametrize(('dead_at', 'alive'), [(None, True), (5.0, False)])
def test_alive(dead_at: float | None, alive: bool) -> None:
    """A result is alive exactly when its life never ran out."""
    assert _r('x', dead_at=dead_at).alive is alive


THREE_ROWS = '\n'.join(
    [
        'scene            alive  dead@  clear@  taken  kills  casts  moved       pots  charges  swaps',
        '---------------  -----  -----  ------  -----  -----  -----  -----  ---------  -------  -----',
        'alpha            yes        -    12.3     10      3      6    121  2 (1 osd)        1      0',
        'bravo-long-name  DEAD    20.0       -     55      1      2     40          0        0      2',
        'charlie          yes        -    40.0      0      0      0      0          1        2      1',
        'total (3)        2/3        -       -     66      4      8    161  3 (1 osd)        3      3',
    ]
)


def test_scorecard_three_rows() -> None:
    """Three results render as a pinned table: header, rule, one row each, then the totals."""
    results = [
        _r(
            'alpha',
            cleared_at=12.34,
            taken=10.4,
            kills=[1, 2, 3],
            casts=6,
            moved=120.6,
            potions=[(3.0, 1001, 'serve'), (9.5, 1002, 'osd')],
            charges=1,
        ),
        _r('bravo-long-name', dead_at=20.0, taken=55.2, kills=[4], casts=2, moved=40.0, swaps=2),
        _r('charlie', cleared_at=40.0, potions=[(5.0, 1003, 'serve')], charges=2, swaps=1),
    ]
    assert scorecard(results) == THREE_ROWS


def test_scorecard_empty() -> None:
    """No results: just the header, the rule and a zero totals row."""
    assert scorecard([]) == '\n'.join(
        [
            'scene      alive  dead@  clear@  taken  kills  casts  moved  pots  charges  swaps',
            '---------  -----  -----  ------  -----  -----  -----  -----  ----  -------  -----',
            'total (0)  0/0        -       -      0      0      0      0     0        0      0',
        ]
    )


@pytest.mark.parametrize(
    ('potions', 'shown'),
    [
        ([(1.0, 1, 'osd'), (2.0, 2, 'serve')], '2 (1 osd)'),
        ([(1.0, 1, 'serve'), (2.0, 2, 'serve'), (3.0, 1, 'serve')], '3'),
    ],
)
def test_scorecard_potion_display(potions: list[tuple[float, int, str]], shown: str) -> None:
    """The pots column shows the osd part only when some potions were drunk by 'osd'."""
    row = scorecard([_r('x', potions=potions)]).splitlines()[2]
    assert shown in row
    assert ('osd' in row) is ('osd' in shown)


def test_scorecard_total_shows_osd_part() -> None:
    """The totals row carries the osd part over all results."""
    results = [_r('a', potions=[(1.0, 1, 'osd')]), _r('b', potions=[(1.0, 1, 'serve')])]
    assert scorecard(results).splitlines()[-1].endswith('2 (1 osd)        0      0')


def test_compare_worse_when_alive_to_dead() -> None:
    """A character that was alive and is now dead is WORSE."""
    report = compare([_r('x')], [_r('x', dead_at=5.0)])
    assert report == 'WORSE x: alive yes -> DEAD'


@pytest.mark.parametrize(
    ('before', 'after', 'verdict'),
    [
        (100.0, 105.0, 'changed'),  # exactly 5 percent: not more than 5
        (100.0, 106.0, 'WORSE'),  # just above 5 percent
        (0.0, 1.0, 'WORSE'),  # rose by one point from nothing
    ],
)
def test_compare_taken_rise_threshold(before: float, after: float, verdict: str) -> None:
    """Taken rising by more than 5 percent (and at least one point) while alive is WORSE."""
    report = compare([_r('x', taken=before)], [_r('x', taken=after)])
    assert report.startswith(f'{verdict} x: ')


@pytest.mark.parametrize(
    ('before', 'after', 'verdict'),
    [
        (100.0, 95.0, 'changed'),  # exactly 5 percent: not more than 5
        (100.0, 94.0, 'better'),  # just above 5 percent
    ],
)
def test_compare_taken_fall_threshold(before: float, after: float, verdict: str) -> None:
    """Taken falling by more than 5 percent (and at least one point) while alive is better."""
    report = compare([_r('x', taken=before)], [_r('x', taken=after)])
    assert report.startswith(f'{verdict} x: ')


def test_compare_worse_when_cleared_is_lost() -> None:
    """A scene that was cleared and no longer is counts as WORSE."""
    report = compare([_r('x', cleared_at=10.0)], [_r('x', cleared_at=None)])
    assert report == 'WORSE x: cleared_at 10.0 -> -'


def test_compare_better_when_revived() -> None:
    """A character that was dead and is now alive is better."""
    report = compare([_r('x', dead_at=3.0)], [_r('x')])
    assert report == 'better x: alive DEAD -> yes'


def test_compare_better_when_newly_cleared() -> None:
    """A scene that was not cleared and now is counts as better."""
    report = compare([_r('x')], [_r('x', cleared_at=10.0)])
    assert report == 'better x: cleared_at - -> 10.0'


def test_compare_changed_for_a_count_change() -> None:
    """A change in kills, with nothing worse or better, is 'changed'."""
    report = compare([_r('x', kills=[1])], [_r('x', kills=[1, 2])])
    assert report == 'changed x: kills 1 -> 2'


def test_compare_worse_takes_precedence_over_better() -> None:
    """A scene that was revived but lost its clear is reported as WORSE."""
    before = [_r('x', dead_at=3.0, cleared_at=10.0)]
    after = [_r('x', cleared_at=None)]
    assert compare(before, after).startswith('WORSE x: ')


def test_compare_groups_are_ordered() -> None:
    """Lines come WORSE first, then changed, better, gone and new; each group sorted by scene name."""
    before = [
        _r('w2', taken=100.0),
        _r('w1'),
        _r('c1', kills=[1]),
        _r('b1', dead_at=3.0),
        _r('g1'),
    ]
    after = [
        _r('w2', taken=200.0),
        _r('w1', dead_at=3.0),
        _r('c1', kills=[1, 2]),
        _r('b1'),
        _r('n1'),
    ]
    assert compare(before, after).splitlines() == [
        'WORSE w1: alive yes -> DEAD',
        'WORSE w2: taken 100 -> 200',
        'changed c1: kills 1 -> 2',
        'better b1: alive DEAD -> yes',
        'gone g1',
        'new n1',
    ]


def test_compare_gone_and_new() -> None:
    """A scene only in before is gone; only in after is new; a shared identical scene adds nothing."""
    report = compare([_r('a'), _r('b')], [_r('b'), _r('c')])
    assert report == 'gone a\nnew c'


@pytest.mark.parametrize(
    ('before', 'after', 'expected'),
    [
        ([], [], 'no differences (0 scenes)'),
        ([_r('a'), _r('b', taken=5.0)], [_r('a'), _r('b', taken=5.2)], 'no differences (2 scenes)'),
    ],
)
def test_compare_no_differences(before: list[Result], after: list[Result], expected: str) -> None:
    """When nothing shown differs the report is the no-differences line with the scene count."""
    assert compare(before, after) == expected
