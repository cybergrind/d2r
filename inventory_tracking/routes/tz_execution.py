"""Observation-gated area workflow for the dormant TZ coordinator.

This module names operations for a guarded macro executor. It sends no input.
An operation advances only when the executor reports its observed result; an
unread/failed operation leaves the same step pending for an explicit stop/skip.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal

from inventory_tracking.common import LOG
from inventory_tracking.routes.tz_leveling import Capability, Coordinator, TerrorEvidence
from inventory_tracking.terror.monsters import TerrorEntry


Action = Literal[
    'prebuff',
    'restock',
    'travel',
    'hunt',
    'target',
    'loot',
    'complete',
    'area-done',
    'reset',
    'done',
    'wait',
    'pause',
    'stop',
]


@dataclass(frozen=True)
class AreaWork:
    game: str
    area: int
    target: Literal['boss', 'chest', 'object'] | None = None
    prebuffed: bool = False
    restocked: bool = False
    arrived: bool = False
    hunted: bool = False
    target_outcome: str | None = None
    looted: bool = False
    completed: bool = False


@dataclass(frozen=True)
class WorkStep:
    action: Action
    reason: str = ''


@dataclass(frozen=True)
class Observation:
    action: Action
    observed: bool
    game: str
    area: int | None = None
    outcome: str = ''


def next_work(
    work: AreaWork,
    capability: Capability,
    evidence: TerrorEvidence | None,
    *,
    now: float,
    max_evidence_age: float = 3,
    manual: bool = False,
    cancelled: bool = False,
) -> WorkStep:
    if cancelled:
        return WorkStep('stop', 'cancelled')
    if manual:
        return WorkStep('pause', 'manual intervention')
    if capability.area != work.area or capability.target != work.target:
        return WorkStep('stop', 'area capability mismatch')
    if work.completed:
        return WorkStep('done')
    if not work.prebuffed:
        return WorkStep('prebuff')
    if not work.restocked:
        return WorkStep('restock')
    if not work.arrived:
        if capability.status != 'ready':
            return WorkStep('stop', capability.reason or capability.status)
        if evidence is None or evidence.game != work.game or not 0 <= now - evidence.observed_at <= max_evidence_age:
            return WorkStep('wait', 'TZ list unread or stale')
        if work.area not in evidence.areas:
            return WorkStep('stop', 'area not in current TZ list')
        return WorkStep('travel')
    if not work.hunted:
        return WorkStep('hunt')
    if work.target is not None and work.target_outcome is None:
        return WorkStep('target')
    if not work.looted:
        return WorkStep('loot')
    return WorkStep('complete')


def advance(work: AreaWork, event: Observation) -> AreaWork:
    """Apply an executor's positive observation, never an attempted action alone."""
    if not event.observed or event.game != work.game:
        return work
    if event.action == 'prebuff' and not work.prebuffed:
        return replace(work, prebuffed=True)
    if event.action == 'restock' and work.prebuffed:
        return replace(work, restocked=True)
    if event.action == 'travel' and work.restocked and event.area == work.area:
        return replace(work, arrived=True)
    if (
        event.action == 'hunt'
        and work.arrived
        and event.area == work.area
        and event.outcome in ('exhausted', 'time-cap', 'path-cap')
    ):
        return replace(work, hunted=True)
    if (
        event.action == 'target'
        and work.hunted
        and event.area == work.area
        and event.outcome in ('killed', 'opened', 'failed', 'unreachable')
    ):
        return replace(work, target_outcome=event.outcome)
    if (
        event.action == 'loot'
        and work.hunted
        and (work.target is None or work.target_outcome is not None)
        and (event.area == work.area and event.outcome == 'clear')
    ):
        return replace(work, looted=True)
    if event.action == 'complete' and work.looted and event.area == work.area:
        return replace(work, completed=True)
    return work


