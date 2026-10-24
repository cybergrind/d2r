"""Where to stand in a fight: one decision for the simulator and for the game. Pure: no game access.

`camp` picks the place within CAMP_REACH with footing, no hostile within KEEP_AWAY, no pack round it
(CROWD_MOST) and a walk there (`Field.ways`) that takes the most points from the next HORIZON seconds of casting
(`taken`, by the build's `Striker.dealt`; all in reach dead early counts up to double). The way costs its seconds
without a cast, or HOP_SECONDS for a teleport; a place must be worth CAMP_GAIN times where the character stands.
No place is jumped to that a melee monster reaches before the first cast is out (`closes`).

History and measurements: combat/plan.md.
"""

import heapq
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from typing import Any, Protocol

from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.policy import ELITE_WEIGHT, MIN_SCORE, Foe, Observation
from inventory_tracking.levels.geometry import Point


KEEP_AWAY = 6.0  # units: no place with a hostile this near
# No place in the middle of a pack: more than CROWD_MOST hostiles within CROWD_UNITS rule it out unless as many
# stand that near the character already (user, 2026-10-12: "we positioned ourselves into big mob group and took
# too much damage"; Drifter Cavern 09:55:34).
CROWD_UNITS = 12.0
CROWD_MOST = 3
# Out of a pack the character stands in: a place with no pack round it is taken when worth this share of where it
# stands, whatever `gain` asks (0: off). Tuned on the replayed Infector seal fight (arena/incident.py, 20 seeds,
# 2026-10-13: life lost 1,062 -> 891 at the median; user: "safe and kill most of mobs as fast as before").
CROWD_ESCAPE = 0.5
ESCAPE_UNITS = 8.0  # the pack stood in: more than CROWD_MOST hostiles this near the character
ESCAPE_MOST = 3  # and at most this many as near the place gone to
# A melee monster comes on while the character is on its way: units a second per point of monstats speed
# (sim/monsters.py PACE), over the way and the first cast, CLOSING_MOST at most (user, 2026-10-12 cow runs:
# "jumping into their groups too aggressively").
CLOSING_PACE = 1.1
CLOSING_MOST = 6.0
AWARE = 20.0  # units: a monster further from the place than this does not come for it (sim/monsters.py)
WAY_SAMPLE = 0.5  # units between the points looked at along a straight walk
HORIZON = 3.0  # seconds the worth of a place is counted over: the pack should be dead well within them
# One cast of a held strike: the Echoing Strike Warlock's (builds/warlock/echoing_strike/sim/input.py CAST_FRAMES).
CAST_SECONDS = 0.36
RUN_SPEED = 20.0  # units a second
WALK_LATENCY = 0.36  # seconds before a walk begins: the cast that has to end, and the click
AS_GOOD = 0.02  # two places whose worth differs by less than this share are as good
HOP_SECONDS = 1.5  # a teleport with the staff: the swap there, the hop, the swap back (the Tower run: 0.7 to 1.5 s)
CAMP_REACH = 24.0  # units from the character a place is looked for (the window shows 23 up and 18 down)
CAMP_GRID = 3.0  # units between the places looked at
DETOUR = 1.4  # a way this many times the straight line is still a walk (the game finds its own way round a corner)
CAMP_GAIN = 1.25  # a place worth this many times where the character stands is worth going to


class Striker(Protocol):
    """What a place is priced by: the reach and the cast of the build's attack (macros/build.py
    `Attack`, which this module cannot import: it is below it)."""

    reach: float  # units: a hostile further from a place is not struck from it
    # Optional (`engaged`, `landing`): `engage`, units from the furthest hostile a jump is best ended at, and
    # `lands(away)`, the share of casts that hit a monster that far off (1.0 without).

    def dealt(
        self, origin: Point, focal: Point, foes: Mapping[int, Foe], blocked: Callable[[Point], bool] | None = None
    ) -> Mapping[int, float]:
        """The points one cast from `origin` at `focal` takes off each of `foes`, by unit id; `blocked`: the
        walls its missiles stop at (None: none)."""
        ...


def engaged(attack: Striker) -> float:
    """Units from the furthest hostile counted on that a jump is best ended at: the attack's `engage`, its reach
    for one that says none."""
    return getattr(attack, 'engage', attack.reach)


def landing(attack: Striker) -> Callable[[float], float]:
    """The attack's `lands` (the share of casts that hit a monster so far off), or every cast for one that says
    none."""
    return getattr(attack, 'lands', None) or (lambda away: 1.0)


def striker(given: Any) -> Striker:
    """The attack a place is priced by: a build's (macros/build.py `Attack`). A cast policy on its
    own is none: whoever has only that makes the attack of it on the build's side."""
    if not hasattr(given, 'dealt'):
        raise TypeError(f'a place is priced by an attack, which says what a cast deals: not by {given!r}')
    return given


