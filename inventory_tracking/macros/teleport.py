"""The teleport step: one step toward the level card's mark, a teleport as far as the screen allows or, at the
door to the next level, a walk into it. The history of each rule is in macros/plan.md.

The mark is the first one on the card (levels/guide.py `target`). Teleport is found, not assumed:
skill 54 in a skill slot gives the key (skills.py); a staff with Teleport charges in either weapon
set says whether to swap first and how many charges are left. Without a staff the key is pressed as
it is (an oskill) and the character moving is the proof. The staff is left in hand afterwards: the
next press needs it too.

The step is asked for again and again: the pointer flicks rather than glides, nothing
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
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.levels.model import Ground, Target
from inventory_tracking.levels.presets import warp_box
from inventory_tracking.levels.route import Point, room_at
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import press_skill, settle, swap_until, world_point
from inventory_tracking.macros.skills import SWAP_WEAPONS, TELEPORT
from inventory_tracking.macros.view import CORNER_BOTTOM, CORNERS, UNIT_PIXELS, VIEW, Viewport
from inventory_tracking.macros.world import Player, Warp
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
WALKING = frozenset((2, 3, 6))  # the character's modes while it goes somewhere on foot (combat/policy.py RUN_MODES)
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
# The aim that takes a door, by `Entries.key`, where the saved logs say: tried first. A door's box hangs
# from its picture, so the aim goes with the preset, not the level. Tower Cellar 1-3 (host, 20:05 on
# 2026-10-10): the stairs down took (-50, -45) in each of the W, E and N presets, after 1.4 s lost on
# each of the two aims before it; S is taken to be the same. The Forgotten Tower in Black Marsh took
# (-50, -45) four times on 2026-10-10 and missed it twice, (0, -45) once of three, (0, 0) never: all
# guesses round a box that is 42 to 122 pixels above the tiles. The door's own box (`box_aim`) goes
# before these, and a door learnt since (`AIMS`) next.
KNOWN_AIMS = {
    'preset 143:stairs': (-50, -45),
    'preset 144:stairs': (-50, -45),
    'preset 145:stairs': (-50, -45),
    'preset 146:stairs': (-50, -45),
    'preset 163:stairs': (-50, -45),
}
DEFAULT_AIMS = Path('inventory_tracking/runs/macros/door-aims.json')
# Where the character stood when a door took it, relative to the warp point the level card marks (world
# units), remembered per door and kept across games: the game walks a clicked character to one spot beside
# the stairs before the level changes (the Catacombs: 3 units "south" of the mark, round a block of walls
# the mark sits in). The last hop lands on that spot, and the click from there is the step in.
DEFAULT_ENTRIES = Path('inventory_tracking/runs/macros/door-entries.json')
ENTRY_MAX = 6.0  # world units from the mark: a last position further off is not the door's own spot
# World units: the remembered spot this near over open ground is walked to by the click on the door, not
# hopped onto (user, 2026-10-10: "we have jumped twice around the entrance": a hop beside the door, a
# hop onto the spot 6 units on, then the click).
ENTRY_WALK = 9.0
ENTRY_NEAR = 4.0  # world units from the remembered spot: near enough to click the door from
WALK_POLL = 0.04  # seconds between looks while the character walks into a door (one game frame)
LOST_KEY = (
    'Teleport is off its key: bind it again (the skill list, the pointer on Teleport, the key). '
    'It is lost when a game is left with the staff in hand'
)
HOVER_SECONDS = 0.06  # for the game to note what is under the pointer after it moved (a frame or two)
# Unit types of the record of the unit under the pointer that are not a door: a monster (the mercenary
# and the summons land beside the character after a hop), an item. An aim with one of them under it is
# left for last: the click would go to that unit.
IN_THE_WAY = frozenset((1, 4))
# The unit type of a door (a warp tile) in that record. In the logs to 2026-10-10 each of the 31 clicks
# a door took had a tile in the record, and none of the 4 made with an object in it took: those were
# clicks on the ground, each walking the character off for 1.4 s (the tower's door in Black Marsh,
# host, 22:43 on 2026-10-10: 6 s around the entrance). The record keeps the last unit when the pointer
# is on nothing, so a tile in it may be the door just come through: such an aim is clicked as before.
TILE_UNIT = 5
# A click made while a cast ends is swallowed: the character neither walks nor goes in. Tower Cellar,
# host, 23:26 and 23:35 on 2026-10-10: attack mode's strike 0.04 s and 0.7 s before the click on the
# stairs, the character where it stood 1.4 s later, then two aims off the door and 4.8 s in all; the
# same aim from the same spot took in 0.23 s in the next game. So the character is waited free
# (`settle`) and a click that moved nobody is made again, STILL_SECONDS on, before the next aim is tried.
DOOR_CLICKS = 2
# A character that has not moved this long after a click was not sent anywhere (a door took one in 0.37 s at most).
STILL_SECONDS = 0.5
WARP_NEAR = 12.0  # world units from the mark to its door unit (the tower's in Black Marsh: 7.0)
LOOKS = 2  # times the aims are looked at for a door under them before one is clicked without (0.14 s an aim)


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
AIMS = Entries(DEFAULT_AIMS)  # the aim that took each door last, kept the same way


def entry_spot(target: Target) -> Point | None:
    """The remembered spot beside `target`'s door (tiles), if any."""
    offset = ENTRIES.offset(target) if target.warp else None
    if offset is None:
        return None
    door = scaled(target.point)
    return (door[0] + offset[0]) / TILE_UNITS, (door[1] + offset[1]) / TILE_UNITS


