"""Positions read by the canvas itself, every frame (user, 2026-10-05: marks lagged).

Ground marks are map points drawn relative to the player, so they are only as fresh as the
player position, and a marked monster walks too. The level guide publishes both twice a second;
in between, the canvas reads the eight position bytes of each unit's dynamic path straight from
the game: the player's (`live` in the ground payload: pid and address) and every mark that
carries a path address (a mark with no unit record: hud/dots.py reads those). Nothing notifies another
process of a memory write without stopping the game, but a read costs microseconds, so polling
once per frame is as good as instant.
The path keeps whole world units at +0x02/+0x06 (confirmed, levels/memory.py); +0x00/+0x04 are
taken as their 16-bit fractions, the classic layout, not confirmed here. A read that fails or
lands far from the published position (a freed path, another level) leaves that one position as
published. Every monster dot, on the map card and on the ground, carries its unit record too: hud/dots.py
reads its mode and position each frame, so a dead monster's dot goes at once and a new monster gets one
from the canvas's own walk of the monster table (rca/2026-10-14/run-1916-hud-findings.md §2); `follow`
puts them on both.

The open-panel flags are read the same way (user, 2026-10-07): while the player reads items in
the inventory, stash, shop or mercenary panel, the canvas draws the slots of HUD.dim_slots faint.
The producer names the flag array in a 'panels' widget (hud/process.py PanelBeacon), which has
no slot and is never drawn. The same widget names the game's input mode byte (1: controller), read each
refresh so the slots are laid out for the layout the game shows (HUD.controller_slots, 2026-10-13).
"""

import os
import struct

from inventory_tracking.common import LOG
from inventory_tracking.config import HUD
from inventory_tracking.hud.scene import Widget
from inventory_tracking.native.layout import TILE_UNITS, UI_PANELS_SIZE
from inventory_tracking.native.memory import ProcessMemory, open_memory
from inventory_tracking.tracking.panels import decode_panels


MAX_DRIFT = 40  # tiles from the published position; further means the address is stale


def position(data: bytes) -> tuple[float, float]:
    """Path bytes +0x00..+0x08 -> (x, y) in tiles."""
    x_fraction, x, y_fraction, y = struct.unpack('<HHHH', data)
    return (x + x_fraction / 65536) / TILE_UNITS, (y + y_fraction / 65536) / TILE_UNITS


class LiveMemory:
    """Keeps /proc/<pid>/mem open for the game the payloads name, rebound when it changes (game/
    GameMemory is the macro's: one game a run, short reads refused). `read(fd, size, address)`: a pread, whose short
    reads the callers' decoders reject."""

    def __init__(self, open_memory=open_memory, read=os.pread):
        self.memory = ProcessMemory(opener=open_memory)
        self.read = read
        self.warned: int | None = None

    @property
    def pid(self) -> int | None:
        return self.memory.pid

    @property
    def fd(self) -> int | None:
        return self.memory.fd

    def close(self):
        self.memory.close()

    def attach(self, pid) -> bool:
        """Whether `pid`'s memory is open for reading (opened here when the game changed)."""
        try:
            self.memory.bind(pid)
        except OSError as exc:
            if self.warned != pid:
                LOG.warning('HUD cannot read the memory of pid %s: %s', pid, exc)
                self.warned = pid
            return False
        return True

    def read_attached(self, size, address) -> bytes:
        """`size` bytes at `address` of the game attach() opened (only called after it returned True)."""
        assert self.fd is not None
        return self.read(self.fd, size, address)


class LiveUnits(LiveMemory):
    def at(self, address, x, y) -> tuple[float, float]:
        """Where the unit whose path is at `address` is now; the published (x, y) when that is unknown."""
        try:
            now_x, now_y = position(self.read_attached(8, address))
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
            [kind, *self.at(path[0], x, y), *path] if len(path) == 1 else [kind, x, y, *path]
            for kind, x, y, *path in payload['marks']
        ]  # a mark with its unit record (path, unit, id) is hud/dots.py's: `follow` places it
        return {**payload, 'player': list(self.at(address, *payload['player'])), 'marks': marks}


class OpenPanels(LiveMemory):
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
            flags = decode_panels(self.read_attached(UI_PANELS_SIZE, address))
        except OSError, ValueError:
            return False
        return any(flags[name] for name in self.names)


class InputModeByte(LiveMemory):
    """Whether the game is in controller mode right now (native/layout.py CONTROLLER_MODE_RVA)."""

    def reading(self, live) -> bool:
        """`live`: (pid, address of the byte), or None. Unreadable or not 0/1 counts as keyboard and mouse."""
        if not live:
            return False
        pid, address = live
        if not self.attach(pid):
            return False
        try:
            return self.read_attached(1, address) == b'\x01'
        except OSError:
            return False


def mode_source(widgets):
    """(pid, address of the input mode byte) from the 'panels' widget, or None."""
    panels = next((w.payload for w in widgets if w.kind == 'panels'), None)
    if not panels or not panels.get('live') or panels.get('controller') is None:
        return None
    return panels['live'][0], panels['controller']


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


def map_card_of(boxes) -> dict | None:
    """The level map card's own dict (levels/map_card.py MapCard payload 'map'), or None."""
    for widget, _ in boxes:
        card = widget.payload.get('map') if widget.kind == 'guide' and isinstance(widget.payload, dict) else None
        if isinstance(card, dict) and isinstance(card.get('map'), dict):
            return card['map']
    return None


def follow(boxes, ground, moved=None):
    """`boxes` with the ground widget's payload replaced by its live one (None = unchanged), and
    the map card's player moved with it: a map that keeps the player in the middle
    (hud/map.py LOCAL_SCALE) would otherwise scroll in half-second steps. `moved` (hud/dots.py
    `LiveDots.frame`): every monster dot where it is now, the dead and gone dropped, the new added."""
    if ground is None and moved is None:
        return boxes
    return [(Widget(w.id, w.kind, w.slot, _followed(w, ground, moved)), box) for w, box in boxes]


def _followed(widget, ground, moved):
    if widget.kind == 'ground':
        return placed_marks(ground or widget.payload, moved)
    card = widget.payload.get('map') if widget.kind == 'guide' and isinstance(widget.payload, dict) else None
    if not (isinstance(card, dict) and isinstance(card.get('map'), dict)):
        return widget.payload
    found = card['map']
    player = ground['player'] if ground else (moved or {}).get('player') or found['player']
    pois = placed(found.get('pois', ()), moved, 4, (moved or {}).get('extra', ()))
    return {**widget.payload, 'map': {**card, 'map': {**found, 'player': list(player), 'pois': pois}}}


def placed(rows, moved, path_at: int, extra=()) -> list:
    """`rows` (map pois, or ground marks: [label,] kind, x, y, path, unit, id) with each unit's position now
    (`moved`), those gone dropped, `extra` added. `path_at`: the index of the path, after x and y."""
    if not moved:
        return list(rows)
    dots, out, uid_at = moved['dots'], [], path_at + 2
    for row in rows:
        if len(row) > uid_at and row[uid_at] in dots:
            where = dots[row[uid_at]]
            if where is None:
                continue
            row = [*row[: path_at - 2], *where, *row[path_at:]]
        out.append(row)
    return out + [list(row) for row in extra]


def placed_marks(ground, moved):
    """The ground payload with its unit marks placed (`placed`), the new monsters of the ground's kinds added."""
    if not moved or ground is None:
        return ground
    extra = [row[1:] for row in moved.get('extra', ()) if row[1] in HUD.ground.kinds]
    return {**ground, 'marks': placed(ground['marks'], moved, 3, extra)}