def no_footing(ground: Any, doors: Sequence[Any] = ()) -> Callable[[Point], bool] | None:
    """Whether the character cannot stand on or walk over a point: a cell the grids do not show walkable (unread
    too, once the level has walls) or a closed door. None without either: anywhere."""
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

    def walled(self) -> Callable[[Point], bool] | None:
        """The walls as a cast's missiles meet them (`Striker.dealt`), read once per cell; None without walls."""
        return None if self.blocked is None else (lambda point: self.wall(*point))

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


@cache
def speed_of(txt: int) -> float:
    """Units a second a monster of `txt` closes at: 0 for one that does not strike from beside the character."""
    row = tables()['monsters'].get(str(txt), {})
    if row.get('isMelee') != '1':
        return 0.0
    return max(float(row.get('Velocity') or 0), float(row.get('Run') or 0)) * CLOSING_PACE


def closes(foe: Any, spot: Point, seconds: float) -> bool:
    """Whether the monster is too near `spot` for a place reached in `seconds`: within KEEP_AWAY now, or,
    a melee monster that would come for the character there, by the time the first cast is out."""
    away = math.dist(spot, foe.at)
    if away < KEEP_AWAY:
        return True
    if away > AWARE:
        return False
    return away - min(speed_of(foe.txt) * (seconds + CAST_SECONDS), CLOSING_MOST) < KEEP_AWAY


def taken(
    seen: Observation,
    attack: Striker,
    field: Field,
    spot: Point,
    after: float,
    *,
    landed: bool = False,
    walls: bool = True,
) -> tuple[float, int]:
    """(worth, casts) of casting from `spot` from `after` seconds to the HORIZON: cast after cast, the best cast at
    a hostile in reach with a clear line takes what `Striker.dealt` says, capped by what each has left (an elite's
    point counted ELITE_WEIGHT times). Worth: the points taken, up to double for being done early. `casts`: until
    nothing in reach is left, 0 when the horizon ends first. `landed`: casts land by distance (`landing`;
    run-1932-findings.md §4); `walls`: blades stop at walls (run-2040-findings.md §3.3). Both are off only for
    the pursuit-off sweep, whose goldens were recorded without them."""
    attack = striker(attack)
    lands = landing(attack) if landed else (lambda away: 1.0)
    near = []
    for unit, foe in seen.foes.items():
        dx, dy = foe.at[0] - spot[0], foe.at[1] - spot[1]
        away = math.hypot(dx, dy)
        if 0 < away <= attack.reach and field.clear(spot, foe.at):
            near.append((unit, foe))
    if not near:
        return 0.0, 0
    within = dict(near)
    share = [lands(math.dist(spot, foe.at)) for _, foe in near]  # of the casts that hit each one from here
    lines = []  # per hostile in reach, the cast at it: (index in `near`, the points it takes off that one)
    blocked = field.walled() if walls else None
    for _, aimed in near:
        hit = attack.dealt(spot, aimed.at, within, blocked)
        lines.append([(k, hit[unit] * share[k]) for k, (unit, _) in enumerate(near) if unit in hit])
    left = [foe.left for _, foe in near]
    # an elite's point ELITE_WEIGHT times, a raising reviver's REVIVER_WEIGHT more (`Foe.weight`, combat/revivers.py; a
    # raised one's is not cut here: a place is priced against fixed bars, and every place of a raised pack would fall)
    weight = [(ELITE_WEIGHT if foe.elite else 1.0) * max(foe.weight, 1.0) for _, foe in near]
    clock, casts, total = after, 0, 0.0
    done = False
    while clock + CAST_SECONDS <= HORIZON:
        best, line = 0.0, None
        for on in lines:
            points = sum(min(blow, left[k]) * weight[k] for k, blow in on if left[k] > 0)
            if points > best:
                best, line = points, on
        if line is None:
            done = True
            break
        clock += CAST_SECONDS
        casts += 1
        total += best
        for k, blow in line:
            left[k] = max(0.0, left[k] - blow)
    done = done or not any(points > 0 for points in left)
    return total * (1 + (HORIZON - clock) / HORIZON if done else 1.0), casts if done else 0