VIEW_STEP = 0.03  # of the window, between the landing spots tried across the view
MIN_GAIN = 3.0  # world units a hop must take off the way to go, or it is not made
# Pixels the pointer may differ from where the macro put it: any. The player's hand works the mouse
# while tapping the key, and a swipe never stops a step (400 still stopped two in the Catacombs); the
# aim is checked and made again instead (`Actuator.aim`).
POINTER_DRIFT = 10**6
HOST_VIEW = Viewport()  # the window a potential is planned for when none is given (16:9, the host's)
REACH_TILES = 5  # tiles one hop of the potential may span: about the view's shorter half (26 units)
# The far potential: hops of up to FAR_TILES, counted from tile centre to tile centre (`hop_between`),
# so a band of no footing five tiles wide is crossed where the window shows the other side. Far Oasis,
# 01:58 on 2026-10-11 (user: "not using tp to move between sections and trying to tp through the
# stairs"; it works in some Act 2 areas that cliffs split): the cliff between two plateaus is 25
# units of no footing and the potential, with five tiles from anywhere on a tile, went round by the
# ramp. Hops really made: 229 of 2,282 were over 30 units, the longest 32. Up and left the window
# shows 31 units, down and right 26, so a cliff may be crossed one way and not the other. A target the
# far potential found no landing for is planned the old way from then on (`FAR_FAILED`).
FAR_TILES = 6
FAR_FAILED: set[tuple[int, int, int]] = set()


def in_view(point: tuple[float, float]) -> bool:
    return Viewport().in_view(point)


def ground_fraction(player: Player, x: float, y: float, aspect: float) -> tuple[float, float]:
    """Where the ground at world (x, y) is drawn (view.py): no lift onto a body."""
    return Viewport(aspect).ground((player.x, player.y), x, y)


