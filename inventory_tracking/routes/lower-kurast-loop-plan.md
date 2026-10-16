# The Lower Kurast loop: KP_6 runs games until toggled off (plan, 2026-10-15)

**Goal** (the player, 2026-10-15): one key, KP_6, toggles a closed loop:
create game → Pandemonium Fortress → prebuff → waypoint to Lower Kurast → each super chest: go, open, pick up →
no chest left → Town Portal (`x`, the key detected, not assumed) → Kurast Docks → waypoint to Pandemonium Fortress →
Save and Exit → again.

The chest part is `lower-kurast-plan.md` (tasks 1–5); this plan is the legs around it and the loop itself.

## What exists (code at `cb555a8`)

| Leg | Exists | Where |
| --- | --- | --- |
| Lobby → next game, prebuff | yes (the macro request, Mod+X), mouse mode only | `routines.py` `create_next_game`, `prebuff`, `run_macro` |
| Save and Exit | yes, mouse mode only | `routines.py` `leave_game` |
| A level run in Lower Kurast | the run mode exists; the chest marks do not (pending) | `pursuit.py`, `lower-kurast-plan.md` |
| Walk in town | no: the hunter and the pursuit refuse in town (`hunt.py:2005`, `2048`); towns have no level handler | — |
| Waypoint panel | its open flag only (`layout.py PANEL_FLAGS['waypoint']` 0x13); no tab or row clicks | — |
| Town Portal | no | — |
| KP_6 | not bound (`compositor.py BINDS`: KP_1–5) | — |

Facts read for this plan (d2data, 2026-10-15): skill 220 Book of Townportal (219 the scroll); object 59
`TownPortal`; waypoints 237 `WaypointAct3` (Kurast Docks, Lower Kurast), 398 `WaypointAct4Town`.

## Phases

### 0. Evidence first (no code that clicks)

- **The portal key.** `skills.skill_keys` with skill 220: the slot table holds the tome when it is on a skill key.
  Log `Macro: loop: Town Portal is on <key>` at the loop's start; refuse to start when it is on none (say which
  key action to bind). Confirm `x` on the player's key file before any cast.
- **Waypoint spots.** Pandemonium Fortress and Kurast Docks are fixed presets: the waypoint objects' spots from the
  DS1 files (`levels/build_objects.py`, add 237 and 398 to the wanted set) and a town handler for each (`levels/
  handlers/towns.py`: the waypoint mark only).
- **The waypoint panel.** Which pixels are the act tabs and the rows, at the player's resolution: from one
  screenshot of the open panel per act (the player takes them; nothing is clicked). The open act and the
  highlighted row are read from memory if `world.py`'s waypoint bytes near 0xC8 hold them (not yet checked live);
  otherwise the click is confirmed by the area changing.
- **Where a new game starts.** Logs since 2026-10-06: the first area of each game against the last area of the
  game before (`probe.log` `Level guide:` lines). This says whether the trip back to act 4 is needed (Open, Q1).

#### Phase 0 findings (2026-10-16)

- **The portal key: `x`.** CybergrindAA's slot table in the takes of 2026-10-15 (`runs/combat/20261015T181240Z-103`
  manifest `slots`) holds skill 220 (Book of Townportal) in slot 5 = key action 19, and the key file
  (`CybergrindAA194867311.keyo`) binds action 19 to `x`. `skill_keys(slots, bindings, (220,))` gives it; nothing
  to hardcode. (Slot 13 holds 221, Book of Identify, on `7`.) The controller bindings name it too: `LT+X Town
  Portal` (probe.log 2026-10-15 21:07:50).
- **Where a new game starts: the town of the act the last one was left in.** The takes since 2026-10-09, 44 games
  of one character, each game's last area against the next game's first: left in act 4 → started in Pandemonium
  Fortress (34 of 34); left in act 5 (Frigid Highlands 119) → Harrogath (2 of 2, cber4→5, cber5→6 on 2026-10-14);
  left in act 2 (area 49) → Lut Gholein (cyber0→cyber1, 2026-10-15). Not "the highest act reached". So a game left
  in act 3 starts the next in Kurast Docks, one waypoint from Lower Kurast (Open, Q1).
