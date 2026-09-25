# Implementation status — 2026-09-25

The requested all-item rollout is incomplete. Family dispatch, reviewed roles and
valid comparison contracts are separate from usable market prices. No missing
named tier defaults to trash, and no missing market facet defaults to zero/false.

## Next planned work — offline guides first

[GUIDE_FIRST G1–G5](GUIDE_FIRST.md) is the next delivery order: every cached
build/variant/player/mercenary item → deduplicated per-item demand → reviewed guide
configurations → compact grouped Build use → offline regression/publication.
This priority update does not change the verified coverage below or claim the new
demand grades/report layout are implemented. Full unique/set/piece tiers and stat
combination indicators remain required, including items absent from guides.

## Verified current coverage

| Requirement | Current evidence | Remaining work |
|---|---|---|
| Build-aware routing | Eight family branches in `registry.py`; 290 reviewed profiles compiled from per-build rules | Remaining source-specific roles, variants and dependencies |
| Every source occurrence retained | Fresh occurrence audit: 62,891 occurrences, 34 builds, 591 build/variant pairs; 49,780 discovery-only, 3,929 identity-review and 9,182 rule-review records | Resolve required identities and semantic rule dispositions; direct source links are not proof of complete rules |
| Source-to-rule traceability | 841 occurrences have related rules; 266 have direct source rules | Review duplicates, alternatives, planner context and source-specific predicates |
| All unique/set tiers | 565 identities, 93 reviewed policies, 472 pending, zero invalid policy sources; 141 pending identities have build/leveling evidence | Source-backed defaults and conditional roll/ethereal/socket overrides; explicit reviewed exclusions where appropriate |
| Exact offline comparisons | Base, affixed, named and runeword policies; scoped seller/date/variant gates; typed current/prepared results | Remaining contribution mechanics and reviewed comparison bands; sufficient actual eligible observations |
| Saved-item behavior | Eighteen saved-item replays; Dread Edge now forms a current and upgrade contract | More representative item families and actual positive scoped cohorts; a contract does not itself establish price |

The named audit has two research-only records and 470 without a WP-I research
record. This does not mean those items lack all KB evidence. Disabled drop flags
also do not automatically establish an exclusion or a trash tier.

## Evidence that limits numerical coverage

The current all-market audit (as of 2026-09-25) reports:

| Policy | Scoped observations | Structurally ready observations |
|---|---:|---:|
| Affixed | 8,728 | 558 |
| Base | 3,209 | 20 |
| Named | 7,089 | 611 |
| Runeword | 4,391 | 130 |

These are observations, not independent sellers, matched cohorts or priced items.
Explicit collection days restored from 135 legacy cache wrappers on 2026-09-25;
9,405 observations (4,512 scoped) now retain dated file/hash provenance. No file
timestamp or listing-update date supplied freshness. Structural readiness does not
validate every modifier or meet the three-seller
gate. Dates, base identity, ethereal state, sockets and contents remain material
gaps. The approved six-item mercenary collection is complete; repeating the same
pages does not establish omitted facets. The named-priority batch resumed with
updated client access: 11 successful pages, 550 listings, 186 scoped observations.
The original 12-request cap includes the prior HTTP403. Five items have two pages;
Crack of the Heavens has one. Fresh original Sunder cohorts support exact penalty
variants Flame Rift -72/-75 and Crack of the Heavens -71 on 2026-09-25; other rolls
still require independent matching sellers and dispersion gates. All four newly
sampled armor/helmet identities lack explicit socket state, so none is structurally
ready for exact pricing. See appraisal-named-priority-market-batch.json.

## Next implementation/research priorities

1. Review the 141 pending named identities with actual build/leveling evidence.
   The source-ranked queue begins with Vampire Gaze, Rockstopper, Stealskull,
   Kira's Guardian, Rockfleece, Flame Rift and Undead Crown. Retain conditional
   utility even when tier evidence is insufficient. Cached listings for the first
   four currently lack necessary variant facets; inspect existing raw evidence
   before considering additional explicitly authorized collection.
2. Resolve required build-occurrence identities and executable rules across the
   full source census. Preserve alternatives, mercenaries and leveling. Do not
   count name overlap or a generic planner item as a reviewed role.
3. Continue family comparison gaps: crafted/socket elemental contributions,
   integer per-level listing conventions, ambiguous trigger identities and
   reviewed secondary-roll bands. Do not replace them with generic tolerances.
4. Reconcile architecture migration and compatibility boundaries against A1–A11
   in ARCHITECTURE.md before final rollout. This audit does not claim those gates
   complete merely because tests pass.

## Reproduce the coverage evidence

Run offline from the repository root:

```sh
uv run --offline python -m pricing.knowledge.assessment.coverage
uv run --offline python -m pricing.knowledge.assessment.maintenance.coverage --as-of 2026-09-25 > pricing/data/appraisal-tier-coverage.json
uv run --offline python -m pricing.knowledge.assessment.maintenance.inventory > pricing/data/appraisal-occurrence-coverage.json
uv run --offline python -m pricing.knowledge.assessment.maintenance.market_readiness --all-items --as-of 2026-09-25 > pricing/data/appraisal-all-market-readiness.json
```

The first command now reports named tier completeness separately from profile and
family counts. The other outputs retain the per-identity/per-occurrence details.
Do not declare the goal complete until the full plan's coverage and validation
requirements have current evidence.
