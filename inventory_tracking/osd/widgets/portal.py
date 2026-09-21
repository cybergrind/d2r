"""A refill reminder that stays latched until the tome is full."""

from collections.abc import Sequence

from ...config import PortalWidgetConfig
from ...models import State
from .base import SampleWidget


class PortalWidget(SampleWidget[PortalWidgetConfig]):
    def reset(self) -> None:
        super().reset()
        self.item_id: int | None = None
        self.latched = False

    def update(self, snapshot: State) -> None:
        super().update(snapshot)
        observation = snapshot.portal_tome
        if not observation.fresh(snapshot.sampled_at, self.max_age):
            return
        tome = observation.value
        if tome is None:
            self.item_id = None
            self.latched = False
            return
        if tome.capacity != self.config.capacity:
            return
        if tome.item_id != self.item_id:
            self.item_id = tome.item_id
            self.latched = False
        if tome.quantity <= self.config.trigger_remaining:
            self.latched = True
        elif tome.quantity == tome.capacity:
            self.latched = False

    def render(self, *, now: float) -> Sequence[str]:
        observation = self.state.portal_tome
        tome = observation.value
        if (
            self.config.enabled
            and observation.fresh(now, self.max_age)
            and observation.fresh(self.state.sampled_at, self.max_age)
            and tome is not None
            and tome.capacity == self.config.capacity
            and 0 <= tome.quantity < tome.capacity
            and self.latched
        ):
            return (f'tp: {tome.capacity - tome.quantity}',)
        return ()
