"""One macro run: read the world, act, and go on only when the game shows the result.

A routine is a plain function of a `Run`. It acts through `run.actuator` and moves forward with
`run.expect(...)`, which polls memory until a predicate holds or raises `Abort`. Pauses pace
the input; they never stand in for evidence. A second hotkey press sets `cancelled`.
"""

import time
from collections.abc import Callable
from threading import Event

from inventory_tracking.macros.actuator import Abort, Actuator
from inventory_tracking.macros.timing import Pace
from inventory_tracking.macros.world import World


POLL = 0.03


class Run:
    def __init__(
        self,
        read: Callable[[], World],
        actuator: Actuator,
        pace: Pace,
        *,
        clock: Callable[[], float] = time.monotonic,
        cancelled: Event | None = None,
        say: Callable[[str], None] = lambda text: None,
    ) -> None:
        self.read = read
        self.actuator = actuator
        self.pace = pace
        self.clock = clock
        self.cancelled = cancelled or Event()
        self.say = say
        self.keys: dict[int, str] = {}
        self.observe: Callable[[World], None] | None = None  # sees every world read

    def world(self) -> World:
        if self.cancelled.is_set():
            raise Abort('cancelled')
        try:
            world = self.read()
        except (OSError, ValueError) as exc:
            raise Abort(f'the game could not be read ({exc})') from exc
        if self.observe is not None:
            self.observe(world)
        return world

    def expect(self, what: str, predicate: Callable[[World], bool], timeout: float) -> World:
        """The first world in which `predicate` holds; `Abort` when none comes in `timeout` seconds."""
        deadline = self.clock() + timeout
        while True:
            world = self.world()
            if predicate(world):
                return world
            if self.clock() >= deadline:
                raise Abort(f'{what}: not seen in {timeout:g}s')
            self.pace.sleep(POLL)

    def seen(self, predicate: Callable[[World], bool], timeout: float) -> World | None:
        """As `expect`, for evidence that is welcome but not required."""
        try:
            return self.expect('', predicate, timeout)
        except Abort:
            if self.cancelled.is_set():
                raise
            return None

    def pause(self, kind: str) -> None:
        if self.cancelled.is_set():
            raise Abort('cancelled')
        self.pace.pause(kind)
