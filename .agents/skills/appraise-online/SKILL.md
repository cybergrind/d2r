---
name: appraise-online
description: Explicit opt-in live D2R item appraisal using scoped Traderie asks and diablo2.io fills. Use only when the user names appraise-online or explicitly requests online/live market checking for an item. Never activate for ordinary screenshots, worth questions, expensive items or local cache misses.
---

# Online appraisal — explicit opt-in

This skill authorizes targeted live research only when the user explicitly requests it.
A screenshot alone, “worth?”, unknown price, stale data or an expensive item is not opt-in.
Default to [appraise](../appraise/SKILL.md). Do not suggest or invoke online research merely
because an offline result is unresolved. These routing rules apply in Pi/Kimi too;
Codex additionally has implicit invocation disabled in agents/openai.yaml.

## Workflow

1. Read the appraise skill for transcription, local lookup, facet selection and the three-part
   report. Its prohibition on live research is lifted only for the explicitly requested item
   in this workflow. All other evidence/price/unknown-field rules remain binding.
2. Start with local lookup and record exactly which comparable class needs current evidence:
   identity/base, rarity, sockets, ethereal status and value-deciding properties. Reuse local
   catalog/property IDs. Do not repeat successful OCR or scan the whole corpus.
3. Read [pricing-refresh](../pricing-refresh/SKILL.md) for the current source tooling, scope
   validation and cache conventions. Use targeted tools under pricing/tools/, not generic web
   price searches. Online item appraisal does not authorize a bulk watchlist refresh.
4. Check any recorded rate-limit hold in pricing/data/appraisal-market-manifest.json before
   contacting that service. Preserve a hold; report the blocker and use cached evidence or the
   other authorized source. Stop on HTTP 429; do not retry around the restriction.
5. Fetch a bounded exact-item sample. Save the response plus fetch time/source/scope metadata
   under pricing/raw/ so results can be imported later. Narrow comparisons locally before
   computing a band. If the sample is empty/thin/incomparable, say unresolved rather than
   widening to another mode or repeatedly paging until a convenient price appears.
6. Produce the same three-part report: actual price/utility, better-roll targets and filter.
   Identify live versus cached evidence and observation dates. No listing creation, messaging
   sellers, loot-filter edits or broad maintenance is included.

## Permitted price sources and scope

- Traderie JSON API through pricing/tools/traderie.py. Required properties: 799 softcore,
  800 false (Non-Ladder), 798 PC, 1854 explicitly containing Reign of the Warlock. Server
  filters are insufficient: verify client-side, quarantine missing/unknown scope.
- diablo2.io trade search through pricing/tools/d2io_search.py with ladder=2 hc=2 plat_pc=1
  legacy_resu=2; activesold=1 for sold-search evidence. Inspect the actual record before calling
  it a fill. Wait at least 30 seconds between requests; retry an empty page at most once.
- No generic price guides, Reddit, d2jsp or other-mode PC threads as price evidence.
  Maxroll establishes build demand, not prices.

Use the tool arguments documented in pricing-refresh; inspect --help if a targeted option
is unclear. The bulk `pricing.knowledge.refresh --refresh-limit ...` command cannot select
one requested item and is not the default online appraisal action.

## Comparison and stopping rules

Unknown listing fields are not zero/false. Verify deciding rolls and empty/filled sockets;
seller rarity labels can be wrong. Equipment bundles are not single-item prices. Deduplicate
sellers, preserve original currency terms and OR groups, and convert with the dated local
Ist ladder. Distinguish asks from fills, listing update time from fetch time and a supported
asking recommendation from an observed sale. A bucket minimum alone is not the price.

Stop when evidence supports the result or the bounded sample cannot resolve it. Preserve
useful self-use/leveling advice independently. Offline fallback remains valid if the network
is blocked; describe that limitation without fabricating current quotes.
