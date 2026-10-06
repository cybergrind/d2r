# All-item assessment: end goal and completion contract

## Current contract (2026-10-06) — read this section first; it overrides everything below

The user named this document the main driving document again on 2026-10-06. It states the end
goal, the measures that prove it and the stopping rule. [PLAN.md](PLAN.md) holds the design,
the steering history and the status (its section 8); the work queue is its newest Steering
block. Everything below this section was frozen by the user on 2026-10-03 and stays frozen:
the scope manifest, coverage matrix, item bank, receipts, per-item formal reviews and the
"Mandatory final gates" table are technical reference and are not resumed or regenerated.

### End goal

On a drop, say quickly whether it is worth keeping to sell, for every item type, in
Softcore / Non-Ladder / PC / Reign of the Warlock, Ist = 1. In priority order: liquid items
first; a fast answer; every type answered (uniques, sets, rares, magic, crafted, charms,
jewels, bases, runewords, runes, materials); uniques and sets separated by rolls and
ethereal status; demand taken from the guides and from market data. The player is not
levelling characters. Keep price: 0.25 Ist, inclusive.

### Evidence rules

- The user does not label, skim or confirm items. Never ask, and never report work as
  blocked on it.
- The guides are the answer key for patterns and demand; scoped Traderie asks are the answer
  key for price, one vote per seller. Asks are not sales; demand never creates a price.
- When a guide and later Traderie evidence disagree, the later evidence wins and the guide
  is corrected with a dated pass.
- Live pulls only through `pricing/tools/`, paced, with the scope filters. The weekly page-0
  pull is authorized; the next is due 2026-10-10 or -11.

### Measures (score files in `inventory_tracking/corpus/data/`, values of 2026-10-06)

| Measure | Target | Now |
|---|---|---|
| Guide worked examples and false-positive rows | 100% pass | 36/36 and 18/18 |
| Guide table rows that are verdict or own-use rows | every row classified with a reason; at least 95% pass | all classified and executing; 402 of 404 pass (99.50%) |
| Listing replay, valuable seller votes flagged | at least 85% | 82.82% (bases 77.82%, rare 45.07%, magic 55.74%); evidence-backed CHECK counts for all types; scorer removed after zero added held-out votes |
| Cheap listings flagged SELL or slow / CHECK; a cheap listing in a cohort where at least 90% of sellers ask the keep price is not a false flag | at most 10% / 25% | 10.37% (over) / 17.68% |
| Named corpus drops that end as CHECK | at most 15% | 12.0% |
| SELL cohorts with turnover or buyers | at least 80%, over an interval of seven days or more | unmeasured (one-day interval) |
| Speed | under 50 ms per item; a ten-item identify pass under 1 s | latest live one-item pass 69.0 ms; prior three-item pass 57.5 ms; required ten-item pass unverified |

A measure counts as met only from a score file produced by the current code and tables. A
number that goes down is reverted or explained in PLAN.md section 8.

### Queue

PLAN.md "Steering 14" (2026-10-06 23:55), in this order, with the Steering 9 rules of pace:

1. Speed: record a ten-item pass by replaying captured identify items through the live
   service path; bring the one-item pass from 69.0 ms under 50 ms.
2. Report the 982 valuable votes vendored for lack of demand as their own miss cause; flag
   none of them. Whether they stay in the denominator is the user's decision after the
   seven-day pull of 2026-10-10 or -11.
3. Rare and magic: authored patterns only, largest missed families first (481 votes short
   of 85%). The paid-property scorer is removed and is not rebuilt.
4. Base variants priced from existing listings (391 votes).
5. Named roll placement and the two remaining guide rows.
6. Evidence-backed CHECK counts as attention for all item types (user, 2026-10-06);
   priced SELL/slow is reported separately. Cheap SELL and demand: at the weekly pull.

### Stopping rule

The work is finished only when every measure above meets its target in the same score run.
A batch, a family, a passing test suite, a status update or a context compaction is not a
reason to stop, and no "continue" is requested from the user. If one item is blocked,
continue with the next; a measure that cannot be reached is reported with its number and
the evidence, never declared met. Do not add gates, manifests or per-batch artifacts to
prove progress: the score files are the proof.

---

> **Frozen reference from here on (user decision, 2026-10-03).** The gates, queues and stopping
> rules below are suspended and do not drive work.

# Reference: contract text as of 2026-10-01

