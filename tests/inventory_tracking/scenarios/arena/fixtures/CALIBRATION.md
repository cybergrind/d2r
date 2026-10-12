# Calibration of the arena

Written by `tests/inventory_tracking/scenarios/arena/calibrate.py` (its module text says how a scene is
played and what is compared) from the takes under `inventory_tracking/runs/combat` on 2026-10-12: every fixture
with a `source`, 8 s from its frame, the monsters rolled with seeds 1 to 5. The table is the
first seed; a ratio is arena / take, with its least and most over the seeds in brackets. A scene is
**trusted** when, with every seed, both ratios are within 0.5 to 2 (the life-lost ratio
is not formed when the take lost under 90 points) and the take holds no single drop over
1.5 times the heaviest blow the scene's monsters can deal in the arena. `trusted.json` holds the
verdicts; `trust.py` reads them.

**Trusted: 3 of 72 scenes** by the comparison of like with like (the arena's blows
against the take's drops that have a suspect: `evidence/blows.py`; the module text of calibrate.py);
**3** by the raw comparison (all the life the take lost, the rule
before the refit of the monsters). Of those not trusted, by like with like:

- neither lost 90 points to blows: nothing to measure: 41
- the arena took under 0.5 of the take: 19
- the take lost under 90 points to blows and the arena took 90 or more: 5
- the arena took over 2 times the take: 3
- believed with the first seed, not with every one: 1

Scenes whose take lost 90 points or more of which under 0.5 have a suspect
("mostly not blows": the arena has nothing to hold against them, whatever its monsters do): 20261011T115400Z-124-122-burst15, 20261011T195037Z-25-373-potions, 20261011T222934Z-24-382-stuck.

## What this says

*Read by hand from the tables below as they stood on 2026-10-12, after the monsters were refitted to the
train half of all takes (`combat/sim/monsters.py`, `evidence/EVIDENCE.md`); a later run rewrites the
tables, not this text. Five of the 72 scenes are not those of the run before the refit: the fixtures
were cut again (cut.py's main set now has its physical resistance) and five newer takes took the place
of five older ones.*

**The arena is no longer three times too harsh; by these windows it is not believable either: 3 scenes
of 72, and the windows cannot say more.** What the monsters do on average is judged elsewhere, on
time that was not chosen for what happened in it: `evidence/refit_check.py` lays each mechanism beside
the check half of all takes, and there the pooled swings, shots, novas and targets are within 0.75 to
1.3 of the measured. Here:

1. **From 3.17 times the takes to 0.48, like with like** (all the arena's points over the take's drops
   that have a suspect; 0.42 raw). The median scene ratio went from 1.86 to 0.15, the quartiles from
   0.75 and 4.01 to 0.05 and 0.73. The arena's character died in 17 windows before and in 1 now; the
   takes' in 2. The arena lands 117 blows where it landed 688 (the takes: 128 drops).
2. **The windows were chosen for what happened in them, and it shows both ways.** 32 scenes were cut
   because the take lost life there (a burst, potions drunk, the death); 40 for something else (a long
   fight, a stuck hunt). With each scene played 30 times and the mean taken (a run by hand, not in the
   tables): in the 32 the arena takes 0.30 of the take's drops with a suspect (5,251 against 17,636
   points), in the 40 it takes 2.4 times (2,307 against 961). A model with the right mean does that
   on windows picked by their outcome: it cannot be told from these fixtures how far the mean is off,
   only that it is not off by three any more. Scenes cut at fixed times, whatever happened, would say.
3. **One window is mostly luck now, as it is in the game.** A swing takes life one time in six, a shot
   one in seventy: 8 s hold 0 to 5 blows of the arena. Over 30 seeds a scene with a ratio is within 0.5 to
   2 in 15% of its plays. The rule of this file (every seed within the bounds) asks for what the
   game itself would not give if the same eight seconds were played twice. Trust by scene is the
   wrong instrument for a model that rolls; a verdict by mechanism (refit_check) or over many windows
   pooled is the right one.
4. **The takes' losses come in clusters, the arena's blows one by one.** 13 drops of 300 points or
   more with a suspect in these windows, 9 of them shared between several strikers; the arena has 5 a
   seed. Where the take lost 1,829 points in 8 s to a pack of Hell Temptresses the arena takes 90: its
   mean for that pack is about 190, the take's eight seconds were ten times that. Rolls that do not
   know of each other do not make such seconds. What makes them is not in a take: a curse, the
   character's protection gone, a stand in the middle of a pack. The recorder writing the character's
   state list would show it.
5. **The sparks of a Lightning Enchanted monster were not refitted and are now the largest part.** 75 of
   the arena's 117 blows, 3,207 of its 9,136 points; every spark that touches the character lands
   (sim/monsters.py: measured on one Herald for where they fly, never for what they take). The one
   scene the arena is far too harsh in (20261011T195037Z-25-373-potions: 4 times the take's blows, the
   character dead in 24 of 30 plays) is the Herald's sparks.
6. **The death (20261011T195037Z-25-493).** The take: one drop of 1,051 at 3.0 s, the tier 2 Herald in
   an attack mode 8.9 units off. Before the refit no monster of the scene could deal it (370 at most)
   and none reached further than 3.2 units. Now the Herald's blow goes up to 1,650 and a swing may be
   begun from up to 12 units; played 400 times (by hand), the arena's character dies in the three
   seconds in 8 plays, loses 500 points or more in 36 and nothing in 186. In the table's first seed it
   loses nothing. So it can die where the recorded one died, and seldom does: the arena does not
   know what made that blow either.
7. **By type** (like with like, the tables below): Ice Spawn scenes pool at 0.83 and hold 2 of the 3
   trusted scenes, Ghost 1.05, Devilkin 1.12 (one nova on the staff's set carries it); the scenes led
   by shooters are low (Dark Archer 0.08, Hell Temptress 0.18), and so are Returned (0.07). All of
   these are scenes of the kinds chosen for their bursts. Black Soul's factor of 5 on every shot was
   not refitted (the takes hold 34 of its shots and no hit of one alone).
8. **The kills did not move** (median 0.78, pooled 0.81 of 58 scenes): they are the character's
   doing and the companions', which this refit did not touch.

**What limits the measurement itself.** 41 scenes have under 90 points lost to blows in the take and
in the arena alike. 3 scenes are mostly not blows (named above): their take lost 168 to 1,479 points
of which under half have a suspect. 19 windows end early at a hostile the scene does not hold; the
scenes of one moment cut three times (20261012T065226Z-130-4606, -4609, -4612) count three times.

**What would make the arena believable for a safety rule, in order:** (a) scenes cut at fixed times,
so that the mean can be checked on windows not chosen by their outcome; (b) the character's state
list in the takes (curses, the protection it has up), so that the clusters can be modelled instead
of averaged; (c) the sparks fitted like the swings; (d) more play against the types that still use the
pooled rows (all but 5 melee types and 3 shooters have their own chance to take life).

## The scenes

| scene | kind | area | hostiles | seconds | taken take | taken arena | ratio | take, with a suspect | ratio | kills take | kills arena | ratio | trusted | notes |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | --- | --- | --- |
| 20261010T214359Z-25-1195-potions | potions | Tower Cellar Level 5 (25) | 18, most DarkStalker (45) | 8.0 | 1490 | 497 | 0.33 (0.00 to 0.33) | 1490 | 0.33 (0.00 to 0.33) | 17 | 8 | 0.47 | no | 2 belt keys replayed on the assumed belt; the character went 27 units from where the scene has it; assumed: hand |
| 20261010T214359Z-25-1258-burst | burst | Tower Cellar Level 5 (25) | 18, most DarkStalker (45) | 8.0 | 1490 | 0 | 0.00 (0.00 to 0.07) | 1490 | 0.00 (0.00 to 0.07) | 18 | 10 | 0.56 | no | 3 belt keys replayed on the assumed belt; the character went 12 units from where the scene has it; assumed: hand |
| 20261011T001816Z-131-1660-potions | potions | Throne of Destruction (131) | 1, most Baal Throne (543) | 0.4 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 0.4 s; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T085143Z-124-102-burst | burst | Halls of Vaught (124) | 47, most IceSpawn (458) | 8.0 | 1001 | 855 | 0.85 (0.58 to 1.46) | 1001 | 0.85 (0.58 to 1.46) | 26 | 28 | 1.08 | yes | 2 belt keys replayed on the assumed belt; assumed: hand |
| 20261011T092540Z-124-101-potions | potions | Halls of Vaught (124) | 47, most IceSpawn (458) | 8.0 | 1053 | 595 | 0.56 (0.56 to 1.02) | 564 | 1.05 (1.05 to 1.91) | 31 | 30 | 0.97 | yes | 3 belt keys replayed on the assumed belt; the character went 25 units from where the scene has it; assumed: hand |
| 20261011T103818Z-124-49-burst15 | burst15 | Halls of Vaught (124) | 14, most Hell Temptress (472) | 1.6 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 1.6 s; the character went 63 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T104325Z-124-216-burst15 | burst15 | Halls of Vaught (124) | 40, most IceSpawn (458) | 8.0 | 449 | 68 | 0.15 (0.01 to 1.11) | 449 | 0.15 (0.01 to 1.11) | 30 | 28 | 0.93 | no (1 of 5 seeds) | the character went 24 units from where the scene has it; assumed: hand |
| 20261011T104524Z-124-72-burst15 | burst15 | Halls of Vaught (124) | 38, most IceSpawn (458) | 1.6 | 0 | 0 | - | 0 | - | 1 | 0 | 0.00 | no | a hostile the scene lacks is within 12 of the character at 1.6 s; the character went 30 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T115400Z-124-122-burst15 | burst15 | Halls of Vaught (124) | 27, most IceSpawn (458) | 8.0 | 672 | 288 | 0.43 (0.00 to 0.61) | 155 | 1.86 (0.00 to 2.63) | 27 | 25 | 0.93 | no (1 of 5 seeds) | the character went 16 units from where the scene has it; assumed: hand; mostly not blows: 155 of the 672 points the take lost have a suspect |
| 20261011T122736Z-124-3499-potions | potions | Halls of Vaught (124) | 23, most Slayerexp (682) | 8.0 | 431 | 17 | 0.04 (0.00 to 0.23) | 370 | 0.05 (0.00 to 0.27) | 20 | 13 | 0.65 | no | 3 belt keys replayed on the assumed belt; the character went 34 units from where the scene has it; assumed: hand |
| 20261011T143225Z-25-155-burst15 | burst15 | Tower Cellar Level 5 (25) | 25, most Ghost (38) | 8.0 | 374 | 113 | 0.30 (0.00 to 0.30) | 374 | 0.30 (0.00 to 0.30) | 9 | 8 | 0.89 | no | assumed: hand |
| 20261011T143607Z-25-987-burst15 | burst15 | Tower Cellar Level 5 (25) | 26, most Devilkin (21) | 8.0 | 420 | 0 | 0.00 (0.00 to 0.49) | 420 | 0.00 (0.00 to 0.49) | 16 | 9 | 0.56 | no | the character went 35 units from where the scene has it; assumed: hand |
| 20261011T161644Z-25-322-burst15 | burst15 | Tower Cellar Level 5 (25) | 9, most Ghost (38) | 6.3 | 359 | 0 | 0.00 (0.00 to 0.00) | 359 | 0.00 (0.00 to 0.00) | 8 | 8 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 6.4 s; the character went 47 units from where the scene has it; assumed: hand |
| 20261011T165853Z-25-18-burst15 | burst15 | Tower Cellar Level 5 (25) | 6, most Ghost (38) | 1.5 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 1.5 s; the character went 90 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T171432Z-25-18-long | long | Tower Cellar Level 5 (25) | 9, most Devilkin (21) | 0.5 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 0.5 s; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T182610Z-6-97-long | long | Black Marsh (6) | 7, most BloodHawk (16) | 1.2 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 1.3 s; the character went 30 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T182707Z-23-31-long | long | Tower Cellar Level 3 (23) | 16, most Devilkin (21) | 8.0 | 0 | 0 | - | 0 | - | 15 | 14 | 0.93 | no | the character went 41 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T183714Z-25-134-long | long | Tower Cellar Level 5 (25) | 24, most DarkArcher (162) | 3.7 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 3.7 s; the character went 35 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T183714Z-25-164-burst15 | burst15 | Tower Cellar Level 5 (25) | 36, most Devilkin (21) | 8.0 | 434 | 66 | 0.15 (0.00 to 0.28) | 434 | 0.15 (0.00 to 0.28) | 11 | 9 | 0.82 | no | the character went 34 units from where the scene has it; assumed: hand |
| 20261011T183714Z-25-375-potions | potions | Tower Cellar Level 5 (25) | 15, most Devilkin (21) | 7.3 | 372 | 58 | 0.15 (0.00 to 0.15) | 372 | 0.15 (0.00 to 0.15) | 9 | 7 | 0.78 | no | a hostile the scene lacks is within 12 of the character at 7.3 s; 5 belt keys replayed on the assumed belt; the character went 24 units from where the scene has it; assumed: hand |
| 20261011T191333Z-25-663-burst15 | burst15 | Tower Cellar Level 5 (25) | 11, most DarkArcher (162) | 8.0 | 864 | 112 | 0.13 (0.04 to 0.19) | 864 | 0.13 (0.04 to 0.19) | 9 | 7 | 0.78 | no | 2 belt keys replayed on the assumed belt; the character went 12 units from where the scene has it; assumed: hand |
| 20261011T191333Z-25-690-burst | burst | Tower Cellar Level 5 (25) | 11, most DarkArcher (162) | 8.0 | 864 | 156 | 0.18 (0.13 to 0.31) | 864 | 0.18 (0.13 to 0.31) | 9 | 6 | 0.67 | no | 2 belt keys replayed on the assumed belt; assumed: hand |
| 20261011T192015Z-25-42-burst15 | burst15 | Tower Cellar Level 5 (25) | 27, most Devilkin (21) | 1.2 | 0 | 0 | - | 0 | - | 1 | 0 | 0.00 | no | a hostile the scene lacks is within 12 of the character at 1.2 s; the character went 30 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T192530Z-21-0-long | long | Tower Cellar Level 1 (21) | 7, most Devilkin (21) | 0.6 | 0 | 15 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 0.6 s; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T193254Z-6-1820-long | long | Black Marsh (6) | 9, most Returned (1) | 4.5 | 0 | 0 | - | 0 | - | 6 | 4 | 0.67 | no | a hostile the scene lacks is within 12 of the character at 4.5 s; the character went 41 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T193625Z-22-358-burst15 | burst15 | Tower Cellar Level 2 (22) | 8, most DarkArcher (162) | 8.0 | 593 | 0 | 0.00 (0.00 to 0.00) | 414 | 0.00 (0.00 to 0.00) | 8 | 7 | 0.88 | no | 2 belt keys replayed on the assumed belt; the character went 48 units from where the scene has it; assumed: hand |
| 20261011T194054Z-25-0-long | long | Tower Cellar Level 5 (25) | 3, most BloodClan (55) | 2.5 | 0 | 0 | - | 0 | - | 3 | 2 | 0.67 | no | a hostile the scene lacks is within 12 of the character at 2.6 s; the character went 21 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T194327Z-6-3063-long | long | Black Marsh (6) | 66, most Carver (20) | 8.0 | 0 | 0 | - | 0 | - | 33 | 34 | 1.03 | no | the character went 24 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T194710Z-22-641-burst15 | burst15 | Tower Cellar Level 2 (22) | 27, most Devilkin (21) | 8.0 | 0 | 0 | - | 0 | - | 15 | 8 | 0.53 | no | the character went 26 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T195037Z-25-2-long | long | Tower Cellar Level 5 (25) | 16, most Devilkin (21) | 8.0 | 0 | 25 | - | 0 | - | 4 | 1 | 0.25 | no | the character went 19 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T195037Z-25-373-potions | potions | Tower Cellar Level 5 (25) | 17, most BloodClan (55) | 7.9 | 1479 | 1387 | 0.94 (0.82 to 2.32) | 409 | 3.39 (2.95 to 8.40) | 6 | 8 | 1.33 | no | the character died in the take at 7.9 s; 3 belt keys replayed on the assumed belt; assumed: hand; the character died in the arena at 4.6 s; mostly not blows: 409 of the 1479 points the take lost have a suspect |
| 20261011T195037Z-25-493-death | death | Tower Cellar Level 5 (25) | 11, most DarkArcher (162) | 3.0 | 1108 | 0 | 0.00 (0.00 to 0.46) | 1108 | 0.00 (0.00 to 0.46) | 0 | 0 | 1.00 | no | the character died in the take at 3.0 s; 1 belt keys replayed on the assumed belt; assumed: hand |
| 20261011T211725Z-22-1093-burst15 | burst15 | Tower Cellar Level 2 (22) | 4, most Ghost (38) | 8.0 | 339 | 381 | 1.12 (0.66 to 1.34) | 229 | 1.66 (0.98 to 1.99) | 4 | 3 | 0.75 | yes | the character went 25 units from where the scene has it; assumed: hand |
| 20261011T211818Z-23-535-long | long | Tower Cellar Level 3 (23) | 12, most Devilkin (21) | 8.0 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T211958Z-25-1-long | long | Tower Cellar Level 5 (25) | 19, most BloodClan (55) | 7.2 | 0 | 165 | - | 0 | - | 5 | 0 | 0.00 | no | a hostile the scene lacks is within 12 of the character at 7.3 s; the character went 59 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T212453Z-23-172-burst15 | burst15 | Tower Cellar Level 3 (23) | 8, most BloodClan (55) | 2.7 | 0 | 0 | - | 0 | - | 4 | 3 | 0.75 | no | a hostile the scene lacks is within 12 of the character at 2.7 s; the character went 48 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T220301Z-6-69-long | long | Black Marsh (6) | 31, most Carver (20) | 8.0 | 0 | 0 | - | 0 | - | 13 | 11 | 0.85 | no | the character went 24 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T222330Z-24-41-long | long | Tower Cellar Level 4 (24) | 8, most Devilkin (21) | 8.0 | 180 | 1196 | 6.64 (0.00 to 6.64) | 180 | 6.64 (0.00 to 6.64) | 6 | 4 | 0.67 | no | the character went 30 units from where the scene has it |
| 20261011T222624Z-25-57-long | long | Tower Cellar Level 5 (25) | 20, most Devilkin (21) | 8.0 | 48 | 0 | - | 48 | - | 0 | 0 | 1.00 | no | the character went 22 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T222923Z-23-115-stuck | stuck | Tower Cellar Level 3 (23) | 7, most Ghost (38) | 6.9 | 0 | 516 | - | 0 | - | 7 | 7 | 1.00 | no | the take ends or leaves the level at 6.9 s; the character went 35 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T222934Z-24-382-stuck | stuck | Tower Cellar Level 4 (24) | 12, most Devilkin (21) | 8.0 | 168 | 274 | 1.63 (0.82 to 2.45) | 0 | - | 12 | 10 | 0.83 | no | the character went 35 units from where the scene has it; mostly not blows: 0 of the 168 points the take lost have a suspect |
| 20261011T223004Z-25-192-stuck | stuck | Tower Cellar Level 5 (25) | 14, most Devilkin (21) | 8.0 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | the character went 18 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T223134Z-38-794-burst15 | burst15 | Tristram (38) | 15, most Returned (1) | 8.0 | 454 | 0 | 0.00 (0.00 to 1.09) | 454 | 0.00 (0.00 to 1.09) | 9 | 6 | 0.67 | no (1 of 5 seeds) | the character went 30 units from where the scene has it |
| 20261011T223134Z-38-817-stuck | stuck | Tristram (38) | 20, most Returned (1) | 8.0 | 454 | 67 | 0.15 (0.00 to 0.56) | 454 | 0.15 (0.00 to 0.56) | 9 | 4 | 0.44 | no | the character went 31 units from where the scene has it |
| 20261011T225311Z-38-622-stuck | stuck | Tristram (38) | 3, most SkeletonArcher (170) | 5.8 | 0 | 0 | - | 0 | - | 3 | 3 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 5.9 s; the character went 47 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T231204Z-38-164-stuck | stuck | Tristram (38) | 9, most Carver (20) | 8.0 | 0 | 75 | - | 0 | - | 5 | 5 | 1.00 | no | the take holds under 90 points of life lost: no ratio |
| 20261011T231408Z-39-134-stuck | stuck | Moo Moo Farm (39) | 66, most Hell Bovine (391) | 8.0 | 0 | 0 | - | 0 | - | 10 | 12 | 1.20 | no | the take holds under 90 points of life lost: no ratio |
| 20261011T231408Z-39-3182-burst15 | burst15 | Moo Moo Farm (39) | 13, most Hell Bovine (391) | 8.0 | 0 | 0 | - | 0 | - | 9 | 5 | 0.56 | no | the character went 43 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T231408Z-39-377-long | long | Moo Moo Farm (39) | 29, most Hell Bovine (391) | 6.3 | 0 | 0 | - | 0 | - | 21 | 11 | 0.52 | no | a hostile the scene lacks is within 12 of the character at 6.3 s; the character went 33 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T233544Z-3-2158-stuck | stuck | Cold Plains (3) | 7, most Fallen (19) | 6.4 | 0 | 0 | - | 0 | - | 6 | 5 | 0.83 | no | a hostile the scene lacks is within 12 of the character at 6.4 s; the character went 44 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T233544Z-3-3280-long | long | Cold Plains (3) | 31, most Fallen (19) | 8.0 | 0 | 0 | - | 0 | - | 18 | 19 | 1.06 | no | the character went 55 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T234014Z-9-197-stuck | stuck | Cave Level 1 (9) | 14, most HungryDead (6) | 8.0 | 0 | 0 | - | 0 | - | 7 | 5 | 0.71 | no | the take holds under 90 points of life lost: no ratio |
| 20261011T234425Z-13-954-stuck | stuck | Cave Level 2 (13) | 1, most HungryDead (6) | 8.0 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | the character went 57 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T061027Z-115-1803-stuck | stuck | Glacial Trail (115) | 11, most ReanimatedHorde (437) | 8.0 | 0 | 0 | - | 0 | - | 11 | 6 | 0.55 | no | the character went 63 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T061557Z-115-298-stuck | stuck | Glacial Trail (115) | 32, most BoneWarrior (648) | 8.0 | 0 | 0 | - | 0 | - | 9 | 15 | 1.67 | no | the character went 29 units from where the scene has it; assumed: level, mods, tier; the take holds under 90 points of life lost: no ratio |
| 20261012T063130Z-116-561-stuck | stuck | Drifter Cavern (116) | 2, most DarkArcher (614) | 8.0 | 0 | 0 | - | 0 | - | 2 | 2 | 1.00 | no | the character went 71 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T064056Z-6-242-stuck | stuck | Black Marsh (6) | 24, most Carver (20) | 8.0 | 0 | 0 | - | 0 | - | 12 | 14 | 1.17 | no | the character went 42 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T064056Z-6-326-long | long | Black Marsh (6) | 23, most Carver (20) | 8.0 | 0 | 0 | - | 0 | - | 12 | 17 | 1.42 | no | the character went 42 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T064210Z-129-354-burst15 | burst15 | The Worldstone Keep Level 2 (129) | 7, most BlackSoul (640) | 8.0 | 329 | 124 | 0.38 (0.25 to 0.46) | 329 | 0.38 (0.25 to 0.46) | 7 | 7 | 1.00 | no | the character went 46 units from where the scene has it |
| 20261012T064210Z-129-698-long | long | The Worldstone Keep Level 2 (129) | 20, most BlackSoul (640) | 8.0 | 0 | 924 | - | 0 | - | 12 | 8 | 0.67 | no | the character went 50 units from where the scene has it; assumed: full; the take holds under 90 points of life lost: no ratio |
| 20261012T064317Z-130-0-long | long | The Worldstone Keep Level 3 (130) | 1, most Baal Taunt (545) | 4.2 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 4.2 s; the character went 39 units from where the scene has it; assumed: full, level, mods, tier; the take holds under 90 points of life lost: no ratio |
| 20261012T064317Z-130-662-stuck | stuck | The Worldstone Keep Level 3 (130) | 11, most Hell Temptress (472) | 8.0 | 0 | 0 | - | 0 | - | 4 | 4 | 1.00 | no | assumed: full, level, mods, tier; the take holds under 90 points of life lost: no ratio |
| 20261012T065226Z-130-0-long | long | The Worldstone Keep Level 3 (130) | 7, most Hell Temptress (472) | 8.0 | 86 | 154 | - | 86 | - | 4 | 3 | 0.75 | no | the character went 46 units from where the scene has it; assumed: full, level; the take holds under 90 points of life lost: no ratio |
| 20261012T065226Z-130-101-stuck | stuck | The Worldstone Keep Level 3 (130) | 7, most Hell Temptress (472) | 8.0 | 99 | 597 | 6.03 (3.50 to 11.99) | 99 | 6.03 (3.50 to 11.99) | 5 | 4 | 0.80 | no | the character went 20 units from where the scene has it; assumed: full |
| 20261012T065226Z-130-4606-burst15 | burst15 | The Worldstone Keep Level 3 (130) | 16, most Hell Temptress (472) | 8.0 | 1937 | 92 | 0.05 (0.00 to 0.21) | 1829 | 0.05 (0.00 to 0.23) | 12 | 5 | 0.42 | no | 3 belt keys replayed on the assumed belt; the character went 20 units from where the scene has it; assumed: full |
| 20261012T065226Z-130-4609-potions | potions | The Worldstone Keep Level 3 (130) | 16, most Hell Temptress (472) | 8.0 | 1937 | 92 | 0.05 (0.00 to 0.21) | 1829 | 0.05 (0.00 to 0.23) | 12 | 5 | 0.42 | no | 3 belt keys replayed on the assumed belt; the character went 20 units from where the scene has it; assumed: full |
| 20261012T065226Z-130-4612-burst | burst | The Worldstone Keep Level 3 (130) | 16, most Hell Temptress (472) | 8.0 | 1937 | 92 | 0.05 (0.00 to 0.21) | 1829 | 0.05 (0.00 to 0.23) | 12 | 5 | 0.42 | no | 3 belt keys replayed on the assumed belt; the character went 20 units from where the scene has it; assumed: full |
| 20261012T165150Z-115-2826-stuck | stuck | Glacial Trail (115) | 23, most BoneWarrior (648) | 8.0 | 35 | 0 | - | 0 | - | 20 | 19 | 0.95 | no | the character went 42 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T165722Z-115-276-stuck | stuck | Glacial Trail (115) | 9, most Blood Lord1 (652) | 8.0 | 77 | 9 | - | 22 | - | 5 | 1 | 0.20 | no | the character went 14 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T165857Z-115-35-stuck | stuck | Glacial Trail (115) | 9, most BoneMage (624) | 8.0 | 72 | 0 | - | 72 | - | 8 | 6 | 0.75 | no | the character went 39 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T165857Z-115-3793-burst15 | burst15 | Glacial Trail (115) | 4, most PitViper (595) | 2.3 | 30 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 2.3 s; the character went 49 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T170305Z-116-59-stuck | stuck | Drifter Cavern (116) | 9, most NightClan (586) | 8.0 | 0 | 0 | - | 0 | - | 9 | 9 | 1.00 | no | the character went 46 units from where the scene has it; the take holds under 90 points of life lost: no ratio |

## The ratios

"Pooled" is all the arena's points over all the take's in the group, the scenes without a ratio of
their own among them. The kills columns are of the scenes where a hostile died in the take. Each
table is given twice: like with like (the take's drops with a suspect), then raw (all its life lost).

### Like with like

| all | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 72 | 3 | 26 | 0.00 | 0.05 | 0.15 | 0.73 | 6.64 | 0.48 | 5 | 58 | 0.78 | 0.81 |

| kind | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| burst15 | 20 | 1 | 12 | 0.00 | 0.00 | 0.14 | 0.32 | 1.86 | 0.20 | 0 | 17 | 0.75 | 0.77 |
| long | 20 | 0 | 1 | 6.64 | 6.64 | 6.64 | 6.64 | 6.64 | 7.89 | 3 | 13 | 0.67 | 0.84 |
| stuck | 20 | 0 | 2 | 0.15 | 1.62 | 3.09 | 4.56 | 6.03 | 2.38 | 2 | 18 | 0.97 | 0.91 |
| potions | 7 | 1 | 6 | 0.05 | 0.08 | 0.24 | 0.87 | 3.39 | 0.53 | 0 | 6 | 0.71 | 0.75 |
| burst | 4 | 1 | 4 | 0.00 | 0.04 | 0.12 | 0.35 | 0.85 | 0.21 | 0 | 4 | 0.61 | 0.75 |
| death | 1 | 0 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0 | 0 | - | - |

By the type most of the scene's hostiles are of:

| most hostiles | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Devilkin (21) | 14 | 0 | 4 | 0.00 | 0.11 | 0.15 | 1.78 | 6.64 | 1.12 | 1 | 9 | 0.67 | 0.70 |
| Hell Temptress (472) | 7 | 0 | 4 | 0.05 | 0.05 | 0.05 | 1.55 | 6.03 | 0.18 | 1 | 6 | 0.58 | 0.53 |
| Carver (20) | 5 | 0 | 0 | - | - | - | - | - | - | 0 | 5 | 1.03 | 1.08 |
| DarkArcher (162) | 5 | 0 | 4 | 0.00 | 0.00 | 0.06 | 0.14 | 0.18 | 0.08 | 0 | 3 | 0.78 | 0.77 |
| Ghost (38) | 5 | 1 | 3 | 0.00 | 0.15 | 0.30 | 0.98 | 1.66 | 1.05 | 1 | 4 | 0.94 | 0.93 |
| IceSpawn (458) | 5 | 2 | 4 | 0.15 | 0.68 | 0.95 | 1.26 | 1.86 | 0.83 | 0 | 5 | 0.93 | 0.97 |
| BloodClan (55) | 4 | 0 | 1 | 3.39 | 3.39 | 3.39 | 3.39 | 3.39 | 3.79 | 1 | 4 | 0.71 | 0.72 |
| Hell Bovine (391) | 3 | 0 | 0 | - | - | - | - | - | - | 0 | 3 | 0.56 | 0.70 |
| Returned (1) | 3 | 0 | 2 | 0.00 | 0.04 | 0.07 | 0.11 | 0.15 | 0.07 | 0 | 3 | 0.67 | 0.58 |
| BlackSoul (640) | 2 | 0 | 1 | 0.38 | 0.38 | 0.38 | 0.38 | 0.38 | 3.18 | 1 | 2 | 0.83 | 0.79 |
| BoneWarrior (648) | 2 | 0 | 0 | - | - | - | - | - | - | 0 | 2 | 1.31 | 1.17 |
| DarkStalker (45) | 2 | 0 | 2 | 0.00 | 0.08 | 0.17 | 0.25 | 0.33 | 0.17 | 0 | 2 | 0.51 | 0.51 |
| Fallen (19) | 2 | 0 | 0 | - | - | - | - | - | - | 0 | 2 | 0.94 | 1.00 |
| HungryDead (6) | 2 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 0.71 | 0.71 |
| Baal Taunt (545) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| Baal Throne (543) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| Blood Lord1 (652) | 1 | 0 | 0 | - | - | - | - | - | 0.40 | 0 | 1 | 0.20 | 0.20 |
| BloodHawk (16) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| BoneMage (624) | 1 | 0 | 0 | - | - | - | - | - | 0.00 | 0 | 1 | 0.75 | 0.75 |
| DarkArcher (614) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 1.00 | 1.00 |
| NightClan (586) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 1.00 | 1.00 |
| PitViper (595) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| ReanimatedHorde (437) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 0.55 | 0.55 |
| SkeletonArcher (170) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 1.00 | 1.00 |
| Slayerexp (682) | 1 | 0 | 1 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0 | 1 | 0.65 | 0.65 |

### Raw

| all | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 72 | 3 | 27 | 0.00 | 0.04 | 0.15 | 0.50 | 6.64 | 0.42 | 4 | 58 | 0.78 | 0.81 |

| kind | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| burst15 | 20 | 1 | 12 | 0.00 | 0.00 | 0.14 | 0.32 | 1.12 | 0.17 | 0 | 17 | 0.75 | 0.77 |
| long | 20 | 0 | 1 | 6.64 | 6.64 | 6.64 | 6.64 | 6.64 | 7.89 | 3 | 13 | 0.67 | 0.84 |
| stuck | 20 | 0 | 3 | 0.15 | 0.89 | 1.63 | 3.83 | 6.03 | 1.70 | 1 | 18 | 0.97 | 0.91 |
| potions | 7 | 1 | 6 | 0.04 | 0.07 | 0.24 | 0.51 | 0.94 | 0.39 | 0 | 6 | 0.71 | 0.75 |
| burst | 4 | 1 | 4 | 0.00 | 0.04 | 0.11 | 0.35 | 0.85 | 0.21 | 0 | 4 | 0.61 | 0.75 |
| death | 1 | 0 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0 | 0 | - | - |

By the type most of the scene's hostiles are of:

| most hostiles | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Devilkin (21) | 14 | 0 | 5 | 0.00 | 0.15 | 0.15 | 1.63 | 6.64 | 1.01 | 0 | 9 | 0.67 | 0.70 |
| Hell Temptress (472) | 7 | 0 | 4 | 0.05 | 0.05 | 0.05 | 1.54 | 6.03 | 0.17 | 1 | 6 | 0.58 | 0.53 |
| Carver (20) | 5 | 0 | 0 | - | - | - | - | - | - | 0 | 5 | 1.03 | 1.08 |
| DarkArcher (162) | 5 | 0 | 4 | 0.00 | 0.00 | 0.06 | 0.14 | 0.18 | 0.08 | 0 | 3 | 0.78 | 0.77 |
| Ghost (38) | 5 | 1 | 3 | 0.00 | 0.15 | 0.30 | 0.71 | 1.12 | 0.94 | 1 | 4 | 0.94 | 0.93 |
| IceSpawn (458) | 5 | 2 | 4 | 0.15 | 0.36 | 0.50 | 0.64 | 0.85 | 0.57 | 0 | 5 | 0.93 | 0.97 |
| BloodClan (55) | 4 | 0 | 1 | 0.94 | 0.94 | 0.94 | 0.94 | 0.94 | 1.05 | 1 | 4 | 0.71 | 0.72 |
| Hell Bovine (391) | 3 | 0 | 0 | - | - | - | - | - | - | 0 | 3 | 0.56 | 0.70 |
| Returned (1) | 3 | 0 | 2 | 0.00 | 0.04 | 0.07 | 0.11 | 0.15 | 0.07 | 0 | 3 | 0.67 | 0.58 |
| BlackSoul (640) | 2 | 0 | 1 | 0.38 | 0.38 | 0.38 | 0.38 | 0.38 | 3.18 | 1 | 2 | 0.83 | 0.79 |
| BoneWarrior (648) | 2 | 0 | 0 | - | - | - | - | - | 0.00 | 0 | 2 | 1.31 | 1.17 |
| DarkStalker (45) | 2 | 0 | 2 | 0.00 | 0.08 | 0.17 | 0.25 | 0.33 | 0.17 | 0 | 2 | 0.51 | 0.51 |
| Fallen (19) | 2 | 0 | 0 | - | - | - | - | - | - | 0 | 2 | 0.94 | 1.00 |
| HungryDead (6) | 2 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 0.71 | 0.71 |
| Baal Taunt (545) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| Baal Throne (543) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| Blood Lord1 (652) | 1 | 0 | 0 | - | - | - | - | - | 0.11 | 0 | 1 | 0.20 | 0.20 |
| BloodHawk (16) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| BoneMage (624) | 1 | 0 | 0 | - | - | - | - | - | 0.00 | 0 | 1 | 0.75 | 0.75 |
| DarkArcher (614) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 1.00 | 1.00 |
| NightClan (586) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 1.00 | 1.00 |
| PitViper (595) | 1 | 0 | 0 | - | - | - | - | - | 0.00 | 0 | 0 | - | - |
| ReanimatedHorde (437) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 0.55 | 0.55 |
| SkeletonArcher (170) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 1.00 | 1.00 |
| Slayerexp (682) | 1 | 0 | 1 | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 | 0.04 | 0 | 1 | 0.65 | 0.65 |

The types with 3 scenes or more, by what the arena makes of them (like with like):

| most hostiles | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BloodClan (55) | 4 | 0 | 1 | 3.39 | 3.39 | 3.39 | 3.39 | 3.39 | 3.79 | 1 | 4 | 0.71 | 0.72 |
| Devilkin (21) | 14 | 0 | 4 | 0.00 | 0.11 | 0.15 | 1.78 | 6.64 | 1.12 | 1 | 9 | 0.67 | 0.70 |
| Ghost (38) | 5 | 1 | 3 | 0.00 | 0.15 | 0.30 | 0.98 | 1.66 | 1.05 | 1 | 4 | 0.94 | 0.93 |
| IceSpawn (458) | 5 | 2 | 4 | 0.15 | 0.68 | 0.95 | 1.26 | 1.86 | 0.83 | 0 | 5 | 0.93 | 0.97 |
| Hell Temptress (472) | 7 | 0 | 4 | 0.05 | 0.05 | 0.05 | 1.55 | 6.03 | 0.18 | 1 | 6 | 0.58 | 0.53 |
| DarkArcher (162) | 5 | 0 | 4 | 0.00 | 0.00 | 0.06 | 0.14 | 0.18 | 0.08 | 0 | 3 | 0.78 | 0.77 |
| Returned (1) | 3 | 0 | 2 | 0.00 | 0.04 | 0.07 | 0.11 | 0.15 | 0.07 | 0 | 3 | 0.67 | 0.58 |
| Carver (20) | 5 | 0 | 0 | - | - | - | - | - | - | 0 | 5 | 1.03 | 1.08 |
| Hell Bovine (391) | 3 | 0 | 0 | - | - | - | - | - | - | 0 | 3 | 0.56 | 0.70 |

## The big drops

| | drops of 300 or more | per 10,000 s | largest |
| --- | ---: | ---: | ---: |
| the takes, all | 15 | 314 | 1051 |
| the takes, with a suspect | 13 | 272 | 1051 |
| the arena, mean of 5 seeds | 5.0 | 105 | - |

The takes' by class: several 9, nova/explosion 3, unknown 2, sole ranged 1. The arena's by seed: 6, 7, 7, 3, 2. 477 s of windows; they were cut around bursts, potions and deaths, so the rate is far above a whole take's (20 in 19,097 s).

## The blows, by who struck

Over the compared windows, first seed. An arena blow is one strike, shot or spark after the
resistances of the set in hand. A drop of the take is the life gone between two samples (several
blows landing together are one drop); it is put on a type only when one monster alone was striking
(`combat/hurts.py` `sole`), so the take's rows by type are a part of its drops: the last row has all,
the drops nobody is blamed for among them.

| striker | arena: kind | blows | median | points | take: drops put on it | median | points |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BloodClan (55) | spark | 43 | 37 | 1602 | 1 | 210 | 210 |
| IceSpawn (458) | melee | 16 | 77 | 1370 | 1 | 13 | 13 |
| Devilkin (21) | nova | 1 | 1196 | 1196 | 0 | - | 0 |
| DarkStalker (45) | melee | 4 | 75 | 679 | 0 | - | 0 |
| Ghost (38) | nova | 2 | 337 | 673 | 0 | - | 0 |
| BlackSoul (640) | shot | 2 | 319 | 638 | 0 | - | 0 |
| Hell Temptress (472) | spark | 11 | 42 | 571 | 0 | - | 0 |
| Ghost (38) | spark | 8 | 37 | 498 | 0 | - | 0 |
| BlackSoul (640) | spark | 9 | 41 | 371 | 0 | - | 0 |
| Ghost (631) | melee | 1 | 288 | 288 | 0 | - | 0 |
| Hell Temptress (472) | shot | 3 | 94 | 281 | 0 | - | 0 |
| BloodClan (55) | melee | 4 | 27 | 234 | 0 | - | 0 |
| Hell Temptress (472) | nova | 1 | 180 | 180 | 0 | - | 0 |
| DarkArcher (162) | spark | 4 | 41 | 165 | 3 | 98 | 203 |
| Slayerexp (682) | melee | 3 | 19 | 115 | 1 | 23 | 23 |
| Carver (20) | melee | 1 | 75 | 75 | 0 | - | 0 |
| Griswold (365) | melee | 1 | 67 | 67 | 0 | - | 0 |
| Arach (685) | melee | 1 | 63 | 63 | 0 | - | 0 |
| Devilkin (21) | melee | 1 | 61 | 61 | 0 | - | 0 |
| BoneMage (624) | shot | 1 | 9 | 9 | 0 | - | 0 |
| Returned (1) | - | 0 | - | 0 | 2 | 157 | 314 |
| every melee | melee | 32 | 66 | 2953 | - | - | - |
| every nova | nova | 4 | 348 | 2048 | - | - | - |
| every shot | shot | 6 | 94 | 928 | - | - | - |
| every spark | spark | 75 | 37 | 3207 | - | - | - |
| all, 477 s of 72 scenes | | 117 | 37 | 9136 | 128 | 132 | 20122 |

## The window

Each scene played for 15 s without leaving at the first stranger (a hostile the scene does not
hold within 12 units of the recorded character). "Still recorded": the take is in the
level and the character alive.

| seconds | scenes still recorded | of them no stranger yet | of those, the take lost enough | median units a monster is from its recording | hostiles within 12: take | arena |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 72 | 64 | 4 | 4.8 | 2.1 | 2.5 |
| 4 | 71 | 59 | 24 | 6.1 | 2.1 | 2.8 |
| 6 | 71 | 56 | 26 | 5.8 | 1.6 | 2.1 |
| 8 | 69 | 49 | 23 | 7.2 | 0.7 | 1.6 |
| 10 | 67 | 40 | 24 | 16.8 | 0.5 | 1.5 |
| 12 | 66 | 33 | 20 | 16.8 | 0.7 | 1.7 |
| 15 | 59 | 25 | 14 | 19.0 | 0.6 | 1.8 |

## The death: 20261011T195037Z-25-493-death

| seconds | life in the take | life in the arena (seed 1) | hostiles within 12 in the arena |
| ---: | ---: | ---: | ---: |
| 0.00 | 995 | 995 | 3 |
| 0.48 | 1018 | 995 | 3 |
| 1.00 | 1029 | 995 | 3 |
| 1.52 | 972 | 1008 | 3 |
| 2.00 | 1006 | 1022 | 3 |
| 2.48 | 1029 | 1038 | 3 |
| 3.00 | 1051 | 1054 | 3 |
| 3.04 | 0 | 1055 | 3 |

- drops in the take: 57 at 1.12 s, 1051 at 3.00 s
- blows in the arena, before an aura: none
- belt keys: column 4 at 1.16 s

## One factor on every blow

Of the 26 scenes with a ratio, the 6 where the arena took nothing are left out (no factor moves them); the rest are split in two by every other name. The median ratio of
the 10 scenes fitted on is 0.32: a factor of **3.15** on every blow would centre it. Played again with it (`play`, `damage_scale`; first seed; "trusted" here is the bare rule of
the two ratios):

| half | scenes | median before | median with the factor | trusted before | trusted with the factor | least | most |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fitted on | 10 | 0.32 | 0.93 | 3 | 3 | 0.16 | 12.97 |
| checked on | 10 | 0.15 | 0.48 | 1 | 1 | 0.16 | 9.91 |
