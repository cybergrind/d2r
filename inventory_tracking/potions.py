"""Per-actor potion execution policy, coordinated against the shared belt."""

import time

from .belt import usable_cells
from .common import LOG
from .config import INPUT
from .models import Actor, BeltCell, Outcome, PotionRequest, PotionResult, PotionSent


def session_identity(state, actor):
    return [
        state.process_id,
        state.process_start,
        state.player_id,
        state.merc.unit_id if actor == Actor.MERC and state.merc else None,
    ]


def fresh(state, now, max_age):
    return (
        not state.reason
        and state.current_raw is not None
        and state.process_id is not None
        and state.process_start is not None
        and state.player_id is not None
        and 0 <= now - state.sampled_at <= max_age
    )


class PotionsController:
    def __init__(self, config, ledger, deliver, *, clock=time.monotonic, input_config=INPUT):
        self.config = config
        self.ledger = ledger
        self.deliver = deliver
        self.clock = clock
        self.input_config = input_config

    def step(self, state, choices):
        if not self.config.enabled:
            return PotionResult(Outcome.DISABLED)
        now = self.clock()
        if not fresh(state, now, self.config.sample_max_age):
            return PotionResult(Outcome.UNAVAILABLE)
        try:
            with self.ledger.transaction() as transaction:
                return self._step(state, choices, now, transaction)
        except BlockingIOError:
            return PotionResult(Outcome.BUSY)
        except OSError, ValueError, TypeError, KeyError:
            LOG.exception('Potion ledger unavailable; refusing input')
            return PotionResult(Outcome.UNAVAILABLE)

    def _step(self, state, choices, now, transaction):
        data = transaction.data
        actor = self.config.actor
        session = session_identity(state, actor)
        record = self._update_actor(data, state, session, now)
        if record['suspended']:
            return PotionResult(Outcome.SUSPENDED)
        if record['pending']:
            return PotionResult(Outcome.PENDING)
        if not choices:
            return PotionResult(Outcome.IDLE)
        if not state.gameplay_ready or state.current_raw <= 0:
            return PotionResult(Outcome.UNAVAILABLE)
        last_delivery = data['last_delivery']
        if last_delivery and last_delivery['session'] == session[:3] and state.sampled_at <= last_delivery['at']:
            return PotionResult(Outcome.STALE_BELT)
        candidate = self._choose_item(data, state, session, choices)
        if candidate is None:
            return PotionResult(Outcome.NO_STOCK)
        potion, item = candidate
        key = f'{actor}:{potion}'
        cooldown = self.config.cooldowns[potion]
        previous = data['cooldowns'].get(key)
        legacy = data['legacy_sent_at']
        if (previous is not None and now - previous < cooldown) or (
            legacy is not None and now - legacy < max(cooldown, self.input_config.legacy_cooldown)
        ):
            return PotionResult(Outcome.COOLDOWN)
        request = PotionRequest(actor, potion, item)
        return self._deliver(state, request, record, now, transaction)

    def _update_actor(self, data, state, session, now):
        actor = self.config.actor
        record = data['actors'].get(actor)
        # A missing merc is not a new session, but must not block pending upkeep.
        if record and session[3] is None and actor == Actor.MERC and record['session'][:3] == session[:3]:
            session[3] = record['session'][3]
        if record is None or record['session'] != session:
            record = {'session': session, 'pending': None, 'suspended': False}
            data['actors'][actor] = record
        pending = record['pending']
        if pending and not record['suspended'] and state.sampled_at > pending['sent_at']:
            if pending['item_id'] not in state.belt_ids:
                LOG.info('%s potion consumption acknowledged: item %s', actor, pending['item_id'])
                record['pending'] = None
            elif now - pending['sent_at'] >= self.config.consumption_timeout:
                record['suspended'] = True
                LOG.warning('%s healing suspended: consumption not acknowledged', actor)
        return record

    @staticmethod
    def _choose_item(data, state, session, choices):
        reserved = {
            r['pending']['item_id']
            for r in data['actors'].values()
            if r['pending'] and r['session'][:3] == session[:3] and r['pending']['item_id'] in state.belt_ids
        }
        for potion in choices:
            cells = usable_cells(state, potion)
            item = next((BeltCell(*cell) for cell in cells if cell[1] not in reserved), None)
            if item is not None:
                break
        else:
            return None
        return potion, item

    def _deliver(self, state, request, record, now, transaction):
        actor, potion, item = request.actor, request.potion, request.item
        data = transaction.data
        session = record['session']
        key = f'{actor}:{potion}'
        # Reserve attempts even on clean focus rejection, avoiding retry bursts.
        data['cooldowns'][key] = now
        transaction.save()
        sent_at = None

        def before_send():
            nonlocal sent_at
            sent_at = self.clock()
            data['cooldowns'][key] = sent_at
            record['pending'] = {'item_id': item.item_id, 'sent_at': sent_at}
            data['last_delivery'] = {'session': session[:3], 'at': sent_at}
            # Persist before the first key-down: interrupted delivery is uncertain.
            transaction.save()

        try:
            sent = self.deliver(state, request, max_age=self.config.sample_max_age, before_send=before_send)
            if sent and sent_at is None:
                raise RuntimeError('Input backend omitted delivery reservation')
        except Exception:
            record['suspended'] = True
            LOG.exception('%s healing suspended after input error', actor)
            return PotionResult(Outcome.SUSPENDED)
        if not sent:
            if sent_at is not None:
                record['suspended'] = True
                return PotionResult(Outcome.SUSPENDED)
            return PotionResult(Outcome.REJECTED)
        finished_at = self.clock()
        data['last_delivery']['at'] = finished_at
        record['pending']['sent_at'] = finished_at
        LOG.info('%s %s potion: column %s; item %s', actor, potion, item.column, item.item_id)
        return PotionResult(Outcome.SENT, PotionSent(request, finished_at))
