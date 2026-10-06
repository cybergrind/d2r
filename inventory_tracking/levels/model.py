"""Level data the framework passes around: where the player is and the level's rooms."""

import base64
import binascii
from dataclasses import dataclass, field
from functools import lru_cache

from inventory_tracking.native.layout import TILE_UNITS


@dataclass(frozen=True)
class Location:
    area_id: int
    level: int
    x: int
    y: int
    # Address of the player's dynamic path, where the HUD re-reads the position (hud/live.py); 0 = unknown.
    path: int = field(default=0, compare=False)


@dataclass(frozen=True)
class Room:
    """One Room2. Large presets are split into 8x8 chunks sharing `block`, the whole preset's bounds."""

    preset: int
    x: int
    y: int
    width: int
    height: int
    variant: int | None = None  # DS1 file index of the preset (lvlprest File1.. order), when readable
    block: tuple[int, int, int, int] | None = None  # whole preset x, y, w, h in tiles, when readable
    leads_to: tuple[int, ...] = ()  # areas of other levels among its Room2 neighbours (level exits)

    def row(self) -> list:
        """Evidence/fixture row: [preset, x, y, w, h] plus [variant, bx, by, bw, bh] when known,
        plus [[areas]] when the room touches other levels."""
        base = [self.preset, self.x, self.y, self.width, self.height]
        if self.block is None and not self.leads_to:
            return base
        extended = [*base, self.variant, *(self.block or (None,) * 4)]
        return [*extended, list(self.leads_to)] if self.leads_to else extended

    @classmethod
    def from_row(cls, row) -> Room:
        if len(row) == 5:
            return cls(*row)
        block = None if row[6] is None else (row[6], row[7], row[8], row[9])
        return cls(*row[:5], row[5], block, tuple(row[10]) if len(row) > 10 else ())

    @property
    def center(self) -> tuple[float, float]:
        """World coordinates, the unit of player path x/y."""
        return (self.x + self.width / 2) * TILE_UNITS, (self.y + self.height / 2) * TILE_UNITS


def pack_cells(bits: str) -> str:
    """'1' (walkable) / '0' per sub-tile, row by row -> base64 of the bits, first sub-tile in the top bit."""
    padded = bits + '0' * (-len(bits) % 8)
    return base64.b64encode(int(padded, 2).to_bytes(len(padded) // 8, 'big')).decode() if bits else ''


@lru_cache(maxsize=4096)
def unpack_cells(cells: str, count: int) -> str | None:
    """Packed cells -> '1'/'0' per sub-tile; None when they are not `count` sub-tiles."""
    try:
        raw = base64.b64decode(cells, validate=True)
    except binascii.Error, ValueError:
        return None
    if not count or len(raw) != (count + 7) // 8:
        return None
    return f'{int.from_bytes(raw, "big"):0{len(raw) * 8}b}'[:count]


def pack_tiles(tiles: str, width: int) -> str:
    """'1'/'0' per tile, row by row -> packed sub-tiles, each tile filling its 5x5 (old wall library)."""
    rows = (tiles[start : start + width] for start in range(0, len(tiles), width))
    return pack_cells(''.join(''.join(cell * TILE_UNITS for cell in row) * TILE_UNITS for row in rows))


@dataclass(frozen=True)
class Walkable:
    """A loaded room's walkable sub-tiles. The bounds are the room in tiles; `cells` holds one bit
    per sub-tile (5x5 a tile, so thin walls survive), row by row, 1 = walkable (`pack_cells`)."""

    x: int
    y: int
    width: int
    height: int
    cells: str


@dataclass(frozen=True)
class LevelSnapshot:
    """The player's location and every Room2 of the current level (read once per entry)."""

    location: Location
    rooms: tuple[Room, ...]


@dataclass(frozen=True)
class Poi:
    label: str
    room: Room
    kind: str  # 'stairs' (next level) | 'previous' | 'waypoint' | 'target' (boss, chest)
    spot: tuple[float, float] | None = None  # tiles: the warp itself (levels/spots.py); None = room centre
    area: int | None = None  # the level this way out leads to, when the rule that made it knows

    @property
    def point(self) -> tuple[float, float]:
        """Where the mark goes, in world units: the spot when known, else the room centre."""
        if self.spot is None:
            return self.room.center
        return self.spot[0] * TILE_UNITS, self.spot[1] * TILE_UNITS


@dataclass(frozen=True)
class Guidance:
    """What a handler found; the framework turns POIs into arrows/dots and problems into warnings."""

    pois: tuple[Poi, ...] = ()
    problems: tuple[str, ...] = ()
