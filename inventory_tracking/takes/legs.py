"""The KP_6 loop's efficiency, read from its takes: how the time on a level goes from one container opened to the next.

The player, 2026-10-16: "can you think about some efficiency metric for runs analysis ... linear distance we need to
travel vs actual distance travelled and time, then find some clear outliers and analyze and test navigation
improvements"; the aim, "minimal time on the map and maximizing number of opened chests per hour".

A leg runs from the character's arrival, or the last container opened, to the next container opened (its mode leaves
0 in the take's objects, `o`); the take's last leg runs from the last one to the level left (`tail`). For each:

- `line`: the straight line from where the character stood to the container; `way`: what it went (frame to frame);
- the seconds, split by the character's mode: `casting` (an action under way, a jump's cast among them), `moving` (a
  walk or a run), `standing` (the rest: a look, a casting delay waited out, a stall);
- `stalls`: the stretches standing STALL_SECONDS and more (a Blade Warp's whole delay and a look are under it), each
  with the log lines said most in it (`reasons`, numbers folded): the first clue to why;
- the first leg begins when the game took input (the log's `took input N s after the arrival`, macros/routines.py
  `took_input`): the level's load before it is the game's, reported as `arrival`;
- a stall the player's hand made (the loop toggled, the run paused) is told apart (`Stall.mine`);
- `lost`: the seconds over the straight line at REFERENCE units a second (Blade Warp's pace: its 22 units every
  1.05 s), the measure the outliers are ranked by;
- `idle`: the seconds the character stood still (under STILL units frame to frame), neither casting nor moving, with
  no input the service sent within QUIET of it: time nothing was done at all (the player, 2026-10-17: "measure
  inactive time (when we're not moving or not doing anything)"). Idle within DELAY of a cast's start is a skill's delay
  waited out (`delay`, Blade Warp's 1.05 s), not counted as idle. `quiet` measures it over a whole take, the towns'
  takes too;
- `away`: the units moved that took the character further from the leg's container: going back ("backtracking
  movements").

Read-only, over the takes on disk (takes/record.py writes them): `python -m inventory_tracking.takes.legs <take>...`.
"""

import argparse
import bisect
import datetime
import itertools
import math
import re
import statistics
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from inventory_tracking.takes.takes import Take


__all__ = ['Leg', 'Quiet', 'legs_of', 'main', 'quiet', 'report']

CHESTS = frozenset((181, 183))  # JungleChest, JungleChest2: the camps' marks (macros/shacks.py)
CONTAINERS = CHESTS | frozenset((104, 106, 107, 208, 209))  # and a shack's others (macros/shacks.py OPENED)
CASTING = frozenset((7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18))  # attacks, casts, skills (macros/routines.py ACTING)
MOVING = frozenset((2, 3, 6))  # walk, run, town walk
REFERENCE = 21.0  # units a second: a Blade Warp's 22 units every 1.05 s (builds/warlock/movement.py WARP_DELAY)
STALL_SECONDS = 1.5  # standing this long and more is a stall
REASONS = 2  # the log lines named for a stall
STILL = 0.5  # units frame to frame: under this the character stood still
QUIET = 0.3  # seconds: an input sent this near (before, or within the frame's span) makes the moment busy
DELAY = 1.05  # seconds after a cast's start: still and quiet there is a skill's delay waited out (Blade Warp's)
NUMBER = re.compile(r'\d+(\.\d+)?')


# A stall whose log says the player's hand made it: the loop toggled by KP_6, the level run paused for the player
PLAYERS = ('request loop', 'Loop on', 'Loop off', 'paused', 'the player', 'the hand')


@dataclass(frozen=True)
class Stall:
    at: float  # the take's clock
    seconds: float
    reasons: tuple[str, ...] = ()

    @property
    def mine(self) -> bool:
        """Whether the player's hand made it (`PLAYERS`), not the macro."""
        return any(word in reason for reason in self.reasons for word in PLAYERS)


def stalled(legs: Iterable[Leg], *, mine: bool) -> float:
    return sum(stall.seconds for leg in legs for stall in leg.stalls if stall.mine == mine)


@dataclass(frozen=True)
class Leg:
    take: str
    begin: float  # the take's clock
    end: float
    to: int | None  # the class of the container opened at its end; None for the tail
    line: float
    way: float
    casting: float
    moving: float
    standing: float
    stalls: tuple[Stall, ...] = field(default=())
    idle: float = 0.0  # seconds still, not casting nor moving, no input sent, past a skill's delay (the module text)
    delay: float = 0.0  # seconds the same, within DELAY of a cast's start
    away: float = 0.0  # units moved further from the container (the tail: none)

    @property
    def seconds(self) -> float:
        return self.end - self.begin

    @property
    def lost(self) -> float:
        """Seconds over the straight line at REFERENCE units a second (the tail: all of it)."""
        return max(0.0, self.seconds - self.line / REFERENCE)

    @property
    def speed(self) -> float:
        return self.line / self.seconds if self.seconds > 0 else 0.0

    @property
    def detour(self) -> float:
        return self.way / self.line if self.line >= 1.0 else 0.0


