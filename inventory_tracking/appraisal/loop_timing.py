"""Per-step timing of one service-loop pass, logged only when the pass was slow.

Every HUD layer the loop publishes expires after hud.scene.LEASE_SECONDS, so a slow pass
shows up in game as a flickering or frozen map; this names the step that took the time.
"""

import time
from contextlib import contextmanager

from inventory_tracking.common import LOG


class PassTimer:
    def __init__(self, threshold: float, *, clock=time.monotonic):
        self.threshold, self.clock = threshold, clock
        self.steps: dict[str, float] = {}

    @contextmanager
    def step(self, name: str):
        started = self.clock()
        try:
            yield
        finally:
            self.steps[name] = self.steps.get(name, 0.0) + self.clock() - started

    def finish(self) -> float:
        """Log the pass if its timed steps (the hotkey wait is not one) exceeded the threshold."""
        steps, self.steps = self.steps, {}
        total = sum(steps.values())
        if total >= self.threshold:
            ranked = sorted(steps.items(), key=lambda item: item[1], reverse=True)
            LOG.warning(
                'Slow service pass: %.0f ms (%s)',
                total * 1000,
                ', '.join(f'{name} {seconds * 1000:.0f}' for name, seconds in ranked if seconds >= 0.001),
            )
        return total
