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
cooldowns, input freshness and acknowledgement timeout; `OSD` holds window settings
plus one nested config per widget (`notifications`, `player_health`, `merc_health`,
`belt`, `teleport`, `portal`, `loot`, `key_stock`, `consume`); `READER` polling/reconnect; `INPUT` focus/key timing, actor modifier `bindings` and `column_keys`.
`RESOURCE_READER` contains supported-build resource settings, requiring revalidation
after updates. Configs are frozen, strictly typed pydantic models: derive variants
with `with_overrides(model, **changes)`, which re-validates; invalid values raise
`ValueError` at import or CLI parse time, never at first use.

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
| `tp: N` | Missing portals only when the tome has fewer than 3 scrolls; hides again at 3 or more |
| `keys: N` | Fewer than 5 ordinary keys in character inventory; 5 or more stays hidden |
| `consume: ~15s left` | Estimated expiry approaching, using observed activation and the applied skill level |
| `consume: no longer active` | Observed removal after being active; shown for 30 seconds by default |
| `loot is not enabled` | Show Items is confirmed OFF in a fresh in-game sample |

Key counts sum all owned inventory stacks, excluding stash, cube, ground and
vendor items. A confirmed empty inventory shows `keys: 0`; unavailable readings
hide the warning. `OSD.key_stock.low_count` sets the strict threshold.

Consume uses the level stored on the applied effect, so restoring +skills gear
after casting does not extend the timer. `OSD.consume.warn_before_seconds`
defaults to 15; `OSD.consume.ended_notice_seconds` defaults to 30. Set
`OSD.consume.enabled=False` to disable it. Restart the OSD after editing config.
If the OSD attaches mid-buff or cannot establish a start and level, it shows only
the removal notice. That notice also covers cancellation by summoning a demon.
It clears early on reapplication and does not repeat while Consume stays absent.
Timers are best-effort estimates, not a game-provided countdown. While the game
still reports an active buff after the estimate, the display says
`consume: recast (estimated timer elapsed)`; it does not claim confirmed expiry.
Unavailable/stale reads hide the message, uncertain tracking drops the estimate,
and death/session changes clear tracking. An indistinguishable active-to-active
refresh can still make an estimate wrong; restart mid-buff cannot recover its age.

The loot warning reads the Show Items state, not whether a loot-filter profile is
selected. Enabling Show Items clears it; unknown/stale readings hide it. The memory
location is verified for the supported executable hash only.

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
potion types in all four bottom slots and drains the fullest column of the chosen
type first (ties go to the lowest column). Player uses plain column keys, merc uses
Shift+column. Potions above empty bottom slots are unusable.

Cooldowns are independent per actor/type, shared across columns and instances.
An actor waits for the selected item's disappearance from the belt; after two
seconds without acknowledgement it suspends until a verified new session or boot.
Pending/suspended state survives an OSD restart. Shared reservations prevent double
selection, key sequences are serialized, and the next sample must start after the
preceding delivery finishes. Corrupt persisted state refuses input.

Input requires fresh, complete living-player state, an eligible living recipient,
exact Niri app ID and X11 PID/start focus, usable stock and no physically held
keys. Key release is attempted even on failure. Focus loss, a held key or sample
expiry before key-down returns `rejected` with a reason, including after the
reservation is saved; that clean refusal rolls back the reservation and retains
the attempt cooldown. Unexpected input/cleanup errors suspend the actor. As authorized by the
user, **open in-game menus are not detected**. Legacy UI offsets were invalid.

## Runtime and diagnostics

GTK4, gtk4-layer-shell and introspection libraries are host dependencies;
PyGObject/pycairo are project dependencies installed by `uv run`. Input uses
`niri`, libX11 and libXtst. `xdotool` was used for the completed owner comparison below and is no longer a runtime dependency. Text mode requires no GTK window.

Omit `--pid` for rediscovery after restarts. The reader checks the supported disk
hash, discovers/captures once per attachment, and polls at 0.1-second intervals.
`--interval` changes polling delay; `--max-age` changes the display's two-second
freshness limit, independently of controller freshness.

