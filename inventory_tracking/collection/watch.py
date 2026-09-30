"""Automatic Win+S: collect once every time the stash panel is closed.

The watcher polls the open-panel flags (tracking/panels.py) from the service loop.
A collection is requested on the open → closed edge of the stash flag only, so one
visit to the stash yields one capture; an unreadable observation forgets the open
state so a game restart or reattach cannot fire a stale edge.
"""

import time
from collections.abc import Callable

from inventory_tracking.common import LOG
from inventory_tracking.models import Observation, ObservationStatus


class StashWatcher:
    def __init__(
        self,
        observe: Callable[[], Observation[dict[str, bool]]],
        collect: Callable[[float], bool],
        *,
        poll_interval: float = 0.5,
        clock=time.monotonic,
    ):
        self.observe, self.collect, self.poll_interval, self.clock = observe, collect, poll_interval, clock
        self.last_poll = -float('inf')
        self.stash_open: bool | None = None  # None until the flags were read once
        self.collections = 0

    def poll(self, now: float | None = None) -> bool:
        """Read the flags when due; returns whether a collection was requested."""
        now = self.clock() if now is None else now
        if now - self.last_poll < self.poll_interval:
            return False
        self.last_poll = now
        observation = self.observe()
        if observation.status != ObservationStatus.AVAILABLE or observation.value is None:
            if self.stash_open is not None:
                LOG.debug('Panel flags unavailable: %s', observation.reason)
            self.stash_open = None
            return False
        was_open, self.stash_open = self.stash_open, observation.value['stash']
        if was_open is not True or self.stash_open:
            return False
        LOG.info('Stash closed; collecting')
        accepted = self.collect(now)
        if accepted:
            self.collections += 1
        return accepted
