# The KP_6 loop's improvement journal

The state of the continuous improvement loop (`.agents/skills/d2-loop-watch/SKILL.md`): what the loop does now, how
fast it goes, what is queued, what waits for the player. Read it first when a watch is started or resumed. Update it at
the end of every round. The design and its phases are in the plans: [Lower Kurast](../routes/lower-kurast-loop-plan.md),
[Andariel](../routes/andariel-loop-plan.md), [TZ leveling](../routes/tz-leveling-loop-plan.md); the loop's code is
[loop.py](loop.py) (the [framework guide](README.md), KP_6); studies are in `rca/<date>/`. Moved here from
`inventory_tracking/routes/lower-kurast-loop-journal.md` on 2026-10-20 (the player: "move ... somewhere into more
proper place and backlink it properly").

## Baseline

**The measure is chests an hour of play** (`tools/speed.py`'s YIELD). Game seconds come from `tools/games.py`:
from one `next game` leg to the next, Save and Exit included; games a recovery left or the player paused are not
counted. The baseline window for `--against` is the newest row marked **baseline**.

| Window (local) | Code | Games | Chests an hour | Game median / p90 s | Chests leg s | Chests a stay (median) | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-10-16 22:50–23:07 | 65cfebc | 18 | – | 52.3 / 67.9 | 27.7 | – | before the stash and repair legs |
| 2026-10-17 02:43–04:31 | + uncommitted | 116 | **280** | 51.4 / 80 | 25.1 | 3 | baseline until 2026-10-18: strike rules, CHEST_BRINGS 0.1 |
| 2026-10-17 04:34–06:50 | + uncommitted | 135 | 280 (±26) | 59.1 / 83 | 32.8 | 4 | longer games, more chests a stay: same yield |
| 2026-10-17 06:51–09:44 | + uncommitted | 179 | 271 (−35..+18) | 55.8 / 79 | 26–31 | | no evidence of a change |
| 2026-10-17 19:45–20:08 | + uncommitted | 26 | 291 (cycles 288; +14, −31..+63) | 47.4 / – | 22.8 | 3 | open at the chest among idle hostiles; Teleport on in all 26 |
| 2026-10-17 20:23–20:47 | + uncommitted | 30 | 296 (cycles 288; +10, −44..+71) | 42.2 / – | 18.0 | 3 | no open across a wall; Teleport on 14 stays, off 15 |
| 2026-10-18 01:14–01:44 | + uncommitted | 46 | **422** (cycles 397; +121, +48..+191 against 20:23) | 36.1 / – | 10.6 | 4 | **baseline**: Enigma, Teleport before Blade Warp, CTA at the arrival; 18.2 chests a minute on the level |
| 2026-10-18 02:01–02:42 | + uncommitted | 70 | 403 (cycles 405; −27, −90..+31: no evidence) | 33.5 / 44.5 | 8.4 | – | one swap back, keys to 24, route chest cap, late pickups; game −2.8 s and chests leg −2.2 s (both better) |

Rates: 60–65 games an hour; 3 waypoint recoveries in 4 h (06:50, 08:13, 09:43), no stop that left loot.

Where a stay's time goes (04:34–06:50, 135 stays, `speed.py`): a stay 34.6 s, made of standing 23.4 s, casting 9.4 s,
moving 1.9 s, and 1.8 s after the last container. 4.7 chests and 3.1 other containers a stay, 8.1 chests a minute
on the level. 18.3 s a stay are lost against Blade Warp's pace (21 u/s) over the straight lines.

## Queue (no ruling needed), most valuable first

- (2026-10-18 03:22) Every key top-up since the BUY_MOST fix goes 12, a click that buys nothing ("still 12"), 15-16, a
  click that buys nothing ("still 16"), 24: two misses of BOUGHT_SECONDS 1.5 s each, ~3 s a trade session (~0.3 s a
  game). Measure how soon a key purchase shows in the count; a shorter wait for keys, or why the click after a full
  stack buys nothing.

- (2026-10-18 02:10) A false MISSED: a magic Jewel at (5382, 3219) "still on the ground after the click" (02:10:14.70),
  gone from the ground reads at ~02:10:14.95 with the character beside it, identified and sold from the inventory at
  02:11:33-45 (no other Jewel picked up between). The pickup's check window ended before the item left the ground.
  Done 02:16: `pickup.CLICKED`/`late`: a valuable clicked and not seen to go, found in the character's grids within
  LATE_SECONDS 5 of the click, is logged "picked up X ...s after the click, late" (the watch's PICKED). Test: test_pickup.
- Wide suite after this hour's changes (macros, combat, builds, scenarios, appraisal): 4652 passed, 86 xfailed.
- 02:18-02:28, 17 games: median 32.5 s, chests 7.6 s, no recovery, no MISSED. A one-off "portals 0" in the trade
  report at 02:20:11.6 (the shop read 20 at 11.56; Town Portal cast at 02:20:34): a read as the shop closed, not acted on.
- 02:18-03:04, 76 games: no recovery. 03:04:16-17 a MISSED: the last chest opened at 16.28, the run ended at 16.43,
  the pickup found nothing, Town Portal cast at 16.57; a Chipped Ruby landed at 17.10 and the portal was gone through at
  17.75. `portal.to_town(..., first)`: the loop's pickup made at the open portal, again while it picks something up
  (PICKS_AT_PORTAL 4), before the click. Test: test_portal. A "Shop check failed" (ownership/page mismatch) at
  02:59:40 is the stock scan read mid-sale, retried clean 2 s later; 10 such in the logs since 2026-10-17.
- 03:05-04:06, 95 games: 383 chests an hour of play against 431 at 01:14-01:44 (no evidence), game 35.7 s (same),
  chests leg 10.3 s (same). The yield's dip is the maps': chests opened a game equal the level guide's Super chests
  marks a game in every session (4.5 and 4.69 before 01:36; 4.0 and 4.03 since; the one short game, 64 at 03:46, had its
  third chest opened by a click whose act expired, then noted operated). No "not opened in 8 tries", no "none here".
  A recovery at 04:06:56: Consume showed nothing twice in town (a unit crowding the Defiler), "not seen 3 times over",
  the game left (~15 s); 5 such since 2026-10-17.
- 04:30:31-04:31:00: the Flawless Ruby and Flawless Sapphire stash stacks full (99); the gems are kept, never sold
  (`Loop.sold_full`: runes only), so they stay in the cube and the inventory ("trade session done (short of the
  contract): cube 4 items"), and each stash visit tries them again. The player's ruling of 2026-10-17 ("cube 3 flawless
  -> perfect") built: `cube.transmute(run, key, txt)`: the cube emptied of all else, three of the gems in, its units
  read back as exactly those three, then Transmute (`horadriccubelayouthd.json` "convert" at (520, 969) of the left
  panel, clicked 35 units in), then one perfect gem of the kind must be all it holds; `perfect_of` by the metadata's
  names. The runner calls it after each stash visit for every full flawless class, up to TRANSMUTES 3. The stash's
  "sold at Jamella from now on" line now says only "stack is full". Tests: test_cube (fakes model the button).
  Restarted 04:35:41. Live 04:39:59: "cube: three Flawless Ruby into a Perfect Ruby" (the button's place right).
  The same session kept a set Ring the appraisal called vendor (`junk.JUNK_QUALITIES`: magic, rare, white only).
- 04:47:00-29: each stash visit tried the full stacks' gems again (out of the cube, refused, back in: ~5 s a visit, two
  visits a session). `stash_loot`: at a game's second visit the full gem stacks' items are passed as `keep` (they stay
  where they are); the first visit still tries them (the player may have cubed some by hand). Runes as before (out of
  the cube, for Jamella).
- Transmutes live: 04:39:59 and 04:53:13 a Perfect Ruby, 05:08:18 a Perfect Sapphire; at 04:52:58 one was not
  made (no room to empty the cube of a junk charm) and was made after the sales.
- 05:25:08 a recovery: a Doom Ape killed on the Town Portal's spot (5210.5, 2813.5) 0.5 s before its click lay under
  the three aims down the portal's middle ("town is not under the pointer at any aim"); the game was left and the next
  began in act 3 (~27 s). The first such in the logs. `teleport.PORTAL_AIMS`: the middle, then the box's top
  (0, -95) and its sides (+-30, -60 / -25), for PORTAL and TOWN_PORTAL. Test: test_portal (red without the change).
  The same game's third Super chest was not skipped: it opened at 313065.4 during the fight with the apes (a click
  that took), and the route saw it operated.
- 05:46:05 a Perfect Amethyst, 06:02:44 a Perfect Ruby (after the sales made room: the first try at 06:02:22 found
  a junk charm in the cube and no room). Four flawless stacks full now (Amethyst, Sapphire, Ruby, Diamond).
- 06:08:50-55: the first stash visit tried each of seven full-stack gems (~1.3 s each). `stash.unload`: a kind
  refused once in a visit is not tried again in it (one try a kind). Test: test_stash (red without the change).
- 07:03-07:07: ten full-stack flawless gems (five kinds, two each) filled the cube; the room read low every game and
  a session ran every game (07:05:21, 07:06:35), each leaving it as low (~30 s a game). `Loop.carrying` leaves out the
  full gem stacks' gems (`full - sold_full`): a room-low session only with something it can take away (junk, the
  unidentified, what the stash takes); keys and scrolls send the loop as before. Test: test_loop (red without it).
  The stash's page grid read for a later move of such gems to a page (`bankexpansionlayouthd.json`: 10 x 10 at
  (89, 219) of the left panel); not built: the pages' free cells are not read, and a click on a taken one swaps.


0. (14:15; the settle and PROBE_WAIT part done 14:36) **Arrival probes cost about 1 s a game in swaps back.** `routines.took_input` swaps until the hands change,
   then swaps back: Lower Kurast takes input 3.5 s after arrival (3.41–3.66, 579 arrivals; the press at about 3.0 never
   takes), Kurast Docks 1.35 s, Pandemonium Fortress 2.1 s; each swap back is about 0.3 s. Candidate: in Pandemonium
   Fortress at a game's end, probe with Escape until the quit menu shows (`leave_game` already skips its Escape when
   the menu is open), so neither swap is made; Kurast Docks: the waypoint click retried until the panel opens
   (movement-findings §4 #2). The legs before and after (trade sessions in the fortress) must keep a probe.
0c. (14:40) **The second shop window for cube junk**: a 1×3 Blade could not come out of the cube with 1 inventory
   cell free until the other junk was sold, so the loop closed, took it out, and reopened Jamella (about 4–5 s,
   14:38:45–58). Ideas: take out what fits first and re-plan after the sales; or sell in the window, then take out.
0d. (16:47) **Goal ping-pong with Teleport between a shack's weapon rack and its super chest** (16:45:24–16:46:17,
   a 77.6 s stay, 382 units): Teleport toward the rack ("0 left after this"), the next look the chest at (5060, 2492),
   then the rack again, landing twice on (5077.5, 2496.5), never within opening reach; 36 Teleport keys, 15 landings,
   25 swaps, 11 retreats ("no progress act fits the life budget", 12 hostiles near). Rare (2 of 80 stays with Teleport
   over 50 s, 1 of 84 before): ~0.5 s a game. Look at `hunt.shack_goal` against the route's chest when both are near.
0b. (14:15) **make_room's cube move is made in Lower Kurast, not in town** (about 1.6 s, 14:10:54–56): `Loop.leg`
   sets `make_room` in the fortress, but the runner acts on it at the start of the next leg, after the waypoint.
   Same seconds either way. In town it cannot meet a monster. Low priority.
