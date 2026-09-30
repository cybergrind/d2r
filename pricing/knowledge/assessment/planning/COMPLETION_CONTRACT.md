# All-item assessment: end goal and completion contract

Updated 2026-09-30 at the user's request. **Status: unfinished.**
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
