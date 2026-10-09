"""Ways out every level has, with or without a handler: its warps and the levels it touches.

Warps. A preset's DS1 file numbers each warp with the level's link slot (levels/ds1.py), and
levels.txt names the level behind that slot (Vis0..7, bundled as LEVEL_LINKS). So a room whose
preset has warp tiles is a way out to a known level, marked on the warp itself. Checked on
2026-10-05 against the saved evidence: in all 1152 warp rooms whose far side was readable
(Room.leads_to), the slot's level was the one read from memory.

Borders. Levels joined without a warp or an open border gap (Rogue Encampment, Monastery Gate,
the Act 2 deserts, the Outer Cloister behind the Barracks) show only as rooms whose neighbours
belong to the other level. Such a level is marked at the room nearest the middle of those rooms,
once any of them has been read (levels/session.py keeps them for the game).

A handler's own marks win: a way out it already marks (by kind, or an entrance it keeps as a side
trip with PoiSpec.warp) is not repeated, so its label and colour stand; a level its border gaps
are waiting to name (ExitsHandler.exits) is left to them. The kind is a guess from the area
numbers, which grow along the story: a lower-numbered level is the way back.

Towns. A town marks only its way out to the wilderness (user, 2026-10-06): Lut Gholein's sewer
ladders and the Harem were noise, its gate to the Rocky Waste is in one of two places. And its
waypoint (user, 2026-10-07), an object the town's DS1 file places (presets.waypoint_spot): known
on entry, before the game streams the object (the Rogue Encampment has four layouts).
"""

import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import replace

from inventory_tracking.levels.handler import Handler, instances
from inventory_tracking.levels.model import Guidance, LevelSnapshot, Poi, Room
from inventory_tracking.levels.presets import display_name, linked_level, warp_spots, waypoint_spot
from inventory_tracking.levels.spots import WAYS_OUT


# Town -> the levels worth an arrow from it: the first wilderness level of its act.
TOWN_WAYS_OUT = {1: {2}, 40: {41}, 75: {76}, 103: {104}, 109: {110}}


def origin(room: Room) -> tuple[int, int]:
    """Where the room's preset starts, in tiles: the whole preset's corner for a chunk."""
    return (room.block or (room.x, room.y))[:2]


def short_name(area: int) -> str:
    return display_name(area).replace(' Level ', ' ')


def kind_for(area: int, target: int) -> str:
    return 'previous' if target < area else 'stairs'


def warp_exits(snapshot: LevelSnapshot) -> tuple[Poi, ...]:
    """One POI per (preset instance, level behind its warps), on the warp tiles."""
    area = snapshot.location.area_id
    pois = []
    for room, _ in instances(snapshot.rooms):
        spots = defaultdict(list)
        for slot, spot in sorted(warp_spots(room.preset, room.variant).items()):
            target = linked_level(area, slot)
            if target is not None:
                spots[target].append(spot)
        x, y = origin(room)
        for target, found in spots.items():
            spot = (x + sum(s[0] for s in found) / len(found), y + sum(s[1] for s in found) / len(found))
            pois.append(Poi(short_name(target), room, kind_for(area, target), spot, target))
    return tuple(pois)


def border_exits(snapshot: LevelSnapshot, skip: Iterable[int] = ()) -> tuple[Poi, ...]:
    """One POI per neighbouring level not in `skip`: the room nearest the middle of those touching it."""
    area, skip = snapshot.location.area_id, set(skip)
    touching: dict[int, list[Room]] = defaultdict(list)
    for room in snapshot.rooms:
        for target in room.leads_to:
            if target not in skip:
                touching[target].append(room)
    pois = []
    for target, rooms in touching.items():
        x = sum(room.x + room.width / 2 for room in rooms) / len(rooms)
        y = sum(room.y + room.height / 2 for room in rooms) / len(rooms)
        nearest = min(rooms, key=lambda r: math.dist((r.x + r.width / 2, r.y + r.height / 2), (x, y)))
        pois.append(Poi(short_name(target), nearest, kind_for(area, target), area=target))
    return tuple(pois)


def preset_waypoints(snapshot: LevelSnapshot) -> tuple[Poi, ...]:
    """One 'waypoint' POI per preset instance whose DS1 file places a waypoint, on the waypoint."""
    pois = []
    for room, _ in instances(snapshot.rooms):
        spot = waypoint_spot(room.preset, room.variant)
        if spot is not None:
            x, y = origin(room)
            pois.append(Poi('Waypoint', room, 'waypoint', (x + spot[0], y + spot[1])))
    return tuple(pois)


def marks_a_way_out(poi: Poi) -> bool:
    return poi.kind in WAYS_OUT or poi.spot is not None


def with_exits(guidance: Guidance, snapshot: LevelSnapshot, pending: Iterable[int] = ()) -> Guidance:
    """`guidance` plus the ways out it does not mark yet; `pending` levels are left to the handler."""
    ways_out = [poi for poi in guidance.pois if marks_a_way_out(poi)]
    marked = {(poi.room.preset, origin(poi.room)) for poi in ways_out}
    extra = [poi for poi in warp_exits(snapshot) if (poi.room.preset, origin(poi.room)) not in marked]
    marked |= {(poi.room.preset, origin(poi.room)) for poi in extra}
    reached = {poi.area for poi in (*ways_out, *extra) if poi.area is not None} | set(pending)
    reached |= {a for room in snapshot.rooms if (room.preset, origin(room)) in marked for a in room.leads_to}
    labels = {poi.label for poi in guidance.pois}
    extra += [poi for poi in border_exits(snapshot, reached) if poi.label not in labels]
    return replace(guidance, pois=(*guidance.pois, *extra)) if extra else guidance


def guide_level(handler: Handler | None, snapshot: LevelSnapshot) -> Guidance:
    """Everything to mark in a level: the handler's POIs (none without a handler) and the ways out."""
    guidance = handler.guide(snapshot) if handler is not None else Guidance()
    guidance = with_exits(guidance, snapshot, (exit_.area for exit_ in getattr(handler, 'exits', ())))
    wanted = TOWN_WAYS_OUT.get(snapshot.location.area_id)
    if wanted is None:
        return guidance
    ways_out = tuple(poi for poi in guidance.pois if poi.area in wanted)
    return replace(guidance, pois=(*ways_out, *preset_waypoints(snapshot)))
