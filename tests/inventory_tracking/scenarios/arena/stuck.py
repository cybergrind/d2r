"""The `stuck` moments of a take (framework-plan.md, Task 1.4, moved to 1.8): the player asked the
macro for a routine PRESSES times within WINDOW seconds and the character did not get anywhere.

A routine press is a line of the service's log (runs/alt-d/<session>/probe.log):

    2026-10-12 00:16:24,205 INFO Macro: request teleport, 0 ms old, while hunt any

read with scenarios/battle/tower_cellar5.py `LINE` (stamp, milliseconds, level, text) and its `presses`
rule for the text (evidence.py's `press` rule is the same without the age). The press was `N ms old`
when the line was written.

The log's clock is the host's local time and a take's is the recorder's monotonic one. The two meet
at the take's opening, which the same log holds:

    2026-10-11 22:50:37,567 INFO Combat take 20261011T195037Z-25 opened in area 25

against the manifest's `started_at` (UTC, 19:50:37.566): the difference, to the quarter hour, is the
log's offset from UTC, and a line's seconds into the take are its stamp less that offset less
`started_at`. Without the opening line (a log cut down for a fixture) the offset is the one the stance
fixtures were cut with (scenarios/stance/build_fixtures.py LOCAL_OFFSET).
"""

import math
import re
from bisect import bisect_left, bisect_right
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from inventory_tracking.macros.teleport import MOVED
from inventory_tracking.takes.takes import Take, player_of
from tests.inventory_tracking.scenarios.arena.moments import APART, Moment
from tests.inventory_tracking.scenarios.battle.tower_cellar5 import LINE
from tests.inventory_tracking.scenarios.stance.build_fixtures import LOCAL_OFFSET


PRESSES = 3  # routine presses ...
WINDOW = 5.0  # ... within this many seconds
PRESS = re.compile(r'Macro: request ([a-z ]+), (\d+) ms old')  # macros/runner.py `request`; as tower_cellar5.presses
OPENED = re.compile(r'Combat take (\S+) opened in area \d+')  # takes/record.py, the line of a take's opening
QUARTER = 900.0  # seconds: a clock's offset from UTC is a whole number of these


def stamp(day: str, milliseconds: str) -> datetime:
    return datetime.strptime(day, '%Y-%m-%d %H:%M:%S').replace(microsecond=int(milliseconds) * 1000, tzinfo=UTC)


def offset(take: Take, probe_lines: Sequence[str]) -> timedelta:
    """The log's clock less UTC: from the line of the take's opening, else LOCAL_OFFSET."""
    names = {take.directory.name, take.recording}
    started = datetime.fromisoformat(take.manifest['started_at'])
    for line in probe_lines:
        if 'Combat take' not in line:
            continue
        match = LINE.match(line)
        opened = OPENED.match(match[4]) if match else None
        if match and opened and opened[1] in names:
            apart = (stamp(match[1], match[2]) - started).total_seconds()
            return timedelta(seconds=round(apart / QUARTER) * QUARTER)
    return LOCAL_OFFSET


def presses(take: Take, probe_lines: Sequence[str]) -> list[tuple[float, str]]:
    """The routine presses of the log that fall in the take: (seconds from its first frame, routine),
    in time order. A press is put where the key went down, not where its line was written."""
    if not take.frames or 'started_at' not in take.manifest:
        return []
    started = datetime.fromisoformat(take.manifest['started_at']) + offset(take, probe_lines)
    found = []
    for line in probe_lines:
        if 'Macro: request' not in line:
            continue
        match = LINE.match(line)
        press = PRESS.search(match[4]) if match else None
        if match and press:
            at = (stamp(match[1], match[2]) - started).total_seconds() - int(press[2]) / 1000
            if 0.0 <= at <= take.seconds:
                found.append((at, press[1]))
    return sorted(found)


def stuck(take: Take, probe_lines: Sequence[str]) -> list[Moment]:
    """The moments at which PRESSES routine presses came within WINDOW seconds while the character
    never got MOVED from where it stood at the first of them (the frames from the first press to the
    last). The moment's frame is that of the first press (no lead: before it the character may have
    been somewhere else); moments within APART seconds of the kept one are one, as in moments.py."""
    asked = presses(take, probe_lines)
    if len(asked) < PRESSES:
        return []
    start = take.frames[0]['t']
    rel = [frame['t'] - start for frame in take.frames]
    times = [at for at, _routine in asked]
    found: list[Moment] = []
    for pos, first in enumerate(times[: len(times) - PRESSES + 1]):
        last = times[pos + PRESSES - 1]
        if last - first > WINDOW or (found and first - found[-1].at < APART):
            continue
        frames = range(max(bisect_right(rel, first) - 1, 0), min(bisect_left(rel, last) + 1, len(rel)))
        places = [player.at for index in frames if (player := player_of(take.frames[index])) is not None]
        if not places:
            continue
        moved = max(math.dist(places[0], place) for place in places)
        if moved >= MOVED:
            continue
        routines = Counter(routine for _at, routine in asked[pos : pos + PRESSES])
        what = ', '.join(f'{routine} x{count}' for routine, count in sorted(routines.items()))
        found.append(Moment(frames[0], 'stuck', first, f'{what} within {last - first:.1f} s, moved {moved:.1f}'))
    return found
