# town.py — history and evidence (moved out of the code, 2026-10-19)

## Why the stash stop is planned
The player, 2026-10-18 12:55: "when we're putting items to shared stash, we just brute forcing each tab, despite we
could exactly know where we can put items"; "we visit the stash only ONE time". The stash is read from memory in town
(game/records.py `StashView`), so every put is planned before a click. Migration step 1 was the stash stop; step 3 added
TRADE_ROOM, `sold_full`, `surplus`, `deposit_to`, `tops_up` and `contract` (macros/town-plan.md).

## TRADE_ROOM = 8
The player, 2026-10-17: "we need to perform mass identify at decard cain -> stash good -> sell junk -> return to loop";
then "probably we need to trade not by 2 junk items, but by remaining free slots". Before, the trigger counted items
(3 then 4 to Cain, 2 then 3 to Jamella): Cain nearly every game for one item, the trade ~6.8 s a cycle (12:00-12:30 on
2026-10-17). 8 cells: a 2 x 4 shield, the largest candidate, fits nowhere below it.

## GEMS_A_KIND = 3, GEMS_KEPT = 6
The player, 09:51 on 2026-10-18: "we don't need to do gem sale until we have 99 pgems of type and we must cube them up
first". Kept with no bound, all seven kinds full, the gems filled the cube: no transmute had room to empty it, a trade
session every game, then the loop stood by a Flawless Sapphire and a Grand Charm with no room (09:22-09:45).

## PARK_JUNK
The player, 16:50 on 2026-10-18: "junk can be temporarily stored in stash, but sold after". A set Battle Boots (2 x 2)
stayed in the cube three visits (16:30-16:35) behind a junk unique Fuscina (2 x 4); the same at 15:06, 15:14, 15:20.

## Moves aside (`_make_way`)
At 14:28 on 2026-10-18 a unique Embossed Plate (2 x 3) stayed in the cube: the inventory's one 2 x 3 held a set Amulet
judged junk, and the plan gave the plate no put (rca/2026-10-18/town-remaining-findings.md §1). Stranded keepers:
15:05:53 on 2026-10-18.

## RUNES_AIM = 80, RUNE_TRANSMUTES = 3
The player, 17:50 on 2026-10-18: "cubed, aim to 80 or lower" (Tal Rune at 99 since 2026-10-17); 18:31: "yes, loop
should use required gems + runes". The gem transmute's log lines (`Macro: cube: three ...`, 12 of 2026-10-18
04:53-09:13) came 1.9 to 4.0 s after the stash stop's line, 2.8 s median, inventory and cube opened each time; the rune
transmute stays in the open stash (right click, the button, Ctrl + Shift + click): 3 a visit is at most ~8 s, likely
~5 s, and takes 9 runes off, so a 99 stack is at 80 within three visits, while the loop brings fewer than one rune of a
kind a visit (10 Tal, 19 Ort in 122 visits on 10-18). Pul and up take two runes: not handled.

## sold_full
A Flawless Amethyst whose stack was full was left on the ground twice: "we just left flawlest amethyst and left the
game. something is wrong" (15:19 on 2026-10-17). Materials: the player, 10:37 on 2026-10-18: "essensies are stacking to
99, when we have full stash cell - just stop picking it up, there is no use for it".

## tops_up
One top-up done at a game's start sent the loop to Halbu again at the game's end for 5 charges, ~8 s (15:48:43 on
2026-10-17).

## named
14:28:27 on 2026-10-18 the log said "1 keepers carried" without naming which.
