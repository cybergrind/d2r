"""Player-first healing orchestration and latest delivery events."""

from .common import LOG
from .models import Actor, PotionResult, PotionSent, State


class Automation:
    def __init__(self, controllers) -> None:
        self.controllers = sorted(controllers, key=lambda controller: controller.config.actor != Actor.PLAYER)
        self._events: dict[Actor, PotionSent] = {}
        self._core: tuple[int, str, int] | None = None

    @property
    def events(self) -> tuple[PotionSent, ...]:
        return tuple(self._events[actor] for actor in Actor if actor in self._events)

    def step(self, state: State) -> dict[Actor, PotionResult]:
        # Only a verified new game drops old deliveries; incomplete reads keep them visible.
        if state.session is not None and state.session.core != self._core:
            if self._core is not None:
                LOG.info('Game session changed; clearing delivery events')
            self._events.clear()
            self._core = state.session.core
        results = {}
        for controller in self.controllers:
            actor = controller.config.actor
            result = controller.step(state)
            results[actor] = result
            if result.event:
                self._events[actor] = result.event
        return results
