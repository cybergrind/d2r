> **FROZEN 2026-10-03 (user decision).** This document no longer drives work: its gates, queues and
> stopping rules are suspended. The active plan is [PLAN.md](PLAN.md). Kept as technical reference only.

# Item-by-item trade qualification

Requested 2026-10-01. Runtime policies cover 40 named identities, with explicit
variant/roll limits (including the separate Shako underlying-item handler); see the dated item findings below and in ROLL_VALUE_FINDINGS.md.
Published report reviews certify only identities whose full native boundary
coverage passes the selected-generation receipt checks. Fixed named jewelry, independent integer-roll jewelry, Grand Charms and explicitly
scoped Colossal Jewels have completion adapters. Narrow native-defense scopes also
cover Horazon’s Legacy and Trang-Oul’s Girth, including shifted mana for Girth. An explicit compound Colossal Jewel
scope verifies paired enhanced damage; a narrow fixed-affix original Pillar armor scope is also implemented. Other compound/family adapters remain pending. A runtime rule does not by itself
establish completion for every variant or prove a numerical market price.
Scope: Softcore / Non-Ladder / PC / RotW. This extends the completion contract;
it does not certify existing tiers or introduce new market prices.

## Required output

Keep three independent conclusions: build usefulness, qualification as a trade
candidate, and supported price. Trade qualification is one of `candidate`,
`premium`, `use_only`, or `unresolved`. `use_only` requires a reviewed reason that
the item misses the relevant trading conditions; a cache miss alone cannot imply
it. None of these labels promises a sale. Keep high/mid/low/trash tiers, but do not
derive trade qualification directly from the tier or number of build mentions.

Show one concise item-specific reason, for example a material roll/combo that
qualifies it or a missing condition. Describe a better dropped variant as a target,
not an upgrade the player can apply to immutable rolls. Distinguish repairable
socket preparation from innate deficiencies. Avoid generic disclaimers.

## Review procedure and architecture

1. Build the review queue from the union of named tiers/watchlists, scoped build
   configurations, market evidence and unresolved valuable-item leads. Review each
   valuable unique, each valuable set piece and relevant set combination separately.
   Preserve low/trash identities in the census; an evidence-backed family disposition
   may close ordinary items, but cannot hide a valuable exceptional variant.
2. For each identity, inspect native ranges and existing role/stat rules. Classify
   each variable stat as required, trade-driving, secondary, or irrelevant to the
   particular trading use. Capture interactions, alternate acceptable combinations,
   ethereal benefits/durability penalties, upgrades, sockets and intrinsic rolls
   separately from inserted jewels/runes and equipped set bonuses.
3. Review cached scoped asks/fills and demand separately. Establish minimum useful,
   ordinary trading and premium conditions where supported. Historical aggregates
   and mixed-mode sales are research leads only. A source saying "perfect is
   premium" does not prove every nonperfect item unsellable. Do not invent a global
   top-20% cutoff or a universal minimum Ist value.
4. Extend the existing assessment policy layer with explicit reviewed trade rules;
   reuse its predicates, native stat keys and tri-state evaluation. Store per-item
   records under `rules/`, with identity/configuration, source hashes/locators/dates,
   material stats, validity predicates, ordinary/premium predicates, rationale and
   review status. Separate rules for alternative uses must not be flattened into
   one AND or a count of good stats. Evaluate independently from gear suitability.
5. Carry the result through the existing assessment domain and appraisal formatter.
   Missing required facts produce `unresolved`; known failure of one use does not
   suppress another qualifying use. Numeric estimates continue to require exact
   supported comparisons. A high ask alone does not establish premium demand.
6. Use red/green item-bank tests through decoding, appraisal and rendering: lowest
   and highest legal rolls; just below/at/above each threshold; mixed good/bad rolls;
   perfect irrelevant stat; ethereal/nonethereal/unknown; native/upgraded/socketed
   variants; missing decisive stat; companion/context conditions. Explicitly test
   items that remain trade candidates even at minimum rolls. Reuse fixtures where
   suitable, but author expected conclusions from reviewed evidence.
7. Add machine-checked coverage obligations for each review and its rule/tests/report
   evidence. Invalidate review receipts on relevant source/rule changes. Migrate the
   scope manifest and completion gate before claiming full coverage. The new
   `trade_qualification` dimension now defaults to pending and legacy matrices
   cannot omit it. The fixed-named-jewelry adapter now requires declared native
case contracts and a current selected-generation execution receipt; other scopes
remain pending. Publish and replay
   only after affected tests and artifact validation pass. Continue across batches.

## Initial review order

