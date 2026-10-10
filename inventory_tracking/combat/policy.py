"""Where to cast Echoing Strike now: one decision for the simulator and for the game (combat/plan.md
stage 5; the steer of 2026-10-10: the simulated gain belonged to code the game never ran).

A policy is a callable from an `Observation` (the character, the live hostiles with the points they
have left, the monsters the Defiler's Health Link holds, the walls, whether the player is moving) to
a `Choice` (the focal point to cast at and the monster the line was laid through) or None. The
simulator builds the observation from a take's frame (sim/engine.py); the hunt builds it from the
game's memory (`observe`, called by macros/hunt.py). Two policies:

`LinePolicy`, the line sweep: through each live hostile within REACH a virtual cast is laid along the
line from the character, with the focal point on, short of and past the monster (OFFSETS), and scored
by the points the emulated blades would take off the monsters where they stand: each contact is worth
the blade's damage capped by what the monster has left (no credit for overkill), with the duplicate
rule, and a hit on a linked monster adds the share of its damage to every other linked one, each
capped by its own points. The best line is cast when it is worth MIN_SCORE. It yields: while the
player is moving it casts nothing (takeover with yield; `yields=False` is the free variant the
simulator scores for comparison).

`NearestPolicy`, the hunt's rule of 2026-10-09: the elite first, then the nearest monster within
STRIKE_REACH with a clear line, the focal point AIM_BEYOND past it. It is the historical baseline the
line sweep is compared with on the same takes. The live fight's own fallback (macros/hunt.py
`Hunter.choose`, for a monster in reach the sweep finds no line for) is a rule of the same shape over
the blades' full REACH, not this class.
"""

import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from inventory_tracking.combat.mechanics.damage import DEFILER, damage_table, link_table
from inventory_tracking.combat.mechanics.echoing_strike import BLADES, OUT_FRAMES, RANGE, cast
from inventory_tracking.combat.mechanics.hits import CONTACT_RADIUS
from inventory_tracking.combat.mechanics.tables import points_of


Point = tuple[float, float]
DUPLICATE = 1 / (2 * BLADES)  # skills.txt calc6 (100 / count) / 2: a cast's blades after the first on a monster and leg
RUN_MODES = frozenset((2, 3, 6))  # walk, run, town walk: the character is going somewhere
REACH = RANGE  # units: a monster further than the blades fly is not a line
OFFSETS = (0.0, -3.0, 4.0)  # focal point along the line relative to the monster: on, short, past (ties: on)
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


@dataclass(frozen=True)
class Choice:
    focal: Point  # where the blades should meet
    unit: int  # the monster the line was laid through
    worth: float  # the points the policy expects of the cast


Policy = Callable[[Observation], Choice | None]


def virtual_cast(
    origin: Point,
    focal: Point,
    foes: dict[int, Foe],
    linked: frozenset[int] | set[int],
    share: float,
    damage_of: Callable[[int], float],
    radius: float = CONTACT_RADIUS,
    blocked: Callable[[Point], bool] | None = None,
    elite_weight: float = 1.0,
) -> float:
    """Points one cast would take off the monsters where they stand, out and back: the duplicate
    rule, each contact capped by what the monster has left, and the link's spread to the other
    linked monsters, each capped by its own points; `blocked` are the walls the blades stop at. Points
    taken off an elite count `elite_weight` times (the worth of a line, not damage)."""
    left = {unit: foe.left for unit, foe in foes.items()}
    total = 0.0
    first: set[tuple[int, str]] = set()
    for path in cast(origin, focal, lambda k: origin, blocked):
        touched: set[tuple[int, str]] = set()
        for k, position in enumerate(path):
            leg = 'out' if k <= OUT_FRAMES else 'back'
            for unit, foe in foes.items():
                if (unit, leg) in touched or left[unit] <= 0 or math.dist(position, foe.at) > radius:
                    continue
                touched.add((unit, leg))
                dealt = damage_of(foe.txt) * (DUPLICATE if (unit, leg) in first else 1.0)
                first.add((unit, leg))
                taken = min(dealt, left[unit])
                left[unit] -= taken
                total += taken * (elite_weight if foe.elite else 1.0)
                if unit in linked:
                    for other in linked:
                        if other != unit and left.get(other, 0) > 0:
                            spread = min(dealt * share, left[other])
                            left[other] -= spread
                            total += spread * (elite_weight if foes[other].elite else 1.0)
    return total


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
class LinePolicy:
    yields: bool = True  # nothing while the player is moving
    reach: float = REACH
    offsets: tuple[float, ...] = OFFSETS
    damage_of: Callable[[int], float] = field(default_factory=damage_table)
    elite_weight: float = ELITE_WEIGHT

    def __call__(self, seen: Observation) -> Choice | None:
        if self.yields and seen.moving:
            return None
        best = self.choose(seen)
        return best if best is not None and best.worth >= MIN_SCORE else None

    def choose(self, seen: Observation) -> Choice | None:
        """The best line through the live hostiles."""
        best: Choice | None = None
        for unit, foe in seen.foes.items():
            away = math.dist(foe.at, seen.origin)
            if away > self.reach or away == 0:
                continue
            ux, uy = (foe.at[0] - seen.origin[0]) / away, (foe.at[1] - seen.origin[1]) / away
            for offset in self.offsets:
                distance = max(MIN_FOCAL, min(away + offset, self.reach - 1))
                focal = (seen.origin[0] + ux * distance, seen.origin[1] + uy * distance)
                worth = virtual_cast(
                    seen.origin, focal, seen.foes, seen.linked, seen.share, self.damage_of, blocked=seen.blocked,
                    elite_weight=self.elite_weight,
                )  # fmt: skip
                if worth > (best.worth if best is not None else 0.0):
                    best = Choice(focal, unit, worth)
        return best


@dataclass
class NearestPolicy:
    yields: bool = False  # the hunt of 2026-10-09 cast whatever the player did
    reach: float = STRIKE_REACH
    beyond: float = AIM_BEYOND
    damage_of: Callable[[int], float] = field(default_factory=damage_table)

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


def linked_set(defilers: Iterable[Point], foes: dict[int, Point], link_range: float, links: int) -> frozenset[int]:
    """The `links` live hostiles nearest a Defiler within its aura range: the ones Health Link holds."""
    posts = list(defilers)
    if not posts or not links:
        return frozenset()
    near = sorted((min(math.dist(post, at) for post in posts), unit) for unit, at in foes.items())
    return frozenset(unit for gap, unit in near[:links] if gap <= link_range)


def observe(
    player: Any,
    hostiles: Iterable[Any],
    companions: Iterable[Any],
    ground: Any = None,
    doors: Sequence[Any] = (),
    *,
    moving: bool = False,
) -> Observation:
    """The observation of the running game: `player` and the monsters are macros/world.py records
    (`hostiles` the ones that may be struck, `companions` the character's own units). A monster's
    points are its type's in the character's area by the life fraction the client shows."""
    foes = {}
    for m in hostiles:
        full = points_of(m.txt_id, player.area)
        foes[m.unit_id] = Foe(m.txt_id, (m.x, m.y), full * (m.life / m.max_life if m.max_life else 1.0), m.leader)
    link_range, links, share = link_table()
    defilers = [(c.x, c.y) for c in companions if c.txt_id == DEFILER]
    linked = linked_set(defilers, {unit: foe.at for unit, foe in foes.items()}, link_range, links)
    return Observation((player.x, player.y), foes, linked, share, walls(ground, doors), moving)
