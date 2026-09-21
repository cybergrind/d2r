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
  → `tests/inventory_tracking/test_images.py`; `inventory_tracking/osd/state.py`
  → `tests/inventory_tracking/osd/test_state.py`. Import production modules by
  their absolute package name. Run `uv run pytest tests -v`.
