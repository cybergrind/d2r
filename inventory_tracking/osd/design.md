# OSD widget contracts

Implemented and live-accepted 2026-09-21. Operational defaults are in the
[runbook](README.md); this page records extension and state contracts.

## Composition

`Presenter` owns ordered widgets: notifications, player HP, merc HP, belt shortages,
Teleport charges, portal tome, Show Items warning, key stock. `default_widgets(config)` builds that list explicitly;
each widget receives only its own nested config (`config.belt`, `config.portal`, …)
plus the window's `max_age` as an explicit argument, so `--max-age` reaches every
widget without being copied into eight configs. Widgets subclass
`SampleWidget[ConfigType]` and implement:

- `update(snapshot)`: consume a domain state.
- `render(now=...)`: return text segments.
- `reset()`: clear retained display state.

Widgets perform no I/O. Update consumes facts/events and advances display state;
render is pure and checks freshness/expiry. Repeated rendering cannot advance a
latch. Reset discards observations/display memory on verified session change.

The reader calls `presenter.update` for every published sample, after automation
events are attached and outside its state lock. A presenter lock serializes updates
and rendering. GUI/text/demo share a persistent presenter, ensuring sampled portal
threshold crossings are retained even between screen refreshes. Unsampled crossings
cannot be recovered. The UI timer still expires notifications if reading stops.

Widget exceptions are logged without repeated identical messages and suppress only
the affected widget until successful update. They neither clear its latch nor stop
healing. The window joins segments with ` · ` and clears/unmaps when empty.
To add a widget: subclass `SampleWidget` with a typed config, add that config as a
field of `OSDConfig`, add one `default_widgets` line, and test observable behavior
under `tests/inventory_tracking/osd/`. `OSDConfig` itself gains no widget-specific
fields.

## Observation and identity rules

`Observation` carries timestamp, available/unavailable status, value and reason.
Available `None` is confirmed absence; unavailable is not absence or zero. Failed
reads never refresh the timestamp of an old value. Each optional widget checks its
own dependencies; resource failures do not gate valid player health/belt readings.

Owned-item selection excludes stash/cube/vendors/ground/other owners. Multiple
matching tomes or equipped charged staffs yield unavailable instead of guessing.
Identity is `State.session` (`SessionIdentity`: process PID/start/player ID; the
ledger's merc record also binds the hireling). A sample without a session is
incomplete and never fresh. A verified change of the core identity resets display
state and clears automation's delivery events; temporary unavailable identity
preserves both while stale output stays hidden.
The current reader cannot positively establish game exit.

Notifications use delivery timestamps, survive unavailable samples for their
remaining lifetime, and reset on identity change. Their text confirms key delivery,
not consumption. Existing health and shortage thresholds are in the runbook.

## Teleport widget

Select one owned, equipped staff with the actual charged Teleport skill across
both weapon sets (body slots 4/5/11/12). Swapping does not imply absence.

| Fresh facts | Output |
| --- | --- |
| Absent, unavailable, invalid, stale or full | Hidden |
| In town, charges missing | `tele N/M repair` |
| Elsewhere or location unknown, below low threshold | `tele N/M` |
| Otherwise | Hidden |

Default low threshold is strictly below 20%, compared without rounding. Zero
charges show anywhere. Town advice requires fresh town evidence; low-charge output
does not. Repair/replacement applies on the next valid observation; no latch.

## Portal widget

The latch belongs to the current tome and session. Defaults: capacity 20, trigger
19; configuration requires `0 <= trigger < capacity` and matching reader capacity.

| Observation | Latch/output |
| --- | --- |
| Full 20 | Off/hidden |
| <=19 | On/`tp: 20 - quantity` (computed number) |
| Partial refill below 20 | On/updated missing count |
| Unavailable or stale | Preserve/hidden |
| Confirmed absence | Reset/hidden |
| New tome/session | Reset, then evaluate new quantity |

`20 → 17 → 16 → 18 → 19 → 20` displays
`hidden → tp: 3 → tp: 4 → tp: 2 → tp: 1 → hidden`.
As of 2026-09-21, even one missing scroll shows immediately, including on startup
or tome/session change. A lower configured trigger retains the optional latch:
once reached, the reminder stays until full. No persistence is implied by
potion-ledger state.

## Show Items widget

`State.show_items` is an optional boolean observation, acquired only after the
live reader accepts the executable hash and establishes an in-game session.
The byte is read twice with process identity and mapping checks. Invalid values,
read failures or detected changes yield unavailable without disabling healing.

Fresh false displays `loot is not enabled`; true, unknown, stale, future or
out-of-game state displays nothing. No toggle count or cross-game latch is kept.
This reflects Show Items, not whether a filter profile is enabled. Controlled
capture evidence and the build-specific RVA are in [layout notes](../layout_notes.md).

## Keys widget

`State.keys` carries the total ordinary-key quantity in owned main-inventory
stacks. Fresh counts strictly below `OSD.key_stock.low_count` (default 5) display
`keys: N`, including zero. At least 5, unknown, stale, future or out-of-game samples
hide the warning. There is no refill latch.

The resource collector marks `keys_sampled` so older snapshots that never scanned
keys cannot be mistaken for zero stock. Quantity stat 70 is read from the separately
verified key-stat descriptor. Each stack must have exactly one plausible quantity;
duplicate item IDs or unreadable stacks make the total unavailable. Stash, cube,
ground, equipped and other-owner items do not contribute.
