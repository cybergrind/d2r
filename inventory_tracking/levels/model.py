"""Level data the framework passes around: where the player is and the level's rooms."""

from dataclasses import dataclass, field

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


@dataclass(frozen=True)
class Walkable:
    """A loaded room's walkable tiles: `cells` is '1' (walkable) / '0' per tile, row by row."""

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