def opened(take: Take) -> list[tuple[float, tuple[float, float], int]]:
    """The containers opened during the take, in order: (clock, place, class)."""
    found, mode_of = [], {}
    for frame in take.frames:
        for row in frame.get('o') or []:
            unit, txt, mode, x, y = row[:5]
            if txt in CONTAINERS and mode_of.get(unit) == 0 and mode != 0:
                found.append((frame['t'], (x, y), txt))
            mode_of[unit] = mode
    return found


def fold(text: str) -> str:
    return NUMBER.sub('N', text.removeprefix('Macro: ')).replace(' (xN)', '')


def _reasons(take: Take, begin: float, end: float) -> tuple[str, ...]:
    said = Counter(
        fold(event['text'])
        for event in take.events
        if event['event'] == 'log' and begin <= event['t'] <= end and 'text' in event
    )
    return tuple(text for text, _ in said.most_common(REASONS))


def sent_times(take: Take) -> list[float]:
    """The clocks of the inputs the service sent (the take's `sent` events), in order."""
    return sorted(event['t'] for event in take.events if event['event'] == 'sent')


def cast_times(take: Take) -> list[float]:
    """The clocks of the character's casts' starts (the take's `cast` events), in order."""
    return sorted(event['t'] for event in take.events if event['event'] == 'cast')


def _delayed(at: float, casts: Sequence[float]) -> bool:
    """Whether `at` is within DELAY of a cast's start."""
    last = bisect.bisect_right(casts, at) - 1
    return last >= 0 and at - casts[last] < DELAY


def _idle(before: dict, after: dict, sent: Sequence[float]) -> bool:
    """Whether the span from `before` to `after` did nothing: still, neither casting nor moving, no input sent. A
    frame whose view byte is 0 is the game's loading screen (macros/routines.py `enter_game`), not idle."""
    if before['p'][1] in CASTING or before['p'][1] in MOVING or before.get('view') == 0:
        return False
    if math.dist((before['p'][3], before['p'][4]), (after['p'][3], after['p'][4])) >= STILL:
        return False
    first = bisect.bisect_left(sent, before['t'] - QUIET)
    return first >= len(sent) or sent[first] > after['t']


def _leg(
    take: Take,
    frames: Sequence[dict],
    to: int | None,
    place: tuple[float, float] | None,
    sent: Sequence[float] = (),
    casts: Sequence[float] = (),
) -> Leg:
    start = frames[0]['p']
    line = math.dist((start[3], start[4]), place) if place is not None else 0.0
    way = casting = moving = standing = idle = delay = away = 0.0
    stalls, still_from = [], None

    def close_stall(until: float) -> None:
        if still_from is not None and until - still_from >= STALL_SECONDS:
            stalls.append(Stall(still_from, until - still_from, _reasons(take, still_from, until)))

    for before, after in itertools.pairwise(frames):
        span, mode = after['t'] - before['t'], before['p'][1]
        way += math.dist((before['p'][3], before['p'][4]), (after['p'][3], after['p'][4]))
        if place is not None:
            away += max(
                0.0,
                math.dist((after['p'][3], after['p'][4]), place) - math.dist((before['p'][3], before['p'][4]), place),
            )
        if _idle(before, after, sent):
            if _delayed(before['t'], casts):
                delay += span
            else:
                idle += span
        if mode in CASTING:
            casting += span
        elif mode in MOVING:
            moving += span
        else:
            standing += span
            if still_from is None:
                still_from = before['t']
            continue
        close_stall(before['t'])
        still_from = None
    close_stall(frames[-1]['t'])
    return Leg(
        take.directory.name,
        frames[0]['t'],
        frames[-1]['t'],
        to,
        line,
        way,
        casting,
        moving,
        standing,
        tuple(stalls),
        idle,
        delay,
        away,
    )


@dataclass(frozen=True)
class Quiet:
    """A whole take's inactive time (`quiet`): the seconds in its area, the idle seconds, and the stretches idle
    STALL_SECONDS and more with the log lines said in them."""

    take: str
    area: int | None
    seconds: float
    idle: float
    stretches: tuple[Stall, ...] = ()
    delay: float = 0.0


def quiet(take: Take) -> Quiet | None:
    """The take's inactive time in its area (a town's take as well as a level's), from the first frame there to the
    last; None with under two frames."""
    area = take.manifest.get('area')
    frames = [frame for frame in take.frames if frame.get('p') and (area is None or frame['p'][2] == area)]
    if len(frames) < 2:
        return None
    sent, casts, idle, delay, stretches, from_ = sent_times(take), cast_times(take), 0.0, 0.0, [], None

    def close(until: float) -> None:
        if from_ is not None and until - from_ >= STALL_SECONDS:
            stretches.append(Stall(from_, until - from_, _reasons(take, from_, until)))

    for before, after in itertools.pairwise(frames):
        if _idle(before, after, sent):
            if _delayed(before['t'], casts):
                delay += after['t'] - before['t']
            else:
                idle += after['t'] - before['t']
                from_ = before['t'] if from_ is None else from_
                continue
        close(before['t'])
        from_ = None
    close(frames[-1]['t'])
    return Quiet(take.directory.name, area, frames[-1]['t'] - frames[0]['t'], idle, tuple(stretches), delay)