class Slice:
    """One active TZ area, driven by a caller's *observed* game and action results.

    ``dispatch`` may start asynchronous macro work. Repeated ticks never send a
    second request while that work is pending. The production coordinator is
    disabled by default and a route must separately be promoted to ``ready``.
    """

    def __init__(
        self,
        coordinator: Coordinator,
        capabilities: dict[int, Capability],
        dispatch: Callable[[Action, int], bool],
        *,
        cancel: Callable[[], None] | None = None,
        action_timeout: float = 90,
    ) -> None:
        self.coordinator = coordinator
        self.capabilities = capabilities
        self.dispatch = dispatch
        self.cancel = cancel or (lambda: None)
        self.action_timeout = action_timeout
        self.work: AreaWork | None = None
        self.pending: Action | None = None
        self.pending_at: float | None = None
        self.prebuffed_game: str | None = None
        self.restocked_game: str | None = None

    def tick(
        self,
        game: str,
        now: float,
        *,
        entries: tuple[TerrorEntry, ...] | None,
        observed_at: float | None = None,
        area: int | None,
        completed: Observation | None = None,
        manual: bool = False,
        dead: bool = False,
        dangerous: bool = False,
        supplies: int | None = None,
        valuable_no_room: bool = False,
        character: str | None = None,
        difficulty: str | None = None,
    ) -> WorkStep:
        if not self.coordinator.on:
            if self.pending is not None:
                self.cancel()
            self.pending = None
            return WorkStep('stop', self.coordinator.stop_reason or 'inactive')
        if self.work is not None and game != self.work.game:
            self.cancel()
            self.pending = None
            self.coordinator._stop('game changed during TZ area')
            return WorkStep('stop', self.coordinator.stop_reason)
        if self.pending is not None and self.pending_at is not None and now - self.pending_at >= self.action_timeout:
            self.cancel()
            self.pending = None
            self.coordinator._stop('TZ area action timed out')
            return WorkStep('stop', self.coordinator.stop_reason)
        self.coordinator.observe(game, entries, at=now if observed_at is None else observed_at)
        choice = self.coordinator.decide(
            game,
            now=now,
            capabilities=self.capabilities,
            manual=manual,
            dead=dead,
            dangerous=dangerous,
            supplies=supplies,
            valuable_no_room=valuable_no_room,
            character=character,
            difficulty=difficulty,
        )
        if choice.action in ('stop', 'pause', 'wait'):
            if choice.action == 'stop':
                self.cancel()
                self.pending = None
            return WorkStep(choice.action, choice.reason)
        if self.work is None:
            if choice.action != 'enter' or choice.area is None:
                return WorkStep('reset' if choice.action == 'reset' else 'wait', choice.reason)
            capability = self.capabilities[choice.area]
            if not self.coordinator.begin_area(game, choice.area, capability, now=now):
                return WorkStep('wait', 'area confirmation was lost')
            self.work = AreaWork(
                game,
                choice.area,
                capability.target,
                prebuffed=self.prebuffed_game == game,
                restocked=self.restocked_game == game,
            )
        work = self.work
        assert work is not None
        if self.pending is not None and completed is not None and completed.action == self.pending:
            newer = advance(work, completed)
            if newer != work:
                self.pending = None
                self.pending_at = None
                self.work = work = newer
                observed = (
                    f'{work.target} {completed.outcome}'
                    if completed.action == 'target' and work.target is not None
                    else f'{completed.action} {completed.outcome or ""}'.strip()
                )
                LOG.info('TZ area %d: %s observed', work.area, observed)
                if completed.action == 'prebuff':
                    self.prebuffed_game = game
                elif completed.action == 'restock':
                    self.restocked_game = game
                if completed.action == 'target' and work.target is not None:
                    self.coordinator.target_outcome(game, work.area, work.target, completed.outcome)
                    if completed.outcome in ('failed', 'unreachable'):
                        self.cancel()
                        self.coordinator._stop(f'{work.target} {completed.outcome} in area {work.area}')
                        return WorkStep('stop', self.coordinator.stop_reason)
        capability = self.capabilities[work.area]
        step = next_work(work, capability, self.coordinator.reads.current(game, now), now=now, manual=manual)
        if step.action == 'complete':
            self.work = advance(work, Observation('complete', True, game, area=work.area))
            if self.coordinator.complete_area(game, work.area, work.target):
                if self.coordinator.metrics is not None and work.target is not None and work.target_outcome is not None:
                    self.coordinator.metrics.target(work.area, work.target, work.target_outcome)
                self.work = None
                return WorkStep('area-done', f'area {work.area} complete')
            return WorkStep('stop', 'route target outcome was not recorded')
        if step.action in ('stop', 'wait', 'pause', 'done'):
            if step.action == 'stop':
                self.cancel()
            return step
        if self.pending is None:
            if not self.dispatch(step.action, work.area):
                self.coordinator._stop(f'{step.action} could not start')
                return WorkStep('stop', self.coordinator.stop_reason)
            if self.coordinator.metrics is not None:
                phase = {
                    'prebuff': 'town',
                    'restock': 'town',
                    'travel': 'travel',
                    'hunt': 'combat',
                    'target': 'combat',
                    'loot': 'loot',
                }[step.action]
                self.coordinator.metrics.phase(phase, now)
            self.pending = step.action
            self.pending_at = now
        return step