def footing(ground: Ground, point: Point) -> bool | None:
    """Whether a teleport aimed at `point` (tiles) finds ground: the sub-tile and its neighbours a
    world unit around are walkable by the read grids. None where no grid covers the spot."""
    x, y = scaled(point)
    centre = ground.walkable(x, y)
    if centre is None:
        return None
    around = (ground.walkable(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
    return centre and all(known is not False for known in around)


def hop_in_view(dx: int, dy: int, view: Viewport = HOST_VIEW) -> bool:
    """Whether a hop of (dx, dy) tiles lands in view from anywhere on the tile it starts from. The view
    is not round: it shows 23 world units up the screen and 18 down to the skill bar, so a gap that is
    crossed going up may not be crossed coming down. The potential counted five tiles every way, and a
    seek step stood still for good where the only way on was 21 units straight down the screen (host,
    19:19 on 2026-10-10, Catacombs 1). The window's own shape decides (`view`): a narrower window
    shows less to the sides (review.md, finding 8)."""
    return view.hop_in_view(dx, dy)


class Way:
    """The way to go from any spot, in tiles: a potential over the landable tiles of the level,
    Dijkstra from the mark's tile with hops of at most REACH_TILES between landable tiles, walls in
    between or not (a teleport crosses them). A tile is landable when its centre has footing by the
    read grids, or lies on a room no grid covers; the mark's tile always is. A hop is one the window
    shows (`view`, the same value the landing is chosen under), so every hop planned can be made."""

    def __init__(self, target: Target, view: Viewport = HOST_VIEW, far: bool = False) -> None:
        # Kept for the landing: built once here, where it was built anew for each of the 800-odd spots a
        # landing looks at (47-150 ms of every hop, and the recorder's late frames before a hop).
        ground = self.ground = Ground(target.ground)
        self.view = view
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
        # (dx, dy) leads from a tile to one a hop may come from: the hop itself is (-dx, -dy).
        self.reach = reach = FAR_TILES if far else REACH_TILES
        self.sees = sees = view.hop_between if far else view.hop_in_view
        offsets = [
            (dx, dy, math.hypot(dx, dy))
            for dx in range(-reach, reach + 1)
            for dy in range(-reach, reach + 1)
            if 0 < math.hypot(dx, dy) <= reach and sees(-dx, -dy)
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
                for dx in range(-self.reach, self.reach + 1)
                for dy in range(-self.reach, self.reach + 1)
                if (tx + dx, ty + dy) in self.cost and self.sees(dx, dy)
                for centre in [(tx + dx + 0.5, ty + dy + 0.5)]
                if math.dist(point, centre) <= self.reach
            ),
            default=math.inf,
        )


@lru_cache(maxsize=8)
def way_for(target: Target, view: Viewport = HOST_VIEW, far: bool = False) -> Way:
    """The potential of a target under a window's shape, kept across presses: rooms, grids, mark and
    window rarely change within a level."""
    return Way(target, view, far)


def spots_in_view(player: Player, aspect: float):
    """Ground points drawn across the view, in tiles, VIEW_STEP of the window apart."""
    (left, right), (top, _) = VIEW
    view = Viewport(aspect)
    columns, rows = int((right - left) / VIEW_STEP) + 1, int((CORNER_BOTTOM - top) / VIEW_STEP) + 1
    for column in range(columns):
        for row in range(rows):
            across, down = left + column * VIEW_STEP, top + row * VIEW_STEP
            if view.hop_view((across, down)):  # the rows beside the skill bar too, while the corners are on
                x, y = world_point(player, across, down, aspect)
                yield x / TILE_UNITS, y / TILE_UNITS


def landable(target: Target, way: Way, point: Point) -> bool:
    """Whether a hop may be aimed at `point` (tiles): footing by the read grids, else a room's rectangle."""
    known = footing(way.ground, point)
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
        if not way.view.hop_view(ground_fraction(player, *scaled(point), aspect)) or not landable(target, way, point):
            continue
        found.append((way.to_go(point), math.dist(point, start), point))
    # Only spots that take MIN_GAIN off the way: a spot beside the door with footing on a tile the way
    # does not count (its centre in the wall the stairs sit in) was the nearest "beside" spot, came out
    # as no gain, and sixteen teleport steps in a row stopped 16 units from the door (host, 19:29 on
    # 2026-10-10, Catacombs 1).
    found = [entry for entry in found if now - entry[0] >= MIN_GAIN / TILE_UNITS]
    if not found:
        return None
    beside = [entry for entry in found if math.dist(scaled(entry[2]), scaled(target.point)) <= APPROACH + 1.0]
    if target.warp and beside:  # a spot beside the door: the one nearest the character, on its side
        cost, _, spot = min(beside, key=lambda entry: entry[1])
    else:
        cost, _, spot = min(found)
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


def landed_from(player: Player, since: Player, aim: Point) -> bool:
    """Whether a hop aimed at `aim` (world units) has taken the character there: it has moved, and it
    stands or is near the aim. A character walking when the hop began moves before the hop does: the
    walk was taken for the landing ("landed …, off by 24" 0.2 s after the key, 2026-10-10 and after)."""
    if not moved(player, since):
        return False
    return player.area != since.area or player.mode not in WALKING or math.dist((player.x, player.y), aim) < MOVED


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


def box_aim(door: Point, warps: tuple[Warp, ...]) -> tuple[int, int] | None:
    """The middle of the click box of the door unit nearest `door` (the mark, world units), in classic
    pixels from the mark; None when no door unit is within WARP_NEAR of it or its box is not known.
    The tower's door in Black Marsh (host, 2026-10-10): the unit 6.5, 2.5 units from the mark, the box
    42 to 122 pixels above it, the aims 45 above on its edge (5 of 9 took)."""
    near = [warp for warp in warps if math.dist((warp.x, warp.y), door) <= WARP_NEAR]
    if not near:
        return None
    warp = min(near, key=lambda found: math.dist((found.x, found.y), door))
    box = warp_box(warp.warp)
    if box is None:
        return None
    dx, dy = warp.x - door[0], warp.y - door[1]
    return round((dx - dy) * 16 + (box[0] + box[2]) / 2), round((dx + dy) * 8 + (box[1] + box[3]) / 2)


def door_aims(target: Target, warps: tuple[Warp, ...] = ()) -> tuple[tuple[int, int], ...]:
    """The aims to try in turn: the middle of the door's own click box when the game shows the door
    (`box_aim`), then the one that took this door before (learnt, `AIMS`, else from KNOWN_AIMS), then
    the rest of DOOR_AIMS."""
    learnt = AIMS.offset(target)
    took = (round(learnt[0]), round(learnt[1])) if learnt is not None else KNOWN_AIMS.get(Entries.key(target))
    first = [aim for aim in (box_aim(scaled(target.point), warps), took) if aim is not None]
    return tuple(dict.fromkeys((*first, *DOOR_AIMS)))


def walk_into(run: Run, target: Target, player: Player, aspect: float) -> None:
    """Click the door and watch the walk: where the mark is, where the character started, how long and
    how far it walked and where it stood when the level changed (the last hop's landing is judged by
    the walk it leaves). The door's entry is where the character stood at the click when the first
    click took (a spot the door is proven to take a click from: the cellar stairs took it from 5.6
    units without a step), else where it stood when the level changed. With the game's record of the
    unit under the pointer (`run.hovered`) an aim is clicked only with a door under it; the aims that
    show none are looked at once more, then clicked as they are. An aim with another unit under
    the pointer waits for the others; after them all the first is made once more, from where the
    clicks on the ground left the character (the tower's door in Black Marsh, host, 20:12 on
    2026-10-10: nothing took from the remembered spot, the same aim took on the next press)."""
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
    last, walked, clicks = start, 0.0, 0

    def aim_at(aim: tuple[int, int]) -> bool:
        across, down = ground_fraction(player, *door, aspect)
        where = (across + aim[0] * UNIT_PIXELS[0] / 16 / aspect, down + aim[1] * UNIT_PIXELS[1] / 8)
        if not in_view(where):
            return False
        run.actuator.aim(*where, scatter=(4, 3))
        return True

    def under() -> tuple[int, int] | None:
        if run.hovered is None:
            return None
        run.pace.sleep(HOVER_SECONDS)
        return run.hovered()

    def click(aim: tuple[int, int], over: tuple[int, int] | None) -> bool:
        """A click where the pointer is, with the character free of its last cast, made again when it
        moved nobody; whether the level changed."""
        for again in range(DOOR_CLICKS):
            settle(run, 0.0, STILL_SECONDS)
            stood = (player.x, player.y)
            if press(aim, over):
                return True
            if math.dist((player.x, player.y), stood) >= MOVED:
                break  # a click on the ground: the door is not under this aim
            if again + 1 < DOOR_CLICKS:
                LOG.info('Macro: the click %s pixels from the door moved nobody; made again', aim)
        return False

    def press(aim: tuple[int, int], over: tuple[int, int] | None) -> bool:
        """One click where the pointer is; whether the level changed."""
        nonlocal player, last, walked, clicks
        clicks += 1
        stood = (player.x, player.y)
        run.actuator.click()
        deadline, still, stirred = run.clock() + DOOR_SECONDS, run.clock() + STILL_SECONDS, False
        while True:
            world = run.world()
            now = world.player
            if now is None or now.area != target.area:
                AIMS.learn(target, aim)
                offset = (last[0] - door[0], last[1] - door[1])
                if clicks == 1 and math.dist(stood, door) <= ENTRY_MAX:
                    offset = (stood[0] - door[0], stood[1] - door[1])  # proven: one click from here is the step in
                LOG.info('Macro: the door took the click %s pixels from its tiles; under the pointer %s', aim, over)
                LOG.info(
                    'Macro: door %s: in after %.2fs, walked %.1f from (%.1f, %.1f) to (%.1f, %.1f); the entry '
                    'at %+.1f, %+.1f from the mark, %.1f away (%s)',
                    target.label, run.clock() - began, walked, *start, *last, *offset, math.hypot(*offset),
                    'remembered' if math.hypot(*offset) <= ENTRY_MAX else 'not remembered: too far from the mark',
                )  # fmt: skip
                if math.hypot(*offset) <= ENTRY_MAX:
                    ENTRIES.learn(target, offset)
                run.say(f'{target.label}: there')
                return True
            here = (now.x, now.y)
            walked += math.dist(here, last)
            last = here
            stirred = stirred or here != stood
            if run.clock() >= deadline or (run.clock() >= still and not stirred):
                break  # no way in, or nobody moved: the click was swallowed
            run.pace.sleep(WALK_POLL)
        player = run.world().player or player  # the click on the ground walked the character
        LOG.info(
            'Macro: the door did not take the click %s pixels from its tiles; under the pointer %s; the character '
            'now at (%.1f, %.1f)',
            aim, over, player.x, player.y,
        )  # fmt: skip
        return False

    aims = door_aims(target, run.warps() if run.warps is not None else ())
    waiting, unseen = [], list(aims)
    for _ in range(LOOKS):
        looked, unseen = unseen, []
        for aim in looked:
            if not aim_at(aim):
                continue
            over = under()
            if over is None or over[0] == TILE_UNIT:
                if click(aim, over):
                    return
            elif over[0] in IN_THE_WAY:
                LOG.info('Macro: the aim %s pixels from the door has the unit %s under it; left for last', aim, over)
                waiting.append(aim)
            else:
                unseen.append(aim)
        if not unseen:
            break
    if unseen:
        LOG.info('Macro: no door under the pointer at the aims %s after %d looks; clicking them', unseen, LOOKS)
    for aim in (*unseen, *waiting, *aims[:1]):
        if aim_at(aim) and click(aim, under()):
            return
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


def clear_walk(ground: Ground, start: Point, end: Point, reach: float) -> bool:
    """Whether `end` is within `reach` of `start` over ground known to be walkable all the way (world units)."""
    away = math.dist(start, end)
    if away > reach:
        return False
    steps = max(1, math.ceil(away * 2))
    return all(
        ground.walkable(start[0] + (end[0] - start[0]) * k / steps, start[1] + (end[1] - start[1]) * k / steps)
        for k in range(steps + 1)
    )


CARD_POLL = 0.05
CARD_SECONDS = 1.2  # for the level card to follow the character into a new level (0.84 s the longest logged)


def card_for(run: Run, read: Callable[[], Target | None] | None, seconds: float = CARD_SECONDS) -> Target | None:
    """The level card's mark, waited for while the card is still the level just left: the service
    reads the new level's card 0.37 s after the arrival at the median (57 logged arrivals), and a
    step asked for meanwhile stopped with "the level card is for another level" (15 of 116 exits
    to 2026-10-10, and after both stairs of the first Worldstone Keep run)."""
    if read is None:
        return None
    until = run.clock() + seconds
    while True:
        target, player = read(), run.world().player
        if player is None or (target is not None and target.area == player.area) or run.clock() >= until:
            return target
        run.pace.sleep(CARD_POLL)


def step_toward(run: Run, target: Target | None, key_names) -> None:
    """One teleport step. `key_names(world, skills)` gives the key per skill (runner)."""
    player, rect = ready(run)
    if target is None:
        raise Abort('nothing is marked on the level card (Win+C shows it)')
    if target.area != player.area:
        raise Abort('the level card is for another level')
    if target.kind == 'previous':
        # The way back is the first mark only where nothing leads on: the step after the door into
        # Tower Cellar 5 clicked the stairs back up to level 4 (host, 20:06 on 2026-10-10).
        raise Abort(f'the only way marked is back to {target.label}')
    aspect = rect[2] / rect[3]
    here = (player.x, player.y)
    entry = entry_spot(target)
    if entry is not None and math.dist(here, scaled(entry)) <= ENTRY_NEAR:
        at_door = True  # on the door's own spot: clicked from here
    elif entry is not None and clear_walk(Ground(target.ground), here, scaled(entry), ENTRY_WALK):
        at_door = True  # a few steps straight to the spot: the click walks them, and a hop is saved
    elif entry is not None and entry_in_view(target, player, way_for(target, Viewport(aspect)), aspect) is not None:
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
    # The far potential first (hops over a cliff the window shows across), the old one when that
    # finds no landing from here, and from then on for this target.
    key = (target.area, math.floor(target.point[0]), math.floor(target.point[1]))
    here = (player.x / TILE_UNITS, player.y / TILE_UNITS)
    found = None
    if key not in FAR_FAILED:
        way = way_for(target, Viewport(aspect), True)
        found = landing(target, player, way, aspect) if way.from_here(here) < math.inf else None
        if found is None:
            if len(FAR_FAILED) > 64:
                FAR_FAILED.clear()
            FAR_FAILED.add(key)
            LOG.info(
                'Macro: no landing by the far way to %s from (%.1f, %.1f): the near way',
                target.label,
                player.x,
                player.y,
            )
    if found is None:
        way = way_for(target, Viewport(aspect))
        if way.from_here(here) == math.inf:
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
    if run.seen(lambda w: w.player is not None and landed_from(w.player, player, aim), HOP_SECONDS) is None:
        after, now = run.world(), run.teleport() if run.teleport is not None else None
        LOG.info(
            'Macro: teleport %s; the character did not move: key %s, slots %s, staff %s, mode now %s, right skill %s',
            where, run.keys.get(TELEPORT), world_slots(after), now,
            after.player.mode if after.player else None, after.player.right_skill if after.player else None,
        )  # fmt: skip
        if not in_view(ground_fraction(player, *aim, aspect)) and CORNERS[0]:
            # Aimed beside the skill bar and nothing came: the game takes no cast there after all.
            CORNERS[0] = False
            way_for.cache_clear()
            LOG.info('Macro: a teleport aimed beside the skill bar did nothing: the corners are left alone from now on')
            raise Abort('Teleport: nothing came of an aim beside the skill bar (not tried there again)')
        if staff is not None and now is not None and now.in_hand and now.charges == staff.charges > 0:
            # The staff in hand, no charge spent: the key cast nothing. The game drops Teleport from its
            # key when a game is left with the staff in hand (user, 2026-10-11; 01:26 that night: three
            # steps in a row, until the key was bound again in the skill list).
            raise Abort(LOST_KEY)
        raise Abort('Teleport: the character did not move (no charges, nowhere to land?)')
    landed = run.world().player
    if landed is not None:
        off = (landed.x - aim[0], landed.y - aim[1])
        LOG.info(
            'Macro: teleport %s; landed at (%.1f, %.1f), off by %.1f (%+.1f, %+.1f)',
            where, landed.x, landed.y, math.hypot(*off), *off,
        )  # fmt: skip
