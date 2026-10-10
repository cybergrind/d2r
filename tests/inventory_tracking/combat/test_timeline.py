"""combat/timeline.py: game ticks from the sample timestamps, stays in an area and mouse buttons."""

import random
from itertools import pairwise
from typing import Any

from inventory_tracking.combat.timeline import (
    GAME_RATE,
    button_down,
    longest_visit,
    ticks,
    visits,
)


def _frame(n: int, t: float, area: int | None = 108, mask: int | None = None) -> dict[str, Any]:
    player = [1, 1, area, 0.0, 0.0] if area is not None else None
    return {'n': n, 't': t, 'p': player, 'in': [0, 0, mask, 0.5, 0.5, []]}


def _even(first_n: int, count: int, rate: float = GAME_RATE) -> list[dict[str, Any]]:
    return [_frame(first_n + k, k / rate) for k in range(count)]


def test_even_sampling_is_identity_from_one() -> None:
    frames = _even(1, 200)
    assert ticks(frames) == {frame['n']: frame['n'] for frame in frames}


def test_even_sampling_is_identity_from_500() -> None:
    frames = _even(500, 200)
    assert ticks(frames) == {frame['n']: frame['n'] for frame in frames}


def test_empty_input_gives_no_ticks() -> None:
    assert ticks([]) == {}


def test_one_late_sample_skips_two_ticks_and_the_offset_stays() -> None:
    frames = _even(1, 3)  # n 1..3 at 0.00, 0.04, 0.08
    frames.append(_frame(4, 0.20))  # 0.12 s after the last one: two periods late
    frames += [_frame(n, (n - 1) / GAME_RATE) for n in range(5, 12)]
    tick_of = ticks(frames)
    assert tick_of[3] == 3
    assert tick_of[4] == 6
    assert all(tick_of[n] == n + 2 for n in range(4, 12))


def test_constant_phase_shift_after_a_late_sample_adds_no_ticks() -> None:
    frames = _even(1, 3)
    frames.append(_frame(4, 0.20))  # late by two periods
    # every later sample sits half a period off the grid
    frames += [_frame(n, (n - 4) / GAME_RATE + 0.20 + 0.02) for n in range(5, 60)]
    tick_of = ticks(frames)
    assert all(tick_of[n] == n + 2 for n in range(4, 60))


def test_small_jitter_is_identity() -> None:
    rng = random.Random(1)
    frames = [_frame(k + 1, k / GAME_RATE + rng.uniform(-0.005, 0.005)) for k in range(2000)]
    assert ticks(frames) == {frame['n']: frame['n'] for frame in frames}


def test_rate_50_recording_is_identity_at_rate_50() -> None:
    frames = _even(1, 300, rate=50.0)
    assert ticks(frames, rate=50.0) == {frame['n']: frame['n'] for frame in frames}


def test_0_08_second_samples_advance_two_ticks_each_at_the_default_rate() -> None:
    frames = [_frame(k + 1, 0.08 * k) for k in range(50)]
    tick_of = ticks(frames)
    steps = [tick_of[b['n']] - tick_of[a['n']] for a, b in pairwise(frames)]
    assert steps == [2] * 49


def test_total_drift_stays_under_one_tick() -> None:
    rng = random.Random(2)
    t = 0.0
    frames = [_frame(1, t)]
    for n in range(2, 501):
        t += rng.choice([0.04, 0.04, 0.04, 0.08, 0.12])
        frames.append(_frame(n, t))
    tick_of = ticks(frames)
    assert abs((tick_of[500] - tick_of[1]) - (frames[-1]['t'] - frames[0]['t']) * GAME_RATE) < 1


def test_visits_go_out_and_back() -> None:
    frames = [_frame(1, 0.0, 108), _frame(2, 0.04, 35), _frame(3, 0.08, 108)]
    assert visits(frames, 108) == [(1, 1), (3, 3)]


def test_visit_survives_a_frame_with_no_player() -> None:
    frames = [
        _frame(1, 0.00, 108),
        _frame(2, 0.04, 108),
        _frame(3, 0.08, None),
        _frame(4, 0.12, 108),
        _frame(5, 0.16, 108),
    ]
    assert visits(frames, 108) == [(1, 5)]


def test_visits_example_with_no_player_frame() -> None:
    areas = [108, 108, 35, 108, None, 108]
    frames = [_frame(n, (n - 1) * 0.04, area) for n, area in enumerate(areas, start=1)]
    assert visits(frames, 108) == [(1, 2), (4, 6)]


def test_visits_with_no_match_is_empty() -> None:
    assert visits([_frame(1, 0.0, 35), _frame(2, 0.04, 35)], 108) == []


def test_longest_visit_counts_frames() -> None:
    areas = [108, 108, 35, 108, 108, 108, 108, 108]
    frames = [_frame(n, (n - 1) * 0.04, area) for n, area in enumerate(areas, start=1)]
    assert longest_visit(frames, 108) == (4, 8)


def test_longest_visit_takes_the_earliest_on_a_tie() -> None:
    areas = [108, 108, 35, 108, 108]
    frames = [_frame(n, (n - 1) * 0.04, area) for n, area in enumerate(areas, start=1)]
    assert longest_visit(frames, 108) == (1, 2)


def test_longest_visit_is_none_without_a_match() -> None:
    assert longest_visit([_frame(1, 0.0, 35)], 108) is None


def test_button_down_reads_button_three() -> None:
    assert button_down(_frame(1, 0.0, mask=1 << 10), 3) is True


def test_button_down_is_false_for_mask_zero() -> None:
    assert button_down(_frame(1, 0.0, mask=0), 3) is False


def test_button_down_is_false_for_mask_none() -> None:
    assert button_down(_frame(1, 0.0, mask=None), 3) is False


def test_button_down_is_false_without_an_in_record() -> None:
    assert button_down({'n': 1, 't': 0.0, 'p': None}, 3) is False


def test_a_take_says_its_rows_layout_and_an_unknown_one_is_refused(tmp_path) -> None:
    # review.md, finding 6: the rows had no version, and their meaning has changed once already.
    import json

    import pytest

    from inventory_tracking.combat.record import SCHEMA
    from inventory_tracking.combat.takes import SCHEMAS, Take

    assert SCHEMA in SCHEMAS
    (tmp_path / 'manifest.json').write_text(json.dumps({'area': 108}))
    assert Take.load(tmp_path).schema == 1  # a take from before the version was written
    (tmp_path / 'manifest.json').write_text(json.dumps({'area': 108, 'schema': SCHEMA}))
    assert Take.load(tmp_path).schema == SCHEMA
    (tmp_path / 'manifest.json').write_text(json.dumps({'area': 108, 'schema': SCHEMA + 1}))
    with pytest.raises(ValueError, match='schema'):
        Take.load(tmp_path)