Start with the existing roll policies rather than declaring them correct. First
War Traveler, Raven Frost, Skin of the Vipermagi, Titan's Revenge, Harlequin Crest
and Griffon's Eye, then every remaining valuable unique/set in the derived queue.
This is a starting order, not the full denominator or a stopping milestone.

Initial inspection found cached WP-I notes distinguish War Traveler MF segments,
Raven Frost dexterity/AR combinations and Vipermagi resistance segments. Existing
policies express some of those tiers. These notes also contain explicitly mixed
Ladder/Hardcore diablo2.io sales and lack sufficient per-row scope/variant proof
in the aggregate. Reuse scope-verified normalized records; do not promote those
aggregate notes into fresh SC/NL sale evidence. Secondary rolls still need review.

After named items, review bases/completed runewords, charms/jewels, then magic,
rare and crafted families. For bases include actual empty sockets and legal socket
outcomes, ethereal status, ED/defense and staffmod/inherent combinations. For
affixed items include required skill/FCR/IAS/socket and defensive/utility combinations
and competing available items. For charms/jewels require meaningful combinations
and overall eligible tiers; a perfect low affix tier is not automatically valuable.
Build breakpoints are loadout constraints unless evidence makes them item-level
requirements. No generic leveling expansion is part of this priority.

Initial evidence inspection: [ROLL_VALUE_FINDINGS.md](ROLL_VALUE_FINDINGS.md).
The census is research evidence, not a passing qualification review.

## Maintenance adapter requirements and implemented scope

The coverage dimension must not remain permanently pending after a review has
actually been validated. Add a focused trade-review maintenance adapter instead
of inferring review completion from named tier status:

1. Read the selected generation’s qualification rules and validate their existing
   source, native mapping, identity, mode, date, independent-seller and ordered-band
   membership checks. Working-tree rules alone cannot certify a published report.
2. Bind each review to explicit native item-bank case IDs and execution receipts,
   pinned to the same generation and relevant source/rule inputs. Collection or
   passing policy tests alone does not establish executed report coverage.
3. Match identity and variant scope precisely. A reviewed identity cannot blindly
   close every build/configuration row; unsupported Titan variants must retain
   open obligations. Fixed-stat jewelry requires legal-variant/identity coverage,
   not fabricated random-roll boundary cases.
4. Close only supported dimensions/rows. Missing receipts, failed cases, mismatched
   generation, changed predicates/source, uncovered material combinations or
   unresolved evidence keep the obligation pending with a specific reason.
5. Test the negative paths before integration into coverage_matrix/completion.
   Preserve denominator/exclusions; rerun scope consistency rather than manually
   marking rows complete. Report which reviews are closed and which remain open.

Implemented in maintenance/trade_reviews.py for exact fixed named-jewelry
identities only. It verifies policy/definition fingerprints, explicit native inputs,
all legal/impossible/unknown variant cases, verdict/material-stat assertions and
exact rendered text/color. Completion revalidates accepted receipts and rejects
unattested reviewed trade rows. An identity review cannot close a build-use row,
market pricing, all-stat reporting, or a variable/conditional trade rule.

Validation checkpoint (2026-10-02, before the unsocketed-capture decoder fix): the registry
`rules/trade_qualification_reviews.json` contains 43 identities and 2,177 required
published-report cases. The rerun passed all 2,177 cases in 995.54 seconds, with
`sources_unchanged=true`, against selected generation
`cac7fa207f519b341cb6bde9d1a045da5642fb7df9f81b0a2802f0bee0271142`.
All 43 reviews passed source/generation/native-contract validation; the actual
receipt was installed at the five accepted registry paths. Evidence:
`pricing/data/appraisal-registered-trade-refresh-2026-10-02.json` and
`pricing/data/report-receipts/registered-trade-reviews.json`.
Coverage recorded all43 accepted trade reviews. Subsequent decoder/test changes
invalidate those receipts for current-source certification; retain the actual past
execution and rerun consolidated verification after implementation settles. Earlier failed/stale runs are
historical and were not rebound. All-item completion remains unproven.

Refresh after relevant inputs change by executing the union of registry `cases`
through `test_appraisal.py::test_constructed_item_through_published_appraisal[<case-id>]`
with an item-bank receipt. Validate generation, source stability and every registered
contract before installing accepted receipt references. Passing tests with changed
inputs must be rerun, not hash-rebound. Continue item-specific roll reviews while
preserving unverified obligations.

