"""Compose widgets and serialize reader updates with UI rendering."""

from threading import Lock

from ..common import LOG
from ..config import OSD
from .widgets.belt import BeltWidget
from .widgets.health import MercHealthWidget, PlayerHealthWidget
from .widgets.notifications import NotificationsWidget
from .widgets.portal import PortalWidget
from .widgets.teleport import TeleportWidget


def default_widgets(config):
    return [
        widget(config)
        for widget in (
            NotificationsWidget,
            PlayerHealthWidget,
            MercHealthWidget,
            BeltWidget,
            TeleportWidget,
            PortalWidget,
        )
    ]


class Presenter:
    def __init__(self, config=OSD, *, widgets=None):
        self.widgets = default_widgets(config) if widgets is None else list(widgets)
        self.lock = Lock()
        self.session = None
        self.failed = set()
        self.errors = {}
        self.last_sample = None

    def _failed(self, index, exc):
        signature = (type(exc), str(exc))
        if self.errors.get(index) != signature:
            LOG.exception('OSD widget %s failed: %s', type(self.widgets[index]).__name__, exc)
        self.errors[index] = signature
        self.failed.add(index)

    def update(self, snapshot):
        with self.lock:
            identity = (snapshot.process_id, snapshot.process_start, snapshot.player_id)
            identity = identity if all(part is not None for part in identity) else None
            changed = identity is not None and identity != self.session
            if not changed and self.last_sample is not None and snapshot.sampled_at < self.last_sample:
                return
            self.last_sample = snapshot.sampled_at
            for index, widget in enumerate(self.widgets):
                try:
                    if changed or snapshot.session_ended:
                        widget.reset()
                    if not snapshot.session_ended:
                        widget.update(snapshot)
                    self.failed.discard(index)
                except Exception as exc:
                    self._failed(index, exc)
            if snapshot.session_ended:
                self.session = None
            elif identity is not None:
                self.session = identity

    def render(self, *, now):
        with self.lock:
            lines = []
            for index, widget in enumerate(self.widgets):
                if index in self.failed:
                    continue
                try:
                    lines.extend(widget.render(now=now))
                    self.errors.pop(index, None)
                except Exception as exc:
                    self._failed(index, exc)
            return lines
