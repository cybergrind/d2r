"""Put a POI on the warp itself instead of its room's centre.

Warp tiles come from the preset's DS1 file (data/preset_warps.json), from the preset origin (`Room.block`
for chunked presets); arriving by stairs lands within a tile of the way-back warp (2026-10-03). A preset with
several warps keeps the room centre. Only ways out move, plus side-trip entrances that opt in (PoiSpec.warp).
A waypoint is an object: `on_waypoint` moves it onto the object once streamed (levels/memory.nearby_waypoints).
"""

from dataclasses import replace

from inventory_tracking.levels.model import Poi
from inventory_tracking.levels.presets import warp_spots


WAYS_OUT = frozenset(('stairs', 'previous', 'exit'))


def pinpoint(poi: Poi, *, warp: bool = False) -> Poi:
    """`warp`: the POI is an entrance whatever its kind (PoiSpec.warp, e.g. Anya's Frozen River)."""
    if poi.kind not in WAYS_OUT and not warp:
        return poi
    room = poi.room
    spots = warp_spots(room.preset, room.variant)
    if len(spots) != 1:
        return poi
    ((x, y),) = spots.values()
    origin_x, origin_y, _w, _h = room.block or (room.x, room.y, room.width, room.height)
    return replace(poi, spot=(origin_x + x, origin_y + y), entrance=warp)


def on_waypoint(poi: Poi, waypoints) -> Poi:
    """A waypoint POI moved onto the waypoint object seen in its room (`waypoints`: tiles)."""
    if poi.kind != 'waypoint':
        return poi
    room = poi.room
    for x, y in waypoints:
        if room.x <= x < room.x + room.width and room.y <= y < room.y + room.height:
            return replace(poi, spot=(x, y))
    return poi
