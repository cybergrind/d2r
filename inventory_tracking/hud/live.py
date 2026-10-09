"""Positions read by the canvas itself, every frame (user, 2026-10-05: marks lagged).

Ground marks are map points drawn relative to the player, so they are only as fresh as the
player position, and a marked monster walks too. The level guide publishes both twice a second;
in between, the canvas reads the eight position bytes of each unit's dynamic path straight from
the game: the player's (`live` in the ground payload: pid and address) and every mark that
carries a path address (pack leaders and Heralds, terror/tracker.py). Nothing notifies another
process of a memory write without stopping the game, but a read costs microseconds, so polling
once per frame is as good as instant.
The path keeps whole world units at +0x02/+0x06 (confirmed, levels/memory.py); +0x00/+0x04 are
taken as their 16-bit fractions, the classic layout, not confirmed here. A read that fails or
lands far from the published position (a freed path, another level) leaves that one position as
published; a monster that died stays marked until the next published card drops it.

The open-panel flags are read the same way (user, 2026-10-07): while the player reads items in
the inventory, stash, shop or mercenary panel, the canvas draws the slots of HUD.dim_slots faint.
The producer names the flag array in a 'panels' widget (hud/process.py PanelBeacon), which has
no slot and is never drawn.
"""

import os
import struct

from inventory_tracking.common import LOG
from inventory_tracking.hud.scene import Widget
from inventory_tracking.native.layout import TILE_UNITS, UI_PANELS_SIZE
from inventory_tracking.tracking.panels import decode_panels


MAX_DRIFT = 40  # tiles from the published position; further means the address is stale


def position(data: bytes) -> tuple[float, float]:
    """Path bytes +0x00..+0x08 -> (x, y) in tiles."""
    x_fraction, x, y_fraction, y = struct.unpack('<HHHH', data)
    return (x + x_fraction / 65536) / TILE_UNITS, (y + y_fraction / 65536) / TILE_UNITS


class GameMemory:
    """Keeps /proc/<pid>/mem open for the game the payloads name."""

    def __init__(self, open_memory=lambda pid: os.open(f'/proc/{pid}/mem', os.O_RDONLY), read=os.pread):
        self.open_memory, self.read = open_memory, read
        self.pid, self.fd, self.warned = None, None, None

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
        self.pid, self.fd = None, None

    def attach(self, pid) -> bool:
        """Whether `pid`'s memory is open for reading (opened here when the game changed)."""
        if pid == self.pid:
            return True
        self.close()
        try:
            self.pid, self.fd = pid, self.open_memory(pid)
        except OSError as exc:
            if self.warned != pid:
                LOG.warning('HUD cannot read the memory of pid %s: %s', pid, exc)
                self.warned = pid
            return False
        return True


class LiveUnits(GameMemory):
    def at(self, address, x, y) -> tuple[float, float]:
        """Where the unit whose path is at `address` is now; the published (x, y) when that is unknown."""
        try:
            now_x, now_y = position(self.read(self.fd, 8, address))
        except OSError, struct.error:
            return x, y
        return (now_x, now_y) if abs(now_x - x) <= MAX_DRIFT and abs(now_y - y) <= MAX_DRIFT else (x, y)

    def locate(self, payload) -> dict | None:
        """The ground payload with every readable position as it is now; None when it should stand as published."""
        live = payload.get('live')
        if not live:
            return None
        pid, address = live
        if not self.attach(pid):
            return None
        marks = [
            [kind, *self.at(path[0], x, y), *path] if path else [kind, x, y] for kind, x, y, *path in payload['marks']
        ]
        return {**payload, 'player': list(self.at(address, *payload['player'])), 'marks': marks}


class OpenPanels(GameMemory):
    """Whether one of the panels `names` (native/layout.py PANEL_FLAGS) is open right now."""

    def __init__(self, names, **memory):
        super().__init__(**memory)
        self.names = tuple(names)

    def reading(self, live) -> bool:
        """`live`: (pid, address of the flag array), or None. Flags that cannot be read or are not
        all 0/1 count as no panel: the HUD stays at full strength."""
        if not live:
            return False
        pid, address = live
        if not self.attach(pid):
            return False
        try:
            flags = decode_panels(self.read(self.fd, UI_PANELS_SIZE, address))
        except OSError, ValueError:
            return False
        return any(flags[name] for name in self.names)


def panel_source(widgets):
    """(where the open-panel flags are, the widgets to lay out): the 'panels' widget only carries
    the address."""
    live = next((w.payload.get('live') for w in widgets if w.kind == 'panels'), None)
    return live, [w for w in widgets if w.kind != 'panels']


class Entrance:
    """Seconds since the ground marks of the current level appeared: the arrows to marks out of
    view start near the player and move out (hud/ground.py arrow_reach)."""

    def __init__(self):
        self.level, self.since = None, 0.0

    def age(self, payload, now) -> float | None:
        if payload is None:
            self.level = None
            return None
        if payload.get('level') != self.level:
            self.level, self.since = payload.get('level'), now
        return now - self.since


def ground_payload_of(boxes) -> dict | None:
    return next((widget.payload for widget, _ in boxes if widget.kind == 'ground'), None)


def follow(boxes, ground):
    """`boxes` with the ground widget's payload replaced by its live one (None = unchanged), and
    the map card's player moved with it: a map that keeps the player in the middle
    (osd/level_map.py LOCAL_SCALE) would otherwise scroll in half-second steps."""
    if ground is None:
        return boxes
    return [(Widget(w.id, w.kind, w.slot, _followed(w, ground)), box) for w, box in boxes]


def _followed(widget, ground):
    if widget.kind == 'ground':
        return ground
    card = widget.payload.get('map') if widget.kind == 'guide' and isinstance(widget.payload, dict) else None
    if not (isinstance(card, dict) and isinstance(card.get('map'), dict)):
        return widget.payload
    return {**widget.payload, 'map': {**card, 'map': {**card['map'], 'player': list(ground['player'])}}}
