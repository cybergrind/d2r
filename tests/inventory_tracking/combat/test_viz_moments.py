"""Tests for the replay moment finder, using small hand-built traces."""

from itertools import pairwise

from inventory_tracking.combat.viz_moments import (
    IDLE,
    KILL,
    KINDS,
    MISS,
    POLICY_AHEAD,
    RECORDED_AHEAD,
    Moment,
    Trace,
    find_moments,
)


def _trace(
    name: str,
    taken: tuple[tuple[int, float], ...] = (),
    casts: tuple[tuple[int, int], ...] = (),
    deaths: dict[int, int] | None = None,
) -> Trace:
    return Trace(name=name, taken=taken, casts=casts, deaths=dict(deaths or {}))


def _of_kind(moments: list[Moment], kind: str) -> list[Moment]:
    return [moment for moment in moments if moment.kind == kind]


def test_kinds_are_the_five_names() -> None:
    assert KINDS == ('policy_ahead', 'recorded_ahead', 'idle', 'miss', 'kill')


def test_policy_ahead_window_exact() -> None:
    recorded = _trace('recorded')
    policy = _trace('policy', taken=((10, 5.0),))
    moments = find_moments(0, 99, recorded, policy)
    assert moments == [Moment(0, 74, POLICY_AHEAD, 'policy took 5 more life in 3.0 s', 5.0)]


def test_recorded_ahead_window_exact() -> None:
    recorded = _trace('recorded', taken=((30, 4.0),))
    policy = _trace('policy')
    moments = find_moments(0, 99, recorded, policy)
    # Windows starting at 0, 15 and 30 all hold the take; the earliest wins and the others overlap it.
    assert moments == [Moment(0, 74, RECORDED_AHEAD, 'recorded casts took 4 more life than policy in 3.0 s', 4.0)]


def test_policy_windows_pick_largest_then_earlier_and_never_overlap() -> None:
    # Ticks 100 and 110 hold 18 life; windows starting at 45, 60, 75 and 90 all reach both and tie at 18.
    # The earliest of them (45) is picked and the rest overlap it. A far take at 400 is a separate window.
    policy = _trace('policy', taken=((100, 10.0), (110, 8.0), (400, 3.0)))
    recorded = _trace('recorded')
    moments = _of_kind(find_moments(0, 499, recorded, policy), POLICY_AHEAD)
    assert moments == [
        Moment(45, 119, POLICY_AHEAD, 'policy took 18 more life in 3.0 s', 18.0),
        Moment(330, 404, POLICY_AHEAD, 'policy took 3 more life in 3.0 s', 3.0),
    ]
    only_one = _of_kind(find_moments(0, 499, recorded, policy, per_kind=1), POLICY_AHEAD)
    assert only_one == [Moment(45, 119, POLICY_AHEAD, 'policy took 18 more life in 3.0 s', 18.0)]


def test_windows_of_one_kind_never_overlap() -> None:
    policy = _trace('policy', taken=tuple((tick, 1.0) for tick in range(0, 500, 10)))
    moments = _of_kind(find_moments(0, 499, _trace('recorded'), policy), POLICY_AHEAD)
    assert 1 <= len(moments) <= 5
    for before, after in pairwise(moments):
        assert before.last < after.first


def test_idle_gaps_exact_with_tie_and_per_kind() -> None:
    # Recorded casts at 20 and 150 leave gaps (-1, 20) too short, (20, 150) and (150, 200).
    recorded = _trace('recorded', casts=((20, 1), (150, 1)))
    policy = _trace('policy', casts=((30, 1), (60, 0), (90, 2), (160, 1), (170, 1)))
    moments = _of_kind(find_moments(0, 199, recorded, policy), IDLE)
    assert moments == [
        Moment(30, 90, IDLE, 'policy cast 2 times on monsters while the player did not cast for 5.2 s', 2.0),
        Moment(160, 170, IDLE, 'policy cast 2 times on monsters while the player did not cast for 2.0 s', 2.0),
    ]
    # Equal values: the earlier moment is kept when only one is allowed.
    first_only = _of_kind(find_moments(0, 199, recorded, policy, per_kind=1), IDLE)
    assert first_only == [moments[0]]


def test_idle_keeps_highest_value() -> None:
    recorded = _trace('recorded', casts=((20, 1), (150, 1)))
    policy = _trace('policy', casts=((30, 1), (60, 0), (90, 2), (160, 1), (170, 1), (175, 1)))
    moments = _of_kind(find_moments(0, 199, recorded, policy, per_kind=1), IDLE)
    assert moments == [
        Moment(160, 175, IDLE, 'policy cast 3 times on monsters while the player did not cast for 2.0 s', 3.0)
    ]


def test_idle_needs_two_policy_casts_in_a_gap() -> None:
    recorded = _trace('recorded', casts=((20, 1), (150, 1)))
    policy = _trace('policy', casts=((30, 1), (60, 0)))
    assert _of_kind(find_moments(0, 199, recorded, policy), IDLE) == []


def test_miss_runs_exact_with_blade_tail_and_end_clamp() -> None:
    # Runs: [10, 20] with 2 casts, [40, 60] with 3 casts, and [90] which would outlive end=100.
    recorded = _trace('recorded', casts=((10, 0), (20, 0), (30, 1), (40, 0), (50, 0), (60, 0), (70, 1), (90, 0)))
    policy = _trace('policy')
    moments = _of_kind(find_moments(0, 100, recorded, policy), MISS)
    assert moments == [
        Moment(10, 58, MISS, '2 recorded casts in a row hit nothing', 2.0),
        Moment(40, 98, MISS, '3 recorded casts in a row hit nothing', 3.0),
        Moment(90, 100, MISS, '1 recorded cast hit nothing', 1.0),
    ]
    biggest = _of_kind(find_moments(0, 100, recorded, policy, per_kind=1), MISS)
    assert biggest == [Moment(40, 98, MISS, '3 recorded casts in a row hit nothing', 3.0)]


