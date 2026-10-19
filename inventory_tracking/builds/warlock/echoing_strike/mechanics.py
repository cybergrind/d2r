"""Echoing Strike's blades as the recordings show them (combat/plan.md stage 3).

Five blades (missile 706) spawn AHEAD of the caster LATERAL across the aim line, fly straight at the focal point
(the pointer POINTER_LAG frames before), converge and pass through it to OUT_FRAMES, then home back on the caster at
SPEED; hits land out and back. The game's rows agree (missiles.txt 706, skills.txt 388): blades after the first on
one monster deal (100 / count) / 2 percent, so five on one body deal 1.4 blades and a line through five monsters
five: spread the blades over the pack. Measures and the fit: builds/history/warlock-echoing_strike-mechanics.md.
"""

import math
from collections.abc import Callable, Sequence

from inventory_tracking.levels.geometry import Point
from inventory_tracking.native.layout import TILE_UNITS


MISSILE = 706  # missiles.txt id of the blade (the player's, slot 9 of the unit table)
BLADES = 5
LATERAL = (-1.9, -0.95, 0.0, 0.95, 1.9)  # across the aim line at the spawn, left to right
AHEAD = 0.8  # units in front of the caster at the spawn
SPEED = 1.12  # units per frame, out and back
OUT_FRAMES = 19  # the furthest point: about 22 units from the caster
LIFE = 38  # frames from spawn to vanishing
HOME = 1.0  # a returning blade this near the caster vanishes
POINTER_LAG = 6  # frames between the pointer that aims the cast and the blades' first frame
RANGE = AHEAD + SPEED * OUT_FRAMES  # 22.1 units


def aim_frame(origin: Point, focal: Point) -> tuple[Point, Point]:
    """Unit vectors along the aim line and across it."""
    away = math.dist(focal, origin) or 1.0
    along = ((focal[0] - origin[0]) / away, (focal[1] - origin[1]) / away)
    return along, (-along[1], along[0])


def stopped(blocked: Callable[[Point], bool] | None, before: Point, after: Point) -> bool:
    """Whether a blade flying from `before` to `after` in one frame meets a wall, at the step's middle or end: a
    step (SPEED) is longer than a cell, so the end alone let blades through one-cell walls (Catacombs 3, 2026-10-10)."""
    if blocked is None:
        return False
    middle = ((before[0] + after[0]) / 2, (before[1] + after[1]) / 2)
    return blocked(middle) or blocked(after)


def cast(
    origin: Point, focal: Point, player_at: Callable[[int], Point], blocked: Callable[[Point], bool] | None = None
) -> list[list[Point]]:
    """The five blades' positions per frame from the spawn (frame 0), left to right across the
    aim line. `player_at(frame)` is where the caster stands then, the return leg's target. A blade
    that reaches a point `blocked` says is a wall (missiles.txt CollideType 3) ends there, out or
    back, and does not return; the middle of each frame's step is looked at too, as a blade flies
    further in a frame than a wall one cell thick is deep (`stopped`)."""
    along, across = aim_frame(origin, focal)
    blades = []
    for lateral in LATERAL:
        start = (
            origin[0] + along[0] * AHEAD + across[0] * lateral,
            origin[1] + along[1] * AHEAD + across[1] * lateral,
        )
        away = math.dist(focal, start) or 1.0
        heading = ((focal[0] - start[0]) / away, (focal[1] - start[1]) / away)
        path = [start]
        for k in range(1, OUT_FRAMES + 1):
            point = (start[0] + heading[0] * SPEED * k, start[1] + heading[1] * SPEED * k)
            if stopped(blocked, path[-1], point):
                break
            path.append(point)
        else:
            x, y = path[-1]
            for frame in range(OUT_FRAMES + 1, LIFE):
                px, py = player_at(frame)
                gap = math.dist((px, py), (x, y))
                if gap < HOME:
                    break
                x, y = x + (px - x) / gap * SPEED, y + (py - y) / gap * SPEED
                if stopped(blocked, path[-1], (x, y)):
                    break
                path.append((x, y))
        blades.append(path)
    return blades


def flown(origin: Point, focal: Point, blocked: Callable[[Point], bool] | None) -> float | None:
    """Units from `origin` the middle blade of `cast` gets on its way out before a wall stops it, the character
    standing; None when it flies out and back. The middle blade flies the aim line, so it says where the cast ends
    at a fraction of `cast`'s price (combat/stance.py `taken`)."""
    if blocked is None:
        return None
    along, _ = aim_frame(origin, focal)
    previous = (origin[0] + along[0] * AHEAD, origin[1] + along[1] * AHEAD)
    for k in range(1, OUT_FRAMES + 1):
        point = (previous[0] + along[0] * SPEED, previous[1] + along[1] * SPEED)
        if stopped(blocked, previous, point):
            return AHEAD + SPEED * (k - 1)
        previous = point
    return None


def focal_point(records: Sequence[Sequence[Point]], first: int = 1, last: int = 9) -> Point:
    """The point nearest the lines the recorded blades fly along between frames `first` and
    `last` (least squares): where a recorded cast converged."""
    a = [[0.0, 0.0], [0.0, 0.0]]
    b = [0.0, 0.0]
    for record in records:
        if len(record) <= first + 1:
            continue  # a blade that died at once (a wall) says nothing of the line
        (x0, y0), (x1, y1) = record[first], record[min(last, len(record) - 1)]
        length = math.hypot(x1 - x0, y1 - y0) or 1.0
        dx, dy = (x1 - x0) / length, (y1 - y0) / length
        projection = [[1 - dx * dx, -dx * dy], [-dx * dy, 1 - dy * dy]]
        for i in range(2):
            a[i][0] += projection[i][0]
            a[i][1] += projection[i][1]
            b[i] += projection[i][0] * x0 + projection[i][1] * y0
    det = a[0][0] * a[1][1] - a[0][1] * a[1][0] or 1e-9
    return (a[1][1] * b[0] - a[0][1] * b[1]) / det, (a[0][0] * b[1] - a[1][0] * b[0]) / det


def errors(records: Sequence[Sequence[Point]], origin: Point, focal: Point, player_at) -> tuple[float, float]:
    """Root mean square distance between recorded and emulated blade positions, (outbound,
    return), the recorded blades matched to the emulated ones by their lateral order."""
    _, across = aim_frame(origin, focal)
    order = sorted(
        range(len(records)),
        key=lambda i: (records[i][0][0] - origin[0]) * across[0] + (records[i][0][1] - origin[1]) * across[1],
    )
    emulated = cast(origin, focal, player_at)
    out, back = [], []
    for index, path in zip(order, emulated, strict=False):
        record = records[index]
        for frame in range(min(len(record), len(path))):
            (out if frame <= OUT_FRAMES else back).append(math.dist(record[frame], path[frame]) ** 2)
    rms = lambda found: math.sqrt(sum(found) / len(found)) if found else math.nan  # ruff: ignore[lambda-assignment]
    return rms(out), rms(back)


def tiles(point: Point) -> Point:
    return point[0] / TILE_UNITS, point[1] / TILE_UNITS
