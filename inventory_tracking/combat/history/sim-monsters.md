# combat/sim/monsters.py: the model and its fit

The module docstring until 2026-10-19 (phase-4 cleanup moved it here). Numbers are the fit of that time;
`data/monsters_fit.json` and the evidence reports beside `tests/inventory_tracking/scenarios/arena/evidence/fit.py`
are the current ones.

Monsters that walk, strike and shoot by themselves: the least a fight needs to answer what the
character does.

The simulator's engine replays a take's monsters open loop (sim/engine.py): they are where they were,
whatever the character does. Here a monster moves as the client's code does and hurts as the takes
show. Three kinds of numbers are in it, and each is said where it is set:

- **read from the game** (data/tables.json): a blow's points, the bonuses of rank, enchantment and
  Herald tier, the walk's chances and speed, the missiles of the enchantments;
- **fitted to one take** (Tower Cellar 5, combat/plan.md 2026-10-11): how a monster walks (the
  constants below);
- **fitted to the train half of all takes** (data/monsters_fit.json, written by
  tests/inventory_tracking/scenarios/arena/evidence/fit.py from that directory's evidence.json,
  sparks.json and swings.json and never by hand; EVIDENCE.md, SPARKS.md and SWINGS.md there are the
  measurements): how long a swing is and how long the rest after it, where in it the blow lands, how
  often a swing that ran out takes life, what a struck monster does, whom a monster goes for, how its
  blows are spread in size, how far it reaches, how a shooter shoots, the nova of a death, the sparks
  of a Lightning Enchanted one. Every number there has its n; a type with too little of its own (the
  evidence's thresholds: 30 s in reach or 10 blows alone for a row; 30 swings run out for a chance of
  its own; 20 shots) uses the pooled row. 332 takes, 9,828 s, one character.

**Walking** (the think function read in the client, the classic scheme of the monstats row): free,
with its target out of reach, a roll of 0-99 under `aip1` walks to it, else it stands `aip2` frames;
a target further off than AWARE is none (Tower Cellar 5: beyond 20 units the Blood Clan and Devilkin
stood 88 to 100% of the frames). A walk goes straight at the target at the monstats `Velocity` times
PACE in world units a second, for WALK_FRAMES at most or until the target is in reach.

**Whom it goes for** (fitted, `targets`): the character or the nearest of its companions. The path
records name the character 0.92 of the time when it is the nearer of the two and 0.51 when a
companion is (the types fought hand to hand, 4,696 and 5,184 s; 16 types have their own pair). How
long a monster keeps to one target is not measured: here each monster has one roll for its life, and
goes for the character when that roll is under the share of the case it is in, so the shares come out
over a pack and no monster wavers. (Before: the nearest of all, the character first for a Goatman.)

**Swinging** (fitted, `melee`; SWINGS.md): with its target within the swing's reach a monster swings.
A swing lasts the usual length of the type's attack runs (10 to 24 frames by type; STRIKE_FRAMES
where not measured), its blow lands two thirds of the way through it (0.67: the median place of 22
drops put on one monster alone) and after it the monster rests before it thinks again: 15 frames at
the median of 50 rests, drawn through their deciles (8 to 36). So a monster nobody strikes swings
every 1.3 s or so. The row's `aip3` and `aip2` do not decide how often it swings in reach: their
classic meaning gives a Blood Hawk 0.03 swings a second where the takes show 1.5. `aidel` is read
and still not used.

**A struck monster staggers** (fitted, `melee.stagger`; `Pack.struck` is told what share of its most
life a hit took). The hits between two steps are one fall of its life, as a take's frames show them,
and the monster staggers with the chance of a fall of that size: 0.06 under a sixteenth of its life,
0.24 to two sixteenths, 0.69 and 0.72 to three and four, 0.93 above (4,066, 697, 635, 320 and 3,217
falls on the train half). It then stands for the frames the takes show (10 at the median of 1,573
spells, drawn through their deciles) and rests as after a swing before it thinks again (the gap
from a staggered swing to the same monster's next was 29 frames at the median of 16: the stagger
and that rest). **A swing whose blow has not landed when the monster staggers is lost.** A dead
monster is gone with its swing (`died`, `remove`). On the train half 0.23 of the swings at the
character ran out, 0.35 ended in a stagger and 0.24 in the monster's death (0.17 not seen to
their end): what the character does to the monsters decides most of what they do to it. Before
2026-10-13 a share of swings (0.29) was cut short by a roll, whatever the character did. A shooter
does not stagger here (not measured), and how long a monster of each type staggers is one curve.

