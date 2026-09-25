---
name: update-kb
description: Update, audit, or extend this D2R repository's offline appraisal knowledge base, including base variants, unique/set definitions, roll ranges, runewords, build demand and leveling. Use for "update KB", missing base prices, coverage audits or folding completed research into the KB. Offline by default; live market collection only when requested.
---

# Update the offline appraisal KB

Work from the D2R repo root. Read `development.md` for code changes. Use local
`third-parties/` references before fetching implementation tables. Never commit
unless asked. Ordinary appraisal remains offline, including cache misses.

## Recover the intended scope

Start with `pricing/knowledge/README.md` and the relevant section of `pricing/plan.html`
(use `pricing/tools/html2text.py` with a real keyword, not an empty keyword).
Reuse completed research instead of repeating it:

- Base asks: `pricing/data/wp-b-prices.json`; curated base demand/mechanics:
  `wp-g-bases.json`; build mentions: `wp-a-bases.json` and `wp-a-variants/`.
- Market normalization and scope rationale: `appraisal-market-research-2026-09-23.md`.
- Definition/range coverage: `inventory_tracking/items/data/RANGE_COVERAGE.md`.
- Historical task scope: 2026-09-23 sessions “Optimize appraisal item caching” and
  “Optimize appraisal process”. Their requirement was fast, offline retrieval across
  valuable items, all top build variants/mercenaries, leveling and base/runeword
  utility; expensive work belongs in maintenance, never the appraisal hot path.
  Read local session history only if current documents leave a relevant gap.

## Audit before updating

Run `uv run --offline python -m pricing.knowledge coverage` and
`uv run --offline python -m pricing.knowledge.bases`.
The latter writes `pricing/data/appraisal-base-coverage.json`: every weapon/armor
base, historical buckets, scoped cached observations and explicit missing research. Catalog presence is not
price coverage. Do not declare a base priced just because a different variant is.

For a reported failure, replay the saved capture first. Keep a fixture and reproduce
it red/green. The host user runs live probes only if saved evidence cannot resolve it.

## Preserve meaningful variant distinctions

Compare base code/name, normal/superior/low quality, ethereal, EDmg/EDef percentage,
base defense, total sockets **and contents**, staffmods, inherent resistances/skills,
and completed runeword identity/rolls. Include item level/socket potential, weapon
speed/requirements and player vs mercenary demand in utility evidence.

- Four empty sockets are not three empty plus one filled. Unsocketed is not unknown.
- Do not price completed runewords using the empty base bucket or rune cost alone.
- No universal ethereal, socket or ED multiplier. Staffmods and perfect rolls require
  appropriate comparisons; unknown facets must not default to false/zero.
- Legacy WP-B keys used missing-field defaults. Keep them historical/contextual,
  including their date and unresolved scope. Preserve all suffix conditions
  (`15ed`, resist/skill bands, `affixed`, `filled`). Never upgrade these aggregates
  to verified exact observations. WP-G repeats their asks: do not count it twice.
- Missing market evidence is unknown, never vendor/zero. Report residual gaps.

## Rebuild offline

Choose adapters for changed inputs; preserve original dates and source locators.
Run dependencies before their consumers:

```sh
uv run --offline python -m pricing.knowledge.legacy
uv run --offline python -m pricing.knowledge.refresh --offline-import
uv run --offline python -m pricing.knowledge.facts
uv run --offline python -m pricing.knowledge.recommendations
uv run --offline python -m pricing.knowledge.valuable
uv run --offline python -m pricing.knowledge rebuild
uv run --offline python -m pricing.knowledge.bases
```

When game definitions change, also regenerate `pricing.knowledge.definitions` and
`inventory_tracking.items.build_metadata` before index publication. When socket or
recipe mechanics change, regenerate `pricing.knowledge.utility` before facts.
Inspect module `--help` where supported. Generated bundles must be reproducible from
local sources; do not hand-edit them to hide missing source data.

Validate affected tests, lint and saved-item replays. For a broad update run
`uv run --offline pytest tests -q`. Compare coverage before/after; report counts,
remaining unknown variants, source dates and maintenance failures. Update `handoff.md`
with runnable commands and the next unresolved gap. A running worker needs a restart
for Python/metadata changes.

## Publish the validated runtime generation

After rebuilding the affected artifacts/index and passing regression checks, run
`uv run --offline python -m pricing.knowledge.publication`. It validates staged
metadata, definitions, rules and bundled source evidence before atomically selecting
the generation under `pricing/data/generations`. Failure preserves the previous
pointer; fix the specific mismatch and republish instead of editing generation files.
Verify the selected bundle with
`uv run --offline python -m pricing.knowledge.assessment.maintenance.replay --publication-store pricing/data/generations`
and compare saved report/price output. Publishing integrity does not establish missing
tier/build/market coverage; keep coverage gaps in the handoff.

