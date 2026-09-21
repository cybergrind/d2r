# OSD widget design — 2026-09-21

Widget implementation and supported-build live resource readers are enabled.
See implementation status below for controlled evidence and remaining visual checks.

The OSD should compose independent widgets. Each widget owns its visibility,
text and any display memory; the window owns placement and styling. Readers
provide facts, healing controllers provide action events, and widgets consume
both without reading memory or sending input.

Current `osd/state.py:display_lines` combines all visibility and formatting.
It is stateless and gates every reading on player health availability. The new
portal latch requires memory, and optional item reads must not suppress valid
health/belt data or disable healing.

## Widget contract and ownership

Use a small Python protocol, explicit construction, and an ordered widget list.
No plugin loader, registration decorators, event bus, or GTK widget subclasses.

```python
class Widget(Protocol):
    def update(self, snapshot: State) -> None: ...
    def render(self, *, now: float) -> tuple[str, ...]: ...
    def reset(self) -> None: ...
```

- `update` consumes each new reader sample, including unavailable observations.
  It validates the widget's dependencies and advances display state once per
  sample. It performs no I/O. Stateless widgets only retain their latest facts.
- `render` is side-effect-free: format the latest fresh facts and current display
  state, or return an empty tuple. Repeated rendering cannot change a latch.
  Time is injected for freshness and notification expiry.
- `reset` discards observations and display memory at a confirmed session change.
- `Presenter` owns the ordered widgets and delegates these operations. It flattens
  their output. It contains no health, charge, or refill rules.
- A short presenter lock serializes reader-thread updates and UI/text rendering.
  Widgets perform only bounded in-memory work under it. Never hold the reader's
  state lock while invoking the presenter or do GTK work under this lock.

Add an optional snapshot observer to `LiveReader`, called for every published
state after automation events are attached. The OSD supplies `presenter.update`;
other reader users need no presenter. This ensures the latch observes a sampled
16 followed by 17 even if no GUI refresh occurred between them. No design can
recover a threshold crossing the memory sampler itself never observed.

GUI, `--text`, `--once`, and demo use the same presenter instance per run.
The UI timer calls `presenter.render(now=...)`, retaining expiry even if the
reader stops publishing. The window joins segments with ` · ` and unmaps when
empty, as it does now. Rendering an empty frame must clear previously shown text.

Catch unexpected widget exceptions at the presenter boundary, log them without
repeated log spam, and suppress that widget's output until a successful update.
Do not reset its latch because of an exception. Errors must not stop other widgets
or propagate into the healing loop. Keep expected unavailable data out of the
exception path.

Initial widget order: potion notifications, player health, merc health, belt
shortages, teleport charges, portal tome. Each receives its own typed configuration
from `config.py`; shared font/position/refresh settings stay in `OSDConfig`.
Adding a widget means adding its class, config, tests, and one factory entry.

## Observations: unavailable is different from absent

Introduce a typed observation wrapper for the new optional domains with
`status` (`available`, `unavailable`), `sampled_at`, `value`, and diagnostic reason.
An available `None` means a complete search established absence. An unavailable
observation must not claim absence, zero stock, or full stock. No previous value
is given a new timestamp when a read fails.

New domain values:

- `TeleportCharges(item_id, current, maximum)` or confirmed absence. Validate
  integers, `maximum > 0`, and `0 <= current <= maximum`.
- `PortalTome(item_id, quantity, capacity)` or confirmed absence. Validate integer
  bounds; the initial supported capacity is 20.
- `Location(area_id, in_town)`; unavailable location is distinct from wilderness.

Each widget checks freshness of its own dependencies, rather than requiring
player HP globally. Reuse existing validated health/belt fields initially;
avoid rewriting healing state as part of this feature. Optional readers report
their failures separately from the core sample completeness gate.

Scope item searches to the identified local player's relevant equipment or
inventory. Exclude stash, cube, ground, vendors, and other owners. Multiple
matching candidates are unavailable with diagnostics until selection is defined;
never sum several tomes or guess which staff is intended.

