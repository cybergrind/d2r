# Offline guide-first assessment and compact build-use reports

Planned 2026-09-25. This is the next delivery priority, before further per-build
vertical slices or new market collection. Reuse existing cached extraction,
occurrence audits, reviewed rules and report components. No new engine or wholesale
re-extraction of already verified facts. This document specifies work, not completed
coverage or newly established item prices.

## Acceleration strategy — complete inventory, incremental reviewed rules

Added 2026-09-25. “Filter” here means an executable assessment/use configuration:
base/quality applicability, whole-item stat requirements, preferences and outcomes.
It does not authorize changes to the in-game loot-filter profiles. A later exporter
may project only predicates supported by the game filter; preserve more detailed
appraisal rules separately and never hide an item based on an unsupported predicate.

**Start faster by reviewing distinct rules, not every occurrence independently.**
Complete the machine-readable inventory first, then run G2–G5 on bounded rule
batches instead of waiting for deep manual review of every guide and item. The full
inventory stays the denominator for completion. An early useful release is a
coverage milestone, not a claim that all rules or trade tiers are finished.

### A. Reuse existing evidence and work only on changes

1. Load the existing occurrence ledger, reviewed role configurations, definitions,
   prepared recommendations and source manifests. Verify source/version compatibility;
   do not restart from raw HTML when structured evidence already exists.
2. Use source hash, extractor version and schema version to reuse unchanged
   extraction. Track dependencies so a changed guide invalidates its affected uses,
   item demand summaries and compiled rules, not the entire KB.
3. Build a semantic configuration fingerprint from applicability, required stat
   groups, alternatives, thresholds, dependencies, stage and roll semantics. Attach
   all source occurrences to that configuration. Matching prose strings alone is
   insufficient; differing minima/companion conditions remain separate rules.
4. Prepare compact review dossiers: normalized candidate, supporting source excerpts,
   conflicting evidence and uncovered identities. Automation may propose extraction
   and grouping, but new semantic requirements need review before becoming active.

Acceptance: unchanged sources are not re-extracted; duplicate guide occurrences
reuse one reviewed configuration without losing provenance. A changed predicate
reopens the affected configuration and its dependent outputs deterministically.

### B. Family templates with explicit applicability and exceptions

Use a small shared predicate/StatsEvaluator implementation and data configurations.
Each base/item needs a traceable rule assignment, not its own evaluator class.
One reviewed family template can cover many bases when its assumptions hold.

For bases, compile legal recipe/socket/quality/equip relationships from the existing
verified tables. This provides broad mechanical eligibility quickly. Layer reviewed
preferred-base, ethereal, speed, requirements and staffmod policies on top. Legal
eligibility alone must not become “good base” or “keep”; unknown desirability stays
unresolved. Never attach a universal ethereal or superior premium.

For magic/rare items, review reusable combinations such as “required X and Y, with
optional Z”, specialized by legal quality, family, skill identity and role. Reuse the
combination evaluator, not arbitrary affix weights. Exact named uniques/sets keep
identity-specific tier records; shared handlers do not substitute for reviewing
every identity's tiers and leveling uses.

Templates retain an explicit generated membership list, source-backed assumptions
and documented overrides. Override conflicts fail validation. Test positive,
near-miss and unknown cases for every distinct predicate branch, and validate legal
membership across all covered identities. Equivalent members need not receive
copy-pasted tests; exceptions require representative regression cases.

### C. Release useful coverage without starving the rest

Use three milestones:

| Milestone | Deliverable | What remains visibly incomplete |
|---|---|---|
| M0: complete inventory | All scoped bases/named items plus cached guide patterns and occurrences; current rules linked; unresolved queues | Inventory presence is not reviewed rule coverage |
| M1: useful first release | Reviewed reusable rules with largest demand/coverage benefit, compact Build use, combination-aware annotations and saved-item checks | Pending families, specialist uses, tiers and prices remain explicit |
| M2: coverage closure | All eligible bases and named identities have reviewed applicable rules or reviewed no-use dispositions; all known useful patterns resolved; all required tiers and leveling records complete | Unbounded unseen affix combinations remain explicit unsupported cases, never presumed trash |

