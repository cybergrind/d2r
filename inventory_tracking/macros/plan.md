# Macros: Win+X prebuff for Pindleskin runs

Plan, 2026-10-06. First version implemented the same day (see Status); not yet run in the game. Companion to the
[input design](../input/design.md), which this package builds on.

## Goal

One hotkey, Win+X, handled by `make serve`, does the chores between Pindleskin runs for
CybergrindAA. It reads where the character is and picks a routine:

| Where | Routine |
| --- | --- |
| Nihlathak's Temple (area 121) | `next-game`: leave the game, create the next one, then the full prebuff |
| anywhere else in a game, town or not | `prebuff`: the full prebuff, without leaving the game |
| not in a game, or another character | nothing; the HUD says why |

A game with other players in it is fine (2026-10-08): the character is the one player unit
with a plausible life, as in the collection path; shared stash tabs and other players' units
have none (`world.local_player`).

Full prebuff, in town after the new game loads: Summon Defiler → Consume (the Defiler, not the
bound demon) → Summon Defiler → Hex: Purge → Psychic Ward.

The package is a base for later macros and characters: the Pindle routines are a thin layer of
steps on top of a generic engine.

## What is already known (checked 2026-10-06)

- **Keys.** `CybergrindAA…keyo` binds `q` (action 21), `6` (action 50), `g` (action 18) and
  `r` (action 48); `input/keybindings.py` already parses this file.
- **Quick Cast is on** (`Settings.json`, `"Quick Cast Enabled": 1`): a skill key casts at the
  cursor at once. So where the pointer is decides where the Defiler appears and what Consume
  and Hex: Purge hit.
- **Skill ids** (d2data `skills.json`): Summon Defiler 377, Consume 381, Bind Demon 382,
  Psychic Ward 387, Hex Purge 389. The summoned Defiler is monster `warputriddefiler`, 744.
- **Readers that exist:** area and town flag, player position (live, per frame), Consume state
  (`tracking/consume.py`), open panels including `quit_menu` (`native/layout.py`), monsters
  with their owner (`native/mercenary.py`, owner at `monster_data` u32[21]).
- **Input that exists:** guarded XTest key chords (`PotionInput.attempt_keys`): focus, exact
  process, no key physically held, fresh sample. No pointer support. The guard needs a
  `SessionIdentity` with a player, which does not exist in the lobby.
- **Hotkey path:** niri binding → `appraisal_service request --…` → datagram → `dispatch()`.
  `Mod+X` is free in the niri config.
- Reference: koolo creates online games by clicking the name field and typing; d2go reads
  lobby state, the last game name and skill-slot bindings, but at offsets of another build.

## Research gates (host probes, before the code that depends on them)

Each gate is a small probe the user runs once; it writes a report file the agent reads. A gate
that fails has a stated fallback, so no gate blocks the whole plan.

| # | Question | Needed for | Fallback |
| --- | --- | --- | --- |
| R1 | Do XTest pointer motion and clicks reach the game under XWayland on niri? | lobby click, aiming | `uinput` virtual pointer |
| R2 | Which key action is which skill slot, and which skill id sits in each slot (memory)? Expect slot of action 21 → 377, 50 → 381, 18 → 389, 48 → 387 | "be sure of the hotkeys" | confirm by effect only (see Verification), with keys pinned in the profile |
| R3 | How to tell lobby / loading / in game for this build | waits in `next-game` | "no player unit and process alive" for out of game; "player unit, area 109, position stable" for loaded |
| R4 | Where is the current game name in memory? | next name (`cyber32` → `cyber33`) | read it from the lobby field is not possible; keep the last name in a state file, seeded once |
| R5 | Can the quit menu and the lobby be driven by keyboard alone (Up/Enter on the menu; is the name field focused on entry)? | fewer pointer actions | click at window-fraction positions |
| R6 | Consume: does it need the pointer on the Defiler, or does it take the nearest demon? Does Hex: Purge need a target? | aiming | always aim |
| R7 | World offset → screen pixel for the game window | aiming at a unit | fixed offset right of the character |

R2, R3 and R4 need the memory work in `pricing/raw/re` (`d2re.py`) against a dump the user
makes; d2go's offsets are starting points only.

### Findings from the first recording (run `20261006T131316Z-5d3e1ad2`, cyber34 → cyber35)

- **R2 answered.** The skill slots are a table at image RVA `0x1E011B0`: 16 records of 28
  bytes, the skill id in the first u32 (`0xFFFFFFFF` empty). Slot `i` is key action `14 + i`
  for slots 0–7 and `46 + (i - 8)` from slot 8. CybergrindAA: slot 4 Hex Purge (`g`), slot 7
  Summon Defiler (`q`), slot 9 Bind Demon (`e`), slot 10 Psychic Ward (`r`), slot 12 Consume
  (`6`). All four keys the user named agree with the table and the key file.
- **R4 answered.** The game name is a zero-terminated ASCII string at RVA `0x1E9A0B8` (copies
  at `0x2170668`, `0x25C2D68`, `0x2600C00`). In the lobby it still holds the game just left,
  which is the number to increase.
- **R3 partly.** Byte 0 of the panel array (`UI_PANELS_RVA`) is 1 in a game and 0 from Save
  and Exit until the next game starts; `quit_menu` (+0x09) is 1 while the menu is open. Lobby
  against character select or a loading screen is not told apart yet.
- **R1 answered** (pointer run `20261006T131851Z-3f71418d`): XTest pointer motion and a left
  click reach the game. The game window was at (1920, 0), 2560×1418, in X root coordinates;
  the click on "Return to Game" at window fraction (0.5, 0.509) closed the quit menu.
- The panel array is not all zero with nothing open (+0x00, +0x0A, +0x0C, +0x12, +0x14, +0x1B
  were set in town), so "nothing open" must test the named flags only.

## Design

```
inventory_tracking/macros/
  plan.md
  timing.py      human-like delays and key holds (seeded RNG, injected sleep)
  actuator.py    key chords, text typing, pointer moves and clicks, behind one guarded interface
  world.py       World: one fresh, validated snapshot of everything a step may ask about
  engine.py      Step, Routine, Runner: act → wait for evidence → next; abort rules
  skills.py      skill id → slot → key for the current character (R2)
  routines/
    prebuff.py   summon_defiler, consume_defiler, purge, ward: reusable buff steps
    new_game.py  leave_game, create_next_game, wait_loaded
  profiles.py    character name → {area rule → routine}; CybergrindAA only
tests/inventory_tracking/macros/…
```

### Engine

A routine is a list of steps. A step has three parts, and the engine owns the loop:

1. **Guard**: what must be true in the `World` before acting (else abort with a reason).
2. **Act**: one small input action through the actuator.
3. **Evidence**: a predicate on later `World` snapshots, with a timeout and at most a small
   number of retries of the act.

No step succeeds on a timer alone. Delays pace the input; memory evidence moves the routine
forward. Examples: Escape → `quit_menu` flag set; Save and Exit → player unit gone; Enter in
the lobby → player unit present in area 109 with a new session; Summon Defiler → a monster 744
owned by the player exists; Consume → Consume active and that Defiler gone and the bound demon
still there; Psychic Ward → its state on the player (state id found during R2/R6 probes).

The runner works on its own thread in `serve`, one routine at a time. It stops at once, and
releases any key it holds, when:

- Win+X is pressed again (cancel);
- the game loses focus, or the process changes;
- the user presses a key or moves the mouse (the existing "no key held" guard, plus a pointer
  position check between actions);
- a guard or evidence fails, the character dies, or an unexpected panel is open.

The first action waits (up to about a second) for the Win and X keys to be released, because
the guard refuses while any key is down. Progress and the abort reason show on a HUD card and
go to the log and a run file under `runs/macro/`.

### Actuator

One interface for keys, text and pointer, so routines never touch X11. It reuses the `input`
package's connection, focus tracker and guards. Two changes there:

- the guard target becomes process-only when there is no player (lobby), instead of a full
  `SessionIdentity`;
