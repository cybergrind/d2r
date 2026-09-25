# Implementation status — 2026-09-25

The requested all-item rollout is incomplete. Family dispatch, reviewed roles and
valid comparison contracts are separate from usable market prices. No missing
named tier defaults to trash, and no missing market facet defaults to zero/false.

## Next planned work — offline guides first

[GUIDE_FIRST G1–G5](GUIDE_FIRST.md) is the next delivery order: every cached
build/variant/player/mercenary item → deduplicated per-item demand → reviewed guide
configurations → compact grouped Build use → offline regression/publication.
Reviewed demand batches and compact reports are implemented as recorded below;
this does not establish full guide or item coverage. Full unique/set/piece tiers and stat
combination indicators remain required, including items absent from guides.

## G1 inventory checkpoint — 2026-09-25

`python -m pricing.knowledge.assessment.maintenance.guide_inventory` now builds
`pricing/data/appraisal-guide-inventory.json` from the existing structured ledger
and variant slots. It preserves every occurrence's details and provenance, seeds
unmentioned catalog identities, and links conservative semantic configurations.
Baseline: 62,891 occurrences; 33 cached guides (34 occurrence build labels including
shared-planner); 1,355 catalog identities; 2,887 total identity/review buckets;
19,311 unresolved occurrences; 297 reviewed profiles / 275 distinct configurations.
All sources registered and hashes verified. A deterministic repeat took 6.425s on
this workspace, with no raw guide/planner extraction; no speedup claim is made.

This is a 109 MB maintenance checkpoint, not a hot-path or published artifact.
G1 remains incomplete: source-slot completeness, set expansion, aliases and
recommendation strength need explicit auditing. G2 grades and G4 compact reporting
are not implemented by this inventory. Next work must use GUIDE_FIRST order rather
than returning to isolated per-build additions.

### Structured variant slot audit

The maintenance inventory now retains source-slot dispositions for the separate
`wp-a-variants` documents: 1,687 represented item slots, 434 empty slots and 116
mercenary context fields across 232 present sides. No missing/conflicting labels
were found in this subset. Original context (including delta/planner flags and
quotes) is preserved; representation does not establish endorsement or inheritance.
The consolidated `wp-a-builds` audit additionally accounts for 2,269 item slots,
441 empty slots and 132 context fields; all 5,510 source occurrences are linked,
with no missing/conflicting labels. It preserves legacy unescaped locators, staged
mercenary alternatives and prose-only entries. Eleven focused tests pass.
G1 still requires raw planner/source section accounting, explicit inheritance/aliases and set links;
these subset counts do not prove the global source-slot gate.

### Planner structure reconciliation

The maintenance audit now traverses cached planner profiles, inventory/cube,
mercenary equipment and socket children without repeating name extraction.
All 49,780 planner occurrences have matching source references; 8,945 empty slots,
740 empty containers and four absent containers remain explicit. No missing,
conflicting or unaccounted occurrences were found. The existing unavailable
planner `1r010653` remains a source gap. Thirteen focused tests pass, including
missing children, mismatched references and cycles. These are structural counts,
not endorsed build uses; raw guide sections and semantic relationships still need
G1 review. Runtime publication is unchanged.

### Set relationship inventory

Definition-backed relationships now retain 1,913 piece-membership references,
eight set-reference candidates and two explicit full-set candidates. Every link
retains the original occurrence/locator and complete canonical member list.
Partial-set wording does not require all pieces; none of these links establishes
standalone endorsement. Definition hash/date/input provenance is retained.
Fifteen focused tests pass. Alias resolution and semantic set-use review remain
pending, so these candidate links do not close G1 or increase demand votes.

### Canonical planner identity correction

The reverse index now uses explicit planner canonical IDs, checking category and
canonical/alias labels against the catalog and quality prefix against planner
quality. Conflicts stay unresolved without name fallback. This resolves 15,380
falsely unresolved affixed base occurrences: unresolved occurrences decrease from
19,311 to 3,931; total identity buckets decrease from 2,887 to 2,739. All 49,780
planner identities reconcile with zero conflicts. Rarity, original display labels,
stats and source details remain on the original occurrences; grouping by base
identity does not pool affix configurations or increase demand votes.
Twenty focused tests pass. Runtime publication is unchanged.

### Explicit variant context dispositions

The inventory now records 232 source variant contexts across consolidated and
separate documents (copies remain provenance, not independent votes): 42 explicitly
Hardcore contexts excluded from Softcore demand, 22 planner-only contexts requiring
endorsement review and 168 other contexts awaiting review. There are 34 delta-only
source records; none has a structured parent link, so no equipment inheritance is
inferred. Original purpose, notes, quotes and planner references remain attached.
Twenty-two focused tests pass. These source dispositions do not alter runtime roles
or establish completed G1/G2 review.

### Cached guide section inventory

All cached `guides__*.html` files are now independently enumerated: 33 pages,
2,015 text sections, zero pages outside the existing demand manifest. Section
heading, anchor, source position and full prose are retained in the maintenance-only
`appraisal-guide-sections.json`. Hash/extractor-version reuse avoids parsing unchanged
pages; repeat output is byte-identical. Script/style text is excluded; navigation
and other non-item prose remain pending relevance review. Twenty-four focused tests
pass. Section presence is not semantic completeness: span-to-ledger reconciliation
and section review remain next, before declaring G1 complete.

### Guide span reconciliation and embedded references

All 5,201 saved guide occurrences reconcile with cached extractor spans; no ledger
rows are unaccounted for. The audit additionally retains 271 empty unresolved spans
that the legacy extractor skipped. Inspection found planner tooltips encode
profile/set/item IDs rather than visible names. Section cache v3 now preserves all
397 embedded item references with source positions and section links; resolving these
against cached planner profiles is the next concrete gap. These references are not
yet endorsements or active rules. Twenty-six focused tests pass; runtime unchanged.

### Embedded tooltip resolution

The 397 guide references now resolve against exact cached planner UID/item IDs:
203 link to existing set occurrences, 107 identify definitions outside that set's
recorded loadout, 82 reference absent sets and five lack the referenced item.
Available item definitions are retained even when the set is absent; no other set
is substituted. These review links preserve section positions and item/profile
locators without promoting planner rolls to thresholds. Twenty-eight focused tests
pass. Runtime rules/reports remain unchanged. Next review these source conflicts
and guide prose together before producing endorsed G2 counts.

### Source conflict review queue

Inspection confirms the 82 absent-set references target six UIDs not present in
their cached planner profile lists. They are now six grouped source blockers,
alongside five missing-item blockers. Every affected guide position/section and
available set UID/name is retained; definition-only alternatives are not classified
as missing-source failures. Thirty focused tests pass. These blockers affect their
own uses; they do not prevent reviewed configurations elsewhere from progressing
through G2–G5 once the global inventory disposition gate is checked.

### First reviewed demand batch — Insight

Added maintenance.guide_demand and explicit guide_use_reviews.json decisions for
12 existing Insight profiles: 11 guide-backed preferred configurations, one
planner-only example excluded from votes. Five distinct builds support the identity;
summary stays Pending with High lower-bound breadth while corpus review is incomplete.
Variant/player/merc duplicates cannot inflate votes; historical, shared-planner,
Hardcore, examples and unreviewed evidence cannot vote. Source and complete profile
fingerprints invalidate stale reviews. Four red-green behavior tests cover counting,
grade boundaries, exclusions and invalidation. This is an unpublished maintenance
batch; G1 semantic gaps remain explicit and no captured-base fit is inferred.
Next connect the prepared summary to compact BuildUseSummary and validate Insight
alongside existing saved reports before runtime publication.

### Compact BuildUseSummary prototype

Added a pure immutable summary model with an eight-entry budget, three visible
clusters/build labels, shared roll targets, explicit failed/unknown counts and all
original role details retained. Duplicate role evidence is idempotent; conflicting
same-ID results fail. Conservative grouping preserves base/dependency/beneficiary
and variant distinctions. Three red-green tests pass. Saved Insight preview has
eight entries and all 12 role details, with five conditional builds distinct from
the reviewed identity-demand lower bound. Preview: tmp/insight-build-use-preview.txt.
Not wired into live reporting yet: grouping labels/progression need refinement,
and full-detail access plus terminal/OSD parity and publication integration remain.
No price/matching/roll behavior changed.

### Compact detail access and restrictions

The prototype now renders readable build names and surfaces a failed requirement
even when its group is omitted. Additional restriction counts route to full detail.
A saved-record CLI (`python -m inventory_tracking.appraisal.build_use_summary
RECORD --full`) exposes all uses, conditions, alternatives and source locators.
Five focused tests pass. Saved Insight compact/full commands verified eight compact
entries and all 12 source-backed detailed roles. Live terminal/OSD wiring, reviewed
role/progression grouping and pinned demand publication remain outstanding.

### Compact renderer enabled

The terminal and OSD now call the same compact BuildUseSummary through the shared
presentation model. The previous detailed formatter remains available, alongside
the saved-record `--full` CLI. Heading styling is preserved. Red parity test → green;
125 focused tests and full suite 2,622 passed / 3 skipped. All 18 published saved-item
replays retain identical assessment semantics and prices; five report texts change,
including Insight's eight-entry Build use. Historical artifact hashes differ but
all remaining assessment fields match. No artifact publication change was needed
for this Python presentation change; restart the worker. Prepared guide demand is
not yet published/wired, so live headings omit its count. Reviewed role/progression
aggregation and demand publication remain next; this does not close G4/G5 broadly.

### Reviewed demand published

Guide-use decisions and summaries are now embedded in the compiled profile bundle;
publication verifies role fingerprints and recomputed counts. Runtime uses the same
pinned profile bytes; legacy bundles omit demand rather than consulting working-tree
reviews. Insight now renders Pending / at least five builds independently of item
fit. Full suite: 2,624 passed / 3 skipped; additional pinned-legacy regression passes.
All 18 saved prices/role/fact/tier/leveling results unchanged; staged/published text
matches and only Insight's heading changes from the prior compact baseline.
Published generation `446e4de125a37891d674f924ed387234047b078e3c57bd558fd8ffa085552b25` (46 artifacts).
Restart worker for Python changes. Other identities and G1 semantic gaps remain
pending; next refine role/progression grouping and extend reviewed demand batches.

### Reviewed progression and grouping boundary fix

Compact grouping now includes evaluated rule and skill traces; previously different
rules could share a row if visible labels matched. Reviewed presentation stages
allow equivalent variants to merge, with original variants retained in full detail.
Insight Starter, Endgame (Standard/MF), and Ubers stages are explicit reviewed data;
no arbitrary unknown-variant stage inference. Actual Insight loadouts remain split
where dependencies/conditions differ. Starter contexts sort ahead of later stages.
121 focused tests; full 2,626 passed / 3 skipped. All 18 saved prices and evaluated
role/fact/tier/leveling results unchanged; staged/published text parity verified.
Published `59756e9538135c0fdb2c0ff8256487c23f59cbd9c6af70a555dad4ed4fa468a4`. Restart worker for Python changes.
Further role-summary refinement and additional reviewed demand batches remain.

### Second reviewed demand batch — Infinity and Sazabi

Added six source-reviewed identity uses: Infinity's three player/merc configurations
count as two distinct builds; Sazabi's three pieces each retain one conditional Ubers
build endorsement. The full-set, Act 5 Frenzy, rune and companion requirements remain
in their existing executable roles. All grades remain Pending because corpus review
is incomplete. Reviewed demand now covers five identities / 18 decisions (one excluded
planner-only Insight example). 29 focused tests pass, all 18 saved prices/assessments
unchanged; only Sazabi's saved heading changes. Staged/published replay parity passes.
Published `a67fb831e984375a5b1256f46e67bf962bcb3954b75f9fb078a73fd89469dd3a`. The next batch must serve the specialist/leveling
or unresolved tail after these two demand batches, per GUIDE_FIRST scheduling.

### Scheduled tail batch — Death's set early gear

Reviewed four explicit Starter/Budget uses for Death's Guard (three builds) and
Death's Hand (one build). Independent cached leveling evidence remains active;
Death's Hand's paired-belt condition and upgraded Death's Guard requirements remain
in the evaluator. One-build breadth does not remove conditional leveling usefulness.
Demand records now cover seven identities / 22 decisions, including the excluded
planner-only Insight example. 18 focused tests pass; all 18 saved reports, prices
and assessment semantics unchanged; staged/published parity verified.
Published `0dcd1656c164abfcf3eb80a250ce23b0e279e015108ee79e5a088d5be40824e1`. Tail scheduling obligation after two demand batches
is met; next demand batches should broaden identity coverage with source-backed
rules, while remaining tiers/market/source gaps stay explicit.

### Utility demand batch — Teleport swap and Enchant prebuff

Reviewed 18 existing source-backed utility roles: Naj's Puzzler has 13 distinct
endorsed-alternative builds; its planner-only Budget example is excluded. Demon Limb
has four prebuff contexts across three builds, with Strafe's Lava Gout alternative
kept separate from preferred uses. Charge availability, recharge/ethereal limits and
equipment requirements stay in the evaluator. Demand review now covers nine identities
and 40 decisions (two excluded planner examples), not nine priced identities.
36 focused tests pass; all 18 saved texts/prices/assessment semantics unchanged;
staged/published replay parity passes. Published `e742e521f6a2d4b2d5f9fc5eff787c852d43b4b44d14362222465734bcf31af1`.
Next one demand batch may precede the scheduled tail batch. Broad scope remains open.


## 2026-09-25 — mercenary gear demand batch

Reviewed 18 existing role records across seven additional identities. Distinct
endorsing builds: Vampire Gaze 4, Crown of Thieves 1, Stealskull 3, Duriel's Shell 2,
Kira's Guardian 1, Rockstopper 1 and Undead Crown 1. Crown's planner-only Leap example
is excluded. Cannot Be Frozen and Fissure starter alternatives remain alternatives;
mercenary/loadout/socket/ethereal conditions remain in the existing evaluator.
Demand review totals: 58 decisions, 16 identities, three excluded planner examples.
These are incomplete demand lower bounds, not new prices or completed named tiers.

Red: missing mercenary demand summary. Green: 11 demand tests and 28 affected role
tests; Ruff passes. All 18 saved texts, prices, roles, facts, tiers and leveling
results remain unchanged. Staged/published assessments agree apart from publication
provenance; text and price parity verified. Published generation:
`4547b5c945281cdf79167cbbfe6c31e026388c208d88f63e7d91492875fe3e79`.
Evidence: `tmp/merc-demand-*`; regression in
`tests/pricing/knowledge/assessment/test_guide_demand_runtime.py`.
Rebuild profiles and maintenance guide_demand, replay, publish, then replay with
`--publication-store pricing/data/generations` using the existing offline commands.

This completes the second demand-led batch since the Death's set tail review.
Next: a specialist/leveling/unresolved tail batch before another demand-led batch.
All-item rule, source review, named tier and market gaps remain open. No new market
collection or runtime Python changes in this batch.


## 2026-09-25 — Sigon's starter combination tail batch

Reused nine existing executable roles and reviewed their three unchanged source
variant records. Added four named demand identities: Sigon's Visor (two builds),
Gage and Sabot (three each), Wrap (one). Starter farming context is preserved; it
is not automatically low-character-level leveling evidence. Strafe/Double Throw
helm-gloves-boots and Berserk gloves-belt-boots remain distinct configurations.
Player companions, Ort versus IAS-jewel socket conditions and unknown loadout
states retain their existing behavior. No whole-set expansion to uncited pieces.

Red: missing Sigon's demand summary. Green: 33 demand, starter-set, socket-payload
and upgrade tests (1.29s), Ruff and diff checks. All 18 saved texts/prices and
role/fact/tier/leveling results unchanged. Published replay equals staged replay
except artifact provenance. Generation:
`9700486b59d4c64738410089bbe62d0bbcd19f56a5dedd8c7086084b873796ca`.
Logs and replays: `tmp/sigons-tail-*`. Review totals: 67 decisions, 20 identities,
three excluded planner examples. No new evaluator or price rule was inferred.

Scheduled tail batch complete; next demand batch should broaden configuration
coverage beyond named items, reviewing how base/affixed patterns connect prepared
demand to captured-item matches. Current demand lookup is identity-name based;
pattern coverage must not be claimed from named-item counts. Reuse source-backed
amulet/ring/base rules, preserving skill identities and required combinations.
All-item named tiers (472 pending at last audit), source review, market and
architecture gates remain open. No network, staging or commits in this batch.


## 2026-09-25 — prepared demand for exact affixed configurations

Added reviewed `pattern` records referencing exact non-named profile IDs, with
source and full profile fingerprint validation. Prepared summaries keep a separate
namespace. Runtime `demand_for_item` selects only true item predicates with
matched/partial outcomes, unions distinct builds and preserves named identity
semantics. Missing/false/unknown/null traces add no votes; duplicate evaluated
roles do not inflate counts. Common pure counting moved to `demand_counts.py`.
Compact report labels the selected scope as matching stat combinations.