def falls(
    seen: Observation, attack: Striker, field: Field, spot: Point, after: float, horizon: float, pace: float = 1.0
) -> dict[int, float]:
    """Seconds from now until each hostile dies by the strikes cast from `spot` (first `after` seconds on, each
    CAST_SECONDS x `pace`): the line `taken` would lay, every cast landing (the spread is
    `SafetySettings.strike_spread`'s), a hit on a linked monster dealt again at `Observation.share` to the other
    linked ones. Only deaths within `horizon`. For combat/harm.py `harm_path`'s `deaths`: no companion's damage,
    no monster's move."""
    attack = striker(attack)
    near = []
    for unit, foe in seen.foes.items():
        if foe.left <= 0:
            continue
        away = math.dist(spot, foe.at)
        if 0 < away <= attack.reach and field.clear(spot, foe.at):
            near.append((unit, foe))
    if not near:
        return {}
    within = dict(near)
    left = {unit: foe.left for unit, foe in seen.foes.items() if foe.left > 0}
    weight = {unit: ELITE_WEIGHT if foe.elite else 1.0 for unit, foe in seen.foes.items()}
    walls = field.walled()
    lines = [dict(attack.dealt(spot, aimed.at, within, walls)) for _, aimed in near]
    linked = [unit for unit in seen.linked if unit in left] if seen.share > 0 else []
    found: dict[int, float] = {}
    clock = after
    step = CAST_SECONDS * pace
    while clock + step <= horizon:
        best, line = 0.0, None
        for on in lines:
            points = sum(min(blow, left[unit]) * weight[unit] for unit, blow in on.items() if left.get(unit, 0) > 0)
            if points > best:
                best, line = points, on
        if line is None:
            break
        clock += step
        spread: dict[int, float] = {}
        for unit, blow in line.items():
            if left.get(unit, 0) <= 0:
                continue
            if unit in seen.linked:
                for other in linked:
                    if other != unit:
                        spread[other] = spread.get(other, 0.0) + blow * seen.share
            left[unit] = max(0.0, left[unit] - blow)
        for unit, points in spread.items():
            left[unit] = max(0.0, left[unit] - points)
        for unit, points in left.items():
            if points <= 0 and unit not in found:
                found[unit] = clock
    return found


def camp(
    seen: Observation,
    attack: Striker,
    barred: Callable[[Point], bool] | None = None,
    *,
    hop: bool = False,
    shown: Callable[[Point], bool] | None = None,
    gain: float = CAMP_GAIN,
    jumps: Sequence[Jump] = (),
    escape: float | None = None,
    landed: bool = False,
    walls: bool = True,
) -> Camp | None:
    """The place worth going to, or None when the character stands well (see the module text). A place is walked
    to by a way of at most DETOUR x the straight line; with `hop` any other with footing is a HOP_SECONDS teleport.
    `shown(spot)`: the window shows it (None: every spot). `gain`: the worth multiple asked. `jumps`: skills it can
    jump by, preferred first; a place is priced by the first that reaches it. `escape`: CROWD_ESCAPE override.
    `landed`, `walls`: as `taken`."""
    attack = striker(attack)
    ring = engaged(attack)
    origin = seen.origin
    field = Field(seen.blocked, barred)
    here, _ = taken(seen, attack, field, origin, 0.0, landed=landed, walls=walls)
    ways = field.ways(origin, CAMP_REACH)
    around = sum(math.dist(origin, foe.at) <= CROWD_UNITS for foe in seen.foes.values())
    pressed = sum(math.dist(origin, foe.at) <= ESCAPE_UNITS for foe in seen.foes.values())
    share = CROWD_ESCAPE if escape is None else escape
    escaping = bool(share) and pressed > CROWD_MOST
    crowd = max(CROWD_MOST, around)
    need = share if escaping else gain
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
            if sum(math.dist(spot, foe.at) <= CROWD_UNITS for foe in seen.foes.values()) > crowd:
                continue
            if escaping and sum(math.dist(spot, foe.at) <= ESCAPE_UNITS for foe in seen.foes.values()) > ESCAPE_MOST:
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
            # Only a jump: it lands blind and at once; a walk is seen coming (held to walks, no pack is walked to).
            if by_hop and any(closes(foe, spot, seconds) for foe in seen.foes.values()):
                continue
            worth, casts = taken(seen, attack, field, spot, seconds, landed=landed, walls=walls)
            if worth < max(MIN_SCORE, need * here):
                continue
            # Of two places as good, the one whose furthest hostile is nearest the engage ring (`engaged`): at the end
            # of the blades' flight a monster's step is a miss.
            edge = max(
                (away for foe in seen.foes.values() if (away := math.dist(spot, foe.at)) <= attack.reach), default=0.0
            )
            close = AS_GOOD if jump is not None else 0.0  # a walk's seconds already tell two places apart
            if (
                best is None
                or worth > best[0] * (1 + close)
                or (close and worth >= best[0] * (1 - close) and abs(edge - ring) < abs(best[1] - ring))
            ):
                units = straight if by_hop or walked is None else walked
                skill = jump.skill if jump is not None else None
                best = (worth, edge, Camp(spot, worth, here, seconds, units, by_hop, casts, skill))
    return best[2] if best is not None else None
