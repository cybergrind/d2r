# HUD canvas: plan

Drafted 2026-09-30 with the user. Status: **phases 1–2 done 2026-09-30** (uncommitted; awaiting an
in-game look). **Phase 3 deferred by the user (2026-09-30)**: `make osd` keeps its own window.

## Goal

Replace the ad-hoc OSD windows (four surfaces in two processes, each positioned its own way)
with **one transparent, click-through canvas** over the game's working area. Producers publish
widgets into named **slots**; one renderer lays them out and draws them with cairo.

| Surface today | Process | Moves to |
| --- | --- | --- |
| Level guide card (arrows + map) | `serve` overlay, own window | Phase 1 |
| Alt+D / shop / identify card | `serve` overlay | Phase 2 |
| Inventory OSD text (health, belt, portal …) | `make osd` | Phase 3 |
| Repair-button mark | `make osd`, own window | Phase 3 |

## Decisions

- **Slot positions are fractions of the game window** (user, 2026-09-30): x from its left edge,
  y from its top edge, so they follow the window's size and position.
- **Game window rectangle.** niri reports `window_size` for every window, but
  `tile_pos_in_workspace_view` only for floating ones (third-parties/niri
  `src/layout/scrolling.rs`: tiled tiles leave it None; checked on niri 26.04). A floating
  game uses its reported position. A tiled game is assumed to sit at the bottom-left of the
  working area, the same assumption the live-accepted repair mark uses.
- **Canvas surface.** A layer-shell overlay anchored to all four edges with exclusive zone 0
  covers exactly the working area (the output minus bars), which is niri's "workspace view".
  Canvas coordinates therefore equal workspace-view coordinates. Its input region is empty
  (click-through), and it is **unmapped whenever the scene is empty**, so a fullscreen game
  keeps direct scanout when nothing is shown.
- **Scene protocol.** Each producer writes one lease file `<producer>.json`,
  `{checked_at, widgets: [{id, kind, slot, payload}]}`, into one scene directory
  (`$XDG_RUNTIME_DIR/d2r-hud/` by default). A stale lease (the 1.5 s used by the OSD today)
  hides that producer's widgets. The renderer reads every file on each refresh.
- **Widgets are pure cairo.** Each kind has `measure(payload) → (w, h)` and
  `draw(cr, w, h, payload)`; composites draw sub-widgets inside their box. Text uses PangoCairo
  markup from `presentation.render_markup`. Everything renders headlessly to an image surface
  in tests. There is no GTK widget tree to rebuild.
