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

Open passages. A way out with no warp behind it (presets.open_passage: levels.txt, or a border) is crossed by
walking, not clicked: the River of Flame's bridge into the Chaos Sanctuary, the Outer Cloister's gate into the
Barracks, every border. Its mark is where the arrow points; `through` gives the place a walk goes to so that the
level changes, PASSAGE_PAST inside the next level (macros/goals.py `route_goal`, the level run's way through).

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
    """One POI per (preset instance, level behind its warps), on the warp tiles; the ways on before
    the ways back, so a level without a handler leads with its next level (the Forgotten Tower's one
    preset holds both: slot 0 Black Marsh, slot 1 Tower Cellar 1)."""
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


# Tiles past the level's edge an open passage's far place lies: one tile (5 units), inside the next level. The River
# of Flame's bridge on 2026-10-14 (takes 20261014T190527Z-107 then 190924Z-108, 192208Z-107 then 192338Z-108): the
# level changed at the rooms' edge (tile row 1120: y 5600.3 in the River, 5599.6 in the Sanctuary a frame later), on
# walks that went on to y 5595.9, a tile in.
PASSAGE_PAST = 1.0
INWARD_STEP = 0.25  # tiles: the walk along a border room toward its edge, when the mark is inside the level
INWARD_LIMIT = 200.0  # tiles: no room is that long


def outward(rooms: tuple[Room, ...], to: int) -> tuple[int, int] | None:
    """The map direction from the level toward level `to`, which it touches without a door: from
    the middle of the level's rooms to the middle of those touching `to`, along the nearer axis.
    None while no room is known to touch it."""
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
    """The far place of an open passage into level `to` marked at `mark` (tiles), in tiles: PASSAGE_PAST past the
    edge of the level's `rooms`, along the passage. A mark beyond the rooms (a handler's mark on the far side: the
    River's bridge end) is crossed from the rooms' nearest point toward it; a mark inside them (a border's room)
    from it the way the level touches `to` (`outward`) to where its rooms end. None: no room, or the mark inside
    them and no room known to touch `to`."""
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
    """The far place (`through`, tiles) of a way out `poi` of level `area` marked at `mark` that is an open passage
    (presets.open_passage); None for a warp, an object (a portal: `Poi.use`), a mark that names no level, or a way
    out that is not one (a waypoint, a boss)."""
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
