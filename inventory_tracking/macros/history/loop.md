# loop.py — design history and the evidence behind its numbers

Moved out of the code comments in the 2026-10-19 cleanup (phase 4). Rulings keep their quote in the code.

## Shape
- The KP_6 loop plays one `Kind`: Lower Kurast chests (routes/lower-kurast-loop-plan.md phase 4), then Andariel
  (the player, 2026-10-18: "I want to build andariel loop that will be similar to lower kurast loop, we're going to
  use the same KP_6 run start/stop it"), then the terror zone kinds (the player, 2026-10-19 ~02:12: "we're going to
  have separate mods: - full clear tz : for herald hunting - tz leveling: clear only elites/champs").
- Games end in act 4 (portal → Kurast Docks → waypoint → Pandemonium Fortress → Save and Exit), where the next game
  starts by its waypoint (the player, 2026-10-16).
- Recover, never stop (the player, 2026-10-17: "we should try to not stuck in some weird situation without being able
  to fix it from agent"; 2026-10-18: "how to setup the loop in the way that would fully prevent us from stopping").
  On 2026-10-17 ten stops of "Save and Exit again and again" stood the loop 200 min until someone looked.
- The town visit replaced four legs (identify, stash, scrolls and keys, the staff's charges) that walked back and forth
  (the player, 2026-10-18 12:55: "we visit the stash only ONE time, no running back and forward"; macros/town-plan.md
  step 3). The player, 15:52 on 2026-10-17: "when we get to maintenance (refilling, trading, repairing) - it is better
  to identify everything, stash good, sell junk, refill, optionally repair ... right now we're running between
  vendors/stash/waypoint with items that could be already 10 times sold".
- Kind metrics (the player, 2026-10-19 ~02:12): "every loop has it's own metric, that it must optimize: boss
  kills/elites kill/opened chest. the only thing that has more priority - proper interactions with drops".

## Numbers
- TRIPS_A_GAME = 3: two trips in one game were needed once in 173 cycles (2026-10-18); a trip is ~37 s of a 240 s
  game. A trip whose visit can take nothing away (the player's charms, 13:38:17) is not repeated.
- DROPS_LAND = 2.0: Andariel's drops land through her death animation (mode 0, 1.55 s in the takes of 11:39-11:48 on
  2026-10-18), the last 1.7 s after the kill; her fight's run ends 0.4 s or more after it. Four games of 19 left
  0.5-0.8 s after the kill (11:41:52, 11:51:39, 11:52:14).
- DROPS_AFTER_KILL = 1.9: from KILLED_AT (the probe sees a death start within 0.25 s). Timed from the first loot leg
  instead, every game waited 2 s, her pack's fight included (13:21 on 2026-10-18). The fight's clock starts at the
  PICK_UP leg: at the fight leg it let the game be left 0.05 s into the loot (13:02:58).
- STILL_SECONDS = 45: the level run stood by a Flawless Diamond with the inventory full from 01:15:03 on 2026-10-17.
  `still` counts afresh per game: the stand of a recovery's pause carried into the next game, left 5 s in, then again
  (09:22:44-09:23:50 on 2026-10-19: 5 recoveries in a row).
- BESET_*: 09:36:41-09:37:11 on 2026-10-19 the recovery's pause stood 30 s at the Frozen River door / Crystalline
  Passage among three hostiles, life 3119 -> 2334, until the player struck them ("we stood still while under attack
  and almost died, only user intervented and helped to kill attackers ... we must not die or we lose exp and our
  gear"); a hit there was 130-260 life (4-8 %). Since then the pause is stood only in the lobby or a town.
- TELEPORT_ON/OFF = 0.35/0.15 of the gold cap: 0.6/0.3 left Teleport off for long stretches; a session's sales
  (~40-100k) pay less than its repairs (~85k). Off under 15 % (141,000 at level 94: a full repair, ~118,000, is still
  paid). With charges, ~7 a cycle (~11,900 gold), it spends about twice what sales bring. Restarts began it off: at
  527,000-588,000 carried 12 of 24 stays were made without it, 32.9 s against 26.0 (16:40-16:50 on 2026-10-17).

## Incidents behind the rules
- `count` by the game just left: counted all in one, the third game after KP_6 stopped the loop ("next game again and
  again in the lobby", 20:55:43 and 21:05:53 on 2026-10-16). Names come round (cyber99 -> cyber1): the second cyber81
  of a session started with the first's count (09:19:49 on 2026-10-18). Afresh after the Abort: a count left over the
  limit gave 4 recoveries in 20 ms (18:55:33-34 on 2026-10-18).
- A loading game is waited for: three recoveries in 20 ms from "not in a game" stopped the loop (12:45:41, 2026-10-17).
- Loose items (unidentified, runes, gems) are the loop's: after the player sorted game 28's items by hand, Antlers, a
  Ring, two runes and a Flawless Topaz read as the player's took the room for a Grand Charm (10:28, 2026-10-18).
- `printed` by unit id: the Gheed's swap at 06:02 on 2026-10-19 put a new charm of its class in its cell.
- The loop's items stay the loop's across restarts (the player, 2026-10-16: "moving items to the cube from inventory -
  seems not working. or working not always").
- Full stacks (the player, 2026-10-17: "we have 99 tal runes and cannot add more. probably we better just sell them (and
  other runes that will have 99)"). Full gem stacks sent the loop to a session every game (07:05-07:07, 2026-10-18);
  without the transmute count the kept gems filled cube and inventory with no session (09:43-10:22, 2026-10-18).
- Fragmented cube room ('.#./.#./.#./...': 9 cells) left a Rage Mask (12:44-12:45, 2026-10-17).
- `make_room` only between visits: in one it moved the session's junk into the cube (13:03, 2026-10-17).
- A restart's first leg in the Rogue Encampment went to the Catacombs with the inventory full (10:21:28, 2026-10-18):
  the room is counted at the first look.
- The Encampment's prebuff: Kashya, Warriv and Cain stand at the start and Consume cannot take them (three tries and the
  game left, 10:20:17, 2026-10-18). Consume in town (the player, 10:58: "consume buff grants +run/walk speed and make
  things faster in town, so, probably we should keep it up in town too").
- `begin_trip`: a Fortress reached before it is not its (11:56:48, 2026-10-18), nor the swap's way back (13:59:45), nor
  the game's first visit (12:36).
- The swap's `forget`: at 13:57:50 on 2026-10-18 the new charm (the same unit) was never tried, the run stood 45 s by it
  (rca/2026-10-18/loop-robustness-findings.md §2.3).
- Gheed's swap ruling (the player, 2026-10-18 13:39): "go to town; put our own gheed into SHARED tab; go back and pick
  new one; go to town, identify; check what is better (magic find roll); keep in own inventory better one".