Prioritize batches by both distinct-build demand and newly covered identities/uses
per distinct rule, with estimated review effort recorded. Do not sort only by raw
mention count or only by market value. A simple reviewed eligibility template may
be cheaper to finish than another bespoke high-demand configuration.

Reserve a tail batch after every two demand-led batches for specialist, leveling,
low-frequency and unresolved cases. This is a scheduling rule, not a limit on total
coverage. Resume checkpoints list remaining IDs, rule dependencies, blockers and
next cases so the long tail cannot disappear behind a “top items done” milestone.

M1 may publish reviewed configurations incrementally under the existing atomic
publication rules. Missing configurations produce REVIEW/unknown with known useful
facts preserved. They do not inherit a default hide/vendor decision or grey stat
dots. Incomplete trade tiers do not become invented prices or auto-trash records.

### D. Separate coverage dimensions and close the denominator

Maintain one coverage matrix keyed by canonical identity/family/quality and use
configuration, with these independent states:

- Discovered/source-accounted-for.
- Mechanics and legal base eligibility verified.
- Reviewed desirability/filter configuration linked (with exact template version).
- Stat combinations and roll annotations supported.
- Set/unique/piece tiers and leveling reviewed, where applicable.
- Report behavior validated.
- Market evidence available, independently of all the above.

For each required dimension, record reviewed, pending, blocked or excluded, with
reason and source locator. A generic family fallback counts as routing only unless
it implements reviewed decisions for that member. Coverage denominators come from
the complete scoped definitions plus the union of guide uses, leveling records,
existing valuable-item evidence and observed unsupported cases. Items absent from
guides remain in scope. Keep market collection off the initial critical path.

Numeric rolls cannot be exhaustively enumerated; required coverage is every scoped
base/named identity and every known useful configuration, with legal ranges and
boundary cases tested. Do not claim knowledge of all future rare combinations.
An unsupported combination creates a durable review entry with its identity/facts
and missing family/configuration, without turning it into a positive or negative
valuation. Newly discovered useful patterns extend the same coverage matrix.

M2 cannot be declared complete with unresolved required identities/configurations
or missing unique/set/piece tiers. Source-blocked records are honest blockers, not
completed coverage. Reviewed no-use decisions require evidence and documented
scope; absence from a guide cannot supply that evidence.

### E. Measure whether the shortcut actually helps

Capture a baseline before implementation: raw occurrences, distinct semantic
configurations, already-reviewed rules, uncovered identities and extraction/review
cost for a representative batch. For each milestone report reused versus new work,
newly reviewed identities/uses, remaining blockers and elapsed processing/review
time. Do not promise a speedup factor before measuring. Verify that duplicate
sources add provenance without extra review or demand inflation, and that a rule
change revalidates its entire membership. Use targeted behavior tests per batch;
run full saved-item/publication checks at release boundaries.

## G1 — Census every cached build, variant and item

Create a manifest of cached guides, prose sections, variant arrays and referenced
planner profiles, retaining hashes, source dates and exact locators. Derive counts
from that manifest; older 33-build totals are historical, not a hardcoded allowlist.
Inspect every build and variant, including guide-only and planner-only contexts.
Missing downloads remain source gaps; this phase stays entirely offline.

Traverse every player and mercenary slot, weapon swap, prebuff, inventory utility,
charm, jewel/socket filler and alternative. Include ordinary bases, magic/rare/crafted
patterns, uniques, set pieces, full/partial sets and completed runewords. Preserve
mercenary act/subtype, build stage, skill parameters, base/ethereal/socket conditions,
AND versus OR options, and required companion/loadout dependencies. A set reference
expands to piece identities while retaining the conditional set-use relationship;
a whole-set mention is not standalone demand for each piece.

Retain immutable occurrence records and normalize into an item-centric reverse
index. Each occurrence carries canonical build/variant/side/slot/item-or-pattern,
recommendation strength (required/preferred/alternative/example/discovery-only),
review state, source provenance and any unresolved identity or source conflict.
Do not treat planner maximum rolls as guide-required minima. Alias resolution,
variant inheritance and shared planners must be explicit and reproducible.

G1 acceptance: every cached occurrence has a disposition and every source/slot is
accounted for. Report raw occurrences, distinct recommended uses, unique builds,
variants and unresolved identities separately. Existing extraction may be reused,
but keyword scans or only already-reviewed profiles cannot stand in for the census.

