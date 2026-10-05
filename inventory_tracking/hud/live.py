"""The player's position read by the canvas itself, every frame (user, 2026-10-05: marks lagged).

Ground marks are map points drawn relative to the player, so they are only as fresh as the
player position. The level guide publishes that twice a second; in between, the canvas reads
the eight position bytes of the player's dynamic path (`live` in the ground payload: pid and
address) straight from the game. Nothing notifies another process of a memory write without
stopping the game, but this read costs microseconds, so polling once per frame is as good as instant.
The path keeps whole world units at +0x02/+0x06 (confirmed, levels/memory.py); +0x00/+0x04 are
taken as their 16-bit fractions, the classic layout, not confirmed here. A read that fails or
lands far from the published position (a freed path, another level) is ignored.
"""

import os
import struct

from inventory_tracking.common import LOG
from inventory_tracking.hud.scene import Widget
from inventory_tracking.native.layout import TILE_UNITS


MAX_DRIFT = 40  # tiles from the published position; further means the address is stale


def position(data: bytes) -> tuple[float, float]:
    """Path bytes +0x00..+0x08 -> (x, y) in tiles."""
    x_fraction, x, y_fraction, y = struct.unpack('<HHHH', data)
    return (x + x_fraction / 65536) / TILE_UNITS, (y + y_fraction / 65536) / TILE_UNITS


class LivePlayer:
    """Keeps /proc/<pid>/mem open for the game the payloads name."""

    def __init__(self, open_memory=lambda pid: os.open(f'/proc/{pid}/mem', os.O_RDONLY), read=os.pread):
        self.open_memory, self.read = open_memory, read
        self.pid, self.fd, self.warned = None, None, None

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
        self.pid, self.fd = None, None

    def locate(self, payload) -> tuple[float, float] | None:
        """The player's position now, in tiles; None when the payload's own position should stand."""
        live = payload.get('live')
        if not live:
            return None
        pid, address = live
        try:
            if pid != self.pid:
                self.close()
                self.pid, self.fd = pid, self.open_memory(pid)
            x, y = position(self.read(self.fd, 8, address))
        except (OSError, struct.error) as exc:
            if self.warned != pid:
                LOG.warning('HUD live position unavailable for pid %s: %s', pid, exc)
                self.warned = pid
            self.close()
            return None
        px, py = payload['player']
        return (x, y) if abs(x - px) <= MAX_DRIFT and abs(y - py) <= MAX_DRIFT else None


def ground_payload_of(boxes) -> dict | None:
    return next((widget.payload for widget, _ in boxes if widget.kind == 'ground'), None)


def follow(boxes, player):
    """`boxes` with the ground widget's player replaced by the live position (None = unchanged)."""
    if player is None:
        return boxes
    return [
        (Widget(w.id, w.kind, w.slot, {**w.payload, 'player': list(player)}) if w.kind == 'ground' else w, box)
        for w, box in boxes
    ]