A verified process/start/player identity change resets widget state. Temporary
unavailability preserves identity and latches but hides affected readings.
Confirmed game exit also resets state; an incomplete/empty traversal alone is
not proof of exit. If a same-process new-game boundary cannot yet be verified,
record that limitation rather than inventing a session ID.

## Existing widgets: preserve behavior

| Widget | Visibility and text |
|---|---|
| Player health | At or below 70%: `current/max` |
| Merc health | Below 65%: existing approximate HP text; confirmed death: `merc dead` |
| Belt shortages | Existing dynamic column rules and target overrides; positive deficits only: `juv N`, `hp N` |
| Potion notification | Successful send event for 1 second, retaining recipient and key |

Keep transparent text, current positioning, one line, and silent connecting or
unavailable states. Events retain their own timestamps and may remain visible
for their remaining lifetime during an unavailable sample. Reset on a confirmed
session change so an old recipient's notification cannot appear in a new game.

## Teleport staff widget

Track the unique equipped Teleport staff across both weapon sets, including while
its set is active. Controlled probes show the secondary staff moves between body
slots 4 and 11 when swapping. Weapon swapping must not make it appear absent.
If multiple equipped staffs qualify, publish unavailable rather than guessing.
Identify an actual
Teleport charged skill on the item, not merely a staff base or a skill bonus.
Do not require the player to carry one.

Proposed text and exact rules:

| Fresh facts | Output |
|---|---|
| No qualifying staff | Hidden |
| Charges unknown/invalid/stale | Hidden; diagnostic reason only |
| Full charges | Hidden |
| In town, any charges missing | `tele N/M repair` |
| Outside town, less than 20% remaining | `tele N/M` |
| Location unavailable, less than 20% remaining | `tele N/M` |
| Otherwise | Hidden |

Use `current * 100 < maximum * low_percent`: exactly 20% is not low.
Town repair advice requires fresh town evidence, but low charges do not.
Zero charges remain visible everywhere when a staff is present. Town plus low
charges produces one segment, not duplicate alerts. Repair clears the alert on
the next valid full-charge observation. Removal/replacement uses the new observed
item immediately. No latch is needed for this widget.

Config: `TeleportWidgetConfig(enabled=True, low_percent=20,
show_repair_in_town=True)`, with shared or explicitly overridden freshness limit.
Repair is advice only; this feature does not click vendors or repair equipment.

## Portal tome widget: refill latch

Config: `PortalWidgetConfig(enabled=True, trigger_remaining=16, capacity=20)`.
Validate `0 <= trigger_remaining < capacity`. Capacity must agree with the
validated reader value; unsupported capacities produce unavailable data.

The latch belongs to the current tome identity in the current session:

| Observation | Latch | Output |
|---|---|---|
| First valid quantity 17–20 | Off | Hidden |
| Quantity at or below 16 | On | `tp: 20 - quantity` (computed number) |
| Latched, refill to 17–19 | On | Updated missing count |
| Quantity reaches 20 | Off | Hidden |
| Unavailable/stale | Preserve | Hidden |
| Confirmed no tome | Reset | Hidden |
| Different tome or session | Reset, evaluate new quantity | According to new quantity |

Example: `20 → 17 → 16 → 18 → 19 → 20` renders
`hidden → hidden → tp: 4 → tp: 2 → tp: 1 → hidden`.
Trigger on `<=16`, so skipped samples and startup at 15 still work. Display in
town and outside town; only the staff repair message is town-specific.
An unavailable read between 16 and 18 must not clear the latch or show an old
missing count. A complete read showing absence does clear it.

Initial design keeps this presentation latch in memory. Restart at 18 therefore
starts hidden; restart at 16 or below latches immediately. Persistence across OSD
restarts is a separate extension if desired, using a dedicated display-state
store and verified identity, never the potion delivery ledger. Removing a tome
and returning it at 18 also starts hidden under the confirmed-absence rule.

## Reader evidence still needed

`units.describe_item` currently exposes ownership, inventory page, body location,
and coordinates. It does not read item charge stats or tome quantity.
`State` does not expose a validated area/town or weapon-set identity.