- **Scale.** Widget sizes are logical pixels at a reference game-window height
  (`reference_height`, 1422 = the user's window), scaled by `window_height / reference_height`
  and clamped to 0.6–2.0.
- **Slots stack** their widgets downward in producer/id order with a gap, so two widgets in one
  slot never overlap.

## Standing rules

Red/green TDD per development.md; plain pytest; headless cairo renders instead of GTK in tests.
The GTK layer (canvas window, monitor choice, timer) stays thin and untested beyond imports.
Keep the old windows until each phase reaches parity, then remove them in the same phase. Other
agents edit `osd/`: change only what a phase moves, and report their test failures separately.

## Phases

### Phase 1: canvas + level guide card

- `hud/scene.py`: widget entries, `publish_layer`, `read_scene` (lease per producer).
- `hud/layout.py`: `GameRect` resolution (floating position or tiled bottom-left), slots,
  scaling, stacking → pixel boxes.
- `hud/widgets.py`: renderer registry; `guide` (arrow rows + map, reusing
  `osd.direction.arrow_polygon` and `osd.level_map.draw_map`).
- `hud/canvas.py` + `hud/__main__.py`: the layer-shell canvas process; `serve` starts it like the
  overlay today (`hud_process`).
- The level guide publishes to the scene instead of `guide.json`; the separate guide window and
  `--guide-x/--guide-y` go away (slot `guide` in config replaces them).

Done as planned, plus:
- `hud/payloads.py` holds the producer-side payload builders, so `serve` never imports GTK/Pango
  (test: importing `hud.process` leaves `gi` unloaded). The first Pango layout starts a
  fontconfig thread, which is why the renderer lives in its own process.
- `hud_process` is started by `serve` (`--hud-scene`, default `$XDG_RUNTIME_DIR/d2r-hud`) and
  `make hud` runs it alone. A `canvas.lock` flock keeps one canvas per scene.
- The guide card draws "here" rows as a dot in the arrow column. Text gets 4 px slack because
  hinting differs between the measuring surface and the canvas.
- The separate guide window, `guide.json` and `--guide-x/--guide-y` were removed. The slot is
  `HUD.slots['guide']` = (0.03, 0.08) of the game window.
- Known test-suite note: after the HUD tests create Pango layouts, `probes/test_cli.py`'s
  `os.fork()` warns that the pytest process is multi-threaded (harmless there: the child only
  reads memory).

### Phase 2: assessment / shop / identify cards on the canvas — done 2026-09-30

- `text` widget (`TextCard`): styled lines word-wrapped to the slot's free width and ellipsized
  at its free height, which is what the old label's width and line caps did. Slots gained
  `max_width` (fraction of the game window); `slot_limit` gives each widget its budget.
- Producers: `appraisal` (Alt+D card) and `cards` (shop + identify, which keep their existing
  mutual exclusion in `serve`). All share slot `assessment` (default x 0.2, y 0.12, max width
  0.45) and stack if ever shown together. `shop/probe.py`'s 5 s result card publishes as
  `shop-probe`.
- Removed with parity: `appraisal/overlay.py` (process, `osd.json`, `read_display`), the
  assessment branch of `osd/window.py`, `place_assessment`, `DirectionCards`,
  `--osd-x/--osd-y` and `APPRAISAL.osd_x/osd_y`. `osd/window.py` now serves only the
  inventory OSD label and repair mark (Phase 3).

### More producers (2026-09-30)

- **Ground runes** (`inventory_tracking/loot/`, producer `loot`, slot `loot` at (0.03, 0.34)): serve's
  `RuneWatcher` polls item units in ground modes 3 (on the ground) and 5 (dropping), keeps runes
  at or above `APPRAISAL.rune_minimum` (default r16 = Io and up, user 2026-09-30), and
  shows them as arrow rows (the guide card without a map), highest rune first. Each new rune is
  logged once. Rune class IDs 625 (El) to 657 (Zod) are bundled in `loot/data/runes.json` from
  the game's classid column (pricing/raw/d2data/misc.json), the source the item decoder uses; a test
  checks every rune against the decoder. The first table used "lineNumber + 523" and was one too high
  (user, 2026-09-30: Ist shown as Mal, Mal as Um).
  **Unconfirmed:** ground modes and the static-path position (+0x10/+0x14). Win+C records
  `ground_items` and names ground runes in its notification, for checking against a real drop.
  Only streamed items exist (roughly a screen or two around the player).
- **Shrines:** the object data layout was confirmed 2026-09-30 with a Stamina Shrine the user
  identified (dump 20260930T121835Z-713d7e8a): +0x08 is the type byte (d2data shrines.json code),
  +0x10 is the shrine table pointer. MapAssist's byte-packed +0x0C is wrong on this build. Unused
  shrines (mode 0) of `APPRAISAL.shrine_marks` (default 18 = Gem) are listed above the runes in the
  `loot` card. Still unconfirmed: that a used shrine leaves mode 0.

### Phase 3: inventory OSD text widgets and the repair mark

Deferred (user, 2026-09-30): `make osd` runs healing, and it must keep working even when `serve`
(appraisal) is slow or frozen, so it stays a separate script with its own window for now.
Constraints if this is revisited:
- Healing and the OSD reader stay in the `make osd` process; the canvas only displays.
- The canvas must not depend on `serve`'s lifetime. Today `serve` starts it (`hud_process`),
  so if `serve` died, OSD widgets would vanish with it. Start it independently (`make hud`,
  or from `make osd` too; the flock keeps it to one instance).
- Publishing must never block the OSD loop (a failed or slow scene write is dropped, not
  retried inline).

### Phase 4: remove the old windows and centring tricks (after Phase 3)

### Ground marks (2026-10-05, user request; not calibrated in-game)

- `hud/ground.py`: the level map's dots of `HUD.ground.kinds` (unique/champion monsters, Heralds,
  next level, exits, waypoints) are also drawn on the game view, as translucent floor ellipses.
  `project` maps a tile offset from the player to window pixels (isometric, 2:1); a mark beyond
  the view becomes a small dot at the window edge in its direction.
- Widget kind `ground` in slot `ground` (the whole game window), published with the map card by
  `guide_widgets`, so the marks show only while the map does and move at the guide's poll rate.
- Open: `HUD.ground.player_x/player_y/tile_height` are the classic 800x600 values scaled to the
  window height. Calibrate against a static mark (a waypoint) in a screenshot with the map pinned.
- Lag fix (2026-10-05): the marks trailed the player by up to ~0.8 s (guide poll 0.5 s, serve loop
  0.2 s, canvas refresh 0.1 s). `hud/live.py`: the canvas re-reads the player's path position
  itself on every frame (`live` = pid + path address in the ground payload, from `Location.path`)
  and redraws when it changed. Monster positions still arrive at the terror probe's 0.25 s.
  Open: the sub-unit fraction at path +0x00/+0x04 is the classic layout, not confirmed in D2R.