1. **Standing after a Blade Warp landing: 1.48 s a stay** (stalls of 1.5 s and more whose log says "Blade Warp aimed
   at ... landed at ...", 69 of 135 stays). That is the time between a landing and the next key that is over the
   warp's delay. Find what the macro waits for there (the look, the path, the field grown). Related:
   movement-findings §4 #3 (grow the way during the flight, ~1 s a game).
2. **Weapon swaps in stalls: 0.41 s a stay** (25 stays). Where does the loop swap on the level, and why? Arrival probe
   (movement-findings §4 #2).
3. **Strikes in stalls: 0.31 s a stay** (23 stays), after the attackers-only rule. Check that they hit attackers.
4. **Refused warps: 0.18 s a stay** ("the game took no cast for the key"). A margin before the next press
   (movement-findings §4 #10).
5. **"priced act expired: look again": 0.13 s a stay**, and "Blade Warp: the character did not move" toward shack
   containers: 0.2 s a stay together.
6. **The step back at a close waypoint** (`waypoint.open_panel`, a direct ground click; deployed 09:44:32): not seen
   played yet. Next close-waypoint case: expect "a step back", a move, and the panel open, with no recovery.
7. **Remembered valuables** (the plan's §14, designed, not built): two of the night's five losses (a Small Charm
   in a pile, a Flawless Emerald seen in a flight past) came from the loop forgetting a valuable it no longer reads.
   First log the distance at which a remembered unit stops being read, then build it. The same change makes the
   census say an item once (its `ground_seen` lives per GameMemory, made per read).
8. Magic rings and amulets are left by the sure mode by design ("taken (material)" in the census only means the read
   listed them). Chipped, flawed and plain gems are hidden by the loot filter. Not losses.
9. Movement (rca/2026-10-17/movement-findings.md §4): compute the path during the warp's flight (~1 s a game); press
   Blade Warp again with a margin, so it is not refused at 1.002 s (~0.3 s); an arrival probe in town without swaps
   (~1.5 s; needs a waypoint retry design).

## Waiting for the player (asked 2026-10-17)

- Teleport charges: moot since Enigma (2026-10-18): Teleport is the character's own, no staff, no charges.
- (2026-10-18 05:51) Full flawless gem stacks: Amethyst, Sapphire, Ruby and Diamond at 99. The loop keeps their gems
  (never sold, never left) and cubes each three into a perfect one (4 made by 05:46); up to two of each kind wait in
  the cube, up to 8 of its 12 cells, so the room runs low sooner (a trade session at 05:51, 6 games after the last).
  Options: the player empties some flawless stacks (the loop then stashes them again); sell flawless gems of a full
  stack; or keep as is (~2 s a game).
  06:20: Flawless Emerald full too (five kinds); six leftovers in the cube, trade sessions every 5-8 games.
  07:57 Flawless Skull, 08:42 Flawless Topaz: all seven kinds full. Leftovers up to 14 cells (the cube holds 12).
  **Ruled 09:40-09:53**: cube them first, parking on the ground what the inventory cannot hold; sell a kind's surplus
  only once its perfect stack is 99 too (the 09:22-09:58 round).
- Shack side containers: ruled 2026-10-17 10:55, only those beside a chest and in sight of it (live 11:02).
- Trim the loop's prebuff (Summon Defiler ×2 + Consume, Hex: Purge, Psychic Ward: ~3 s a game).
- Shorten the human-like pauses (lobby, Save and Exit, waypoint panel: 0.5–1 s a game).
- Raise the 50% stash threshold (the stash is visited every 3–4 games now).
- Selling for gold: identify at Cain, appraise every item, sell only clear junk. Designed, not approved ("Not yet").
  Selling full rune stacks (99) is approved and live.

## Rounds

Newest first. One entry per round: the time, what was seen (with the clock), what was changed (files), the tests run,
when it was restarted, what the next games showed.

### 2026-10-18 17:50: rulings, second set; restart 17:54 with the 16:50 rulings built

- Built and live at 17:54:22 (service 20261018T145422Z-a9c1363b; 2286 macro tests, 702 triage): junk parked on a page
  for a stranded keeper (`town.PARK_JUNK`), `Contract.stash_full` and the loop's stop on it, several trips a game
  (`TRIPS_A_GAME` 3, only after a trip that gained room), a refused Grand Charm with no room: the cube, then the swap
  by a trip; the best copy of a unique/set kept (`copies.py`, live since 17:09); unidentified items in the shuffle;
  the rare amulet rule (+1 class or +2 tree with 10 FCR and 20+ life; rules rebuilt: 462). None of today's 12 sold
  rare amulets would have been kept. Knowledge test `test_scoped_asking_evidence_is_exactly_preserved_from_offline_snapshot`
  fails on a market snapshot hash (cached data, not the diff).
- The player, 17:50: a keeper may wait in the cube (not a miss); a valuable with no room: stop and clear the inventory
  with the town routine, then take it; a 45 s stall: analyse each case; 99 rune stacks: cube them, aim at 80 or lower.

### 2026-10-18 17:10: the stash full for a Grand Charm: the loop off (the 16:50 ruling)

- 17:09 visit: a Latent Bone Break (unique Grand Charm, 1x3, a Sunder charm, "slow") stayed in the cube: `town.place`
  over the visit snapshot (`visits/170903.json`) finds no page with a free 1x3 (pages free 0:0 1:0 2:1 3:2 4:0 5:5).
  The planner predicted it and matched. By the ruling "if stash is full - we need to stop loop" (its code not live:
  agents at work), the loop was turned off by hand at the lobby: restart 17:09:53 (20261018T140953Z-9eb06bab), loop
  off. The charm is safe in the cube. The loop waits for the player to clear stash space.

### 2026-10-18 16:50: the player's rulings (town, sales, trips)

- Junk may be parked on a stash page during the stash stop and sold after (the stranded-keeper case; `JAMELLA_FIRST`
  stays off).
- A full stash (a keeper no page takes) stops the loop.
- Loop sales keep the best copy of each unique and set item first; only surplus copies are sold.
- Rare amulets with +FCR, +2 skills, +life are good, and other combinations may be; a high vendor price alone does not
  make one a keeper.
- The shuffle may move unidentified items. One game may make several trips to town. A refused Grand Charm (the
  Gheed's carry-one) causes a trip.
- Still open: a keeper deferred in the cube, the full-inventory class (lootpolicy `NO_ROOM_PLAIN`), the guard and
  give-ups, a 45 s stall as room, 99 rune stacks, the rune backlog pace, the cube plan, F1/F3.

### 2026-10-18 16:10-16:35: the architecture plan, first round (the player: "go ahead with parallel sub-agents")

Five agents in parallel, disjoint files, each the first steps of its study (`rca/2026-10-18/arch-*.md`); behaviour kept
except step 4's fix. Wide suite 2253 passed; ruff and pyrefly clean. Restart 16:34:19 (service 20261018T133419Z-2e7dc9ff).
- Step 1 (observability): every pattern the loop-watch tools read in `tools/logwords.py` (producer `file:line`, a real
  line each); 80 contract tests (`tests/skills/test_loop_watch_lines.py`) build the core lines from production format
  strings. Fixed: Cain's identify count in `trade.py`, the "put down: its stack is full" kind, `REPAIRED` missing every
  repair since 8accb7d. Replays before/after identical but for those.
- Step 2 (orchestration): `Abort(cause=...)` (actuator.py `Cause`: hand, refused, room, stall, other) and
  `runner.classify`; the words are the fallback, same branches (31-text table); "has not moved" = stall, still a room
  cause (ruling pending). `loop.GameId` and `Loop.observe` log "game changed", no readers yet.
- Step 3 (level behaviour): `lootpolicy.verdict` reproduces the five sites (press, run, sweep, guard, sightings) over a
  5040-row golden table; shadow calls in `pick_up`, `stay_by`, `gather` log disagreements and the disputed class
  `NO_ROOM_PLAIN` (ruling pending), once per site, unit and game.
- Step 4 (actions): `act.py` (`until`, `perform`, `Failed`); the `_until` copies through it; `use_thing` asks `took()`
  before the first aim and between aims (`PANEL_GRACE` 0.25 s; the 14:42:09 class), red test first. Fakes: `opens_after`,
  `walk_reach`, `panel_covers`.
- Step 5 (town planning): a snapshot per visit (`<session>/visits/<HHMMSS>.json`, `visitlog.py`), `townplan.plan_visit`
  in shadow ("town plan: predicts …", then "matched"/"differs"); fixtures of 14:28, 14:56, 15:06, 15:14, 15:20.
- 16:30, 16:31, 16:35: a set Battle Boots (verdict self, 2x2) stayed in the cube three visits. First told as a full stash
  (wrong): the 16:35 snapshot (`visits/163522.json`) shows `town.place` puts it on shared page 5 (a 2x2 at (2, 8)); the
  inventory had no 2x2 for it to come out through before the stash (a junk unique Fuscina 2x4 sold only after it): the
  stranded case, waiting for the ruling (park junk on a page, or Jamella first). The planner predicted the miss and
  matched; with the park-junk ruling its fixtures (15:06, 15:14, 15:20) show none.

### 2026-10-18 15:35-16:00: a Ring the clicks did not take; the watch's MISSED; architecture studies

- 15:49 MISSED Flawless Skull was the watch's own false alarm: `watch.py` kept its own ground tracking, without the
  click rule `games.py` gained at 15:34. One rule now (`games.clicked`), used by both; today's log replayed through the
  watch gives what `games.py` gives (one left: the 15:35 Flawless Amethyst, walked to from 3 away, "did not move",
  never in the census again: taken by the walk's click most likely, not proven).
- 15:53:05 stop (game 67): a set Ring 5 away under the pointer; 11 clicks from one footing took nothing, the character
  stepping 0.4 and snapped back (take 20261018T125257Z-37; open ground between, allies only near). Both trips back went
  nowhere in 0.2 s: the pickup's SHUNNED (30 s) hid the Ring from the press after, and `approach` does nothing within a
  click. Fix (`runner._go_back`): a trip back lifts the shun and, more than `AT_DROP_UNITS` 3 away, moves to the drop
  in hand (`pickup.moved_in_hand`); a resume gives the sightings their trips again (`sightings.again`). Tests:
  `test_a_trip_back_lifts_the_pickups_give_up_and_moves_to_a_valuable_within_a_click`, the restart test pins tries 0.
  Restart 15:58:30 (service 20261018T125830Z-c4eec9ab): the trip teleported onto the Ring, picked up from 0.7 at
  15:58:41, the game left after.
- The Jamella-before-the-stash reorder (`visit.JAMELLA_FIRST`) is off until the player rules; its tests switch it on.
- Architecture studies (read-only): `rca/2026-10-18/arch-{loop-orchestration,town-planning,level-behaviour,actions,
  observability}.md`.

### 2026-10-18 14:05-15:00: studies of what is left; trips, restart and waypoint fixes

- Measure since 14:29 (`andy.py`): 88.9 Andariel kills an hour, clean cycle median 36.9 s; stairs 1 press, 0 walked.
  Town visits (step 3's TOWN leg) held the contract at 14:31, 14:38, 14:45, 14:50 (20-28 s; cube empty, 2x4 free).
- Studies (read-only, `rca/2026-10-18/`): `town-remaining-findings.md` (the 14:28 miss: a unique Embossed Plate
  2x3 stayed in the cube, its only block held a junk Amulet sold later at Jamella; steps 4-5: 35 rune transmutes of
  backlog, perfect gems/shards/essences cannot be freed), `loop-robustness-findings.md` (restart forgets Andariel
  slain; Gheed's swap late; the waypoint panel already opened by the walk's click; HUD shop errors harmless),
  `trips-and-towns-findings.md` (D1-D5 trip defects, LK trips, act 1/3 services). Cube wrapper design:
  `macros/cube-plan.md` (not built, for the player's review).
- Fixed, restart 14:48:40 (service 20261018T114835Z-2dc9cf24): TRIP resets `returned` (D4, the 14:00 stop); the
  return from a trip gives the sightings their trips back (`Sightings.again`, D2); trip and drop only for a room
  cause, a trip only when `carrying` (D1, D3); REPEATS TOWN 3 (D5); tracker keeps `slain` over a restart and saves a
  boss kill at once; `waypoint.open_panel` takes an open panel as done, no step back onto it (seen live once by 14:51).
  Tests: test_runner, test_sightings, test_waypoint, test_tracker; wide suite 2209 passed.
- Restart 15:02:19 (service 20261018T120214Z-72a31d3f), 399 focused tests: the Gheed's swap at the first refused
  click (`pickup.Refused`; in a level run through `hunter.carry_one`, the hunt's give-up as a backstop) and the level
  run's give-up memory cleared at GHEED_STASH (`Loop.forget`); the stash stop moves junk/keys aside or puts junk into
  the cube for a cube keeper with no block (`town._make_way`, `StashStop.shuffles`/`into_cube`, `visit._aside`). The
  contract had missed a cube keeper again at 14:56 (unique Spiked Club) and 15:01 (set Boots). Unproven in the game:
  a pick-up/put-down in the inventory with the stash open.
- 15:06 miss (set Boots, 2x2): no move could free a block (a junk unique Fuscina 2x4 held the inventory, the cube full:
  15 cells needed, 13 free). Built, in the tree but not restarted: `StashStop.stranded` and a visit order Cain ->
  Jamella -> stash in that case only (`visit._stranded`); 178 focused tests pass. Waits for the player's ruling: it
  departs from the ruled order Cain -> stash -> Jamella. The keeper is not lost meanwhile (it waits in the cube).
- Waiting for the player: rune backlog pace; 99 rune stacks sold or cubed; may the shuffle move unidentified items; a
  second trip a game; a refused charm as a trip's cause; the cube wrapper plan.

### 2026-10-18 12:55-14:03: town visit by the stash view, precise stairs, Gheed's swap to the shared stash

- Town visit (the player, 12:55: one visit, no back and forth, the stash known): plan `macros/town-plan.md` (study),
  steps 0-2 built by an agent: `world.stash_view` (shared pages by +0xD8, resource stacks by +0x9C), `town.py`
  planner, `visit.py` stash stop (no page tries; the shared page last shown remembered). Live 13:26/13:31: the 13:27
  session arrival->waypoint 20.1 s (32-40 s before), stash 6.5 s, one opening. Steps 3-7 open (one TOWN leg).
- Stairs (the player, 13:05: "make teleport location to next level entrance more precise"): an agent found the door
  goal kept the loop's 3-unit short stop and the remembered entries sat where no hop lands; `teleport.entry_stand`
  (nearest landable spot within 2), `way_out` short 0. Live 13:26: walks 0.0, in after 0.26-0.28 s (36 of 58 walked
  before). Also `pursuit.to_the_door` ends a run within ENTRY_REACH of an entry no hop gets nearer to (a 48 s stall,
  12:46:41).
- Drops: DROPS_LAND was timed from the fight's post (no wait at all, 13:02:58), then from the first loot leg (2 s every
  game); now from the kill (terror/bosses.py KILLED_AT, DROPS_AFTER_KILL 1.9).
- Fetch: a trip back takes FETCH_HOPS 16 (HOPS 4 left a Flawless Topaz 92 short, 13:15); a non-room stop is a repeated
  leg, not a room trip. The sightings survive a restart (`resume_state['sightings']`; a restart lost that topaz).
- After her death the loop's run is over while nothing hurts (hunt.py judge: Hold -> Ended for a looped run at
  LOOT/LEAVE; key_asks yields on Ended): 11.5 s and 30 kills of her pack at 13:26:39. To measure.
- Gheed's (the player, 13:39-13:41: own Gheed's to the SHARED tab, pick the new, identify, keep the better MF; "you
  cannot pickup another gheed if you have another in inventory/private tab"): rebuilt by an agent (charms.py `park`,
  `choose`; legs GHEED_STASH, GHEED_CHOOSE; runner `_gheeds_swap` on any stop with a unique Grand Charm left).
  My mistake: the 13:16 non-room rule ran before the swap check (the loop stood 13:35-13:56). Live 13:57-14:03: theirs
  (34%) to shared page 1, the new picked up, identified 34%, tie kept theirs, the new on shared page 2 ("sell").
- Tracker: a boss first seen dead counts as killed (a restart mid-game); did not fire at 14:00 (her corpse gone).
- Open: a restart mid-game on Catacombs 4 with her corpse gone still stands 45 s; the shop check's HUD read races
  (harmless); town steps 3-7; F1/F3 rulings.

### 2026-10-18 12:33-12:50: the loop never stands stopped (room by shape, recoveries pause, essence dropped)

- The player, 12:30-12:40: "analyze when we have stopped and how to setup the loop in the way that would fully
  prevent us from stopping"; "you have all the facilites to solve this issue? don't you think about it?"; "we're just
  need to make some space ... we should have 2x4 inventory space when we have emptied cube/inventory"; "probably we
  don't need 2x sets of keys for non LK loop".
- Stops 10-16 to 10-18: 52; today 5 of 6 were no room for a valuable (35 + 3 + 16 + 37 min idle), the rest repeats.
  My mistake: the 11:56 Brandistock stop stood 37 min while I did speed work (the skill's "wait for the player").
- 12:36: the trip for room did nothing in the Fortress (9 cells free by count) and the 2 x 4 Brandistock still found
  no room: the loop's key stack at (3, 0) split the only 2 x 4 the player's charms leave.
- Changed: cube.py `keys_move` frees a BIG_BLOCK 2 x 4 first (a 3 x 3 counted larger); runner.py make_room arranges
  the keys before the cube (12:41:39 "the keys moved (3, 0) to (2, 2)", the Brandistock picked up); loop.py TRIP is a
  whole session of its own (cramped whatever the count; identified/shopped/restashed/arranged reset) and the keys are
  arranged after every session (TO_THE_ENCAMPMENT too); Kind.keys: Andariel buys one key stack (KEYS_ONE_STACK), LK
  two; `recover` never stops the loop (past RECOVERIES a RECOVERY_PAUSE 30 s, a warning), only death does; a full
  stack's material no vendor buys is dropped in town (cube.py `drop_item`, loop `discard`). Tests: test_cube,
  test_loop (4), test_runner. Skill rule 3c and the "stops here" row: fix and turn the loop on at once.
- Restarts 12:41:26 (Brandistock taken), 12:43:47, then the next lobby with the essence drop.
- Open: a restart mid-game on Catacombs 4 does not know Andariel died (12:42:19: stood 45 s, then left).

### 2026-10-18 11:38-12:25: Andariel kills an hour; drops, stairs, trip and strike-first fixes

- The player, 11:41: "next level teleports: now we walk from time to time ... engagement speed on level 4: we're
  rolling our attack not as fast as we can ... use sub-agent to build metric: andy kills per hour and then work
  towards to improve it".
- **Metric:** `tools/andy.py` (kills an hour of play, cycle phases, stairs walks, the fight from the takes). Baseline:
  10:20-11:38 54 kills/h (median cycle 49.7 s); 11:38-11:56 (A1 live) 83 kills/h (39.5 s; +28, 90% +16..+39).
  Phases since 11:38 (s a cycle): next game 7.8, Catacombs 3 run 6.7, Catacombs 2 run 4.5, in reach to dead 4.2,
  loot after 4.1, arrival to in reach 4.0, waypoint 3.4, town 3.1.
- **Studies:** `rca/2026-10-18/stairs-walks-findings.md` (walks at the stairs from a learning bug: a spot the click
  walked on from was learned as proven; ~0.3 s a game), `rca/2026-10-18/andariel-cadence-findings.md` (1.25 strikes/s
  of 2.78; the hop/strike alternation of I2's strike gap 1.96 s a fight; landing to the strike press 0.48 s; casts
  under the strike 0.8 s; a Dol Rune side drop cost 5.7 s once).
- **11:52, MISSED Sol Rune** on Catacombs 2 (left for 2 hostiles, then the stairs): runner.py `down` takes what was
  seen on the level (`take_one`: pickup, then `_fetch`) before the stairs press; REPEATS DOWN 8 -> 12.
- **11:52, Save and Exit 0.6 s after her kill:** her drops land through her 1.55 s death animation (items seen up to
  1.7 s after the kill); 4 of 19 games left at 0.5-0.8 s. loop.py `DROPS_LAND` 2.0 s after her fight's end before her
  level is left with nothing picked up. Tests: test_loop (2).
- **11:56, stop: a Unique Brandistock with no room:** the trip for room went back through the portal 3 s later with no
  session (`fortressed` set by the game's own session before the trip). TRIP resets `fortressed`. Test: test_loop.
  The loop waits for the player there (Catacombs 4, game 24).
- **Stairs** (findings §5 A+B+C): teleport.py learns a clicked-from spot only when the click walked under NO_WALK 0.5
  (else where the level changed, and only over a spot it was clicked from); a walk round to the entry of ENTRY_AROUND
  8 within NEAR_WARP is the click's, not a hop; goals.py `way_out` aims the run at the remembered entry within
  ENTRY_GOAL_NEAR 2 (hunt.py `door_entry`). Tests: test_teleport (3), test_pursuit (1).
- **F2, strike first:** hunt.py `key_asks(unstruck=)`: no second judgement before the strike's press short of a fresh
  press; the better-place look after the press. Test: test_hunt.
- Suites: 4870 passed (macros, combat, builds, scenarios, levels, routes) before F2; 4037 passed (macros, scenarios,
  builds) with F2. Service restarted 12:25 with all of it, the loop off (waiting for the player).
- Waiting for the player: F1 (Teleport toward the boss not held to the strike gap while nothing hurts: bends U1); F3
  (no sigil, no side drop while the boss is in reach and nothing hurts); the Twisted Essence (vendors refuse it: drop
  a full-stack material in town, or keep carrying it); the Brandistock (loop on for a trip, or by hand).
- To measure once on: `andy.py --since '<on>' --against '2026-10-18 11:38' '2026-10-18 11:56'`: arrival to dead (7.6
  s), landing to strike, stairs presses a visit, kills an hour; guards: least life on Level 4, MISSED.

### 2026-10-18 10:05-10:40: the Andariel loop (KP_6 run kinds); room, prebuff, double-tap fixes

The player, 10:05: "I want to build andariel loop that will be similar to lower kurast loop, we're going to use the same
KP_6 run start/stop it"; "inventory management and trading - same as LK"; Gheed's Fortune carry-one to be swapped through
the stash. Plan: `andariel-loop-plan.md`. Nothing committed.

- **Run kinds** (`macros/loop.py` `Kind`, `KINDS`, `kind_of`): KP_6 three times switches the kind; a start with none
  chosen takes the kind of where the character is; a restart keeps it (`resume_state` `loop_kind`, `restart.py --kind`);
  the HUD badge `LOOP SURE ANDARIEL`. Andariel's legs: `to the Catacombs`, `down the Catacombs` (rushed level run to
  the stairs, then the press through them), `Andariel` (the level run, fighting), `what is left`, Save and Exit on
  Level 4; the next game starts in the Rogue Encampment. A session due there: `to Pandemonium Fortress`, LK's session.
- **10:20:17, the prebuff in the Rogue Encampment**: Consume three times unseen, the game left (townsfolk: routines.py
  TOWN_NPCS). Now cast on Catacombs Level 2.
- **10:22:20, the inventory full at a restart's first leg**: the room was read only from the second look; the player's
  items now told first (`sort` before the room). And a transmute's worth of kept gems (3 of a kind, perfect not full)
  is a session's work (`carrying`): 21 such items had brought no session since 09:43.
- **Town trip for room** (`TRIP`, `TO_THE_ENCAMPMENT`, `THROUGH_PORTAL`, portal.py `through_portal`): a valuable on an
  Andariel level with no room, the cube tried: portal, the Fortress's session, the Rogue Encampment's waypoint, back
  through the portal; once a game. Played 10:28:18-10:28:38 (20 s end to end); that time no session came (see next).
- **Items moved by hand read as the player's** (`sort` `loose`): after game 28's by-hand sorting, Antlers, a Ring, two
  runes and a Topaz took the loop's room (no 1 x 3 for a Grand Charm). An unidentified item, a rune or a gem is never
  taken for the player's at the first look (10:32:03: 5 taken; the Grand Charm picked up, the session at 10:33 sold
  three, an empty cube and 9 cells after).
- **10:26:40, a full clear of Catacombs Level 2 (80 s)**: the loop's two posts 0.35 s apart (the first took the last
  game's held run of Level 4 and ended at once) read as a double press of KP_1. The loop's posts (`Pursuit.looped`) are
  no taps and take no run of before.
- **Gheed's Fortune swap** (`macros/charms.py`, `SWAP_OUT`, `SWAP_BACK`; world.py `Carried.unique`, `Pack.stashed`):
  a refused unique Grand Charm with the player's Gheed's carried (row 359 read: 10:39:10 "Grand Charm (0,0) unique row
  359"): theirs onto the personal stash page (read exactly; a shared page is not), back through the portal, the new one
  picked, then the new one into the stash and theirs back, `own` moved to its new cell. Fakes only; not seen in a game.
- **Full material stacks** (the player, 10:37: "essensies are stacking to 99, when we have full stash cell - just stop
  picking it up"): `sold_full` takes the Materials tab's kinds too (not potions): not picked up, carried ones sold.
- **My mistake, 10:39:02-10:39:10**: the player paused with KP_6 while `restart.py --loop on` waited; it turned the loop
  on again (it was off 0.04 s later). restart.py now keeps the loop off when it sees it go off while waiting.
- Tests: test_loop (Andariel legs, trip, swap legs, kinds, materials), test_runner (three presses, resume), test_charms
  (fakes model the personal page), test_runmode (looped posts). Wide suite 1918 passed.
- Seen: clean games 55-61 s (down the Catacombs 27-33 s, Andariel 14 s, next game 7 s), the player's by hand 59 s.
- **10:55, the stands by packs on the way down** (the player: "when we're teleporting along the level near group of
  mobs, we're freezing ... then, after a few seconds we starts attacking"; rca/2026-10-18/freeze-near-mobs-findings.md):
  the stairs are a way, so `Hunter.cleared` made each pack within 30 units the goal, and the rush gate held the strike
  RUSH_UNMOVED (1.5 s) after each Teleport: 41 stands, 74 s, 10:20-10:41. Now the loop's rushed run (not a full
  clear) keeps the route's goal (hunting/choice.py `cleared`; test_runmode). Measured 10:55-10:58, 5 games: down the Catacombs
  median 14.3 s (27-33 s before, 51-57 s in games 6-8), games 46.5 s median, 88/h (58.9/h before); no "clearing the
  way (" goal. Wide suite 1926 passed.
- **11:00, the prebuff back in town** (the player, 10:58: "consume buff grants +run/walk speed and make things faster
  in town, so, probably we should keep it up in town too ... battle orders, summon defiler - we can do it on entering
  battleground"): the town's prebuff (Consume, Hex: Purge, Psychic Ward) at the game's start again, Battle Orders at
  the arrival's swap and the Defiler on the field as they were; a town prebuff the Rogue Encampment's townsfolk spoil
  is made again on Catacombs 2 and the game kept (loop.py `NEXT_GAME`; test_loop). Measured 11:00-11:04: Consume in
  the Rogue Encampment 5 of 5; to the Catacombs median 5.3 s (6.6), down the Catacombs 11.4 s (14.3: no prebuff
  there), games 39.8 s median, 105/h.
- **11:12, junk set, unique and crafted items sold** (the player, 11:10: "we should sell junk rings and other junk
  items; imporant!: do not sell own equipment or valuable items", "also, we can sell set/unique junk items"): junk.py
  JUNK_QUALITIES and pickmode.py `sellable` take them when appraised `vendor`; never a set or unique charm (Sunders,
  Gheed's, Annihilus, the Torch), never the player's items (`loot` excludes `own`). Tests: test_junk.
- Open: a restart mid-game does not know Andariel died (the fight stands at her mark 45 s, then the game is left);
  Andariel's mark (46, 46) worked in every game so far.

### 2026-10-18 09:22-09:58: full flawless gems jammed the cube; parked on the ground for the transmute

- Seen: from 09:22 every game was a trade session (60-80 s, ~33 s before): the loop's 14 then 19 items were all
  flawless gems of the seven full stacks, the cube full of them; a transmute must empty the cube but the inventory had
  room for 9, so none ran ("no room in the inventory for the item ... the cube must be emptied of"). Each session also
  spent ~14 s on stash refusals of those gems. 09:45:38, game 28: the loop stood by a Flawless Sapphire and a Grand
  Charm with no room (the guard); the player handles it by hand.
- Rulings (the player, 09:40-09:53): first "sell surplus to Jamella"; then "we don't need to do gem sale until we have
  99 pgems of type and we must cube them up first"; parking: "drop on the ground then pickup and move to cube".
- Changed:
  - `loop.py` `surplus` (GEMS_A_KIND 3, GEMS_KEPT 6): a full kind's flawless gems past that are junk for Jamella, only
    when the perfect gem's stack is full too (none is today: no sale now).
  - `cube.py` `transmute(..., park)` / `_park`: a cube item the inventory has no room for is taken up and dropped at
    PARK_POINT (0.5, 0.7, between the panels), `park` told first.
  - `world.py` `PutDown.park`: a parked unit is not the player's put-down (picked up again, kept in the leave guard).
  - `runner.py` `stash_loot`: after a transmute that parked, the inventory's loop items go into the cube, then
    `pick_up` takes the parked gems back (len + PICK_SLACK 3 presses).
- Tests: test_loop (surplus, perfect gate), test_cube (seven parked, the perfect made; no `park`: nothing dropped),
  test_supply (a parked unit stays in the drops), fakes (a plain click takes a cube item up; ground below 0.6);
  198 focused passed; ruff, pyrefly clean. The runner's pick-up after parking is not tested on fakes: first seen live.
- Restart 09:58:31, loop off (the player is at game 28). Expect at the next session: "put down for the transmute",
  "three Flawless X into a Perfect X", "picked up again", and nothing left on the town ground.
- Not done: the stash's per-session refusals of the full gems (~14 s a session) are still tried each first visit.

### 2026-10-18 09:19: a game name come round again stopped the loop

- Seen: 09:19:49, game 198, at Save and Exit: "next game again and again in the lobby after cyber81: nothing came of
  it" four times in 20 ms, then the loop stopped. Not the player (no `PLAYER: loop off`). Cause (verified): names wrap
  cyber99 → cyber1 (`world.py:514`); cyber81 was made at 08:14:05 and again at 09:19:16, and `Loop.count` keyed its
  counts by the name, so the second cyber81's lobby began at the first one's count and every recovery hit the guard.
- Changed: `Loop.count` counts only where the loop is now (`counted_in`; `made` cleared when the place changes). The
  repeat guard is unchanged within one game or one lobby (the 2026-10-16 per-game-left test still passes).
- Tests: `test_loop.py` 28 passed (new `test_a_game_name_come_round_again_starts_its_own_count`); ruff, pyrefly clean.
- Restart 09:21:58, loop on, pickup sure. Expect: no stop at the next wrap (about 99 games on, ~11:15).

### 2026-10-18 01:36: CTA at the arrival's swap; trade goods out of the sure mode; resources with no tab clicked

- Teleport-first round (01:14-01:36): 30 games, 0 Blade Warps. Goldens: the 47 `staff-none+warp-ready` decisions
  rebuilt (each Blade Warp → Teleport, nothing else changed).
- Call to Arms at the arrival (the player: "go ahead with the CTA at the arrival swap"): `routines.took_input` calls
  `run.arrival_swap` with the other set in hand; `cta.cast_in_hand` casts BC/BO there when the Call to Arms is held,
  out of town, Battle Orders not shown. Saves the caster's own swap pair (~0.5-0.7 s a game). Tests: test_cta.
- Pickup modes (the player: "we now don't need gold anymore ... move things that we're added for gold trades ... into
  separate category ... use sure for valuable things or small things"): SURE no longer takes the skilled magic/rare
  trade goods (`identified_for`); TRADE (`traded`) = sure + them; REGULAR as before. Double KP_6: SURE → TRADE →
  REGULAR. HUD "LOOP TRADE". The bases judged by rolls (Void, Monarch, Paladin shields) stay in SURE.
- Stash (the player: "you don't need to open appropriate tab ... automatically gets to correct tab"): inventory
  resources Ctrl + clicked with the tab shown; their own tab only after a refusal, which there means a full stack;
  the cube's resources from one resource tab shown once. Test: `test_the_inventorys_resources_go_onto_their_tabs_...`.
- Restarted 01:36:04 (pickup sure valuables). To check: "Call to Arms at the arrival" lines and no separate CTA swap;
  stash visits with no tab clicks; trade sessions rarer.
- 01:36:20 live: cast at the arrival swap; the swap back pressed 0.4 s after Battle Orders was not taken (a second
  0.6 s later was): `cast_in_hand` waits for the cast to end (CAST_OVER 1.0). Restarted 01:37:37; at 01:37:52 one swap
  back, the first hop 1.2 s after the input check. Stash 01:37:17: 12 items in 4.9 s, no refusal.
- 01:37:56-01:38:42 a recovery: Lower Kurast's route chest (5100, 2532) never under the pointer, another object
  (2, 1408512986, not one the takes list) at all 6 aims, 46 tries until the 45 s watchdog left the game. Not new
  code (use_thing untouched), first seen. `hunt.ROUTE_USE_TRIES` 8: then the chest is left as gone
  (`route.note_empty`, "not opened in 8 tries"); seals never. Test: test_herald. Restarted 01:41:27.
- 01:41-01:56: the swap back after the arrival's Battle Orders was refused 25 of 26 times at 0.39-0.42 s from its key
  (the mode read the cast over), and taken at the retry ~1.0 s; the caster's own at 0.56-0.61 s was taken 44 of 44.
  `cta.SWAP_AFTER_CAST` 0.6 s from the last cast's key before the swap back: ~0.4 s an arrival.
  First taken from before `routines.cast` (which waits for the cast before it), so still 0.42 s (01:57-01:59); now
  from the key's down (`cast` returns it): 02:01:19 one swap back, 0.61 s after Battle Orders. Restarted 02:01:05.
- 02:01-02:07, 10 games: one swap back at each arrival, median game 31.4 s, chests 6.9 s, no recovery.
- Where the town's ~25 s goes (game 10, 02:06:16-02:06:33.8): Save and Exit to the lobby 1.1 s; create to loaded 5.3 s;
  the town prebuff 3.0 s (Summon Defiler, Consume, Summon Defiler, Hex: Purge, Psychic Ward); to the waypoint and its
  click 1.4 s; Lower Kurast's load until a swap takes 3.5 s; Call to Arms 1.3 s. The loads are the game's own; the
  prebuff is the one part the macro could cut, and it is the player's ruling (Waiting for the player).
- 25 games 01:41-01:56: median 32.4 s, chests leg 7.5 s, no recovery. Town is ~25 s of the 32 s game: next game 8.1,
  to Lower Kurast 8.1, to the fortress 4.8, Town Portal 2.7 (the next candidates).
- Keys topped up to 15, not 24, at 01:47:23 and 01:57:01 (from 2): 2 -> 12, a click that bought nothing, 15 (+3), another
  that bought nothing, and BUY_CLICKS 2 counted both. Over the sessions: 86 top-ups to 24, 3 to 15, 1 to 3.
  `shop._buy`: misses counted in a row, BUY_MOST 6 -> 9. Test: test_shop (fakes `buys_take`). Restarted at the lobby.
  Live 02:08:23: "still 15", then 24 carried: keys 7 -> 24.

### 2026-10-18 01:14: Enigma's Teleport before Blade Warp

- The loop since 01:05 (Enigma, no staff): its routed legs were Teleports (88 casts), but 4 short pursuits to chests
  ("safe approach", "retreating") and one sweep stride were Blade Warps, 0.44-0.76 s from the key, then its 1.05 s
  delay. These take the movement set's first jump (`stride_of`, the retreats' `options`), and the Warlock's sets all
  led with the blade. The player: "now we have an enigma ... for LK runs we need to use only enigma and stop using
  blade warp in almost all situations".
- `builds/warlock/movement.py`: the own-Teleport set has Teleport first, the blade after (`Ways.then`); the staff set
  and the walk keep the blade first. `Ways.wait`/`routed_wait`: no casting delay is waited for while a jump before it
  in the set is ready. Still by Blade Warp by name: the mercenary's escort (`hunt.escorted`, a jump that brings) and
  Mephisto's bridge. `loop.py`: the gold rule's "Blade Warp alone" line is not said with Teleport of one's own.
- Tests: builds/warlock/test_movement.py (the blade's tests now with a staff in hand; the own-Teleport order, the
  stride over a wall, no wait). Restarted 01:14:23. To check: Blade Warp lines a game (was 5 in 12 games).
- 5 games after: 62 Teleports, 0 Blade Warps; 538 chests an hour of play against 396 (6 games: too few to judge).
- Next candidate (queued, after this one is measured): the arrival is ~6.5 s before the first hop (01:15:45-52):
  the input check's swaps 3.5 s, the cube 1.2 s, the Call to Arms' swap there and back 1.5 s. The check's last swap
  puts the Call to Arms in hand: casting BC/BO then would save a swap pair (~0.5-0.7 s a game).

### 2026-10-17 17:26: Halbu's menu opened standing; two key stacks; the repair errand at 20%; names wrap at 99

- The player: "there are still some issues with clicking trade/repair for repair". 17:21:57-17:22:05: the menu was
  open already (the walk click opened it) and the next opened as the character still walked (mode 3); the menu stays
  where he was drawn as it opened, the lines were aimed from where he was drawn after: two misses, the third (standing)
  took. `shop._open_menu`: a menu open already, or opened mid-walk, is closed and opened again standing; MENU_CLICKS
  2 → 3. Picture `menu-257-172200.png` (Jamella beside him).
- Errands: each is a whole session (15:53), and with Teleport the keys (~2.5 a game, under 3 every 4 games) and the
  charges (~11 a game, under 30% in ~4 games) sent the loop to a session every 3-4 games. The player: "probably we
  need to carry 2 sets of keys, instead of 12 => 24": `shop.KEYS_WANTED` 24 (a second stack, one cell);
  `repair.REPAIR_BELOW` 0.3 → 0.2. Tests: `test_a_second_key_stack_is_bought_with_the_first_full`, the full-stack
  tests at 24.
- The player: "upon reaching 99, we start from 1 again": `world.next_name` wraps (cyber287 → cyber1 at 17:13:31).
- Restarted 17:26:27.

### 2026-10-17 17:09: Cain's lines tried nearest the learned one

- 17:05:56-17:06:03: the identify leg took 28 s; Cain's Identify Items line came on the fourth try (8.5 s) though
  the learned lift was two half-lines off the first tried: the scan went from 0.16 up after the learned one. The learned
  lifts drift with where the vendor is drawn (Jamella 0.2346 → 0.2290 the same minute). `cain.lifts`: the scan sorted
  by its distance from the learned lift. Test: `test_his_lines_are_tried_nearest_the_learned_one_first`. Restarted
  17:09:11.

### 2026-10-18 00:10-01:03: terror zones: clear order, super chests, doors, tomb tour; a death to a Herald

- Clear order (hunt.py REMEMBERED_NEAR 45): the player, "we starts to go from one side to another back and forward";
  126 of 179 legs to a remembered monster were over 60 units. Now: in sight, remembered within 45, the room tour, the
  far remembered last. Loaded 00:23:07.
- Super chests (hunting/choice.py `super_chest_goal`, SUPER_NEAR 60): opened live at 00:24:26 (Infernal Pit), 00:49, 00:52.
- Doors with no press in a terror zone (runner.py `_run_over`, `onward`): live at 00:35:46, door to the next level's
  run in 1.5 s.
- Tomb tour (routes: `tour`, `back`; the player: canyon first, then tombs; trade by Town Portal in Lut Gholein):
  route "Tal Rasha's Tombs"; live at 01:00:38 (into tomb 69). Plan: rca/2026-10-18/canyon-loop-plan.md (trade: next).
- Death at 00:54:55: a tier 5 Apparition Herald (Extra Fast, Cursed, Mana Burn, Aura Enchanted) and 15 came up 13
  units from the Herald stand (OMEN_STAND 14), all within 10 at once; 2634 life in 0.6 s after two rejuvenations.
  Stand now 20 (reach 22); Death Mark and Sigil: Lethargy go on a Herald in reach first (the player: "prioritizing
  keeping herald on sigil lethargy + death mark"): mark.py `unmarked_herald`, buffs.py HERALD_SIGIL_SECONDS 6.
  Loaded 01:03:21, not played yet.
- Zones rotate on the hour: at 01:00 the run in the canyon was no longer a terror zone's (no auto door, tomb 69 ran
  to its way back, not a full clear).

### 2026-10-17 23:57: terror zones: Herald omen, cube room; CTA keys per weapon set

- CTA: its skills are on keys only with it in hand (the player: "swap weapon and there are 7 and 8 bound"): the row
  asks `GameMemory.cta` (worn in either set, read every 10 s), the caster reads the keys after the swap. Played
  23:41:01: swap, BC on 7, BO on 8, swap back, 1.4 s; states 51 and 32 on 0.3/0.35 s after their keys (the state word
  layout verified); recast every ~3 min.
- Herald (rca/2026-10-17/herald-findings.md): missile 737 `heraldspawner` (Range 125 frames) where a kill died, the
  Herald there 5 s later (6 of 6; 4.97 s and the same spot verified). hunt.py HERALD_OMEN: the full clear fights only
  within 22 of the spot, else stands 14 from it; a live Herald is its first goal and a boss. Played 23:56:24: omen
  read, stand at 23:56:26, the pack struck 23:56:29.9.
- Cube room (the player, 23:55: "if we have cube space - we should move items there"): outside the loop, a valuable
  with no room, the cube with room and no hostile within 30: the valuables the macro picked up itself (pickup.py
  TAKEN, by unit id) go into the cube (cube.py `stash`), the run takes the drop. Loaded 23:57:57; not played yet.
- Throne of Destruction: a full clear ends between Baal's waves ("nothing is left"): a routing candidate.

### 2026-10-17 23:35: Call to Arms kept up; terror-zone measure (loaded 23:35:07, not played yet)

- The player, 23:10: "now we have call to arms, so we need to use it and keep it's buff active ... automatic ...
  probably cta cannot be used in town". skills.txt: Battle Orders 149, Battle Command 155 have no `InTown` (the
  Warlock's buffs do). CybergrindAA's swap set since 22:58: Call to Arms (Flail, (97, 149, 4), (97, 155, 4)) + Spirit.
- macros/cta.py: an upkeep row (first of the upkeep) cast while Battle Orders is not shown on the character (state 32;
  BC 51; the state word inferred, not yet seen to change), never in a town, the game in front; its caster swaps to
  the CTA, casts Battle Command then Battle Orders, and swaps back. The CTA reads as `cta` in `GameMemory.hands`;
  CybergrindAA's main set is now told by the HotO Flail alone (both sets hold a Spirit). ~130 s a cast at level 12:
  one cast per LK stay. Needs Battle Orders (and Battle Command) on skill keys.
- To verify: "Call to Arms: Battle Command, Battle Orders" once a game at the LK waypoint, the HotO back in hand after,
  and whether the state reads (else the row recasts every 60 s: STATE_DISTRUST).
- Terror zones: tools/tz.py (kills a minute per level stay). Baseline 23:00-23:33: 19 stays, 29.4 min, 1610 kills,
  54.9 kills a minute, standing 37%. One 47.5 s stand by an Amulet with the inventory full and the cube with room
  (hunting/choice.py `stay_by`: waits for the player).

### 2026-10-17 22:37: Enigma worn: its Teleport is the character's own (no game played yet)

- The player put on Enigma (collection 22:26: Mage Plate, raw stat (97, 54, 1), "+1 to Teleport") and kept Naj's
  Puzzler (69/69 Teleport charges) on the swap. Before: `GameMemory.teleport` found the staff, so every move took
  `StaffTeleport`: a swap to the staff and a charge per cast, and the loop's Teleport still hung on the gold
  hysteresis (`teleports`). Enigma's skill was never used.
- Fix: `world.GameMemory.own_teleport` (a worn item outside the swap set with NONCLASS_SKILL_STAT 97 on skill 54,
  read once per set of worn items); `teleport()` is None then, so movement takes `OwnTeleport` (no swap, no
  charge), and the runner gives the loop LOOPED_TELEPORT in every game ("Macro: loop: Teleport is the character's
  own: in every move"). Test: test_world `test_enigmas_teleport_is_the_characters_own_...`. Wide suite 4276 passed.
  Loaded 22:37:00 with the loop off.
- To verify on the first games: the line above once; no "Swap Weapons" around Teleport; no charges spent (the staff
  stays 69/69); Teleport casts in the stays.
- Gap found and closed (22:50): repairs were triggered only by the staff's charges (repair.py `wants`); with the staff
  ignored nothing sent the loop to Halbu, and Enigma's durability (33/60 at 22:26) only fell. Now
  `GameMemory.wear` reads the worn item with the least share of durability (ethereal and indestructible aside), the
  loop goes to Halbu under WEAR_BELOW 0.4 of it, and a durability-only repair pays only a cost read off the tooltip,
  with WEAR_CARRIED 200,000 or more carried (no quote of charges can check it; the stash's gold kept out of reach).
  The "gold carried" line now says the most worn item each game. Tests: test_world `least_worn`, test_loop
  `test_a_worn_item_low_on_durability_...`. Not played: the first durability repair's cost is unknown.
- Also to watch: Teleport in every move now costs mana, not charges (549 mana, Enigma's damage to mana): a stay
  short of mana would show as Teleport casts that move nothing.

### 2026-10-17 21:50: the shack's other container clicked, not hopped to; stuck escape by Teleport; loop stopped by the player

- The player, 21:50: "we teleport into center of it and then go to weapon stand and travel back to chest. Probably we
  can make initial teleport immediately ready to click on chest or stand". Verified: chest and rack stand 12 apart on
  one row; after opening one the other was 13-17 away (past OPEN_NEAR) and hopped to: 1.75 s from the first open to
  the second (81 times today; 28 since chest-first 21:14), against 0.72 s where it was clicked (160). `hunt.paired`:
  standing by an opened container (PAIR_BY 4), its shack's other (PAIR_UNITS 14) is clicked from PAIR_NEAR 18 on a
  clear line. Test `test_the_shacks_other_container_is_clicked_from_beside_the_one_opened`. Expected ~1 s a shack.
  The landing between them (the player's own idea) is next if this measures well. Not deployed yet (loop stopped).
- 21:49:56-21:50:40 a recovery (45 s unmoved): one Blade Warp 15 units east "did not move" eight times; the spot
  barred 4 s each (DEAD_END_SECONDS), Blade Warp distrusted 3 s, no walked way grown, Teleport off for the gold: no
  act at all, then the same warp. Once today. `Hunter.dead_end`: a second failure near the same spot within
  STUCK_WINDOW 20 s lets the loop's moves take Teleport for STUCK_SECONDS 10 (`looped_now`), and a Teleport is not
  barred meanwhile. Test `test_a_move_failed_twice_at_one_spot_lets_the_loop_take_teleport_for_a_while`.
- 21:51:07 "Save and Exit again and again in cyber96: nothing came of it": the loop stopped; the player pressed KP_6
  at 21:51:09 (on), it stopped again at 21:51:11. The player: "I'm going to stop the loop, meanwhile you can fix
  things and do some cleanup and fix tests".
- Tests: the full repo run (pricing aside) failed 10 goldens: `Drop.rolls` (18:56) added `"rolls": null` to every
  serialized drop. `build_golden` rebuilt decisions.json; the diff is exactly 10 added `rolls` lines.
- Gold study (subagent, read-only; rca/2026-10-17/gold-income-findings.md): sales ~448k an hour (magic daggers
  125k, grimoires 67k, Barbarian helms 65k, pelts 59k, circlets 54k), repairs ~429k an hour (since 15:28 540k against
  451k sold). A Teleport stay spends 7.8 charges and makes ~7.7 weapon swaps (~2.8 s, as much as Teleport saves):
  after a Teleport `safety.move_price` gives every other move `needs='battle'` and `hunt` swaps back before the next
  Blade Warp. Candidates: (1) keep the staff in hand for the loop's Blade Warps and walks (needs an in-game check
  that Blade Warp casts with a staff), up to ~2.8 s a Teleport stay; (2) no Teleport on legs under ~30 units per
  leg (0.88 charges a stay, no time lost); (3) no new vendor kinds now. Waiting for a game to check (1).
- Earlier the same hour: the Teleport window (21:37, `hunt.act_window`), the blocked-open fight (21:26), the drop
  for room (21:14), chest-first (21:14) are live; their windows are cut by the stop.

### 2026-10-17 21:05: room by shape (the loop's stop); the route's chest in reach before the shack's rack (speed)

- 20:47-21:00: after the wall fix was kept the watch only narrated games for ~15 min. The player: "where we not in our
  continuous optimization cycle?"; goal set: "every 5 game cycles make sure that we're advancing in optimization and
  effectivity" (memory `d2r-loop-five-game-cadence`).
- 21:00:03 **stop**: "inventory full: no room for Grand Charm; Grand Charm lies on the ground: the loop stops here"
  (game 47, magic Grand Charm at (5029, 2857)). Cause (verified): `Loop.leg` counted room in cells (TRADE_ROOM 8)
  and the free cells were in pieces; the cube's last two '##.' twice; no session before the game; make-room put 2
  of 3 items in the cube, the Grand Charm (1 x 3) fit nowhere. Fix: `loop.SURE_BLOCK` (1, 3): no such block free in
  the inventory nor the cube is room low. Test `test_cells_free_with_no_block_a_grand_charm_fits_are_no_room`. Wide
  suite 1872 passed. Deployed 21:02:15 with the loop off: **the player's to resume** (the charm on the ground).
- Speed: `Hunter.at_hand`: the route's chest within OPEN_NEAR and `open_reaches` comes before `shack_goal`'s
  container (`goal`). Study: 9 of 27 stays went to the rack first from within 4 of the chest, 2.9 s to the chest
  opened; expected ~0.35 s a stay. Keeps the rack opened in the visit (SHACK_TRIES) and the 16:47 ping-pong guard
  (no move: the chest is opened from where the character stands). Test
  `test_the_routes_chest_in_reach_comes_before_the_shacks_rack`. Deployed with the loop off; the window starts at
  the player's resume. Measure: "rack first while at the chest" count, the chests leg.
- 21:10 the player: "and? why we have stopped fixing things and monitoring?" — I had left the stop for the player and
  only reported. The loop could not clear it itself: the cube had no room, the room fix acts in town only.
- `cube.droppable` / `cube.drop_for` (SURE_BLOCK moved to cube.py): after the cube was tried (`room_tried`), once a
  game (`Loop.dropped`) the runner drops one of the loop's items taken only to identify (unidentified magic or rare,
  a SKILLED type; never a charm, jewel, rune, gem, ring or amulet, never the player's own) whose cells free the
  block, the smallest; `SHUNNED` for DROPPED_SECONDS. Then the loop stops for the player as before. Tests:
  `test_an_item_taken_only_to_identify_is_dropped_for_a_grand_charms_block`, the runner's no-room test (cube, then
  drop, then stop). Deployed 21:14:21 with the loop on: 21:14:46 a magic Avenger Guard dropped for a 1x3 block (the
  put-down guard took it as the player's: not taken again), 21:14:47.8 the Grand Charm picked up, Town Portal.
  The chest-first window starts 21:14.
- 21:19 (game 5 of the window): rack first with the chest in reach 51 times in 20:23-21:00 (46 games) → 0 in 5 games.
- 21:23 RATE 224 over 10 cycles: not the change. Two trade games, 3.3 chests a cycle (layouts), and a 6.5 s chest
  blocked by a monster (21:16:22-28.9): two aims had a monster under them ("has (1, ...) under it; not clicked"),
  the open's priced 1.5 s ran out before `use_thing` raised `Covered`, so the hunt never fought it; four tries until it
  walked off. Pre-existing (56 such aims on 2026-10-17), exposed by no strikes on idle hostiles (19:38).
- `teleport.use_thing`: a priced expiry (`EXPIRED`) after a monster was seen under an aim is raised as `Covered`
  (the fight with it first: `Hunter.blocked`). Test
  `test_a_monster_seen_on_the_object_is_told_in_the_way_when_the_acts_time_runs_out`. Restarted 21:26:35.
  Measure: "no use of <container>: priced act expired" repeats after a covered aim.
- Teleport study (subagent, read-only; rca/2026-10-17/teleport-not-cast-findings.md): 31 of 683 Teleport keys
  (17:43-21:00) started a cast (mode 10, skill 54, normal length) that moved nothing and spent no charge; nothing
  measured separates them (swap timing, mode, previous cast, mana, target, hostiles); ~5% since the afternoon of
  10-12 (0.2-0.5% before): the step is open. The re-press (REPRESS_SECONDS 0.6) landed in 126 of 126, but the act's
  priced window (0.81 s, 1.56 with a swap) ran out first in 115: counted a failed jump, Teleport distrusted
  WARP_RETRY, ~1.6 s each. Fix (option A): `hunt.act_window`: a Teleport act's window is its price plus
  REPRESS_SECONDS (the price unchanged). Test
  `test_a_teleports_window_holds_the_keys_second_press_and_its_price_is_unchanged`. Expected ~1.0 s a failure,
  15-20 s an hour with Teleport on. Measure: "nothing 0.6s after the key" followed by "priced act expired".
- 21:41 chest-first at 31 games (21:14-21:41; Teleport 15 stays with a charge, 17 without) against 20:23-21:00: the
  targeted measure moved (rack first with the chest in reach 51 in 46 games → 0); YIELD 305 → 261 (−43, −99..+9: no
  evidence), chests leg 17.7 → 20.5 (−0.8..+6.2), stays without Teleport 20.9 → 23.1 s; stalls 1.6 s a stay, spread
  over pre-existing causes (the arrival's cube move 0.40, Blade Warp not cast 0.16-0.23, the 21:16 monster-blocked
  chest 0.19), none from the rack/chest order. Kept on its own measure; 30 more games before a verdict on yield.

### 2026-10-17 20:22: a loop chest is not opened across a wall (speed)

- Study (subagent, read-only; rca/2026-10-17/slow-legs-findings.md): the 8 legs that lost most 19:45-20:08. The two
  worst (19:54:27, 13.9 s; 20:03:41, 10.5 s): a shack's chest clicked from 11-12 away outside its wall
  (`hunt.judge`, OPEN_NEAR a straight distance), the open's 1.5 s ran out ("priced act expired"), a Teleport's
  swaps failed while the game walked the character round, then warps round and a Teleport in. "The walked way is
  still being grown" is not the cause: those lines come from the flight's pointer guess (`Travel.ahead`), and only
  3 looks ended in "no way: still being grown" (0.06 s a stay). The journal's earlier "the flight grows it" is wrong.
- Replayed on 933 opens 17:43-20:08 (each take's level.json): `walk_reaches` (ROUND_CLICK 5) would refuse 6 good
  opens (corners clipped); the walk round at most 1.5 times the line refuses 0 of 896 opened and catches 34 of 34
  across a wall. `travel.open_reaches` (ROUND_OPEN 1.5), used in `hunt.judge`'s loop branch. Test:
  `test_a_chest_is_opened_from_afar_only_where_the_walk_to_it_is_not_round_a_wall`. Expected ~1.0 s a stay
  (0.85 in the earlier window); measure: "lost to the pace" and the chests leg, opens that expire.
- 20:20:31 "cyber5 was not created": once today, 14 s, the next game made; noted only.
- Restarted 20:22:39 (Teleport re-decided at the first look: carried ~163k, on).
- Measured 20:23-20:47 (30 games; Teleport on in 14 stays, off in 15) against 19:45-20:22 (42, Teleport mostly on):
  opens that expired 12 of 346 → 1 of 225 (the targeted measure); chests leg 23.1 → 17.9 s (−9.0..+0.7), lost to
  the pace 10.2 → 8.0 s a stay (−4.3..+0.2), idle on the level 1.8 → 1.1 (better), the game 49.0 → 42.2 s;
  chests a stay 3.0 → 3.0. CYCLES 283 → 288, YIELD 286 → 296 (+10, −44..+71: no evidence). **Kept.**
- Also from the study, not done: chest before its shack's rack when standing at the chest (~0.35 s a stay); the
  Teleports the game did not cast (~0.45 s a stay); grow the field outside the look's clock (~0.06 s).

### 2026-10-17 19:38: the loop's run opens its chest among idle hostiles (speed); 0os +3 Abyss bases taken

- The player, 19:40: "strikes on hp loss - looks promising, especially since we have psychic ward"; "0 socket +3
  abyss - let's pickup them"; "start in LK will make things very slow, it isn't worth it" (off the queue).
- Measured 19:20-19:35 (15 stays): 31 strike presses, 1.28 s held a stay; 30 followed no loss of life and 1.5 s or
  more standing. Cause (verified, 19:21:34, take 20261017T162121Z-79): landed 4 away from the chest with hostiles in
  reach, `pursuit.run_level` returned Hold before `arrived`, so the safety priced no Operate; the only candidate was
  the hold, the hunt waited RUSH_UNMOVED (1.7 s) and struck (2.3 s), then opened: about 4 s.
- `pursuit.run_level`: on the loop's run (`rush`), at the goal (`there`), an operated goal (use, stand, pick up), not
  hurt within HURT_SECONDS and not settling: the open or pickup is offered, the hold still priced beside it
  (`arbitrate`'s rush rule decides; a dear open still holds). Test:
  `test_the_loops_run_at_its_chest_among_idle_hostiles_opens_it_unless_just_hurt`.
  Expected: strikes held per stay 1.28 s → under 0.6; stall seconds before a chest down ~2-4 s a stay where it fires.
- `pickmode.void_base`: or 0 sockets with +3 Abyss (ABYSS 402). Test updated.
- Restarted 19:38:20. Window for the measure: from 19:38 against 17:43-19:20 (and 19:20-19:38).
- 19:41-19:43, the first stays after it: strikes still after holds, 2-3 units off the chest. `there` (the goal's
  `near`) was false while the navigator had no step left (`moved`: arrival); the open was offered at neither. Fixed:
  `run_level` asks `moved` too and takes its Operate. Test extended. Restarted 19:44:58: the window starts there.
- Measured 19:45-20:08 (26 stays, Teleport on in all) against 17:43-19:38 (124): macro stalls 2.1 → 0.0 s a stay
  (90% −2.3..−1.2, better), idle on the level 2.0 → 1.5 (better); strike button held 1.28 → 0.83 s a stay (17 stays,
  scratchpad count), 8 of 38 strikes after a life loss, most of the rest on the way, not at the chest. CYCLES
  268 → 288, YIELD 276 → 291 (+14, −31..+63: no evidence; the earlier window had Teleport-off stretches). **Kept.**
- Struck off the queue: "Teleport only on long legs" was the 13:14-13:36 selective-charges trial (HOP_FROM 40): no
  time bought. 20:07:36 the repair took the carried gold to 97,416: Teleport off from game 27 by the hysteresis.
- Next candidates (the window's own ranking): standing 17.1 s of a 24.4 s stay; lost to the pace 10.2 s a stay, the
  worst legs toward weapon racks (class 107) with 8-12 s standing in them.
- Shared stash cleanup plan: subagent (read-only), to rca/2026-10-17/stash-cleanup-plan.md.

### 2026-10-17 19:20: Monarchs and elite Paladin shields picked up by their rolls

- 19:19:19 the key arrangement's first session: "the keys moved (4, 3) to (2, 2)".
- The player, 19:10: "start picking up monarchs (for 4os deflecting) and sacred targes (check what are expensive
  ones)". Market study (subagent, read-only; stat ids checked in pricing/raw/game-excel/itemstatcost.txt: 16
  item_armor_percent, 39/41/43/45 the resists, 194 sockets; ETHEREAL_FLAG 0x400000): see pickmode.py's comment.
- `world.Rolls` / `base_rolls` / `rolled`: sockets, staff mods, ED, the least resist, eth, read off the ground for
  white, superior and magic daggers, shields and Paladin shields; said in the census. `pickmode.shield_base`: a
  superior Monarch at 15% ED with 0 or 4 sockets; a magic 4os Monarch (identified, appraised; `sellable` when
  `vendor`); a white/superior Sacred Targe at 45 all res, or 40-44 with 3+ sockets; a Sacred Rondache at 45 with 4
  sockets, eth or superior. Unread: not taken. Tests: `test_a_monarch_or_a_sacred_targe_is_taken_by_the_rolls_that_
  sell` and the updated Void ones. Wide suite 1869 passed. Restarted 19:20:15. Not played: the resists read on a
  Paladin shield on the ground (the census will say ' 45 all res').
- The loot filter shows gray Monarchs only (the census saw magic Monarchs and normal Sacred Targes); a superior 0os
  Monarch the filter hides is never read. The study contradicts parts of guides/pricing-primer.html (eth 45@ fills
  34-46, not 46-63) and the filter's gray-Monarch rule (white 4os asks 0.79).

### 2026-10-17 19:14: the key stacks arranged for the largest free block

- The player, 19:10: "move key two cells left to make continuous 2x4 space". `cube.keys_move` (pure: the key stack
  and the free cell that makes the largest free rectangle larger) and `cube.arrange_keys` (a click takes it up,
  checked by `Pack.pointer`; a click puts it down, checked in memory; else back where it was; anything else taken up
  is put back), called once a session before its report (`Loop.leg` `arrange`). Fake: a click puts an item down on the
  cell clicked; `carried` shows the pointer. Test:
  `test_a_key_stack_that_splits_the_free_cells_is_moved_to_make_the_largest_block`. Restarted 19:14:40. Not played yet.
- The player's second ask (pick up Monarchs for 4os Deflecting, the expensive Sacred Targes): a market study runs.

### 2026-10-17 19:08: trash jewels, rings and amulets are sold

- The player, 19:06: "actually, we can sell trash jewels/rings/amus". `pickmode.sellable`: magic or rare jewels,
  rings and amulets the appraisal calls `vendor` are junk too; never a rune, gem, set, unique or crafted item. Test:
  `test_a_rune_gem_set_or_unique_is_never_junk_but_a_charm_jewel_ring_or_amulet_may_be`. Restarted at the next lobby.

### 2026-10-17 19:03: a remembered valuable keeps the place it was seen at

- 19:02:23 the Chipped Sapphire was picked up; a read in the same moment had it at (3, 3), its inventory cell, and
  `Sightings.update` moved the sighting there: "out of the read, the character 5372 away". Two trips back, then "the
  loop stops here" (19:02:25) for a gem in the inventory. `Sightings.update`: a sighting keeps its first place (items
  on the ground do not move). Test: `test_a_valuable_read_at_its_inventory_cell_while_picked_up_is_still_where_it_lay`.
  Checked the gem was picked up (log), then restarted with the loop on, 19:03:24.

### 2026-10-17 19:00: a white Void base is taken only with 3 sockets and +3 Abyss or +3 Hex: Purge

- The player, 18:56: "it looks like we're storing daggers with 1os... we need good staff mod and we need 3os; we
  shouldn't waste shared stash tab". The pickup took every white or superior Kriss, Blade, Cinquedeas, Stilleto,
  Fanged Knife and Legend Spike, sockets unread (a 0os Stilleto 17:47:19, a 0os Kriss 18:23:07); in town only `vendor`
  was sold, the rest stashed on the shared pages.
- Market study (subagent, read-only; the property ids and the Kris counts checked): scoped Traderie asks, fills and
  buyers of 2026-09-18 to 10-09. 3os +3 Abyss (prop 1579): asks median 11.4 Ist (32 sellers), fills 8.2 (23); +3 Hex:
  Purge (1566): fills 17.5 (7); buyers 14 and 4 of 26, every other skill 1 or none; +2 at best fills 1.0-1.4; 1os and
  2os no market; elite no premium of its own; 0os +3 Abyss asks 11.4 (10 sellers) for Larzuk, not taken (the
  player: "we need 3os"). Contradicts guides/warlock.html §4/§5 and guides/pricing.html §7 ("every gray elite dagger").
- `world.rolled`/`base_rolls`: a white dagger's sockets (stat 194) and staff mods (stat 107 by its layer) read off
  the ground, said in the census (`ground: normal Kriss 3os +3 Abyss ...`). `pickmode.void_base`: VOID_SOCKETS 3 and
  +VOID_LEVEL 3 of VOID_STAFFMODS {Abyss, Hex: Purge}; unread: not taken. Tests:
  `test_a_white_void_base_is_taken_only_with_three_sockets_and_a_paid_staff_mod_at_three`,
  `test_a_white_daggers_sockets_and_staff_mods_are_read_off_the_ground_and_said`. Wide suite 1866 passed. Restarted
  19:00:52. Not played yet: the ground read of an item's staff mods (stat 107 layers) is new.
- Waiting for the player: 0os +3 Abyss bases (Larzuk); the guides' Void lines to correct; the stash's stored daggers.

### 2026-10-17 18:46: the repair's stash check waits for the cost to leave the carried gold

- 18:44:57 the repair logged "gold 165932 -> 165323" for a quoted 61,006: the wait after the click ended at the
  carried gold's first move, and the stash's check was read then too. The next game read 104,317 carried
  (165,323 - 61,006): paid from the carried gold, no `repair-touched-stash.txt`. A stash deduction landing late could
  have passed that check. `repair.repair`: waits (GOLD_SETTLE_SECONDS) for the carried gold to fall by (1 -
  QUOTE_DRIFT) of the cost before the stash's check and the log. No fake test covers the repair's click; the helpers'
  tests pass. Restarted 18:46:09.

### 2026-10-17 18:29: an unreachable gold pile no longer leaves the game from Lower Kurast

- The player: "why did we exit not in act 4?" Game 22 (18:26:19): the "what is left" leg went for 5024 gold 24 units
  off, "not in view"; `pickup.collect` raised, the leg stopped, and the recovery (`Loop.recover`: abandon) did Save
  and Exit from Lower Kurast. Game 23 began in act 3: walked to the Docks waypoint, to the fortress, Save and Exit
  (25 s and a lobby lost). The level run had already given the pile up after 2 tries.
- `pickup.pick_up`: a gold pile not in view or not taken is shunned for SHUN_SECONDS and the press returns False (the
  leg goes on to the portal); other stops raise as before. Test:
  `test_a_gold_pile_out_of_view_is_left_alone_and_the_press_goes_on`. Restarted 18:29:31.
- Not changed: a game begun in Kurast Docks goes to the fortress and leaves (`next_leg` TO_THE_FORTRESS, "a game begun
  here is not the loop's to play"); going to Lower Kurast from the Docks would save that game, kept for later.

### 2026-10-17 18:06: no walk back to the waypoint after Halbu when the game is left

- Game 11's session (18:04:19-18:05:03, 44 s): Cain 3 s, the stash 12.5 s (8 s of full pages, the first visit after
  a restart), Jamella 14 s (with the second window), Halbu 4.5 s, then 8.6 s walked back to the waypoint before Save and
  Exit. The shop already left from Jamella at a game's end; the repair did not. `Loop.walks_back`: not when the game
  is left next (the chests done, no second stash due). Test:
  `test_after_halbu_at_a_games_end_the_game_is_left_from_beside_him`. Restarted 18:06:49 (the stash's page memory
  starts over).
- The stash's page memory worked at 18:04:28-36: the first visit walked to shared page 3, remembered.
- Gold: two repairs since 17:52 cost ~204k, the sales ~105k; 90,739 carried after 18:04:54, under TELEPORT_OFF: the
  stays go without Teleport until the sales lift it over 329k.

### 2026-10-17 17:55: the stash starts at the page that had room last

- 17:51:57-17:52:12 the stash took 15 s: the personal page and shared pages 1-3 full, each opened in turn before the
  fourth took the items. Today: 267 "page N is full" over 129 visits (~2 s each). `stash.Pages` (held by the runner,
  reset by a restart): a visit starts at the page that took an item last. Test:
  `test_a_visit_starts_at_the_page_that_had_room_last`. Restarted 17:55:08.
- The stash is nearly full: shared pages 4 and 5 are what is left. Told the player.

### 2026-10-17 17:47: the mercenary's life read as points; white Void bases appraised

- The player: "we usually try to reposition us that turns be slower than just take few hits and kill mobs". 15:45-17:40
  (65 stays): fights were short (78 strikes, ~1.3 s a stay); the repositioning was the mercenary's escort, 35 times,
  ~4.3 s each to the next container (2.3 s a stay; 17:35:32 warped 16 units away from a chest 17 away). Cause
  (verified): `escort.kept_alive` took the mercenary's life stat as points, but it is a share of 128
  (native/mercenary.py, the healer's reading: of 32768 raw); a whole mercenary was 128 of 2367 and "died" in 25-100%
  of the rollouts among LK trash. No mercenary death in the logs. `escort.LIFE_SHARE`: points = most × share / 128.
  Tests: `test_a_whole_mercenarys_life_is_its_most_life_in_points_not_the_share_it_is_read_as`, the hook tests on the
  share scale. Restarted 17:43:14; 0 escorts in the next 4 stays (2 expected before).
- The player: "we're storing every 3os dagger, while in reality we need something that is really good for void".
  White Void bases (`pickmode.VOID_BASES`) needed no identify, so they skipped the appraisal and were stashed. Now
  `pickmode.sellable` takes a white or superior Void base, and `junk_of` appraises it at the session (the identify
  worker's `appraise`): `vendor` is sold at Jamella's, any other verdict stashed. Test:
  `test_a_white_void_base_is_junk_when_the_appraisal_calls_it_vendor_and_kept_otherwise`. Restarted 17:46:55.
  Unplayed: what verdicts the appraisal gives white Void bases (watch `appraised white ...`).
- Strikes (the player's "we don't even need to kill some trash mobs"): the rush strikes only when hurt in the last
  2 s or with no move for 1.5 s (`hunt.HURT_SECONDS`, `RUSH_UNMOVED`); 23 of 78 fights were one cast that killed
  nothing (~0.2 s a stay). Not changed: measure the escort fix first.
- Teleport is on again since 17:43 (carried gold ~312k): the window since then is not comparable to 17:33-17:43.

### 2026-10-17 17:01: Halbu before the second stash; Teleport's gold marks lowered

- 16:54 a session zigzagged: Cain and the stash (west), Jamella (east), the stash again for a cube keeper (west), then
  Halbu (east). `next_leg`: Halbu first when due, then the stash by the waypoint (restarted 16:55:33).
- Gold: a session's sales (~40-100k) pay less than its repairs (~85k, 11-12 charges a game since 16:48); at 0.6/0.3
  Teleport would be off for long stretches. TELEPORT_ON/OFF 0.35/0.15 (329,000/141,000 at level 94; a full repair
  ~118,000 still paid from the carried gold). Restarted 17:01:40.

### 2026-10-17 16:51: Teleport decided at the first look after a start

- 16:26-16:50 measured worse: CYCLES 293 → 233 (90% [-91, -26]), a stay 21.3 → 27.3 s: 12 of 24 stays without
  Teleport (32.9 s against 26.0 with). Each restart began `Loop.teleports` False, and the carried 527,000-588,000 was
  under TELEPORT_ON (564,000): off until it rose. Now None at a start, decided at the first look: on over TELEPORT_OFF.
  Test: `test_after_a_start_teleport_is_on_over_the_lower_mark`. Restarted 16:51:52; "469682 gold carried of 940000:
  Teleport in the moves". My restarts cost this: restart less while measuring.

### 2026-10-17 16:40: the cube's plan packs larger first; Halbu's misses fail fast

- 16:39:01: a whole session one game after a full one: "room low: 2 cells free (inventory 2, cube 12, loop items 3
  ... cube rows .../.../.../...)". `cube.plan` placed smaller first: a rune at (0,0), a 1×3 Stilleto in the second
  column, the 2×2 Antlers nowhere, so `overflow` said the room was low (also the unexplained 14:15 case). Now larger
  first, or smaller first where that places more (`_placed`). Test:
  `test_an_empty_cube_takes_a_rune_a_one_by_three_and_a_two_by_two`. Restarted 16:40:30.
- 16:31:30-16:32:02: Halbu's menu opened ten times, none of ten lifts took (34 s, then no repair for 10 games; the
  character 2 units from him). `repair.lifts`: the learned lift and half a line either side only; his menu pictured
  before the second try (`shop._picture(always=True)`); `RETRY_GAMES` 10 → 3. The next visit (16:33:59) repaired.

### 2026-10-17 16:26: Teleport + the merged sessions measured; an unread repair cost

- **Measured** 15:45–16:10 (22 clean cycles, `--against 14:07 15:00`): a stay 26.8 → **19.2 s** (better), chests a
  minute 8.7 → **10.3** (better), stalls 2.9 → 1.6 s a stay (better: the quiet way budget), cycle median 49.0 → 43.3 s;
  CYCLES 268 → 274 (no evidence: 3.8 chests a cycle against 4.2, the levels' luck). RATE at 16:25: 293 over 20
  cycles, 285 over 25 (baseline 279). Town legs are now 24.5 of 43 s.
- 16:25:12: Halbu not repaired: OCR read "Tae ee" from a clear "Repair all equipment: 47449" (repair-162512.png; 8 such
  misses today). `repair.covered`: an unread (or untrusted) cost is paid when the carried gold is at least twice the
  expected and 50,000 more (the vendor takes from the stash only what the carried gold does not cover; the check after
  still turns repairs off if the stash's gold moves). Test: `test_an_unread_cost_is_paid_only_with_the_carried_gold_far_over_it`.
- The repair's logged gold after is the first step of the change (16:08:09: "719449 -> 718927" for an 80,201 quote;
  the next look read 638,726): logging only, queued.

### 2026-10-17 16:07: the gold over the cap deposited; no walk back between Halbu and Jamella

- The player, 15:58: "we repaired staff -> walked to wp -> walked to jamella". `Loop.shop_next`: after Halbu no walk
  back to the waypoint while Jamella is still to visit, and `restock(back=...)` not before Halbu. Test:
  `test_after_halbu_the_loop_goes_to_jamella_when_she_is_next_not_to_the_waypoint`.
- **Gold deposit** (`stash.deposit`, `loop.deposit_to`): at the stash with the carried gold within 70,000 of the cap,
  down to the cap less 250,000. The inventory's gold button with the stash open (layout (429, 1347) + half the
  button), the dialog prefilled with all the gold (the player confirmed), BackSpace ×8, the amount, Return, checked
  by the carried gold. The dialog sets no flag in the 0x40 panel bytes (picture `runs/alt-d/deposit-160226.png`: it
  showed "920112", OK, Cancel); so it is waited 0.3 s; a failure is pictured and Escaped. The stash opens for it with
  no item to put in. **First deposit 16:07:51: 243,212 in, 690,000 carried.** Tests: three in test_stash.py (the fake
  now has the dialog).

### 2026-10-17 15:53: any vendor errand is the whole session; Halbu less often

- The player, 15:52: "when we get to maintenance (refilling, trading, repairing) - it is better to identify everything,
  stash good, sell junk, refill, optionally repair ... right now we're running between vendors/stash/waypoint with items
  that could be already 10 times sold". `next_leg`: keys/scrolls short or the staff to repair start the session
  (IDENTIFY) when the loop carries anything (`errand`). Test: `test_any_errand_to_a_vendor_is_the_whole_session`.
- 15:45: Halbu on its own only under 30% of the charges (`repair.REPAIR_BELOW` 0.5 → 0.3; 3.9 s a cycle at 50% with
  Teleport); a session's top-up only until the session is done (`loop.tops_up`: one at a game's start sent the loop
  to Halbu again at its end for 5 charges, 15:48:43). The quiet way budget (`safety.way_seconds`, 0.15 s with no
  hostile within 30 units) went live with it: measure the cold-way waits (1.1 s a game before).
- The gold cap still blocks sales near 940,000 (sessions short of the contract, then again a game later): the
  player: "probably we need to move extra gold to our cube [stash]": the deposit is designed (the inventory's gold
  button with the stash open, the dialog prefilled with all gold, the player confirmed), not built: the dialog's panel
  flag is unknown, so the first build reads every flag before and after the click and types only with one new.

### 2026-10-17 15:37: the repair before the sales near the cap; Save and Exit past a late panel

- 15:33:27: a session sold nothing at 908,518 of 940,000, then the repair spent 39,237 (the sales' room). Now a
  session near the cap repairs first (`Loop.capped`, `next_leg`). Test:
  `test_near_the_gold_cap_a_session_repairs_before_it_sells`.
- **Stop** 15:35:47 "quit menu: not seen in 2s": `repair.back`'s walk ended with a click on the waypoint, whose panel
  opened at 15:35:43.4, after `leave_game`'s panel check; the swaps did not take, Escape closed the waypoint panel, no
  quit menu, and the loop stopped. Now each Save and Exit try closes the panels open then and asks for the quit menu
  again (`QUIT_MENU_SECONDS`). Test: `test_a_panel_that_opens_after_the_first_look_does_not_keep_the_game_from_being_left`
  (fails on the old code). Restarted with the loop on at 15:37:26.
- 15:32:02: a stop by key code 55 held (`v`, not the macro's): the player's, confirmed ("it was me").
- Measuring now: Teleport by gold (since 15:28:50), 30 cycles, against 14:07–15:00 without Teleport (275 / 257).

### 2026-10-17 15:28: gems never left; the gold cap; Teleport paid by surplus gold

- **Loss** 15:19:42 and again later: a Flawless Amethyst left on the ground, the player: "we just left flawlest amethyst
  and left the game. something is wrong". Cause: `full-stacks.json` held 575 and 585 (Flawless Amethyst, Sapphire), so
  the pickup skipped them like the 99 Tal Runes. The ruling was the runes'. Fix (15:23:28): `Loop.sold_full` (runes
  only) for the pickup and the sale; gems are always picked up, tried at the stash at every visit (15:28:50), never
  sold. The player: "for gems - we need to cube 3 flawless -> perfect" (cubed some by hand at 15:27); the loop's own
  transmute is queued. Test: `test_a_full_stash_stack_skips_its_rune_but_never_a_gem`.
- **Gold cap** (the player: "selling things over this gold limit - just drops extra gold on the ground"): the cap is
  level × 10,000 (level 94: 940,000); 926,683 carried at 15:28. `shop.restock` sells nothing that could pass it
  (`SALE_MOST` 35,000), and nothing with the level unread. Tests: `test_no_sale_may_take_the_gold_carried_over_the_cap`
  and two more (the fake now sells).
- **Teleport by gold** (the player: "if we make enough gold - we can use teleport staff more often"): `loop.teleports`
  from 60% of the cap, off under 30%, `travel.LOOPED_TELEPORT` (hop_from 0) set on the hunter per leg. 15:29: on;
  ~69 charges in the first game; Halbu 56 → 69 for 22,720 gold. Expected ~282 chests an hour of cycles (as before
  13:36), at ~12k gold a cycle against ~6k of sales.
- Not done: speed's "walked way still being grown" (1.1 s a game, 268 waits in 78 games): the flight already grows it
  without a bound, the waits are the next chest's cold field after each opening; candidate: a bigger way share in the
  quiet, or pre-growing the next mark's field while the chest opens.

### 2026-10-17 15:02: the arrival probe kept; the trade session's dead clicks

- **Measured** the probe 14:36–15:00 (25 cycles, `--against 14:07 14:36`): town legs 24.7 → **23.9 s** a game (−0.8,
  90% [−1.5, −0.1]: better), as expected; took input → `there` 0.32 → 0.07–0.12 s; no swap back failed. CYCLES 279 →
  257 (no evidence: chests a cycle 4.2 → 4.0, the chests leg unchanged). **Kept.**
- **Candidate** (15:02:12): two dead waits in a trade session. (1) `cube.unpack` clicked cube items the inventory had
  no block for, twice each (3 s an item: three at 14:51:04–14, the identify leg 27 s); now it passes over them
  (`room_for(inventory_rows(...))`), and the session's second stash takes them. (2) `shop.restock` clicked the Misc
  tab and waited for each kind already full (0.7 s: the Tome of Identify every visit); now it checks the count first.
  Expected 1–10 s a session. Measure: the identify and 'scrolls and keys' legs; `trade session done` still clean.
  Tests: `test_a_cube_item_the_inventory_has_no_block_for_is_not_clicked`, `test_a_kind_full_already_gets_no_tab_click`
  (both fail without the change).

### 2026-10-17 14:36: "No Teleport, high-value trade" kept; a faster arrival probe

- **Measured** 14:07–14:32 (25 cycles, `speed.py --against 02:43 04:31`): CYCLES 279 → **275** chests an hour of cycles
  (−4, 90% [−25, +19]: no evidence), game 51.4 → 47.5 s, chests a minute 8.3 → 9.3. **Kept**: same chests, no charges
  spent, so no repairs. Trade sessions every ~6 games, each ending as the contract says (`trade session done: cube 0
  items, 10 inventory cells free, junk left 0, keys 12, portals 20, staff 69/69`). Sales of 35,000 (Cinquedeas, Sun
  Spirit, Horned Helm); a unique amulet (Mara's?) appraised 'sell' and stashed.
- 14:17: a diagnostic `loop: room low: ...` line at the trade's trigger (loop.py). Game 9 at 14:15 began a session one
  game after a full one (3 pickups, cube empty): not explained yet. The two triggers logged since (14:25, 14:31) were
  real (a cube whose free cells no carried item fits).
- **Candidate** (14:36:22): the arrival probe (`routines.took_input`). The swap back took 0.32 s, 0.2 of it the settle
  meant for after a cast (the character stands on arrival), three times a game. Probe swaps that took showed 0.05–0.2 s
  after the key (249 of 249), so PROBE_WAIT 0.35 → 0.25. Expected **0.6–0.8 s a game**. Measure: took input → `there`
  (0.32 s now), the `took input` times, and no `the swap back ... did not come` line. Test:
  `test_an_arrivals_probe_swaps_back_without_a_settle`.
- Noted, not changed: "Shop check failed: Shop stock changed during scan" is the HUD's shop reader seeing the sales
  (it retried complete 2 s later); an ERROR with a traceback for a benign retry. The second restock pass sells cube
  items whose first take-out failed: not wasted.

### 2026-10-17 12:06: the trade at Deckard Cain, in batches; the shop only for what is needed

The player, 11:50–12:05: "aim to sell at least 2 items ... both from cube and inventory"; (chosen) "identify each game,
keep junk until 2+", then "not all rolls are good sell, but every class specific item can roll 35k. we need to perform
mass identify at decard cain -> stash good -> sell junk -> return to loop"; "refill when we have to sell something,
and keep bare refills at minimum ... measure shopping time".

- Built: `macros/cain.py` (Cain, monstats 246 `cain4`, at (5023, 5033): his Identify Items line found by lifts, checked
  by the items' flags; learned 0.2052 at 12:01:21; the tome the fallback). The loop's trade (loop.py MASS): unidentified
  items wait in the inventory or the cube; Cain when 3 are carried or fewer than 8 cells are free; the stash's next
  visit forced for the keepers, the junk and the unidentified kept out of it by unit (`unload(keep=)`); the junk judged
  at each look in the fortress by `IdentifyWorker.appraise` (by unit id, so across games and moves); Jamella with 2 or
  more to sell, the cube's junk taken out first. `shop.USUAL`: Jamella, Halbu, Cain walked toward at their usual places
  when out of the units' reach (from Cain's place Jamella was not in sight, 12:01:23: a recovery). The Tome of Identify
  no longer makes a visit (`short`). Repair: the font's 0 read as Q ("1Q1677" for 101,677, 11:54 and 11:59: no
  repair): `repair.LOOKALIKES`; repaired 12:04:09, 9 -> 69 charges for 101,677. games.py: a full stack's gem is not
  MISSED. Tests: test_cain.py (2), test_loop, test_repair_quote, test_shop; wide suite 2255 passed. Restarts 11:59:47,
  12:03:56, 12:06:03.
- Sales 11:38–12:06 (trade.py): 15 junk items, 164,902 gold (162% of the repair), ~488,000 gold an hour of play; Jamella
  5.0 s a game, Cain 1.9 s. By kind: magic/rare grimoires pay back 1.0–1.3, Barbarian helms and daggers 0.7 at one item
  a visit, charms 0.01–0.04. Batch of 12:05:51: magic Mithral Point 35,000, rare Stilleto 35,000, magic Amulet 2,195.
- 12:08–12:15: the repair's cost guard compared a partial repair (62,918 for 37 charges) with the whole last quote and
  refused it: now the gold a charge (`repair.expected`, QUOTE_FILE "cost charges"). The carried gold read at the
  click had not moved (208,801 -> 208,801 for 69,696): the check waits for it (`GOLD_SETTLE_SECONDS`); the loop's own
  log at 12:11:08 showed 139,105 carried, the repair paid from it. The player: "you don't need to read stash gold,
  just use gold in the inventory": the loop logs the carried gold once a game. The cube's Grand Charm stayed unsold
  (taken out before the sales, no room, 12:13:06): the inventory's junk is sold first, then the cube's taken out and
  sold. The forced stash at Save and Exit found no stash in sight from Jamella's (12:13:16): the stash is visited at
  once after Cain, beside him (the stash at (5019, 5040), `stash.USUAL` when out of sight). Restarted 12:15:21.
- Repairs: 12:04:09 (9 -> 69, 101,677), 12:09:40 (28 -> 69, 69,696), 12:14:44 (28 -> 69, 69,479): about every 5
  games, ~14,000 gold a game. Carried gold 95,287 after the last.
- The player, 12:20: "did you measure all time, not just level? ... iterations starts on LK arrival, and loop ends on
  the next LK arrival": speed.py CYCLES (the measure from now on). 02:43–04:31: 113 cycles, 4.4 chests, **279 chests an
  hour**; 10:33–10:51: 285; 11:38–12:22: 29 cycles, 4.1 chests, **255** (-23, 90% [-45, -2]: worse). A cycle now: the
  chests 24.7 s (29.6: the Teleport charges), Jamella 4.4 (0.8), Cain 2.6, repair 0.6: the trade costs ~6.8 s a cycle
  against ~5 s the charges save. The whole-games YIELD (295) left out the games recoveries cut.
- Speed round 12:22:28 (restart): fewer, bigger trade visits, MASS 3 -> 4 (Cain), SELL_BATCH 2 -> 3 (Jamella; any junk
  when fewer than 8 cells are free). Expect: Jamella + Cain under ~6.8 s a cycle, CYCLES not worse. Measure after 30+
  cycles: `speed.py --since '2026-10-17 12:22' --against '2026-10-17 11:38' '2026-10-17 12:22'`.
- The player, 12:23: "maybe chest per hour, some sliding metric to steer": watch.py `RATE:` every 5 cycles, chests an
  hour over the last 20 and 60 cycles against the baseline 279 (run with `uv run --offline python -u`). The 13 uncut
  cycles of 11:59–12:22 (many restarts): 242.
- 12:26–12:27: three recoveries in a row stopped the loop: a greyed waypoint row (12:26:03, once) left a game in Kurast
  Docks, and from the docks' start the walk to the waypoint (~130 units) ran out of its 16 clicks 2 units short
  (12:26:25, 12:26:53); beside Halbu the same at 12:10:04. `shop.WALK_CLICKS` 30. Restarted 12:27:55.
- Hourly chests an hour of cycles (the player: "calculate chest per hour for 4 hours"): 08:30 265, 09:30 254 (15
  cycles), 10:30 **279**, 11:30 246.
- The player, 12:30–12:33: "trade not by 2 junk items, but by remaining free slots"; "we should aim for runs where
  identifying is triggered: we moved all good to our chest, moved all resources, sold all junk, refill tp/keys,
  repaired staff if we can afford it; thus -> have full cube free slots + some free inventory slots"; "we do not need
  to go cain every game". Now (loop.py TRADE_ROOM 8): one session, once a game, when fewer than 8 cells are free in the
  inventory and the cube together and the loop carries anything: Cain only with something to identify, the stash
  (keepers, resources, the cube emptied), Jamella (all junk, keys, scrolls), the repair at the next game's start if
  the carried gold covers it. No stash visit outside a session; in town with under 8 inventory cells the loop's items
  go into the cube (`make_room`). Restarted 12:31:57, 12:33:31. Measure CYCLES and RATE from 12:33.
- 12:33–12:41: RATE 285 over the first 10 cycles. The first full session (12:38): Cain identified 7, sold a Wolf Head
  20,091, a Circlet 21,649, a Kriss 10,227 (51,967); a Bone Knife (`check`), a rare Amulet and two Jewels kept; the
  session's game 93 s. Fixes (stops, not steering): the repair's tooltip read '' as a line (repair-123918.png,
  "101803": `repair.PAGE_MODES` 7, then 6, then 13; 6 reads all twelve pictures of the day); from beside Halbu the
  waypoint was listed in sight 37 units off and no aim reached it (12:39:25, a recovery; also 12:10:04): `repair.back`
  walks toward it after every visit to him. Restarted 12:41:31: the CYCLES window of the session design runs from
  12:33:31 (one cut at 12:41).
- 12:41:43: the cost read (101,803) and refused by the 90% margin (107,753 carried): `repair.CARRIED_SHARE` 0.98 (the
  gold a charge catches misreads). 12:42:58 repaired 9 -> 69 for 102,020, carried 108,820 -> 6,800. RATE 285 (15).
- 12:45:41 the loop stopped: a Magic Rage Mask, a candidate with no room, warned "Inventory full ... left on the
  ground"; the runner's watchdog (made for the stand-by by a valuable) took it for one, in the lobby too, cancelled the
  game's creation twice, and "not in a game" while it loaded made three recoveries in 20 ms. Fixed: the watchdog only
  for "... make room" in a game (runner.py); a loading game is waited for (`LOADING_SECONDS`). Why no session before:
  the cube's 9 free cells in pieces no item fit ('.#./.#./.#./...'): the room counted as none then (`overflow`).
  test_loop (13). Restarted 12:47:13, 12:48:33.
- 12:48:41: a visit for keys came first, then the session (Cain 12:48:49): its junk not sold that game (sold the next,
  12:50:11). The session's identify leg allows Jamella again (`shopped` reset). Restarted 12:51:06: the 30 cycles of
  the session design are measured from here (steer after analysis).
- The player, 12:55: "analyze our trading behavior". 12:33–12:55 (trade.py, speed.py): 16 uncut cycles, **276 chests an
  hour of cycles** (255 before the sessions, 279 the best hour); the trade 4.4 s a game (Jamella 2.4, Cain 2.3; 6.8–7.0
  before). 13 identified (12 `vendor`, a Bone Knife `check`); 6 sold for 79,008 (13,168 a sale), the sales 77% of the
  repair of 12:42. By kind: Druid pelts, circlets, grimoires, daggers 10–24k a sale; helms, charms, javelins under
  3k. Defects the analysis and the player found: the session's stash moved its junk into the cube (12:53:57) and only
  one of four came out for Jamella (12:54:10; the player: "we had space to move more item and sell them all"); a
  Jamella visit: walk 3.6 s, her window at 5.6 s, the stock at 6.0, the first sale at 8.9 (a gold-settling wait), done
  9.4; a second pass opened her window again (~6 s; the player: "we spend a lot of time just to open trade window").
  Fixed: the session's junk stays in the inventory (runner `stash_loot`); `cube.unpack` clicks an item twice and passes
  over one that does not come out; the cube's junk comes out before her window opens, one window sells all; no gold
  settling before the sales (nothing bought yet). Restarted 12:55:50, 12:57:40, 12:59:21.
- The player, 13:04: "remember and enforce my previous instructions about what should happen when we're deciding to
  identify and trade. we must go to LK with all refilled and empty cube and free inventory slots (without selling our
  own gear, just junk)". The contract (memory `d2r-trade-session-contract`, SKILL.md rule 3b). Enforced: no
  `make_room` in a session (at 13:03 it moved the session's junk into the cube first); in a session any missing charge
  is repaired if the carried gold covers it, a session at a game's end repairs before Save and Exit; the session's end
  says `trade session done: cube N items, F inventory cells free, junk left J, keys, portals, staff` ("short of the
  contract" when the cube or junk is not empty or keys/scrolls short). test_loop (14). Restarted 13:06:06.
- The player, 13:09: "it looks like we're constantly low on tp charges, probably it worth to analyze whether it worth
  to have tp or trading/repairing doesn't really cover time difference". Since 10:30, 112 cycles: with charges (41,
  median 7 casts) **282** chests an hour of cycles, without (71) **258**; the chests leg 23.5 s against 27.7; the
  morning's (no TP, no trade) 279. Gold 12:11–13:08: repairs 333k an hour (1,700 a charge), sales 272k, pickups ~9k
  (inferred from the carried gold, uncertain): ~-52k an hour, so the charges run dry. ~2,800 gold a second saved.
  Most casts were the last 14–20 units to a chest in Blade Warp's delay, often with a weapon swap. The player chose
  selective charges: the loop's move hops only toward a goal 40 units and further (`travel.HOP_FROM`,
  `Intent.hop_from`, `movement.hops`); test_pursuit. Expect: ~2–3 casts a cycle, the chests leg near 24–25 s, repairs
  covered by sales, CYCLES near 282.
- 13:12:16 the first session line: "short of the contract: cube 1 items ... staff 9/69": the repair refused at
  102,206 with 104,270 carried (98%): `CARRIED_SHARE` 0.99; a 1 x 3 Blade did not come out of the cube after smaller
  ones (13:11:52): `cube.unpack` takes the tallest first. Restarted 13:14:30: the selective charges' window begins.
- 13:14:42 repaired 9 -> 69 for 102,206 (carried 104,270 -> 2,064). 13:16:16 "short of the contract: cube 2 items":
  the session's stash, beside Cain, came before the sales; the inventory full of junk, three of the cube's keepers
  did not come out (13:15:47–54). Now the session goes to the stash again after Jamella when the cube still holds
  items (`STASH` leg, once a game). test_loop (16). Restarted 13:17:25 (a failing test hidden by `| tail` was
  chained into that restart: only the test needed changing; SKILL.md Fix step 4 warns of it).
- 13:24:09 the tooltip "50548" read as "5@548" (the font's slashed 0): `LOOKALIKES` '@', 'Ø', 'ø'. Sessions met the
  contract from 13:19 (cube 0, junk 0, keys 12, portals 20, the staff topped up by the session's repair).
- 13:36 analysis (13 cycles since 13:14): **221** chests an hour of cycles (279 -> -57, 90% [-86, -26]: worse); a
  cycle: the chests 27.3 s (selective charges, 3.3 casts a stay, bought no time: 27.7 with none), Jamella 5.4,
  Cain 4.7, repair 1.8, stash 0.8: the trade ~12.7 s a cycle, sessions every 2–4 games at ~45–50 s. Sales by kind
  since 11:26: Paladin shields 32.5k a sale, rare daggers 35k, claws 22.5k, magic daggers 20.2k (15), circlets
  15.4k, grimoires 14.1k (11), Barbarian helms 13.3k (10), Druid pelts 12.4k; magic amulets 2.2k (8), javelins 1.1k.
  The player chose "No TP, high-value trade only": `travel.HOP_FROM` inf (no Teleport in the loop), the candidates
  without the Amazon's bows, spears, javelins and the magic amulets (`pickmode.SKILLED`). The selective rule's own
  defect, seen at 13:58:07 (40 s stood: "the move found brings the goal no nearer by the way"): the way measured by
  hops past 40 units and on foot under, a move across the line no nearer; gone with no hops at all.
- 13:52–14:01: four recoveries in 9 minutes (Save and Exit not left in 10 s twice, the stand-by above, Consume once)
  stopped the loop at 14:01:27; the watch had lapsed (re-armed late), the player saw it first ("you have stopped for a
  long time in the town"). Fixed: Save and Exit clicked up to three times, 4 s each (`routines.LEAVE_TRIES`).
  Restarted 14:05:54 (the trade and TP changes), 14:07:42 (Save and Exit). The measure of "no TP, high-value trade"
  runs from 14:07:42.
- The player asked the best find since yesterday: an Ohm Rune (13:57, ~4.05 Ist, the ladder of 2026-09-18), Titan's
  Revenge (13:43, appraised `slow`, no market row offline), an Ist Rune (04:57).

### 2026-10-17 11:16: items with skills identified and appraised; the junk to Jamella (plan §15)

- Built §15: `pickmode.candidate`/`is_candidate`, `junk.py` (Tome of Identify, `junk`), the loop's IDENTIFY leg,
  junk kept out of the stash and sold at Jamella (`shop.restock`: each sale checked, the carried gold logged),
  `IdentifyWorker.verdicts_now`. Also: speed.py's teleport section (06:51–10:51: a stay 23.6 s with a charge against
  30.6 s without). Tests: test_junk.py, test_pickmode, test_loop, test_sightings; wide suite 2248 passed.
- 11:17:30 game 1: a magic Tiara (Damage Reduced by 3) and a magic Spirit Mask (+86% ED) identified with the tome
  in 1.8 s, both appraised `vendor` 0.4 s later. **Defect:** the lobby's leg read no inventory and cleared the junk,
  so game 2 had no shop leg and its stash put both into the shared stash (11:17:50). The player, 11:18: "we identified
  items that aren't worth keep and moved them to storage instead of selling. so, we got no money, no storage space".
  Fixed: the junk is pruned only when the inventory is read (test_loop). Restarted 11:19:16 with the loop off (the
  player turned it off at 11:17:52).
- 11:21: the player: "implement correct behavior first, then unpause". The junk is now sold in the same game: in the
  fortress, identify (at a game's end, and at its start for what is left unidentified), then Jamella (once a game),
  then Save and Exit; the shop fills the Tome of Identify. test_loop (2), test_shop. Restarted 11:21:28, loop on.
- 11:23:47–11:23:55 (game 3): identified 2, both `vendor`, sold at Jamella in the same game: magic Demonhide Gloves
  and a **magic Large Charm**; carried gold 98,616 -> 105,457 (+6,841). The charm was a sure valuable sold by
  mistake: the junk rule took any loop item appraised `vendor`. Fixed to the identify-only kinds
  (`pickmode.identified_for`), then the player, 11:25: "you can sell identified junk charms" (`pickmode.sellable`:
  magic or rare charms too; never jewels, rings, runes, gems, sets, uniques). test_junk.
- 11:23:58: Save and Exit not done in 10 s, then the game lost the focus (the player at another window, writing);
  the player's KP_6 at 11:24:41 and 11:24:45 stopped at the mouse moved and a key, then "Save and Exit again and
  again". Not a code defect seen.
- The player, 11:26: "you need to measure our trading efficiency time/gold, what we pickup, what we sell it for":
  `tools/trade.py`; the log now names each item appraised and the gold each sale brought. Restarted 11:26:25, loop on.
- The player, 11:29: "some metric for picking up items for trade: type vs space vs time to trade to gold per
  trade/per occupied cell": trade.py's table by kind, with the payback (the seconds its gold buys as Teleport charges
  over the seconds it cost). The rate: after the 10:33 repair the staff spent 7.5 charges a game, its 69 charges
  lasting 8 games; at 1,742 gold a charge and ~7 s saved a game (not proven), a second costs ~1,870 gold. A 5,200 gold
  glove that costs 1.5 s to pick up, 2.2 s to identify and 6 s of a selling visit pays back 0.29: the visit is the
  cost. Lever to try once the table has data: sell only when the visit is made anyway (keys/scrolls short) or with
  several junk items carried.
- 11:33:23: a magic Grand Charm appraised `vendor` sold for 435 gold (the visit 10 s, keys and scrolls bought too).
- 11:29:56: the inventory full (the player's own items leave a few cells): an Ethereal Rare Circlet left on the
  ground, the loop's items moved into the cube.
- The player, 11:35: "the most gold cost is weapons and items that can give +skills (35k for good rolls)
  blades/daggers/necro/sorc, also class specific offhands can roll. charms - aren't usually gold source, but we're
  picking them in hunt for a good rolls. usually it worth to sell in batches, when low inventory space, rather than
  every loop". Changed: the candidates are the class items (weapons, off-hands, helms), circlets and magic amulets
  (gloves, boots, belts dropped); junk is sold when the loop's items take over half the room (`SELL_ABOVE`) or on a
  visit made for keys and scrolls; the junk is kept in `runs/alt-d/loop-junk.json` across restarts. test_loop,
  test_pickmode, test_junk. Restarted 11:38:01, loop on.
- 11:37:28: repaired, the staff 9 -> 69 charges, carried gold 124,550 -> 22,215 (102,335).
- 11:41–11:44: a visit nearly every game: half the loop's room is one Grand Charm and little else, the player's own
  items leaving few cells. Now a batch is sold when fewer than 8 cells are free (`SELL_ROOM`: a 2 x 4 shield no
  longer fits), the free cells logged. Save and Exit failed twice after an end-of-game visit (11:42:32, 11:44:41: the
  run back to the waypoint still under way, the weapon swaps not taken, the quit menu not seen): at a game's end the
  shop no longer walks back (`restock(back=False)`). A Grand Charm's sale read -140 gold twice (the purchases' cost
  landing late): the shop sells first, then buys. The Tome of Identify read and refilled (18 -> 20). Magic Codex:
  `check`, kept. Restarted 11:44:58 and 11:46:21.

### 2026-10-17 11:00: inactive time and going back measured; shack containers only beside a chest

The player, 10:55: "lower amount of out-of-shacks interactions ... interact only with interactables directly visible
from superchests within small radius"; "add measurement that will measure inactive time ... and backtracking
movements"; "feel free to launch loop again" (restarted 10:56:10, loop on).

- Measures (`combat/legs.py` `Leg.idle`, `Leg.delay`, `Leg.away`, `quiet`; `speed.py` section 4 and three
  `--against` measures). Idle: still (under 0.5 units a frame), neither casting nor moving, no input sent within
  0.3 s, not the loading screen (view byte 0); within 1.05 s of a cast's start it is Blade Warp's delay, apart.
  The baseline 02:43–04:31: on the level 3.9 s idle a stay of 31.1, plus 6.8 s in the warp's delay; Kurast Docks
  0.2 s a game; Pandemonium Fortress 1.2 s a game; going back 14 units a stay (~0.7 s at the warp's pace). The
  worst legs went back 19–35 units. test_legs.py.
- Shack containers (`shacks.py` BY_CHEST 15 units, a clear line from the chest's spot as well as from the character):
  the night's logs had 636 shack container goals; by the camp's file only the weapon rack (12 units from the chest at
  (60, 12)) is beside a chest; the armor stand (32–34), the rolled baskets (27–29) and jungle chests (25–35) are left
  now. test_shacks.py (7). Wide suite 1814 passed. Restarted 11:02:25. To check: "others a stay" falls from 3.1,
  the stay shortens, chests a stay unchanged, YIELD not worse.

### 2026-10-17 10:30: remembered valuables built; the repair's cost read fixed

- Built the plan's §14 (`macros/sightings.py`; runner `_sighted`, `_fetch`, `_valuable_left`; world.py
  `GameMemory.where_area`): the loop keeps every valuable its pickup would take in Lower Kurast until it is off the
  ground; the "what is left" leg goes back for one no press took (2 trips, 40 s a game, then the loop stops for the
  player); the guard counts them. The census's `ground_seen` is shared by the runner: an item is said once.
  Tests: test_sightings.py (6), test_runner.py (the fetch). Wide suite: 1806 passed.
- To verify in play: `Macro: remembered ... out of the read, the character N away` (the client's reach),
  `gone back for it (trip N)`, and no `MISSED:` from the watch.
- 10:31:02: the repair's tooltip was read as noise and nothing was repaired (155,824 gold carried, the tooltip said
  111,469). The picture was 1400 × 330 with the stash's items in it; now only the band over the button (720 × 90,
  `--psm 7`) and the last long number of it (`repair.cost_of`): it read all ten pictures of the night.
  test_repair_quote.py (6). Restarted 10:32:55.
- 10:33:13: repaired at Halbu, the staff 5 → 69 charges, carried gold 155,824 → 44,355 (the quoted 111,469); the
  stash's gold untouched.
- 10:33–10:50, 20 games (the player turned the loop off at 10:50:09): median 51.2 s, 69 games and 280 chests an hour
  (the baseline's yield; ±50, no evidence either way), macro stalls 3.4 → 1.7 s a stay (better: 90% interval
  excludes 0), the stay 27.0 → 22.9 s (no evidence yet). No MISSED, no recovery, no stop; no trip back was needed
  (no `remembered` line: every valuable seen was picked up where it lay).

### 2026-10-17 10:50: lost valuables over the night (the player: "check if we have lost something valuable")

- 693 games 22:00–09:48: five valuables the sure mode takes were never picked up (the plan's §14 table): a Flawless
  Diamond (a recovery, guarded since 01:21), a set Ring and a set Amulet (`pickmode.sure` took rare jewelry only), a
  Small Charm in a pile (presses failed) and a Flawless Emerald seen off the route (forgotten).
- Fixed: `pickmode.sure` takes set and unique rings and amulets (test_pickmode.py; test_pickmode and the runner's
  pickup tests pass). Deployed by a restart with the loop off; not played yet.
- `games.py`: items matched to the pickups by the place aimed at, then by name (a pile's later items); a game a
  restart cut is checked against the next session; MISSED (the sure mode takes it) apart from what is left by
  design. `watch.py`: a `MISSED:` line at the end of every game.
- Designed, not built: remembered valuables (the plan's §14).

### 2026-10-17 10:30: the speed analysis tool (no game change)

- `tools/speed.py` added. It answered the "chests leg +7 s after 04:34" question: no regression. The yield was 280
  chests an hour before and after; stays opened more chests (median 3 → 4). Off the queue.
- New candidates 1–5 above come from its stall ranking over 04:34–06:50.

### 2026-10-17 night (00:00–09:56): the first watched night

- Watched with the scratchpad watcher (now `tools/watch.py`). The loop ran unattended for hours.
- Added: stash visits over 50% occupancy (`stash.unload`: through the inventory, resource tabs, personal tab, then
  the shared pages by their arrows); full stash stacks not picked up and sold at Jamella; rare amulets picked up; the
  ground census; Halbu's Repair All on carried gold only (the tooltip's cost read by OCR, the stash's gold checked
  after: `repair.py`; the first repair 0 → 69 charges, 137,369 → 15,050 carried gold, stash untouched).
- Guards: a game is never left while a valuable it would pick up lies on the ground (`runner.valuable_left`); a stop
  by the player's hand retries the leg; the watchdogs pause during a focus wait; make-room once a game.
- Faster: strikes only on attackers in the loop's run (strike casting 4.1 → 1.4–2.1 s a stay); CHEST_BRINGS 0.25 → 0.1;
  a refused warp no longer adds a dead end; terror zones no longer force a full clear on the loop's run.
- Fixed: the click geometry from the game's layout files (vendor panel, stash tabs and arrows), the menu line from the
  point drawn when the menu opened, per-vendor lifts learned in `runs/alt-d/menu-lifts.json`; the pointer shift on
  panel changes (`actuator.rebase`); waypoint path walks from Kurast Docks; a close waypoint stepped back from.
- Mistakes: a recovery left a game with a Flawless Diamond on the ground (the guard above came after); a potion was
  wrongly marked as a full class and one Full Rejuvenation Potion was sold (`stash._potion`).
- Not committed: everything above (the player commits).
- 09:48:50: the player turned the loop off (KP_6). 09:56: the watch was paused at the player's ask.

### 2026-10-18 18:10 — stall study and rulings

- `rca/2026-10-18/stalls-findings.md`: 25 firings of the 45 s watchdog from 10-16 to now (count checked); 5 real no-room,
  4+ standing at Andariel's mark after a restart, 7 refused Gheed's charm, 7 path dead ends, 1 focus wait, 1 at 17:58.
- Rulings: no room only when it is real; kill memory only for Andariel; a dead end skips the goal. The 17:58 game
  (Teleport cast but no move, Save and Exit ×5 failed): the player says it is our code — an RCA runs
  (`rca/2026-10-18/freeze-findings.md`).
- Loop agent done (Q1 in the loop: hold → cube → trip); 381 focused tests pass. Waiting for the reload: town agent,
  F1/F3 agent, then the wide suite (player, 18:03: reload only after the agents finish).
- Waiting for the player: LK has no trip, so no room there drops an unidentified carried item even for a cheap find.

### 2026-10-18 18:25 — agents done; visible-loot rule

- F1/F3 agent done: `pursuit.RUSH_THE_BOSS = True` (F1), `buffs.QUIET_BY_THE_BOSS = False` (F3, flip after ~30 games of
  F1). 468 tests re-run here pass.
- Town agent done: `town.KEEPER_IN_CUBE = True` (a keeper with a page but no way out waits in the cube); rune stacks over
  80 cubed down (El..Ort, gem-free; recipes from cubemain.txt via `build_rune_cube.py` → `data/rune_cube.json`), 3 a
  visit; rune sales stopped. Thul and up need a gem: not cubed (a ruling for the player). 156 town tests pass here.
- Game 40 (18:22:16): the run teleported 3.5 units past a Ko Rune not read yet, first read it 34 away behind, ran on
  ("not on the way"); the player stopped the loop and took it. Ruling (IMPORTANT): loot visible before the run starts,
  a valuable seen is taken now. A fix agent is on it (arrival wait for the loot read; valuables in the read taken).
- Reload waits for that fix, then the wide suite.
- 18:27:27 restart (`20261018T152722Z-44de31b1`, the player: "restart on the next town"): wide suite 2320 passed first.
  Live: F1, keeper in cube, rune stacks cubed to 80 (3 a visit), no rune sales, Q1 hold → cube → trip in the loop.
  Not yet live: the visible-loot fix (agent working), the stall rulings (room only when real, dead end skips the goal).
- Freeze RCA (`rca/2026-10-18/freeze-findings.md`): not the server. The game took our keys but not our pointer moves
  or clicks from the level load on; the first hop landed on the stale cursor spot (the town waypoint row). Teleport's
  own no-move check is cut off by `priced_for` (~1.4 s), so it was replanned 10×. Fix A (detect a lost pointer, fail
  fast, log XQueryPointer's window) then B (Save and Exit by keyboard) recommended. Open: where was the real mouse?
- 18:42:09 restart (`20261018T154203Z-045794c2`), wide suite 2332 passed. Live now: gem rune recipes (Thul/Amn with
  Chipped Topaz/Amethyst from the Gems tab; never a Ber), and the visible-loot fix. Cause of the Ko Rune (verified in
  take 20261018T152213Z-35): a fresh drop (monster 2809246671 died at t=3.41, rune read at 3.49), 34.5 straight but
  117 walked behind a wall, so `on_the_way` (walked ≤ PICK_NEAR 40) refused it. Fix: on the loop's Teleport run a
  valuable is taken when Teleport reaches it within 2.5 s; and the first move on a level waits until 2.0 s after the
  arrival (item units near the arrival appeared 0.74–1.89 s late in 20 of 2211 cases). Cost expected ≈1.5–2 s on
  Catacombs 3 and 4 each (~3.5 s a game). Measure kills an hour against 84/h.
- 18:47 the player: the arrival wait is "totally wrong. we DO not need to wait. we MUST check if loot toggle is
  enabled". Verified in `runs/osd/.../osd.log`: game 40 (18:22:02-07) `make osd` pressed Show Items 3 times during the
  load and gave up ("still off after 3 presses"). The 2.0 s hold is removed (hunt.py, runner, engine, journey back to
  as before); `World.show_items` reads the toggle's byte (UI panels + 0xC) and `routines.show_items_on` presses the
  character's Show Items key before every loop level run (≤3 presses, else Abort). The Teleport-reach valuable rule
  stays. Gem step: Ctrl+Shift+left click moves 1 gem (the player, 18:48).
- 18:50:03 restart (`20261018T154958Z-f1eb20c4`), wide suite 2332 passed.

## Handoff — 2026-10-18 19:00

**State.** `make serve` session `20261018T155841Z-a09873cf` (restart 18:58:47; F1 window from 18:50:03), the loop on, kind Andariel; `make
osd` running (Show Items presses, healer). Watch: monitor on `tools/watch.py` (re-arm every 30 min). No agent running.
Nothing committed (branch `combat-framework`, a large uncommitted tree: the player says "commit").

**Live since 18:50 (wide suite 2332 passed before it):**
- F1 `pursuit.RUSH_THE_BOSS = True` (since 18:27); F3 `buffs.QUIET_BY_THE_BOSS = False` (flip after F1 is measured).
- Town: keeper waits in the cube (`KEEPER_IN_CUBE`), junk parked on a page (`PARK_JUNK`), stash full stops the loop,
  best copy kept (`copies.py`), rare amulet rule; rune stacks over 80 cubed toward 80, 3 a visit, gem recipes with
  the gem from the Gems tab by Ctrl+Shift+left click (7.3 s for 3 at 18:54); no rune sales; never a Ber.
- Loop: a valuable with no room → hold, cube, trip (`lootpolicy`, `pickup`, `runner`); a valuable Teleport reaches
  within 2.5 s is taken now (`hunt.on_the_way`, `LOOP_PICK_SECONDS`); Show Items checked before every loop level run
  (`routines.show_items_on`, `World.show_items`). The 2 s arrival hold was removed (the player: "totally wrong").

**Live since the 18:58:47 restart (`20261018T155841Z-a09873cf`, wide suite 2333 passed):**
- `loop.Loop.count`: a leg over its count is counted afresh after its stop (18:55:34: the player's mouse in the lobby
  twice, then 4 "next game again and again" recoveries in 20 ms and a 30 s hold). Test
  `test_a_leg_over_its_count_is_counted_afresh_after_its_stop`.

**Measure next:** F1 on games since 18:50 (`andy.py --since '2026-10-18 18:50' --against '2026-10-18 17:54'
'2026-10-18 18:27'`): Catacombs 4 arrival → Andariel dead (was 7.3 s a cycle; in reach to dead 3.4 s median), guards:
lowest life on Level 4, potions drunk, MISSED. Kills an hour against 84/h (17:54-18:15). Then flip F3 and measure.
Confirm the first `Show Items was off before the level run: turned on` line (osd still wastes its presses during the
load: make it wait for the load, a small fix in `automation/show_items.py`).

**Ready to build (rulings given, 18:10):** watchdog names its cause; 45 s stall = no room only when a valuable is
remembered and the inventory has no room for its size (`ROOM_CAUSES = {'room'}`; tests pinned at test_runner.py
~1262, 1505-1517, 1620-1660, 1805-1875; keep 04:32:26 and 13:36-13:39 behaviour); a dead end skips the goal (leave only
when the run's last goal is unreachable); Andariel: the kill memory only. See `rca/2026-10-18/stalls-findings.md`.
The lost pointer of 17:58 (`rca/2026-10-18/freeze-findings.md`): fix A (a hop landing on the last pointer spot, or two
casts with no move toward a walkable aim → lost pointer: log XQueryPointer's window, end the run) then B (Save and Exit
by keyboard; probe the menu's keys first). Also: Teleport's own no-move check is cut off by `hunt.priced_for` (~1.4 s).

**Waiting for the player:** where the mouse was at 17:58-17:59; Lower Kurast with no room drops an unidentified carried
item even for a cheap find (no trip leg there) — allowed?; the cube plan review (`cube-plan.md`); the guard and
give-ups (Q2).

**Queue:** Catacombs 2 run to the stairs p90 10 s (median 4.6 s) — the top speed candidate; the HUD shop card's
"Shop check failed" during sales (skip it); the watch's MISSED after the player's own pickup (`game None`); key
top-up misses (~3 s a visit); pre-existing pyrefly errors in tests (`shop.py:157` false positive on `*toward`);
round 2 of the architecture plan (GameState/Excursion, events.jsonl, DropLedger, ensure_panels, the planner taking the
clicks after ~30 matched visits); Lower Kurast trips; act 1/3 town services; Thul feeds from Ort (Thul transmutes with
Chipped Topaz now keep it moving).

### 2026-10-18 19:07 — Andariel watch, F1 measure, F3 trial

- Watch re-armed on `20261018T155841Z-a09873cf` at 19:02; loop on, Andariel. The player turned it off at 19:03:13
  and back on at 19:03:27; no agent restart during that pause. No MISSED in the 18:50–19:07 window.
- F1 since 18:27: 48 kills by 19:02 (41 clean cycles); 83.0 kills/hour of play vs 80.3 in the 17:54–18:27 window.
  Cycle rate 82.9 → 82.6/hour (90% interval on the difference −10.6..+9.9: no evidence). Catacombs 4 arrival →
  Andariel in reach 3.4 → 2.6 s in the 18:50–19:07 window (90% interval −1.2..−0.3), arrival → kill 7.1 →
  6.1 s (−1.2..−0.3). In reach → dead stayed 3.4 s. The later 18:50–19:07 window had 22 kills in 0.28 h of
  play, 79.8/hour; one 28 s lobby recovery, one 14 s player pause, two town visits. No overall rate win is proven.
- F3 `buffs.QUIET_BY_THE_BOSS = True` trial began in service `20261018T160706Z-281e5e6c` at 19:07:12. It
  postpones side drops near a live boss and skips the optional sigil only while unharmed; Death Mark and potions stay.
  Expected saving: ~0.3 s in reach from the sigil, plus avoided loot detours when they occur. Measure in reach → dead,
  arrival → kill, kills/hour, lowest life, potions, and MISSED after 30+ clean cycles; compare 18:50–19:07. Focused
  tests: 182 passed; wide restart suite: 2333 passed, 7 skipped; ruff and pyrefly on `buffs.py` clean. The restart
  waited for the lobby and resumed with Andariel on. No commit.
- Trade in 18:50–19:07: 6 appraised `vendor` items sold for 7,558 carried gold; two slow uniques kept. The two sales
  visits used ~1.0 s per game including identify, and the payback of each sold kind was under 1; consider the pickup
  mix only after the F3 trial, without relaxing the player's pickup rulings.
- At 19:20:07 the player turned KP_6 off in the next game after the previous Save and Exit; no valuable was left in
  that game. F3 so far: 19 kills in 0.21 h of play = 88.6/hour; 18 kill-to-kill cycles, 17 clean; no MISSED, stop or
  recovery. In reach → dead 3.4 → 3.3 s (90% interval −0.3..+0.2, no evidence); rate 81.6 → 84.6/hour of cycles
  (+3.0, interval −8.0..+13.1, no evidence). The lowest life in 18 Catacombs 4 takes was 94%; none below 90%.
  The player remains in control; leave the loop off. Continue the same F3 trial after `PLAYER: loop on` until 30+
  clean cycles before a keep/revert decision.

### 2026-10-18 20:18 — stash page priority

- Player ruling (verbatim): "I want to change priority for storing items: shared tab 3 > 4 > 5 and only after that shared tabs 2 > 1 > personal".
- Implemented in `macros/stash.py`, `town.py`, `visit.py`, `charms.py`: the planned town visit, fallback scan, temporary
  shared parking and Gheed's storage follow 3, 4, 5, 2, 1, 0. Resource items retain their dedicated tabs. Each new
  fallback item starts at page 3 so a newly freed preferred page is checked again.
- Tests: focused town/stash/charms/townplan/visit 149 passed; wide macro/combat/builds/skills suite 2334 passed,
  7 skipped. Ruff, format, pyrefly and `git diff --check` clean. `restart.py --loop keep` waited for the lobby at
  20:18:53 and resumed service `20261018T171854Z-6096f3b0` at 20:18:59, loop on, Andariel. The new service has not
  yet logged a keeper stash put; that live placement remains to be observed.

### 2026-10-18 20:27 — Andariel watch after the stash reload

- Service `20261018T171854Z-6096f3b0` resumed Andariel on. The 20:20:31 town visit used the unread-view fallback,
  stashed 7 items in 6.2 s, and ended with cube 0, junk 0 and the 2x4 block free. The log did not record the destination
  pages, so live confirmation of the new page priority remains open.
- F3 trial from 19:07 through 20:25: 37 kills in 0.43 h active play, 85.9 kills/h; 36 kill-to-kill cycles (31 clean),
  median 40.3 s. Versus 18:50–19:07: cycles 81.6→84.4 kills/h, 90% interval for the difference −7.0..+12.9;
  in-reach→dead 3.4→3.3 s, interval −0.3..+0.1. Neither target shows a clear improvement; keep observing toward the
  90-game no-evidence rule. No valuable was reported missed in the 20:15–20:25 games (`games.py`).
- Two recoveries lost an Andariel game to `no click took the waypoint` (20:18:14 and 20:21:01). The second followed
  the town visit: eight waypoint clicks near y=0.09–0.11 of the game window, character unchanged at (5058, 5034),
  then Save and Exit. The take `20261018T172026Z-103` shows the macro sent those clicks; the reason the existing
  walk-into-view guard did not take the character closer is under investigation. Brief `no level map yet` stops in
  later games recovered and the loop continued.
- 20:29:28 diagnostic restart `20261018T172924Z-e22d123e` at the lobby, loop kept on, Andariel. `waypoint.py` now
  logs the projected ground position, whether route marks exist, and open panels when the waypoint is outside the
  safe view; it changes no movement. Focused waypoint tests 14 passed, wide suite 2334 passed and 7 skipped; ruff,
  format, pyrefly, diff check clean. Watch the next out-of-view attempt to choose a fix from evidence.

### 2026-10-18 20:43 — low-value set jewelry appraisal

- Player ruling (verbatim): "Keep one, sell duplicates (recommended)" for low-value set rings and amulets. The existing
  `macros/copies.py` guard protects the first or better owned copy, but sparse name asks caused Angelic Halo, Angelic
  Wings, Cathan's Sigil and Civerb's Icon to receive `check`, so duplicates never reached that guard.
- The 2026-10-04 SC/NL/PC/RotW offline ask snapshot has both Q1 and median below 0.25 Ist for these four. The triage
  engine now assigns `vendor` only to the reviewed set ring/amulet names with both figures still below the keep
  threshold and no matched pattern, roll comparison, placement or own-use rule. Sparse asks remain reference only;
  the other already-vendor cheap set jewelry keeps its existing verdict. Arcanna's Sign, Tal Rasha's Adjudication and
  Telling of Beads remain outside the vendor bucket.
- Tests: focused triage/copy guard 38 passed; broader pricing triage and identify 783 passed; pre-restart loop suite
  2335 passed, 7 skipped. Ruff, formatting and diff check clean. Pyrefly reports 21 existing errors on the unchanged
  dynamic portions of `pricing/triage/engine.py`, none in the new rule. Reloaded at the lobby into
  `20261018T174318Z-50855956` at 20:43:23; Andariel loop on. A live duplicate sale under the new rule remains to be
  observed.
- Replayed the actual Civerb's Icon identify read from the preceding service through the new retrieval and identify
  summary: triage is enabled for it, and the summary now says `vendor` with a one-seller reference band and no claimed
  price estimate. The restarted service completed its first Andariel game in 32 s.

### 2026-10-18 20:47 — watch after the appraisal reload

- Current service `20261018T174318Z-50855956` remains on Andariel. The first completed game killed her in 32 s.
  Game 2 took 79 s because the first attempt (`cyberrd46`) left from Catacombs 2 at 20:44:22 without a macro Save and
  Exit, then `cyberrd47` reached and killed Andariel. Before that exit, Teleport and Blade Warp both left the
  character at (22826, 6516); the take `20261018T174409Z-35` has 49 sent macro inputs and no player/healer input.
  There was no ground valuable seen in that attempt. The mechanism of the game exit or no-move inputs is unverified;
  watch the next occurrence against `rca/2026-10-18/freeze-findings.md` before changing movement code.
- F3 through 20:45: 62 Andariel kills in 0.75 h active play, 82.6 kills/hour; 54 clean cycles. Compared with
  18:50–19:07, 81.6 → 83.5 kills/hour of cycles, 90% interval −7.5..+11.8: no rate evidence yet. Continue toward
  the 90-game no-evidence decision. The latest three-minute inactivity watcher remains live.

### 2026-10-18 21:03 — Sigil ruling, town and waypoint fixes

- Player ruling: keep Sigil: Lethargy for all strong enemies. The F3 skip had only an estimated 0.31 s cast cost and
  no clear improvement in kills/hour, so `sigil_due` again applies to bosses, champions and uniques while
  unharmed. Herald priority remains. The separate rule to defer side drops beside a live boss remains enabled.
- Final F3 window before reversal, 19:07–21:02: 85 Andariel kills in 1.03 h active play, 82.2 kills/hour; 75 clean
  kill-to-kill cycles. Against 18:50–19:07, cycle rate 81.6→82.2 kills/hour, 90% interval −8.7..+10.2: no evidence
  of a speed gain. The user ruling ended the trial; it is not a measured proof of Sigil's safety or damage benefit.
- The unread stash fallback left Humongous (unique Giant Axe) in the cube at 20:48:36, 20:55:01 and 20:57:40: a first
  cube unload had no 2x3 space, but stashing carried keepers freed 2x4 and the fallback never retried. It now makes
  one more unload after that space opens. Regression test went red on the contract then green.
- At 20:50:25 the waypoint walk ended on predicted proximity before a game correction moved the character ~25 units
  away; the projected waypoint was again outside safe view. The waypoint action now rechecks the settled position and
  approaches again, at most three times. A corrected-walk regression went red then green. Live recurrence still
  needed to confirm the recovery is gone.
- Focused combat tests 185 passed; waypoint and town tests 52 passed. Pre-restart wide suite 2336 passed, 7 skipped;
  ruff, formatting, pyrefly on edited files and diff check clean. Lobby restart at 21:02:46 loaded the changes into
  `20261018T180247Z-aa3e0870`, Andariel loop on. First game killed Andariel in 35 s. The new log records Sigil at
  21:03:17 after the first strike on elite 156 (Andariel), confirming the ruling is live. The 3-minute watcher follows
  the new service.

### 2026-10-18 21:07 — unread-stash follow-up

- First town visit after the 21:02 reload still left Humongous in the cube at 21:04:01. The first fix retried only
  when inventory room already existed after the scan. Snapshot `210347.json` shows junk rings at (3,1) and (3,2)
  blocked the only 2x3 opening at that point; Jamella sold them later, leaving a 2x4 opening. This is a different
  state from the initial regression. A later 21:06:51 town visit stashed the axe after those rings were gone.
- A second red/green regression now holds the right columns as owned charms, the two blocking junk rings, and the
  cube axe. The unread scan shifts the junk rings within the inventory while at the stash, repeats the scan, and
  sells the rings at Jamella. This preserves the player's stash-then-Jamella, one-stash-walk order. Focused town
  suite 98 passed; lint and type checks clean. The required pre-restart suite passed 2339 tests, 7 skipped; TZ service
  and route checks passed 79. Lobby restart at 21:16:11 loaded it into `20261018T181613Z-cb6f45c4`, Andariel on;
  first completed game 33 s. A fresh blocked cube keeper has not yet occurred, so live confirmation of the junk
  shuffle remains open. The watcher follows the new service.

### 2026-10-18 21:28 — watch and TZ offline implementation

- The Andariel service `20261018T181613Z-cb6f45c4` completed 19 games after the reload while watched, without a
  reported recovery or sure-loot miss. Town visits at 21:19:15 and 21:26:25 ended cube 0, block 2x4 free and no junk;
  neither reproduced the two-junk-ring block. Sigil remained enabled for strong enemies.
- The separate TZ one-game path has a disabled request and HUD seam, fresh client-service TZ/effect reads, route
  inventory, elite hunt, observed boss/chest target and loot steps, restart-safe planning and elapsed-time metrics.
  Its service runtime is gated off by default and no route is marked played-ready; no TZ run was launched. Offline
  focused suite 245 passed; final macro/combat/build/skill suite 2341 passed, 7 skipped. Ruff, format, pyrefly on
  changed TZ and town files, and diff check clean. The TZ plan names the played route and shard evidence still needed.

### 2026-10-19 00:03 — code activation, loop held off

- Player requested the new code activated. Wide gate: 2368 passed, 7 skipped; pricing triage: 707 passed. Focused
  ownership/town/TZ checks: 446 passed; Hunt: 169 passed. Ruff and Pyrefly on the changed Hunt file passed.
- Restart request with `--loop keep` loaded session `20261018T210345Z-3c922404` at 00:03:51. Startup confirmed
  `loop off, pickup sure valuables, run Andariel`; the player's manual game remains open. No automated Andy run was
  started because protected inventory still lacks the live shadow town visit and identical item-ID reuse after an
  unobserved manual sale is not ruled out.
- The navigation diagnostic in `hunt.better_stand` is live; it logs ready jumps and own-Teleport/staff reads when a
  non-Teleport firing-spot jump is chosen while Teleport is on a key. No movement policy changed.
- River of Flame entrance incident at 23:59:11–20: the crossing click was covered by a monster across the border,
  and the run had no clear shot or firing move from the River side. RCA:
  `rca/2026-10-19/chaos-entrance-pack-findings.md`. No passage fallback was shipped in this restart.

### 2026-10-19 — minute health checks

- Replaced three simultaneous watchers with one `flock --nonblock` guarded watcher, running through `uv run --offline`.
  Persistent output: `inventory_tracking/runs/alt-d/watch.log`; active exec handle 97053.
- Added a health report every 60 seconds, even while farming is off and manual play generates fresh log lines.
  Reports loop state separately from log freshness; unavailable/stale evidence does not declare the host service dead.
  Historical loop legs retain their logged time, so rearming does not make an old stalled loop appear fresh.
- Regression suite: 83 passed. Ruff and formatting clean; Pyrefly 0 errors with the tools directory on its search path
  (the standalone scripts import `games` and `logwords` from that directory).
- Player pressed KP_6 at 00:07:20; service confirmed Loop on at 00:07:21 and the watcher observed game 1 complete
  in 33 seconds. The watcher did not initiate that transition. No service restart or inventory action made for this change.
- Watcher flagged the earlier manual Chaos Grand Charm as missed (game None); initial carried inventory has a Grand
  Charm but logs alone do not prove it is that drop. First town visit reported the 2x4 block still occupied; protected
  baseline items were left in place. These are follow-up findings, not evidence of a clean unattended run.

- Live health reports verified at 00:07:42, 00:08:42, 00:09:42 and 00:10:42. The watcher followed the player's
  pause at 00:09:27, service replacement at 00:09:31, and loop-on at 00:09:40. Five Andariel kills through 00:11:
  82.5 kills/h over 0.06 h of active play (short sample, not an optimization result).

### 2026-10-19 — conditional Fortress visit ruling

- Player: “we need to visit it when we need to perform town sell/clear inventory/refill consumables and only in such cases”.
- Do not introduce a visit after every game just because an item was picked up. Town scheduling must use the same
  positive ownership evidence as the shared town visit, so protected starting items cannot cause empty detours.
  Preserve actual low-room disposition, consumable needs and existing repair requirements.
- The pickup ledger currently resets at a game boundary. Loot whose positive identity cannot be carried across that
  boundary remains protected; legacy location/quality guesses must not regain authority to move or sell it.

### 2026-10-19 00:21–00:33 — town completion and ownership failures

- Navigation fixes (expired-act cancellation, successful retry clearing old failure, own Teleport before rooms arrive)
  and conditional town trigger passed combined gate 2381 tests, 7 skipped. Root restart --loop keep at 00:21:37 loaded
  session 20261018T212132Z-0cb3352a with loop off: the preceding game had already stopped for full inventory with
  Talic's Anguish on the ground. The game was preserved.
- User correctly identified broken clearing despite an empty cube. At 00:21:16 the physical inventory was full, the
  cube empty, and shared visit had zero authorized items. Items were prior-game pickups; their grants had expired.
  Skipping false detours was not a complete ownership fix. The user later cleared space and resumed at 00:24:30;
  the first-look inventory at 00:24:40 contains charms and supplies, without the old belt, amulet, gems and rune.
- Fixed an additional same-game defect: temporary in-game unread player suspends grants, rather than discarding them.
  Actual exit still clears grants. Added shared completion enforcement: any required town contract miss stops all
  callers before return/exit; deferred cube keeper exemption retained. Combined gate 2386 passed, 7 skipped.
  Changed files' Ruff/format/types passed; the user's 00:27:53 and later restart loaded those settled changes.
- Crossgame continuity remains unresolved. Snapshot content alone cannot safely restore grants. New work is isolated:
  continuous input audit, strict complete pack snapshot, and pure controlled-handoff verification. No new grants are
  enabled by this work yet. Do not claim town automation fully fixed until that path is proven.
- Minute watcher continues in handle97053 with singleton lock; reports stops, player pauses/resumes and service changes.
  Current service after user's 00:32:13 restart: 20261018T213213Z-c4faa25f; loop on at 00:32:52.

### 2026-10-19 00:37–00:50 — recent pickups still skipped by cube

- Player ruling: “we must not move any item that wasn't done by us ... then we just track what was picked up by us
  and what was picked up by user”. Empty cells are available capacity, not permission to move later occupants.
- Clean first-look at 00:37:16 followed by pickups Talic's Anguish 00:37:41, Chipped Diamond 00:39:24,
  Unique Legend Sword 00:40:01 and Amulet 00:41:17. Each was followed by a new game before the first cube attempt.
  At 00:41:51 full inventory stopped the loop beside Unique Demonhide Sash. `cube.stash` returned zero because
  `Ownership.observe` had cleared these receipts; there was no evidence of a failed cube click.
- Controlled save/load handoff and strict complete inventory reader are implemented, including empty unallocated
  cube and native cursor rejection. Combined focused check: 100 passed. Service lifecycle wiring added and tested.
  Not yet deployed: live input attribution and sanctioned identification continuity still under integration.
  Do not interpret passing pure eligibility tests as proof of an actual cube/town completion.
- Minute health watcher remains active; loop off after automatic inventory stop, fresh service logs through 00:48:54.

### 2026-10-19 01:00–01:13 — requested rollback to cells

- Player requested “just track inventory cells” and “restore older version”; priority is working Andy runs,
  inventory space and selling without selling player charms. The native input-audit experiment was removed from
  service/OSD delivery. No OSD restart is required by the restored path. Prior experiment saved under
  `rca/2026-10-19/before-cell-rollback/`.
- Historical e73eaa8 supplies the prior working flow but blindly counted all cube items as loot; that original
  charm-sale defect is not restored. Complete initial inventory/cube rectangles are protected; confirmed pickups
  get cell records that follow verified automation moves and rebind across automatic game changes.
- New lightweight lifecycle test includes actual cube clicks, Cain identification and shared-tab3 storage.
  Vendor regression refuses initial player charm and sells confirmed automation loot. Temporary stash staging
  regression covers park→retrieve→sale. All remain subject to final wide gate and live verification.
- User restarted serve at01:10:23, session20261018T221023Z-cfe7956b, loop off in Rogue Encampment.
  Final stash-staging hook was added afterward, so root must reload the final tested tree before farming.

- Final rollback gate:2483 passed,7 skipped (89.16s); changed production Ruff/format and targeted types clean.
  Two old synthetic loop fixtures were corrected to use valid non-overlapping rectangles and actual cube occupants.
- Root restart --loop on --kind andariel succeeded at01:20:01, session20261018T221956Z-a63cf4ce.
  Live strict baseline succeeded:30/40 inventory cells protected,0/12 cube cells protected. Andariel enabled;
  service waits for game-window focus. User asked to focus it; no kill/storage/sale live proof yet.

### 2026-10-19 01:22–01:28 — live rollback verification in progress

- Focus restored through the reusable `tools/focus_game.py` niri helper at01:22:40. Actual Andariel
  games2–10 completed in31–37s; automatic exits and next-game cell reconciliation logged each cycle.
- Singleton minute watcher handle97053 was polled live at01:27; health lines at01:25:06,01:26:06,
  01:27:07 show fresh logs and advancing game numbers. No restart or duplicate watcher needed.
- Four pickups observed (two rings, Grand Charm, Tal Rune). No cube transfer or town sale yet;
  live inventory clearing remains unverified. Initial baseline protects16charms among30occupied cells.
- Historical game=None MISSED alerts were investigated separately in
  `rca/2026-10-19/manual-fullclear-missed-loot-findings.md`; they concern preceding manual sessions,
  not evidence that these new Andariel runs lost those items.

### 2026-10-19 01:30 — first live cube and town completion verified

- Full inventory beside Grand Charm triggered cube at01:30:07;7of7 farmeditems moved at01:30:10,
  GrandCharm picked immediately, followed by successful automatic game reconciliation.
- Next game visited Fortress for accumulated loot. Six appraised vendor items sold (three newly farmed
  charms and three rings), two runes stashed; town completed01:30:50 in23.6s with cube empty,
  10freecells including2x4block, junk0, keys12, identifies20, groundclear.
- Root compared all19 protected inventory item records in visits/013030.json start versus end:
  same unitIDs, types, coordinates, sizes, qualities and unique rows; zero changes. This includes all16
  starting charms. Cursor empty, contract misses empty. Snapshot does not include individual item stats.
- Loop resumed Catacombs immediately. Minute watcher97053 remains live; no service restart needed.
- Follow-up measurement at01:31: `andy.py --since 2026-10-19\ 01:23 --no-takes` reports14kills,
  95.6kills/h over0.15h including town;13kill-to-kill cycles median34.8s,p9037.2s.
  Short observation window, not evidence for a speed optimization. Town game completed82s and next game started.
  Independent baseline collection comparison also confirms exact16/16 original charm layout.

### 2026-10-19 01:35 — inventory code restored, volatile cells (Claude)

- The player: "we had it working for the major part of the day ... broken it with some recent changes"; "issue isn't
  assuming the all cube cells as volatile. issue was that we have moved our charms there"; "cube is volatile; empty
  cells on the start of character - are volatile ... do not lose this when we restart game, reload `make serve`".
- Codex's ownership ledger and audit removed (it stopped the cube stash and town visits after every new game); the
  inventory modules are back at e73eaa8 (84.6 kills/h, 18:00–22:20) with the unread-stash fixes, movement fixes and TZ
  kept. New `macros/volatile.py`: per-character volatile cells in `runs/alt-d/volatile-cells.json` (CybergrindAA:
  10 cells, seeded from the 00:37:16 first look), plus stats prints of the player's items: never junk, sold or dropped.
  Design: `rca/2026-10-19/volatile-cells-restore.md`. Wide suite 3047 passed, 7 skipped. `make serve` was not running:
  nothing restarted; the next start loads it.

### 2026-10-19 01:35–01:36 — concurrent worktree change; live service retained

- Root found the deployed ownership.py/ownership_cycle.py absent from disk and new volatile.py plus caller
  changes. These were not made by root or the assigned TZ agent. No root restart: live session remains
  20261018T221956Z-a63cf4ce with its verified inventory behavior. Asked player which concurrent work owns this.
- TZ mode candidate is documented in rca/2026-10-19/andariel-terror-phase-findings.md. Agent confirmed no
  implementation/test edits were made before hold. Do not reload the mixed tree based on the old2483test gate.
- Watcher97053 polled live;01:36:09 health confirms fresh log, game20 completed56s, game21creating01:36:10.
  Continue monitoring existing process; clarification blocks deployment, not farming or live checks.

### 2026-10-19 01:38–01:40 — keeper stop and external restart

- Second townvisit013830 completed sales but stopped for cube-held uniqueEmbossedPlate (Atma'sWail).
  Unread stash fallback tried to unload it before sales while insufficient space existed, then left it after
  selling junk. End snapshot has10freecells; all19protectedrows unchanged. Need fallback keeper follow-up.
- External restart (not requested by root) loaded20261018T223906Z-91ca0ee6 at01:39:11 and resumedAndy.
  Firstlook confirms original16charms pluscube/tome/key in place, EmbossedPlate stillincube.
  New volatile-cell implementation logs19protecteditems and16learnedstatsprints; no root changes deployed.
- One open-waypoint recovery exited initialgame; nextgame reachedAndy and killedher01:39:50.
  Singleton watcher97053 remains live across restart. New implementation's full towncycle notyetverified.

### 2026-10-19 01:44–01:45 — new service town audit

- Currentservice townvisit reached unreadstash fallback; five items stashed, DwarfStar and Vidala'sSnare
  sold only after duplicate check confirmed an owned copy at least as good. All19protectedinventoryrows
  identical between start/end in visits/014437.json; cube stillholdsAtma'sWail.
- Keeper remains unresolved: firstfallback cannotunload2x3armor beforestashing; secondattempt reports
  inventorydidnotopen, cube0of1takenout. Townlogs contractmisses but newexternalversion continuesfarming.
  Root assigned read-onlyRCA; productionedits/restarts stillheld pending concurrentownershipclarification.
-01:45:11 health fresh, game7activelyfighting; Andydead01:45:12. Singletonmonitor live.
- RCA correction: secondfallback was a retry after `the mouse was moved` at01:44:37.613.
  Recordedpanels: firstinventorypress386236.683 opensinventory(.687), abort.745; retrykey.798
  closesinventory(.807). Unconditionalinventorytoggle caused thetimeout; ensure-open should be idempotent.
  Evidence reviewed by inventoryagent; report pending. No productionfixdeployedbyroot.

### 2026-10-19 01:52 — current service complete town cycle

- At01:52:00 fourfarmitems movedcube, groundpickup completed, nextgame requiredtown.
- Unreadstash fallback freedroom, then rescannedinplace for cubekeeper: stash5, unload1, stash1.
  End01:52:35: cube0,10freecells,2x4block,junk0,keys12,groundclear,18.4s. Catacombsresumed.
- Root compared visits/015220.json protected19records start/end: no identity, position, size,quality,
  identified orunique-rowchanges; cubeempty,cursorempty,missesempty. Includes original16charms.
- This confirms currentfallback succeeds without interruption; it does not fix the separately proven
  retry-closes-inventory defect. No root codeedit/restart.
-01:54:26 secondnewservicecube clear moved4items and pickedUniqueLargeShield beforeexit.
  Town015447 ended01:55:00: cube0,10freecells,contractcomplete. Rootcompared19protectedrows
  start/end: unchanged (all16originalcharms included). DuplicatecheckedvendorLargeShield and
  newlypickedSmallCharm sold; farmingresumed andAndydead01:55:22. No rootrestart.

### 2026-10-19 02:02 — player pause

- Newservice town020107 completed02:01:33 with cube0,10freecells,contractcomplete; all19protectedrows
  unchanged. Andydead02:01:58, exit02:02:01. Nextgame23 started; playerpausedloop02:02:12.
- Rootwillnotresumeorrestartrunwhileplayerpauseholds. Minute watcher97053 remainsactive to detectresume.
- Outstanding codefixes are documented (TZmode coupling; inventorytoggleonretry), notdeployedbyroot.
  Concurrentinventoryrewrite/restartwasexternal; noownerclarificationreceivedyet.
- Playerresumed02:03:41; rootdidnotsendtoggle. Game23completed24s active, game24completed36s,
  Andydead02:04:37 andgame25started02:04:41.02:04:17 minutecheck confirms freshactiveprogress.
  Pace returns afterTZrotationwithoutrootcodechange. Monitor97053confirmedlive.

### 2026-10-19 01:39–02:10 — watch, Deep shards, stash view (Claude)

- 01:39 restart (`20261018T223906Z-91ca0ee6`): the 01:19:56 service had loaded a half-edited tree (Codex's runner
  stop on any contract miss). Volatile cells live at the first look (19 player items, 16 prints). Sales 01:38–02:01
  all `vendor` among loop items (surplus Dwarf Star, Vidala's Snare, Stormguild; loop charms in volatile cells).
  Room-making works again (cube 4–8 items mid-run; Unique Cryptic Axe kept, stashed as `sell`). The unread-stash
  retry freed the stuck Embossed Plate at 01:52.
- 01:45–02:00 Catacombs was the terror zone: full clear after Andariel (`runmode.mode_of`), loot-after-kill median
  26.7 s vs 2.4 s, 56 kills/h; asked the player whether the Andariel loop should skip the TZ full clear (no answer
  yet). From 02:00 games 24–37 s again.
- Player: "we have left deepworld worldstone shard and left the game". 01:59:14 game 19: the shard was never in the
  pickup's drops: class 677 was in FULL_FILE since 22:14 on 2026-10-18, when the unread scan took two refused puts for
  a full stack (it held 83: collection DB and the player) and dropped that shard in town. Cause of the unread stash
  since 20:18: the player emptied shared page 5; an empty page has no grid allocated and `stash_view_of` read it as no
  view (collection: page 5 has 0 items). Fixes: an absent shared-page grid is an empty page (world.py); a refusal with
  the stash unread is logged, kept carried, never a full stack nor a drop (visit.py `_stash`); FULL_FILE set to [669]
  (Twisted Essence of Suffering, 99). Tests red/green (test_world, test_visit); wide suite 2534 passed, 7 skipped.
  Restart 02:10:15 `20261018T231015Z-d282b6a6`, loop on. Two Deep shards lost (22:14 in town, 01:59 on Catacombs 4).
- Verify: the next Fortress visit logs `stash view: pages free ...` (not `unread`), and Deep shards are picked up.
- TZ leveling goal-queue work runs in a separate worktree `.claude/worktrees/tz-goals` (agent), not live.

### 2026-10-19 02:10–02:13 — external reload and inventory continuity verified

- Externalrestart02:10:19 loaded20261018T231015Z-d282b6a6; rootdidnotrequestit.
  Beforeexit8items movedcube, Amulet/SmallCharm picked. Newbaseline retains30protectedcells,
  16fingerprints,19protecteditems. Games1–3completed39/35/34s.
- Town021226 completed02:12:50: cube0,10freecells,2x4block,junk0,contractcomplete,27.1s.
  Rootcompared19protecteditemrowsbefore/after: unchanged,includingall16originalcharms.
  Recentloot carriedacrossrestart was processed; Catacombsresumed andAndyphase02:13:07.
- Minute watcher97053confirmedlive andfollowedreload. Concurrentownerclarification remainsunanswered;
  rootproductionfixesremainheld. No blanketclaimthatunfixedretrycaseisresolved.
- 02:12 rulings: "andy loop shouldn't focus on full clearing level"; "full clear tz: for herald hunting; tz leveling:
  clear only elites/champs"; "every loop has it's own metric, that it must optimize: boss kills/elites kill/opened
  chest. the only thing that has more priority - proper interactions with drops". `hunt.Hunter.run_mode`: no terror
  full clear on any `looped` pursuit (the Andariel fight had rush=False). Test in test_runmode.py; wide suite 2535
  passed. Stash view confirmed read at 02:12:23 (`pages free 0:15 1:87 2:34 3:21 4:96 5:100`; full stacks Full
  Rejuvenation Potion, Twisted Essence of Suffering). Restart 02:15:05 `20261018T231505Z-a0398029`, loop on.
  Rulings relayed to the TZ agent.

### 2026-10-19 02:33 — measured: no terror full clear in the loop (since the 02:15 restart)

- `andy.py --since '2026-10-19 02:15' --against '2026-10-18 18:00' '2026-10-18 22:20'`: 31 kills in 0.30 h,
  **99.1 kills an hour of cycles** against 84.6 (+14.5, 90% [+8.0, +20.8]: better); cycle median 35.4 s against 37.4;
  Catacombs 3 run 3.9 s against 4.8, loot after the kill 1.9 against 2.4. MISSED 0. Kept.
- The watch read full-stacks.json only at its start (armed 02:10, the file changed 02:10:09), so it reported the
  full Twisted Essence of Suffering as MISSED each game: watch.py now re-reads the file at each game's end.
- Next candidates (most seconds a cycle): loot after the kill p90 8.1 s (median 1.9); the trade session 36.3 s (the
  stash stop 17.1 s at 02:24); Catacombs 2/3 runs p90 6.8/6.6 s against 5.0/3.9.
- 02:36 the slow loot phases (8.1-8.7 s at 02:17, 02:20, 02:22): a drop (a Large Charm 22 away at 02:17:18) lies
  among Andariel's escort (34 hostiles); the loop teleports to it and fights the 17-23 in reach on the way. That is
  the drops-first rule at work, no defect; not a speed candidate without a ruling.
- 02:45 the stash stop (13.8 s at 02:40): open 0.8 s, 4 items in 3.4 s, the cube's 2 out and the reopening 2.1 s, three
  rune transmutes 4.6 s (the ruling: stacks over 80 cubed toward 80). At most ~2 s a visit to gain (a visit every ~10
  games: ~0.2 s a cycle): no candidate. Noted: `stash: the Ornate Armor went onto page 1, planned 3: page 1 is the one
  shown` (stashed, not lost; the page shown wins over the plan).
- 02:50 candidate waiting a ruling: the pickup step's `opening.open_near` (KP_1 ruling 2026-10-12, containers within
  12 units) opens containers on the Andariel run: since 02:15, 53 opened in ~52 games, 38.9 s from "Opening" to
  "opened" (~0.75 s a cycle, ~2%), 32 of them Barrels on the way to Andariel (02:46:03 three barrels, 1.5 s before
  the first Teleport toward her). Proposal for the player: no containers on the Andariel loop (or no barrels), the LK
  loop and KP_1 unchanged. Not changed without the ruling (rule 9).
- 03:02 borderline sale, for the player: rare Amulet "Rune Wing" (+1 Warlock skills, all resistances +13%, 8 MF)
  sold for 35000 gold as `vendor`: the triage pattern wants +1 class skills with two of the listed stats, all
  resistances at 15+ (13 of 15). By the rules (not +2 skills, FCR or life); the threshold is the pricing KB's.
- 03:07 an hour since the 02:15 restart: 82 kills in 0.87 h, **93.6 kills an hour of cycles** against 84.6 (+9.0, 90%
  [+3.7, +14.2]: better), cycle median 36.2 s, 6 trade sessions (median 32.3 s, all clean), MISSED 0, no stop.
- 03:20 game 100 (56 s, Andariel 27 s): a unique Death Mask (Hellwarden's Will?) with the inventory full; the run
  stood by it 03:19:45.7-03:19:50.4 (`idle`, 4.7 s) before `room is made in the cube`, cubed 5, picked it up 03:19:53.
  No loss. Small candidate: the 4.7 s wait before the cube move (rare: ~0.15 s a cycle).
- 03:48 **two rare amulets sold against the 16:50 ruling** ("Rare amulets with +FCR, +2 skills, +life are good"):
  Corruption Scarab (+41 life, FR 35%) for 12110 and Havoc Torc (+59 life, +1 Eldritch Skills) for 3664, both
  appraised `vendor`: the triage pattern built from the ruling (+1 class or +2 tree with 10 FCR and 20+ life) is
  narrower than its words. Fix: `macros/keepers.py` `amulet_keeper` (a rare or crafted amulet with any FCR, any life
  or 2+ skills, or its stats unread, is kept; stat ids from itemstatcost.txt: maxhp 7 >> 8, FCR 105, all skills 127,
  class 83, tree 188), `Run.kept_item` set by the runner, checked in `visit` (no junk: "kept by its stats, not sold")
  and `shop.restock` ("kept by its stats (...): never sold"). Tests: test_keepers.py (11), test_shop, test_visit;
  wide suite 2399 passed, 7 skipped. Restart 03:53:37 `20261019T005337Z-58e34851`, loop on. Verify: the next rare
  amulet with life shows `kept by its stats`. The pricing rule itself (pricing/data/triage) not changed.
- 04:13 two hours since 02:15 (both services): 183 kills in 1.97 h, **92.5 kills an hour of cycles** against 84.6
  (+7.8, 90% [+3.7, +12.0]), cycle median 35.9 s, 16 trade sessions (median 33.0 s), MISSED 0, no stop.
- 04:23 one stash view unread: read at 04:23:09.967 (`pages free ... 4:70 5:100`), `hands.view()` None at 04:23:12.955
  (`the stash is not read: the scan`); the scan put 5 in, 0 left, the session clean. First of this service; watch for
  a repeat before a study (a transient read of the shared pages' units).
- 04:13 keeper guard check: no rare amulet with life seen since the 03:53 restart yet (not verified live).
- 04:53 keeper guard verified live: Corruption Mark (rare Amulet: +32 life, +74 mana) appraised `vendor`, `town
  visit: Amulet (+32 life) kept by its stats, not sold` (04:53:30.159).
- 05:31 since the 03:53 restart: 152 kills in 1.63 h, **93.2 kills an hour of cycles** against 84.6 (+8.6, 90% [+4.3,
  +12.9]), cycle median 35.6 s, 13 trade sessions (median 30.4 s), MISSED 0, no stop. The keeper guard costs no time.
- 06:02 Gheed's swap: a Gheed's Fortune (36 MF, 89 GF, 12% prices; "sell") replaced the player's (34 MF) at (0, 0);
  the old one on shared page 1. Gap found: `Loop.tell` learnt the player's prints only when `own` (class and cell)
  changed, so the new charm in the same cell was not learnt (16 prints). Fix: `printed` keyed by the unit ids of the
  player's items (loop.py); test_volatile `test_a_new_item_in_the_same_cell_is_learnt_too`; wide suite 2400 passed.
  Restart 06:06:03 `20261019T030603Z-fb5d2a99`; 06:06:17 `1 more of the player's items known by their stats` (17).
  (No loss risk meanwhile: unique charms are never `sellable`.)
- 06:04 copies: Hwanin's Refuge sold as surplus; Demon Limb kept (FR 20 against the owned 16).
- 06:18 `trade session done (short of the contract: cube 1 items (normal Flawless Amethyst at (1, 1)))`: its stash
  stack full (FULL_FILE now [575, 669]), the gem kept in the cube for the 3 -> perfect transmute (town.py GEMS_A_KIND,
  the 09:51 ruling on 2026-10-18); the planner predicted it. No loss; the contract counted the kept gem as a cube miss.
  Fix: `town.contract` counts a kept gem in the cube as waiting (deferred), as `_kept_gem` already did for keepers;
  test_town `test_a_full_stacks_flawless_gem_kept_in_the_cube_waits_there_not_a_miss`; wide suite 2401 passed.
  Restart 06:22:31 `20261019T032231Z-a3e99abf`, loop on.
- 06:13 a second Gheed's Fortune (35 MF): the player's (36) kept, the new one onto shared page 5.
- 06:29 stash room: the shared pages' free cells 337 at 02:23 (1:87 2:34 3:20 4:96 5:100) -> 136 at 06:28 (1:29 2:12
  3:0 4:6 5:89): ~50 cells an hour of keepers, ~2.5 h left at that pace (less for a big keeper's block). A keeper no
  page takes stops the loop (the 16:50 ruling): told the player.
- 07:26 `short of the contract: block 2x4 taken`: four Flawless Amethysts kept (the stack full); the transmute took
  three at 07:26:19 (a Perfect Amethyst, stashed); the fourth stayed carried at (4, 2), in the block (visit
  snapshot 072614.json). The loop's own (a volatile cell); the next room check cubes it. Not fixed live (rare: a 4th
  kept gem of a kind): queue — after `hands.transmute`, a kept gem carried in the block goes into the emptied cube.
- 07:34 `andy.py --since 06:22`: 106 kills in 1.19 h, **89.1/h** (median cycle 36.5 s, p90 61.0 s), MISSED 0, no
  stop. 11 trade sessions (median 24.9 s), one trip to town for room (49.8 s). Loot after the kill p90 9.6 s (median
  2.3 s): the next speed candidate once the stash question is settled. 07:31 trade: four `vendor` charms sold
  (3485 gold, all from the loop's cells), Thundergod's Vigor (`slow`) stashed (page 1, planned 4), cube 2 = kept
  flawless gems, contract held. Shared stash free: 1:10 2:6 3:0 4:3 5:75 before it.
- 07:38 `stash: 181494 gold to deposit, the carried gold still 871494` twice a visit (~3 s each, again 07:42): the
  stash showed 12500000 gold (deposit-failed-073808.png), a round number taken as its most; deposits refused. Fix:
  `stash.deposit` reads the stash's gold (stat 15 `goldbank`) and deposits only what BANK_MOST leaves room for, none
  under DEPOSIT_LEAST (BANK_MOST inferred from the picture). test_stash
  `test_a_stash_at_its_most_gold_takes_no_deposit_and_one_near_it_only_what_fits`. **For the player**: carried gold
  872740 of the 940000 cap and the stash full of gold: sales stop when a sale could pass the cap (SALE_MOST), about
  an hour of trade sessions away; then junk stays unsold. Needs a gold ruling.
- 07:40 queued fix done: after the gem transmutes, a kept gem still carried goes into the emptied cube
  (`cube.stash_only`, runner `transmute_gems`; `town.kept_gem` made public). test_cube
  `test_only_the_wanted_loop_items_go_into_the_cube`. Wide suite 2403 passed. Restart 07:42:53
  `20261019T044248Z-e41838bc`, loop on. Verify: the next deposit says `its gold 12500000 of 12500000` and no
  deposit-failed picture; a 4th kept gem ends in the cube.
- 07:41 The Rising Sun sold (`vendor`, copies: an owned copy rolls at least as well): correct.
- 07:53 the goldbank fix did not fire (deposit-failed-075352.png): the gold goes to the tab shown, there the
  Shared/Gems tab (its gold 12500000), the personal stash's gold separate. Fix replaced: `stash.deposit` clicks the
  Personal tab first; one refused deposit ends the deposits until a restart (`stash.REFUSED`), its line now with
  stat 15. Dropped the BANK_MOST guess. test_stash `test_the_deposit_shows_the_personal_tab_and_one_refused_ends_the_
  deposits`; conftest `no_deposit_refused`. Wide suite 2403 passed. Restart 07:57:15 `20261019T045711Z-5a295660`.
  Verify: the next trade session's `gold deposited` line (carried falls to ~690000) and the sales go on.
  07:57:49 verified: `stash: 188959 gold deposited, 690000 carried` (Personal tab); sales went on (690000 -> 702759).
- 08:15 `andy.py --since 07:42`: 49 kills in 0.55 h, **88.3/h** (median cycle 36.2 s), MISSED 0, no stop. Loot after
  the kill median 6.2 s (2.3 s at 06:22-07:33): candidate to study (more pickups, or a slower pickup?). Shared
  stash page 5 at 39 free (75 at 07:31): ~60 cells an hour, about an hour of keepers' room left.
- 08:17 **Wraithra Clasp sold** (rare amulet, +2 to Summoning Skills, +18 str, DR 3; 10993 gold): the amulet keeper
  never saw the skills. `World.item_stats` kept layer 0 alone, and item_addskill_tab (188) sits on the tree's layer,
  item_addclassskills (83) on the class's: keepers.py's "+2 skills" was blind to them since 03:48 (FCR and life were
  read). Fix: `world.item_values` adds LAYERED_SKILLS (83, 188) at the most of any layer. test_world
  `test_an_items_tree_and_class_skills_are_read_off_their_layers`. Wide suite 2404 passed. Restart 08:20:22
  `20261019T052017Z-ea7b4e47`. Verify: the next rare amulet with +2 tree/class skills logs `kept by its stats`.
- 08:47 `andy.py --since 07:57`: 70 kills in 0.82 h, **85.1/h** (median cycle 36.8 s), MISSED 0, no stop; loot after
  the kill back to median 2.0 s (the 6.2 s of 07:42-08:15 was the drops). Shared stash free 1:5 2:6 3:0 4:3 5:13
  (27; personal 15) at 08:44: a large keeper may find no page soon, then the loop stops (the 16:50 ruling).
  Not yet seen live: a +2 tree/class amulet (the 08:20 fix).

## 2026-10-19 09:00 — TZ leveling loop launched (the player: "launch tz-leveling loop after then next run and monitor/improve it")

- The TZ goals work of the sub-agent (worktree `tz-goals`, design `macros/goals-plan.md`) applied to the live tree
  (patch of 02:33, one import hunk of runner.py by hand: `kept_gem`); `tzloop.ENABLED = True`; two tests of the off
  state pin it off. Wide suite + routes + terror 2808 passed. Restart 09:00:39 `20261019T060035Z-b858f8b1`
  `--kind tz`. Andariel loop until 09:00: 85.1/h (07:57-08:46).
- First game: `tz: zone Act3-GreatMarsh: Great Marsh from 77`, waypoint, level run with `agenda: target an
  unexplored room` (Great Marsh is COVER). Metric: `elites.py` (elite kills an hour; Andariel baseline 213.6/h).
  §9 checks to watch: zone read, level run with the agenda, room package, leave guard, game length (1200 s cap).
- 09:01-09:04 **the level run ended at a drop's guards**: `agenda_cleared`'s fight-first goal (`first_fight` from the
  drop's PICK_UP) had no route, no `clearing`, no `guarded`; on a routeless level (Great Marsh) `pursuit.run_level`
  ended the run ("nothing is left to go to on this level"), the elites known and the gold left, the game left after
  20-55 s. Fix: the fight is `clearing=True` (hunt.py). test_tzloop side-drop test asserts it. Restart 09:05:12.
- 09:04-09:15 **Water Watchers** (tentacle1-3, tentaclehead1-3: 258-263) under the marsh's water: struck 4 casts each
  (~8 s) before `untouched` left them alone 20 s, then again: 25 s of one fight, a 45 s watchdog leave (09:08:00),
  8 episodes in the 330 s game 4. The player: "in marsh we can stuck and try to attack mobs that aren't visible and
  don't attack us at all". Fix: hunt.py SUBMERGED left out of `hostiles` (the safety no longer prices their harm:
  they hurt only at the water's edge). test_hunt `test_a_water_watcher_under_the_water_is_no_hostile`. Wide suite
  2809 passed. Restart 09:15:54 `20261019T061550Z-9e514b94`.
- 09:11 `elites.py --since 09:00`: 175.3 elite kills an hour over 10 games (0.17 h; Andariel 213.6/h): lobby 16% and
  travel 18% for 60 s games (most cut short by the first bug), level 65%. The player: "our current elites kill ratio
  is under the any meaningful value". Next: measure after the two fixes; candidate: an exploring budget (leave a
  COVER level when no leader is found for N s of exploring: a new game costs ~25 s of lobby and travel).
- 09:15-09:20 **NPC menus** (the player: "we cannot click identify all from the first attempt ... make sure that we
  have generic code"): over the sessions Identify took first try 206/212, Trade 208/214; the lifts that took sit on
  a line's edges (Cain 0.2052 and 0.2165, Jamella 0.229 and 0.2346), so one learned lift misses by a pixel or two.
  shop.py `menu_line` (generic: open, click at each lift, the line's own check, learn, close), used by cain.py,
  `_open_trade` and repair.py; menu-lifts.json keeps the last HITS_KEPT=40 hits per NPC and aims at their middle.
  Logged "menu line missed: <npc>, <line> <lift> (try N)". In the tree, not yet live.
- 09:22 **my mistake**: menu-lifts.json written in the new list format while the old code was live: 3 town visits
  failed (09:22:07/18/30, "unsupported operand type(s) for -: 'float' and 'list'"), the game left each time, nothing
  lost. File reverted. A shared data file changes format only after the code that reads it is live.
- 09:22:44-09:23:50 **recovery chain**: after the 4th recovery (game 6: Consume showed nothing 3 times by the
  Fortress waypoint), RECOVERY_PAUSE 30 s stood in the game, and `Loop.still`'s clock ran on through the pause and
  into game 7 (the same waypoint spot): "has not moved for 45 s" 5 s into game 7, a 5th recovery. Fix: loop.py
  `still(where, now, game)` counts afresh in a new game and while cooling; runner passes the game. test_loop
  `test_a_new_game_and_the_recovery_pause_count_no_stand`. Wide suite 2447 passed (without scenarios). Restart due
  with the menu change. Open: Consume by the Fortress waypoint showing nothing (once in ~10 games so far).
- 09:33:30 restart `20261019T063324Z-9e62e834`: the stillness fix, menu_line (Cain, Jamella, Halbu), super chests as
  the agenda's CHEST tier (agent; agenda.py, hunting/choice.py `agenda_chests`/`agenda_chest`).
- 09:32-09:38 **Frozen River never entered** (zone Crystalline Passage → Frozen River): the side-trip entrance (POI
  kind 'target', PoiSpec.warp) was no door for guide.py `_target_of` (warp only for WAYS_OUT): "no hop toward Frozen
  River: the character is beside it", "TZ next level" ×40 in 2 s, the game left, every game. Fix: Poi.entrance set by
  spots.py `pinpoint(warp=True)`, guide.py counts it a door. test_spots. Restart 09:38:54 `e1cbc3d4`: "door Frozen
  River: in after 0.28s".
- ~09:43 the player: "we stood still while under attack and almost died, only user intervented ... we must not die".
  Not found yet in the logs (no healer drink); an agent studies it (rca/2026-10-19/near-death-findings.md, fix to come).
- ~09:45 the player's ruling: "if we died - we MUST not take ANY other actions, no reviving, no save/exits, nothing at
  all". Before: only `choose`/`next_leg` raised Dead; a death seen anywhere else (press_skill's Abort, a watchdog, a
  leg's stop) was a recovery, whose next leg is Save and Exit. Fix: routines.Dead (press_skill, pickup, hunt raise it),
  leave_game refuses when dead, runner `_loop_stopped` reads the mode (`_dead`) and stops the loop, presses nothing.
  test_routines, test_runner. Restart 09:46:50 `c0f1cd6e`.
- 09:46:02-43 Frozen River: "no way toward Frozenstein ... no way of hops leads over the rooms", 40 s idle, the 45 s
  watchdog left the game (ON_THE_WAY: no rooms explored). Fix: hunt.py `wayless`: a route goal with no way turns that
  level to COVER for the game ("agenda: no way to X: the level is explored for it"). test_tzloop. The player turned the
  loop off at 09:48:21; restart 09:50:46 `88b8c83d` with the loop kept off. menu-lifts.json seeded with the line edges
  (Cain 0.2052/0.2165 → aim 0.2108, Jamella 0.229/0.2346 → 0.2318).
- elites.py now prints activities (engaging = fight seconds; approach, explore, chests, pickup, travel, town, lobby).
- **Near death found** (agent, rca/2026-10-19/near-death-findings.md; checked in the frames: p[7] life): take
  20261019T063559Z-113, 09:36:41 "4 recoveries ... the next leg after 30 s": `Loop.leg` slept RECOVERY_PAUSE standing
  in Crystalline Passage, attack mode off; three monsters (508) hit the character 3119 -> 2335 (09:36:53-:03), the
  player struck 14 times at 09:37:05. Fix A: the pause is waited only in the lobby or a town (Save and Exit first in a
  level). Fix B: `Loop.beset` (BESET_LOSS 5% within BESET_SECONDS 4 standing outside a fight, attack mode off): the
  game is left at once, cause 'beset', even with a valuable on the ground (departs from the 2026-10-17 ruling:
  survival first; the player's ruling asked). Wide suite 2903 passed. Restart 09:59:00 `77542362`, loop kept off.
- 22:39 on 2026-10-19, restart `cfbbd255`, loop kept on (resumed as Andariel from an old pending request; TZ asked
  back from the next game). Live: TZ level-run fixes (room stop inside the room, walled rooms seen, no empty
  next_room, 2 s pass at a reached stop, strikers engaged behind ENGAGE_STRIKERS), TZ only within terror zones
  (TRANSIT policy, `tzloop.select`, `Pursuit.allowed`), Red portal after Mephisto then Save and Exit, act-3 game end
  via the Fortress, no-excursion/idle stops (IDLE_GAMES 3), route-start town visit, one no-room routine, boss drops
  awaited and a fresh ground read before leaving, no Teleport spot under the skill bar plus a dud-hop bar, Defiler
  re-summon spots, every magic/rare `vendor` sold, real stash landing pages, Docks walk clicks on the ground, KP_3
  BUFF, KP_4 jump, experience lines. Wide suite 3208 passed, ruff/format/pyrefly clean. Next: town exits (phase 2),
  fight churn S4, seal order S3, Consume-in-town recovery.
- 2026-10-19 23:05:46 restart `4f6c3b55` (loop off, run TZ leveling): live: boss-mark empty wait 3 s then explore (`EMPTY_MARK_GOES_ON`, Endugu idle 22:49 game 3), S4 yield carry, town exits (Blood Moor, Rocky Waste, Outer Steppes walk out of town), watch: legs summed, STALL needs no progress. The restart went through at a stop: game 5 Spider Forest Herald dropped a Unique Grand Charm (Gheed's?) refused (one carried); TZ kinds have no Gheed's swap (goals-plan open question 4) — the room rules then a stop. Agent on the TZ Gheed's swap; the game kept open with the charm on the ground.
- 2026-10-19 23:20:10 restart `f08c1031` (loop on): TZ Gheed's swap (agent; agenda package, act's town + the Fortress), Consume beside a townsperson re-summons, prebuff goes on without Consume, room stop kept (`KEEP_STOP`). Live in the same game 5 (Spider Forest): refused 23:20:16 → portal, Fortress, the player's (34%) onto shared page 3, back, picked up 23:20:41, Cain, kept the player's against the new 28% (onto shared page 4), back through 23:21:04, package done, run goes on. Open: S3 near-seal rule (agenda.py) drafted, not applied.
- 2026-10-19 23:28:32 restart `ae9eb094` (loop on, TZ leveling) at a lobby: S3 near-seal rule (`USE_FIRST`, `USE_NEAR` 60: the route's seal/chest within 60 before a farther tour room). Watch: 'Teleport toward Vizier seal 2' right after seal 1 in Chaos. Nothing else pending a restart.
- 2026-10-19 23:41 restart `00ebde58` (loop on). Stop at 23:35:00 "inventory is open" (Set Heavy Bracers on the ground): the cube's room step (23:34:19) was cancelled by the fight back; its Escape went through `guard` and was refused (Cancelled), so the inventory and cube stayed open; the fight read them as the player's hand and stood 40 s beset (life 2950 -> 1703), then the 45 s still and the stop. Fixed: actuator.py `closing`, cube.py `close` (through a cancel, never dead) in the 5 cube routines; loop.py `tidy_panels` closes inventory/cube at the first leg after the loop is turned on. Also live: running/legs.py ZONE_LEFT ends a level run whose zone moved on (23:30 Spider Forest explored 1.5 min after the zone went to Dry Hills). Verified 23:41:03: panels closed, cube room made, bracers picked up. Suite 3894.
- 2026-10-19 23:56:27 restart `28713585` (loop on) at a lobby: pickup.py logs a pickup made by a move's click ('picked up X … by a move's click'), so the watch's MISSED for the 23:42 Tal Rune (taken by a walk click, carried, stashed 23:46) does not repeat. Magic rings/amulets at pickup 'good' are left by design.
- 2026-10-20 00:05:56 restart `eeb08c50` (loop off, at a stop): live: pursuit.py `through` walks a passage no hop gets nearer to from THROUGH_WALK 40 (00:02:18 Outer Steppes: "no footing in view brings the character nearer", 23 off, 45 s idle; game 4 again at 00:03:56). The stop 00:05:54: a Grand Charm in Outer Steppes (5477, 5092), its pickup failed among 9 drops (another label under the pointer), the run went through into the Plains (Izual dead 00:05:49), then "before leaving: no pickup and no trip back took it" x3 — sightings fetch only in the character's own level. Agent on the cross-level fetch; the game kept open, loop off.
- 2026-10-20 00:22:07 restart `2da4a96f` (loop on): cross-level fetch (sightings.py `fetch(across=)`, running/valuables.py `crossing`/`cross`, TZ_PICKUP only) and pickup.py LOOKED (the next try starts at the aims not yet tried). Live in the same game: 00:22:16 'across the open passage into Outer Steppes', in Steppes 00:22:19, the Grand Charm picked up 00:22:23 (7 s from the leg). Open gap: tzroutine.produce adds PICKUP only for the current level, so a Town Portal for a next excursion could still leave one on another level (last_look still guards the game).
- 2026-10-20 00:22:27 follow-up (minor): after the cross-level fetch the Steppes' route step was already done, so 'TZ next level' on into the Plains had no stage ('no route stage') and repeated until the again-and-again guard left the game (4 s, nothing left). Better: after a fetch on a level whose route is done, the agenda's game end.
- 2026-10-20 01:01:27 recovery: Lost City (zone Lost City + Valley of Snakes) 'at Ancient Tunnels (Valley of Snakes is not marked yet)' x8, the again-and-again guard left the game (nothing lost, +903,881). goals.py route_goal takes the card's first mark when the stage's is not on the card. Fixed in hunting/choice.py `goal`: an agenda run seeks the nearest unexplored room ('seek Valley of Snakes (not marked yet): an unexplored room'); the player's own press keeps the card's. Test in test_tz_leveling.py; suite 3904. Restart queued for the next lobby.
- 2026-10-20 01:05:01 recovery: Lost City 'no way toward Valley of Snakes' 45 s after its rooms were explored (wayless set), the watchdog left the game. Fixed: hunting/judging.py `judge` ends the run NO_WAY_ENDS (8 s) after a wayless level's route goal still has no way ('no way to X after exploring for it N s'). Also live since 01:05:03 `49093edc`: the unmarked-way-out seek. Suite 3905; restart queued for the next lobby.
- 2026-10-20 01:08:36 restart `4c86e8c9` (at the lobby after a beset recovery in Lost City at 01:08:29, nothing left): NO_WAY_ENDS live. First visit 01:09:28 clean (contract held; Cathan's Seal sold as a surplus copy, carried gold only).
- 2026-10-20 01:08:29 recovery (false): Lost City, standing by an Ith Rune, 'hit standing outside a fight (life 1886/1886)': Battle Orders ran out (2937/2937 -> 1886/1886, cast 01:05:28, ~180 s), no attacker. `Loop.beset` compared points; now it compares life missing from the maximum. Test `test_battle_orders_running_out_is_no_hit` in test_loop.py; wide suite 2482 green. Restart queued for the next lobby.
- 2026-10-20 01:13:16-01:13:54 recovery: Lost City, NO_WAY_ENDS ended the run ('no way to Valley of Snakes after exploring for it 8 s') but 'TZ next level' made the same run again every 8 s until the 45 s watchdog left the game (nothing lost, +549,835). Fixed: runner.py `_run_over` on a 'no way to ' end (hunting/base.py NO_WAY_TO) calls agenda.py `Agenda.no_way_on`: the level's NEXT_LEVEL goals stay out for the game (the game's end next). Tests in test_agenda.py and test_runner.py; wide suite 2484 green. Restart queued for the next lobby.
- 2026-10-20 01:17:35 restart `bfee96a3`: the no-way-on drop live. 01:13:35-01:17:28 (b39d8143, before it) was the same Lost City 'no way to Valley of Snakes' repeat, left by the watchdog. Queue: Valley of Snakes never reached from Lost City in 3 games running (94/94 rooms explored, 16 with no way); read-only study -> rca/2026-10-20/valley-of-snakes-findings.md.
- 2026-10-20 01:19:43 verified: 'agenda: no way on from level 44: its next level is dropped for the game', Save and Exit 0.1 s later (game 131 s, +613,437; no 45 s stand).
- 2026-10-20 01:27 study done (rca/2026-10-20/valley-of-snakes-findings.md): 44<->45 is a border; `exits.border_exits` marks the middle room touching 45, on cliff (game 3: room 379 'Desert Cliff Left Ends', 20.8 tiles from the canyon opening at rooms 373/374); `through` pushes 1 tile out over cliff; teleport.Way finds no footing within FAR_TILES. Fix (agent, in progress): with ground, a mark inside the rooms snaps to the nearest outward edge tile with footing (~24 tiles), then crosses.
- 2026-10-20 01:32 Valley of Snakes fix in (agent): levels/exits.py `through`/`passage_of` take the read grids; a mark inside the rooms goes to `open_edge` (the nearest outward edge tile with footing within EDGE_SNAP 24 tiles, lru-cached, 0.3 ms) before crossing; guide.py `_target_of` and running/valuables.py `crossing` pass the ground. Fixture tests/inventory_tracking/fixtures/levels/lost_city_valley_border.json; tests in test_exits.py (2) and test_tz_leveling.py (1). Wide suite + levels 2935 green. Restart queued. Verify: the next Lost City game crosses into Valley of Snakes ('agenda: next next level: on into Valley of Snakes' then a level run of 45).
- 2026-10-20 01:36:24 recovery: the zone is all of Kurast; Upper Kurast (81) -> Kurast Causeway (82): 'at Kurast Causeway: going through takes a press', then 'TZ next level' / 'no hop toward Kurast Causeway: the character is beside it' x30 in 1 s, the again-and-again guard left the game (nothing lost). Take 20261019T223442Z-81: no room's leads_to names 82, so exits.py `outward` was None, `through` None, the open passage taken for a door. Fixed: `outward(rooms, to, mark)` falls back to the mark's side of the rooms' middle (north here: far place (968, 486.75) tiles, snapped to (967.5, 486.75)). test_exits.py updated (+ a north case, a mark at the middle stays None). Suite 3045 green. Restart queued.
- 2026-10-20 01:41:16 restart `62049b9d`: the Causeway fallback live. 01:41:08 (9d80d070, before it) was the same Upper Kurast -> Causeway repeat, another layout (mark (1160, 368) tiles); offline on take 223956Z-81 the far place is now (1159.5, 358.75), past the north edge (ymin 360). Verify: the next Upper Kurast game enters Kurast Causeway.
- 2026-10-20 01:47:26 recovery (fix live, still): Upper Kurast -> Causeway 'going through takes a press' again. Root: the Kurast handler's 'Kurast Causeway' Poi has no area (PoiSpec carries none), so `passage_of` saw no level and the mark stayed a door. Fixed: exits.py `poi_area` (the Poi's area, else the one level whose shown or short name is its label, ways out only); `passage_of` and guide.py `_target_of` (`into`) use it. Test `test_a_handlers_way_out_names_its_level_by_its_label`. Suite incl. scenarios 5413 green. Restart queued.
- 2026-10-20 01:51:34 recovery (first of its kind tonight, 1 in 22 Sling casts): Sewers Level 2 after Khalim's Heart, 'no Town Portal opened 2.5s after the cast from the Sling', the game left (0 drops on the ground). Noted; fix if it repeats.
- 2026-10-20 01:55:07 restart `c132cc20`: `poi_area` live (the Causeway mark names level 82).
- 2026-10-20 01:54:14-01:55:00 recovery: Sewers Level 1, the agenda's Super chest opened ('Super chest: opened', 5 magics), then 'At Super chest' / 'what the object used brings comes first' every 0.2 s for 45 s, the watchdog left the game (nothing valuable left; the magics were 'left'). 1 of 2 chests in the session. RCA + fix to an agent (rca/2026-10-20/super-chest-settle-findings.md).
- 2026-10-20 01:58:53 repair skipped: 'the cost not read': tesseract found no eng.traineddata, tmp/ (with tmp/item-ocr/tessdata) is gone. Fixed: repair.py TESSDATA -> pricing/raw/ocr/tessdata (the same file kept there; reads the saved quote 'REPAIR ALL EQUIPMENT: 10745'). Test `test_the_ocr_data_is_kept_out_of_tmp`. Goes live with the next restart (after the chest agent's edits).
- 2026-10-20 02:06 chest fix in (agent; rca/2026-10-20/super-chest-settle-findings.md): the take showed one chest under three unit ids (the client names it anew when its room reloads); the agenda chased a stale id and `operate` renewed `settled_at` at an already opened chest. Fixed: teleport.py `used_already`; moves.py `operate` renews the wait only for an object not used before; agenda.py `observe` keeps one goal per chest place; choice.py `agenda_chests` counts tried-out units as spent out of sight. 2 tests in test_tz_leveling.py. Wide suite 3049 green. Restart queued with the repair OCR path (02:05:13 skipped again on the old path).
- 2026-10-20 02:07:02 restart `9e091a26`: the chest fix and the repair OCR path live. Verify: the next repair reads its cost; a reopened Super chest leaves in under a second.
- 2026-10-20 02:07:38 verified: the repair read its cost, 11,571 from the carried gold (833,916 -> 822,345); the most worn item was at 4/12.
- 2026-10-20 02:11 hour check (01:13-02:10): 31 games, 32.3/h, median 94.5 s; ~18.1M exp/h said by the loop (24.8M over ended games); 0 MISSED; 7 recoveries, each fixed since (Valley of Snakes x2, Causeway x3, chest settle x1) but the one Sling Town Portal miss (noted). Lost City the slowest level a minute (177k/min, Valley never reached before the fix).
- 2026-10-20 02:17:08 note (1 in 10 visits): The Ancients' Way run 11 s, +29k (others 32-66 s, +189-492k): 'agenda: no target here: the route's own goal' with 4 leaders known, then on into Icy Cellar. Candidate: why leaders known were not targeted (REMEMBERED_NEAR / tour); look if it repeats.
- 2026-10-20 02:34:20 the short zone run again (2 in ~15 games): Crystalline Passage 11 s, +50k (others +173k/+472k), 'agenda: no target here: the route's own goal' after 2 elites and a Unique Ring (picked up); Frozen River's door beside the waypoint. Read-only study -> rca/2026-10-20/short-zone-runs-findings.md.
- 2026-10-20 02:41 study (rca/2026-10-20/short-zone-runs-findings.md): no defect. Waypoint levels 118 and 113 are ON_THE_WAY by policy_of (the next level holds a boss stage: Snapchip Shatter, Frozenstein); ON_THE_WAY takes leaders in sight and remembered within 45 only, no room search. Short runs = the waypoint 107-151 units from the door (4 games, +29k-110k) vs 234-437 (+173k-492k). Options (each the player's ruling, open Q2): COVER for 118/113 via tzroutine.py POLICY; remembered leaders within 90 on ON_THE_WAY; one more look at the door. Not changed.
- 2026-10-20 03:10 hour check (02:07-03:10, session 9e091a26, all fixes live): 35 games, 33.5/h, median 105 s, p90 158 s; 15.7M exp/h; 0 recoveries, 0 stops, 0 MISSED (2 harmless shop-card races). Frozen Tundra (new zone at 03:00) 172k/min against 333-405k/min for the 02:00 zone's levels.
- 2026-10-20 03:30:20 STOP: 'the terror zone Act1-MooMooFarm is not playable: no excursion' (cause idle -> STOP), the loop off in the Rogue Encampment. Fixed (the loop never stands): tzloop.py raises cause 'zone' with `loop.cooling` to `zone_wait` (ZONE_SETTLE 20 s after the next ZONE_TURN 1800 s of the wall clock; zones turned on each half hour 01:30-03:30); stops.py 'zone' -> LEAVE; loop.py `leg` sleeps the pause in COOLING_SLICE slices, a cancelled run ends it; `overdue` not counted while cooling; `recover` keeps a longer cooling. Tests in test_tzloop.py, test_stops.py, test_loop.py; suite 3053 green. Restart with the loop on at 03:34.
- 2026-10-20 03:34:19 restart `63f10842` (loop on): 'the next zone in 1560 s: the game is left at once and the loop goes on', then 'waiting 1560 s before the next leg' (stood in the Rogue Encampment, safe; the game left after it). Verify ~04:00:20: the next zone read and played.
- 2026-10-20 03:37 watch.py: WAITING (logwords.py) holds STALL off for the loop's own wait ('loop: waiting N s before the next leg'); test in test_loop_watch_lines.py; the watch re-armed.
- 2026-10-20 04:00:20 verified: the zone wait ended on time (zone Barracks + Jail levels read at 04:00:00), Save and Exit, a new game at 04:00:21, prebuffing by 04:00:30. No STALL during the wait.
- 2026-10-20 04:01:32, 04:03:02 recoveries: Outer Cloister -> Barracks (zone Barracks + Jail): 'Barracks: an open passage: walking through' then 'no move toward Barracks: the character did not move' x9, the 45 s watchdog left the game (twice, nothing lost). Take 20261020T010037Z-27: a closed door, class 24 mode 0, at (15141, 4802) in the 4-unit gap of the level's edge wall. Fixed: teleport.py USES gains the door classes (levels/doors.py `door_sizes`), game/decode.py USED reads doors among the things, hunting/moves.py `advance` opens a closed door across a passage's walk (`door_across`, DOOR_NEAR 15) by `use_thing` before walking. Test in test_hunt.py; suite incl. game 3062 green. Restart queued for the next lobby.
- 2026-10-20 04:07:56 restart `315db9a2` (loop on, TZ leveling): the door fix live. Game 5 before it (04:07:49) was a third 45 s Barracks door stall on the old code. Verify: 'Opening the door to Barracks' / 'Barracks: the door is open' on the next Outer Cloister -> Barracks crossing (zone until 04:30).
- 2026-10-20 04:08:27 verified: 'Opening the door to Barracks, 8 away' -> 'Barracks: the door is open' (0.5 s), walked 10 units through, 'on into Barracks' at 04:08:28. The Outer Cloister -> Barracks stall is gone.
- 2026-10-20 04:28 five-game check (zone Barracks + Jail, since 315db9a2): games 1-5 clean, 206-270 s, 1.0-1.2M exp each (~17M exp/h), 0 recoveries, 0 MISSED; two visits full contract; Gheed's Fortune kept, Cathan's Seal sold as a surplus copy. 'staff ?' in the visit line = no Teleport-charge staff read (long-standing, harmless). Next: the 04:30 zone turn.
- 2026-10-20 04:32:49-04:32:58 recovery (zone Worldstone Keep 2-3 + Throne + Chamber, 'Baal from 129: [129, 130, 131, 132]', 128 skipped): Throne of Destruction done (35/35 rooms), then 'TZ next level' into the Worldstone Chamber (no way: opens only after Baal) made again every 0.3 s ('nothing is left to go to on this level: no route stage, no boss known'), the repeat guard left the game (nothing lost; game 7 172 s, 1.15M exp). Fixed: runner.py `_run_over` drops the way on (agenda `no_way_on`) also when a level done (agenda.finished) ends its run with pursuit.py NOTHING_LEFT. Test in test_runner.py; focused 165 green. Open for the player: Baal's waves and Baal are not done in this zone (the Chamber is never reached).
- 2026-10-20 04:36:11 restart `98388b04` (loop on, TZ leveling; wide suite 2953 green): the Throne fix live. Game 8 (04:36:03) was a second Throne repeat on the old code. Verify: after 'agenda: level 131 done', 'agenda: no way on from level 131' and the game's own end, no repeat guard.
- 2026-10-20 04:39:05 verified: 'agenda: level 131 done' -> 'no way on from level 131' (0.14 s) -> 'leave game: no goals left' -> Save and Exit. Game 1 175 s, 726k exp, no repeat guard. Note: Worldstone Keep 3 run 8 s (ON_THE_WAY: its next level has the Baal stage), the open short-run question (Q2).
- 2026-10-20 04:45:22 recovery (Throne of Destruction, take 20261020T014314Z-131): 'seek Lister the Tormentor: nothing in reach here yet' from 04:44:37, no living hostile in the read (19+9 corpses, the merc, summons), no wave came; the 45 s watchdog left the game. `empty_mark` skipped seeks of a boss not known yet. Fixed: judging.py `empty_mark` gives such a seek up after SEEK_WAIT 20 s (hunting/base.py), a wave fought (Hold) counts its wait afresh; then the level is explored for it, ends, is done, and the Throne fix leaves the game. Test in test_tz_leveling.py.
- 2026-10-20 04:46:43 recovery (Worldstone Keep 2, take 20261020T014539Z-129): 45 s in one place in a fight, full life 2937, 13 of ~35 Stone Skin hostiles killed, the no-move watchdog left the game mid-fight. Fixed: combat/score.py `LiveScore.killed` (running kill count); loop.py `still(..., kills)` counts a stand afresh on a kill; running/watch.py passes the hunter's count. Test in test_loop.py. Focused 408 green; wide suite running, restart after.
- 2026-10-20 04:53:3x restart `9a440c48` (loop on, TZ leveling; wide suite 2955 green): SEEK_WAIT for unknown-boss seeks and the kill-aware no-move check live. Verify: 'no boss here after 20 s' at the Throne instead of the 45 s watchdog; no stall in a fight that kills.
- 2026-10-20 04:57:39 verified: Throne 'seek Lister ... no boss here after 20 s' -> explored (35/35) -> 'level 131 done' -> 'no way on from level 131' -> 'leave game: no goals left' -> Save and Exit at 04:57:42 (3 s after the give-up, no watchdog). Game 1 249 s, 1.61M exp.
- 2026-10-20 05:09 five-game check (since 9a440c48): games 1-5 clean (145-249 s, 0.5-1.6M exp), 0 recoveries, 0 MISSED; zone turned at 05:00 to Arreat Plateau (112 only; 126 Pit of Acheron skipped: its red portal not read yet), ~0.5-0.6M exp a game. The kill-aware no-move check still to be seen in a long fight.
- 2026-10-20 05:35:30 DISCONNECT (zone Dark Wood + Underground Passage, game 15 cyberr72): the game vanished mid-fight ('the fight stopped (not in a game)', life 2937/2937, no death); Battle.net dropped the client to the character screen, **Offline** tab, CyberA (level 2 Paladin) selected (screenshot 05:39). The loop's NEXT_GAME leg then clicked the lobby's game-name field and typed into that screen for 5 min: 'cyberr72 was not created', 'the game name field did not take the keys' x8, 'next game again and again'. Nothing changed on screen (05:40 screenshot: the same 3 offline characters, no dialog). Loop turned off 05:40:43 (`caeecec1`). Fixed: actuator Cause 'lobby' on create_next_game's three Aborts (routines.py); stops.py `first`: one lobby failure LEAVE (tried again), LOBBY_STOPS 2 in a row STOP; Loop.lobby_fails counted in recovery.py, reset by a game made (loop.py `next_game`). Test in test_stops.py; wide suite 2958 green. Restart `834c4951` 05:43:43 with the loop OFF. Waiting for the player to reconnect (Online tab) and turn the loop on.
- 2026-10-20 08:21:22 PLAYER: loop on (after the Battle.net reconnect); the first game made at once; zone Catacombs (Andariel from 32: [32-37]). Watch and danger watch re-armed.
- 2026-10-20 08:22:37-08:24:58 REGRESSION (zone Catacombs, games 2-9 of `834c4951`): every game ended in Inner Cloister ~20 s in, 0-86k exp. The 04:36 Throne fix took ONE 'nothing is left to go to' end of a done level (Inner Cloister, ON_THE_WAY, done in 5 s) as no way on; that end is the crossing's first look. Logs: a good crossing (Outer Cloister -> Barracks) had 1 such end, the Throne 28. Fixed: agenda.py `nothing_left` counts them, NOTHING_LEFT_ENDS 5 in a game before `no_way_on`; runner.py calls it. Test in test_runner.py; wide 2958 green. Restart `4188f3cb` 08:25:04 (loop on).
- 2026-10-20 ~08:24 RULING (the player): Catacombs zone "we must not just end in inner cloister / there are 2 options: inner cloister -> cathedral -> catacombs level -> kill andy / or cat2 -> cat 3 -> cat 4 -> andy". Verify: games reach Andariel and kill her.
- 2026-10-20 08:25:23 the NOTHING_LEFT_ENDS fix not enough: 5 ends in 0.8 s, game 1 of `4188f3cb` still left in Inner Cloister. Cause: no level handler for Inner Cloister (32) or the Cathedral (33): no card mark for the route's enter('Cathedral') stage, so its goal is None and every next-level run ends at once (the press deferred to the route step, the sweep takes it). The Catacombs zone was never played before tonight. Loop OFF 08:25:53 (`61c32a19`). Fixed for now by the player's second route: tzroutine.py START_AT {'Andariel': 35} (the trip from the Catacombs 2 waypoint; 32-34 skipped). Tests test_tzroutine.py, test_tzloop.py updated; wide 2958 green. Restart `c0cb0229` 08:28:42, loop ON. 08:29:18 verified: Catacombs 2 done, on into Catacombs 3. Agent on Inner Cloister / Cathedral handlers (levels/handlers) for the first route.
- 2026-10-20 08:30:01 STOP (Catacombs 4, game 1 of `c0cb0229`): Andariel killed 08:29:53 (the Cat2 route works); Set Occult Codex dropped, inventory full ("make room"), room made in the cube 08:30:00, then the zone turned at 08:30 and `choose` raised 'no terror zone is read in this game' on every leg: FETCH once, then 'the loop stops here' (valuable on the ground). Fixed: tzloop.py `choose`, no zone read with a valuable sighted out of town: the agenda's PICKUP of it first, then the game's end. Test in test_tzloop.py; wide 2958 green. Agent held (nothing on disk). Restart `5231fa2f` 08:31:59 loop ON: the Codex was already carried at its first look (picked up while stopped, likely by the player), so nothing was lost; the game left (no zone), the next game reads the new zone.
- 2026-10-20 08:32-08:38 zone Chaos Sanctuary (108 only; River of Flame 107 transit): games 2-3 killed Diablo (852k, 1.01M exp), then 08:38:04 STOP 'idle: 3 games in a row with no level run'. Cause: the River's NEXT_LEVEL run carries on into the Sanctuary (seals, Diablo) in one run, no LEVEL leg, and only a LEVEL leg reset `loop.idle`. Fixed: tzloop.py `choose`, a new game after one with a worked run (agenda.worked) counts afresh. Test in test_tzloop.py (fails without the fix). Agent done: levels/handlers/cathedral.py (Inner Cloister 32: Cathedral doorway, waypoint, Jail 3; Cathedral 33: Catacombs 1 stairs, Inner Cloister back), confirmed=False, 7 tests; START_AT {'Andariel': 35} kept until a game from the Inner Cloister is watched (its note: spots.pinpoint moves a way-out mark onto a one-warp preset's warp, worked around by variant=None; a closed door at the doorway is possible). Wide 3075 green. Restart `af106adc` 08:40:28, loop ON.
- 2026-10-20 ~08:42 RULING (the player, keeping): duplicates only for expensive items; a cheap item (like 0.6 Ist) kept only if better than owned copies; know the valuable rolls of every kept item. Plans: valuable white/grey bases, +3os daggers, merc 4os eth bases, expensive blues, Monarch of Deflection 4os, field identify by scroll and drop the bad, identify scroll restock; one loot abstraction (loot.items / item.is_keep / item.drop / loot.occupied / loot.optimize_space / town_routine.run). Design agent started: inventory_tracking/loot/design.md.
- 2026-10-20 08:48:46 PLAYER: loop off (game 4, River of Flame crossing). Waiting for 'loop on'.
- 2026-10-20 08:49:43 PLAYER: loop on.
- 2026-10-20 08:43:48 game 2 of `af106adc` (zone Chaos Sanctuary): the player saw "reached CS and immediately save/exited". Agent study rca/2026-10-20/crossing-teleport-back-findings.md: right after the passage into 108, the agenda's kill target was a River of Flame elite still in the client's units (the monster read has no level, and 108's map was not read yet); the Teleport toward it landed back in 107, whose route step was done, so 'no way on from level 107' and the game was left. The "Echoing Strike is on no skill key" stop was a cancel race (its message wrong, harmless). Fixed F1: hunting/choice.py `agenda_target` counts a leader (live or remembered) only inside this level's rooms (levels/route.py `room_at`); no rooms read, none. Test in test_tzloop.py (fails without the fix); wide 3076 green. F2 (the stop's message) and F3 (carry a run back across) not done.
- 2026-10-20 08:54:38 PLAYER: loop off (after game 5: 172 s, 1.07M exp). Restart `185d40a7` 08:55:24 with the loop kept OFF: F1 live. Waiting for 'loop on'.
- 2026-10-20 09:03:54 PLAYER: loop on (F1 crossing fix live since 08:55:24).
- 2026-10-20 09:19:08 'trade session done (short of the contract: block 2x4 taken, junk left 4)': carried gold 920,176 of the cap 940,000 (level 94), the stash's gold full ('no deposit again until a restart'), so shop.py sold nothing ('no sale over the cap (4 items kept)'). Fixed by the player's 08:42 ruling ("we don't need money from selling these items"): visit.py DROP_CAPPED_JUNK, the loop's junk left unsold with the gold read at its cap is put down in town (cube.drop_item, protected items never). Test in test_visit.py; wide 3077 green. Restart queued at the next lobby. The gold at its cap will block every sale from now on: the loop's junk is dropped each visit.
- 2026-10-20 09:22:20 restart 20261020T062214Z-65c72ef6 (DROP_CAPPED_JUNK live). Verified at 09:22:59-09:23:03: carried gold 940,000 of 940,000, four vendor items (a magic Grand Charm, a Large Charm, a rare Ring appraised vendor at 09:11 and 09:18, one more) 'dropped in town: the gold is at its cap and no sale is made'; 'trade session done: cube 0 items, block 2x4 free, … junk left 0'. The set Ring copies kept was not dropped.
- 2026-10-20 09:22:12, 09:26:02, 09:27:20, 09:30:09: four 45 s no-move stalls, each the same: a gold pile (7679, 7464 gold) at the gold cap. The game puts a clicked pile back down under a new unit id, the pickup says "picked up", and the next look aims for it again. Fixed in game/memory.py: `gold_room` (level x GOLD_PER_LEVEL less stat 14) leaves a pile over the room out of the look ('gold pile N: A gold over the cap (room for R): left', once a pile). LEVEL_STAT and GOLD_PER_LEVEL moved to game/layout.py (shop.py imports them). Test test_memory.py `test_a_gold_pile_over_the_gold_cap_is_left_out_of_the_look`; tests/inventory_tracking all 7490 green. Restart 20261020T063012Z-defdd01a at 09:30:16.
- 2026-10-20 09:26 watch: 'MISSED: rare Ring at (5094, 5062)' was the loop's own town drop (the census sees it before the drop's line). games.py `put_down` + logwords TOWN_DROP: an item first seen within 20 lines before a 'dropped in town' line is no miss; test `test_the_loops_own_town_drop_is_no_miss`; watch re-armed with it.
- 2026-10-20 ~09:33 PLAYER rulings: "tz leveling should do baal and trone fight" (the Throne waves and Baal, not left after the Throne's exploration); "start M0+M1" (loot/design.md, the recommended answers). Two background agents: Throne/Baal (tzroutine/agenda/hunting/handlers), loot M0+M1 (inventory_tracking/loot/, shadow hooks only).
- 2026-10-20 ~09:35 PLAYER: "we need to open superchests when we encountering them" (Maggot Lair zone, passed unopened). Agent on it: rca/2026-10-20/superchest-findings.md.
- 2026-10-20 ~09:45 superchest agent done (rca/2026-10-20/superchest-findings.md): Maggot Lair's sparkling chests are TombChest1/2 (87/88) at `PlaceUniqueChest` spots (levels/model.py UNIQUE_CHEST); hunting/choice.py took only class 397 as a super chest. New macros/superchests.py (ENABLED, unique-chest spots from preset_objects.json, mark_use), choice.py super_chest_goal/agenda_chests/agenda_chest. Replay of six Lair takes: 8 of 26 chests within CHEST_NEAR 60 would have been goals (18 seen only 61-98 away). Tests test_superchests.py, test_tz_leveling.py, test_herald.py (31 green); wide 2975 green. Restart 20261020T064837Z-ec3dab8e at 09:48:42. Verify: 'agenda: target Super chest (open, ...)' -> 'Super chest: opened' in the next Maggot Lair (or any unique-chest level) game.
- 2026-10-20 09:39-09:44 during the player's pause: the player's own items on the town ground (Crown of Ages, set rings/amulet, rare amulets, Gheed's); 'MISSED: game None' lines; Gheed's carried at 09:44:41; the rest asked of the player.
- 2026-10-20 09:50:13-09:50:14 verified (Maggot Lair 62): 'agenda: target Super chest (open, tier 5)' -> TombChest1 (class 87) 'Super chest: opened' at (17532, 6661) and a second at (17532, 6684); four rares spilled, the Horned Helm taken by the shown rule, the rest left by the pickup rules.
- 2026-10-20 ~09:52 PLAYER: "nope, in maggot layer 3 superchest wasn't opened". 09:50:19-09:50:53: Level guide 'Treasure room: east', the run went north to Coldworm and left; the treasure room's unique-chest spot was never within CHEST_NEAR 60. Superchest agent resumed: go to every unique-chest spot the read rooms show before the level is done.
- 2026-10-20 ~09:53 PLAYER: "in coldworm's room there was a glowing chest - we always should try to open such chests whenever we encountered them" (relayed to the superchest agent).
- 2026-10-20 09:54:25-09:54:28: the player took the mouse in town: 'the mouse was moved: the leg is made again' x3 in 1 s -> 'agenda: the town visit dropped: its leg stopped 3 times' -> Save and Exit under the player's hand (Tab pressed) -> 'Save and Exit again and again'; the player turned the loop off 09:54:29. Nothing lost (in town). Fixed: tzloop.py perform: a Hand stop (the player's input) is re-raised before agenda.failed, so it never counts toward TRIES. Test test_tzloop.py test_the_players_own_input_is_no_failure_of_the_leg; tzloop/agenda/runner 175 green. Not live yet (with the next restart).
- 2026-10-20 ~09:56 Throne agent done (rca/2026-10-20/throne-waves-findings.md): the waves need the hall clear and the character in the hall; the TZ fight stage for Lister had no mark and became a level-wide seek 135-194 units off the throne. New hunting/throne.py (THRONE_WAVES, WAVE_WAIT 60, BAAL_LEAVES 30, PORTAL_SECONDS 30), hook in choice.py goal(), loop.still(waiting=), watch.py passes waves.due; levels/model.py THRONE_PORTAL in CLICKED, teleport.py USES[THRONE_PORTAL]. Portal click untried in the game (fallback: no_way_on(131) as before).
- 2026-10-20 ~10:00 superchest agent round 2: Lair 3 treasure spots never within 97 units; Coldworm's glowing chest is objects.txt 356 (StaffOfKingsChest), never read (quest chests left out of containers.json). Glowing chests now from objects.txt Overlay 1 + PopulateFn 3 (macros/data/glowing_chests.json: 354-356, 397, 405-407, 455; game/decode.py glowing_chests); superchests.LEVEL_SPOTS: every unique-chest/glowing spot of the level is a goal before the route's own (choice.py level_chest). NOTE for a commit: decode.py loads the untracked glowing_chests.json.
- 2026-10-20 ~10:03 loot agent M0+M1 done (shadow only; rca/2026-10-20/loot-m0-research.md, design.md §9): 72 acceptance cases, 33 strict xfails of today's code. Finding: appraisal/service.py:752 builds IdentifyWorker without owned=, so owned_verdict never runs in the loop (the third Goblin Toe stashed). R1 no (unidentified: no affixes, no sockets), R3 no, R2 partly; ground ED read always 0 (stat 16 is in the +0xD0 chain).
- 2026-10-20 ~10:03 the git index has staged entries (loot files, superchests, choice.py, the journal, tests) that no agent of this session staged; left as is for the player.
- 2026-10-20 10:05:26 restart 20261020T070526Z-c221adbb (loop kept off; tests/inventory_tracking + skills 7840 green): Throne waves/Baal, superchests round 2, the Hand fix, loot shadow live. The game process was gone since 09:57:44 (closed while the loop was off): the service waits for D2R.exe; no resume line until the game is back.
- 2026-10-20 ~10:15 (game closed; the player: "we're paused game for some time / we need to progress with code"): F2 done: hunt.py attack mode's two `except Abort` handlers raise Cancelled when run.cancelled is set (the runner's cancel racing the strike check said "Echoing Strike is on no skill key and on neither mouse button" as a stop). Test test_hunt.py test_the_runners_cancel_racing_the_strike_check_is_a_cancel_not_a_false_stop; hunt 173 green. Agents started: loot quick fixes (+3 Apocalypse in VOID_STAFFMODS, ground ED read), M3 (loot/storage.py, byte-equal, visit snapshot replay), Throne portal/waves offline check against the 10-11 takes.
- 2026-10-20 ~10:18 PLAYER: "also start M4 field identify". Agent started: loot/api.py FIELD_IDENTIFY, G6 (magic Monarchs) on by default, G9-G11 built but off until ruled; field drops only of items picked for an M4 class.
- 2026-10-20 ~10:30 loot quick fixes done: pickmode.py VOID_STAFFMODS = {402 Abyss, 389 Hex Purge, 401 Apocalypse} (skills.json); ground ED: game/decode.py chain_defense reads stat 16 from the +0xD0 modifier chain (owned_chain in items/modifiers.py, socket-filler lists skipped), Rolls.defense None when unread (not cached); replay of 106,658 captured item reads all equal. Live after the next restart: +3 Apocalypse 3os Void daggers, superior Monarchs >= 15% ED; census shows 'N% ED'. Not live yet.
- 2026-10-20 ~10:35 Throne portal check done (throne-waves-findings.md §5): FinalPortal 563 at (15090, 5005), never read in a take; Baal turns 543 -> 559 (baalcrabstairs) 10-11 s after the last wave and walks in; the portal goal had started under the walking Baal: seat_of counts 543/559, hall fought first while he is read, BAAL_LEAVES from the hall's clear, PORTAL_OPENS 1.0 s after he is gone. Clicks that took: (+11,-26) .. (-1,-49) px; the click walks to the foot, a second click from the foot may be needed (handled by use_thing). use_thing's log line now has the object's mode and selectable flag. Wave gaps 11.5-13.5 s (41.5 s when away): WAVE_WAIT 60 kept.
- 2026-10-20 ~10:50 M3 done (design.md §9): planning moved to loot/storage.py from cube.py, town.py and stash.py (resource tables, to break an import cycle), re-exported; Storage/room/room_low/cells_low/occupied; loop.py room arithmetic through storage. Replay: 13 fixture visits (52 stops) golden + opt-in slow replay of 191 local snapshots / 727 stops against the pre-move code from git: all equal.
- 2026-10-20 ~11:00 M4 done (design.md §9): loot/api.py FIELD_IDENTIFY = True, CLASSES = {'G6'} (magic Monarchs; G9-G11 built, off until ruled), IDENTIFY_RESERVE 5 (shop.short, town contract 'identifies N'), only while the KP_6 loop is on; loot/hands.py GameHands (Tome clicks of junk.identify, the worker's appraisal, cube.drop_item, PutDown.reject); quiet rules (no hostile in SIGHT, life over the floor, no pickable valuable, not in town). Hooks: portal.py to_town, loop.py leave, running/execution.py before make_room; pickmode kept/is_candidate take FIELD.pick. Second guard `droppable` never drops sets/uniques/runes/gems/potions/charms/jewels, want rows (4os, Deflecting) or >= 1 Ist. Log: 'loot: field: ...', 'dropped in the field: ...' (logwords FIELD_DROP, no MISSED). Side finding: unit 1728653239 is a Monarch 'of Blocking' (suffix 172), not Deflecting (173).
- 2026-10-20 ~11:02 full suite tests/inventory_tracking + skills 8016 passed exit 0, ruff/pyrefly clean. Restart asked (--loop keep): the service waits for D2R.exe (game closed since 09:57) and has not taken the request yet; it should on the game's start. Live then: Throne waves/Baal + portal fixes, superchests round 2, Hand fix, F2, loot shadow, +3 Apocalypse, ground ED, M3, M4 (G6).
- 2026-10-20 ~11:05 PLAYER: "turn on G9-G11 too": loot/api.py CLASSES = {G6, G9, G10, G11} (magic Monarchs; magic/rare daggers and grimoires; magic/rare circlets; magic rings/amulets). test_api.py updated; loot+macros 2306 green. Live with the pending restart (the game's start).
- 2026-10-20 11:49:08 the game back: session 20261020T084902Z-edc16eeb took the queued restart (all of today's code live). Game 2 (TZ): a magic Ring picked for G11 at 11:51:11 ('loot: shadow: ... new pick G11 identify / old leave'), never identified: 'loot: field: Town Portal: 1 to identify wait: 3 hostiles within 30' (11:52:40), then 'Save and Exit: 1 to identify wait: in town (Cain)'. PLAYER: "in the last run we picked up magic ring and haven't id'ed it. is that correct behavior?" Fixed: loot/hands.py unquiet: town is quiet (the tome there, not Cain's next trade visit); test test_hands.py test_in_town_it_is_quiet_and_the_tome_identifies_there; loot+macros+skills 2409 green. Restart 20261020T085917Z-d75cbf1c 11:59:22 (loop off, TZ leveling).
- 2026-10-20 ~12:00 PLAYER: (big items) "we want to check them and drop in the middle of the run, without caring them along occupying a lot of space to the town"; then "start all three": 1) field identify of shown magic/rare >= 4 cells, 2) 8-cell magic/rare spears/polearms/bows picked for the field check, 3) M5 ground bases (ROLLED_TYPES widened, want rows only). One agent (shared files).
- 2026-10-20 ~12:10 PLAYER: "when we visit cain it identifies all items across cube + inventory, so, in most cases this is preferrable way to identify items when in town". The trade visit runs at the next game's start (after the TZ waypoint), so the field batch in town now waits for Cain when that visit is due: loot/hands.py GameHands.cain_ahead, running/execution.py field_hands passes (room_low and carrying) or short or repair; with no visit due the tome identifies in town (11:59 fix). Test test_hands.py test_in_town_with_a_visit_due_cain_identifies_them_there. Not live yet (with the big-items agent's restart).
- 2026-10-20 ~12:15 PLAYER own-use bases: merc Insight (BiS, eth preferred), Paladin Exile (4os, all res >= 40, eth preferred), merc Cure (3os helm), merc Chain of Honor (4os armor, Archon Plate?, eth ok). Added to the big-items agent's M5 step as own-use want rows.
- 2026-10-20 ~12:18 PLAYER: "also keep a base for spirit monarch" (added to the big-items agent's own-use rows).
- 2026-10-20 ~12:45 big-items agent done (design.md §9): GOOD never picked shown magic/rare non-jewelry before (the census 'taken (shown)' is before the level's filter). G14 (loot/api.py FIELD_BIG, BIG_CELLS 4, leaves a 1x3 free, other valuables first), G15 (FIELD_OVERSIZE: shown classes over 6 cells, loot/shown.py oversize_rules), M5 (loot/ground_judge.py BASES; ROLLED_TYPES + pole spea aspe tors abow swor axe helm; Rolls.damage stat 17 and tabs stat 188; wants.json 89 rows, G16 market bases per Q7). Own-use: Insight = G3 eth merc polearms (+ Matriarchal Spear); Exile = white Sacred Targe/Rondache 0/4os all res >= 40; Cure = G17 eth 0/3os Corona/Spired Helm/Bone Visage/Demonhead (not live: no filter Show rule); CoH = eth 4os Archon Plate; Spirit = non-eth 4os Monarch in LEFT_ROWS (one owned: MSockB/MSockC). 11 M5 xfails now pass. Fragile: build_wants cites pickmode.py line numbers (rerun build_wants after edits). Full suite 8087 passed exit 0; restart 20261020T094705Z-49f6ab71 12:47:09 (loop off, TZ leveling): all live incl. the Cain-in-town rule.
- 2026-10-20 ~12:50 PLAYER: "I want to try to find rare helms (tiara, corona, etc) that are really good - fcr + 2skills level + other valuable stats / I want to keep more monarch bases". Agent started: a rare helm/circlet keep rule (FCR + 2 Warlock skills + another stat, by the game data and the KB), field-checked; Spirit row out of LEFT_ROWS with an owned-copies cap (default 6).
- 2026-10-20 ~13:00 PLAYER: "add the filter show rules too" (Cure eth elite helms, rare/eth polearms, wanted oversize classes, rare circlets/helms, 4os Monarchs). Filter agent started (lootfilter skill); the player re-imports in the game.
- 2026-10-20 ~13:20 rare helm/Monarch agent done (design.md §9): FCR on a helm only on circlets (of the Magus 20 / Apprentice 10); +2 Warlock on a rare = Arch-Devil's (amulets, circlets); +2 tree prefixes Dreadful (Demon), Tainted (Eldritch), Erratic (Chaos); plain helms (Corona, Shako, Spired Helm) roll neither. G10 rows: rare circlet 20 FCR + +2 Warlock/Eldritch + a third stat always kept (dupes too); +2 Warlock without FCR, 20 FCR with +1/+2 tree/30 FRW kept (pricing.html:233, primer:482); the rest dropped in the field (keep.JUNK_UNWANTED, K8) unless >= 1 Ist by own rolls. Thin asks: +2/20/third 11.4 -> 57.1 Ist (5 sellers, 2026-09-18/19). Monarchs: LEFT_ROWS empty, keep_up_to SPIRIT_MONARCH_CAP 6, owned 2 (MSockB, MSockC) via loot/value.py owned_bases. Suite 8119 passed exit 0. Not live yet (with the filter agent's restart).
- 2026-10-20 ~13:08 filter agent done: lootfilter/warlock_lean.json + v2 (19 rules): SHOW Cure Helms Gray (urn uhm uh9 usk, lowQuality + filterEtherealSocketed: gray copies only), SHOW Rare Merc Polearms (7s8 7wc 7pa 7h7 7vo 7br), SHOW Magic Amazon Bows Spears (amb amc am9 amd ame); the player's 14 chipped/flawed gems folded into Lean; rare plain helms not shown (no FCR/+class skills on helms). The macro reads the repo profile (loot/shown.py FILTER), the game the imported one: the player re-imports 'Warlock Lean2'. Suite 8119 passed exit 0; restart 20261020T100847Z-9e6e7367 13:08:51 (loop off): rare circlet rule, Monarch cap 6, filter rules live in the macro.
- 2026-10-20 ~13:15 PLAYER: "let's retire other filters. and keep only one filter file at all". Agent started: one file in lootfilter/ (the 'Warlock Lean2' import, also build_filter's source), the rest removed, references updated.
- 2026-10-20 ~13:20 PLAYER: "I'm not sure about colosus voulge speed wise, probably we need to keep only fast bases first". weapons.json speed: Mancatcher -20 (spear), Thresher/Giant Thresher -10, Great Poleaxe 0, Cryptic Axe/Colossus Voulge +10 (210 str, 4os max); Insight itype pole/staf/miss (no spears). build_wants.py: MERC_FAST (Thresher, Giant Thresher) always-keep G3 row; new 'merc-polearm-eth-4os-superior-slow' trade row (MERC_SLOW, kept by worth). wants.json 94 rows; four fixtures updated (K5 / K10 for the unpriced spear); loot 550 green. Not live yet.
- 2026-10-20 ~13:25 PLAYER: "we will need good infinity base later": MERC_FAST += Mancatcher (spear -20; Infinity itype pole/spea). wants.json rebuilt, loot 550 green. Not live yet. 13:18:22 PLAYER: loop on (TZ loop, code of 13:08).
- 2026-10-20 ~13:25 filter-retire agent done: lootfilter/ holds only warlock_lean_v2.json ('Warlock Lean2', 19 rules, sha256 = the 13:03 build); warlock_lean.json, warlock_echoing_strike.json removed (rm), names sidecar moved to inventory_tracking/loot/data/filter_names.json (untracked: commit with build_filter.py); build_filter regenerates the four generated rules in place. Full suite 8122 passed exit 0; restart queued at the next lobby (fast merc bases, Mancatcher, filter changes).
- 2026-10-20 ~13:28 PLAYER: "identify a big items in the middle of the run (like right now we have a big hammer in cube) and probably drop them without bringing to the town". The 'hammer' = a Unique War Club put in the cube at 13:19:34 (inventory full); the field routine skips uniques/sets and cube items. Agent started: big uniques/sets field-checked (drop only surplus not-better < 1 Ist copies), cube items seen, the batch before a room trip.
- 2026-10-20 13:24:42 restart 20261020T102438Z-aeb607aa (loop on, TZ leveling): fast merc bases (Thresher, Giant Thresher, Mancatcher) always-keep, slow ones by worth; one filter file.
- 2026-10-20 ~13:30 PLAYER: magic gloves "40ias + annother valuable roll, like skills ... for javazon": task 4 of the big-uniques agent (field class, KB evidence, filter Show rule). Also: the carried gold 940,000 (09:35) -> 77,778 (13:25) with no loop spend in the logs (the player's own play while paused/closed); sales go on again under the cap. 13:25:15 'Shop check failed ... ownership/page mismatch': the HUD's shop card raced a sale (the next check complete): harmless.
- 2026-10-20 13:33:17 STOP (game 3, Tristram TZ): Wirt's body dropped a Wirt's Leg; 3 aims "under the pointer, no click picked it up", then `loop stopped: ... Wirt's Leg lies on the ground`. Cause: the game takes no second leg while one is had (the player's, stashed: unit 2992421233, class 88, visit 133027.json). PLAYER: "we should handle situation when we cannot pickup the second wirt's leg" / "if we already have one, we cannot pick another one => don't waste time". Fix: game/memory.py `had_already` + loot/materials.py `CARRY_ONE = ('leg',)`: a carry-one drop is left out of the look while an item of its class is walked off the ground (inventory, cube, stash, worn); logged once ("one is had already, the game takes no second: left"). Test test_memory.py `test_a_second_wirts_leg_is_left_while_one_is_had`.
- 2026-10-20 13:41:55 restart 20261020T104146Z-7c4977ec (loop on, TZ leveling; wide suite 8157 passed): the carry-one Wirt's Leg fix, plus the big-items agent's G18 (`FIELD_NAMED = True`: big uniques/sets field-identified, dropped only as surplus not-better <1 Ist copies) and the cube items taken out for the field identify. Verified 13:41:55: "carry-one: Wirt's Leg (unit 1548915653) on the ground: one is had already ... left", then the game left by Save and Exit with no stop. The HUD's loot mark still points at the leg (cosmetic).
- 2026-10-20 13:51:11 restart 20261020T105107Z-e9d9dd94 (loop on, TZ leveling; wide suite 8188 passed): G19 magic gloves live (every magic glove identified in the field; kept: +3 Javelin/Bow/Martial Arts with 20 IAS always, +3 Passive / +2 Javelin / +2 Martial Arts with 20 IAS as wants, or >= 1 Ist by its rolls; the rest K8 junk dropped in the field). Game data: magic gloves top at 20 IAS (of Alacrity); 40 IAS is javelins only. No filter change (SHOW Magic ARMOR covers all 15 glove codes). G18 seen working before it at 13:51:05: a unique Templar Coat identified in the field at Save and Exit = Guardian Angel, kept K5 (1 Ist by its rolls).
- 2026-10-20 ~14:05 PLAYER: "when we're running canion of the magi TZ - do we follow each small/big tomb atm or just one location?" / "use sub-agent, we need to utilize smaller tombs too - it gives a great ext/hour rate". Found: the TZ plan of Act2-TalRashas is [46] only; tombs 66-72 skipped ("tour 46→66 cannot designate one entrance", routes/tz_routes.py RouteHop.blocker), 73 no excursion; game 5 (14:00-14:02) cleared the Canyon and left at a tomb entrance. Agent started: the TZ plan takes the catalogue tour, Canyon then each of the 7 tombs (nearest not yet entered), bounded, per-tomb experience lines; Duriel's Lair out for now.
- 2026-10-20 14:03:32-14:04:20 STAND (game 6, Canyon): last Macro line `fight ... Nothing left in reach` while going for a Northern Worldstone Shard (pickup, then its guard); then only attack mode's `idle: 1 hostiles, none in reach` every 3 s; the 45 s watchdog left the game at 14:04:20. PLAYER: "find out why we have stopped in the middle of the run without moving and attacking. it seems wrong". RCA agent started (findings: rca/2026-10-20/stand-after-fight-findings.md); also checks whether the shard was left on the ground.
- 2026-10-20 ~14:17 stand RCA done (rca/2026-10-20/stand-after-fight-findings.md): the 14:03:35-14:04:20 stand was the level run standing by a magic Ring with no room (`pursuit: the inventory has no room for Ring ...: the run stands by it (the cube has room for it)`); the poll's cube room is once a game and was spent at 14:02:56 on a Unique Razor Bow, so nothing answered; the watchdog left the game with the Ring (an identify candidate, no keeper) on the ground. Same cause 2026-10-20 01:24:42 (Grand Charm, 40 s lost); 15 other idle->watchdog cases since 10-16 have other causes (10 Andariel-mark stands 10-18, 2 No way toward, 2 Khalim's Brain, 1 Gheed's). Fix: running/watch.py `stood_after_cube` (after MAKE_ROOM_AFTER 5 s: a candidate is waived and the run goes on; a kept valuable with no hostile within 30 goes to the loop's room rules; hostiles near: wait), `stand_answered` in recovery.py/runner.py; tests running/test_watch.py (9). Open for the player: stand by field candidates at all, or a second cube try a game.
- 2026-10-20 14:26:11 restart 20261020T112607Z-7288f87b (loop on, TZ leveling; wide suite 8210 passed): the stand fix (running/watch.py stood_after_cube) and the Tal Rasha's Tombs tour in TZ (tz_routes `_whole_tour`, tzroutine tour Excursion, tzloop `tour_back`, per-tomb experience lines; Duriel's Lair out). PLAYER ~14:25: "have we identified magic monarch that was dropped in the current run?" — no: 14:24:32 magic Monarch 0os seen (shadow G6), never picked: `leaves_room` (a 2x4 plus a 1x3 after) fails with the 10 free cells after a visit (the kept 2x4 block + 2); the 13:53 magic gloves likewise. Proposed to the player: take a big field item into the reserved block and identify it at once when quiet. Waiting for the ruling.
- 2026-10-20 14:28:36 first live tomb tour (game 1 of 20261020T112607Z-7288f87b): Canyon +536,677 in 125 s, then "Tomb ... gone through into level 72", "the Tal Rasha's Tomb 7 run (toured level 1 of 7)", Tomb 7 cleared +354,365 in 118 s (14:30:34). The zone rotated at 14:30 (Act1-ColdPlains: Cave [3, 9, 13]) before the way back. Tomb exp/h on this one: ~10.8M against the Canyon's ~15.4M; a measure needs whole tours. PLAYER ~14:29: gray 2os Grand Crown left: right (Cure is Shael-Io-Tal, 3 sockets, runes.json); "monarch is 2x3": the code's sizes.json says so (my 2x4 was wrong), the room skip still holds; correction sent to the room agent.
- 2026-10-20 ~14:31 PLAYER: "right now we're not using mark death for magic immune mobs. but our damage is mostly magic, so we need to engage our daemon even for regular mobs when they do have magic immunity (for WarlockAA build!)". Today builds/warlock/mark.py marks only a Herald, leaders/bosses, or a plain monster under pressure, and nothing reads monster immunities. Agent started: read immunity (live stats or monstats/monumod), mark an immune monster (after an unmarked Herald), the fight keeps going around it, switch MARK_IMMUNE. Also 14:31: a surplus Cathan's Seal (0.07 Ist, "an owned copy rolls at least as well") sold: by the copies rule.
- 2026-10-20 ~14:41 PLAYER: "why we have kept boots with <1 ist value?" — Waterwalk 0.647 Ist: the first copy (keep one of each unique, 2026-10-04), the guide's boot alternative (warlock.html §1), asks q1 0.53/median 0.67 (7 sellers, 2026-10-04) = slow. PLAYER: "why unique tresher wasn't identified min-run?" — 14:38:04 no room → the stand fix's trip to town at 14:38:09 (5 s, not 45: the fix works live); picked 14:38:57; 14:39:22 field 'room' waited (2 hostiles within 30), then both items cubed for a Grand Charm; at Save and Exit the 2x4 could not come out of the cube (no room plus the 1x3), "1 wait (Cain in town)". Sent to the room-redesign agent as a case.
- 2026-10-20 ~14:49 Death Mark agent done: MARK_IMMUNE = True (builds/warlock/mark.py:66): a magic-immune monster (stat 37 >= 100, read live off the look's stat list: decode.py monsters_and_dead, Monster.resists) gets Death Mark after an unmarked Herald, before leaders; re-marked after MARK_SECONDS; the safety stops it only under pressure with a life cost. The strike itself is physical (missile 706: SrcDam, no EType) plus cold from gear; the magic is the Hex: Purge explosions (skill 389 EType mag; 23% magic mastery, 15% pierce). Log: `Macro: mark: Death Mark on the monster N (unit): immune to magic ... (resists ...)`. Tests 81 green; wide 8251 passed. Open rulings: physical immunes too? immune before a priced leader? nearest immune first?
- 2026-10-20 14:55:11 restart 20261020T115501Z-4b07df55 (loop on, TZ leveling; wide suite 8251 passed with FIELD_AT_ONCE on): Death Mark on magic immunes (MARK_IMMUNE) and the room redesign (loot/api.py FIELD_AT_ONCE: a big field item squeezed into the visit's free block, identified at the first quiet look between level-run moves (hunt.py `field_now`), dropped or cubed; a cubed big item comes out without the 1x3 reserve). The room agent was held mid-work (final report pending). PLAYER: "why we couldn't pickup/identify/drop rare kris in the last game?" — 14:52:26 a rare Kriss (G9, 1x3) "no room ... left on the ground": gems filled the free cells, and an identify candidate gets no cube room or trip; sent to the room agent.
- 2026-10-20 ~14:58 PLAYER: "we need to optimize space (move to cube) and identify items during games / if we have no room for optimization to keep picking up items - we need to do town routine". Live after 14:55: at-once identify works (14:57:25 Bone Circlet dropped mid-level); 14:55:53 Blood Spirit and 14:56:05 Horned Helm "left: no room for its 2x2". Sent to the room agent: pack the loop's items into the cube first, identify at once, then a town trip for room (field candidates too), bounded.
- 2026-10-20 14:57:50 PLAYER: loop off (KP_6), at the start of game 2 of 20261020T115501Z-4b07df55, in town (the cube full, a visit was next); nothing on the ground. Waiting for PLAYER: loop on.
- 2026-10-20 ~15:02 PLAYER: "item wise pickups: probably we should move all items that we're going to stash in town (gems/runes/statues/etc) pickup and stash in cube, to have space for identifying items along the way". Sent to the room agent: cube the stash-bound kinds at the first quiet moment after pickup, batched, behind a switch; check the visit's cube emptying and the rune transmutes.
- 2026-10-20 ~15:03 PLAYER: "we were fighting against pack with uniq leader, but we focused rest of the pack, not leader and never death marked the leader so our daemon was still all the time". Log 20261020T115501Z-4b07df55 game 3, Spider Forest: elite 397 (1156325300) the agenda's target 15:01:05-15:01:44, no mark line at all; elite 127 refused twice by the safety's price (-0.24 s, -0.21 s) before a mark at 15:02:01. RCA agent started (take combat/20261020T120017Z-76; findings rca/2026-10-20/leader-not-marked-findings.md): why no mark, the price's demon term, the aim's leader weight, a log line for a due mark not cast.
- 2026-10-20 ~15:04 PLAYER: "and overall aim against moving enemies was pretty bad. probably we need to do some smart targeting against moving enemies". Added to the leader-mark agent (it owns the aim): measure misses by monster speed in the takes, lead the aim by velocity x blade travel time (clamped) behind LEAD_MOVING, verify with the sim replay before it ships on.
- 2026-10-20 15:21:38-15:22:39 DANGER (game 6, Spider Forest arrival): the at-once field routine (FIELD_AT_ONCE, hunt.py field_now) pressed the inventory key 1 s after the waypoint arrival (session.py inputs: only the macro's), the fight-back leg cancelled it at 15:21:39 and left inventory+cube open; the run read them as "the player's hand", attack paused, 2 healing potions while hit, the 45 s watchdog left the game. Loop off by the player since 15:28:13. Sent to the room agent: close panels on every exit (try/finally), a stricter quiet rule (radius, not after an arrival or a hit), and the loop closing panels it opened itself. Also from the room agent's report (15:0x): CUBE_AT_PICKUP, the cube room for small candidates and the trip for field items are in the tree, not shipped.
- 2026-10-20 ~15:05 PLAYER (by answer): "Sell cheap duplicates" (M2 town side on) and "Death Mark answers as is" (only magic immunity; immune before a priced leader; the nearest immune first). M2 sent to the room agent.
- 2026-10-20 ~15:40 leader-mark/aim agent done (rca/2026-10-20/leader-not-marked-findings.md): elite 397 (unique Fetish) was "trash" (1.85 casts < TRASH_CASTS 2), refused silently, died to one cast; the Thorned Hulk marks were refused because the bound Urdar (189) was not in the price (only Pit Lord/merc/Defiler measured): PRICE_ANY_DEMON on (Urdar at the Pit Lord's rate scaled 115/130: gain 0.52 s > 0.37 s cast); SAY_PASSED on (a line for every passed leader); MARK_LEADERS written, off (changes 9 golden replays); the two marks cast at 15:01:02 and 15:02:01 did not take (no mark stats on any monster; 78% take across today's 307 presses; no check exists). Aim: hit rate by speed across the line 63.9 / 58.1 / 53.9%, distance matters more (80% < 10 u, 57% at 16-30); velocity lead loses hits in replay: LEAD_MOVING off; path-record routes +0.91% points/s in the sim (needs a live path read, not built). Off-screen due cast logged. Player rulings needed: MARK_LEADERS on; leader weight in the aim; a did-the-mark-take recast; path-record lead.
- 2026-10-20 15:47:46 restart 20261020T124746Z-369d81d5 (loop keep: off; wide suite 8285 passed): the panel-left-open fix (cube.close seen_through, junk.identify finally, OPENED/tidy, field_quiet AT_ONCE_CLEAR 60 / SETTLE 3 s / HURT 3 s), the room parts (CUBE_AT_PICKUP, cube room for small candidates, the field trip), PRICE_ANY_DEMON and SAY_PASSED on; MARK_LEADERS and LEAD_MOVING off. The game was not running at the restart ("Waiting for D2R.exe"): the service waits for it. M2 (sell cheap duplicates) is the room agent's next task, not in this restart.
- 2026-10-20 16:35 M2 on (`keep.DECIDES = True`, the player's "Sell cheap duplicates"): a set/unique copy under 1 Ist, not better than an owned copy and with no want row, is sold at the visit instead of stashed. Today's replay: only The Reaper's Toll (0.653 Ist, 1 owned). Wide suite green (8293 passed). restart.py --loop keep asked at 16:35 while serve waits for D2R.exe: the request file stays and is taken up at the game's attach (service.py checks it only attached); loop off. Verify: `copies:`/`shop: sold` lines name only K6-cheap set/unique copies.
- 2026-10-20 16:47:25 restart `20261020T134725Z-faaa6310` taken up at the game's attach: "resumed after a restart: loop off, pickup good, run Andariel". Live: M2 (DECIDES True) on top of the 15:47:46 set (panel fix, CUBE_AT_PICKUP, field trip, PRICE_ANY_DEMON, SAY_PASSED).
- 2026-10-20 ~17:00 ruling (the player, "go ahead with the merge agent"): one keep/sell code path for every activity (loot/design.md §7 M6): the town visit decides with `keep.decide` like the field; the old chain (junk.junk_of, copies.sold/keep_copy, keepers.amulet_keeper, cube.drop_for) retired; K7 Small Charm fix (no price = keep, S8); ground_judge learns Worldstone Shards and Wirt's Leg. Behind a switch, shadow (log only) for ~30 cycles before it decides. Audit 16:55: pickup already one path (execution.py run.loot -> pickmode.kept -> lootpolicy.verdict); keep/sell two chains; shadow differences today: Reaper's Toll (M2), a magic Small Charm (new K7 drop vs old keep).
- 2026-10-20 17:03 fix (not live yet): CUBE_AT_PICKUP said "no room in the cube" at 16:52, 16:54, 16:56, 16:58, each time with the cube empty after a visit: an empty cube has no grid in memory (Pack.cube None). `loot/api.py cube_fits` and `room_moves` now read it through `storage.roomed`. Test `test_an_empty_cube_with_no_grid_in_memory_takes_the_stash_bound_items`; loot tests 655 passed. Ships with the merge agent's restart. Verify: "loot: cube: N of the loop's stash-bound items moved in" right after a visit.
- 2026-10-20 17:15:40 stall, game 11 (+0 exp): right after the town exit into the Outer Steppes, the run aimed at "Plains of Despair" at (5153.8, 5087.5), the Fortress gate (every other run: (5420.0, 4953.8)); "an open passage: walking through" took the character back into the Fortress (take 20261020T141454Z-103); the level run waited "on the move" 46 s; the 45 s watchdog left the game. No valuable on the ground, no danger. Agent on it (pursuit/route/TZ files; findings rca/2026-10-20/fortress-gate-passage-findings.md).
- 2026-10-20 17:35 M6 built (agent): `loot.keep.TOWN_DECIDES = False` (shadow: "loot: shadow: town merge: ..."); the visit's sale from `keep.decide` under `town_kept` guards when on; junk_of / copies.sold / _decided / cube.drop_for retired behind it. keep.py fixes live at the next restart (field + M2): K7 unpriced charm/jewel kept (S8), K1 keeps Wirt's Leg, a strictly better set/unique copy kept before K8. Wants row rare-amulet-fcr-life-skills gains +2 tree (stat 188). ground_judge (shadow) learns shards/statues/Uber keys/essences/Leg. Replay of today's 34 visits (295 items): 6 differ — Atma's Wail, Goblin Toe, Reaper's Toll (M2 sells them already), Demon Limb (mixed copy: Q-M6-3), 2 replay-limit items. Wide suite 8370 passed (agent), loot+visit 783 passed (coordinator). Open: Q-M6-1..4 (rca/2026-10-20/town-merge-findings.md). Restart waits for the gate agent.
- 2026-10-20 ~17:30 ruling (the player, "as recommended, and add grimoires to the ground read"): Q-M6-1 cheap not-better copies sold only when `slow` for the 30-cycle log (sell/check later if no keeper shows; never self/keep); Q-M6-2 under 0.25 Ist but not vendor: kept; Q-M6-3 mixed copies by score (Q2), after a weapon's ED is compared (agent); Q-M6-4 TOWN_DECIDES on after ~30 cycles of "town merge" lines with no keeper among "would sell". Grimoires: `grim` (all 15 Warlock books, wa1-waf, staff mods, up to 3 sockets) added to game/layout.py BASE_ROLLED_TYPES (read only, no wants row picks them); test `test_a_white_grimoires_sockets_are_read_off_the_ground`.
- 2026-10-20 17:40 gate fix built (agent; rca/2026-10-20/fortress-gate-passage-findings.md): `levels/exits.py` `outward` chose west by 0.6 tile (the level's middle against the three rooms touching the Plains), `open_edge` snapped to the gate tile touching only the Fortress. New `facing()` (the side most next-level rooms open on), `open_edge` never snaps to a room touching another level only; `hunt.py left_for_town` ends a field level run in a town at once (`pursuit.LEVEL_LEFT`). Once only in 21 town exits since 10-18. Changes the direction in 34 of 603 recorded layouts (act 3 jungles, act 5 highlands, Monastery Gate: 38 -> 9 tiles off the real crossing); 32 of 33 real crossings agree. Wide suite 8382 passed (agent); 312 focused passed (coordinator). Watch: passage walks in act 3/5; "run: in <town>, off the run's level ..." rare.
- 2026-10-20 17:40:50 restart `20261020T144050Z-f7a585f0` (loop on, at the game 24 lobby; "resumed after a restart: loop on, pickup good, run TZ leveling"). Wide suite 8382 passed, pyrefly 0 errors. Live: the empty-cube fix (cube_fits/room_moves via storage.roomed), the gate fix (exits.facing, hunt.left_for_town), keep.py fixes (K7 unpriced charm/jewel kept, K1 Wirt's Leg, a strictly better copy before K8), weapon ED in the copy comparison (value._observed_specs; The Reaper's Toll now a better copy), the rare-amulet +2 tree row, grimoires in the ground read, M6 town merge in shadow (TOWN_DECIDES False). Verify: "loot: cube: N of the loop's stash-bound items moved in" after a visit; "loot: shadow: town merge:" lines each visit; "ground: normal ... Grimoire Nos"; Act 3/5 passage walks.
- 2026-10-20 18:24:31 PLAYER: loop off after game 14 of 20261020T144050Z-f7a585f0. Since the 17:40:50 restart: 14 games clean (no stall, stop, danger), ~12.5M exp/h; cube-at-pickup verified (moves into the empty cube); town merge shadow agreed on every visit so far (0 differ). Open: ~30 cycles of "town merge" lines, then TOWN_DECIDES on (Q-M6-4); watch Act 3/5 passage walks (exits.facing).
- 2026-10-20 ~18:45 the player committed today's work (ea8f8ac). Rulings: "1. switch on new rules" (TOWN_DECIDES True now, before the 30 cycles: flipped; 31 visit/copies/junk tests assume the old chain's fake verdicts: the merge agent adapts them, restart after green); "2. ok" (watch the Act 3/5 crossings); "3. implement, also find out if we need to pickup other white/grey items. it looks like we don't need to pickup them to assess, so it worth to assess every item => we need a proper list and rules to determine expensive items (matron bow? offhands? shields?)" (agent: ground read for every white/grey type, a sourced base list and pickup rules, grimoires included); "4. ok, recast. pack leader/herald first" (agent: Death Mark recast when it did not take, and leaders/Heralds marked and struck first). "make sure that sub-agents are active or kill them": two finished agents of 10-19 stopped.
- 2026-10-20 ~18:55 the journal moved from `inventory_tracking/routes/lower-kurast-loop-journal.md` to `inventory_tracking/macros/loop-journal.md` (the player: "move ... somewhere into more proper place and backlink it properly"), by plain mv (the index untouched). Backlinks: root README.md map, macros/README.md KP_6 row, d2-loop-watch SKILL.md, routes/lower-kurast-loop-plan.md, routes/andariel-loop-plan.md, loot/design.md, the memories. Three agents running: town-merge switch-on tests, white/grey bases, Death Mark recast + leaders/Heralds first.
- 2026-10-20 ~19:05 TOWN_DECIDES True made green (agent): the 31 failures were test fakes giving no appraisals; the shared `Town` fake passes `appraised(...)` as Hands.appraise; 2 old-chain tests pinned False (`old_chain()`). No production change, no live defect found. Coordinator: town+loot 809 passed. Restart waits for the bases and Death Mark agents.
- 2026-10-20 18:42:41 restart `20261020T154241Z-2bf38af2` (loop on, the player had turned it on at 18:39:50; at the game 16 lobby): live TOWN_DECIDES True (one town decision; the old chain off). Wide suite 8382 passed. The bases and Death Mark agents held (no production edits yet), then "go".
- 2026-10-20 ~18:43 ruling (the player): "i'd like you to take exp shrines along the way". The macros never used shrines (HUD marks Gem Shrines only). Agent: Experience Shrines (type 15) as a side goal on the shared path, only Experience Shrines (another shrine replaces its effect), safety guards, bounded detour, switch EXP_SHRINES.
- 2026-10-20 ~18:50 rulings (the player): (a) "it looks like we're often go next level faster then we have explored previous level, let's find out why"; (b) "add another mode TZ+: it tries to kill slightly more mobs on levels with not so many mobs to get herald spawn / 1. we don't want to clear very large levels with 300 mobs or so / 2. ... we just kill reasonable groups and if herald doesn't spawn - we're fine, we don't want to kill alone mobs in the corners / 3. TZ+ is default TZ mode from now"; (c) "terrorize with worldstone shards whole act and go whole act, zone by zone / ... any stone with 90+ quantity / we want to kill act boss first for possible statue drop (probably we will create separate mode later, for statue farming)". Agents: (a)+(b) one agent (tz files, fight/clear choice); (c) a read-only research+design agent (rca/2026-10-20/act-terrorize-findings.md, routes/act-terrorize-plan.md), built after TZ+.
- 2026-10-20 ~18:58 ruling (the player): "fore levels with 300+ mobs - we just clear big groups and elites/champions" (TZ+: big levels take big groups and elite packs only; relayed to the TZ+ agent).
- 2026-10-20 ~19:00 ruling (the player): "for TZ/TZ+ modes we want to know how to handle whole terrorized act (when we terrorized it manually with stone)" (relayed to the act-terrorize design agent; TZ+ agent keeps terror detection list-driven).
- 2026-10-20 ~19:15 act-terrorize study done (rca/2026-10-20/act-terrorize-findings.md, routes/act-terrorize-plan.md): a shard is right-clicked in the inventory (Hell, TZ games); each act's manual zone = all its field levels; statues ua1-ua5 from the act bosses (~4-5% a kill, ~7-8% terrorized, computed). Today a hand-used shard stops TZ/TZ+ ("no terror zone is read": tz_groups.match_active_zone needs one rotating zone). First step after TZ+: match_zones (act + rotation). Waiting: the player's answers to the recommendations and one in-game shard test. Exp Shrines agent done (EXP_SHRINES True, 17 tests), waits for the next restart.
- 2026-10-20 ~19:15 white/grey bases done (agent; rca/2026-10-20/white-bases-findings.md): ground read for all 22 weapon + 12 armor types (BASE_ROLLED_TYPES), class staff mods verified in 24,852 captured whites; 18 new rows (G20 class items: grimoires +3 Summon Tainted/Consume/Bind Demon/Sigil: Death and +3 Abyss/Apocalypse 2os, talons, Necro wands +3/+3, FoH/Hammer scepters, pelts, Barb helms Find Item, ES staves; G8 0os +3 Hex: Purge daggers; G16 market bases; G7 45-res Targe); filter +4 Show rules (23 rules) — the player must re-import Warlock Lean2 before the restart. Coordinator: 864 focused passed. Open: 4 questions (findings).
- 2026-10-20 ~19:25 rulings (the player): (1) "I have reimported it last time. do we have more changes?" — yes: 4 Show rules added after ea8f8ac (Staff Mod Wands Scepters, Staff Mod Staves Gray, Pelts Barb Helms Gray, Superior Mask Bone Shield): one more re-import before the base rules go live; (2) "yes, let's do act 4 mode. we are adding a lot of modes, probably we need to pop some kind of dialogue to chose the mode on 3 clicks: shard act 4 as an entry" (agents: a mode picker on the triple KP_6 now; the Act 4 shard mode after TZ+ lands, with the recommended answers); (3) rare boots/belts: "we can keep really good ones" (field identify; rare boots/belts already shown by "SHOW Rare ARMOR"); (4) "ok": the bases agent's 4 questions as recommended.
- 2026-10-20 ~19:35 Death Mark done (agent; rca/2026-10-20/mark-recast-leaders-findings.md): state 212 = the mark (1822/1831 agree with stat 34<0); take rate today 71.5% (82 misses on a neighbour under the pointer, 26 on no one with a moving target); recast after 0.8 s, MARK_RECASTS 2; AIM_CHECK (pointer re-put on a moved target, hover read, moved up/away from a neighbour up to 2 times); MARK_LEADERS True (Herald, immune, leader, priced); FOCUS_LEADERS False (15 tests, an arena kill-speed test). Goldens changed and checked. Coordinator: 613 focused passed. Waits for the restart.
- 2026-10-20 ~19:40 TZ+ done (agent; rca/2026-10-20/tz-level-leave-findings.md): the early leave was the policy (boss-trip levels ON_THE_WAY: agenda.in_level returns before the room tour; Halls/Dry Hills groups ended at 26-56% completion, Heralds ~2%). TZ+: policy PLUS on levels under BIG_LEVEL 300 (explore, leaders, groups of GROUP_MIN 4 linked within 15 within 60 units); big levels groups of BIG_GROUP 8+ and elite packs; TZ_PLUS True, HUD "TZ+". Expected: games 3.5-7 min, +3-8% exp/h, a Herald in ~45-62% of games. Coordinator: 282 focused passed. Open: 3 questions. Next: the Act 4 shard agent (TZ files free).
- 2026-10-20 ~19:40 mode picker done (agent): three KP_6 presses open a HUD card (kindpick.py, PickerCard, slot y 0.22): 1 press next, 2 pick, 3 close, 6 s timeout; "Shard: Act 4" coming entry until an act kind exists; no HUD → the old cycle. Open: 4 questions. Waits for the restart.
- 2026-10-20 ~19:47 rare boots/belts done (agent): field identify classes G21 (boots) and G22 (belts) in loot/api.py CLASSES; kept only by want rows (build_wants.py rare-boots-30frw-fhr-2res-extra, -20frw-fhr-2res30-extra, -20frw-fhr-3res; rare-belt-24fhr-life-res-extra, -24fhr-companion), the rest K8 dropped at the feet (keep.JUNK_UNWANTED + boot, belt); a KB price ≥1 Ist still keeps (K5). No filter change ("SHOW Rare ARMOR" covers them). ~0.08 a game (17 boots, 9 belts over 326 games). Wide suite green (agent, 8644 passed); coordinator 162 focused passed. Open: 3 questions (24 FHR + one companion kept; 3-res no-FRW boots dropped; magic craft-base boots picked by size). Waits for the restart.
- 2026-10-20 19:49:22 restart → 20261020T164916Z-454aec6d (loop on, TZ leveling; the player: "when we could enable TZ+ mode?"). Live: TZ+ (TZ_PLUS), white bases ground read (the 4 new Show rules wait for the player's filter re-import), Experience Shrines, Death Mark recast + leaders, mode picker, rare boots/belts G21/G22, Act 4 step 1 (tz_groups.match_zones: a hand-terrorized act is played boss first, then the rotation; MANUAL_ZONES, BOSS_FIRST), the `terrorize` request (CLICKS False). Wide suite 3603 passed. Watch: `agenda: ... worked tz+`, `shrine:`, `Death Mark ... cast again`, the picker, the :00/:30 rotation (no "no terror zone is read" stop now), the first Act 3/5 crossing.
- 2026-10-20 ~20:05 the player: "we're not picking up rare books/other offhands - they cannot roll something very valuable?" and, on a finds table, "why we're stashing low roll items?". Found: (1) the field identify has not worked since 15:12 (session 115501Z): the Tome of Identify (534, carried at (8,0)) reads `identifies None`, so every field item waits ("charges are unread" / "empty or not carried") and is left, and the shop never refills it ("identifies: None carried, no room for more"); hypothesis: an empty Tome has no quantity stat (agent fixing). (2) Of the table: Spirit Forge 19:30 and Tal Rasha's belt 19:39 were sold (the table is wrong), Corpsemourn kept K4 first copy (rule), Skullder's Ire 0.842 Ist, slow, equal to the 1 owned: the shadow said K6 drop but the town kept it with no line (agent tracing). (3) Rare orbs, shields, heads: "no class takes it" (read-only study agent: rca/2026-10-20/rare-offhands-findings.md). Loop off 20:04:27 by the player, on 20:06:13.
- 2026-10-20 ~20:10 ruling: "ok, let's probably keep only uniques that are mentioned in guides as something that I probably could use" — the loop's cheap (<1 Ist, vendor/slow) set/unique finds not named usable in guides/warlock.html or pricing.html §6 are sold even as the first copy (K4 narrowed, behind a switch; sets included by my reading); given to the town-keep agent with the Skullder fix.
- 2026-10-20 ~20:14 Tome fix done (agent): an empty Tome of Identify has no quantity stat; game/decode.py `quantity(..., empty=0)` for the Tome only; the shop then refills it (`identifies 0 -> 20`) and a short Tome calls a visit. The player had refilled it by hand at Akara 20:04:41; the field identified again at 20:08:47. 40 focused passed (coordinator). Waits for the restart with the town-keep agent. Stoutnail 0.927 equal to the 1 owned sold by K6 at 20:13:09 (the K6 equal case works; Skullder differs).
- 2026-10-20 ~20:17 widened: "we shouldn't limit to just warlock's guide. actually I'd like to try paladin, sorc, barb, necro, traps and amazon builds" — usable list from wp-a-builds.json / wp-a-variants/ for those classes + Warlock + merc (leveling loadouts included); relayed to the town-keep and off-hand agents.
- 2026-10-20 ~20:22 rare off-hands study done (rca/2026-10-20/rare-offhands-findings.md): per 100 games rare orbs 5.2, heads 2.1, Paladin shields 2.1, grimoires 3.1; paying rolls (asks, Oct 3-4): orb +2 Sorc/tree + a +3 staff mod or +2 Sorc + 20 FCR, head +5 paid, Paladin shield +2 Pala / 40+ all res / 2os; none of 30 stored rare orbs or 21 heads reach the gate. Proposed G23 orbs, G24 heads, G25 elite Paladin shields (+ Kurast Shield to the filter), ~2-3 Ist/100 games (asks; no fills cached); plain shields left. Builds to try name magic class items (Magus orb, Venomous head, Cunning/Quickness claws, Lancer javelin, Rose scepter), none has a want row. Waits for the player.
- 2026-10-20 ~20:28 town-keep agent done: Skullder cause = the own-use want row own-88-skullder-s-ire (triage own.json) made surplus_copy keep it while K6 ignored it; fix: a want spares only the first copy (later copies only always_keep), the town logs "kept against the keep rules". Ruling built: keep.FIRST_COPY_USABLE_ONLY / FIRST_COPY_SETS True, TOWN_RULED {K4, K6}; usable list 190 items from wp-a-builds/variants (build_wants.usable_rows, wants.json 312 rows). Would now sell today: The Patriarch 0.4, Steel Pillar 0.904, Demonhorn's Edge 0.925, Corpsemourn 0.562, Messerschmidt's Reaver 0.196. Wide suite 8669 passed. Restart waits for the player's OK on the list (switch off = 8 tests assume on).
- 2026-10-20 ~20:45 the player on claws: "probably we need to try to look up only elite claws with a specific base, not just random +3 skill ... for claws matters: good fast base, 40 ias?, good skill" — read-only claws study agent (rca/2026-10-20/claws-findings.md): bases with speed, skills by build, IAS affixes (white claws have none), magic rows for a field identify, fills.
- 2026-10-20 ~21:02 5-game check: TZ+ session 164916Z 9.7M exp/h over 1.17 h (incl. the player's 2-min pause; zones Stony Tomb/Rocky Waste, Palace Cellar/Arcane) vs 12.8M/h in 154241Z (TZ): zones differ, 19 games < 30; judge at 30+ games by zone.
- 2026-10-20 ~21:02 claws study done (rca/2026-10-20/claws-findings.md): fastest Greater/Runic Talons (-30), Greater/Feral Claws (-20); only h2h2 rolls white skills; white claws have no IAS (max 40 "of Quickness" on magic); fills: white GT +3 Phoenix Strike median 11.42 (12), +3 LS alone 4.05 ×2, +3 LS + Mind Blast 22.8; magic +2 Assassin / 40 IAS / +3 LS 456.84 and 171.31 but Cunning 0.31% × Quickness 1.93% → <0.1 Ist an identified claw. No breakpoint table in the repo. Proposed W1 PS, W2 LS (ranked by a second +3), W3 low CoT, O1 own use (ruling), M0-M3 magic (lottery). Waits for the player.
- 2026-10-20 ~21:05 the player on claws: "1. yes" (keep two white +3 LS / DS / WoF claws for own use), "2. is it actually that good?" (magic claws). Claw rows agent started: W1 PS, W2 LS, own-use cap 2.
- 2026-10-20 21:03:42 possible MISSED (hard rule 1): a Herald's Western Worldstone Shard at (10145, 11897), area 119, read "taken (material)" twice, no pickup line; the loop picked eth magic Demonhide Gloves and a potion beside it, then explored on (21:03:44) and left the game at 21:04:22; no later ground read of the shard; watch printed no MISSED. Asked the player to check the inventory/cube. Trace pending.
- 2026-10-20 ~21:20 claws rows done (agent): W1 PS, W2 LS (second +3 WB/MB/DS ranks higher), W3 CoT, O1 own trap claws keep_up_to 2 (per base+sockets); coordinator: loot/api.py town_kept ignores capped wants (keep_up_to) on a give-up, strict xfail removed; wide suite 8707 passed, pyrefly 0. Act 4 hand-shard readiness confirmed to the player (Act4-Manual 104-108; Diablo seals ran 08:36 today); the automatic shard step waits for the in-game test. Loop paused by the player since 21:04.
- 2026-10-20 21:17-21:27 Act 4 hand-shard test: the player: "ctrl left click moves exactly one shard into inventory", "any variant, you can right click on it", "it shows Act 4"; client list 104-108 at 21:17:26; plan 21:18:21 `Act4-Manual + Act5-AncientsWay: Diablo from 106: [106, 107, 108]; Izual from 103; Icy Cellar from 118`; the game took the City of the Damned waypoint first (21:22:16): against the ruling (River of Flame wp -> CS -> Diablo -> rest of the River -> City/Steppes/Plains). Coordinator: terrorize.CLICKS True, actloop.ENABLED True, restart.py/elites.py --kind act4, 3 tests pinned; wide suite 8707 passed. Order fix to an agent; restart held for it.
- 2026-10-20 ~21:30 ruling: "launch mode with shards usage as soon as it ready / make sure, that we're farming until it's done / we need to farm all the time" — restart --kind act4 once the order fix lands; relayed to the order agent (game not cut before the act is done; never a stop on no shard).
- 2026-10-20 ~21:37 order fix done (agent): tzroutine `_route_trips` took the widest excursion (Diablo from 106); now routes/tz_routes.py `nearest_excursion` (BOSS_NEAREST), crossed levels ON_THE_WAY then worked after the kill (Excursion.passes, Itinerary.crossed, tzloop `reopen`, Agenda.reopened); Act4-Manual plan: Diablo from 107 [107,108] (107 crossed), 107 rest, 106, Izual 103 [103,104,105]; rotations unchanged; Acts 1/3/5 likewise. Coordinator: REPEATS[TZ_LEVEL] 40 -> 60. Wide suite 8712 passed. Restart asked --kind act4 --loop keep at the next lobby (also: Tome fix, Skullder fix, FIRST_COPY_USABLE_ONLY list, claws W1-W3/O1, CLICKS/ENABLED).
- 2026-10-20 21:38:12 defect: the Izual trip entered the Plains of Despair and left at once ("no target here: the route's own goal", "the level run ends: what is left of the route is loot"; Plains +0 in 5s; no Izual kill). Sent to the order agent (held from production edits until the restart is done).
- 2026-10-20 21:42:21 restart -> 20261020T184216Z-86b2d9c3, loop on, run Shard: Act 4 (restart.py --kind act4). Live: act4 kind (CLICKS, ENABLED), boss-first order (nearest excursion, crossed levels), REPEATS TZ_LEVEL 60, Tome empty=0 refill, Skullder fix + town keep line, FIRST_COPY_USABLE_ONLY (190 usable), claws W1-W3/O1 + capped wants in town. Not yet: the Plains/Izual skip (agent, released 21:43). Game 21 (hand shard) +3.65M in 1203 s, cut by the TZ cap.
- 2026-10-20 ~21:46 the Plains "skip" was a misreading (verified): the Steppes run carried into the Plains at 21:35:26 ("on into Plains of Despair"), worked tz+, Boss kill: Izual 21:37:20, a Herald ~21:38; the experience line books a carried level to the level the run began in (Plains +0 = the loot leg). Open: split the experience line per area (minor).
- 2026-10-20 21:42:42 / 21:42:54 defect: the act4 shard step "no inventory key read" (actloop.use_shard passed None) left games 1 and 2 at once (the player: "something is wrong, we have restarted game twice ... with no obvious reasons"); after 2 the kind gave up (TZ+ on the rotation, as designed). Fix (coordinator): LegHands.inventory_key (loop.py) set in running/legs.py `_loop_hands`, tzloop passes tz.inventory_key() to actloop.use_shard; the agent made terrorize.py refuse a missing key only with the stash closed. Test test_the_shard_step_gets_the_characters_inventory_key. Wide suite 8717 passed, pyrefly 0. Restart asked --kind act4 at the next lobby. The player: "we probably need to do town routine in the beginning, if required" — built: actloop.shard_goal waits while loop.visit_due (room low / trip / short stock / repair), the visit first.
- 2026-10-20 22:00:18 restart -> 20261020T190014Z-64d16800 (act4, key fix). 22:00:43 the loop used a Deep Worldstone Shard itself (stack 99 -> 98, "the act read terrorized"); plan 22:00:45 `Act4-Manual + Act2-Sewers: Diablo from 107: [107, 108], [107] crossed to the boss, worked after it; Diablo from 107: [107]; Diablo from 106: [106]; Izual from 103: [103, 104, 105]; Radament from 48`; next waypoint: to River of Flame (Diablo). The act4 mode works end to end.
- 2026-10-20 22:00-22:18 first automatic act4 game: shard 22:00:43, River wp -> CS seals -> Diablo 22:04:57, River rest (22:05-22:09), City (22:09-22:11), Steppes walk out 22:11:47, Izual 22:17:20, then the rotation (Radament 22:18). The boss-first order held. No danger lines.
- 2026-10-20 22:20-22:39 act4 game 2: shard 98->97, Diablo 22:25:24, Izual 22:34:53, rotation Nihlathak 22:38:21; 1113 s, +3.56M (~11.5M/h). Game 1 1211 s +3.55M (~10.6M/h). Finds kept: Skin of the Vipermagi (better than 3 owned), Bartuc's Cut-Throat (better), The Stone of Jordan (2.29 Ist).
- 2026-10-20 ~22:50 ruling: shard runs for acts 1, 2, 3, 5 with their own orders (memory d2r-kp6-loop-rulings, verbatim), a reusable act-run framework with per-act scripts, sub-agents per act. Plan: a framework agent first (acts/ package, act kinds, the act4 port), then one agent per act on its own script file. The act4 farm keeps running.
- 2026-10-20 ~23:05 ruling: keep dangerous monsters under Sigil: Lethargy all the time; evidence: Diablo fight 23:01:41-23:02:06, one sigil 23:01:56, none after (SIGIL_SECONDS 10). Agent on builds/warlock/buffs.py (position/state-based recast).
- 2026-10-20 ~23:10 ruling: Diablo lightning dodge = walk around him, not Teleport (he follows a Teleport at once). Agent on combat/threats/diablo.py, macros/safety.py, pursuit.py.
- 2026-10-20 ~23:15 act framework done (macros/acts/: engine.py, act4.py scripted with the live plan line; ACT_SCRIPTS switch; act1-5 kinds; harness). Act 1/2/3/5 agents spawned (each owns acts/act<N>.py + its test + catalog/act<N>.py routes). Not live until a restart.
- 2026-10-20 ~23:15 the player: "act 4: we couldn't find way to plains of despair in current game, I moved char through the gate manually". Cause: the open-passage walk (pursuit `through`) clicked the passage 37 units south, off the screen: "the place near Plains of Despair is not in view" x52 23:10:47-57, the player walked it. Fix: travel.py WALK_PARTWAY + in_view_toward (a walk off the screen goes to the farthest point of its line in view); tests in test_travel.py. Not live until restart.
- 2026-10-20 ~23:20 the player (confirmed approach): batch field identify on need is liked: "we're not wasting time identifying individually every separate item but doing bath when we actually need it / I like how it feels in time and fast". Keep it.
- 2026-10-20 ~23:35 acts: act 1 ready (tzloop `reenter` fix from the act 1 agent: a second trip down a way on taken in the game had no way on; also hit Act 4 with the Burial Grounds in rotation), act 2 ready (Duriel missing: his lair opens only by the Orifice in the true tomb; Harem/Sewers 1 new alternate routes), act 5 ready (Baal step on: Throne waves never seen live; Halls of Anguish/Nihlathak Temple/WSK1/Bloody Foothills new alternate routes). loop.py ACT_SECONDS {1: 3900, 5: 3600}. Tests: kindpick coming-kinds generalised, tzroutine generic-plan tests pin ACT_SCRIPTS off. Act 3 agent still running. Not live until restart.
- 2026-10-20 ~23:40 act 3 ready: loop.py REPEATS TZ_PORTAL 20+TRIPS, TZ_WAYPOINT 20+2*TRIPS+4 (act 3 has 15 trips; was 13 portals), ACT_SECONDS[3] 3600. The player on Baal: "we go throne room / kill 5 waves of mobs (last with lester) / wait until he moves through his portal + some extra to portal to be activatable / go through his portal in his room / kill him" = throne.py as built; PORTAL_OPENS 1.0 -> 2.5 s ("+ some extra"). All 5 act scripts ready; not live until restart.
- 2026-10-20 ~23:45 Diablo agent: WALK_AROUND in combat/threats/diablo.py + safety.py bars Teleport (non-retreat) while his stream is at the character. Evidence: logged dodges were already walks; the Teleports were fight "better place" hops mid-stream (0-19 life lost, merc took it); walk steps that end in a stand lost median 205 (23:01: 450 points on one stream); his "follow" was likely his charge (mode 14). Next: chained walks round him (asked of the agent). 8 wide-suite failures are the sigil agent's area.
- 2026-10-20 ~23:45 rulings on lazy-work findings: rings/amulets to Cain unidentified; gold unchanged (skip only at the cap); Jamella only when needed (tome <~10 or keys <3), else junk put down in town. Field-merge agent (§5) running; #1 relayed to it; Jamella agent spawned.
- 2026-10-20 ~23:46 Jamella ruling widened: also when carried gold is low (relayed to the Jamella agent).
- 2026-10-20 ~23:50 sigil agent done: SIGIL_KEEPS (buffs.py: dangerous = Herald/boss/super unique/leaders; recast on out of radius 6 (lvl 15 medium), no state 192, <1 s left, Herald 6 s; SIGIL_GAP 1 s; look every 0.5 s) + SIGIL_AIM_AFRESH (casters.py: aim where the monster stands at the key — the 23:01:55 sigil was 10.7 units off by a 0.3-0.5 s old look). Duration 19 s, state 192 seen 0.48 s after the key. Key re-press only after Death Mark, costs ~0.05 s, left. Wide 8770 passed. Holding the Diablo/field/Jamella agents for a restart.
- 2026-10-20 23:57:23 restart -> 20261020T205718Z-9185e37d (loop on, Shard: Act 4). Live: travel WALK_PARTWAY (Plains passage), sigil SIGIL_KEEPS + SIGIL_AIM_AFRESH, Diablo WALK_AROUND (WALK_ROUND off), throne PORTAL_OPENS 2.5, tzloop reenter, act scripts 1-5 ready (picker offers act1-act5), ACT_SECONDS {1:3900,3:3600,5:3600}, REPEATS TZ_PORTAL/TZ_WAYPOINT raised. Wide 8770 passed. Agents released: Diablo chain walk, field one-opening + rings to Cain, Jamella at need.
- 2026-10-21 ~00:05 ruling: Diablo: circle round him, close (WALK_ROUND on, tight radius); relayed to the Diablo agent. First live Diablo fight on WALK_AROUND: ~5 s, life 2873/2907 after, Mithral Point dropped.
- 2026-10-21 ~00:10 field agent done: loot/api.py ONE_OPENING (one inventory open/close per field visit; drop at PARK_POINT with the cube open) + RINGS_TO_CAIN (magic rings/amulets carried unidentified to Cain; Tome only as last resort for room). Both True, live at the next restart.
- 2026-10-21 ~00:15 Jamella agent done: visit.py JAMELLA_AT_NEED (her when keys <3, tome <10, portals short, gold <200k = repair.py WEAR_CARRIED, or junk of a never-put-down kind; else junk put down in town in one opening, "jamella -"). Wide 8801 passed. Live at the next restart.
- 2026-10-21 ~00:20 Diablo agent done: WALK_ROUND True, AROUND_RADIUS 14 (harm.py melee stand-in prices 10 at 370 mean vs budget 578; 14 the nearest that fits), circling only while his stream is at the character; sim from 9 units: life lost 137->71 / 398->269, lightning 45->6, kill +2-3.5 s; from 18 units worse (fire wall). Arena 8 seeds: spell damage 141/137 -> 76, no deaths. Holding the Engorge agent for a restart.
- 2026-10-21 00:19:16 restart -> 20261020T211911Z-0a4e743b (loop off by the player at 00:18:52, kept off; Shard: Act 4). Live now: WALK_ROUND (circle Diablo at 14 while his stream is at the character), ONE_OPENING, RINGS_TO_CAIN, JAMELLA_AT_NEED. Engorge switches (ENGORGE_LIFE_SHARE, ENGORGE_HOVER_FIRST, ENGORGE_SPARE_ENDS) built, off: next, one at a time (cows_stand golden to re-record). Wide 8815 passed.
- 2026-10-21 00:46 DEFECT: game 2 of 20261020T211911Z-0a4e743b: no Diablo. Vizier 1, 2 opened; De Seis "did not take the click" then "At De Seis seal" -> "use De Seis seal is done"; Infector seals never mentioned (opened in game 1 at 00:27); "no route stage, no boss known" at 00:45:59. Suspect: progress carried across games and/or a use stage done on arrival. RCA agent spawned.
- 2026-10-21 ~00:50 the player: "diablo fight was ruined by us not killing second group of mobs after third seal / I did this manually, but we need to make sure that we have fixed this". Added to the seal RCA agent (resumed after an API limit). Set Bone Visage on the ground at (7795, 5302) at the player's stop 00:48:54.
- 2026-10-21 ~00:55 pickup RCA agent: misclicks onto potions, inventory potions dropped not stashed (ruling), slow pickups.
- 2026-10-21 00:55:22 LOST VALUABLE: unique Double Bow (5628, 4499) left: back from a room trip, walk_until toward the portal took it, through_portal then clicked the town portal from the City ("the level is not under the pointer at any aim"), recovery RECOVER because valuable_left read None: sightings.update deleted the bow (character within GONE_UNITS, the arrival read held no ground units). The player: "we returned to item on the ground, and instead of picking it - we exit the game / that is VERY BAD". Fix: sightings.py ARRIVAL_SECONDS 3 (a sighting from before the arrival is not judged gone in the first 3 s), portal.py THROUGH_ON_THE_WAY (a walk or click that went through is the arrival). Tests test_sightings, test_portal.
- 2026-10-21 ~01:01 wide 8819 passed with the seal agent's SEAL_BOSS_BY_SEAL (goals.py) and SETTLE_FOUND_USED (moves.py) set False (no regression tests yet). Restart queued for the next lobby: sightings ARRIVAL_SECONDS + portal THROUGH_ON_THE_WAY go live. Game 3: all 5 seals opened in order, De Seis pack killed, Diablo circled (01:00:11).
