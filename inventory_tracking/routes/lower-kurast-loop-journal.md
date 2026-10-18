# The KP_6 loop's improvement journal

The state of the continuous improvement loop (`.agents/skills/d2-loop-watch/SKILL.md`): what the loop does now, how
fast it goes, what is queued, what waits for the player. Read it first when a watch is started or resumed. Update it at
the end of every round. The design and its phases are in [the plan](lower-kurast-loop-plan.md); studies are in
`rca/<date>/`.

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
  clear) keeps the route's goal (hunt.py `cleared`; test_runmode). Measured 10:55-10:58, 5 games: down the Catacombs
  median 14.3 s (27-33 s before, 51-57 s in games 6-8), games 46.5 s median, 88/h (58.9/h before); no "clearing the
  way (" goal. Wide suite 1926 passed.
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
- Super chests (hunt.py `super_chest_goal`, SUPER_NEAR 60): opened live at 00:24:26 (Infernal Pit), 00:49, 00:52.
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
  (hunt.py `stay_by`: waits for the player).

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
