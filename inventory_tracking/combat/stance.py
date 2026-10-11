"""Where to stand in a fight: one decision for the simulator and for the game.

`camp` picks the place within CAMP_REACH of the character, with footing, no hostile within KEEP_AWAY
and a walk there (`Field.ways`), that takes the most points from the next HORIZON seconds of casting
(`taken`). Casting is modelled as the best straight line through the hostiles in reach, BLADES_A_CAST
blades off each one on it per cast; a place where all in reach die early counts up to double. The walk
there costs its seconds without a cast, or a HOP_SECONDS teleport. The place is chosen only when it takes
CAMP_GAIN times what the character takes where it stands. The distance to a monster is not counted.
Pure: no game access.

History and measurements: combat/plan.md.
"""

import heapq
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from inventory_tracking.combat.mechanics.hits import CONTACT_RADIUS
from inventory_tracking.combat.policy import MIN_SCORE, LinePolicy, Observation


Point = tuple[float, float]
KEEP_AWAY = 6.0  # units: no place with a hostile this near
WAY_SAMPLE = 0.5  # units between the points looked at along a straight walk
HORIZON = 3.0  # seconds the worth of a place is counted over: the pack should be dead well within them
CAST_SECONDS = 0.36  # one cast of a held strike (combat/sim/input.py CAST_FRAMES at 25 frames a second)
RUN_SPEED = 20.0  # units a second
WALK_LATENCY = 0.36  # seconds before a walk begins: the cast that has to end, and the click
ENGAGE = 14.0  # units from the furthest hostile counted on that a jump is best ended at
AS_GOOD = 0.02  # two places whose worth differs by less than this share are as good
HOP_SECONDS = 1.5  # a teleport with the staff: the swap there, the hop, the swap back (the Tower run: 0.7 to 1.5 s)
CAMP_REACH = 24.0  # units from the character a place is looked for (the window shows 23 up and 18 down)
CAMP_GRID = 3.0  # units between the places looked at
DETOUR = 1.4  # a way this many times the straight line is still a walk (the game finds its own way round a corner)
CAMP_GAIN = 1.25  # a place worth this many times where the character stands is worth going to
# What one cast takes off a monster on its line, in blades: the first whole and the rest by the
# duplicate rule, out and back (combat/policy.py `virtual_cast`: 2,800 points of a 1,000-point blade).
BLADES_A_CAST = 2.8


def no_footing(ground: Any, doors: Sequence[Any] = ()) -> Callable[[Point], bool] | None:
    """Whether the character cannot stand on or walk over a point: a cell the read grids do not show
    as walkable (an unread one too, once the level has walls), or a closed door. None without walls
    or closed doors: anywhere."""
    closed = [door for door in doors if door.closed]
    walked = ground.walkable if ground is not None and len(ground) > 0 else None
    if walked is None and not closed:
        return None

    def barred(point: Point) -> bool:
        if walked is not None and walked(*point) is not True:
            return True
        return any(door.blocks(point) for door in closed)

    return barred


