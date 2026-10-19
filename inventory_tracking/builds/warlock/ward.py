"""Psychic Ward as the combat simulator plays it: a guard (combat/sim/guard.py) on the character (skills.txt 387;
rca/2026-10-13/re/notes-absorb.md). The pool [take]: 185 points (stats 361 = 362 in the takes of 2026-10-12/13).
The kinds [code]: physical only. The stun [table]: calc1 dm12 frames at the ward's level, not recorded: WARD_LEVEL
is a stand-in fixed by the pool. The derivation: builds/history/warlock-ward.md.
"""

from inventory_tracking.combat.sim.guard import GuardRule


WARD_POOL = 185.0  # points
WARD_LEVEL = 12  # stand-in: 12 or 15 by the pool (module text)


def dm12(level: int, least: int = 37, most: int = 85) -> int:
    """skills.txt's `dm12` (Param1, Param2) at `level`: the game's diminishing returns, integer steps."""
    return least + (most - least) * (110 * level // (level + 6)) // 100


PSYCHIC_WARD_GUARD = GuardRule(most=WARD_POOL, kinds=('physical',), stun=dm12(WARD_LEVEL))
