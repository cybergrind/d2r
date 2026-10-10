# Host conveniences for the item collection (inventory_tracking/collection/plan.md).
UV ?= uv run --offline
COLLECTION_HTML ?= inventory_tracking/runs/collection/collection.html

.PHONY: export open serve collect equipped status test hud traderie-preview

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

## serve: start the Alt+D / Win+S / Win+D / Win+C worker (binds its hotkeys in niri while it runs, input/compositor.py; collects on stash close; Win+C re-shows the level map and dumps level memory; Win+X runs the prebuff macro; KP_4 teleports toward the level map's mark or walks into a near door; KP_2 teleports toward the nearest elite, else an unexplored room; KP_3 toggles attack mode, which kills whatever comes into reach while you move about; shows unread Traderie notifications, also without the game)
serve:
	$(UV) python -m inventory_tracking.appraisal_service serve

## collect: read the running game's items once without the hotkey
collect:
	$(UV) python -m inventory_tracking.collection collect

## equipped: record only what the character and the mercenary wear, plus the sheet (no stash reads)
equipped:
	$(UV) python -m inventory_tracking.collection collect --equipped

## status: collection database counts
status:
	$(UV) python -m inventory_tracking.collection status

## test: collection tests
test:
	$(UV) pytest tests/inventory_tracking/collection -q
