"""Player-first healing orchestration and latest delivery events."""

from .models import Actor


class Automation:
    def __init__(self, controllers):
        self.controllers = sorted(controllers, key=lambda controller: controller.config.actor != Actor.PLAYER)
        self._events = {}

    @property
    def events(self):
        return tuple(self._events[actor] for actor in Actor if actor in self._events)

    def step(self, state):
        results = {}
        for controller in self.controllers:
            actor = controller.config.actor
            result = controller.step(state)
            results[actor] = result
            if result.event:
                self._events[actor] = result.event
        return results
