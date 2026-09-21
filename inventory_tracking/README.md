# Host memory and image diagnostics

Python package in the D2R repository; no third-party runtime dependencies.
This establishes process visibility, read access and PE-image candidates, not HP/belt offsets.

## User: run on the host

With D2R running, from the repository root:

```sh
uv run -m inventory_tracking probe
```

If multiple game instances are found, select the actual game PID:

```sh
uv run -m inventory_tracking probe --pid 2487980
```

The example PID came from the user's 2026-09-21 process listing and may change.
Launchers that only mention D2R.exe in their arguments are excluded. Start as
your ordinary desktop user. Permission failures are useful diagnostic results;
the script does not change sysctl settings or elevate itself.

Each invocation creates `inventory_tracking/runs/<UTC-time>-<unique-id>/`:

- `probe.log`: Python logging, including environment, probe results and tracebacks.
- `report.json`: atomically published `running`, then `complete`, `blocked` or
  `failed` state, timestamps, process identity, diagnostics and exit code.

The directory is resolved relative to the package, not the current working
directory. Use `--output /shared/path` **before** `probe` or `watch` to override it.
Host and agent must see the same underlying output directory. Reports/logs are
ignored by Git. Only selected environment variables are logged; no complete
environment or command-line dump and no memory bytes are logged.

The probe reads up to 16 bytes from a readable mapping in the game process using
both `process_vm_readv` and `/proc/<pid>/mem`. It prefers a named D2R.exe mapping,
but can use another readable mapping when Wine uses anonymous/memfd mappings.
It neither attaches a debugger nor stops/writes the game. It also hashes the
mapped game's on-disk file, or a clearly labeled D2R.exe candidate in the game's
working directory. That hash identifies a disk artifact; it is not a validated
game version or proof that the file has not changed since launch.

## Discover the loaded game image

```sh
uv run -m inventory_tracking probe --images
```

After the access probe, this compares bounded PE32+ headers at readable mapping
starts and the disk preferred base against the fingerprinted disk executable.
Anonymous Wine mappings are supported. It reads headers only: at most 16,384
candidate addresses, with each header constrained to 64 KiB. It does not dump
runtime code or assume a fixed game base.

`report.json` gains an `images` result. One matching header with a readable/executable entrypoint inside a declared code
section gives `candidate`
and `candidate_base`; multiple matches give `ambiguous`, no match gives
`unavailable`, and reaching the scan limit gives `incomplete`. Process restarts
or changes to mappings covering parsed PE headers or matching-image entrypoints give `stale`. Unrelated allocations
are ignored. These before/after checks are not an atomic snapshot, and a header
match does not prove code identity or validate game structures. Only `candidate`
returns success with `--images`; other discovery outcomes return exit code 2
(or 1 for an execution failure). Plain `probe` retains access-only semantics.

Code pages can have fragmented permissions in the live game: full executable
section coverage is recorded as evidence but is not required. Header matches
include bounded mapping metadata and entrypoint permissions to distinguish an
ordinary non-executable copy from a loaded-image candidate. Neither this heuristic
nor permission checks establish that every code page can be read or decrypted.

## Agent: detect a user run without a chat reply

Start this watcher before asking the user to run the probe:

```sh
uv run -m inventory_tracking watch --timeout 300
```

Use the execution tool's short yield to leave it running, and poll the returned
session while continuing work. The watcher checks shared files once per second,
announces new runs, and prints a finished JSON report immediately on completion.
Then read that run's `probe.log` and analyze its errors and read results. A
`blocked`/`failed` report also completes the watcher: failures are not ignored.
Default behavior ignores runs already present when the watcher starts.

If the user has already run the script:

```sh
uv run -m inventory_tracking watch --include-existing --timeout 5
```

This accepts existing reports, considering newest directory names first. Check
the run ID and timestamps before treating a report as current. A killed probe
may leave `running` indefinitely; a watcher timeout is not proof of completion.
No automatic chat-turn wakeup is provided: detection works while the agent has
an active turn and is polling the watcher. Across turns, inspect existing reports.

Exit codes: `0` = at least one memory interface read successfully with stable
process identity, `2` = target found but access not established, `1` = diagnostic
failure (including missing/ambiguous target), `124` = watcher timed out.

## Interpretation and validation

Compare reader/game UID and namespaces, `ptrace_scope`, capabilities, mapping
visibility, and the separate read-interface results. EPERM alone does not identify
which policy denied access. A successful read is permission evidence, not proof
that health/inventory structures have been found.

