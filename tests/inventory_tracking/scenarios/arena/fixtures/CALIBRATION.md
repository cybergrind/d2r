# Calibration of the arena

Written by `tests/inventory_tracking/scenarios/arena/calibrate.py` (its module text says how a scene is
played and what is compared) from the takes under `inventory_tracking/runs/combat` on 2026-10-12: every fixture
with a `source`, 8 s from its frame, the monsters rolled with seeds 1 to 5. The table is the
first seed; a ratio is arena / take, with its least and most over the seeds in brackets. A scene is
**trusted** when, with every seed, both ratios are within 0.5 to 2 (the life-lost ratio
is not formed when the take lost under 90 points) and the take holds no single drop over
1.5 times the heaviest blow the scene's monsters can deal in the arena. `trusted.json` holds the
verdicts; `trust.py` reads them.

**Trusted: 1 of 72 scenes.** Of the others:

- neither lost 90 points: nothing to measure: 33
- the arena took over 2 times the take: 13
- the take lost under 90 points and the arena took 90 or more: 10
- the arena took under 0.5 of the take: 7
- the life lost agrees, the kills do not: 4
- believed with the first seed, not with every one: 2
- both ratios agree with every seed, but the take holds a blow the arena cannot deal: 2

## What this says

*Read by hand from the tables below as they stood on 2026-10-12; a later run rewrites the tables, not
this text.*

**The arena cannot be believed yet: 1 scene of 72.** Not because the comparison is too strict: of the
29 scenes where the take holds enough lost life to measure against, the arena is within a factor of
two on the life lost in 9 with the first seed, and only one of those also agrees on the kills, holds
with every seed and has no blow in the take that the arena cannot deal.

1. **Too harsh, by about three times in sum, and not evenly.** Over all windows the arena's blows sum
   to 73,490 points where the takes' drops sum to 20,618 (3.6 times); by the table's measure, the
   falls of the life, all the arena's over all the takes' is 3.17. The median
   scene ratio is 1.86, the quartiles 0.75 and 4.01, the range 0.00 to 25.2. In 10 further scenes the
   take lost under 90 points and the arena took 90 to 5,795. The arena's character died in 17 windows;
   the take's in 2.
2. **It lands far more blows, each smaller.** 688 arena blows (median 85 points) against 128 drops in
   the takes (median 136): five times as often. The rate is what is off, more than the size of a blow.
3. **The ranged model is the largest part of it.** 392 of the 688 blows are shots and they carry 50,539
   of the 73,490 points: the shots alone are 2.5 times all the life the takes lost to everything.
   A ranged monster of the arena lands one shot a second on anything within 30 units in a clear line
   (mobs.py SHOT_FRAMES, SHOT_LANDS, RANGED_REACH: all three are that file's assumptions; no missile
   flies, so none misses and none is walked out of). By type: Hell Temptress (472) 130 shots,
   DarkArcher (162) 122, ReturnedArcher (578) 64, BlackSoul (640) 50 shots of a median 223 points (its
   threat-table `hard` factor of 5.0 is on every shot). The scenes led by these types pool at 2.6 to
   28 times the take.
4. **Melee is too frequent where a pack is in contact, and absent where the take had it.** IceSpawn
   (458) scenes pool at 4.8 (134 strikes of a median 82; the takes there show single drops of up to
   547). BloodClan (55) scenes at 4.1. No strike of the arena is ever missed, blocked or dodged
   (sim/monsters.py: "raw points, before the defence, block"), and the main weapon set's physical
   resistance is unknown and taken as none (cut.py UNKNOWN). Against that, Returned (1) scenes pool at
   0.13 and 7 scenes are under half: in the one traced (20261011T223134Z-38-794) the take has Griswold
   and a Returned striking from 2.2 and 3.0 units with the character as their target, while the arena's
   Griswold stops 10 units off and strikes a companion. *Hypothesis:* "the target is the nearest of
   the character and its companions" (sim/monsters.py, fitted to Tower Cellar 5) sends the arena's
   monsters to the mercenary and the pets more than the game does.
5. **The takes' damage comes in single large drops the arena has no blow for.** In 8 scenes a drop of
   the take is over 1.5 times the heaviest blow any monster of the scene can deal in the arena (322 to
   1,051 points against 93 to 370). Seen next to them in the takes: missiles the model does not have
   (the nova of a Cold Enchanted monster's death, `coldunique` 194, 359 points with nobody striking;
   others the tables do not name), and several monsters landing between two samples. So the arena
   bleeds the character steadily where the game hits it rarely and hard: a rule that watches for a
   burst is judged in the wrong world even where the sums agree.
6. **The death (20261011T195037Z-25-493) is the plainest case of 5.** The take: life 995 rising to 1,051
   on a potion, then one drop of 1,051 at 3.0 s with the tier 2 Herald in an attack mode 8.9 units
   off. The arena: four minion strikes of about 100 doubled by the Herald's aura, life 995 to 218, no
   death; its Herald can deal 370 at most and reaches 3.2 units (sim/monsters.py REACH), so it does
   not strike at all. The ratio is 0.75 by accident of the sums, and the scene is marked not trusted
   for it.
