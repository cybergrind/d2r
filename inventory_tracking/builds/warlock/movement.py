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
# Seconds between the keys of two Blade Warps. The game counts the skill's delay of 20 frames (0.8 s) not
# from the key but from the cast's action frame: in the take of 12:33 on 2026-10-13 the character's state
# 185 `cooldown` was set 0.20 s after the key (0.17 to 0.23) and held 0.80 s (0.77 to 0.82), 64 warps of 64.
# Counted as 0.8 s from the key, a second warp pressed 0.8 to 1.0 s after the first was refused by the
# game and then waited on for JUMP_SECONDS (36 of 46 such keys over 2026-10-11 to 13; 2 of 296 from 1.05 s).
WARP_DELAY = 1.05
# Seconds from a key's down before which the delay state read clear is not yet Blade Warp's cooldown over (the
# skill's 20 frames from the cast's action frame: 1.0 s from the key, rca/2026-10-13/re-findings.md item 4). The
# state clears 0.96 to 1.03 s after the key, a tick or so before the game takes the next cast: over the games of
# 00:25, 02:19 and 06:05 on 2026-10-14 every refused key came 0.928 to 0.986 s after the one before, each on a
# look that read the state clear (11 of 17 such keys refused), and none of the 98 keys 0.99 s or more after it
# (rca/2026-10-14/run-0305-findings.md §5.1, scripts/warp_gaps.py).
WARP_CLEARED = 1.0
# What a jump takes from its key to standing there, for the choice of a place (combat/stance.py `Jump`).
WARP_SECONDS, WARP_SPEED = 0.35, 45.0  # Blade Warp: the cast, then the blade's flight in units a second
# JUMP_REACH: units of a jump: in view, and within the blade's range. The blade flies there: no wall in its way.
BLADE_WARP_JUMP = Jump(BLADE_WARP, WARP_SECONDS, WARP_SPEED, JUMP_REACH, JUMP_LEAST, line=True)
# In controller mode the blade flies its controller `defaultTargetDistance` in the stick's direction (read,
# controllerskillsettings.json: 17 units; where it lands is measured by `Pad jump:` lines, macros/pad.py).
BLADE_WARP_PAD_REACH = 17.0
# Blade Warp brings the character's minions and the mercenary with it (the player, 2026-10-14: "it can be used to
# reposition the merc to avoid his death"): combat/escort.py prices a warp for that.
BLADE_WARP_SOURCE = JumpSource(
    BLADE_WARP_JUMP, delay=WARP_DELAY, cleared=WARP_CLEARED, pad_reach=BLADE_WARP_PAD_REACH, brings=True
)

# The shared sets in their order, the blade first in each: Blade Warp, then Teleport, then the walk.
MOVEMENT = tuple(shared.led_by(BLADE_WARP_SOURCE) for shared in SHARED)
