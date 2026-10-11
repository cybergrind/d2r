"""Route situations on recorded levels: a reference planner, a game that honours the walls, and the run
of the production planner hop by hop.

The reference counts hops, nothing else: the fewest teleports from a spot to within ARRIVE of a mark over
the level's real footing. Its rules are read out of the production code, none is its own:

- A hop may land where the window shows ground: `Viewport.in_view(Viewport.ground(origin, x, y))`, the
  test `teleport.landing` puts every candidate through. In world units that is a box in (x - y, x + y)
  around the character (`reach_box`): wider than high, and reaching further up the screen than down.
- A landing has footing: `teleport.footing`, the sub-tile walkable and no sub-tile a unit around it known
  to be a wall. The character's own spot needs none (`Way.from_here`).
- Nothing between the two ends counts: a teleport crosses walls (`Way`: "walls in between or not").
- A spot is where the character stands, a sub-tile's centre: the landings in the logs are all at x.5.

The production planner works under two limits of its own that the reference does not share: its potential
steps between 5-unit tiles and by at most REACH_TILES of them, and counts the way in units, not in hops.

`WalledGame` is the scripted game of the macro tests with the level's real ground under it: a teleport
aimed at a spot without footing moves nobody. What the real game does there (it may put the character
beside the spot instead) is not in the logs: every logged hop was aimed at known footing.
"""

import gzip
import json
import math
import time
from dataclasses import dataclass, field, replace
from functools import lru_cache
from itertools import pairwise
from pathlib import Path

from inventory_tracking.levels.model import Ground, Room, Target, Walkable, unpack_cells
from inventory_tracking.macros import teleport
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.view import Viewport
from inventory_tracking.macros.world import Teleport
from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.macros.fakes import KEYS, WINDOW, Game, player, world


Point = tuple[float, float]
Cell = tuple[int, int]  # a sub-tile: the world unit square whose corner it names
FIXTURES = Path(__file__).parent / 'fixtures'
HOST_ASPECT = WINDOW[2] / WINDOW[3]  # the host's window, as the macro tests' fake
ARRIVE = 5.0  # world units from the mark at which a route has arrived: one tile
HOP_LIMIT = 60  # steps a run of the production planner is given
SAME_AIM = 2.0  # world units: two refused aims this near are the same one (the aim scatters a little)
REACH_SPAN = 80  # world units no window reaches: the search for the box's sides stops here


def reach_box(view: Viewport) -> tuple[int, int, int, int]:
    """(least, most) of x - y and (least, most) of x + y, in whole world units, a hop may span under
    `view` between two sub-tile centres: what `Viewport.in_view` passes of `Viewport.ground`, the
    test `teleport.landing` puts every candidate through. The game lands the character on the centre
    of the sub-tile clicked, so a click on the last sliver of a sub-tile in view reaches up to a unit
    further than this: the reference does not count on it."""

    def furthest(across: int, down: int) -> int:
        span = 0
        while span < REACH_SPAN and view.in_view(
            view.ground((0.0, 0.0), (across + down) * (span + 1) / 2, (down - across) * (span + 1) / 2)
        ):
            span += 1
        return span

    return -furthest(-1, 0), furthest(1, 0), -furthest(0, -1), furthest(0, 1)


def _spread_bits(row: int, low: int, high: int) -> int:
    """The bits of `row` moved up by every count from `low` to `high` (down where negative), OR-ed."""
    width, found, have = high - low + 1, row, 1
    while have * 2 <= width:
        found |= found << have
        have *= 2
    found |= found << (width - have)
    return found << low if low >= 0 else found >> -low


def _spread_rows(rows: list[int], low: int, high: int) -> list[int]:
    """Row i of the result is rows i + low to i + high OR-ed (rows off either end are empty)."""
    count, width = len(rows), high - low + 1
    before = max(-low, 0)
    found = [0] * before + list(rows) + [0] * (width + max(high, 0))
    have = 1
    while have * 2 <= width:
        found = [found[i] | found[i + have] for i in range(len(found) - have)]
        have *= 2
    rest = width - have
    found = [found[i] | found[i + rest] for i in range(len(found) - rest)]
    return [found[i + low + before] for i in range(count)]


