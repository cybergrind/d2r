# Health and potion OSD

Run from the host desktop terminal in the repository root:

```sh
uv run -m inventory_tracking.osd
```

The display is a single line of alerts. For example, with health above 70%:

```text
juv 3 · hp 1
```

`juv` and `hp` report missing potions using dynamic targets for each four-slot
belt column. The bottom potion chooses healing or rejuvenation; normal/full
rejuvenations count together, as do all standard healing tiers. If the bottom is
empty, the lowest remaining item chooses the target. An entirely empty column
assumes rejuvenation, so an empty belt shows `juv 16`. Slots with another potion
type do not satisfy the selected target. Columns led by other item types do not
produce healing/rejuvenation shortages. Targets update on every valid sample.
This currently assumes the player's four-row belt.

Current/max player health appears only at or below 70%. Empty alerts unmap the
window. Startup, incomplete, unavailable and stale readings stay blank; diagnostic
files remain available. Only text is visible, with transparent backgrounds.
Inventory/stash potions are not counted. Optional `--rejuvenation-target` and
`--healing-target` override automatic tracking with global rejuvenation and
healing stock targets respectively, counting all supported tiers.

Preview without accessing D2R:

```sh
uv run -m inventory_tracking.osd --demo
```

Preview is explicitly labeled `PREVIEW` and uses fixed example values. Visual
placement and fullscreen behavior still need testing in the actual game session.
Stop either mode with **Ctrl+C in the launching terminal**.

Position, font and targets:

```sh
uv run -m inventory_tracking.osd --x 0 --y -130 --font-size 16 \
  --rejuvenation-target 8 --healing-target 8
```

The default is a single line in 16px text, centered horizontally and 130 logical
pixels above the screen center. `--x` / `--y` are offsets from center: positive
x moves right; negative y moves up.
Use `--monitor 0` (zero-based) to select an output; otherwise the compositor chooses.
The window requests the overlay layer, no keyboard interaction, an empty mouse
input region and no reserved screen space. It is currently desktop-wide; it does
not automatically hide when D2R loses focus. Player and mercenary healing are enabled by default; use `--no-player-heal --no-merc-heal` for read-only mode.

Terminal diagnostics (no GTK needed):

```sh
uv run -m inventory_tracking.osd --text
uv run -m inventory_tracking.osd --once
uv run -m inventory_tracking.osd --demo --once
```

`--once` exits 0 for a health sample and 2 for unavailable state. Continuous mode
retries when the game is absent or inaccessible. Omit `--pid` for process
rediscovery after restarts; specifying it pins one process number.

The live adapter is experimental, using the existing research traversal on the
recorded executable hash. It discovers/captures the image once per attachment,
then reads units with a 0.1-second delay between samples (`--interval`). Old values
expire after 2 seconds (`--max-age`). Unknown, ambiguous, incomplete and stale
readings suppress pickup advice. Each sample selects the sole player candidate
with plausible effective life/max stats, then counts its owned belt items. This
is a research heuristic, not a verified local-player selector for all multiplayer
states. Automation retains the configured freshness and input checks; it does not resolve this research limitation.

Run artifacts are under `inventory_tracking/runs/osd/<run-id>/`: `osd.log`, atomic
`state.json` and the latest `units.json`. Capture bytes live only in a temporary
attachment directory and are removed on disconnect/normal shutdown. The GUI reads
state independently of the worker, so slow memory reads cannot freeze rendering.

Runtime dependencies: GTK4, gtk4-layer-shell and their introspection metadata,
plus PyGObject/pycairo installed by `uv run` as standard project dependencies. The local host already has the
native GTK4/layer-shell libraries. Wayland layer-shell support is required; this
backend targets the observed Niri session, not an X11 overlay fallback.

