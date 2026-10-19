# combat/sim/casters.py: design notes

The module docstring until 2026-10-19, moved here by the phase-4 cleanup (numbers and pointers as of then).

The Chaos Sanctuary's monsters as the game's own code plays them: the four AI routines read in the client,
their skills and missiles from the game's tables, the curses as states on whom they land.

sim/monsters.py plays every type by what the takes show of it (a fitted swing, a fitted shot). Four types
had nothing of their own there, and three of them are casters it played as walkers or as pooled shooters:
the Storm Caster (306), the Doom Knight (310), the Oblivion Knight (312) and the Venom Lord (362), and every
row of monstats with the same AI (the seal bosses are such rows with a rank). Here a monster of those AIs
thinks as the client's code does and casts what its row says; `Pack` hands such a walker to `Minds`.

Sources, as each number below says where it is set:

- **[code]** the think routines read in Binary Ninja (rca/2026-10-13/re/notes-ai.md: the frame every routine
  runs in, AI 70 FingerMage, AI 72 DoomKnight; notes-ai-74.md: AI 74 OblivionKnight; notes-mobs.md: AI 89
  Megademon, the target search, the walk helpers), and the damage rules (notes-damage.md: skill and
  missile damage by level, resistances, to-hit);
- **[table]** casters.json, written by build_casters.py from the game's tables (monstats, skills, missiles,
  difficultylevels, states): the AI parameters, skills and their levels, the missiles' speed, range and
  damage, the curses' effects, lengths and radii;
- **[take]** measured on the train half of the Chaos Sanctuary takes (rca/2026-10-13/scripts/casters_measure.py,
  output casters-measure-train.txt): the length of a mode (a cast, a swing), the frame of it a missile is let
  go at, and how far a missile goes in a frame per point of its `Vel` (the code that turns `Vel` into a step
  is in the encrypted missiles parser page). The client's animation data would give the first two; it is
  not on disk;
- **[inferred]** what neither says and a choice had to be made: named where it is made.

**The frame (all four)** [code]. A monster with no target stands and looks again after 10 frames while the
character is within 25, `d - 10` frames to 35, 25 frames beyond. Its target is the nearest of the character
and its companions within the radius (`aidist`, empty for all of them: 35) by the AI's metric, max(|dx|,
|dy|) + min(|dx|, |dy|) / 2 in sub-tiles (the arena's units); none beyond 55 of the character. Sight is
needed only until the monster first had a target; after that it finds the nearest through walls. Chosen
again at every think: no threat, no memory. After an action the next think comes at the end of its mode
plus `aidel` (13 frames, 11 for a Venom Lord); after an idle of n frames, n frames on. A walk is no mode
that ends here: the monster walks on toward its goal and thinks again `aidel` frames after it set out
[inferred: the code schedules the think from the mode's base frame; for a walk that frame is taken as the
start]. Rolls are 0 to 99 from the monster's own generator (the pack's, one per unit, seeded by the
play's seed), "roll < aipN" as the code has it.

**What is not the game's**: a monster's body bars nothing; a missile flies through walls (as the pack's other
missiles) and ends on a body within SHOT_CONTACT of it; melee reach is the pack's REACH for every type;
a monster in its pack does not wake its pack-mates (the game shares the first-sight flag in a pack: the
scene has no packs); the companions take blows and do not die (their life in points is in no take) and
deal nothing; a curse changes the character's resistances only (Decrepify's slower run and attack, and
its halved damage, are not played).
