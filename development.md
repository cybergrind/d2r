# Development practices

Applies to repository code changes. Linked from [AGENTS.md](AGENTS.md).

- Use red/green TDD when it adds meaningful confidence: reproduce a bug or state
  the required behavior in a failing test, implement the change, then refactor
  with the tests green. Prioritize process access, lifecycle/race handling and
  host/agent handoffs; avoid tests that merely repeat implementation details.
- Separate low-level platform details into focused functions/modules. Keep
  high-level workflows readable in domain terms, with clear names and minimal
  syscall, filesystem or serialization mechanics inline.
- Reuse common modules for logging and shared functionality. Use Python logging
  and persist host-side diagnostics to files the sandboxed agent can inspect.
- Use Python with `uv run` for inventory-tracking tooling. The user runs host
  probes; agents remain sandboxed and consume shared logs/status files. Provide
  completion detection so an active agent can proceed without a user chat reply.
- Use pytest with plain test functions, assertions and pytest parametrization;
  do not use unittest test cases or its runner. Standard-library `unittest.mock`
  remains suitable for mocks. Run meaningful tests and applicable lint/format
  checks before delivery.
- Lint is the pre-commit hook's: `uv run ruff check`, `uv run ruff format --check` and
  `uv run pyrefly check` must be clean, and a plain run sees what the hook sees (ruff's
  preview rules are on in `pyproject.toml`). Pyrefly reports 0 errors on the whole
  project (since 2026-10-15) and must stay there: fix the type, and use
  `# pyrefly: ignore[<kind>]` only where a test passes a wrong type on purpose, with the
  reason on the line.

- Keep tests under `tests/`, mirroring module paths: `inventory_tracking/images.py`
  → `tests/inventory_tracking/test_images.py`; `inventory_tracking/osd/presenter.py`
  → `tests/inventory_tracking/osd/test_presenter.py`. Import production modules by
  their absolute package name. Run `uv run pytest tests -v`.
- Tests run serially, one run on the host at a time (user, 2026-10-15: parallel runs locked the
  host the player plays on). `tests/conftest.py` turns `-n` off before xdist starts any worker,
  makes a run wait while another holds the host's one test slot (a `flock` in `.test-slots/`),
  and runs it at nice 19 with the lowest best-effort I/O priority (`D2R_TEST_PRIORITY=normal`
  keeps the usual priority for timing measurements). `tests/inventory_tracking` takes about
  9 minutes and 2 GB; run the files a change touches, and the whole tree once at the end.
  The `xdist_group` marks and the `loadgroup` scheduler in `tests/inventory_tracking/conftest.py`
  stay for a run that turns parallel runs back on.

- External implementation references are checked out under `third-parties/`. Read
  `third-parties/README.md` and use local sources before fetching GitHub pages.
  `third-parties/repos.json` records revisions; layouts still require local build
  validation. Do not update or execute these reference checkouts implicitly.
