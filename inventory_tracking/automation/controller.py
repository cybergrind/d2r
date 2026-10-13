"""Healing orchestration (whom first: automation/priority.py), latest delivery events and outcome transitions."""

from collections.abc import Mapping

from inventory_tracking.automation.priority import PlayerWatch, StockWatch, Verdict
from inventory_tracking.common import LOG
from inventory_tracking.config import HEAL_PRIORITY, HealPriorityConfig
from inventory_tracking.models import Actor, Outcome, PotionResult, PotionSent, State


# Outcomes worth a log line and an OSD status; the actor is not healing although it may be needed.
NOTABLE = frozenset({Outcome.REJECTED, Outcome.BACKOFF, Outcome.SUSPENDED, Outcome.NO_STOCK, Outcome.HELD})
# Outcomes proving the actor is healing normally again; the rest (cooldown after a rejected attempt,
# unavailable, stale belt, busy, disabled) say nothing either way and keep the last notable status.
RESOLVING = frozenset({Outcome.IDLE, Outcome.SENT, Outcome.PENDING})


def describe(result: PotionResult) -> str:
    return f'{result.outcome} ({result.reason})' if result.reason is not None else str(result.outcome)


class Automation:
    def __init__(self, controllers, extras=(), priority: HealPriorityConfig = HEAL_PRIORITY) -> None:
        self.controllers = list(controllers)
        self.extras = list(extras)  # steps after healing (Show Items); a failure there never stops healing
        # The character's situation at each sample (None with the priority off: the character first, always).
        self.watch = PlayerWatch(priority) if priority.enabled else None
        self.stock = StockWatch(priority)
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
        verdict = self.watch.look(state) if self.watch is not None else None
        change = self.stock.look(state)
        if change is not None:
            (LOG.warning if change.fell else LOG.info)('%s', change.line)
        results = {}
        for controller in self.ordered(verdict):
            actor = controller.config.actor
            result = controller.step(state, verdict)
            results[actor] = result
            self._results[actor] = result
            self._log_transition(actor, result, verdict)
            if result.event:
                self._events[actor] = result.event
                self.stock.sent(result.event)
        for extra in self.extras:
            try:
                extra.step(state)
            except Exception:
                LOG.exception('%s failed', type(extra).__name__)
        return results

    def ordered(self, verdict: Verdict | None) -> list:
        """The mercenary first (the player's ruling, 2026-10-13), the character first when he is critical or his
        situation is unread."""
        player_first = verdict is None or verdict.critical
        return sorted(self.controllers, key=lambda each: (each.config.actor == Actor.PLAYER) != player_first)

    def _log_transition(self, actor: Actor, result: PotionResult, verdict: Verdict | None = None) -> None:
        """One line when an actor stops healing normally and one when it is back; quiet ticks never log."""
        if result.outcome in NOTABLE:
            status = (result.outcome, result.reason)
            if self._notable.get(actor) != status:
                self._notable[actor] = status
                detail = f': {verdict}' if result.outcome == Outcome.HELD and verdict is not None else ''
                LOG.info('%s healing: %s%s', actor, describe(result), detail)
        elif result.outcome in RESOLVING and actor in self._notable:
            del self._notable[actor]
            LOG.info('%s healing: %s', actor, describe(result))
