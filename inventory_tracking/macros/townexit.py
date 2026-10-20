"""The walk out of a town into the first level of a terror zone trip that has no waypoint: the Rogue Encampment into
the Blood Moor, Lut Gholein into the Rocky Waste, the Pandemonium Fortress into the Outer Steppes. The player,
2026-10-19 ~22:20: "for levels that begins from town (blood moore/den and rocky waste/tomb) - find out where is town
exit and use it to run out of the town".

Teleport and Blade Warp are not cast in town (skills.txt InTown), so the way out is walked with `shop.walk_until`'s
clicks. They go along the walk to the town's gate (levels/town_gate.py) and on past its edge until the level changes.
Each step is logged (`Macro: town exit: …`): Lut Gholein's gate was never walked before it was written
(rca/2026-10-19/town-exit-findings.md).
"""

import math
from collections.abc import Callable

from inventory_tracking.common import LOG
from inventory_tracking.game.records import World
from inventory_tracking.levels.geometry import Point
from inventory_tracking.levels.model import Ground, Level
from inventory_tracking.levels.presets import display_name
from inventory_tracking.levels.town_gate import Gate, town_gate
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run


OUT_CLICKS = 40  # walk clicks at most: the longest walk found is ~150 units (the Fortress' stairs), ~13 of STEP
AHEAD = 2.0  # STEPs of the walk ahead of the character a click aims at (walk_until cuts it to one STEP)
ENTERING = 3.0  # seconds for the level guide to have the town the character stands in (pursuit.py ENTERING)
SIDE_NAMES = {(0, -1): 'north', (1, 0): 'east', (0, 1): 'south', (-1, 0): 'west'}


def aim(gate: Gate, here: Point, reach: float, clear: Callable[[Point, Point], bool] | None = None) -> Point:
    """Where the next click aims from `here`: the furthest point of the gate's walk within `reach` and on a `clear`
    line, onward from the walk's point nearest `here` (not past one out of reach or behind a wall: the walk may come
    back near round one); past the edge once the walk's end is so."""
    path = gate.path
    if not path:
        return gate.beyond
    nearest = min(range(len(path)), key=lambda index: math.dist(path[index], here))
    furthest = nearest
    for index in range(nearest, len(path)):
        if math.dist(path[index], here) > reach or (clear is not None and not clear(here, path[index])):
            break
        furthest = index
    if furthest == len(path) - 1 and math.dist(path[-1], here) <= reach:
        return gate.beyond
    return path[furthest]


def walk_out(run: Run, level: Callable[[], Level | None], to: int) -> World:
    """Walk from the town the character stands in into level `to`, across the town's edge; the world there. `Abort`
    out of town, with no gate found, or when the level does not change."""
    from inventory_tracking.macros.shop import STEP, walk_until  # shop.py imports macros below this one

    world = run.world()
    player = world.player
    if player is None:
        raise Abort('no character read')
    if player.area == to:
        return world
    if not player.in_town:
        raise Abort(f'not in town: no walk out into {display_name(to)}')
    town = player.area

    def mapped(_: World) -> bool:
        seen = level()
        return seen is not None and seen.area == town

    run.seen(mapped, ENTERING)
    known = level()
    if known is None or known.area != town:
        raise Abort(f'{display_name(town)}: the level guide has no map of the town')
    from inventory_tracking.macros.travel import clear_line  # travel.py imports shop.py's neighbours

    ground = Ground(known.ground) if known.ground else None
    gate = town_gate(known.rooms, ground.walkable if ground is not None else None, (player.x, player.y))
    if gate is None:
        raise Abort(f"{display_name(town)}: the town's layout is not read: no way out known")
    LOG.info(
        'Macro: town exit: %s into %s: the %s gate at (%.1f, %.1f), %s; from (%.1f, %.1f), past the edge at '
        '(%.1f, %.1f)',
        display_name(town), display_name(to), SIDE_NAMES[gate.side], *gate.edge,
        f'{gate.length:.0f} units of walk on the walls ({len(gate.path)} cells)' if gate.walls
        else "the walls unread: GATES' gate, walked straight",
        player.x, player.y, *gate.beyond,
    )  # fmt: skip
    clicks = 0

    def place(now: World) -> Point | None:
        nonlocal clicks
        if now.player is None:
            return None
        here = (now.player.x, now.player.y)
        there = aim(gate, here, AHEAD * STEP, (lambda a, b: clear_line(ground, (), a, b)) if ground else None)
        clicks += 1
        LOG.info('Macro: town exit: click %d at (%.1f, %.1f) toward (%.1f, %.1f), %.0f units from the edge', clicks,
                 *here, *there, math.dist(here, gate.edge))  # fmt: skip
        return there

    def crossed(now: World) -> bool:
        return now.player is not None and now.player.area != town

    try:
        world = walk_until(run, place, None, f'the way out to {display_name(to)}', until=crossed, clicks=OUT_CLICKS)
    except Abort as stop:
        now = run.world().player
        where = f'at ({now.x:.1f}, {now.y:.1f})' if now is not None else 'unread'
        LOG.info('Macro: town exit: %s: %s, %s', display_name(town), stop, where)
        raise
    player = world.player
    assert player is not None  # `crossed`
    if player.area != to:
        raise Abort(f'the walk out of {display_name(town)} came to {display_name(player.area)}, not {display_name(to)}')
    LOG.info('Macro: town exit: in %s after %d clicks, at (%.1f, %.1f): the edge crossed %.1f units from the gate',
             display_name(to), clicks, player.x, player.y, math.dist((player.x, player.y), gate.edge))  # fmt: skip
    return world
