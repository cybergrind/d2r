"""KP_4: one step toward the level card's mark, a teleport as far as the screen allows or, at the
door to the next level, a walk into it. The history of each rule is in macros/plan.md.

The mark is the first one on the card (levels/guide.py `target`). Teleport is found, not assumed:
skill 54 in a skill slot gives the key (skills.py); a staff with Teleport charges in either weapon
set says whether to swap first and how many charges are left. Without a staff the key is pressed as
it is (an oskill) and the character moving is the proof. The staff is left in hand afterwards: the
next press needs it too.

The key is pressed again and again with Win held: the pointer flicks rather than glides, nothing
waits at the end, the mouse may drift under the player's hand (POINTER_DRIFT), and a press during a
step queues one more step (runner).

A hop lands on the footing in view that leaves the shortest way to go (`landing`). Footing is the
loaded rooms' walkable sub-tiles where they were read (the spot and its neighbours a world unit
around, `footing`); the room rectangle stands in where no grid was read. The way to go is a
potential over landable tiles (`Way`): Dijkstra from the mark's tile, each step a hop of at most
REACH_TILES, walls in between or not, cached per target. The mark itself is a candidate, so the last
hop lands on it. Each hop logs where it aimed and where the character landed.

A door is clicked, not teleported onto: a teleport onto a warp tile does not take it, walking into it
does. The game walks a clicked character to one spot beside the stairs before the level changes; that
spot is remembered per door (`Entries`), the last hop lands on it, and the click from there is the
step in. A door with no spot known yet is clicked from within NEAR_WARP, after a hop beside it
(`approaches`). The click goes to the ground at the warp tiles first and to the doorway drawn above
them next (DOOR_AIMS).
"""

import heapq
import json
import math
from functools import lru_cache
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.levels.model import Ground, Target
from inventory_tracking.levels.route import Point, room_at
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import (
    BODY_LIFT,
    UNIT_PIXELS,
    press_skill,
    screen_fraction,
    swap_until,
    world_point,
)
from inventory_tracking.macros.skills import SWAP_WEAPONS, TELEPORT
from inventory_tracking.macros.world import Player
from inventory_tracking.native.layout import TILE_UNITS


# World units: a door this close is walked into, not teleported next to (from 20 the character
# walked around a wall for six seconds).
NEAR_WARP = 10.0
# The last hop before a door with no remembered spot lands beside it, not on it: spots APPROACH units
# from the warp's centre, a tile beyond its own tiles, the nearest to the character among those with
# footing. Nothing nearer than WARP_TILES to the centre is landed on.
APPROACH = 6.5
WARP_TILES = 5.0
BEARINGS = 16
MOVED = 2.0  # world units the character must have moved for a teleport or a walk to count
HOP_SECONDS = 1.5  # a teleport resolves well within this
WALK_SECONDS = 1.5  # the first step of a walk
# Where a door is clicked, in classic pixels (600 high; across, down) from the ground at the centre
# of its warp tiles, tried in turn until the level changes. The ground takes the doors of the
# Catacombs and the Jail and none in the Worldstone Keep. lvlwarp.txt has why: a door takes clicks in a box around its
# picture, which reaches 30 pixels below the tile for 'Act 1 Catacombs Down' and 5 for 'Act 5 Baal
# Temple Down', 110 above for both. The side aims are for a box that sits left or right of the
# tiles' centre (the Baal boxes are 95 and 80 wide, the two tiles 160); which tile the box hangs
# from is not known here.
DOOR_AIMS = ((0, 0), (0, -45), (-50, -45), (50, -45))
DOOR_SECONDS = 1.2  # a click on a door at most NEAR_WARP away, then the new level: 0.2 to 0.35 s in the log
DOOR_TOOK: dict[int, tuple[int, int]] = {}  # area -> the aim that took its door last, tried first next time
# Where the character stood when a door took it, relative to the warp point the level card marks (world
# units), remembered per door and kept across games: the game walks a clicked character to one spot beside
# the stairs before the level changes (the Catacombs: 3 units "south" of the mark, round a block of walls
# the mark sits in). The last hop lands on that spot, and the click from there is the step in.
DEFAULT_ENTRIES = Path('inventory_tracking/runs/macros/door-entries.json')
ENTRY_MAX = 6.0  # world units from the mark: a last position further off is not the door's own spot
ENTRY_NEAR = 4.0  # world units from the remembered spot: near enough to click the door from
WALK_POLL = 0.04  # seconds between looks while the character walks into a door (one game frame)


