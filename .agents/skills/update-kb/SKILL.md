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

## Optional live maintenance

Only when the user requests fresh research/online maintenance, follow
[pricing-refresh](../pricing-refresh/SKILL.md). Inspect the market manifest's
maintenance hold first; do not hammer HTTP 429/Cloudflare failures. Resume bounded
jobs, preserve failed targets and publish only after offline validation.

Traderie asks require explicit SC / Non-Ladder / PC / RotW properties; unknown scope
is quarantined. diablo2.io fills require matching scope and sold status. Deduplicate
sellers, normalize quantity, preserve ask alternatives and dated Ist conversions.
Generic web guides are not price evidence; Maxroll supplies demand/mechanics only.
