"""Shared widget storage for the latest immutable sample."""

from ...models import State


class SampleWidget:
    def __init__(self, config):
        self.config = config
        self.reset()

    def reset(self):
        self.state = State(0, reason='not sampled')

    def update(self, snapshot):
        self.state = snapshot

    def fresh(self, now):
        return not self.state.reason and 0 <= now - self.state.sampled_at <= self.config.max_age
