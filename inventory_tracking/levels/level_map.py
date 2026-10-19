"""Build the OSD map card for a level: every Room2, the player, the handler's POIs and a teleport route, in tiles."""

import re
from collections.abc import Iterable

from inventory_tracking.levels.map_card import MapCard, MapPoi
from inventory_tracking.levels.model import LevelSnapshot, Location, Poi, Room, Walkable
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.route import route
from inventory_tracking.native.layout import TILE_UNITS


# Outdoor level edges (fences, cliffs, ravines): 'Border' in every act's preset names (120 presets).
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
    toward: tuple[float, float] | None = None,
    routed: bool = True,
    units: tuple[int, int] | None = None,
) -> MapCard:
    """`location` overrides the snapshot's position; `visited` (room bounds ever loaded) shades rooms; `dots` are
    live marks in tiles; `pid` lets the HUD follow the player; `whole` draws a big level whole; `units` is for
    the HUD's own monster walk (hud/live.py). The route goes to `toward` (tiles) or the first reachable POI
    (levels/route.py); none when not `routed`."""
    where = location or snapshot.location
    player = (where.x / TILE_UNITS, where.y / TILE_UNITS)
    pois = tuple(pois)
    marks = tuple(MapPoi(p.label, p.kind, *(p.spot or centre(p.room))) for p in pois)
    path: tuple[tuple[float, float], ...] = ()
    ends = [toward] if toward is not None else [(mark.x, mark.y) for mark in marks] if routed else []
    for end in ends:
        hops = route(snapshot.rooms, player, end)
        if hops:
            path = tuple(hops)
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
        units=units,
    )