Before enabling either new widget against live memory:

1. Verify item/skill/stat identifiers against the local data dump. No guessed
   item codes or offsets. Inspect bounded item stats using the existing build gate.
2. Compare the staff tooltip with probe records, use one Teleport charge, swap
   weapons both ways, remove the staff, and repair it. Establish current/max
   encoding, ownership, set assignment and stable item identity.
3. Compare tome quantities before/after use and refill, including empty/full,
   movement to stash and removal. Establish quantity, capacity and inventory scope.
4. Establish player area through the current build's room/level data and verify
   town/non-town transitions. Do not reuse the known-invalid menu-state reader.
5. Record complete fixtures plus unavailable/mutating reads. Revalidate new
   pointers/identity/fields after reading, with bounded traversals. Fail only the
   affected optional observation when possible.

The user runs host probes; automated tests replay captured records. Widget
implementation and demo can proceed with synthetic observations while these
facts remain unavailable in live mode.

## Implementation sequence with red/green pytest

1. Preserve existing display cases as contract tests. Introduce the protocol,
   presenter and four existing widgets; prove equivalent output and empty-window
   clearing through GUI/text/demo integration. Keep legacy CLI overrides working.
2. Add optional observation models and nested widget configuration in `config.py`.
   Test absent versus unavailable, invalid bounds, freshness and dependency
   independence. No changes to healing thresholds or input policy.
3. Implement the portal latch against observation sequences. Test boundary 16,
   skipped counts, partial refill, full refill, failed reads, absence, replacement,
   session reset, startup and repeated rendering. Verify all reader samples reach
   the presenter even between GUI refreshes.
4. Implement teleport visibility against fixtures. Test exactly/below 20%, zero,
   full, town, unknown/stale location, absent staff and replacement. Check that
   an optional reader failure leaves existing widgets and healing operational.
5. Add and validate item/location probes separately, then promote verified
   decoders into the shared domain reader. Add regression tests from captured
   evidence and document build-specific layouts.
6. Wire live observations, diagnostic artifacts and demo sequences; run pytest,
   lint/format checks, then user-run visual checks for use/refill/repair/swap and
   a fully healthy empty OSD. Update handoff with actual validation status.

Suggested files: `osd/widgets/{base,health,belt,notifications,teleport,portal}.py`,
`osd/presenter.py`, and focused item/location domain readers as evidence dictates.
Tests mirror these paths under `tests/inventory_tracking/`. Retire the monolithic
formatter after all entry points use the presenter; do not retain two rule sets.

## Implementation status — 2026-09-21

Implemented the widget protocol, persistent synchronized presenter, GUI/text/demo
integration, existing display widgets, portal latch and teleport widget. Typed
optional observations distinguish confirmed absence from unavailable data;
configuration lives in `config.py`. Existing CLI overrides remain compatible.
The single-sample formatter now delegates to widgets rather than duplicating rules.

Added `--demo-resources` for deterministic visual review and `probe --resources`
for bounded read-only evidence collection. `resource_probe.py` records candidate
item arrays and location chains; `resources.py` performs scoped decoding with
independent validation gates. Controlled host probes established the supported
build's descriptors, weapon-slot remapping and town/field chain; `RESOURCE_READER`
now enables these sources. The live sampling path includes resource reads.

Tests exercise threshold/latch sequences, rendering purity, stale/unavailable
observations, replacement/session resets, reader-to-presenter delivery, widget
failure isolation, notification expiry/session boundaries, malformed optional
records, item mutation and location-pointer changes. Host evidence confirms
32/33→31/33 charges, 18→16 portals, staff slots 4→11, and town 109→field 111.
The restarted OSD also published 14 portals and 29/33 charges in area 110.
Partial/full refill, repair and removal have fixture coverage; those visual
transitions still need in-game confirmation. Confirmed game-exit detection remains unavailable;
identity changes reset widgets, while uncertain reads preserve latch state.

Verification: `uv run pytest tests -q` → **189 passed, 1 skipped**; Ruff lint and
format checks pass. Demo and probe CLI checks pass without accessing the game.
