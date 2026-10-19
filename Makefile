# Host conveniences for the item collection (inventory_tracking/collection/plan.md).
UV ?= uv run --offline
COLLECTION_HTML ?= inventory_tracking/runs/collection/collection.html

.PHONY: export open serve collect equipped status test test-all lint hud traderie-preview

## export: write the searchable single-file HTML from the collection database
export:
	$(UV) python -m inventory_tracking.collection export --html $(COLLECTION_HTML)

osd:
	$(UV) python -m inventory_tracking.osd

## hud: run the HUD canvas on its own (`serve` also starts it; a second one exits quietly)
hud:
	$(UV) python -m inventory_tracking.hud

## traderie-preview: show a sample Traderie notifications card for 30 s (works without the game or `serve`)
traderie-preview:
	$(UV) python -m inventory_tracking.hud.traderie

## open: export, then open the page in the default browser
open: export
	xdg-open $(COLLECTION_HTML)

## serve: start the Alt+D / Win+S / Win+D / Win+C worker (binds its hotkeys in niri while it runs, input/compositor.py; collects on stash close; Win+C re-shows the level map and dumps level memory; Win+X runs the prebuff macro; KP_4 teleports toward the level map's mark or walks into a near door; KP_2 teleports toward the nearest elite, else an unexplored room; KP_3 toggles attack mode, which kills whatever comes into reach while you move about; KP_1 picks up a valuable drop or a potion the belt wants (after the fight when one is on), else steps to where the monsters near can be struck, else does KP_2; inside a fight it also steps to a better place to stand; shows unread Traderie notifications, also without the game)
serve:
	$(UV) python -m inventory_tracking.appraisal serve

## collect: read the running game's items once without the hotkey
collect:
	$(UV) python -m inventory_tracking.collection collect

## equipped: record only what the character and the mercenary wear, plus the sheet (no stash reads)
equipped:
	$(UV) python -m inventory_tracking.collection collect --equipped

## status: collection database counts
status:
	$(UV) python -m inventory_tracking.collection status

## test: the routine lane, slow arena plays aside (6 workers while the game is not running, tests/conftest.py)
test:
	$(UV) pytest tests/inventory_tracking tests/skills -q -m "not slow" -n 6

## test-all: every test, the slow arena plays among them (before a commit)
test-all:
	$(UV) pytest tests -q -n 6 --dist loadgroup

## lint: ruff and pyrefly over the repository
lint:
	$(UV) ruff check .
	$(UV) ruff format --check .
	$(UV) pyrefly check

.PHONY: combat-viz combat-view combat-view-check stance-viz stance-view

## combat-viz: export every combat take for the replay viewer (combat_viewer/README.md) to inventory_tracking/runs/combat/viz
combat-viz:
	$(UV) python -m inventory_tracking.builds.warlock.echoing_strike.viz inventory_tracking/runs/combat

## combat-view: open the replay viewer (Godot 4) on the exported takes
combat-view:
	godot --path combat_viewer

## stance-viz: export the recorded step moments, one run per stepping strategy, to inventory_tracking/runs/combat/viz-stance
stance-viz:
	$(UV) python -m tests.inventory_tracking.scenarios.stance.export_viz

## stance-view: open the replay viewer on the step comparisons (first rule on the left; Tab changes the strategy on the right)
stance-view:
	godot --path combat_viewer -- $(CURDIR)/inventory_tracking/runs/combat/viz-stance

## combat-view-check: drive the viewer headless through every exported take and every key (prints SCRIPT ERROR lines, if any)
combat-view-check:
	godot --headless --path combat_viewer --script res://tests/drive.gd

.PHONY: filter
## filter: read the Chronicle from the running game (skipped when no game is seen), rebuild lootfilter/warlock_lean_v2.json and copy it to the clipboard
filter:
	-$(UV) python -m inventory_tracking.probes.chronicle
	$(UV) python -m inventory_tracking.loot.build_filter

.PHONY: grow

## grow: dump the running game and merge its newly decrypted code pages into pricing/raw/re/D2R-decrypted.exe (ARGS="--at 0x…" checks addresses)
grow:
	$(UV) python inventory_tracking/native/grow.py $(ARGS)