Scalar jewelry review uses native roll limits and every predicate threshold
(below/at/above), with joint combinations across independent material rolls.
Each missing/illegal component is exercised with the other components at known
maximums, plus identified/ethereal/socket/content variant boundaries. Exact
qualification and rendered text/color contracts must pass in the selected
generation. BK has12 cases; Raven28, including perfect Dexterity alone, perfect
AR alone and double-perfect. This is not a price, liquidity, build-use or all-stat
report attestation. Shifted/encoded/parameterized, correlated or compound rolls,
and unresolved legal branches require separate review rather than this adapter.

2026-10-01 Sandstorm Trek: reviewed explicit ethereal15/15 premium and other
ethereal ordinary asking segments, requiring all four variable rolls. Removed
unconditional nonethereal15/15 premium promotion.36 native report cases added;
nonethereal/further roll refinements and identity-wide trade closure remain open.

2026-10-01: Highlord fixed-stat candidate rule added with8 native report cases.
Wisp qualification remains open: cached flat absorb689 is not verified percent
absorb1866. Atma qualification remains open: scoped observations lack dates.
Neither unresolved source gap was silently converted into a demand verdict.

2026-10-01 Gheed: reviewed40MF premium segment and lower-MF ordinary segment,
requiring all three legal rolls. Removed unsupported38-39 high promotion and
excluded an impossible45MF listing.31 native report cases added. Collector
premiums tied to gold/discount remain open; no identity-wide completion review.

2026-10-01 Nagelring:30MF ordinary/low candidate with both native rolls verified;
no separate75AR premium (only2 sellers), lower-MF demand unresolved.21 native
report cases added. Identity-wide trade review remains open.

2026-10-01 Dwarf Star15MDR ordinary/low and Metalgrid supported-cohort ordinary/
mid qualification added. Metalgrid native shared-resistance integrity enforced.
13+46 native report cases; lower Dwarf and joint-perfect Metalgrid remain open.

2026-10-01 Girth: explicit total-defense representation and134-166 report range;
50mana premium/mid versus lower ordinary/low on complete verified captures.
Mixed bonus/total listing fields are rejected.29 native bank cases; collector
bonus-defense pricing and identity-wide trade closure remain open.

2026-10-01 continuation: original Trang Claws and original Tal15MF belt now have
source-backed ordinary-candidate policies. Evidence-only native total-defense
inference expands original cohorts without mutating cached source fields. No
upgrade/collector premium or lower-MF worthlessness claim; identity completion
remains open. See ROLL_VALUE_FINDINGS.md for cohort counts and excluded variants.

2026-10-01 continuation: Sling's3 independent variable rolls now have ordinary
3–4 magic-pierce versus premium5 qualification, backed by complete matched asks.
The scalar identity review includes42 native cases and the narrowly verified
plain item Energy representation. Completion is subject to the selected published
receipt, not the existence of authored cases. Numeric price matching unchanged.

2026-10-01 continuation: Entropy Locket uses the reviewed any-roll demand cohort
for ordinary candidacy, with allfive native rolls verified. No premium inferred
from perfect values or an arbitrary cutoff from the minimum observed listing.
Scalar completion requires264 independently authored native report cases and a
valid published receipt. Price comparisons remain unchanged.

2026-10-01 continuation: Opalvein now has separate source-backed elemental
qualification while preserving its native single-choice property group. Physical,
magic and poison variants remain unreviewed for qualification; they retain valid
existing identity tiers. No identity-wide completion claim: a property-group
completion adapter and the remaining subtype evidence are still outstanding.

2026-10-01 continuation: Defender's Fire has a separately evidenced10/10core
premium, with all secondary rolls verified. Native Colossal Jewels now have an
explicit completion scope sharing integer partition proofs with jewelry but not
borrowing its base-family authorization. Publication/execution evidence is the
completion gate; authored cases alone do not certify the identity.

2026-10-01 continuation: Protector's Stone now has ordinary qualification with
all five native rolls verified, including equal ED17/18. A narrow compound
Colossal Jewel completion adapter proves58 report cases. Gheed's existing
31 cases now use a separately scoped Grand Charm review; native MF threshold
39/40 and both secondary roll boundaries remain mandatory. No changed Gheed
pricing/tier rule or new secondary-stat premium. Both require a current published
execution receipt before coverage acceptance.

2026-10-01 continuation: Flame Rift and Crack of the Heavens have ordinary
qualification across legal -90..-70 penalties. Original catalog-bound Sunder
magnitudes use the existing signed projection; capture values are never negated.
Their tier variant guards now reject impossible ethereal/socketed charms.
Grand Charm scalar completion reviews require28 native report cases and a
current selected-generation receipt. Perfect-penalty premiums are not inferred.

