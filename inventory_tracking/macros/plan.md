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
