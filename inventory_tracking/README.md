# Inventory tracking

D2R host memory reader, item appraisal/collection, level guidance, combat macros
and player/merc potion automation. Helpers run on the host under Proton Experimental /
Steam Linux Runtime 4; the OSD targets Niri Wayland. This entry describes the package
as of 2026-10-13; dated probe evidence is linked separately.

- [OSD runbook](osd/README.md): startup, configuration, behavior and diagnostics.
- [Macro framework](macros/README.md): runtime flow, terminology, code map and verification.
- [Widget contracts](osd/design.md): presentation architecture and resource latches.
- [Input sub-module design](input/design.md): guarded facade for focus and key delivery.
- [Input sub-module plan](input/plan.md): resolved contract and implementation steps.
- Guard-only host check: `uv run -m inventory_tracking.input --check`; [runbook](osd/README.md#input-guard-check).
- [Layout reference](history/layout_notes.md): supported build, memory fields and evidence.
- [Merc HP research](history/merc_health_research.md): unresolved panel mismatch and external readers.
- [Appraisal and collection](APPRAISAL.md): Alt+D, identify/stash automation and persisted reports.
- [Assessment contract](../pricing/knowledge/assessment/planning/COMPLETION_CONTRACT.md): current item-assessment work; use its Current contract section.

## Package structure

| Package | Responsibility |
| --- | --- |
| `native/` | Linux process access, build/layout checks, memory/image/unit readers |
| `tracking/` | Live reader lifecycle and player, belt, resource and buff observations |
| `hover/` | Native UI traversal, selection validation and bounded hover sampling |
| `items/` | Offline item decoding, stat-family strategies, metadata and its builder |
| `appraisal/` | Frozen capture, worker lifecycle, local KB integration and readable results |
| `automation/` | Healing decisions, potion delivery coordination and ledger |
| `probes/` | Host research commands and diagnostic workflows |
| `input/` | Focus checks and guarded keyboard delivery |
| `osd/` | Overlay presentation and widgets |
| `macros/`, `combat/`, `builds/` | Request execution, shared combat decisions and build-specific behavior |
| `collection/`, `shop/` | Inventory collection and shop assessment |
| `levels/`, `terror/` | Level guidance, routes and monster/zone tracking |

Shared `config.py`, `models.py`, `common.py` and `reports.py` remain at the root.
Imports use explicit package paths. Tests mirror the packages, with shared captured
fixtures under `tests/inventory_tracking/fixtures/`.

Runtime code uses `hover.sampling` and `native.session` directly; it does not import
research command modules. Offline `items` decoding does not depend on live capture,
terminal formatting or the KB. Run artifacts remain under `inventory_tracking/runs/`.

Preferred commands are `uv run --offline -m inventory_tracking.appraisal serve`,
`uv run --offline -m inventory_tracking.probes.hover_ui`, and
`uv run --offline -m inventory_tracking.items.build_metadata`. `inventory_tracking`,
`inventory_tracking.input` and `inventory_tracking.osd` commands are unchanged.

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

For interpretation after a game update, use the [layout reference](history/layout_notes.md).
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

## Historical evidence

[Research history](history/RESEARCH_HISTORY.md) preserves the original external-reference
survey and hover prototypes. Their “not implemented” statements describe those
prototypes, not the current service. Read only the relevant probe when investigating
its evidence. `handoff.md` remains frozen and does not drive current work.