Backend references:
[upstream Python initialization](https://github.com/wmww/gtk4-layer-shell/blob/main/examples/simple-example.py),
[layer-shell API](https://wmww.github.io/gtk4-layer-shell/gtk4-layer-shell-GTK4-Layer-Shell.html),
[GDK input regions](https://docs.gtk.org/gdk4/method.Surface.set_input_region.html).

Tests mirror production paths under `tests/inventory_tracking/osd/`:

```sh
uv run pytest tests -v
uv run ruff check inventory_tracking tests
uv run ruff format --check inventory_tracking tests
```


## Mercenary health and healing

Act 2 hirelings are matched to the player's unit ID via monster data `+0x54`.
`merc current/max` appears only strictly below 65% life; `merc dead`
means the identified unit is dying/dead or has zero life. Missing/ambiguous
mercenaries produce no merc line and cannot trigger input.

Merc life is a normalized client fraction out of 32768. The maximum comes from
effective stats; injured HP is an estimate (shown with `~`). The cause of its
discrepancy from the mercenary inventory's exact HP is unresolved.
Full 32768/32768 matched the user's 2090/2090. The controller compares the native
fraction against the configured merc thresholds, without rounding the displayed number. The exact
relationship to the inventory HP text is still under investigation after a
persistent user-reported mismatch; quantization alone is not established.

Normal startup enables mercenary healing using fresh, complete readings, death
checks, exact game focus, usable belt potions and per-actor/type cooldowns. As authorized
by the user on 2026-09-21, open in-game menus are not detected: the old menu-state
layout is invalid for this build. Merc healing and its debug notification were confirmed working in-game; the new player/rejuvenation paths still need live validation. Use
`uv run -m inventory_tracking.osd --no-player-heal --no-merc-heal` to observe without input.
Stop with Ctrl+C in the launching terminal. Demo and `--once` never send input.

Standard healing potions (minor through super) are detected in any bottom belt
cell, using its column key (with Shift for the merc). Higher potions across gaps and other potion types are
not used. Each actor has an independent cooldown for each potion type, shared across
columns and OSD instances using the same output root. Player rejuvenation uses
one second; player healing and both merc potion types use three seconds.
A healing potion does not delay the same actor's rejuvenation, but consumption
must still be acknowledged before another potion is sent to that actor. Shared
item reservations prevent double selection, and the next send requires a sample
started after the preceding key delivery finished. Physical held keys, stale
samples, incomplete readings, missing process identity and player/merc death
suppress input. Both Niri game-window focus and the exact X11 game PID must match.

Consumption acknowledgement uses the selected item's disappearance from the
belt. Without acknowledgement within two seconds, healing suspends until a new
identified session. Suspension and pending consumption survive an OSD restart;
restarting is not a way to bypass an uncertain delivery. No blind retries for
that recipient. `player-heal.json` and `merc-heal.json` record uniform outcome/event
objects; `osd.log` records sends, acknowledgements and errors.
After successful input, the OSD shows `merc potion sent (Shift+N)` for the selected column
for one second. This debug message reports key delivery, not confirmed consumption;
rejected or failed input produces no message.
The input backend requires `niri`, `xdotool`, libX11 and libXtst on the host.
Mercenary ownership remains specific to the supported build.


## Potion defaults

Edit `inventory_tracking/config.py`. `PLAYER_HEALING` and `MERC_HEALING` are
complete, immutable `HealingConfig` values: actor, enabled flag, thresholds and
cooldowns keyed by `PotionType`, sample freshness, and consumption timeout.
`OSD` controls visibility thresholds, notification duration, font, position,
monitor, display freshness, refresh interval, and optional stock targets.
`READER` and `INPUT` contain polling/reconnect and platform input settings.
CLI overrides are applied to these objects once at startup.

Current healing thresholds:

| Recipient | Healing potion below | Rejuvenation below |
| --- | --- | --- |
| Player | 65% | 40% |
| Merc | 55% | 20% |

The thresholds are strict: exactly 40% player life uses healing, not rejuvenation.
Both controllers are enabled by default; `--no-player-heal` and `--no-merc-heal`
disable them independently. Player actions are considered first. Player healing
does not require a living merc. Rejuvenation takes priority below its threshold,
with healing as fallback when no rejuvenation is usable. Normal/full rejuvenations and healing potions are detected by item type in all
four columns on every sample, including mixed columns and all-rejuvenation belts. Player keys are plain
1/2/3/4; merc keys include Shift. No input is sent across empty bottom slots. Potion thresholds do not change when
the belt changes: an all-rejuvenation belt uses the rejuvenation thresholds.
OSD shortage targets automatically follow each column; no target flags are needed
when switching to all rejuvenations.
Player sends also show a one-second `player potion sent (1)` notification.
Each recipient waits for its selected item to disappear from the belt before
sending again, and suspends after an unacknowledged consumption timeout.


## Runtime structure and persisted state

- `state.py` converts research snapshots; `models.py` defines domain records.
- `belt.py` classifies supported potion families and computes column shortages.
- `heal.py` chooses eligible potion types from health and injected configuration.
- `potions.py` owns per-actor cooldown, pending consumption, and suspension policy.
- `potion_ledger.py` serializes instances and atomically saves `potions.json` in
  the output root. It keeps the existing `merc-input.lock` path and imports its
  old same-boot timestamp conservatively on first use. Corrupt state refuses input.
- `potion_input.py` handles focus/freshness checks and key delivery; it contains
  no cooldown selection. All key releases are attempted; release errors suspend
  the actor and do not produce success feedback.
- `automation.py` runs player before merc and collects typed delivery events.
- `reader.py` owns attachment, in-memory sampling, reconnect, and reports.
- `osd/` formats and renders state; neither healing nor sampling depends on GTK.

Stop the previous OSD process before launching this version. The migration does
not coordinate cooldown policy with a concurrently running older implementation.
Ledger cooldown timestamps are discarded after a system reboot. Pending actor
state resets only on a verified session identity change (or a new boot).
See [refactoring plan and completion log](../refactoring_plan.md).

## Extending the OSD

The persistent `Presenter` in `presenter.py` owns an ordered list of widgets in
`widgets/`. Each implements `update(snapshot)`, pure `render(now=...)`, and
`reset()`. The reader delivers every published sample to the presenter; GUI and
text output render the same state. Widgets have no GTK or input dependencies.
To add one, implement the protocol, add configuration in `config.py`, add it to
`default_widgets`, and mirror its tests under `tests/inventory_tracking/osd/`.
The old `display_lines` function is a single-sample compatibility adapter and
must not be used for a stream requiring latch memory.

`OSD.teleport` controls the low-charge threshold (strictly below 20%) and town
repair reminder. `OSD.portal` controls the refill latch (trigger at 16 or fewer,
clear at 20). The portal reminder survives partial refill and unavailable reads;
unknown readings are hidden. Confirmed absence, replacement or session change
resets it. It is not persisted across OSD restarts.

Preview a repeating sequence of repair and portal-refill states, without reading
D2R or sending keys:

```sh
uv run -m inventory_tracking.osd --demo-resources
# Also works with --text; the sequence advances every three seconds.
```

Live resource readings are enabled for the supported build. `RESOURCE_READER`
in `config.py` selects the verified tome +0x30 and staff +0xe8 stat descriptors
and the room/level location chain. Controlled probes matched 32/33→31/33 staff
charges, 18→16 portals and a town-to-field transition. Weapon swaps move the
staff between slots 4 and 11: selection checks both equipped weapon sets and
requires a unique charged Teleport staff. Inventory/stash staffs are excluded.
No staff is a normal, hidden state. These settings require new verification
when the supported game build changes.

Capture the missing evidence with the read-only host command:

```sh
uv run -m inventory_tracking probe --resources
```

It writes candidate item stat arrays, item ownership/location and player area
records under `resources` in `units.json`, using a separate bounded read budget.
Normal probe completion/report watching still works. Capture tome use/refill,
staff charge use/repair/removal and both weapon-swap positions, and town/field
transitions. Compare with visible counts before changing the relevant
`RESOURCE_READER` settings. Missing or ambiguous evidence stays unavailable and
does not affect healing. See [design and implementation status](design.md).
