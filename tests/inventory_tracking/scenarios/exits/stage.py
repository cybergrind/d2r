"""The stage for the exit scenarios: a recorded level, a game that walks and teleports over its walls,
and a player who asks for the teleport step again and again.

The levels are cut from combat takes (`fixtures/*.json`: the rooms, the walkable and flight grids, the
door units as first seen). The mark is found the way the level card finds it (`card_target`).

What the faked game does, and where each number comes from (`evidence.py` over the logs of
2026-10-09 and 10):

- A teleport lands CAST_SECONDS after its key, where the pointer was at the key, when the ground there
  can be walked on; else nobody moves. The character reads as casting meanwhile.
- A click on the door's box walks the character to the door's spot over the walkable sub-tiles, round
  walls and closed doors, at WALK_SPEED; ENTER_SECONDS after it gets there the level changes. A click
  made standing within STAND_TAKE of the mark with open ground to the spot takes without a step (the
  Catacombs' stairs took 42 logged clicks so, in 0.15-0.29 s, from up to 5.8 away). With no way to the spot
  the character stands.
- The door's spot is the mark + (0, 3) in the Catacombs: where the character last stood in 44 of the 56
  takes that end at the stairs (the other 12 up to 5 units west of it).
- A click on plain ground walks the character there.
- The record of the unit under the pointer is (5, id) on a door's box (12 of 12 logged takes), (1, id)
  on a monster's body, else (0, 0).

UNVERIFIED in the game: what a click on a door does with a closed door in the way (here: the character
stands at the door), and the exact reach of STAND_TAKE.
"""

import heapq
import json
import math
from dataclasses import dataclass, field, replace
from functools import cache
from itertools import pairwise
from pathlib import Path

from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.exits import guide_level
from inventory_tracking.levels.level_map import centre
from inventory_tracking.levels.model import Ground, LevelSnapshot, Location, Room, Target, Walkable
from inventory_tracking.levels.registry import handler_for
from inventory_tracking.levels.spots import WAYS_OUT, pinpoint
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.teleport import card_for, step_toward
from inventory_tracking.macros.world import Monster, Teleport
from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.macros.fakes import KEYS, Game, player, world


FIXTURES = Path(__file__).parent / 'fixtures'
CAST_SECONDS = 0.2  # the Teleport key to the landing (0.22-0.26 s in the log, the reads included)
WALK_SPEED = 19.0  # world units a second (walks of 6-10 units took 0.42-0.73 s, 0.2 s of it the door)
ENTER_SECONDS = 0.2  # at the door's spot to the next level (0.21 s the median of 42 clicks with no walk)
STAND_TAKE = 6.0  # world units from the mark a standing character is taken from
DOOR_BOX = 5.0  # world units round the mark's ground (lifted by `door_above`) where a click is on the door
SPOT = (0.0, 3.0)  # the Catacombs' stairs: the door's spot from the mark
WALK_REACH = 45.0  # world units round the door a walk is searched over
WARP_UNIT = 5  # the unit type of a level's door in the record of the unit under the pointer


def keys(_world, skills):
    return {skill: KEYS[skill] for skill in skills}


@dataclass(frozen=True)
class Stage:
    """A recorded level with the mark the level card leads with."""

    name: str
    area: int
    rooms: tuple[Room, ...]
    grids: tuple[Walkable, ...]
    doors: tuple[Door, ...]
    arrived_at: tuple[float, float]  # where the recorded character came into the level
    ground: Ground = field(compare=False, repr=False, default=None)

    @property
    def target(self) -> Target:
        return card_target(self.area, self.rooms, self.grids)

    @property
    def mark(self) -> tuple[float, float]:
        """The door's mark in world units."""
        point = self.target.point
        return point[0] * TILE_UNITS, point[1] * TILE_UNITS

    @property
    def spot(self) -> tuple[float, float]:
        """Where the game walks a clicked character to (world units)."""
        return self.mark[0] + SPOT[0], self.mark[1] + SPOT[1]

    def off(self, dx: float, dy: float) -> tuple[float, float]:
        """A world point given from the mark."""
        return self.mark[0] + dx, self.mark[1] + dy


