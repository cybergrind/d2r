# combat/sim/baal.py: design notes

The module docstring until 2026-10-19, moved here by the phase-4 cleanup (numbers and pointers as of then).

Baal in the Worldstone Chamber (monstats `baalcrab` 544, AI BaalCrab) and his clone (`baalclone` 570, AI
BaalCrabClone) as the arena plays them: his think, his casts, their missiles, the tentacles he raises and the clone he
splits off. sim/casters.py `Minds` plays him (`BAAL`) as it plays Diablo; this module holds his rules and his rows
(baal.json, written by `build` below from the game's tables). rca/2026-10-14/re/baal-ai.md has the reading,
rca/2026-10-14/baal-sim.md the evidence before it.

**His think is read** (2026-10-14, the pages decrypted by the player's dumps of a Baal fight): `ai_d2_ai_135_baalcrab_
think` 0x1404B9E80 and the clone's 0x1404BA810 in pricing/raw/re/D2R-decrypted.exe.bndb; the code follows D2MOO's
AiBaal.cpp (1.10) but for his teleport and his target score. Sources, as each number says:

- **[code]** read in the client (the routine's address in rca/2026-10-14/re/names.md);
- **[table]** baal.json from pricing/raw/game-excel (his row, the skills' damage, the missiles), monseq/levels of
  third-parties/d2data;
- **[take]** the last 3 s of the Throne take 20261011T001816Z-131 (S2 24 frames, S3 22 frames, a tentacle's swing);
- **[probe]** the alt-d terror probes of eight Baal kills (rca/2026-10-14/baal-sim.md section 1);
- **[inferred]** what neither settles, named where it is chosen.

**The think** [code]: every THINK_FRAMES (25) frames, whatever he did (the think's tail deletes his AI events and sets
the next at frame + 25; every act of his lasts 25 frames or less). His target is the best score among the character
and the companions (`aim`): the character wins outright once it has hit him within THREAT_FRAMES and stands within
THREAT_REACH (the D2R threat state 231, the damage it dealt him, weighs on top of the 1.10 score); before that the
1.10 score's known parts decide (in his melee 500, in sight 375; ties go to the character, scored first). One draw
over 16 weights (`weights`, by melee, sight, the distance less size, his life, the candidates' count, the best score,
the clones made) picks the act. Out of melee in sight, Hell: idle 200 - life %, the four walks 5 each, Defense Curse
40 (70 once the best score passes 60), tentacles 40, nova 70 (0 beyond 25), inferno 80, cold missiles 60 (+25 with
four or more candidates, 0 beyond 35), teleport 20 (30 beyond 25), clone 20 then 10 then 0.

- *nova* (S3): 64 missiles 555 in a ring [code], NOVA_STEP a frame for `Range` 40 frames, fire 218..243 [table], one
  hit a body a ring [inferred, as Diablo's ring];
- *inferno* (his sequence, shown as SQ): the do-function is Diablo's DiabLight one [code: srvdofunc 95 = 152]: each
  missile 554 flies at where his target stands when it is made; the stream ends Param1 20 frames after it began
  [code + table]; the first at the sequence's do event, frame 11 [table: monseq seq_baalinferno], then one a frame
  as Diablo's takes show for the same function [take, Diablo] (10 missiles); a missile lives 19 frames [take rule] and
  takes INFERNO_SHARE of its points a contact [probe, fitted];
- *cold missiles* (A1): ONE maker 589 at his target's point [code], 0.96 a frame for 50 frames, which each frame it
  enters a new sub-tile sheds two trails 590, one each way across its line [code: the perpendicular stored; D2MOO the
  shedding], 0.62 a frame for 20 frames: a band 12 units to each side of his line; cold 83..103 a hit [table]; a cast
  takes from a body once, maker and trails together [inferred, fitted: after a look in A1 the probe's character lost
  20 at the median, 34 on average, 176 at most in 1.5 s, about one hit of 23 after its resistance; trails each
  taking their own hit would be some eleven];
- *tentacles* (S2): 4 to 6 tries [code: roll % 3 + 2 + Hell's 2], each at his target + (-9..8, -9..8) [code], of one
  class a cast, 564 or 565 [code + D2MOO]; a try on bad ground is lost; each stands TENTACLE_SECONDS [probe];
- *Defense Curse* (S3) on bodies within 12 of his target for 875 frames [table]; Blood Mana only on a player whose
  most mana passes its most life [code]: not this character [probe: state 114 never seen];
- *teleport* (A1): to a random point of the 40 x 40 room he stands in [code: room bounds + 1 .. + 39, 20 tries], not
  toward or away from anyone; the Chamber's rooms by its preset [table: level 132 at sub-tile 15000, 5760];
- *clone*: no life threshold, no timer [code]: an act of the draw (out of melee, in sight), only while no clone of his
  lives; at his target + (-12..11, -12..11), with a third of his life and of his most life [code]; it thinks as he
  does but never raises tentacles, teleports or clones (those draws walk) [code], and dies with him [code];
- *smash* (A2) in his melee only [code]; the walks: up to 12 toward the target, round it, 16 about himself, home.
