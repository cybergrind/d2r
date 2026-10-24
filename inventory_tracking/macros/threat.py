"""Waits that a hostile hitting the character ends (rca/2026-10-23/pause-findings.md).

The player, 2026-10-23 ~11:25: "pauses not like human-like at all, it is like several seconds pause under heavy
attacks, nothing like human at all ... human will react in under 200ms". The loop's fixed waits slept through blows:
the boss drops' "may still be landing" wait (37 pauses, 75 s, 675 life over the nights of 2026-10-22/23) among them.

`watched_sleep` sleeps in FRAME slices and looks at each: with a live hostile within NEAR of the character while its
life has fallen since the wait began, it raises `Abort(cause='beset')`, the loop's own stop for a character hit
standing outside a fight (running/watch.py `poll`, macros/stops.py `first`: the attacker fought back, then the
ground's valuables fetched, life low: the game left). The watchdog alone sees it after BESET_LOSS (5 %) within
BESET_SECONDS, polled once a second: a 2 s wait was over before it.

WATCHED_WAITS (2026-10-23) False: the plain sleep, as before.
"""

import math

from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.records import World
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.native.layout import DEAD_MODES, LIFE_STAT


WATCHED_WAITS = True
FRAME = 0.04  # seconds between the looks of a watched wait: one game frame
NEAR = 10.0  # world units: a hostile this near the character is on it


def near_hostile(world: World, near: float = NEAR) -> bool:
    """A live hostile (not an ally, no owner) within `near` of the character."""
    player = world.player
    if player is None:
        return False
    here = (player.x, player.y)
    return any(
        not m.ally and m.owner == NO_OWNER and m.mode not in DEAD_MODES and math.dist(here, (m.x, m.y)) <= near
        for m in world.monsters
    )


def life_of(run: Run, world: World) -> int | None:
    """The character's life points now; None unread."""
    player = world.player
    if player is None or not player.stats_at or run.unit_stats is None:
        return None
    try:
        stats = run.unit_stats(player.stats_at)
    except OSError, ValueError:
        return None
    return stats[LIFE_STAT] >> 8 if LIFE_STAT in stats else None


def watched_sleep(run: Run, seconds: float, what: str) -> None:
    """`run.pace.sleep(seconds)`, ended by `Abort(cause='beset')` once a hostile within NEAR has the character's life
    falling (WATCHED_WAITS)."""
    if not WATCHED_WAITS or seconds <= 0:
        run.pace.sleep(max(0.0, seconds))
        return
    # Counted slices, not the clock: a clock that the sleep does not move (a test's run) still ends the wait
    slices = max(1, math.ceil(seconds / FRAME - 1e-9))
    began = None
    for index in range(slices + 1):
        world = run.world()
        life = life_of(run, world)
        if began is None:
            began = life
        elif life is not None and life < began and near_hostile(world):
            raise Abort(
                f'the character is hit during {what} ({began - life} life in {min(seconds, index * FRAME):.1f}s, '
                f'a hostile within {NEAR:.0f}): fought back',
                cause='beset',
            )
        if index == slices:
            return
        run.pace.sleep(min(FRAME, seconds - index * FRAME))