def playable(take: Take, first: float) -> float:
    """When the game took input after the arrival (the log's `took input`), else the take's first frame."""
    said = next((e['t'] for e in take.events if e['event'] == 'log' and 'took input' in e.get('text', '')), None)
    return said if said is not None and said >= first else first


def legs_of(take: Take) -> list[Leg]:
    """The take's legs (the module text): from the first frame the character stands in the level to each container
    opened, then the tail to the take's end."""
    frames = [frame for frame in take.frames if frame.get('p')]
    if len(frames) < 2:
        return []
    area = take.manifest.get('area')
    frames = [frame for frame in frames if area is None or frame['p'][2] == area]
    found, begin, sent, casts = (
        [],
        playable(take, frames[0]['t'] if frames else 0.0),
        sent_times(take),
        cast_times(take),
    )
    for at, place, txt in opened(take):
        span = [frame for frame in frames if begin <= frame['t'] <= at]
        if len(span) >= 2:
            found.append(_leg(take, span, txt, place, sent, casts))
        begin = at
    tail = [frame for frame in frames if frame['t'] >= begin]
    if len(tail) >= 2:
        found.append(_leg(take, tail, None, None, sent, casts))
    return found


def clock_of(take: Take, at: float) -> str:
    """The local clock of the take's time `at` (the log's), from the manifest's start."""
    started = take.manifest.get('started_at')
    if not started or not take.frames:
        return f'{at:.1f}'
    when = datetime.datetime.fromisoformat(started).astimezone() + datetime.timedelta(seconds=at - take.frames[0]['t'])
    return when.strftime('%H:%M:%S')


def report(takes: Iterable[Take], worst: int = 12) -> list[str]:
    """The lines said: each take's time and containers, the totals, and the `worst` legs by seconds lost."""
    lines, every, by_take = [], [], {}
    for take in takes:
        found = legs_of(take)
        by_take[take.directory.name] = take
        every += found
        seconds = take.seconds
        chests = sum(leg.to in CHESTS for leg in found)
        others = sum(leg.to is not None and leg.to not in CHESTS for leg in found)
        lost = sum(leg.lost for leg in found if leg.to is not None)
        arrival = found[0].begin - take.frames[0]['t'] if found else 0.0
        code = str((take.manifest.get('code') or {}).get('commit', ''))[:7]
        lines.append(
            f'{take.directory.name} {code} {clock_of(take, take.frames[0]["t"])} {seconds:5.1f}s on the level '
            f'(arrival {arrival:3.1f}s), {chests} chests and {others} others opened, stalls '
            f"{stalled(found, mine=False):4.1f}s (the player's {stalled(found, mine=True):4.1f}s), lost {lost:4.1f}s"
        )
    legs = [leg for leg in every if leg.to is not None]
    if not legs:
        return [*lines, 'no container opened']
    seconds = sum(leg.seconds for leg in every)
    chests = sum(leg.to in CHESTS for leg in legs)
    split = {name: sum(getattr(leg, name) for leg in every) for name in ('casting', 'moving', 'standing')}
    lines += [
        f'{len(by_take)} stays, {seconds:.0f}s on the level: {chests} chests, {60 * chests / seconds:.1f} a minute; '
        + ', '.join(f'{name} {value:.0f}s' for name, value in split.items()),
        f'{len(legs)} legs to a container: speed median {statistics.median(leg.speed for leg in legs):.1f} u/s '
        f"(Blade Warp's pace {REFERENCE:g}), detour median {statistics.median(leg.detour for leg in legs):.2f}, "
        f'lost {sum(leg.lost for leg in legs):.0f}s, in stalls {stalled(legs, mine=False):.0f}s '
        f"and the player's {stalled(legs, mine=True):.0f}s",
        f'after the last container: {sum(leg.seconds for leg in every if leg.to is None):.0f}s in all',
        f'the {worst} legs that lost most:',
    ]
    for leg in sorted(legs, key=lambda leg: leg.lost, reverse=True)[:worst]:
        take = by_take[leg.take]
        lines.append(
            f'  {leg.take} {clock_of(take, leg.begin)} to {leg.to}: line {leg.line:5.1f} way {leg.way:6.1f} '
            f'{leg.seconds:5.1f}s (casting {leg.casting:4.1f}, moving {leg.moving:4.1f}, standing {leg.standing:4.1f}) '
            f'lost {leg.lost:4.1f}s'
        )
        for stall in leg.stalls:
            whose = ' (the player)' if stall.mine else ''
            said = ' | '.join(stall.reasons)
            lines.append(f'      stall {clock_of(take, stall.at)} {stall.seconds:4.1f}s{whose}: {said}')
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('takes', nargs='+', type=Path, help='take directories (runs/combat/<stamp>-<area>)')
    parser.add_argument('--worst', type=int, default=12, help='the legs listed, the most seconds lost first')
    args = parser.parse_args(argv)
    for line in report((Take.load(path) for path in args.takes), args.worst):
        print(line)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
