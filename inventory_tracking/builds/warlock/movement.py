"""How a Warlock moves: the shared movement sets with Blade Warp among their jumps.

Blade Warp needs a clear line (a thrown blade), spends no staff charge and needs no swap, but has a casting delay:
it comes before a staff's Teleport. Teleport of the character's own (Enigma) comes first (the player, 2026-10-18:
"now we have an enigma ... stop using blade warp in almost all situations"). Blade Warp is still asked for by name
to bring the mercenary out of danger (`JumpSource.brings`) and on Mephisto's bridge.
"""

from inventory_tracking.builds.warlock.skills import BLADE_WARP
from inventory_tracking.combat.stance import Jump
from inventory_tracking.macros.build import JumpSource
from inventory_tracking.macros.movement import SHARED, OwnTeleport
from inventory_tracking.macros.travel import JUMP_LEAST, JUMP_REACH


# Seconds between the keys of two Blade Warps: the skill's 20-frame delay counts from the cast's action frame, about
# 0.2 s after the key (state 185 `cooldown`, take of 2026-10-13 12:33); 0.8 s from the key was refused.
WARP_DELAY = 1.05
# Seconds from a key before which the delay state read clear is not yet the cooldown over: it clears a tick or so
# before the game takes the next cast (rca/2026-10-14/run-0305-findings.md §5.1).
WARP_CLEARED = 1.0
# What a jump takes from its key to standing there, for the choice of a place (combat/stance.py `Jump`).
WARP_SECONDS, WARP_SPEED = 0.35, 45.0  # Blade Warp: the cast, then the blade's flight in units a second
# JUMP_REACH: units of a jump: in view, and within the blade's range. The blade flies there: no wall in its way.
BLADE_WARP_JUMP = Jump(BLADE_WARP, WARP_SECONDS, WARP_SPEED, JUMP_REACH, JUMP_LEAST, line=True)
# In controller mode the blade flies controllerskillsettings.json `defaultTargetDistance` along the stick.
BLADE_WARP_PAD_REACH = 17.0
# Blade Warp brings the character's minions and the mercenary with it (the player, 2026-10-14: "it can be used to
# reposition the merc to avoid his death"): combat/escort.py prices a warp for that.
BLADE_WARP_SOURCE = JumpSource(
    BLADE_WARP_JUMP, delay=WARP_DELAY, cleared=WARP_CLEARED, pad_reach=BLADE_WARP_PAD_REACH, brings=True
)

# The shared sets in their order: Teleport of the character's own first (with Enigma a set's first jump is taken
# everywhere, 2026-10-18), then the blade, then a staff's Teleport.
MOVEMENT = tuple(
    shared.then(BLADE_WARP_SOURCE) if isinstance(shared, OwnTeleport) else shared.led_by(BLADE_WARP_SOURCE)
    for shared in SHARED
)
