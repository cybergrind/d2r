"""Time-limited successful potion delivery feedback."""

from ...models import Actor
from .base import SampleWidget


class NotificationsWidget(SampleWidget):
    def reset(self):
        super().reset()
        self.event_floor = None if getattr(self, 'has_sample', False) else float('-inf')
        self.has_sample = False

    def update(self, snapshot):
        if self.event_floor is None:
            self.event_floor = snapshot.sampled_at
        self.has_sample = True
        super().update(snapshot)

    def render(self, *, now):
        lines = []
        for event in self.state.events:
            if (
                self.event_floor is not None
                and event.sent_at >= self.event_floor
                and 0 <= now - event.sent_at < self.config.notification_seconds
            ):
                request = event.request
                key = f'Shift+{request.item.column}' if request.actor == Actor.MERC else str(request.item.column)
                lines.append(f'{request.actor} potion sent ({key})')
        return tuple(lines)
