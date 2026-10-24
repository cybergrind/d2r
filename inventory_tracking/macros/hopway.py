"""The hop potential grown lazily (teleport.py `Way`, `way_for`, `landing`): the same answers, a fraction of the work.

Why (2026-10-23, rca/2026-10-23/realtime-reads-findings.md, the safety's look): `Way` runs Dijkstra over every
landable tile of the level when it is built, and `way_for` builds one for each new goal point (the Target's point is
a float, so a goal that follows a monster or a group's nearest member is a new Target nearly every look). On the TZ
levels of 2026-10-23 (32-80 rooms, 4600-5100 tiles) one build is 37-53 ms of CPU (13 ms of it the landable scan,
which no goal changes), the far and the near potential both when the far one gives no landing; the look's
"the goal's way" / "the act asked for" stages (the goal's way is asked in either) ran 158-235 ms after each
"agenda: target a group of N".

Here the landable tiles are kept per level (`landable_tiles`) and the Dijkstra from the mark is grown only as far as
an answer needs: a tile's way is known once it is settled (popped), and a landing needs only the tiles whose way is
under the character's (`landing`: a spot is kept only when it takes MIN_GAIN off the way from where the character
stands). The pops are the original's in the original's order, so every way is the same float.

Wiring (the owner of movement.py / teleport.py): `movement.hop_way` and `hop_leg` take `way_for` and `landing` from
this module; `Way` itself stays for the callers that read its whole `cost` (hunt.py's explore tour,
tests/.../explore/nearest_rule.py). Not wired here (2026-10-23).
"""

import heapq
import math
import threading
from functools import lru_cache

from inventory_tracking.game.view import CORNERS, Viewport
from inventory_tracking.levels.model import Ground, Room, Target, Walkable
from inventory_tracking.levels.reach import bars, crossed, lined
from inventory_tracking.levels.route import Point, room_at
from inventory_tracking.macros.teleport import (
    APPROACH,
    FAR_TILES,
    HOST_VIEW,
    MIN_GAIN,
    REACH_TILES,
    WARP_TILES,
    approaches,
    centre,
    entry_stand,
    footing,
    ground_fraction,
    in_view,
    scaled,
    spots_in_view,
)
from inventory_tracking.native.layout import TILE_UNITS


# 2026-10-24 (rca/2026-10-24/realtime-4-findings.md §2): the potential grown as A* toward the character (the queue keyed
# by the way so far plus the straight line to where the character stands, a consistent bound: a hop of (dx, dy) costs
# hypot(dx, dy)), so a far goal settles the tiles between it and the character, not every tile as near the goal. The
# same ways, the same landing. Live (Durance of Hate 2, 08:06Z) a new far goal's Dijkstra settled ~4000 tiles, 65-98 ms
# of CPU per potential and twice when the far one has no landing: the judges of 200-400 ms after "agenda: target ...".
# False: grown in the way's order (Dijkstra), as before. On 2026-10-24 ~14:10, gated (gate6: 1220 pairs identical,
# cs kills/s 0.815 both, 0 landings changed of 2772 live hop ways, p99 38 -> 20 ms).
ASTAR_HOPS = True
SLACK = 1e-9  # tiles: a key's sum rounds, a bound's sum rounds the other way


@lru_cache(maxsize=8)
def landable_tiles(rooms: tuple[Room, ...], grids: tuple[Walkable, ...]) -> frozenset[tuple[int, int]]:
    """The room tiles a hop may land on (`Way`'s scan: footing at the centre by the grids, or no grid there), kept
    per level: no goal changes them."""
    ground = Ground(grids)
    found: set[tuple[int, int]] = set()
    for room in rooms:
        for x in range(room.x, room.x + room.width):
            for y in range(room.y, room.y + room.height):
                known = footing(ground, (x + 0.5, y + 0.5))
                if known or known is None:
                    found.add((x, y))
    return frozenset(found)


@lru_cache(maxsize=4)
def _ground(grids: tuple[Walkable, ...]) -> Ground:
    return Ground(grids)


