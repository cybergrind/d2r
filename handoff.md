# Inventory tracking handoff — 2026-09-21

Continue [inventory_tracking.md](inventory_tracking.md): health/belt reader → OSD →
observation-only potion decisions → automatic input. Process-access diagnostics,
bounded runtime capture and player/item research probes are implemented. HP and
belt locations have controlled validation, including column-1 use/gaps and
bottom/top placement, damage/healing, character selection and a new game.
A full process restart also passed; mixed columns, belt capacity and robust
local-player selection remain open. See [layout notes](inventory_tracking/layout_notes.md). Follow [development.md](development.md): Python/uv, meaningful
red/green TDD, separate low-level modules, shared logging, readable workflows.

## Current state — start here

This summary supersedes older research status and decisions recorded below.

- Run `uv run -m inventory_tracking.osd`; player and merc automation default on.
  Observation only: add `--no-player-heal --no-merc-heal`. Demo/once never send keys.
- Edit `inventory_tracking/healing_config.py`: player healing <65%, rejuvenation
  <40%; merc healing <55%, rejuvenation <20%. Player rejuvenation cooldown is
  1 second; all other potions require 3 seconds since the last delivered potion.
  The backend shares cooldown across recipients and OSD instances/restarts.
- Potion types are detected in all four bottom slots every sample. Player uses
  plain column keys; merc uses Shift+column. Rejuvenation has emergency priority,
  with healing fallback. Player is considered first. Higher potions across empty
  bottom slots cannot be used. Each recipient tracks consumption acknowledgement
  and suspends on timeout instead of retrying blindly.
- Shortage tracking is automatic per four-row column: bottom item defines type;
  if bottom is empty, lowest remaining item defines type; entirely empty means
  rejuvenation. Normal/full rejuvenations count together, as do healing tiers.
  Empty belt shows `juv 16`. Explicit CLI targets remain optional overrides.
- OSD is one transparent text line, 16px, centered 130 logical pixels above
  center. Player HP appears at/below 70%; merc HP strictly below 65%, controlled
  by `MERC_HEALTH_DISPLAY_BELOW_PERCENT` in `osd/state.py`. Dead merc still shows
  `merc dead`. Successful potion sends show a one-second debug message. Empty
  alerts unmap the window; stale/incomplete health and stock readings stay blank.
- User confirmed merc healing and debug feedback work in-game. Subsequent player,
  rejuvenation, dynamic-column/shortage and merc-visibility changes have pytest
  coverage but still need live verification. Injured merc HP remains approximate;
  persistent disagreement with the inventory panel is unresolved.
- Invalid old UI offsets are diagnostic research only. User explicitly authorized
  healing without in-game menu detection. Freshness, complete readings, death,
  exact Niri/X11 process focus, held-key and usable-belt checks remain active.
- Outstanding: exact merc HP source, live verification of the latest changes,
  belt capacities other than four rows, and robust multiplayer player selection.
- Latest checks: `uv run pytest tests -q` => **107 passed, 1 skipped**;
  `uv run ruff check inventory_tracking tests` and format check both pass.
  All tests are pytest under `tests/`, mirroring module layout. No commit made.

Older sections below preserve probe evidence and the development history; their
pending questions and previous defaults are superseded by this summary.

## Working setup

- User runs `uv run -m inventory_tracking probe` on the host. Agents remain sandboxed.
- Agent starts `uv run -m inventory_tracking watch --timeout 300` before the user
  runs the probe; poll the execution session to detect completion without a chat
  reply. For an already completed run, use `watch --include-existing --timeout 5`.
- Shared output: `inventory_tracking/runs/<run-id>/{probe.log,report.json}`;
  Git-ignored. See [package README](inventory_tracking/README.md).
- Host run `20260920T210805Z-de6e8b64` succeeded: both `process_vm_readv` and
  `/proc/<pid>/mem` read 16 bytes; watcher detected it automatically. Normal UID
  1000, no effective capabilities, Yama mode 1; no permission changes required.