The Alt+D worker now defaults to that publication store. A running published worker
selects updates at request boundaries and pins one generation/date through capture,
decoding, retrieval and cache use. Restart for Python changes or to migrate an old
legacy worker. Use explicit `--database <path>` only for legacy/test-index operation;
it bypasses publication selection. A missing/invalid initial publication fails with
an actionable error rather than mixing working-tree inputs. Do not delete retained
generations while readers may still use them. No live market collection is implied.

## Optional live maintenance

Only when the user requests fresh research/online maintenance, follow
[pricing-refresh](../pricing-refresh/SKILL.md). Inspect the market manifest's
maintenance hold first; do not hammer HTTP 429/Cloudflare failures. Resume bounded
jobs, preserve failed targets and publish only after offline validation.

Traderie asks require explicit SC / Non-Ladder / PC / RotW properties; unknown scope
is quarantined. diablo2.io fills require matching scope and sold status. Deduplicate
sellers, normalize quantity, preserve ask alternatives and dated Ist conversions.
Generic web guides are not price evidence; Maxroll supplies demand/mechanics only.

## Report estimates and valuable-item watchlist

Run `uv run --offline python -m pricing.knowledge.valuable` after updating
WP-I, appraisal-demand or definitions, and before rebuilding SQLite. This imports
the cached valuable-unique-set-items table, preserving its 2024-03-06 date and
ladder context. It writes appraisal-value-watch.json and
pricing/knowledge/VALUABLE_ITEMS.md. Guide tiers drive keep/review priority only,
never numerical Non-Ladder pricing. Build mentions alone get a separate demand
highlight. Recheck conditions rather than treating every roll as high value.

Numerical report estimates use only scope-verified SC/NL/PC/RotW asks. Legacy
aggregate buckets remain research context and cannot become an estimate.
Classifier contracts now govern numerical estimates: exact identity, rarity,
ethereal, sockets/contents and complete modifier sets. No generic nearby tolerance.
Three dated independent sellers are required for an estimate; stale/undated/thin
cohorts remain diagnostics. Unsupported policies and market mappings remain gaps.
See `pricing/knowledge/assessment/README.md` for the implemented scope.

## Build-demand completeness audit

For missed build/mercenary items, rebuild `pricing.knowledge.builds`, then
`pricing.knowledge.valuable`, then the index. Run
`uv run --offline python -m pricing.knowledge.demand_audit` and read
`pricing/knowledge/DEMAND_AUDIT.md`; the full actionable labels and locators are in
`pricing/data/appraisal-demand-audit.json`. Decorated named items retain original
setup text and canonical identity separately. Preserve variant, side, slot and
socket/set conditions through the watchlist and report. Do not promote every shared
planner profile or a composite prose mention to an endorsed requirement.

Catalog completeness is not demand or price completeness. Review generic patterns,
missing planners and slot-specific important-roll rules separately. Follow
`pricing/knowledge/ASSESSMENT_DESIGN.md` for the planned family/build-role classifier;
its first contracts are implemented; remaining families/profiles are explicit coverage gaps. Never treat a build mention alone as proof
the captured item satisfies a setup. Unknown decoding blocks numerical estimates;
unrelated same-base reference prices stay out of terminal reports.


## Reviewed classifier profiles

After reviewing source-specific role rules, publish with
`uv run --offline python -m pricing.knowledge.assessment.build_profiles`, then
`uv run --offline python -m pricing.knowledge.assessment.coverage`.
Keep source locators/hashes/dates and skill IDs validated. Re-run positive/negative
role cases, comparable exclusion tests and saved-item replays. Native stat semantics
are independent of UI labels and market property IDs. A whole-build stat paragraph
is not a slot-level item requirement. Rebuilding broad demand alone does not create
reviewed role rules. Restore the profile artifact with the offline KB snapshot;
missing profiles cause explicit coverage gaps, never online fetching.

## Completed runewords

`uv run --offline python -m pricing.knowledge.runewords` publishes all definition
records, variable ranges, demand and actual market coverage into
`appraisal-runewords.json`; rebuild the index afterward. This does not fetch prices.
With explicit live-collection authorization, read pricing-refresh and run
`uv run --offline python pricing/tools/collect_runewords.py --collect --pages 2`.
It resumes cached pages and stops on source errors/429. Raw dated responses live in
`pricing/raw/traderie/runeword-refresh/`; --pages 4 expands the existing sample.
Then run refresh --offline-import, runewords, valuable, and rebuild. Rebuild bundled
item metadata when newly observed scalar property labels add market mappings;
review the generated diff and update captured-output expectations only for those
verified mapping additions.

A completed recipe establishes filled sockets/count, not ethereal status. Use the
listing's explicit base selector, and reject No base/missing/incompatible selectors.
Never merge weapon/armor variants or compare by word name alone. All-variable-roll
capture, base/ethereal, defense and exact item properties gate numerical estimates.
A cached ask is not automatically an exact comparable or an estimate. The named
catalog has 101 entries versus 99 game definitions; case-only Hustle variant names
are canonicalized, unknown names are retained without inventing definitions.
