"""A highlight around a smith's Repair All button while the equipped Teleport staff is missing charges."""

from collections.abc import Sequence
from dataclasses import dataclass

from inventory_tracking.config import RepairMarkWidgetConfig
from inventory_tracking.osd.widgets.base import SampleWidget


@dataclass(frozen=True)
class Mark:
    """A square highlight in game-window units (fractions of the window height; x from the left, y from the bottom)."""

    kind: str
    center_x: float
    center_y: float
    size: float
    color: str
    pulse_seconds: float


class RepairMarkWidget(SampleWidget[RepairMarkWidgetConfig]):
    """No text: the window draws the mark returned by `mark`, text mode names it."""

    def render(self, *, now: float) -> Sequence[str]:
        return ()

    def mark(self, *, now: float) -> Mark | None:
        teleport, shop = self.state.teleport, self.state.shop
        charges, panel = teleport.value, shop.value
        if (
            self.config.enabled
            and teleport.fresh(now, self.max_age)
            and shop.fresh(now, self.max_age)
            and self.state.fresh(now, self.max_age)
            and charges is not None
            and charges.current < charges.maximum
            and panel is not None
            and panel.open
            and panel.smith
        ):
            config = self.config
            return Mark('repair', config.center_x, config.center_y, config.size, config.color, config.pulse_seconds)
        return None
