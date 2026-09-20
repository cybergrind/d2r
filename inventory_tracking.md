# D2R inventory and health OSD implementation plan

Written: 2026-09-20. Updated: 2026-09-21. Status: host access, image discovery,
runtime capture and unit research implemented. Belt move and effective HP
locations confirmed in controlled samples; lifecycle validation, OSD and
controller remain planned.

## Objective

D2R runs through Steam in an isolated environment. Add an on-screen display above
the game that makes potion stock and health easy to read while farming.

- Show full rejuvenation and super healing potion counts, with configurable
  low-stock indicators so the player knows when to pick up more.
- Show availability in each belt column. The usual arrangement is full
  rejuvenations in columns 1–2 and super healing potions in columns 3–4, but the
  reader must report actual contents rather than assume this arrangement.
- Show current/max health and health percentage.
- Add automatic full rejuvenation use when health falls below a configurable
  threshold, once the underlying readings and input handling are reliable.

Memory reading is the preferred approach to investigate. Existing reader source
and Cheat Engine tables are research leads, not verified solutions for this build.

## Open questions and initial inspection

- What creates the isolation: Steam Linux Runtime, Flatpak, a container, VM, or
  another mechanism? Which Proton/Wine version and prefix are in use?
- What is the exact D2R executable/build, and is play online or offline?
- Which display server/compositor and fullscreen mode are in use? Is Gamescope
  involved? What resolution and UI scaling are used?
- From where can a helper access the game process, display an overlay, and send
  input to the correct game instance?
- What belt key bindings are configured? What health and low-stock thresholds
  should be used? Keep these configurable rather than embedding assumptions.

Resolve technical details by inspecting the running setup where possible. Record
the results here before choosing the reader, overlay, or input backend.

## Memory-reader preparation — inspected 2026-09-20

Observed from the agent command environment:

- UID/GID are 1000/1000. The process list exposes only agent processes; neither
  Steam, Wine nor D2R is visible. An explicit escalated process-list command
  returns the same view. This does not establish whether D2R is running on the
  host; host/game process visibility is the first unresolved prerequisite.
- Visible `kernel.yama.ptrace_scope` is `1`. Effective and bounding capabilities
  are zero; `NoNewPrivs=1` and `Seccomp=2`. The seccomp filter's syscall policy
  has not been tested. No actual game-memory read has been attempted.
- Python 3, GDB, Wine, Steam, Flatpak, nsenter and capability utilities are on
  PATH. Their presence does not establish how the game is launched.
- Environment variables report Wayland (`WAYLAND_DISPLAY=wayland-1`) and
  `DISPLAY=:0`; compositor, game display mode and overlay access remain unknown.

Setup needed before memory-reader agents can validate live data:

1. Run D2R and provide a reader execution environment that can see its Linux PID
   and `/proc/<pid>/maps`. Prefer a host-side reader/helper, with agents consuming
   its output through a shared file or local IPC. Alternatively, launch the agent
   runner with appropriate process visibility. The current escalation request
   does not provide that visibility; filesystem access alone is insufficient.
2. Verify game UID, Proton/Wine prefix, namespaces and executable/build from that
   environment. Do not select offsets until the installed executable is known.
3. Establish memory-read permission. With Yama mode 1, same UID alone is generally
   insufficient for an unrelated Linux reader. Options include a reader that is
   an ancestor of the actual game process, an explicit target-side ptracer
   allowance, or a narrowly scoped host helper with `CAP_SYS_PTRACE` in the
   relevant user namespace. Existing Steam processes may defeat an assumed
   launcher/child relationship, so verify the actual process ancestry.
   A temporary host `ptrace_scope=0` is another option for same-UID dumpable
   targets, but broadens access for other processes and does not fix PID
   visibility, seccomp or other access checks. No permission settings were changed.
4. Prove access with a small read-only `process_vm_readv` or `/proc/<pid>/mem`
   probe against a known readable mapping, without attaching/stopping the game.
   Record PID, mapping, bytes-read count and error code; avoid logging arbitrary
   game-memory contents. Successful map listing alone is not proof of memory
   access. Repeat after restarting D2R.
