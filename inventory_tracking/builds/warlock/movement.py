"""How a Warlock moves: the shared movement sets, each with Blade Warp before its own jumps.

Blade Warp throws a blade and puts the character where it lands, so it needs a clear line there, as
a shot does; it spends no charge of a staff and needs no weapon swap, and it has a casting delay.
That is why it comes first in every set: with a staff worn, with Teleport as a skill of the
character's own, and with neither.
"""

from inventory_tracking.builds.warlock.skills import BLADE_WARP
from inventory_tracking.combat.stance import Jump
from inventory_tracking.macros.build import JumpSource
from inventory_tracking.macros.movement import SHARED
from inventory_tracking.macros.travel import JUMP_LEAST, JUMP_REACH


# A stride is a jump when a skill makes one without a weapon swap: Blade Warp first (skills.txt 390, a casting
# delay of 20 frames, spends no charges), else Teleport when in hand or a skill of the character's own (Enigma).
WARP_DELAY = 0.8  # seconds between two Blade Warps (the skill's casting delay)
# What a jump takes from its key to standing there, for the choice of a place (combat/stance.py `Jump`).
WARP_SECONDS, WARP_SPEED = 0.35, 45.0  # Blade Warp: the cast, then the blade's flight in units a second
# JUMP_REACH: units of a jump: in view, and within the blade's range. The blade flies there: no wall in its way.
BLADE_WARP_JUMP = Jump(BLADE_WARP, WARP_SECONDS, WARP_SPEED, JUMP_REACH, JUMP_LEAST, line=True)
BLADE_WARP_SOURCE = JumpSource(BLADE_WARP_JUMP, delay=WARP_DELAY)

# The shared sets in their order, the blade first in each: Blade Warp, then Teleport, then the walk.
MOVEMENT = tuple(shared.led_by(BLADE_WARP_SOURCE) for shared in SHARED)
