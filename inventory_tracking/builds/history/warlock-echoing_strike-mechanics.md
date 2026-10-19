# builds/warlock/echoing_strike/mechanics.py: design notes

The module docstring until 2026-10-19, moved here by the phase-4 cleanup (numbers and pointers as of then).

Echoing Strike's blades as the recordings show them (combat/plan.md stage 3).

Measured on the second Chaos Sanctuary take (2026-10-09, 268 casts of five blades, missile txt
id 706, owner at unit record offset 0xEC): the five blades spawn AHEAD units in front of the
caster, LATERAL units across the aim line, and each flies straight at the focal point, so they
converge there (the recorded convergence lies at 0.98 of the pointer's distance), pass through
it, reach their furthest point at OUT_FRAMES, then home back on the caster's current position at
the same SPEED and vanish next to them (LIFE frames in all; recorded lifetime 38). Hits land on
the way out and on the way back. The focal point is where the pointer stood about POINTER_LAG
frames before the blades appear (the press, the cast animation, then the spawn). Emulated
against the recorded blade positions with the focal point fitted from the blades themselves,
the root mean square error is 1.0 units outbound and 1.6 on the return.

The game's own rows (combat/data/tables.json, 2026-10-10) agree: missiles.txt 706 `echoingstrike`
has Vel 24, Range 20 frames, ReturnFire 1 (the way back), NextDelay 20 (the same target can be hit
again twenty frames later: once out, once back), CollideType 3 (walls stop it); skills.txt 388 is
a weapon attack (SrcDam 116/128 of the weapon's damage plus 8-12 flat, +30% and +5% per level,
to-hit lvl*10) whose blade count is 1 + Mirrored Blades level / 5 (five at level 20) and whose
blades after the first deal (100 / count) / 2 percent each: 10% with five. So five blades
converging on one monster deal 1.4 times one blade, while a line through five monsters deals
five times: the aim should spread the blades over the pack, not stack them on one body. The
recorded life drops agree: 30/128 at the median with one blade near the monster, 39/128 with all
five.