def way(barred: Callable[[Point], bool] | None, start: Point, end: Point) -> bool:
    """Whether a straight walk from `start` ends on footing with nothing barred on it. The start
    itself is not looked at: the character stands on cells the grids call unwalkable now and then
    (macros/sight.py MARGIN)."""
    if barred is None:
        return True
    if any(barred((end[0] + dx, end[1] + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
        return False
    length = math.dist(start, end)
    steps = max(int(length / WAY_SAMPLE), 1)
    return not any(
        barred((start[0] + (end[0] - start[0]) * k / steps, start[1] + (end[1] - start[1]) * k / steps))
        for k in range(2, steps)
    )


@dataclass(frozen=True)
class Camp:
    spot: Point  # where to stand
    worth: float  # `taken` from there: the points of the next HORIZON seconds, more for being done early
    here: float  # the same from where the character stands
    seconds: float  # the way there
    walk: float  # units of the way (the straight line for a hop)
    hop: bool = False  # by a teleport or a jump: no walk gets there, or the walk is slower
    casts: int = 0  # casts until nothing is left in its reach, as counted (0: more than the horizon holds)
    skill: int | None = None  # the jump it is priced by (`Jump.skill`); None: a walk, or the plain `hop`


@dataclass(frozen=True)
class Jump:
    """A way to a place the character has besides walking: a skill that puts it there."""

    skill: int
    seconds: float  # from the key to standing there, at no distance
    speed: float  # units a second on top of that (math.inf: there at once)
    reach: float  # units it carries at most
    least: float  # a place nearer than this is walked to
    line: bool  # whether it needs a clear line there (a thrown blade), as a shot does

    def takes(self, away: float) -> float:
        return self.seconds + away / self.speed


class Field:
    """The walls and the footing around the character, read once per cell (a cell is one unit: the
    grids' own)."""

    def __init__(self, blocked: Callable[[Point], bool] | None, barred: Callable[[Point], bool] | None) -> None:
        self.blocked, self.barred = blocked, barred
        self.walls: dict[tuple[int, int], bool] = {}
        self.bars: dict[tuple[int, int], bool] = {}

    def wall(self, x: float, y: float) -> bool:
        if self.blocked is None:
            return False
        cell = (math.floor(x), math.floor(y))
        known = self.walls.get(cell)
        if known is None:
            known = self.walls[cell] = self.blocked((cell[0] + 0.5, cell[1] + 0.5))
        return known

    def bar(self, cell: tuple[int, int]) -> bool:
        if self.barred is None:
            return False
        known = self.bars.get(cell)
        if known is None:
            known = self.bars[cell] = self.barred((cell[0] + 0.5, cell[1] + 0.5))
        return known

    def clear(self, start: Point, end: Point) -> bool:
        """`policy.clear_line` over the cells."""
        length = math.dist(start, end)
        if self.blocked is None or length <= 3.0:
            return True
        steps = max(int((length - 3.0) / 0.5), 1)
        ux, uy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
        for index in range(steps + 1):
            along = min(1.5 + index * 0.5, length - 1.5)
            if self.wall(start[0] + ux * along, start[1] + uy * along):
                return False
        return True

    def ways(self, origin: Point, reach: float) -> dict[tuple[int, int], float]:
        """Units of the shortest walk from `origin` to every cell within `reach` of it, over cells
        that are not barred (the cell the character stands on is taken as it is)."""
        start = (math.floor(origin[0]), math.floor(origin[1]))
        found = {start: 0.0}
        queue = [(0.0, start)]
        limit = reach * DETOUR + 2
        while queue:
            gone, cell = heapq.heappop(queue)
            if gone > found[cell]:
                continue
            for dx, dy, step in STEPS:
                near = (cell[0] + dx, cell[1] + dy)
                further = gone + step
                if further > limit or abs(near[0] - start[0]) > reach or abs(near[1] - start[1]) > reach:
                    continue
                if further >= found.get(near, math.inf) or self.bar(near):
                    continue
                if dx and dy and (self.bar((cell[0] + dx, cell[1])) or self.bar((cell[0], cell[1] + dy))):
                    continue  # no cutting a corner
                found[near] = further
                heapq.heappush(queue, (further, near))
        return found


STEPS = tuple((dx, dy, math.hypot(dx, dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)


def taken(seen: Observation, policy: LinePolicy, field: Field, spot: Point, after: float) -> tuple[float, int]:
    """(worth, casts) of casting from `spot` from `after` seconds on to the HORIZON: cast after cast
    the best straight line through the hostiles in reach with a clear line takes BLADES_A_CAST blades
    off each one on it (capped by what it has left, an elite weighted as the policy weights it). The
    worth is the points taken, and up to as much again for being done early: all in reach dead at
    once would double it, dead as the horizon ends adds nothing. `casts` is how many it takes until
    nothing in reach is left, 0 when the horizon ends first."""
    near = []
    for unit, foe in seen.foes.items():
        dx, dy = foe.at[0] - spot[0], foe.at[1] - spot[1]
        away = math.hypot(dx, dy)
        if 0 < away <= policy.reach and field.clear(spot, foe.at):
            near.append((unit, foe, dx, dy, away))
    if not near:
        return 0.0, 0
    lines = []
    for _, _, tx, ty, away in near:
        ux, uy = tx / away, ty / away
        lines.append(
            [
                k
                for k, (_, _, dx, dy, _) in enumerate(near)
                if dx * ux + dy * uy > 0 and abs(dx * uy - dy * ux) <= CONTACT_RADIUS
            ]
        )
    left = [foe.left for _, foe, *_ in near]
    blow = [policy.damage_of(foe.txt) * BLADES_A_CAST for _, foe, *_ in near]
    weight = [policy.elite_weight if foe.elite else 1.0 for _, foe, *_ in near]
    clock, casts, total = after, 0, 0.0
    done = False
    while clock + CAST_SECONDS <= HORIZON:
        best, line = 0.0, None
        for on in lines:
            points = sum(min(blow[k], left[k]) * weight[k] for k in on if left[k] > 0)
            if points > best:
                best, line = points, on
        if line is None:
            done = True
            break
        clock += CAST_SECONDS
        casts += 1
        total += best
        for k in line:
            left[k] = max(0.0, left[k] - blow[k])
    done = done or not any(points > 0 for points in left)
    return total * (1 + (HORIZON - clock) / HORIZON if done else 1.0), casts if done else 0


def camp(
    seen: Observation,
    policy: LinePolicy,
    barred: Callable[[Point], bool] | None = None,
    *,
    hop: bool = False,
    shown: Callable[[Point], bool] | None = None,
    gain: float = CAMP_GAIN,
    jumps: Sequence[Jump] = (),
) -> Camp | None:
    """The place worth going to from where the character stands, or None when it stands well: the
    place within CAMP_REACH where the next HORIZON seconds take the most, the way there counted
    as seconds without a cast. A place is walked to when a way of at most DETOUR times the straight
    line leads there; with `hop` every other place with footing is a teleport of HOP_SECONDS away,
    and so is a walked one when the hop is faster. `shown(spot)`: whether the window shows the spot
    (a click or a hop needs it); None: every spot. `gain`: how many times the worth of where the
    character stands a place has to be. `jumps`: the skills the character can jump by now, the
    preferred first: a place one of them reaches is priced by the first that does (and walked to only
    when none does), so the place is chosen for the way the character will take there."""
    origin = seen.origin
    field = Field(seen.blocked, barred)
    here, _ = taken(seen, policy, field, origin, 0.0)
    ways = field.ways(origin, CAMP_REACH)
    best: tuple[float, float, Camp] | None = None  # (worth, the furthest hostile it counts on, the place)
    count = int(CAMP_REACH // CAMP_GRID)
    for i in range(-count, count + 1):
        for j in range(-count, count + 1):
            spot = (math.floor(origin[0]) + i * CAMP_GRID + 0.5, math.floor(origin[1]) + j * CAMP_GRID + 0.5)
            straight = math.dist(origin, spot)
            if not 0 < straight <= CAMP_REACH or (shown is not None and not shown(spot)):
                continue
            cell = (math.floor(spot[0]), math.floor(spot[1]))
            if any(field.bar((cell[0] + dx, cell[1] + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                continue
            if any(math.dist(spot, foe.at) < KEEP_AWAY for foe in seen.foes.values()):
                continue
            walked = ways.get(cell)
            on_foot = walked is not None and walked <= max(straight * DETOUR, straight + 2)
            seconds = WALK_LATENCY + walked / RUN_SPEED if on_foot and walked is not None else math.inf
            by_hop = hop and seconds > HOP_SECONDS
            if by_hop:
                seconds = HOP_SECONDS
            jump = next(
                (
                    jump
                    for jump in jumps
                    if jump.least <= straight <= jump.reach and (not jump.line or field.clear(origin, spot))
                ),
                None,
            )
            if jump is not None:
                seconds, by_hop = jump.takes(straight), True
            if seconds >= HORIZON:
                continue
            worth, casts = taken(seen, policy, field, spot, seconds)
            if worth < max(MIN_SCORE, gain * here):
                continue
            # Of two places as good (a jump takes as long to any of them) the one whose furthest hostile
            # is nearest ENGAGE away: at the end of the blades' flight a step of a monster's is a miss,
            # and next to the pack is where it strikes.
            edge = max(
                (away for foe in seen.foes.values() if (away := math.dist(spot, foe.at)) <= policy.reach), default=0.0
            )
            close = AS_GOOD if jump is not None else 0.0  # a walk's seconds already tell two places apart
            if (
                best is None
                or worth > best[0] * (1 + close)
                or (close and worth >= best[0] * (1 - close) and abs(edge - ENGAGE) < abs(best[1] - ENGAGE))
            ):
                units = straight if by_hop or walked is None else walked
                skill = jump.skill if jump is not None else None
                best = (worth, edge, Camp(spot, worth, here, seconds, units, by_hop, casts, skill))
    return best[2] if best is not None else None
