# Macros: Win+X prebuff for Pindleskin runs

Plan, 2026-10-06. First version implemented the same day (see Status); not yet run in the game. Companion to the
[input design](../input/design.md), which this package builds on.

## Current contract (2026-10-10)
What the code does today, per the module docstrings of the macro modules and input/compositor.py.
Where a dated note below disagrees, those docstrings and this section win. The bindings are in
input/compositor.py; no key is named here.

The actions
- The macro request (routines.py). Runs the routine for where the character stands: in Nihlathak's
  Temple, the Frigid Highlands, the Bloody Foothills, the Fortress just after act 3, or Catacombs
  Level 4 with Andariel dead, it leaves the game and creates the next one; in the lobby it creates
  the next game; then it prebuffs. Anywhere else it prebuffs where the character stands.
- The teleport step (teleport.py). One hop, or one walk into a door, toward the first mark on the
  level card. A hop lands on footing in view that leaves the shortest way to the mark. A door is
  clicked, never teleported onto. Teleport comes from a staff with charges, or from a skill slot.
- The seek step (hunt.py, `Hunter.seek`). One step toward the nearest unique, champion or super
  unique, live or remembered: a walk when the firing spot is close over clear ground, else a
  teleport hop. With none known, toward the nearest unexplored room. Attack mode is on after it.
- The attack mode toggle (hunt.py, `Hunter.attack_mode`). Starts or stops a run that fights what is
  in reach, the elite first. The strike is one held input for the fight, with the pointer on the
  line the combat policy picks (combat/policy.py). Death Mark goes on the strongest monster in
  reach; Sigil: Lethargy goes under an elite.
- The pickup step (pickup.py). The first rule that applies: pick up the nearest valuable ground
  item; pick up a healing or full rejuvenation potion when the belt is short of that kind; with the
  belt full and life low, drink one and pick up one; otherwise a seek step. During attack mode it
  waits for the fight to end.

Rules that hold across actions
- Every transition of the runner (a request, a run ending and what follows it, shutdown) is made
  under one lock: a run and a request never both start a successor, and shutdown is final
  (runner.py). A cancel is the exception type `Cancelled`, not a message text.
- One window shape (`view.Viewport`) decides what a hop may span, where a landing may be and where a
  cast may be aimed: the way is planned for the window the hop is made in (2026-10-10 night).
- What is fought is within the blades' reach with a clear shot (REACH, 22 units); a firing spot the
  seek step goes to is within STRIKE_REACH (20). A hop of the way spans at most REACH_TILES and
  lands in view: both hold.
- A request cancels the running action, except a step's own request during that step, which queues
  one more step (runner.py). The teleport and seek steps pause attack mode for their step, then
  resume it; the pickup step waits for the fight to end.
- Attack mode ends only on its own toggle, the macro request, the game being left, or
  MISSES_IN_A_ROW fights stopped one after another (hunt.py). The player's moves, casts and mouse
  use do not end it. A key the player holds makes it wait before a fight, but does not end a fight
  under way (2026-10-10, 18:01).
- The player's move comes before any strike: a left click releases the strike and blocks it until
  the character has gone and stands again. A click the game may have swallowed during a cast is made
  again for the player (hunt.py, 2026-10-10 evening).
- The main weapon set is swapped in only for a tough pack (hunt.py): life alone, 40,000 life points
  of monsters in reach (TOUGH_POINTS), an elite's life counted ELITE_LIFE (2) times (2026-10-10,
  18:14).
- Prebuff and demon slots: beside the bound demon there are two demon slots, and an active Consume
  holds one. A prebuff consumes the standing Defiler where it stands, then summons its replacement,
  and Consume is cast on every prebuff (2026-10-06; 2026-10-10, 18:47). A hostile monster next to a
  Defiler is not a crowd: Consume cannot take it.
- A hop must gain way: the landing takes the most off the way, and a hop taking less than MIN_GAIN
  (3 units) is not made (2026-10-09, 18:02). The way counts only hops the view can show (2026-10-10,
  19:19).
- The pointer is checked against where the macro left it; Actuator.aim makes the aim again (three
  tries). The teleport step's allowance is unlimited (teleport.POINTER_DRIFT, 2026-10-10, 18:01).
- Every action first checks focus and that no key is physically held (actuator.py). A step goes on
  only on evidence from the game; pauses never stand in for it (engine.py).

Unresolved
- Review finding 2: the simulator scores the fight's aim (combat/controller.py `LiveAim`), not the
  rest of the fight: holds, retaps, the weapon swap, marks and sigils chosen live and the yield to a
  click are not replayed against recorded input.
- Review finding 7: the fakes under the hunt's tests advance the clock only through sleeps, so the
  tests show the order of actions, not how long a memory read or a decision keeps a click waiting.
- Pointer swinging: with near-equal lines the choice flips every 0.2 to 0.5 s (2026-10-10, 18:01).
  Preferring the line already aimed along is proposed, not tried.
- A Defiler summoned before Consume and left standing: whether it costs the buff is unknown
  (2026-10-10, 18:47). Open question to the user (19:19): is that state acceptable, or must the
  standing Defiler be summoned after the Consume?
- "loaded game: not seen in 40s" after creating cyber21 (2026-10-10, 19:22); the cause is not in the
  notes.
- Pickup: the belt cell of a belt item (its path x) is unconfirmed, and what the hover record holds
  with nothing under the pointer is not known (2026-10-10, 18:46 to 18:54).

Everything below is the dated history: the first plan, then notes in order. Later notes supersede
earlier ones.

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

## (historical) Design

