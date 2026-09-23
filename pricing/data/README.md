# Local appraisal data

Git stores code, tests, schemas and research notes. The datasets in this directory,
including historical wp-* JSON, appraisal-*.json/jsonl, refresh jobs and SQLite,
are local and ignored. Raw downloads/models under pricing/raw/ are also ignored.
Synthetic test fixtures remain tracked. Optional OCR screenshots under
tests/pricing/knowledge/fixtures/ are local and ignored; copy them separately to run
the image integration tests.

Existing local files are preserved. Removing them from the Git index does not delete
them on disk or rewrite earlier commits. Back up and transfer data separately from Git.

## Restore on another machine

Copy a trusted snapshot's pricing/data/ files into this directory. For an offline
rebuild, the minimum inputs are:

- appraisal-catalog.json
- appraisal-trade-catalog.json
- appraisal-demand.json
- appraisal-utility.json
- appraisal-legacy.json
- appraisal-market.jsonl
- appraisal-item-facts.json
- appraisal-recommendations.json

Also restore appraisal-properties.json for property lookup/OCR and wp-f-ladder.json
for currency conversion. Preserve the full data snapshot for legacy fallback evidence,
maintenance and research; raw inputs/models are needed only by their respective adapters
and OCR. Use matching artifacts from the same snapshot: rebuild validates dependencies.

From the repository root:

```sh
uv run --offline python -m pricing.knowledge rebuild
uv run --offline python -m pricing.knowledge lookup Ring --rarity rare --limit 2
```

A fresh clone alone contains no market database. Do not fetch online merely because data
is absent. Restore a snapshot or explicitly request maintenance. Corpus integration tests
skip when their optional local data is absent; synthetic behavior tests still run.
