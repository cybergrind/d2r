"""The Echoing Strike Warlock as the one object the framework asks (macros/build.py `Build`).

Movement and the buff plan so far: the attack and the weapon sets are still in macros/ and combat/,
and move here task by task (framework-plan.md Stage 3).
"""

from inventory_tracking.builds.warlock.buffs import BUFFS
from inventory_tracking.builds.warlock.casters import CASTERS
from inventory_tracking.builds.warlock.movement import MOVEMENT
from inventory_tracking.macros.build import Build
from inventory_tracking.macros.skills import ECHOING_STRIKE
from inventory_tracking.macros.world import World


def strikes(world: World) -> bool:
    """Whose it is: a character with Echoing Strike where it is cast from, a skill key or a mouse
    button (what hunt.py `strike_input` holds). Not with no character in the world."""
    player = world.player
    if player is None:
        return False
    return ECHOING_STRIKE in world.slots or ECHOING_STRIKE in (player.left_skill, player.right_skill)


ECHOING_STRIKE_BUILD = Build(
    name='echoing strike warlock',
    applies=strikes,
    attack=None,
    movement=MOVEMENT,
    buffs=BUFFS,
    casters=CASTERS,
)
