"""Low ordinary-key count in the player's inventory."""

from inventory_tracking.config import KeysWidgetConfig
from inventory_tracking.osd.widgets.base import SampleWidget


class KeysWidget(SampleWidget[KeysWidgetConfig]):
    def render(self, *, now: float) -> tuple[str, ...]:
        observation = self.state.keys
        count = observation.value
        if (
            self.config.enabled
            and self.fresh(now)
            and observation.fresh(now, self.max_age)
            and type(count) is int
            and 0 <= count < self.config.low_count
        ):
            return (f'keys: {count}',)
        return ()
