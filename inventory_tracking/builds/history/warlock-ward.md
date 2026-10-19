# builds/warlock/ward.py: design notes

The module docstring until 2026-10-19, moved here by the phase-4 cleanup (numbers and pointers as of then).

Psychic Ward as the combat simulator plays it: a guard (combat/sim/guard.py) on the character
(rca/2026-10-13/re/notes-absorb.md has the client's code; skills.txt 387).

- The pool [take]: 185 points. The takes' `character_stats` hold stat 361 `psychicward` = 362 `psychicwardmax` =
  47,360 (x256) in 32 of the 35 takes of 2026-10-12/13 whose stats hold the ward (34,560 = 135 in two of
  2026-10-12 evening; 135,680 = 530 in one, 092319, of a level 99 character). The table's formula is
  (ln34 + (Levitate + Cleave base levels) x par8) x 256 with ln34 = 15 + 10 per level above 1 and par8 15.
- The kinds [code]: physical only (the handler reads and writes the record's physical field alone).
- The stun [table + inferred level]: calc1 = dm12, 37 + (85 - 37) x (110 L / (L + 6)) / 100 frames at the ward's
  level L. L is not recorded. The pool fixes it to 12 (synergy levels 4) or 15 (2): 185 = 15 + 10 (L - 1) + 15 s
  with s >= 2 (Cleave and Levitate are its prerequisites) and L >= 10 (stat 127, all skills, 9 in the take of
  14:16 on 2026-10-13); dm12 is 72 frames at 12 and 74 at 15. WARD_LEVEL takes the first: a named stand-in.
  The records of 2026-10-13 show a Doom Knight stunned 3.1 to 3.6 s after its swing at their resolution.
