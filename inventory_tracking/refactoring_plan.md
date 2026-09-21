# Healing and OSD refactoring plan — 2026-09-21

Status: implementation steps 1–7 completed locally with red/green pytest; user-run live validation remains pending. The design below records the original plan.

## Pain points found in the current code

| Area | Current problem | Improvement |
| --- | --- | --- |
| `merc_heal.py` | `MercHealController` serves both actors, selects thresholds from globals, chooses potions, manages cooldowns, and tracks acknowledgement/suspension. | `HealController` receives actor healing configuration and a `PotionsController`; split health policy from potion execution. |
| `merc_input.py` | `MercInput` also serves both actors and repeats cooldown policy, inferring potion type from a column. | Rename to generic input delivery; receive an explicit potion request. Keep platform checks here, policy elsewhere. |
| Cooldowns | Controller has one `last_attempt`; backend has one persisted `sent_at` for every actor/type. Player rejuvenation is a special case in both places. | Explicit per-actor configuration with a potion-type-to-cooldown map and one authoritative cooldown implementation. |
| Configuration | Healing globals, OSD literals, CLI defaults, polling/reconnect timing, and key timing are scattered. | Replace `healing_config.py` with `config.py`, using grouped dataclasses and explicit player/merc defaults. |
| `osd/state.py` | Contains research parsing, player selection, belt validation/classification, shortages, input eligibility, notification state, and formatting. Automation depends on an OSD-owned model. | Move game state and snapshot conversion out of OSD; separate belt logic and formatting. |
| Potion representation | Class IDs are classified repeatedly; types alternate between cell field names and display strings. Tuple identity selects the rejuvenation cooldown. | A `PotionType` enum and named belt-item/request records; use display labels only when rendering. |
| Belt counts | Dynamic shortages count all healing/rejuvenation tiers, while explicit target overrides count only super healing/full rejuvenation. Synthetic states silently fall back to fixed 8/8 targets. | One classification/counting path; explicit overrides count the same potion families. Give demo states real belt contents. |
| `osd/reader.py` | Owns attachment, sampling, JSON rereading, healing orchestration, notifications, threading, and reports. Player/merc paths and diagnostics differ. | Extract sampling and automation responsibilities; iterate an explicit player-first controller sequence with uniform results/reports. |
| Execution results | A boolean cannot explain cooldown, unavailable stock, focus rejection, or acknowledgement waiting. Notifications are bolted on via dynamic attribute names. | Small typed outcomes and potion-sent events, consumed by reports and OSD. Distinguish key delivery from consumption confirmation. |
| Shared belt | Independent cooldowns alone would permit two actors to select the same item from a single sample. Pending acknowledgements currently belong to separate controllers. | Shared item reservation and cross-instance coordination, without a global healing cooldown. |
| Lifecycle | Cooldown, session reset, suspension, and pending-item state are intertwined. A missing merc returns before pending acknowledgement handling. | Explicit lifecycle rules; process pending actions separately from deciding whether an actor currently needs healing. |
| Test structure | Input tests import a fixture builder from controller tests; integration behavior lives in OSD state tests; mocks rely on legacy names/default merc arguments. | Shared fixtures in `conftest.py` where useful; tests mirror the new modules and assert behavior through injected clocks/input. |
| Documentation | Several names/docstrings still describe merc-only or observation-only behavior; historical handoff content obscures current contracts. | Update current reference docs and link the migration plan; retain research evidence separately. |

## Proposed responsibilities

