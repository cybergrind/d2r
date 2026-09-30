"""Scene protocol: each producer writes one lease file of widgets; the renderer merges them.

`<scene dir>/<producer>.json` = {checked_at: monotonic, widgets: [{id, kind, slot, payload}]}.
A layer older than LEASE_SECONDS is hidden, so a stalled or dead producer clears itself.
Monotonic time is shared by processes on one host, which is where producer and renderer run.
"""

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from inventory_tracking.reports import publish


LEASE_SECONDS = 1.5
DEFAULT_SCENE = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'd2r-hud'


@dataclass(frozen=True)
class Widget:
    id: str
    kind: str
    slot: str
    payload: dict[str, Any]

    @classmethod
    def from_payload(cls, value) -> Widget:
        if not isinstance(value, dict):
            raise ValueError('widget must be an object')
        fields = [value.get(key) for key in ('id', 'kind', 'slot')]
        if not all(isinstance(field, str) and field for field in fields) or not isinstance(value.get('payload'), dict):
            raise ValueError('widget needs string id/kind/slot and an object payload')
        return cls(*fields, value['payload'])


def publish_layer(directory: Path, producer: str, widgets, *, now: float | None = None):
    directory.mkdir(parents=True, exist_ok=True)
    checked_at = time.monotonic() if now is None else now
    publish(directory / f'{producer}.json', {'checked_at': checked_at, 'widgets': [asdict(w) for w in widgets]})


def read_scene(directory: Path, *, now: float) -> list[Widget]:
    """Fresh widgets of every producer, in producer (file name) then widget id order."""
    scene = []
    try:
        paths = sorted(directory.glob('*.json'))
    except OSError:
        return []
    for path in paths:
        try:
            frame = json.loads(path.read_text())
            if not 0 <= now - frame['checked_at'] < LEASE_SECONDS:
                continue
            widgets = [Widget.from_payload(value) for value in frame['widgets']]
        except OSError, ValueError, KeyError, TypeError:
            continue  # one malformed producer never hides the others
        scene.extend(sorted(widgets, key=lambda w: w.id))
    return scene