class LazyWay:
    """`teleport.Way` with its Dijkstra grown on demand: `to_go`, `from_here`, `hops`, `on_rooms` and the attributes
    `landing` reads (`ground`, `view`, `rooms`, `barred`, `mark`, `reach`, `sees`) as `Way` has them."""

    def __init__(self, target: Target, view: Viewport = HOST_VIEW, far: bool = False) -> None:
        self.ground = _ground(target.ground)
        self.view = view
        self.rooms = target.rooms
        self.barred = bars(self.ground.grids) if lined(target.area) else None
        self.mark = target.point
        mark = (math.floor(target.point[0]), math.floor(target.point[1]))
        self.landable = landable_tiles(target.rooms, target.ground) | {mark}
        self.reach = reach = FAR_TILES if far else REACH_TILES
        self.sees = sees = view.hop_between if far else view.hop_in_view
        self.offsets = [
            (dx, dy, math.hypot(dx, dy))
            for dx in range(-reach, reach + 1)
            for dy in range(-reach, reach + 1)
            if 0 < math.hypot(dx, dy) <= reach and sees(-dx, -dy)
        ]
        self.home = mark
        self.marked = scaled(target.point)
        self.cost: dict[tuple[int, int], float] = {mark: 0.0}  # tentative; final once in `settled`
        self.settled: set[tuple[int, int]] = set()
        self.queue = [(0.0, mark)]
        self.lock = threading.Lock()
        # ASTAR_HOPS: the queue is keyed by way + `_ahead` toward `toward` (tiles: where the character stood at the last
        # `from_here`); None: by the way alone, as Dijkstra's
        self.astar = ASTAR_HOPS
        self.toward: Point | None = None

    def _ahead(self, tile: tuple[int, int]) -> float:
        """The straight line from the tile to `toward` (0 without one): no way of hops is shorter."""
        toward = self.toward
        return 0.0 if toward is None else math.hypot(tile[0] - toward[0], tile[1] - toward[1])

    def _aim(self, point: Point) -> None:
        """ASTAR_HOPS: the queue keyed toward `point` (the open tiles' ways so far kept); the caller holds the lock."""
        if not self.astar or self.toward == point:
            return
        self.toward = point
        open_tiles = {tile for _, tile in self.queue if tile not in self.settled}
        self.queue = [(self.cost[tile] + self._ahead(tile), tile) for tile in open_tiles]
        heapq.heapify(self.queue)

    def _pop(self) -> None:
        """One step of `Way`'s loop: the next tile settled and its hops relaxed."""
        key, (x, y) = heapq.heappop(self.queue)
        if (x, y) in self.settled or (not self.astar and key > self.cost[x, y]):
            return
        here_cost = self.cost[x, y]  # a key of an older way of this tile pops after its newer one
        self.settled.add((x, y))
        barred, cost, landable = self.barred, self.cost, self.landable
        ahead = self._ahead if self.astar else None
        for dx, dy, step in self.offsets:
            there = (x + dx, y + dy)
            if there in landable and here_cost + step < cost.get(there, math.inf):
                if barred is not None and not crossed(
                    barred, centre(there), self.marked if (x, y) == self.home else centre((x, y))
                ):
                    continue
                cost[there] = here_cost + step
                heapq.heappush(self.queue, (here_cost + step + (ahead(there) if ahead else 0.0), there))

    def _grow_to(self, bound: float, ahead: float = 0.0) -> None:
        """Settle every tile whose way is at most `bound`; with ASTAR_HOPS every such tile within `ahead` of `toward`
        (a key of way + line at most their sum, SLACK for the sums' rounding)."""
        with self.lock:
            limit = bound + ahead + SLACK if self.astar else bound
            while self.queue and self.queue[0][0] <= limit:
                self._pop()

    def _settle(self, tile: tuple[int, int]) -> float:
        """The tile's way (inf: none), grown until it is settled or nothing is left."""
        if tile not in self.landable:
            return math.inf
        with self.lock:
            while tile not in self.settled and self.queue:
                self._pop()
        return self.cost[tile] if tile in self.settled else math.inf

    def _to_go(self, point: Point, cost: float) -> float:
        anchor = self.mark if cost == 0.0 else (math.floor(point[0]) + 0.5, math.floor(point[1]) + 0.5)  # ruff: ignore[float-equality-comparison] the mark's own 0
        return cost + math.dist(point, anchor)

    def hops(self, start: Point, point: Point) -> bool:
        return self.barred is None or crossed(self.barred, scaled(start), scaled(point))

    def on_rooms(self, point: Point) -> bool:
        return room_at(self.rooms, point) is not None

    def to_go(self, point: Point) -> float:
        """`Way.to_go`: the tile's way plus the way to its centre (to the mark in the mark's tile)."""
        cost = self._settle((math.floor(point[0]), math.floor(point[1])))
        return math.inf if cost == math.inf else self._to_go(point, cost)

    def to_go_below(self, point: Point, bound: float) -> float:
        """`to_go` where the tile's way is under `bound` (grown to it), else inf: what a landing needs."""
        tile = (math.floor(point[0]), math.floor(point[1]))
        if self.astar:
            self._grow_to(bound, self._ahead(tile))
            # A* settles tiles past `bound` too (a short line makes up for a long way): those are not under it
            if tile in self.settled and self.cost[tile] <= bound:
                return self._to_go(point, self.cost[tile])
            return math.inf
        self._grow_to(bound)
        return self._to_go(point, self.cost[tile]) if tile in self.settled else math.inf

    def from_here(self, point: Point) -> float:
        """`Way.from_here`: `to_go`, or, off landable ground, the best landable tile one hop away, grown only until no
        tile left unsettled could beat the best found."""
        tile = (math.floor(point[0]), math.floor(point[1]))
        if self.astar:
            with self.lock:
                self._aim(point)
        if tile in self.landable:
            here = self.to_go(point)
            if here < math.inf:
                return here
        tx, ty = tile
        near = [
            (tx + dx, ty + dy)
            for dx in range(-self.reach, self.reach + 1)
            for dy in range(-self.reach, self.reach + 1)
            if (tx + dx, ty + dy) in self.landable
            and self.sees(dx, dy)
            and math.dist(point, (tx + dx + 0.5, ty + dy + 0.5)) <= self.reach
        ]
        # A* (ASTAR_HOPS): a cell's way under `best` has a key under best + its line to `toward`, at most `ahead`
        ahead = max((self._ahead(cell) for cell in near), default=0.0) + SLACK if self.astar else 0.0
        with self.lock:
            while True:
                best = min(
                    (
                        self._to_go(c, self.cost[cell]) + math.dist(point, c)
                        for cell in near
                        if cell in self.settled
                        for c in [(cell[0] + 0.5, cell[1] + 0.5)]
                    ),
                    default=math.inf,
                )
                if not self.queue or all(cell in self.settled for cell in near) or self.queue[0][0] > best + ahead:
                    return best
                self._pop()