class Entries:
    """Remembered entry spots: `offset` gives a door's, `learn` keeps one; a JSON file when `path` is set."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.known: dict[str, tuple[float, float]] | None = None

    @staticmethod
    def level_key(target: Target) -> str:
        """The door's kind in its level: what a preset not met yet falls back on. The Catacombs' stairs
        presets 291, 292 and 294 are the same block of walls with the same spot beside it."""
        return f'area {target.area}:{target.kind}'

    @staticmethod
    def key(target: Target) -> str:
        """The door's kind in its room's preset: a stairs preset comes in four orientations (N, S, E, W)
        and the spot beside it turns with them, whatever the level; the area stands in without a room."""
        room = room_at(target.rooms, target.point)
        return f'preset {room.preset}:{target.kind}' if room is not None else Entries.level_key(target)

    def load(self) -> dict[str, tuple[float, float]]:
        if self.known is None:
            self.known = {}
            if self.path is not None and self.path.exists():
                try:
                    found = json.loads(self.path.read_text())
                    self.known = {key: (float(x), float(y)) for key, (x, y) in found.items()}
                except (OSError, ValueError, TypeError) as exc:
                    LOG.info('Macro: the door entries could not be read (%s)', exc)
        return self.known

    def offset(self, target: Target) -> tuple[float, float] | None:
        known = self.load()
        return known.get(self.key(target)) or known.get(self.level_key(target))

    def learn(self, target: Target, offset: tuple[float, float]) -> None:
        known = self.load()
        known[self.key(target)] = known[self.level_key(target)] = (round(offset[0], 1), round(offset[1], 1))
        if self.path is not None:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps(known, indent=1, sort_keys=True))
            except OSError as exc:
                LOG.info('Macro: the door entries could not be written (%s)', exc)


ENTRIES = Entries(DEFAULT_ENTRIES)


def entry_spot(target: Target) -> Point | None:
    """The remembered spot beside `target`'s door (tiles), if any."""
    offset = ENTRIES.offset(target) if target.warp else None
    if offset is None:
        return None
    door = scaled(target.point)
    return (door[0] + offset[0]) / TILE_UNITS, (door[1] + offset[1]) / TILE_UNITS


# Where ground can be clicked, as window fractions: inside the view, above the skill bar. Wider than
# routines.AIM_LIMITS (a cast on a unit): the bottom bar covers about the lowest sixth of the window.
VIEW = ((0.03, 0.97), (0.05, 0.84))
VIEW_STEP = 0.03  # of the window, between the landing spots tried across the view
MIN_GAIN = 3.0  # world units a hop must take off the way to go, or it is not made
# Pixels the pointer may differ from where the macro put it: any. The player's hand works the mouse
# while tapping the key, and a swipe never stops a step (400 still stopped two in the Catacombs); the
# aim is checked and made again instead (`Actuator.aim`).
POINTER_DRIFT = 10**6
REACH_TILES = 5  # tiles one hop of the potential may span: about the view's shorter half (26 units)


def in_view(point: tuple[float, float]) -> bool:
    return all(low <= value <= high for value, (low, high) in zip(point, VIEW, strict=True))


def ground_fraction(player: Player, x: float, y: float, aspect: float) -> tuple[float, float]:
    """Where the ground at world (x, y) is drawn: `screen_fraction` without the lift onto a body."""
    across, down = screen_fraction(player, x, y, aspect)
    return across, down + BODY_LIFT


