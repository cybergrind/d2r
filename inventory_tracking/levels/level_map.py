"""Build the OSD map card for a level: every Room2, the player, the handler's POIs and a route, in tiles."""

import re
from collections.abc import Iterable

from inventory_tracking.levels.model import LevelSnapshot, Location, Poi, Room, Walkable
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.route import route
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.osd.level_map import MapCard, MapPoi


# Outdoor level edges (fences, cliffs, ravines): 'Border' in every act's names, e.g. 'Act 1 - Wild
# Border 3', 'Act 3 - Slums Border NE', 'Act 5 - Barricade Cliff Border 2 Snow' (120 presets).
EDGE = re.compile(r'\bBorder\b')


def room_kind(room: Room) -> str:
    return 'edge' if EDGE.search(preset_name(room.preset)) else 'room'


def centre(room: Room) -> tuple[float, float]:
    return room.x + room.width / 2, room.y + room.height / 2


def build_map(
    snapshot: LevelSnapshot,
    pois: Iterable[Poi],
    location: Location | None = None,
    walkable: Iterable[Walkable] = (),
    *,
    visited: set | None = None,
    dots: Iterable[MapPoi] = (),
    pid: int | None = None,
    whole: bool = False,
) -> MapCard:
    """`location` overrides the snapshot's player position (live dot while the card is shown).
    `visited` (bounds of the rooms ever loaded, terror/tracker.py) shades the rooms: the others
    are drawn dimmer. `dots` are extra live marks in tiles (monsters, a Herald).
    `pid` (the game process) lets the HUD follow the player between cards when the location has its path.
    `whole` draws a big level whole instead of the part around the player (osd/level_map.py).

    The route leads to the first POI reachable through doorways (mazes only; levels/route.py).
    """
    where = location or snapshot.location
    player = (where.x / TILE_UNITS, where.y / TILE_UNITS)
    pois = tuple(pois)
    marks = tuple(MapPoi(p.label, p.kind, *(p.spot or centre(p.room))) for p in pois)
    path: tuple[tuple[float, float], ...] = ()
    for poi, mark in zip(pois, marks, strict=True):
        rooms = route(snapshot.rooms, player, poi.room)
        if rooms:
            path = (player, *(centre(room) for room in rooms[1:-1]), (mark.x, mark.y))
            break
    return MapCard(
        rooms=tuple((r.x, r.y, r.width, r.height) for r in snapshot.rooms),
        player=player,
        pois=(*marks, *dots),
        route=path,
        room_kinds=tuple(room_kind(r) for r in snapshot.rooms),
        walkable=tuple((g.x, g.y, g.width, g.height, g.cells) for g in walkable),
        visited=tuple(int((r.x, r.y, r.width, r.height) in visited) for r in snapshot.rooms) if visited else (),
        live=(pid, where.path) if pid and where.path else None,
        whole=whole,
    )
