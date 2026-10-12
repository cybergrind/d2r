"""The `stuck` moments (stuck.py): routine presses of the service's log laid on a take's clock."""

from datetime import timedelta
from pathlib import Path

from inventory_tracking.combat.takes import Take
from inventory_tracking.macros.teleport import MOVED
from tests.inventory_tracking.scenarios.arena.moments import Moment
from tests.inventory_tracking.scenarios.arena.stuck import offset, presses, stuck
from tests.inventory_tracking.scenarios.stance.build_fixtures import LOCAL_OFFSET


TOWER = Path(__file__).parents[1] / 'battle' / 'fixtures' / 'tower-cellar5-herald'
NAME = '20261011T120000Z-25'
OPENED = f'2026-10-11 15:00:00,003 INFO Combat take {NAME} opened in area 25'  # 12:00:00 UTC on a clock of UTC+3


def take(places: list[tuple[float, float]], rate: float = 5.0) -> Take:
    """A take that began at 12:00:00 UTC with the character at `places`, `rate` frames a second."""
    frames = [
        {'t': 500.0 + index / rate, 'n': index, 'p': [1, 1, 25, x, y, 0, 388, 900, 1800, 400, 500], 'm': [], 'x': []}
        for index, (x, y) in enumerate(places)
    ]
    return Take(Path('/nowhere') / NAME, {'schema': 2, 'started_at': '2026-10-11T12:00:00+00:00'}, frames)


def press(seconds: float, routine: str = 'teleport', age: int = 0, hour: int = 15) -> str:
    """The log's line of a routine press `seconds` into the take (macros/runner.py `request`)."""
    whole, milli = int(seconds), round(seconds % 1 * 1000)
    stamp = f'2026-10-11 {hour:02d}:00:{whole:02d},{milli:03d}'
    return f'{stamp} INFO Macro: request {routine}, {age} ms old, while hunt any'


STILL = [(100.0, 200.0)] * 60  # twelve seconds on one spot


def test_three_presses_in_five_seconds_on_one_spot_are_a_moment_at_the_first():
    lines = [OPENED, press(2.0), press(3.5), press(6.9)]
    assert stuck(take(STILL), lines) == [Moment(10, 'stuck', 2.0, 'teleport x3 within 4.9 s, moved 0.0')]


def test_the_note_names_the_routines_pressed():
    lines = [OPENED, press(2.0, 'pickup'), press(2.5, 'hunt any'), press(3.0, 'pickup')]
    assert stuck(take(STILL), lines)[0].note == 'hunt any x1, pickup x2 within 1.0 s, moved 0.0'


def test_two_presses_or_three_spread_over_more_than_five_seconds_are_none():
    assert stuck(take(STILL), [OPENED, press(2.0), press(3.0)]) == []
    assert stuck(take(STILL), [OPENED, press(2.0), press(3.0), press(7.1)]) == []


def test_a_character_that_moved_was_not_stuck():
    lines = [OPENED, press(2.0), press(3.0), press(4.0)]
    hopped = [(100.0, 200.0)] * 16 + [(100.0 + MOVED, 200.0)] * 44  # the hop shows 3.2 s in
    assert stuck(take(hopped), lines) == []
    nearly = [(100.0, 200.0)] * 16 + [(100.0 + MOVED - 0.01, 200.0)] * 44
    assert [moment.note for moment in stuck(take(nearly), lines)] == ['teleport x3 within 2.0 s, moved 2.0']
    # A move after the last of the three is not in their time.
    late = [(100.0, 200.0)] * 22 + [(130.0, 200.0)] * 38
    assert len(stuck(take(late), lines)) == 1


def test_a_press_is_where_the_key_went_down_not_where_its_line_was_written():
    lines = [OPENED, press(2.0), press(3.0), press(7.4, age=500)]  # the key 6.9 s in
    assert [at for at, _routine in presses(take(STILL), lines)] == [2.0, 3.0, 6.9]
    assert len(stuck(take(STILL), lines)) == 1


def test_moments_nearer_than_five_seconds_are_one():
    lines = [OPENED, *(press(1.0 + n) for n in range(10))]  # a press a second from 1.0 to 10.0
    assert [moment.at for moment in stuck(take(STILL), lines)] == [1.0, 6.0]


def test_presses_outside_the_take_and_lines_of_other_kinds_are_not_read():
    lines = [OPENED, press(13.0), press(14.0), press(15.0), '2026-10-11 15:00:02,000 INFO Macro: Attack mode on']
    lines += ['2026-10-11 15:00:03,000 WARNING Macro: request teleport dropped: 2600 ms old', 'not a log line']
    assert presses(take(STILL), lines) == []
    assert stuck(take(STILL), lines) == []


def test_the_logs_offset_from_utc_is_read_from_the_takes_opening():
    assert offset(take(STILL), [OPENED]) == timedelta(hours=3)
    summer = OPENED.replace('15:00:00', '14:00:00')  # the same opening on a clock of UTC+2
    lines = [summer, press(2.0, hour=14), press(3.0, hour=14), press(4.0, hour=14)]
    assert offset(take(STILL), lines) == timedelta(hours=2)
    assert [moment.at for moment in stuck(take(STILL), lines)] == [2.0]
    # The opening of another take says nothing about this one: the stance fixtures' offset.
    assert offset(take(STILL), [OPENED.replace(NAME, '20261011T110000Z-25')]) == LOCAL_OFFSET
    assert offset(take(STILL), []) == LOCAL_OFFSET


def test_a_take_without_frames_or_start_has_none():
    assert stuck(Take(Path('/nowhere') / NAME, {'schema': 2}), [OPENED, press(1.0), press(2.0), press(3.0)]) == []
    assert stuck(take([]), [OPENED, press(1.0), press(2.0), press(3.0)]) == []


def test_the_tower_cellar_log_on_its_take():
    """The fixture of scenarios/battle: a trim of 20261011T195037Z-25 with the service's log of the same
    seconds. Pickup was pressed fourteen times in the fight; the first presses came while the character
    walked, and the three from 12.0 s (22:50:49.56 in the log) found it standing under the Herald's pack."""
    found = Take.load(TOWER)
    lines = (TOWER / 'probe.log').read_text().splitlines()
    assert offset(found, lines) == timedelta(hours=3)
    asked = presses(found, lines)
    assert len(asked) == 14
    assert asked[0] == (1.353948, 'pickup')  # 22:50:38.920 less the take's start, 19:50:37.566052 UTC
    assert stuck(found, lines) == [Moment(295, 'stuck', 11.993948, 'pickup x3 within 1.4 s, moved 0.0')]