@cache
def card_target(area: int, rooms: tuple[Room, ...], grids: tuple[Walkable, ...]) -> Target | None:
    """The level card's first mark, as levels/guide.LevelGuide.target makes it from the rooms read."""
    snapshot = LevelSnapshot(Location(area, 0, 0, 0), rooms)
    pois = tuple(pinpoint(poi) for poi in guide_level(handler_for(area), snapshot).pois)
    if not pois:
        return None
    poi = pois[0]
    warp = poi.kind in WAYS_OUT and poi.spot is not None
    return Target(area, rooms, poi.spot or centre(poi.room), poi.label, poi.kind, warp, grids)


@cache
def stage(name: str) -> Stage:
    found = json.loads((FIXTURES / f'{name}.json').read_text())
    rooms = tuple(
        Room(
            row['preset'], row['x'], row['y'], row['width'], row['height'], row.get('variant'),
            tuple(row['block']) if row.get('block') else None, tuple(row.get('leads_to', ())),
        )
        for row in found['rooms']
    )  # fmt: skip
    grids = tuple(Walkable(**grid) for grid in found['ground'])
    doors = tuple(Door(index + 1, txt, mode, x, y) for index, (txt, mode, x, y) in enumerate(found['doors']))
    return Stage(name, found['area'], rooms, grids, doors, tuple(found['arrived_at']), Ground(grids))


def walk_path(ground: Ground, doors, start, end) -> list[tuple[float, float]] | None:
    """The shortest way from `start` to `end` over walkable sub-tiles, past no closed door; None without one."""
    closed = [door for door in doors if door.closed]
    first, goal = (math.floor(start[0]), math.floor(start[1])), (math.floor(end[0]), math.floor(end[1]))

    def free(cell) -> bool:
        centre_ = (cell[0] + 0.5, cell[1] + 0.5)
        return (
            math.dist(centre_, end) <= WALK_REACH
            and ground.walkable(*centre_) is True
            and not any(door.blocks(centre_) for door in closed)
        )

    if not free(goal):
        return None
    cost, came, queue = {first: 0.0}, {}, [(0.0, first)]
    while queue:
        so_far, cell = heapq.heappop(queue)
        if cell == goal:
            break
        if so_far > cost[cell]:
            continue
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                there = (cell[0] + dx, cell[1] + dy)
                if (
                    (dx or dy)
                    and free(there)
                    and (not (dx and dy) or (free((there[0], cell[1])) and free((cell[0], there[1]))))
                ):
                    step = so_far + math.hypot(dx, dy)
                    if step < cost.get(there, math.inf):
                        cost[there], came[there] = step, cell
                        heapq.heappush(queue, (step, there))
    if goal not in cost:
        return None
    cells = [goal]
    while cells[-1] != first:
        cells.append(came[cells[-1]])
    return [start, *((x + 0.5, y + 0.5) for x, y in reversed(cells[:-1])), end]


def open_line(ground: Ground, doors, start, end) -> bool:
    closed = [door for door in doors if door.closed]
    steps = max(1, math.ceil(math.dist(start, end) * 2))
    points = [
        (start[0] + (end[0] - start[0]) * k / steps, start[1] + (end[1] - start[1]) * k / steps)
        for k in range(steps + 1)
    ]
    return all(ground.walkable(*point) is True and not any(door.blocks(point) for door in closed) for point in points)


