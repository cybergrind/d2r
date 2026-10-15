"""Per-actor potion execution policy, coordinated against the shared belt."""

import time
from collections.abc import Callable, Sequence

from inventory_tracking.automation.ledger import (
    ActorRecord,
    LastDelivery,
    LedgerData,
    LedgerTransaction,
    PendingReservation,
    PotionLedger,
    cooldown_key,
)
from inventory_tracking.common import LOG
from inventory_tracking.config import HealingConfig
from inventory_tracking.input import Delivery, InputError, Refused, Target
from inventory_tracking.models import (
    Actor,
    BeltCell,
    Outcome,
    PotionRequest,
    PotionResult,
    PotionSent,
    PotionType,
    SessionIdentity,
    State,
)
from inventory_tracking.tracking.belt import column_stock


def actor_session(state: State, session: SessionIdentity, actor: Actor) -> SessionIdentity:
    """The merc actor's record is bound to the hireling; the player's record ignores it."""
    if actor == Actor.MERC:
        return session._replace(merc_id=state.merc.unit_id if state.merc else None)
    return session


class PotionsController:
    def __init__(
        self,
        config: HealingConfig,
        ledger: PotionLedger,
        delivery: Delivery,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self.ledger = ledger
        self.delivery = delivery
        self.clock = clock
        # The game's input mode each press was made in, by item (rca/2026-10-13/controller-mode.md plan step 5):
        # the acknowledgement or the miss says it again, so a game in controller mode shows whether belt keys
        # act there, and whether a press during a pending flip is lost.
        self.pressed_in: dict[int, str] = {}
        # cooldown key -> the last stamp this controller set itself: a stamp of another's (the macro's drinker claims
        # the character's potion before its key: automation/ledger.py `PotionLedger.claim`) is stood off for, said once
        self.stamped: dict[str, float] = {}
        self.stood_off: float | None = None

    def step(self, state: State, choices: Sequence[PotionType]) -> PotionResult:
        if not self.config.enabled:
            return PotionResult(Outcome.DISABLED)
        now = self.clock()
        session = state.session
        if session is None or not state.fresh(now, self.config.sample_max_age):
            return PotionResult(Outcome.UNAVAILABLE)
        try:
            with self.ledger.transaction() as transaction:
                return self._step(state, actor_session(state, session, self.config.actor), choices, now, transaction)
        except BlockingIOError:
            return PotionResult(Outcome.BUSY)
        except OSError, ValueError, TypeError, KeyError:
            LOG.exception('Potion ledger unavailable; refusing input')
            return PotionResult(Outcome.UNAVAILABLE)

    def _step(
        self,
        state: State,
        session: SessionIdentity,
        choices: Sequence[PotionType],
        now: float,
        transaction: LedgerTransaction,
    ) -> PotionResult:
        data = transaction.data
        actor = self.config.actor
        record = self._update_actor(data, state, session, now)
        if record.suspended:
            return PotionResult(Outcome.SUSPENDED)
        if record.suspended_until is not None:
            if now < record.suspended_until:
                return PotionResult(Outcome.SUSPENDED)
            record.suspended_until = None
            LOG.info('%s healing resumed after pause', actor)
        if record.pending:
            return PotionResult(Outcome.PENDING)
        if not choices:
            return PotionResult(Outcome.IDLE)
        if record.retry_at is not None:
            if now < record.retry_at:
                return PotionResult(Outcome.BACKOFF)
            record.retry_at = None
        player = state.health_for(Actor.PLAYER)
        if player is None or player[0] <= 0:
            return PotionResult(Outcome.UNAVAILABLE)
        delivery = data.last_delivery
        if delivery and delivery.session == session.core and state.sampled_at <= delivery.at:
            return PotionResult(Outcome.STALE_BELT)
        candidate = self._choose_item(data, state, session, choices)
        if candidate is None:
            return PotionResult(Outcome.NO_STOCK)
        potion, item = candidate
        cooldown = self.config.cooldowns[potion]
        previous = data.cooldowns.get(cooldown_key(actor, potion))
        if previous is not None and now - previous < cooldown:
            self._stand_off(potion, previous, now)
            return PotionResult(Outcome.COOLDOWN)
        return self._deliver(state, PotionRequest(actor, potion, item), record, now, transaction)

    def _stand_off(self, potion: PotionType, stamp: float, now: float) -> None:
        """One line when a potion wanted now is held back by a stamp this controller did not set: the macro's drinker
        took the potion for this blow (one drinker per blow, rca/2026-10-14/run-1932-findings.md issue 2)."""
        key = cooldown_key(self.config.actor, potion)
        if self.stamped.get(key) == stamp or self.stood_off == stamp:
            return
        self.stood_off = stamp
        LOG.info(
            '%s healing: standing off: the macro took a %s potion %.2f s ago (its claim in the ledger); %.1f s '
            'cooldown',
            self.config.actor, potion, now - stamp, self.config.cooldowns[potion],
        )  # fmt: skip

    def _update_actor(self, data: LedgerData, state: State, session: SessionIdentity, now: float) -> ActorRecord:
        actor = self.config.actor
        record = data.actors.get(actor)
        # A missing merc is not a new session, but must not block pending upkeep.
        if record and session.merc_id is None and actor == Actor.MERC and record.session.core == session.core:
            session = session._replace(merc_id=record.session.merc_id)
        if record is None or record.session != session:
            record = ActorRecord(session=session)
            data.actors[actor] = record
        pending = record.pending
        if pending and not record.suspended and state.sampled_at > pending.sent_at:
            if state.belt is None or pending.item_id not in state.belt.item_ids:
                LOG.info(
                    '%s potion consumption acknowledged: item %s%s',
                    actor,
                    pending.item_id,
                    self._pressed(pending.item_id),
                )
                record.pending = None
                record.misses = 0
                record.retry_at = None
            elif now - pending.sent_at >= self.config.consumption_timeout:
                self._miss(record, pending, now)
        return record

    def _miss(self, record: ActorRecord, pending: PendingReservation, now: float) -> None:
        """A lost keypress is ordinary: retry with growing backoff, and only pause after a run of them."""
        actor = self.config.actor
        said = self._pressed(pending.item_id)
        record.pending = None
        record.misses += 1
        if record.misses >= self.config.max_consecutive_misses:
            record.misses = 0
            record.retry_at = None
            record.suspended_until = now + self.config.suspend_seconds
            LOG.warning(
                '%s healing paused for %.0f s: %d potions in a row were not consumed (last item %s%s)',
                actor,
                self.config.suspend_seconds,
                self.config.max_consecutive_misses,
                pending.item_id,
                said,
            )
            return
        delay = min(self.config.retry_backoff * 2 ** (record.misses - 1), self.config.retry_backoff_max)
        record.retry_at = now + delay
        LOG.warning(
            '%s potion not consumed: item %s%s; retry in %.1f s (miss %d of %d)',
            actor,
            pending.item_id,
            said,
            delay,
            record.misses,
            self.config.max_consecutive_misses,
        )

    def _pressed(self, item_id: int) -> str:
        """' (pressed in controller mode)' and the like; '' when the press's mode is not known."""
        mode = self.pressed_in.pop(item_id, None)
        if not mode:
            return ''
        return f' (pressed while {mode})' if mode.startswith('switching') else f' (pressed in {mode} mode)'

    @staticmethod
    def _choose_item(
        data: LedgerData, state: State, session: SessionIdentity, choices: Sequence[PotionType]
    ) -> tuple[PotionType, BeltCell] | None:
        belt_ids = state.belt.item_ids if state.belt else ()
        reserved = {
            record.pending.item_id
            for record in data.actors.values()
            if record.pending and record.session.core == session.core and record.pending.item_id in belt_ids
        }
        contents = state.belt.contents if state.belt else ()
        for potion in choices:
            usable = [cell for cell in state.usable_cells(potion) if cell.item_id not in reserved]
            if usable:
                # Drain the fullest column first so short stacks keep a reserve; ties keep the lowest column.
                return potion, max(usable, key=lambda cell: (column_stock(contents, cell.column, potion), -cell.column))
        return None

    def _deliver(
        self, state: State, request: PotionRequest, record: ActorRecord, now: float, transaction: LedgerTransaction
    ) -> PotionResult:
        actor, potion, item = request.actor, request.potion, request.item
        data = transaction.data
        key = cooldown_key(actor, potion)
        # Reserve attempts even on clean focus rejection, avoiding retry bursts.
        data.cooldowns[key] = self.stamped[key] = now
        transaction.save()
        previous = (record.pending, data.last_delivery)
        refusal = None
        completion: tuple[PendingReservation, LastDelivery, float] | None = None
        try:
            with self.delivery.attempt(
                Target(record.session, state.sampled_at, self.config.sample_max_age), request
            ) as attempt:
                refusal = attempt.refusal
                if refusal is None:
                    reserved_at = self.clock()
                    data.cooldowns[key] = self.stamped[key] = reserved_at
                    reservation = PendingReservation(item_id=item.item_id, sent_at=reserved_at)
                    delivery = LastDelivery(session=record.session.core, at=reserved_at)
                    record.pending = reservation
                    data.last_delivery = delivery
                    # A ledger save failure propagates without pressing or suspending.
                    transaction.save()
                    try:
                        finished_at = attempt.send()
                        completion = (reservation, delivery, finished_at)
                    except Refused as exc:
                        record.pending, data.last_delivery = previous
                        transaction.save()
                        refusal = exc.refusal
        except InputError:
            record.suspended = True
            LOG.exception('%s healing suspended after input error', actor)
            return PotionResult(Outcome.SUSPENDED)
        if completion is None:
            return PotionResult(Outcome.REJECTED, reason=refusal)
        reservation, delivery, finished_at = completion
        delivery.at = finished_at
        reservation.sent_at = finished_at
        mode = state.input_mode.value
        if mode is not None:
            self.pressed_in[item.item_id] = mode.label
            if len(self.pressed_in) > 64:  # items never acknowledged nor missed (a new session): the oldest go
                self.pressed_in.pop(next(iter(self.pressed_in)))
        LOG.info(
            '%s %s potion: column %s; item %s; input %s',
            actor,
            potion,
            item.column,
            item.item_id,
            mode.label if mode is not None else 'unread',
        )
        return PotionResult(Outcome.SENT, PotionSent(request, finished_at))
