"""The service's own load, measured once a second into the combat take (rca/2026-10-13/latency-findings.md, fix 1).

The 21:42 game of 2026-10-13 could not tell host load from the GIL convoy: the slow passes were logged in wall
time only and the host's load average only at KP_4 presses. Now, once a second while the character is out of town
(appraisal/cadence.py modes level and working), the service loop notes a `load` event (takes/record.py
`Recorder.note`, schema 4, additive):

- `s`: the window's seconds; `mode`: the service cadence's mode then (appraisal/cadence.py: town, level, working);
- `cpu`: the service process's CPU over the window, % of one core (all its threads); `main`: the main loop's own;
- `load`: the host's 1-minute load average; `ctx`: the process's involuntary context switches in the window
  (the host took a CPU away from one of its threads);
- `passes`: the main loop's passes; `pass_ms`: {step: ms} summed over them (loop_timing.py's steps); `pass_max`:
  the longest pass, ms;
- `looks`: the macro's looks at the game (macros/runner.py `looked`); `look_ms`: [median, max] ms, None without one.

The check for the next game (takes under inventory_tracking/runs/combat):

    uv run --offline python -m inventory_tracking.appraisal.load inventory_tracking/runs/combat/<take>...

prints a line per take: windows, look median/p90/max, the main loop's busiest share, CPU and load, and the windows
starved (a look over STARVED_LOOK_MS or a pass over STARVED_PASS_MS).
"""

import argparse
import os
import resource
import statistics
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


EVERY = 1.0  # seconds a window spans
STARVED_LOOK_MS = 100.0  # a full look is 4-10 ms in a game (latency-findings 2.3): 100 is a convoy or a starved CPU
STARVED_PASS_MS = 500.0  # loop_timing.py's slow pass (APPRAISAL.slow_loop_seconds)


def involuntary_switches() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_nivcsw


class LoadMeter:
    """Gathers a window's numbers (`passed` from the main loop's PassTimer, `looked` from the macro's thread) and
    hands them to `note` once a window while `noting()` holds. `poll` is called from the main loop's thread: its
    thread CPU is the main loop's."""

    def __init__(
        self,
        note: Callable[..., None],
        *,
        every: float = EVERY,
        clock: Callable[[], float] = time.monotonic,
        cpu: Callable[[], float] = time.process_time,
        thread_cpu: Callable[[], float] = time.thread_time,
        loadavg: Callable[[], tuple[float, float, float]] = os.getloadavg,
        switches: Callable[[], int] = involuntary_switches,
    ) -> None:
        self.note, self.every = note, every
        self.clock, self.cpu, self.thread_cpu, self.loadavg, self.switches = clock, cpu, thread_cpu, loadavg, switches
        self.lock = threading.Lock()
        self.looks: list[float] = []
        self.started: tuple[float, float, float, int] | None = None  # clock, process CPU, thread CPU, switches
        self.steps: dict[str, float] = {}
        self.passes = 0
        self.pass_max = 0.0

    def looked(self, seconds: float) -> None:
        """A look of the macro's at the game (any thread)."""
        with self.lock:
            self.looks.append(seconds)

    def passed(self, steps: dict[str, float], total: float) -> None:
        """One pass of the main loop (loop_timing.PassTimer `passed`)."""
        for name, seconds in steps.items():
            self.steps[name] = self.steps.get(name, 0.0) + seconds
        self.passes += 1
        self.pass_max = max(self.pass_max, total)

    def poll(self, now: float, mode: str, noting: bool) -> dict[str, Any] | None:
        """Close the window when it is due: its event, noted when `noting` (out of town)."""
        if self.started is None:
            self._restart(now)
            return None
        began, cpu, thread_cpu, switches = self.started
        span = now - began
        if span < self.every:
            return None
        with self.lock:
            looks, self.looks = self.looks, []
        fields: dict[str, Any] = {
            's': round(span, 3),
            'mode': mode,
            'cpu': round(100 * (self.cpu() - cpu) / span, 1),
            'main': round(100 * (self.thread_cpu() - thread_cpu) / span, 1),
            'load': round(self.loadavg()[0], 2),
            'ctx': self.switches() - switches,
            'passes': self.passes,
            'pass_ms': {name: round(1000 * seconds, 1) for name, seconds in self.steps.items() if seconds >= 0.0005},
            'pass_max': round(1000 * self.pass_max, 1),
            'looks': len(looks),
            'look_ms': [round(1000 * statistics.median(looks), 1), round(1000 * max(looks), 1)] if looks else None,
        }
        self._restart(now)
        if not noting:
            return None
        self.note('load', **fields)
        return fields

    def _restart(self, now: float) -> None:
        self.started = (now, self.cpu(), self.thread_cpu(), self.switches())
        self.steps, self.passes, self.pass_max = {}, 0, 0.0


def percentile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))]


def summary(directory: Path) -> str:
    """One line on a take's `load` events."""
    from inventory_tracking.takes.takes import lines

    windows = [event for event in lines(directory / 'events.jsonl') if event.get('event') == 'load']
    if not windows:
        return f'{directory.name}: no load events (a take before 2026-10-13 night, or no level)'
    looks = [w['look_ms'] for w in windows if w.get('look_ms')]
    medians, maxima = [look[0] for look in looks], [look[1] for look in looks]
    starved = [
        w
        for w in windows
        if (w.get('look_ms') and w['look_ms'][1] > STARVED_LOOK_MS) or w.get('pass_max', 0) > STARVED_PASS_MS
    ]
    steps: dict[str, float] = {}
    for w in windows:
        for name, ms in (w.get('pass_ms') or {}).items():
            steps[name] = steps.get(name, 0.0) + ms
    span = sum(w['s'] for w in windows) * 1000
    busiest = ', '.join(f'{name} {100 * ms / span:.1f}%' for name, ms in sorted(steps.items(), key=lambda i: -i[1])[:3])
    look = (
        f'look median {statistics.median(medians):.1f} ms, p90 of maxima {percentile(maxima, 0.9):.0f}, '
        f'max {max(maxima):.0f}'
        if looks
        else 'no macro looks'
    )
    cpu = [w['cpu'] for w in windows]
    return (
        f'{directory.name}: {len(windows)} s; {look}; main loop {busiest or "idle"}; '
        f'cpu p90 {percentile(cpu, 0.9):.0f}%, load max {max(w["load"] for w in windows):.1f}; '
        f'starved {len(starved)} of {len(windows)} s'
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='One line per combat take on the service load it recorded.')
    parser.add_argument('takes', nargs='+', type=Path)
    for directory in parser.parse_args(argv).takes:
        print(summary(directory))
    return 0


if __name__ == '__main__':
    sys.exit(main())
