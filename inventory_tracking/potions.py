"""Per-actor potion execution policy, coordinated against the shared belt."""

import time
from collections.abc import Callable, Sequence

from .belt import column_stock
from .common import LOG
from .config import HealingConfig
from .input import Delivery, InputError, Refused, Target
from .models import (
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
from .potion_ledger import (
    ActorRecord,
    LastDelivery,
    LedgerData,
    LedgerTransaction,
    PendingReservation,
    PotionLedger,
    cooldown_key,
)


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
        if record.pending:
            return PotionResult(Outcome.PENDING)
        if not choices:
            return PotionResult(Outcome.IDLE)
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
            return PotionResult(Outcome.COOLDOWN)
        return self._deliver(state, PotionRequest(actor, potion, item), record, now, transaction)

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
                LOG.info('%s potion consumption acknowledged: item %s', actor, pending.item_id)
                record.pending = None
            elif now - pending.sent_at >= self.config.consumption_timeout:
                record.suspended = True
                LOG.warning('%s healing suspended: consumption not acknowledged', actor)
        return record

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
        data.cooldowns[key] = now
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
                    data.cooldowns[key] = reserved_at
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
        LOG.info('%s %s potion: column %s; item %s', actor, potion, item.column, item.item_id)
        return PotionResult(Outcome.SENT, PotionSent(request, finished_at))
