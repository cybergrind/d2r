"""Player and mercenary health presentation, with the healing status when it is not healing."""

from collections.abc import Sequence

from inventory_tracking.automation.controller import NOTABLE, describe
from inventory_tracking.config import MercHealthWidgetConfig, PlayerHealthWidgetConfig
from inventory_tracking.models import Actor, State
from inventory_tracking.osd.widgets.base import SampleWidget


def healing_status(state: State, actor: Actor, prefix: str) -> tuple[str, ...]:
    """A line naming why the actor is not being healed; nothing while healing works or is not needed."""
    result = state.outcomes.get(actor)
    if result is None or result.outcome not in NOTABLE:
        return ()
    return (f'{prefix}heal: {describe(result)}',)


class PlayerHealthWidget(SampleWidget[PlayerHealthWidgetConfig]):
    def render(self, *, now: float) -> Sequence[str]:
        health = self.state.health_for(Actor.PLAYER)
        if not self.config.enabled or health is None or not self.fresh(now):
            return ()
        current, maximum = health
        lines = (f'{current >> 8}/{maximum >> 8}',) if current * 100 <= maximum * self.config.percent else ()
        return lines + healing_status(self.state, Actor.PLAYER, '')


class MercHealthWidget(SampleWidget[MercHealthWidgetConfig]):
    def render(self, *, now: float) -> Sequence[str]:
        merc = self.state.merc
        if not self.config.enabled or not self.fresh(now) or merc is None:
            return ()
        health = self.state.health_for(Actor.MERC)
        if health is None:
            return ('merc dead',)
        current, maximum = health
        lines: tuple[str, ...] = ()
        if current * 100 < maximum * self.config.percent:
            prefix = '' if current == maximum else '~'
            lines = (f'merc {prefix}{merc.current_raw >> 8}/{merc.maximum_raw >> 8}',)
        return lines + healing_status(self.state, Actor.MERC, 'merc ')
