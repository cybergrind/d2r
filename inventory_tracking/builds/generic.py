"""The build for a character no build claims: no fight of its own, and the ways any character moves by."""

from inventory_tracking.macros.build import Build
from inventory_tracking.macros.movement import SHARED
from inventory_tracking.macros.world import World


def everyone(world: World) -> bool:
    """Whose it is: any character. Not with no character in the world."""
    return world.player is not None


# The shared movement sets as they are: Teleport from a worn staff or as a skill of the character's own, else a walk.
GENERIC = Build(name='generic', applies=everyone, attack=None, movement=SHARED)
