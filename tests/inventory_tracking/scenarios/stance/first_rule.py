"""The first rule for the step (combat/stance.py on 2026-10-10, replaced the next day by `camp`), kept
here as the reference the recorded moments are compared against: spots a straight walk of at most 12
units away, the best straight line from each, the policy's own line for the four best, and a step
only for a line worth twice the line from where the character stands.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, replace

from inventory_tracking.combat.mechanics.hits import CONTACT_RADIUS
from inventory_tracking.combat.policy import MIN_SCORE, LinePolicy, Observation, clear_line
from inventory_tracking.combat.stance import KEEP_AWAY, way


Point = tuple[float, float]
RINGS = (4.0, 8.0, 12.0)
BEARINGS = 16
CROWD = 8.0
STEP_GAIN = 2.0
SHORTLIST = 4


@dataclass(frozen=True)
class Stand:
    spot: Point
    worth: float
    here: float
    unit: int
    walk: float


def lined(seen: Observation, policy: LinePolicy, spot: Point) -> float:
    near = [
        (foe, math.dist(spot, foe.at))
        for foe in seen.foes.values()
        if 0 < math.dist(spot, foe.at) <= policy.reach and clear_line(seen.blocked, spot, foe.at)
    ]
    worth = [min(policy.damage_of(foe.txt), foe.left) * (policy.elite_weight if foe.elite else 1.0) for foe, _ in near]
    best = 0.0
    for through, away in near:
        ux, uy = (through.at[0] - spot[0]) / away, (through.at[1] - spot[1]) / away
        total = 0.0
        for (foe, _), points in zip(near, worth, strict=True):
            dx, dy = foe.at[0] - spot[0], foe.at[1] - spot[1]
            if dx * ux + dy * uy > 0 and abs(dx * uy - dy * ux) <= CONTACT_RADIUS:
                total += points
        best = max(best, total)
    return best


def stand(
    seen: Observation,
    policy: LinePolicy,
    barred: Callable[[Point], bool] | None = None,
    aimable: Callable[[Point, Point], Point | None] | None = None,
) -> Stand | None:
    origin = seen.origin
    best_here = policy.choose(seen)
    here = best_here.worth if best_here is not None and best_here.worth >= MIN_SCORE else 0.0
    spots = []
    for ring in RINGS:
        for bearing in range(BEARINGS):
            angle = 2 * math.pi * bearing / BEARINGS
            spot = (origin[0] + ring * math.cos(angle), origin[1] + ring * math.sin(angle))
            gaps = [math.dist(spot, foe.at) for foe in seen.foes.values()]
            if any(gap < KEEP_AWAY for gap in gaps) or not way(barred, origin, spot):
                continue
            reach = lined(seen, policy, spot)
            if reach >= MIN_SCORE:
                spots.append((-reach, sum(gap < CROWD for gap in gaps), ring, spot))
    found: tuple[tuple[float, int, float], Stand] | None = None
    for _, crowd, ring, spot in sorted(spots)[:SHORTLIST]:
        bound = None if aimable is None else (lambda focal, spot=spot: aimable(spot, focal))
        within = {
            unit: foe
            for unit, foe in seen.foes.items()
            if unit in seen.linked or math.dist(spot, foe.at) <= policy.reach + CONTACT_RADIUS
        }
        line = policy.choose(replace(seen, origin=spot, foes=within, aimable=bound))
        if line is None or line.worth < max(MIN_SCORE, STEP_GAIN * here):
            continue
        rank = (-line.worth, crowd, ring)
        if found is None or rank < found[0]:
            found = (rank, Stand(spot, line.worth, here, line.unit, ring))
    return found[1] if found is not None else None