2026-10-01 continuation: Horazon's Legacy has ordinary qualification with all
three affixes and unmodified native base defense verified. A narrow original
elite set-boot review scope includes complete-capture and contribution guards;
41 native report cases support it. The report shows59–68 defense. Missing
defense cannot erase the separate broad item tier. No new exact-price rule or
perfect-affix/defense premium. Published receipts remain mandatory for closure.

2026-10-01 continuation: Trang-Oul’s Girth has an explicit total-defense-set-belt
completion adapter. Native base59–66 plus flat75–100 yields total134–166;
raw mana uses shift8 and is compared in decoded25–50 units. The existing
ordinary vs50mana premium policy is unchanged. Thirty native report cases
include malformed fractional mana, conditional cold resistance, incomplete
captures and extra defense contributors. Generic scalar scopes still reject
shifted or aggregate axes. Review acceptance requires the selected execution
receipt; no collector-defense premium or numerical price is inferred.

2026-10-01 Metalgrid correction: joint450AR/35allres no longer loses ordinary
candidacy or its medium refinement solely because its premium-price bucket
lacks priced sellers. This is an explicit item-specific beneficial-roll inference
from established demand; it is not a newly observed priced cohort. Seven dated
complete scoped sellers and the original source hashes remain unchanged.
No premium classification or numeric estimate is inferred. A complete perfect
native item, including charges, explicitly retains unavailable price/no matches.

New compound_named_jewelry scope verifies native shared res-all identity, equal
limits and all four member metadata, missing/outside/unequal components and joint
AR/defense/resistance endpoints. ED Colossal Jewels keep their separate scope.
Seventeen registry reviews require the shared selected-generation receipt; the
47 Metalgrid report cases and47 resistance review checks are not themselves a
claim that all named or all-item work is complete.

## Current evidence inventory — 2026-10-01

`pricing/data/appraisal-named-trade-evidence-inventory-2026-10-01.json` records
all548 named policies, dated scoped single-item asking observations, independent
sellers and explicit variant-field gaps. It pins the market, policy and review
registry hashes. Counts combine rolls/variants and are research triage only:
they do not prove a comparable cohort, valid native stats, demand or completion.
The current30 runtime rules and22 registered report reviews remain distinct.
Historical dated paragraphs above record prior states; the current rules and
validated selected-generation receipts govern runtime/completion.

Priority unique review found these dated single-item asking samples:

| Item | Rows | Sellers with all variant fields explicit | Key gap |
|---|---:|---:|---|
| War Traveler |56|1|55 rows omit ethereal status; the sole explicit specimen is ethereal.|
| Skin of the Vipermagi |28|0|Ethereal, base, sockets or contents missing.|
| Griffon's Eye |68|0|Ethereal/socket fields incomplete; some listings contain jewels.|
| Harlequin Crest |40|0|Every row omits ethereal;39 omit sockets/contents.|

Do not infer nonethereal/unsocketed from omitted listing selectors. These gaps
cannot be repaired by pooling defense, MF or elemental-roll bands. Deterministic
native-defense inference is a possible separate implementation only with a proof
that variants cannot overlap; it cannot establish missing socket contents or
separate inserted modifiers. War Traveler has only three rows with explicit total
defense, including one upgraded specimen; this is not a ready ordinary-vs-premium
cohort. Shako's frequent Defense399 entries are not automatically total1855.

Dwarf Star follow-up is documented in
`pricing/data/appraisal-dwarf-trade-review-2026-10-01.md`: the earlier15MDR rule
is withdrawn, and the13/15 union does not establish a meaningful cutoff.
No new qualification or premium is inferred from the evidence inventory.

Next implementation candidates with explicit set variants include Immortal King's
Pillar (8 rows/7 sellers), Forge (5/5), and Detail (5/4). Review useful demand,
native properties, asking magnitude and complete variant/roll cohorts before
assigning a verdict; baseline trash/low does not settle that decision. Ordinary
starter expansion remains out of scope. Unresolved priority uniques remain in
the queue rather than being silently marked completed or worthless.

## Immortal King component review — 2026-10-01

Pillar now has original-base ordinary qualification from four independent dated
single-item SC/NL/PC/RotW sellers. All standalone affixes are fixed; base defense
and conditional set bonuses do not establish a premium. Explicit original base,
nonethereal status and empty/no sockets are required. Existing baseline tier and
exact-price matcher are unchanged. Two contradictory flat/total-defense listings
were excluded without rewriting observations. Forge and Detail have only two
original-base sellers each after separating upgrades, so remain unresolved.