First three configurations: Lightning Starter magic +3 Lightning amulet; Nova
Starter magic +1 Lightning / 10 FCR; Blizzard Starter magic +1 Cold / 10 FCR.
Reviewed exact cached slot locators and non-planner-only Starter contexts. +3
Lightning/10 FCR yields two builds; without FCR one; Cold uses remain separate.
Wrong rarity and incomplete modifiers supply no claim. No new price/fit rule or
inference from a rare item's generated title. Counts: 70 review decisions across
20 named identities and three exact patterns; three excluded planner examples.

Red: missing pattern selector; then full-suite null-trace regression reproduced
and fixed. Green: 2,634 tests passed, three skipped (90.06s); Ruff and diff checks.
All 18 saved reports/prices/roles/facts/tiers/leveling unchanged; staged/published
assessment parity apart from provenance. Published:
`5c6089e0e90d19f07b8a7a798ca676a276fa83684fdddc5561186118f84ad655`.
Logs: `tmp/pattern-demand-*`. Restart the Alt+D worker for these Python changes.

First demand-led batch after Sigon's tail. Next: review source-backed rare-ring
combinations and base configurations through the same exact-pattern path; after
one more demand-led batch reserve a specialist/leveling tail. No arbitrary pattern
pooling: shared templates and full coverage matrix remain unfinished. All-item
named tiers, market coverage, source review and architecture gates remain open.
No new market collection, staging or commits.


## 2026-09-25 — rare-ring pattern demand batch

Reviewed all six existing rare-ring configurations: Lightning Starter/Ubers,
Nova Starter, Blizzard Starter/Magic Find/Set Build. Exact source hashes, slot
records and non-planner-only variant contexts checked. Candidate requirements
stay distinct from secondary planner roll targets. Repeated rings and variants
count once per build. Retained native element identities, quality restrictions,
complete modifier combinations and conditional full-loadout evaluation.

Red: rare-ring candidate had no prepared demand. Green: 23 pattern-demand,
rare-ring role and demand compiler/runtime tests; Ruff and diff checks. A cast-rate,
mana, all-resistance and MF ring matches five configurations across three builds;
removing two resistance elements removes the Starter Lightning/Nova combinations.
Unknown capture does not prove the missing resistance. Blizzard's strength/life/
cold-resist Starter combination works separately without requiring cast rate.
No new evaluator, named tier or numerical price assumptions.

All 18 saved texts/prices/role/fact/tier/leveling results unchanged; staged/published
assessments agree apart from artifact provenance. Published `bc4e4c5ca6d38b6d05af244e4b5ce3daee6214049a6ef5d212d9469ae99c8421`.
Evidence: `tmp/ring-demand-*`. Review totals: 76 decisions across 20 named identities
and nine exact patterns, including three excluded planner examples.

Second demand-led batch after Sigon's tail is complete. Next reserved tail:
review specialized base uses (for example Gold Find socketed swords), first checking
whether existing evaluated outcomes expose complete item predicates for prepared
demand selection. Null traces must remain unverified, never promoted by role name.
All-item source/configuration, named tiers, mechanics and market gaps remain open.
No runtime Python change, network collection, staging or commits in this batch.


## 2026-09-25 — specialized six-Lem sword tail batch

Reviewed seven existing Gold Find sword records against their exact source slots
and variant flags: Standard off-hand and both War Cry/Whirlwind swap hands qualify;
two planner-only Leap examples do not vote. Five configurations still count as one
build. Total reviews: 83 across 20 named identities and 16 patterns; five excluded
examples. This is demand coverage, not additional priced identities.

Preserved exact base/quality/class/socket predicates and six linked rune dependency.
Empty or differently filled swords remain conditional preparation; only the exact
six-Lem payload satisfies the rune dependency. Known three sockets, magic quality,
wrong class and unknown class do not establish this pattern's applicability.
Unknown item-level socket outcome remains explicit preparation, never an assertion
of a guaranteed six-socket result. Existing ethereal non-attacking limitations stay.
Report heading generalized from matching stat combinations to matching configurations.

Red: missing base-pattern demand, then report scope wording. Green: 38 focused
pattern/compiler/runtime, rune-payload and formatter tests; Ruff/diff checks. All18
saved texts/prices/roles/facts/tiers/leveling unchanged; staged/published parity
apart from provenance. Published `064e8d435a884f0a90c9c6055be8eb4a98de227d1871b64934d0f65814326278`. Evidence `tmp/gold-tail-*`.
Restart worker for formatter wording; no evaluator behavior changed.

Scheduled tail complete. Next focus: reusable base eligibility and socket-outcome
coverage against native definitions (GUIDE_FIRST B/D/G3), with reviewed desirability
kept separate. More demand records alone cannot close mechanics, stat-desirability,
named-tier or numerical-price coverage. Audit the current base path for item-level,
quality, recipe and socket dependencies before extending family templates.
Full source review, all named tiers and architecture/market gates remain incomplete.
No network collection, staging or commits.


## 2026-09-25 — base socket mechanics audit and unknown-state fixes

Cross-checked every cached legal type/capacity edge against local native weapon,
armor and item-type tables: 5,092 edges / 426 base identities, zero socket-cap
mismatches. Source hashes and dated evidence: `tmp/socket-native-audit.json`.
This verifies capacity data, not complete family desirability or prices.

Found and fixed two missing-evidence paths. `utility.socket_options` treated an
explicit null current socket count as zero, and absent item-type limits could
produce zero-socket outcomes or TypeError. It now returns conditional/unverified
results with no proposed counts. Base capacity is validated separately; known
unsocketable bases do not produce a zero-socket action. `prepare_sockets` could
label absent caps impossible or fail during low-quality normalization; it now
returns unverified with no preparation requests before either route is planned.
Valid existing socket and recipe rules remain unchanged.

Red: six utility cases plus six preparation cases reproduced the failures.
Green: 30 focused tests; full suite 2,648 passed / three skipped (93.56s), Ruff and
diff checks. All18 published saved texts/prices/full assessments unchanged.
Publication revalidation retains `064e8d435a884f0a90c9c6055be8eb4a98de227d1871b64934d0f65814326278` (no data rebuild/change needed).
Logs/replay: `tmp/socket-audit-*`. Restart worker for Python mechanics changes.

Next: turn the verified mechanical denominator into the planned independent
coverage matrix, linking legal base eligibility to reviewed desirability policies,
stat annotations and market evidence without conflating those dimensions. Review
remaining unsupported base families/recipes from that matrix; do not infer demand
from legal compatibility. All-item named-tier, source review, price and architecture
gates remain open. This mechanics audit does not consume a demand-led review batch;
Gold Find was the last scheduled tail. No network, staging or commits.


## 2026-09-25 — independent base coverage matrix foundation

Added maintenance/base_matrix.py with a deterministic offline command:
`uv run --offline python -m pricing.knowledge.assessment.maintenance.base_matrix`
redirect to `pricing/data/appraisal-base-matrix.json`. Native catalog denominator:
523 bases / 1,569 normal-superior-low-quality rows, including unmentioned and
unsocketable bases. All native socket-cap checks agree with cached recipe edges;
426 bases have legal type/capacity links. 114 quality rows have candidate profile
links (type ancestry/quality only), explicitly not reviewed template membership.

Separate dimensions: discovery, socket mechanics, recipe eligibility, desirability,
stat annotations, named-tier applicability, report and market evidence. Every state
has a reason; sources retain file/hash provenance. All1,569 recipe/desirability/
annotation/report/market rows remain pending membership audits; this does not erase
existing runtime features or claim they are fully covered. Named tiers excluded
only because these are base-quality rows, not because named items leave scope.
Base-level market counts never become quality/ethereal/socket/roll-matched prices.

Red: missing matrix module. Green: 32 matrix, utility and preparation tests; Ruff,
diff check and byte-identical real-corpus regeneration. Tests verify full denominator,
unmentioned bases, duplicate edge idempotence, unsupported quality membership,
independence of market/desirability and conflicting/missing cap evidence. No runtime
code/artifact changes; selected generation remains the last published Gold Find
bundle. No new network, staging or commits.

Next: audit exact base/template membership and recipe availability into this matrix,
including reviewed mechanical exclusions where native socket/type rules prove them.
Do not leave every dimension permanently pending or mark type-name links reviewed.
Then integrate named/affixed configuration dimensions with existing audits; this
base-only matrix is not yet the required unified all-item matrix. Full all-item
pricing, tiers, useful modifiers and source/architecture gates remain incomplete.


## 2026-09-25 — native recipe membership closes mechanical matrix dimension

Added maintenance/recipe_eligibility.py and integrated it into base_matrix. It
independently enumerates completed native recipes using both type parents,
excluded types, base capacity, exact rune order/count and complete flags. Missing
or unexpected cached edges block review; duplicate edges are idempotent. Absent
catalogs remain pending; empty catalogs and incomplete ancestry block conclusions.
No use/value exclusion follows from missing or incompatible runeword recipes.

Actual corpus: 99 completed native recipes, 5,092 matching legal edges, 426 bases
verified and 97 mechanically excluded from runeword compatibility; zero conflicts.
Across quality rows: 1,278 reviewed / 291 excluded type-capacity entries. Full mode
availability and quality-specific preparation remain pending separately. No new
Non-Ladder availability claims, desired-base assignments or price assumptions.

Red: missing native membership module, then empty-catalog false exclusion.
Green: 35 distinct focused native/matrix/utility/preparation tests; Ruff and diff
checks. Real matrix regeneration byte-identical after validation. Native recipe
file/hash added to source manifest. Output pricing/data/appraisal-base-matrix.json;
command unchanged. Maintenance-only changes; no runtime behavior/artifact change
or need to republish the existing runtime generation.

Next: close recipe mode/quality-route evidence and exact reviewed template
membership using this matrix; integrate named and affixed configurations into the
unified all-item matrix. No source absence or mechanical exclusion substitutes for
reviewed demand/tier/price conclusions. All-item tier, market, annotation and
architecture gates remain incomplete. No network, staging or commits.


## 2026-09-25 — combination-aware stat evaluator foundation

Inspection confirmed that §8.1 desirability was not implemented: report colors
represent roll quality only. Added immutable StatConfiguration/StatPriority/
StatEvaluation and pure StatsEvaluator in assessment/stat_evaluation.py. It reuses
typed predicates, applies explicit quality/type filters and complete mandatory
combinations before activation, retains traces/provenance and merges strongest
positive annotations only across independently matched configurations. Source,
version, role linkage, review state and rationale are required. No conversion from
important_stats, no compensation by optional stats, no fake absent stat rows,
no default grey/trash and no inference of roll quality.

Red: evaluator import/contracts absent. Green: five evaluator tests plus five
existing pattern-demand tests; Ruff/diff checks. Cases cover X+Y, below/unknown Y,
quality mismatch, independent incomplete/complete uses, alternatives, exclusions,
context, identification/socket state, unknown review, inactive supporting stats,
duplicate/conflicting configs and immutable inputs/results. Roll channel remains
unassessed. No runtime integration/config publication or report change yet.

Next required step: reviewed configuration compiler with role fingerprint/source
validation, reuse existing role outcomes/dependencies (do not create another role
engine), indexed pinned artifact and shared result integration, then terminal/OSD
line mappings and independent dot/text colors. First real configurations should
use the already-reviewed amulet/ring combinations; priorities need explicit review,
not inferred importance lists. All-family migration, roll policy and coverage-aware
irrelevance remain required. No price behavior change, network, staging or commits.


## 2026-09-25 — stat compiler and linked-role gating

StatsEvaluator now consumes existing RoleAssessment outcomes or compatibility
mappings, defaults missing roles to unknown, and retains complete linked dependency/
preparation evidence. Conditional/failed/unknown roles cannot earn confirmed markers;
duplicate identical outcomes are stable and conflicting outcomes rejected. Standalone
combination tests explicitly supply matched role fixtures. No second role engine.

Added maintenance/stat_configurations.py: exact role fingerprint, source path within
root, source-file SHA256, review date, explicit scope/predicate and priority validation.
A changed role or source invalidates the review. No auto-conversion from important_stats.
Three explicit source-reviewed amulet priorities are in rules/stat_use_reviews.json:
Lightning Starter skill ranks, Nova Lightning+FCR, Blizzard Cold+FCR. Their full existing
role conditions remain conditional. Real typed-role regression proves these do not gain
confirmed markers merely because the item modifiers pass.

Red: missing role-outcome API and compiler module. Green: 13 focused evaluator,
compiler/real-role and pattern-demand tests; Ruff and diff checks. No runtime result
integration or publication yet; no report/price change. No network/staging/commits.

Next: embed compiled configurations in the pinned profile bundle with publication
validation, index selection, and immutable AssessmentResult field. Then implement
semantic stat-line mapping and terminal/OSD channels. Review generic role conditions
as mandatory versus advisory before promising confirmed green dots for local item
combinations; do not silently weaken existing dependency gates. All §8.1 roll-policy,
irrelevance, per-family coverage and full objective requirements remain outstanding.


## 2026-09-25 — published stat configurations and shared result integration

build_profiles now embeds explicit stat reviews and compiled configurations in the
existing profile artifact. stat_bundle.py serializes/deserializes immutable records
and validates semantic equivalence to embedded reviews/roles without source-file
reads. Offline compilation still verifies original source bytes; publication also
validates bundled profile sources. ProfileRepository validates configurations once
per generation and indexes quality/type applicability using existing CandidateIndex.
Runtime loads only prepared pinned data, never working-tree stat review files.

Engine passes existing typed roles to StatsEvaluator and stores its immutable result
in AssessmentResult.stat_evaluation. The compatibility JSON contains configurations,
traces and annotations when applicable. Explicit injected profiles do not inherit
bundled stat configurations. Legacy generations without the field make no claim;
a test proves an in-flight pinned snapshot stays unchanged across repository update.
Tampered priorities are rejected. Three reviewed amulet configurations remain
conditional under full-loadout requirements, with no confirmed positive annotations.

Red: absent bundle API, then integration fixture corrected to pin the complete
repository snapshot rather than supply an incomplete strict artifact bundle.
Green: full suite 2,663 passed / three skipped (89.79s), Ruff/diff checks. All18 saved
texts/prices/roles/facts/tiers/leveling unchanged; staged/published assessment parity
apart from provenance. Published `0097052e70bc61d8e7f86c46b322af917a4236219a7e2a9080e02d158340621f`. Evidence `tmp/stat-bundle-*`.
Restart Alt+D for Python integration. Terminal/OSD dot rendering is still pending.

Next: verified semantic-to-display stat attribution and independent desirability
marker/roll-text styling, with real conditional-use explanation and mandatory versus
advisory review. Preserve current role gates; do not force dots by erasing unmet
conditions. Then expand configurations/family coverage and remaining native/template,
named tier and scoped pricing gaps. No network, staging or commits.


## 2026-09-25 — independent stat marker and roll-text presentation

Added stat_markers.py, mapping prepared positive annotations to decoded display
lines with one unambiguous native StatKey. Green `● [desirable]` and readable blue
`● [supporting]` preserve plain-text meaning; stat text keeps its existing roll tone.
Combined lines with multiple keys and unreviewed/unsupported meanings remain
unmarked. No renderer evaluates role predicates or creates a grey/trash fallback.

StyledLine now supports immutable StyledSpan segments. Existing unsegmented payloads
retain their shape; segmented payloads validate that spans reproduce the literal
line. Rich and escaped GTK markup render the same independent colors. ItemAssessment
uses these lines for terminal and OSD. Current real amulet roles remain conditional,
so no positive marker is manufactured for them.

Red: missing marker renderer; integration fixture then supplied required decision
metadata. Green: 47 focused display/formatter checks; full suite 2,668 passed / three
skipped (92.45s), Ruff/diff checks. All18 published saved texts/prices/full assessments
unchanged. Evidence tmp/stat-markers-tests.log and tmp/stat-markers-published.json.
No data artifact change; generation remains 0097052e70bc61d8e7f86c46b322af917a4236219a7e2a9080e02d158340621f.
Restart worker and OSD process for Python mixed-span rendering support.

Next: review mandatory versus advisory conditions for real local stat combinations,
without weakening typed dependencies, and expand configuration coverage. Verify
combined/split line contribution attribution before marking those lines. Numeric-only
roll text styling, reviewed roll policies, coverage-aware irrelevant markers, all
base/magic/rare families and remaining tier/market/source/architecture gates are
still required. No network, staging or commits.


## 2026-09-25 — explicit advisory review enables local amulet markers

Reviewed the three cached Starter amulet slot requirements and their sole generic
full-loadout reminder. StatConfiguration now permits exact advisory_conditions;
compiler rejects text not present in the linked role conditions. Version2 amulet
reviews classify the whole-build breakpoint/resistance/resource reminder as advisory
for local skill/FCR usefulness only. Existing role outcomes remain partial and retain
their missing notes. No claim that the entire character build is ready.

Local annotations are allowed only when complete item predicates pass, remaining
missing notes are entirely the reviewed advisory set, and rule/skill/dependency/
equipment gates are true/met. Unknown/false dependencies, hypothetical preparation,
additional missing conditions or unreviewed notes still block markers. Empty advisory
fields are omitted when serializing, preserving prior published configuration shape.
Prior bundle semantic validation passes with the new implementation.