Updated 2026-10-01 at the user's request. **Status: unfinished.**
This document governs completion and stopping. It supersedes older milestone,
checkpoint and priority wording where that wording suggests stopping early.
GUIDE_FIRST.md and IMPLEMENTATION_PLAN.md retain their technical architecture.

## One end goal

Deliver and publish an offline system that identifies valuable items in
Softcore / Non-Ladder / PC / Reign of the Warlock (Ist = 1), including their
valuable rolls, bases, sockets, ethereal variants and relevant player/mercenary
uses. Also highlight valuable or exceptional best-in-slot leveling items.
The player is not leveling characters: generic leveling equipment, ordinary
starter progression and exhaustive leveling-build walkthroughs are out of scope.
Hardcore and Ladder-only build uses, market research and pricing are out of scope.
Do not expand handlers or tests to complete those modes. Retain shared items and
their applicable Softcore/Non-Ladder uses; mode-isolation checks remain necessary
to prevent foreign-mode evidence from entering their assessments.
“Exceptional leveling” is not restricted to the Rare quality; a unique, set,
runeword, base or affixed item can qualify when evidence establishes that use.

A family-wide classification can account for ordinary low-demand items without
implementing every generic leveling setup. All-item coverage means no valuable
item/configuration is silently missed, not a requirement to explain every possible
use of every item. Missing evidence alone still cannot establish trash value.

“All items” includes bases, normal/superior/low-quality variants, magic, rare,
crafted, unique, set pieces, partial/full sets, completed runewords, charms, jewels,
runes and other eligible utility/consumable families. An explicit reviewed family
rule may cover many members; a separate class per item is unnecessary.

No numerical price is promised without evidence. However, every family must have
implemented pricing logic and every scoped pricing target must receive a reviewed
pricing disposition. A generic “not implemented” or an unexamined cache miss fails
completion. Assessment completion and numerical-price availability are measured
separately; neither may be reported as the other.

## User scope clarification and queue migration (2026-09-29)

This clarification supersedes older requirements for exhaustive generic leveling
and starter-equipment coverage. Keep baseline trade classification for every named
item. Preserve existing valid rules, but stop generating new deep handlers, market
research or item-bank scenarios solely for unremarkable leveling uses.

Prioritize valuable Non-Ladder items and configurations, then valuable/exceptional
best leveling items. Use all gathered builds to discover demand; a starter label
alone does not exclude an item that also has trade or endgame/mercenary value.
Mixed-use items remain included for those valuable uses. Do not blanket-exclude
all low-level gear or treat unreviewed demand as worthless.

The previous 114,252-check queue was generated under a broader scope and is NOT
the remaining-work count for this clarified goal. Required next maintenance work:
reclassify source/configuration obligations with explicit scope reasons, preserve
valuable and unknown-demand leads, and regenerate the manifest, queue and gates.
Historical generic-leveling obligations must not prevent completion after that
migration; unfinished valuable-item work must not be hidden by it. Final gates
and the zero-required-work stopping rule apply to this user-defined scope.

## Game-mode scope clarification (2026-09-30)

Only **Softcore / Non-Ladder** is in scope; retain PC / RotW and Ist = 1.
Skip Hardcore-only and Ladder-only configurations, demand, pricing research and
required item-bank targets. They must not block completion or contribute to
Softcore / Non-Ladder demand or valuation. Keep historical source records for
traceability, with exact source-backed exclusions in the scope manifest.

Exclude the incompatible use, not every item mentioned by that use. Shared items
remain eligible through independently supported Softcore / Non-Ladder uses.
Do not treat Ladder availability as proof of Non-Ladder availability, nor confuse
Non-Ladder ownership/trading with eligibility to create a runeword. Unknown mode
must remain unresolved rather than silently defaulting to compatible evidence.

Apply this filter before generating remaining-work and required-test counts;
regenerate dependent manifests and gates after validating the exclusions.

## Sellability and meaningful rolls (2026-10-01)

The immediate review priority is valuable uniques and set items **one by one**,
then the equivalent valuable configurations of other item families. Preserve
universal baseline tiers, but do not treat baseline tier coverage, guide inclusion,
build usefulness or a perfect stat as proof that this particular item is sellable.
Follow [the roll-value review plan](ROLL_VALUE_REVIEW.md). This priority supersedes
ordinary starter/build-profile expansion and incidental item-bank gap filling.

