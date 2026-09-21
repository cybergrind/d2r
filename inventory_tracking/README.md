# Inventory tracking

D2R health/belt/resource reader, alert OSD and player/merc potion automation.
Live behavior was accepted by the user on 2026-09-21. Helpers run on the host
under Proton Experimental / Steam Linux Runtime 4; the OSD targets Niri Wayland.

- [OSD runbook](osd/README.md): startup, configuration, behavior and diagnostics.
- [Widget contracts](osd/design.md): presentation architecture and resource latches.
- [Input sub-module design](input/design.md): guarded facade for focus and key delivery.
- [Input sub-module plan](input/plan.md): resolved contract and implementation steps.
- Guard-only host check: `uv run -m inventory_tracking.input --check`; [runbook](osd/README.md#input-guard-check).
- [Layout reference](layout_notes.md): supported build, memory fields and evidence.
- [Merc HP research](merc_health_research.md): unresolved panel mismatch and external readers.
- [Current handoff](../handoff.md): acceptance and current work status.

## Host probes

Run as the desktop user, with D2R running, from the repository root:

```sh
uv run -m inventory_tracking probe                # process identity and read access
uv run -m inventory_tracking probe --images       # matching loaded PE candidate
uv run -m inventory_tracking probe --capture      # bounded runtime image capture
uv run -m inventory_tracking probe --units        # player/item research snapshot
uv run -m inventory_tracking probe --merc         # also Act 2 merc stats/ownership
uv run -m inventory_tracking probe --resources    # staff/tome stats and location
```

`--merc`/`--resources` imply units; units imply capture and image discovery.
Use `--pid PID` to select among game instances; rediscover after restart.
`--output /shared/path` goes **before** `probe` or `watch`. Default output is
`inventory_tracking/runs/`, independent of the working directory.

Each run has a unique UTC/UUID directory with `probe.log` and atomic `report.json`.
Capture adds `image.bin`/`capture.json`; unit probes add `units.json`.
Reports transition from `running` to `complete`, `blocked`, or `failed`.
All run artifacts are Git-ignored. Probes do not stop/write the game, send input,
change permissions or elevate themselves.

| Result | Exit code |
| --- | --- |
| Requested diagnostic completed | 0 |
| Target found but access/layout/snapshot incomplete or unavailable | 2 |
| Failure, including missing/ambiguous process | 1 |
| Watch timeout | 124 |

`complete` means the requested research checks passed, not gameplay readiness.
Raw research retains `validated=false`; domain selection applies additional
build, ownership, plausibility and freshness checks before automation.

## Watch a host run from the agent

Start before the host probe, then poll its execution session:

```sh
uv run -m inventory_tracking watch --timeout 300
# Inspect a report that already exists:
uv run -m inventory_tracking watch --include-existing --timeout 5
```

The watcher checks once per second and prints the completed report, including
blocked/failed results. Existing reports are ignored unless requested; verify
run IDs/dates when accepting old reports. A killed probe may leave `running`;
a timeout is not completion. Watching requires an active agent execution session,
and does not automatically wake a later chat turn.

## Acquisition guarantees and limits

- Access probes read up to 16 bytes with both `process_vm_readv` and `/proc/PID/mem`,
  checking PID/start identity before and after. Wine anonymous/memfd mappings are
  supported; a named D2R.exe map is unnecessary. Normal host access succeeded
  without permission changes in the recorded setup.
- Image discovery matches bounded PE32+ headers against the disk fingerprint,
  selecting a unique candidate with an executable entrypoint. Writable copies
  remain separate candidates. Header/entry mapping changes invalidate results;
  unrelated allocations do not. A matching header does not prove complete code
  readability or validate unit layouts.
- Capture is limited to 64 MiB. `image.bin` is a compact sequence of readable
  ranges, **not a loadable PE**; `capture.json` maps addresses to offsets. Missing
  pages are omitted. Capture files are owner-only and may contain runtime bytes.
- Unit traversal bounds counts/reads and rechecks interpreted headers, table
  heads and mappings. Incomplete reads suppress HP/belt summaries but retain raw
  evidence. Start/end monotonic timestamps bound acquisition. These sequential
  checks are not atomic: in-place or reverted mutations can still escape them.
- Resource reads have a separate budget and recheck item values/identity/location.
  Optional failures produce unavailable resource observations, without disabling
  otherwise valid health/belt input decisions.

For interpretation after a game update, use the [layout reference](layout_notes.md).
Linux access references: [Yama](https://www.kernel.org/doc/html/latest/admin-guide/LSM/Yama.html),
[process_vm_readv](https://man7.org/linux/man-pages/man2/process_vm_readv.2.html).

## Development

Follow [development.md](../development.md). Tests mirror modules under `tests/`:

```sh
uv run pytest tests -q
uv run ruff check inventory_tracking tests
uv run ruff format --check inventory_tracking tests
```

The real child-process syscall test skips when the agent environment denies
access; host probe evidence is separate. [OSD runtime structure](osd/README.md#runtime-structure)
maps domain and automation modules. Acquisition modules separate Linux access,
PE parsing/capture, bounded unit/resource reads, and report publication.

## Other projects and research references

Reviewed 2026-09-21. These are source/design leads, not validated offsets for our
installed D2R build. See the [merc HP comparison](merc_health_research.md) for
commit-pinned source links, calculations and limitations.

| Project | Why it is useful |
| --- | --- |
| [d2go — accessible fork](https://github.com/relentlessricktrinidad/d2go) | D2R memory structures and stat readers. Merc HP uses the same normalized /32768 estimate as ours, with an ordinary-HP fallback. Original hectorgimenez repository was inaccessible during this review. |
| [D2R-AutoPotion-Go](https://github.com/Apethor/D2R-AutoPotion-Go) | Potion watcher and related d2go code lineage; same merc HP heuristic, not an independent exact-HP solution. |
| [Koolo — accessible fork](https://github.com/dulingzhi/koolo) | Player/merc health policies, belt use and recovery workflows; consumes d2go's merc percentage. Original hectorgimenez repository was inaccessible during this review. |
| [MapAssist — accessible fork](https://github.com/dglEnraged/MapAssist) | C# unit/stat-list readers and overlay architecture; generic monster life/max ratio is not validated for our merc encoding. |
| [d2r-mapview](https://github.com/joffreybesos/d2r-mapview) | AutoHotkey memory readers and HUD implementation; useful comparison for unit/area/stat layouts, without an exact merc HP solution. |
| [Botty](https://github.com/johannes-do/botty) | Visual alternative: estimates merc health from filled pixels in the portrait health bar. Useful for an independent display cross-check. |
| [D2BS](https://github.com/noah-/d2bs) | Legacy Diablo II client integration. Merc HP calls the game's unit-ID-based percentage function, suggesting a separate client health source to investigate. Old addresses do not apply to D2R. |
| [D2MOO](https://github.com/ThePhrozenKeep/D2MOO) | Reconstructed legacy game code: 128-step monster life, throttled updates, owner-facing percentage and explicit merc-stat delivery. Explains possible mechanisms; does not prove current RotW behavior. |
| [Cartographer / Wanderer](https://github.com/cartographerwanders/d2rmanager-cartographer-wanderer) | Modern HUD reference advertising merc HP. The inspected snapshot contains documentation/images only, so its health algorithm could not be inspected. |
| [D2tools / ReadMem](https://github.com/antoinemalloc/D2tools/tree/main/ReadMem) | Earlier Windows/Rust player HP/mana reader lead; not established as a merc HP source by this comparison. |
| [diablo2utils](https://github.com/ChrisTitusTech/diablo2utils) | Earlier Linux memory-structure/signature and patching references. Layouts remain build-specific and must be checked against local evidence. |

Production changes require supported-build validation; related forks should not
be counted as independent confirmation. External code was inspected in temporary
checkouts outside this repository; no third-party runtime was installed or run.