Red: absent advisory contract; then real amulet tests had no expected annotations.
Green: full suite 2,669 passed / three skipped (90.97s), Ruff/diff checks. End-to-end
example tmp/stat-advisory-example.txt shows two desirable markers while both relevant
build roles remain partial. All18 saved texts/prices/roles/facts/tiers/leveling unchanged;
staged/published parity apart from provenance. Published `1884b617e7a8d63b545acf48a183a795f61a6a242399d1c11ce1c148ef9dc9fe`.
Evidence tmp/stat-advisory-*. Restart worker for Python advisory gating changes.

Next: review explicit essential/supporting priorities for rare-ring configurations,
then further families, keeping whole-combination checks and exact advisory scope.
Combined/split stat attribution, numeric roll-only coloring, reviewed roll policies,
irrelevance coverage, full named tiers and market/source/architecture gates remain
required. No network, staging or commits.

## Rare-ring stat priorities — 2026-09-25

Six existing reviewed rare-ring roles now have explicit source-bound stat priorities:
Lightning Starter/Ubers, Nova Starter, Blizzard Starter/Magic Find/Set Build.
Together with the three amulet reviews, nine configurations are prepared. Cast
rate is desirable where required; source-listed resources, resistances and utility
are supporting only after the complete mandatory combination passes. The generic
loadout reminder is advisory for local markers; Nova resistance-mix and Uber gear
conditions still block confirmed markers. Role fit, roll quality and prices are
unchanged. No broad important_stats list was converted automatically.

Red/green: missing configurations failed first; 22 targeted tests now pass, with
positive, near-miss, incomplete-capture, wrong-quality and independent-use cases.
All 18 saved reports/prices/roles are unchanged; selected-generation replay matches
staged assessment output. Published generation:
`c218e03381259865c57d09ae988a998340b922d7a462e66fca72175de9490df7`.
This data-only annotation batch does not add demand votes or close all-family
annotation, unified coverage matrix, unique/set tier or market gaps. Next annotation
work should cover a reviewed base/specialist configuration and its boundary cases;
keep pending coverage dimensions explicit under GUIDE_FIRST.

## Six-Lem specialist stat annotations — 2026-09-25

Seven existing Gold Find Barbarian sword uses now have explicit source-bound gold
find priorities (16 total prepared stat configurations). A marker requires captured
450% gold find, exact six-Lem child linkage, eligible normal/superior base, known
Barbarian context and identification. It cannot come from the stat total alone.
Preparation and hand-use/durability notes are advisory only for this local marker
once payload validation passes; overall role fit remains conditional. Ethereal
status does not alter the gold-find marker or establish an ethereal premium.

Red/green: the new socket-stat test first failed on missing configurations. Thirty
affected tests pass, including wrong/missing rune links, duplicate child IDs, wrong
base/quality/socket count, unidentified items, insufficient gold find, unsocketed
bases and wrong/unknown class. All 18 saved reports, prices and role outcomes remain
unchanged; staged and selected-generation assessments agree. Publication:
`639c6e542b32a3cce3ad968ff83b05d0b3f3b1239f5c8a965879b82a607d8240`.
No new demand votes or market evidence. This specialist annotation batch still
leaves the unified identity/use coverage matrix, broader stat configurations,
unique/set tiers and price coverage unfinished. Next: unify the existing base
matrix and named/guide inventories so uncovered identities and configurations have
one explicit per-dimension denominator before further annotation batches.

## Unified coverage matrix foundation — 2026-09-25

`maintenance.coverage_matrix` joins the existing guide identity inventory, native
base-quality matrix, named tier audit and prepared use/stat configurations. Output:
`pricing/data/appraisal-coverage-matrix.json`. Each dimension retains state, reason
and source locator; independent row kinds have separate denominators. An existing
use rule never upgrades identity-wide desirability, leveling, report or price
coverage. Compiled stat priorities are separate from complete roll annotations.

Current counts: 2,739 identity/review rows (1,355 catalog-resolved, 1,384 unresolved),
1,569 base-quality rows, 368 use-quality assignments from 297 profiles. Named tier
joins retain 93 reviewed identities; 472 named identities remain pending. Sixteen
stat configurations cover 23 quality-specific uses. No total-row item-count claim.

Red/green checks cover omitted-from-guides identities, unresolved labels, independent
dimensions, stale tier sources, duplicate rows, dangling occurrence identities and
stale input snapshots. Seventeen affected tests pass; Ruff passes. Two complete
corpus builds are byte-identical. Base and guide inventories were refreshed offline
using existing extraction; 62,891 occurrences remain accounted for. Input hashes and
the guide profile fingerprint must match before the matrix is built.

This maintenance-only foundation is not the completed GUIDE_FIRST denominator:
separate leveling/valuable/observed-unsupported inputs still need an explicit union,
identity-to-template membership needs review, and known pattern applicability remains
unresolved. Next extend those missing input links and add actionable per-dimension
review queues. No runtime changes, market collection or new publication in this batch;
selected runtime generation remains `639c6e542b32a3cce3ad968ff83b05d0b3f3b1239f5c8a965879b82a607d8240`.

## Leveling and valuable-item coverage union — 2026-09-25

The maintenance matrix now retains all 75 prepared named leveling recommendations,
13 generic leveling patterns and 223 valuable-item records. All 298 named records
link by exact quality/name to one catalog identity; the 13 generic patterns stay
blocked for explicit identity/configuration review. Missing or ambiguous names are
never merged. Full evidence, dates, conditions and locators remain attached, with
reverse evidence links on identity rows. Reviewed explicit/inferred leveling uses
have their own reviewed dimension; they do not mark identity-wide review complete.
Watchlist tiers/asks do not become reviewed market tiers or exact prices.

Twenty affected tests pass after red/green cases for evidence union, ambiguity and
explicit source recommendations. Ruff passes; two complete matrix builds are
byte-identical. Source-input hashes from recommendations and watchlist are validated
alongside prior manifests. New denominator: 311 evidence records, separately from
2,739 identity/review, 1,569 base-quality and 368 use-quality rows.

Next: add durable observed-unsupported capture entries and actionable per-dimension
review queues, then close known pattern/template assignments. The 13 unlinked
leveling patterns are concrete tail candidates. No runtime change/publication or
live market collection; previous selected runtime generation remains active.

## Observed replay ledger and dimension queues — 2026-09-25

`maintenance.observed_review` imports saved replay results into the durable offline
`appraisal-observed-review.json` ledger. Capture path/content hash identifies each
record. Repeated imports are idempotent; changed assessments append history, retain
original facts/unknowns and replace only the current gap list. Unseen captures are
not dropped. Current corpus: 18 captures, 79 open gaps split into capture facts,
market mappings, reviewed-use coverage and market evidence. No gap implies zero
value, no demand or permission to collect live prices.

The unified matrix adds observed_capture rows and per-dimension review_queues with
row ID, reason and provenance. Independent dimensions remain pending unless their
own evidence is complete. Source hashes are checked before integration. Queue order
is deterministic by row ID; demand/effort scheduling is a later review step.

Red/green cases cover idempotence, resolution history, unseen capture retention and
queue separation. All 23 affected tests pass; Ruff/diff checks pass. Re-importing
the real ledger and rebuilding the matrix are byte-identical. Replayed all 18 saved
items against the selected generation: assessment, report and prices unchanged.
This is maintenance-only: no runtime publication or worker restart is required.

Next: use the queues to review generic leveling patterns and exact template
membership. The ledger currently covers imported saved replays only; automatic
worker capture ingestion and new unknown-item discovery remain separate work.
Full named tiers, family annotations and exact market coverage remain incomplete.

## Generic leveling audit and Topaz linkage fix — 2026-09-25

Audit correction: all 13 generic leveling patterns already have executable
conditional policies in policies/generic_leveling.py and policies/socket_leveling.py.
The matrix's 13 unlinked records indicate missing configuration links, not absent
runtime evaluators. Do not implement duplicate policies. Next maintenance work is
to link each source-indexed pattern to its exact policy applicability and tests.

The audit found a real false-positive path: Topaz armor accepted any positive MF
and a child with a Topaz base code without complete child linkage or sufficient
observed bonus. It now reuses complete_fillers to verify counts, unique unit IDs
and positions, then requires at least the sum of native Topaz MF bonuses (9/13/16/
20/24 by grade). One occupied and one empty socket remains valid; all sockets need
not be filled. Source values verified against pinned d2data gems.json. The positive
fixture now includes actual linked-child evidence instead of relying on incomplete
socket metadata. Regression cases failed before the fix and pass after it.

Full suite: 2,681 passed, 3 skipped in 89.35s. Ruff/diff checks pass. All 18 saved
published-generation replays are byte-equivalent as parsed JSON to the previous
run; no prices, roles or existing reports changed. This is a runtime Python fix:
restart the Alt+D worker to use it. Data generation is unchanged.

## Existing generic-leveling policy links — 2026-09-25

`maintenance.leveling_links` connects all 13 cached generic recommendations to
existing runtime policies. Affixed patterns retain exact quality/type/stat-group
applicability, archetypes and conditions; socket patterns retain the exact policy
symbol/source index. Each link carries the reviewed candidate-source fingerprint,
implementation hash and shared identified/non-ethereal guards. Both ring policies
remain distinct under their shared source pattern. Matching requires exact cached
name/timestamp/slots/context/market-evidence fields and source URL, not name alone.
Changed source fingerprints fail; changed recommendation text stays unlinked.

The matrix now has zero unlinked evidence rows in the current 311-record union:
298 named records and 13 linked patterns. Leveling coverage has 88 reviewed uses
(75 named plus 13 conditional patterns). This is not full identity coverage, stat
annotation support, report validation or market pricing; those dimensions stay
separate and pending. No new evaluator or runtime behavior was introduced.

Red/green link tests and the complete policy test directory pass: 275 tests.
Ruff/diff checks pass; two full matrix builds are byte-identical. Runtime generation
and saved-item behavior are unchanged from the previous validated Topaz fix.
Next use the matrix's remaining desirability/stat/tier queues for actual coverage
expansion; base template membership and 472 named tier reviews remain unfinished.

## Definition-backed named socket facets — 2026-09-25

The pending named-tier audit found explicit rune/gem payloads with missing socket
counts. Normalization now proves one filled socket only when every named unique/set
variant is socketable and lacks a native sock modifier, and property 934 identifies
one known rune/gem. Quest socketing is capped at one for these qualities (local
D2MOO SUnitNpc.cpp:2286). Native socket-roll items such as Tomb Reaver/Crown of Ages,
generic Jewel, blank/None and multiple-filler descriptions do not inherit a count.
Explicit conflicting counts are retained and rejected. Base upgrade and ethereal
facets remain independent unknowns. Source/definition generation is recorded.

Six scoped cached observations in the mercenary batch gain the count: Vampire Gaze
2, Shaftstop 2, Stealskull 1, Crown of Thieves 1. Across the full cache, named
structurally ready observations increase from 611 to 616 (7,089 scoped unchanged).
Readiness is not an exact modifier match or a three-seller cohort; no missing tier
was assigned from this change. Existing caches still lack other required facets.

Red/green regressions cover explicit proof, native sockets, ambiguous payloads and
contradictions. Full suite: 2,697 passed, 3 skipped in 94.81s; Ruff/diff checks pass.
Offline import, runewords, watchlist, bases and index rebuilt. All 18 saved reports
and prices are unchanged; selected-generation replay matches staged assessment.
Published `fd8f967470aec9ebf0ee4de9cc8a8f1528bafdc78234ffffd1664b4adfe57ff3`.
Tier/base/unified matrix and market readiness audits refreshed. No live requests.
Restart the Alt+D worker for the Python normalization change.

Next: continue source-backed rule/tier review with exact variants; missing seller
facets cannot be filled by assuming an unsocketed/non-ethereal default. The named
policy and all-family/stat coverage gates remain incomplete.

## Fixed native named sockets — 2026-09-25

Prepared definitions now retain conservative native_socket_range data, calculated
from property func14 min/max or positive parameter, inventory dimensions, base
capacity and all three native item-level brackets. Only the same count across every
bracket and same-name definition establishes a fixed listing count. Variable,
missing or unsupported encodings stay unknown. This uses the pinned local
ItemMods.cpp PropertyFunc14 and Items.cpp ITEMS_GetMaxSockets mechanics.

Sixteen identities have fixed counts, including Moser's, Ali Baba, Hone Sundan,
Witchwild, Bonehew, selected Griswold/Immortal King pieces and Spike Thorn. Market
normalization records definition-generation provenance, preserves omitted socket
contents as unknown, and rejects contradictory explicit counts. No empty-socket,
ethereal or upgrade defaults were added. Cached scoped count recovery: 309 rows
(Bonehew267, Ali Baba16, IK Stone Crusher18, IK Will8). Named structural readiness
remains616/7,089: other facets are still missing, so no new price is asserted.

Red/green tests cover parameter clamping, variable rolls, item-level ambiguity,
missing tables, definition-backed counts, unknown contents and explicit conflicts.
Full suite: 2,700 passed, 3 skipped in92.26s; Ruff/diff checks pass. Rebuilt definitions,
metadata, facts, recommendations, profiles, offline market and downstream data/index.
All18 saved reports/prices unchanged; staged and published assessments agree.
Published `0b0b4209ca4e5f1c1398d1f1c54b6a4cb085f94712cd7e6066beeea80e010c86`.
Updated replay ledger and guide/tier/base/unified coverage audits. No live requests.
Restart Alt+D for the Python change. Remaining work includes reviewed base-template
membership, guide-use/stat coverage and472 named identity tier policies.

## Runtime-equivalent base profile routing — 2026-09-25

The base matrix now reuses CandidateIndex and the typed predicate evaluator with
partial catalog facts instead of expanding type ancestry and ignoring must guards.
It records each assignment's exact profile fingerprint, source and guard trace.
A proven-false guard excludes an assignment; unknown rolls, ethereal/sockets,
identification and loadout remain unknown. No synthetic stat zero or current-item
fit is inferred. The unified matrix retains these traces and a separate reviewed
policy_routing dimension; desirability and prices remain pending.

Across 1,569 base-quality rows, broad profile candidates shrink from114 rows to6:
618 selector assignments contain600 proven-false guards and18 unknown candidates.
These are build-role-profile assignments only. Separate recipe mechanics and
base-use policy coverage are not removed or counted as failed by this result.
This makes the existing profile denominator honest; it does not fill every base's
reviewed usefulness/template gap.

Red/green tests reproduce the ancestor-selector mismatch and base-code pruning,
while retaining unknown modifier/ethereal candidates. Sixteen affected matrix,
recipe and link tests pass; Ruff/diff checks pass. Two corpus base-matrix builds
are byte-identical, and all assignment traces survive the unified matrix join.
Maintenance-only: runtime generation and saved-item behavior are unchanged.
Next review actual base-use policy assignments alongside these role profiles;
do not mistake the six candidate rows for all base assessment coverage.

## Base perfection evidence gates — 2026-09-25

The base-use audit found two false positives: perfect preferred base could be set
before checking capture completeness/identification, and roll strengths read raw
stats without the shared conflict check. Perfect status now requires complete,
identified capture. Superior ED/defense/AR claims additionally require superior
quality, and all roll reads respect typed native-stat conflict state. Independent
valid strengths remain available; conflicts do not turn the whole item worthless.

Red/green regressions reproduce incomplete/unidentified captures, normal quality
with superior-looking values and duplicate native damage/AR stats in both mercenary
and Grief paths. Full suite: 2,703 passed, 3 skipped in88.71s; Ruff/diff checks pass.
All18 published saved reports, prices and assessments are unchanged. No data
publication needed; restart the worker for the Python fix.

A separate read-only catalog audit of the actual base-use evaluator found438 routes
across183 base-quality rows (61 base identities). With item flags, sockets and rolls
unknown, all438 remain unverified and none claims perfection. This is separate from
the build-role profile matrix's six remaining candidate rows. The audit does not
prove full desirability coverage or price coverage. Next fold these actual base-use
routes into the matrix with source/version evidence and explicit remaining gates.

## Base-use routes integrated into coverage — 2026-09-25

The base matrix now invokes the existing base-use evaluator with shared partial
catalog facts, in addition to auditing build-role profiles. It retains runeword,
beneficiary, source locators, preparation state, strengths, missing requirements
and alternatives. The unified matrix preserves the complete routes. A separate
base_use_routing dimension distinguishes a performed audit from an omitted one;
desirability, actual item fit and market evidence remain separate pending dimensions.
Source manifests now include runtime base-use/preparation code and item metadata.

Corpus: 438 base-use routes across 183 base-quality rows, alongside 618 build-role
selector assignments. All 438 remain unverified with unknown item/socket evidence;
none claims a perfect base. Two complete base builds are byte-identical and all
routes survive the unified join. Nineteen affected tests pass after red/green
integration and omitted-audit cases; Ruff/diff checks pass. Maintenance-only change:
no runtime publication or additional worker restart is required.

Next extend actual reviewed base-use coverage from cached guides, beginning with
caster sword bases currently absent from the Spirit player-quality branches.
Preserve class, progression, ethereal durability and socket-preparation distinctions;
existing route counts do not establish complete all-base usefulness or prices.

## Spirit caster sword bases — 2026-09-25

