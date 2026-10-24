"""The act queue measured in the run (2026-10-23, rca/2026-10-23/realtime-2-findings.md): what runs between a pursuit's
look and its act's first input, and the staff read once a judge.

`LapBook` keeps one pursue's laps (`begin` at its look, `lap` at each part's end, the reads it made through the run's
readers timed by `reads`) and, at the next `begin`, closes it with the actuator's own input times (`Actuator.sent`):
an act over ACT_LAPS_OVER is said with its parts, and every ACT_LAPS_EVERY seconds the parts' p50/p90 over the acts
since. Measurement only (base.py ACT_LAPS).

`staff_once` (base.py STAFF_ONCE): within the block the run's staff reader reads the game once and gives that answer
again; a judge makes no act, so the staff cannot change in it. `loot_once` (base.py LOOT_ONCE, 2026-10-23): the
same for the loot read (the life, the belt, the drops): one judge's goal and pricing from one read.
"""

import math
import time
from collections import defaultdict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from inventory_tracking.common import LOG
from inventory_tracking.macros.hunting import base


READERS = ('read', 'loot', 'teleport', 'hands', 'flights', 'things', 'own_teleport', 'unit_stats')
KEPT = 4096  # acts kept for the once-a-minute line


@contextmanager
def staff_once(run: Any) -> Iterator[None]:
    """The run's staff (`run.teleport`) read once for the block (STAFF_ONCE); as it was outside it."""
    with read_once(run, 'teleport', base.STAFF_ONCE):
        yield


@contextmanager
def loot_once(run: Any) -> Iterator[None]:
    """The run's loot (`run.loot`: life, mana, belt, drops) read once for the block (LOOT_ONCE): the goal's drops and
    the safety's life of one judge from one read, the nearest to its look; as it was outside it."""
    with read_once(run, 'loot', base.LOOT_ONCE):
        yield


@contextmanager
def read_once(run: Any, name: str, on: bool) -> Iterator[None]:
    """The run's reader `name` read once within the block and its answer given again; a raise is not kept. Off, or no
    such reader: as it is."""
    read = getattr(run, name, None)
    if not on or read is None:
        yield
        return
    held: list = []

    def once():
        if not held:
            held.append(read())
        return held[0]

    setattr(run, name, once)
    try:
        yield
    finally:
        setattr(run, name, read)


@dataclass
class Laps:
    """One pursue: its look's time, each part's end (seconds after the look), the reads by reader (count, seconds)."""

    began: float
    parts: dict[str, float] = field(default_factory=dict)
    reads: dict[str, list[float]] = field(default_factory=lambda: defaultdict(lambda: [0, 0.0]))
    priced: float | None = None  # the safety's pricing (its decision's `ms`), seconds
    by: str = ''  # the act's means (Teleport, Walking, ...)
    phase: str = 'judge'  # whose reads are being timed: the judge's, then 'after'
    restore: Callable[[], object] | None = None  # puts the run's readers back
    # '<phase> <reader>' -> [count, seconds] (2026-10-23: which reads the judge's reads are)
    by_reader: dict[str, list[float]] = field(default_factory=lambda: defaultdict(lambda: [0, 0.0]))
    cpu_began: float | None = None  # the thread's CPU clock at the look (ACT_CPU)
    cpu_judged: float | None = None  # its CPU seconds to the judge's end (ACT_CPU)


class LapBook:
    """The laps of the pursues of one hunter (`begin`, `lap`, `reads`), said as above."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        said: Callable[[str], None] | None = None,
        cpu_clock: Callable[[], float] = time.thread_time,
    ):
        self.clock, self.cpu_clock = clock, cpu_clock
        self.said = said or (lambda text: LOG.info('Macro: %s', text))
        self.current: Laps | None = None
        self.done: list[dict[str, float]] = []
        self.said_at = -math.inf
        self.since = 0  # acts over ACT_LAPS_OVER not said since the last said
        self.every_at: float | None = None

    def begin(self, sent: Callable[[float], tuple[float | None, float | None]] | None) -> None:
        """A pursue's look: the last pursue closed with the inputs `sent(since)` gives (first input, first down)."""
        self.close(sent)
        self.current = Laps(self.clock(), cpu_began=self.cpu_clock() if base.ACT_CPU else None)

    def lap(self, name: str) -> None:
        if self.current is not None and name not in self.current.parts:
            self.current.parts[name] = self.clock() - self.current.began
            if name == 'judge':
                self.current.phase = 'after'
                if self.current.cpu_began is not None:
                    self.current.cpu_judged = self.cpu_clock() - self.current.cpu_began

    def reads(self, run: Any) -> None:
        """The run's readers timed while this pursue is the current one (its laps' reads: the judge's apart); put
        back at its close."""
        current = self.current
        if current is None:
            return
        kept = {name: read for name in READERS if (read := getattr(run, name, None)) is not None}

        def timed(name: str, read: Callable[..., Any]) -> Callable[..., Any]:
            def inner(*args: Any, **kwargs: Any) -> Any:
                if self.current is not current:
                    return read(*args, **kwargs)
                began = self.clock()
                try:
                    return read(*args, **kwargs)
                finally:
                    took = self.clock() - began
                    for tally in (current.reads[current.phase], current.by_reader[f'{current.phase} {name}']):
                        tally[0] += 1
                        tally[1] += took

            return inner

        for name, read in kept.items():
            setattr(run, name, timed(name, read))
        current.restore = lambda: [setattr(run, name, read) for name, read in kept.items()]

    def close(self, sent: Callable[[float], tuple[float | None, float | None]] | None) -> dict[str, float] | None:
        """The current pursue's parts once its act's input is known; None for a pursue that made no move."""
        current, self.current = self.current, None
        if current is not None and current.restore is not None:
            current.restore()
        if current is None or 'make' not in current.parts or sent is None:
            return None
        first, down = sent(current.began + current.parts['make'])
        if first is None:
            return None
        parts = parted(current, first - current.began, None if down is None else down - first)
        self.done.append(parts)
        del self.done[:-KEPT]
        now = self.clock()
        if parts['input'] >= base.ACT_LAPS_OVER:
            if now - self.said_at >= base.ACT_LAPS_SAID:
                more = f' ({self.since} more since)' if self.since else ''
                self.said(f'act queue: {line(parts, current.by)}{more}')
                self.said_at, self.since = now, 0
            else:
                self.since += 1
        if self.every_at is None:
            self.every_at = now
        elif now - self.every_at >= base.ACT_LAPS_EVERY:
            self.every_at = now
            self.said(f'act queue (p50/p90 ms over {len(self.done)} acts): {summary(self.done)}')
            self.done = []
        return parts


