"""Player-first healing orchestration, latest delivery events and outcome transitions."""

from collections.abc import Mapping

from inventory_tracking.common import LOG
from inventory_tracking.models import Actor, Outcome, PotionResult, PotionSent, State


# Outcomes worth a log line and an OSD status; the actor is not healing although it may be needed.
NOTABLE = frozenset({Outcome.REJECTED, Outcome.BACKOFF, Outcome.SUSPENDED, Outcome.NO_STOCK})
# Outcomes proving the actor is healing normally again; the rest (cooldown after a rejected attempt,
# unavailable, stale belt, busy, disabled) say nothing either way and keep the last notable status.
RESOLVING = frozenset({Outcome.IDLE, Outcome.SENT, Outcome.PENDING})


def describe(result: PotionResult) -> str:
    return f'{result.outcome} ({result.reason})' if result.reason is not None else str(result.outcome)


class Automation:
    def __init__(self, controllers) -> None:
        self.controllers = sorted(controllers, key=lambda controller: controller.config.actor != Actor.PLAYER)
        self._events: dict[Actor, PotionSent] = {}
        self._results: dict[Actor, PotionResult] = {}
        self._notable: dict[Actor, tuple[Outcome, object]] = {}
        self._core: tuple[int, str, int] | None = None

    @property
    def events(self) -> tuple[PotionSent, ...]:
        return tuple(self._events[actor] for actor in Actor if actor in self._events)

    @property
    def outcomes(self) -> Mapping[Actor, PotionResult]:
        return dict(self._results)

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
            self._results[actor] = result
            self._log_transition(actor, result)
            if result.event:
                self._events[actor] = result.event
        return results

    def _log_transition(self, actor: Actor, result: PotionResult) -> None:
        """One line when an actor stops healing normally and one when it is back; quiet ticks never log."""
        if result.outcome in NOTABLE:
            status = (result.outcome, result.reason)
            if self._notable.get(actor) != status:
                self._notable[actor] = status
                LOG.info('%s healing: %s', actor, describe(result))
        elif result.outcome in RESOLVING and actor in self._notable:
            del self._notable[actor]
            LOG.info('%s healing: %s', actor, describe(result))
