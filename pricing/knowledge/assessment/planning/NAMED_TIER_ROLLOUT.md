# Universal unique/set tiers — mandatory completion gate

**Execution update2026-09-26:** Phase1 tier gate is published and verified in
`39ee03c46fb5d42f6ab70d1b8a5484e80d23ce87113478f660c82174bdc6cfe9`.
408uniques,140set pieces,35sets,2958rendered cases; all gate counters zero.
The pause/checkpoint below is historical and superseded. Phase2 is active; follow
the complete remaining queue. Validation and exact limits are in the newest handoff.

Updated 2026-09-26 at the user's request after another Guardian Angel scan had no
trade tier. **Tier coverage is incomplete. Pause unrelated build/stat/base/market
handler work until the gate below passes.** This supersedes earlier declarations
that the 548-policy inventory completed baseline tiering.

## Confirmed failure and corrected objective

Latest capture: `inventory_tracking/runs/alt-d/20260926T102641Z-b5aa4b20/latest.json`,
Guardian Angel, nonethereal, `trade_tier.status=pending_review`, `tier=null`.
Its existing policy only covers original-base ethereal200%ED specimens. That is a
premium rule, not a baseline. Preserving the original93 conditional policies while
adding455 others left ordinary variants uncovered. Socketed Shako had the same
structural problem: an empty-socket condition suppressed the entire tier.

A policy row, an assigned default behind a restrictive predicate, or zero unexplained
identity-inventory entries does NOT establish runtime tier coverage.

Required outcome:

- Every eligible unique identity has a visible trade tier.
- Every eligible set piece has its own visible trade tier.
- Every eligible complete set has a separate trade tier and documented component
  relationships; a valuable set does not make every component equally valuable.
- Valuable leveling items and set combinations have separate leveling tiers.
- Trade labels: **high, mid, low, trash**. High green, mid yellow, low blue, trash red;
  use the same colors for leveling. Existing internal `med` may remain compatible,
  but the user-facing label should be `mid`.
- Ordinary, low-roll, ethereal/nonethereal, socketed and upgraded variants cannot
  lose their baseline merely because a premium or build-fit condition fails.

Scope: SC / Non-Ladder / PC / RotW. Qualitative trade tiers are separate from numeric
Ist estimates. Missing comparable listings cannot remove a tier or imply trash.

## Step 1 — Establish the full denominator

Inventory the complete native unique, set-piece and parent-set catalogs, joined to
all gathered build guides and native definitions. Current starting counts are
565 named identities,548 policy rows and35 native set records; these are audit
inputs, not completion counts. Validate parent-set membership and native variants.

Keep quest, disabled and unfinished/non-droppable records visible with precise native
eligibility evidence. Report eligible, excluded and unresolved counts separately;
never make the denominator smaller by dropping an inconvenient item or unknown use.
Availability uncertainty remains explicit. No ordinary item may be excluded because
it lacks a guide mention or market observation.

Deliverable: a deterministic census with separate rows for unique, set piece and
complete set; baseline status, trade tier, leveling-review status, evidence and
remaining variant questions. Replace the current policy-presence completion metric.

## Step 2 — Scan all build evidence before assigning the final list

Use the gathered guide corpus and occurrence ledger, not just already implemented
profiles or the most popular builds. Account for every build, variant, progression
stage, player/mercenary side, main/swap slot, prebuff item and explicit alternative.
Include specialist/Ubers, budget, leveling and partial/full-set setups. Record
Hardcore-only uses separately rather than silently endorsing them for Softcore.

For every named item/set collect:

- Builds and exact variants using it; beneficiary, slot and role.
- Whether preferred, an alternative, a leveling stopgap or a required combination.
- What properties matter, relevant rolls, ethereal preference and socket payloads.
- Set companions and piece-count thresholds; standalone versus combination utility.
- Cached valuable-item lists and correctly scoped market evidence where available.

Deduplicate repeated planner/text occurrences. Review contradictory sources and
unresolved aliases explicitly. Absence from a guide is not evidence of trash. This
scan is tier research; do not resume unrelated detailed stat handlers as a substitute.

## Step 3 — Assign a reviewed baseline to every eligible entry

Review sets as complete families, assigning both the full-set tier and each piece's
tier. Then review uniques by equipment/utility family, including items absent from
popular guides. Prioritize valuable and specialist uses, but finish the entire list.

Each baseline must have a dated rationale and traceable evidence. Use high/mid/low/
trash consistently for trading usefulness; do not equate build popularity or a
historical ladder grade with current Non-Ladder market prices. Trash requires a
positive review of the item's role and alternatives, not a cache miss.

