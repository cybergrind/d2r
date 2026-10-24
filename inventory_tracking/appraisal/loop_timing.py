"""Per-step timing of one service-loop pass, logged only when the pass was slow.

Every HUD layer the loop publishes expires after hud.scene.LEASE_SECONDS, so a slow pass
shows up in game as a flickering or frozen map; this names the step that took the time.
"""

import time
from contextlib import contextmanager

from inventory_tracking.common import LOG


# 2026-10-24 (realtime-4): each step's CPU time on the main thread too (`passed(..., cpu=)`, load.py `pass_cpu_ms`).
# A step's wall time counts its waits for the GIL and the game; its thread CPU is what it held the GIL for, the share
# that moving it off the service's GIL would free. False: wall time only, as before. On 2026-10-24 ~12:30.
STEP_CPU = True


class PassTimer:
    def __init__(self, threshold: float, *, clock=time.monotonic, passed=None, cpu_clock=time.thread_time):
        """`passed(steps, total)`: told every pass's step times in seconds (appraisal/load.py `LoadMeter`); with
        STEP_CPU also `cpu=` {step: the main thread's CPU seconds}."""
        self.threshold, self.clock, self.passed, self.cpu_clock = threshold, clock, passed, cpu_clock
        self.steps: dict[str, float] = {}
        self.cpu_steps: dict[str, float] = {}
        self.current: tuple[str | None, float] = (None, 0.0)  # the step under way and when it began

    @contextmanager
    def step(self, name: str):
        started = self.clock()
        cpu_started = self.cpu_clock() if STEP_CPU else 0.0
        self.current = (name, started)
        try:
            yield
        finally:
            self.current = (None, started)
            self.steps[name] = self.steps.get(name, 0.0) + self.clock() - started
            if STEP_CPU:
                self.cpu_steps[name] = self.cpu_steps.get(name, 0.0) + self.cpu_clock() - cpu_started

    def finish(self) -> float:
        """Log the pass if its timed steps (the hotkey wait is not one) exceeded the threshold."""
        steps, self.steps = self.steps, {}
        cpu, self.cpu_steps = self.cpu_steps, {}
        total = sum(steps.values())
        if self.passed is not None:
            if STEP_CPU:
                self.passed(steps, total, cpu=cpu)
            else:
                self.passed(steps, total)
        if total >= self.threshold:
            ranked = sorted(steps.items(), key=lambda item: item[1], reverse=True)
            LOG.warning(
                'Slow service pass: %.0f ms (%s)',
                total * 1000,
                ', '.join(f'{name} {seconds * 1000:.0f}' for name, seconds in ranked if seconds >= 0.001),
            )
        return total