Research: `pricing/data/appraisal-ik-component-trade-review-2026-10-01.md`.
11 policy cases ran red then green;11 staged native report cases passed. Native
report execution for Pillar does not yet establish an identity-wide maintenance
review: fixed-affix armor/base-defense and set-context coverage must be proved
before extending the adapter. The22 registered reviews remain separate.

## Fixed-affix set armor attestation — 2026-10-01

The `fixed_set_armor` maintenance scope now has an explicit Pillar native proof:
original War Boots, fixed standalone affixes and fixed conditional set properties,
unshifted native defense and verified elite upgrade identity. It rejects changed
roll mappings, variable or new properties, missing variant/base guards and new
premium rules. It does not borrow the fixed-jewelry proof for armor.

Twelve Pillar report contracts include original118/128 defense,278/288 with the
conditional160 defense bonus, the upgraded base, and identification/ethereal/
socket/content boundaries. All required cases must execute for the selected
generation with exact verdict/text/color assertions. Each missing endpoint or
variant leaves the review pending. Foreign bases remain rejected even if a case
fingerprint is rebound. Upgraded demand, full/partial set usefulness and exact
prices remain separate obligations.

Registry now has23 authored reviews; receipt validation determines acceptance.
Focused proof tests first rejected the absent adapter; three additional negative
cases reproduced unchecked mappings/guards/types before those gaps were fixed.
277 maintenance regressions and12 staged native cases passed. Publication and
final execution evidence must still be checked before claiming closure.

Final fixed-armor validation:970 published report cases passed, all23 reviews
accepted. The selected runtime generation remains36919a2341e1096557a21a82fc6f17acafceada60b8b82fca9d6a3c41f44fca8;
maintenance-only code/registry changes do not create a new runtime artifact hash.
The final matrix marks original Pillar trade qualification reviewed; overall
completion remains false with110690 required obligations,8326 trade qualifications.
`add func=2` is explicitly required; absent/0/1/boolean/float modes are rejected.
Next source-backed import issue: unconditional extra properties on Claws and
Civerb Cudgel; see the dated research note in pricing/data.


## Crown of Ages evidence review — 2026-10-02

Reviewed the current cached single-item asks individually: 43 dated SC/NL/PC/RotW
observations from 31 sellers. None establishes empty sockets: 33 have unknown
contents and 10 contain jewels or runes. Those ten are not ten clean native-roll
comparables. Ber-filled examples report both native-looking and total damage
reduction; some enhanced-defense fields contradict the fixed native 50% modifier.
Do not manufacture a two-socket/premium cutoff from that mixture, or label
one-socket variants worthless. The independent native dimensions are one/two
sockets, 10–15% damage reduction, 20–30 all resistance and 100–150 flat defense.

Research artifact: `pricing/data/appraisal-crown-ages-roll-research-2026-10-02.json`.
It pins the market snapshot and lists the observation IDs. Runtime qualification
and prices are unchanged. Next evidence must distinguish empty sockets and native
rolls from inserted modifiers; the existing review remains open.

## Andariel’s Visage evidence review — 2026-10-02

The 45 scoped single-item cached asks contain five fully described variants from
only two independent sellers. All five are ethereal and filled: four with Ral,
one with a generic Jewel. The two Ral examples with 30 strength / 10 life leech
come from the same seller. The Jewel example cannot establish intrinsic rolls
without its modifiers. These samples do not establish an ordinary/premium cutoff
or a three-seller estimate for any cohort. Nonethereal and empty-socket variants
remain separate evidence gaps.

Native ranges are 100–150 enhanced defense, 25–30 strength and 8–10 life leech.
Build requirements also depend on the fixed IAS, fire-resistance penalty, socket
payload and complete mercenary loadout. They are not universal trading thresholds.
See `pricing/data/appraisal-andariel-variant-audit-2026-10-02.json` for source pins,
listing IDs and relevant build profiles. Runtime qualification remains unchanged.

## Windforce evidence review — 2026-10-02

Thirteen dated scoped single-item asks span reported mana leech 6% (two sellers),
7% (five sellers), 8% (five sellers), and one unspecified roll. Twelve omit socket
count/contents; the sole complete variant contains an Ort rune and reports 8%.
Unknown socket payloads prevent treating the reported leech as a proven intrinsic
roll or constructing an empty-socket price cohort. A perfect-only sellability gate
is not established by these observations; low rolls cannot be called worthless.

The sole variable native modifier is 6–8% mana leech. The 250% enhanced damage,
20% IAS and level-scaled maximum damage coefficient are fixed. Numeric pricing and
ordinary/premium qualification remain unresolved pending exact variant evidence
and reviewed physical-bow demand. Evidence and listing IDs:
`pricing/data/appraisal-windforce-variant-audit-2026-10-02.json`.
