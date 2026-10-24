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
from functools import lru_cache
from typing import TYPE_CHECKING

from inventory_tracking.levels.handler import Handler, instances
from inventory_tracking.levels.model import Ground, Guidance, LevelSnapshot, Poi, Room, Walkable
from inventory_tracking.levels.presets import (
    DISPLAY_NAMES,
    display_name,
    linked_level,
    open_passage,
    warp_spots,
    waypoint_spot,
)
from inventory_tracking.levels.spots import WAYS_OUT
from inventory_tracking.native.layout import TILE_UNITS


if TYPE_CHECKING:
    from inventory_tracking.levels.doors import Door


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
EDGE_SNAP = 24.0  # tiles (three rooms): how far along the level's edge a border mark goes to its open tile


# Axis directions in tiles: east, south, west, north
SIDES = ((1, 0), (0, 1), (-1, 0), (0, -1))


def covered(rooms: tuple[Room, ...]) -> frozenset[tuple[int, int]]:
    """The tiles the level's rooms cover."""
    return frozenset(
        (x, y)
        for room in rooms
        for x in range(room.x, room.x + room.width)
        for y in range(room.y, room.y + room.height)
    )


def open_on(tiles: frozenset[tuple[int, int]], room: Room, side: tuple[int, int]) -> bool:
    """Whether most of the tiles just past `room`'s `side` lie in none of the level's rooms (`tiles`)."""
    dx, dy = side
    if dx:
        x = room.x + room.width if dx > 0 else room.x - 1
        beyond = [(x, room.y + i) for i in range(room.height)]
    else:
        y = room.y + room.height if dy > 0 else room.y - 1
        beyond = [(room.x + i, y) for i in range(room.width)]
    return 2 * sum(cell not in tiles for cell in beyond) > len(beyond)


def box_gap(one: Room, other: Room) -> float:
    """Tiles between two rooms' boxes (0 when they touch or overlap)."""
    dx = max(other.x - (one.x + one.width), one.x - (other.x + other.width), 0)
    dy = max(other.y - (one.y + one.height), one.y - (other.y + other.height), 0)
    return math.hypot(dx, dy)


def foreign(rooms: tuple[Room, ...], to: int) -> list[Room]:
    """The rooms touching another level and not `to`: the edge of that level (a town's gate), not `to`'s."""
    return [room for room in rooms if room.leads_to and to not in room.leads_to]


@lru_cache(maxsize=16)
def facing(rooms: tuple[Room, ...], to: int) -> tuple[int, int] | None:
    """The side the level's rooms touching `to` are open on (no room of the level past them) the most, less the times
    the rooms near them touching other levels are open on it; None: no side wins alone (a tie, as the Cathedral's
    chunked preset into the Inner Cloister, take 20261017T210206Z-33, open east and west once each), or none is open.
    Outer Steppes into the Plains of Despair, 17:14:53 on 2026-10-20 (take 20261020T141450Z-104): the Plains south of
    three rooms beside the Fortress gate; the rooms' middles lay 27.9 west and 27.3 south of each other, the west won
    by 0.6 tiles, and the run walked back into the town (rca/2026-10-20/fortress-gate-passage-findings.md)."""
    edge = [room for room in rooms if to in room.leads_to]
    if not edge:
        return None
    tiles = covered(rooms)
    near = [room for room in foreign(rooms, to) if min(box_gap(room, each) for each in edge) <= EDGE_SNAP]
    score = {
        side: sum(open_on(tiles, room, side) for room in edge) - sum(open_on(tiles, room, side) for room in near)
        for side in SIDES
    }
    best = max(score.values())
    winners = [side for side, points in score.items() if points == best]
    return winners[0] if best > 0 and len(winners) == 1 else None


def outward(rooms: tuple[Room, ...], to: int, mark: tuple[float, float] | None = None) -> tuple[int, int] | None:
    """The side the level's rooms touching `to` are open on (`facing`); with no such side, the axis direction
    from the middle of the level's rooms to the middle of those touching `to`, or to `mark` while no room is known to
    touch it (a handler's mark: Upper Kurast's Kurast Causeway, 2026-10-20 01:36:23, was taken for a door and 'going
    through takes a press' looped until the game was left); None with neither."""

    def middle(found: list[Room] | tuple[Room, ...]) -> tuple[float, float]:
        return (
            sum(room.x + room.width / 2 for room in found) / len(found),
            sum(room.y + room.height / 2 for room in found) / len(found),
        )

    edge = [room for room in rooms if to in room.leads_to]
    if edge:
        ex, ey = middle(edge)
    elif mark is not None:
        ex, ey = mark
    else:
        return None
    lx, ly = middle(rooms)
    dx, dy = ex - lx, ey - ly
    if not edge and dx == dy == 0:
        return None  # a mark at the middle has no side
    side = facing(rooms, to)
    if side is not None:
        return side
    if abs(dx) >= abs(dy):
        return (1 if dx > 0 else -1, 0)
    return (0, 1 if dy > 0 else -1)


