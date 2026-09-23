"""Shared widget storage for the latest immutable sample."""

from collections.abc import Sequence

from inventory_tracking.models import State


class SampleWidget[C]:
    """A widget owns its typed config; display freshness is a window property handed in by the factory."""

    def __init__(self, config: C, *, max_age: float) -> None:
        self.config = config
        self.max_age = max_age
        self.reset()

    def reset(self) -> None:
        self.state = State(sampled_at=0, reason='not sampled')

    def update(self, snapshot: State) -> None:
        self.state = snapshot

    def fresh(self, now: float) -> bool:
        return self.state.fresh(now, self.max_age)

    def render(self, *, now: float) -> Sequence[str]:
        raise NotImplementedError
