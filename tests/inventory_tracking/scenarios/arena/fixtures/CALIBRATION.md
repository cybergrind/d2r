# Calibration of the arena

Written by `tests/inventory_tracking/scenarios/arena/calibrate.py` (its module text says how a scene is
played and what is compared) from the takes under `inventory_tracking/runs/combat` on 2026-10-13: every fixture
with a `source`, 8 s from its frame, the monsters rolled with seeds 1 to 5. The table is the
first seed; a ratio is arena / take, with its least and most over the seeds in brackets. A scene is
**trusted** when, with every seed, both ratios are within 0.5 to 2 (the life-lost ratio
is not formed when the take lost under 90 points) and the take holds no single drop over
1.5 times the heaviest blow the scene's monsters can deal in the arena. `trusted.json` holds the
verdicts; `trust.py` reads them.

**Trusted: 0 of 112 scenes** by the comparison of like with like (the arena's blows
against the take's drops that have a suspect: `evidence/blows.py`; the module text of calibrate.py);
**0** by the raw comparison (all the life the take lost, the rule
before the refit of the monsters). Of those not trusted, by like with like:

- neither lost 90 points to blows: nothing to measure: 80
- the arena took under 0.5 of the take: 19
- the take lost under 90 points to blows and the arena took 90 or more: 4
- the life lost agrees, the kills do not: 3
- the arena took over 2 times the take: 3
- believed with the first seed, not with every one: 3

Scenes whose take lost 90 points or more of which under 0.5 have a suspect
("mostly not blows": the arena has nothing to hold against them, whatever its monsters do): 20261011T115400Z-124-122-burst15, 20261011T123516Z-124-121-fixed, 20261011T195037Z-25-373-potions, 20261011T222934Z-24-382-stuck.

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
| 20261010T181624Z-35-595-fixed | fixed | Catacombs Level 2 (35) | 10, most DarkOne (22) | 8.0 | 0 | 0 | - | 0 | - | 8 | 8 | 1.00 | no | the character went 36 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261010T191229Z-36-111-fixed | fixed | Catacombs Level 3 (36) | 11, most Ghoul (7) | 8.0 | 37 | 331 | - | 0 | - | 9 | 6 | 0.67 | no | the character went 13 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261010T202951Z-23-124-fixed | fixed | Tower Cellar Level 3 (23) | 19, most BloodClan (55) | 8.0 | 0 | 0 | - | 0 | - | 11 | 8 | 0.73 | no | the character went 44 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261010T204327Z-22-123-fixed | fixed | Tower Cellar Level 2 (22) | 10, most Devilkin (21) | 8.0 | 0 | 5 | - | 0 | - | 8 | 8 | 1.00 | no | the character went 69 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261010T205536Z-21-122-fixed | fixed | Tower Cellar Level 1 (21) | 3, most BloodClan (55) | 8.0 | 0 | 0 | - | 0 | - | 3 | 2 | 0.67 | no | the character went 100 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261010T214359Z-25-1195-potions | potions | Tower Cellar Level 5 (25) | 18, most DarkStalker (45) | 8.0 | 1490 | 40 | 0.03 (0.00 to 0.05) | 1490 | 0.03 (0.00 to 0.05) | 17 | 8 | 0.47 | no | 2 belt keys replayed on the assumed belt; the character went 27 units from where the scene has it; assumed: hand |
| 20261010T214359Z-25-1258-burst | burst | Tower Cellar Level 5 (25) | 18, most DarkStalker (45) | 8.0 | 1490 | 0 | 0.00 (0.00 to 0.18) | 1490 | 0.00 (0.00 to 0.18) | 18 | 10 | 0.56 | no | 3 belt keys replayed on the assumed belt; the character went 12 units from where the scene has it; assumed: hand |
| 20261010T214830Z-22-124-fixed | fixed | Tower Cellar Level 2 (22) | 25, most Devilkin (21) | 3.5 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | the take ends or leaves the level at 3.5 s; the character went 64 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261010T225724Z-43-1100-fixed | fixed | Far Oasis (43) | 9, most BlackRaptor (17) | 8.0 | 0 | 0 | - | 0 | - | 9 | 4 | 0.44 | no | the character went 22 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T001816Z-131-1660-potions | potions | Throne of Destruction (131) | 1, most Baal Throne (543) | 0.4 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 0.4 s; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T085143Z-124-102-burst | burst | Halls of Vaught (124) | 47, most IceSpawn (458) | 8.0 | 1001 | 1411 | 1.41 (0.21 to 1.41) | 1001 | 1.41 (0.21 to 1.41) | 26 | 0 | 0.00 | no | 2 belt keys replayed on the assumed belt; assumed: hand |
| 20261011T085756Z-123-104-fixed | fixed | Halls of Pain (123) | 34, most Zealot (671) | 6.7 | 223 | 1625 | 7.29 (0.16 to 7.29) | 223 | 7.29 (0.16 to 7.29) | 11 | 0 | 0.00 | no (2 of 5 seeds) | a hostile the scene lacks is within 12 of the character at 6.7 s; the character went 46 units from where the scene has it; assumed: hand |
| 20261011T092540Z-124-101-potions | potions | Halls of Vaught (124) | 47, most IceSpawn (458) | 8.0 | 1053 | 746 | 0.71 (0.44 to 1.77) | 564 | 1.32 (0.82 to 3.30) | 31 | 0 | 0.00 | no (1 of 5 seeds) | 3 belt keys replayed on the assumed belt; the character went 25 units from where the scene has it; assumed: hand |
| 20261011T094636Z-123-117-fixed | fixed | Halls of Pain (123) | 29, most Zealot (671) | 2.1 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 2.2 s; the character went 66 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T102058Z-123-122-fixed | fixed | Halls of Pain (123) | 22, most Flayer (659) | 1.3 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 1.3 s; the character went 54 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T103818Z-124-49-burst15 | burst15 | Halls of Vaught (124) | 14, most Hell Temptress (472) | 1.6 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 1.6 s; the character went 63 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T104058Z-123-122-fixed | fixed | Halls of Pain (123) | 23, most Zealot (671) | 1.4 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 1.4 s; the character went 51 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T104325Z-124-216-burst15 | burst15 | Halls of Vaught (124) | 40, most IceSpawn (458) | 8.0 | 449 | 12 | 0.03 (0.00 to 0.92) | 449 | 0.03 (0.00 to 0.92) | 30 | 28 | 0.93 | no (1 of 5 seeds) | the character went 24 units from where the scene has it; assumed: hand |
| 20261011T104524Z-124-72-burst15 | burst15 | Halls of Vaught (124) | 38, most IceSpawn (458) | 1.6 | 0 | 0 | - | 0 | - | 1 | 1 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 1.6 s; the character went 30 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T104934Z-124-118-fixed | fixed | Halls of Vaught (124) | 47, most IceSpawn (458) | 8.0 | 43 | 3 | - | 43 | - | 36 | 25 | 0.69 | no | assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T115046Z-124-122-fixed | fixed | Halls of Vaught (124) | 44, most IceSpawn (458) | 8.0 | 24 | 25 | - | 0 | - | 41 | 21 | 0.51 | no | the character went 12 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T115400Z-124-122-burst15 | burst15 | Halls of Vaught (124) | 27, most IceSpawn (458) | 8.0 | 672 | 0 | 0.00 (0.00 to 0.19) | 155 | 0.00 (0.00 to 0.81) | 27 | 25 | 0.93 | no (2 of 5 seeds) | the character went 16 units from where the scene has it; assumed: hand; mostly not blows: 155 of the 672 points the take lost have a suspect |
| 20261011T122736Z-124-3499-potions | potions | Halls of Vaught (124) | 23, most Slayerexp (682) | 8.0 | 431 | 296 | 0.69 (0.00 to 0.74) | 370 | 0.80 (0.00 to 0.86) | 20 | 13 | 0.65 | no (1 of 5 seeds) | 3 belt keys replayed on the assumed belt; the character went 34 units from where the scene has it; assumed: hand |
| 20261011T123516Z-124-121-fixed | fixed | Halls of Vaught (124) | 28, most IceSpawn (458) | 8.0 | 181 | 217 | 1.20 (0.11 to 1.98) | 0 | - | 22 | 15 | 0.68 | no | the character went 27 units from where the scene has it; assumed: hand; mostly not blows: 0 of the 181 points the take lost have a suspect |
| 20261011T130810Z-74-612-fixed | fixed | Arcane Sanctuary (74) | 31, most HellClan (56) | 8.0 | 0 | 0 | - | 0 | - | 28 | 22 | 0.79 | no | the character went 44 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T135720Z-21-123-fixed | fixed | Tower Cellar Level 1 (21) | 10, most Devilkin (21) | 3.7 | 0 | 0 | - | 0 | - | 5 | 1 | 0.20 | no | a hostile the scene lacks is within 12 of the character at 3.8 s; the character went 63 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T140324Z-25-122-fixed | fixed | Tower Cellar Level 5 (25) | 29, most Devilkin (21) | 8.0 | 0 | 0 | - | 0 | - | 10 | 8 | 0.80 | no | the character went 26 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T141549Z-21-124-fixed | fixed | Tower Cellar Level 1 (21) | 9, most BloodClan (55) | 3.8 | 0 | 0 | - | 0 | - | 6 | 3 | 0.50 | no | a hostile the scene lacks is within 12 of the character at 3.8 s; the character went 32 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T142329Z-6-119-fixed | fixed | Black Marsh (6) | 30, most Carver (20) | 8.0 | 0 | 0 | - | 0 | - | 12 | 4 | 0.33 | no | the character went 72 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T143205Z-6-118-fixed | fixed | Black Marsh (6) | 20, most NightClan (54) | 1.4 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | the take ends or leaves the level at 1.4 s; the character went 59 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T143225Z-25-155-burst15 | burst15 | Tower Cellar Level 5 (25) | 25, most Ghost (38) | 8.0 | 374 | 626 | 1.67 (0.00 to 2.28) | 374 | 1.67 (0.00 to 2.28) | 9 | 8 | 0.89 | no (2 of 5 seeds) | assumed: hand |
| 20261011T143607Z-25-987-burst15 | burst15 | Tower Cellar Level 5 (25) | 26, most Devilkin (21) | 8.0 | 420 | 0 | 0.00 (0.00 to 0.99) | 420 | 0.00 (0.00 to 0.99) | 16 | 9 | 0.56 | no | the character went 35 units from where the scene has it; assumed: hand |
| 20261011T145954Z-21-123-fixed | fixed | Tower Cellar Level 1 (21) | 30, most Devilkin (21) | 8.0 | 0 | 177 | - | 0 | - | 8 | 3 | 0.38 | no | the character went 39 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T151545Z-21-124-fixed | fixed | Tower Cellar Level 1 (21) | 22, most DarkArcher (162) | 1.9 | 0 | 0 | - | 0 | - | 2 | 0 | 0.00 | no | the take ends or leaves the level at 1.9 s; the character went 53 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T152636Z-25-123-fixed | fixed | Tower Cellar Level 5 (25) | 17, most BloodClan (55) | 8.0 | 9 | 0 | - | 9 | - | 8 | 1 | 0.12 | no | the character went 24 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T160245Z-23-123-fixed | fixed | Tower Cellar Level 3 (23) | 6, most Ghost (38) | 6.1 | 0 | 0 | - | 0 | - | 4 | 4 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 6.2 s; the character went 35 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T161007Z-25-123-fixed | fixed | Tower Cellar Level 5 (25) | 36, most Devilkin (21) | 8.0 | 0 | 0 | - | 0 | - | 15 | 10 | 0.67 | no | the character went 21 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T161644Z-25-118-fixed | fixed | Tower Cellar Level 5 (25) | 17, most DarkStalker (45) | 8.0 | 0 | 0 | - | 0 | - | 15 | 14 | 0.93 | no | the character went 44 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T161644Z-25-322-burst15 | burst15 | Tower Cellar Level 5 (25) | 9, most Ghost (38) | 6.3 | 359 | 157 | 0.44 (0.00 to 0.44) | 359 | 0.44 (0.00 to 0.44) | 8 | 6 | 0.75 | no | a hostile the scene lacks is within 12 of the character at 6.4 s; the character went 47 units from where the scene has it; assumed: hand |
| 20261011T162923Z-25-123-fixed | fixed | Tower Cellar Level 5 (25) | 8, most Devilkin (21) | 7.3 | 0 | 0 | - | 0 | - | 5 | 5 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 7.3 s; the character went 49 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T163643Z-25-123-fixed | fixed | Tower Cellar Level 5 (25) | 5, most BloodClan (55) | 8.0 | 186 | 0 | 0.00 (0.00 to 0.00) | 186 | 0.00 (0.00 to 0.00) | 5 | 3 | 0.60 | no | the character went 13 units from where the scene has it; assumed: hand |
| 20261011T165853Z-25-18-burst15 | burst15 | Tower Cellar Level 5 (25) | 6, most Ghost (38) | 1.5 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 1.5 s; the character went 90 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T170041Z-25-123-fixed | fixed | Tower Cellar Level 5 (25) | 12, most BloodClan (55) | 8.0 | 0 | 191 | - | 0 | - | 8 | 5 | 0.62 | no | assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T171432Z-25-18-long | long | Tower Cellar Level 5 (25) | 9, most Devilkin (21) | 0.5 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 0.5 s; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T182610Z-6-97-long | long | Black Marsh (6) | 7, most BloodHawk (16) | 1.2 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 1.3 s; the character went 30 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T182645Z-21-121-fixed | fixed | Tower Cellar Level 1 (21) | 17, most DarkArcher (162) | 7.7 | 0 | 0 | - | 0 | - | 2 | 2 | 1.00 | no | the take ends or leaves the level at 7.7 s; the character went 91 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T182707Z-23-31-long | long | Tower Cellar Level 3 (23) | 16, most Devilkin (21) | 8.0 | 0 | 0 | - | 0 | - | 15 | 13 | 0.87 | no | the character went 41 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T183714Z-25-134-long | long | Tower Cellar Level 5 (25) | 24, most DarkArcher (162) | 3.7 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 3.7 s; the character went 35 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T183714Z-25-164-burst15 | burst15 | Tower Cellar Level 5 (25) | 36, most Devilkin (21) | 8.0 | 434 | 357 | 0.82 (0.00 to 0.82) | 434 | 0.82 (0.00 to 0.82) | 11 | 0 | 0.00 | no | the character went 34 units from where the scene has it; assumed: hand |
| 20261011T183714Z-25-375-potions | potions | Tower Cellar Level 5 (25) | 15, most Devilkin (21) | 7.3 | 372 | 0 | 0.00 (0.00 to 0.11) | 372 | 0.00 (0.00 to 0.11) | 9 | 7 | 0.78 | no | a hostile the scene lacks is within 12 of the character at 7.3 s; 5 belt keys replayed on the assumed belt; the character went 24 units from where the scene has it; assumed: hand |
| 20261011T191333Z-25-663-burst15 | burst15 | Tower Cellar Level 5 (25) | 11, most DarkArcher (162) | 8.0 | 864 | 0 | 0.00 (0.00 to 0.05) | 864 | 0.00 (0.00 to 0.05) | 9 | 6 | 0.67 | no | 2 belt keys replayed on the assumed belt; the character went 12 units from where the scene has it; assumed: hand |
| 20261011T191333Z-25-690-burst | burst | Tower Cellar Level 5 (25) | 11, most DarkArcher (162) | 8.0 | 864 | 49 | 0.06 (0.00 to 0.06) | 864 | 0.06 (0.00 to 0.06) | 9 | 5 | 0.56 | no | 2 belt keys replayed on the assumed belt; assumed: hand |
| 20261011T192015Z-25-118-fixed | fixed | Tower Cellar Level 5 (25) | 28, most Devilkin (21) | 8.0 | 0 | 0 | - | 0 | - | 10 | 10 | 1.00 | no | the character went 23 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T192015Z-25-42-burst15 | burst15 | Tower Cellar Level 5 (25) | 27, most Devilkin (21) | 1.2 | 0 | 0 | - | 0 | - | 1 | 0 | 0.00 | no | a hostile the scene lacks is within 12 of the character at 1.2 s; the character went 30 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T192530Z-21-0-long | long | Tower Cellar Level 1 (21) | 7, most Devilkin (21) | 0.6 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 0.6 s; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T192932Z-24-114-fixed | fixed | Tower Cellar Level 4 (24) | 12, most DarkArcher (162) | 4.8 | 0 | 0 | - | 0 | - | 6 | 5 | 0.83 | no | the take ends or leaves the level at 4.8 s; the character went 42 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T193254Z-6-1820-long | long | Black Marsh (6) | 9, most Returned (1) | 4.5 | 0 | 0 | - | 0 | - | 6 | 4 | 0.67 | no | a hostile the scene lacks is within 12 of the character at 4.5 s; the character went 41 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T193625Z-22-358-burst15 | burst15 | Tower Cellar Level 2 (22) | 8, most DarkArcher (162) | 8.0 | 593 | 0 | 0.00 (0.00 to 0.00) | 414 | 0.00 (0.00 to 0.00) | 8 | 7 | 0.88 | no | 2 belt keys replayed on the assumed belt; the character went 48 units from where the scene has it; assumed: hand |
| 20261011T194054Z-25-0-long | long | Tower Cellar Level 5 (25) | 3, most BloodClan (55) | 2.5 | 0 | 0 | - | 0 | - | 3 | 2 | 0.67 | no | a hostile the scene lacks is within 12 of the character at 2.6 s; the character went 21 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T194327Z-6-3063-long | long | Black Marsh (6) | 66, most Carver (20) | 8.0 | 0 | 0 | - | 0 | - | 33 | 34 | 1.03 | no | the character went 24 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T194710Z-22-641-burst15 | burst15 | Tower Cellar Level 2 (22) | 27, most Devilkin (21) | 8.0 | 0 | 0 | - | 0 | - | 15 | 7 | 0.47 | no | the character went 26 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T194956Z-24-616-fixed | fixed | Tower Cellar Level 4 (24) | 15, most Devilkin (21) | 8.0 | 13 | 0 | - | 0 | - | 13 | 10 | 0.77 | no | the character went 46 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T195037Z-25-2-long | long | Tower Cellar Level 5 (25) | 16, most Devilkin (21) | 8.0 | 0 | 3 | - | 0 | - | 4 | 1 | 0.25 | no | the character went 19 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T195037Z-25-373-potions | potions | Tower Cellar Level 5 (25) | 17, most BloodClan (55) | 7.9 | 1479 | 216 | 0.15 (0.00 to 0.68) | 409 | 0.53 (0.00 to 2.46) | 6 | 7 | 1.17 | no (2 of 5 seeds) | the character died in the take at 7.9 s; 3 belt keys replayed on the assumed belt; assumed: hand; mostly not blows: 409 of the 1479 points the take lost have a suspect |
| 20261011T195037Z-25-493-death | death | Tower Cellar Level 5 (25) | 11, most DarkArcher (162) | 3.0 | 1108 | 487 | 0.44 (0.00 to 0.82) | 1108 | 0.44 (0.00 to 0.82) | 0 | 0 | 1.00 | no (1 of 5 seeds) | the character died in the take at 3.0 s; 1 belt keys replayed on the assumed belt; assumed: hand |
| 20261011T211725Z-22-1093-burst15 | burst15 | Tower Cellar Level 2 (22) | 4, most Ghost (38) | 8.0 | 339 | 0 | 0.00 (0.00 to 0.46) | 229 | 0.00 (0.00 to 0.69) | 4 | 3 | 0.75 | no (2 of 5 seeds) | the character went 25 units from where the scene has it; assumed: hand |
| 20261011T211818Z-23-535-long | long | Tower Cellar Level 3 (23) | 12, most Devilkin (21) | 8.0 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T211958Z-25-1-long | long | Tower Cellar Level 5 (25) | 19, most BloodClan (55) | 7.2 | 0 | 0 | - | 0 | - | 5 | 1 | 0.20 | no | a hostile the scene lacks is within 12 of the character at 7.3 s; the character went 59 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T212453Z-23-121-fixed | fixed | Tower Cellar Level 3 (23) | 5, most DarkArcher (162) | 3.0 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 3.1 s; the character went 79 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T212453Z-23-172-burst15 | burst15 | Tower Cellar Level 3 (23) | 8, most BloodClan (55) | 2.7 | 0 | 0 | - | 0 | - | 4 | 4 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 2.7 s; the character went 48 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T213803Z-23-123-fixed | fixed | Tower Cellar Level 3 (23) | 4, most Devilkin (21) | 0.4 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | the take ends or leaves the level at 0.4 s; assumed: hand; the take holds under 90 points of life lost: no ratio; compared for under 2 s |
| 20261011T214806Z-25-110-fixed | fixed | Tower Cellar Level 5 (25) | 10, most Devilkin (21) | 8.0 | 0 | 0 | - | 0 | - | 7 | 6 | 0.86 | no | the character went 44 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T220301Z-6-69-long | long | Black Marsh (6) | 31, most Carver (20) | 8.0 | 0 | 0 | - | 0 | - | 13 | 11 | 0.85 | no | the character went 24 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T220409Z-23-613-fixed | fixed | Tower Cellar Level 3 (23) | 22, most Devilkin (21) | 8.0 | 0 | 0 | - | 0 | - | 5 | 7 | 1.40 | no | the character went 105 units from where the scene has it; assumed: hand; the take holds under 90 points of life lost: no ratio |
| 20261011T222330Z-24-41-long | long | Tower Cellar Level 4 (24) | 8, most Devilkin (21) | 8.0 | 180 | 1196 | 6.64 (0.00 to 6.64) | 180 | 6.64 (0.00 to 6.64) | 6 | 4 | 0.67 | no | the character went 30 units from where the scene has it |
| 20261011T222624Z-25-57-long | long | Tower Cellar Level 5 (25) | 20, most Devilkin (21) | 8.0 | 48 | 0 | - | 48 | - | 0 | 0 | 1.00 | no | the character went 22 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T222901Z-22-124-fixed | fixed | Tower Cellar Level 2 (22) | 10, most Ghost (38) | 5.6 | 0 | 0 | - | 0 | - | 5 | 5 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 5.6 s; the character went 122 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T222923Z-23-115-stuck | stuck | Tower Cellar Level 3 (23) | 7, most Ghost (38) | 6.9 | 0 | 0 | - | 0 | - | 7 | 7 | 1.00 | no | the take ends or leaves the level at 6.9 s; the character went 35 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T222934Z-24-382-stuck | stuck | Tower Cellar Level 4 (24) | 12, most Devilkin (21) | 8.0 | 168 | 0 | 0.00 (0.00 to 0.00) | 0 | - | 12 | 10 | 0.83 | no | the character went 35 units from where the scene has it; mostly not blows: 0 of the 168 points the take lost have a suspect |
| 20261011T223004Z-25-192-stuck | stuck | Tower Cellar Level 5 (25) | 14, most Devilkin (21) | 8.0 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | the character went 18 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T223134Z-38-794-burst15 | burst15 | Tristram (38) | 15, most Returned (1) | 8.0 | 454 | 0 | 0.00 (0.00 to 0.58) | 454 | 0.00 (0.00 to 0.58) | 9 | 6 | 0.67 | no (1 of 5 seeds) | the character went 30 units from where the scene has it |
| 20261011T223134Z-38-817-stuck | stuck | Tristram (38) | 20, most Returned (1) | 8.0 | 454 | 0 | 0.00 (0.00 to 0.64) | 454 | 0.00 (0.00 to 0.64) | 9 | 4 | 0.44 | no | the character went 31 units from where the scene has it |
| 20261011T225311Z-38-622-stuck | stuck | Tristram (38) | 3, most SkeletonArcher (170) | 5.8 | 0 | 0 | - | 0 | - | 3 | 3 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 5.9 s; the character went 47 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T231204Z-38-164-stuck | stuck | Tristram (38) | 9, most Carver (20) | 8.0 | 0 | 0 | - | 0 | - | 5 | 5 | 1.00 | no | the take holds under 90 points of life lost: no ratio |
| 20261011T231408Z-39-134-stuck | stuck | Moo Moo Farm (39) | 66, most Hell Bovine (391) | 8.0 | 0 | 0 | - | 0 | - | 10 | 12 | 1.20 | no | the take holds under 90 points of life lost: no ratio |
| 20261011T231408Z-39-3182-burst15 | burst15 | Moo Moo Farm (39) | 13, most Hell Bovine (391) | 8.0 | 0 | 0 | - | 0 | - | 9 | 5 | 0.56 | no | the character went 43 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T231408Z-39-377-long | long | Moo Moo Farm (39) | 29, most Hell Bovine (391) | 6.3 | 0 | 0 | - | 0 | - | 21 | 9 | 0.43 | no | a hostile the scene lacks is within 12 of the character at 6.3 s; the character went 33 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T233544Z-3-2158-stuck | stuck | Cold Plains (3) | 7, most Fallen (19) | 6.4 | 0 | 0 | - | 0 | - | 6 | 5 | 0.83 | no | a hostile the scene lacks is within 12 of the character at 6.4 s; the character went 44 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T233544Z-3-3280-long | long | Cold Plains (3) | 31, most Fallen (19) | 8.0 | 0 | 0 | - | 0 | - | 18 | 19 | 1.06 | no | the character went 55 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T234014Z-9-197-stuck | stuck | Cave Level 1 (9) | 14, most HungryDead (6) | 8.0 | 0 | 0 | - | 0 | - | 7 | 5 | 0.71 | no | the take holds under 90 points of life lost: no ratio |
| 20261011T234425Z-13-121-fixed | fixed | Cave Level 2 (13) | 22, most HungryDead (6) | 8.0 | 0 | 0 | - | 0 | - | 7 | 4 | 0.57 | no | the character went 25 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261011T234425Z-13-954-stuck | stuck | Cave Level 2 (13) | 1, most HungryDead (6) | 8.0 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | the character went 57 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T061027Z-115-1803-stuck | stuck | Glacial Trail (115) | 11, most ReanimatedHorde (437) | 8.0 | 0 | 0 | - | 0 | - | 11 | 5 | 0.45 | no | the character went 63 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T061557Z-115-298-stuck | stuck | Glacial Trail (115) | 32, most BoneWarrior (648) | 8.0 | 0 | 0 | - | 0 | - | 9 | 15 | 1.67 | no | the character went 29 units from where the scene has it; assumed: level, mods, tier; the take holds under 90 points of life lost: no ratio |
| 20261012T063130Z-116-561-stuck | stuck | Drifter Cavern (116) | 2, most DarkArcher (614) | 8.0 | 0 | 0 | - | 0 | - | 2 | 2 | 1.00 | no | the character went 71 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T064056Z-6-242-stuck | stuck | Black Marsh (6) | 24, most Carver (20) | 8.0 | 0 | 0 | - | 0 | - | 12 | 14 | 1.17 | no | the character went 42 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T064056Z-6-326-long | long | Black Marsh (6) | 23, most Carver (20) | 8.0 | 0 | 0 | - | 0 | - | 12 | 17 | 1.42 | no | the character went 42 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T064210Z-129-354-burst15 | burst15 | The Worldstone Keep Level 2 (129) | 7, most BlackSoul (640) | 8.0 | 329 | 0 | 0.00 (0.00 to 0.20) | 329 | 0.00 (0.00 to 0.20) | 7 | 7 | 1.00 | no | the character went 46 units from where the scene has it |
| 20261012T064210Z-129-698-long | long | The Worldstone Keep Level 2 (129) | 20, most BlackSoul (640) | 8.0 | 0 | 74 | - | 0 | - | 12 | 8 | 0.67 | no | the character went 50 units from where the scene has it; assumed: full; the take holds under 90 points of life lost: no ratio |
| 20261012T064317Z-130-0-long | long | The Worldstone Keep Level 3 (130) | 1, most Baal Taunt (545) | 4.2 | 0 | 0 | - | 0 | - | 0 | 0 | 1.00 | no | a hostile the scene lacks is within 12 of the character at 4.2 s; the character went 39 units from where the scene has it; assumed: full, level, mods, tier; the take holds under 90 points of life lost: no ratio |
| 20261012T064317Z-130-662-stuck | stuck | The Worldstone Keep Level 3 (130) | 11, most Hell Temptress (472) | 8.0 | 0 | 0 | - | 0 | - | 4 | 4 | 1.00 | no | assumed: full, level, mods, tier; the take holds under 90 points of life lost: no ratio |
| 20261012T065226Z-130-0-long | long | The Worldstone Keep Level 3 (130) | 7, most Hell Temptress (472) | 8.0 | 86 | 0 | - | 86 | - | 4 | 3 | 0.75 | no | the character went 46 units from where the scene has it; assumed: full, level; the take holds under 90 points of life lost: no ratio |
| 20261012T065226Z-130-101-stuck | stuck | The Worldstone Keep Level 3 (130) | 7, most Hell Temptress (472) | 8.0 | 99 | 360 | 3.63 (0.00 to 8.85) | 99 | 3.63 (0.00 to 8.85) | 5 | 3 | 0.60 | no (1 of 5 seeds) | the character went 20 units from where the scene has it; assumed: full |
| 20261012T065226Z-130-4606-burst15 | burst15 | The Worldstone Keep Level 3 (130) | 16, most Hell Temptress (472) | 8.0 | 1937 | 95 | 0.05 (0.00 to 0.22) | 1829 | 0.05 (0.00 to 0.23) | 12 | 5 | 0.42 | no | 3 belt keys replayed on the assumed belt; the character went 20 units from where the scene has it; assumed: full |
| 20261012T065226Z-130-4609-potions | potions | The Worldstone Keep Level 3 (130) | 16, most Hell Temptress (472) | 8.0 | 1937 | 95 | 0.05 (0.00 to 0.22) | 1829 | 0.05 (0.00 to 0.23) | 12 | 5 | 0.42 | no | 3 belt keys replayed on the assumed belt; the character went 20 units from where the scene has it; assumed: full |
| 20261012T065226Z-130-4612-burst | burst | The Worldstone Keep Level 3 (130) | 16, most Hell Temptress (472) | 8.0 | 1937 | 95 | 0.05 (0.00 to 0.22) | 1829 | 0.05 (0.00 to 0.23) | 12 | 5 | 0.42 | no | 3 belt keys replayed on the assumed belt; the character went 20 units from where the scene has it; assumed: full |
| 20261012T165150Z-115-2826-stuck | stuck | Glacial Trail (115) | 23, most BoneWarrior (648) | 8.0 | 35 | 0 | - | 0 | - | 20 | 18 | 0.90 | no | the character went 42 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T165722Z-115-276-stuck | stuck | Glacial Trail (115) | 9, most Blood Lord1 (652) | 8.0 | 77 | 9 | - | 22 | - | 5 | 0 | 0.00 | no | the character went 14 units from where the scene has it; the take holds under 90 points of life lost: no ratio |
| 20261012T165857Z-115-2104-fixed | fixed | Glacial Trail (115) | 17, most Blood Lord1 (652) | 8.0 | 15 | 0 | - | 15 | - | 7 | 6 | 0.86 | no | the take holds under 90 points of life lost: no ratio |
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
| all | 112 | 0 | 28 | 0.00 | 0.00 | 0.05 | 0.81 | 7.29 | 0.47 | 4 | 91 | 0.73 | 0.68 |

| kind | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed | 40 | 0 | 2 | 0.00 | 1.82 | 3.64 | 5.46 | 7.29 | 5.41 | 4 | 33 | 0.69 | 0.67 |
| burst15 | 20 | 0 | 12 | 0.00 | 0.00 | 0.00 | 0.15 | 1.67 | 0.20 | 0 | 17 | 0.75 | 0.71 |
| long | 20 | 0 | 1 | 6.64 | 6.64 | 6.64 | 6.64 | 6.64 | 4.05 | 0 | 13 | 0.67 | 0.83 |
| stuck | 20 | 0 | 2 | 0.00 | 0.91 | 1.82 | 2.72 | 3.63 | 0.57 | 0 | 18 | 0.95 | 0.88 |
| potions | 7 | 0 | 6 | 0.00 | 0.03 | 0.29 | 0.73 | 1.32 | 0.28 | 0 | 6 | 0.56 | 0.42 |
| burst | 4 | 0 | 4 | 0.00 | 0.04 | 0.05 | 0.40 | 1.41 | 0.30 | 0 | 4 | 0.49 | 0.31 |
| death | 1 | 0 | 1 | 0.44 | 0.44 | 0.44 | 0.44 | 0.44 | 0.44 | 0 | 0 | - | - |

By the type most of the scene's hostiles are of:

| most hostiles | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Devilkin (21) | 26 | 0 | 4 | 0.00 | 0.00 | 0.41 | 2.28 | 6.64 | 1.20 | 1 | 19 | 0.77 | 0.68 |
| BloodClan (55) | 10 | 0 | 2 | 0.00 | 0.13 | 0.26 | 0.40 | 0.53 | 0.67 | 1 | 10 | 0.65 | 0.61 |
| DarkArcher (162) | 9 | 0 | 4 | 0.00 | 0.00 | 0.03 | 0.15 | 0.44 | 0.17 | 0 | 6 | 0.75 | 0.69 |
| IceSpawn (458) | 8 | 0 | 4 | 0.00 | 0.02 | 0.67 | 1.34 | 1.41 | 1.09 | 1 | 8 | 0.69 | 0.54 |
| Ghost (38) | 7 | 0 | 3 | 0.00 | 0.22 | 0.44 | 1.06 | 1.67 | 0.81 | 0 | 6 | 0.94 | 0.89 |
| Hell Temptress (472) | 7 | 0 | 4 | 0.05 | 0.05 | 0.05 | 0.95 | 3.63 | 0.11 | 0 | 6 | 0.51 | 0.51 |
| Carver (20) | 6 | 0 | 0 | - | - | - | - | - | - | 0 | 6 | 1.02 | 0.98 |
| DarkStalker (45) | 3 | 0 | 2 | 0.00 | 0.01 | 0.01 | 0.02 | 0.03 | 0.01 | 0 | 3 | 0.56 | 0.64 |
| Hell Bovine (391) | 3 | 0 | 0 | - | - | - | - | - | - | 0 | 3 | 0.56 | 0.65 |
| HungryDead (6) | 3 | 0 | 0 | - | - | - | - | - | - | 0 | 2 | 0.64 | 0.64 |
| Returned (1) | 3 | 0 | 2 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0 | 3 | 0.67 | 0.58 |
| Zealot (671) | 3 | 0 | 1 | 7.29 | 7.29 | 7.29 | 7.29 | 7.29 | 7.29 | 0 | 1 | 0.00 | 0.00 |
| BlackSoul (640) | 2 | 0 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.22 | 0 | 2 | 0.83 | 0.79 |
| Blood Lord1 (652) | 2 | 0 | 0 | - | - | - | - | - | 0.24 | 0 | 2 | 0.43 | 0.50 |
| BoneWarrior (648) | 2 | 0 | 0 | - | - | - | - | - | - | 0 | 2 | 1.28 | 1.14 |
| Fallen (19) | 2 | 0 | 0 | - | - | - | - | - | - | 0 | 2 | 0.94 | 1.00 |
| Baal Taunt (545) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| Baal Throne (543) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| BlackRaptor (17) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 0.44 | 0.44 |
| BloodHawk (16) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| BoneMage (624) | 1 | 0 | 0 | - | - | - | - | - | 0.00 | 0 | 1 | 0.75 | 0.75 |
| DarkArcher (614) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 1.00 | 1.00 |
| DarkOne (22) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 1.00 | 1.00 |
| Flayer (659) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| Ghoul (7) | 1 | 0 | 0 | - | - | - | - | - | - | 1 | 1 | 0.67 | 0.67 |
| HellClan (56) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 0.79 | 0.79 |
| NightClan (54) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| NightClan (586) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 1.00 | 1.00 |
| PitViper (595) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| ReanimatedHorde (437) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 0.45 | 0.45 |
| SkeletonArcher (170) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 1.00 | 1.00 |
| Slayerexp (682) | 1 | 0 | 1 | 0.80 | 0.80 | 0.80 | 0.80 | 0.80 | 0.80 | 0 | 1 | 0.65 | 0.65 |

### Raw

| all | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 112 | 0 | 30 | 0.00 | 0.00 | 0.05 | 0.70 | 7.29 | 0.40 | 3 | 91 | 0.73 | 0.68 |

| kind | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed | 40 | 0 | 3 | 0.00 | 0.60 | 1.20 | 4.24 | 7.29 | 3.52 | 3 | 33 | 0.69 | 0.67 |
| burst15 | 20 | 0 | 12 | 0.00 | 0.00 | 0.00 | 0.15 | 1.67 | 0.17 | 0 | 17 | 0.75 | 0.71 |
| long | 20 | 0 | 1 | 6.64 | 6.64 | 6.64 | 6.64 | 6.64 | 4.05 | 0 | 13 | 0.67 | 0.83 |
| stuck | 20 | 0 | 3 | 0.00 | 0.00 | 0.00 | 1.82 | 3.63 | 0.41 | 0 | 18 | 0.95 | 0.88 |
| potions | 7 | 0 | 6 | 0.00 | 0.03 | 0.10 | 0.55 | 0.71 | 0.21 | 0 | 6 | 0.56 | 0.42 |
| burst | 4 | 0 | 4 | 0.00 | 0.04 | 0.05 | 0.40 | 1.41 | 0.29 | 0 | 4 | 0.49 | 0.31 |
| death | 1 | 0 | 1 | 0.44 | 0.44 | 0.44 | 0.44 | 0.44 | 0.44 | 0 | 0 | - | - |

By the type most of the scene's hostiles are of:

| most hostiles | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Devilkin (21) | 26 | 0 | 5 | 0.00 | 0.00 | 0.00 | 0.82 | 6.64 | 1.06 | 1 | 19 | 0.77 | 0.68 |
| BloodClan (55) | 10 | 0 | 2 | 0.00 | 0.04 | 0.07 | 0.11 | 0.15 | 0.24 | 1 | 10 | 0.65 | 0.61 |
| DarkArcher (162) | 9 | 0 | 4 | 0.00 | 0.00 | 0.03 | 0.15 | 0.44 | 0.16 | 0 | 6 | 0.75 | 0.69 |
| IceSpawn (458) | 8 | 0 | 5 | 0.00 | 0.03 | 0.71 | 1.20 | 1.41 | 0.71 | 0 | 8 | 0.69 | 0.54 |
| Ghost (38) | 7 | 0 | 3 | 0.00 | 0.22 | 0.44 | 1.06 | 1.67 | 0.73 | 0 | 6 | 0.94 | 0.89 |
| Hell Temptress (472) | 7 | 0 | 4 | 0.05 | 0.05 | 0.05 | 0.94 | 3.63 | 0.11 | 0 | 6 | 0.51 | 0.51 |
| Carver (20) | 6 | 0 | 0 | - | - | - | - | - | - | 0 | 6 | 1.02 | 0.98 |
| DarkStalker (45) | 3 | 0 | 2 | 0.00 | 0.01 | 0.01 | 0.02 | 0.03 | 0.01 | 0 | 3 | 0.56 | 0.64 |
| Hell Bovine (391) | 3 | 0 | 0 | - | - | - | - | - | - | 0 | 3 | 0.56 | 0.65 |
| HungryDead (6) | 3 | 0 | 0 | - | - | - | - | - | - | 0 | 2 | 0.64 | 0.64 |
| Returned (1) | 3 | 0 | 2 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0 | 3 | 0.67 | 0.58 |
| Zealot (671) | 3 | 0 | 1 | 7.29 | 7.29 | 7.29 | 7.29 | 7.29 | 7.29 | 0 | 1 | 0.00 | 0.00 |
| BlackSoul (640) | 2 | 0 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.22 | 0 | 2 | 0.83 | 0.79 |
| Blood Lord1 (652) | 2 | 0 | 0 | - | - | - | - | - | 0.10 | 0 | 2 | 0.43 | 0.50 |
| BoneWarrior (648) | 2 | 0 | 0 | - | - | - | - | - | 0.00 | 0 | 2 | 1.28 | 1.14 |
| Fallen (19) | 2 | 0 | 0 | - | - | - | - | - | - | 0 | 2 | 0.94 | 1.00 |
| Baal Taunt (545) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| Baal Throne (543) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| BlackRaptor (17) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 0.44 | 0.44 |
| BloodHawk (16) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| BoneMage (624) | 1 | 0 | 0 | - | - | - | - | - | 0.00 | 0 | 1 | 0.75 | 0.75 |
| DarkArcher (614) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 1.00 | 1.00 |
| DarkOne (22) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 1.00 | 1.00 |
| Flayer (659) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| Ghoul (7) | 1 | 0 | 0 | - | - | - | - | - | 8.95 | 1 | 1 | 0.67 | 0.67 |
| HellClan (56) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 0.79 | 0.79 |
| NightClan (54) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 0 | - | - |
| NightClan (586) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 1.00 | 1.00 |
| PitViper (595) | 1 | 0 | 0 | - | - | - | - | - | 0.00 | 0 | 0 | - | - |
| ReanimatedHorde (437) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 0.45 | 0.45 |
| SkeletonArcher (170) | 1 | 0 | 0 | - | - | - | - | - | - | 0 | 1 | 1.00 | 1.00 |
| Slayerexp (682) | 1 | 0 | 1 | 0.69 | 0.69 | 0.69 | 0.69 | 0.69 | 0.69 | 0 | 1 | 0.65 | 0.65 |

The types with 3 scenes or more, by what the arena makes of them (like with like):

| most hostiles | scenes | trusted | with a ratio | least | quartile | median | quartile | most | pooled | arena hurt, take did not | kills: n | median | pooled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Zealot (671) | 3 | 0 | 1 | 7.29 | 7.29 | 7.29 | 7.29 | 7.29 | 7.29 | 0 | 1 | 0.00 | 0.00 |
| Devilkin (21) | 26 | 0 | 4 | 0.00 | 0.00 | 0.41 | 2.28 | 6.64 | 1.20 | 1 | 19 | 0.77 | 0.68 |
| IceSpawn (458) | 8 | 0 | 4 | 0.00 | 0.02 | 0.67 | 1.34 | 1.41 | 1.09 | 1 | 8 | 0.69 | 0.54 |
| Ghost (38) | 7 | 0 | 3 | 0.00 | 0.22 | 0.44 | 1.06 | 1.67 | 0.81 | 0 | 6 | 0.94 | 0.89 |
| BloodClan (55) | 10 | 0 | 2 | 0.00 | 0.13 | 0.26 | 0.40 | 0.53 | 0.67 | 1 | 10 | 0.65 | 0.61 |
| DarkArcher (162) | 9 | 0 | 4 | 0.00 | 0.00 | 0.03 | 0.15 | 0.44 | 0.17 | 0 | 6 | 0.75 | 0.69 |
| Hell Temptress (472) | 7 | 0 | 4 | 0.05 | 0.05 | 0.05 | 0.95 | 3.63 | 0.11 | 0 | 6 | 0.51 | 0.51 |
| DarkStalker (45) | 3 | 0 | 2 | 0.00 | 0.01 | 0.01 | 0.02 | 0.03 | 0.01 | 0 | 3 | 0.56 | 0.64 |
| Carver (20) | 6 | 0 | 0 | - | - | - | - | - | - | 0 | 6 | 1.02 | 0.98 |
| Hell Bovine (391) | 3 | 0 | 0 | - | - | - | - | - | - | 0 | 3 | 0.56 | 0.65 |
| HungryDead (6) | 3 | 0 | 0 | - | - | - | - | - | - | 0 | 2 | 0.64 | 0.64 |
| Returned (1) | 3 | 0 | 2 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0 | 3 | 0.67 | 0.58 |

## The big drops

| | drops of 300 or more | per 10,000 s | largest |
| --- | ---: | ---: | ---: |
| the takes, all | 15 | 206 | 1051 |
| the takes, with a suspect | 13 | 178 | 1051 |
| the arena, mean of 5 seeds | 4.8 | 66 | - |

The takes' by class: several 9, nova/explosion 3, unknown 2, sole ranged 1. The arena's by seed: 9, 3, 9, 3, 0. 730 s of windows; they were cut around bursts, potions and deaths, so the rate is far above a whole take's (20 in 19,097 s).

## The blows, by who struck

Over the compared windows, first seed. An arena blow is one strike, shot or spark after the
resistances of the set in hand. A drop of the take is the life gone between two samples (several
blows landing together are one drop); it is put on a type only when one monster alone was striking
(`takes/hurts.py` `sole`), so the take's rows by type are a part of its drops: the last row has all,
the drops nobody is blamed for among them.

| striker | arena: kind | blows | median | points | take: drops put on it | median | points |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| IceSpawn (458) | melee | 36 | 37 | 2193 | 1 | 13 | 13 |
| Zealot (671) | melee | 6 | 185 | 1767 | 1 | 67 | 67 |
| DarkStalker (45) | melee | 9 | 67 | 1249 | 0 | - | 0 |
| Devilkin (21) | nova | 1 | 1196 | 1196 | 0 | - | 0 |
| BloodClan (55) | melee | 7 | 72 | 555 | 1 | 210 | 210 |
| Slayerexp (682) | melee | 6 | 17 | 411 | 1 | 23 | 23 |
| Hell Temptress (472) | nova | 1 | 360 | 360 | 0 | - | 0 |
| Ghoul (7) | melee | 1 | 331 | 331 | 0 | - | 0 |
| Hell Temptress (472) | shot | 3 | 97 | 290 | 0 | - | 0 |
| DarkArcher (162) | nova | 1 | 177 | 177 | 3 | 98 | 203 |
| Ghost (38) | nova | 1 | 157 | 157 | 0 | - | 0 |
| NightMarauder (295) | melee | 1 | 115 | 115 | 0 | - | 0 |
| Arach (685) | melee | 2 | 52 | 105 | 0 | - | 0 |
| Ghost (38) | melee | 1 | 51 | 51 | 0 | - | 0 |
| BlackSoul (640) | shot | 1 | 37 | 37 | 0 | - | 0 |
| BoneMage (624) | shot | 1 | 9 | 9 | 0 | - | 0 |
| DarkArcher (162) | shot | 1 | 5 | 5 | 0 | - | 0 |
| ReturnedArcher (578) | shot | 1 | 3 | 3 | 0 | - | 0 |
| Devilkin (21) | melee | 1 | 3 | 3 | 0 | - | 0 |
| Nihlathak (526) | melee | 3 | 0 | 0 | 0 | - | 0 |
| Returned (1) | - | 0 | - | 0 | 2 | 157 | 314 |
| every melee | melee | 73 | 51 | 6781 | - | - | - |
| every nova | nova | 4 | 268 | 1890 | - | - | - |
| every shot | shot | 7 | 37 | 344 | - | - | - |
| all, 730 s of 112 scenes | | 84 | 55 | 9014 | 140 | 114 | 20829 |

## The window

Each scene played for 15 s without leaving at the first stranger (a hostile the scene does not
hold within 12 units of the recorded character). "Still recorded": the take is in the
level and the character alive.

| seconds | scenes still recorded | of them no stranger yet | of those, the take lost enough | median units a monster is from its recording | hostiles within 12: take | arena |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 110 | 100 | 6 | 4.2 | 1.8 | 2.3 |
| 4 | 107 | 89 | 26 | 5.7 | 1.7 | 2.3 |
| 6 | 102 | 84 | 29 | 5.8 | 1.3 | 2.2 |
| 8 | 99 | 73 | 25 | 8.7 | 0.7 | 2.5 |
| 10 | 95 | 57 | 26 | 10.6 | 0.4 | 2.8 |
| 12 | 92 | 46 | 21 | 9.1 | 0.7 | 3.3 |
| 15 | 84 | 36 | 15 | 17.0 | 0.6 | 3.8 |

## The death: 20261011T195037Z-25-493-death

| seconds | life in the take | life in the arena (seed 1) | hostiles within 12 in the arena |
| ---: | ---: | ---: | ---: |
| 0.00 | 995 | 995 | 3 |
| 0.48 | 1018 | 995 | 3 |
| 1.00 | 1029 | 995 | 3 |
| 1.52 | 972 | 864 | 3 |
| 2.00 | 1006 | 879 | 3 |
| 2.48 | 1029 | 894 | 3 |
| 3.00 | 1051 | 564 | 3 |
| 3.04 | 0 | 565 | 3 |

- drops in the take: 57 at 1.12 s, 1051 at 3.00 s
- blows in the arena, before an aura: 72 at 1.36 s (BloodClan (55), melee), 173 at 2.76 s (BloodClan (55), melee), 30 at 3.00 s (BloodClan (55), melee)
- belt keys: column 4 at 1.16 s

## One factor on every blow

Of the 28 scenes with a ratio, the 11 where the arena took nothing are left out (no factor moves them); the rest are split in two by every other name. The median ratio of
the 9 scenes fitted on is 0.53: a factor of **1.90** on every blow would centre it. Played again with it (`play`, `damage_scale`; first seed; "trusted" here is the bare rule of
the two ratios):

| half | scenes | median before | median with the factor | trusted before | trusted with the factor | least | most |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fitted on | 9 | 0.53 | 1.01 | 2 | 1 | 0.05 | 11.12 |
| checked on | 8 | 0.62 | 1.18 | 1 | 3 | 0.10 | 6.89 |
