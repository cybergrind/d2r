"""Statistics for the threat level: life lost per second against the monsters that stood there."""

import json

import pytest

from inventory_tracking.terror.exposure import by_score, by_state, by_type, main, samples


GLOAM, GHOUL, DARK_RANGER = 118, 7, 160


def seen(unit_id, txt_id, *, friendly=False):
    stats = [[0, 172, 2]] if friendly else []
    return {'event': 'seen', 'unit_id': unit_id, 'txt_id': txt_id, 'mode': 1, 'area': 7, 'x': 0, 'y': 0} | {
        'data_hex': '00' * 0x80,
        'stats': stats,
    }


def around(t, life, *unit_ids, area=7):
    near = [[unit_id, 0, 1, 5010 + 2 * unit_id, 5000] for unit_id in unit_ids]
    return {'event': 'around', 't': t, 'area': area, 'x': 5000, 'y': 5000, 'life': life, 'max': 1000, 'near': near}


def life(t, value):
    return {'event': 'life', 't': t, 'area': 7, 'life': value, 'max': 1000, 'x': 5000, 'y': 5000}


def test_a_sample_is_the_life_lost_between_two_looks_around_with_the_hostile_monsters_there():
    events = [
        seen(1, GLOAM), seen(2, GLOAM), seen(3, DARK_RANGER, friendly=True),
        around(1.0, 1000, 1, 2, 3), life(1.25, 900), life(1.5, 950), life(1.75, 800), around(2.0, 800, 1, 2),
    ]  # fmt: skip

    (sample,) = samples(events)

    assert (sample.seconds, sample.lost) == (1.0, pytest.approx(0.25))  # the potion's 50 back are not a gain
    assert [(unit.unit_id, unit.txt_id, unit.x) for unit in sample.units] == [(1, GLOAM, 5012), (2, GLOAM, 5014)]
    assert sample.score == pytest.approx(2 * 1.9 * 5 * 0.25)


def test_a_pause_another_level_or_another_game_ends_a_sample():
    late = [seen(1, GLOAM), around(1.0, 1000, 1), around(9.0, 500, 1)]
    moved = [seen(1, GLOAM), around(1.0, 1000, 1), around(2.0, 500, 1, area=8)]
    left = [seen(1, GLOAM), around(1.0, 1000, 1), {'event': 'left_game', 't': 1.5}, around(2.0, 500, 1)]

    assert [samples(events) for events in (late, moved, left)] == [[], [], []]


def test_life_lost_is_laid_on_the_types_that_stood_there():
    # Two Gloams cost 10% a second; eight Ghouls beside them or alone cost nothing.
    events = [*(seen(n, GLOAM) for n in (1, 2)), *(seen(n, GHOUL) for n in range(10, 18))]
    value, t = 100000, 0.0
    for step in range(30):
        who = ((1, 2), tuple(range(10, 18)), (1, 2, *range(10, 18)))[step % 3]
        events.append(around(t, value, *who))
        value -= 0 if step % 3 == 1 else 100
        t += 1.0
    events.append(around(t, value))

    rows = {row.name: row for row in by_type(samples(events))}

    assert rows['Gloam'].unit_seconds == 40
    assert rows['Gloam'].lost == pytest.approx(0.05, rel=0.05)  # of the life, per monster and second
    assert rows['Ghoul'].lost == pytest.approx(0, abs=1e-3)
    assert rows['Gloam'].threat == pytest.approx(1.9 * 5 * 0.25)


def test_the_bands_are_checked_by_the_life_lost_at_each_score():
    events = [*(seen(n, GLOAM) for n in range(1, 7)), around(0.0, 1000, 1), around(1.0, 990, *range(1, 7))]
    events += [around(2.0, 700, *range(1, 7)), around(3.0, 650)]

    low, high = by_score(samples(events), edges=(9.0,))

    assert (low.seconds, low.lost, low.worst) == (1.0, pytest.approx(0.01), pytest.approx(0.01))
    assert (high.seconds, high.lost, high.worst) == (2.0, pytest.approx(0.17), pytest.approx(0.29))


def test_the_players_states_raise_the_samples_score_and_are_counted_apart():
    cursed = around(1.0, 1000, 1, 2) | {'states': [9, 61, 208]}
    events = [seen(1, GLOAM), seen(2, GLOAM), around(0.0, 1000, 1, 2), cursed, around(2.0, 600, 1, 2), around(3.0, 600)]

    plain, lowered, _ = samples(events)
    rows = {row.name: row for row in by_state([plain, lowered])}

    assert (plain.states, lowered.states) == (frozenset(), frozenset((9, 61, 208)))
    assert lowered.score > 2 * plain.score
    assert (rows['none'].seconds, rows['none'].lost) == (1.0, 0)
    assert (rows['Lower Resist'].seconds, rows['Lower Resist'].lost) == (1.0, pytest.approx(0.4))
    assert rows['Amplify Damage'].lost == pytest.approx(0.4)
    assert '208' in rows  # a state the model has no name for is still counted


def test_rare_types_are_left_out_and_a_type_the_model_scores_nothing_has_no_factor():
    events = [seen(1, GLOAM), *(seen(n, GHOUL) for n in (10, 11)), seen(20, 99999)]
    events += [around(float(t), 1000 - 10 * t, 1, 10, 11, 20) for t in range(6)]

    rows = {row.name: row for row in by_type(samples(events), min_seconds=8)}

    assert set(rows) == {'Ghoul'}  # 10 monster-seconds; the Gloam has 5, the unknown type no row at all
    all_rows = {row.name: row for row in by_type(samples(events))}
    assert (all_rows['Gloam'].unit_seconds, all_rows['Gloam'].off is not None) == (5, True)
    assert all_rows['Ghoul'].threat > 0


def test_the_script_prints_the_three_tables_or_says_that_nothing_was_logged_yet(tmp_path, capsys):
    log, empty = tmp_path / 'terror-probe.jsonl', tmp_path / 'old.jsonl'
    events = [seen(1, GLOAM), seen(2, GLOAM)]
    events += [around(float(t), 1000 - 100 * t, 1, 2) | {'states': [61]} for t in range(4)]
    log.write_text('\n'.join(json.dumps(event) for event in events))
    empty.write_text(json.dumps(seen(1, GLOAM)))

    assert main([str(log), '--min-seconds', '0']) == 0
    out = capsys.readouterr().out
    assert out.startswith('3 samples, 3 s with monsters within a screen, in 1 logs')
    lines = [line.split() for line in out.splitlines()]
    assert ['9-12', '3', '10.00%', '10%'] in lines  # two Gloams under Lower Resist score 11.9
    assert ['Gloam', '6', '5.94', '5.000%', '1.0x'] in lines
    assert ['Lower', 'Resist', '3', '10.00%'] in lines

    assert main([str(empty)]) == 0
    assert 'No `around` events yet' in capsys.readouterr().out
