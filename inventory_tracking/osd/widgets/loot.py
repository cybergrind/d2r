"""Warn when item labels are confirmed off in the current game."""

from inventory_tracking.config import LootWidgetConfig
from inventory_tracking.osd.widgets.base import SampleWidget


class LootWidget(SampleWidget[LootWidgetConfig]):
    def render(self, *, now: float) -> tuple[str, ...]:
        observation = self.state.show_items
        if (
            self.config.enabled
            and self.fresh(now)
            and observation.fresh(now, self.max_age)
            and observation.value is False
        ):
            return ('loot is not enabled',)
        return ()
