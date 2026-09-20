# Inventory tracking handoff — 2026-09-21

Continue [inventory_tracking.md](inventory_tracking.md): health/belt reader → OSD →
observation-only potion decisions → automatic input. Process-access diagnostics,
bounded runtime capture and player/item research probes are implemented. HP and
belt locations have initial controlled validation; lifecycle and input semantics
remain unvalidated. See [layout notes](inventory_tracking/layout_notes.md). Follow [development.md](development.md): Python/uv, meaningful
red/green TDD, separate low-level modules, shared logging, readable workflows.

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
2. Validate belt visual row direction and which index a belt key consumes;
   test refill/mixed columns and capacity changes. A column-1 move is confirmed.
3. Validate HP during damage/healing and new games/process restarts. Effective
   stats `+0xe8` matched two gear-induced life changes. Derive local-player
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

Last validation: 25 tests passed, 1 sandbox-denied `process_vm_readv` child test
skipped; host success independently verified both interfaces. Ruff lint/format
passed. Tests: `uv run python -m unittest discover -s inventory_tracking -t . -v`.
Do not commit unless asked; preserve unrelated working-tree changes.