class Footing:
    """The sub-tiles of a level a teleport may land on, by `teleport.footing`, as one bit each.

    The bits are laid out by the window's own axes: row x + y, bit x - y. A hop's box (`reach_box`) is
    then a plain rectangle, and one hop from a whole set of spots is two runs of shifts.
    """

    def __init__(self, ground: Ground) -> None:
        grids = ground.grids
        self.x = min(grid.x for grid in grids) * TILE_UNITS
        self.y = min(grid.y for grid in grids) * TILE_UNITS
        self.width = max(grid.x + grid.width for grid in grids) * TILE_UNITS - self.x
        self.height = max(grid.y + grid.height for grid in grids) * TILE_UNITS - self.y
        walk = [0] * self.height  # by world row, bit = column
        wall = [0] * self.height
        for grid in grids:
            columns, rows = grid.width * TILE_UNITS, grid.height * TILE_UNITS
            bits = unpack_cells(grid.cells, columns * rows)
            if bits is None:
                continue
            left, top = grid.x * TILE_UNITS - self.x, grid.y * TILE_UNITS - self.y
            full = (1 << columns) - 1
            for row in range(rows):
                # The first sub-tile of a row is its first character: bit `column` is character `column`.
                line = int(bits[row * columns : (row + 1) * columns][::-1], 2)
                walk[top + row] |= line << left
                wall[top + row] |= (line ^ full) << left
        near = [_spread_bits(row, -1, 1) for row in wall]
        near = _spread_rows(near, -1, 1)
        self.cells = [walk[row] & ~near[row] for row in range(self.height)]
        self.rows = [0] * (self.width + self.height)
        for row, line in enumerate(self.cells):
            while line:
                lowest = line & -line
                column = lowest.bit_length() - 1
                self.rows[column + row] |= 1 << (column - row + self.height)
                line ^= lowest

    def cell(self, point: Point) -> Cell:
        return math.floor(point[0]) - self.x, math.floor(point[1]) - self.y

    def has(self, point: Point) -> bool:
        column, row = self.cell(point)
        return 0 <= row < self.height and column >= 0 and bool(self.cells[row] >> column & 1)

    def spot(self, row: int, bit: int) -> Point:
        """The world point of a bit: the centre of its sub-tile."""
        across = bit - self.height
        return (row + across) / 2 + self.x + 0.5, (row - across) / 2 + self.y + 0.5

    def near(self, point: Point, within: float) -> list[Point]:
        """The spots with footing at most `within` world units from `point`."""
        reach = math.ceil(within)
        found = []
        for dx in range(-reach, reach + 1):
            for dy in range(-reach, reach + 1):
                spot = (math.floor(point[0]) + dx + 0.5, math.floor(point[1]) + dy + 0.5)
                if math.dist(spot, point) <= within and self.has(spot):
                    found.append(spot)
        return found


class HopField:
    """The fewest hops to within `arrive` of `mark` from every spot with footing: breadth first from the
    mark's side, a whole layer at a time (`layers[k]` holds the spots k hops away)."""

    def __init__(
        self,
        footing: Footing,
        mark: Point,
        view: Viewport,
        arrive: float = ARRIVE,
        ends: list[Point] | None = None,
    ) -> None:
        """`ends`: the spots that end the route, when they are not simply those within `arrive` of the
        mark (a hunt ends wherever the monster can be struck from)."""
        self.footing, self.mark, self.view, self.arrive = footing, mark, view, arrive
        self.box = reach_box(view)
        low_across, high_across, low_down, high_down = self.box
        rows = [0] * len(footing.rows)
        for spot in footing.near(mark, arrive) if ends is None else ends:
            column, row = footing.cell(spot)
            rows[column + row] |= 1 << (column - row + footing.height)
        self.layers = [rows]
        seen = list(rows)
        edge = rows
        while any(edge):
            # A spot is one hop from the edge when the edge has a spot inside the box around it.
            wide = _spread_rows(edge, low_down, high_down)
            edge = [
                _spread_bits(wide[i], -high_across, -low_across) & footing.rows[i] & ~seen[i] if wide[i] else 0
                for i in range(len(rows))
            ]
            if any(edge):
                self.layers.append(edge)
                seen = [seen[i] | edge[i] for i in range(len(rows))]

    def at(self, point: Point) -> int | None:
        """Hops left from a spot with footing; None when it has none or no way leads on."""
        column, row = self.footing.cell(point)
        if not (0 <= column + row < len(self.footing.rows)) or column - row + self.footing.height < 0:
            return None
        bit = 1 << (column - row + self.footing.height)
        return next((count for count, layer in enumerate(self.layers) if layer[column + row] & bit), None)

    def in_reach(self, point: Point) -> list[tuple[int, Point]]:
        """(hops left, spot) of every spot one hop from `point` that a way leads on from."""
        low_across, high_across, low_down, high_down = self.box
        column, row = self.footing.cell(point)
        here, bit = column + row, column - row + self.footing.height
        found = []
        lowest_bit = max(bit + low_across, 0)
        mask = ((1 << (bit + high_across - lowest_bit + 1)) - 1) << lowest_bit
        for there in range(max(here + low_down, 0), min(here + high_down, len(self.footing.rows) - 1) + 1):
            for count, layer in enumerate(self.layers):
                line = layer[there] & mask
                while line:
                    lowest = line & -line
                    found.append((count, self.footing.spot(there, lowest.bit_length() - 1)))
                    line ^= lowest
        return found

    def hops(self, start: Point) -> int | None:
        """The fewest hops from `start`, which needs no footing itself; 0 within `arrive` of the mark."""
        if math.dist(start, self.mark) <= self.arrive:
            return 0
        known = self.at(start)
        if known is not None:
            return max(known, 1)  # its sub-tile's centre is within `arrive`, the spot itself is not
        return min((count + 1 for count, _ in self.in_reach(start)), default=None)

    def route(self, start: Point) -> list[Point] | None:
        """One route of the fewest hops: of the spots that keep the count, each hop takes the one
        nearest the mark, so the route is short without being proven the shortest."""
        left = self.hops(start)
        if left is None:
            return None
        found, here = [start], start
        while left > 0:
            ahead = [spot for count, spot in self.in_reach(here) if count == left - 1]
            here = min(ahead, key=lambda spot: math.dist(spot, self.mark))
            found.append(here)
            left -= 1
        return found