## G2 — Demand breadth and guide grade

For each canonical item/pattern publish an auditable demand summary:

- Number and IDs of distinct builds recommending it, with primary/preferred versus
  alternatives separate; class/archetype spread is descriptive, not player popularity.
- Unique variants per build and contexts: starter/budget, standard/endgame, MF/GF,
  specialized activities, leveling, player/mercenary and utility/prebuff.
- Qualified uses by exact base/roll/companion conditions, and pending evidence.
- A separate identity-level breadth summary and captured-item match summary.
  Insight in one base must not inherit confirmed fit from all Insight loadouts.

Deduplicate the same semantic use across prose/planner/cache copies and source
aliases. One build contributes at most one breadth vote per item/pattern; ten
variants of one build do not count as ten builds. A shared planner does not establish
endorsement by every linked guide without source-specific evidence. Excluded,
historical-only, discovery-only and unresolved references do not add confirmed votes.
A single build appearing on player and mercenary sides still counts once globally;
side/stage breakdowns retain both uses without adding them to the global total.

**Initial guide-demand rubric (design choice, to validate on the offline corpus):**

| Grade | Distinct reviewed recommending builds |
|---|---|
| High | 5 or more |
| Med | 2–4 |
| Low | 1 |
| No reviewed use | 0 after complete review |
| Pending | Incomplete evidence; counts are a disclosed lower bound |

Display exact counts alongside the grade. Include primary and endorsed alternative
uses in breadth, but expose their separate counts; example/discovery mentions do not
qualify. Breadth is monotonic: adding an independent supported build cannot lower
the guide-demand grade. Grade thresholds are versioned, not market facts. Before
publication review the item-frequency distribution and record any rubric change;
do not invent weights or silently boost items for many duplicate variants.

Guide demand raises the guide-based usefulness/keep priority and orders the rule
review queue. Preserve a separate specialist-use assessment: one build's essential
item can be a strong keeper despite low breadth. Valuable leveling items remain
visible independently. No guide mentions means no reviewed guide use, not trash.

Do not equate this grade with trade price, rarity or high/med/low/trash market tiers.
A common Insight can have high guide demand without being an expensive trade item.
Existing named trade tiers, independent leveling assessments and exact scoped price
gates remain intact. Guides alone can establish use and desirable combinations;
they cannot establish supply, scarcity or Ist prices.

## G3 — Group items and compile guide-derived assessments

Review the item-centric list in descending distinct-build breadth, with explicit
secondary queues for specialist, leveling and unresolved identities. Every item
remains in the queue; breadth changes order, never coverage obligations. Group by
mechanics and compatible use configuration, not name similarity alone:

- Named items: identity-level uses plus distinct variant/roll/set dependencies.
- Bases: recipe/role, base-family legality, sockets, ethereal and staffmod requirements.
- Affixed items: complete required modifier combinations and supporting preferences.
- Completed runewords: identity breadth plus separate base/beneficiary configurations.

Compile reviewed guide statements into existing role policies and the planned
StatsEvaluator configurations. Separate required thresholds, desired targets,
alternatives, illustrative planner rolls and dependencies. Use native definitions
for mechanics validation; if a guide leaves a condition unspecified, retain that
uncertainty instead of guessing. Do not strengthen a preference into a requirement.

Publish per-item guide-use dossiers, deduplicated configuration links and demand
summaries in the existing versioned artifact generation. Appraisal consumes this
prepared data offline; no scraping or source parsing on the hot path. Provenance
and one pinned generation connect demand counts, evaluated matches and report text.

G3 acceptance: every item from G1 maps to reviewed executable configurations or an
explicit blocking source/mechanics gap. Every base/magic/rare matched configuration
feeds stat desirability; roll quality stays separate. Universal unique/set/piece
tier coverage remains a separate completion gate, including identities absent from
guides. No market refresh is a prerequisite for guide-based usefulness updates.

## G4 — Compact Build use, with details on demand

Create one pure BuildUseSummary formatter over structured evaluated outcomes and
prepared demand facts; terminal and OSD render the same summary model. Presentation
must not change matching, count only visible rows, or infer fit from guide mentions.