Each valuable identity/configuration needs a reviewed distinction between useful
gear, a trade candidate and a premium trade candidate. Record the material rolls,
required combinations, ethereal/socket/base conditions, qualifying boundaries and
what the captured item lacks. Some items remain trade candidates at minimum rolls;
others need particular rolls to justify the highlight. Neither case is universal.
Unknown facts or inadequate evidence must not silently qualify or disqualify it.

Completion requires evidence-backed item-specific decisions, executable boundary
tests and visible report checks. A generic percentage-of-perfect cutoff or a
mechanical conversion of every mid/high baseline into "sellable" fails this gate.
Asking prices establish asking segments, not completed sales or liquidity.

## Finite, auditable scope

Create one versioned scope manifest from the union of enabled native definitions,
all gathered build guides as discovery evidence, scoped player and mercenary
equipment, swaps, prebuffs, alternatives, socket payloads, partial/full set uses,
valuable or exceptional best-in-slot leveling research,
existing valuable-item evidence and saved unsupported scans. Pin source hashes,
dates and extraction versions; derive denominators from it, never from rule counts.

Every source occurrence must link to a reviewed semantic configuration or a reviewed
exclusion with a specific reason. Deduplication must preserve all source links and
must not merge different conditions. Missing referenced sources and contradictions
remain blockers until resolved; they cannot be relabeled excluded for convenience.
Items absent from guides still require review. Lack of a mention is not a no-use
or trash decision. Enumerate legal variant dimensions and predicate boundaries,
not infinitely many possible numerical rolls or hypothetical future builds.
New discoveries during implementation enter this manifest and queue; future game
patches/source revisions after delivery are maintenance work against a new version.

## Mandatory final gates — all must pass together

| Gate | Required evidence |
|---|---|
| Scope closure | Every eligible identity/family and known configuration accounted for; zero unexplained identities, unreviewed occurrences or unresolved required source conflicts. |
| Universal tiers | Every eligible unique, set piece and complete set has a rendered baseline trade tier high/mid/low/trash; premium conditions never suppress it. Leveling highlights and detailed reviews are required only for valuable or exceptional best-in-slot leveling items and combinations; generic leveling uses are excluded. |
| Executable assessment | Every scoped member has a reviewed applicable decision rule or evidence-backed disposition. All known useful configurations match correctly, including alternatives, swaps/prebuffs, mercenary roles and companions. Generic routing/unknown fallbacks do not count as reviewed coverage. |
| Variant quality | Relevant ethereal status, ED/defense, native and upgraded bases, staffmods/inherent mods, rolls/tiers, sockets and actual contents are supported. Base assessment explains eligible words, best/preferred bases where justified, deficiencies and legal socket outcomes without assuming unknown item level. |
| Roll-dependent trade value | Every valuable named item and scoped valuable configuration has a reviewed trade qualification distinct from build utility; material rolls/combinations and ethereal/socket conditions, ordinary versus premium boundaries, unknown handling, source evidence, boundary item-bank tests and published report assertions are complete. Existing baseline tiers alone do not satisfy this gate. |
| Pricing | Every family has tested comparison/valuation rules. Every pricing target has either a supported dated estimate or a reviewed evidence-unavailable disposition identifying the actual deficiency. Cached usable evidence is processed; source scope, facets, independent sellers and asks versus fills are preserved. No unfinished parser/rule/research task is disguised as absent market evidence. |
| Reports | Published reports display the assessment, trade/leveling highlights, relevant ranges and actionable deficiencies concisely. No repeated generic disclaimers. Known unsupported inputs preserve uncertainty and produce a durable review record. |
| Item bank | Every important/valuable item across every scoped build/use has independently authored positive, near-miss and unknown-fact scenarios. Constructed items run through native decoding and the full offline appraisal pipeline, with `dirty-equals` partial expectations for the specific build contribution, tiers, relevant stats and pricing/report behavior. Include mercenaries, alternatives, sockets/ethereal variants and valuable leveling uses. Case presence is not a test pass; retain a coverage manifest and passing run tied to the final generation. |
| Verification | Positive, near-miss, unknown and boundary tests cover each distinct rule/exception; all saved captures replay; a final full regression run passes, with any skips explicitly justified; lint and artifact/source validation pass. |
| Delivery | One selected generation contains the verified artifacts. Its replays match the validated staged outputs. Final coverage report identifies manifest/generation/test evidence and zero remaining required work. Any necessary runtime restart/deployment is verified, or delivery is explicitly still pending. |

