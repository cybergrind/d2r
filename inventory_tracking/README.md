# Host memory-access diagnostic

Python package in the D2R repository; no third-party runtime dependencies.
This establishes process visibility and read access, not HP/belt offsets.

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

The sandbox test suite verifies `/proc/<pid>/mem` against an owned child process.
Its real `process_vm_readv` child test explicitly skips on environment permission
denial; the successful host run supplies separate evidence for that interface.

Module responsibilities: `probe.py` coordinates diagnostics; `linux_process.py`
handles procfs and file fingerprints; `memory.py` wraps memory-read interfaces;
`reports.py` handles atomic report publication and watching; `common.py` provides
shared logging and helpers; `diagnostics.py` defines the CLI.

```sh
uv run python -m unittest inventory_tracking.test_diagnostics -v
uv run ruff check inventory_tracking
```

Interface references: [process_vm_readv](https://man7.org/linux/man-pages/man2/process_vm_readv.2.html)
and [Yama permissions](https://cdn.kernel.org/doc/html/latest/admin-guide/LSM/Yama.html).