- `X11Connection` gains pointer motion and button events (or a `uinput` backend, per R1).

Pointer targets are fractions of the game window, as the HUD slots are, so they survive a
resolution change. `make osd` (healing) presses keys from another process; a shared `flock`
around each chord keeps a potion press from landing inside a macro chord or the typed name.

### Timing

- Between actions: a base delay per kind (key after key, after a pointer move, after a screen
  change) with a skewed random spread, clamped; roughly 80–250 ms between casts beyond the
  cast's own evidence wait, 300–700 ms after a screen change.
- Key hold 40–110 ms, random; typed digits 60–160 ms apart.
- Pointer moves travel along a short eased path with a few pixels of scatter on the end point,
  not a jump.
- One seeded RNG and an injected `sleep`, so tests are exact and fast.

### Hotkeys must be known, not assumed

`skills.py` resolves each skill the routine needs: skill id → slot (memory, R2) → key (the
character's key file). If any skill has no pressable key, or the slot holds another skill, the
routine does not start and the card names the missing skill. Nothing in the profile says "q";
it says "Summon Defiler".

### Routine: `next-game` (in Nihlathak's Temple)

1. Guard: in game, area 121, alive, no panel open (close with Escape first if one is).
2. Escape → quit menu open. Save and Exit (keyboard or click, R5) → out of game.
3. Wait for the lobby with the Create Game tab (R3). Not there within the timeout → abort; the
   macro never navigates menus it does not recognise.
4. Next name: trailing number of the last game name + 1 (R4). Click the name field, select
   all, type the name, Enter. The password field keeps its value.
5. Wait until loaded: new session, area 109, position stable. A "game already exists" or any
   modal → abort.
6. Full prebuff (below).

### Prebuff steps

- **Summon Defiler**: pointer to a spot right of the character (the user's habit), press the
  key, evidence: an owned 744 appears. Its unit id is remembered.
- **Consume**: pointer onto that Defiler's screen position (R7), re-read just before the
  press; evidence as above. If the bound demon vanished instead, abort and say so.
- **Summon Defiler** again, **Hex: Purge**, **Psychic Ward**, each with its evidence.

### Routine: `prebuff` (anywhere but the Temple)

The prebuff steps above, with no menu or lobby step. It never opens a menu.

## Order of work

1. Probes R1–R7 and their reports; fold the answers into this plan.
2. `timing.py`, `engine.py` with fakes: step loop, evidence, retries, every abort rule (TDD).
3. `input` changes: process-only target, pointer events, cross-process chord lock.
4. `world.py` and `skills.py` on recorded snapshots.
5. `prebuff` end to end (no menus or lobby, lowest risk), host-verified.
6. `next-game`: leave, lobby, name, load; then the full prebuff.
7. Hotkey: `request --macro`, `macro <t>` in `dispatch()`, the niri `Mod+X` line, HUD card,
   README and Makefile notes.

## Risk to accept before building

This sends synthetic input to an online Battle.net game and creates games automatically,
which Blizzard's terms do not allow; randomised timing lowers how mechanical it looks but
gives no guarantee about account action. Healing already sends keys the same way; this goes
further (menus, lobby, game creation).

## Decisions (user, 2026-10-06)

- In Nihlathak's Temple Win+X always leaves the game, whatever is alive nearby.
- Everywhere else, town or not, Win+X does the same full prebuff (Summon Defiler, Consume,
  Summon Defiler, Hex: Purge, Psychic Ward), also in a game made by hand. There is no shorter
  routine outside town.

## Status (2026-10-06)

Built: `timing.py`, `actuator.py`, `world.py`, `skills.py`, `engine.py`, `routines.py`,
`runner.py`, `probe.py`; `request --macro` and `macro <t>` in the service; pointer events in
`input/keyboard.py`. Tested against a scripted game (tests/inventory_tracking/macros), not yet
in the real one.

Differences from the design above, and what is still open:

- Routines are plain functions of a `Run` (`run.expect(what, predicate, timeout)`), not step
  objects; `profiles.py` is a constant in `routines.py` until a second character needs it.
- Host run 16:37: the summon is monster class 744 as expected, but its owner field (the one
  that works for the mercenary) is `0xFFFFFFFF`, so summons cannot be told by owner. The
  Defiler is now "a new class-744 unit"; Consume must make that unit vanish, so a Consume that
  took the bound demon still stops the macro. The Defiler's unit and data bytes go to the log
  to find the real owner field.
- Hex: Purge and Psychic Ward have no known mark in memory: the cast animation is looked for
  and a miss is only logged. Their states should be found and made required evidence.
- Consume aims with the classic isometric projection (`routines.screen_fraction`), unverified
  in D2R; the summon spot and the Consume aim are close together, which helps.
- First host run (16:32): Save and Exit worked; the name was then typed blind after a fixed
  pause, nothing landed and Enter did nothing. The name at `0x1E9A0B8` is the lobby field's own
  text (the recording shows `cyber3` mid-edit), so each edit is now checked there: click, End,
  one Backspace, and only a shortened name lets the macro go on (up to six tries); Enter is
  pressed only when the field reads the new name. The fixed lobby pause is gone.
- Not built: the cross-process lock against `make osd` key presses, the run file under
  `runs/macro/`.
- Prebuff is a goal, not a fixed sequence (user, 2026-10-06): end with Consume active and one
  Defiler out. A Defiler summoned while one stands cancels Consume, so a standing Defiler is
  consumed (buff missing) or kept (buff active), and a summon happens only with none out.
- Loading (user, 2026-10-06: the macro started on the loading screen). The first recording has
  two bytes for it: `0x2122131` is 1 only on the loading screen, `0x20D7DA0` is 1 in a game
  and returns to 1 three seconds after the loading byte clears. "Playable" needs both, and the
  macro waits for it after creating a game and refuses to start without it. One recording
  only: confirm on the host.
- Only the changed end of the game name is retyped (cyber36: one Backspace and `7`).
- Click positions are corrected for the 22-pixel desktop bar above the game window.
- Host, same day: with both bytes required the macro refused to start in a loaded game, so
  one of them is not what the recording suggested. Now nothing gates the start (the bytes are
  logged there); after creating a game the loading byte is used only if it was clear in the
  lobby, together with "the town's units exist" and a 1.2–2 s pause.
- Host run 17:38: with the real cursor parked on the left, the Defiler appeared at the spot
  the synthetic pointer move named and was consumed, so the game honours XTest motion for
  quick casts (the cursor the compositor draws does not follow). The projection matched across
  to 0.003 of the width; the feet line moved from 0.47 to 0.494 of the height. The "settled"
  byte read 0 in that loaded game: it was the wrong one of the two.
- Host run 18:29: the lobby step works (click, one Backspace, the new digit, Enter). The
  prebuff then started 3 s after Enter and three summons over the next 6 s were ignored: the
  character and the town's units exist while the loading screen is up, and the "loading" byte
  read 1 in loaded games, so neither byte from the recording is used any more. Now nothing is
  pressed for 8.5 s after Enter, and the first summon is repeated until a Defiler appears (up
  to 40 s after Enter). Twenty candidate bytes are traced during that wait and their changes
  logged with the time of the first working summon, to find a real "playable" mark.
- Host run 18:35: creating the game failed in the game itself (an error on screen); the macro
  waited 45 s for it, and for those 45 s the service loop stood still ("Slow service pass:
  47466 ms, level map"). Cause: the macro kept the process-wide X11 lock for its whole run and
  the level map's focus check opens its own X connection. The macro's connection now holds
  the lock only to open and close (`connect(exclusive=False)`), and a game that does not exist
  12 s after Enter stops the macro with "was not created".
- Loading mark found (two traced host runs, 18:37 and 18:38, first summon accepted at 9.7 s
  on the first try, the user seeing about 3 s of idle game before it): the byte at
  `0x1EB3465` is 255 in a game, 0 from 0.6 s after Enter, and 254 at 6.55 s and 6.18 s; the
  recording agrees (back 6.5 s after Enter). The macro now waits for it to leave 0 and then
  only a 0.35–0.75 s pause; the fixed 8.5 s is the fallback when the byte never shows the
  loading. The trace stays on to check the mark on further runs.
- Lobby (user, 2026-10-06): Win+X out of a game creates the next game and prebuffs. The
  character and its keys are checked once the game is up, before any skill key.
- Eldritch and Shenk run (user, 2026-10-06): Win+X in the Frigid Highlands (111) or the Bloody
  Foothills (110) leaves and makes the next game, as in the Temple. The whole level counts;
  "near the waypoint" is not measured. Both are counted by terror/bosses.py.
- Weapons (user, 2026-10-06): the prebuff is cast with Heart of the Oak + Spirit (base codes
  `fla`, `uit`, per character in `routines.CHARACTERS`). The set in hand is read from the
  equipped items at body locations 4 and 5; with the other set in hand the Swap Weapons key
  (key action 44, `c` in CybergrindAA's file, read from the file) is pressed first and the
  set is left in hand. Unconfirmed on the host.
- Bound demon consumed (host, 20:51): Consume took it with the pointer on the Defiler; the
  macro only noticed afterwards. Now Consume is pressed only while no other living monster
  (the mercenary aside) is within 7 world units of the Defiler, checked again after the
  pointer move; a crowded Defiler is replaced by one summoned at an open spot (five spots,
  open ones first), and after three tries the macro stops without pressing. Research logged
  on each Consume: image addresses holding (monster, Defiler id) with the pointer on it, to
  find the "unit under the pointer" record and require it before the key.
- 2026-10-07, "a key was pressed" in a new game (host, 13:11, and seven earlier runs): the key
  was the OSD's own Show Items press (`z`, 1.5 s into a game, retried every 2 s), down at the
  moment of the macro's first summon or just after Consume; the timestamps in `osd.log` agree
  to 20 ms. The guard now reads which keys are down (`held_keys`) and leaves out the
  character's Show Items key (`Actuator.allow`); every other key still stops the macro. The
  OSD's potion keys are not left out yet: no stop has been traced to one.
- 2026-10-07, three crowded Defilers in a row, twice (host, 13:08, Rogue Encampment by the
  stash): every replacement was summoned at the first spot again, which read as open, and
  was crowded there again. Each replacement now starts one spot further on, and the log
  names what crowds the Defiler (class and offset). What it was is not known: unconfirmed
  whether the bound demon or a walking town resident.
- 2026-10-07, "something stays too close" five times (host, 19:37 to 19:43, Rogue Encampment):
  the log now names the crowd. Of 16 crowded Defilers, 13 had Kashya (150), Warriv (155) or
  Cain (265) in the crowd, 5 of them nobody else; the bound demon (Pit Lord, 361) was in 11. Seven
  were crowded only by the cover column added that morning, not by the 7-unit circle. Each
  crowded verdict waits a second and summons again, so three in a row is five seconds and a
  stop. Consume itself was as before: pressed about 0.35 s after the summon on both days, 3
  misses in 111 (10-06) and 3 in 71 (10-07). Changes: townsfolk (`TOWN_NPCS`, monstats npc = 1)
  no longer count as bystanders (assumed, not seen: Consume cannot take them); skipping spots
  keeps the open ones first; and Consume is aimed after the character is ready, at the Defiler
  as it stands, following it if it walked during the pointer move (`aim_at`; user: the Defiler
  moves). A Defiler that never stands still through four aims is not consumed: the pointer
  would be where it was, and the bound demon may stand there (user: never consume the demon).
  Not yet run on the host.
- 2026-10-07, "Consume: not seen in 2.5s" at 20:04 (host, new game, Rogue Encampment), with the
  changes above running: the key went down 0.34 s after the summon, as in the three runs before
  it that worked; no drift was logged. The monster probe shows the Defiler standing where it
  landed (2, -8 from the character) with no death, and all 11 units alive afterwards: Consume
  did nothing and the bound demon was not touched. Why is not known: the log held nothing
  about the scene. Not the weapon swap before it (10 of 11 swapped runs worked) and not the
  OSD's Show Items key (same timing in runs that worked). It is the miss seen all along: 7 of
  186 presses over two days. The probe also shows consumed Defilers dying where they were
  first seen, so in 0.35 s a Defiler does not walk. Now a press that changed nothing (Defiler
  there, buff off) is logged with the scene (`log_miss`: modes, the mercenary, townsfolk, the
  pointer) and made again under the same checks, three presses at most; anything else stops
  as before.

- 2026-10-06, act 4 after act 3 (user: Mephisto and other act 3 runs step into act 4 before Save and
  Exit): the Pandemonium Fortress (103) is a run end while the character came to it from an act 3
  level (75-102) at most 180 s ago. The service notes game and level once a second
  (`journey.Journey`, `MacroRunner.poll`); a game that started in the Fortress has no level before
  it, so Win+X there only prebuffs. Scripted tests only; not run on the host yet.

- 2026-10-06, Consume is always cast (user: the buff ran out; "active" says nothing about the time
  left): every prebuff consumes a Defiler (the standing one, else a summoned one) and then summons
  one, whether or not Consume is active. This replaces "press only what is missing". Research: the
  buff's 0x80-byte record is logged before and after each cast ("Consume record"), to find the
  field with the time left; with it the cast could be skipped while plenty remains.

- 2026-10-07, Andariel run (user): Win+X on Catacombs Level 4 (area 37) with no live Andariel
  (monster 156) in the unit table is a run end: leave, create the next game, prebuff. With her
  alive in the table it prebuffs. No corpse is asked for (user, after two host runs): hers leaves
  the unit table 19 s after the kill, and a service started after the kill never saw it. She is in
  the table from 86 units away; further off before the fight, Win+X leaves the game. Scripted
  tests only.

- 2026-10-07 01:46, bound demon consumed again (host): the demon (class 189) stood 8 world units
  from the standing Defiler, past the 7-unit clearance, but below it on the screen (3 iso units
  across, 11 down), so its body covered the pointer. Clearance is now also a screen column around
  the Defiler (`routines.in_the_way`: 9 across, 26 below, 8 above, in x - y / x + y units); the
  same test picks the open summon spots. The numbers are from this one case, not measured sprite
  sizes. Still open and the real protection: read the unit under the pointer before the key.
- Host, 2026-10-08: in a game joined by other players the macro said "not in a game". The
  player lookup wanted one character name among the player units, and another player's unit
  carries its own. Now, with several names, the character is the one unit with a plausible
  life (`tracking/state.select_player`'s rule; `Caras` in collection/research.md R3 had none).
  Not yet confirmed on the host.

## Win+T: one step toward the level card's mark (2026-10-09)

User: a hotkey that teleports as far as possible toward the target, found dynamically (whether
Teleport is available, which key, which weapon set), and that walks into the door when it is close
instead of teleporting next to it. Built the same day in `teleport.py`, scripted tests only.

- **Hotkey path:** niri `Mod+T` → `request --teleport` → `teleport <t>` → `MacroRunner.request(…,
  routine='teleport')`. Either hotkey pressed during a run cancels it (one runner, one thread).
- **The mark** is the level card's first POI, what the first arrow line points at
  (`LevelGuide.target()`: area, rooms, point in tiles, label, kind, whether the point is the warp
  tile). No card up → "nothing is marked on the level card (Win+C shows it)"; a card for another
  level → stop. `make serve` pins the card, so there normally is one.
- **The way** is the teleport route (`levels/route.py`, same day: straight over rooms, around void
  wider than `REACH`). The hop lands at the farthest point of the route's first leg that is both
  drawn on screen (`routines.AIM_LIMITS`) and on a room (`teleport.landing`); the pointer goes to
  the ground there (`ground_fraction`: `screen_fraction` without the body lift) and the Teleport key
  follows (Quick Cast). Straight east that is about 23 world units, the skill bar being the limit.
- **Teleport is found, not assumed.** Skill 54 must sit in a skill slot (the key comes from the
  character's key file as for every skill). `GameMemory.teleport()` reads the worn staff with
  Teleport charges from either weapon set (stat 204, layer >> 6 == 54, the item's full stat list at
  `RESOURCE_READER.teleport_stats_offset`): no charges → stop before any key; on the other set →
  Swap Weapons first and wait for it in hand; left in hand afterwards (the next press needs it).
  Without such a staff the key is pressed as it is (Teleport as a skill: Enigma one day).
- **Evidence:** the character moved at least `MOVED` (2) world units within 1.5 s, else "did not
  move (no charges, no mana, nowhere to land?)".
- **The door:** a mark of kind stairs/previous/exit whose point is the warp tile (`levels/spots.py`
  pinpointed it) within `NEAR_WARP` (20 world units, four tiles) and on screen is clicked, not
  teleported to: teleporting onto a warp tile does not take it. Evidence: the character moves; the
  level change is announced when it comes within 6 s.
- Open: `NEAR_WARP`, the on-screen limits and the walk's path (a wall between the character and the
  door makes the game walk around) are untested in the game; so is the charge read on the swap
  set, which the OSD's Teleport widget reads the same way.

### Pressed again and again (host, 2026-10-09 17:44–17:46)

The first build was unusable (user): "a key is held" twice (Win still down), six hops that each
gained about 15 world units on a 465-unit way with 5–8 s between them, the door walk stopped by "the
mouse was moved", and a press during a step cancelled it. Changes:

- **Hotkey process:** `appraisal_service request` took 0.35 s (imports). `inventory_tracking/request.py`
  sends the same datagram with the standard library only, in about 10 ms; the niri `Mod+T` line now
  runs `.venv/bin/python -S …/request.py teleport`. The other bindings could follow.
- **Win held:** the teleport routine allows `Super_L`/`Super_R` down (`runner.HOTKEY_KEYS`) and no
  longer waits for a release. Whether the game takes the macro's `t` while Super is down is unproven.
- **Mouse:** the drift guard is 60 px for this routine (`teleport.POINTER_DRIFT`); the player's hand
  is on the mouse. Pointer moves are flicks (`Actuator.move(quick=True)`: 3–6 steps, 30–90 ms after).
- **Longer hops:** the landing may go anywhere the view shows ground (`teleport.VIEW`, up to 0.84 of
  the height), not only `routines.AIM_LIMITS`: about 26 units down-screen, 31 across, 32 up-screen.
  The classic projection scale bounds this; a real teleport reaches about one screen as well.
- **Chaining:** `MacroRunner.working` says whether a run acts; the card no longer keeps the run
  "alive". Win+T during a teleport step queues one more step (one at most); Win+X during anything,
  or Win+T during a prebuff, cancels. No throttle on Win+T.
- Nothing waits after the hop; the evidence (the character moved) ends the step.

### Landings (host, 2026-10-09 17:53, Durance): aimed against landed

User: some teleports landed far off and some were aimed over wide gaps. A Room2 rectangle is not
ground: it holds walls, pits and chasms, and a teleport aimed at one lands wherever the game finds
footing, or nowhere ("did not move" at 17:53:41). Changes: the target carries the walkable sub-tile
grids the level map reads for the loaded rooms (`Target.ground`, `levels/model.walkable_at`); the
landing is the farthest in-view point of the leg whose sub-tile and the eight around it are
walkable (`teleport.footing`), the room rectangle standing in only where no grid covers the spot.
Every hop logs "teleport aimed at (x, y), d from (px, py), cut by leg|view|ground, footing …, n
grids, pointer … in …; landed at (x, y), off by d (dx, dy)". Read those lines after the next run:
a steady offset means the projection scale (`routines.UNIT_PIXELS`, verified only near the
character) is off at range; a landing on the far side of a wall means the footing margin is small.
The 17:53 hops gained 22, 19, 6, 15, 28 and 23 units, so the 6-unit one is the first to look at.

### The whole view, not the leg (host, 2026-10-09 18:02)

The first logged hop had the projection 0.7 units off at 18.8 units (aimed (17748.8, 7112.6), landed
(17749.5, 7112.5)), so aim is not the problem. The ten presses after it all stopped with "nothing to
land on in view": the landing was searched along the route's first leg only, and that leg crossed a
chasm, so no in-view point of it had footing. Now `teleport.landing` tries ground points across the
whole view (`spots_in_view`, 0.03 of the window apart, plus the route points themselves so the last
hop lands on the mark) and takes the one leaving the shortest way to go (`Way.to_go`: the distance
to a route point reachable by a teleport chain, void no wider than `route.REACH`, plus the route from
it). A hop is made only if it takes `MIN_GAIN` (3 units) off the way; else "no footing in view brings
the character nearer to …". The log line says how much a hop took off the way ("… off the way").
Cost on the Durance 2 fixture with 48 grids of 8x8 rooms: 38 ms per landing search, 0.5 ms for the route.

### A potential, not straight lines (host, 2026-10-09 18:10, Durance 2 game cyber5)

Game cyber4 chained nine hops of 24–30 units and walked into the door, every landing within 1.1
units of its aim. Game cyber5 stalled after two hops ("no footing in view brings the character
nearer", ten times). Replayed offline from the evidence record of that entry and the wall library
(`runs/levels/evidence/101/20261009T151111.json`): from the second position the pulled-tight route's
first point was 33 tiles away and the straight-line void rule called 425 of the footings in view
unreachable, leaving 4.8 units of gain and then none. Now `route.distances` runs Dijkstra from the
mark over the room instances once (tiles per instance to the mark), and a spot's way to go is its
distance to its own room's point or a neighbouring room's (within `REACH`) plus that room's
distance. The replay from the same start now chains hops of 20–31 units through the stalled spot,
20–28 ms per landing search. The route drawn on the map is unchanged.

### Tile potential (host, 2026-10-09 18:18, Durance 2 game cyber6)

Twelve hops of 22–28 units, one "did not move" that the retry took, one landing 3.5 units off,
then a stall at (17702.5, 6899.5) with 134 units left. The footing map of the replay (evidence
`101/20261009T151828.json`, wall library): the character stood in a north–south corridor, the
room's own south-west was solid wall, and the only footing with any gain lay in a parallel corridor
just past the view's left edge (−42 units across; the view shows ±34). One cost per room could not
express that. `teleport.Way` is now a potential over landable tiles: Dijkstra from the mark's tile,
hops of at most `REACH_TILES` (5) to other landable tiles, walls in between or not; a tile is
landable when its centre has footing, or lies on a room without a grid. Built once per target
(`way_for`, cached: 4.7k tiles in 87 ms), 5 ms per landing after. The replay now reaches the door
from both stalled positions (8 and 16 hops of 22–31 units). `route.distances` (room potential) is
gone again. The service started at 18:13 ran with a half-edited import and failed four presses
("Macro failed", NameError); the 18:14 service was whole.

### KP_4, and the door only from ten units (user, 2026-10-09 evening)

The binding moved from Win+T to the bare keypad 4 (niri `KP_4`, same fast sender); the runner allows
`KP_4` down as it allowed the Mod. Host 18:23: a walk into the door started from 19.9 units and took
six seconds around a wall before a second press arrived, so `NEAR_WARP` is 10 units: teleport until
almost there (the last hop lands on the door tile itself when it has footing). The walk line now
says the distance. Host 18:21: five presses stopped on "the mouse was moved" with the 60-pixel
drift allowance; it is 400 for this routine.

Teleport on KP_5 in the game (user, 2026-10-09 evening): the key file then holds VK_NUMPAD5 (0x65),
which `input/keybindings.x11_name` now turns into `KP_5` (the whole keypad, the navigation keys,
Escape and BackSpace were added). X11 puts KP_5 and KP_Begin on one key code (84 here), so the
macro's press lands as whatever Num Lock makes of it, exactly like the player's own; the game
must have been bound with the same Num Lock state the player plays with. The niri `KP_4` binding
likewise fires only while Num Lock is on (off, the key is KP_Left).

`KP_4` bound nothing (user, 2026-10-09 evening): niri matches configured binds against the raw
keysym, the key's level without Num Lock (`src/input/mod.rs`, `raw_latin_sym_or_raw_current_sym`,
`find_bind`), and the keypad 4's raw keysym is `KP_Left`. The niri line is `KP_Left` now; the game,
which gets the key when niri does not take it, still sees KP_4. The arrow key is `Left`, no clash.

## Hunting: KP_2 (elites) and KP_3 (any mob), 2026-10-09 evening

User request: two more keys built on the teleport step. Both first kill what stands in reach; when
nothing does, KP_2 teleports toward the nearest unique, champion or super unique, KP_3 toward the
nearest monster of any kind; when none is known, either teleports toward the nearest unexplored
room, where more will show. Kills are Echoing Strike (skill 388), with Sigil: Lethargy (393)
under elites first. One press is one step, as with KP_4: an attack burst, or one hop. The same
key during a step queues one more; any other macro key cancels.

### What was found (installed game, key file and sources, 2026-10-09)

- **Echoing Strike is the left-click skill**: it is in no skill slot of `CybergrindAA` (the slot
  table in the macro records: slots 0-12 hold 379, 390, 375, 384, 389, 220, 393, 377, -, 382,
  387, 54, 381) and skills.txt marks it `leftskill`. So it is cast by a left click on the
  monster with Shift held (the classic "attack in place": the character does not walk when the
  click misses). Its missile (`echoingstrike`, missiles.txt) has velocity 24 and range 20
  frames: about 19 world units if velocity is units per second as walking is (walk 6, run 9);
  `STRIKE_REACH` starts at 15 and the host logs will say.
- **Sigil: Lethargy sits on a mouse button**: slot 6 (action 20) is bound to code 0x102. Codes
  from 0x100 are mouse buttons; the untouched key files bind 0x100 (action 59), 0x101 (Show
  Items' second key), 0x102, 0x103 and 0x104 (actions 39/40, the wheel) by default. Taken as
  the buttons beyond left and right in order: middle, mouse 4, mouse 5, wheel up, wheel down
  (X11 buttons 2, 8, 9, 4, 5). `input/keybindings.x11_name` now names them `Button2`…; the
  actuator presses a `Button…` name with XTest button events. Unverified until the first host
  log: if the sigil does not appear, the order is wrong.
- The sigil's radius is 7 units (skills.txt Param1) and it is cast at the cursor (Quick Cast).
- **Monster type flags** (`terror/tracker.py`): monster data byte +0x1A, 0x08 unique, 0x04
  champion, 0x02 super unique, 0x10 minion. Allies carry stat 172. `macros/world.py` reads the
  flags for every live monster now (one 0x58-byte read of the monster data per unit instead of
  the 4-byte owner read) and the alignment stat (three small reads), so `World.monsters` can be
  filtered for hostiles and leaders without the terror probe.
- **Line of sight** is the sub-tile grid the level guide already reads (`levels/model.Ground`):
  the blades fly over the ground, so a shot is clear when every sub-tile along the line is
  walkable. Unknown sub-tiles (no grid) count as clear; the monster's own tile is skipped.
- **Remembered monsters**: the terror tracker keeps every hostile seen this game at its last
  position (`positions`) and which are leaders (`leaders`); the level guide's rooms minus the
  tracker's `explored` bounds are the unexplored rooms.

### Design

`macros/sight.py` — pure geometry over `Ground`: `clear_shot(ground, start, end)` samples the
line every half unit; `firing_spots(ground, mob, reach)` are the points on rings around the
monster (radii reach-3 down to 4 units, 16 bearings) with footing and a clear shot, nearest to the
player first; `in_reach(ground, player, mob, reach)` is distance and a clear shot.

`macros/hunt.py` — one step: checks (game, panels, town, level map for this level), then

1. **in reach**: hostiles within `STRIKE_REACH` with a clear shot: attack the nearest (a leader
   before a plain monster). Sigil: Lethargy on a leader first unless cast at it within
   `SIGIL_SECONDS`; then Echoing Strike bursts (Shift+click on the monster) until it is gone
   or `BURST` casts were made. The cast animation (player mode in ACTING) is the evidence.
2. **seek**: the nearest wanted monster, live from memory or remembered by the tracker (KP_2:
   leaders; KP_3: any). The hop goes toward the nearest firing spot around it (or the monster
   itself when no grid is known there), through the teleport step's landing machinery with an
   ad-hoc `Target`.
3. **explore**: the nearest unexplored room's centre (rooms the player was never in or next to)
   as the target; "the level is explored" when none is left.

`macros/teleport.py` splits `step_toward` into the checks and `hop_toward(run, target, …)`, so
the hunt reuses the landing and the logs. The runner gains routines `hunt elites` and `hunt any`
(prefixes `hunt elites ` / `hunt any `), `request.py` kinds `hunt-elites` / `hunt-any`, niri
`KP_Down` and `KP_Next` (the keypad 2 and 3 without Num Lock, as KP_Left is the 4). The guide
gives `level()` (area, rooms, ground without a mark); the tracker gives `remembered(area)`.

### Steps

1. Monster flags and alignment in `world.py`; `hostiles`, `leaders` helpers. Tests on decoding.
2. `sight.py` with tests on a grid with a wall.
3. `hunt.py` quarry choice (in reach → seek → explore) with tests on the fake game.
4. The attack: mouse-button names in `keybindings`, `Actuator.tap` on buttons, Shift+click,
   evidence; fake game reacts (a sigil at the pointer, a strike kills what is under it).
5. Wiring: runner routines, service, `request.py`, niri, Makefile comment, plan.

### Status (2026-10-09, late evening): implemented, not yet pressed in the game

All five steps are in the tree. `world.monsters()` reads flags and alignment for every live monster
(tests build units with champion, minion, ally and owned flags). `sight.py` and `hunt.py` are
tested on the fake game: a monster in reach takes Shift+clicks until it dies; an elite gets the
sigil first and not again within `SIGIL_SECONDS`; a monster behind a one-sub-tile wall is not
struck but hopped around; nothing in reach hops onto a firing ring around the nearest elite (KP_2)
or monster (KP_3), remembered ones included; no quarry hops toward the nearest unexplored room;
an explored level stops with "the level is explored". The runner treats KP_2/KP_3 like KP_4 (the
same key queues one more step, any other cancels). The HUD card says what each press did.

To verify on the host, in this order: (1) KP_2 with a monster in reach — the log must show
"Echoing Strike at …" and the monster vanish; if "no attack seen after the click", Echoing Strike
is not the left-click skill, or Shift+click does not cast it; (2) an elite in reach — "Sigil:
Lethargy" first; if no sigil appears under it, the mouse-button order (0x102 = X11 button 9) is
wrong; (3) `STRIKE_REACH` (15): strikes that fall short mean the blades fly less than thought.
Nothing new is needed in the game's bindings; Num Lock on, as for KP_4.

### First host presses (2026-10-09, 20:07–20:18, River of Flame) and the fixes

- **Nothing was cast** (user: "it casts sigil and doesn't cast echoing strike"). The log agrees: four
  bursts of Shift+clicks on a Strangler at 12 units, an action animation after each, the monster
  never moved or died, the player's life untouched. The left button held the plain attack, not
  Echoing Strike. The user put Echoing Strike on `7`; the hunt now aims the pointer at the monster
  and taps the skill key (Quick Cast), as it does for the sigil. Without a key it falls back to the
  mouse button that holds the skill, read from the unit's skill list (+0x100, as d2go reads it):
  a right click, or Shift+left click; neither → "Echoing Strike is on no skill key and on neither
  mouse button (left Attack, right …)".
- **Metrics** (user: "we need some kind of debug metric, whether we're within killing range and if we're
  actually killing"): every step logs "hunt <mode>: N hostiles, M in reach (15 units, G grids),
  nearest <who> <life>, <d> away; left <skill>, right <skill>"; every strike logs the distance, the
  pointer and its window fraction, the mode seen after the key and the monster's life before and
  after (stats 6/7, now read with the alignment); the HUD says "<who>: 128/128 -> 40/128 after 3
  strikes" or "is down after 2 strikes". Each hop logs the character's position too.
- **"no way over the rooms"** (user: "it cannot navigate to the next monster", twice). Replayed from
  the 107 evidence records, the wall library and the probe's positions: the character stood on a
  tile whose centre is lava or wall edge (River of Flame corridors), so its tile was not landable
  and the potential had no value there, though the firing spot and the monster were fine.
  `Way.from_here` now takes the best landable tile within one hop when the own tile has none; both
  stuck positions get a 22–23-unit hop toward the firing spot.
- **Hops landing 18 and 23 units off their aim** with the pointer far from where it was put: the hand
  on the mouse between the aim and the key (POINTER_DRIFT allows 400 px). `Actuator.aim` now reads the
  pointer back after the quick move and moves again, up to three times, while it is more than
  AIM_TOLERANCE (25 px) off; the log says "the pointer was found at …; aiming again". Every aimed
  action (teleport, door click, sigil, strike) uses it. BURST is 3: the hand moved the mouse past
  the drift allowance during the 2.4-second bursts of four.

### One press, one fight (user, 2026-10-09 late evening)

"Try to kill mobs without continuously smashing the button if there are mobs in killing radius":
`Hunter.fight` loops while something stands in reach, the elite first, then the nearest, a burst of
BURST strikes per aim, up to FIGHT_SECONDS (60) per press, and says "Nothing left in reach: 2 down in
3 bursts" (or "Fight stopped after 60s"). The next press hops toward the next quarry as before. The
runner asks the hunter whether a fight is on: the hunt key then cancels (`fighting`), while during a
hop it still queues one more step. Other macro keys cancel as before.

### Teleport presses ignored (host, 20:26–20:27 on 2026-10-09, service started 20:25)

Every KP_5 press after the restart ended "the character did not move" with the staff at 69 charges
throughout, while a `7` press between them cast Echoing Strike (mode 10, the monster died). In the
20:16 session each KP_5 press also put Teleport on the right mouse button (the hunt line said "right
Teleport"); after the restart the right button stayed on Echoing Strike through every KP_5 press, so
the game never acted on the key. Num Lock is on (X indicator), key code 84 still gives KP_5, the key
file (20:11) still binds slot 14 to KP_5 and slot 13 to `7`, the player's states are those of the
working session. Not resolved offline: the "did not move" log line now adds the key pressed, the
slot table, the staff (charges, in hand), the player's mode and the right skill, and every skill
press logs its key and the mode before it.

### Watch after the step, and Death Mark (user, 2026-10-09 late)

The lost teleports were the game dropping the Teleport hotkey (user): the slot check catches it when
the slot table shows it, and the "did not move" line prints the table otherwise.

"KP_2/KP_3 act like before, but also kill mobs that come into radius later, until we cancel by moving
the mouse or casting": after its step (fight or hop) a hunt run stays in `Hunter.watch`: every
WATCH_POLL it looks for a hostile in reach and fights it; it ends when the pointer wanders more than
WATCH_DRIFT pixels, a key is held, the character moves or casts on its own (mode in ACTING), a panel
opens, WATCH_SECONDS pass, or the runner releases it: the hunt key pressed during a watch ends it and
the next step follows at once (runner `again` + `Hunter.release`). The HUD names why it ended.

"Include Death Mark `d`, not too often, on the strongest mob": in a fight, once per DEATH_MARK_SECONDS
(8), Death Mark (skill 375, slot 2, `d`) goes on the strongest monster in reach — an elite, else the
most life, else the nearest — pointer on its body, then the key. Skipped when the skill is in no
slot. The strike key is resolved before any cast, so a missing Echoing Strike key stops the fight
before the mark or the sigil.

### Exploring by the way, not by distance (host, 20:49 on 2026-10-09, Chaos Sanctuary entrance)

Every press ended "no way over the rooms to the unexplored part of the level": the five unexplored
rooms nearest the entrance walkway as the crow flies are lava, with no landable tile a hop away, so
each had no way, and the corridor's rooms further off were never tried. `Hunter.explore` now builds
one potential from the character's own tile (`teleport.Way` with the character as the mark, which
makes its tile landable whatever its centre is) and takes the unexplored room with the cheapest
landable tile, that tile being the hop's mark. One Way build per press (~90 ms) instead of one per
candidate room. The log says which room, at which tile, how many tiles by the way.

### Walk the short way (user, 2026-10-09 late)

"For a very short distance in hunt we can walk instead of teleporting": a firing spot within
WALK_UNITS (10, as NEAR_WARP) over clear ground (sight.clear_shot from the character to the spot) is
clicked, and the character walking is the evidence (`walk_to`); a wall between keeps the teleport.
The HUD says "Walking 8 toward the monster 19 (11)".

### Attack mode on KP_3, seeking on KP_2 (user, 2026-10-09 late: "still quite clunky")

The step-then-watch design is gone. KP_3 toggles **attack mode** (`Hunter.attack_mode`, runner
`ATTACK`): a run that lives until cancelled, looking every POLL for a hostile in reach and fighting
it (the same fight: Death Mark on the strongest, sigil under an elite, strike bursts). The player's
mouse and their own moves never end it: the actuator's drift allowance is lifted for the run, and a
cast seen while the macro is idle counts as the player's attack only when no teleport jump
(JUMP_UNITS within JUMP_SECONDS) follows. It ends on KP_3 again, on Win+X, on the player's attack
("Attack mode off: you attacked"), or after MISSES_IN_A_ROW fights that stopped (the mouse pulled off
the aim, a held key, a missing strike key). Town, panels and menus are waited through. KP_4 and KP_2
during attack mode pause it: the runner cancels the attack run with the step `pending`, runs the step,
and restarts the mode after ("Attack mode paused", then "Attack mode on").

KP_2 (`Hunter.seek`) only moves: onto the nearest firing spot around the nearest unique, champion or
super unique, live or remembered, by a walk when within WALK_UNITS over clear ground, else by a
teleport hop; with none known, toward the unexplored room nearest by the way. An elite already in
reach is named ("… is in reach (KP_3 turns attack mode on)"). Plain monsters are never sought.

### Attack mode on the host, 21:17 and 21:20 on 2026-10-09: "it doesn't try to kill mobs"

The log (runs/alt-d/20261009T181617Z): KP_3 at 21:17:31, "Attack mode off: you attacked" at 21:17:36
with no fight between, and the same at 21:17:44/46, while the player only moved toward the monsters
(a teleport or a sigil of their own: the cast was seen, the jump test did not clear it). The next KP_3
then said "Attack mode off": the run had returned, not aborted, and the runner's toggle stayed on, so
the key had to be pressed twice. In the Chaos Sanctuary at 21:20 a fight did start, and four in a row
stopped "the mouse is being moved": `Actuator.aim` re-checks the pointer three times, which the hand
on the mouse fails every time; one strike got through (mode after 10, the monster hit), then "you
attacked" again at 21:20:15.

Changes: the player's own casts never end attack mode (the jump test, JUMP_UNITS/JUMP_SECONDS and
`Hunter.teleported` are gone: only KP_3, Win+X or MISSES_IN_A_ROW end it); `Actuator.steady`, off
for the mode, makes `aim` one move with the key right after, no re-check (the hop's re-aim stays for
KP_4/KP_2); a key the player holds makes the mode wait instead of counting a stopped fight; the
runner clears the toggle when the mode's run returns on its own.

Later the same night, from writing the mode's logic out in words: `sight.clear_shot` sampled the
line from the character's own position, so a character on a tile the grids call unwalkable (River of
Flame's lava edges, the earlier "no way over the rooms" stall) had no clear shot at anything and the
mode sat silent: the MARGIN now applies at both ends. And the mode said nothing while idle; it now
logs every IDLE_LOG_SECONDS what it sees ("idle: N hostiles, none in reach; nearest … away, shot
clear/blocked") so a silent mode can be read in the log.

### The burst cast the player's way (user, 2026-10-09 night)

"It doesn't cast with the same speed as when I just hold the mouse button and aim": a tap per cast
with a wait for the animation between and pauses around the aim was slower than the game's own
rate. `Hunter.attack` now holds the input for the burst (`Actuator.hold`: pressed once, kept down,
the pointer aimed again and again meanwhile, released at the end), so the game casts at its rate as
with the player's held button; the right mouse button is the input when it holds Echoing Strike
(the player's own way, right skill 388 in the log), the key or Shift+left click otherwise. A game
that casts once per press gets the input released and pressed again after RETAP_SECONDS idle. The
burst ends when the monster is gone, BURST_CASTS cast animations were told apart, or BURST_SECONDS
passed (chained casts may show no neutral frame between them). "The daggers move into the focal
point: draw a straight line to the mob and aim behind it so all daggers hit": the aim is the ground
AIM_BEYOND units past the monster on the line from the character (`Hunter.aim_beyond`), not the
monster's body. One log line per burst: casts seen, seconds, distance, the aim point, the pointer,
life before and after.

### Next: a recorded, replayable, scored auto-attack (2026-10-09 night)

The user wants a real implementation: record how they play (casts, aims, movement, rotation,
rooms, monsters, missiles), replay recorded situations in a simulator with an Echoing Strike
that behaves like the game's, score policies by effective DPS, and only then build an attack
mode that does not get in the way of moving and beats manual play in the game. The staged plan
with success criteria is `inventory_tracking/combat/plan.md`; the hunt code here becomes its
policy's client at the end.

### Win+X in the lobby (2026-10-10 15:15)

Attack mode's loop waited whenever the world had no player, the lobby included, so the mode's run
stayed alive after the game was left and Win+X in the lobby only cancelled it (and, before 15:00,
ran no macro after). Now the mode ends on its own when the world is not in a game ("attack mode
off: the game was left") and Win+X there starts the macro at once; in a game Win+X ends the mode and
runs the macro after it (runner.py).

### Win+X in the lobby after a restart (2026-10-10 15:30)

The second cause, from the service logs: the three `make serve` starts of 15:09, 15:13 and 15:15
were made in the lobby and never attached ("Waiting for a character in game: unit table
unavailable", 0 signature candidates in every capture), and the hotkey loop starts only after the
attach, so no press was even read. The unit table is found by a code signature and D2R.exe's code
pages decrypt lazily: in the menus the signature's page is still encrypted. The table's RVA is a
constant of the build (0x1ead470, signature at 0x705a8, the same in the last 40 attachments), so
`tracking/reader.py` now remembers a successful scan per executable sha256 in
`runs/alt-d/unit-table.json` (seeded from those attachments) and attaches from it when the scan
finds nothing. Not verified against the live game from this session: the game process is not
visible from here.

### KP_2 turns attack mode on, KP_3 toggles, the fight is one held strike (2026-10-10 evening)

User: "KP_2 not enabling auto-attack mode, person stayed near mobs without attacking until I hit
KP_3 myself"; the log of 15:51 shows eight KP_2 presses answered "the elite is in reach (KP_3 turns
attack mode on)". Now KP_2 does its step and attack mode follows it (a step that stops, or finds the
elite already in reach, leaves the mode on all the same), and KP_3 toggles the mode on and off (the
morning's "never off" is withdrawn by the user). Win+X as before: ends the mode, runs the macro.

The fight itself changed the same day (combat/plan.md, the steer): one hold of the strike input
through the whole fight, the pointer on the line the combat policy picks (`combat/policy.py`, the one
the simulator scores; elite first by weight, the old nearest rule when no line is found), a look every
0.04 s. It yields to the player: a key down, the left button down, or the character walking or
running ends the fight ("Yielded (...)"), and the mode waits until they stand. After each fight the
card shows the last minute's points per second and kills per minute. `Hunter.attack` and
`aim_beyond` are gone; BURST_CASTS and READY_SECONDS with them.

### The door's own spot, and the walk-in log (2026-10-10 17:00, user: "the latest point of teleporting became even worse")

From the take frames of two Catacombs doors (levels 1 and 2, both stairs preset 294): the level card's
mark sits inside an 8 x 9 block of walls; the game walks a clicked character to one spot 3 units
"south" of the mark (+0.0, +3.0 world units both times) and the level changes there, not when the
character passes within 2 units of the mark on another side. The hops had landed 10 and 8 units off,
north and north-east of the block (the APPROACH ring spot nearest the character, not the open side),
and the walk round the block took 0.9 and 0.8 s.

- `teleport.Entries`: where the character stood when a door took it, relative to the mark, remembered
  per stairs preset and kind (`preset 294:stairs`; a preset is one orientation of the stairs, shared by
  every level that uses it) in `runs/macros/door-entries.json`, seeded with (0, +3) for preset 294.
  A last position more than ENTRY_MAX (6) from the mark is not a door's spot and is not kept.
- With a remembered spot KP_4's last hop lands on it (inside WARP_TILES of the mark), and a press
  within ENTRY_NEAR (4) of it clicks the door; a press nearer the mark than NEAR_WARP but off the spot
  hops onto the spot first instead of walking round. A door with no spot yet behaves as before and
  teaches its spot on the first walk in.
- The log the user asked for: every hop toward a door says where the mark is, the remembered spot and
  how far from the mark it aims; every walk in says the mark, the start, and at the level change the
  seconds, the units walked, the last position and its offset from the mark ("Macro: door ...").

Untested in the game as of this note. If a door's remembered spot is wrong for a level (another
orientation under the same preset), the walk's log line shows the new offset and it replaces the old.

### The run of 17:12 (2026-10-10): the first door still off, a sigil stopped fights

- Door 1 was stairs preset 292, not the 294 that had been seeded, so its spot was "not known yet":
  the hop landed 7.1 from the mark and the walk took 0.52 s over 8.3 units, ending at +0.2, +2.8 from
  the mark (the same spot as preset 294's). Door 2 (preset 291) took the click at once from 6.4 away,
  at -5.0, +4.0 from the mark, without a step. Presets 291, 292 and 294 are the same block of walls
  with the mark in its east column and a notch three wide open to the "south"; both spots lie about 3
  units from the notch's mouth. So a spot learned on a level now also stands for every other stairs
  preset of that level (`Entries.level_key`, looked up after the preset's own), and the file is seeded
  for presets 291-294 and levels 35 and 36.
- "the fight stopped (the elite ... is out of view)" four times in a row: the sigil's own check, which
  the fix for the focal point had left. An elite off the screen now gets no sigil for a second and
  the fight goes on.
- KP_2 walked 3-4 units toward an elite 19-21 away and broke off the fight attack mode was in ("the
  character did not move" 1.6 s later, twice). An elite within the blades' reach (22.1) with a clear
  shot is now "in reach" for KP_2, and attack mode engages at that same reach instead of 20.

### The main weapons for fights and for leaving (user, 2026-10-10 evening)

User: swap to the main weapon before Save and Exit; fight with the main weapon (more skill levels,
more damage) and use the other set only to teleport; keep it dynamic, since Teleport will come from
Enigma later and the other set will then be the prebuff one.

- `routines.CHARACTERS` now gives a `Loadout` per character: `prebuff` (the set the buffs are cast
  with) and `battle` (the main set). Both are Heart of the Oak + Spirit for CybergrindAA today; when
  Enigma comes only this table changes. What casts Teleport was already read from the game
  (`take_teleport`: a worn staff with charges is swapped in, else the skill is cast as it is).
- `leave_game` takes the main set before Escape (`take_battle_weapons`); a swap that does not come is
  logged and the exit goes on.
- Attack mode takes the main set before each fight (`Hunter.main_weapons`, "Main weapons for the
  fight"): a hop leaves the staff's set in hand and the fights after it were cast with it. The next
  hop swaps the staff back in. A swap that fails is not asked for again for 5 s; a character not in
  the table, or hands that cannot be read, are left alone. Cost: one swap (about 0.3 s) per change
  between hopping and fighting.

### The run of 17:25 (2026-10-10): doors instant, swaps dropped

- Both doors: the last hop aimed 3.0 from the mark (the remembered spot), the click took in 0.19 s and
  0.20 s with nothing walked. The entry memory works for the Catacombs' stairs.
- The swap to the main weapons cost more than it gave on level 1: standing 63% of the frames with a
  target (29% the run before), 2452 points per combat second (3644). Two causes in the log:
  1. The game dropped swaps pressed 0.05-0.4 s after a cast or a landing, though the character read as
     free: five of them, each waited on for 1.2 s ("the main weapons are not in hand after a swap",
     "the Teleport staff in hand: not seen in 1.2s", which also lost the KP_2 step). `swap_until`
     (routines.py) now presses again when nothing shows in 0.5 s, up to three times, for the main set,
     the prebuff set and the staff alike.
  2. In a chain of KP_2 presses every hop was followed by a swap to the main set and the next by a swap
     back. The main set is now taken only once attack mode has run MAIN_AFTER (1 s) since the last
     step: a fight begun earlier is fought with what is held and stops for the swap at that time.
- "no cast seen after the right click" stopped a fight whose first 0.8 s went to Death Mark and two
  sigils: the clock for the first strike now starts after them.

### The player's move before any strike; the main weapons for tough packs only (user, 2026-10-10 evening)

User: "movement in auto-attack mode is quite clunky: I need to click several times to move, because
echoing strike prevents the movement ... some kind of priority queue, to make movement have priority
over strikes, but keep strikes working when no movement is queued"; and the swap to the main weapons
"only for tougher packs".

Why the clicks were lost: the game takes no click while a cast runs, and a click (60-120 ms) is over
before the cast is. The mode looked at the left button every 40 or 100 ms, let the strike go when it
saw it, and struck again at the next look because the button was up and the character stood: the
move never started. And while the hand took the pointer to the spot, the fight pulled it back to the
strike line (the pointer "strayed"), so a click could land on the line.

- **A pending move** (`hunt.Move`, one slot: the latest press). The left button is looked at every
  10 ms (`Hunter.nap`, `sense`), in fights and between them. A press lets the strike input go at
  once and nothing is cast while the move is pending (`serve_move`). The move is done when the
  character has gone (walk or run mode, or a unit from where it stood) and stands again with the
  button up. If instead the character stands free with the button up for 0.12 s and has gone nowhere,
  the cast swallowed the click: the macro makes it again where the player made it (the pointer put
  there and back), twice at most, 0.3 s apart; after 2 s with nothing to show the move is dropped and
  the strikes go on. Whatever was under the pointer gets the click: ground, an item, a door.
- **The hand's pointer is left alone**: a pointer that strayed from where the macro put it is not
  aimed again until it has rested 0.2 s.
- **Main weapons**: swapped in only for a tough pack: an elite in reach, or 40,000 life points
  between the monsters in reach (`TOUGH_POINTS`; a Catacombs pack of ten is about 15,000-30,000, a
  Chaos Sanctuary pack of eight knights about 50,000), and still only a second after the last step.

Untested in the game as of this note. To watch for: a replayed click on a monster walks the
character into melee (the left button holds Attack), as the player's own click there would.

### The run of 17:45 (2026-10-10): the first run with the pending move

- Doors instant again (0.22 s). The main weapons were asked for four times, each for an elite.
- Five fights ended "Yielded (a move was asked for)" and two clicks were made again for the player.
  One click was still lost (take 144525, 49.45 s in): it was made while the mode was inside Death Mark
  and then the swap to the main weapons, about 1.2 s in which nothing looked at the button; the player
  clicked again. Every pause of attack mode now looks at the button (`attack_mode` wraps the pace's
  sleep: `watchful`), and the macro's own clicks are not taken for the player's (`Actuator.tap`
  counts its buttons as held by itself).
- Nine of eleven swaps took a second press, half a second each: the first, pressed right behind a
  cast, was dropped. `routines.settle` now waits for the character to have stood free 0.2 s before
  the first press.
- `combat compare`: standing with a target 21% / 35% / 23% on levels 1-3, 3224 / 5965 / 8798 points
  per combat second (the run before: 22% / 21% / 25%, 2822 / 2289 / 4381).

### The run of 17:53 (2026-10-10): clicks made again that the game had taken

- Swaps: 17 presses for about 14 swaps (nine of eleven had needed two the run before): the 0.2 s
  settle works. The door: 0.21 s, nothing walked.
- Eleven clicks were made again for the player, and four moves "showed nothing after 2 clicks", all
  four within five seconds on level 3 after the fight: clicks made while the character stood free
  (loot beside it), which the game had taken and which moved nothing; each was clicked twice more at
  the same spot. A click is now made again only when it was pressed while a cast ran or the strike was
  held (`Move.swallowed`, from `Hunter.casting`); a click made while the character stood free is the
  game's, and the strikes wait MOVE_QUIET (0.4 s) for a walk to show and then go on.

### Cleanup round (2026-10-10 evening, while the next run was prepared)

No behaviour change meant. The module texts of `hunt.py` and `teleport.py` now say what the code
does; the dated history of each rule stays here and is no longer repeated in comments. Dead code
removed: `hunt.ready_to_act`, `sim/situation.kills_by_type`, `mechanics/tables.monster_name`. In
`teleport.py` the "can a hop land on the door's remembered spot" check, written out twice, is one
function (`entry_in_view`, with `landable`), and `step_toward` is one decision (walk in or hop).
No test was removed: the ones that looked alike test different layers (the policy alone, the
simulator, the live fight). Full suite 2707 passed.

### The runs of 18:01 and 18:05 (2026-10-10, before the cleanup round): key taps and swipes

Log `runs/alt-d/20261010T145910Z-ab96ed7c`, takes `150139Z-36`, `150254Z-37`, `150546Z-36`,
`150604Z-37`. Doors: four of four in 0.19-0.22 s with no walk. Standing with a target 17-24%
(level 3 at 17% and 19%, the lowest so far), 5000-6100 points per combat second. Five clicks made
again, none "showed nothing".

- **The player's own skill key broke the fight.** In `150254Z-37` the player tapped `s` (Blade Warp,
  skill 390) twenty times; ten fights in a row ended "Yielded (a key is held)" after 0.3-1.5 s, each
  letting the strike go and starting over about half a second later, once as a stopped fight ("a key
  was pressed", the macro's own aim meeting the key). Now a key held while the strike is held is no
  yield: the strike stays down, as the player's own hand would hold it, and the macro's aims, marks
  and sigils wait for the release (`Hunter.fight`, `moving(keys=False)`). Before a fight has begun a
  held key still makes the mode wait.
- **A swipe stopped two steps** ("the mouse was moved": the pointer 600 and 870 px off the aim 100 ms
  after it, one KP_4 and one KP_2). `teleport.POINTER_DRIFT` is unlimited now: the hand never stops a
  step; `Actuator.aim` makes the aim again (three tries) as it already did for smaller drifts.
- **Save and Exit stopped "a key was pressed"** (18:06:54): Win was held 2 s around Win+X (the macro
  waits for its release), let go, and pressed again 0.4 s after the macro began, which cancels it by
  design. Not changed.
- Seen, not changed: with several lines of near-equal worth the choice flips between them every
  0.2-0.5 s and the pointer swings across the screen (18:03:23-26). A candidate for a small
  preference for the line already aimed along, to be tried in the simulator first.

Tests: `test_a_key_the_player_taps_during_a_fight_leaves_the_strike_held`,
`test_a_swipe_of_the_hand_across_the_screen_does_not_stop_the_step`. Full suite 2710 passed.
