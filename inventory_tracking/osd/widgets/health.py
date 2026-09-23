"""Player and mercenary health presentation."""

from collections.abc import Sequence

from inventory_tracking.config import MercHealthWidgetConfig, PlayerHealthWidgetConfig
from inventory_tracking.models import Actor
from inventory_tracking.osd.widgets.base import SampleWidget


class PlayerHealthWidget(SampleWidget[PlayerHealthWidgetConfig]):
    def render(self, *, now: float) -> Sequence[str]:
        health = self.state.health_for(Actor.PLAYER)
        if not self.config.enabled or health is None or not self.fresh(now):
            return ()
        current, maximum = health
        if current * 100 <= maximum * self.config.percent:
            return (f'{current >> 8}/{maximum >> 8}',)
        return ()


class MercHealthWidget(SampleWidget[MercHealthWidgetConfig]):
    def render(self, *, now: float) -> Sequence[str]:
        merc = self.state.merc
        if not self.config.enabled or not self.fresh(now) or merc is None:
            return ()
        health = self.state.health_for(Actor.MERC)
        if health is None:
            return ('merc dead',)
        current, maximum = health
        if current * 100 < maximum * self.config.percent:
            prefix = '' if current == maximum else '~'
            return (f'merc {prefix}{merc.current_raw >> 8}/{merc.maximum_raw >> 8}',)
        return ()
