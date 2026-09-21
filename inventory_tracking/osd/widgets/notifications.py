"""Time-limited successful potion delivery feedback."""

from collections.abc import Sequence

from ...config import NotificationsWidgetConfig
from ...models import Actor, State
from .base import SampleWidget


class NotificationsWidget(SampleWidget[NotificationsWidgetConfig]):
    def reset(self) -> None:
        super().reset()
        # Deliveries before the first sample of a new session belong to the old one.
        self.event_floor: float | None = None if getattr(self, 'has_sample', False) else float('-inf')
        self.has_sample = False

    def update(self, snapshot: State) -> None:
        if self.event_floor is None:
            self.event_floor = snapshot.sampled_at
        self.has_sample = True
        super().update(snapshot)

    def render(self, *, now: float) -> Sequence[str]:
        if not self.config.enabled:
            return ()
        lines = []
        for event in self.state.events:
            if (
                self.event_floor is not None
                and event.sent_at >= self.event_floor
                and 0 <= now - event.sent_at < self.config.seconds
            ):
                request = event.request
                key = f'Shift+{request.item.column}' if request.actor == Actor.MERC else str(request.item.column)
                lines.append(f'{request.actor} potion sent ({key})')
        return tuple(lines)
