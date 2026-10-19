"""The navigation controller: which means a loop's goals are reached by, from what the character has
(macros/goals-plan.md §5; the player, 2026-10-19: "handled by navigation controller, that knows our
abilities/equipment").

It names the navigation class (movement.py HOPS / WARPS / WALKS) and the move intent; it moves nothing (the movement
set does, walking or warping a hop it cannot make). The order:

1. Teleport of the character's own (Enigma, a Sorceress): every move, no charge.
2. The staff's charges, while the gold pays for them (loop.py `teleports`) and more than LOW_CHARGES are left.
3. A free jump on a key (Blade Warp; named by the build), warped where it beats the walk.
4. The walk.
"""

from dataclasses import dataclass

from inventory_tracking.game.records import Teleport
from inventory_tracking.macros.build import Intent
from inventory_tracking.macros.movement import HOPS, WALKS, WARPS
from inventory_tracking.macros.travel import LOOPED, LOOPED_TELEPORT, LOW_CHARGES


@dataclass(frozen=True)
class Abilities:
    """What the character can move by now; None is unread or undecided. `staff`: the worn staff with Teleport
    charges; `pays`: the gold pays for its charges this game; `free_jump`: the name of a no-cost jump on a key."""

    own_teleport: bool | None = None
    staff: Teleport | None = None
    pays: bool | None = None
    free_jump: str | None = None


@dataclass(frozen=True)
class Means:
    """The class a far goal is planned by (`kind`), the intent the loop's moves are asked with, and why."""

    kind: str
    intent: Intent
    why: str


def means(abilities: Abilities) -> Means:
    """The means in hand, in the module's order."""
    if abilities.own_teleport:
        return Means(HOPS, LOOPED_TELEPORT, "Teleport of the character's own: every move")
    staff = abilities.staff
    if staff is not None and staff.charges > LOW_CHARGES and abilities.pays:
        return Means(HOPS, LOOPED_TELEPORT, f"the staff's Teleport ({staff.charges} charges), the gold pays for them")
    if abilities.free_jump is not None:
        unpaid = '' if staff is None else f"; the staff's {staff.charges} charges kept"
        return Means(WARPS, LOOPED, f'{abilities.free_jump} and the walk{unpaid}')
    return Means(WALKS, LOOPED, 'the walk: no Teleport to spend and no free jump')