5. Only then begin HP/belt layout research. Access permission and correct
   build-specific interpretation are separate gates. Overlay and input setup
   are not prerequisites for the terminal memory-reader proof.

References: [Linux Yama documentation](https://cdn.kernel.org/doc/html/latest/admin-guide/LSM/Yama.html)
and [process_vm_readv permission checks](https://man7.org/linux/man-pages/man2/process_vm_readv.2.html).

## Host diagnostic handoff — 2026-09-21

Implemented the Python package [`inventory_tracking/`](inventory_tracking/README.md).
Run `uv run -m inventory_tracking probe` on the host with D2R running.
It writes a unique run directory containing `probe.log` and atomic `report.json`.
The sandboxed agent can run `uv run -m inventory_tracking watch --timeout 300`
beforehand to detect completion without a user chat reply. See the package README
for existing-report handling, exit codes, and validation instructions.

The user's process listing identifies Steam Linux Runtime 4 / pressure-vessel,
Proton Experimental, and game PID 2487980 at the time of the listing. Runtime
PID should be rediscovered on each run; executable layout still requires validation.
No HP/belt reader, overlay or input automation has been implemented by this pass.

Validated host run `20260920T210805Z-de6e8b64` (2026-09-21 00:08 local time):

- The sandbox watcher automatically detected completion via the shared run files.
- Both `process_vm_readv` and `/proc/2487980/mem` read 16 bytes at `0xe20000`
  successfully; PID/start-time identity was stable through inspection.
- The mapping was `/memfd:wine-mapping (deleted)` with `r-xp` permissions.
  No named D2R.exe mapping was found. The first diagnostic had incorrectly
  required that name; a regression test now covers unnamed readable mappings.
- Host reader: UID 1000, `CapEff=0`, `NoNewPrivs=0`, `Seccomp=0`, Yama mode 1.
  No permission changes are needed for the tested host reader. The reason this
  target passes the access policy is not established by the probe.
- Reader/game share PID namespace `pid:[4026531836]`; their user and mount
  namespaces differ. Steam's isolation does not prevent this host read.
- Prefix: `/mnt/extra/1000/games/steam/steamapps/compatdata/2536520/pfx/`.
- Disk candidate `/proc/2487980/cwd/D2R.exe` SHA-256:
  `1e2ac459feb3f4bbfa818cdff49800480502beae9f90cfa4cba9e7e1f8bfa3b7`.
  This fingerprints the disk file; it does not identify a validated memory layout.

Reader placement is now established: user-run host helper, sandboxed agents
consuming logs/reports. Revalidate after a game restart, then investigate the
loaded PE image and player/HP/belt structures without assuming named mappings.

## PE-image discovery continuation — 2026-09-21

`uv run -m inventory_tracking probe --images` now performs bounded PE32+ header
matching against the fingerprinted disk executable, including anonymous mappings.
The disk hash is unchanged; preferred image base is `0x140000000`, entry RVA
`0x5f3d0`, and image size 41,455,616 bytes. Binary Ninja's active disk view agrees
with the parsed section layout. None of these establishes the runtime base.

Initial host scans detected map churn and returned `stale` despite successful
memory access. The consistency check now focuses on parsed PE header mappings;
regression tests cover unrelated allocations, changed header mappings and process
restarts. Host run `20260920T212621Z-621c7470` then found two matching headers
(`0x3370000`, `0x140000000`) and correctly reported ambiguity. Mapping evidence from
`20260920T212841Z-06ebd375` shows a non-executable writable copy at `0x3370000`
and fragmented executable pages at `0x140000000`, including the PE entrypoint.
Candidate selection now checks the entrypoint rather than requiring every code
page to be readable/executable. Host run `20260920T213011Z-4a49130c` successfully selected `0x140000000`
as the sole executable-entrypoint candidate. HP/belt layouts and restart
revalidation remain outstanding. See [handoff.md](handoff.md) for next steps.

## HP and belt location findings — 2026-09-21

The runtime scan located the unit table at RVA `0x1ead470`; linked units use
`+0x158`. Player/item chains and ownership yielded the user-confirmed full belt:
8 full rejuvenations and 8 super healing potions. A controlled column-1 move
changed the same potion from belt cell 12 to inventory `(3,1)`, leaving 7/8.

Effective stats are reached through player `+0x88`, then the array descriptor at
stat list `+0xe8`. Life/max-life IDs 6/7 use 8-bit fractional values. The user
confirmed readings matching gear changes **1722 → 1700 → 1545**. Base max life
from `+0x30` excludes bonuses; the old reference's `+0xa8` descriptor is empty.

Run `uv run -m inventory_tracking probe --units` on the host for a fresh research
snapshot. See [layout notes](inventory_tracking/layout_notes.md) for exact fields,
run IDs and evidence. New games/restarts, damage/healing, local-player selection,
belt consumption order, capacity and row orientation still need validation.
These findings do not establish controller-ready state.

## Architecture

```text
Game reader → validated, timestamped state → OSD
                                         → potion controller → belt key
Recorded state ───────────────────────────→ OSD / controller tests
```

Keep acquisition, rendering, decision logic, and input delivery separate. The
reader should publish a common state format so recorded fixtures or a later
screen-recognition backend can feed the same OSD and controller.

State should include:

- Process/session identity and monotonic sample time.
- Current/max HP and validity of the health reading.
- Belt capacity and individual cells: position, potion identity, empty/unknown.
- Derived totals by potion type, per-column counts, and the next usable potion
  for each configured belt key.
- Gameplay readiness, focus, and menu/chat/loading/death state where detectable.
  Unknown conditions must remain explicit.
- Reader status and errors; distinguish unavailable data from a real zero.

Select the implementation language and UI toolkit after the environment and reader
proofs of concept. Avoid committing to a native Windows or Linux overlay before
testing it in the actual display setup.

## Milestone 1 — Environment and overlay feasibility

- [ ] Record the environment details above and identify the intended game process.
- [ ] Determine where the reader must run to access that process.
- [ ] Prototype an overlay displaying fixed example values over the game.
- [ ] Verify visibility in the actual fullscreen mode, placement, and scaling.
- [ ] Verify the overlay does not steal focus or intercept gameplay input.
- [ ] Check behavior when switching windows, restarting the game, or changing
      resolution.

**Exit criterion:** a documented reader placement and a dummy OSD that works in
the player's real setup. This can proceed independently of memory-layout research.

## Milestone 2 — Read and validate health

- [ ] Inspect existing D2R reader source and relevant Cheat Engine tables for
      player lookup and current/max HP structures.
- [ ] Check each candidate against the installed executable/build; do not reuse
      an offset solely because it worked for another version.
- [ ] Build a minimal read-only helper that prints timestamped current/max HP.
- [ ] Compare its output with the game during damage, healing, and max-life changes.
- [ ] Repeat across character selection, new games, loading, death, and process
      restarts. Reject stale pointers and impossible values.
- [ ] Record the supported build, lookup method, observed update latency, and
      failure behavior. Unsupported layouts must produce an unavailable state.

**Exit criterion:** health readings consistently match the game and recover after
session/process changes without displaying old readings as current.

## Milestone 3 — Read and validate the belt

- [ ] Locate belt item data and determine cell positions, capacity, and item types.
- [ ] Verify the mapping from each belt key to the next consumed cell, including
      mixed columns and gaps. Do not infer it from total counts.
- [ ] Identify full rejuvenations and super healing potions from verified game
      data. Verify any item codes against the local d2data dump before adding them.
- [ ] Print the full belt grid, per-column availability, and potion totals.
- [ ] Validate drinking, pickup, refill, manual rearrangement, empty columns,
      mixed potion types, and belt capacity changes.
- [ ] Detect inconsistent snapshots during mutations and reread them before
      publishing usable controller state.

**Exit criterion:** the terminal shows verified health and every belt cell, and
counts remain correct through the operations above.

**Fallback decision:** if memory access or layout discovery proves impractical,
evaluate screen recognition. First establish whether all belt rows can remain
visible. Hidden cells cannot be counted directly from screenshots; tracking only
pickups and key presses can drift. Represent uncertain counts explicitly and
reassess whether the fallback provides enough information for automation.

## Milestone 4 — Live OSD

- [ ] Connect the validated reader state to the overlay.
- [ ] Show full rejuvenation and super healing totals, per-column availability,
      current/max HP, and HP percentage.
- [ ] Add configurable position, scale, contrast, and low-stock thresholds.
- [ ] Mark readings as unknown/stale when the reader disconnects or samples expire.
- [ ] Show controller status separately: disabled, observing, armed, or suspended.
- [ ] Measure refresh latency and resource use during a normal farming session;
      choose polling and rendering rates from those observations.

**Exit criterion:** a useful read-only OSD during normal farming, with accurate
counts and clear handling of unavailable data.

## Milestone 5 — Potion decisions in observation-only mode

- [ ] Implement a configurable HP percentage trigger using fresh, validated state.
- [ ] Select a configured belt key whose next usable potion is a full rejuvenation.
      Handle exhausted or mixed columns without assuming columns 1–2 are valid.
- [ ] Suppress decisions when gameplay/focus is unsuitable, relevant state is
      unknown, or the game is loading, in a blocking menu/chat, or the player is dead.
- [ ] Log the proposed action, triggering health, selected column, and sample age
      without sending input.
- [ ] Define cooldown, recovery/rearming behavior, and bounded retry rules so
      sustained low HP cannot cause uncontrolled repeated actions.
- [ ] Record representative state sequences and replay them through the controller.

**Exit criterion:** replay tests and live observation produce the intended
decisions for threshold crossings, sustained low HP, empty/mixed belts, healing,
stale readings, focus loss, and session changes.

## Milestone 6 — Automatic potion input

- [ ] Implement input delivery for the established environment and configured keys.
- [ ] Start disabled; provide an explicit arm/disarm control and an immediate
      disable hotkey, with visible OSD status.
- [ ] Recheck state freshness, focus, and the selected column immediately before
      sending one key press; guarantee key release.
- [ ] Observe belt consumption as acknowledgement. HP recovery alone is not proof
      that the intended potion was consumed.
- [ ] Bound acknowledgement timeout and retries. Suspend with a visible reason if
      consumption cannot be confirmed; never continue issuing blind key presses.
- [ ] Invalidate pending actions on process/session change, reader failure, or
      loss of gameplay readiness.
- [ ] Validate controlled live use, manual drinking during a pending action, and
      game/reader disconnects before normal farming use.

**Exit criterion:** the controller consumes the intended potion under the configured
conditions, confirms the action, and reliably stops when data or targeting becomes
uncertain. It cannot guarantee survival against damage between observations.

## Delivery order and validation

1. Environment notes, dummy overlay, and verified terminal health/belt reader.
2. Usable read-only OSD with configuration and reconnect handling.
3. Observation-only potion controller with recorded replay tests.
4. Automatic input with acknowledgement, bounded retries, and disable controls.

Test controller behavior using recorded state sequences, and validate process
access, rendering, and input against the actual game environment. Keep a short
runbook covering startup, supported game build, configuration, disabling automatic
use, and revalidation after game updates.

## Research references

Reviewed as leads on 2026-09-20; none has been validated against this setup:

- [D2tools ReadMem](https://github.com/antoinemalloc/D2tools/tree/main/ReadMem):
  existing Windows Rust reader for HP/mana. The
  [project documentation](https://github.com/antoinemalloc/D2tools#readmem) notes
  patch-sensitive addresses and potential anti-cheat detection. Read-only access
  does not establish suitability for online use.
- [Cheat Engine pointer-scan documentation](https://www.cheatengine.org/help/pointer-scan.htm):
  reference for validating pointer candidates after addresses change or the game
  restarts.
- [XDG Desktop Portal RemoteDesktop API](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.RemoteDesktop.html):
  possible capture/input integration to investigate if the actual Linux session
  and isolation mechanism support it; not a selected backend.