- **Waypoint marks in town: they exist.** `levels/exits.py` `preset_waypoints` marks each town's waypoint from its
  DS1 file (`guide_level` gives a town its way out and the waypoint): Kurast Docks preset 529 'Act 3 - Town' at
  tile (31.8, 9.8) from its origin, Pandemonium Fortress 797 'Act 4 - Fortress' at (8.8, 3.8); one file each.
  No `build_objects` change and no town handler are needed for the mark.
- **The waypoint panel, from the game's own UI layout** (`data/global/ui/layouts/waypointspaneloriginalhd.json`,
  `…expansionhd.json`, `_profilehd.json`, read with `terror_zones/game_files.py`): the panel is `$LeftPanelRect`
  (x 236, y −651, 1162×1507) at `$LeftPanelAnchor` (0.0, 0.397 of the screen); in it the act tabs from (148, 201),
  five of 174×70 with −1 padding; the rows from (152, 264), `buttonOffset` 123 apart. Assuming the HD layout's
  2160-unit reference height scaled to the window's (to confirm), in a 16:9 window the act III tab's centre is at
  (0.213, 0.205) of the window, act IV's (0.258, 0.205), the first row's top at y 0.218 and each next row 0.057
  lower. The panel opens on the character's own act (to confirm). Act III's rows: Kurast Docks, Spider Forest,
  Great Marsh, Flayer Jungle, **Lower Kurast (5th)**, Kurast Bazaar, Upper Kurast, Travincal, Durance of Hate 2.
  To confirm with one screenshot of the open panel in Kurast Docks (nothing clicked); a click is confirmed by the
  area changing, as the plan has it.
- **What the findings change: nothing** (the player, 2026-10-16, Open Q1): "exiting in act 3 is bad, because it
  requires quite long walk to the waypoint; we're tp's to act 3 town => waypoint => act 4 town => save exit to save
  time". A game started in Kurast Docks begins far from its waypoint; the portal from Lower Kurast lands near it,
  and Pandemonium Fortress starts the next game by its own. The loop stays as planned; the waypoint panel needs both
  tabs: act IV's (first row, Pandemonium Fortress) from Kurast Docks, act III's (fifth row, Lower Kurast) from
  Pandemonium Fortress.

### 1. Town walking

**Rescoped and written 2026-10-16 (uncommitted, not played): no walk of the macro's own.** The player's takes of
2026-10-15 put the waypoint a click away in both towns: every game started in Pandemonium Fortress at (5048, 5044),
25 units from its waypoint (13 of 13), and every portal from Lower Kurast left them in Kurast Docks at
(5158, 5068), 20 units from its (9 of 9); they clicked it and the game walked them there (4.5–6 s from arrival to
the next level, the panel included). So phase 1 is `macros/waypoint.py` `open_panel(run)`: the waypoint object the
game shows (`levels/memory.py WAYPOINT_CLASSES`, now in `world.USED`: recorded too), clicked on its picture with
`use_thing` (each aim only with the waypoint under the pointer), done when the `waypoint` panel is open
(`Use.opens`). objects.txt gives waypoints no click box; the aims round the ground point are a guess for the played
check to confirm (`Macro: the waypoint took the click … pixels from its ground`). The navigator walk below stays
unbuilt until a town needs it. Tests: `test_waypoint.py`.

- `macros/town.py`: `walk_to(run, mark)`: the navigator over the town's ground (`travel.py`, walking only: no
  Teleport or Blade Warp in town), clicks within the view toward the mark, done within USE_NEAR. The game's own
  walk-to-click is the step; no pathing beyond the navigator's.
- Tests: a fixture of each town's rooms (one Win+C dump of each, the player standing at the start); the walk from
  the start to the waypoint in the arena's terms (offline ground).

### 2. Waypoint travel

**Written 2026-10-16 (uncommitted, not played):** `macros/waypoint.py` `travel(run, to_area)`: the panel (phase 1),
the level's act tab, its row, done in the level; mouse mode only; not reached → `Abort` with the panel closed
(Escape). Tab and row from the installed game's levels.txt (`build_waypoints.py` → `macros/data/waypoints.json`,
39 waypoints: Lower Kurast act III row 4, Pandemonium Fortress act IV row 0). The pixels from the game's own layout
files (`waypointspanelexpansionhd.json`, `_profilehd.json`), a layout unit 1/2160 of the window's height: the same
rule puts the pause menu's Save and Exit at 0.440 and Return to Game at 0.505 of the height, where the macros click
them from screenshots (0.438, 0.509). Unread from the layout: the row button's height (the click goes 45 units into
the row, the rows 123 apart) and whether a window wider than 16:9 shifts the left panel (CybergrindAA's is
2560 x 1418, 1.81). The played check confirms both: the level reached is the evidence. Tests: `test_waypoint.py`,
`test_pad.py` (refused in controller mode).