Added reviewed caster-use routing for Crystal Sword, Broad Sword and Long Sword.
The utility KB explicitly recommends Crystal Sword for Spirit; the other two remain
legal alternatives, not promoted guide recommendations. All use existing socket
preparation, quality and captured-fact gates. Casting gets no superior physical-damage
premium or mercenary ethereal preference. Ethereal melee durability and unknown
ethereal status remain explicit; wearer/setup verification prevents perfect claims.
Source: appraisal-utility.json, Crystal Sword/sockets_by_runeword/Spirit plus native
runes/Spirit;weapons/{crs,bsd,lsd} legality edges. No new prices or build votes.

Red/green regression covers three bases, known/unknown ethereal state, unsocketed
preparation, wrong sockets and magic exclusion. All 18 saved published reports and
price estimates are unchanged. Evidence: tmp/spirit-sword-published.json;
full suite log: tmp/spirit-sword-full-tests.log. Restart Alt+D for Python changes.

## Call to Arms prebuff bases — 2026-09-25

Added reviewed prebuff routing for Crystal Sword, Flail and War Scepter using
appraisal-utility.json recommendation locators `<base>/sockets_by_runeword/Call to Arms`.
Native recipe edges gate legality. Prebuff skill utility does not inherit physical
ED/AR premiums or a mercenary ethereal preference. Ethereal melee durability remains
explicit; War Scepter staffmods and intended wearer/setup still need verification.
No named-tier, build-count or numerical-price changes. All use existing socket
preparation, including impossible high-ilvl superior Crystal Sword and low-ilvl
five-socket targets. Red/green tests cover these boundaries and filled sockets.
24 affected base/preparation tests and Ruff pass. Saved replay evidence:
`tmp/cta-base-published.json`; refreshed matrix: `tmp/cta-base-matrix.json`.
Restart Alt+D for this Python change. Broader template, annotation and price coverage
remains pending; these routes are not coverage closure.

## Shared caster/prebuff templates — 2026-09-25

Replaced growing Spirit-sword and Call to Arms branches with one evaluator in
caster_base_templates.py. Two versioned immutable configurations explicitly assign
six recipe/base pairs, source locators, role-specific advice and a War Scepter
staffmod exception. Compilation rejects overlapping memberships, missing provenance
and exceptions outside membership. Native recipe legality remains independently
gated, and all six assignments are tested against the prepared native recipe index.
Recommendations still determine preference separately; no additional build votes,
prices or generalized type-wide demand were introduced.

Red/green configuration validation plus existing behavior/preparation tests: 26 pass.
All 18 saved reports/prices and all 1,569 base-quality audit rows are unchanged.
Maintenance source hashes now include the template module, so edits invalidate the
base matrix. Refreshed unified matrix; evidence tmp/base-templates-{published,matrix,coverage}.json.
Ruff checks pass. Python-only refactor: no new runtime data generation; restart the
worker when adopting code changes. Remaining family templates and stat annotations
are not complete. Next scheduled tail batch should address a specialist/leveling
use from the unresolved queue, rather than adding another high-demand weapon slice.

## Tail batch: mercenary Crushing Blow leveling — 2026-09-25

Reviewed existing source appraisal-leveling-candidates-2026-09-23.json,
/generic_patterns/6 (17:42): explicitly includes Act 2 mercenary boss use. The
previous generic runtime policy emitted player use only and globally rejected
ethereal items. Added a separate conditional mercenary pattern for unique/set
polearms and spears with positive known Crushing Blow. Named definition validation
remains enforced by assess_leveling; conflicting stats, unidentified items and
impossible ethereal sets are excluded. No imaginary magic/rare Crushing Blow
polearm affixes were added. Damage, speed, survival and wearer requirements remain
conditional, with no price or named-tier inference.

Moved ethereal gates to side-specific pattern applicability; socket/player patterns
retain non-ethereal gating. Source deduplication includes beneficiary so player use
cannot erase mercenary use. Maintenance policy links preserve each side's guards.
Red/green Hone Sundan cases cover ethereal true/false/unknown, unidentified/conflicting
stats and wrong identity/base. 271 policy/link tests and 121 report/link tests pass;
Ruff passes. All 18 saved reports/prices unchanged in tmp/merc-leveling-published.json.
Unified coverage refreshed in tmp/merc-leveling-coverage.json. Python-only change;
restart Alt+D. The source fingerprint remains unchanged; no runtime data publication
or live collection required. This is the scheduled tail batch after the Spirit/CTA
base batches; remaining family, stat annotation, named-tier and market gaps persist.

Next resume a demand-led reusable family/configuration from the current coverage
queue, retaining GUIDE_FIRST separate usefulness/price dimensions and explicit
unknown facts. Do not count this conditional rule as complete unique/set coverage.

## Heart of the Oak caster base — 2026-09-25

Added Flail to the shared caster templates for Heart of the Oak, using the cached
explicit utility recommendation. Native recipe legality remains separate; no sword
compatibility or all-mace preference is inferred. The template preserves setup and
wearer requirements, separates physical damage from caster utility, and describes
Oak Sage/Raven charge use. Ethereal is not assigned a price premium: repeated charge
use favors non-ethereal, because ethereal equipment cannot be repaired/recharged.
Evidence: native runes Heart of the Oak charged properties, cubemain/139 `weap,noe`,
and D2MOO ITEMS_IsRepairable excluding ethereal before checking charged skills.

Red/green regression covers ethereal true/false/unknown, incompatible sword, and
high-ilvl superior versus normal Flail socket preparation. The former cannot reach
four sockets; the latter retains the cube's 1/6 chance. 25 focused tests and Ruff
pass. Full suite evidence: tmp/hoto-base-full-tests.log. Replay evidence:
tmp/hoto-base-published.json. Python-only change; restart Alt+D. No price/tier or
build-count evidence was added. All-family completion remains pending.

## Progression armor/shield/helm bases — 2026-09-25

Added four reviewed player-family configurations with eleven explicit assignments:
Stealth (Quilted, Leather, Hard Leather, Studded Leather), Smoke (Mage Plate,
Studded Leather), Rhyme (Bone Shield, Targe, Preserved Head), Lore (Cap, Diadem).
Each links the cached utility `<base>/sockets_by_runeword/<word>` recommendation;
native legality and existing socket preparation remain independent. Membership
validation rejects overlaps and orphan exceptions. All assigned recommendations
are tested against the prepared catalog. This does not add build votes or prices.

Rhyme preserves Paladin inherent-resistance and Necromancer staffmod checks. Lore
Diadem explicitly requires level 64 (native armor levelreq), avoiding an early-use
claim. Wearer requirements remain unverified; non-ethereal is preferred for player
repairability. No superior-defense premium or perfect-base claim is inferred.

Red/green behavior tests cover all eleven assignments, ethereal durability,
quality exclusion, unknown setup, and superior versus normal Mage Plate two-socket
preparation. Native Studded Leather supports two sockets (do not confuse its cap
with Mage Plate). 37 base/preparation tests passed, followed by 13 progression tests
including membership validation. Ruff passes. Replay and audit evidence:
tmp/progression-bases-{published,matrix}.json. The audit hashes the new module.
Python-only change; restart Alt+D. Remaining reviewed families, stat annotations,
named tiers and exact-market coverage are still incomplete.

## Specialist staffmod bases — 2026-09-25

Scheduled tail batch: added Leaf Short Staff, Memory Battle Staff and White Bone
Wand to the shared caster templates using existing explicit utility recommendation
locators. Native recipe legality remains separate. Each requires review of the
intended skill/staffmod setup and wearer requirements, without inventing skill
minima, physical-damage premiums or perfect-base claims. Leaf/Memory state the
two-handed weapon/shield tradeoff; White retains one-handed use and Necromancer
skill qualification. No market or build-count evidence was added.

Red/green tests verify ready items, quality exclusion and normalized low-quality
bases. All three can reach their target socket count after normalization; native
Battle Staff caps are 4/4/4, so do not assume a three-socket low-ilvl cap. Regenerated
staffmods and other properties are explicitly not inherited. The maintenance source
manifest now hashes mechanics/low_quality.py as a base-use dependency.
39 base/template/preparation tests and Ruff pass. Replay/audit evidence:
tmp/staffmod-bases-{published,matrix}.json. Python-only change; restart Alt+D.
Full objective remains incomplete: known family/configuration, annotations, named
tiers and exact-price gaps still require review. Resume demand-led batches after
this specialist batch; no live collection is required by these changes.

## Treachery Mage Plate: separate wearers — 2026-09-25

Added Mage Plate Treachery base assessment with independent player and mercenary
uses. Evidence is the explicit Character / Mercenary recommendation strings in
appraisal-utility.json Mage Plate/sockets_by_runeword/Treachery, not aggregate
per-base build lists. Player repairs favor non-ethereal; mercenary use prefers
ethereal. Missing ethereal status stays unknown. Both uses require actual defense
and wearer requirements to be checked; superior defense alone cannot establish
perfect suitability or a trade premium. Native Treachery gethit-skill Fade confirms
activation-dependent survival, kept in the tradeoff instead of assuming active Fade.

Red/green role tests cover all ethereal states and filled-socket clearing. Forty
base/template/preparation tests and Ruff pass. Evidence:
tmp/treachery-base-{published,matrix}.json. Python-only change; restart Alt+D.
No prices, tiers or build counts were added. Broad family/annotation/named-tier/
market coverage remains incomplete; next batch should return to reviewed affixed
item configurations, not infer completion from base-route growth.

## Amazon glove stat priorities — 2026-09-25

Reviewed the exact cached glove slots for Lightning Fury Standard/Magic Find/Ubers
and Lightning Strike Standard/boss swap. Added five stat-priority configurations
against unchanged source hashes and full role fingerprints. Required Javelin skills
and IAS are desirable only after the whole combination passes; the source-listed
secondary attributes/resists/MF/mana steal are supporting at positive observed rolls.
Planner maxima remain targets, not required minima or perfect-roll annotations.
The general breakpoint/loadout reminder is advisory only for present item markers;
overall build fit remains conditional. The boss-swap Arachnid Mesh dependency stays
mandatory and cannot be waived by the advisory-condition review.

Red/green tests cover rare 2/20, magic 3/20, incomplete/missing pair, wrong quality,
ethereal state and unmet boss companion. Eleven targeted stat/bundle tests pass;
Ruff passes. Prepared stat configurations increase from 16 to 21 without adding
role profiles (297 unchanged), named tiers or prices. Sources: wp-a-variants/
lightning-fury-amazon-guide.json /variants/{1,2,3}/player/Gloves and
lightning-strike-amazon.json /variants/1/player/Gloves. Full release evidence:
tmp/glove-stats-full-tests.log, tmp/glove-stats-{staged,published}.json.

## Crafted-glove stat combinations — 2026-09-25

Added three explicit stat reviews for Double Throw Standard Hit Power gloves,
Smite High Investment Blood gloves and Dragon Talon Budget Blood gloves. Exact
cached source slots and existing role fingerprints are retained. IAS/Knockback,
IAS/Crushing Blow, and Martial Arts/IAS/Crushing Blow/life-steal combinations stay
independent: missing or unknown mandatory stats block that configuration's markers.
The source-listed optional attributes, life and resistances are supporting at
positive observed rolls, not universal required maxima. Smite planner life/mana
steal is intentionally left unannotated; its utility to that role is not established
by this review. General loadout reminders are advisory only for item-stat markers;
no full-fit, crafting-recipe identity, or numerical price is inferred.

Red/green tests cover all three combinations, absent/unknown members, wrong quality
and ethereal exclusion. 263 role/stat/bundle/presentation tests pass; Ruff passes.
Prepared stat configurations: 24 (was 21); role profiles remain 297. Sources:
wp-a-variants/double-throw-barbarian-guide.json /variants/1/player/Gloves,
smite-paladin.json /variants/2/player/Gloves, dragon-talon-assassin.json
/variants/0/player/Gloves. Evidence tmp/crafted-gloves-{staged,published,publication}.json.
This is an offline reviewed-data change; existing current published workers adopt
it at request boundaries. Remaining all-family, named-tier and market requirements
are not complete.

## Circlet stat-use configurations — 2026-09-25

Added six source-reviewed stat configurations: Poison Nova Standard, FoH Tri-Brid,
Abyss Standard, Berserk Max Mobility rare circlets; Enchant Standard and Max Enchant
magic circlets. Exact cached Helmet slots and complete existing-role fingerprints
are preserved. Matching class skills/FCR form mandatory rare combinations; Enchant
requires its Fire skill tree. Source-reviewed life/dexterity/movement preferences
are supporting at positive observed rolls, not required maxima. Max Enchant does
not inherit Standard's movement-speed annotation. Socket/filler checks remain
conditions on overall fit, advisory only for these present item-stat markers.
Known non-ethereal status additionally gates player-helmet annotations. No socket
completion, ethereal exception, perfect-roll or price claim follows from markers.

Red/green tests cover all six role/quality/skill combinations, missing/unknown
mandatory skills, lower FCR, wrong quality and ethereal true/unknown. Fifteen focused
stat/bundle tests pass; Ruff passes. Prepared configurations: 30, roles: 297.
Sources are unchanged wp-a-variants Helmet locators in the six profiles; no raw
research repeated and no market collection. Evidence tmp/circlet-stats-*.json.
Remaining all-family configuration, named-tier and exact-market gaps stay pending.

## Rare boot stat configurations — 2026-09-25

Added ten exact-source boot stat reviews: Blizzard Standard, Lightning Sentry
Standard, Fire Warlock Standard/MF, Lightning Fury Ubers, Lightning Strike Ubers,
Fissure Ubers, Lightning Sorceress Ubers, Gold Find Budget and Nova Starter.
Required combinations remain distinct: movement plus fire/lightning/cold resistance,
movement/fire resistance/gold find, or Nova's movement/fire resistance pair. Positive
source-listed secondary recovery, dexterity, MF or poison-length reduction is
supporting; no universal tri-resist rule, minimum maximum-roll target or price is
introduced. Known non-ethereal status and entire role predicate remain mandatory.
Full-loadout comparison is advisory only for item-stat markers, not overall fit.
All source Boots locators were inspected; existing role fingerprints/hashes retained.

Red/green tests cover every configuration, zero and unknown mandatory modifiers,
quality/ethereal exclusions and independent roll-quality state. 260 affected
role/stat/bundle/presentation tests pass; Ruff passes. Prepared stat configurations
increase from 30 to 40, role profiles remain 297. Evidence tmp/boot-stats-*.json.
This is an offline prepared-data update. Overall family, named-tier, leveling and
exact-market completion remains pending under GUIDE_FIRST.

## Specialist IAS/resistance jewel stat reviews — 2026-09-25

Scheduled specialist batch: seven source-specific jewel configurations added for
Andariel's Visage mercenary fire-resistance setups (Lightning Standard/MF, Blizzard
Standard/Set, Hammer Standard/Ubers) and Guillaume's Face player lightning-resistance
setup (Hammer Ubers). Exact cached helmet payload locators were inspected. Both
modifiers are desirable only after the whole magic-jewel predicate and typed wearer/
recipient dependency pass. Fixed 15 IAS remains exact, not >=15 without an upper
bound. Resistance maximum stays a preference; no perfect-roll or price inference.

Socket availability and full breakpoint/resistance checks remain overall role
conditions, advisory only for recognizing useful jewel stats. Thus highlights do
not say ready-to-socket. Unknown/wrong recipient or wrong wearer prevents markers.
Tests also cover incomplete modifier capture, impossible 16 IAS and wrong quality.
Ten focused stat/bundle tests and Ruff pass. Prepared configurations: 47 (was 40),
297 role profiles unchanged. Full regression/replay/publication evidence:
tmp/jewel-stats-{full-tests.log,staged.json,published.json,publication.json}.
This is an offline prepared-data update; no live research or new prices. The full
GUIDE_FIRST denominator, named tiers and remaining configurations are incomplete.

## Sorceress amulet stat reviews — 2026-09-25

Added seven configurations for Enchant Budget/Max Enchant magic amulets and Nova
Standard/MF/Hydra plus Enchant Standard/MF crafted amulets. Exact cached Amulet slots
were inspected; existing source hashes and full-role fingerprints are preserved.
Matching Fire-tree versus Sorceress-class skills and variant-specific 10/15 FCR
remain mandatory combinations. Source-specific life/mana/regeneration/MF/strength
preferences are supporting at positive observed rolls. The Enchant all-resistance
preference stays grouped: one resistance does not satisfy it. Planner maxima are
targets, not generic required minima. Prebuff and loadout reminders are advisory
only for present item markers; overall fit remains conditional. No price, recipe
identity or roll-quality inference added.

Red/green tests cover all seven thresholds/qualities/skill identities, missing or
unknown skills, insufficient FCR and partial/full all-resistance groups. Sixteen
focused stat/bundle tests and Ruff pass. Prepared configurations: 54, roles: 297.
The pinned-bundle test now sees five magic amulet configurations, preserving
publication isolation and legacy behavior. Evidence tmp/amulet-stats-*.json.
All-item/price/named-tier and remaining reviewed-stat coverage remains incomplete.

## Class-specific magic amulet stats — 2026-09-25

