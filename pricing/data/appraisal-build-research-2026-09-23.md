# Build-demand appraisal research — 2026-09-23

Research only. No changes to production ledgers or appraisal code. Scope is SC / Non-Ladder / PC / RotW. Maxroll supplies demand and mechanics, never market prices.

## Measured inventory and denominator

The existing ledger covers **all 26 S/A overall-tier builds**, not all top builds across activities. Those 26 have **116 extracted variants**, **1,662 raw item labels**, **2,756 item occurrences**, and **156 labels mentioned on mercenaries**. Class coverage: Warlock 4, Barbarian 3, Paladin 4, Sorceress 5, Assassin 4, Druid 1, Amazon 3, Necromancer 2. Existing derived catalogues contain 62 recommended bases, 71 demand-linked runewords and 169 magic/rare/crafted/charm patterns. These counts were recomputed from JSON on 2026-09-23; they are not claims that every label is a distinct game item.

A defensible mandatory denominator is **33 builds: union of S/A across overall, density, elite hunting, ladder start and Ubers**. Exactly seven are absent from the ledger:

| Guide slug | S/A source that adds it |
|---|---|
| blood-boil-warlock-guide | Elite hunting |
| fire-wall-sorceress-guide | Ladder start, Ubers |
| frozen-orb-meteor-sorceress | Ladder start |
| frozen-orb-sorceress | Ladder start |
| hydra-sorceress | Ladder start |
| summoner-warlock-guide | Ubers |
| zeal-paladin | Ubers |

The five lists collectively link **58 builds**, leaving 25 lower-tier builds beyond that mandatory union. They are useful secondary demand sources; their absence must never mean an item is worthless. The terror-zone tier list ranks **areas**, not builds, and contributes no guide links. Overall snapshot tiers: S15/A11/B14/C11/D5/F2. These tiers come from already-cached pages fetched 2026-09-18 (overall page updated May 22, 2026), not a new live ranking assertion. Exact slugs by list and tier are in `appraisal-build-source-inventory-2026-09-23.json`.

## Sources preserved during this research

Seven missing guide pages fetched successfully 2026-09-23 via `pricing/tools/fetch.sh`, stored as `pricing/raw/mr/guides__<slug>.html`. The guide cache now holds 33 guide pages (125 HTML pages total, formerly 118). All 35 distinct planner IDs in these HTML pages plus 13 older IDs cited by the existing variant source notes were fetched successfully, giving **48 JSON files in `pricing/raw/mr/planners/`**, **286 profile sets**, and **6,046 raw item definitions**. The tracked inventory contains per-file hashes, source dates, counts and set names. Raw cache is git-ignored, so a durable reproducibility plan must explicitly preserve these files or make the manifest sufficient to refetch and detect drift.

Source URLs: `https://maxroll.gg/d2/guides/<slug>`, `https://planners.maxroll.gg/profiles/d2/<id>`. Existing guide and variant notes establish mappings from Maxroll item IDs through `https://assets-ng.maxroll.gg/d2planner/game/data.json`, `strings.json`, and the RotW d2data dump. The current repository has no locally discoverable `weapons.json` dump: extraction must acquire and pin the actual game-data source revision instead of guessing names or codes.

## Precise gaps and risks

1. Seven top guides have not been extracted into the demand ledger. The 26 existing guides have a substantial previous variant pass; redo by deterministic comparison, not another manual wholesale transcription.
2. 286 raw planner sets are not 286 recommended variants. They include skill trees, testing, embedded tooltips, historical loadouts and unused sets. Record all; tag recommended/embedded/historical/excluded with justification. Never silently discard a `Skill Tree` set: Dragon Talon notes show useful alternate items stored in its cube.
3. Exact raw item properties were collapsed into names. A 1,662-label index is not a canonical catalogue: it mixes counts, sockets, annotations, rare names and runeword-plus-base phrases. `wp_a_variants.py` strips parentheticals and uses substring matching; this loses distinctions needed for appraisal. Preserve raw observations and canonical IDs separately.
4. Generic `Rare Ring`, `Rare Boots`, `Caster Crafted Amulet` rows carry free-text desired stats, not executable thresholds or trade price buckets. Build demand is necessary but insufficient to value arbitrary affix combinations.
5. Current base weights conflate recommended bases with legal bases. An early-game helm runeword resolving to Diadem is a known example; large weight does not make every such base valuable. The full legality graph requires item type inheritance, sockets, item-level caps and game version, separate from recommended base preferences and market evidence.
6. Existing guide prose and planner data conflict in multiple cases: Nova tabs are mislabeled internally; Lightning Fury and Fissure embed older merc/Ubers planners; Dream and Poison Nova refer to missing Hardcore tabs; Strafe Magic Find prose differs from its loadout. Keep both with provenance and confidence; no silent overwrite.
7. Endgame Starter variants are generally Hell-entry budget gear, not complete level 1–75 leveling coverage. Leveling needs an independent class-by-class source inventory and use windows.
8. Existing runeword aliases include Hustle / Mania / Hysteria; base suitability and mode craftability need explicit versioned fields. No inferred ethereal preference may override physical possibility of a base.

## Deterministic extraction design

