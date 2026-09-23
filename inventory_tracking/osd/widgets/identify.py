"""Low identify-tome stock reminder, visible only in town."""

from ...config import IdentifyWidgetConfig
from .base import SampleWidget


class IdentifyWidget(SampleWidget[IdentifyWidgetConfig]):
    def render(self, *, now: float) -> tuple[str, ...]:
        observation = self.state.identify_tome
        tome = observation.value
        location = self.state.location
        if (
            self.config.enabled
            and self.fresh(now)
            and observation.fresh(now, self.max_age)
            and tome is not None
            and tome.quantity < self.config.low_count
            and location.fresh(now, self.max_age)
            and location.value is not None
            and location.value.in_town
        ):
            return (f'id: {tome.quantity}',)
        return ()
