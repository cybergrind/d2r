# OSD widget contracts

Implemented and live-accepted 2026-09-21. Operational defaults are in the
[runbook](README.md); this page records extension and state contracts.

## Composition

`Presenter` owns ordered widgets: notifications, player HP, merc HP, belt shortages,
Teleport charges, portal tome, Show Items warning, key stock, Consume, repair mark. `default_widgets(config)` builds that list explicitly;
each widget receives only its own nested config (`config.belt`, `config.portal`, …)
plus the window's `max_age` as an explicit argument, so `--max-age` reaches every
widget without being copied into nine configs. Widgets subclass
`SampleWidget[ConfigType]` and implement:

- `update(snapshot)`: consume a domain state.
- `render(now=...)`: return text segments.
- `reset()`: clear retained display state.

Widgets perform no I/O. Update consumes facts/events and advances display state;
render is pure and checks freshness/expiry. Repeated rendering cannot advance
display state. Reset discards observations/display memory on verified session change.

The reader calls `presenter.update` for every published sample, after automation
events are attached and outside its state lock. A presenter lock serializes updates
and rendering. GUI/text/demo share a persistent presenter and display the latest
accepted resource sample. The UI timer still expires notifications if reading stops.

A widget may also implement `mark(now=...)` returning a `Mark` (or None): a square
highlight in game-window units that `Presenter.marks` collects with the same
isolation as `render`. The window draws marks on a separate click-through surface;
text mode prints `<kind> mark`.

Widget exceptions are logged without repeated identical messages and suppress only
the affected widget until successful update. They do not stop healing. The window joins segments with ` · ` and clears/unmaps when empty.
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

As of 2026-09-27, the reminder appears only in town, when the town portal tome
has 3 or fewer scrolls. Defaults: capacity 20, inclusive trigger 3; configuration
requires `0 <= trigger < capacity` and matching reader capacity. Town evidence
follows the Teleport repair rule: a fresh location observation with `in_town`.

| Fresh facts | Output |
| --- | --- |
| In town, 0–3 remaining | `tp: 20 - quantity` (missing scroll count) |
| 4 or more remaining, including partial refill | Hidden |
| Outside town, or location unavailable/stale | Hidden |
| Unavailable, stale, or absent tome | Hidden |
| New tome/session | Evaluate its current quantity |

In town, `20 → 4 → 3 → 2 → 0 → 4` displays
`hidden → hidden → tp: 17 → tp: 18 → tp: 20 → hidden`; the same quantities
outside town display nothing. There is no refill latch. This threshold uses the
book quantity; the swap-weapon Teleport charge widget has its own independent rules.
Before 2026-09-27 the trigger was 2 and the reminder showed anywhere.

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

## Repair mark widget

`State.shop` is an `Observation[ShopPanel]` read by `tracking/shop_panel.py` after
the build gate: the NPC shop panel flag (`tracking/panels.py`) plus, only while it
is set, the vendor units in the sampled monster group whose shop grids hold items
(`collection/capture.read_owner_grids`). Trade generates a vendor's stock and closing
Trade releases it (shop/README.md), so exactly one loaded vendor identifies the open
panel. `ShopPanel(open, vendor, smith)`; `smith` is true for Charsi, Fara, Hratli,
Halbu and Larzuk (monstats ids in `SMITHS`). No loaded vendor, several loaded
vendors, unreadable flags/grids or a panel that closes during the read are
unavailable, never a guess.

| Fresh facts | Mark |
| --- | --- |
| Smith panel open, equipped Teleport staff below maximum charges | `repair` square from `OSD.repair_mark` |
| Full charges, absent/unavailable staff | None |
| Non-smith vendor, closed panel, unavailable/stale shop observation | None |

Geometry: `center_x`/`center_y`/`size` are fractions of the game window height,
x from the window's left edge and y from its bottom edge, because the game scales
its UI with the window height and anchors the vendor panel to the left. The window
anchors the mark surface to the output's bottom-left corner with margins derived from
`niri msg focused-window`'s `layout.window_size`, so a game window tiled under a top
bar is covered exactly; other placements shift the mark by the window's offset.
When the game is not focused the mark is hidden (no geometry); `--demo-repair`
falls back to the first output's full geometry so the preview can be seen without
a game. The mark is redrawn every refresh with a sine pulse of `pulse_seconds`.
