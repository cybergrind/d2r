# Macros: Win+X prebuff for Pindleskin runs

Plan, 2026-10-06. Nothing here is implemented yet. Companion to the
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
