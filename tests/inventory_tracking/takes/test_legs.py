"""The loop's efficiency read from its takes (takes/legs.py)."""

from pathlib import Path

import pytest

from inventory_tracking.takes.legs import REFERENCE, STALL_SECONDS, legs_of, quiet, report
from inventory_tracking.takes.takes import Take


AREA = 79
CHEST, RACK = 181, 107


def frame(t: float, x: float, y: float, mode: int = 1, objects=()) -> dict:
    return {'t': t, 'p': [1, mode, AREA, x, y], 'm': [], 'o': [list(o) for o in objects]}


def take(frames, events=()) -> Take:
    return Take(Path('20261016T190332Z-79'), {'area': AREA, 'schema': 4}, list(frames), list(events))


def test_a_leg_runs_from_the_arrival_to_each_container_opened_then_the_tail():
    chest = (7, CHEST, 0, 100.0, 0.0)
    rack = (8, RACK, 0, 100.0, 30.0)
    frames = [
        frame(0.0, 0.0, 0.0, objects=(chest, rack)),
        frame(1.0, 0.0, 0.0, 10, (chest, rack)),  # a cast
        frame(2.0, 50.0, 0.0, 3, (chest, rack)),  # a run
        frame(3.0, 98.0, 0.0, objects=(chest, rack)),
        frame(4.0, 98.0, 0.0, objects=((7, CHEST, 2, 100.0, 0.0), rack)),  # the chest opened
        frame(5.0, 98.0, 28.0, 3, ((7, CHEST, 2, 100.0, 0.0), rack)),
        frame(6.0, 98.0, 28.0, objects=((7, CHEST, 2, 100.0, 0.0), (8, RACK, 2, 100.0, 30.0))),  # the rack
        frame(7.0, 98.0, 28.0),
    ]

    first, second, tail = legs_of(take(frames))

    assert (first.to, first.line, first.way, first.seconds) == (CHEST, 100.0, 98.0, 4.0)
    assert (first.casting, first.moving, first.standing) == (1.0, 1.0, 2.0)
    assert first.lost == 0.0  # faster than Blade Warp's pace: nothing lost
    slow = legs_of(
        take(
            [frame(t, 0.0, 0.0) for t in (0.0, 9.0)]
            + [
                frame(10.0, 98.0, 0.0, objects=((7, CHEST, 0, 100.0, 0.0),)),
                frame(11.0, 98.0, 0.0, objects=((7, CHEST, 2, 100.0, 0.0),)),
            ]
        )
    )[0]
    assert slow.lost == pytest.approx(11.0 - 100.0 / REFERENCE)
    assert (second.to, second.seconds) == (RACK, 2.0)
    assert (tail.to, tail.seconds, tail.lost) == (None, 1.0, 1.0)


def test_a_stall_is_standing_long_with_the_log_lines_said_in_it_and_the_players_told_apart():
    frames = [frame(t, 0.0, 0.0) for t in (0.0, 1.0, 2.0, 3.0)] + [frame(4.0, 20.0, 0.0, 3), frame(5.0, 40.0, 0.0)]
    said = [
        {'t': 0.5, 'event': 'log', 'text': 'Macro: No move toward Super chests: the character did not move (x3)'},
        {'t': 1.5, 'event': 'log', 'text': 'Macro: No move toward Super chests: the character did not move (x4)'},
        {'t': 2.5, 'event': 'log', 'text': 'Macro: Firing spot'},
    ]

    [tail] = legs_of(take(frames, said))

    [stall] = tail.stalls
    assert (stall.at, stall.seconds) == (0.0, 4.0)
    assert stall.reasons == ('No move toward Super chests: the character did not move', 'Firing spot')
    assert not stall.mine
    played = [{'t': 0.5, 'event': 'log', 'text': 'Macro: pursuit: the level run is paused: a click'}]
    assert legs_of(take(frames, played))[0].stalls[0].mine
    short = [frame(0.0, 0.0, 0.0), frame(STALL_SECONDS - 0.1, 0.0, 0.0, 3), frame(2.0, 20.0, 0.0)]
    assert legs_of(take(short))[0].stalls == ()


def test_the_first_leg_begins_when_the_game_took_input_and_the_report_names_the_worst():
    chest = (7, CHEST, 0, 50.0, 0.0)
    frames = [frame(t, 0.0, 0.0, objects=(chest,)) for t in (0.0, 1.0, 2.0, 3.0, 4.0)]
    frames += [frame(5.0, 48.0, 0.0, objects=((7, CHEST, 2, 50.0, 0.0),)), frame(6.0, 48.0, 0.0)]
    said = 'Macro: Lower Kurast: took input 3.90s after the arrival (a weapon swap)'
    took = [{'t': 3.9, 'event': 'log', 'text': said}]

    first = legs_of(take(frames, took))[0]

    assert first.begin == 4.0  # the frame at or after the game took input
    lines = report([take(frames, took)], worst=1)
    assert 'arrival 4.0s' in lines[0]
    assert '1 chests and 0 others opened' in lines[0]
    assert any(line.startswith('  20261016T190332Z-79') for line in lines)


def test_idle_is_standing_still_with_no_input_sent_and_away_is_going_back_from_the_container():
    chest = (7, CHEST, 0, 100.0, 0.0)
    frames = [
        frame(0.0, 50.0, 0.0, objects=(chest,)),
        frame(1.0, 50.0, 0.0, objects=(chest,)),  # still, nothing sent: idle
        frame(2.0, 50.0, 0.0, objects=(chest,)),  # still, a key sent in the span: busy
        frame(3.0, 40.0, 0.0, 3, (chest,)),  # a run back, 10 units further from the chest
        frame(4.0, 98.0, 0.0, 3, (chest,)),
        frame(5.0, 98.0, 0.0, objects=((7, CHEST, 2, 100.0, 0.0),)),
    ]
    sent = [{'t': 1.5, 'event': 'sent', 'input': 'key', 'by': 'macro'}]

    leg = legs_of(take(frames, sent))[0]

    assert leg.idle == pytest.approx(1.0)
    assert leg.away == pytest.approx(10.0)
    found = quiet(take(frames, sent))
    assert found is not None
    assert (found.seconds, found.idle, found.stretches) == (5.0, pytest.approx(1.0), ())
    long = quiet(take([frame(t, 0.0, 0.0) for t in (0.0, 1.0, 2.0)]))
    assert long is not None
    assert [(s.at, s.seconds) for s in long.stretches] == [(0.0, 2.0)]
    cast = [{'t': 0.0, 'event': 'cast', 'mode': 10, 'macro': True}]
    waited = quiet(take([frame(t, 0.0, 0.0) for t in (0.0, 1.1, 2.1)], cast))
    assert waited is not None
    assert (waited.delay, waited.idle) == (pytest.approx(1.1), pytest.approx(1.0))  # Blade Warp's delay, then idle
    loading = quiet(take([{**frame(t, 0.0, 0.0), 'view': 0} for t in (0.0, 1.0, 2.0)]))
    assert loading is not None
    assert loading.idle == 0.0  # the game's loading screen, not the macro's
