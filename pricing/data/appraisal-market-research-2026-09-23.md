# Offline appraisal market research — 2026-09-23

Scope: Softcore / Non-Ladder / PC / Reign of the Warlock; Ist = 1. Research only. Existing datasets were not overwritten. The six live probes below use the public Traderie API through the repository's `traderie.py` helpers, explicit client-side scope filtering, and `pricecheck.band` conversion. No web price guides were used.

## Inventory and freshness

| Existing artifact | Coverage measured locally |
|---|---:|
| Traderie JSON files directly in `pricing/raw/traderie/` | 296 |
| Listing occurrences in those files (duplicates possible) | 30,918 |
| Cached diablo2.io files | 149 |
| Cached Maxroll files | 118 |
| `wp-b-prices.json` base/class-item rows | 45 |
| Base/class-item buckets | 925 |
| Buckets with priced observations | 754 |
| Buckets with fewer than five priced observations | 728 |
| `wp-i-uniques-misc.json` rows | 139: 65 unique, 24 set, 30 miscellaneous, 13 crafted, 6 rare, 1 charm |
| Unique/misc rows with non-null median | 131 |
| Unique/misc rows with nonempty diablo2.io field | 22 (not necessarily valid scoped fills) |
| `wp-h-jewels-charms.json` rows | 124: 35 jewel, 89 charm |
| Jewel/charm rows with non-null median / nonempty fills field | 113 / 28 |
| Build guides / distinct variant-index labels | 26 / 1,662 |
| Build demand bases / runewords / blue-pattern labels | 62 / 71 / 169 |

The authoritative snapshot metadata predominantly says 2026-09-18. Listing `updated_at` is not fetch time. Several later listing dates exist in raw files, but no uniform fetch manifest ties every raw file to a reliable observation date. File modification time must never supply market freshness. Derived tables can be older than their raw inputs. Counts above measure stored rows, not complete distinct item or market coverage.

Raw listing game-version values: 28,530 exact RotW; 1,202 absent; 911 exact Lord of Destruction; 125 `lord of destruction,reign of the warlock`; 84 `classic`; 56 `classic (base game)`; five reversed RotW/LoD combinations; three RotW/classic/LoD combinations; two LoD/classic combinations. A robust importer tokenizes explicit comma-separated versions and requires an explicit RotW token. Missing and unrecognized versions are quarantined. Combined strings without RotW are rejected. All three other scope fields must also match exactly.

## Representative dated API probes

Fetched 2026-09-23; **asks**, one newest page (50 listings) per item, explicit RotW token, SC/NL/PC. Conversion uses the **2026-09-18** ladder and dated fallback currencies. These are mixed-roll name-level diagnostics, not appraisal prices. Seller voting and OR-group conversion use existing `pricecheck.band`, whose limitations are documented below. Equipment quantities have not been resolved into single-item comparables.

| Item | In-scope / fetched | Priced sellers | Min / median / max Ist |
|---|---:|---:|---:|
| Griffon's Eye | 0 / 50 | 0 | unavailable |
| Sazabi's Mental Sheath | 16 / 50 | 8 | 0.143 / 1 / 8.573 |
| Greater Talons | 49 / 50 | 7 | 22.842 / 34.263 / 57.105 |
| Mithril Point | 43 / 50 | 7 | 11.421 / 91.368 / 456.84 |
| Grand Charm | 27 / 50 | 6 | 0.674 / 3.0265 / 57.105 |
| Bloodfist | 24 / 50 | 14 | 0.02 / 1 / 46.6 |

Griffon's newest page was entirely Ladder. This is evidence that first-page sampling can miss the requested economy, not evidence of no market. Greater Talons has 49 scoped listing rows but just seven convertible seller votes: listing count is a poor coverage target. Bloodfist's mixed aggregate spans 0.02–46.6 Ist and cannot price an ordinary leveling pair. Unconverted alternatives included Small Charm, Grand Charm and Random Minor Key.

Full strictly scoped probe listings, original properties, seller IDs, item quantities, source URLs and observation dates are retained separately in `pricing/raw/traderie/appraisal-research-2026-09-23/representative-probes.json` (git-ignored). This research note is the portable summary; implementation should export normalized evidence into tracked data rather than rely on ignored cache being present.

## Existing failure modes to address