Evidence-unavailable is acceptable only after the applicable offline sources and
matching logic have been reviewed. It means “no defensible numeric estimate”, not
zero value, worthless, or priced. Track these records separately with reasons and
research targets. If required evidence cannot be obtained under current access or
authorization, record a blocker and seek the needed input; do not declare success.
Never invent market values or quietly relax completion gates to empty the queue.

Final verification scope also binds the current runtime sources, tests and fixtures,
dependency manifests and Makefile through `maintenance/verification_scope.py`.
Changing, adding or removing these inputs invalidates prior final attestations.
Generated worker logs, bytecode and KB outputs are not executable-source evidence;
the KB and publication artifacts remain covered by their separate manifests.

## Execution order from the current state

1. Implement a trustworthy completion ledger/gate over the manifest before further
   open-ended profile expansion. Replace hardcoded pending statuses with derived
   review states and exact source/configuration links. Persist the actionable queue
   outside tmp/. Prove the gate fails on the current unfinished state and on missing
   identity, source link, variant, pricing handler and report coverage.
2. Preserve and recheck the completed universal-tier baseline. It is a prerequisite,
   not the end goal. Keep existing valid profiles and source reviews.
3. Finish source/configuration closure using reviewed family templates plus specific
   exceptions. Resume queued Zeal uses, then all remaining named, base, affixed,
   specialist, valuable/exceptional leveling and no-guide cases. Do not expand generic
   leveling or ordinary starter setups. Prioritize coverage gain without dropping
   the long tail; handle source conflicts alongside other independent work.
4. Close variant, stat/range, socket, report and pricing-policy gaps for all members.
   Process existing scoped market evidence. Keep evidence deficits separate from
   implementation deficits; live maintenance follows existing authorization rules.
5. Run the final gates, repair every failure and revalidate affected work. Publish,
   verify selected runtime output and generate the final completion report.

Use red-green tests for behavior changes. Batch size is an execution detail.
Publish safe incremental improvements and continue immediately to the next open
queue entry. Do not rerun successful one-shot data appenders.

## Stopping rule

**Stop and call the work finished only when every final gate above passes for the
same manifest and selected generation, with zero pending or blocked required work.**

A batch, item family, phase, milestone, test pass, successful publication, profile
count, checkpoint or context compaction is never a reason to stop the process.
Intermediate updates are progress reports, not final delivery. Do not ask the user
to say “continue” after a checkpoint. If one task is blocked, continue independent
work. A user-requested pause or a genuine blocker preventing all remaining work
may interrupt execution, but must be reported as unfinished, never completed.

Current baseline: selected generation
`519baede215d35e06dda726c80e1af3ef4187ea233dadc343373d0f2b6eaa0a0`,
2,317 profiles and 2,309 stat configurations. Universal tiers are verified;
all-item assessment is not. The 142 named identities / 850 missing item-build leads
are only one remaining queue, not the complete denominator. Existing dossier
pending totals are discovery partitions and cannot yet demonstrate closure.

## Seasonal-definition correctness follow-up (2026-09-29)

The local ordinary table `third-parties/d2data/json/base/uniqueitems.json` and
imported overlay `pricing/raw/d2data/uniqueitems.json` differ under shared table IDs.
`appraisal-seasonal-named-audit.json` preserves both rows and source hashes;
regenerate with `uv run --offline python -m
pricing.knowledge.assessment.maintenance.seasonal_named_audit`.

Only applicable Non-Ladder correctness and valuable-item cases require closure.
Season-15 Ladder demand/pricing expansion is out of scope without affirmative
Non-Ladder availability evidence. Preserve completed defensive parsing work; do
not prioritize generic leveling uniques merely because their variants differ.
Technical work identified before the scope clarification:
- Preserve and resolve ordinary versus season-15 definitions for Gravenspine,
  The Battlebranch, Bane Ash, Pluckeye, Piercerib, Blinkbats Form, The Ward,
  Manald Heal and Bloodletter. A native table ID alone is insufficient.
- Review the separate `disableChronicle` change on Cold Rupture, Flame Rift,
  Crack of the Heavens, Rotting Fissure, Bone Break and Black Cleft; this is
  mode eligibility evidence, not an additional stat roll.
- Link these conflicts into the machine completion scope. The standalone audit
  does not yet do that and cannot close any existing task.
