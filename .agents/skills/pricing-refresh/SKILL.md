---
name: pricing-refresh
description: Pull or refresh D2R market data (Traderie asks, diablo2.io fills), rebuild the ladder/bucket/base tables, extend the guides or run pricing/plan.html work packages; the tool cheat sheet and fold-back conventions.
---

# Refreshing prices and extending the guides

Ordinary item appraisal uses `appraise` offline. An explicit request for live prices on one
item uses [appraise-online](../appraise-online/SKILL.md), which may consult this tool reference.
Do not start bulk maintenance to answer a screenshot or a missing-price result.

Scope filters are mandatory everywhere: Traderie props 799 = softcore, 800 = false (Non-Ladder),
798 = PC, 1854 = RotW (filter client-side, the server ignores bool/string filters); diablo2.io
`ladder=2 hc=2 plat_pc=1 legacy_resu=2`, `activesold=1` for fills. Ist conversion always via
`pricing/data/wp-f-ladder.json` field `ist`.

## Offline knowledge-base maintenance (2026-09-23)

The active architecture and coverage plan is `pricing/plan.html`; it supersedes the old WP-A…J
plan. Appraisal reads `pricing/knowledge/` offline, including expensive items and cache misses.
See `pricing/knowledge/README.md` for commands. Portable `pricing/data/appraisal-*.json` and
`appraisal-market.jsonl` are the source of the rebuildable SQLite index.

- `uv run python -m pricing.knowledge.refresh --offline-import` re-normalizes cached observations
  and saved jobs without networking.
- Explicit online maintenance: `uv run python -m pricing.knowledge.refresh --refresh-limit 30 --pages 4`.
  Inspect the manifest's maintenance hold first; the initial batch stopped on HTTP 429. Preserve
  resumable jobs and source errors, and never weaken scope to fill a coverage gap.
- Prepared leveling maintenance: run `uv run --offline python -m pricing.knowledge.facts`, then
  `uv run --offline python -m pricing.knowledge.recommendations`, then rebuild. These adapters read
  cached inputs only. Portable facts/recommendations publish indexed equip requirements, reviewed
  use cases and provenance; raw source mentions are not automatically recommendations.
- Read questions use `recommend --class sorc --quality unique,set --max-level 25` or `item NAME --full`.
  See README for filters and explicit coverage gaps. Do not refresh merely to answer a read query.
- `uv run python -m pricing.knowledge rebuild` publishes portable data to the offline index.
- `uv run python -m pricing.knowledge coverage` reports indexed source counts. Adapter coverage
  and missing-market states live in the demand/utility/watchlist/market manifest files.

The new importer requires explicit RotW membership, quarantines unknown versions, preserves
array properties, and separates name-level watch bands from facet-matched evidence. Legacy tools
below remain research helpers; their old cache flags are not a strict offline or strict-scope contract.

## Tools (`pricing/tools/`, all verified 2026-09-18; run from the repo root)

```
python3 pricing/tools/traderie.py search <name>                       # catalog id
python3 pricing/tools/traderie.py listings <itemId> 4 --sc --nl --pc --props   # 50/page, 0-based; --rarity rare|magic|unique, --eth/--noeth, --json
python3 pricing/tools/traderie.py runes Pul Um Mal Ist Gul Vex Ohm Lo Sur Ber Jah Cham Zod   # rune-for-rune asks → pricing/raw/traderie/rune-*.json
python3 pricing/tools/d2io_search.py "<keyword>" ladder=2 hc=2 plat_pc=1 activesold=1 legacy_resu=2 --out pricing/raw/d2io/search-<x>.html
python3 pricing/tools/d2io_search.py --parse pricing/raw/d2io/search-<x>.html   # re-parse a cached page
pricing/tools/fetch.sh <url> <outfile>                                 # browser UA, skips if cached
python3 pricing/tools/html2text.py <file.html> ["keyword" [context]]   # guides and cached pages as text
python3 pricing/tools/tables.py <file.html>                            # maxroll gear tables
```
Item ids already used: `pricing/tools/wp_b_ids.txt`. diablo2.io: keywords are mandatory, ≥ 30 s
between searches (guest flood control), retry once on an empty page, page 2 is `&start=30`.
Traderie: `prices[].group` — same group summed, different groups are OR-alternatives (take the
cheapest); rune/gem asks are per whole stack; one vote per `seller_id`; a bucket with 47 listings from
6 sellers is a wall, not a market. Cached pulls: `pricing/raw/traderie/<slug>.json` (bare list) and
`wpi-*` / `wph-*` (`{"listings": [...]}`), `pricing/raw/d2io/*.html`, `pricing/raw/mr/` (maxroll).

## Rebuild sequence (primer §7 has the tested full runbook)

```
python3 pricing/tools/rune_ladder.py > pricing/data/wp-f-ladder.json     # from rune-*.json
python3 pricing/tools/wp_b_buckets.py pricing/data/wp-b-prices.json      # base buckets from raw pulls
python3 pricing/tools/wp_g_build.py                                      # writes wp-g-bases.json
python3 pricing/tools/wp_a_variants.py --write                           # merges wp-a-variants/ into wp-a-builds.json
```
Jewels / charms / uniques (WP-H / WP-I) have no build script: re-pull and re-bucket by the property ids
listed in primer §3–§5. Step 5 of the runbook (ladder monotonic check) is a warning, not a gate.

## Where things live and how to fold results back

- Active plan: `pricing/plan.html` (offline appraisal P0…P9). Historical work-package hand-offs remain
  in `pricing/data/wp-*.md`; original tools and evidence have not been removed.
- Guide conventions: `guides/planning-with-html.html` — body = settled truth, no inline revision markers;
  every review or Q&A pass is appended to the guide's collapsed Review log with a date; rejected ideas are
  recorded so they are not re-proposed; unverified claims go to the "verify in-game" appendix.
- New screenshot verdicts go to `guides/pricing.html` §8 (worked examples) and
  `pricing/data/addendum-2026-09-18-session.json`; if a verdict turns out wrong in trade, record the fill
  there and fix the guide row.
- Build demand: maxroll guides — main gear via `tables.py`, variants and mercs via the d2planner profile
  JSON (`https://planners.maxroll.gg/profiles/d2/<data-d2-id>`), names from the d2data dump for RotW ids.
- Orientation pages (diablo2.io price guide 2026-08-28, maxroll trading guide) are never a price source.
- The repo is under git on `main`; do not commit unless asked. `pricing/raw/` is git-ignored.

For catalog-wide offline KB audits, base-variant gaps and folding existing research
into runtime appraisal, use [update-kb](../update-kb/SKILL.md). It includes the
coverage audit and preserves historical bucket limitations.
