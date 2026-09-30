"""Map ↔ screen geometry shared by arrows and the map card.

World units are player path coordinates; Room2 tiles are TILE_UNITS world units. The screen
is isometric: +x runs down-right, +y down-left. Compass words use map axes (north = -y),
the axes preset doorways are named by; the user confirmed "north" for the Arcane arm at -y.
"""

import math
from dataclasses import dataclass

from inventory_tracking.levels.model import Location, Poi, Room
from inventory_tracking.native.layout import TILE_UNITS


# Screen-space arrows, counter-clockwise from right in 45° steps.
ARROWS = ('→', '↗', '↑', '↖', '←', '↙', '↓', '↘')


def arrow(dx: float, dy: float) -> str:
    screen_x, screen_up = dx - dy, -(dx + dy) / 2
    return ARROWS[round(math.degrees(math.atan2(screen_up, screen_x)) / 45) % 8]


def compass(dx: float, dy: float) -> str:
    if abs(dy) >= abs(dx):
        return 'north' if dy < 0 else 'south'
    return 'east' if dx > 0 else 'west'


@dataclass(frozen=True)
class Pointer:
    label: str
    room: Room | None
    dx: float
    dy: float
    here: bool = False  # the player stands in the POI's room: no direction to give
    kind: str = 'target'  # Poi kind; picks the row colour (osd/level_map.KIND_TONES)

    @property
    def arrow(self) -> str:
        return arrow(self.dx, self.dy)

    @property
    def compass(self) -> str:
        return compass(self.dx, self.dy)

    @property
    def distance(self) -> float:
        """World units; ~1 per yard, a screen is roughly 40 wide."""
        return math.hypot(self.dx, self.dy)


def pointer(poi: Poi, location: Location) -> Pointer:
    room = poi.room
    cx, cy = room.center
    tx, ty = location.x / TILE_UNITS, location.y / TILE_UNITS
    here = room.x <= tx < room.x + room.width and room.y <= ty < room.y + room.height
    return Pointer(poi.label, room, cx - location.x, cy - location.y, here, poi.kind)