def test_kill_exact_threshold_sign_and_missing_units() -> None:
    recorded = _trace('recorded', deaths={7: 300, 9: 200, 13: 50, 99: 100})
    policy = _trace('policy', deaths={7: 100, 9: 190, 13: 120})
    moments = _of_kind(
        find_moments(0, 500, _trace('recorded'), _trace('policy'), elites=frozenset({7, 9, 13, 99})), KILL
    )
    assert moments == []
    moments = _of_kind(find_moments(0, 500, recorded, policy, elites=frozenset({7, 9, 13, 99})), KILL)
    assert moments == [
        Moment(50, 120, KILL, 'an elite dies 2.8 s later under policy', -2.8),
        Moment(100, 300, KILL, 'an elite dies 8.0 s earlier under policy', 8.0),
    ]


def test_kill_ties_take_earlier_first_and_per_kind_keeps_largest() -> None:
    recorded = _trace('recorded', deaths={3: 400, 4: 100})
    policy = _trace('policy', deaths={3: 350, 4: 150})
    moments = find_moments(0, 500, _trace('recorded'), _trace('policy'), elites=frozenset({3, 4}), per_kind=1)
    assert _of_kind(moments, KILL) == []
    moments = find_moments(0, 500, recorded, policy, elites=frozenset({3, 4}), per_kind=1)
    assert _of_kind(moments, KILL) == [Moment(100, 150, KILL, 'an elite dies 2.0 s later under policy', -2.0)]


def test_kill_per_kind_keeps_largest_absolute_value() -> None:
    recorded = _trace('recorded', deaths={1: 150, 2: 200, 3: 250, 4: 300})
    policy = _trace('policy', deaths={1: 100, 2: 100, 3: 100, 4: 100})
    moments = find_moments(0, 500, recorded, policy, elites=frozenset({1, 2, 3, 4}), per_kind=2)
    assert _of_kind(moments, KILL) == [
        Moment(100, 250, KILL, 'an elite dies 6.0 s earlier under policy', 6.0),
        Moment(100, 300, KILL, 'an elite dies 8.0 s earlier under policy', 8.0),
    ]


def test_moments_are_clamped_into_range() -> None:
    # The miss run at 10 ends at 48, before start=50, so both ends clamp to 50.
    recorded = _trace('recorded', casts=((10, 0),), deaths={1: 10})
    policy = _trace('policy', deaths={1: 300})
    moments = find_moments(50, 100, recorded, policy, elites=frozenset({1}))
    assert Moment(50, 50, MISS, '1 recorded cast hit nothing', 1.0) in moments
    assert Moment(50, 100, KILL, 'an elite dies 11.6 s later under policy', -11.6) in moments
    for moment in moments:
        assert 50 <= moment.first <= moment.last <= 100


def test_empty_traces_give_nothing() -> None:
    empty = _trace('empty')
    assert find_moments(0, 500, empty, _trace('policy')) == []
    assert find_moments(0, 500, empty, empty, elites=frozenset({1, 2})) == []


def test_end_before_start_gives_nothing() -> None:
    busy = _trace('recorded', taken=((10, 5.0),), casts=((20, 0),))
    assert find_moments(100, 50, busy, _trace('policy', taken=((60, 9.0),))) == []


def _combined() -> tuple[int, int, Trace, Trace, frozenset[int]]:
    recorded = _trace('recorded', casts=((20, 0), (30, 0)), deaths={5: 300})
    policy = _trace(
        'policy',
        taken=((100, 10.0), (110, 8.0), (400, 3.0)),
        casts=((120, 1), (130, 1)),
        deaths={5: 200},
    )
    return 0, 499, recorded, policy, frozenset({5})


def test_combined_result_is_exact_and_sorted() -> None:
    start, end, recorded, policy, elites = _combined()
    moments = find_moments(start, end, recorded, policy, elites=elites)
    assert moments == [
        Moment(20, 68, MISS, '2 recorded casts in a row hit nothing', 2.0),
        Moment(45, 119, POLICY_AHEAD, 'policy took 18 more life in 3.0 s', 18.0),
        Moment(120, 130, IDLE, 'policy cast 2 times on monsters while the player did not cast for 18.8 s', 2.0),
        Moment(200, 300, KILL, 'an elite dies 4.0 s earlier under policy', 4.0),
        Moment(330, 404, POLICY_AHEAD, 'policy took 3 more life in 3.0 s', 3.0),
    ]
    keys = [(moment.first, moment.last, moment.kind) for moment in moments]
    assert keys == sorted(keys)


def test_repeated_calls_are_equal_and_inputs_untouched() -> None:
    start, end, recorded, policy, elites = _combined()
    before = (recorded.taken, recorded.casts, dict(recorded.deaths), policy.taken, policy.casts, dict(policy.deaths))
    first = find_moments(start, end, recorded, policy, elites=elites)
    second = find_moments(start, end, recorded, policy, elites=elites)
    assert first == second
    after = (recorded.taken, recorded.casts, recorded.deaths, policy.taken, policy.casts, policy.deaths)
    assert before == after


def test_a_missed_cast_long_after_the_one_before_starts_its_own_run():
    recorded = Trace('recorded', [], [(100, 0), (120, 0), (400, 0)], {})
    policy = Trace('live', [], [], {})
    found = [m for m in find_moments(1, 1000, recorded, policy, miss_gap=75) if m.kind == MISS]
    assert [(m.first, m.last, m.value) for m in found] == [(100, 158, 2.0), (400, 438, 1.0)]