Added six exact-source configurations: Lightning Sentry and Wake of Fire Cunning
Whale/Apprentice amulets; Poison Nova Starter/Budget Venomous amulets. Cached guide
slot identities inspected; existing native-affix predicates and full role/source
fingerprints preserved. Typed player class, skill tree, quality and suffix remain
mandatory; no cross-class or rare-item inheritance. Whale's 81-life lower bound
stays distinct from its 100-life preference. All highlighted stats participate in
the required combination; overall loadout fit remains conditional.

Red/green tests cover all six, wrong/unknown class, insufficient/missing/unknown
modifiers, rarity and ethereal exclusion. Five focused config/bundle tests and
Ruff pass. Prepared configurations: 60; role profiles unchanged at 297. Compiler
and pinned-bundle coverage assertions updated to 16 total amulet configurations
and 11 magic amulet candidates; behavioral and isolation assertions retained.
Evidence tmp/class-amulet-stats-*.json. No price or named-tier change. Teleport
charge amulets remain pending a separate charge-parameter annotation design.

## Specialist dynamic charge-stat targets — 2026-09-25

Added charge:<skill-id> annotation targets, resolved to actual native 204:<parameter>
rows by the existing charged-skill validator. Valid positive-charge rows for the
requested skill are selected across spell levels; exhausted, conflicting, malformed
or unrelated skill rows are never marked even if another row establishes availability.
Ordinary scalar target behavior and prior prepared schemas remain compatible.
Targets serialize through the existing validated configuration bundle. Shared
terminal/OSD stat formatting already accepts the resolved native keys.

Added two reviewed Teleport amulet configurations (Berserk and Poison Nova), using
exact cached gear-note alternatives. Typed class and available-charge dependencies
remain mandatory. Equipment/progression alternatives remain conditions on overall
fit, advisory only for recognizing an available Teleport property; this does not
recommend replacing Enigma. No numerical price or perfect-charge-roll inference.
Prepared configurations: 62; existing role profiles unchanged. Red/green tests cover
mixed charge levels, exhausted/duplicate/wrong-skill rows, malformed selectors,
bundle roundtrip, class/quality scope and shared rendered markers. Eighteen focused
stat/bundle/compiler tests and Ruff pass. Full evidence tmp/charge-stats-*.json/log.
Python change requires Alt+D restart. Full all-item/named-tier/market coverage remains
incomplete; this is the scheduled specialist batch after the two amulet batches.

## RCA: life bonuses incorrectly keyed as current HP — 2026-09-25

Belt-stat review found ten existing roles using native 6:0 (hitpoints) for item
+Life; native itemstatcost/decoder identifies 7:0 (maxhp) as the Life bonus. Six
belt roles (FoH/Holy Bolt/Fury/Poison starters, Summoner/Smite crafted starters) and
four small-charm roles (Lightning Ubers, Blizzard Standard life/all-res and life/cold,
Hammer Ubers) were affected. Exact source locators all describe +Life, not current HP.
Must predicates, preference predicates and important_stats now consistently use7:0.
Source values/thresholds, quality scopes and dependencies are unchanged.

Root cause: handwritten role JSON used the wrong adjacent native stat; handcrafted
role tests repeated it instead of crossing the decoder/normalizer boundary. Updated
those fixtures and added actual decode_stats→normalize→role regressions (fixed-point
life raw values). Nine cases failed before the fix; the initial24 affected tests
passed after it. Added coverage for all four small-charm roles and a negative check
that current HP cannot satisfy the item-life predicate. Full evidence:
tmp/life-stat-{red.log,full-tests.log,staged.json,published.json,publication.json}.
The intended belt annotation expansion is deferred until this correctness fix is
validated/published. No new prices or stat-review count claimed; configurations62,
roles297. This fixes matching prerequisites, not missing source or market coverage.

## Magic/rare belt stat annotations — 2026-09-25

Added eight reviewed configurations: Hammer/Blizzard/Wake Starter recovery+fire
resistance belts; FoH/Holy Bolt Starter life+cold resistance; Fury/Poison Starter
life+fire resistance; Gold Find Budget recovery+cold/lightning resistance+gold.
Exact source Belt slots inspected. Whole quality-specific combinations remain
mandatory; player-equipment annotations additionally require known non-ethereal
state. Corrected Life7:0 is used, never currentHP6:0. Source roll targets remain
preferences and no lower observed roll is falsely marked perfect.

Potion capacity, equipment, remaining survival/breakpoint and mercenary-kill setup
checks remain conditions on overall fit, advisory only for item-stat recognition.
No price or full-loadout claim follows from markers. Red/green tests cover all eight
combinations, missing/unknown modifiers, crafted exclusion, ethereal true/unknown,
and current-HP negative cases. Seventeen focused tests and Ruff pass. Prepared
configurations:70; roles297 unchanged. Evidence tmp/belt-stats-*.json. Crafted belt
annotations remain separate work; preserve the Smite Life Tap qualification.

## Verified current coverage

| Requirement | Current evidence | Remaining work |
|---|---|---|
| Build-aware routing | Eight family branches in `registry.py`; 297 reviewed profiles compiled from per-build rules | Remaining source-specific roles, variants and dependencies |
| Every source occurrence retained | Fresh occurrence audit: 62,891 occurrences, 34 builds, 591 build/variant pairs; 49,780 discovery-only, 3,929 identity-review and 9,182 rule-review records | Resolve required identities and semantic rule dispositions; direct source links are not proof of complete rules |
| Source-to-rule traceability | 857 occurrences have related rules; 273 have direct source rules | Review duplicates, alternatives, planner context and source-specific predicates |
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

### Belt publication verification — 2026-09-25

Revalidated the selected generation against `tmp/belt-stats-publication.json`:
`ce01ee72694fac2d681150aa1a097cdbb996d04bc91a76fcce38fc4d9b76ef33`.
All 18 saved staged and published reports and price results match the preceding
Life-stat generation. Re-ran the belt stat-priority and stat-bundle tests: 10 passed.
Copied the completed base matrix and regenerated the unified coverage matrix after
source-fingerprint validation (`tmp/belt-stats-coverage.json`). The use/quality
stat-desirability dimension now has 79 reviewed and 289 pending rows; 70 reviewed
configurations do not establish full report, market or family coverage.

Next: review crafted caster belt combinations using exact cached slot evidence;
keep Smite Life Tap dependencies explicit. Follow GUIDE_FIRST's specialist/leveling
tail scheduling and preserve separate coverage dimensions. No new market collection
or runtime code change was needed for this verification.

## Crafted caster belt stat annotations — 2026-09-25

Reviewed exact cached belt slots for Abyss, Echoing, Fire Warlock, Fissure,
Lightning Sorceress, Nova and Summoner starter configurations. Added seven
reviewed stat configurations, bringing the prepared total to 77 (297 roles).
Whole modifier combinations remain mandatory. Echoing/Fire resistance alternatives
are evaluated within their own configurations, without requiring every resistance.
Five explicit loadout FCR dependencies remain mandatory; missing/below-threshold
context cannot activate annotations. Known non-ethereal crafted equipment is
required. Source roll targets remain preferences, not perfect-roll claims.

Red: seven missing-configuration failures. Green: 268 affected role/stat/compiler/
presentation tests passed. Tests cover required-stat near misses, incomplete
captures, quality/ethereal exclusions, alternative resistance branches, FCR boundary
and unknown context, and Life7 versus currentHP6. Ruff and diff checks pass.
All 18 staged/published saved reports and price results are unchanged. No saved
crafted-belt capture exists; targeted fact-level tests cover the new configurations.

Published generation `5550361cf1bf7c54f6135c9e09ca7a8ca257ef17e8b85bd1fbccd277771b1ed6`. Refreshed guide inventory, base matrix and
unified coverage; stat desirability now records 86 reviewed and
282 pending use/quality rows. Evidence: `tmp/crafted-belt-stats-*`.
This is data-only; no additional worker restart is required.

Next is the GUIDE_FIRST specialist/leveling tail after the two belt batches:
review Smite Blood-belt sustain semantics (Life Leech is not Life Tap), preserving
its Ubers dependencies before enabling markers. Then resume unresolved family and
named-tier queues. Full coverage and all-item pricing remain incomplete; annotations
do not supply missing market evidence.

## Specialist tail: Smite Blood-belt review — 2026-09-25

Reviewed the cached Smite Starter purpose, Belt slot and variant quotes. Removed
Life Leech from important stats and better-roll preferences: the guide requires
Life Tap for sustain separately. Kept the complete cited crafted combination as
the candidate predicate; present leech is not promoted to a desirable modifier.
Added annotations for Open Wounds, recovery and Life, requiring known non-ethereal
crafted equipment. Overall role remains partial with Life Tap, CBF, Crushing Blow,
resistance, equipment and potion-capacity qualifications intact. Reviewing these
conditions as advisory for item-stat recognition does not satisfy the loadout.

Red regression reproduced the incorrect leech priority. Green: 262 affected tests;
Ruff and diff checks pass. Negative cases include missing/unknown required modifiers,
quality, ethereal, identification and currentHP6 versus Life7. Changing leech1→3
does not add a marker. All18 staged/published saved reports and price results remain
unchanged; the Smite belt itself is covered by domain tests, not a saved capture.
78 reviewed stat configurations;297 roles. Published `06fda35c6b7346894a0d4b842f949d551b00f357484b95ebc139c6e0cecf5a5d`.
Guide/base/unified maintenance refreshed: stat desirability 87 reviewed,
281 pending use/quality rows. Evidence `tmp/smite-belt-stats-*`.

This completes the scheduled specialist tail following the magic/rare and crafted
caster belt batches. Next demand-led batch: inspect the ten pending grand-charm
(`lcha`) configurations (life skillers, FHR skiller and starter skillers), preserving
exact class/tree identity and whole combinations. The25 small-charm configurations
are a subsequent family; do not pool incompatible survival/MF branches. Remaining
named tiers, source gaps and market evidence still prevent all-item completion.
Data-only publication; no new Python-worker restart required.

## Grand-charm stat configurations — 2026-09-25

Reviewed all ten existing Grand Charm role source slots: six Life skillers
(Blizzard/Fury/Hammer/Nova/Poison/Lightning), two FHR skillers (Hammer/Lightning),
and plain starter skillers (Poison/Lightning). Added exact skill-tree and suffix
annotations through the existing shared evaluator; source45-Life preferences are
not minimum requirements or perfect-roll claims. Plain starter roles do not inherit
Life/FHR priorities. Inventory allocation remains conditional on the full charm
setup, advisory only for recognizing this item's modifiers. Magic quality,
identification and known non-ethereal constraints remain active.

Red:10 missing-configuration failures. Green:271 affected tests; Ruff/diff checks
pass. Tests cover wrong skill tree, Life/FHR substitution, FHR11 versus12, current
HP versus Life, absent/unknown required modifiers and quality/ethereal/identification
exclusions. All18 staged/published saved reports and prices unchanged; no Grand
Charm saved capture is present, so new behavior is covered by targeted domain tests.
88 configurations,297 roles. Generation `c7ab0f1af827698659c4155dfcb634ea2ac9a827f7ab6cf3e90542b7ecf486f8` is selected. Guide inventory, base
matrix and unified coverage refreshed: 97 reviewed and 271
pending stat-desirability use/quality rows. Evidence `tmp/grand-charm-stats-*`.

Next: the25 small-charm configurations, reviewed in compatible combination groups
(life/resistance, MF/resistance, FHR/resistance and other source-specific branches).
After that second demand-led batch, schedule the GUIDE_FIRST specialist/leveling
tail. Named-tier closure and scoped market evidence remain independent unfinished
requirements. No additional Python-worker restart is needed for this data update.

## Small-charm combination annotations — 2026-09-25

Reviewed the25 existing Small Charm role slots, grouped into seven compatible
combinations: Life/all-resistance, Life/cold, MF/all-resistance, FHR/all-resistance,
lightning/MF, fire/MF and mana/MF. All four resistances are mandatory in all-resistance
configurations. Source counts remain inventory-allocation context; they do not
increase demand votes. Allocation conditions remain on overall fit, advisory only
for stat recognition. Known non-ethereal magic quality/identification is required.
Source maximum-roll targets are not annotation minima or perfect-roll claims.

Red: seven missing-configuration cases. Green:268 affected tests; Ruff/diff checks
pass. Tests cover every generated member, incomplete combinations, partial all-res,
wrong charm size/quality, ethereal/identification, Life versus currentHP, Mana versus
current mana and MF versus Gold Find. No pooled resistance or cross-family credit.
All18 staged/published saved reports and prices unchanged; these new Small Charm
combinations have domain tests, not saved capture fixtures. Prepared configurations
113; roles297. Generation `90cb517e7e4b4a258ebbe2b977a3029af6e1f71b07de5ac6eaaaba164b571c42` is selected.
Guide inventory/base/unified coverage refreshed: 122 reviewed and
246 pending stat-desirability use/quality rows. Evidence:
`tmp/small-charm-stats-*`. No new Python-worker restart required.

Next scheduled specialist tail: Life Tap charge wands, using existing dynamic
charge targets and exact skill/remaining-charge rules. Pending role IDs:
`smite-paladin-starter-charges-82`, `dragon-talon-assassin-budget-charges-82`,
`dream-paladin-ubers-charges-82`. Check exact source slot, recharge/ethereal caveats
and context before activating markers; a charged wand does not prove ongoing
sustain or complete Ubers fit. Full named-tier and market closure remain pending.

## Specialist tail: Life Tap charged wands — 2026-09-25

Reviewed exact Smite Starter, Dragon Talon Budget and Dream Ubers wand slots.
Added three dynamic charge:82 configurations using the existing resolver, preserving
magic/rare quality, player class and available-charge gates. Dream requires known
absence of both Last Wish and Dracul's Grasp; unknown companion context cannot
activate its marker. Corrected recharge wording to distinguish non-ethereal copies.
Ethereal copies retain usable remaining charges, with a finite-charge/no-repair
qualification. Charge presence does not prove the curse is applied or full Ubers
sustain. Equipment and remaining loadout conditions remain on overall partial fit,
advisory only for identifying the charge stat.

Red:3 missing-configuration failures. Green:271 affected tests; Ruff/diff checks
pass. Tests cover all three roles, magic/rare quality, empty/wrong-skill/malformed/
conflicting charges, wrong/unknown class, Dream companion presence/unknown state,
identification, wrong item type and terminal stat marker. All18 staged/published
saved reports and prices unchanged; new wand scenarios use domain/presentation
tests rather than saved captures.116 configurations,297 roles.
Generation `c8ad53accf57ab47e915b83840a9cec8ac1a12c6378c2235b7bdbadc016584bd` selected; guide/base/unified maintenance refreshed.
Stat-desirability use/quality rows: 128 reviewed,240 pending.
Evidence `tmp/life-tap-stats-*`; no Python-worker restart needed for this data update.

Next demand-led batches: review17 Teleport travel-staff configurations, then the
remaining9 Lower Resist wand configurations using exact source/loadout requirements.
Reuse charge targets; do not infer immunity breaks, applied curses or permanent
sustain from charges. Follow with another specialist/leveling tail. Named tiers,
full guide review and exact scoped market evidence remain incomplete.

## Teleport travel-staff annotations — 2026-09-25

Reviewed17 exact staff source slots across seven classes. Added dynamic charge:54
annotations with class, quality, identification and valid remaining-charge gates.
Converted explicit Berserk and Poison pre-Enigma/Bramble conditions into typed
absence-of-equipped-Enigma dependencies, alongside the existing Smite gate. Unknown
loadout cannot establish these alternatives; Bramble remains compatible. Other farm,
swap/inventory and equipment conditions remain on partial role fit, advisory only
for recognizing usable charges. Incidental planner resistances/charge counts were
not promoted to requirements. Recharge wording now distinguishes non-ethereal copies;
ethereal copies retain finite remaining travel utility, not rechargeability.

Red:17 missing-configuration failures. Green:285 affected tests; Ruff/diff checks
pass. Tests cover each role, magic/rare, unknown/wrong class, empty/malformed/wrong
skill/conflicting charges, ethereal finite use, wrong type, identification and
known/unknown Enigma alternatives. All18 staged/published reports and prices remain
unchanged; staff scenarios have domain tests, not saved capture fixtures.
133 stat configurations;297 roles. Generation `12f8623c8f58e59c61f61808d492af5951d5d3d9c69d80c139befcd4df70e2ef` selected.
Guide inventory/base/unified maintenance refreshed: 162 reviewed,
206 pending stat-desirability use/quality rows. Evidence:
`tmp/travel-staff-stats-*`. Data-only update; no new Python-worker restart required.

Next demand-led batch: the remaining9 Lower Resist wand configurations, retaining
class and exact gear/curse dependencies and not inferring immunity breaks from
charges. Then schedule a specialist/leveling tail. Full guide review, named tiers,
base desirability and exact market coverage remain independent unfinished gates.

## Lower Resist wand annotations — 2026-09-25

Reviewed nine exact cached wand slots. Added dynamic charge:91 configurations,
preserving class, valid remaining charges and the opposite Infinity dependencies:
Blizzard Starter requires known absence; Lightning Ubers requires known presence.
Unknown mercenary gear cannot establish either. Lightning Strike Ubers keeps its
manual-curse alternative even with Plague. Inventory/swap placement, equipment,
target effect and Uber Mephisto qualifications remain on partial role fit, advisory
only for recognizing usable charges. Recharge wording distinguishes non-ethereal
copies; ethereal charges provide finite utility. No immunity-break or applied-curse
claim follows from a marker.

