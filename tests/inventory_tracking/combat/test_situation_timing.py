"""Situations cut from takes in game ticks (combat/timeline.py, sim/situation.py `cut` and `in_ticks`): sample
numbers become ticks from the timestamps, a late sample takes the ticks it was late by, what a sample showed is
held through the ticks skipped before the next one, and events and presses follow their frames."""

import json

import pytest

from inventory_tracking.combat.__main__ import window
from inventory_tracking.combat.sim.situation import cut, describe
from inventory_tracking.combat.takes import Take
from inventory_tracking.combat.timeline import HOLD_TICKS


EVEN = 0.04  # seconds between samples when nothing is late
STRIKE = 1 << 10  # the pointer record's mask bit for the right mouse button (button 3)
LATE = {6: 0.12}  # sample 6 comes 0.12 s after sample 5: every later sample is 0.08 s behind even sampling


def stamps(count, gaps=None):
    """The timestamps of samples 1..count, EVEN apart unless `gaps` gives a sample its own gap from the one before."""
    gaps = gaps or {}
    out, t = {1: 0.0}, 0.0
    for n in range(2, count + 1):
        t += gaps.get(n, EVEN)
        out[n] = t
    return out


def live(unit, x, y):
    """A live hostile monster of type 310 at full life, nobody's."""
    return [unit, 310, 1, x, y, 128, 128, 0, 0xFFFFFFFF, 0]


def sample(n, t, *, area=108, mask=0, monsters=()):
    """Sample `n` at time `t`: the player stands at x = 5000 + n, the strike button is down when `mask` has STRIKE."""
    return {
        't': t, 'n': n, 'late': 0, 'game': True, 'panels': [], 'macro': False,
        'p': [1, 1, area, 5000.0 + n, 5000.0, 0, 388], 'm': list(monsters), 'x': [],
        'in': [0, 0, mask, 0.5, 0.5, []], 'rect': [0, 0, 2560, 1418],
    }  # fmt: skip


