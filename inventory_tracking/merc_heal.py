"""Player/merc potion policy with cooldown and belt acknowledgement."""

from . import healing_config as config
from .common import LOG


class MercHealController:
    def __init__(self, target='merc'):
        if target not in ('player', 'merc'):
            raise ValueError('Unknown potion recipient')
        self.target = target
        self.last_attempt = float('-inf')
        self.pending = None
        self.session = None
        self.suspended = False

    def step(self, state, now, send):
        if (
            state.current_raw is None
            or (self.target == 'merc' and state.merc is None)
            or not 0 <= now - state.sampled_at <= config.SAMPLE_MAX_AGE_SECONDS
        ):
            return
        session = (
            state.process_id,
            state.process_start,
            state.player_id,
            state.merc.unit_id if self.target == 'merc' and state.merc else None,
        )
        if session != self.session:
            self.session = session
            self.pending = None
            self.suspended = False
        if self.pending is not None:
            item_id, sent_at = self.pending
            if item_id not in state.belt_ids:
                LOG.info('%s potion consumption acknowledged: item %s', self.target, item_id)
                self.pending = None
            elif now - sent_at >= config.CONSUMPTION_TIMEOUT_SECONDS:
                LOG.warning('%s healing suspended: potion consumption not acknowledged', self.target)
                self.suspended = True
                self.pending = None
        merc = state.merc
        if self.suspended or self.pending is not None or not state.gameplay_ready or state.current_raw <= 0:
            return
        if self.target == 'merc':
            if merc is None or not merc.alive or merc.current_raw <= 0:
                return
            current, maximum = merc.life_fraction_raw, 32768
            health_threshold = config.MERC_HEALTH_POTION_BELOW_PERCENT
            rejuv_threshold = config.MERC_REJUVENATION_BELOW_PERCENT
        else:
            current, maximum = state.current_raw, state.maximum_raw
            health_threshold = config.PLAYER_HEALTH_POTION_BELOW_PERCENT
            rejuv_threshold = config.PLAYER_REJUVENATION_BELOW_PERCENT
        if maximum is None or maximum <= 0:
            return
        # Prefer rejuvenation in emergencies; fall back to healing if none is usable.
        if current * 100 < maximum * rejuv_threshold and state.rejuvenation_cells:
            cells = state.rejuvenation_cells
        elif current * 100 < maximum * health_threshold and state.healing_cells:
            cells = state.healing_cells
        else:
            return
        cooldown = (
            config.PLAYER_REJUVENATION_COOLDOWN_SECONDS
            if self.target == 'player' and cells is state.rejuvenation_cells
            else config.POTION_COOLDOWN_SECONDS
        )
        if now - self.last_attempt < cooldown:
            return
        column, item_id = cells[0]
        # Reserve even on input failure: retries must never produce a burst.
        self.last_attempt = now
        try:
            sent = send(state, column)
        except Exception:
            self.suspended = True
            LOG.exception('%s healing suspended after input error', self.target)
            return
        if sent:
            self.pending = (item_id, now)
            LOG.info(
                '%s potion: column %s; life %s/%s; item %s',
                self.target,
                column,
                current,
                maximum,
                item_id,
            )
