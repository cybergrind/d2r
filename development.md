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

- Keep tests under `tests/`, mirroring module paths: `inventory_tracking/images.py`
  → `tests/inventory_tracking/test_images.py`; `inventory_tracking/osd/presenter.py`
  → `tests/inventory_tracking/osd/test_presenter.py`. Import production modules by
  their absolute package name. Run `uv run pytest tests -v`.
- A whole tree or a large directory runs in parallel with pytest-xdist (a dev
  dependency): `uv run --offline pytest tests/inventory_tracking -q -p no:cacheprovider
  -n auto --dist loadgroup` (about a minute on the 16-core host, against 10 serially).
  `tests/inventory_tracking/conftest.py` makes `loadgroup` keep each file on one worker,
  as `loadfile` does, except tests marked `@pytest.mark.xdist_group(name)`, which run
  with their group; the groups start first. A test whose plays are cached
  (`functools.cache`) shares a group, or its file, with the other tests that read
  them, or the plays are made again on another worker. Mark a new family of
  expensive plays as a group of its own when one file would hold a worker for more
  than half a minute. A failing test's id under `loadgroup` ends in `@<group>`: drop
  that to run it alone. It is not in the pytest config: a single file or test runs
  faster serially, so pass `-n` only for big runs.

- External implementation references are checked out under `third-parties/`. Read
  `third-parties/README.md` and use local sources before fetching GitHub pages.
  `third-parties/repos.json` records revisions; layouts still require local build
  validation. Do not update or execute these reference checkouts implicitly.