`--output` defaults to `inventory_tracking/runs/osd/`. Each run contains `osd.log`,
`state.json`, latest `units.json`, and `player-heal.json`/`merc-heal.json` outcome reports. Each outcome includes
`reason` (`unfocused`, `no_display`, `unknown_key`, `key_held`, `stale`) for
`rejected`, otherwise null. The output root
holds `potions.json` (schema version 2) and `potions.lock`, shared by instances; keep
them to retain cooldowns/reservations/suspension. The ledger is rewritten only when a
step changed it, so it stays quiet while idle. Version 0/1 files migrate on first
use: the retired shared timestamp seeds every per-type cooldown. The old
`merc-input.lock` keeps serializing instances started in the same boot; after a
reboot only `potions.lock` is used.
Do not run an older implementation alongside this one. Temporary image captures
are removed on disconnect/normal shutdown. See [host probes](../README.md#host-probes)
for read-only evidence collection.

### Input guard check

```sh
uv run -m inventory_tracking.input --check
uv run -m inventory_tracking.input --check --pid 12345 --output inventory_tracking/runs/input-check.json
```

This opens and closes one attempt per actor/column and **never presses keys**.
Each JSON line reports the app id, X11 owner PID/identity match, configured
keycodes, held-key guard, result, display-open time and total elapsed milliseconds. Guards stop at the first
refusal; null means a value was not checked, not success. Exit 0 means all eight
attempts were ready, 2 means a refusal/input error, and 1 means process discovery
or identity failed. This checks input readiness, not health/belt policy.

The optional report is published atomically with `state: complete` (checks ran,
even when refused) or `failed`, timestamps and `exit_code`, so a host run can be
reviewed from the shared filesystem. To check game focus, start the command with
a short shell delay and switch to the game before the check begins:

```sh
sleep 3
uv run -m inventory_tracking.input --check --output inventory_tracking/runs/input-game.json
```

Repeat with terminal focus and a different output filename; expect `unfocused`.
Do not infer host acceptance from unit tests or demo output.

### Native X11 owner verification — passed

2026-09-21: the owner check now reads `_NET_WM_PID` from the focused X11 window
or up to 16 ancestors on the attempt's existing connection. Exact executable,
PID and start-time matching remain required. A scoped X error handler makes a
disappearing window an ownership refusal; property and child buffers are freed.
The compositor check still runs on every entry and send.

Host verification passed at 2026-09-21 13:05 UTC: eight game checks ready with
PID 2911790 matching xdotool; eight kitty checks refused, no X11 owner and no
xdotool PID output. Reports: `runs/input-game.json` and
`runs/input-terminal.json`. Display-open median was about 0.18 ms, with one
5.08 ms game outlier. The original comparison procedure is retained below. With D2R running,
paste this whole block into a desktop terminal, then focus the game during the
delay. Keep focus unchanged until both commands finish:

```sh
sleep 3
uv run -m inventory_tracking.input --check --output inventory_tracking/runs/input-game.json
xdotool getwindowfocus getwindowpid > inventory_tracking/runs/input-game-xdotool.txt
```

Repeat with terminal focus, changing filenames to `input-terminal.json` and
`input-terminal-xdotool.txt`. Game focus should produce eight `ready` results
with the game's PID; terminal focus must produce `unfocused` even if XWayland's
last focused window still belongs to the game. Compare each report's
`owner_pid` with the corresponding xdotool output. Reports are read-only checks;
no game key is sent. The agent can inspect the completed shared reports directly.

### Focus tracker verification — passed

FocusTracker now owns a daemon `niri msg --json event-stream` subprocess. It
initializes focus from the complete WindowsChanged snapshot's `is_focused` flags,
then applies window/focus changes. A select loop wakes within 0.25 s; unchanged
focus remains valid while its heartbeat is at most one second old. Partial or
backlogged input is not trusted. EOF, process exit or invalid/unknown events
invalidate the cache, retry at 0.5–5 s backoff, and require a fresh snapshot.
Known unrelated events do not invalidate focus. Missing/stalled state falls back
to the one-shot query; exact X11 executable/PID/start ownership is always checked.
The subprocess is terminated and reaped at OSD/CLI shutdown.

The initialization rule corrects the draft plan: Niri's
[state replication](https://raw.githubusercontent.com/YaLTeR/niri/main/niri-ipc/src/state.rs)
does not include a separate initial WindowFocusChanged event.

```sh
uv run -m inventory_tracking.input --check --duration 20 --output inventory_tracking/runs/input-tracker.json > inventory_tracking/runs/input-tracker.log
```

During the 20-second run, switch between game and terminal a few times, leaving
each focused and the keyboard released for several seconds. No keys are sent.
The output report should show `source: cache`, healthy `heartbeat_age`, and
`ready` results only with game focus and exact identity. Transition-time
`key_held` refusals are expected while a switching shortcut is held.
Exit 2 is expected because the trace includes terminal refusals.

Diagnostics include `changed_at` (cache focus update), `checked_at` (guard
start), and `update_ms` (time from reading the event batch to updating the
cache). These measure processing and observation delay, not physical switch
latency: Niri's focus event has no event-generation timestamp. The default
check interval is 0.1 s.
`--interval` changes that interval, `--duration` is bounded to 300 seconds,
and omitting duration still performs one pass. The optional JSON report gets
its completion marker after all checks and tracker shutdown.

Host result, 2026-09-21 13:17:10–13:17:30 UTC: 1,560 guard checks all used the
cache on one stream connection, without errors or fallback. All 648 kitty
checks returned `unfocused`; 912 game checks comprised 864 `key_held` refusals
and 48 `ready` results, all with exact PID/start identity and no held key for
ready results. No input was sent. The large held-key count records X11's held
state; this trace does not identify which key was down.

Across 18 focus transitions, the next guard observed the cache change after
19.7–87.9 ms at the configured 100 ms polling interval. Event-batch processing
was 0.038–0.141 ms; heartbeat age never exceeded 0.251 s. These are observation
and processing delays, not measured physical-switch latency. Evidence remains
in `runs/input-tracker.json` and `runs/input-tracker.log`.

Step 7 is closed as unnecessary: display-open time was median 0.130 ms,
p95 0.296 ms, max 2.720 ms. Total guard time was median 0.316 ms and p95
0.678 ms. Keep the simpler per-attempt connection lifecycle; revisit reuse
only if later host measurements show a sustained multi-millisecond opening cost.

## Runtime structure

| Module | Responsibility |
| --- | --- |
| `layout.py` | Verified build facts: executable hash, class/stat IDs, belt geometry, town IDs |
| `config.py` | Pydantic settings models (`HealingConfig`, `OSDConfig` + widget configs, `ReaderConfig`, `InputConfig`, `ResourceReaderConfig`) and `with_overrides` |
| `models.py` | `State` (`session`, `health`, `belt`, `merc`, observations, events), `SessionIdentity`, `PlayerHealth`, `BeltSnapshot`, `Observation`, outcomes |
| `state.py` | Research snapshot → `State`: player selection, identity, belt walk as separate helpers |
| `belt.py`, `mercenary.py`, `resources.py` | Belt classification, owned merc and optional resource decoding |
| `reader.py` | Attachment, in-memory sampling, lifecycle, reports and observer delivery |
| `heal.py` | Health thresholds and potion priority via `State.health_for(actor)` |
| `potions.py` | Actor/type cooldown, consumption and suspension policy |
| `potion_ledger.py` | Locked, pydantic-validated ledger; publishes only when a transaction changed it |
| `input/` | Last-moment guards and key sequence; Niri/X11 focus probe; cached XTest helper |
| `automation.py` | Player-first orchestration; clears delivery events on a verified new game |
| `osd/presenter.py`, `osd/widgets/` | Explicit widget factory and stateful presentation, independent of GTK/input |
| `osd/window.py`, `osd/__main__.py` | Window and configured component assembly |

## Known limits

Local-player selection remains heuristic in multiplayer; belt capacity assumes
four rows. Injured merc HP estimates use a normalized fraction and can disagree
with the inventory panel: see [merc HP research](../merc_health_research.md).
Confirmed game-exit detection is unavailable; uncertain reads hide stale values
while preserving widget latches, and verified identity changes reset them.
Memory reads are sequential, not atomic. Build updates require layout revalidation.
