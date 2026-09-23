# Offline appraisal knowledge

The normal appraisal path reads a local SQLite index. Network research belongs to
the separate refresh workflow. JSON evidence and SQLite are local data, excluded from Git. Restore a separate data
snapshot into `pricing/data/` before appraisal; see [data setup](#local-data-setup) below.
The SQLite index can be rebuilt from that snapshot without raw downloads.

Independent appraisal facets (2026-09-23):

```sh
# Base identity only; not a text match against related items:
uv run --offline python -m pricing.knowledge search --base "Crystal Sword" --kind catalog
# Skill matters across bases; property 1577 is Sigil: Death in the local dictionary:
uv run --offline python -m pricing.knowledge search --kind market --property-min '1577=3'
# Exact base, quality and socket count must all match:
uv run --offline python -m pricing.knowledge search --base "Crystal Sword" --kind base_rule --rarity normal --sockets 4
# Recipe discovery across bases:
uv run --offline python -m pricing.knowledge search --kind base_rule --runeword Spirit --sockets 4
```

Search supports exact `--property 'ID=JSON'` and numeric `--property-min 'ID=N'`,
independently or combined with base, quality, sockets and existing context facets.
All constraints apply before the result limit. Missing properties, numeric strings
and booleans do not match numeric skills. Property IDs must come from `properties`.
Skill search currently covers explicit observation properties, not every planner
stat or prose keep pattern. Cross-base hits are discovery evidence, never a pooled
price band. Search results can include unverified market scope; only the scoped
lookup/comparable path can support prices. Recipe discovery preserves empty-socket
and mode prerequisites; it does not certify that the photographed item meets them.

Schema 3 requires an offline `rebuild` after upgrading from schema 2. It publishes
quality and predicate socket facets consistently. Current broad property search
uses SQL JSON predicates; the measured skill query takes about 201 ms, versus
1–5 ms for base/recipe queries. Indexed property postings are planned in
`pricing/plan.html#pipeline-plan`, along with the image-to-decision orchestrator.

For “good early-game Sorc uniques/sets”, start with the prepared recommendation command:

```sh
uv run --offline python -m pricing.knowledge recommend --class sorc --quality unique,set
uv run --offline python -m pricing.knowledge recommend --class necro --min-level 26 --max-level 40
uv run --offline python -m pricing.knowledge recommend --class barb --archetype melee --max-level 25
uv run --offline python -m pricing.knowledge recommend --class sorc --side merc --max-level 40
uv run --offline python -m pricing.knowledge item "Magefist" --full
```

`recommend` joins prepared facts and reviewed advice, applies eligibility before ranking,
and returns requirements, benefit values, reasons, conditions, source dates/locators and gaps.
It defaults to equip levels 1–25, unique/set quality and player gear; Sorceress/Necromancer
also default to caster applicability. Defaults are disclosed. Override `--archetype melee`
for attack variants. Level range describes minimum equip requirements, not when usefulness
expires. Character attributes and owned set pieces are not assumed. Strength/dexterity values
apply to the original base and ordinary non-ethereal item unless explicitly stated; upgrades,
socket additions and unresolved requirement modifiers need review.

Filters include `--slot` (hands/gloves, feet/boots, head/helm, waist/belt, offhand/shield,
weapon, body, amulet, ring), `--side`, `--quality`, `--min-level`, `--max-level`, and `--archetype`.
Class aliases include sorc/necro/barb/pally/sin/zon. Quality aliases include uniq/uniques/sets.
Output is at most 12 items by default and budgeted to 12 KiB. Use the returned `next_offset`
with `--offset` for remaining results; `total` counts all eligible identities. A single unusually
large complete record is retained with an explicit size warning rather than losing conditions.
`item --full` expands by exact name, alias or stable ID; ambiguous aliases remain ambiguous.
`lookup` also includes prepared facts and utility for known unique/set identities, alongside its
independent appraisal evidence. Full item expansion retains class and player/mercenary context.

The prepared layer currently has 573 cached unique/set identities and 75 reviewed recommendation
records, including three mercenary options and explicit Sorceress/Necromancer/Warlock guide reviews.
All eight classes receive reviewed general utility, not complete build-specific advice. Fifteen
transcript candidates remain explicit gaps (including runewords); generic patterns stay separate.
Twenty-eight unique catalog names remain unmatched, including variants; the apparent 32 missing
set entries are whole-set bundles rather than missing set items. Set-wide bonuses and requirement
modifier arithmetic have explicit gaps. See coverage in the two portable artifacts below.

Rebuild source adapters only when their cached inputs or review rules change:

```sh
uv run --offline python -m pricing.knowledge.facts
uv run --offline python -m pricing.knowledge.recommendations
uv run --offline python -m pricing.knowledge rebuild
```

The normal `rebuild` reads portable `appraisal-item-facts.json` and
`appraisal-recommendations.json` with the existing evidence artifacts; raw downloads are not
needed. SQLite schema version 3 is separate from portable evidence schema version 1. Publication
is atomic; failed publication preserves the previous file. Source fingerprints identify each
prepared snapshot. FTS remains a discovery fallback, not a recommendation classifier.

Benchmark using `python -m pricing.knowledge.benchmark --help`; dated before/after reports are in
`pricing/data/appraisal-retrieval-{baseline,final}-2026-09-23.json`. They measure local process and
DB work, not model reasoning or screenshot review. Normal reads and rebuild never refresh prices.

An optional [local PyOCR preprocessing stage](OCR.md) extracts a structured draft
from item screenshots, with original text, confidence and review crops. Review
uncertain fields before using them as exact lookup predicates.

```sh
uv run python -m pricing.knowledge rebuild
uv run python -m pricing.knowledge lookup "Bloodfist"
uv run python -m pricing.knowledge lookup "Greater Talons" --rarity normal --sockets 3 --no-ethereal
uv run python -m pricing.knowledge properties "Javelin"
uv run python -m pricing.knowledge properties "Faster Cast Rate"
uv run python -m pricing.knowledge search "attack speed" --kind leveling
uv run python -m pricing.knowledge search "" --side merc --class Warlock
uv run python -m pricing.knowledge coverage
uv run python -m pricing.knowledge sockets "Crystal Sword" --method larzuk --ilvl 28
```

Use `--property 'ID=JSON_VALUE'` with IDs from the property dictionary. Exact facets restrict the
requested comparison, but do not prove all value-deciding rolls were supplied.

`lookup` groups identity, demand, leveling, base rules, historical evidence and
normalized market observations. Evidence sections are bounded; their counts show
how much was omitted. `search --limit` retrieves more source records. Search is
lexical discovery: matching words do not establish item compatibility or price.
`--full` expands original evidence and source metadata. `--socket-contents empty`
requires explicit empty-socket evidence; missing listing contents stay unknown.

Price evidence distinguishes name-level watch bands from facet-matched bands.
Check deciding affixes and dated representative terms before quoting. Missing
prices remain unresolved. Leveling usefulness and build demand remain useful
without a resale price. Historical aggregate tables have unverified scope labels;
they never become verified exact-roll observations just by importing them.

The files `appraisal-demand.json`, `appraisal-utility.json`,
`appraisal-market-manifest.json`, and `appraisal-watchlist.json` contain coverage
details and remaining gaps. See [the implementation plan](../plan.html) for
research sources, scope, review findings and maintenance contracts.

To rebuild source adapters after research changes, run their explicit module
commands (`builds`, `utility`, `legacy`). These adapters read cached source files;
the ordinary index rebuild uses the portable outputs. Preserve dated old market
observations when refreshing, and inspect rate-limit/failed-job states rather
than interpreting them as no market.

```sh
# Offline re-import after source cache or saved refresh jobs change:
uv run python -m pricing.knowledge.refresh --offline-import
# Explicit ONLINE maintenance, after the recorded rate-limit hold has cleared:
uv run python -m pricing.knowledge.refresh --refresh-limit 30 --pages 4
# Publish the resulting portable evidence to the local read index:
uv run python -m pricing.knowledge rebuild
```

The initial refresh stopped on HTTP 429. Consult `appraisal-market-manifest.json`
and saved jobs before resuming. A completed catalog census does not imply that
every item has a price, nor that name-level seller coverage covers every valuable
roll. Existing observations without fetch timestamps retain unknown dates.

## Local data setup

The entire `pricing/data/` directory is excluded from Git, including research notes and
schemas stored there. Keep a separate backup of this directory and `pricing/raw/`.
Optional OCR screenshots under `tests/pricing/knowledge/fixtures/` are also local.


Copy a trusted snapshot's pricing/data/ files into `pricing/data/`. For an offline
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


### Image extraction (EasyOCR)

Use the separate, explicitly provisioned OCR environment documented in [OCR.md](OCR.md):

```sh
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 /tmp/d2r-easyocr-env/bin/python -m pricing.knowledge image IMAGE
```

This returns a draft plus local candidate evidence for the calling agent to review.
It does not approve prices or automatically infer unreadable fields. Tesseract and
its project extra have been retired. Missing models fail locally without downloads.
