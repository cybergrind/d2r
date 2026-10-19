"""Requests waiting for the current run to end: one per routine, taken by priority, each with an expiry.

A teleport step two seconds after its key is a surprise, not a step (user, 2026-10-12): an expired request is dropped
and logged (also in its press's trace).
"""

import math
import time
from collections.abc import Callable

from inventory_tracking.common import LOG
from inventory_tracking.macros.latency import Press, Trace


class Waiting:
    def __init__(self, priority: tuple[str, ...], trace: Trace, clock: Callable[[], float] = time.monotonic) -> None:
        self.priority, self.trace, self.clock = priority, trace, clock
        self.entries: dict[str, tuple[float, Press | None]] = {}  # routine -> (good until, its press)

    def put(self, routine: str, until: float = math.inf, press: Press | None = None) -> None:
        """`routine` waits, good until `until` on the clock; a request of it that waited already gives way."""
        self.drop(routine, 'another press took its place')
        self.entries[routine] = (until, press)

    def drop(self, routine: str, why: str) -> None:
        found = self.entries.pop(routine, None)
        if found is not None:
            self.trace.close(found[1], ended=why)

    def clear(self, why: str) -> None:
        for routine in list(self.entries):
            self.drop(routine, why)

    def first(self) -> str | None:
        """The routine to run next, by priority; those that waited too long are dropped on the way."""
        now = self.clock()
        for routine in sorted(self.entries, key=self._rank):
            until = self.entries[routine][0]
            if now <= until:
                return routine
            LOG.warning('Macro: %s dropped: it waited %.0f ms too long', routine, 1000 * (now - until))
            self.drop(routine, 'expired')
        return None

    def take(self, routine: str) -> tuple[float, Press | None]:
        """`routine` begins: (good until, its press), no longer waiting."""
        return self.entries.pop(routine, (math.inf, None))

    def _rank(self, routine: str) -> int:
        return self.priority.index(routine) if routine in self.priority else len(self.priority)
