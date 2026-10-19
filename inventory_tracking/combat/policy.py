"""Where to cast now: one decision for the simulator and for the game (combat/plan.md stage 5).

A policy maps an `Observation` (the character, live hostiles with their points left, linked monsters, walls,
whether the player is moving) to a `Choice` (focal point and the monster the line was laid through) or None. A
build's simulator builds the observation from a take's frame; the hunt from memory (`observe`). What a cast is
worth is the build's (macros/build.py `Attack`). `NearestPolicy` (the elite first, then the nearest within
STRIKE_REACH, AIM_BEYOND past it) is the framework's own: the baseline a build's policy is compared with.

`Observation.linked`, `share` and `marked` are the Warlock's facts (Health Link, Death Mark) under plain names,
until a second build shows what an attack's own facts are.
"""

import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from inventory_tracking.combat.mechanics.movement import Route
from inventory_tracking.combat.mechanics.tables import points_of
from inventory_tracking.levels.geometry import Point


RUN_MODES = frozenset((2, 3, 6))  # walk, run, town walk: the character is going somewhere
# Read by the framework and the build's sweep alike; set with the Echoing Strike Warlock's blades only.
MIN_FOCAL = 4.0  # units: no focal point nearer the character than this
MIN_SCORE = 1.0  # points: a line worth casting along
ELITE_WEIGHT = (
    2.0  # a point off a unique, champion or super unique counts this much: the elite first (user, 2026-10-09)
)
STRIKE_REACH = 20.0  # units: the hunt's reach (the blades fly 22 out; the player engages at 12-14 at the median)
AIM_BEYOND = 1.0  # units past the monster where the hunt's rule puts the focal point
LINE_SAMPLE = 0.5  # units between the points looked at along a line
LINE_MARGIN = 1.5  # units at both ends of a line not looked at (macros/sight.py)


@dataclass(frozen=True)
class Foe:
    txt: int
    at: Point
    left: float  # life points left
    elite: bool = False  # a unique, champion or super unique
    route: Route | None = None  # the waypoints it is walking, when the observer read them (mechanics/movement.py)

    def ahead(self, frames: int) -> Point:
        """Where it is `frames` from now: along its route, else where it stands."""
        return self.route.after(self.at, frames) if self.route is not None else self.at


@dataclass
class Observation:
    origin: Point  # where the character stands
    foes: dict[int, Foe]  # live hostiles by unit id
    linked: frozenset[int] = frozenset()  # the monsters Health Link holds
    share: float = 0.0  # the damage dealt again to each other linked monster
    blocked: Callable[[Point], bool] | None = None  # the walls and closed doors for a blade cast now
    moving: bool = False  # the player is going somewhere: the pointer is theirs
    mana: float = math.inf
    marked: frozenset[int] = frozenset()  # the monsters under Death Mark
    frame: int = 0  # the simulator's frame (0 in the game)
    # The focal point the pointer can really be put on for a wanted one (the window shows less than the
    # blades reach: game/view.py), or None when no point of that line can; None here: any focal point.
    aimable: Callable[[Point], Point | None] | None = None


@dataclass(frozen=True)
class Choice:
    focal: Point  # where the blades should meet
    unit: int  # the monster the line was laid through
    worth: float  # the points the policy expects of the cast


Policy = Callable[[Observation], Choice | None]


def clear_line(blocked: Callable[[Point], bool] | None, start: Point, end: Point) -> bool:
    """Whether nothing `blocked` names lies on the line, both ends left out by LINE_MARGIN."""
    length = math.dist(start, end)
    if blocked is None or length <= 2 * LINE_MARGIN:
        return True
    steps = max(int((length - 2 * LINE_MARGIN) / LINE_SAMPLE), 1)
    for index in range(steps + 1):
        t = min((LINE_MARGIN + index * LINE_SAMPLE) / length, (length - LINE_MARGIN) / length)
        if blocked((start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t)):
            return False
    return True


@dataclass
class NearestPolicy:
    yields: bool = False  # the hunt of 2026-10-09 cast whatever the player did
    reach: float = STRIKE_REACH
    beyond: float = AIM_BEYOND
    # Points a cast takes off a monster of a type (a build's damage table; the framework has none).
    damage_of: Callable[[int], float] = field(kw_only=True)

    def __call__(self, seen: Observation) -> Choice | None:
        if self.yields and seen.moving:
            return None
        near = [
            (not foe.elite, math.dist(foe.at, seen.origin), unit)
            for unit, foe in seen.foes.items()
            if 0 < math.dist(foe.at, seen.origin) <= self.reach and clear_line(seen.blocked, seen.origin, foe.at)
        ]
        if not near:
            return None
        _, away, unit = min(near)
        at = seen.foes[unit].at
        focal = (
            at[0] + (at[0] - seen.origin[0]) / away * self.beyond,
            at[1] + (at[1] - seen.origin[1]) / away * self.beyond,
        )
        return Choice(focal, unit, self.damage_of(seen.foes[unit].txt))


def walls(ground: Any, doors: Sequence[Any] = ()) -> Callable[[Point], bool] | None:
    """Whether a point stops a blade: a cell with the block-missile bit (native/layout.py), an unread cell when the
    level has walls, or a closed door. None without walls or doors. Block-walk alone does not stop a blade (blades
    recorded over such cells, Catacombs 2026-10-10); a grid without a flight layer stops none."""
    closed = [door for door in doors if door.closed]
    walled = ground is not None and len(ground) > 0
    if not walled and not closed:
        return None

    def blocked(point: Point) -> bool:
        if walled and (ground.walkable(*point) is None or ground.flyable(*point) is False):
            return True
        return any(door.blocks(point) for door in closed)

    return blocked


def observe(
    player: Any,
    hostiles: Iterable[Any],
    companions: Iterable[Any] = (),
    ground: Any = None,
    doors: Sequence[Any] = (),
    *,
    moving: bool = False,
    aimable: Callable[[Point], Point | None] | None = None,
) -> Observation:
    """The observation of the running game from game/records.py records (`hostiles`: the ones that may be struck).
    A monster's points: its type's in the area by the client's life fraction. Companions are read by the attack's
    `sees` (macros/build.py `Attack`), not here."""
    foes = {}
    for m in hostiles:
        full = points_of(m.txt_id, player.area)
        foes[m.unit_id] = Foe(m.txt_id, (m.x, m.y), full * (m.life / m.max_life if m.max_life else 1.0), m.leader)
    return Observation((player.x, player.y), foes, blocked=walls(ground, doors), moving=moving, aimable=aimable)