Red:9 missing-configuration failures. Green:277 affected tests; Ruff/diff checks
pass. Tests cover all nine roles, magic/rare, charge state/skill/conflicts, class,
identification, ethereal finite utility and known/unknown/opposite Infinity gear.
All18 staged/published saved reports and price results unchanged; new wand scenarios
use domain tests, not saved captures.142 configurations;297 roles.
Generation `ddb0b28399f7535fe79f7276d22662bff2d266985e1ab094f203cd211e1aaf4a` selected. Guide inventory/base/unified audits refreshed:
180 reviewed,188 pending stat-desirability use/quality rows.
Evidence `tmp/lower-resist-stats-*`; no new Python-worker restart required.

Next scheduled specialist tail after the two charged-utility batches: review
`enchant-prebuff-orb-candidate`, preserving native staffmod versus affix skills and
prebuff-specific requirements. Then resume unreviewed circlet/claw/pelt/base-use
configurations. Full named tiers, guide review and exact scoped prices remain
independent unfinished requirements; configuration coverage is not market coverage.

## Specialist tail: Enchant prebuff orb — 2026-09-25

Reviewed the exact Max Enchant Weapon slot. Added one configuration requiring the
Fire skill-tree affix and native Enchant/Fire Mastery staffmods together. Class-wide
skills, another tree and oskill identities cannot substitute. Planner+3 maxima
remain preferences; lower positive values can establish the skill candidate.
FCR is not silently highlighted as necessary to prebuff. Socket/facet and equipment
checks remain on partial full-use fit, advisory only for skill recognition.
Ethereal state does not remove the captured prebuff skills or establish melee utility.

Red: missing configuration reproduced. Green:262 affected tests; Ruff/diff checks
pass (one test-comprehension lint fix). Tests cover each missing/unknown member,
wrong skill identities, conflicting native rows, magic-only applicability, item type,
identification, lower/max rolls and ethereal states. All18 staged/published saved
reports and prices unchanged. The saved orb captures remain regression controls;
this specific Enchant combination is tested at the domain boundary.
143 configurations;297 roles. Generation `e3d514ad573555bc7a508e731b733550d9a7c177ddc7875d8487b6f6db2d740d` selected.
Guide inventory/base/unified refreshed: 181 reviewed,187 pending
stat-desirability use/quality rows. Evidence `tmp/enchant-orb-stats-*`.
No new Python-worker restart required for this data-only change.

Next: source-specific trap-claw and Druid pelt skill combinations, preserving
quality, base, skill identity, socket and setup conditions. After two demand-led
batches return to specialist/leveling review. Named tiers, source completeness,
base desirability and exact scoped prices remain independent unfinished gates.

## Trap-claw skill annotations — 2026-09-25

Reviewed Wake of Fire and Lightning Sentry Standard Weapon slots. Added two
configurations requiring Traps plus the matching native trap staffmod. IAS, Weapon
Block and the source-specific Fire Blast/Death Sentry are supporting only after the
core pair matches. Verified native skill IDs against bundled metadata. Missing
supporting stats do not invalidate the core candidate. Planner+3/40IAS remain
targets, not annotation minima. Socket/payload, base-speed and remaining equipment
are still full-setup checks; no breakpoint, best-base or price claim follows.

Red:2 missing-configuration failures. Green:263 affected tests; Ruff/diff checks
pass. Tests cover exact tree/staffmod identities, cross-trap substitution, oskill/
class-skill substitution, missing/unknown core members, independent supporting
stats, quality/type/identification and conflicting capture rows. All18 staged and
published reports/prices unchanged, including existing claw captures. New complete
trap-pair combinations are covered by domain tests rather than saved captures.
145 configurations;297 roles. Generation `d4e81cc25b5715780ee865b352a0a4b4b4fca47618b3b123f74059c1f77676e1` selected.
Guide/base/unified maintenance refreshed: 183 reviewed,185
pending stat-desirability use/quality rows. Evidence `tmp/trap-claw-stats-*`.
No new Python-worker restart required for the data-only update.

Next demand-led batch: `fissure-standard-pelt` and `fissure-magic-find-pelt`; review
source-specific rare skill combinations and socket requirements. Then schedule a
specialist/leveling tail. Named tiers, complete source review, base desirability
and exact scoped market evidence remain independent unfinished gates.

## Fissure magic-pelt annotations — 2026-09-25

Reviewed exact Standard and Magic Find Helmet choices. Added two configurations
requiring Druid class, non-ethereal magic quality, +3 Elemental/+3 Fissure and the
existing verified two-socket Defender's Fire + Fire Rainbow Facet setup. Socket
dependencies were not waived for stat annotations: wrong elements, names-only,
parent-total substitution and missing Defender's Fire do not activate markers.
Standard Hurricane/Grizzly are supporting positive bonuses only; MF does not
inherit them. Equipment/preparation conditions remain on partial overall fit.
Earlier handoff wording describing these as rare was incorrect: both are magic.

Red:2 missing-configuration failures. Green:263 affected tests; Ruff/diff checks
pass. Tests cover core thresholds, absent/unknown skills, socket evidence, class,
quality, ethereal/identification and variant-specific supporting bonuses. All18
staged/published saved reports and prices unchanged. These pelt combinations use
domain fixtures, not captured live items.147 configurations;297 roles.
Generation `b88dcecefd3715b200bb45b17126c4af872f2043a17b30943ec1cc8df95ccdd1` selected. Guide/base/unified maintenance refreshed:
185 reviewed,183 pending stat-desirability use/quality rows.
Evidence `tmp/pelt-stats-*`; no new Python-worker restart required.

Next specialist/leveling tail: Double Throw starter magic Cruel throwing weapons
and crafted alternatives, preserving the documented attack/damage combination,
main-hand/off-hand contexts and ethereal/replenishment considerations. Do not infer
generic rare throwing-weapon prices. Remaining named tiers, guide completeness,
base desirability and exact scoped prices are separate unfinished requirements.

## Specialist tail: Double Throw starter weapons — 2026-09-25

Reviewed four exact main/off-hand source entries. Crafted Balanced Axe annotations
require the complete Barbarian skills/IAS/ED endpoints/leech/Life combination.
Cruel elite alternatives retain201..300ED on both endpoints and enumerated base
membership, with IAS supporting only. Source quality, Barbarian class, non-ethereal
state and no-cold-damage predicate remain mandatory; incomplete captures cannot
prove absence of cold. Full-gear corpse preservation, actual throwing damage,
breakpoints, equipment and quantity sustain remain conditions on partial overall
fit, advisory only for recognizing the captured modifiers. No generic rare-weapon
price or ethereal replenishment inference.

Red:4 missing-configuration failures. Green:265 affected tests; Ruff/diff checks
pass. Tests cover both hands, quality/base/class/ethereal, missing/unknown stats,
cold damage, ED boundaries, optional IAS and currentHP versus Life. All18 staged/
published reports and prices unchanged. New throwing combinations use domain tests,
not saved captures.151 configurations;297 roles.
Generation `ff92fdae976c94b32116a2b0a49d5fb31212bc69a147a5d39fe37adc46fa77a4` selected. Guide/base/unified maintenance refreshed:
189 reviewed,179 pending stat-desirability use/quality rows.
Evidence `tmp/throwing-stats-*`; no new Python-worker restart required.

Next: audit combined-stat presentation, particularly a single ED line representing
native17/18. Domain annotations alone do not prove a multi-key rendered line shows
a marker; current single-key rendering needs a conservative shared-configuration
rule and report regression before claiming this dimension complete. Then resume
remaining circlet and rare throwing-weapon configurations. Named tiers, full source
coverage, base desirability and exact scoped prices remain unfinished.

## Combined-stat report markers — 2026-09-25

Fixed the shared stat formatter dropping every multi-native-stat marker. Combined
lines now require a common (configuration ID, desirability) contribution across all
represented native keys. Missing/unreviewed components, disjoint configuration
votes or mixed meanings within the only shared role leave the line unmarked.
Aggregate desirable votes cannot pool unrelated roles; a shared supporting role
can produce a supporting marker. Desirability prefix and roll-quality text colors
remain independent. Unresolved lines retain their original presentation.

Red regression reproduced the missing ED marker. Five focused tests now pass,
including an actual Cruel configuration through the production ED combiner and
shared terminal/OSD report. All18 published saved reports and prices unchanged.
Full suite: 2,890 passed, 3 skipped in 140.51s. Ruff, format and diff checks pass.
No KB evidence or prices
changed; the selected data generation stays the throwing-stats publication.
Evidence `tmp/combined-markers-*`. Python formatter change requires restarting
the Alt+D worker to take effect.

Next: resume unreviewed circlet and rare throwing-weapon configurations, preserving
socket/payload and build conditions. Multi-key rendering support does not close
per-family report coverage or named-tier/market/source-review gaps.

## Magus circlet skill/FCR annotations — 2026-09-25

Reviewed four exact source entries: Double Throw/Berserk Berserker's Magus and
Wake/Lightning Sentry Cunning Magus. Added stat configurations preserving class,
non-ethereal state and complete2Barbarian/20FCR or3Traps/20FCR combinations.
Existing magic/rare Barbarian equivalence is retained; Cunning remains magic-only.
Socket payloads, equipment and full-loadout breakpoints remain conditions on partial
fit, advisory only for skill/FCR recognition. No completed-helmet or price claim.

Red:4 missing-configuration failures. Green:267 affected tests; Ruff/diff checks
pass. Tests cover each role, quality, thresholds, missing/unknown modifiers, class,
ethereal, identification and class-skill substitution for Traps. All18 staged and
published saved reports/prices unchanged; new combinations use domain fixtures.
155 configurations;297 roles. Generation `60ddf06bb2afb2b1b90a830a8c6aa0e3a6411c551e25f22daeb8753e5442526b` selected.
Guide/base/unified refreshed: 195 reviewed,173 pending
stat-desirability use/quality rows. Evidence `tmp/magus-stats-*`.
Data-only change; no further worker restart beyond the preceding formatter update.

Next demand-led batch: six empty-socket Diadem/Tiara suffix configurations, preserving
exact base, three empty sockets, class and FRW/Dex/MF thresholds. Then schedule a
specialist/leveling tail. Named tiers, complete source review, base desirability
and scoped exact-price evidence remain independent unfinished gates.

## Empty-socket circlet suffix annotations — 2026-09-25

Reviewed six Artisan/Jeweler source entries: Double Throw Speed/Nirvana/Luck
Diadems, Strafe Speed/Nirvana Diadems and Berserk Luck Tiara. Added suffix markers
only after exact base/class/magic non-ethereal quality/three-empty-socket predicates
pass. FRW30, Dex21 and MF26 lower thresholds retained. Filled/partial/unknown sockets
or fewer than three do not qualify. Empty sockets do not grant proposed jewels'
IAS or damage; socket investment and full-setup checks remain on partial fit.

Red:6 missing-configuration failures. Green:269 affected tests; Ruff/diff checks
pass. Tests cover all six roles, threshold near misses, unknown stats, socket count/
contents, Diadem versus Tiara, class, quality, ethereal and identification. All18
staged/published saved reports and prices unchanged; new combinations use domain
fixtures.161 configurations;297 roles. Generation `c6ea179117667e74d28069f40029c9f6003d9bb1734fb6d5e0f4c4e11a53fc7f` selected.
Guide/base/unified refreshed: 201 reviewed,167 pending
stat-desirability use/quality rows. Evidence `tmp/socket-circlet-stats-*`.
Data-only update; no further restart beyond the prior combined-stat formatter fix.

Next scheduled starter/specialist tail: `lightning-fury-starter-lancers-javelin`,
reviewing the inherent/affix skill combination and quality/base requirements before
claiming highlights. Then resume remaining rare-throwing and socket-base families.
Full named tiers, source completeness, base desirability and scoped prices remain
independent unfinished gates.

## Starter tail: Lancer javelin annotations — 2026-09-25

Reviewed Lightning Fury Starter Weapon. Added one configuration preserving Amazon
class, magic non-ethereal Matriarchal Javelin and captured4..6Javelin/Spear skills
with exactly40IAS. The observed total combines inherent/affix contributions; it does
not prove a specific prefix roll. Prefer6 without deriving perfect-roll status.
Full52IAS target, equipment and throwing quantity remain conditions on partial
fit, advisory only for recognizing the current skill/speed pair.

Red: missing configuration reproduced. Green:264 affected tests; Ruff/diff checks
pass. Tests cover skills4/5/6 and invalid3/7, exact IAS boundaries, unknown values,
wrong base/quality/class, ethereal/identification and conflicting capture rows.
All18 staged/published saved reports and prices unchanged; this javelin uses a
domain fixture, not a saved capture.162 configurations;297 roles.
Generation `85049fc7d24f8c3c1c673aa02a7148874d4621e6e2ab14dc1e5298d907df79f4` selected. Guide/base/unified refreshed:
202 reviewed,166 pending stat-desirability use/quality rows.
Evidence `tmp/javelin-stats-*`. Data-only update; no further worker restart beyond
the prior combined-stat formatter fix.

Next: rare throwing planner weapon/off-hand configurations, then remaining socket
base families. Preserve complete modifier/quantity-sustain conditions and exact
scope. Named tiers, source completeness, base desirability and matched price
evidence remain independent unfinished requirements.

## Rare throwing planner-target annotations — 2026-09-25

Reviewed decoded cached planner db0106mf items77/76/79, preserving their2023 source
date and high-roll example scope. Added separate main/off-hand configurations for
ethereal rare Ghost Glaive/Winged Axe/Flying Axe with the complete ED/AR/IAS/Combat
skills/replenishment/Amplify combination. Typed replenishment and chance units,
Barbarian class, zero sockets and cold exclusion remain mandatory. These exact
planner targets do not establish minimum viable rolls or market valuations.
Quantity sustain, actual damage/breakpoints and equipment remain on partial fit;
lower rolls retain the explicit separate-assessment qualification.

Red:2 missing-configuration failures. Green:265 affected tests; Ruff/diff checks
pass. Tests cover both roles and all3bases, required-stat near misses/unknowns,
wrong units, cold, incomplete capture, class, quality, ethereal and socket state.
All18 staged/published reports/prices unchanged; new rare throwing scenarios use
domain fixtures.164 configurations;297 roles. Generation `a5ecb0e9e7f2abe8559246a37952ed6b8c9a7f32abdd22a6c854edf2412226e3` selected.
Guide/base/unified refreshed: 204 reviewed,164 pending
stat-desirability use/quality rows. Evidence `tmp/rare-throwing-stats-*`.
Data-only update; no further worker restart beyond the prior formatter change.

Next: remaining socket-base families (JMOD shield configurations, Shroud suffixes,
Crown leveling variants), with exact base/quality/socket state preserved. Keep
preparation eligibility distinct from completed payload utility. Full named tiers,
source review, base desirability and exact scoped prices remain unfinished.

## JMOD preparation annotations — 2026-09-25

Reviewed12 exact cached JMOD source entries. Added class-specific blocking-pair
annotations requiring magic non-ethereal Monarch, four empty sockets,20block and
30FBR. Missing/unknown/filled/partial socket state does not qualify. Fissure MF
retains four-Ist preparation while the other configurations retain their Facet
requirements; empty sockets never supply future MF or elemental bonuses. Complete
block/cast-rate/equipment checks remain on partial fit, advisory only for present
base-modifier recognition.

Red:5 grouped missing-configuration failures. Green:268 affected tests; Ruff/diff
checks pass. Tests cover every role member, both blocking thresholds, unknown stats,
class, base/quality, ethereal/identification and socket count/contents. All18 staged/
published reports and prices unchanged; new JMOD scenarios use domain fixtures.
176 configurations;297 roles. Generation `c37c5b87e09279f110c34831da3adbaf8475d0d1f7c1f52687bbf113139b3964` selected.
Guide/base/unified refreshed: 216 reviewed,152 pending
stat-desirability use/quality rows. Evidence `tmp/jmod-stats-*`.
Data-only update; no further restart beyond the prior combined-stat formatter fix.

Next scheduled starter/leveling tail: the two Lightning Strike Crown socket-base
variants. These may have no captured stat priority on an empty base; review the
appropriate usefulness/preparation/report behavior rather than inventing a stat.
Then resume Strafe Shroud suffixes and remaining reviewed-rule coverage gaps.
Full named tiers, source review, base desirability and exact scoped prices remain
independent unfinished gates.

## Starter tail: Crown preparation review — 2026-09-25

Reviewed both exact Lightning Strike Artisan Crown source rows: three Perfect
Topazes versus Ral/Ort/Thul. Neither specifies a base-defense target. Removed
unsupported31:0 defense from important_stats, which previously leaked into the
role's important_rolls. Preserve magic Crown/Amazon/non-ethereal/three-empty-socket
eligibility and exact future filler guidance. The empty base has no stat priority;
no invented marker or future MF/resistance bonus was added.