- `macros/waypoint.py`: `travel(run, to_area)`: walk to the town's waypoint (phase 1), click it (`use_thing`
  with a `Use` for 237/398 whose `took` is the panel open), click the act tab, click the level's row, wait for
  the area. Mouse mode only, refused in controller mode as Save and Exit is.
- A waypoint the character has not got (greyed row) or a panel that does not open: `Abort` with its reason.
- Tests: the panel's clicks against a fake world whose area changes on the right row.

### 3. Town Portal

**Written 2026-10-16 (uncommitted, not played):** `macros/portal.py` `to_town(run, key_names)`. Evidence from the
player's takes of 2026-10-15: each of their casts in Lower Kurast is Quick Cast (the right button shows 220 for
0.3–0.4 s), and they clicked the portal 0.9–1.4 s after it. objects.txt TownPortal (59): `Selectable2` only, the
permanent portal's click box. The portal is the one not there before the cast, open (mode 2), nearest the
character, waited for up to 2.5 s; then `use_thing` with `USES[TOWN_PORTAL]`, done when the level changes.
59 joins `world.USED`, so the recorder writes portals from now on (the takes had none to measure the spot by).
The tome's charges are not read: no portal is `Abort`ed as "is the tome empty?". Tests: `test_portal.py`.

- `macros/portal.py`: `to_town(run)`: the tome's key (phase 0), the cast, the portal object (59) that appears
  beside the character (its owner: the character, if the unit says so), clicked with the object aims, done when
  the area is a town. No tome charges left (`Abort`, "no Town Portal charges").
- Tests: the key from a key file with 220 on a slot; the portal click on a fake world.

### 4. The loop