def write_take(tmp_path, samples, events=(), manifest=None):
    directory = tmp_path / '20261010T000000Z-108'
    directory.mkdir()
    (directory / 'manifest.json').write_text(json.dumps(manifest or {'area': 108}))
    (directory / 'frames.jsonl').write_text(''.join(json.dumps(s) + '\n' for s in samples))
    (directory / 'events.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))
    return Take.load(directory)


def late_take(tmp_path, times, present=10, events=()):
    """Ten samples at `times`; monster 7 (at x = 5010 + n) is in samples 1..`present` only."""
    samples = [sample(n, t, monsters=[live(7, 5010.0 + n, 5000.0)] if n <= present else []) for n, t in times.items()]
    return write_take(tmp_path, samples, events)


def test_an_evenly_sampled_take_has_one_tick_per_sample(tmp_path):
    # Without late samples the ticks are the sample numbers and the monster is kept on every one of them.
    take = late_take(tmp_path, stamps(50), present=50)
    situation = cut(take)
    assert (situation.start, situation.end) == (1, 50)
    assert situation.seconds == pytest.approx(49 / 25)
    assert situation.late_ticks == 0
    assert all(situation.ticks[n] == n for n in range(1, 51))
    assert all(n in situation.monsters[7].path for n in range(1, 51))


def test_a_late_sample_moves_the_later_ticks_and_holds_the_monster_through_the_gap(tmp_path):
    # A sample 0.08 s late is two ticks late: the ticks after it move, and the sample before is held through the gap.
    take = late_take(tmp_path, stamps(10, LATE))
    situation = cut(take)
    assert situation.ticks[5] == 5
    assert situation.ticks[6] == 8
    assert situation.end == 12
    assert situation.late_ticks == 2
    assert situation.seconds == pytest.approx(11 / 25)
    track = situation.monsters[7]
    assert track.path[6] == track.path[7] == track.path[5] == (5015.0, 5000.0)
    assert situation.player_at(7) == (5005.0, 5000.0)


def test_a_monster_is_not_held_through_skipped_ticks_when_the_next_sample_lacks_it(tmp_path):
    # Holding a monster the next sample no longer shows would invent a position for it.
    take = late_take(tmp_path, stamps(10, LATE), present=5)
    track = cut(take).monsters[7]
    assert track.last == 5
    assert 6 not in track.path
    assert 7 not in track.path


def test_a_hole_longer_than_the_hold_is_left_a_hole(tmp_path):
    # A second without samples is not something the take knows: nothing is held through it.
    take = late_take(tmp_path, stamps(10, {6: 1.0}))
    situation = cut(take)
    track = situation.monsters[7]
    assert situation.ticks[6] - situation.ticks[5] - 1 > HOLD_TICKS
    assert 5 in track.path
    assert situation.ticks[6] in track.path
    assert all(tick not in track.path for tick in range(situation.ticks[5] + 1, situation.ticks[6]))
    assert situation.seconds == pytest.approx((situation.end - situation.start) / 25)
    assert situation.end - situation.start >= 30


def test_events_follow_their_frame_to_its_tick(tmp_path):
    # A recorded kill or hit is placed on the tick of the sample it was stamped with, not on its sample number.
    times = stamps(10, LATE)
    events = [
        {'t': times[8], 'event': 'kill', 'unit': 7, 'txt': 310, 'macro': False},
        {'t': times[7], 'event': 'hit', 'unit': 7, 'txt': 310, 'life': [128, 64], 'macro': False},
    ]
    situation = cut(late_take(tmp_path, times, events=events))
    assert situation.monsters[7].recorded_death == situation.ticks[8]
    ((tick, lost),) = situation.drops[7]
    assert tick == situation.ticks[7]
    assert lost > 0


def test_frames_of_other_levels_are_left_out_with_their_monsters(tmp_path):
    # A stay in another level must not leak its monsters or its frames into the situation.
    areas = [108] * 5 + [35] * 5 + [108] * 5
    samples = []
    for n, (t, area) in enumerate(zip(stamps(15).values(), areas, strict=True), start=1):
        unit = 7 if area == 108 else 9
        samples.append(sample(n, t, area=area, monsters=[live(unit, 5010.0, 5000.0)]))
    situation = cut(write_take(tmp_path, samples))
    assert 9 not in situation.monsters
    assert 7 in situation.monsters
    assert set(situation.ticks) == set(range(1, 6)) | set(range(11, 16))


def test_a_strike_button_held_at_the_start_is_a_press_at_the_first_frame(tmp_path):
    # The press was before the situation: it still has to count as the first thing the strike does.
    samples = [sample(n, t, mask=STRIKE) for n, t in stamps(5).items()]
    situation = cut(write_take(tmp_path, samples))
    assert situation.presses == [(situation.start, True)]


def test_a_cut_from_the_middle_takes_the_button_held_there_and_its_release(tmp_path):
    # Presses are read on the cut's own ticks: held from the window's first sample, released at sample 8.
    times = stamps(10)
    samples = [sample(n, times[n], mask=STRIKE if 2 <= n <= 7 else 0) for n in range(1, 11)]
    events = [
        {'t': times[2], 'event': 'button', 'button': 3, 'down': True},
        {'t': times[8], 'event': 'button', 'button': 3, 'down': False},
    ]
    situation = cut(write_take(tmp_path, samples, events), 5, 10)
    assert situation.presses == [(situation.ticks[5], True), (situation.ticks[8], False)]


def test_no_button_and_no_events_means_no_presses(tmp_path):
    # Nothing pressed is nothing to replay: the presses list stays empty.
    situation = cut(late_take(tmp_path, stamps(10, LATE)))
    assert situation.presses == []


def test_a_take_recorded_faster_than_the_game_is_refused(tmp_path):
    # More samples a second than the game has frames would give ticks that are not real: refuse the take.
    samples = [sample(n, t) for n, t in stamps(10).items()]
    take = write_take(tmp_path, samples, manifest={'area': 108, 'rate': 50.0})
    with pytest.raises(ValueError, match='samples a second'):
        cut(take)


def test_describe_reports_the_late_ticks_of_the_situation(tmp_path):
    # The report that the CLI prints must show the same late ticks the situation carries.
    situation = cut(late_take(tmp_path, stamps(10, LATE)))
    assert describe(situation)['late_ticks'] == situation.late_ticks == 2


def test_the_cli_window_picks_the_longest_stay_in_the_area(tmp_path):
    # The CLI cuts the longest stay in the area asked for; an area never visited is an error, not an empty cut.
    areas = [108] * 3 + [35] * 4 + [108] * 6
    samples = [sample(n, t, area=area) for (n, t), area in zip(stamps(13).items(), areas, strict=True)]
    take = write_take(tmp_path, samples)
    assert set(window(take, 108).ticks) == set(range(8, 14))
    with pytest.raises(SystemExit):
        window(take, 99)