Red:2 regressions reproduced inappropriate important-roll output. Green:265 affected
tests; Ruff/diff checks pass. Tests prove defense is not a requirement/priority,
preparation remains partial and unknown/filled sockets do not qualify. All18 staged/
published reports/prices unchanged; Crown scenarios use domain fixtures.
176 configurations;297 roles unchanged. Generation `caad2623e7d9a8a5fb6b374c7dcef9bf46566c1e9d5b6b5c7c845778c6f862ba` selected.
Guide/base/unified maintenance refreshed; stat-desirability counts do not increase.
The current matrix still leaves these rows pending because it lacks an explicit
source-reviewed no-stat-priority disposition. Do not fabricate empty configurations
to inflate coverage. Evidence `tmp/crown-review-*`.

Next: implement validated no-stat-priority review dispositions for the Crown pair
in coverage maintenance (source/profile fingerprints, reason and invalidation),
then resume Strafe Shroud suffixes. Full named tiers, source review, base desirability
and exact scoped prices remain unfinished. Data-only runtime change; no further
worker restart beyond the prior formatter fix.

## Reviewed no-stat-priority coverage dispositions — 2026-09-25

Added maintenance-only explicit dispositions for the two reviewed Lightning Strike
Crown preparation roles. Excludes only stat_desirability; stat annotations, report,
market and all other dimensions retain their prior states. No empty runtime stat
configuration and no no-use/vendor decision is introduced. Reviews bind exact role
fingerprints, source locators/hashes and review dates; stale evidence, duplicate
reviews, unsupported dispositions and conflicts with priorities fail validation.
Unreviewed roles with no important_stats remain pending.

Red:8 missing-interface failures. Green:89 maintenance/Crown tests;10 focused tests
rechecked after tightening exception assertions. Ruff and diff checks pass. Full
matrix comparison proves exactly two row/dimension changes: use-quality stat
coverage is216 reviewed,2 excluded,150 pending. Evidence:
`tmp/stat-dispositions-{red,green}.log`, `tmp/stat-dispositions-coverage.json`.
No runtime artifacts changed or publication required; selected generation remains
`caad2623e7d9a8a5fb6b374c7dcef9bf46566c1e9d5b6b5c7c845778c6f862ba`.
Next: resume Strafe Shroud suffix review with whole-item/socket conditions and
source-backed priorities. Full named tiers, source review, base desirability and
exact scoped prices remain unfinished independent gates.

## Strafe Shroud preparation stat priorities — 2026-09-25

Reviewed cached Strafe Body Armor alternatives1/2 and native expansion torso
suffix rows: Stability24FHR, Precision10–15Dexterity. Added two source-bound stat
configurations preserving Amazon/magic/non-ethereal/exact Dusk Shroud/four-empty-
socket gates. Removed unsupported defense priority from both roles. Precision15
remains a preference; no future socket bonus, breakpoint or price is inferred.
Complete socket payload and loadout guidance retain partial preparation status.

Red:2 missing-configuration failures. Green:340 affected role/stat/maintenance tests;
Ruff/format/diff checks pass. Domain fixtures cover suffix minima, absent/unknown
stats, no cross-suffix substitution, wrong base/quality/class, ethereal/identification
and socket count/contents. All18 staged and published reports and prices unchanged.
178stat configurations;297roles. Generation
`c63e6c44c48579b10a8cd4c935302c5f5bd3becc6cf11a0cb90089b47faad671`
selected. Guide/base/unified maintenance refreshed:218reviewed,2excluded,148pending
use-quality stat-desirability rows. Evidence `tmp/shroud-stats-*`. Data-only runtime
update; no additional worker restart required.

Next: Mirrored Blades Starter Rhyme Grimoire preparation (all three staffmods plus
exact two-empty-socket/base/class constraints), then remaining starter dagger and
imbued throwing configurations. Named tiers, exhaustive source review, base
usefulness and exact offline price coverage remain independent unfinished gates.

## Rhyme Grimoire preparation staffmods — 2026-09-25

Reviewed exact Mirrored Blades Starter offhand source and native Grimoire/skill
identities. Added one stat configuration for normal and superior non-ethereal
Grimoire with two empty sockets, Warlock context and all three positive staffmods:
Mirrored Blades392, Hex Purge389, Summon Defiler377. Stronger staffmods qualify
without inferred perfect-roll status. Shael/Eth insertion remains a partial-use
condition; empty bases receive no completed recipe bonuses or price claim.

Red:2 missing-configuration cases. Green:340 affected tests; Ruff/format/diff checks
pass. Fixtures cover both qualities, each missing/zero/unknown skill, Hex Purge
explosion404 and other skill-bonus substitutions, wrong base/class/quality,
identification/ethereal and socket count/contents. All18 staged and published saved
reports/prices unchanged.179configurations/297roles. Generation
`3f87e4ff3df597b5e629d4a6632133f314ae8f87080c8786153f283afd6648fc`
selected; guide/base/unified coverage refreshed:220reviewed,2excluded,146pending
use-quality stat-desirability rows. Evidence `tmp/grimoire-stats-*`. Data-only update.

Next: starter Echoing/Abyss dagger rules still use required_any_stats without an
explicit must predicate. Review exact source requirements and applicability before
adding stat configurations; keep FCR dependencies and alternative-weapon advice.
Then imbued throwing configurations. Named tiers, full guide/source review, base
utility and exact scoped market coverage remain independent unfinished gates.

## Abyss starter dagger priorities and duplicate-gate reporting — 2026-09-25

Reviewed exact cached Abyss Starter prose: check daggers for skill ranks before
Spirit; the75FCR target is a whole-loadout target. Added an explicit any-skill
predicate preserving existing alternatives and one stat configuration for magic,
rare and crafted daggers. Present relevant skill bonuses are desirable; FCR is
supporting only and cannot qualify a dagger alone. No ED/AR priority, socket or
ethereal premium inferred. Existing pre-runeword/loadout qualifications remain.

Saved Dread Edge replay exposed duplicated restriction text when the typed gate
exactly repeated required_any_stats. Role evaluation now reuses the identical
trace and reports the specific skill outcome once. Distinct compound requirements
retain their independent restrictions. Red3 configuration failures and3 duplicate
report cases; focused green, then full2974passed/3skipped(135.77s). The initial
artifact-equality failure was resolved by rebuilding profiles. Ruff/format/diff pass.
All18 final staged/published reports and prices equal the prior generation after
the duplicate-report fix. Evidence `tmp/abyss-dagger-*`.

180configurations/297roles. Generation
`148c6cc03f09cb1772616096873449c02786b584e03f027d810202c0d626f7d9`
selected and revalidated. Guide/base/unified refreshed:223reviewed,2excluded,
143pending use-quality stat rows. Restart Alt+D for the Python reporting change.

Source concern requiring next review: echoing-starter-dagger still has no stat
configuration. Direct cached HTML confirms its dagger passage concerns three-
socket future runeword bases, whereas the old role selects magic/rare/crafted.
General AR/skill advice alone does not prove that specific affixed-weapon role.
Correct that legacy role's source scope/coverage before adding annotations; do
not silently promote it as a reviewed affixed guide recommendation. Cached source:
pricing/raw/mr/guides__echoing-strike-warlock-guide.html, Starter Setup paragraph.
Then resume remaining imbued throwing configurations. Named tiers, source review,
base usefulness and exact price coverage remain unfinished independent gates.

## Corrected Echoing affixed-dagger source mapping — 2026-09-25

Retired echoing-starter-dagger from executable profiles: exact cached Starter prose
advises future three-socket runeword daggers, not magic/rare/crafted weapon use.
General attack-rating and skills advice across gear does not establish that role.
Retained original profile, source hash/locator, review rationale and pending base
replacement in planning/retired_role_reviews.json. No no-use/trash/price decision.
The passage does not name a recipe or required staffmod combination; native legal
socket eligibility alone must not be promoted to desirable-base coverage.

Red: saved Dread Edge incorrectly matched Echoing. Green:114 focused tests.
Broader assessment run1637passed/3failed because repository fixtures mutated the
first profile without renewing its now-present stat review. Fixed those fixtures
to compile a valid reviewed update; all8repository/stat-bundle rechecks pass.
Runtime stale-review validation remains intact. Ruff/format/diff checks pass.
Skill-evidence tests now use the retained Abyss role, preserving their original
unknown/conflict/absence semantics. Evidence `tmp/echoing-source-*`.

Published Dread Edge now shows0confirmed/0conditional builds instead of the false
Echoing candidate; other17report texts unchanged. All18prices unchanged. Generation
`d349958b5e98921a9d167712211935669cfa10d958e7301e97008eb932ce8fec`.
All62891source occurrences and2739identity IDs retained; direct rule links273→271.
296executable roles/180stat configurations. Use-quality rows368→365; stat states
223reviewed/2excluded/140pending. This reduction removes three invalid quality
assignments; it is NOT three newly completed reviews. Original base-source work
remains open. No additional Python runtime changes/restart beyond prior checkpoint.

Next: remaining five Double Throw imbued examples (axe/knife/harpoon). Preserve
slot-specific stat combinations and planner-example scope. Echoing runeword-base
replacement, full source review, named tiers, base usefulness and exact offline
price coverage remain unfinished gates.

## Double Throw imbued-example priorities — 2026-09-25

Reviewed cached db0106mf embedded items80/81/143: Flying Axe, Flying Knife and
Winged Harpoon, retaining2023source date and five guide hand placements. Added five
stat configurations requiring each complete rare/ethereal/Barbarian/zero-socket,
no-cold combination. Axe fire resistance/IAS, knife AR/Amplify/mana leech and
harpoon IAS/life leech stay separate alongside ED, Combat skills and typed quantity
replenishment. Match means the cited example, not a minimum viable roll, guaranteed
imbue, unlimited quantity, breakpoint or price. Preparation/loadout advice remains.

Red:5missing configurations. Green:349affected tests; Ruff/format/diff checks pass.
Fixtures cover all five roles, each missing/below-target modifier, typed units,
cold/incomplete captures, base/quality/class/ethereal/socket/identification gates,
and unrelated example modifiers do not inherit priorities. All18staged/published
report texts/prices unchanged.185configs/296roles. Generation
`e0d0b2c2655cd31d20f2ebd4601461d9230fbf6c1f262f02409f9b021220666f`.
Guide/base/unified refreshed:228reviewed,2excluded,135pending use-quality stat rows.
Evidence `tmp/imbue-stats-*`. Data-only, no additional worker restart.

Current executable non-named role priority queue is covered:185configurations plus
the2Crown dispositions. This is NOT all-item or all-guide completion, and does not
close roll/report/price dimensions. Remaining109role configurations are named items
and completed runewords (44set quality rows,39unique,26normal/26superior runeword).
Next: add explicit identity-safe stat-configuration support, starting with completed
Insight roles as GUIDE_FIRST's acceptance fixture. Current compiler rejects named
roles; some have typed must/base families (Insight), while others lack them (Sazabi).
Do not remove that guard without preserving exact identity, completed recipe/base,
companion/mercenary conditions and independently reviewed priorities. Continue
specialist/leveling tail scheduling and the outstanding named-tier/base/source/price
gates; Echoing base replacement remains pending documented source review.

## Identity-bound named stat configurations and Insight — 2026-09-25

Compiler now accepts reviewed named roles only with explicit base types and a must
predicate. It composes exact name selectors into the compiled required predicate;
identity remains enforced outside CandidateIndex and after serialization. No new
schema or inference from important_stats. Named roles lacking mechanical predicates
still fail compilation rather than receiving invented applicability.

Reviewed12 completed Insight mercenary configurations for Meditation mana support.
Require identity/runeword, polearm/spear, four filled sockets, native aura and exact
mercenary dependency. Remaining equipment advice stays partial. Only Meditation
gets desirability; ED/Critical Strike are not automatically imported from old
important_stats. Range/perfect-roll quality remains separate. Unknown context does
not gain a stat-match claim; exact prices and named tiers are unaffected.

Red: named compiler rejection plus12 missing-config cases.117focused tests pass.
Full suite2993passed/3skipped with1publication locator fixture failure: mutating the
first profile now hits its stat-review guard before locator validation. Renewed the
test's stat binding so the original source-locator rejection is actually exercised;
all11publication validation checks pass.13Insight tests pass including saved Bill
under explicit Act2Might context (level12Meditation highlighted). Ruff/format/diff
checks pass. All18default staged/published texts/prices unchanged. Evidence
`tmp/{named-stats,insight-stats}-*`.

197stat configurations/296roles. Generation
`b7f50bf926f71ed5e87d9685a197eba6fec90de21f52622dfa23c7e569c2c94c`.
Guide/base/unified refreshed:252reviewed,2excluded,111pending use-quality stat rows.
Restart Alt+D: runtime bundle validation imports the changed compiler, so an older
worker must load the new identity-binding implementation to accept named reviews.

Next: three existing Infinity roles (self-wield and mercenary) with beneficiary-
specific stat semantics; then reserve a specialist/leveling named-item batch.
97named/runeword role configs remain,37already have explicit types/must. Remaining
named profiles need reviewed mechanical requirements before annotation. Broad
source census review, unique/set tiers, base utility, roll/report coverage and
matched offline prices remain independent unfinished gates.

## Infinity beneficiary-specific priorities — 2026-09-25

Reviewed cached Nova Standard/Hydra Hybrid and Lightning Strike Standard sources.
Added three identity-bound stat configurations: Nova self-wield highlights wearer
lightning pierce; mercenary highlights Conviction with paired ED as physical support;
Amazon self-wield highlights pierce with paired ED as physical support. No Nova
spell-damage claim from ED; mercenary weapon pierce does not transfer to player.
ED annotations require both decoded components. Range quality remains separate.

Made Nova Hydra Hybrid's source-specific Might/Holy Freeze mercenary choice a typed
dependency (previously prose only); renewed that role's guide-use fingerprint.
Recipe/four-filled-socket/aura and exact weapon family gates remain required. Source
base preferences, Amazon staffmods/Faith, equipment and full loadout stay partial;
none become universal best-base, ethereal, breakpoint or price claims.

Red:3missing configs. Green:348affected tests; Ruff/format/diff pass. Cases cover
both qualities, identity/recipe/socket/type/identification, aura, missing ED pair,
unknown pierce and missing/wrong/supported mercenary contexts. All18staged/published
reports and prices unchanged; Infinity cases use domain fixtures.200configs/296roles.
Generation `77b452b2a15148898ea116f0d27addf5a0115a070c22a6c96626cef5139ffd08`.
Guide/base/unified refreshed:258reviewed/2excluded/105pending use-quality stat rows.
Evidence `tmp/infinity-stats-*`. Data-only; no additional restart beyond prior
named-stat compiler update.

Next scheduled specialist/budget tail: Dragon Talon Kira's Guardian and Duriel's
Shell Cannot Be Frozen alternatives, preserving resistance combination, non-ethereal
player use and the slot/complete-Uber-loadout qualifications.94named/runeword roles
remain without stat configs. All-item named tiers, base/source review, roll/report
coverage and exact scoped price evidence remain independent unfinished gates.

## Specialist budget tail: Kira/Duriel CBF alternatives — 2026-09-25

Reviewed exact Dragon Talon Budget quote naming Kira's Guardian/Duriel's Shell as
Cannot Be Frozen alternatives. Added two named stat configurations: CBF desirable,
all four elemental resistances supporting. Preserve unique identity/base family,
Assassin/non-ethereal and complete native CBF/resistance combination. Slot tradeoffs,
Crushing Blow/AR/full resistance, equipment and level90/Uber readiness stay partial;
no defense/life priority, resistance-cap or market claim inferred. Added the cached
May22,2026source date to both role and guide-use records and renewed fingerprints.

Red:2missing configurations. Green:347affected tests; Ruff/format/diff pass. Cases
cover each absent/zero/unknown modifier, name/type/quality/class/ethereal and
identification; unrelated defense/life do not become priorities. Both alternatives
retain their own slot and full-loadout qualifications. All18staged/published report
texts/prices unchanged; new cases use domain fixtures.202configs/296roles.
Generation `c4da29605e77bbafdc67f583e96df09d2d924345516bb3422fac9483bdec66e0`.
Guide/base/unified refreshed:260reviewed/2excluded/103pending use-quality stat rows.
Evidence `tmp/budget-cbf-stats-*`. Data-only; no additional restart beyond the prior
named-stat compiler update.

Next demand batch: three Stealskull MF mercenary and four Crown of Thieves GF
mercenary configurations. Review socket payload, ethereal/upgrade and exact setup
requirements; no universal farming-helm premium or priority from mere mention.
92named/runeword configs remain. Named tiers, source/base/roll/report coverage and
matched offline prices remain independent unfinished gates.

## Farming mercenary helmets: Stealskull/Crown priorities — 2026-09-25

Reviewed seven exact cached MF/GF helmet entries: three Stealskull/Ist variants and
four upgraded Crown of Thieves/Lem variants. Added source-bound configs with MF/GF
desirable and life leech/Stealskull IAS supporting. Exact unique/type, complete
modifier combination, verified socket rune and mercenary remain mandatory; Crown's
Corona upgrade dependency is retained. Ethereal remains a preference (including
unknown/non-ethereal cases), not a price multiplier or stat-annotation requirement.
No defense priority or native-perfect-roll claim is inferred from socket totals;
full equip/breakpoint/survival and kill attribution remain separate.