- `config.py`: `HealingConfig`, `OSDConfig`, `ReaderConfig`, and `InputConfig`, plus named defaults. CLI overrides produce configuration objects once at startup. Validate finite durations, threshold ranges/order, and complete potion maps. Use immutable configuration, including defensive copies/read-only mappings where necessary; a frozen dataclass alone does not freeze a dict.
- `models.py`: shared `Actor`, `PotionType`, health/sample, belt-item, potion-request and result/event records. Keep records limited to actual boundaries; avoid a generic framework.
- `belt.py`: verified class-ID classification, usable bottom-slot selection, family counts, and dynamic column shortages.
- `state.py`: research snapshot conversion and validation into the domain sample. No GTK, OSD formatting, or potion delivery.
- `heal.py`: `HealController(config, potions)` checks actor health and orders eligible potion choices. Rejuvenation retains emergency priority; healing remains the fallback when rejuvenation stock is unavailable. Actor extraction is explicit, including merc fraction and death status.
- `potions.py`: one `PotionsController` per actor, configured with that actor's cooldown map. Own cooldown eligibility, pending consumption, timeout/suspension, and requests to the shared delivery coordinator. Return outcomes instead of requiring the reader to inspect mutable internals.
- `potion_input.py`: focus/process identity/freshness checks and plain/Shift key delivery, guaranteed release, and shared serialization. A small coordinator/ledger handles cross-instance reservations and cooldown persistence; it uses the same policy supplied to the actor controllers, not a second set of hardcoded rules.
- `reader.py`: attachment, sample acquisition, reconnect, and lifecycle. Return in-memory snapshots from the sampling path; JSON remains diagnostic output rather than the internal transport.
- `automation.py`: player-first orchestration, shared belt reservations, and uniform actor status/events. This is where simultaneous actor requests are reconciled.
- `osd/state.py`: presentation only: sample plus events and `OSDConfig` to text. `osd/window.py` handles GTK; `osd/__main__.py` composes configured components.

Keep binary layout constants and verified class IDs alongside their reader/classification code. They are build facts, not user configuration options. All adjustable runtime defaults belong in `config.py`.

## Configuration contract

Each actor gets a complete `HealingConfig`: actor, enabled flag, thresholds by potion type, cooldowns by potion type, sample maximum age, and consumption timeout. No missing-key fallback to another actor's defaults.

| Actor | Healing threshold | Rejuvenation threshold | Healing cooldown | Rejuvenation cooldown |
| --- | --- | --- | --- | --- |
| Player | <65% | <40% | 3 seconds | 1 second |
| Merc | <55% | <20% | 3 seconds | 3 seconds |

Proposed cooldown semantics: independently track each `(actor, potion type)` across columns and application instances. For example, player healing does not delay merc healing or player rejuvenation. This is an intentional behavior change from the current shared last-potion timestamp, not just a rename. Record and test it explicitly before migration.

Pending consumption still blocks another potion for that actor until acknowledged. Reserve the selected item globally so another actor/instance cannot reuse it. Serialize key sequences, and require a fresh belt observation after delivery before another actor selects stock; independent cooldowns do not make a pre-delivery snapshot current.

Keep conservative reservation on uncertain/failed delivery to avoid retry bursts. Distinguish rejection before input from partial/uncertain key delivery in results. On timeout, suspend that actor rather than resend. Reset pending/suspension on a verified session change, retain applicable cooldown history, and discard another boot's monotonic timestamps. Persist actor/type keys and process/session/item identity where appropriate. Handle the old single-timestamp ledger conservatively during migration; do not silently bypass existing protection by merely renaming its file.

`OSDConfig` includes player visibility at/below 70%, merc visibility strictly below 65%, one-second notifications, two-second display freshness, 16px font, font family/weight/color, center offsets `(0, -130)`, monitor, refresh interval, and optional stock targets. Preserve transparent text, click-through behavior, and a hidden window when empty. `ReaderConfig` covers polling/reconnect/shutdown timings; `InputConfig` covers focus query timeout, game app ID, and key hold duration. Keep read freshness and display freshness distinct and clearly named.

## Implementation sequence

1. **Capture contracts.** Run the existing pytest suite. Add meaningful tests for injected non-default actor settings, independent actor/type cooldowns, simultaneous demand for one belt item, and cross-instance coordination. Preserve existing boundary/death/focus/acknowledgement cases. Mark intentional changes in cooldown and override-count semantics clearly.
2. **Centralize configuration.** Introduce typed potion/actor identifiers and validated dataclasses in `config.py`; replace scattered runtime defaults and CLI help references. Preserve existing behavior until the explicit cooldown migration. Ensure GUI and text mode receive the same resolved settings.
3. **Separate domain state and belt logic.** Move snapshot parsing out of OSD, unify classification/counting, replace untyped tuples at public boundaries, and remove synthetic 8/8 fallback. Move the associated tests to matching paths.
4. **Extract potion execution.** Build per-actor `PotionsController` with injected clock/delivery, typed outcomes, acknowledgement lifecycle, and shared reservation/ledger support. Introduce the independent cooldown semantics here. Test restart, partial delivery, stale samples, and multiple instances before wiring live input.
5. **Simplify healing and input.** Rename/extract `HealController` and generic input module. Inject configuration and `PotionsController`; remove target-specific cooldown branches, tuple-identity decisions, and legacy default-merc calling conventions.
6. **Simplify runtime and OSD.** Extract reader/automation coordination, stop rereading JSON each tick, publish uniform diagnostics, and render typed notification events. Preserve player-first priority and sample invalidation on reconnect.
7. **Finish migration.** Remove obsolete modules/imports, update run instructions and handoff, run pytest plus lint/format checks, then perform user-run live validation. Stage or commit only when requested.

