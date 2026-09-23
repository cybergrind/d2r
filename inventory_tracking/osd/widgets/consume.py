"""Best-effort cast-level timer, with a bounded notice on observed removal."""

import math

from ...config import ConsumeWidgetConfig
from ...models import ConsumeBuff
from .base import SampleWidget


class ConsumeWidget(SampleWidget[ConsumeWidgetConfig]):
    def reset(self):
        super().reset()
        self.previous: ConsumeBuff | None = None
        self.last_seen: float | None = None
        self.deadline: float | None = None
        self.notice_until: float | None = None
        self.continuous = False

    def update(self, snapshot):
        super().update(snapshot)
        if snapshot.health is not None and snapshot.health.current_raw <= 0:
            self.reset()
            return
        observation = snapshot.consume
        now = observation.sampled_at
        # Optional reads follow the core sample. Evaluate both at the later time.
        if (
            snapshot.session is None
            or not snapshot.fresh(now, self.max_age)
            or not observation.fresh(now, self.max_age)
            or observation.value is None
        ):
            self.continuous = False
            self.deadline = None
            return
        if self.last_seen is not None and now <= self.last_seen:
            return
        current = observation.value
        adjacent = self.continuous and self.last_seen is not None and now - self.last_seen <= self.max_age
        if not adjacent:
            self.deadline = None
        if current.active:
            self.notice_until = None
            if adjacent and self.previous is not None and not self.previous.active:
                level = current.level
                if type(level) is int and 1 <= level <= 255:
                    # Consume ln12: 1000 + 500*(level-1) frames at 25 Hz.
                    self.deadline = now + 40 + 20 * (level - 1)
            elif self.previous != current:
                # Replacement/level change may be a refresh, not proof of a cast.
                self.deadline = None
        else:
            if self.previous is not None and self.previous.active:
                self.notice_until = now + self.config.ended_notice_seconds
            self.deadline = None
        self.previous = current
        self.last_seen = now
        self.continuous = True

    def render(self, *, now):
        if not self.config.enabled or not self.fresh(now) or not self.state.consume.fresh(now, self.max_age):
            return ()
        current = self.state.consume.value
        if current is None:
            return ()
        if not current.active and self.notice_until is not None and now < self.notice_until:
            return ('consume: no longer active',)
        if current.active and self.deadline is not None:
            remaining = self.deadline - now
            if remaining <= 0:
                return ('consume: recast (estimated timer elapsed)',)
            if remaining <= self.config.warn_before_seconds:
                return (f'consume: ~{math.ceil(remaining)}s left',)
        return ()
