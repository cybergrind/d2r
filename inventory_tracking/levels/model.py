"""Level data the framework passes around: where the player is and the level's rooms."""

import base64
import binascii
import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import SupportsInt

from inventory_tracking.native.layout import TILE_UNITS


# objects.txt ids of the objects a mark may name for the step to click (`Poi.use`).
PORTAL = 60  # PortalPermanent: the red portal that stays (the Cairn Stones' to Tristram)
# TownPortal (macros/portal.py), no mark's; clickable in mode 2 only (objects.txt Selectable2)
TOWN_PORTAL = 59
WIRTS_BODY = 268
# Objects the map files place at a preset's spot, which a mark may sit on (`PoiSpec.thing`;
# levels/data/preset_objects.json). Ids checked against d2data objects.json on 2026-10-12.
SUPER_CHEST = 397  # ConsolationChest, the "sparkly chest"
SEALS = (392, 393, 394, 395, 396)  # DiabloSeal1-5: arm E holds 392 and 393, arm N 394, arm W 395 and 396
ARCANE_PORTAL = 298
MEPHISTO_BRIDGE = 341
HELL_GATE = 342  # the red portal to act 4 on Mephisto's bridge
CUBE_CHEST, SCROLL_CHEST, STAFF_CHEST = 354, 355, 356  # Horadric Cube, Horadric Scroll, Staff of Kings
SEWER_STAIRS, SEWER_LEVER = 366, 367  # Kurast Sewers 1
HEART_CHEST, BRAIN_CHEST, EYE_CHEST = 405, 406, 407  # Khalim's
FROZEN_ANYA = 460  # DrehyaOutsideTown
# SevenTombsReceptacle, the true tomb's Orifice (objpreset act 2 index 126 in TombNTalrasha.ds1 and its three turns),
# and DurielPortal ("Duriel's Lair"), the portal the game spawns 13 units west and 3 south of it once the Horadric
# Staff quest is done (D2MOO A2Q6.cpp ACT2Q6_Timer_UpdateObjects; objects.txt, checked against d2data 2026-10-21)
ORIFICE, DURIEL_PORTAL = 152, 100
ANCIENTS_ALTAR, ANCIENTS_GATEWAY = 546, 547
THRONE_PORTAL = 563  # FinalPortal, to the Worldstone Chamber
# objpreset.txt `PlaceUniqueChest`: a spot where the game rolls a chest class at level creation (JungleChest 181 or
# 183 in Lower Kurast, lower-kurast-plan.md), so no objects.txt row; an id above every row (586 the last). The mark
# opens whatever container is there (the player, 2026-10-16).
UNIQUE_CHEST = 1000
PLACEHOLDERS = {'PlaceUniqueChest': UNIQUE_CHEST}  # objpreset ObjectClass -> the id it is marked by
# Placed objects the teleport step clicks at their mark (macros/teleport.py USES), carried as `Poi.use`. The Throne's
# portal too since 2026-10-20 (the player, ~09:33: "tz leveling should do baal and trone fight"): objects.txt gives it
# no click box, so it is taken by its picture, as the player clicked it at 00:18 on 2026-10-11
CLICKED = frozenset((SUPER_CHEST, *SEALS, HELL_GATE, ARCANE_PORTAL, UNIQUE_CHEST, THRONE_PORTAL))
MARKABLE = frozenset((
    SUPER_CHEST, *SEALS, ARCANE_PORTAL, MEPHISTO_BRIDGE, HELL_GATE, CUBE_CHEST, SCROLL_CHEST, STAFF_CHEST,
    SEWER_STAIRS, SEWER_LEVER, HEART_CHEST, BRAIN_CHEST, EYE_CHEST, FROZEN_ANYA, ANCIENTS_ALTAR,
    ANCIENTS_GATEWAY, THRONE_PORTAL, UNIQUE_CHEST, ORIFICE,
))  # fmt: skip


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
        preset, x, y, width, height, variant = row[:6]
        block = None if row[6] is None else (row[6], row[7], row[8], row[9])
        return cls(preset, x, y, width, height, variant, block, tuple(row[10]) if len(row) > 10 else ())

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


def pack_masks(values: Iterable[SupportsInt]) -> str:
    """Raw u16 collision masks, row by row -> base64 (little-endian u16 each)."""
    data = b''.join(int(value).to_bytes(2, 'little') for value in values)
    return base64.b64encode(data).decode() if data else ''


@lru_cache(maxsize=4096)
def unpack_masks(masks: str, count: int) -> tuple[int, ...] | None:
    """Packed masks -> one u16 per sub-tile; None when absent or not `count` of them."""
    try:
        raw = base64.b64decode(masks, validate=True)
    except binascii.Error, ValueError:
        return None
    if not count or len(raw) != count * 2:
        return None
    return tuple(int.from_bytes(raw[i : i + 2], 'little') for i in range(0, len(raw), 2))


def pack_tiles(tiles: str, width: int) -> str:
    """'1'/'0' per tile, row by row -> packed sub-tiles, each tile filling its 5x5 (old wall library)."""
    rows = (tiles[start : start + width] for start in range(0, len(tiles), width))
    return pack_cells(''.join(''.join(cell * TILE_UNITS for cell in row) * TILE_UNITS for row in rows))