- Preserve provenance in definition compilation and runtime variant selection,
  reject ambiguous comparison cohorts, and cover ordinary/seasonal/unknown
  captures with item-bank scenarios before publishing.
- Do not infer Non-Ladder availability or season transfers from a season flag.
  Manald's ordinary row has no faster-cast bonus; its season-15 row adds 10%.

Implementation progress: the compiler now retains nested ordinary definitions;
DefinitionStore exposes both and named comparison supports complete unsocketed
FCR/IAS/FRW disambiguation. Cross-version listings cannot borrow missing fixed
bonuses. This is staged, not published completion: metadata/report consumers,
non-scalar differences, scope integration and full variant item-bank gates remain.

## Dimension-specific scope reviews (2026-09-29)

`value_scope_reviews.json` may separately record `dimensions` reviews for exact
non-leveling uses. These exclude only that use-quality row's `leveling` obligation;
they do not exclude the item, its source occurrence, its item-bank cases, or any
trade/stat/variant/socket/price/report obligation. Named identity-level leveling
reviews and separately sourced exceptional-leveling combinations remain required.
Each review binds the exact profile fingerprint, source hash and quote, review date
and specific reason. Only the `non_leveling_use` classification and `leveling`
dimension are accepted. Stale reviews fail validation; absent reviews remain work.
Completion records these separately in `dimension_scope_dispositions`. Do not
interpret this mechanism or a lower queue count as complete scope migration.

### Exact raw quote links for dimension reviews (2026-09-30)

For an older profile without embedded source quotes, a dimension-only review may
provide `quote_source` with `path`, `sha256` and a JSON-pointer `locator`. The path
and hash must equal the pinned profile source; the locator must be that exact
source location or a descendant, and resolve to the review's exact string quote.
A sibling slot, parent context, different file/hash or invented quote is rejected.
The profile fingerprint and source hash remain mandatory. Whole-use exclusions
still require the existing profile quote; this mechanism cannot exclude an item,
source occurrence, market/stat/socket/report obligation or item-bank requirement.
Uber-use reviews cite the cached variant purpose or explicit boss setup section
and discharge only their additional leveling walkthrough obligation. Named-item
leveling tiers and separately sourced exceptional-leveling uses remain in scope.

## Scope membership manifest verification (2026-09-30)

`pricing/data/appraisal-value-scope-manifest.json` records every current identity,
base-quality row, reviewed-profile quality, semantic configuration, source
occurrence, saved capture and other coverage-evidence row. Generate it with `uv run --offline python -m
pricing.knowledge.assessment.maintenance.completion --write-scope-manifest`, then
run completion normally to verify the stored artifact against current inputs.
The generator consumes already validated scope exclusions; it does not create
new exclusions from age, absent guide endorsement or missing value evidence.
Mixed configurations remain retained unless every constituent use is excluded.

The migration gate requires both the explicit completed review state and exact
manifest agreement. A `migration_status: complete` flag alone cannot pass it.
Generating or verifying membership does not approve migration, close source
reviews, prove item-bank coverage or establish assessment/price completion.
Retained unknown-demand leads keep their outstanding obligations. Membership
changes invalidate scope-bound completion evidence. The current migration review
remains partial until its remaining classification and item-bank work is settled.

### Containing variant purpose links (2026-09-30)

A dimension-only review for a player/mercenary equipment location may use
`variant_context` to identify its actual containing variant and `quote_source`
to quote that variant's exact `purpose`. This is limited to the canonical
`wp-a-builds.json` and build-specific `wp-a-variants/<build>.json` layouts.
The build, variant index/name, source hash, profile fingerprint and existing
equipment location must agree; another variant, an arbitrary parent, a sibling
item quote or an invented slot cannot supply this evidence. This records context
for an explicit semantic review; a variant label alone creates no exclusion.
It can discharge only the additional use-quality leveling dimension, never a
whole use, item identity, named/exceptional-leveling review, or other obligation.


### Seasonal conflict scope integration (2026-09-30)

Completion now verifies the seasonal audit against both current native tables,
adds each difference as a retained `definition_conflict` manifest member and a
`seasonal_definition:<table_key>` source-review task, and binds the audit into
final scope fingerprints. A real definition inventory without the audit is
blocked; omitted, forged or stale audit rows fail validation. Audit status and
aggregate complete flags cannot certify resolution. The 15 known differences
remain pending Non-Ladder correctness work, including six mode-eligibility
changes. This adds no Ladder demand/pricing scope and makes no transfer claim.
Resolving these tasks still requires reviewed runtime version/mode selection,
comparison and report evidence; creating the audit is not such evidence.