Review all original93 policies first for premium-only applicability, including
Guardian Angel, Shaftstop, Crown of Thieves and Duriel's Shell. Also audit socketed
versions of otherwise fixed-tier items such as Stormshield and Naj's Puzzler. Retain
valid premium evidence, but do not preserve missing-baseline behavior.

## Step 4 — Separate baseline, variant adjustments and exact price

Implementation responsibilities stay together under `assessment/policies/`:

1. Baseline lookup by verified canonical identity returns a reviewed tier, independent
   of successful premium-roll matching, market availability or current build fit.
2. Variant rules refine that baseline using rolls, ethereal status, native definition
   variant, upgrades and sockets. A false premium predicate retains the baseline.
   Unknown premium facts retain a visible baseline and mark only the premium unknown.
3. Socket contributions must not masquerade as intrinsic rolls. If separation is
   unavailable, retain the underlying-item baseline and withhold the unsupported
   premium. Do not include a valuable filler in an unqualified base-item tier.
4. Exact-price contracts remain independent and strict. No baseline or source-derived
   tier creates an Ist price or relaxes seller/scope/variant matching.

Keep provenance for both baseline and applied adjustment. Validate duplicate/missing
identities and contradictory overrides. Reuse the existing predicate/runtime machinery;
add only the separation needed to prevent a failed premium rule from returning no tier.

Complete-set assessment uses a parent-set identity and component relationship data;
it must not claim the player owns the set from scanning one piece. The single-piece
report can expose relevant set-combination utility without presenting full-set value
as the price/tier of that piece.

## Step 5 — Complete valuable leveling coverage

Audit each entry for leveling usefulness separately from trade value. Add high/mid/
low leveling tiers for desirable items; retain class/archetype, equip level/Strength,
stage, mercenary suitability and required set companions. A trade-trash item may
still have a valuable leveling role and must be highlighted accordingly.

Every entry needs a reviewed leveling disposition: recommendation, conditional
combination or no specific leveling recommendation with rationale. An absent row
must not silently mean the review was completed. Do not display redundant negative
leveling boilerplate for items with no leveling recommendation.

## Step 6 — Red/green tests proving rendered coverage

Start with the latest Guardian Angel capture as a failing end-to-end regression.
Also replay socketed Shako and Griswold's Heart. Assert a visible trade tier in the
actual terminal and OSD document, not merely a policy's existence.

Generate valid census cases from native definitions, including each same-name native
variant. Exercise ordinary minimum/maximum rolls, legal ethereal states, unsocketed,
empty/filled sockets, legal upgrades and random skill/element variants. Test unknown
premium facts separately: they must not hide the known identity baseline. Invalid or
unidentified identity evidence still must not fabricate an item tier.

Preserve premium boundary tests and intrinsic/socket distinction. Check full-set and
piece independence, leveling-only value, matching colors and `mid` display. Compare
existing saved numerical prices before/after to catch unintended pricing changes.

Required machine-readable gates:

- Eligible uniques missing a reviewed baseline: **0**.
- Eligible set pieces missing a reviewed baseline: **0**.
- Eligible complete sets missing a reviewed baseline: **0**.
- Valid generated/captured items rendering no trade tier: **0**.
- Unreviewed leveling dispositions: **0**; known valuable leveling items omitted: **0**.
- Unaccounted gathered build/variant/mercenary/alternative evidence: **0**, with genuine
  source ambiguities separately enumerated rather than silently promoted to reviewed.

## Step 7 — Publish and verify before resuming anything else

Run affected tests and the full suite, rebuild the coverage report and atomically
publish. Replay through the selected publication, including Guardian Angel, Shako
and Griswold. Report denominator, exclusions and gate results explicitly. A successful
publication or a policy-count census alone cannot satisfy this gate.

**Only after these checks demonstrate a tier on EVERY eligible unique, set piece and
complete set may the remaining detailed build/stat/base handlers resume.** The previous
batch cadence is suspended. Numeric market gaps remain separate and do not block a
qualitative tier, nor justify inventing one without review.

## Paused work checkpoint

Latest selected publication: `c99da49b9295c5d23ed3687dc4d6ac52f0c8a2337eb0ae153acdf9197510e613`
(Enigma/Raven Frost/Sigon batch). Hoto11roles, Griffon14roles, Rhyme14new+1updated
role and the Colossal Jewel socket-matcher correction are in the working tree;
757profiles/749stat configurations have been rebuilt locally. Their new targeted
checks passed, but the combined bundle has NOT been published. Preserve this work;
do not claim it shipped or continue it ahead of universal tiering. Guardian Angel's
missing tier has been diagnosed, not fixed by this planning update.