def in_rooms(rooms: Iterable[Room], point: tuple[float, float]) -> bool:
    """Whether `point` (tiles) lies in one of `rooms`."""
    x, y = point
    return any(room.x <= x < room.x + room.width and room.y <= y < room.y + room.height for room in rooms)


def footed(ground: Ground, tile: tuple[int, int]) -> bool:
    """Whether a hop lands on `tile`'s centre by the read grids: its sub-tile walkable and none a unit around known
    unwalkable (macros/teleport.py `footing`); False where no grid covers it."""
    x, y = (tile[0] + 0.5) * TILE_UNITS, (tile[1] + 0.5) * TILE_UNITS
    if ground.walkable(x, y) is not True:
        return False
    return all(ground.walkable(x + dx, y + dy) is not False for dx in (-1, 0, 1) for dy in (-1, 0, 1))


@lru_cache(maxsize=16)
def open_edge(
    rooms: tuple[Room, ...],
    grids: tuple[Walkable, ...],
    mark: tuple[float, float],
    way: tuple[int, int],
    to: int | None = None,
) -> tuple[float, float] | None:
    """The centre of the tile nearest `mark` within EDGE_SNAP that lies on the rooms' edge facing `way` (the tile
    beyond it in no room) and has footing by `grids`, never in a room touching another level and not `to` (the
    Fortress gate's room, 17:14:53 on 2026-10-20: `facing`); None: none read there."""
    ground = Ground(grids)
    barred = covered(tuple(foreign(rooms, to))) if to is not None else frozenset()

    def gap(room: Room) -> float:
        nearest = (min(max(mark[0], room.x), room.x + room.width), min(max(mark[1], room.y), room.y + room.height))
        return math.dist(mark, nearest)

    tiles = {
        (x, y)
        for room in rooms
        if gap(room) <= EDGE_SNAP + 1  # the tiles beyond those within EDGE_SNAP too
        for x in range(room.x, room.x + room.width)
        for y in range(room.y, room.y + room.height)
    }
    found = [
        (math.dist(mark, (x + 0.5, y + 0.5)), (x, y))
        for x, y in tiles
        if (x + way[0], y + way[1]) not in tiles
        and (x, y) not in barred
        and math.dist(mark, (x + 0.5, y + 0.5)) <= EDGE_SNAP
        and footed(ground, (x, y))
    ]
    if not found:
        return None
    x, y = min(found)[1]
    return (x + 0.5, y + 0.5)


def through(
    rooms: tuple[Room, ...], mark: tuple[float, float], to: int, grids: tuple[Walkable, ...] = ()
) -> tuple[float, float] | None:
    """The far place (tiles) of an open passage into `to` marked at `mark`: PASSAGE_PAST past the rooms' edge.
    A mark beyond the rooms is approached from their nearest point; one inside walks `outward` to the edge, from
    the open edge tile nearest it when `grids` show one (`open_edge`). None: no rooms, or a mark inside at the
    rooms' middle with no room known to touch `to`."""
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
    way = outward(rooms, to, mark)
    if way is None:
        return None
    if grids:
        # A border mark sits at a touching room's centre, which may be cliff: straight out from it no hop lands
        # (Lost City to Valley of Snakes, 2026-10-20 01:01-01:17, five games: the mark in room 379 'Desert Cliff Left
        # Ends', the canyon 21 tiles west; rca/2026-10-20/valley-of-snakes-findings.md)
        mark = open_edge(rooms, tuple(grids), mark, way, to) or mark
    x, y, walked = *mark, 0.0
    while in_rooms(rooms, (x, y)) and walked < INWARD_LIMIT:
        x, y, walked = x + way[0] * INWARD_STEP, y + way[1] * INWARD_STEP, walked + INWARD_STEP
    if walked >= INWARD_LIMIT:
        return None
    return (x + way[0] * PASSAGE_PAST, y + way[1] * PASSAGE_PAST)


@lru_cache(maxsize=1)
def _areas_by_name() -> dict[str, int]:
    """Level by its shown name (and `short_name`), for the names only one level has."""
    found: dict[str, set[int]] = defaultdict(set)
    for area in DISPLAY_NAMES:
        found[display_name(area)].add(area)
        found[short_name(area)].add(area)
    return {name: next(iter(areas)) for name, areas in found.items() if len(areas) == 1}


def poi_area(poi: Poi) -> int | None:
    """The level a way out leads into: its own, else the one its label names. A handler's marks name no level (the
    Kurast handler's 'Kurast Causeway', 2026-10-20 01:47:26: no level, no passage, taken for a door; 'going through
    takes a press' looped until the game was left)."""
    if poi.area is not None or poi.kind not in WAYS_OUT:
        return poi.area
    return _areas_by_name().get(poi.label)


def passage_of(
    area: int, rooms: tuple[Room, ...], poi: Poi, mark: tuple[float, float], grids: tuple[Walkable, ...] = ()
) -> tuple[float, float] | None:
    """`through` for a way out that is an open passage (presets.open_passage); None for a warp, an object
    (`Poi.use`), a mark naming no level, or no way out."""
    to = poi_area(poi)
    if poi.kind not in WAYS_OUT or to is None or poi.use or not open_passage(area, to):
        return None
    return through(rooms, mark, to, grids)


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