**A swing is not a hit** (fitted, `takes_life`). A swing lands if the monster has not staggered and
the target is still within the swing's reach, and on the character it takes life only with a
chance: 0.30 pooled (0.15 to 0.44 of 98 swings that ran out at a character standing still; 0.37 of
the 23 with no other hostile beside it), a Devilkin's own 0.16 (38); no other type has the 30 such
swings for a chance of its own. That chance is **one number for several things a take cannot tell
apart**: the miss of the to-hit roll, a block, and a blow that whatever protects the character took
whole. It was measured on one character and is that character's; another build would need its own.
Neither the character's leaving nor its strikes are in it: here a blow already fails when the
target has left the reach or the monster has staggered, so a change of how the character moves or
strikes is answered by the model, not by this chance. (Before 2026-10-13 it was 0.16 of every
swing of half its length or more, with the strikes folded in: a character that did not strike for
two seconds was hurt as seldom as one that did, and a recorded fight showed four times the loss,
tests/.../arena/fixtures/incidents/INCIDENTS.md.) The bounds are wide: the low one counts the drops
put on that monster alone, the high one those it shares with other suspects, and the middle is
used; **in a pack hardly any drop is one monster's alone, so there the middle is too low** by an
amount the takes do not give (the Chaos Sanctuary's Doom Knights: 0.00 to 0.76 of 21 on the check
half, 11 of 14 by hand in the recorded fight, 1 such swing on the train half). A blow on a
companion always lands (nothing was measured there, and nothing here hurts a companion).

**Reach** (REACH for the body of the blows, fitted `reach.tail` beyond): the takes show swings begun
at the character from further off, ever fewer: 0.41 of the rate within 3.5 units at 3.5 to 4 units,
0.16 to 5, 0.05 to 6, 0.02 to 12 (18 to 68 swings a band). At each think a monster's reach is drawn
from that curve; the blow lands if the target is within it. One curve for all: the takes hold 1
blow of a unique alone on the train half, too few for a rank's own. Beyond 6 units the curve is in
part the casts of types that are not called ranged (a shaman's): an upper bound there.

**What a blow is worth**, from the tables (raw points, before the resistances of whoever takes it):
the monster level's `DM(H)` times a roll in the row's `A1MinD(H)..A1MaxD(H)` percent, raised by the
rank (difficultylevels `UniqueDamageBonus`, `ChampionDamageBonus`), by Extra Strong (monumod's
constants) and by a Herald's tier (the Terror Zone's config). The bonuses are multiplied here;
whether the game adds them is not known. An elemental enchantment (Lightning 17, Fire 9, Cold 18)
adds a roll of monumod's "Elemental Min..Max Damage % Bonus" of the blow's physical points, by rank.
**Its spread is fitted** (`melee.spread`, `shots.spread`): the table's roll is within a quarter of its
mean, the drops one monster dealt alone are not (49 of plain monsters: 56 at the median, 118 at the
90th percentile, 320 the largest, against a heaviest blow of 86 to 102 by the tables; 28 shots: 37,
254, 449). So the roll is multiplied by a factor drawn through those quantiles over their mean (0.08
to 5.0 for a strike, 0.06 to 5.1 for a shot): the mean blow stays the table's, one blow in ten is
over 1.8 times it. What makes the large ones (a curse, an aura, two blows between two frames) is
not known; the small ones may be blows partly absorbed.