def lands(way: LazyWay, point: Point) -> bool:
    """`teleport.landable` over a `LazyWay`."""
    known = footing(way.ground, point)
    return known if known is not None else way.on_rooms(point)


def entry_in(target: Target, player, way: LazyWay, aspect: float) -> Point | None:
    """`teleport.entry_in_view` over a `LazyWay`."""
    entry = entry_stand(target)
    if entry is None or not in_view(ground_fraction(player, *scaled(entry), aspect)):
        return None
    start = (player.x / TILE_UNITS, player.y / TILE_UNITS)
    return entry if lands(way, entry) and way.hops(start, entry) else None


def way_for(target: Target, view: Viewport = HOST_VIEW, far: bool = False) -> LazyWay:
    """`teleport.way_for` with the lazy potential, kept per the level's line rule and the view's corners too
    (2026-10-23: a switch of reach.TELEPORT_LINE or view.CORNERS gets a new way, not one kept under the other)."""
    return kept_way(target, view, far, (lined(target.area), CORNERS[0]))


@lru_cache(maxsize=8)
def kept_way(target: Target, view: Viewport, far: bool, rules: tuple[bool, bool]) -> LazyWay:
    del rules  # a key only: LazyWay reads them itself
    return LazyWay(target, view, far)


def landing(
    target: Target, player, way: LazyWay, aspect: float, ring: tuple[float, float] | None = None
) -> tuple[Point, float] | None:
    """`teleport.landing` over a `LazyWay`: the same spot and gain. A spot is kept only when its way is MIN_GAIN under
    the character's, so the potential is grown no further than the character's own way."""
    start = (player.x / TILE_UNITS, player.y / TILE_UNITS)
    now = way.from_here(start)

    def outside(point: Point) -> bool:
        return ring is not None and not ring[0] <= math.dist(point, start) * TILE_UNITS <= ring[1]

    entry = entry_in(target, player, way, aspect)
    if entry is not None and not outside(entry):
        return entry, now - way.to_go(entry)
    candidates = (*spots_in_view(player, aspect), *(approaches(target) if target.warp else (target.point,)))
    found: list[tuple[float, float, Point]] = []
    for point in candidates:
        if outside(point):
            continue
        if target.warp and math.dist(scaled(point), scaled(target.point)) < WARP_TILES:
            continue
        if not way.view.hop_view(ground_fraction(player, *scaled(point), aspect)) or not lands(way, point):
            continue
        if not way.hops(start, point):
            continue
        found.append((way.to_go_below(point, now), math.dist(point, start), point))
    found = [entry for entry in found if now - entry[0] >= MIN_GAIN / TILE_UNITS]
    if not found:
        return None
    beside = [entry for entry in found if math.dist(scaled(entry[2]), scaled(target.point)) <= APPROACH + 1.0]
    if target.warp and beside:
        cost, _, spot = min(beside, key=lambda entry: entry[1])
    else:
        cost, _, spot = min(found)
    return spot, now - cost