def parted(laps: Laps, to_input: float, aim: float | None) -> dict[str, float]:
    """Seconds by part: judge (its pricing and its reads apart), loot, stale, advance, make (to the first input),
    the aim (to the key or button), and the reads of the whole pursue."""
    points = laps.parts
    judged = points.get('judge', 0.0)
    reads_judge = laps.reads.get('judge', [0, 0.0])[1]
    out = {
        'judge': judged,
        'priced': laps.priced or 0.0,
        'judge reads': reads_judge,
        'judge rest': max(0.0, judged - (laps.priced or 0.0) - reads_judge),
        'loot': points.get('loot', judged) - judged,
        'stale': points.get('stale', points.get('loot', judged)) - points.get('loot', judged),
        'advance': points['make'] - points.get('stale', points.get('loot', judged)),
        'make': to_input - points['make'],
        'input': to_input,
        'reads': laps.reads.get('after', [0, 0.0])[1] + laps.reads.get('judge', [0, 0.0])[1],
        'read count': float(laps.reads.get('after', [0, 0.0])[0] + laps.reads.get('judge', [0, 0.0])[0]),
    }
    if aim is not None:
        out['aim'] = aim
    if laps.cpu_judged is not None:
        out['judge cpu'] = laps.cpu_judged
    for key, (count, seconds) in laps.by_reader.items():
        out[f'reads: {key}'] = seconds
        out[f'count: {key}'] = float(count)
    return out


def line(parts: dict[str, float], by: str) -> str:
    ms = {name: 1000 * value for name, value in parts.items()}
    aim = f'; aim to the press {ms["aim"]:.0f}' if 'aim' in ms else ''
    cpu = f'cpu {ms["judge cpu"]:.0f}; ' if 'judge cpu' in ms else ''
    return (
        f'{by or "the act"} {ms["input"]:.0f} ms from the look to its first input: judge {ms["judge"]:.0f} '
        f'({cpu}priced {ms["priced"]:.0f}, reads {ms["judge reads"]:.0f}, the rest {ms["judge rest"]:.0f}), '
        f'loot {ms["loot"]:.0f}, '
        f'stale {ms["stale"]:.0f}, advance {ms["advance"]:.0f}, make {ms["make"]:.0f}{aim}; reads {ms["reads"]:.0f} '
        f'in {parts["read count"]:.0f}'
    )


def summary(done: list[dict[str, float]]) -> str:
    def spread(name: str) -> str:
        values = sorted(row[name] for row in done if name in row)
        if not values:
            return f'{name} -'
        p90 = values[min(len(values) - 1, int(0.9 * (len(values) - 1) + 0.5))]
        return f'{name} {1000 * values[len(values) // 2]:.0f}/{1000 * p90:.0f}'

    names = ('input', 'judge', 'priced', 'judge reads', 'judge rest', 'loot', 'stale', 'advance', 'make', 'aim')
    if any('judge cpu' in row for row in done):
        names = (*names[:2], 'judge cpu', *names[2:])
    line = ', '.join(spread(name) for name in names)
    # Each reader's mean per act (ms, reads), the costliest first: what the reads are
    readers = {key[len('reads: ') :] for row in done for key in row if key.startswith('reads: ')}
    means = sorted(
        (
            (sum(row.get(f'reads: {key}', 0.0) for row in done) / len(done),
             sum(row.get(f'count: {key}', 0.0) for row in done) / len(done), key)
            for key in readers
        ),
        reverse=True,
    )  # fmt: skip
    if means:
        line += '; reads per act (mean ms, count): ' + ', '.join(
            f'{key} {1000 * ms:.1f} ({count:.1f})' for ms, count, key in means[:8]
        )
    return line
