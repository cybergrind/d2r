# OSD and potion automation

Live behavior accepted 2026-09-21. Run from a host desktop terminal at repo root:

```sh
uv run -m inventory_tracking.osd
# Read-only observation:
uv run -m inventory_tracking.osd --no-player-heal --no-merc-heal
# Input-free previews:
uv run -m inventory_tracking.osd --demo
uv run -m inventory_tracking.osd --demo-resources
```

Both controllers default on. Ctrl+C stops the process; restart after changing
code/config. `--text` prints alerts instead of opening GTK and retains automation
unless disabled. `--once` prints one sample and exits; it and all demos never
send keys. Once exits 0 for a health sample, 2 for unavailable state.

## Configuration and alerts

Edit [config.py](../config.py): `PLAYER_HEALING`/`MERC_HEALING` hold thresholds,
cooldowns, input freshness and acknowledgement timeout; `OSD` holds display/widget
settings; `READER` polling/reconnect; `INPUT` focus/key timing. `RESOURCE_READER`
contains supported-build resource settings, requiring revalidation after updates.

Default appearance is one transparent line, 16px, centered 130 logical pixels
above center. The window requests no keyboard interaction, an empty pointer input
region and no reserved space. It is desktop-wide, without focus-based hiding.
Empty alerts unmap the window; startup/stale/incomplete health and stock stay blank.

```sh
uv run -m inventory_tracking.osd --x 0 --y -130 --font-size 16 --monitor 0
uv run -m inventory_tracking.osd --rejuvenation-target 16 --healing-target 0
```

Offsets use logical pixels from center; monitor is zero-based (omitted means
compositor choice). Stock overrides are optional. Otherwise each four-slot column
gets its target family from the bottom potion, or lowest remaining potion if the
bottom is empty. Empty columns default to rejuvenation; other leading types create
no hp/juv target. All healing tiers count together, as do normal/full rejuvenations.
Only belt stock counts; an empty four-row belt shows `juv 16`.

| Alert | Default visibility |
| --- | --- |
| Player `current/max` | At or below 70% HP |
| Merc `~current/max` | Strictly below 65%; confirmed death shows `merc dead` |
| `juv N`, `hp N` | Positive potion deficits |
| Potion sent, recipient/key | One second after successful key delivery; acknowledgement is separate |
| `tele N/M repair` | Equipped Teleport staff missing charges in town |
| `tele N/M` | Below 20% charges outside town or with unknown location |
| `tp: N` | Missing portals once tome reaches <=16; stays until full at 20 |

The staff is tracked across both equipped weapon sets; inventory/stash staffs are
excluded. Unknown/absent resources hide their widget. Portal partial refill retains
the reminder; confirmed absence/replacement or session change resets it. The latch
is not persisted across OSD restarts. Exact rules: [widget contracts](design.md).

## Potion policy

| Recipient | Healing below | Rejuvenation below | Healing cooldown | Rejuvenation cooldown |
| --- | --- | --- | --- | --- |
| Player | 65% | 40% | 3 seconds | 1 second |
| Merc | 55% | 20% | 3 seconds | 3 seconds |

Thresholds are strict. Rejuvenation has emergency priority with healing fallback;
player is considered first and does not require a merc. Each sample identifies
potion types in all four bottom slots. Player uses plain column keys, merc uses
Shift+column. Potions above empty bottom slots are unusable.

Cooldowns are independent per actor/type, shared across columns and instances.
An actor waits for the selected item's disappearance from the belt; after two
seconds without acknowledgement it suspends until a verified new session or boot.
Pending/suspended state survives an OSD restart. Shared reservations prevent double
selection, key sequences are serialized, and the next sample must start after the
preceding delivery finishes. Corrupt persisted state refuses input.

Input requires fresh, complete living-player state, an eligible living recipient,
exact Niri app ID and X11 PID/start focus, usable stock and no physically held
conflicting keys. Key release is attempted even on failure. As authorized by the
user, **open in-game menus are not detected**. Legacy UI offsets were invalid.

## Runtime and diagnostics

GTK4, gtk4-layer-shell and introspection libraries are host dependencies;
PyGObject/pycairo are project dependencies installed by `uv run`. Input uses
`niri`, `xdotool`, libX11 and libXtst. Text mode requires no GTK window.

Omit `--pid` for rediscovery after restarts. The reader checks the supported disk
hash, discovers/captures once per attachment, and polls at 0.1-second intervals.
`--interval` changes polling delay; `--max-age` changes the display's two-second
freshness limit, independently of controller freshness.

`--output` defaults to `inventory_tracking/runs/osd/`. Each run contains `osd.log`,
`state.json`, latest `units.json`, and player/merc outcome reports. The output root
holds `potions.json` and `merc-input.lock`, shared by instances; keep them to retain
cooldowns/reservations/suspension. Legacy same-boot timestamps migrate conservatively.
Do not run an older implementation alongside this one. Temporary image captures
are removed on disconnect/normal shutdown. See [host probes](../README.md#host-probes)
for read-only evidence collection.

## Runtime structure

| Module | Responsibility |
| --- | --- |
| `models.py`, `state.py` | Domain records and validated research-to-state conversion |
| `belt.py`, `mercenary.py`, `resources.py` | Belt classification, owned merc and optional resource decoding |
| `reader.py` | Attachment, in-memory sampling, lifecycle, reports and observer delivery |
| `heal.py` | Health thresholds and potion priority |
| `potions.py` | Actor/type cooldown, consumption and suspension policy |
| `potion_ledger.py` | Locked persistent delivery/reservation state |
| `potion_input.py` | Focus/freshness checks and platform key delivery |
| `automation.py` | Player-first orchestration and uniform outcomes/events |
| `osd/presenter.py`, `osd/widgets/` | Stateful presentation, independent of GTK/input |
| `osd/window.py`, `osd/__main__.py` | Window and configured component assembly |

## Known limits

Local-player selection remains heuristic in multiplayer; belt capacity assumes
four rows. Injured merc HP estimates use a normalized fraction and can disagree
with the inventory panel: see [merc HP research](../merc_health_research.md).
Confirmed game-exit detection is unavailable; uncertain reads hide stale values
while preserving widget latches, and verified identity changes reset them.
Memory reads are sequential, not atomic. Build updates require layout revalidation.
