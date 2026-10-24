"""The late bind's targets (actuator.py LATE_BIND, 2026-10-23, rca/2026-10-23/realtime-3-findings.md): where an aim's
spot is in the window by the newest look, taken again by the actuator at the input (`Actuator.bound`).

The decision keeps its own look (the spot, the prey, the line); only its place in the window is re-taken: from where
the newest look sees the character, and for a strike with the prey's move since added to the focal. `aim` passes the
bind only with the switch on, so a run's actuator that knows no bind (tests, harnesses) is asked as before.
"""

from collections.abc import Callable
from typing import Any

from inventory_tracking.game.records import Monster, World
from inventory_tracking.game.view import Viewport
from inventory_tracking.levels.geometry import Point
from inventory_tracking.macros import actuator


Fraction = tuple[float, float]
# 2026-10-23 (realtime-3-findings.md §3): the strike's focal also moved as its prey moved since the fight's look. The
# arena (fane, pursuit scenes): the Herald killed 1-4 s later with it, the line through the pack broken. False: only the
# window's own move is taken again (the character's place now), the focal as the fight chose it.
STRIKE_FOLLOWS = False


def newest_world(run: Any, *, light: bool = False) -> Any:
    """The newest look of the game for a bind (with FRAMES, the reader's newest frame: 0.1-0.4 ms). One function for
    every bind, so the arena's gate can look without its look's side effects (the arena starts held casts at a look:
    a bind's extra look would change the fight there, never in the game)."""
    if light:
        with run.lightly():
            return run.world()
    return run.world()


def aim(run: Any, where: Fraction, *, scatter: tuple[int, int], bind: Callable[[], Fraction | None]) -> None:
    """`run.actuator.aim(*where, scatter=scatter)`, with `bind` while LATE_BIND is on."""
    if actuator.LATE_BIND:
        run.actuator.aim(*where, scatter=scatter, bind=bind)
    else:
        run.actuator.aim(*where, scatter=scatter)


def strike_world(run: Any) -> World:
    """The strike bind's look (`newest_strike`): the newest world. Apart from `newest_world` so a harness can give the
    strike's look alone a peek with no side effects (2026-10-24: the loop and battle goldens, whose reads are frozen).
    """
    return newest_world(run)


def newest_strike(run: Any, prey: Monster, focal: Point, view: Viewport) -> Fraction | None:
    """Where the strike's focal is in the window by the newest look: aimed from where the character stands now, the
    focal moved as the prey moved since the fight's look with STRIKE_FOLLOWS. None: no character, the prey not in the
    look (dead, gone, another level), or off the screen."""
    world = strike_world(run)
    player = world.player
    if player is None:
        return None
    now = next((m for m in world.monsters if m.unit_id == prey.unit_id), None)
    if now is None:
        return None
    moved = (focal[0] + now.x - prey.x, focal[1] + now.y - prey.y) if STRIKE_FOLLOWS else focal
    return view.aim((player.x, player.y), moved)
