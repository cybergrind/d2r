# Host conveniences for the item collection (inventory_tracking/collection/plan.md).
UV ?= uv run --offline
COLLECTION_HTML ?= inventory_tracking/runs/collection/collection.html

.PHONY: export open serve collect status test

## export: write the searchable single-file HTML from the collection database
export:
	$(UV) python -m inventory_tracking.collection export --html $(COLLECTION_HTML)

## open: export, then open the page in the default browser
open: export
	xdg-open $(COLLECTION_HTML)

## serve: start the Alt+D / Win+S worker
serve:
	$(UV) -m inventory_tracking.appraisal_service serve

## collect: read the running game's items once without the hotkey
collect:
	$(UV) python -m inventory_tracking.collection collect

## status: collection database counts
status:
	$(UV) python -m inventory_tracking.collection status

## test: collection tests
test:
	$(UV) pytest tests/inventory_tracking/collection -q
