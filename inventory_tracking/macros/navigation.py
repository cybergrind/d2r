"""The navigation controller: the means a loop's goals are gone to by, from what the character has (macros/goals-plan.md
§5; the player, 2026-10-19: "navigation to the point: is some kind of goal, handled by navigation controller, that
knows our abilities/equipment (enigma? teleport charges in staff, blade warp, walking, something else, regular sorc
teleport)").

It names the navigation class (macros/movement.py HOPS / WARPS / WALKS) and the loop's move intent (travel.py LOOPED or
LOOPED_TELEPORT); it moves nothing. Every move is still the movement set's (`Ways.means`, `Ways.leg`): a hop that
cannot be made now is walked or warped by the set itself. The order:

1. Teleport of the character's own (Enigma, a Sorceress: Teleport on a key with no staff worn): every move, no charge
   (runner.py LOOPED_TELEPORT for `own_teleport`, 2026-10-18).
2. The staff's charges, while the carried gold pays for them (macros/loop.py `teleports`: from TELEPORT_ON of the gold
   cap until under TELEPORT_OFF) and the staff holds more than LOW_CHARGES (the player's own steps keep those).
3. A jump that costs nothing on a key (the Warlock's Blade Warp: the build's movement sets name it; this module names
   no skill): the walked way, warped where it beats the walk.
4. The walk.
"""

from dataclasses import dataclass

from inventory_tracking.macros.build import Intent
from inventory_tracking.macros.game.records import Teleport
from inventory_tracking.macros.movement import HOPS, WALKS, WARPS
from inventory_tracking.macros.travel import LOOPED, LOOPED_TELEPORT, LOW_CHARGES


@dataclass(frozen=True)
class Abilities:
    """What the character can move by now. `own_teleport`: Teleport is its own (None: unread); `staff`: the worn staff
    with Teleport charges (None: none worn, or unread); `pays`: the gold carried pays for the staff's charges this
    game (macros/loop.py `teleports`; None: not decided); `free_jump`: the name of a jump that costs nothing on a key
    (None: none)."""

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
    """The means in hand (the module text)."""
    if abilities.own_teleport:
        return Means(HOPS, LOOPED_TELEPORT, "Teleport of the character's own: every move")
    staff = abilities.staff
    if staff is not None and staff.charges > LOW_CHARGES and abilities.pays:
        return Means(HOPS, LOOPED_TELEPORT, f"the staff's Teleport ({staff.charges} charges), the gold pays for them")
    if abilities.free_jump is not None:
        unpaid = '' if staff is None else f"; the staff's {staff.charges} charges kept"
        return Means(WARPS, LOOPED, f'{abilities.free_jump} and the walk{unpaid}')
    return Means(WALKS, LOOPED, 'the walk: no Teleport to spend and no free jump')