class LevelGame(Game):
    """The faked game on a recorded level (the module's docstring has its rules)."""

    def __init__(
        self, level: Stage, start, *, charges: int = 40, next_area: int | None = None, beyond: Stage | None = None
    ) -> None:
        super().__init__(
            replace(world(level.area), player=player(level.area, x=start[0], y=start[1]), doors=level.doors)
        )
        self.level = level
        self.ground = level.ground
        self.staff = Teleport(charges, 69, True)
        self.beyond = beyond  # the level behind the door, when the scenario goes on there
        self.next_area = (beyond.area if beyond else level.area + 1) if next_area is None else next_area
        self.next_start = beyond.arrived_at if beyond else (22595.5, 9617.5)  # where the stairs put the character
        self.box: tuple[float, float] | None = level.mark  # the door's ground; None: the level has no door on
        self.spot = level.spot
        self.walk = None  # (points, when it began, whether the door is at its end)
        self.hops: list[tuple[tuple[float, float], tuple[float, float]]] = []  # (from, to) per landing
        self.door_clicks = 0
        self.ground_clicks: list[tuple[float, float]] = []
        self.walked = 0.0
        self.entered_at: float | None = None
        self.on_enter = lambda: None

    # --- what the macro's events do ---

    def react(self, event):
        self.read()
        w = self.world
        if not w.in_game or w.open_panels or self.deaf:
            return super().react(event)
        if event == ('key', KEYS[TELEPORT]):
            self.cast()
        elif event[0] == 'click' and not self.keys.shift:
            self.clicked()
        else:
            super().react(event)

    def cast(self) -> None:
        w = self.world
        if self.staff is None or not self.staff.in_hand or self.staff.charges <= 0 or self.acting_until is not None:
            return
        aim, start = self.ground_under_pointer(), (w.player.x, w.player.y)
        if self.ground.walkable(*aim) is False:
            return
        self.walk = None
        self.staff = replace(self.staff, charges=self.staff.charges - 1)
        self.world = replace(w, player=replace(w.player, mode=10))
        self.acting_until = self.clock.now + CAST_SECONDS

        def land() -> None:
            self.hops.append((start, aim))
            self.world = replace(self.world, player=replace(self.world.player, x=aim[0], y=aim[1]))

        self.arrivals.append((self.clock.now + CAST_SECONDS, land))
        self.arrivals.sort(key=lambda arrival: arrival[0])

    def on_door(self) -> bool:
        """Whether the pointer is on the door's box."""
        if self.box is None:
            return False
        gx, gy = self.ground_under_pointer()
        lift = self.door_above / 16
        return math.dist((gx + lift, gy + lift), self.box) < DOOR_BOX

    def clicked(self) -> None:
        here = (self.world.player.x, self.world.player.y)
        if self.on_door():
            self.door_clicks += 1
            doors = self.world.doors
            if math.dist(here, self.box) <= STAND_TAKE and open_line(self.ground, doors, here, self.spot):
                self.walk = ([here], self.clock.now, True)
                return
            path = walk_path(self.ground, doors, here, self.spot)
            if path is None:  # no way there: up to the closed door at most, and no further
                reach = self.reachable_toward(here, self.spot)
                self.walk = None if reach is None else (reach, self.clock.now, False)
            else:
                self.walk = (path, self.clock.now, True)
            return
        aim = self.ground_under_pointer()
        self.ground_clicks.append(aim)
        path = walk_path(self.ground, self.world.doors, here, aim) if math.dist(here, aim) < 40 else None
        self.walk = None if path is None else (path, self.clock.now, False)

    def reachable_toward(self, here, end):
        """The straight walk toward `end` as far as open ground goes."""
        away = math.dist(here, end)
        points = [here]
        for k in range(1, math.ceil(away) + 1):
            point = (here[0] + (end[0] - here[0]) * k / away, here[1] + (end[1] - here[1]) * k / away)
            if not open_line(self.ground, self.world.doors, points[-1], point):
                break
            points.append(point)
        return points if len(points) > 1 else None

    # --- what happens on its own ---

    def read(self):
        if self.walk is not None and self.world.in_game and self.world.player is not None:
            points, began, door = self.walk
            gone = (self.clock.now - began) * WALK_SPEED
            length = sum(math.dist(a, b) for a, b in pairwise(points))
            at, left = points[-1], min(gone, length)
            for a, b in pairwise(points):
                part = math.dist(a, b)
                if left <= part:
                    at = (a[0] + (b[0] - a[0]) * left / part, a[1] + (b[1] - a[1]) * left / part) if part else a
                    break
                left -= part
            before = self.world.player
            self.walked += math.dist((before.x, before.y), at)
            self.world = replace(self.world, player=replace(before, x=at[0], y=at[1]))
            if gone >= length:
                if not door:
                    self.walk = None
                elif self.clock.now >= began + length / WALK_SPEED + ENTER_SECONDS:
                    self.walk = None
                    self.enter()
        return super().read()

    def enter(self) -> None:
        self.entered_at = self.clock.now
        x, y = self.next_start
        after = self.beyond
        self.world = replace(
            self.world,
            player=replace(self.world.player, area=self.next_area, x=x, y=y),
            monsters=(),
            doors=after.doors if after else (),
        )
        self.box = None
        if after is not None:
            self.level, self.ground = after, after.ground
            if after.target is not None and after.target.kind != 'previous':
                self.box, self.spot = after.mark, after.spot
        self.on_enter()

    def run(self, seed=1):
        run = super().run(seed)
        run.hovered = self.hovered
        return run

    def hovered(self) -> tuple[int, int]:
        x, y = self.under_pointer()
        for monster in self.world.monsters:
            if math.dist((monster.x, monster.y), (x, y)) < 2.5:
                return (1, monster.unit_id)
        return (WARP_UNIT, 4242) if self.on_door() else (0, 0)