def footing(ground: Ground, point: Point) -> bool | None:
    """Whether a teleport aimed at `point` (tiles) finds ground: the sub-tile and its neighbours a
    world unit around are walkable by the read grids. None where no grid covers the spot."""
    x, y = scaled(point)
    centre = ground.walkable(x, y)
    if centre is None:
        return None
    around = (ground.walkable(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
    return centre and all(known is not False for known in around)


class Way:
    """The way to go from any spot, in tiles: a potential over the landable tiles of the level,
    Dijkstra from the mark's tile with hops of at most REACH_TILES between landable tiles, walls in
    between or not (a teleport crosses them). A tile is landable when its centre has footing by the
    read grids, or lies on a room no grid covers; the mark's tile always is."""

    def __init__(self, target: Target) -> None:
        ground = Ground(target.ground)
        self.rooms = target.rooms
        landable: set[tuple[int, int]] = set()
        for room in self.rooms:
            for x in range(room.x, room.x + room.width):
                for y in range(room.y, room.y + room.height):
                    known = footing(ground, (x + 0.5, y + 0.5))
                    if known or known is None:
                        landable.add((x, y))
        self.mark = target.point
        mark = (math.floor(target.point[0]), math.floor(target.point[1]))
        landable.add(mark)
        offsets = [
            (dx, dy, math.hypot(dx, dy))
            for dx in range(-REACH_TILES, REACH_TILES + 1)
            for dy in range(-REACH_TILES, REACH_TILES + 1)
            if 0 < math.hypot(dx, dy) <= REACH_TILES
        ]
        self.cost = {mark: 0.0}
        queue = [(0.0, mark)]
        while queue:
            here_cost, (x, y) = heapq.heappop(queue)
            if here_cost > self.cost[x, y]:
                continue
            for dx, dy, step in offsets:
                there = (x + dx, y + dy)
                if there in landable and here_cost + step < self.cost.get(there, math.inf):
                    self.cost[there] = here_cost + step
                    heapq.heappush(queue, (here_cost + step, there))

    def on_rooms(self, point: Point) -> bool:
        return room_at(self.rooms, point) is not None

    def to_go(self, point: Point) -> float:
        """Tiles left from `point`: its tile's potential plus the way to the tile's centre, or to the
        mark itself in the mark's tile, so the mark is the one spot with nothing left."""
        tile = (math.floor(point[0]), math.floor(point[1]))
        cost = self.cost.get(tile)
        if cost is None:
            return math.inf
        anchor = self.mark if cost == 0.0 else (tile[0] + 0.5, tile[1] + 0.5)
        return cost + math.dist(point, anchor)

    def from_here(self, point: Point) -> float:
        """Tiles left from where the character stands: as `to_go`, or, when its own tile is not landable
        (a lava edge in the River of Flame), the best landable tile one hop away."""
        here = self.to_go(point)
        if here < math.inf:
            return here
        tx, ty = math.floor(point[0]), math.floor(point[1])
        return min(
            (
                self.to_go(centre) + math.dist(point, centre)
                for dx in range(-REACH_TILES, REACH_TILES + 1)
                for dy in range(-REACH_TILES, REACH_TILES + 1)
                if (tx + dx, ty + dy) in self.cost
                for centre in [(tx + dx + 0.5, ty + dy + 0.5)]
                if math.dist(point, centre) <= REACH_TILES
            ),
            default=math.inf,
        )


@lru_cache(maxsize=4)
def way_for(target: Target) -> Way:
    """The potential of a target, kept across presses: rooms, grids and mark rarely change within a level."""
    return Way(target)


def spots_in_view(player: Player, aspect: float):
    """Ground points drawn across the view, in tiles, VIEW_STEP of the window apart."""
    (left, right), (top, bottom) = VIEW
    columns, rows = int((right - left) / VIEW_STEP) + 1, int((bottom - top) / VIEW_STEP) + 1
    for column in range(columns):
        for row in range(rows):
            x, y = world_point(player, left + column * VIEW_STEP, top + row * VIEW_STEP, aspect)
            yield x / TILE_UNITS, y / TILE_UNITS


def landable(target: Target, way: Way, point: Point) -> bool:
    """Whether a hop may be aimed at `point` (tiles): footing by the read grids, else a room's rectangle."""
    known = footing(Ground(target.ground), point)
    return known if known is not None else way.on_rooms(point)


def entry_in_view(target: Target, player: Player, way: Way, aspect: float) -> Point | None:
    """The door's remembered spot (tiles) when a hop from here can land on it."""
    entry = entry_spot(target)
    if entry is None or not in_view(ground_fraction(player, *scaled(entry), aspect)):
        return None
    return entry if landable(target, way, entry) else None


def landing(target: Target, player: Player, way: Way, aspect: float) -> tuple[Point, float] | None:
    """The footing in view that leaves the shortest way to the mark, with the tiles it takes off the
    way from where the character stands; None when nothing in view brings it MIN_GAIN nearer."""
    start = (player.x / TILE_UNITS, player.y / TILE_UNITS)
    now = way.from_here(start)
    entry = entry_in_view(target, player, way, aspect)
    if entry is not None:
        return entry, now - way.to_go(entry)  # the door's own spot is in view: the hop that ends the way
    candidates = (*spots_in_view(player, aspect), *(approaches(target) if target.warp else (target.point,)))
    found: list[tuple[float, float, Point]] = []  # (way to go, distance from the character, spot)
    for point in candidates:
        if target.warp and math.dist(scaled(point), scaled(target.point)) < WARP_TILES:
            continue  # the warp's own tiles: a hop onto them lands anywhere beside
        if not in_view(ground_fraction(player, *scaled(point), aspect)) or not landable(target, way, point):
            continue
        found.append((way.to_go(point), math.dist(point, start), point))
    if not found:
        return None
    beside = [entry for entry in found if math.dist(scaled(entry[2]), scaled(target.point)) <= APPROACH + 1.0]
    if target.warp and beside:  # a spot beside the door: the one nearest the character, on its side
        cost, _, spot = min(beside, key=lambda entry: entry[1])
    else:
        cost, _, spot = min(found)
    if now - cost < MIN_GAIN / TILE_UNITS:
        return None
    return spot, now - cost


def approaches(target: Target) -> list[Point]:
    """Spots (tiles) APPROACH units around a warp, where the last hop may land."""
    cx, cy = scaled(target.point)
    return [
        ((cx + APPROACH * math.cos(angle)) / TILE_UNITS, (cy + APPROACH * math.sin(angle)) / TILE_UNITS)
        for angle in (2 * math.pi * k / BEARINGS for k in range(BEARINGS))
    ]


def scaled(tile: Point) -> Point:
    return tile[0] * TILE_UNITS, tile[1] * TILE_UNITS


def moved(player: Player, since: Player) -> bool:
    return player.area != since.area or math.dist((player.x, player.y), (since.x, since.y)) >= MOVED


def take_teleport(run: Run, key_names) -> None:
    """Have the Teleport key in `run.keys` and the staff that casts it in hand, if a staff it is."""
    world = run.world()
    if TELEPORT not in world.slots:
        raise Abort('Teleport is not on a skill key')
    staff = run.teleport() if run.teleport is not None else None
    if staff is None:
        run.keys = key_names(world, (TELEPORT,))
        return
    if staff.charges == 0:
        raise Abort('the Teleport staff has no charges left')
    if staff.in_hand:
        run.keys = key_names(world, (TELEPORT,))
        return
    run.keys = key_names(world, (TELEPORT, SWAP_WEAPONS))

    def in_hand() -> bool:
        now = run.teleport() if run.teleport is not None else None
        return now is not None and now.in_hand

    if not swap_until(run, in_hand):  # pressed again when the game drops it (routines.swap_until)
        raise Abort('the Teleport staff is not in hand after the swaps')
    run.pause('key')


def door_aims(area: int) -> tuple[tuple[int, int], ...]:
    took = DOOR_TOOK.get(area)
    return DOOR_AIMS if took is None else (took, *(aim for aim in DOOR_AIMS if aim != took))


def walk_into(run: Run, target: Target, player: Player, aspect: float) -> None:
    """Click the door and watch the walk: where the mark is, where the character started, how long and
    how far it walked and where it stood when the level changed (the last hop's landing is judged by
    the walk it leaves). That last spot is remembered as the door's entry."""
    door = scaled(target.point)
    if not in_view(ground_fraction(player, *door, aspect)):
        raise Abort(f'{target.label} is not in view')
    start = (player.x, player.y)
    known = ENTRIES.offset(target)
    run.say(f'Walking into {target.label}, {math.dist(start, door):.0f} away')
    LOG.info(
        'Macro: door %s marked at (%.1f, %.1f); the character at (%.1f, %.1f), %.1f from the mark; entry %s',
        target.label, *door, *start, math.dist(start, door),
        'not known yet' if known is None else f'remembered {known[0]:+.1f}, {known[1]:+.1f} from the mark',
    )  # fmt: skip
    began = run.clock()
    last, walked = start, 0.0
    for aim in door_aims(target.area):
        across, down = ground_fraction(player, *door, aspect)
        where = (across + aim[0] * UNIT_PIXELS[0] / 16 / aspect, down + aim[1] * UNIT_PIXELS[1] / 8)
        if not in_view(where):
            continue
        run.actuator.aim(*where, scatter=(4, 3))
        run.actuator.click()
        deadline = run.clock() + DOOR_SECONDS
        while True:
            world = run.world()
            now = world.player
            if now is None or now.area != target.area:
                DOOR_TOOK[target.area] = aim
                offset = (last[0] - door[0], last[1] - door[1])
                LOG.info('Macro: the door took the click %s pixels from its tiles', aim)
                LOG.info(
                    'Macro: door %s: in after %.2fs, walked %.1f from (%.1f, %.1f) to (%.1f, %.1f); the level '
                    'changed %.1f from the mark, at %+.1f, %+.1f from it (the entry %s)',
                    target.label, run.clock() - began, walked, *start, *last, math.hypot(*offset), *offset,
                    'remembered' if math.hypot(*offset) <= ENTRY_MAX else 'not remembered: too far from the mark',
                )  # fmt: skip
                if math.hypot(*offset) <= ENTRY_MAX:
                    ENTRIES.learn(target, offset)
                run.say(f'{target.label}: there')
                return
            here = (now.x, now.y)
            walked += math.dist(here, last)
            last = here
            if run.clock() >= deadline:
                break
            run.pace.sleep(WALK_POLL)
        player = run.world().player or player  # the click on the ground walked the character
        LOG.info('Macro: the door did not take the click %s pixels from its tiles', aim)
    raise Abort(f'no click took {target.label}')


def world_slots(world) -> str:
    return ','.join('-' if skill is None else str(skill) for skill in world.slots)


def ready(run: Run) -> tuple[Player, tuple[int, int, int, int]]:
    """The checks every step shares: in a game, nothing open, a game window. (the player, the window rect)."""
    world = run.world()
    if world.player is None:
        raise Abort('not in a game')
    if world.open_panels:
        raise Abort(f'{world.open_panels[0]} is open')
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        raise Abort('no game window')
    run.actuator.drift = POINTER_DRIFT
    return world.player, rect


def step_toward(run: Run, target: Target | None, key_names) -> None:
    """One press of KP_4. `key_names(world, skills)` gives the key per skill (runner)."""
    player, rect = ready(run)
    if target is None:
        raise Abort('nothing is marked on the level card (Win+C shows it)')
    if target.area != player.area:
        raise Abort('the level card is for another level')
    aspect = rect[2] / rect[3]
    here = (player.x, player.y)
    entry = entry_spot(target)
    if entry is not None and math.dist(here, scaled(entry)) <= ENTRY_NEAR:
        at_door = True  # on the door's own spot: clicked from here
    elif entry is not None and entry_in_view(target, player, way_for(target), aspect) is not None:
        at_door = False  # the spot is a hop away: onto it first, however near the door is
    else:
        at_door = target.warp and math.dist(here, scaled(target.point)) <= NEAR_WARP
    if at_door:
        walk_into(run, target, player, aspect)
    else:
        hop_toward(run, target, player, rect, key_names)


def hop_toward(run: Run, target: Target, player: Player, rect: tuple[int, int, int, int], key_names) -> None:
    """One teleport toward `target`: the landing in view that leaves the shortest way (the hunt
    keys use it too, macros/hunt.py)."""
    aspect = rect[2] / rect[3]
    way = way_for(target)
    if way.from_here((player.x / TILE_UNITS, player.y / TILE_UNITS)) == math.inf:
        raise Abort(f'no way over the rooms to {target.label}')
    found = landing(target, player, way, aspect)
    if found is None:
        raise Abort(f'no footing in view brings the character nearer to {target.label}')
    spot, gain = found
    take_teleport(run, key_names)
    left = math.dist(spot, target.point) * TILE_UNITS
    staff = run.teleport() if run.teleport is not None else None
    charges = f', {staff.charges} charges' if staff is not None else ''
    run.say(f'Teleport toward {target.label}: {left:.0f} left after this{charges}')
    run.actuator.aim(*ground_fraction(player, *scaled(spot), aspect), scatter=(4, 3))
    press_skill(run, TELEPORT)
    aim = scaled(spot)
    if target.warp:
        door, entry = scaled(target.point), entry_spot(target)
        LOG.info(
            'Macro: door %s marked at (%.1f, %.1f), entry %s; this hop aims %.1f from the mark',
            target.label, *door,
            'not known yet' if entry is None else '({:.1f}, {:.1f})'.format(*scaled(entry)), math.dist(aim, door),
        )  # fmt: skip
    where = (
        f'aimed at ({aim[0]:.1f}, {aim[1]:.1f}), {math.dist(aim, (player.x, player.y)):.1f} from ({player.x:.1f}, '
        f'{player.y:.1f}), {gain * TILE_UNITS:.1f} off the way, footing {footing(Ground(target.ground), spot)}, '
        f'{len(target.ground)} grids, '
        f'pointer {run.actuator.keys.pointer()} in {rect}'
    )
    if run.seen(lambda w: w.player is not None and moved(w.player, player), HOP_SECONDS) is None:
        after, now = run.world(), run.teleport() if run.teleport is not None else None
        LOG.info(
            'Macro: teleport %s; the character did not move: key %s, slots %s, staff %s, mode now %s, right skill %s',
            where, run.keys.get(TELEPORT), world_slots(after), now,
            after.player.mode if after.player else None, after.player.right_skill if after.player else None,
        )  # fmt: skip
        raise Abort('Teleport: the character did not move (no charges, no mana, nowhere to land?)')
    landed = run.world().player
    if landed is not None:
        off = (landed.x - aim[0], landed.y - aim[1])
        LOG.info(
            'Macro: teleport %s; landed at (%.1f, %.1f), off by %.1f (%+.1f, %+.1f)',
            where, landed.x, landed.y, math.hypot(*off), *off,
        )  # fmt: skip