*Superseded 2026-10-10: see Current contract. The Status of 2026-10-06 ("Differences from the
design above") has the routines as plain functions of a `Run` in `routines.py`, not a package of
step objects.*

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

### (historical) Engine

*Superseded by the Status of 2026-10-06 and the engine.py docstring: a routine is a plain function
of a `Run` that calls `run.expect`, not a list of step objects.*

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

*Partly superseded: the bullet "Prebuff is a goal, not a fixed sequence" (a standing Defiler is
consumed or kept) is replaced by the 2026-10-06 "Consume is always cast" note and the 2026-10-10
prebuff note on demon slots. See Current contract.*

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

## (historical) Win+T: one step toward the level card's mark (2026-10-09)

*Superseded 2026-10-10: see Current contract. The binding changed, the door's walk distance went
from 20 units to 10 (`NEAR_WARP`, 2026-10-09 evening), and the drift allowance changed later. The
hop and door rules are otherwise as written, and the later notes give the values now in use.*

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

### (historical) Pressed again and again (host, 2026-10-09 17:44–17:46)

*Superseded in part: the 60-pixel drift allowance became 400 px (2026-10-09 evening), then
unlimited (2026-10-10, 18:01).*

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

### (historical) Landings (host, 2026-10-09 17:53, Durance): aimed against landed

*Superseded 2026-10-09, 18:02: the landing is searched over the whole view, not only along the
route's first leg (see the next section).*

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

### (historical) The whole view, not the leg (host, 2026-10-09 18:02)

*Superseded 2026-10-09, 18:18: the way is a potential over landable tiles (`Way`). The way to go
from route points described here was replaced (see Tile potential below).*

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

### (historical) A potential, not straight lines (host, 2026-10-09 18:10, Durance 2 game cyber5)

*Superseded 2026-10-09, 18:18: the room potential (`route.distances`) was removed again. See Tile
potential below.*

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

## (historical) Hunting: KP_2 (elites) and KP_3 (any mob), 2026-10-09 evening

*Superseded in part: from 2026-10-09 late, the attack mode toggle runs its own loop, and the seek
step goes toward uniques, champions and super uniques only. See the Attack mode sections below and
Current contract.*

User request: two more keys built on the teleport step. Both first kill what stands in reach; when
nothing does, KP_2 teleports toward the nearest unique, champion or super unique, KP_3 toward the
nearest monster of any kind; when none is known, either teleports toward the nearest unexplored
room, where more will show. Kills are Echoing Strike (skill 388), with Sigil: Lethargy (393)
under elites first. One press is one step, as with KP_4: an attack burst, or one hop. The same
key during a step queues one more; any other macro key cancels.

### (historical) What was found (installed game, key file and sources, 2026-10-09)

*Superseded 2026-10-09, see First host presses below: Echoing Strike was not on the left click on
the host. It is cast by its skill key or by the mouse button that holds it.*

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

### (historical) Design

*Superseded in part, 2026-10-09 late and 2026-10-10 (Attack mode sections below and Current
contract): the attack mode toggle is a run, the seek step goes toward uniques, champions and super
uniques, and the strike is one held input.*

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

### (historical) Status (2026-10-09, late evening): implemented, not yet pressed in the game

*Superseded 2026-10-09 late (see Attack mode on KP_3 below): the seek step only moves, and the
attack mode toggle runs its own loop. The runner no longer treats the seek step like the teleport
step.*

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

### (historical) One press, one fight (user, 2026-10-09 late evening)

*Superseded 2026-10-10 evening ("KP_2 turns attack mode on"): the fight is one held strike on the
combat policy's line, not bursts per aim.*

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

### (historical) Watch after the step, and Death Mark (user, 2026-10-09 late)

*Superseded 2026-10-09 late (see Attack mode on KP_3 below): the watch after a step is gone, and
attack mode runs until its toggle. The Death Mark rule still holds (hunt.py).*

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

### (historical) Attack mode on KP_3, seeking on KP_2 (user, 2026-10-09 late: "still quite clunky")

*Superseded in part: the player's own casts no longer end attack mode (section "Attack mode on the
host", 2026-10-09), and the seek step turns attack mode on (2026-10-10 evening).*

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

### (historical) The burst cast the player's way (user, 2026-10-09 night)

*Superseded 2026-10-10 evening ("KP_2 turns attack mode on"): `Hunter.attack` and `aim_beyond` are
gone. The fight is one held strike on the combat policy's line.*

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

### (historical) The main weapons for fights and for leaving (user, 2026-10-10 evening)

*Superseded in part: attack mode no longer takes the main set before each fight. It is swapped in
only for a tough pack ("The player's move before any strike" and "The run of 18:14").*

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

*Partly superseded: "tough" was an elite in reach or 40,000 life points. In "The run of 18:14" it
became life alone (TOUGH_POINTS 40,000, with an elite's life counted ELITE_LIFE times).*

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

### The run of 18:14 (2026-10-10): a swap for every elite pack

Log `runs/alt-d/20261010T151330Z-4372106b`, takes `151436Z-36` (standing 23%, 5316 points/s) and
`151510Z-37` (31%, 4630). The door in 0.22 s; three clicks made again, one each. No key yields and
no step stopped by the mouse (the fixes for both were live).

- **Seven swaps to the main weapons in 80 s**, one after nearly every KP_2 stop: any elite made a
  pack "tough". Each time the fight ran 0.9 s with the staff, stopped, swapped (0.25-0.75 s), and was
  over 0.2-1.5 s later (once with nothing left to strike); the next KP_2 swapped the staff back.
  Now `tough` is life alone: `TOUGH_POINTS` (40,000) in reach, an elite's points counted
  `ELITE_LIFE` (2, the Hell multiplier) times. A Catacombs pack is 15,000-30,000.
- **"a key was pressed" 1.8 s into Win+X**, in the lobby while the next game was being created (the
  take had closed, so the key is not on record). The stop now names the key code.

Full suite 2710 passed.

### The run of 18:21 (2026-10-10): the life-only tough rule live

Log `runs/alt-d/20261010T152009Z-eadc9465`, takes `152100Z-35` (standing 19%, 3983 points/s: the
lowest standing share on level 1 so far, 21-92% before), `152148Z-36` (22%, 4167), `152239Z-37`
(27%, 7879). Doors 0.21 and 0.17 s. Four swaps to the main weapons in three levels (seven in two the
run before). Four clicks made again (one twice).

- Two fights stopped for the main weapons and no swap followed: the pack was tough when the fight
  began and no longer a second later. `fight` now asks `tough` again when the swap is due and fights
  on when the answer is no.
- The Win+X stop in the lobby names its key now: code 133, Super_L, down again about 1.5 s after the
  press that started the macro (third run in a row). User, same evening: intentional, Win
  alone is how they stop the next game from being created. Nothing to change.

Full suite 2711 passed.

### (historical) KP_1: pick up, else KP_4 (user, 2026-10-10 evening)

*Superseded 2026-10-10, 18:41 (see "Action names" below): with nothing to pick up the step is a
seek step, not a teleport step.*

Asked for: one key for the non-battle action, one-off per press: pick up a valuable item (the ones
already marked), walking or teleporting by distance; pick up a potion when the belt is missing one;
drink and pick up when life is missing and the belt is full; never walk half a map for a potion;
during a fight, wait until the pack is dead; with nothing to pick up, act as KP_4.

Built (`macros/pickup.py`, module text has the rules and constants):

- `GameMemory.loot` (world.py) reads, in the macro's own thread: the drops the loot marks show
  (the same functions and settings as loot/watch.py: runes from `rune_minimum`, `material_marks`,
  bases of uniques from `unique_minimum`), healing and rejuvenation potions on the ground, the
  character's belt by cell and its life.
- `choose`: nearest valuable; else a potion within `POTION_UNITS` (25) of a kind the belt is short
  of (`column_shortages`), rejuvenation first; else, belt full and life under `DRINK_BELOW` (70%), a
  potion of the kind lying near is drunk from the hotkey row (`INPUT.column_keys`) and the one on
  the ground picked up; else `step_toward`.
- `approach` / `take`: within `PICK_UNITS` (20) and in view the drop's ground is clicked (then 10
  classic pixels above and below, `ITEM_AIMS`); further off, up to `HOPS` (4) teleports toward it by
  the level map first. The item leaving the ground is the proof; every try is logged ("Macro:
  picked up ...", "... still on the ground after the click ...").
- Runner: routine `pickup`, a step key like KP_4 (the same key during its step queues one more).
  During attack mode it does not cancel the mode: `Hunter.after_fight` is set and the mode pauses
  itself the next time nothing is in reach (`step_aside`), the pickup runs, the mode resumes.
- Key: niri `KP_End` (keypad 1 by raw keysym) -> `request.py pickup` -> `pickup <monotonic>`.

Unconfirmed on the host: that a left click on the ground under an item picks it up with Show Items
on (labels may sit elsewhere and take the click); the belt cell read (path x of a belt item, as
tracking/state.py reads it; the "belt short (rejuvenation, healing)" in the "Macro: pickup:" log
line shows what was read); item positions on the ground (loot/ground.py's own caveat). The first
host presses should be read against those log lines.

Tests: `test_pickup.py` (11), `test_kp_1_during_attack_mode_waits_for_the_fight_and_the_mode_resumes_after`,
`test_a_step_waiting_for_the_fight_gets_its_turn_when_nothing_is_left_in_reach`. Full suite 2724 passed.

### Action names, the pickup step's fallback, and its first host presses (2026-10-10, 18:41 and after)

**Names (user: "use names for actions instead of hotkeys in code/comments, we're going to revamp
hotkeys").** Code, comments and test names now speak of the macro request, the teleport step, the
seek step, the attack mode toggle and the pickup step. The keys are named in one file,
`input/compositor.py` (`BINDS`, and `STEP_KEYS`, the key names a step binding may leave down, which
the runner allows). The Makefile's help line keeps the keys, being the user's reference. The dated
notes above keep the key names they were written with: KP_4 = teleport step, KP_2 = seek step,
KP_3 = attack mode toggle, KP_1 = pickup step, Win+X = macro request.

**The pickup step with nothing to pick up is a seek step** (user), not a teleport step: toward the
next elite, attack mode on after it (`pick_up(..., otherwise)`, the runner passes `Hunter.seek`).

**First host presses of the pickup step (18:41, log `runs/alt-d/20261010T154020Z-e8b28c67`): nothing
picked up.** A Large Charm at (22709, 6597): the read was right (5 drops, the position, life
1813/1813, belt full), the walk was made, and six clicks left it on the ground. Where the character
ended after each click against where the click was meant to land: 9 to 21 classic pixels below the
item every time (the aims were 0, -10 and +10 down). So a click lands about 14 pixels lower than
`ground_fraction` says for a spot this near, and the item was never under the pointer. Changed:
`ITEM_AIMS` starts 14 pixels above the item's ground and goes round that (seven aims); a miss is
called as soon as the character has stood 0.4 s after the click (a miss took 1.9-3.2 s); each try
logs whether the game holds a (item type, unit id) pair anywhere in its data while the pointer is on
the aim ("hover [...]"), to find a hover record the click could wait for. Still unconfirmed that a
click on the item itself, rather than on its label, picks it up.

**A seek step that clicked under the character's feet** (18:38:02, log `...153209Z-8cf6b9de`:
"Walking 1 toward the elite", "the character did not move"): the firing spot was 0.6 units from the
character while the shot from its exact place read blocked. A firing spot nearer than `MOVED` is
now "in reach: attack mode takes it".

That run (takes `153249Z-35` to `153825Z-37`, two games): standing 15-26%, 3350-7418 points/s,
doors 0.15-0.21 s. Full suite 2725 passed.

### A prebuff in the middle of a level (host, 18:47-18:48 on 2026-10-10; user: "consume stopped working")

Log `runs/alt-d/20261010T154652Z-2795d203`, take `154734Z-36` (the Defilers' modes per frame).
The macro request among monsters: the standing Defiler was "crowded" by hostile monsters (classes
361, 135), another was summoned, crowded again, three in a row, and the press stopped with "Consume
was not pressed". A second press 5 s later summoned two more before it consumed one.

What the take shows, and the user's rule for it: beside the bound demon the character has two demon
slots, and an active Consume holds one. Each Defiler summoned with both taken ended the oldest: the
first extra one the Consume in force (cast at the start of the game), the later ones the oldest
Defiler (its mode goes to 0, then 12, the frame the new one appears). The first press therefore left
the character with two Defilers and no Consume.

Fix: a hostile monster is not a bystander (`routines.bystanders`): Consume cannot take it. Only the
character's own units (allied or owned: the bound demon) and monsters whose stats could not be read
make a Defiler crowded. In a level the standing Defiler is now consumed where it stands and the one
that stays out is summoned after, the order of a new game.

Not settled: the second press ended with the Consume read as active and one older Defiler standing,
and the user saw no buff after it. Nothing was summoned afterwards in the take. Whether a Defiler
older than the Consume matters is unknown; with the fix that state should not arise in a level.

Test: `test_hostile_monsters_around_the_defiler_do_not_make_it_crowded`.

### The pickup step picks up (host, 18:46-18:54 on 2026-10-10), and the hover record

Logs `runs/alt-d/20261010T154652Z-2795d203` and `...155224Z-c6fddb5e`. With the aims 14 pixels
higher, four of four items were picked up: a Large Charm (2.9 away), two Western Worldstone Shards
(5.1 and 16.5 away) at the first aim, 0.01-0.6 s after the click; a Flawless Skull at the second
aim, after a first click from which the character neither walked nor picked it up (attack mode's
last cast was ending). About forty presses with nothing to pick up went on as seek steps.

The whole-data search for (item type, unit id) under the pointer found the same single address on
all five clicks, two games and three levels: image RVA `0x1E010A4` (`world.HOVER_RVA`,
`GameMemory.hovered`). `take` now looks before it clicks: an aim is clicked only when the record
names the item, twice if the first click takes nothing; when no aim shows the item, or without the
record, every aim is clicked as before. The 13 MB search per click is gone from the step.
Unknown: what the record holds with nothing under the pointer (the log line "under the pointer
(type, id)" on each click shows it).

The belt read "short (0, 0)" on every press and potions lay about each time: consistent with a
full belt, not yet seen with a gap.

### "We're not moving anywhere" (host, 19:19 on 2026-10-10, Catacombs 1)

Log `runs/alt-d/20261010T161751Z-b673644a`: from 19:19:06 on, twenty-two seek steps in a row (some
through the pickup step) stopped with "no footing in view brings the character nearer to the elite
122", the character at (22667.5, 6636.5), the firing spot 45 units east at (22712.6, 6638.1).

Replayed from the take's `level.json` (`runs/combat/20261010T161836Z-35`): between the two lies 42
units of ground nobody can stand on. The potential (`teleport.Way`) said 9.4 tiles to go, straight
across, by a hop onto tile (4537, 1328), 21 units straight down the screen from the character. The
view ends at the skill bar 18 units down (23 up, 22 to a side): that tile is never in view from
there, so no landing took anything off the way and every press stopped. The potential counted
`REACH_TILES` (five tiles) every way.

Fix: the potential's hops are those the view shows (`hop_in_view`, for a 16:9 window, half a tile of
slack for where on its tile the character stands). On the same data the way from that spot is 14.2
tiles and four landings in a row bring the character to the firing spot, round the gap. A mark the
view-shaped hops cannot reach at all now stops with "no way over the rooms" at once.

Test: `test_the_potential_plans_no_hop_the_view_cannot_show`.

The same log, other things seen (19:17-19:23):

- The pickup step took a healing potion with the belt one short ("belt short (0, 1)", "(0, 0)" after):
  the belt read and the potion rule work on the host. Two clicks at the first aim took nothing though
  the hover record named the potion (the character stood 0.7 from it and shuffled); the second aim
  took it.
- "the Defiler is crowded by class 361" is the bound demon (monstats 361, megademon2, a Pit Lord), not
  a hostile: it was the crowd in four of the five lines of the 18:48 prebuff too (one was a Banished,
  class 135, which the hostile rule now leaves out). So a prebuff with the demon near still summons
  replacements and ends with the Consume cast and a Defiler older than it standing. Open question to
  the user: is that state good, or must the standing Defiler be summoned after the Consume?
- "loaded game: not seen in 40s" after Creating cyber21 (19:22): the game did not come up in time.

### The teleport step stuck 16 units from a door (host, 19:29 on 2026-10-10, Catacombs 1)

Log `runs/alt-d/20261010T162744Z-78ffd146`: sixteen teleport steps in a row stopped with "no footing
in view brings the character nearer to Next level", the character at (22762, 6586), the door marked
at (22772.5, 6597.5), its remembered entry at (22773.5, 6600.5).

Replayed from `runs/combat/20261010T162810Z-35/level.json`: the entry was drawn at 0.8407 of the
window's height, a hair below the view's 0.84, so the landing fell back on the spots beside the door
and took the one nearest the character. That one, (4554.9, 1318.4) in tiles, has footing but lies on
a tile whose centre is the wall the stairs sit in: the way gives it no cost (infinite), the landing
came out as "no gain", and nothing else was tried. `landing` now drops every spot that does not take
`MIN_GAIN` off the way before it chooses, beside the door or not. On the same data: one hop to 7.4
from the mark, then the hop onto the entry.

Test: `test_a_spot_beside_the_door_the_way_does_not_count_is_not_the_landing`. Full suite 2730 passed.

### "We have jumped twice around the entrance" (user, 19:32 on 2026-10-10)

With the landing fix live (log `runs/alt-d/20261010T163147Z-b55e51ce`), both doors were taken, each
by a hop beside the door (5.7 and 6.5 from the mark), a second hop onto the remembered spot 3 from
it, then the click: three requests for the last ten units.

`step_toward` now clicks the door when the remembered spot is within `ENTRY_WALK` (9 units) over
ground known to be walkable all the way (`clear_walk`): the click walks those steps, as it did
before the spot was known, and the second hop is not made. With a wall on the line (the stairs'
own block, when the first hop lands on its far side) the hop onto the spot stays.

Tests: `test_a_remembered_spot_a_few_steps_off_over_open_ground_is_walked_to_by_the_click`,
`test_a_remembered_spot_behind_a_wall_is_still_hopped_onto`. Full suite 2732 passed.

### Only full rejuvenation potions (user, 19:37 on 2026-10-10)

Log `runs/alt-d/20261010T163615Z-baf2dbe0`: with the belt one rejuvenation short, two pickup steps
went for "a rejuvenation potion" (class 530, the plain one) and fourteen clicks took nothing; the
record of the unit under the pointer named a monster and an object, never the potion (it may be
hidden by the loot filter, which would leave nothing to click). The user wants full ones only.
`GameMemory.loot` now lists class 531 alone as a rejuvenation drop. Healing potions of every size
are still listed.

### The run of 19:39 (2026-10-10): clean, one swallowed walk click

Log `runs/alt-d/20261010T163858Z-335f235d`, takes `163953Z-35` (standing 15%, 3528 points/s),
`164040Z-36` (14%, 6062), `164132Z-37` (17%, 7551): the lowest standing shares of a whole game so
far. A full rejuvenation potion was picked up with the belt one short (plain ones no longer listed);
38 pickup steps with nothing to take went on as seek steps; both doors in 0.18-0.25 s; no step
stopped on footing.

One seek step stopped: "Walking 7 toward the elite", "the character did not move", right after
attack mode was paused in the middle of a fight. `hunt.walk_to` now waits for the character to be
free (`routines.settle`) and makes the click a second time if nothing moved. Test:
`test_a_walk_click_the_game_swallows_is_made_again`.

### The Forgotten Tower run of 20:05 (2026-10-10; user: "teleport accuracy in tower sub-par")

Log `runs/alt-d/20261010T170512Z-dc293596/probe.log`, Black Marsh to Tower Cellar 5.

- The hops are accurate: every teleport toward a door landed within 0.8 units of its aim (one 6.2).
  The time went at the doors. The stairs down in Tower Cellar 1, 2 and 3 (presets 143, 144, 146:
  'Crypt Next' W, E, N) each took the third aim, (-50, -45), after 1.4 s on (0, 0) and 1.4 s on
  (0, -45): 3.0 s a door against 0.5 s for a first-aim door. The tower's door in Black Marsh
  (preset 163) took the second, (0, -45). The Catacombs stairs take (0, 0) (41 of 41 in the logs).
- The aim that took a door was kept per area, in memory: each cellar level started over. It is now
  kept per preset like the entry spot (`AIMS`, `runs/macros/door-aims.json`), behind `KNOWN_AIMS`,
  the aims read from this log (preset 145, 'Crypt Next S', assumed like the other three).
- In Tower Cellar 5 the only mark is the stairs back up, and the step after arriving clicked them (the
  mouse moving stopped it). A step toward a 'previous' mark now stops with "the only way marked is
  back to …".
- The card: Black Marsh leads with the Forgotten Tower (`ExitsHandler.pois_first`), and a level
  without a handler lists its ways on before its ways back (the Forgotten Tower itself).

### The tower run of 20:12 (2026-10-10; user: "teleport locations are still off", potions, Win+X)

Log `runs/alt-d/20261010T171057Z-6dd75801/probe.log`, with `KNOWN_AIMS` live.

- The cellar stairs took the first click, (-50, -45), in 0.17 to 0.26 s on each of the four levels, twice
  with no step at all, from 1.1 and 5.6 units. So where the level changes is not always a spot the
  character is walked to: it may be where it stood. The door's entry is now where the character
  stood at the click when the first click took (a spot proven to work), else where the level
  changed, as before.
- The tower's door in Black Marsh: the hop landed on the remembered spot (-3.9, -0.6), a place the
  character had only walked through, and none of the four aims took in 5.5 s. The next press, from
  (0, -4) where the ground clicks had left the character, took (0, -45) in 0.28 s. Why the first
  press failed is not known: the log did not say what was under the pointer. Now each door click
  logs the unit under the pointer and where the character stands after a miss; an aim with a
  monster or an item under it (the mercenary and the summons land beside the character after a
  hop) is left for last; after all the aims the first is made once more from where the character
  ended up. The entry of preset 163 in `door-entries.json` was set by hand to (0, -4).
- UNCONFIRMED: what the hover record holds over a door (unit type 5?). The next log says; if it
  does, the aims can be looked at first and only the one on the door clicked, as pickup.take does.
- One hop right after arriving in Tower Cellar 1 did not move the character (20:12:49, 0.5 s after
  the door); the next press did. Not changed.
- Potions (user: "only super hp or full rejuv"): the pickup step went for smaller healing potions,
  which the loot filter hides, and 9 clicks took nothing (20:12, 20:13). `GameMemory.loot` lists
  class 606 alone as a healing drop (`SUPER_HEALING`).
- Win+X on Tower Cellar 5 with no live Countess (class 45 with the super unique flag) leaves the
  game, makes the next one and prebuffs, as on Andariel's level (`routines.run_ended`). As there,
  the request before she is in the unit table leaves too.
- The same door at 20:17 (same log): from (+5, +5), behind the tower, (0, -45) and (0, 0) missed and
  (-50, -45) took after a 22-unit walk round it; the level changed at (-2.6, 0). All three level
  changes were west of the mark ((-3.9, -0.6), (-3, -3), (-2.6, 0)): the way in is from there, and
  the one click that took at once was made from (0, -4). `door-aims.json` for preset 163 was set
  back to (0, -45), the aim of that click, by hand.

### The rest of the review: one lock, one window, the controller apart (2026-10-10 late night)

The detail and the scoreboard are in `combat/plan.md` under the same date. For the macros:

- **Runner.** Every transition is made under one lock, so a request arriving while a run hands
  over to its successor waits for the hand-over (a test slows it down; without the lock a teleport
  step started beside attack mode). A cancel is `Cancelled(Abort)`; the runner no longer reads the
  message text. Shutdown stays final.
- **Window.** `macros/view.py` `Viewport` is the one projection. `Way(target, view)` plans hops for
  the window they are made in and `way_for` keeps one potential per window; before, the way was
  planned for 16:9 whatever the window.
- **Fight.** The decisions are in `combat/controller.py` and the loop in `Hunter.fight` asks them:
  where to cast, whose the pointer is, the held input, the player's move. Three changes of
  behaviour, none seen in the game yet: a line is chosen by the focal point the pointer can reach
  (a monster low on the screen was scored with a focal point the aim then shortened); the idle
  hold is pressed again only after the look at the player's click; a re-press is not made when the
  game has lost the focus.
- **Pace.** `Pace.watched(look, every, clock)` is how attack mode sees a click during any pause;
  `pace.sleep` is no longer overwritten.
- **Consume.** The scan for the unit under the pointer runs only with `D2R_MACRO_RESEARCH` set.

To watch for in the next run: fights against monsters low on the screen (the line may differ), a
click during a fight in a game that casts once per press, and hops in a window that is not 16:9.

### The first run on the reworked code (20:56, 2026-10-10)

Run `20261010T175558Z-e84efc83`, cyber28: Catacombs 1 to 3 in 2 min 38 s from the game's creation to
Save and Exit, on the code of the note above (the lock, the window, the controller). No failed
macro, no fight stopped on an error, no "nothing in view to aim at"; the pickup step took a Grand
Charm and a Flawless Amethyst, the door of each level took its click 0.6 s after the walk began.

- **Two seek steps stopped "the mouse is being moved"** (20:57:35 and 20:58:20): three aims in 0.4 s,
  each found 500 to 1100 pixels off, the hand sweeping the mouse while the key was tapped. The
  hand has the length of a move (three to six steps and the pause after) to carry the pointer off.
  `Actuator.aim`'s last try is now `jump`: the pointer put there in one step and looked at at once.
  A test with a hand that moves the pointer during every pause passes on the third try.
- **"Shot blocked" at 4 to 9 units** (20:57:16 to 20:57:21, 46 hostiles, the character idle 5 s until
  two seek steps): replayed from the take, the monsters stood behind a closed door (object 64 at
  22650, 6630) and the wall beside it. The block is real. The first seek step's hop aimed at a
  firing spot inside the room and landed in the doorway; the second got in. Not changed.
- Fights log few "casts seen" (2 in 2.4 s with 13 down): the count is of the character leaving and
  entering a cast, and a held input chains casts without leaving. A log number only.

### A pile of potions: the one not wanted was taken (21:10, 2026-10-10)

Run `20261010T180707Z-06dd5189`; the user drank two healing potions and pressed the pickup step by
eight drops: it took a healing potion, then a full rejuvenation the belt had no room to want, then
the second healing potion, in 6 s. The log: no aim had the chosen potion under the pointer, so
every aim was clicked blind, and the record of the unit under the pointer named a different item at
each click (four ids): in a pile the game stacks the labels, and the clicks took whatever lay there.

- `pickup.take` knows what else lies there: another drop of the kind wanted under the pointer is
  clicked and counts (`alike`); an aim with a listed drop of another kind under it is never clicked,
  in the looking pass or the blind one (`others`). An item the list does not hold (gold, a plain
  item) does not stop a blind click, so a stale record cannot stop every aim.
- Nine more aims are looked at before any blind click (`PILE_AIMS`: up to 64 pixels above the
  ground and 30 to a side), where a stacked label may be. They are never clicked blind.
- One press now takes every potion the belt is short of, `PICKS` (4) at most, looking at the belt
  again after each; still one valuable a press and one drink a press.

Five tests on a scripted pile (a label shifted 44 pixels up behind an unwanted potion; a label that
cannot be found at all: the press gives up with nothing taken; another potion of the kind serving;
two potions in one press; one valuable a press). Not seen in the game yet. Still unknown: where the
game really puts a stacked label; the first run with a pile will show which aim found it.

### Attack mode on and nothing attacked: a door as a square (21:18, 2026-10-10)

Run `20261010T181433Z-e945ba1c`, Catacombs 3. A seek step landed at (22545.5, 9608.5), 1.5 units
before Andariel's closed door (object 47 at 22545, 9610), and for ten seconds the mode logged "none
in reach; nearest ... 4 away, shot blocked" with thirty hostiles round the character; the user's
press of the toggle turned the mode off, which is how they saw it had been on.

Replayed from the take: every shot from that spot was stopped by the door, also at monsters on the
character's own side of it. `Door.blocks` was a square of half the door's longer side plus one unit
each way: 9 x 9 units for this door of 7 x 1 sub-tiles. A door now blocks its footprint, one unit
longer at each end for the frame and half a unit thicker to each side (`Door.extent`: 4.5 x 1.0 for
this one). A test holds the recorded positions: clear at the two monsters on the character's side,
blocked at the two behind the door, clear past the door's end.

The note of 20:56 called the "shot blocked at 4 to 9 units" of that run real. For its first position
it was (a wall cell and the door between); for the second, 2.5 units from a 1 x 4 door, the square
(radius 3) held the character too, so part of that wait was this fault.

Also in this run, not changed: three stops on "the game lost the focus" (21:17:41 in a pickup,
21:18:03 twice at a fight's start, 0.1 s apart), each with the pointer near the window's left edge
(x 2049 and 2146; the window begins at 1920). The mode went on 0.3 s later each time. Cause not
known: the hand crossing to the other screen, or a window there taking the focus under the pointer.

### Every rune, the essences and the keys for the pickup step (2026-10-10 night)

User: "add essences/keys to valuable items, so we would pick them up", and "I'd like to pick up all
runes". The Pandemonium keys were valuable already (`loot/materials.py` `keys`, codes pk1 to pk3).
New: a group `essences` (codes tes, ceh, bet, fed, checked against the item bases: classes 669 to
672), on by default in `material_marks`, so the HUD points at them too; and
`pickup_rune_minimum = 'r01'` for the pickup step alone, while the HUD's rune marks stay at
`rune_minimum` (Io and up). Not seen in the game yet.

The game of 21:24 in the same log ran on the service started at 21:14, so before the door fix and
the pile fix: its "shot blocked" at 9 and 10 units and its two "lost the focus" stops (21:25:43,
pointer at x 2367) say nothing new.

### 2026-10-10 night: the pickup step takes rings and jewels

- User: pick up rings, jewels and all runes. Runes were already all taken (`pickup_rune_minimum`).
- `loot/materials.GROUPS` has `rings` (`rin`) and `jewels` (`jew`), codes checked against the bases;
  config `pickup_also` names them for the pickup step only, so the HUD's marks do not point at
  every ring. `world.loot` keeps one drop per unit (a unique ring is a ring and a marked unique).
- Not yet seen in the game.

### 2026-10-10 22:14 run: Worldstone Keep 2 to the Throne (the first run outside the Catacombs)

No take exists: `combat_areas` did not hold the Keep. It does now (128-131), so the next run records.

Changes from the run (user):
- **Hydras** (monstats hydra1-3, txt 351-353) are not hostiles (`hunt.HYDRAS`). The Council's fire
  heads never die; at 22:18:37 the fight held the strike on them for 11 s until attack mode was
  switched off, and the held strike kept the player from moving away.
- **Amulets** join `pickup_also` (group `amulets`, code `amu`).
- **Identified charms, rings, jewels and amulets on the ground are left alone**
  (`materials.APPRAISED`, `ground_materials(..., appraised)`): one read and dropped by the player
  was offered again. The HUD marks follow the same rule.
- **A drop no click picks up is given up** after `MISSED_AIMS` = 3 aims that had it under the
  pointer, and left alone for `SHUN_SECONDS` = 30. At 22:16:13 a Large Charm took 30 clicks in 21 s
  at 16 aims, the item under the pointer each time, the character walking to and past it; the
  player picked it up by hand 4 s after. Cause unknown (no take). Potions showed the same twice
  (22:15:33, 22:19:13): two clicks at (0, -14) walked to the potion, the click at (0, -24) took it.

Where the run stuck, from the log (not fixed here):
- "the level card is for another level" after both stairs (22:15:52, 22:17:07).
- 22:15:52: "Teleport: the character did not move" 10 s after arriving in Keep 3.
- 22:17:34: "Echoing Strike is on no skill key and on neither mouse button (right Teleport)", twice,
  then a swap: the fight found the teleport staff in hand.
- 22:15:17: a player's move "showed nothing after 2 clicks" (both swallowed by casts).
- Black Souls (txt 640, physical resistance 90): four fights in a row with 0 down at 22:15:28.
- Idle with hostiles "shot blocked" for 7 s (22:15:06) and 11 × 3 s lines on one monster 45-64 away
  (22:17:45, 22:19:35): attack mode does not move, so nothing happens until the player does.

### 2026-10-10 night: synthetic situations (five sub-agents)

`tests/inventory_tracking/scenarios/{revivers,threat,navigation,exits,loop}/`: situations as tests,
with what fails today marked `xfail(strict)` and the measured numbers in the reason (71 xfails in
all; the whole suite is 3163 passed). No production change came with them. Each directory has its
evidence pass over the logs and takes as a module. The proposals are in the session report; the
ones with the best ground are: build `Ground` once per landing (47-150 ms a hop), strike before
Death Mark and the sigil (0.3-0.7 s on 190 of 405 fight starts), wait for the new level's card
instead of stopping (15 stops in 116 exits), an immunity flag and a threat weight on the aim line,
and repositioning when a reviver cannot be hit.

### 2026-10-10 late night: the first three scenario proposals, Engorge, potion aims

User: do the first three proposals, step by step; then the requests from the second Worldstone run.

1. **One `Ground` per landing** (`teleport.Way.ground`, used by `landable`): was built for each of
   about 810 spots, 47-150 ms a hop. Three scenario xfails pass.
2. **The strike before Death Mark and the sigil** (`hunt.fight`, `FIRST_STRIKE_SECONDS`): they are
   cast under the held strike once a cast is out (or 0.3 s after the press). The first cast flies
   unmarked; a mark is not cast on a monster that died meanwhile. The eight tests that pinned the
   old order were rewritten. A race this exposed is closed in `actuator.hold`: the press-again skips
   the press when the player's left button is down by then (review.md, finding 7).
3. **The step waits for the new level's card** (`teleport.card_for`, up to `CARD_SECONDS` = 1.2):
   no "the level card is for another level" stop for a press made on arrival.
4. **Engorge** (skills.txt 379, on a corpse; user): under the held strike, on the nearest corpse in
   view within 20 units, when a demon of the character's is under 70% of its life (every 4 s at
   most) and every 15 s for the buff. `world.corpses` is its own walk, asked for only then. A demon
   is an allied or owned monster that is no hireling, or a Defiler. Unconfirmed in the game:
   whether the pointer on a corpse's ground selects it, and whether a used corpse still serves; the
   log line names the unit under the pointer for that.
5. **Potions are clicked at (0, -24) first** (`pickup.take`): 14 of 16 potions went there, and 10
   clicks at (0, -14) only walked the character to the potion.

Scenario xfails: 71 at the start, 63 now (two more passed with the door-click work of another
session the same night).

Open, from the 22:25 and 22:39 runs (both before these changes were loaded):
- An Ort Rune under the pointer with the character standing on it took none of 6 clicks (22:41,
  Tower Cellar), like the Large Charm of 22:16. A full inventory would explain both; the pickup
  step does not look at the inventory's room.
- Movement inside a fight (user: needed; today's is clunky under the held strike): not started.

### 2026-10-10 late night: the pickup step looks at the inventory's room

User: the inventory was full when the Ort Rune (22:41) and the Large Charm (22:16) took no click.
- `world.loot` reads the carried inventory's grid (`collection.capture.read_owner_grids`, grid 2)
  into `Loot.room`, and each drop's cells from `loot/data/sizes.json` (weapons, armor and misc.txt
  `invwidth`/`invheight`, built by `loot/build_sizes.py` from the install) into `Drop.size`.
- `pickup.choose` leaves a valuable with no free block of its size. With nothing else to pick up the
  press stops with "inventory full: no room for …" and does not go on to the seek step, which
  would teleport away from the drop (user); with a potion the belt wants it takes the potion and
  says the same. Unread rows: as before.
- Not yet seen in the game. A potion the belt has no column for would go to the inventory; the
  step only takes potions the belt is short of, so that case does not arise.
- Later (user): make room by itself, moving items into the Horadric Cube. Not started; it needs
  the cube's grid (grid 5 of the same reader), the inventory panel opened and items dragged.

### 2026-10-10 23:00: the tower's door in Black Marsh, and where a door takes a click

Logs `runs/alt-d/20261010T193944Z-5aaf616f` (22:43: 6.08 s at the door, five clicks) and
`...195222Z-84f7f137` (22:59: 3.32 s, three clicks; 22:56: 0.78 s, one click).

- The hover record holds a door as (5, unit id), and it keeps the last unit when the pointer is
  on nothing: at 22:59 it named the tower's door through two clicks that walked the character on
  the ground (the last hop's aim had been on the door). At 22:43 it held an object from town.
  `walk_into` now clicks an aim only with a tile in the record, looks twice, then clicks as before:
  that stops the clicks with a stale object or nothing, not those with a stale door.
- A door is a unit of type 5 in the unit table (slot 5), class = lvlwarp Id, with a static path
  like an object's. Read from the running game at 23:02: the tower's door (Id 10) at (15651, 5385),
  the mark at (15657.5, 5387.5); in the Forgotten Tower the way out (Id 11) at (10004, 8003) and
  the stairs down (Id 12) at (10002, 8013), mark (10002.5, 8012.5).
- lvlwarp.txt gives the box a door takes clicks in, classic pixels from that unit's place on
  screen (`levels/data/warp_boxes.json`). For the tower's door the box is 42 to 122 pixels above
  the mark and 74 left to 76 right of it: the aims 45 above were on its lower edge (5 of 9 took
  that day), the one on the tiles never took. For the stairs down in the tower the box holds the
  tiles, and (0, 0) took both times.
- `door_aims` now leads with the middle of the door's own box (`box_aim`, from `Run.warps`), then
  the aim learnt, then the old guesses. UNCONFIRMED in game: the next log's first click on each
  door says whether the box is right (the aim logged is the box's middle, e.g. (1, -82) at the tower).
- Not changed: a click that hits the door from its far side walks the character round for more
  than DOOR_SECONDS (1.2 s), and the next aim then interrupts the walk.

### 2026-10-10 23:08 run: the Tower to the Countess (user: too many mistakes at the end)

On the service of 23:08, before "inventory full" stopped the press. No take: the Tower was not in
`combat_areas` (Cellar 1-5 added now). What the log shows from Cellar 4 on:
- 23:11:28 Grand Charm, 4.2 s: 16 aims looked at from 16 away and none had it (2.4 s), a click made
  anyway with a corpse under the pointer walked the character up, the next aim took it. Now
  (`pickup.take`): from over `NEAR_UNITS` = 6 only the nearer aims are looked at, then the
  character walks up (`walk_up`), then every aim, and only then are aims clicked unseen.
- 23:11:32 "no room for Amulet", then the seek step teleported 18 units away from it. Fixed after
  that service was started (the press stops there).
- 23:11:50 a hop logged "landed … off by 24.0" 0.19 s after the key: the character was walking when
  the hop began, and the walk's movement was taken for the landing. Not fixed (teleport.py is being
  worked on by another session).
- 23:11:58 and 23:12:20, "Main weapons for the fight": two swaps in Cellar 5, each after a hop
  with the staff, 0.7 to 1.5 s without a strike.
- 23:12:12 Engorge 0.3 s after a Death Mark, at a corpse 1.7 from the character with the marked,
  live monster under the pointer. Now (`hunt.engorge`): the two nearest corpses are looked at and
  the key is pressed only when no live monster and no item label is under the pointer;
  `world.corpses` gives the unit ids for that. Of the 12 casts logged that evening 11 named a
  monster under the pointer and one an item; which of the 11 were the corpse is not known.
- Idle with hostiles 14 to 23 away and "shot blocked": 4 s at 23:12:07, 5 s at 23:12:15, 8 s at
  23:12:27. Attack mode stands; the player walked. This is the movement inside a fight still to do.

### Plan: a step inside the fight, asked for with the pickup key (2026-10-10 late night; not built)

User: plan movement inside a fight; the pickup key "feels too clunky when waiting to finish the
distant mob: if we're in a fight we can use it as a signal that we might reposition", which also
keeps the rule that the mode never gets in the way of the player's own moves.

So the mode still never moves on its own. One press of the pickup key while hostiles are near is
one step to a better place to stand; the strike goes on from there.

Measured on the 45 service logs of 2026-10-10 (scripts were scratch, numbers only):
- Attack mode idle with hostiles within 30 units and none in reach: 383 stretches, 1605 s in all,
  median 3 s, 84 of 6 s or more. The nearest was "shot blocked" on 630 of 862 such log lines.
- Of the time a fight's line went through some monster, 19% was through one 20 or more units away
  and 25% through one 16 to 20 away (the blades fly 22). 247 of 750 fights ended on a monster 18 or
  more away.
- The character runs 20 units a second (15 to 21, five runs of 0.5 s or more in the takes): a step
  of 8 units is 0.4 s, of 12 units 0.6 s, plus the cast that has to end first.
- How long a pickup press waited for its fight cannot be read: the request's arrival is not logged.

**What the pickup key does, by what is around (new rows marked):**

| Around the character | Today | Planned |
|---|---|---|
| Nothing hostile within `ENGAGE_UNITS` (30) | pick up, else a seek step | the same |
| A fight on (something in reach) | waits for the fight, then picks up, else seeks | **steps now** to a better stand if there is one; a valuable seen on the ground at the press is still picked up after the fight; no seek step follows |
| Hostiles near, none in reach (the idle stretches) | pick up, else a seek step toward an elite or an unexplored room | pick up; else **a step to the nearest spot with a shot** at them (a walk within `STEP_UNITS`, else a hop to a firing spot as the seek step does for an elite) |

A press with no better place says so on the card ("Standing well") and moves nothing.

**Stage 1, the decision (`combat/stance.py`, pure, scored by the simulator like the policy):**
`stand(seen, here, ground, doors) -> Stand | None`.
- Candidates: three rings of 16 bearings within `STEP_UNITS` (12) of the character, with footing
  and a straight walkable way from where it stands (no closed door on it).
- Worth of a candidate, cheap pass: the life-weighted hostiles it has in reach with a clear shot
  (`sight.in_reach`), an elite counted as the policy counts it. The best three then get the
  policy's own line worth from there (`LinePolicy.choose` on the observation moved to the spot; one
  asking costs up to 50 ms, so not all 48).
- Cost: `KEEP_AWAY` (6 units) from every hostile or the candidate is dropped; fewer hostiles within
  8 units breaks ties; then the shorter walk.
- A step is worth it when nothing is in reach from here and something is from there, or when the
  line there is worth `STEP_GAIN` (1.3) times the line here. Both numbers are to be set from the
  simulator, not guessed: the revivers scenarios (of the 5 the flagged sweep leaves short, a move
  to a plain firing spot mends 3) and the threat scenes that want a step (`a_step_out_of_the_pincer`,
  `low_life_in_melee_breaks_contact`).
- Budget: one decision under 250 ms, measured in scenarios/loop.

**Stage 2, the act (`Hunter.reposition`, runner):**
- Runner: a pickup request during attack mode sets `Hunter.step_asked` beside `after_fight`
  (today's wait). The fight loop and the idle loop read it at their next look.
- The step itself is the move machinery the mode already has for the player's own click
  (`controller.Move`, `serve`, `serve_move`): the strike is let go, the click is made on the spot
  once the cast has ended, twice at most, the strike is pressed again when the character stands.
  To check before building on it: that the macro's own click is not read back as a press of the
  player's (`sense`).
- The player's hand wins: a left press of theirs, a held key or a character already on the move
  drops the step.
- No teleport inside a fight while Teleport is on the staff: the swap there and back cost 0.7 to
  1.5 s without a strike in the Tower run. The mover is one function so a hop can replace the walk
  when Teleport is on the main weapons.
- Log, for the next run's reading: the request's arrival, the spot, what was in reach before and
  after, seconds from the press to the first cast from the new spot.

**Stage 3, on the host:** a press in a fight with a pack half behind a wall; a press with the last
monster 20 away; a press in an idle stretch with monsters round a corner; a press with a rune on
the ground mid-fight (step now, rune after); a press while walking by hand (nothing happens).

**Later, each on its own evidence:** a threat and reviver weight in the candidate's worth (the
tables are test data today: scenarios/revivers/revivers.json, scenarios/threat/threat_table.json);
a step away at low life; the step taken unasked in the idle stretches (a config switch, off).

Open, the user's call: whether a press in a fight keeps the pickup waiting when a valuable lies on
the ground (planned: yes), and whether the idle step should ever come unasked (planned: no).

### Stage 1 of the step inside the fight: the decision (2026-10-10 late night; user: yes to both open points)

Settled: a press in a fight steps now and the valuable seen at the press is still picked up after
the fight; the step never comes unasked.

Built: `combat/stance.py` `stand(seen, policy, barred, aimable) -> Stand | None`, with `no_footing`
(the walk's counterpart of `policy.walls`) and nothing wired to the game yet. Differences from the
plan above, each from a measurement:
- The cheap pass is `lined`, the best straight line from the spot, not a count of what is in reach:
  with a pack in the open every spot reaches all of it and the shortlist was the four nearest spots.
- `STEP_GAIN` is 2.0, not 1.3. Asked at every decision in the 17 reviver scenarios (harder than one
  press; a move costs the harness 1 s): 1.3 met 10 and made 3 fights slower in 16 moves, 1.5 met 11
  with 2 slower in 15 moves, 2.0 and 3.0 met 12 with none slower in 3 moves; today's aim meets 9.
  Mended by one step each: `shaman_behind_a_wall`, `shaman_out_of_reach`,
  `unraveler_raises_from_out_of_reach`. Not mended by a step alone: the closed cell, two revivers
  that raise each other, the `tough_` packs (scenarios/stance/test_revivers.py).
- The shortlist is 4 spots and the policy is given only what a blade from the spot can touch. One
  decision: 144 ms at the median (200 at most) with 30 hostiles in the open, 228 (334) with 60;
  one asking of the policy alone is 37 and 100 ms there. Stage 2 has the fight's own last choice
  for the line from here and need not ask again.
- No worth for the distance to a monster: the last plain monster of a fight took 0.8 s of its full
  life at 4 to 16 units and 0.9 s at 16 to 22 (402 fights, logs of 2026-10-10). So a press with one
  far monster in reach and a clear line answers "Standing well"; the wait of the pickup step for a
  far monster is not a matter of where the character stands. What made those waits long is not
  known (the request's arrival is not logged): stage 2 logs it.

Not looked at: the threat scenes (a step out of a pincer, low life): they want a worth for danger,
which is the later stage. Tests: combat/test_stance.py (9), scenarios/stance (19).

### Stage 2 of the step inside the fight: the pickup request takes it (2026-10-10 late night)

Built, not yet run in the game:
- Runner: a pickup request during attack mode sets `Hunter.step_asked` beside `after_fight`, and
  every accepted request is logged with its age and what ran ("Macro: request pickup, 12 ms old,
  while hunt any"): the wait of a press can be read from the next log.
- In a fight (`Hunter.asked_step`, at the fight's next look): with nothing to pick up
  (`pickup.choose` is None) the wait is dropped (`after_fight` cleared, the runner's pending step
  taken back through `unwait`), so no pickup and no seek step follow the fight. `better_stand`
  asks combat/stance.py; a stand found ends the fight with "Stepping to a better stand", and
  `take_step` walks there with `walk_to` (the seek step's walk: the cast is waited out, two clicks
  at most), unless the player moves: a press of theirs, a held key, a character already going. No
  stand: "Standing well: no better spot within 12", and the hold goes on. Not the `Move`/`serve`
  machinery the plan named: `walk_to` already does what was wanted of it, and the macro's own click
  is not read as the player's (`Actuator.button_held`).
- With nothing in reach the press is the pickup step as before, and its "else" is `Hunter.step`
  instead of the seek step: with hostiles within `ENGAGE_UNITS` (30) the better stand a walk away;
  else, none of them in reach, the nearest firing spot at the nearest (`go`, the seek step's own
  walk-or-hop, split out of `seek`); with something in reach and no better stand "Standing well";
  with none near the seek step.
- Logged per step: hostiles in reach and near, the spot, its line's worth against the line here,
  whether a pickup follows, and "first cast N s after the step".

Known gap: `policy.walls` stops no blade on a grid without a flight layer while `sight.clear_shot`
falls back to the walk bit there; the stand follows the policy. Level maps read since 2026-10-10
11:44 UTC have the layer.

To verify on the host: the five presses of stage 3 above. Tests: test_hunt.py (7 new),
test_runner.py (1 new).

### 2026-10-10 23:36: the tower run after the door boxes; clicks a cast swallowed

Log `runs/alt-d/20261010T202552Z-582f4e7d` (three tower runs, 23:26 to 23:36).

- The door's own box works: the tower's door in Black Marsh took the first click all three times
  ((1, -82), 0.21 to 0.28 s); the stairs into the cellar ((-26, -35)) 0.50 s three times; the stairs
  down ((-40, -39)) 11 of 13 first clicks, 0.23 to 0.43 s.
- The two misses (23:26:56 'Crypt Next N', 23:35:51 'Crypt Next W', 4.8 s each): attack mode fired
  an Echoing Strike 0.04 s and 0.7 s before the click; the character stood where it was 1.4 s
  later (the click was swallowed), the old aims (0, 0) and (0, -45) followed (both off this door's
  box) and (-50, -45) took. The same aim from the same spot of the same preset took in 0.23 s at 23:32.
- `walk_into` now waits the character free before a door click (`settle`, no longer than
  STILL_SECONDS) and makes a click again when nobody has moved 0.5 s after it (DOOR_CLICKS = 2),
  before any other aim. UNCONFIRMED in game.

### The step looks for the pack, not the next monster (2026-10-11; user: "didn't really advance into effective positioning")

User, after the Tower runs of 23:45-23:57: the step picked up monsters in one or two groups and spent
several seconds where moving close to the whole group would have cleared it in under a second;
reproduce the situations with sub-agents, bring a better strategy, test it.

The log of that service (20261010T204511Z): 48 presses with hostiles near. The first rule answered
"no better stand" 27 times of the 39 that have a take, 14 of them with at most half of the hostiles
within 30 units in reach, and its steps were 8 or 12 units, toward the next monster.

Two sub-agents (Haiku), files of their own under tests/inventory_tracking/scenarios/stance/:
- `build_fixtures.py`, `fixtures/` (39 moments, 270 KB): the frame of each logged press from its
  take, the hostiles, companions, doors, the grids within 60 units, and what the game then did.
- `harness.py`: the moment replayed frame by frame with the production aim and the emulated blades;
  a walk costs 0.36 s and its way at 20 units a second, a hop 1.5 s. Monsters stand still, which the
  recorded ones did not (they came to the character: the recorded fights ended in 3.0 s at the median
  with no step at all), so the seconds compare strategies with each other only.

The new decision, `combat/stance.py` `camp` (the module text has the rules): every place within 24
units with footing, in view, a way on foot of at most 1.4 times the straight line (round a corner:
the game finds it from one click), no hostile within 6; its worth is what the next 3 s of casting
take from there after the way, counted as best straight lines cast after cast, and up to as much
again for having all in reach dead early. A place 1.25 times where the character stands is gone to.
One decision took 5 ms at the median and 10 at most on the moments (the first rule: 144 to 200).

And the mode follows on (`Hunter.follow_on`): after a press, for 8 s, up to two more steps, each
only when nothing is in reach and hostiles are near, dropped by any move of the player's. This is
the one place the mode moves without a press of its own; `FOLLOW_STEPS = 0` turns it off.

Measured on the 39 moments, 15 s each, "cleared" = every hostile that stood within 30 units dead:

| strategy | cleared | seconds in all | points in the first 3 s |
|---|---|---|---|
| no step | 8 | 476 | 155k |
| the first rule | 26 | 255 | 316k |
| `camp`, one step | 29 | 226 | 397k |
| `camp` and the follow-on steps | 34 | 181 | 397k |
| the same with a teleport allowed | 36 | 162 | |

The best single walk found by trying every place also cleared 29, in 58 s where `camp` took 70 on
the 28 both cleared. The reviver scenarios: 12 of 17 met, none slower, as the first rule at 2.0.
Tried and dropped: counting each point by the seconds left when it is taken (as many cleared, 6% less
in the first 3 s); no step while what is in reach dies within two casts (one more moment cleared,
12% less in the first 3 s, one reviver scenario lost). Settings that changed the seconds by under
1%: CAMP_GAIN 1.1 to 1.5, KEEP_AWAY 4, CAMP_GRID 2, HORIZON 4 (HORIZON 2 cleared 26).

Known: at one moment (23:56:16) the step leaves two monsters in reach for a pack of more points 22
away. A teleport is not taken by the step (the decision can count one: `hop=True`); the press with
nothing in reach and no place on foot still hops to a firing spot as before (`Hunter.go`).

Tests: combat/test_stance.py (11), scenarios/stance (fixtures 118, harness 7, moments 42, revivers
19), test_hunt.py (3 new for the follow-on steps). Full suite 3398 passed.

### The sweep, and the comparisons in the viewer (2026-10-11 night; user: Black Marsh, "two minutes for seconds of work")

The run (service 20261010T204511Z, 00:24:56 to 00:25:56, still on the first rule; no take: Black
Marsh was not in `combat_areas`, it is now): 49 hostiles in the open, 59 kills in 60 s, 25 presses
of the pickup request and 5 of the teleport step, 12 fights of 29.3 s in all. The presses in a
fight were answered "no better stand" with 2 of 50, 1 of 32, 1 of 15 hostiles in reach: the fight
picked at the nearest pack's edge from 20 units, and the next pack waited for a press.

Cast cadence, from the blades' births in the 30 Tower takes of that night (363 casts): two casts
in a fight are 0.40 s apart at the median, and 28% of the gaps are over 0.9 s; with every gap at
0.36 s the casting would take 112 s of the 235 s it took. The 88 long gaps by what the log shows
between the casts: the mode paused for a step, 41 (52 s lost); Death Mark, 16 (18 s: about 1.1 s
a mark); nothing logged, 15 (18 s); a walk, 5; Engorge, 4; a sigil, 2. Not acted on yet; Death
Mark's second is the next thing to look at.

Built: the follow-on steps are a sweep (`Hunter.follow_on`, `sweep_to`, `toward`, and the look in
`fight` every `FOLLOW_CHECK` = 0.7 s). After a press of the pickup request the mode goes to a
better place whenever `camp` finds one, in a fight too, and with nothing in reach strides
(`STRIDE` = 16 units, to end `STAND_OFF` = 14 short) toward the nearest hostile within
`SWEEP_UNITS` = 60; until nothing hostile is that near, the player moves by hand, `FOLLOW_STEPS`
= 12 steps are taken or `FOLLOW_SECONDS` = 8 pass with no step. On foot only: in the open-field
scenario hops for strides over 12 units took as long as walking them.

Open field (scenarios/stance/test_open_field.py; five packs of ten of the Marsh's monsters over
90 units, standing still, six fields, 60 s): no step 3.5 kills of 50; the first rule pressed at
every decision 26.7; `camp` at every decision 38.8; the sweep all 50 in 32.6 s, of which 18 s are
its 49 casts.

The viewer (two Sonnet sub-agents): `scenarios/stance/export_viz.py` writes each recorded moment
as a viewer file with one run per strategy (`make stance-viz`, `make stance-view`); the harness's
`play` takes a `Trace`. combat_viewer reads two optional fields of a run, `player` (its own
character track) and `moves` (README, "The exported file"), draws each view's own character, the
moves and the trail, and names the left run by its label. `first_rule.py` keeps the first rule as
the reference run. Checked headless on the 39 files (no script error) and by one picture.

### Death Mark's second, Hex: Purge kept on, and the first runs with the sweep (2026-10-11, 01:00)

**Death Mark** (user: look at its cost). 101 marks in the takes of 2026-10-10 night: the casts before
and after a mark are 1.26 s apart at the median (0.40 s without one). The key goes down 0.15 s after
the last blades, the mark's own cast ends 0.42 s after the key, and then the character stood free
0.37 s at the median (0.08 at the first quartile, 0.62 at the ninth decile) before the next strike:
the hold's own press-again waits `RETAP_SECONDS` of idling. A sigil: 1.56 s between the casts.
- `Hunter.resume`: after a mark, a sigil, Engorge or Hex: Purge in a fight, the strike is let go
  and pressed again as soon as that cast shows (0.25 s at most), so the game has it waiting. The
  `pause('key')` after each of them is gone. Unconfirmed in the game: that a press made under
  another skill's cast is taken up when it ends (the input model says so for the strike's own).
- `worth_a_mark`: Death Mark makes one monster take more damage (skills.txt 375: 5 + 2 a level
  per cent, for 125 + 13 a level frames) and costs about two casts; only a monster with more than
  `MARK_CASTS` = 4 casts of life is marked. A plain monster of the Marsh or the Tower has a third
  to one cast of life, an elite of the Chaos Sanctuary 2.5: the marks of that night (monster 20 at
  109/128 and the like) would not be cast now.

**Hex: Purge** (user: "if we don't have active hex-purge we should activate it: without it there is
no damage"). `world.Player.hex_purge`: state 202 (states.txt `hexpurge`, the aurastate of skill
389), bit 10 of the state word tracking/consume.py already reads for state 208. Attack mode casts
it whenever that reads off: between fights at once, in a fight under the strike. A cast the state
does not show is tried once more, then every 60 s, with a warning in the log: the bit comes from
the tables and has not been seen to change in the game yet. The first run will show it (the log
line "Hex: Purge" at the start of a mode whose buff is on would be the sign it reads wrong).

**Black Marsh, 00:50:36, the first run with the sweep** (take 20261010T215036Z-6): 67.6 s, 88 kills,
47 casts (19 s of casting at 0.4 s each); two packs, each gone in 12 to 15 s. The time between
casts beyond 0.4 s: 20.5 s in 3 gaps where a key press paused the mode (14 s of them idle after the
sweep ended at 00:50:56: "7 hostiles, none in reach; nearest 55 away, shot blocked"), 7.6 s in 6
sweep walks, 3.5 s in 3 Death Marks, 7.6 s before the first cast and 9 s after the last.
**Tower Cellar 3, 00:48:39** (take 20261010T214839Z-23; user: not optimal, stuck at one moment):
- 00:48:53 "sweeping with 14 hostiles near and none in reach: no better place", the nearest 38 away
  behind a wall: the sweep ended and waited for a press.
- 00:48:59 the sweep left a fight with an elite (3 of 17 in reach) for a place 24 units and 1.6 s
  away worth 1.7 times; the player pressed the teleport step a second later.
- 00:49:01 between two teleport steps toward the stairs the sweep walked the character 25 units
  back toward two monsters: the moment it stuck.
Fixed: a teleport or seek request (and the macro) ends the sweep (`runner.request`); with nothing
in reach and no place or stride on foot, the sweep makes the seek step's own move onto a firing
spot at the nearest hostile (`Hunter.go`: a walk or a teleport hop; so the sweep can now spend
staff charges); a stride of under 8 units that ends behind a wall is not taken; a place the sweep
leaves a fight for unasked must be worth `SWEEP_GAIN` = 1.5 times (two of that run's six such
steps were for 1.27 and 1.34). Seen and left: with the staff in hand a chain of teleport steps
covers 26 units in 0.8 s, faster than the walk the open-field scenario assumed against it (1.5 s
with the swaps); the sweep still walks its strides.

### The sweep's strides are jumps (2026-10-11, 01:30; user: teleport hops or Blade Warp, Blade Warp preferred until Enigma)

`Hunter.toward` gives a stride as a jump of up to `JUMP_REACH` = 26 units (the longest of the full
length, three quarters and half that is in view and lands on footing) when `jump_by` names a skill
that needs no weapon swap, and `Hunter.jump` makes it (pointer on the ground there, the key, the
character seen elsewhere within 1.5 s):
1. Blade Warp (skills.txt 390, "hurl an astral weapon that teleports you to its impact": any melee
   weapon, mana 15, casting delay 20 frames; missile 707 Vel 36 for 20 frames, half again the
   strike's blades' 24, so about 33 units) when it is in a slot, its delay is over and no wall is on
   the blade's line;
2. else Teleport when the staff is in hand with charges, or it is the character's own skill;
3. else the walk of 16 as before.
A stride under 8 units is walked. A jump that moves nothing leaves that skill alone for 30 s. The
places `camp` finds are still walked to (they are often round a corner, and under 24 units).

Unconfirmed in the game, and what the first run's log lines ("Blade Warp aimed at … landed at …,
off by …, N s after the key") are for: where a Blade Warp aimed at open ground lands (the pointer,
the end of its range, or the first monster on its line), how long it takes, and whether the
strike's skill is back on the right button at once after it.

Tests: test_hunt.py (5 new). The fake game lands a Blade Warp on the pointer's ground.

### Black Marsh, 01:13: the movement was fighting itself (2026-10-11; user: attack stopped once, clunky moves and pickups, "something is wrong with our movement calculation")

The run (service of 01:04, so with the sweep, Hex: Purge and the mark rule, without the jumps; take
20261010T221305Z-6; 40 to 76 hostiles about). What the log shows:
- **Attack stopped**, 01:13:48-58 and 01:14:36-40: a step's walk said "the character did not move"
  after about 4 s (`walk_to`: two clicks, 1.5 s each, a second to settle), and the next look chose
  the same place again. Nothing was cast meanwhile; the user toggled the mode at 01:14:40.
- **Steps for little, back and forth**: with 6 to 10 hostiles in reach the mode left for places 9
  to 25 units away worth 1.29 to 1.48 times (south at 01:13:13 and :18, back north at :22, east at
  :26, west at :33), each 1 to 1.6 s of walking and about 1 s more to the first cast. The worth is
  counted with the monsters standing where they are; these came to the character.
- **Presses against the sweep**: the pickup request (25 presses in 40 s) with nothing to pick up
  paused the mode, walked a step of its own from wherever the sweep's walk had got to, or sought an
  elite and explored by teleport, and the sweep walked back.
- **Pickups**: a shard 14 away took 6 s (01:13:27), the character sent 18 units past it and back;
  a ring was passed twice (01:14:23). Both began under a walk: the aim was taken while the character
  ran, so the click landed off by the way it went meanwhile. Before the ring a hop was logged
  "landed, off by 28" 0.2 s after the key (the walk again), and a second hop followed.

Changed:
1. `step_walk`: a step's walk is one click and 0.7 s; not clicked with a live monster under the
   pointer (the left button attacks it). A place a step failed for is left alone 10 s; two failures
   in a row end the sweep.
2. A step of 8 units or more is a jump when the character can make one (`take_step`: `jump_by`;
   Blade Warp over a clear line, else Teleport without a swap), places `camp` finds included.
3. `SWEEP_GAIN` = 2.0, and a step asked for inside a fight needs it too.
4. `Hunter.step` (the pickup request with nothing to pick up): with hostiles within 60 units it
   starts the sweep and moves nothing itself; the mode takes the steps. No walk of its own, no
   seek or exploring while hostiles are that near.
5. `pickup.standing`: an aim is taken once the character stands (1.5 s at most).
6. `teleport.landed_from`: a hop has landed when the character has moved and stands, or is at the
   aim; a walk under way is not it. (teleport.py is also worked on by another session.)

Not yet in a run: the jumps (Blade Warp's landing is unconfirmed), and all of the above.

### Black Marsh, 01:26: the first run with the jumps (2026-10-11; take 20261010T222623Z-6)

153.5 s, 138 kills, 148 casts (59 s of casting at 0.4 s each), 67 presses of the pickup request.
- **Blade Warp lands on the pointer.** 31 jumps of 9.5 to 24 units: off by 1.0 at the median, 2.8 at
  most; 0.35 s and 45 units a second after the key (0.79 s at the median); the key 0.39 s after the
  decision, the first cast 0.17 s after the landing. 8 Teleports from the staff in hand: 0.31 s after
  the key. So a Blade Warp of 19 units is about 1.35 s from decision to cast, a Teleport about 0.9.
  Blade Warp stays first (it spends no charges; the staff went from 69 to 44 in the run).
- The steps inside a fight were for 2 to 16 times the worth, with 1 to 5 hostiles in reach; none
  failed for the walk ("No step" once: a monster under the pointer). Three pickups, each one click.
- **Stuck once, 01:26:37-49:** three seek steps in a row pressed the Teleport key and nothing came
  (staff in hand, 50 charges before and after, mode 1 and the right skill unchanged through each).
  The player then opened the skill list, pressed the key there, and the fourth step teleported to
  the same spot. The slot table in memory showed Teleport on its key all along. Not understood; the
  first teleport of that game, right after the first weapon swap. 14.8 s without a cast.
- Time between casts beyond 0.4 s: 53.2 s in 25 gaps with a Blade Warp in them (travel between
  packs: 2 to 30 hostiles alive at a time), 14.8 s the teleports that did nothing, 9.4 s a pickup.

Changed: `Hunter.jump` no longer waits for the character itself before the aim (`press_skill`
does) and takes a landing by `teleport.landed_from` (one Teleport jump was logged "landed, off by
33.7" under a walk); the stopped teleport step's message asks whether Teleport is still on its key.

### Teleport off its key, and the seek step's order (2026-10-11, 02:00; user)

**Teleport's key** (user: "teleport was broken because I exit game without switching to main hand:
detect that and ask to bind teleport, or bind automatically if possible"). The game drops Teleport
from its key when a game is left with the staff in hand; the slot table in memory still shows it.
- `runner.poll`: a game whose first readable look at the hands finds the staff in hand is said once
  on the card ("This game began with the staff in hand. Teleport is off its key: bind it again…"),
  unless a run is working.
- `teleport.hop_toward`: a key that moves nothing with the staff in hand and no charge spent stops
  the step with that same text (`LOST_KEY`), not "the character did not move".
- The macro's own Save and Exit takes the main weapons first already (`routines.leave_game`).
- Not bound automatically. What the player did at 01:26:43 (take 20261010T222623Z-6): a click on the
  right skill's button at (0.534, 0.951) of the window, the pointer on Teleport's icon at (0.5285,
  0.581), the key, a click on the button again. The icon's place moves with the skills the list
  holds and nothing read from memory says what is under the pointer there, so a wrong skill would
  take the key unseen. Possible on request, checked by a Teleport that then casts.

**The seek step for a Terror Zone** (user: "exploring somewhat random in different directions… kill
mobs to reach the breakpoint more efficiently"). A level's completion is the share of rooms loaded
times kills over hostiles seen (terror/chance.py): every room and every kill, elite or not.
- What the 01:13 log shows of the wandering: the pickup request's seek went to a remembered elite
  100 to 130 units off across unexplored rooms and plain packs, then explored from there, and the
  sweep walked between.
- `Hunter.seek(any_hostile=True)`, what the pickup request now asks for: the nearest known hostile
  of any kind (live, else remembered by the tracker), unless the nearest unexplored room is more
  than a room (40 units) nearer; else that room. The seek step proper still goes to elites first.
- `Hunter.frontier`: the unexplored room is the nearest by the way plus up to `TURN_TILES` = 8 for
  turning back from the last explore step's heading. Replayed on five recorded layouts (Black Marsh
  three times, Catacombs 2 twice; rooms marked as the tracker marks them, hops of 5 tiles): nearest
  alone 196 hops and 128 radians of turning, with the turn counted 200 hops and 68 radians. A count
  for rooms with explored neighbours ("finish the pocket") made it longer (202 to 206 hops) and
  was left out. So the order was not costing hops; the gain is fewer turns back.
- `Hunter.vanished`: a remembered monster that is not live within 25 units of where it was seen is
  not gone to again (elites too).

### What the strikes do nothing to is left alone (2026-10-11, 02:20; user: Far Oasis, the birds in the air)

User: "we've spent a lot of time hunting for birds that weren't on land, effectively immortal; keep
in mind if an enemy is in a similar state (it looks similar to hydras)". Take 20261010T224210Z-43
(175.9 s): 33 Undead Scavengers (monstats 111, MonType vulture), 32 killed, 73 hits. Of the hits 55
came while the bird walked, attacked or was struck (modes 2, 3, 4, 9: 1,797 frames) and 12 in modes
1 and 8 (8,807 frames): those two are the bird in the air. The log of that run has 48 lines laid
through a bird, most at 128/128.
- By type: `hostiles` leaves out a vulture (`VULTURES`: vulture1-5 of the tables) in mode 1 or 8.
  On the ground it is a hostile like any other.
- By what is seen, for whatever else is in such a state (something burrowed, an immune):
  `Hunter.untouched`. A monster whose life reads, that was the line's monster for `UNTOUCHED_CASTS`
  = 4 casts and shows the life it had, is no hostile for `UNTOUCHABLE_SECONDS` = 20: not fought,
  not swept toward, not sought (`Hunter.foes`), and said once on the card ("… takes no damage: left
  alone"). Then it is tried again. A monster whose life goes down at all starts the count anew.
The fake game now takes a point of the client's life off a monster that survives a hit (`unhurt`
names the ones it does not).

### Hops over a cliff: the far potential (2026-10-11, 02:40; user: Far Oasis, "not using tp to move between sections and trying to tp through the stairs")

Take 20261010T225724Z-43. The cliff between two plateaus is a band of no footing 5 tiles (25
units) wide. `Way` planned hops of at most `REACH_TILES` = 5 tiles, each counted in view from
anywhere on its two tiles (`hop_in_view`), so no hop spanned the band and the way went round by the
ramp: at 01:58:00 three hops north-east to it for a room 15 tiles east. Hops really made, all
logs: 2,282 landed, 229 of over 30 units, the longest 32.
- `Way(target, view, far=True)`: hops of up to `FAR_TILES` = 6, in view from tile centre to tile
  centre (`Viewport.hop_between`). `hop_toward` plans by it first; when it finds no landing from
  where the character stands, the old potential takes over for that target (`FAR_FAILED`).
- On the take's ground: west over the cliff 3 hops where the old way took 7; east over it the
  same 4 or 8 hops as before, by the ramp. The window shows 31 units up and to the left of the
  character and 26 down and to the right (VIEW ends at 0.84 of the height, above the skill bar),
  and going east the hop is 30 units down the screen. Whether the game takes a cast aimed lower
  than that beside the bar (the corners of a 2560-wide window show ground there) is not known: no
  hop was ever aimed below 0.84.
- The navigation scenarios: across-and-back 13 -> 11 hops, down-the-screen 8 -> 6 (the band 20
  units deep is hopped over), the Catacombs wall 21 units thick before the stairs room is hopped
  over (three strict xfails gone, with their two route-length ones); recorded-door-1725 12 -> 13
  hops (the far way fails once on it and the near way takes over), the others unchanged.
The sweep's own strides are not planned by this: a Blade Warp needs a clear line and a walk a way
on foot, so across a cliff the sweep still ends in `Hunter.go`, which is this hop.

### Teleports aimed beside the skill bar (2026-10-11, 03:00; user: "yes, let the macro try the corners")

`Viewport.hop_view`: a teleport may be aimed inside `VIEW` or, beside the skill bar, down to
`CORNER_BOTTOM` = 0.95 of the height where the aim is at least `HUD_HALF` = 0.56 window heights
from the middle (the bar taken as about 0.48: a guess with room to spare). `landing` and the far
potential (`hop_between`) use it; clicks on the ground and on items, and the sweep's jumps, stay
inside `VIEW`. With it the window shows 34 units down the screen instead of 26.
- On the Far Oasis take: east over the cliff from further south 3 hops (one of them aimed beside
  the bar) where it was 8 by the ramp.
- Unconfirmed in the game: that a cast aimed there is taken. The first hop aimed there that moves
  nothing turns the corners off for the session (`view.CORNERS`, the potentials planned with them
  forgotten) and stops with "nothing came of an aim beside the skill bar"; the next press is
  planned in the plain view. A lost Teleport key reads the same on such a hop, and shows as itself
  on the next.
- Under test the corners are off unless a test asks for them (the `corners` fixture): the pinned
  routes are the plain view's until a run has shown the game takes these aims. With them on, the
  navigation scenarios came out shorter still (around-the-void, recorded-door-1725, recorded-hunt-1848
  met their reference counts).

### The explore step follows a tour (2026-10-11, 03:30; user: "better with exploration now, but not perfect, too many back-and-forward iterations ... simulate what was the optimal way on this map")

The Far Oasis run of 02:16 (take `20261010T231634Z-43`, 96 rooms, 3.5 minutes): west along the middle,
south, east along the south, then eight hops back from the south-east corner to the middle, north-west,
east along the north, and at the end fourteen hops across the whole map for a strip of three rooms on
the west edge it had passed two rooms from at 02:17:11 (and 92 to 93 rooms "explored of 96": the rest
have no ground a teleport lands on, and the rule went only to rooms it could land in).
- The rule was not random any more, but it had no plan: the nearest unexplored room by the way, a turn
  counted as up to 8 tiles more. That leaves strips behind and comes back for them.
- `macros/tour.py` `tour`: the places to stand so that every unexplored room is seen (a place shows its
  room and the rooms touching it, as terror/tracker.py marks them), in a short order from where the
  character stands: a cover chosen greedily, ordered nearest-first, shortened by turning stretches
  around and moving, dropping and shifting stops. Straight lines between room centres; 1 to 4 ms for
  96 rooms. `Hunter.frontier` takes its first stop, by the stop's tile nearest by the way; planned anew
  at every explore step (fights move the character), the tour before kept unless the new one is
  `KEEP_TILES` = 8 shorter. The heading and `TURN_TILES` are gone.
- A room no teleport lands in is seen from a room beside it; a room no standable room touches is left.
- Replayed with nothing to fight (tests/inventory_tracking/scenarios/explore: the hunt's own choice,
  the teleport's own landing over the read ground; the old rule kept as `nearest_rule.py`), Far Oasis,
  hops and rooms seen of 96:

  | from                               | nearest room | tour     |
  | where the run came in              | 53, 90       | 46, 96   |
  | the south-east corner (02:18:06)   | 53, 94       | 43, 96   |
  | the north-west (02:18:45)          | 51, 89       | 42, 96   |

  (aims beside the skill bar on, as narrowed below; off, as under test: 62/89, 57/94, 52/89 against 49, 46, 49 with all
  96.) From each of the run's own explore decisions, with what it had seen by then, the tour had 3 to
  10 hops less left than the old rule in the first half, and as many in the last quarter.
- In the abstract (hops of 5.5 tiles in straight lines, four starts each on Far Oasis, Black Marsh,
  Catacombs 2 and Tower Cellar 3): nearest room 612 hops, tour 442.
- Not changed: a known hostile still goes before the tour when it is not a room's worth further than
  the first stop (`ROOM_UNITS`), and a fight takes the character where the monsters are.

### What the game took beside the skill bar (same run)

Four teleports were aimed beside the bar. Those 0.67, 0.72 and 0.85 window heights from the middle
(0.89 to 0.92 down) landed on the spot (one read 24 off because it was read before the character
arrived); the one at 0.63 (pointer 385 px from the left edge, 0.92 down) did nothing, and turned the
corners off for the rest of that session as written. `HUD_HALF` 0.56 -> 0.70: on 2560 x 1418 the outer
11% each side, and none in a 4:3 window.

### Frigid Highlands terrorized: doors, huts, and where the game is left (2026-10-11, 04:00; user: "too focused on killing doors; we don't target demon huts at all; win-x closed game ... only near eldritch")

The run of 02:40 (log `20261010T233922Z-b0852dea`; no combat take, level 111 was not recorded).
- Doors and walls. barricadedoor1/2 (432, 433), prisondoor (434), barricadewall1/2 (524, 525) are
  monsters to the client: killable, AI Idle, `neverCount` 1, no experience (monstats.txt of the
  installed game). 37 lines were aimed at them and 15 died; each counts 6,400 to 8,600 points to a
  line, as much as a Blunderbore. `terror.tracker.BARRICADES`: no hostile for the hunt (not fought,
  swept or sought toward) and kept with the tracker's allies (not counted as seen or killed, not
  remembered). The Barricade Tower (435, AI SiegeTower, no `neverCount`) stays a hostile.
- Huts. The Evil hut (528, AI GenericSpawner, spawns imp1, killable, 14,000 to 17,000 points) stood in
  `routines.TOWN_NPCS` by mistake, with neither `npc` nor `inTown` in the table, so it never was a
  hostile: the seek step went to its remembered place ("0 hostiles" 34 units from it) and fought the
  imps it made. 540 (ancientbarb1) stood there the same way. Both taken out. Three of the run's five
  huts died to lines aimed at other monsters, so the blades do strike them; whether a line can be
  aimed at one (its place may read as no ground) is not known: level 111 is now in `combat_areas`.
- The macro request. `run_ended` took the whole of levels 110 and 111 as the end of the Eldritch and
  Shenk run; the request at (3260, 4932), 550 units from where Eldritch died, left the game where a
  prebuff was meant. Now on those two levels only within `BOSS_UNITS` = 100 of where a super unique
  of the level was last seen this game (`ZoneTracker.supers`, through `Run.supers`); anywhere else
  it is the prebuff. Without the tracker the whole level counts, as before.

### The second Frigid Highlands run ran the old code; the staff ran dry (2026-10-11, 04:20)

The run of 02:48 to 02:57 is in the same log as the one before (`20261010T233922Z-b0852dea`, the
service started at 02:39): no "the first of N stops" line, 31 lines aimed at doors and walls, no
combat take. Nothing of the tour, the doors, the huts or the leave rule was in it.
- New in it: 36 teleports toward monsters and rooms took the staff from 69 charges to none by 02:55,
  and the next ten presses stopped with "the Teleport staff has no charges left".
- `Hunter.afoot`: with the charges gone the seek step (toward a monster's firing spot or the tour's
  next stop) is a Blade Warp of up to `JUMP_REACH` straight toward it over a clear line with footing,
  else one click's walk of `STRIDE`; with neither it stops and says so. Not a route: across a cliff
  or around a wall it stops, where the teleport would have hopped.

### The first Frigid Highlands run on the new code (2026-10-11, 04:40; log `20261010T235738Z-73c5e1c4`, take `20261010T235913Z-111`, 103 s)

- Doors and walls: no line aimed at one; four of the six seen ended at full life, two were grazed.
- Huts: a line was aimed at the Evil hut 2765459647 ("worth 6770", 16 away) and it died (128 -> 0 in
  the take), so a hut can be aimed at. The second hut was still alive when the game was left.
- The macro request was not pressed in the level: the leave rule is untested in the game.
- Walk steps refused for "a monster is under the pointer there": six in the run, five within three
  seconds at 03:00:01. The first two were aimed 2 and 3 units from the Defiler and the mercenary; the
  next had nothing alive within 8 units of the aim, so the game's name of the unit under the pointer
  seems to stay after the pointer has left it. `step_walk` now minds only monsters a click attacks
  (`attackable`: not the character's own, not an ally) that stand within `HOVER_UNITS` = 12 of the
  ground aimed at.
- A drink that did not take: at 03:00:04 the belt key went out 0.3 s after a teleport, the belt
  stayed full, and six clicks on two super healing potions took nothing in 6.4 s; the next press, the
  belt one short by then, took one in 0.44 s. `pickup.drink` looks at the belt after the key, presses
  once more after `DRINK_SECONDS` = 0.6, and then stops with "the potion on N was not drunk".
- One Blade Warp moved nothing (02:59:42, 1.6 s); one Death Mauler at 25/128 was left alone as taking
  no damage after four casts. Not looked into.

### Durance of Hate 2: 22 seconds on one spot (2026-10-11, 05:00; user: "a strange movement lag, when we were stuck and wasn't able to move anywhere")

Log `20261011T000449Z-44a7c9ed`, 03:09:13 to 03:09:34; no combat take (levels 100-102 were not
recorded; now in `combat_areas`).
- What the log and the terror probe show: at 03:09:12.26 the sweep clicked a walk of 23 units from
  (17821.5, 6819.5); the character got 5 units, to (17816, 6818), and stayed there in mode 3 (run)
  until 03:09:34. The Defiler stood within 2 units of it the whole time and the bound demon (361)
  5 to 6 units off on the line of the walk. The game went on: life rose 1098 -> 1813 at its usual
  rate, four monsters near died, the pets moved. Three teleport requests pressed the weapon swap six
  times with no swap ("the Teleport staff is not in hand after the swaps"). At 03:09:34 the character
  stood 9 units away in mode 1 and everything worked again.
- Why it stood is not known: the left button's state was not logged, and nothing recorded the level.
  The macro's own clicks are released in a `finally`; whether the game counted a button as down is
  not shown by anything kept.
- What the macro added to it: attack mode yields to "the character is on the move" (`RUN_MODES`),
  so for those 22 s it cast nothing and logged nothing, with 5 to 27 hostiles near.
- `Hunter.moving`: a character in a walking or running mode that has not moved `MOVED` units for
  `RUN_IN_PLACE` = 1.5 s is not on the move: said once ("runs in place at ... not waited for") and
  the mode fights, sweeps and steps again. A held key and the left button down are waited for as
  before, and what the mode waits for is now logged every `WAIT_LOG_SECONDS` = 3 with the place and
  the mode, so the next standstill names its reason.
- Unknown: whether a cast or a jump of the mode's frees the character. The next one will show it.
