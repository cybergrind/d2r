# Inventory tracking handoff

Updated 2026-09-21. **Delivered and live-accepted:** the user confirmed “live
verification is done: everything seems working.” No delivery task remains open.

Start at [inventory_tracking/README.md](inventory_tracking/README.md), which links
operation, layout evidence, widget contracts and external projects. Run on host:

```sh
uv run -m inventory_tracking.osd
# Observation only:
uv run -m inventory_tracking.osd --no-player-heal --no-merc-heal
```

Both player and merc automation default on. Exact settings and persisted input
state are documented once in the [runbook](inventory_tracking/osd/README.md).

## Remaining research

- [Merc HP comparison](inventory_tracking/merc_health_research.md): our normalized
  formula matches d2go; legacy update/cache paths are promising leads for the
  panel discrepancy. No replacement formula/offset or new live evidence yet.
- Other belt capacities and robust multiplayer player selection remain unsupported.
- Menu detection is absent by user authorization; confirmed game-exit detection
  is unavailable. Existing focus/freshness/identity/input checks remain required.

## Structure pass — 2026-09-21

[followup_plan.md](inventory_tracking/followup_plan.md) steps 0–10 are implemented:
ledger writes only on change and is schema version 2 with a pydantic model;
`State` is keyword-only and composed of `SessionIdentity`, `PlayerHealth` and
`BeltSnapshot` with `health_for(actor)`; config is pydantic (`with_overrides`);
typed widget configs and an explicit factory; `layout.py` constants; `FocusProbe`
and `X11Keyboard` collaborators; pyrefly runs at preset `default` with 0 errors.
Default thresholds, cooldowns, OSD text and input guards are unchanged. One
behavior change on migration: the retired 3-second shared cooldown is folded
into per-type cooldowns, so a migrated timestamp follows each type's own
cooldown. Validation: 239 passed, 1 skipped, pre-commit green. Not re-verified
in-game after the pass. No commit made.

## Cleanup — 2026-09-21

Removed invalid unused UI scanning/sampling, the test-only formatter adapter,
and an unused widget protocol declaration. Display checks now exercise the live
Presenter; two tests of the discarded UI implementation and one duplicate target
case were removed. Ledger migration and safety/race coverage remain.

Consolidated operation/layout/widget docs and removed the completed refactoring
plan and duplicated historical handoffs. Unique build/probe evidence remains in
[layout_notes.md](inventory_tracking/layout_notes.md); external project links and
merc research remain available. No runtime defaults or healing policy changed.

Validation: **186 passed, 1 skipped**, Ruff lint/format passed. The skip is the
agent-environment-denied memory syscall test. Cleanup was not separately tested
in-game; prior live acceptance covers the delivered behavior. No commit made.