Added cached May22,2026source dates to the seven role/guide-use records and renewed
fingerprints. Red:7missing configs. Green:352affected tests; Ruff/format/diff pass.
Tests cover every member, modifiers absent/zero/unknown, required child rune versus
empty/wrong/unknown socket state, missing/wrong mercenary, identity/quality and
unupgraded Grand Crown. All18staged/published report texts/prices unchanged; new
helmet combinations use domain fixtures.209configs/296roles. Generation
`40b5c78ccbc7e541822e40b10f1622a66319cd10c68753fae6c809129be695c2`.
Guide/base/unified refreshed:267reviewed/2excluded/96pending use-quality stat rows.
Evidence `tmp/farming-helm-stats-*`. Data-only; no additional restart beyond the
named-stat compiler update.

Next: six Vampire Gaze mercenary roles, preserving compound IAS/resistance jewels,
Um alternatives and the Mephisto activity restriction. After that demand batch,
reserve the next specialist/leveling tail.85named/runeword configurations remain;
all-item tiers, source/base/roll/report coverage and scoped exact price evidence
remain independent unfinished gates.

## Vampire Gaze setup priorities and explicit activity — 2026-09-25

Reviewed six cached Gaze setups. Life leech/physical reduction are desirable only
with the complete native pair, correct identity and source mercenary/socket setup.
Three Rogue sources retain a single compound15IAS/all-resistance jewel; captured
parent IAS/resistance totals also receive priorities only after that child proof.
Two Frenzy sources require Um; Lightning Strike Ubers has no invented socket gate.
No defense/MDR priority, guaranteed survival or ethereal requirement inferred.

Added nullable explicit AssessmentContext.activity and a typed Uber Mephisto
requirement to Lightning Sorceress's Act5role. Missing/malformed/other-boss/ordinary
Mephisto contexts cannot activate its priorities. The source's other-Ubers Act2
alternative remains in conditional advice. Added cached source dates and renewed
role/guide fingerprints. Restart Alt+D for the context schema used by validation.

Red:6missing configs, then3missing parent-jewel annotations. Initial focused run
also exposed an overly strict test assumption: fully captured child jewels can
prove an existential match with an unknown parent summary. Kept that valid proof;
empty contradiction, missing children, parent totals alone and split jewels fail.
Full3013passed/3skipped(161.43s), then final parent-priority data update verified with
105affected checks. Ruff/format/diff pass. All18default staged/published texts/prices
unchanged; Gaze-specific cases use domain fixtures. Evidence `tmp/gaze-*`.

215configs/296roles; generation
`750aac3177396602a102b5a6071b5ed994d99f0ff732ea07b715d9bf4e9277ce`.
Guide/base/unified refreshed:273reviewed/2excluded/90pending use-quality stat rows.
79named/runeword configs remain. Next scheduled starter tail: Fissure Lore pelt;
review whether +3Fissure is a planner target versus a minimum before compiling.
All-item named tiers, source/base/roll/report coverage and exact scoped prices remain
independent unfinished gates.

## Fissure Starter Lore: planner preference correction — 2026-09-25

Cached Starter prose prioritizes +skills without a numeric Fissure minimum. The
pictured +3 Fissure Lore Antlers is now a preference; positive +1/+2 staffmods also
qualify as skill-support candidates. This reviewed inference does not establish
farming readiness. Exact Lore identity/recipe, pelt, normal/superior quality, Druid,
non-ethereal and two filled sockets remain required. Captured Fissure and all-skills
are desirable; a missing all-skills line is never fabricated from the recipe.
Source review and guide-use fingerprints renewed; one stat configuration added.

Red: five failures (missing configuration and former +3 minimum). Green: 348 affected
checks, Ruff/format and diff check pass. All 18 staged and published saved reports
and prices match the prior generation. No saved Lore capture exists in this replay
set; specific +1/+2/+3, preference, near-miss and unknown behavior uses domain tests.
Published generation d7aff9647e8493f758ee5a1d942a73b123021a940d4ebe994cb6aff233913102.
216 configs / 296 roles; use-quality stat coverage 275 reviewed, 2 excluded,
88 pending. Guide inventory and base/coverage matrices refreshed offline.
Evidence: tmp/lore-stats-*. Data-only; no additional restart beyond Gaze context.

The scheduled starter tail is complete. Next demand batch should be selected from
remaining named-role dossiers by distinct-build breadth and new use coverage,
checking source-required versus planner-target semantics before adding priorities.
78 named/runeword role configurations remain; this finite queue does not close
all-item coverage. Named tiers (93 reviewed / 472 pending), guide semantics,
base/roll/report coverage and exact scoped market evidence remain unfinished.

## Naj Teleport-swap stat priorities — 2026-09-25

Demand-led batch selected from the remaining named queue: 13 distinct cached build
lists share Naj's Puzzler as a weapon-swap alternative. Reused exact source locators,
May 22 source dates, existing class/native base/charge/equipment predicates and
conditional advice. Added verified staff type selectors and renewed guide-use
fingerprints, then 13 explicit charge-priority reviews. No guide re-extraction or
market collection. Available Teleport charges are desirable only after the full
existing role gates and charge payload validation; missing charges are not invented.
Roll quality remains independent. This does not claim current loadout need, main
weapon suitability, perfect rolls or price. The planner-only Fal variant remains
separate and unreviewed for stat priorities.

Red: 13 missing-config failures. Green: 110 affected tests; Ruff/format/diff checks
pass. Cases cover every role plus empty/malformed/wrong-level/duplicate charges,
wrong identity/type/quality/class, unknown ethereal/equipment facts, level shortfall
and socket-modified equipment uncertainty. No saved Naj capture exists; domain
fixtures prove its new behavior. All 18 existing saved reports/prices match before
and after publication. Evidence tmp/naj-stats-*. Data-only; no new restart required.
Generation 49cb4e3e3b76b89afd69a778eda881f48a18682fe285e54ab748ae1963051923.
229 configs / 296 roles; use-quality stat coverage 288 reviewed / 2 excluded /
75 pending. Guide inventory/base/coverage matrices refreshed. 65 named/runeword
role configs remain; global guide semantics, named tiers, base/roll/report and
scoped exact-price coverage are still incomplete.

Next demand batch: four Demon Limb prebuff configurations across Echoing, Strafe
and Dream, preserving available Enchant charges and the Lava Gout alternative.
Then reserve a specialist/leveling tail (including the separate Fal Naj planner
source review). This is batch one of two since the Lore starter tail.

## Demon Limb prebuff priorities — 2026-09-25

Second demand-led batch since the Lore tail: four configurations across three
builds (Echoing Standard/Ubers, Strafe Standard, Dream Ubers). Reused cached variant
sources and dates, confirmed prebuff prose, and added verified club applicability
plus source-bound Enchant-charge priorities. Strafe's absence-of-Lava-Gout dependency
remains mandatory; missing loadout is unknown. Only valid available Enchant charge
rows receive markers. Damage does not become desirable for a prebuff role. Ethereal
copies with charges retain temporary utility and the existing recharge limitation;
unknown ethereal status does not invent repairability. Equipment advice and buff
activity remain conditional, not proof of a currently active buff or combat use.

Red: four missing configuration failures. Green: 349 affected maintenance/role/stat
checks plus nine existing Demon Limb/demand tests. Ruff/format/diff checks pass.
Every configuration exercises identity, type, quality, class, empty/malformed/wrong
skill/duplicate charge failures, all ethereal states, and the Strafe alternative.
All 18 staged/published saved report texts and prices unchanged. No saved Demon Limb
capture exists in that set; new behavior uses domain fixtures. Evidence tmp/demon-stats-*.
Generation 2f96e99e51af41b3067a913646c0661e3bdf6edfae260ce7791cda97bd7d790c.
233 configs / 296 roles; use-quality stat coverage 292 reviewed / 2 excluded /
71 pending. Guide inventory and base/coverage matrices refreshed offline. Data-only;
no new worker restart beyond previously documented context changes.

Next scheduled specialist/leveling tail: review the separate Poison Nova Fal Naj
planner source and its equipment/endorsement limitations before deciding whether
stat priorities are justified. Keep planner-only discovery separate from confirmed
build demand. 61 named/runeword configurations remain, with global guide semantics,
named tiers (93 reviewed / 472 pending), base/roll/report coverage and scoped prices
still incomplete. Do not treat this role queue as the all-item denominator.

## Fal Naj planner example retired from executable roles — 2026-09-25

Scheduled specialist tail found a source-strength inconsistency: the existing
Poison Nova Fal-socketed Naj review says example, not separate guide endorsement,
but an executable candidate role still emitted it. Removed that one runtime role
and guide-use link; preserved full previous profile, example review and source in
planning/retired_role_reviews.json. Original source/occurrence data stays intact.
Exact variant endorsement and socket-modified equipment readiness remain pending.
The independently endorsed Poison Nova Naj swap remains, as do all 13 reviewed Naj
build alternatives. No no-use/trash disposition or negative price claim follows.

Red: one incorrect role-presence test failure. Green: 110 focused checks and all
1,699 assessment tests (119.41s); Ruff/format/diff pass. All 18 staged/published
report texts and price estimates unchanged. Naj demand still counts 13 distinct
builds. Published generation 51e071b02b2ee3ea1320ce54076421d54b9e9b4559c5b408ae3b9309f1376563.
233 stat configs / 295 executable roles. Use-quality rows 365 → 364; stat states
292 reviewed / 2 excluded / 70 pending. This pending decrease is removal of an
unsupported executable assignment, not completion of a stat review. Guide inventory
and base/coverage matrices refreshed; source occurrences retained. Evidence
 tmp/fal-source-*. Data-only; prior Python restart guidance remains.

Next demand batch: Angelic ring/amulet combinations across five builds. Review
piece versus active set-bonus priorities and required companions; do not annotate
an amulet with a bonus belonging only to the ring or imply a whole set is equipped.
60 named/runeword configs remain; global source/tier/base/roll/report/market gates
remain unfinished. Tail complete; demand-batch scheduling restarts at zero.

## Angelic piece-specific stat priorities — 2026-09-25

Demand batch one after the Fal source tail: ten ring/amulet roles across five builds.
Reused reviewed pairing sources and native setitems: Halo aprop1a att/lvl maps to
native 224, while Wings has no such property. Five ring configurations mark only
captured positive 224:0 desirable after exact class/player companion/multiplicity
checks. Flat attack rating cannot substitute, missing set bonuses are not fabricated,
and no perfect-roll/price claim follows. Existing readiness advice stays conditional.

Five source-bound no-stat-priority dispositions cover the enabling amulet roles:
these sources establish the pair's attack-rating use, not an independent priority
for the amulet's captured stats. This is not no-use, trash or a ban on future reviewed
amulet priorities. Existing Build use and companion conditions remain intact.

Red: five missing configurations. Green: 107 affected checks after updating the
explicit exclusion inventory test from two Crowns to two Crowns plus five amulets.
Ruff/format/diff pass. Cases cover every build, ring counts, unknown/merc-only/wrong
companions, absent/zero/duplicate/wrong stat, identity/class/type/quality. No saved
Angelic capture exists; domain fixtures verify new behavior. All 18 saved staged
and published report texts/prices unchanged. Evidence tmp/angelic-stats-*.
Generation 379f5e805c0447897849b432133fbb803c45cb49ee0b24d20ee70bffd4951579. 238 configs / 295 roles;
stat-use 297 reviewed / 7 excluded / 60 pending. Guide/base/coverage refreshed.
Data-only; no new restart. Five exclusions are explicit per-use reviews, not a
universal amulet rule or new completed market coverage.

Next demand batch: Sigon/Death's starter set combinations, preserving distinct
piece bonuses and partial-set requirements; then scheduled specialist/leveling tail.
50 named/runeword roles still lack a stat configuration or reviewed disposition.
Global guide semantics, named tiers, base/roll/report and exact scoped prices remain
unfinished; this finite role queue is not the all-item denominator.

## Starter set glove/belt priorities — 2026-09-25

Second demand batch after the Fal tail: seven configurations, covering three Sigon
Gage combinations, Enchant Death's Hand/Guard, and two upgraded Guard setups.
Native piece definitions confirm IAS on Gage/Hand and CBF on Guard. Reviewed
inference from these attack-oriented combinations marks only captured relevant
stats, after exact player/class/companion or upgraded-base gates. Never transfer
other-piece bonuses or fabricate a set bonus on an unequipped hover. The generic
source conditions still qualify equipment, breakpoints and full build readiness.
Normal Death's Guard retains its true item predicate/CBF utility, but cannot satisfy
the cited upgraded potion-capacity configuration. No market premium inferred.

Red: seven missing configs. Initial green run exposed two test-only mapping-access
errors; corrected rule_trace['truth'] access. Final 112 affected checks pass;
Ruff/format/diff pass. Every role checks identity/type/quality/class, missing/zero/
duplicate stats, absent/unknown/merc-only companions, plus normal-versus-upgraded
belts. All 18 staged/published saved report texts/prices unchanged; these seven
set configurations use domain fixtures, not new live captures. Evidence
 tmp/starter-set-stats-*. Generation 9e70df3914cd602162e796597dc8cc164931e72098e400484b10f847c3ae6112.
245 configs / 295 roles; stat-use 304 reviewed / 7 excluded / 53 pending.
Guide/base/coverage refreshed offline. Data-only; no additional worker restart.

Next scheduled specialist/leveling tail: remaining six starter Sigon helmet/boot/
Wrap uses, including source-specific Ort/IAS-jewel conditions and the distinction
between a piece bonus and a set-enabling role. Do not mark all native properties
valuable merely because the named combination is useful. 43 named/runeword roles
still need stat review/disposition; all-item guide/tier/base/roll/report/market
coverage remains incomplete.

## Remaining Sigon starter stat reviews — 2026-09-25

Scheduled specialist/leveling tail covered two Visor and three Sabot uses plus
Berserk Wrap. Five configs prioritize captured piece-owned AR (Visor native224,
Sabot native19) within exact reviewed player combinations. Strafe's explicit AR
benefit and native definitions support this; Double Throw/Berserk are documented
inferences from their attack-oriented combinations. No manufactured bonus from
identity alone, no automatic MF/defense priority. Visor still needs its verified
Ort or15IAS-jewel child; parent IAS totals cannot replace child proof.
Wrap has a source-bound no-stat-priority disposition for this enabling use; no
other-piece bonus is transferred and useful Build use remains.

Red: six missing configs/disposition failures. Green:111affected checks; Ruff/format/
diff pass. Every build tests absent/unknown/merc-only companions, identity/quality/
type/class, missing/zero/duplicate stat and helmet payload failures. No saved Sigon
capture; domain fixtures verify new behavior. All18staged/published report texts
and prices unchanged. Evidence tmp/sigon-stats-*.
Generation 1e0375608f60407eb811e4085b05c89b1d2f19dc52b04dc1bae4890d34a82061.250configs/295roles;
stat-use309reviewed/8excluded/47pending. Guide/base/coverage refreshed offline.
Data-only; prior Python restart instructions remain. Tail complete.

Next: review three Tal Rasha Magic Find roles as one set-dependent configuration
family, followed by Sazabi piece-specific roles; then reserve the specialist tail.
37named/runeword roles still need stat review/disposition. Global source semantics,
named tiers, base/roll/report coverage and scoped exact prices remain incomplete.
Before claiming this finite role queue finished, audit GUIDE_FIRST obligations
against the full coverage denominator, not just executable roles.

## Tal Rasha MF piece priorities — 2026-09-25

First demand batch after Sigon tail: three named roles from cached Lightning MF
source, which explicitly values MF/FCR/resistances. Native piece definitions limit
priorities: armor MF/FCR/fire/cold/lightning resist; belt MF/FCR; amulet lightning
resist. Amulet FCR needs more than the cited three pieces and shared set MF is not
copied onto every piece. Mark only captured positive values. Exact name/type,
Sorceress, other two player pieces,117total FCR and armor Ist remain mandatory.
Added explicit identity predicates to formerly selector-only roles, preserving
runtime identity selection; no new gear minima, stat fabrication or prices.

Red: three missing configs. Initial green found an old magic/rare/crafted amulet
test counting all amulet configurations; narrowed its fixture selection to its
actual affixed-quality scope. Final107affected tests pass, including existing Tal
roles and loadout-breakpoint checks; Ruff/format/diff pass. New cases cover every
piece, missing stats, no transferred bonuses, wrong identity/type/quality/class,
missing/merc-only companions, unknown/below117FCR, and armor socket failures.
No saved Tal capture exists; domain fixtures verify its new behavior. All18staged/
published saved report texts/prices unchanged. Evidence tmp/tal-stats-*.
Generation e0477e85495fe62fd3a4afc691bded6228f08c8991762687bff6d09aa3295707.253configs/295roles;
stat-use312reviewed/8excluded/44pending. Guide/base/coverage refreshed offline.
Data-only; no new restart.34named roles still need stat review/disposition.
Next: three Sazabi roles with piece-specific priorities and full mercenary/socket
conditions; then reserve the specialist tail. All-item guide/tier/base/roll/report/
market coverage remains incomplete.
