"""A refill reminder shown only while the tome is below its stock threshold."""

from collections.abc import Sequence

from inventory_tracking.config import PortalWidgetConfig
from inventory_tracking.osd.widgets.base import SampleWidget


class PortalWidget(SampleWidget[PortalWidgetConfig]):
    def render(self, *, now: float) -> Sequence[str]:
        observation = self.state.portal_tome
        tome = observation.value
        if (
            self.config.enabled
            and observation.fresh(now, self.max_age)
            and observation.fresh(self.state.sampled_at, self.max_age)
            and tome is not None
            and tome.capacity == self.config.capacity
            and 0 <= tome.quantity <= self.config.trigger_remaining
        ):
            return (f'tp: {tome.capacity - tome.quantity}',)
        return ()
