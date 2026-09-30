# Host conveniences for the item collection (inventory_tracking/collection/plan.md).
UV ?= uv run --offline
COLLECTION_HTML ?= inventory_tracking/runs/collection/collection.html

.PHONY: export open serve collect equipped status test hud

## export: write the searchable single-file HTML from the collection database
export:
	$(UV) python -m inventory_tracking.collection export --html $(COLLECTION_HTML)

osd:
	$(UV) python -m inventory_tracking.osd

## hud: run the HUD canvas on its own (`serve` also starts it; a second one exits quietly)
hud:
	$(UV) python -m inventory_tracking.hud

## open: export, then open the page in the default browser
open: export
	xdg-open $(COLLECTION_HTML)

## serve: start the Alt+D / Win+S / Win+D / Win+C worker (collects on stash close; Win+C re-shows the level map and dumps level memory)
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