# TARGET_KEEPS_WARPS (2026-10-24, rca/2026-10-24/route-spin-findings.md "The way up"): a level that is one fixed
# preset (levels/handlers/treasure_levels.py: Pit, Hole and Underground Passage Level 2, Swampy Pit 3, Flayer Dungeon 3,
# Sewers 2, Frozen River, Drifter Cavern, Icy Cellar; the Durance of Hate 3's complex) has its target mark (a chest,
# Anya, Mephisto's Red portal) in the same preset instance as its stairs up, and that instance counted as marked, so its
# warp exit, the way back, never reached the card: the climb's stage (macros/zonenav.py `back`) found no mark ("Anya
# (Crystalline Passage is not marked yet)"), each "TZ up" leg's run ended "nothing is left to go to" and the climb was
# the Town Portal and the waypoint (14:09:44-14:09:46 on 2026-10-24; 22 of the 28 "way up … made 6 times" of
# 2026-10-21..24). True: an instance hides its warp exit to a level only when a way out (stairs, previous, exit) marks
# it or a mark there leads to that level. False: any mark with a spot hides them, as before. On from the restart after
# 2026-10-24 14:32 (the coordinator's go; the gate: tests/inventory_tracking/levels/test_exits_one_preset.py 12, and
# levels, routes, macros/acts, test_tzloop.py, test_zonenav.py 927 passed with the switch on and 927 with it off).
TARGET_KEEPS_WARPS = True


def with_exits(guidance: Guidance, snapshot: LevelSnapshot, pending: Iterable[int] = ()) -> Guidance:
    """`guidance` plus the ways out it does not mark yet; `pending` levels are left to the handler."""
    ways_out = [poi for poi in guidance.pois if marks_a_way_out(poi)]
    marked = {(poi.room.preset, origin(poi.room)) for poi in ways_out}
    if TARGET_KEEPS_WARPS:
        doors = {(poi.room.preset, origin(poi.room)) for poi in ways_out if poi.kind in WAYS_OUT}
        led = {(poi.room.preset, origin(poi.room), poi.area) for poi in ways_out if poi.area is not None}
        extra = [
            poi
            for poi in warp_exits(snapshot)
            if (poi.room.preset, origin(poi.room)) not in doors
            and (poi.room.preset, origin(poi.room), poi.area) not in led
        ]
    else:
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


# 17:48:34-17:49:17 on 2026-10-23 (take 20261023T144821Z-27): the Outer Cloister's way into the Monastery Gate marked
# at (15177.5, 5005.0), where the level's edge is roof; every walk click there "set the character off in none of
# 0.17s" and the 45 s watchdog stopped the loop with Mephisto, Baal and five shard acts owed. The way through was the
# closed door (class 24) at (15141, 5002), in the edge's gap 37 units west (games that marked (15137.5, 5005.0) went
# through it).
# A door on the edge the passage crosses (within DOOR_ON_EDGE of its place) is the passage: the walk goes to the tile
# past it, and a closed one is opened on the way (macros/hunting/moves.py `door_across`, macros/route.py `cross`).
DOOR_ON_EDGE = 60.0  # world units along the edge from the passage's place
EDGE_DEPTH = 2.0  # tiles: how far past the rooms' edge a door on it may stand


def door_passage(
    doors: Iterable[Door], rooms: tuple[Room, ...], place: tuple[float, float]
) -> tuple[float, float] | None:
    """The place past the door nearest `place` that stands on the same level edge (the rooms end on its inner side,
    within EDGE_DEPTH tiles), within DOOR_ON_EDGE; None: no rooms, no such door, or no edge found at `place`."""
    if not rooms:
        return None
    tile = (place[0] / TILE_UNITS, place[1] / TILE_UNITS)
    ways = [w for w in ((0, 1), (0, -1), (1, 0), (-1, 0)) if in_rooms(rooms, (tile[0] - 2 * w[0], tile[1] - 2 * w[1]))]
    if len(ways) != 1 or in_rooms(rooms, tile):
        return None
    way = ways[0]
    found = []
    for door in doors:
        at = (door.x / TILE_UNITS, door.y / TILE_UNITS)
        inner = (at[0] - way[0] * EDGE_DEPTH, at[1] - way[1] * EDGE_DEPTH)
        outer = (at[0] + way[0] * 1.0, at[1] + way[1] * 1.0)
        if in_rooms(rooms, inner) and not in_rooms(rooms, outer) and math.dist(place, (door.x, door.y)) <= DOOR_ON_EDGE:
            found.append(door)
    if not found:
        return None
    door = min(found, key=lambda d: math.dist(place, (d.x, d.y)))
    past = PASSAGE_PAST * TILE_UNITS
    return (door.x + way[0] * past, door.y + way[1] * past)
