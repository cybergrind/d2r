# combat/sim/diablo.py: design notes

The module docstring until 2026-10-19, moved here by the phase-4 cleanup (numbers and pointers as of then).

Diablo (monstats `diablo`, txt 243, AI 51 "Diablo") as the client's code plays him: his think, his red lightning
stream, his fire ring and fire wall, his swings. sim/casters.py `Minds` plays him (`DIABLO`) as it plays the four
Chaos Sanctuary casters; this module holds his rules and his rows (diablo.json, written by `build` below from the
game's tables).

Sources (rca/2026-10-13/re/notes-ai-diablo.md has the addresses and the decompiled reading; rca/2026-10-13/diablo.md
the checks against the takes):

- **[code]** read in Binary Ninja: the think `ai_d2_ai_51_think` (0x14047EC70), its weight table
  `ai_d2_ai_51_decide` (0x14047DD70), the target search `ai_d2_ai_51_find_target` (0x14047E880) and its score
  (0x14047D4A0), the lightning's start and do functions (srvstfunc 53 0x140470950, srvdofunc 152 0x140470F60) and
  the aim (0x1403AD6B0: each missile goes at where the target stands when it is made);
- **[table]** diablo.json from pricing/raw/game-excel: his row, his skills, their missiles;
- **[take]** measured on the 19 recorded Diablo fights (rca/2026-10-13/scripts/diablo_takes.py, diablo-takes.txt;
  diablo_releases in diablo.md section 2): a mode's frames, the frame of it a missile is let go at, how many, how
  fast they go;
- **[inferred]** what neither settles, named where it is chosen.

**The think** [code]. No target search radius to speak of (anyone in the act within 1020 sub-tiles) and no sight
needed to notice. Each think draws one of 17 actions with the weights of `weights` (a sum, one roll uniform over it)
from three tables: the target in melee, out of melee in sight, out of melee out of sight; then changed by the
target's resistances (he favours the element it resists less: fire raw stat against lightning), the distance (no
lightning at all beyond LIGHTNING_RANGE: the run and the wall take its place), how many candidates he has, his and
the target's distance from his home. After an action he thinks again at its mode's end plus `aidel` (12 in Hell).

**The red lightning** (DiabLight, mode SC) [code + take]: the cast puts state 12 `inferno` on him and an end frame
40 frames on (Param1); from the do frame on (10 frames into SC [take]) one missile 172 a frame [take: 38 to 39 a
cast], each **aimed at where the target stands at that frame** (it follows the target), flying STREAM_STEP a frame
[take: 0.88] for Param2 + level - 1 frames (39 at level 10 [code + take]), through every body (Pierce). A missile
takes its points x `DamageRate` / 1024 (82) **each frame a body is within CONTACT of it** [take-checked: a standing
character loses 16 points a frame of the stream at 75 % lightning resistance, the table's 34 raw a hit x 0.08 x
about 6 missiles in contact]. Points at level 10 (Sk1lvl 3 + 7): physical 24.3..26.3, lightning 42.3..52.5
(HitShift 6) [table + code].
