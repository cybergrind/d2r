"""Human-like pauses and key holds: short, never the same twice, skewed towards the quick end.

One seeded generator and an injected `sleep`, so tests are exact and take no time.
"""

import random
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager


# Seconds (shortest, longest) by what was just done.
PAUSES = {
    'key': (0.09, 0.26),  # between two skill keys, on top of waiting for the cast itself
    'type': (0.06, 0.17),  # between typed characters
    'aim': (0.1, 0.24),  # pointer arrived, before the key or click
    'flick': (0.03, 0.09),  # the same for a quick move (the teleport step, pressed again and again)
    'screen': (0.35, 0.75),  # a menu or screen has just appeared
}
HOLD = (0.045, 0.11)
POINTER_STEP = (0.007, 0.018)


class Pace:
    def __init__(self, rng: random.Random | None = None, sleep: Callable[[float], None] = time.sleep) -> None:
        self.rng = rng or random.Random()
        self.plain_sleep = sleep
        self.look: Callable[[], object] | None = None  # called before and every `every` seconds of a sleep
        self.every = 0.0
        self.clock: Callable[[], float] = time.monotonic

    def sleep(self, seconds: float) -> None:
        """Sleep `seconds`; while `watched`, in slices with a look before each and one at the end."""
        if self.look is None:
            self.plain_sleep(seconds)
            return
        until = self.clock() + seconds
        while True:
            self.look()
            left = until - self.clock()
            if left <= 0:
                return
            self.plain_sleep(min(self.every, left))

    @contextmanager
    def watched(self, look: Callable[[], object], every: float, clock: Callable[[], float]) -> Iterator[None]:
        """Within the block every pause made through this pace, whoever makes it (a routine's own
        waits, a key hold, a pointer step), calls `look` every `every` seconds: attack mode looks at
        the player's mouse button there, so no click goes unseen while the macro waits on something."""
        before = (self.look, self.every, self.clock)
        self.look, self.every, self.clock = look, every, clock
        try:
            yield
        finally:
            self.look, self.every, self.clock = before

    def between(self, low: float, high: float) -> float:
        """A duration in [low, high], most often in its lower half."""
        return low + (high - low) * self.rng.betavariate(2, 4)

    def pause(self, kind: str) -> None:
        self.sleep(self.between(*PAUSES[kind]))

    def hold(self) -> None:
        self.sleep(self.between(*HOLD))

    def pointer_step(self) -> None:
        self.sleep(self.between(*POINTER_STEP))