@dataclass(frozen=True)
class Situation:
    """A start and a mark on a recorded level. `hidden` names rooms (by index) whose walls the planner is
    not given, as a room the game had not loaded: the game under it still has them."""

    name: str
    area: int
    rooms: tuple[Room, ...]
    ground: tuple[Walkable, ...]
    start: Point  # world units
    mark: Point  # world units
    aspect: float = HOST_ASPECT
    hidden: tuple[int, ...] = ()
    source: str = ''  # the take the level was cut from, and the log line of the real journey if any
    note: str = ''
    recorded_hops: int | None = None  # hops the macro really made on this journey, by the log
    arrive: float = ARRIVE  # world units from the mark at which the route has arrived

    @property
    def window(self) -> tuple[int, int, int, int]:
        return WINDOW[0], WINDOW[1], round(WINDOW[3] * self.aspect), WINDOW[3]

    @property
    def view(self) -> Viewport:
        return Viewport.of(self.window)

    @property
    def target(self) -> Target:
        """What the production planner is given: every room, and the grids of the rooms not hidden."""
        covered = {(room.x, room.y) for index, room in enumerate(self.rooms) if index in self.hidden}
        known = tuple(grid for grid in self.ground if (grid.x, grid.y) not in covered)
        mark = (self.mark[0] / TILE_UNITS, self.mark[1] / TILE_UNITS)
        return Target(self.area, self.rooms, mark, 'the mark', 'hunt', False, known)


def load(name: str) -> Situation:
    path = FIXTURES / f'{name}.json'
    if path.exists():
        found = json.loads(path.read_text())
    else:
        with gzip.open(path.with_suffix('.json.gz'), 'rt', encoding='utf-8') as handle:
            found = json.load(handle)
    return Situation(
        name=name,
        area=found['area'],
        rooms=tuple(Room.from_row(row) for row in found['rooms']),
        ground=tuple(Walkable(*grid) for grid in found['ground']),
        start=tuple(found['start']),
        mark=tuple(found['mark']),
        aspect=found.get('aspect', HOST_ASPECT),
        hidden=tuple(found.get('hidden', ())),
        source=found.get('source', ''),
        note=found.get('note', ''),
        recorded_hops=found.get('recorded_hops'),
        arrive=found.get('arrive', ARRIVE),
    )


def names() -> list[str]:
    return sorted(path.name.split('.')[0] for path in FIXTURES.glob('*.json*'))


@lru_cache(maxsize=32)
def footing_of(ground: tuple[Walkable, ...]) -> Footing:
    return Footing(Ground(ground))


@lru_cache(maxsize=64)
def field_of(situation: Situation) -> HopField:
    return HopField(footing_of(situation.ground), situation.mark, situation.view, situation.arrive)