1. Freeze tier-list/guide/asset/planner manifests with URL, fetched timestamp, source update timestamp, hash, extractor version and inclusion status. Gate mandatory guides at 33/33, then optionally extend to all 58.
2. Parse actual HTML attributes and JSON payloads. Some pages have markup represented inside encoded payloads; plain HTMLParser captured only 20 of the 35 planner IDs, while the source text exposed 35. Decode embedded structures and reconcile parser coverage; do not silently assume DOM spans are exhaustive.
3. Decode the outer planner JSON `data` string. **36 of 48** have nested `planner`; **12 of 48** are legacy direct `items`/`profiles`. Preserve this as a tested compatibility case.
4. For every set, extract equipped items, both weapon swaps, inventory, cube, mercenary slots and recursively socketed items. Retain planner ID + set UID + item ID + source JSON pointer. Resolve direct misc/base-code inventory entries separately from numeric item references.
5. Resolve item IDs to canonical unique/set/runeword/base identities with pinned d2data and Maxroll mappings. Retain quality, ethereal, superior, sockets, staffmods, affixes and exact stats. Extract runeword identity and base identity independently. Reuse IDs and alias tables rather than approximate text matches.
6. Extract table alternatives, prose-only recommendations, set bonuses, prebuff/charge tools and mercenary choices; attach their evidence to the same canonical catalogue. Resolve remaining names to explicit `unresolved` records for review.
7. Compute demand facets: class, build, activity, variant, stage, slot, player/merc, merc act/aura, runeword, base, legal sockets, recommended sockets, affix predicate, source date. Distinguish actual loadout use from mere tooltip reference.
8. Build a watchlist from union of all recommended demand, leveling demand, rare/magic/craft patterns and demonstrated market value. Join snapshots by canonical ID plus roll/base qualifiers. Demand absence alone must never produce `vendor`.

## Completion gates for implementation and review

- 33/33 mandatory top guides indexed with every displayed variant mapped; each unmatched tab or planner set is classified with a reason.
- All 48 fetched planners decode; every item reference resolves or appears in a visible unresolved queue. Counts need not equal recommendation counts, but reconciliation must explain every record.
- Tests cover nested/legacy payloads, alternate weapons, two merc weapons, cube prebuffs, socketed jewels, direct base/misc inventory codes, RotW IDs and stale/prose conflicts.
- No market claim is inferred from build weights. Each watched family has dated scoped evidence, a qualitative keep use, or an explicit unsampled/uncertain status.
- Runeword legality and base desirability are separate relations; tests exercise sockets and item-level gates rather than merely repeating generated tables.
- Offline appraisal fixtures include Sazabi merc gear, Tal Rasha Set Build, Angelic starter pair, dual Plague merc, Enchant prebuff gear, low-value recommended runeword base, and an item absent from build lists but represented in market data.

## Implementation discovery and final import census — 2026-09-23

The initial 48-planner census was incomplete: legacy guide markup also uses `data-d2planner-profile` / `data-d2planner-id`, alongside current `data-d2-id`. The implementation's adversarial test exposed this boundary. Another 67 referenced profiles were fetched: 66 succeeded, one (`1r010653`) returned HTTP 404. The final portable demand artifact records **114 valid planners, 719 sets, 12,625 raw item definitions, and 60,491 occurrence rows** across 33 guides. All raw definitions are preserved, including unused definitions and socket contents; every occurrence has a stable ID and source locator. Source sharing is represented by `details.related_builds`, without guessing ownership or treating every set in a linked planner as a recommendation.

The demand artifact itself is the expanded hashed source census; the earlier research inventory deliberately remains the dated initial observation. `coverage.unavailable_planners` records the historical 404. The 26 existing guides retain their manually reviewed alternatives/variants; the seven new guides have linked item mentions and full planner evidence with `manual_variant_review:false`. Historical disagreement adjudication is still distinct from successful ingestion. Final unresolved counts: no raw planner identity is unresolved; 4,547 prose/legacy labels remain `pattern_or_unresolved` (many are genuine generic rare/crafted/affix patterns, rather than failed item names).

Implementation: `pricing/knowledge/builds.py`; output `pricing/data/appraisal-demand.json`; tests `tests/pricing/knowledge/test_builds.py`. Red/green tests covered missing initial decoder, legacy HTML labels, nested/legacy profile payloads, swaps, dual merc weapons, cube gear, socket fillers, direct item codes, unresolved references, nonrecommended skill sets and unused definitions. Five tests and Ruff passed on 2026-09-23. The importer and its reusable decoder/catalog helpers perform no network access.

Final review pass (2026-09-23): the seven new guides' visible tabs, explicit prose alternatives and mercenary differences were manually reconciled in `appraisal-build-variant-review-2026-09-23.json`; demand coverage now records 33/33 reviewed guides. This reviews source coverage and conflicts, not every gameplay claim. Fire Wall and Frozen Orb/Meteor visibly embed historical profiles in several tabs; both historical and newer source evidence remains. Summoner Warlock's Magic Find prose incorrectly calls the build Blood Boil; review records the typo without reassigning demand. Planner sockets/ethereal values and source-derived spelling aliases are exposed as top-level facets. One historical planner remains unavailable; generic unresolved labels remain explicitly marked.