1. `traderie.py listings` and `runes` do not filter RotW. `pricecheck.band` rejects only two exact non-RotW strings, accepting absent versions, `classic`, and combined non-RotW values. Legacy processed rows are not automatically strictly scoped just because their metadata says RotW.
2. `pricecheck --cache` still calls catalog search and silently fetches when a cache file is absent. Catalog IDs, aliases and item types need a portable local cache. Offline must prohibit requests, not merely prefer cached files.
3. The six probe bands mix rarity, sockets, ethereal status, staffmods and premiums. Exact matching predicates must precede band calculation. Median of a name-level feed cannot become an exact-roll quote.
4. `pricecheck.band` discards the entire listing when any price component is unconvertible, even if a separate OR group contains a complete convertible ask. Group conversion should mark only the affected group unavailable; preserve unresolved alternatives as uncertainty. Never partially sum an incomplete group.
5. Seller votes must be deduplicated inside each exact comparable cohort. Deduplicating once at item-name level suppresses distinct premium classes. Repeated listings across files also need source/listing-ID deduplication.
6. Rune/gem stack semantics differ from equipment, and existing paths do not share a single unit policy for keys, essences, sets and other stackables. Equipment amount >1 is ambiguous until terms establish per-item or total-lot pricing; exclude it from confirmed single-item bands.
7. `--id` loses catalog type (`?`), so stackable rune/gem division is skipped; preserving type is correctness-critical.
8. WP-H/WP-I have no deterministic rebuild scripts. Bucket definitions and hand-maintained prose are mixed with computed prices. Thin flags do not consistently mean five distinct priced sellers.
9. Some diablo2.io item pages are explicitly mixed economy; only scoped trade searches with `activesold=1` are fills. Nonempty legacy `d2io`/`fills` fields are not sufficient proof of scoped transactions. Sold-page parsing must retain actual terms and scope or yield unpriced evidence.
10. The historical Top-tier ask-to-fill heuristic is not observed fills for a new item. Preserve separate ask band, observed fill band and optional heuristic; never silently transform one into the other.
11. Low-rune fallback values are inconsistent across legacy code and metadata. Every conversion needs currency snapshot ID/date and approximation flags. Price refresh and currency refresh must be independently visible.
12. Current raw cache filenames include variants, duplicated prefixes, spaces, IDs and `.json`. Deriving canonical identity from filenames is unreliable; identity comes from catalog IDs and verified d2data mappings.

## Recommended cache design

Use relational facets for identity, rarity, slot, item class, sockets, ethereal, superior, numeric affixes, staffmods, level restrictions and recipe eligibility. Full-text lookup adds aliases and prose. Vector similarity is optional for ambiguous narrative discovery; it cannot establish exact sockets, thresholds, runeword legality, market scope or price matches.

Maintain a portable, versioned JSON export (or JSONL for observations) and derive a SQLite index locally. Normalized observations should include source and listing ID; catalog/canonical item ID; raw and normalized properties; seller ID; all price OR groups; original price currencies and quantities; item quantity; unit policy and ambiguity; source listing date; independent UTC `observed_at`; scope fields and validation result; source URL/raw checksum; currency snapshot ID/date; computed comparable class IDs. Preserve unknown fields without inventing values. Explicitly distinguish historical imported metadata dates from newly observed dates.

Separate long-lived demand/mechanics from expiring market observations. A class can be known valuable or useful for leveling while its numerical quote is stale/unresolved. Keep nullable prices and statuses such as `fresh`, `stale`, `missing`, `offer_only`, `thin`, `scope_unknown`, `unconverted`, `ambiguous_quantity`. No status implying zero value follows from missing asks. Leveling usefulness is independent of resale price and requires a slot/class/level/use-case record.

Bulk coverage should join **all catalog uniques/sets/currencies**, all build/variant/merc/leveling named items, verified runeword/base/socket combinations, and valuable affix classes. Finite named items can be exhaustively inventoried; combinatorial rares need explicit pattern rules and an unknown-item retention fallback. Never claim all valuable rolls are already enumerated.

## Refresh policy and acceptance targets

- Separate explicit refresh CLI from offline appraisal CLI. Appraisal has no network fallback, even for expensive or unknown items; it returns the best dated evidence and queues missing class coverage.
- Bootstrap IDs/types/aliases once; preserve catalog pagination manifests, fetch dates and checksums. Use exact canonical IDs for subsequent price jobs.
- Refresh demand-driven cohorts in parallel with bounded concurrency and retries; maintain budgets and resume manifests. Fetch beyond one page until a minimum scoped distinct-seller target or configured page cap is reached. Track cap reached, pages, excluded scope, offer-only and unconvertible counts. Scarcity never licenses unsafe scope relaxation.
- Initial proposed schedules: currency daily; frequently appraised/high-value classes every 1–3 days; ordinary saleable items weekly; low-value leveling inventory monthly. These are configurable operational proposals, not claims about measured market volatility.
- Build broad baseline coverage, then stratify by exact meaningful rolls: named unique roll breakpoints; base/socket/eth/superior/staffmods; skiller tree/life; jewel affix combinations; rare/craft slot gates. Refresh important empty cohorts explicitly rather than interpret absence as zero.
- diablo2.io fill jobs remain serialized with at least 30 seconds between searches and one retry on empty response. They use `ladder=2 hc=2 plat_pc=1 legacy_resu=2 activesold=1`; no generic item page qualifies as scoped fill evidence.
- Track denominators separately: known items, demand references mapped, mechanics combinations supported, value classes, classes with observations, classes with at least five distinct comparable sellers, unknown/version-quarantined rows, dated fills. A single completion percentage hides missing evidence.
- Red/green tests must cover no-network offline hits/misses; strict scope including unknown/multi-version cases; OR alternatives with an unknown group; stack and equipment units; seller votes per class; affix boundary near misses; staleness and currency provenance; pagination with a first page wholly outside scope; reproducible export/import with no ignored raw cache.

The 2026-09-21 speed review measured 94% less output, not end-to-end latency. New benchmarks should replay screenshot-transcribed fixture queries and measure tool rounds, payload tokens/bytes, total local query time and answer correctness. Aim for one compact offline retrieval payload containing identity, matched patterns, demand/leveling reasons, exact comparable evidence, next-better thresholds, and current loot-filter match.