class Card:
    """The level card between the service's reads: the mark of the level it last read, read again `lag`
    seconds after the character changed level (0.37 s the median of 57 logged arrivals, 0.84 the longest)."""

    def __init__(self, play: LevelGame, lag: float = 0.37) -> None:
        self.play, self.lag = play, lag
        self.shown = play.level
        self.changed: float | None = None

    def __call__(self) -> Target | None:
        now = self.play.level
        if now is not self.shown:
            if self.changed is None:
                self.changed = self.play.entered_at
            if self.play.clock.now - self.changed >= self.lag:
                self.shown, self.changed = now, None
        return self.shown.target


def hostile(unit: int, at, txt: int = 61) -> Monster:
    return Monster(unit, txt, 1, at[0], at[1], 0xFFFFFFFF, life=100, max_life=100)


@dataclass
class Outcome:
    """What a run of steps cost: the measures the scenarios assert."""

    presses: int = 0  # steps asked for
    hops: int = 0  # teleports that landed (a charge each)
    clicks: int = 0  # clicks on the door's box
    strays: int = 0  # clicks that went to plain ground
    seconds: float = 0.0  # by the faked clock, from the first press to the next level (or the last step's end)
    stops: list[str] = field(default_factory=list)
    entered: bool = False
    walked: float = 0.0
    landings: list[tuple[float, float]] = field(default_factory=list)


def press(play: LevelGame, card, outcome: Outcome | None = None, *, seed: int = 1) -> Outcome:
    """One teleport step, as the runner makes it: the mark the card shows at that moment, a stop shown
    where the step stops. THE SEAM: a change that lets a step wait for the card or go on to the click
    after its hop changes nothing here as long as `step_toward(run, target, key_names)` stays."""
    outcome = outcome or Outcome()
    hops, began = len(play.hops), play.clock.now
    outcome.presses += 1
    try:
        run = play.run(seed + outcome.presses)
        step_toward(run, card_for(run, card), keys)
    except Abort as stop:
        outcome.stops.append(str(stop))
    play.read()
    outcome.hops += len(play.hops) - hops
    outcome.landings += [landed for _, landed in play.hops[hops:]]
    outcome.clicks, outcome.strays, outcome.walked = play.door_clicks, len(play.ground_clicks), play.walked
    outcome.entered = play.entered_at is not None
    outcome.seconds += (play.entered_at if outcome.entered and play.entered_at >= began else play.clock.now) - began
    return outcome


def to_the_door(play: LevelGame, limit: int = 8, *, think: float = 0.0, seed: int = 1) -> Outcome:
    """The player taps the action until the next level or a stop, at most `limit` times; a tap made
    during a step queues the next one, so no time passes between them (`think` adds some)."""
    outcome = Outcome()
    target = play.level.target
    while outcome.presses < limit and not outcome.entered and not outcome.stops:
        if outcome.presses and think:
            play.clock.sleep(think)
            outcome.seconds += think
        press(play, lambda: target, outcome, seed=seed)
    return outcome