- Game PID was `2487980` (rediscover on restart), Steam AppID `2536520`, Proton
  Experimental / Steam Linux Runtime 4 / pressure-vessel. Prefix:
  `/mnt/extra/1000/games/steam/steamapps/compatdata/2536520/pfx/`.
- No named D2R.exe mapping appeared. Probe succeeded at `0xe20000` in
  `/memfd:wine-mapping (deleted)`. This address is **not** an established game-image
  base or HP/belt address. Missing PE filename must not prevent memory probing.

## Binary Ninja

- Global Codex MCP `binaryninja` configured in `~/.codex/config.toml`:
  `http://127.0.0.1:24642/mcp`, no authentication. Initialize handshake succeeded.
  Reload/restart the Codex session if tools are not available yet.
- Server instruction: call `bn_binary_view_list`, then `bn_binary_view_set_active`
  with the intended handle before using a file opened in the UI. Do not assume
  the game file is already open or active.
- Binary: `/mnt/extra/1000/games/steam/steamapps/common/Diablo II Resurrected/D2R.exe`.
  `/proc/<pid>/exe` points to Wine's loader instead.
- Disk SHA-256: `1e2ac459feb3f4bbfa818cdff49800480502beae9f90cfa4cba9e7e1f8bfa3b7`.
  No executable version/layout has been validated. External reader docs report
  encrypted disk code; check whether a runtime image dump is needed for analysis.

## Next steps and sources

1. Continue from the confirmed table/stat locations in the layout notes; do not
   repeat process-access or PE-base research. `probe --units` rescans the image
   and reads candidate player/item chains, recording `units.json`.
2. Column-1 consumption, compaction, refill and bottom/top placement have live
   evidence below; a top-only potion was not consumed across empty lower slots.
   Still test mixed columns, other keys and capacity changes.
3. Damage sample 1526/1545 matched the user display, followed by a healed
   1545/1545 sample. Character selection and a new game passed research checks;
   one full process restart passed too. Effective
   stats `+0xe8` also matched gear-induced life changes. Derive local-player
   identity robustly: several player-like units share the character name.
4. Turn research into a build-gated reader with timestamped unavailable/stale
   states before implementing overlay or controller decisions.

Research leads inspected, **not validated for this build**:

- [d2go item reader](https://github.com/relentlessricktrinidad/d2go/blob/main/pkg/memory/item.go):
  strongest belt lead; item unit table, ownership, mode/location `2`, path coordinates.
  [Belt model](https://github.com/relentlessricktrinidad/d2go/blob/main/pkg/data/belt.go).
- [diablo2utils structures/signatures](https://github.com/ChrisTitusTech/diablo2utils/blob/master/docs/d2r-memory-offsets.md)
  and [patching guide](https://github.com/ChrisTitusTech/diablo2utils/blob/master/docs/patching-guide.md):
  Linux reads and layouts documented for `3.1.91636`. Sources disagree on some
  offsets (including next-unit links); do not mix constants without validation.
- [D2tools ReadMem](https://github.com/antoinemalloc/D2tools/tree/main/ReadMem):
  additional HP/player lead. No verified belt Cheat Engine table was found.

## Continuation — 2026-09-21

- Completed the existing `probe --images` implementation (`images.py`,
  `image_probe.py`, CLI integration and tests). It parses PE32+ metadata at
  readable mapping starts and the disk preferred base, without named-map assumptions.
  A unique matching header is only a candidate, not validated code or game state.
- Binary Ninja tools are available in this session. Listed views and explicitly
  activated `view_1`; its open item is the intended disk D2R.exe. Handles are
  session-specific. No database or binary modifications were made.
- Independently parsed the disk PE and rechecked its SHA-256 (unchanged).
  Preferred base `0x140000000`, entry RVA `0x5f3d0`, image size 41,455,616 bytes;
  eight sections. These disk values do not establish the runtime base.
- The documented unit-table signature `48 03 C7 49 8B 8C C6` has no matches
  in this disk file's executable section. This alone does not prove encryption;
  runtime code analysis or a changed signature may be needed. Source remains
  the linked diablo2utils offsets document; its offsets are not adopted.
- Host discovery runs initially returned `stale` despite successful access:
  comparing all mappings, then all screened addresses, included changing game
  allocations. Regression tests now demonstrate that unrelated non-PE mapping
  churn is ignored, but a changed parsed-header mapping or restarted process
  rejects the candidate. Stale mapping results retain diagnostic image metadata
  without publishing `candidate_base`. Before/after checks are not atomic.
- Host run `20260920T212621Z-621c7470` found 88 PE images from 2,464
  addresses and two exact disk-header matches (`0x3370000`, `0x140000000`).
- Mapping evidence from `20260920T212841Z-06ebd375` distinguishes them:
  `0x3370000` is one `rw-s` memfd mapping spanning the image size;
  `0x140000000` has an `r--s` header and fragmented `r-xs` code mappings.
  Its entrypoint `0x14005f3d0` lies in `0x14005c000–0x140060000` (`r-xs`).
  The report counted 532 readable overlapping mappings for this image; the
  mapping list is capped at 128 and explicitly marked truncated.
- Requiring every code-section byte to be readable/executable was too strict.
  Final candidate selection requires matching disk headers plus an executable,
  readable entrypoint inside a declared code section. Full code-section coverage
  remains diagnostic metadata. Regression tests cover fragmented code and
  exclusion of a non-executable header copy. Header/entry mapping checks and
  process identity checks still reject stale evidence.
- Final host run `20260920T213011Z-4a49130c` completed successfully:
  `images.status=candidate`, `candidate_base=0x140000000`. The writable copy
  at `0x3370000` was rejected because its entrypoint is not executable. Both
  memory interfaces still succeeded; PID/start-time identity stayed stable.
  HP/belt structures remain unvalidated.
- Runtime capture and signature scanning are now implemented; the findings
  below supersede the earlier "HP/belt unvalidated" state.

## Location findings — 2026-09-21

- Disk version strings: `3.3.93787`, hash unchanged.
- Fresh runtime signature `0x1400705a8` resolves table RVA **`0x1ead470`**
  (absolute **`0x141ead470`** for this process). Runtime instructions and
  successful chains support next-unit **`+0x158`**.
- `probe --capture` writes sparse `image.bin` + `capture.json`; `probe --units`
  implies capture and adds `units.json` and a human-readable candidate summary.
  These are sequential research snapshots with explicit gaps and limits, not
  controller-ready state. See the README for bounds and artifact format.
- Initial capture `20260920T213737Z-f87e5a68`: 28,213,248 readable bytes,
  no changed captured mappings, exactly one table signature.
- Initial units `20260920T214122Z-ef1b565e`: 7 player-like records, 331 items,
  complete stable traversal. Belt owner `2018320017` (`CybergrindAA`) had
  8 full rejuvenations (class ID 531) and 8 super healing potions (606).
  IDs/codes were verified against d2data misc JSON; user confirmed the belt.
- Move run `20260920T214459Z-21ea3335`: potion ID `133700180` left belt cell
  index 12 for inventory `(3,1)`; belt now 7 rejuvenations + 8 healing potions.
  Cell position comes from item path `+0x10` (u16), mode from unit `+0x0c`,
  owner from item data `+0x0c`. Visual row/drinking order still needs validation.
- Effective stat-array descriptor is **`*(player + 0x88) + 0xe8`**, not the
  old d2go `+0xa8` (empty here). Descriptor holds array pointer and count;
  eight-byte entries hold layer u16, ID u16, value i32. IDs 6/7 give current/max
  life, scaled by 256. Array order/addresses are not constants.
- Gear-change runs `20260920T214644Z-f445000d` and
  `20260920T214659Z-c839a949` read **1700/1700** and **1545/1545**, matching
  the user's reported changes from **1722**. Base max at descriptor `+0x30`
  remained 1010 and must not be mistaken for effective maximum life.
- No input automation, OSD, robust local-player selector or lifecycle-validating
  production reader exists yet. `validated` stays false on research output.


## Pressure-vessel / Wine research — 2026-09-21

- [Valve's Steam Runtime documentation](https://github.com/ValveSoftware/steam-runtime/blob/master/README.md)
  describes Linux namespace containers for a predictable library environment.
  [Pressure-vessel design](https://gitlab.steamos.cloud/steamrt/steam-runtime-tools/-/blob/main/docs/pressure-vessel.md)
  describes runtime bind mounts and game-specific containers. This does not imply
  a separate VM address space or encrypted game memory.
- Our host reader and game share the PID namespace and differ in mount/user
  namespaces. Actual successful host reads establish access in this setup;
  the agent's restricted process view is a separate execution environment.
  No container entry, root, or permission change is currently needed.
- [Valve Wine mapping implementation](https://github.com/ValveSoftware/wine/blob/proton_11.0/server/mapping.c)
  creates anonymous backing files with `memfd_create("wine-mapping", ...)`.
  This explains why that pathname is normal Wine evidence, rather than evidence
  of a pressure-vessel memory barrier. This branch is a research reference, not
  a verified exact source revision of the installed Proton Experimental.
- [Linux process_vm_readv documentation](https://man7.org/linux/man-pages/man2/process_vm_readv.2.html)
  specifies ptrace access checks, partial reads and non-atomic transfers.
  Keep reads bounded and preserve unavailable ranges. We have not established
  the cause of D2R's fragmented page permissions or whether the writable alias
  contains identical runtime code; investigate these separately from isolation.

Last validation: 28 tests passed, 1 sandbox-denied `process_vm_readv` child test
skipped; host success independently verified both interfaces. Ruff lint/format
passed. Tests: `uv run pytest tests -v`.
Do not commit unless asked; preserve unrelated working-tree changes.


## Snapshot consistency continuation — 2026-09-21

- Added regression tests demonstrating that unchanged unit IDs/links could hide
  changed modes or data/stat pointers. The probe now compares every interpreted
  unit-header field immediately after reading details and again after all groups
  have been traversed. It also rechecks both table heads at the end.
- Changed headers or failed final reads mark the group incomplete with diagnostic
  errors. Incomplete snapshots retain research evidence in `units.json` but no
  longer emit the convenient HP/belt summary. Existing CLI behavior returns
  `blocked` / exit 2 for incomplete research. `validated` remains false.
- `sample_finished_monotonic` now complements the start timestamp. These checks
  are not atomic: in-place changes to stats/item paths, or changes that revert
  between checks, can still evade detection. This is not a production reader.
- Validation: 28 tests passed, 1 environment-denied syscall test skipped; Ruff
  lint and formatting passed. No new host sample was collected in this pass.
- Next live experiment: record a fresh `probe --units` baseline with the belt
  expanded and note displayed HP and column-1 contents. Press the configured
  column-1 belt key once, then collect another probe without refilling. Compare
  item IDs and all remaining cell indices to distinguish the consumed cell from
  any column shifting. Record the visual row explicitly; disappearing from the
  belt alone does not prove consumption. Then test refill and damage/healing,
  followed by a new game and process restart. Local-player identity remains open.


## Fresh baseline — 2026-09-21

Host run `20260920T220112Z-745625ae` passed the strengthened unit-header and
end-of-traversal checks (`complete=true`, `validated=false`). Same process
PID/start identity and belt owner `2018320017`; unit sampling interval was
about 54.6 ms, excluding image discovery/capture. Effective life read 1565/1565.
Belt contained 7 full rejuvenations and 8 super healing potions; column 1 had
indices 0/4/8 occupied and 12 empty. The user confirmed displayed HP 1565 and exactly one missing rejuvenation.
Damage/healing and consumption remain unvalidated; the next requested sample
is after one column-1 belt-key press, without refill.


Follow-up run `20260920T220350Z-e785d99d` also completed successfully: all 15
belt item IDs and cells were unchanged, with effective HP still 1565/1565.
User confirmed column-1 key is `1` and this sample was taken BEFORE pressing
it. This is a second unchanged baseline, not a consumption experiment.


### Belt-key sample — 2026-09-21

Run `20260920T220447Z-1c0cbce6` passed consistency checks with the same process
identity. Compared with the pre-key baseline `20260920T220350Z-e785d99d`,
column-1 items `534817104` (cell 0) and `267400360` (cell 4) disappeared from
the item traversal; item `2592217162` moved from cell 8 to cell 0. Other belt
items were unchanged. Totals: 5 full rejuvenations, 8 super healing potions;
effective HP still 1565/1565. This demonstrates cell compaction toward index 0,
and the user confirmed pressing `1` twice, accounting for the two missing
potions. This supports consumption from the low-index end with compaction;
the intermediate state was not sampled. Visual row orientation remains open.


Run `20260920T220644Z-25a9fb89` completed with stable checks after the requested
single additional `1` press. The remaining column-1 item `2592217162` at cell 0
was absent; column 1 was empty, with 4 rejuvenations and 8 healing potions total.
Effective HP remained 1565/1565. Together with the user-confirmed two-press
sample, this supports key `1` consuming from the low-index end of column 1.
Visual row mapping, mixed columns, refill and capacity changes remain open.


Refill run `20260920T220745Z-e0e00dfb` passed consistency checks. Following the
instruction to place one full rejuvenation in the lowest visible column-1 slot,
new item `1512026217` appeared at cell 0; other belt cells were unchanged.
Totals returned to 5 rejuvenations / 8 healing potions; HP stayed 1565/1565.
This supports bottom visual row = indices 0–3, subject to correct requested
placement. Next requested action is moving that same item to the highest visible
column-1 slot to cross-check orientation.


Row check `20260920T220840Z-e4a53156` passed: the same item `1512026217`
moved from cell 0 to cell 12 following the instruction to move it from the
lowest to the highest visible slot. These controlled placements support
column-1 visual rows bottom-to-top = 0, 4, 8, 12. This supersedes the ambiguous
"bottom" wording in the older manual-move sample. A key-use test with only
cell 12 occupied is pending to check gaps below a potion.


Gap sample `20260920T220954Z-ee251a0c` passed checks, but item `1512026217`
remained at cell 12, with lower column-1 cells empty and HP 1565/1565.
User confirmed pressing `1` with the game focused and observing the potion
stay in place. In this controlled case the key did not skip the empty lower
slots to consume cell 12. An occupied column is not necessarily usable; retain
individual cells when deriving next-potion availability.


### Damage validation — 2026-09-21

Host run `20260920T221144Z-bad7ad0f` completed with stable checks. Effective
life/max raw values were 390656/395520 (8-bit fractional format), displaying
1526/1545, exactly matching the user's report. This validates one below-maximum
health sample. Effective maximum differs from the preceding 1565 baseline;
its cause was not established. Next requested sample is after healing to full
without further gear changes. Regeneration and update latency are not measured.


Healing follow-up `20260920T221233Z-a19c71a0` completed with stable checks and
effective HP 1545/1545 after the request to heal without gear changes. The
sample pair shows current life recovering from 1526 to 1545 with max 1545
unchanged. The damaged display was explicitly user-confirmed; the healed
sample is memory evidence after the requested action. Next: character selection,
new game, then process restart to establish lifecycle behavior.


Character-selection sample `20260920T221324Z-0fa21cef` completed with stable
empty player and item tables (0/0); both candidate summary lists were empty.
No previous session's HP or belt candidates were retained. `complete` here means
research traversal completed, not gameplay readiness: the production reader
must publish unavailable/outside-game state rather than zero HP or zero stock.
Next requested sample: same character after joining a new game.


New-game run `20260920T221417Z-f81f2565` passed in the same process. The table
was rescanned at `0x141ead470`; belt owner/player ID changed from `2018320017`
to `44171616`, and player address changed from `0x8614ca20` to `0x8617a920`.
Effective HP was 1545/1545. Seven player-like units remained, but only the
belt-owner candidate had effective life/max stats. Its inventory marker `+0x70`
was 4032 (earlier 8800); other candidates had zero. This correlation is research,
not a robust selector or a fixed marker value. No local-player rule is adopted.
Next requested experiment: fully close/reopen D2R, enter a game, then probe.


### Process restart — 2026-09-21

Run `20260920T221700Z-a2ce2a59` completed after fully restarting D2R. New
process identity: PID 2532947, start ticks 270903159 (previous PID 2487980,
start ticks 270397116). Both memory interfaces succeeded without permission
changes. Disk SHA-256 is unchanged; image candidate `0x140000000` and scanned
table `0x141ead470` were rediscovered. Seven player-like units and
330 items passed traversal/header/mapping checks. New belt-owner/player ID
44347742 at `0x7b53bfc0` had effective HP 1545/1545; belt candidates
contained 5 full rejuvenations and 7 super healing potions. The top-only
column-1 potion remained at index 12. These are fresh post-restart research
readings, not reused pointers or a production reconnect implementation.

Live validation now covers column-1 consumption/compaction, bottom/top placement,
refill, a top-only gap, one below-max HP display match, healing, character
selection, a new game and one full process restart. Remaining reader work:
robust local-player identification (including empty belt/multiple players),
build gating, explicit unavailable/stale state, in-place mutation checks,
mixed columns/other keys and belt capacity. No overlay or controller exists yet.


## OSD submodule and test layout — 2026-09-21

Implemented `inventory_tracking/osd/`: independent state/formatting, live research
adapter, Wayland GTK4 layer-shell window and CLI. Run on host:
`uv run -m inventory_tracking.osd`; use `--demo` for the visual pass.
See `inventory_tracking/osd/README.md` for positions, targets, terminal diagnostics
and logs. Default text is health plus missing full rejuvenations / super healing
potions against 8/8 targets, with zero-deficit lines hidden. No potion input.

The adapter gates the known disk hash, captures/scans once per attachment,
then polls research units with a 0.5-second delay. It rediscovers after process
changes, expires old samples, and suppresses counts on ambiguous/incomplete data.
Player selection is deliberately still labeled research: unique plausible
full-life-stat candidate, then owner-filtered belt items. Multiplayer identity,
in-place mutation coverage and belt capacity are not solved by this OSD.

Toolkit imports and preview text were checked; actual window visibility,
fullscreen placement and click-through behavior await the user's visual pass.
The overlay is desktop-wide, without focus-based hiding. Build-gating and
reconnect tests cover rejection before layout reads and clearing old values
before discovering a new process.

Moved tests to `tests/` mirroring production paths, including
`tests/inventory_tracking/osd/test_state.py` and `test_reader.py`. Updated imports,
discovery commands and development conventions. Validation: 37 passed, one
sandbox-denied syscall test skipped; Ruff lint/format passed.


### OSD visual adjustment — 2026-09-21

User confirmed the OSD works. Changed to a compact single line, e.g.
`1545/1545 · rejuv 3 · hp 1`, using 16px text and smaller padding. The window
is centered on its output, with content shifted up 80 logical pixels by default.
`--x`/`--y` now specify signed offsets from center (default 0/-80), rather than
top-left margins. Restart the OSD to apply these changes.


### OSD alert visibility — 2026-09-21

Health now appears only at or below 70%, using raw fixed-point values for the
threshold. Potion labels are `juv` / `hp`, each omitted when no stock is missing.
With healthy HP and both targets met, the label and its background are fully
transparent; polling continues so alerts can reappear. Unavailable/stale status
remains visible. Boundary tests cover exactly 70% and one raw unit above it.


### Quiet incomplete reads and opaque text background — 2026-09-21

Incomplete research samples now produce no OSD text/background while retaining
the diagnostic reason in state.json; fresh startup shows `- (connecting)`.
Latest inspected host samples were complete with 1545/1545 HP and 8/8 stock,
so the screenshot's earlier incomplete sample was not available for diagnosing
its specific race. No consistency checks were relaxed. Changed the text panel
from translucent to solid dark background; the empty overlay stays transparent.


### Empty means no mapped OSD — 2026-09-21

User reported an old `hp 1` alert lingering despite no shortages. Latest saved
readings showed full health and 8/8 stock. Changed rendering from label opacity
to hiding/unmapping the entire window when alert text is empty, and remapping it
when an alert appears. Text is cleared on every update. Startup, unavailable and
stale statuses no longer appear on the OSD; diagnostics remain in run artifacts.
Regression tests cover shortage→refill and blank startup→new alert transitions.
Live compositor validation of the residual-text fix is still pending.


### Text-only OSD — 2026-09-21

Removed the solid label background at the user's request. Window and label
backgrounds are transparent; only text is drawn. Empty-alert window hiding
remains unchanged. Restart the OSD to apply the style.


## Mercenary OSD and healing continuation — 2026-09-21

User requests Act 2 Holy Freeze merc health and automatic healing strictly below
60% with Shift+3/4, no more than once per three seconds, never for a dead merc.
`probe --merc` now adds type-1 chains. Host run
`20260920T224656Z-12747c44` found class 338, unit 2460266851 at `0x7b560140`;
monster data `+0x54` matched player 44347742. Effective max at stat list `+0xe8`
was 535040 / 256 = 2090, matching user baseline 2090/2090. Life ID 6 was 32768,
not ordinary player fixed-point HP. The d2go data.go `MercHPPercent` method uses
this normalized scale. The current OSD derives life as max * fraction / 32768,
marks non-full values with `~`, and shows `merc dead` for zero life or modes 0/12.

**Unresolved health discrepancy:** user showed inventory 2048/2090 while OSD
showed 1943/2090, then ~2057/2090 persisting a long time. Damage samples in logs
include raw fractions 31744, 32000, 32256 and 32512. Do NOT claim quantization
alone explains the mismatch. User was asked whether closing/reopening the merc
inventory refreshes its HP value; answer pending. Exact inventory HP source
and below-60% live validation remain outstanding.

Monster traversal now reads stats only for Act 2 hirelings; animation changes
among living modes do not invalidate them, but entering/leaving death does.
This addresses frequent `None` readings during combat without treating unknown
as dead. Indexed mapping lookup shortened observed sampling from hundreds of
milliseconds to about 6 ms; default polling delay is now 0.1 seconds.

Implemented `merc_heal.py` policy and `merc_input.py` XTest backend. Tests cover
zero/dead/missing merc, strict threshold, fresh readings, bottom-cell selection,
shared cooldown across columns, pending item disappearance, timeout suspension,
focus checks, failure key release, and shared lock across OSD instances. Standard
healing class IDs 602–606 verified in cached d2data misc JSON. The backend checks
Niri app_id steam_app_2536520 AND X11 focused PID/start identity, avoids physically
held keys, releases Shift/key in finally, and uses a persisted boot-aware cooldown
under the shared OSD output root. `--no-merc-heal` is observation mode; demo and
`--once` send no input. No actual automated potion key has been live-validated.

**Live input currently blocked by invalid menu layout.** Added `game_ui.py` to
research old d2go UI signature. Matching instructions point near `0x141ebd176`,
but interpreting bytes starting `0x141ebd16c` with old panel offsets is WRONG:
several offsets land in nearby monster-name text (`Undead`, `Minion`), not boolean
flags. Therefore gameplay_ready remains false. Do not weaken that check silently.
User was asked whether to use focus/death/freshness/belt/cooldown checks without
in-game menu detection, or keep input disabled until menu detection is solved;
answer pending. Most recent observation run `20260920T225718Z-40aa2bea`.

Sources used as leads: d2go `memory/monsters.go`, `memory/offset.go`,
`memory/game_reader.go`, `data/data.go`, `data/mode/npc_mode.go`; d2data monstats
class 338. These are not evidence that old UI offsets fit this build. Tests use
pytest under mirrored `tests/inventory_tracking/` paths. No commits.


### Authorized merc healing without menu detection — 2026-09-21

User answered “Use the working checks.” This supersedes the pending menu-gate
decision above. Live state now derives gameplay_ready from complete validated
player/belt/merc readings, process identity and living player/merc; it ignores the
invalid research UI result. Removed the live reader's hardcoded UI RVA filter.
Freshness, exact Niri/X11 process focus, bottom-cell healing selection, physical
key checks, belt consumption acknowledgement and shared three-second cooldown
remain enforced. Open in-game menus are not detected. Restart the OSD normally
to enable this behavior; --no-merc-heal remains observation-only.

A pytest regression passes a real snapshot through selection and the controller,
confirming a heal request despite a false legacy UI flag, and no request for
incomplete samples, missing identity or dead player/merc. Actual automated input
and the persistent merc HP discrepancy still require host validation.


### Merc potion debug OSD — 2026-09-21

Successful merc potion input now appends `merc potion sent (Shift+3)` or
`merc potion sent (Shift+4)` to the OSD for one second measured after sending.
The notification survives subsequent/incomplete samples and expires independently
of health freshness. Failed/rejected sends do not create notifications. This is
a key-send notification; belt acknowledgement remains separate. Pytest covers
both columns, expiry, sample transitions and rejected/failed input.


### Player and merc potion thresholds — 2026-09-21

User confirmed merc healing and the one-second debug OSD work in-game. Added
`inventory_tracking/healing_config.py` with strict defaults: player healing <65%,
rejuvenation <40%; merc healing <55%, rejuvenation <20%. Player rejuvenation
cooldown is 1 second as requested; other potions remain 3 seconds. Backend lock
measures cooldown from the last delivered potion across recipients/instances.
Rejuvenation (verified class IDs 530/531) uses bottom columns 1/2; healing remains
3/4. Emergency rejuvenation takes priority with healing fallback. Player policy
runs first and does not require a merc; merc death/unknown still suppresses merc
input. Each recipient retains independent belt acknowledgement/suspension.

Both policies default on; observe with `--no-player-heal --no-merc-heal`. Player
keys omit Shift and have their own one-second OSD send notification. Existing
merc module names are retained; controller accepts a recipient. Freshness, focus,
held-key checks and no-menu-detection behavior are unchanged. New player and
rejuvenation paths require live verification. Pytest: 86 passed, 1 skipped; lint
and formatting pass.


### Dynamic potion columns — 2026-09-21

Verification found fixed column filtering (rejuvenations 1/2, healing 3/4).
Removed those assumptions: each fresh snapshot identifies either potion type
in any of the four bottom slots and selects the matching column. Higher slots
across gaps stay unusable. Existing controllers and input cooldown already use
actual potion classification, so player rejuvenations in columns 3/4 retain the
one-second cooldown. Tests cover all supported healing/rejuvenation types in
all bottom columns and a live snapshot transition to an all-rejuvenation belt
for both recipients. Thresholds remain unchanged; OSD shortage targets remain
explicit CLI settings (16 full rejuvenations: --rejuvenation-target 16
--healing-target 0). No live game input was sent during this verification.


### Automatic shortage targets — 2026-09-21

Default shortage tracking now derives each four-slot column's type from its bottom
item, or lowest remaining item if bottom is empty. Entirely empty columns default
to rejuvenation. Matching standard healing tiers count together; normal/full
rejuvenations count together. Other types do not satisfy the column's target, and
columns led by other types are not reported as hp/juv. Empty belt => juv 16.
This assumes the current four-row belt. Explicit CLI target overrides remain
available, but default to None (automatic). Healing policy still requires usable
bottom potions; no thresholds/cooldowns changed. Pytest: 104 passed, 1 skipped.


### Merc OSD visibility — 2026-09-21

Merc health now appears only strictly below 65% of its native life fraction.
`MERC_HEALTH_DISPLAY_BELOW_PERCENT` in osd/state.py controls visibility independently
of potion thresholds. Dead-merc alerts and one-second potion notifications remain.
