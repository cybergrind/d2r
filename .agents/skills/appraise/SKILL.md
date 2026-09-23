---
name: appraise
description: Appraise D2R item screenshots or tooltips using the offline local knowledge base first; report trade value, leveling/self-use, better rolls and loot-filter rationale. Also retrieve class-specific unique/set leveling recommendations. SC/NL/PC/RotW, Ist = 1.
---

# Offline item appraisal

Run commands from the repository root. Scope: Softcore / Non-Ladder / PC / Reign of the
Warlock; player build: Echoing Strike Warlock. Use local evidence, never web prices.

This is the default appraisal skill. Only an explicit request for online/live market
checking or `appraise-online` selects [appraise-online](../appraise-online/SKILL.md).
An expensive item, stale/missing prices or unresolved result does not trigger that skill.

## Required first evidence action

After reading the screenshot, run the local lookup **before opening guides, wp-* files,
raw caches, or searching the repository**:

```sh
uv run --offline python -m pricing.knowledge lookup "Ring" --rarity rare --limit 2
```

Replace Ring/rare with the observed item and rarity. For randomly named rare/magic items,
query the base (Havoc Eye → Ring; Knight's Mithril Point → Mithril Point). For unique/set
items, query the unique/set name. Unknown identity is a discovery/review case, not a guessed
match. Supply only confirmed sockets/ethereal facets when relevant.

This is the appraisal entry point for every agent, including Pi/Kimi. Do not substitute
manual file scans for it. The full image-to-report orchestrator is still planned;
`pricing.knowledge appraise` does not exist. Use the working commands here.

If the index is missing or incompatible, run once:

```sh
uv run --offline python -m pricing.knowledge rebuild
```

Then retry. If local execution fails, report the exact blocker; do not silently replace
lookup with online research. No dependency/model download during appraisal.

## Read the image once

Transcribe rarity, base/name, every modifier and number, requirements, sockets and ethereal
status. Distinguish absent from unknown on clipped screenshots. Direct visual reading is
appropriate for a clear attached image; OCR is optional, not a required detour.

If an OCR draft exists, reuse it and review flagged fields against the image. When needed,
the EasyOCR command below returns a draft plus offline candidate evidence. Reuse that
evidence instead of repeating equivalent lookups; the calling agent supplies the final
review and decision. The dedicated OCR environment must already be provisioned:

```sh
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 /tmp/d2r-easyocr-env/bin/python -m pricing.knowledge image IMAGE
```

OCR is a draft: never repair uncertain numbers from expected stats. Its `appraisal_ready:
false` is not a reason to rerun successful OCR. Confirm rarity/omitted modifiers visually;
unknown sockets, contents or ethereal status must not default to zero/empty/false. Read
`pricing/knowledge/OCR.md` only for an actual OCR setup/problem.

## Refine locally by the deciding facets

Inspect lookup's evidence, counts, gaps, prepared facts and market status. Reuse all useful
sections; `prepared` contains unique/set requirements and reviewed utility. Large counts
mean evidence was omitted, not that the first two records are the best applicable records.

Resolve property IDs from the local dictionary, not memory:

```sh
uv run --offline python -m pricing.knowledge properties "Faster Cast Rate"
uv run --offline python -m pricing.knowledge lookup "Ring" --rarity rare --property '520=10' --limit 2
```

Add the other confirmed deciding affixes for actual comparables. Matching only FCR is not
an exact-roll price. Preserve unknown properties; do not invent missing predicates.
Choose further searches by the question, rather than always running every branch:

```sh
# Exact base identity:
uv run --offline python -m pricing.knowledge search --base "Crystal Sword" --kind catalog
# Skill discovery across bases (1577 is Sigil: Death in the local dictionary):
uv run --offline python -m pricing.knowledge search --kind market --property-min '1577=3' --limit 3
# Correct base AND sockets AND quality:
uv run --offline python -m pricing.knowledge search --base "Crystal Sword" --kind base_rule --rarity normal --sockets 4 --limit 12
# Specific recipe, without hiding it behind the first two unrelated rules:
uv run --offline python -m pricing.knowledge search --base "Crystal Sword" --kind base_rule --runeword Spirit --sockets 4
# Focused leveling or build evidence:
uv run --offline python -m pricing.knowledge search "fcr" --kind leveling --class sorceress --limit 3
```

Exact `--property 'ID=JSON'` and numeric `--property-min 'ID=N'` can combine with other
search facets. Search hits are discovery evidence: property search currently covers explicit
observation properties, not all planner stats/prose. Cross-base hits cannot be pooled as a
price for the photographed item. Recipe legality does not mean recommended or immediately
usable: check rarity, empty sockets, exact count and mode; unknown item level stays conditional.

## Fill only the remaining evidence gaps

After lookup/refinement, state the missing question internally before a fallback read.
Examples: the discard rule, a better-roll target, or the current filter explanation.
Read only that local source/row; do not run the old full guide/bucket/variant checklist.

- Guide criteria: `python3 pricing/tools/html2text.py guides/pricing.html "Ring (caster)" 450`.
  Use a distinctive phrase, not broad repeated words like `ring`. Expand a clipped row.
- Current filter: select the matching rule in `lootfilter/warlock_lean.json`, then its named
  row in `guides/warlock.html` via html2text. Reuse a verified catalog base code from lookup;
  consult cached d2data only if unresolved. Never guess codes. For unclear filter semantics,
  read the relevant part of `.agents/skills/lootfilter/SKILL.md`.
- Before vendor on rares, magic class items, uniques or sets: inspect indexed demand,
  leveling, skill patterns and relevant base rules. If indexed coverage is insufficient,
  read the specific wp-b-prices/wp-a-blues/wp-a-variants row needed. No build mention is
  not proof of worthlessness. Incidental guide mentions are not keep recommendations.
- Raw JSON/legacy buckets are targeted fallbacks only. `pricecheck.py --cache` is not
  strictly offline and must not be used. Never run refresh tools during appraisal.

Aim for a bounded first response (~2,000 evidence tokens), with focused expansion when
needed. Do not truncate JSON with head/sed and then reason from incomplete records. Stop
price research when supported or unresolved; complete utility and filter checks, then answer.

## Decision rules

- Distinguish name-level watch bands, requested-facet matches and actual comparable rolls.
  `comparable_evidence_requires_roll_review` is not an approved quote. Check scope, affixes,
  single-item quantity, seller counts and dates. Historical `legacy_unverified` buckets
  cannot establish verified prices. Seller rarity labels may conflict with listed modifiers.
- Missing/thin/stale evidence never automatically means vendor. An explicit applicable guide
  rejection can support vendor independently of missing asks; complete keep checks first.
- Keep trade value separate from leveling/self-use. Conditional sets need their companions;
  base legality alone is not a keep reason. Attribute requirements and upgrades stay qualified.
- Give a payable rune/gem asking price only when supported. Convert using the dated local
  `pricing/data/wp-f-ladder.json`; distinguish asks from fills and heuristic offers from sales.
  Otherwise write `Price: unresolved — no matching local comparisons`; do not invent zero Ist.
- No live refresh, market browsing, code/filter edits or corpus maintenance just to answer a drop.

## Report

A screenshot alone requests all three parts; keep the answer concise:

1. **Price as is:** KEEP / SELL / VENDOR / REVIEW, the deciding modifiers, supported payable
   price or unresolved status, and dated source. Separate leveling keep from trade value.
   For a supported discard: `vendor; no trade listing recommended`, with guide-based rationale.
   Label thin samples (<5 sellers or priced observations), unknown dates and asks without fills.
2. **What would make it worth more:** one to three relevant missing/chase rolls. Quote a band
   only with actual comparable evidence; otherwise say the improved roll needs appraisal.
3. **Why the filter shows it:** current matching rule and its intended target; whether this
   item meets that target. Filter inclusion is not proof of trade value.

Cite local source paths/locators. Do not claim OCR, full automation or timings you did not run.
A question specifically about usefulness or filter behavior needs only the requested parts.

## Unique/set leveling recommendations

For a class/level shopping or keep list, the first command is instead:

```sh
uv run --offline python -m pricing.knowledge recommend --class sorc --quality unique,set --max-level 25
```

Disclose the 1–25 default if no level was given. Sorc/necro default to caster; change archetype
for attack variants. Use returned reasons/requirements/conditions/sources and pagination.
`item "Magefist" --full` expands a specific identity only when needed. No three-part price
report is required for a leveling list. See `pricing/knowledge/README.md` only for additional
filters or coverage details, not as a prerequisite to the first command.
