"""Where to cast now: one decision for the simulator and for the game (combat/plan.md stage 5; the
steer of 2026-10-10: the simulated gain belonged to code the game never ran).

A policy is a callable from an `Observation` (the character, the live hostiles with the points they
have left, the monsters a link of the character's own units holds, the walls, whether the player is
moving) to a `Choice` (the focal point to cast at and the monster the line was laid through) or None.
A simulator builds the observation from a take's frame (a build's own: builds/warlock/echoing_strike/
sim/engine.py); the hunt builds it from the game's memory (`observe`, called by macros/hunt.py, and
the attack's `sees` for the link). What a build's cast is worth and where it goes is the build's
(macros/build.py `Attack`; the line sweep of the Echoing Strike Warlock is builds/warlock/
echoing_strike/attack.py `LinePolicy`). One policy is the framework's own:

`NearestPolicy`, the hunt's rule of 2026-10-09: the elite first, then the nearest monster within
STRIKE_REACH with a clear line, the focal point AIM_BEYOND past it. It is the historical baseline a
build's policy is compared with on the same takes. The live fight's own fallback (macros/hunt.py
`Hunter.choose`, for a monster in reach the attack finds no line for) is a rule of the same shape over
the attack's full reach, not this class.

`Observation.linked`, `share` and `marked` are the Warlock's facts under plain names (the Defiler's
Health Link, Death Mark): the fields stay until a second build shows what an attack's own facts are.
"""

import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from inventory_tracking.combat.mechanics.movement import Route
from inventory_tracking.combat.mechanics.tables import points_of


Point = tuple[float, float]
RUN_MODES = frozenset((2, 3, 6))  # walk, run, town walk: the character is going somewhere
# The two below are read by the framework and by the build's sweep alike, so they stay here. Both were
# set with the Echoing Strike Warlock's blades (builds/warlock/echoing_strike/attack.py) and no other
# attack has tested them.
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
    # blades reach: macros/view.py), or None when no point of that line can; None here: any focal point.
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
    # Points a cast takes off a monster of a type: the worth the choice is given, by a build's damage
    # table. It has no default: the framework has no damage table of its own.
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
    """Whether a point stops a blade: a cell the grid's flight layer says a missile does not fly
    through (the block-missile bit, native/layout.py), an unread cell when the level has walls (a
    room not loaded), or a closed door standing there. None without walls or closed doors. A cell
    that only blocks walking does not stop a blade (the Catacombs takes of 2026-10-10 11:24 UTC:
    recorded blades over block-walk cells for up to 16 frames), and a grid without a flight layer
    (a level map before 11:44 UTC) stops none."""
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
    """The observation of the running game: `player` and the monsters are macros/game/records.py records
    (`hostiles` the ones that may be struck). A monster's points are its type's in the character's
    area by the life fraction the client shows. `companions`, the character's own units, are not
    read here: what an attack reads off them (a link they hold between monsters) is its `sees`
    (macros/build.py `Attack`), asked by the caller with the same units."""
    foes = {}
    for m in hostiles:
        full = points_of(m.txt_id, player.area)
        foes[m.unit_id] = Foe(m.txt_id, (m.x, m.y), full * (m.life / m.max_life if m.max_life else 1.0), m.leader)
    return Observation((player.x, player.y), foes, blocked=walls(ground, doors), moving=moving, aimable=aimable)
