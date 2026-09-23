"""Optional secondary staff charge and town repair reminder."""

from collections.abc import Sequence

from inventory_tracking.config import TeleportWidgetConfig
from inventory_tracking.osd.widgets.base import SampleWidget


class TeleportWidget(SampleWidget[TeleportWidgetConfig]):
    def render(self, *, now: float) -> Sequence[str]:
        observation = self.state.teleport
        charges = observation.value
        if not self.config.enabled or not observation.fresh(now, self.max_age) or charges is None:
            return ()
        if charges.current == charges.maximum:
            return ()
        location = self.state.location
        repair = (
            self.config.show_repair_in_town
            and location.fresh(now, self.max_age)
            and location.value is not None
            and location.value.in_town
        )
        low = charges.current * 100 < charges.maximum * self.config.low_percent
        if repair or low:
            return (f'tele {charges.current}/{charges.maximum}' + (' repair' if repair else ''),)
        return ()