**Shooting** (fitted, `shots`; the cycle was tests/.../arena/mobs.py's, one landed shot a second): a
monster given a shot (`Pack(shots=...)`) stands and shoots at what it has within SHOT_REACH in sight.
A shot every 1 / rate seconds (0.43 a second pooled over 2,282 shots; 22 types their own, 0.18 to
0.72), the gap drawn evenly from half to one and a half of that. Its mark is the character with the
measured share (0.62: the missiles that flew at where it stood), else the nearest companion. The
missile flies to where its mark stood at the monstats `MissA1` missile's `Vel` in units a second
(written into the fit from the game's tables; a type without one: 20.6, the mean by shots) and ends
on the character if it is within SHOT_CONTACT of that place then: **walking or teleporting out of a
shot is the flight time, not a factor**. A missile that arrives under the character takes life with
the measured chance, 0.023 pooled (three types with 390 to 600 shots have their own): the points the
takes put on a shooter alone and half of its share of the drops it shares, in hits of the mean size
(79 points, 28 hits), per shot that flew at the character (2,657 shots, 0.62 of them). It folds what
a swing's chance folds, and the bodies and walls a missile ends on. It is counted in points because
the counts of drops bound it only between 0.02 and 0.14. A shooter's path record does not say whom
it shoots at (0.17 of 4,514), so the missiles are what the mark is fitted on.

**A death's nova** (read and fitted, `nova`): a champion or unique carrying Cold Enchanted lets a ring
of `coldunique` (194) go when it dies (37 of 37 such deaths on the train half showed it, 0 of 373 of
plain monsters and minions carrying it). It spreads at the missile's `Vel` for its `Range` frames
(13.4 units; the furthest corpse of a nova drop was 11.7 off) and takes the missile's cold points at
the monster's level (729 at level 85: 182 through a cold resistance at the cap, the takes' median
174 of 15) when it passes the character, with the measured chance (0.70 of 37 deaths within 12
units), twice the points one time in five (5 of the train half's 26 nova drops are over 300 points,
which one ring does not reach at any level seen). A Fire Enchanted death's
explosion is in the takes at a median under 10 points and is not modelled; a Lightning Enchanted
death shows nothing.

**Sparks** (read and fitted, `sparks`; SPARKS.md beside the evidence is the measurement: 51 releases
and 408 sparks on the train half). A Lightning Enchanted unique or super unique lets sparks of
`lightunique` (195) go when it is struck (`Pack.struck`); its minions and a plain monster carrying
the enchantment let none go (0 releases of 296 minions seen struck, 51 of 31 of the 67 leaders).
A release comes with the time the monster is being struck, not with each hit: a hit stands for the
frames since the hit before, 10 at most, and a second of that time brings 0.95 releases (51 in
53.8 s; a chance per hit, 0.25 of 205, gives the monsters' counts worse, and hits a few frames apart
do not each bring one), never sooner than 5 frames after the one before (the least of 20 gaps). Why
a release comes the takes do not say, and a Herald's hits are mostly too small to be seen in them.
Eight sparks to a release (51 of 51), one to each 45 degrees and not at whoever struck; each flies
at the missile's `Vel` (12 units a second: 0.48 a frame, the takes' 0.483) along its own direction
or 45 degrees to either side of it, choosing again every 6 frames (the commonest run of 1,774),
which puts it 28 units out after 70 frames (27.2 at the median of 78), and is gone after 77 frames
(the most of 408) or on the first body it meets. The character is in its reach within 2.5 units
(what the evidence calls ended on it), and of the sparks that came that near 0.39 ended on it (11
of 28): the others fly on past it. **A spark that ends on the character takes life with the fitted
chance, and that chance is 0**: none of the 11 was followed by a drop, nor by a point less of life,
so the truth is under 0.24 at 95% (`upper95`) and the size of a spark's blow is not measured at all.
It stays the missile's by the tables (`EMin` and the per-level columns at the monster's level:
2 x level - 1), taken only if the chance is ever set above 0. Like a swing's, the chance is one
number for a miss, a block, a spark of next to no points (the level its missile is cast at may not
be the monster's) and this character's own protection. A spark on a companion always lands (as a
swing: not measured, and nothing here hurts a companion). Before the fit (one take, Tower Cellar 5)
any monster with the enchantment released, with a chance of a third at each frame it was struck in,
and every spark within 2 units of the character took its points.

Not modelled: damage that is no blow (poison, burning: a third of the life the takes lost has no
suspect at all), fleeing, bodies in each other's way, walls (a walk is a straight line and a shot
needs no line here: tests/.../arena/mobs.py adds both), a hurt companion, curses and auras.