User's process listing shows Steam Linux Runtime 4 / pressure-vessel and Proton
Experimental; the helper records the live prefix and namespaces where accessible.

Host validation on 2026-09-21 (local time), run `20260920T210805Z-de6e8b64`:
both interfaces read 16 bytes successfully from PID 2487980 at `0xe20000`, a
`/memfd:wine-mapping (deleted)` mapping. Process identity remained stable. The
ordinary host user had UID 1000, no effective capabilities and `ptrace_scope=1`;
no permission changes were required for this run. The sandbox watcher detected
completion through the shared output directory without a user chat reply.

Image-discovery host validation, run `20260920T213011Z-4a49130c`:
selected `0x140000000` as the sole matching-header candidate with an executable
entrypoint. A second matching header at `0x3370000` belonged to a non-executable
writable mapping. Runtime code is fragmented across mappings; this validates
candidate discovery, not HP/belt offsets or complete code readability.

The sandbox test suite verifies `/proc/<pid>/mem` against an owned child process.
Its real `process_vm_readv` child test explicitly skips on environment permission
denial; the successful host run supplies separate evidence for that interface.

Module responsibilities: `probe.py` coordinates diagnostics; `linux_process.py`
handles procfs and file fingerprints; `memory.py` wraps memory-read interfaces;
`images.py` parses bounded PE headers and finds candidates; `image_probe.py`
coordinates disk fingerprint matching and live consistency checks;
`reports.py` handles atomic report publication and watching; `common.py` provides
shared logging and helpers; `diagnostics.py` defines the CLI.

```sh
uv run pytest tests/inventory_tracking/test_diagnostics.py tests/inventory_tracking/test_images.py -v
uv run ruff check inventory_tracking tests
```

Interface references: [process_vm_readv](https://man7.org/linux/man-pages/man2/process_vm_readv.2.html)
and [Yama permissions](https://cdn.kernel.org/doc/html/latest/admin-guide/LSM/Yama.html).

## Runtime location research

With the character in a game, preferably standing in town:

```sh
uv run -m inventory_tracking probe --capture
uv run -m inventory_tracking probe --units
```

`--capture` implies image discovery and saves `image.bin` plus `capture.json` in
that run's directory. The binary is a compact stream of captured ranges, **not a
loadable PE file**. The manifest maps each block's address, length and file offset;
missing pages are omitted, never filled with invented zero bytes. Image size and
read volume are bounded to 64 MiB, with reads up to 64 KiB. Changed mappings are
marked and excluded from signature scanning. Process/image identity changes
invalidate candidates. Captures are sequential, not atomic. Only local, Git-ignored
artifacts contain runtime bytes; the binary has owner-only permissions.

The unit-table search uses the d2go signature and decodes its module-relative
32-bit displacement; it does not adopt an older build's fixed table address.
Only readable portions of executable sections are scanned, so no match does not
prove that the signature is absent from unreadable pages.

`--units` implies a fresh capture, then inspects a single candidate table. It
writes `units.json` with bounded player/item chains, owner IDs, item modes, path
coordinates and candidate stat arrays. Reads are limited to 8 MiB total, units
to 2,048 per type, and stat arrays to 1,024 entries. Cycles, type/bucket mismatches,
short reads and changed unit headers/heads are reported. All interpreted header
fields and both table heads are checked again after traversal. Incomplete research
returns exit 2 and suppresses the candidate summary; raw evidence remains in
`units.json`. Start/end monotonic timestamps bound the read interval. In-place
stat/path mutations and changes that revert between checks can still escape these
non-atomic checks. A successful research run
is **not** validated gameplay state: `validated` remains false, and no input is
sent. Displayed base maximum HP may exclude bonuses; compare candidate arrays
with the game before deriving a health percentage.

Tests for all diagnostics and research modules:

```sh
uv run pytest tests -v
uv run ruff check inventory_tracking tests
uv run ruff format --check inventory_tracking tests
```


## Experimental live OSD

The [OSD submodule](osd/README.md) displays health and missing belt potions:

```sh
uv run -m inventory_tracking.osd
uv run -m inventory_tracking.osd --demo
```

Defaults target 8 full rejuvenations and 8 super healing potions. Zero-deficit
lines are hidden. The live adapter remains research-only; visual validation
in-game is the next step. Tests now live under `tests/inventory_tracking/`,
mirroring module paths.
