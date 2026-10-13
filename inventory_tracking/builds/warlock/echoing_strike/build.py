"""The Echoing Strike Warlock as the one object the framework asks (macros/build.py `Build`).

The attack, movement, the buff plan, the guard Psychic Ward keeps (`Shield`) and the draw of Death Mark (`Draw`).
The weapon sets are a character's own: the layer of a character gives them (builds/characters.py), and the build as
it is here has none.
"""

from inventory_tracking.builds.warlock.buffs import BUFFS, ward_shown
from inventory_tracking.builds.warlock.casters import CASTERS
from inventory_tracking.builds.warlock.echoing_strike.attack import ECHOING_STRIKE_ATTACK
from inventory_tracking.builds.warlock.mark import DEATH_MARK_DRAW
from inventory_tracking.builds.warlock.movement import MOVEMENT
from inventory_tracking.builds.warlock.skills import ECHOING_STRIKE
from inventory_tracking.builds.warlock.ward import PSYCHIC_WARD_GUARD
from inventory_tracking.macros.build import Build, Shield
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
    shield=Shield(PSYCHIC_WARD_GUARD, ward_shown),  # Psychic Ward: the safety price credits its pool and stun
    draw=DEATH_MARK_DRAW,  # Death Mark sends the demons onto a monster: the safety price weighs it (mark.py)
)