class WalledGame(Game):
    """The scripted game over a level's real ground: a teleport aimed at a sub-tile that is not walkable
    moves nobody. The game asks less than `teleport.footing` does: of the logged hops whose level was
    recorded, five landed a sub-tile from a wall (the aim scatters by a few pixels) and four of them
    landed on the aim."""

    def __init__(self, situation: Situation) -> None:
        start = player(situation.area, x=situation.start[0], y=situation.start[1])
        super().__init__(world(situation.area, player=start))
        self.ground = Ground(situation.ground)
        self.window = situation.window
        self.keys.focused_window_rect = lambda: self.window
        self.keys.fraction = self.fraction
        self.refused: list[Point] = []  # spots a teleport was aimed at that are not walkable

    def fraction(self) -> Point:
        x, y, width, height = self.window
        return (self.keys.at[0] - x) / width, (self.keys.at[1] - y) / height

    def ground_under_pointer(self) -> Point:
        here = self.world.player
        return Viewport.of(self.window).world((here.x, here.y), *self.fraction())

    def react(self, event) -> None:
        if event == ('key', KEYS[teleport.TELEPORT]) and self.world.in_game:
            spot = self.ground_under_pointer()
            if not self.ground.walkable(*spot):
                self.refused.append(spot)
                return
            super().react(event)
            here = self.world.player  # the sub-tile's centre: every landing in the logs is at x.5
            self.world = replace(self.world, player=replace(here, x=int(here.x) + 0.5, y=int(here.y) + 0.5))
            return
        super().react(event)


@dataclass
class Trip:
    """What the production planner did with a situation, and what the reference says of it."""

    situation: Situation
    spots: list[Point] = field(default_factory=list)  # where the character stood: the start, then each landing
    presses: int = 0  # teleports cast, landed or not
    refused: list[Point] = field(default_factory=list)  # aims without footing: a charge and a wait for nothing
    stopped: str = ''  # why the run ended short of the mark, in the planner's own words
    planning: float = 0.0  # seconds of the planner's own work, the game's waits not counted
    reference: int | None = None

    @property
    def hops(self) -> int:
        return len(self.spots) - 1

    @property
    def arrived(self) -> bool:
        return math.dist(self.spots[-1], self.situation.mark) <= self.situation.arrive

    @property
    def distance(self) -> float:
        return sum(math.dist(a, b) for a, b in pairwise(self.spots))

    @property
    def over(self) -> int | None:
        return None if self.reference is None else self.presses - self.reference

    @property
    def reference_distance(self) -> float | None:
        """World units of one route of the fewest hops (`HopField.route`)."""
        route = field_of(self.situation).route(self.situation.start)
        return None if route is None else sum(math.dist(a, b) for a, b in pairwise(route))

    def lost(self) -> list[tuple[int, Point, int, int]]:
        """(hop number, where from, hops the reference had left before, and after) of every hop that
        did not take one off the reference's count: where the jumps went."""
        field_ = field_of(self.situation)
        found = []
        for number, (before, after) in enumerate(pairwise(self.spots), 1):
            had, has = field_.hops(before), field_.hops(after)
            if had is not None and has is not None and has > had - 1:
                found.append((number, before, had, has))
        return found

    def line(self) -> str:
        reference = 'no way' if self.reference is None else str(self.reference)
        ended = 'arrived' if self.arrived else f'stopped {math.dist(self.spots[-1], self.situation.mark):.0f} short'
        return (
            f'{self.situation.name}: production {self.presses} hops ({ended}, {self.distance:.0f} units'
            f'{f", {len(self.refused)} into walls" if self.refused else ""}), reference {reference}'
            f'{f", recorded {self.situation.recorded_hops}" if self.situation.recorded_hops else ""}'
        )


def keys(_world, skills):
    return {skill: KEYS[skill] for skill in skills}


def run_production(situation: Situation, limit: int = HOP_LIMIT) -> Trip:
    """The production planner asked for one hop after another (`teleport.hop_toward`, the step the
    teleport and seek actions share) until the character is within ARRIVE of the mark, the planner
    has nothing more to offer, or the same aim was refused twice. The game's waits run on the
    scripted clock, so the seconds measured are the planner's own."""
    game = WalledGame(situation)
    game.staff = Teleport(10_000, 10_000, True)
    target = situation.target
    trip = Trip(situation, [situation.start], reference=field_of(situation).hops(situation.start))
    began = time.perf_counter()
    while not trip.arrived and trip.presses < limit:
        try:
            teleport.hop_toward(game.run(), target, game.world.player, game.window, keys)
        except Abort as stop:
            trip.stopped = str(stop)
            if len(game.refused) == len(trip.refused):
                break
            trip.presses += 1
            trip.refused = list(game.refused)
            if len(trip.refused) >= 2 and math.dist(trip.refused[-1], trip.refused[-2]) < SAME_AIM:
                break  # the same wall again: the planner has no other answer from here
            continue
        trip.presses += 1
        now = game.world.player
        trip.spots.append((now.x, now.y))
    trip.planning = time.perf_counter() - began
    return trip