**Written 2026-10-16 (uncommitted, not played):** `macros/loop.py` (`next_leg`, `Loop.leg`) and the runner's `loop`
routine, toggled by KP_6 (`KP_Right` in `compositor.py BINDS`, `loop ` in `request.py`, the service's
`MACRO_ROUTINES`). One leg a run; the runner's `_follow` starts the next whenever nothing else follows, the end of
the KP_1 level run among them (the chests' leg posts that run and turns attack mode on, as KP_1 does). Legs: the
lobby → the next game and its prebuff; Pandemonium Fortress, the game not done → prebuff if not yet, waypoint to
Lower Kurast; Lower Kurast at the `use` stage → the level run; at `loot` → one pickup a leg, nothing left marks it
looted; after → a pickup if any, else Town Portal (the game marked done); Kurast Docks → waypoint to Pandemonium
Fortress; Pandemonium Fortress, the game done → Save and Exit. Stops, said as `Macro: loop stopped: <why>`: a leg's
`Abort` (controller mode among them: every leg's routine refuses it), the character dead, a place with no leg, a leg
made more than its limit in one game (the level run 3 times, pickups 20, others twice). Not yet: low life and
potions as stops of their own (the level run's safety has them), a valuable that does not fit, a cap on games
(Open Q3), the HUD line beyond the `Macro:` line `run.say` gives. Tests: `test_loop.py`, `test_runner.py`.

- `macros/loop.py`: a state machine read from where the character is, so it resumes from any point:

  | Where | Does |
  | --- | --- |
  | lobby | `create_next_game` |
  | Pandemonium Fortress, game fresh | `prebuff`, then `waypoint.travel(LOWER_KURAST)` |
  | Lower Kurast, chests left | the level run (`lower-kurast-plan.md`), pickups as the pickup rules have them |
  | Lower Kurast, chests done and the ground clean | `portal.to_town` |
  | Kurast Docks | `waypoint.travel(PANDEMONIUM_FORTRESS)` |
  | Pandemonium Fortress, the run done | `leave_game` |

- **KP_6** (`KP_Right`, `compositor.py BINDS` → kind `loop`): on starts the loop, off ends it at once (the run is
  cancelled; the character stays where it is). The HUD shows "Loop: game N, <state>".
- **It stops by itself, saying why** (the character left where it is; `Macro: loop stopped: <why>`):
  a stage that `Abort`s; the character dead; life below the safety's leave line (the existing harm model,
  `combat/harm.py`); a valuable that does not fit (the "stop near it" ruling); potions below the reserve; the game
  not created; controller mode.
- **The player's hand** pauses it as it pauses a level run, and it goes on by itself after SETTLE seconds
  (the ruling of 2026-10-13).
- Tests: the state machine over a scripted world (every row above, each stop reason); KP_6 on/off.

### 5. Played checks

One game by hand-held stages first (each leg with its own key, the loop off), then the loop for a few games.
RCA after each session as usual: time per game by leg, chests opened, drops left, every stop and its reason.

**The checklist (2026-10-16).** Only the chests have a key of their own (KP_1); the portal and the waypoints are
legs of the loop. Since the loop reads its leg from where the character is, a leg is played by hand by pressing
KP_6 where it starts and KP_6 again once it is over (the loop off at once, the character left where it is).
`make serve` only; mouse mode.

| # | Where, what | KP | What shows it worked (probe.log, `Macro:` lines) | What it settles |
| --- | --- | --- | --- | --- |
| 1 | Lower Kurast with the chests opened (KP_1) and the ground clean | KP_6, then KP_6 in Kurast Docks | `Loop: game 1, Town Portal`; `Town Portal on x`; `object … (class 59) … the character at …`; `town took the click …`; `town: there` | the portal's key, its spot beside the character, its open delay (phase 3) |
| 2 | Kurast Docks, just through the portal | KP_6, then KP_6 in Pandemonium Fortress | `Loop: game 1, to Pandemonium Fortress`; `the waypoint took the click (x, y) pixels from its ground`; `waypoint: tab 4 at …, row 1 at … of a WxH window`; `The Pandemonium Fortress: there` | the waypoint's aims (phase 1), the panel's tab and row (phase 2) |
| 3 | Pandemonium Fortress, that game | KP_6, then KP_6 in the lobby | `Loop: game 1, Save and Exit` | the act 4 ending |
| 4 | the lobby | KP_6, then KP_6 in Lower Kurast | `Loop: game 1, next game`; `Creating cyberN`; the prebuff; `Loop: …, to Lower Kurast`; `waypoint: tab 3 …, row 5 …`; `Lower Kurast: there` | the act III tab and the fifth row |
| 5 | Lower Kurast | KP_6 and watch | `Loop: …, the chests` then the KP_1 run's own lines; `route Lower Kurast: no Super chests on this level` in a level without a camp | the chests' hand-over and its return to the loop |
| 6 | then a few games with the loop on | KP_6 once | a `Loop: game N, …` line per leg; `loop stopped: <why>` if it stops | the whole loop; time per game |

What to keep an eye on, and stop with KP_6: a click at a wrong row (the level reached says it: the loop stops
when it is not the one asked for), the character standing still in town (a waypoint not under the pointer: `the
waypoint is not under the pointer at any aim`), a leg the log repeats.

### 6. After the first played games (rca/2026-10-16/loop-chests-findings.md)

The games of 19:55–20:04 on 2026-10-16 and the player's rulings after them.

- **6a, done (uncommitted).** The loop goes on once its chest run ends:
  - `Hunter.run_over` → `MacroRunner._run_over`: attack mode stops, the loop's next leg follows.
  - Before, the mode went on sweeping until KP_6 was pressed: 44, 24 and 9 s.
- **6b, done (uncommitted).** The loop's chest run doesn't fight what costs it nothing:
  - `Pursuit.rush` and `Facts.rush` drop the strike gap (I2), and `Hunter.rushing` drops the fight's "better place".
  - A strike is made only where the arbiter prices it under the move.
  - The player: "don't fight what isn't attacking", for KP_6 only.
- **6c, done (uncommitted, not played).** The shacks' other containers, "only if we encounter them in shacks and
  direct visibility + close, do not hunt them". The code: `macros/shacks.py` and `Hunter.shack_goal`, as a side goal
  of the loop's run. Played, the log says `Opening Weapon rack, N away` (or Armor stand, Basket, Jungle chest) and
  `Weapon rack, in the shack` in the pursuit's lines:
  - What: the weapon rack (107, fixed at (48, 12) of the camp), the armor stand (104, at (12, 23)), rolled jungle
    chests (181, 183), and the baskets (208, 209).
  - The rule: the character and the container in the same camp (the bonfire layout's `Room.block`), the container
    closed (`usable`), in sight (`clear_shot`), within 25 units (clicked from where the character stands), not one of
    the camp's three chest spots (the route's own). Two tries at most per container.
- **6d, done (uncommitted, not played).** Faster opens, on the loop's run:
  - An object is clicked from within 12 units (`hunt.py` OPEN_NEAR), not from 18–23 units away.
  - The hop toward it aims 3 units short of it, on the character's side (`beside`), not at its tile.
  - Several marks of one label are led the shortest way through them all (`levels/guide.py` `tour_first`, up to 7
    marks; for every route, not the loop's alone). Game 1 would have gone 266 units, not 353.
  - A shack's container is a side goal of the level's route, so the run still opens one after the last chest.
    Without that, `run_level` ended a run whose goal had no route.
  - In play, `Opening Super chests, N away` should say N ≤ 12.
- **6e, done (uncommitted, not played).** The arrival wait. The view byte showed no load in any of 8 trips, so the
  wait was always the fixed 5 s. Now a weapon swap probes the game (`routines.took_input`):
  - Swap Weapons is pressed until the set in hand changes, then swapped back to the set held before (a game left with
    the staff in hand loses Teleport's key).
  - The 5 s stays only as the most it waits.
  - Every in-game leg of the loop now has the character's keys, Swap Weapons among them.
  - In play the log says `<level>: took input N s after the arrival (a weapon swap)`.
  - `no load shown; 5s …` means the probe could not run, or no swap took.

### 6f. The shack stalls and the staff's charges: done (uncommitted, not played)

rca/2026-10-16/loop-shack-stalls-findings.md:
- No firing spots on the loop's run, and a spot a move failed to reach is barred for 4 s (every run).
- The loop's goals spare the staff (travel.py `LOOPED`): Blade Warp first wherever it reaches, Teleport only where it
  does not, the last 10 charges kept.

### 7. Pickup mode (a double press of KP_6): done (uncommitted, not played)

The code:
- `macros/pickmode.py`: `sure`, `kept`, `next_mode`.
- `MacroRunner._loop_tap` and `_judge_loop_taps` judge the KP_6 presses; `_picked` filters the run's loot while the
  loop is on.
- Drops now carry `source`, `txt` and `quality`; `ground_materials` reads the quality.
- The HUD's mode word is `LOOP SURE` or `LOOP ALL` (`run_badge`).
- The log says `Loop pickup: regular` or `Loop pickup: sure valuables` when the mode switches.
- Later that day, the player: "make sure that we still pickup all jewels, + pickup worldstone shards/other valuable
  drops". The sure mode also takes every jewel (`jewl`, `cjwl`) and whatever the loot marks point at (`Drop.prized`:
  the shards, essences, statues, flawless and perfect gems, every unique and set item the loot filter shows).
- The types come from the bundled item metadata (misc.txt's type column): gems `gema` `gemd` `geme` `gemr` `gems`
  `gemt` `gemz`; charms `scha` `mcha` `lcha` `csch`; runes `rune`; rings `ring`, rare at quality 6 (`loot/shown.py`
  RARITIES).
- KP_1, KP_4 and the rest, with the loop off, pick up as before.

The design, as planned:

- **Sure valuables (the default):** rare rings, the uniques `loot/data/uniques.json` prices at `unique_minimum` and
  up, every rune, every gem, every charm.
- **Regular:** today's pickup (`pickup.choose`, the config's rules).
- **Supply in both modes:** potions the belt is short of, and gold (the player, 2026-10-16: "we need it to repair our
  staff of teleportation").
- **The switch:** made like KP_1's run mode (`runmode.Taps`): exactly two presses within DOUBLE seconds switch the
  pickup mode and leave the loop as it was. A single press toggles the loop once the window is over, so it now acts
  0.35 s after the press. The HUD shows the mode.
- **Where it applies:** a filter over the drops `GameMemory.loot` marks (their `source`: rune, material, unique,
  named, shown, also), so no rule is written twice.

### 8. Town Portal scrolls and keys (3 or more of each before a run): done (uncommitted, not played)

**The code.** `macros/shop.py` (`short`, `restock`, `walk_until`); `Pack.keys` and `Pack.portals` (quantity stat 70 at
the resource reader's verified offsets); `GameMemory.stock`, `world.stock_of`, `Run.stock`; the loop's SHOP leg
(`scrolls and keys`) in Pandemonium Fortress before the waypoint, while `Loop.short`.

**The steps.**
1. Walk toward Jamella until she is drawn well inside the window.
2. Click her: up to three aims on her body, each checked by the game's hover record.
3. Wait for her menu, then click its Trade line, 0.218 of the window above her.
4. Require `npc_shop` and a key and a scroll in her stock. Gamble is never tried, and nothing is bought otherwise.
5. Click the Misc tab, then shift + right click the key and a scroll, each followed by the counts.
6. Escape, but only with one of her panels open (with nothing open it opens the game's menu).
7. Walk back until the waypoint is on the screen.

**In play.** The log says `Shop: N keys, M portals` before and after, and `Macro: shop: keys a -> b, portals c -> d`.
Not known until played: whether a shift + right click buys a full stack of keys and fills the tome. The counts show it.

The design, as planned:

- **Counts:** `tracking/resources.py` already reads them (`select_tome`, `select_keys`; offsets verified 2026-09-21).
  The macros read neither yet.
- **The leg:** in Pandemonium Fortress, before the waypoint to Lower Kurast, when either is under 3. Jamella (405)
  sells both; a visit buys both up.
- **The steps:**
  1. Find Jamella among the units.
  2. Click her (the hover check, as for the waypoint).
  3. Choose Trade.
  4. Find the scroll and the key in her stock grid (`shop/capture.py`, read the same way).
  5. Buy with the clicks the game takes.
  6. Close the panel.
- **Not known yet:**
  - the trade menu's layout and the stock panel's cells (from the game's layout JSON, as the waypoint panel was);
  - whether a shift + right click buys a full stack of keys and fills the tome;
  - where Jamella stands against the waypoint.
- **Phase 0 first:** a played evidence pass, reads only, before any click.

#### Phase 8 evidence (2026-10-16, offline)

- **Jamella (monstats 405)** in 101 takes of Pandemonium Fortress: at (5083.5, 5058.5) in 63 of them. She wanders up
  to 9 units from it. She is 38 units from the game's start (5048, 5044) and 56 from the waypoint, so a shop visit is a
  walk there and back, made only when a count is under 3.
- **The vendor panel** (`data/global/ui/layouts/vendorpanellayouthd.json`, `_profilehd.json`, read with
  `terror_zones/game_files.py`):
  - `$LeftPanelRect` at `$LeftPanelAnchor`, as the waypoint panel.
  - 4 tabs from (82, 162), 249 × 75 each: Armor, Weapons, Weapons, Misc.
  - The stock grid from (91, 233), 10 × 10 cells of `$ItemCellSize` 98 × 98.
  - Close at (1075, 9).
- **The stock in memory:** `shop/capture.py` (`locate_stock`, `stock_members`) reads each item of the vendor's four
  grids (2–5) with its tab (`inventory_page`) and cell (`x`, `y`). So the key's (558) and the Town Portal scroll's
  cells are read, not assumed. The stock is in memory only once the trade window has been opened in the game
  ("Shop stock unloaded" before).
- **The NPC menu** (`npcdialogpanelhd.json`): drawn beside the NPC (`verticalOffset` 20), its lines sized by
  `$StyleNPCDialogueSize` with 10 units between them. Its place on the screen is not in the layout, so it needs one
  screenshot of the open menu.
- **Already recorded by the takes:** each frame has `panels` (`npc_interact` while the menu is open, `npc_shop` while
  the trade window is), `in` (the pointer), the character and Jamella. A screenshot's moment is matched to the take
  by its clock.
- **Asked of the player (one visit, by hand, `make serve` running):**
  1. A screenshot with Jamella's menu open.
  2. A screenshot with her trade window on the Misc tab.
  3. Optionally, a key and a scroll bought with a shift + right click (does it buy a full stack, fill the tome?); the
     resource readers will show the counts.
- **Counts:** `tracking/resources.py` `select_keys` and `select_tome`, to be read by `GameMemory` for the macros.
- **The player's visit (2026-10-16 21:03 and 21:15, two screenshots, takes `20261016T180313Z-103` and
  `…181510Z-103`):**
  - Jamella's menu: her name, then Trade, Gamble, Cancel. In the window, Trade is 0.2214 and 0.2155 of its height above
    where `routines.screen_fraction` draws her (her place from the take, the character's at the click). It is centred
    on her, within 0.013. The menu's lines are 0.0226 apart, so an aim at her drawn point plus (0, −0.218) is inside
    the Trade line.
  - Each Trade click opened `npc_shop` (with `inventory`) 1.0 to 1.2 s after the click on her: the click is confirmed by
    the panel flag.
  - The click on her was made from 3.5 units off. The game walks the character the rest.
  - The trade window's Misc tab, and its stock grid's last column (the key at row 5), are where the layout puts them:
    measured on the screenshot, within 2 pixels of the screenshot's scale.
  - The Misc tab holds the tomes, the potions, the key and the scrolls.

### 9. Loot to Cube (more games without the player): done by mouse (uncommitted, not played)

**The code.** `macros/cube.py` (`plan`, `stash`, `cell_point`), `world.carried_items` / `pack_of` /
`GameMemory.carried` / `Run.carried`, `Loop.own`, the LEAVE leg's `stash`, and `keybindings.action_key` with
INVENTORY = 1.

**The steps.** In Pandemonium Fortress, before Save and Exit:
1. The inventory is opened by its key (`i`).
2. The cube is opened by a right click on it.
3. Each item that came since the loop began (not in `Loop.own`, by class and cell; never the cube, a tome or a key) and
   fits the cube is sent into it by a Ctrl + click, smaller items first. The player, later that day: "we can move
   faster items to cube - open and ctrl+click on item". The game finds the room itself.
4. Escape closes the panels.

Each click is checked in memory: the item lies in the cube's grid. One that does not go in is put back if it came onto
the pointer, and the loop stops.

**The evidence.**
- The layouts: the inventory 10 × 4 at (93, 897) of `$RightPanelRect` (−1394, −651) at (1.0, 0.397); the cube 3 × 4 at
  (431, 534) of the left panel; 98 units a cell. The screenshot of 21:16 puts the inventory's first cell where they
  say.
- The key file's action 1 is Inventory (`i`, `b`).
- The player opened the cube in Pandemonium Fortress by hand at 21:03 and 21:15.

**In play.** The log says `Macro: cube: N of M of the loop's items moved in` and `Cube: N items put in`.

**Open.** The cube holds 12 cells. An item the player moves in the inventory during a loop is seen as the loop's.

Before, the plan was:

Loot to Cube works only in controller mode (the virtual pad's X, `input/gamepad.py`, `macros/pad.py`). The macros
follow the game's mode and never switch it. The player's answer (Open 4): the inventory's items are moved into the
cube between games, so more games run before the inventory is full.

## Open (for the player)

1. ~~Why back to act 4?~~ Answered (the player, 2026-10-16): a game left in act 3 starts in Kurast Docks, a long
   walk from its waypoint; the portal lands near it, and Pandemonium Fortress's start is by its waypoint. The loop
   goes portal → Kurast Docks → waypoint → Pandemonium Fortress → Save and Exit.
2. ~~Lower Kurast's own waypoint~~ Answered (the player, 2026-10-15): "in LK we prefer to use portal because it is
   usually faster way, then a navigating back". After the last chest the loop always casts Town Portal.
3. **Stops**: is the list in phase 4 right? A cap on games or hours?
4. ~~Loot to Cube (phase 9)~~ Answered (the player, 2026-10-16): "probably move items between games": the
   inventory's items into the cube between games, not the drops picked into it.

## Order

LK plan 1–2 (the chests work) → phase 0 → 3 → 1 → 2 → 4 → LK plan 3–5 → 5 → 6a–6e → 7 → 8 → 9. Each phase its own
commit with its tests (serial, one run at a time).