Each step should leave runnable code and a green suite; avoid a single large rewrite. No compatibility aliases for internal merc-only names unless a real external caller is found.

## Acceptance and limits

- Non-default injected settings change both decision and delivery behavior without editing controller code.
- Tests cover exact threshold boundaries, emergency priority and stock fallback, all bottom columns, all supported potion tiers, per-actor/type cooldown boundaries, and shared-item contention.
- No input for stale/incomplete samples, dead/unknown actor, wrong focus/process, held keys, unavailable bottom stock, pending acknowledgement, or suspended actor. Player can heal with no merc. Key release remains guaranteed on failures.
- Restart/session tests cover invalid samples not resetting suspension, verified identity changes, persisted cooldowns, and old ledger migration.
- OSD tests preserve blank startup/stale/healthy behavior, refill clearing, merc visibility, and one-second delivery messages across missing samples.
- Use pytest under mirrored `tests/` paths, with deterministic clocks and mocked platform input. Run the full suite and applicable lint/format checks; mocks do not establish in-game correctness.
- Live checks: independent actor settings, switching belt families, potion consumption and acknowledgement, and unchanged OSD placement/visibility. Agents do not inject test keys into the running game.
- Out of scope: exact merc HP research, menu detection, multiplayer local-player selection, and discovering belt capacity. Preserve the authorized no-menu-detection policy and current four-row assumption; do not present unresolved research as fixed by restructuring.


## Completion log — 2026-09-21

1. **Contracts:** baseline 107 passed/1 skipped. Added failing contracts for new
   configuration, family counting, controller injection/independence, and shared
   belt handling before implementing those changes.
2. **Configuration:** `config.py` has complete immutable actor dataclasses and
   OSD/reader/input defaults. Invalid ranges/durations/maps are rejected; CLI
   resolves overrides once. Removed `healing_config.py`.
3. **Domain:** moved snapshot conversion to `state.py`, identifiers/records to
   `models.py`, classification/counting to `belt.py`. Removed duplicate stored
   stock counts and synthetic 8/8 fallback. Explicit targets count all tiers.
4. **Potions:** independent actor/type cooldowns, acknowledgement/suspension,
   shared reservations and persisted restart behavior implemented. Atomic ledger
   publication preserves old data on write failure. Legacy timestamps migrate
   conservatively; malformed ledger state refuses input.
5. **Healing/input:** `HealController(config, potions)` contains health policy;
   `PotionInput` performs platform delivery without cooldown logic. Legacy merc
   names removed. Red/green tests also caught sample-during-delivery acceptance
   and silent key-release failure; both are fixed.
6. **Runtime/OSD:** player-first `Automation` emits typed outcomes/events;
   `LiveReader` samples in memory and publishes uniform reports. OSD consumes
   domain state with resolved settings, preserving one-second notifications
   through incomplete reads. Tests confirm demo/once cannot deliver keys.
7. **Validation/docs:** 151 passed, 1 skipped. Full lint/format and diff checks;
   demo CLI produces `PREVIEW · juv 3 · hp 1`. Current README and handoff updated.
   Required changes staged at the user’s request; no commit made.

Cross-instance serialization resides in `potion_ledger.py`, separate from the
platform input adapter; policy remains solely in `PotionsController`. Reports
contain outcome/event values rather than exposing controller internals. Latest
per-actor events travel with domain state for consistent reader/OSD publication.

Live follow-up remains: restart OSD after stopping the older implementation;
verify configured player/merc thresholds, independent cooldowns, belt-family
switches, consumption acknowledgement, and OSD messages/placement. No real input
was injected by this implementation/test session. Exact merc HP, other belt
capacities, menu detection and multiplayer selection remain outside this change.
