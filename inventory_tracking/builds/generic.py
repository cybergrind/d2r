"""The build for a character no build claims: no fight of its own, and no movement sets until the
shared ones exist (a later stage adds them)."""

from inventory_tracking.macros.build import Build
from inventory_tracking.macros.world import World


def everyone(world: World) -> bool:
    """Whose it is: any character."""
    return True


GENERIC = Build(name='generic', applies=everyone, attack=None, movement=())