### Exact generic recommendation evidence reviews (2026-09-30)

`value_scope_reviews.json` may contain `evidence` reviews for an exact imported
`leveling_pattern` without named/candidate identity links. Each review pins the
complete matrix row, original generic-pattern source hash and locator, exact
context quote, review date and specific generic-leveling reason. Completion
validates the imported fields against that source before excluding the evidence
row; the manifest retains it with its exclusion disposition. No item identity,
source occurrence, profile, configuration, socket mechanic or separately valuable
or exceptional-leveling recommendation inherits that exclusion. Stale inputs,
changed targets and unreviewed sibling recommendations remain rejected or pending.

### Reviewed ordinary starter variants (2026-09-30)

`value_scope_reviews.json` may contain `variants` reviews of one guide variant each
(`maintenance/starter_scope.py`). A row quotes the variant's exact `purpose` from
`wp-a-variants/<build>.json`, pins the same variant in `wp-a-builds.json`, pins the
build's guide HTML and lists planner profiles for that variant. Each planner must be
linked from that guide, carry the reviewed title and hold a profile with the variant's
exact name; a planner titled for another build is not listed. Hashes, locators and
dates are verified; a label alone excludes nothing.

It excludes only source occurrences under those anchors that no other review has
claimed and that carry no retained source rule. Item identities, uses, configurations,
trade tiers, exceptional-leveling reviews, pricing, reports and item-bank obligations
are untouched. The first pass (21 variants, 39 planner profiles) retained Smite
Starter (minimum Uber gear), Holy Bolt Starter (specialised mercenary aura setup),
every Budget variant and shared planners without a guide variant.

### User-approved dormant planner definitions (2026-09-30)

The user approved excluding maxroll planner item definitions that no planner profile
places and no guide links (`planner_definitions` in `value_scope_reviews.json`,
`maintenance/planner_definition_scope.py`). Only an unclaimed "Unreferenced
definitions" occurrence whose root `/items/<id>` is an `unreachable_candidates` entry
of a planner report without issues qualifies, from an audit pinned to the current
inventory with no guide or source issues. The audit no longer blanks every planner
because one planner is missing or unsupported: guide references are keyed by planner
id, so that gap stays its own. Reachable definitions, planners with issues and every
item identity and downstream obligation stay in scope.

## Valuable copies and modifier combinations (2026-10-02)

A better owned copy is not a keep limit. Keep every independently valuable item;
charms can occupy multiple inventory cells and jewels are used across socket
setups. Owned comparison must remain informational and may not suppress trade
qualification, a supported price, or a useful multi-copy configuration.

Evaluate combinations rather than a mean roll percentage or isolated T1 label.
Explicitly cover life + maximum damage + attack rating charms across their native
sizes, skill/life and resistance/life charms, and useful multi-modifier jewels.
Verify native legal ranges, interacting affixes, missing decisive stats, relevant
uses and scoped evidence; distinguish build demand from actual trade qualification.
Test positive, near-miss and unknown combinations with better/equal owned copies.
Do not classify every T1 jewel or all charms as valuable merely to avoid a miss.


## Resale outcome and shared combinations (2026-10-03)

The user clarified that the main output is valuable-to-trade items with sufficient
liquidity, and requested shared assessments combining good stat patterns with
collections of suitable bases. Follow DELIVERY_APPROACH.md for the revised execution
architecture. Reuse family/combination rules with explicit membership and exceptions;
individual handlers or duplicated build-specific rules are not completion goals.

Preserve the all-item scope, universal baseline tiers and exceptional leveling
requirements. Main report priority is the specimen's resale recommendation, not
exhaustive build utility. Keep numerical price, trade qualification and liquidity
separate. Asking listings and guide mentions alone do not prove turnover. Unknown
liquidity remains unknown; high asks cannot establish an easy sale. A final coverage
claim must include the reviewed liquidity disposition and supporting evidence kind,
including honest insufficiency where no defensible liquidity claim is possible.
This clarification does not authorize new live collection or relax final gates.


The user subsequently selected **broad demand and reasonable selling effort;
mark niche items separately**, and explicitly asked to separate actually sellable
items from nice/self-use items. This is the default resale policy, not a pending
question. Do not impose a strict staples-only or slow-high-value default.