@dataclass(frozen=True)
class Walkable:
    """A loaded room's walkable sub-tiles: bounds in tiles; `cells` one bit per sub-tile (5x5 a tile, so thin
    walls survive), row by row, 1 = walkable (`pack_cells`)."""

    x: int
    y: int
    width: int
    height: int
    cells: str
    # 1 = a missile flies: the mask's block-missile bit (native/layout.py); '' unknown (old level maps).
    flight: str = ''
    # Raw u16 collision masks per sub-tile (`pack_masks`), for research (combat/plan.md); '' unknown.
    masks: str = ''


# A tile's decoded grid: (grid, walk bits, flight bits (None when absent/malformed), sub-tile columns, left, top).
type _Tile = tuple[Walkable, str | None, str | None, int, int, int]
# Decoded tables kept: the loaded-room set grows as rooms load, so a game's last few suffice (1-2 MB each for
# Chaos). Never changed once built, so threads share them.
TABLES = 16


@lru_cache(maxsize=TABLES)
def _tiles(grids: tuple[Walkable, ...]) -> dict[tuple[int, int], _Tile]:
    """The decoded grid of each tile, built once per set of grids; a later grid wins an overlapped tile."""
    tiles: dict[tuple[int, int], _Tile] = {}
    for grid in grids:
        columns, count = grid.width * TILE_UNITS, grid.width * grid.height * TILE_UNITS * TILE_UNITS
        tile = (
            grid,
            unpack_cells(grid.cells, count),
            unpack_cells(grid.flight, count),
            columns,
            grid.x * TILE_UNITS,
            grid.y * TILE_UNITS,
        )
        for x in range(grid.x, grid.x + grid.width):
            for y in range(grid.y, grid.y + grid.height):
                tiles[x, y] = tile
    return tiles


class Ground:
    """Walkability of world points (one sub-tile = one world unit) from loaded rooms' grids; None where no
    grid covers the point. Cheap: decoded tables are shared (`_tiles`)."""

    def __init__(self, grids: Iterable[Walkable]) -> None:
        self.grids = tuple(grids)
        self.tiles = _tiles(self.grids)

    def __len__(self) -> int:
        return len(self.grids)

    def walkable(self, x: float, y: float) -> bool | None:
        tile = self.tiles.get((math.floor(x / TILE_UNITS), math.floor(y / TILE_UNITS)))
        if tile is None:
            return None
        _, cells, _, columns, left, top = tile
        if cells is None:
            return None
        return cells[int(y - top) * columns + int(x - left)] == '1'

    def flyable(self, x: float, y: float) -> bool | None:
        """Whether a missile flies through the sub-tile at a world point; None without a flight layer."""
        tile = self.tiles.get((math.floor(x / TILE_UNITS), math.floor(y / TILE_UNITS)))
        if tile is None:
            return None
        _, _, flight, columns, left, top = tile
        if flight is None:
            return None
        return flight[int(y - top) * columns + int(x - left)] == '1'

    def mask(self, x: float, y: float) -> int | None:
        """The raw collision mask of the sub-tile at a world point; None where no grid has masks."""
        tile = self.tiles.get((math.floor(x / TILE_UNITS), math.floor(y / TILE_UNITS)))
        if tile is None:
            return None
        grid, _, _, columns, left, top = tile
        values = unpack_masks(grid.masks, columns * grid.height * TILE_UNITS)
        if values is None:
            return None
        return values[int(y - top) * columns + int(x - left)]


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
    use: int = 0  # objects.txt id of an object near the mark to click: a portal, a body (PoiSpec.use)
    entrance: bool = False  # a side-trip entrance (PoiSpec.warp): a door to walk into whatever its kind

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
    # Labels known to have no mark here (an `each` spec, every layout read, none placing it): their stage is done.
    absent: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Lead:
    """The mark the level card leads with (routes/progress.py); `area`: the level it leads into, if a way on."""

    label: str
    area: int | None = None
    skip: frozenset[tuple[float, float]] = frozenset()  # places (tiles) of marks with the label done with


@dataclass(frozen=True)
class Level:
    """The current level as the level guide knows it, for a macro that picks its own mark (macros/hunt.py)."""

    area: int
    rooms: tuple[Room, ...]
    ground: tuple[Walkable, ...] = ()  # walkable sub-tiles of the loaded rooms, when the walls were read


@dataclass(frozen=True)
class Target:
    """The level card's first mark, for a macro that moves the character toward it (macros/teleport.py)."""

    area: int
    rooms: tuple[Room, ...]
    point: tuple[float, float]  # tiles
    label: str
    kind: str
    warp: bool = False  # the point is the warp tile itself (levels/spots.py): a door to walk into
    ground: tuple[Walkable, ...] = ()  # walkable sub-tiles of the loaded rooms, when the walls were read
    use: int = 0  # objects.txt id of an object near the point the step clicks: a portal, a body (macros/teleport.py)
    # An open passage's far place, in tiles (levels/exits.py `through`): walking there crosses into the next level
    # with no warp (River of Flame to Chaos Sanctuary). None: a warp, an object or no way out.
    passage: tuple[float, float] | None = None
    into: int | None = None  # the level `passage` leads into (macros/pursuit.py `carried`)
