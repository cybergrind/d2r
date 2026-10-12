"""The Echoing Strike Warlock as the one object the framework asks (macros/build.py `Build`).

The attack, movement and the buff plan. The weapon sets are a character's own: the layer of a
character gives them (builds/characters.py), and the build as it is here has none.
"""

from inventory_tracking.builds.warlock.buffs import BUFFS
from inventory_tracking.builds.warlock.casters import CASTERS
from inventory_tracking.builds.warlock.echoing_strike.attack import ECHOING_STRIKE_ATTACK
from inventory_tracking.builds.warlock.movement import MOVEMENT
from inventory_tracking.builds.warlock.skills import ECHOING_STRIKE
from inventory_tracking.macros.build import Build
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
    attack=ECHOING_STRIKE_ATTACK,
    movement=MOVEMENT,
    buffs=BUFFS,
    casters=CASTERS,
)