7. **The kills agree better than the life.** Median 0.81, pooled 0.80 over the 58 scenes where
   something died: the arena kills a fifth fewer, which is the direction the missing companions'
   damage and Death Mark give (game.py's list). Four scenes fail on the kills alone.
8. **One factor does not mend it.** 0.47 on every blow centres the median (0.99 on the half it was
   found on, 1.07 on the other) and the range stays 0.05 to 12.3; the bare rule then trusts 8 of 25
   instead of 5. The misses are by type and by mechanism, not a scale.

**What limits the measurement itself.** 33 scenes have under 90 points lost in the take and in the
arena alike (most `long` and `stuck` scenes: nobody was hurt in those 8 s). They are not misses; the
rule leaves them untrusted because nothing was measured, and `trusted.json` cannot say "agrees,
unmeasured". 19 windows end early at a hostile the scene does not hold (the character hopped on, or
something came into the client's memory beside it); 38 scenes have the hand assumed; the scenes of
one moment cut three times (20261012T065226Z-130-4606, -4609, -4612) count three times. Hell Bovine
(391): three scenes, no life lost in either world, so the 212 points a second seen in contact is
neither confirmed nor refuted here. A Herald's life (cut.py `full_points`) only shows in the kills.

**What to change first in the model (not done here):** (a) the ranged attacker: a missile that flies
and can miss, and a rate from the takes instead of one landed shot a second; (b) a chance to hit for
melee (monstats `A1TH`, the character's defence and block) and the main set's physical resistance;
(c) who a monster goes for; (d) the big single blows: a Herald's or unique's reach and top blow, death
novas. A refit by type needs, for each type, drops that one monster dealt alone: the takes of these
fixtures hold 9 such drops in the compared windows (the table of blows), so it needs
`combat/hurts.py` run over all takes, or `terror/exposure.py`'s per-type rates, not these 72 windows.

## The scenes

| scene | kind | area | hostiles | seconds | taken take | taken arena | ratio | kills take | kills arena | ratio | trusted | notes |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- | --- | --- |
| 20261010T214359Z-25-1195-potions | potions | Tower Cellar Level 5 (25) | 18, most DarkStalker (45) | 8.0 | 1490 | 2975 | 2.00 (2.00 to 2.43) | 17 | 6 | 0.35 | no | 2 belt keys replayed on the assumed belt; the character went 27 units from where the scene has it; assumed: hand; the character died in the arena at 3.4 s |
| 20261010T214359Z-25-1258-burst | burst | Tower Cellar Level 5 (25) | 18, most DarkStalker (45) | 8.0 | 1490 | 2284 | 1.53 (1.53 to 2.01) | 18 | 10 | 0.56 | no (3 of 5 seeds) | 3 belt keys replayed on the assumed belt; the character went 12 units from where the scene has it; assumed: hand; the character died in the arena at 2.7 s |
| 20261011T001816Z-131-1660-potions | potions | Throne of Destruction (131) | 1, most Baal Throne (543) | 0.4 | 0 | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 0.4 s; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T085143Z-124-102-burst | burst | Halls of Vaught (124) | 47, most IceSpawn (458) | 8.0 | 1001 | 8219 | 8.21 (7.79 to 8.21) | 26 | 28 | 1.08 | no | 2 belt keys replayed on the assumed belt; assumed: hand; the character died in the arena at 3.6 s, 4 times in all; a blow the arena cannot deal: a drop of 547 points in the take, at most 113 a blow in the arena |
| 20261011T092540Z-124-101-potions | potions | Halls of Vaught (124) | 47, most IceSpawn (458) | 8.0 | 1053 | 5521 | 5.24 (4.80 to 5.49) | 31 | 29 | 0.94 | no | 3 belt keys replayed on the assumed belt; the character went 25 units from where the scene has it; assumed: hand; the character died in the arena at 2.8 s, 2 times in all; a blow the arena cannot deal: a drop of 489 points in the take, at most 103 a blow in the arena |
| 20261011T102814Z-124-194-burst15 | burst15 | Halls of Vaught (124) | 26, most IceSpawn (458) | 8.0 | 417 | 44 | 0.11 (0.00 to 0.32) | 21 | 20 | 0.95 | no | 2 belt keys replayed on the assumed belt; the character went 22 units from where the scene has it; assumed: hand; a blow the arena cannot deal: a drop of 322 points in the take, at most 93 a blow in the arena |
| 20261011T103818Z-124-49-burst15 | burst15 | Halls of Vaught (124) | 14, most Hell Temptress (472) | 1.6 | 0 | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 1.6 s; the character went 63 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T104325Z-124-216-burst15 | burst15 | Halls of Vaught (124) | 40, most IceSpawn (458) | 8.0 | 449 | 2540 | 5.66 (5.46 to 6.70) | 30 | 28 | 0.93 | no | the character went 24 units from where the scene has it; assumed: hand; the character died in the arena at 4.3 s; a blow the arena cannot deal: a drop of 449 points in the take, at most 93 a blow in the arena |
| 20261011T104524Z-124-72-burst15 | burst15 | Halls of Vaught (124) | 38, most IceSpawn (458) | 1.6 | 0 | 329 | - | 1 | 0 | 0.00 | no | a hostile the scene lacks is within 12 of the character at 1.6 s; the character went 30 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T115400Z-124-122-burst15 | burst15 | Halls of Vaught (124) | 27, most IceSpawn (458) | 8.0 | 672 | 735 | 1.09 (0.98 to 1.16) | 27 | 22 | 0.81 | no (a blow the arena cannot deal) | the character went 16 units from where the scene has it; assumed: hand; a blow the arena cannot deal: a drop of 352 points in the take, at most 195 a blow in the arena |
| 20261011T122736Z-124-3499-potions | potions | Halls of Vaught (124) | 23, most Slayerexp (682) | 8.0 | 431 | 2223 | 5.16 (5.16 to 5.98) | 20 | 13 | 0.65 | no | 3 belt keys replayed on the assumed belt; the character went 34 units from where the scene has it; assumed: hand; the character died in the arena at 5.4 s |
| 20261011T143225Z-25-155-burst15 | burst15 | Tower Cellar Level 5 (25) | 25, most Ghost (38) | 8.0 | 374 | 497 | 1.33 (1.33 to 2.15) | 9 | 8 | 0.89 | no (2 of 5 seeds) | assumed: hand |
| 20261011T143607Z-25-987-burst15 | burst15 | Tower Cellar Level 5 (25) | 26, most Devilkin (21) | 8.0 | 420 | 621 | 1.48 (1.25 to 1.88) | 16 | 7 | 0.44 | no (4 of 5 seeds) | the character went 35 units from where the scene has it; assumed: hand |
| 20261011T161644Z-25-322-burst15 | burst15 | Tower Cellar Level 5 (25) | 9, most Ghost (38) | 6.3 | 359 | 0 | 0.00 (0.00 to 0.00) | 8 | 8 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 6.4 s; the character went 47 units from where the scene has it; assumed: hand; a blow the arena cannot deal: a drop of 359 points in the take, at most 204 a blow in the arena |
| 20261011T165853Z-25-18-burst15 | burst15 | Tower Cellar Level 5 (25) | 6, most Ghost (38) | 1.5 | 0 | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 1.5 s; the character went 90 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T171432Z-25-18-long | long | Tower Cellar Level 5 (25) | 9, most Devilkin (21) | 0.5 | 0 | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 0.5 s; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T182610Z-6-97-long | long | Black Marsh (6) | 7, most BloodHawk (16) | 1.2 | 0 | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 1.3 s; the character went 30 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T182707Z-23-31-long | long | Tower Cellar Level 3 (23) | 16, most Devilkin (21) | 8.0 | 0 | 0 | - | 15 | 14 | 0.93 | no | the character went 41 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T183714Z-25-134-long | long | Tower Cellar Level 5 (25) | 24, most DarkArcher (162) | 3.7 | 0 | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 3.7 s; the character went 35 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T183714Z-25-164-burst15 | burst15 | Tower Cellar Level 5 (25) | 36, most Devilkin (21) | 8.0 | 434 | 1136 | 2.62 (2.62 to 2.62) | 11 | 7 | 0.64 | no | the character went 34 units from where the scene has it; assumed: hand |
| 20261011T183714Z-25-375-potions | potions | Tower Cellar Level 5 (25) | 15, most Devilkin (21) | 7.3 | 372 | 81 | 0.22 (0.00 to 0.22) | 9 | 7 | 0.78 | no | a hostile the scene lacks is within 12 of the character at 7.3 s; 5 belt keys replayed on the assumed belt; the character went 24 units from where the scene has it; assumed: hand; a blow the arena cannot deal: a drop of 372 points in the take, at most 179 a blow in the arena |
| 20261011T191333Z-25-663-burst15 | burst15 | Tower Cellar Level 5 (25) | 11, most DarkArcher (162) | 8.0 | 864 | 3074 | 3.56 (3.29 to 3.62) | 9 | 7 | 0.78 | no | 2 belt keys replayed on the assumed belt; the character went 12 units from where the scene has it; assumed: hand; the character died in the arena at 2.4 s |
| 20261011T191333Z-25-690-burst | burst | Tower Cellar Level 5 (25) | 11, most DarkArcher (162) | 8.0 | 864 | 2408 | 2.79 (2.75 to 3.06) | 9 | 6 | 0.67 | no | 2 belt keys replayed on the assumed belt; assumed: hand; the character died in the arena at 2.4 s |
| 20261011T192015Z-25-42-burst15 | burst15 | Tower Cellar Level 5 (25) | 27, most Devilkin (21) | 1.2 | 0 | 0 | - | 1 | 0 | 0.00 | no | a hostile the scene lacks is within 12 of the character at 1.2 s; the character went 30 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T192530Z-21-0-long | long | Tower Cellar Level 1 (21) | 7, most Devilkin (21) | 0.6 | 0 | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 0.6 s; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T193254Z-6-1820-long | long | Black Marsh (6) | 9, most Returned (1) | 4.5 | 0 | 0 | - | 6 | 4 | 0.67 | no | a hostile the scene lacks is within 12 of the character at 4.5 s; the character went 41 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T193625Z-22-358-burst15 | burst15 | Tower Cellar Level 2 (22) | 8, most DarkArcher (162) | 8.0 | 593 | 2681 | 4.52 (4.26 to 4.78) | 8 | 7 | 0.88 | no | 2 belt keys replayed on the assumed belt; the character went 48 units from where the scene has it; assumed: hand; the character died in the arena at 2.8 s |
| 20261011T194054Z-25-0-long | long | Tower Cellar Level 5 (25) | 3, most BloodClan (55) | 2.5 | 0 | 0 | - | 3 | 2 | 0.67 | no | a hostile the scene lacks is within 12 of the character at 2.6 s; the character went 21 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T194327Z-6-3063-long | long | Black Marsh (6) | 66, most Carver (20) | 8.0 | 0 | 0 | - | 33 | 34 | 1.03 | no | the character went 24 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T194710Z-22-641-burst15 | burst15 | Tower Cellar Level 2 (22) | 27, most Devilkin (21) | 8.0 | 0 | 90 | - | 15 | 8 | 0.53 | no | the character went 26 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T195037Z-25-2-long | long | Tower Cellar Level 5 (25) | 16, most Devilkin (21) | 8.0 | 0 | 189 | - | 4 | 1 | 0.25 | no | the character went 19 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T195037Z-25-373-potions | potions | Tower Cellar Level 5 (25) | 17, most BloodClan (55) | 7.9 | 1479 | 5934 | 4.01 (2.85 to 4.45) | 6 | 8 | 1.33 | no | the character died in the take at 7.9 s; 3 belt keys replayed on the assumed belt; assumed: hand; the character died in the arena at 2.3 s, 3 times in all |
| 20261011T195037Z-25-493-death | death | Tower Cellar Level 5 (25) | 11, most DarkArcher (162) | 3.0 | 1108 | 831 | 0.75 (0.74 to 1.41) | 0 | 0 | 1.00 | no (a blow the arena cannot deal) | the character died in the take at 3.0 s; 1 belt keys replayed on the assumed belt; assumed: hand; a blow the arena cannot deal: a drop of 1051 points in the take, at most 370 a blow in the arena |
| 20261011T211725Z-22-1093-burst15 | burst15 | Tower Cellar Level 2 (22) | 4, most Ghost (38) | 8.0 | 339 | 571 | 1.68 (0.66 to 1.68) | 4 | 3 | 0.75 | yes | the character went 25 units from where the scene has it; assumed: hand |
| 20261011T211818Z-23-535-long | long | Tower Cellar Level 3 (23) | 12, most Devilkin (21) | 8.0 | 0 | 0 | - | 0 | 0 | 1.00 | no | assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T211958Z-25-1-long | long | Tower Cellar Level 5 (25) | 19, most BloodClan (55) | 7.2 | 0 | 194 | - | 5 | 0 | 0.00 | no | a hostile the scene lacks is within 12 of the character at 7.3 s; the character went 59 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T212453Z-23-172-burst15 | burst15 | Tower Cellar Level 3 (23) | 8, most BloodClan (55) | 2.7 | 0 | 0 | - | 4 | 3 | 0.75 | no | a hostile the scene lacks is within 12 of the character at 2.7 s; the character went 48 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T220301Z-6-69-long | long | Black Marsh (6) | 31, most Carver (20) | 8.0 | 0 | 0 | - | 13 | 11 | 0.85 | no | the character went 24 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T222330Z-24-41-long | long | Tower Cellar Level 4 (24) | 8, most Devilkin (21) | 8.0 | 180 | 0 | 0.00 (0.00 to 0.00) | 6 | 6 | 1.00 | no | the character went 30 units from where the scene has it |
| 20261011T222330Z-24-80-stuck | stuck | Tower Cellar Level 4 (24) | 12, most Devilkin (21) | 8.0 | 180 | 0 | 0.00 (0.00 to 0.59) | 8 | 6 | 0.75 | no (1 of 5 seeds) | the character went 25 units from where the scene has it |
| 20261011T222518Z-6-63-stuck | stuck | Black Marsh (6) | 4, most Carver (20) | 3.0 | 34 | 0 | - | 0 | 0 | 1.00 | no | the take ends or leaves the level at 3.0 s; the character went 49 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T222544Z-23-414-stuck | stuck | Tower Cellar Level 3 (23) | 11, most DarkArcher (162) | 8.0 | 3 | 548 | - | 3 | 3 | 1.00 | no | the character went 32 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T222624Z-25-340-stuck | stuck | Tower Cellar Level 5 (25) | 15, most Ghost (38) | 8.0 | 79 | 70 | - | 7 | 6 | 0.86 | no | the character went 22 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T222624Z-25-57-long | long | Tower Cellar Level 5 (25) | 20, most Devilkin (21) | 8.0 | 48 | 0 | - | 0 | 0 | 1.00 | no | the character went 22 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T222923Z-23-115-stuck | stuck | Tower Cellar Level 3 (23) | 7, most Ghost (38) | 6.9 | 0 | 0 | - | 7 | 7 | 1.00 | no | the take ends or leaves the level at 6.9 s; the character went 35 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T222934Z-24-382-stuck | stuck | Tower Cellar Level 4 (24) | 12, most Devilkin (21) | 8.0 | 168 | 411 | 2.45 (0.00 to 2.45) | 12 | 11 | 0.92 | no (3 of 5 seeds) | the character went 35 units from where the scene has it |
| 20261011T223004Z-25-192-stuck | stuck | Tower Cellar Level 5 (25) | 14, most Devilkin (21) | 8.0 | 0 | 0 | - | 0 | 0 | 1.00 | no | the character went 18 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T223134Z-38-794-burst15 | burst15 | Tristram (38) | 15, most Returned (1) | 8.0 | 454 | 0 | 0.00 (0.00 to 0.09) | 9 | 6 | 0.67 | no | the character went 30 units from where the scene has it |
| 20261011T223134Z-38-817-stuck | stuck | Tristram (38) | 20, most Returned (1) | 8.0 | 454 | 117 | 0.26 (0.17 to 0.26) | 9 | 4 | 0.44 | no | the character went 31 units from where the scene has it |
| 20261011T225311Z-38-622-stuck | stuck | Tristram (38) | 3, most SkeletonArcher (170) | 5.8 | 0 | 35 | - | 3 | 3 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 5.9 s; the character went 47 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T231204Z-38-164-stuck | stuck | Tristram (38) | 9, most Carver (20) | 8.0 | 0 | 32 | - | 5 | 5 | 1.00 | no | the take holds under 90 points of life lost: no ratio |
| 20261011T231408Z-39-134-stuck | stuck | Moo Moo Farm (39) | 66, most Hell Bovine (391) | 8.0 | 0 | 0 | - | 10 | 11 | 1.10 | no | the take holds under 90 points of life lost: no ratio |
| 20261011T231408Z-39-3182-burst15 | burst15 | Moo Moo Farm (39) | 13, most Hell Bovine (391) | 8.0 | 0 | 0 | - | 9 | 5 | 0.56 | no | the character went 43 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T231408Z-39-377-long | long | Moo Moo Farm (39) | 29, most Hell Bovine (391) | 6.3 | 0 | 0 | - | 21 | 10 | 0.48 | no | a hostile the scene lacks is within 12 of the character at 6.3 s; the character went 33 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T233544Z-3-2158-stuck | stuck | Cold Plains (3) | 7, most Fallen (19) | 6.4 | 0 | 0 | - | 6 | 5 | 0.83 | no | a hostile the scene lacks is within 12 of the character at 6.4 s; the character went 44 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T233544Z-3-3280-long | long | Cold Plains (3) | 31, most Fallen (19) | 8.0 | 0 | 0 | - | 18 | 20 | 1.11 | no | the character went 55 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T234014Z-9-197-stuck | stuck | Cave Level 1 (9) | 14, most HungryDead (6) | 8.0 | 0 | 0 | - | 7 | 6 | 0.86 | no | the take holds under 90 points of life lost: no ratio |
| 20261011T234425Z-13-954-stuck | stuck | Cave Level 2 (13) | 1, most HungryDead (6) | 8.0 | 0 | 0 | - | 0 | 0 | 1.00 | no | the character went 57 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T061027Z-115-1803-stuck | stuck | Glacial Trail (115) | 11, most ReanimatedHorde (437) | 8.0 | 0 | 0 | - | 11 | 7 | 0.64 | no | the character went 63 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T061557Z-115-298-stuck | stuck | Glacial Trail (115) | 32, most BoneWarrior (648) | 8.0 | 0 | 626 | - | 9 | 15 | 1.67 | no | the character went 29 units from where the scene has it; assumed: level, mods, tier; the take holds under 90 points of life lost: no ratio |
| 20261012T063130Z-116-561-stuck | stuck | Drifter Cavern (116) | 2, most DarkArcher (614) | 8.0 | 0 | 223 | - | 2 | 2 | 1.00 | no | the character went 71 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T064056Z-6-242-stuck | stuck | Black Marsh (6) | 24, most Carver (20) | 8.0 | 0 | 0 | - | 12 | 13 | 1.08 | no | the character went 42 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T064056Z-6-326-long | long | Black Marsh (6) | 23, most Carver (20) | 8.0 | 0 | 0 | - | 12 | 16 | 1.33 | no | the character went 42 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T064210Z-129-354-burst15 | burst15 | The Worldstone Keep Level 2 (129) | 7, most BlackSoul (640) | 8.0 | 329 | 3517 | 10.69 (9.93 to 10.69) | 7 | 7 | 1.00 | no | the character went 46 units from where the scene has it; the character died in the arena at 1.3 s, 2 times in all |
| 20261012T064210Z-129-698-long | long | The Worldstone Keep Level 2 (129) | 20, most BlackSoul (640) | 8.0 | 0 | 5795 | - | 12 | 8 | 0.67 | no | the character went 50 units from where the scene has it; assumed: full; the character died in the arena at 3.5 s, 3 times in all; the take holds under 90 points of life lost: no ratio |
| 20261012T064317Z-130-0-long | long | The Worldstone Keep Level 3 (130) | 1, most Baal Taunt (545) | 4.2 | 0 | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 4.2 s; the character went 39 units from where the scene has it; assumed: full, level, mods, tier; the take holds under 90 points of life lost: no ratio |
| 20261012T064317Z-130-662-stuck | stuck | The Worldstone Keep Level 3 (130) | 11, most Hell Temptress (472) | 8.0 | 0 | 173 | - | 4 | 4 | 1.00 | no | assumed: full, level, mods, tier; the take holds under 90 points of life lost: no ratio |
| 20261012T065226Z-130-0-long | long | The Worldstone Keep Level 3 (130) | 7, most Hell Temptress (472) | 8.0 | 86 | 2084 | - | 4 | 3 | 0.75 | no | the character went 46 units from where the scene has it; assumed: full, level; the character died in the arena at 5.3 s; the take holds under 90 points of life lost: no ratio |
| 20261012T065226Z-130-101-stuck | stuck | The Worldstone Keep Level 3 (130) | 7, most Hell Temptress (472) | 8.0 | 99 | 2497 | 25.22 (16.80 to 28.53) | 5 | 4 | 0.80 | no | the character went 20 units from where the scene has it; assumed: full; the character died in the arena at 3.7 s |
| 20261012T065226Z-130-4606-burst15 | burst15 | The Worldstone Keep Level 3 (130) | 16, most Hell Temptress (472) | 8.0 | 1937 | 3611 | 1.86 (1.76 to 2.15) | 12 | 4 | 0.33 | no | 3 belt keys replayed on the assumed belt; the character went 20 units from where the scene has it; assumed: full; the character died in the arena at 2.1 s |
| 20261012T065226Z-130-4609-potions | potions | The Worldstone Keep Level 3 (130) | 16, most Hell Temptress (472) | 8.0 | 1937 | 3171 | 1.64 (1.64 to 1.98) | 12 | 4 | 0.33 | no | 3 belt keys replayed on the assumed belt; the character went 20 units from where the scene has it; assumed: full; the character died in the arena at 2.4 s |
| 20261012T065226Z-130-4612-burst | burst | The Worldstone Keep Level 3 (130) | 16, most Hell Temptress (472) | 8.0 | 1937 | 4139 | 2.14 (1.80 to 2.14) | 12 | 4 | 0.33 | no | 3 belt keys replayed on the assumed belt; the character went 20 units from where the scene has it; assumed: full; the character died in the arena at 1.8 s |

## The ratios

"Pooled" is all the arena's points over all the take's in the group, the scenes without a ratio of
their own among them. The kills columns are of the scenes where a hostile died in the take.

| all | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 72 | 1 | 29 | 0.00 | 0.75 | 1.86 | 4.01 | 25.22 | 3.17 | 10 | 58 | 0.81 | 0.80 |

| kind | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| burst15 | 20 | 1 | 13 | 0.00 | 1.09 | 1.68 | 3.56 | 10.69 | 2.55 | 2 | 18 | 0.75 | 0.75 |
| long | 20 | 0 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 26.31 | 4 | 13 | 0.75 | 0.85 |
| stuck | 20 | 0 | 4 | 0.00 | 0.19 | 1.35 | 8.14 | 25.22 | 4.65 | 4 | 17 | 1.00 | 0.93 |
| potions | 7 | 0 | 6 | 0.22 | 1.73 | 3.00 | 4.87 | 5.24 | 2.94 | 0 | 6 | 0.71 | 0.71 |
| burst | 4 | 0 | 4 | 1.53 | 1.99 | 2.46 | 4.14 | 8.21 | 3.22 | 0 | 4 | 0.61 | 0.74 |
| death | 1 | 0 | 1 | 0.75 | 0.75 | 0.75 | 0.75 | 0.75 | 0.75 | 0 | 0 | - | - |

By the type most of the scene's hostiles are of:

| most hostiles | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Devilkin (21) | 15 | 0 | 6 | 0.00 | 0.05 | 0.85 | 2.21 | 2.62 | 1.40 | 2 | 10 | 0.69 | 0.69 |
| Hell Temptress (472) | 7 | 0 | 4 | 1.64 | 1.81 | 2.00 | 7.91 | 25.22 | 2.61 | 2 | 6 | 0.54 | 0.47 |
| Carver (20) | 6 | 0 | 0 | - | - | - | - | - | 0.93 | 0 | 5 | 1.03 | 1.05 |
| DarkArcher (162) | 6 | 0 | 4 | 0.75 | 2.28 | 3.17 | 3.80 | 4.52 | 2.78 | 1 | 4 | 0.83 | 0.79 |
| Ghost (38) | 6 | 1 | 3 | 0.00 | 0.66 | 1.33 | 1.51 | 1.68 | 0.99 | 0 | 5 | 0.89 | 0.91 |
| IceSpawn (458) | 6 | 0 | 5 | 0.11 | 1.09 | 5.24 | 5.66 | 8.21 | 4.84 | 1 | 6 | 0.93 | 0.93 |
| BloodClan (55) | 4 | 0 | 1 | 4.01 | 4.01 | 4.01 | 4.01 | 4.01 | 4.14 | 1 | 4 | 0.71 | 0.72 |
| Hell Bovine (391) | 3 | 0 | 0 | - | - | - | - | - | - | 0 | 3 | 0.56 | 0.65 |
| Returned (1) | 3 | 0 | 2 | 0.00 | 0.06 | 0.13 | 0.19 | 0.26 | 0.13 | 0 | 3 | 0.67 | 0.58 |
| BlackSoul (640) | 2 | 0 | 1 | 10.69 | 10.69 | 10.69 | 10.69 | 10.69 | 28.31 | 1 | 2 | 0.83 | 0.79 |
| DarkStalker (45) | 2 | 0 | 2 | 1.53 | 1.65 | 1.76 | 1.88 | 2.00 | 1.76 | 0 | 2 | 0.45 | 0.46 |
| Fallen (19) | 2 | 0 | 0 | - | - | - | - | - | - | 0 | 2 | 0.97 | 1.04 |
| HungryDead (6) | 2 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 0.86 | 0.86 |
| Baal Taunt (545) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| Baal Throne (543) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| BloodHawk (16) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| BoneWarrior (648) | 1 | 0 | 0 | - | - | - | - | - | - | 1 | 1 | 1.67 | 1.67 |
| DarkArcher (614) | 1 | 0 | 0 | - | - | - | - | - | - | 1 | 1 | 1.00 | 1.00 |
| ReanimatedHorde (437) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 0.64 | 0.64 |
| SkeletonArcher (170) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 1.00 | 1.00 |
| Slayerexp (682) | 1 | 0 | 1 | 5.16 | 5.16 | 5.16 | 5.16 | 5.16 | 5.16 | 0 | 1 | 0.65 | 0.65 |

The types with 3 scenes or more, by what the arena makes of them:

| most hostiles | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| IceSpawn (458) | 6 | 0 | 5 | 0.11 | 1.09 | 5.24 | 5.66 | 8.21 | 4.84 | 1 | 6 | 0.93 | 0.93 |
| BloodClan (55) | 4 | 0 | 1 | 4.01 | 4.01 | 4.01 | 4.01 | 4.01 | 4.14 | 1 | 4 | 0.71 | 0.72 |
| DarkArcher (162) | 6 | 0 | 4 | 0.75 | 2.28 | 3.17 | 3.80 | 4.52 | 2.78 | 1 | 4 | 0.83 | 0.79 |
| Hell Temptress (472) | 7 | 0 | 4 | 1.64 | 1.81 | 2.00 | 7.91 | 25.22 | 2.61 | 2 | 6 | 0.54 | 0.47 |
| Devilkin (21) | 15 | 0 | 6 | 0.00 | 0.05 | 0.85 | 2.21 | 2.62 | 1.40 | 2 | 10 | 0.69 | 0.69 |
| Ghost (38) | 6 | 1 | 3 | 0.00 | 0.66 | 1.33 | 1.51 | 1.68 | 0.99 | 0 | 5 | 0.89 | 0.91 |
| Carver (20) | 6 | 0 | 0 | - | - | - | - | - | 0.93 | 0 | 5 | 1.03 | 1.05 |
| Returned (1) | 3 | 0 | 2 | 0.00 | 0.06 | 0.13 | 0.19 | 0.26 | 0.13 | 0 | 3 | 0.67 | 0.58 |
| Hell Bovine (391) | 3 | 0 | 0 | - | - | - | - | - | - | 0 | 3 | 0.56 | 0.65 |

## The blows, by who struck

Over the compared windows, first seed. An arena blow is one strike, shot or spark after the
resistances of the set in hand. A drop of the take is the life gone between two samples (several
blows landing together are one drop); it is put on a type only when one monster alone was striking
(`combat/hurts.py` `sole`), so the take's rows by type are a part of its drops: the last row has all.

| striker | arena: kind | blows | median | points | take: drops put on it | median | points |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Hell Temptress (472) | shot | 130 | 148 | 18692 | 0 | - | 0 |
| DarkArcher (162) | shot | 122 | 97 | 13538 | 3 | 98 | 203 |
| BlackSoul (640) | shot | 50 | 223 | 12489 | 0 | - | 0 |
| IceSpawn (458) | melee | 134 | 82 | 10901 | 1 | 13 | 13 |
| BloodClan (55) | melee | 38 | 96 | 4613 | 2 | 144 | 289 |
| ReturnedArcher (578) | shot | 64 | 66 | 4211 | 0 | - | 0 |
| BloodClan (55) | spark | 47 | 37 | 1751 | 0 | - | 0 |
| DarkStalker (45) | melee | 15 | 79 | 1538 | 0 | - | 0 |
| Slayerexp (682) | melee | 9 | 84 | 762 | 1 | 23 | 23 |
| Hell Temptress (472) | spark | 12 | 42 | 725 | 0 | - | 0 |
| TombViper (597) | shot | 12 | 56 | 670 | 0 | - | 0 |
| Ghost (38) | spark | 9 | 37 | 635 | 0 | - | 0 |
| PitViper (595) | shot | 6 | 94 | 564 | 0 | - | 0 |
| Arach (685) | melee | 5 | 92 | 453 | 0 | - | 0 |
| Ghost (38) | melee | 4 | 96 | 418 | 0 | - | 0 |
| Ghost (631) | melee | 4 | 85 | 331 | 0 | - | 0 |
| Devilkin (21) | melee | 3 | 92 | 271 | 0 | - | 0 |
| DarkArcher (614) | shot | 4 | 56 | 223 | 0 | - | 0 |
| DarkArcher (162) | spark | 5 | 41 | 206 | 0 | - | 0 |
| BlackSoul (640) | spark | 5 | 41 | 206 | 0 | - | 0 |
| SkeletonArcher (170) | shot | 4 | 39 | 152 | 0 | - | 0 |
| BoneWarrior (648) | melee | 1 | 62 | 62 | 0 | - | 0 |
| Nihlathak (526) | spark | 1 | 46 | 46 | 0 | - | 0 |
| Carver (20) | melee | 1 | 32 | 32 | 0 | - | 0 |
| Nihlathak (526) | melee | 2 | 0 | 0 | 0 | - | 0 |
| Baal Taunt (545) | melee | 1 | 0 | 0 | 0 | - | 0 |
| Returned (1) | - | 0 | - | 0 | 2 | 157 | 314 |
| every melee | melee | 217 | 83 | 19383 | - | - | - |
| every shot | shot | 392 | 96 | 50539 | - | - | - |
| every spark | spark | 79 | 37 | 3569 | - | - | - |
| all, 478 s of 72 scenes | | 688 | 85 | 73490 | 128 | 136 | 20618 |

## The window

Each scene played for 15 s without leaving at the first stranger (a hostile the scene does not
hold within 12 units of the recorded character). "Still recorded": the take is in the
level and the character alive.

| seconds | scenes still recorded | of them no stranger yet | of those, the take lost enough | median units a monster is from its recording | hostiles within 12: take | arena |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 72 | 64 | 4 | 4.2 | 2.1 | 2.6 |
| 4 | 70 | 59 | 26 | 5.8 | 2.2 | 3.0 |
| 6 | 70 | 56 | 28 | 5.9 | 1.6 | 2.2 |
| 8 | 68 | 49 | 25 | 6.4 | 0.7 | 1.7 |
| 10 | 66 | 42 | 25 | 15.9 | 0.5 | 1.8 |
| 12 | 64 | 33 | 20 | 12.0 | 0.7 | 2.0 |
| 15 | 57 | 25 | 14 | 16.8 | 0.6 | 1.8 |

## The death: 20261011T195037Z-25-493-death

| seconds | life in the take | life in the arena (seed 1) | hostiles within 12 in the arena |
| ---: | ---: | ---: | ---: |
| 0.00 | 995 | 995 | 3 |
| 0.48 | 1018 | 995 | 3 |
| 1.00 | 1029 | 995 | 3 |
| 1.52 | 972 | 1008 | 3 |
| 2.00 | 1006 | 771 | 3 |
| 2.48 | 1029 | 597 | 3 |
| 3.00 | 1051 | 218 | 3 |
| 3.04 | 0 | 219 | 3 |

- drops in the take: 57 at 1.12 s, 1051 at 3.00 s
- blows in the arena, before an aura: 126 at 2.00 s (BloodClan (55), melee), 95 at 2.28 s (BloodClan (55), melee), 102 at 2.64 s (BloodClan (55), melee), 96 at 2.92 s (BloodClan (55), melee)
- belt keys: column 4 at 1.16 s

## One factor on every blow

Of the 29 scenes with a ratio, the 4 where the arena took nothing are left out (no factor moves them); the rest are split in two by every other name. The median ratio of
the 13 scenes fitted on is 2.14: a factor of **0.47** on every blow would centre it. Played again with it (`play`, `damage_scale`; first seed; "trusted" here is the bare rule of
the two ratios):

| half | scenes | median before | median with the factor | trusted before | trusted with the factor | least | most |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fitted on | 13 | 2.14 | 0.99 | 3 | 5 | 0.05 | 5.10 |
| checked on | 12 | 2.24 | 1.07 | 2 | 3 | 0.09 | 12.29 |
