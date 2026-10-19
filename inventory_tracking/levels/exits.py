"""Ways out every level has, with or without a handler: its warps and the levels it touches.

Warps: a DS1 warp's link slot names the level behind it (levels.txt Vis0..7), marked on the warp itself.
Borders: a level joined without a warp shows as rooms whose neighbours belong to it, marked at the room
nearest their middle. A handler's own marks win and are not repeated; kind is guessed from area numbers
(lower = the way back). Open passages (presets.open_passage) are walked, not clicked: `through` gives the
place PASSAGE_PAST inside the next level. Towns mark only their way to the wilderness (user, 2026-10-06)
and their waypoint (user, 2026-10-07). Rationale and evidence: levels/history/exits.md.
"""

import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import replace

from inventory_tracking.levels.handler import Handler, instances
from inventory_tracking.levels.model import Guidance, LevelSnapshot, Poi, Room
from inventory_tracking.levels.presets import display_name, linked_level, open_passage, warp_spots, waypoint_spot
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
    """One POI per (preset instance, level behind its warps), on the warp tiles; ways on before ways back,
    so a level without a handler leads with its next level."""
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
    return tuple(sorted(pois, key=lambda poi: poi.kind == 'previous'))


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


# Tiles past the level's edge an open passage's far place lies; the level changes at the rooms' edge
# (River of Flame bridge, take 20261014T190527Z-107).
PASSAGE_PAST = 1.0
INWARD_STEP = 0.25  # tiles: the walk along a border room toward its edge, when the mark is inside the level
INWARD_LIMIT = 200.0  # tiles: no room is that long


def outward(rooms: tuple[Room, ...], to: int) -> tuple[int, int] | None:
    """The axis direction from the middle of the level's rooms to the middle of those touching `to`; None
    while no room is known to touch it."""
    edge = [room for room in rooms if to in room.leads_to]
    if not edge:
        return None

    def middle(found: list[Room] | tuple[Room, ...]) -> tuple[float, float]:
        return (
            sum(room.x + room.width / 2 for room in found) / len(found),
            sum(room.y + room.height / 2 for room in found) / len(found),
        )

    (ex, ey), (lx, ly) = middle(edge), middle(rooms)
    dx, dy = ex - lx, ey - ly
    if abs(dx) >= abs(dy):
        return (1 if dx > 0 else -1, 0)
    return (0, 1 if dy > 0 else -1)


def in_rooms(rooms: Iterable[Room], point: tuple[float, float]) -> bool:
    """Whether `point` (tiles) lies in one of `rooms`."""
    x, y = point
    return any(room.x <= x < room.x + room.width and room.y <= y < room.y + room.height for room in rooms)


def through(rooms: tuple[Room, ...], mark: tuple[float, float], to: int) -> tuple[float, float] | None:
    """The far place (tiles) of an open passage into `to` marked at `mark`: PASSAGE_PAST past the rooms' edge.
    A mark beyond the rooms is approached from their nearest point; one inside walks `outward` to the edge.
    None: no rooms, or a mark inside and no room known to touch `to`."""
    if not rooms:
        return None
    if not in_rooms(rooms, mark):

        def nearest(room: Room) -> tuple[float, float]:
            return (
                min(max(mark[0], room.x), room.x + room.width),
                min(max(mark[1], room.y), room.y + room.height),
            )

        edge = min((nearest(room) for room in rooms), key=lambda point: math.dist(point, mark))
        gap = math.dist(edge, mark)
        if gap > 1e-6:
            dx, dy = (mark[0] - edge[0]) / gap, (mark[1] - edge[1]) / gap
            return (edge[0] + dx * PASSAGE_PAST, edge[1] + dy * PASSAGE_PAST)
    way = outward(rooms, to)
    if way is None:
        return None
    x, y, walked = *mark, 0.0
    while in_rooms(rooms, (x, y)) and walked < INWARD_LIMIT:
        x, y, walked = x + way[0] * INWARD_STEP, y + way[1] * INWARD_STEP, walked + INWARD_STEP
    if walked >= INWARD_LIMIT:
        return None
    return (x + way[0] * PASSAGE_PAST, y + way[1] * PASSAGE_PAST)


def passage_of(area: int, rooms: tuple[Room, ...], poi: Poi, mark: tuple[float, float]) -> tuple[float, float] | None:
    """`through` for a way out that is an open passage (presets.open_passage); None for a warp, an object
    (`Poi.use`), a mark naming no level, or no way out."""
    if poi.kind not in WAYS_OUT or poi.area is None or poi.use or not open_passage(area, poi.area):
        return None
    return through(rooms, mark, poi.area)


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
