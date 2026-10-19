# macros/pickup.py — design notes and evidence moved out of the module (phase 4 cleanup, 2026-10-19)

## The step's order (user, 2026-10-10: one thing that is not fighting, the first that applies)

1. A valuable on the ground: every rune, what the loot marks point at (materials with the keys and essences,
   bases of expensive uniques; loot/ground.py), and the equipment the loot filter shows (unique and set items, and
   the smaller rare, magic and white ones, with what a Warlock uses; loot/shown.py), the nearest first. Then a gold
   pile of `pickup_gold_minimum` or more within one jump: a Blade Warp onto it, and a click if that did not take it.
2. A super healing or full rejuvenation potion near the character when the belt is missing one of its kind
   (tracking/belt.py `column_shortages`: a column holds what its lowest potion is, an empty one what it last held
   this game (`Loot.columns`), or config.BELT's layout, else rejuvenation).
3. With the belt full, life missing and such a potion near: one of the same kind is drunk from the belt and the
   one on the ground picked up in its place.
4. Nothing of those: the press is hunt.Hunter.step (the sweep with hostiles near, else a seek step).

During attack mode a press with something to pick up stops the fight for it at once (hunt.Hunter.asked_step;
since 2026-10-11 for gold and potions as for valuables); with nothing to pick up it asks the fight for a better
stand.

On the host (2026-10-10): the drops, their positions and the life read right, and a click on the item itself
picks it up with Show Items on. UNCONFIRMED then: the belt cell of a belt item (its path x, as tracking/state.py
reads it), and what the hover record holds with nothing under the pointer.

## Evidence behind the tuned numbers and rules

- FETCH_HOPS 16: HOPS left a Flawless Topaz 92 units short twice from 182 away, and the loop stopped
  (13:15:35-13:16:00 on 2026-10-18).
- DRINK_SECONDS / DRINK_TAPS: Frigid Highlands, 03:00:04 on 2026-10-11, the key went out 0.3 s after a teleport,
  the belt stayed full, and six clicks on two potions picked nothing up (6.4 s); the next press, the belt one short
  by then, took the potion in 0.44 s.
- ITEM_AIMS: the first host presses (18:41 on 2026-10-10, a Large Charm) clicked at 0, -10 and +10 down: the
  character walked to spots 9 to 21 pixels below the item and picked nothing up, so a click lands about 14 pixels
  lower than `ground_fraction` says. With the raised aims four of four items were picked up (18:46 to 18:54). In
  every log up to 2026-10-11 the first click with the item under the pointer took it 101 of 111 times at 24 px up,
  87 of 130 at 14 px (none of 21 at 6); an aim on the label's lower edge walks the character to the ground behind
  it (an Eth Rune in the Tower, 16:53:14: two such clicks ran 17 units past it).
- LOOK_AIMS: of the 71 pickups from 17:20 to 19:11 on 2026-10-11 that ended on a label seen, 62 had it 24 px up,
  5 at 54, 2 at 34, 1 at 14 and 1 at (-10, -14): in a pile the next label sits 30 px higher. A Sol Rune among three
  potions and another rune (Tower Cellar 5, 19:38:29) had its label at 44, the fifteenth aim, after a walk past it.
- PILE_AIMS never clicked blind: a press clicked whatever lay at the first aims and took a full rejuvenation with the
  belt full of them (host, 21:10 on 2026-10-10).
- PILE_DROPS / pile_aims: a Flawless Diamond among 12 drops showed at none of the 16 aims, four presses running
  (Arcane Sanctuary, 16:03:45 to 16:04:06 on 2026-10-11); the player took it by hand.
- SHUN_MISS: four presses went to that diamond while gold and a rune lay beside it.
- MISSED_AIMS / SHUN_SECONDS: Worldstone Keep 3, 22:16 on 2026-10-10: a Large Charm under the pointer at 16 aims,
  30 clicks in 21 s picked nothing up (cause unknown, no take recorded).
- CLICKED / LATE_SECONDS: a magic Jewel left the ground ~0.25 s after its wait (02:10:14.70-14.95 on 2026-10-18)
  and the watch called it missed.
- Refused (Gheed's Fortune carry-one): the player, 2026-10-18 13:41: "you cannot pickup another gheed if you have
  another in inventory/private tab". Before, two more aims, two trips back and a stop (13:34:48.1-13:34:53.8), or
  the 45 s stand of a level run that gave the charm up (13:56:41-13:57:26).
- Far drops looked at before blind clicks: Tower Cellar 4, 23:11 on 2026-10-10: a Grand Charm 16 away showed at none
  of 16 aims (2.4 s), the first blind click had a corpse under it, and from 2 away the next aim took it.
- A click that walked the character breaks the aim's clicks: a second click there walked 8 units further off (the
  Eth Rune).
- Gold: landing on a pile has not taken one yet (7210 at 13:30:30 and 5283 at 13:43:43 on 2026-10-11, the character
  0.7 from it); a click on that ground walked 1.2 more, the pile still there (user: "bad coordinates"), so the pile
  is clicked where the game says it is under the pointer.
- A pile is no stop of the press: the loop left Lower Kurast by Save and Exit for 5024 gold "not in view" 24 units
  off (18:26:19 on 2026-10-17), and its next game began in act 3.
- `standing`: Black Marsh, 01:13 on 2026-10-11: a shard 14 away took 6 s, the character sent 18 units past it and
  back; a ring was passed twice (both under a walk of attack mode's). A click under a cast is swallowed: three of the
  sweep's pickups on 2026-10-11, 14:51 to 14:54, the first click took nothing with the item under the pointer.
- `worth_a_stop`: Tower Cellar, 17:35:18 on 2026-10-11: the sweep had stopped for a Ring 29 away, a teleport step
  cancelled that pickup 30 ms later, and two more steps left the level (user: "we have missed more important unique
  and moved away").
- Dead check in `click`: Tower Cellar 5, 22:51:00 on 2026-10-11: the clicks went on 4.7 s over the body.
- Potions not taken, logged: Chaos Sanctuary, 00:10:21 on 2026-10-13: short 8 and 5, three healing potions,
  "nothing to pick up". Said to the player: three super healing potions with full healing columns read as a failed
  pickup (13:47:09 on 2026-10-11).
- Full inventory stop: going on to the seek step would teleport away from the drop (user, 2026-10-10 night). For gear
  the filter shows the press goes on (user, 2026-10-12: "allow moving when the item isn't very valuable"; Drifter
  Cavern, 20:00: 37 presses in a row stopped for a Superior Old Book). A shown unique/set is prized (2026-10-14,
  run-1214-findings.md §3.1). In the loop the plain valuables hold too (the player, 2026-10-18 17:50: "we should stop
  and clear inventory with our designated town routine"); step 4 of rca/2026-10-18/arch-level-behaviour.md.
- `alike` needs room: a Rare Horned Helm with no room lay beside an Ith Rune (Tower Cellar 5, 19:03:28 on
  2026-10-11): clicked four times, 3.5 s, before the rune's label was found.
- A pile of valuables is one press: the Tower, 16:53 and 16:55 on 2026-10-11, two runes and then three within 5
  units took a press each, with attack mode back on in between.
- `approach` hop fallback: rca/2026-10-13/run-2110-findings.md §2.3 (an Amn Rune 24 away left twice with "the
  Teleport staff has no charges left"); clear line: rca/2026-10-14/run-0025-findings.md §2.2 (a drop 17 away across
  lava is 43 by walking), run-1214-findings.md §3.2 (18 away round a wall corner never walked to).
