"""Toolkit-independent formatting of domain state."""

from ..belt import column_shortages, potion_count
from ..config import OSD
from ..models import Actor, PotionType


def display_lines(state, *, now, config=OSD):
    lines = []
    for event in state.events:
        if 0 <= now - event.sent_at < config.notification_seconds:
            request = event.request
            key = f'Shift+{request.item.column}' if request.actor == Actor.MERC else str(request.item.column)
            lines.append(f'{request.actor} potion sent ({key})')
    if state.current_raw is None or not 0 <= now - state.sampled_at <= config.max_age:
        return lines
    if state.current_raw * 100 <= state.maximum_raw * config.player_health_percent:
        lines.append(f'{state.current_raw >> 8}/{state.maximum_raw >> 8}')
    if state.merc is not None:
        if not state.merc.alive:
            lines.append('merc dead')
        elif state.merc.life_fraction_raw * 100 < 32768 * config.merc_health_percent:
            prefix = '' if state.merc.life_fraction_raw == 32768 else '~'
            lines.append(f'merc {prefix}{state.merc.current_raw >> 8}/{state.merc.maximum_raw >> 8}')
    if state.belt_contents is None:
        return lines
    missing_rejuvenations, missing_healing = column_shortages(state.belt_contents)
    if config.rejuvenation_target is not None:
        missing_rejuvenations = max(
            0, config.rejuvenation_target - potion_count(state.belt_contents, PotionType.REJUVENATION)
        )
    if config.healing_target is not None:
        missing_healing = max(0, config.healing_target - potion_count(state.belt_contents, PotionType.HEALING))
    if missing_rejuvenations:
        lines.append(f'juv {missing_rejuvenations}')
    if missing_healing:
        lines.append(f'hp {missing_healing}')
    return lines
