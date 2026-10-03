"""Put a POI on the warp itself instead of its room's centre.

A preset's DS1 file places its warp tiles (levels/ds1.py, bundled as data/preset_warps.json),
in tiles from the preset origin: the whole preset's bounds (`Room.block`) for chunked presets,
the room itself otherwise. Checked on 2026-10-03 against the entry fixtures: arriving by stairs
puts the player within a tile of the way-back warp (Jail 2 and 3, Catacombs 3, Worldstone Keep 3).
A preset with several warps (Graveyard, Harem, Act 3 Bridge, Baal Entrance) keeps the room
centre: which slot a POI means is not known here. Only ways out move: bosses, chests and
waypoints are objects, not warps, and keep their place even in a preset that also holds a warp
(Nihlathak's 'Temple Final Room' holds the way back; the handler puts him across it). An
entrance kept as a side trip ('target' colour: Frozen River, the Kurast temples) opts in with
PoiSpec.warp.
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
    return replace(poi, spot=(origin_x + x, origin_y + y))