Default report budget: at most 8 logical lines for Build use and at most 3 role
clusters. Keep shallow indentation, short labels and one shared target line. Narrow
views wrap naturally; line budgets refer to logical entries, not physical wraps.
Use a neutral heading/count, existing fit-status colors and accessible text labels;
reserve the stat dots for their own desirability channel.

Group by beneficiary/role, progression, match state, materially different base
requirements and dependency signature. Aggregate variants within a build and builds
within equivalent roles. Keep confirmed, conditional and unknown groups distinct.
Do not merge starter versus elite-base recommendations when the captured base's fit
differs. Player weapon, mercenary weapon and Iron Golem ingredient are distinct uses,
even if the runeword name is identical.

Default content, ordered by relevance to the captured item:

1. Guide-demand grade and distinct-build count; distinguish identity-level demand
   from this item's confirmed/conditional fit counts.
2. Up to 3 concise role/stage clusters; show at most 3 representative build labels
   across the section plus “+N more”. Use stable ordering; explicit user context can
   prioritize their build, otherwise matched before conditional, then priority/ID.
3. One deduplicated better-roll target line, only for targets relevant to the item.
4. One actionable qualification/limitation line, only if it changes the decision.
5. A detail affordance/omitted-group count when necessary; retain the complete
   structured list for full CLI output and a separately expandable detail report.

Important failed gates or conflicts affecting the recommendation take precedence
over optional examples. They must not disappear behind an arbitrary top-N cutoff.
If needed show a concise “Other uses have different base/gear requirements” line
and route the exact differences to details. Do not insert generic survival warnings
or repeated “mercenary type unconfirmed” for every guide. When evaluating potential
use without a live loadout, group that condition once: “Conditional on merc type/gear”.
Show named armor/helm only when a dependency materially explains fit; otherwise
leave cited loadouts in the detail view. Missing live context is not a broken item.

**Insight mockup — layout only, counts and grade computed from reviewed data:**

```text
Build use · [guide demand] · [N] builds
  Mercenary mana support · Starter / Budget
    Lightning, Blizzard, Hammerdin · +[N] more
  Higher-investment mercenary setups · conditional on base/gear
  Better roll: Meditation level 17 [when this target is source-supported]
  This base: [actual fit or one material limitation]
  Details: [M] guide uses, loadouts and alternatives
```

The rendered report substitutes supported content and omits empty entries; it must
not print bracketed templates. Do not assert Insight is high demand from this
mockup. An Iron Golem role, when present in reviewed data, receives its own compact
cluster instead of being collapsed into mercenary use. The detail view groups by
role then build, lists variant names together, factors common advice once, and
retains exact source locators, original labels, base alternatives, cited armor/helm,
status and unmet conditions. Full detail must remain reachable even when OSD cannot
support interaction; use the existing full terminal/report path rather than adding
inert “expand” controls.

## G5 — Validation, publication and completion

| Gate | Required checks |
|---|---|
| Census | Every cached build/variant/side/slot accounted for; guide-only, planner-only, inherited variants, all alternatives and socket payloads retained |
| Counts | Duplicate text, planner copies and variant aliases do not inflate breadth; one extra independent build increases count; player/merc overlap counted once globally |
| Grade | Boundary tests; count lower bounds under partial review; alternative strength visible; zero mentions never defaults to trash; specialist and leveling usefulness survive |
| Evaluation | Same item across distinct bases/roles; required versus preferred rolls; unknown dependencies; mandatory combinations; no pooled incompatible configurations |
| Display | Saved Insight report reduced to budget; exact full-use counts preserved; no repeated loadout boilerplate; critical restrictions retained; stable order, narrow/plain terminal and OSD parity |
| Regression | Replay existing captures; no named-tier, stat-roll or exact-price semantics changed by grouping; adding duplicate source evidence leaves grade and summary unchanged |
| Publication | Auditable before/after coverage, source hashes/dates, deterministic generation, no network, prior valid generation retained on failure |

Complete the global G1 inventory, then run G2 → G3 → G4 → G5 per reviewed rule
batch under the acceleration milestones above. Small schema/compiler changes may support G1–G3;
large per-build rewrites and further online price collection are not the first step.
Use Insight as the first reporting acceptance fixture, then a multi-role runeword,
a set-dependent item and a combination-sensitive magic/rare item. Finish all-item
coverage after proving the pipeline, not after reviewing only these examples.
