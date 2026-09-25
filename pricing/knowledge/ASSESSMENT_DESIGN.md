# Build-aware offline item assessment

Design, 2026-09-24. Target economy: Softcore / Non-Ladder / PC / RotW; Ist = 1.
This is the implementation contract for replacing generic nearby-roll valuation.
The first implementation slice is now active; see [implementation status](assessment/README.md).
The broader family/profile rollout below remains the target, not a completeness claim.

The next implementation sequence and exhaustive cached inventory are in
[the offline assessment plan](assessment/planning/IMPLEMENTATION_PLAN.md)
(2026-09-24). Use its delivery gates for the broader rollout.

## Why the current estimator fails

Saved Dread Edge capture:
`inventory_tracking/runs/alt-d/20260923T213532Z-be6ed17d/request-21/report.json`.
The photographed rare Cinquedeas is non-ethereal, unsocketed, with 51% ED,
20% IAS, +2 Eldritch skills, +2 Enhanced Entropy and per-level damage/AR.
The report correctly withheld an item price but printed a 97.0785 Ist median
from four same-base rare listings. Representatives include ethereal 273–300% ED
weapons. That cohort does not establish this item's value. Dates of observation
are unknown; listing update dates and currency snapshot dates are separate facts.

The captured decoder still leaves skill-tab parameter 57, maximum damage per
level, and cold duration unresolved. A complete-looking property dictionary is
therefore not a complete item. Screenshot truth must remain distinct from decoded
memory and inferred facts. Do not infer omitted item properties as zero.

Other structural problems:

- A universal 20% tolerance has no relationship to build breakpoints or trade demand.
- Exact matching of supplied properties permits unexamined extra premium properties.
- Unknown ethereal/socket contents can enter nearby cohorts.
- Same base is too broad for rares, yet too narrow for discovering substitute gear.
- Skill names are mapped through display strings instead of stable semantic IDs.
- Build mentions and whole-character stat priorities are not item-slot requirements.
- Tier/perfect-roll highlights describe modifier rolls, not item usefulness or price.
- Ask availability measures supply; it is not proof of sales, demand or liquidity.

Immediate safeguards implemented: do not print a numerical same-base reference
beside an unpriced item; unresolved stats block both exact and approximate estimates.
The generic nearby matcher has been retired from appraisal. Initial exact contracts
and explicit unsupported-policy gaps replace it; remaining work is listed below.

## Assessment stages and contracts

1. Normalize item facts without losing provenance.
2. Select quality policy, item-family handler and applicable build-role profiles.
3. Evaluate each build profile independently: matched, partial, failed or unknown.
4. Produce a comparable contract for each supported role and value segment.
5. Filter verified NL market observations against that contract.
6. Summarize eligible evidence; emit utility and price conclusions separately.

One item can have several roles. Never sum scores across unrelated builds or pool
all role-specific cohorts. Unsupported families fall back to explicit review with
no invented price. Market matching does not require a guide mention when exact
variant evidence is independently adequate; absence from guides is not rejection.

### ItemFacts

Keep identity (base code, item type hierarchy, named/runeword identity), rarity,
base tier, requirements/item level, identification state, ethereal tri-state,
total/filled/empty sockets and actual contents. Include original/upgraded base,
superior modifiers, durability/replenish/repair/indestructibility when relevant.

Stats use native stat ID plus parameter/skill ID, unit, raw value and normalized
value. Keep affix/staffmod/inherent/socket/set origins separate where proven;
otherwise mark aggregate. Per-level modifiers store coefficient and reference
level, not merely the viewer's rendered number. Comparison must not depend on
which character hovered the item. Skill/tab/class/charge/proc identities are distinct.

Every fact has observed/derived/unknown status and source. Handler-required facts
must be complete; lack of an unresolved row does not prove capture completeness.
Display text and Traderie IDs are adapters, never the semantic model.

### BuildProfile

Store build ID, class, variant, player/mercenary side, slot, role (damage, caster,
prebuff, swap, leveling, PvP), stage and level bracket, game-version applicability,
source URL/path/date/hash and precise planner/profile/section locator.

Each profile has:

- Allowed item families, qualities, named alternatives and legal equip constraints.
- Required predicates and required stat combinations; all/any groups are explicit.
- Important rolls and role-specific ordering; optional utility and irrelevant stats.
- Breakpoint dependencies, including gear outside this item. Without a loadout,
  report potential contribution rather than claiming a breakpoint is reached.
- Ethereal policy with reason, repair/replenish exceptions and socket/content rules.
- Known alternatives and opportunity cost, supported by the same build variant.
- Reviewed status: discovery-only, extracted candidate, or reviewed executable rule.

A source's whole-build '+skills/FCR/life/resists' paragraph must not become required
ring affixes. Generic slot mentions are discovery only. Endgame and starter needs
stay separate; hardcore/ladder guide context cannot silently become NL evidence.
Ladder-origin mechanics may inform utility only after version/availability review;
market evidence must always meet the actual economy filter.

### Handler composition

Use a small strategy registry rather than one class per base or one giant switch:
`quality policy × item-family handler × build-role profile`.
The registry resolves from verified item type ancestry, with explicit priority and
ambiguity errors. Named/runeword quality policies override generic affix pricing.
Family mechanics remain reusable across normal/magic/rare/crafted items.

| Family/policy | Deciding facets and mechanics |
| --- | --- |
| Runeword bases | Recipe-compatible base, real empty sockets, socket potential and method/ilvl, ethereal role, superior ED/defense, inherent skills/resists/staffmods, requirements |
| Completed runewords | Recipe identity, allowed base, rolled skills/auras/FCR/damage, ethereal, actual contents; never priced as rune cost or empty base |
| Physical weapons | Base damage/speed/reach/requirements, ED plus flat/per-level damage, IAS, AR, relevant skills, leech/procs, ethereal and repair/replenish, sockets; role-specific effective damage |
| Caster/class weapons | Class/tree/specific skill combination, FCR where legal, staffmods, relevant mastery/resistance modifiers, useful charges/prebuff; physical ED does not establish caster value |
| Circlets/class helms | Class/tree skills together with FCR/FRW/sockets, life/stats/resists; distinguish class helms and low-level roles |
| Rings/amulets | Legal quality-specific skill/FCR combinations, leech/AR for attack roles, life/mana/attributes/resists; crafted fixed vs random contributions |
| Gloves/boots/belts | IAS + relevant skills/leech/CB where legal, FRW/FHR and resist combinations, strength/life, crafted properties, defense only when role-relevant |
| Armor/shields | Defense, block, FHR, resists, class skills, sockets, ethereal/repair/merc role; shield inherent modifiers and requirements |
| Charms/jewels | Charm size, exact tree/skill, coupled damage/AR/life or resist/utility combinations; jewel IAS/ED combinations, level restrictions, socket use |
| Unique/set overlay | Exact identity, variable rolls, ethereal/upgraded/socket variant, partial/full-set conditions, build stage and alternatives |

These are assessment axes, not universal keep thresholds. Numeric thresholds must
come from reviewed rules or validated comparisons. No blanket ethereal multiplier,
perfect-roll multiplier, or conversion from a utility score to Ist.

Suggested package layout (future): `pricing/knowledge/assessment/` containing
`models.py`, `normalize.py`, `registry.py`, `profiles.py`, `engine.py`,
`comparables.py`, and `handlers/` modules for the families above. Keep database
retrieval, market normalization and terminal rendering outside handler code.

Handler interface:

```
assess(facts, profile, definitions) -> Assessment
comparison_contract(facts, assessment) -> ComparableContract
```

Assessment returns profile applicability, matched/missing/failed predicates,
important observed rolls, conditional benefits, alternatives, sources and gaps.
ComparableContract returns hard identity/role constraints, required known facets,
per-stat matching policy, extra-affix policy and a versioned segment ID.

## Comparable selection and price evidence

Hard filters precede similarity: verified economy, identity/compatible family,
quality, build-role segment, ethereal, sockets/contents, relevant skill identities,
repair/indestructible status and required stat combinations. Unknown required
listing fields are excluded, not treated as false or zero. Explicit not-applicable
is distinct from unknown (e.g. a family that cannot have sockets).

Within that cohort, handler-defined bands may compare secondary rolls. A band must
not cross skill/IAS/FCR/level-requirement breakpoints or perfect-roll segments.
Additional valuable affixes on a listing can disqualify it; comparisons are
symmetric with respect to value-driving features. Cross-base substitutions need
an explicit equivalence rule and are labeled separately from same-base matches.

Store all candidates and exclusion reasons in diagnostics, not just three sample
listings. Deduplicate listings and sellers; keep ask alternatives/quantity and
currency conversion provenance. Use the existing per-seller policy consistently.
Expose dated asks and fills separately; never turn listing age into a sale.

Initial publication policy: no single item estimate from fewer than three eligible
independent sellers. One/two sellers can be shown as individual *comparable asks*
with a thin-evidence label. Three is a conservative engineering default, not a
claim of statistical certainty; calibrate per segment with offline fixtures.
Unknown observation dates permit historical evidence only, not a current estimate.
Large dispersion, stale evidence or unresolved premiums can still require abstention.
Show a robust band and median rather than a precise-looking standalone number.
Do not silently discard high asks as outliers; retain exclusion decisions and policy.

Trade confidence, build suitability, decoding completeness and roll quality are
separate fields. A high roll of an irrelevant modifier must not highlight the whole
item as valuable. A valuable watchlist entry triggers review, not guaranteed value.

## Offline KB publication

Reuse `appraisal-definitions.json`, `appraisal-demand.json`, `wp-a-builds.json`,
`wp-a-blues.json`, `wp-a-variants/`, base utility and market artifacts. Build demand
currently has both broad mentions and detailed variant/planner evidence; preserve
those different strengths. The generic desirable-stats strings need slot-level
review before execution. Do not generate rules by assigning every mentioned stat
to every listed item.

New portable artifacts:

- `appraisal-build-profiles.json`: reviewed role predicates with source locators.
- `appraisal-assessment-policies.json`: family/quality comparison contracts.
- `appraisal-assessment-coverage.json`: supported profiles, missing source rules,
  missing decoded facts, unmapped market fields and eligible seller coverage.

Track schema, rules version, generator version and source fingerprints. Validate
legal stat/family combinations, unknown IDs, impossible predicates, overlapping
registry entries and every source reference. Publish artifacts and dependent SQLite
index as a consistent validated generation. Hot-path appraisal is offline and does
not parse guide HTML. A missing policy is a named coverage gap, never guessed logic.

## Dread Edge acceptance case

Keep the screenshot transcription alongside the frozen snapshot; do not overwrite
raw facts to force a match. Resolve the native decoding gaps first.

1. Classify rare dagger, non-ethereal, zero sockets; do not route to runeword-base pricing.
2. Assess physical and Warlock skill roles independently. ED 51%, IAS 20%, per-level
   max damage/AR and the exact skill pair matter differently to those roles.
3. Evaluate max damage/AR at a documented common level while retaining coefficients.
4. Retrieve matching Warlock variant evidence; do not infer demand from '+2 skills'.
   Local `wp-a-builds.json` has Echoing Strike Standard using ethereal Void Legend
   Spike and Starter using Spirit/two-handed options. Those are alternatives,
   not evidence that every Warlock dagger is an equivalent substitute. Likewise,
   Mirrored Blades' ED/IAS priority is not proof this one-handed dagger fits its setup.
5. Reject the ethereal 273–300% ED reference listings as comparable prices.
6. Explain any supported starter/prebuff/attack role, missing requirements and known
   alternatives. Without reviewed fit evidence, say build fit unverified.
7. Price only a qualifying comparable cohort. Otherwise output price unavailable,
   with reasons; do not infer vendor value or quote the 97 Ist reference median.

Expected report order: identity/facets → build-role assessment with important rolls
and gaps → comparable price evidence/confidence → alternatives and keep/review reason.
Full rejected listings remain available in JSON diagnostics.

## Implementation and validation sequence

1. Preserve Dread Edge frozen capture and screenshot truth in a regression fixture;
   resolve skill-tab and per-level decoding, then replay without touching live memory.
2. Implement semantic ItemFacts, completeness and strategy registry. Seed reviewed
   rare dagger physical/Warlock profiles from exact local variant sources. Prove
   role mismatch and unknown ethereal/sockets cannot leak into estimates.
3. Replace generic 20% comparisons through contracts. Add adversarial pairs: same
   stats/different roles, extra premium affix, per-level totals at different viewer
   levels, known vs unknown ethereal, equal sockets/different contents, and ladder
   observations. Test abstention and a real eligible cohort, not only rejection.
4. Add clean bases/runewords and named unique/set overlay; replay Cryptic Axe,
   Mancatcher, Spirit, Insight, Shako and Guardian Angel. Require important rolls.
5. Extend class weapons, jewelry, charms and remaining armor families. Replay
   Storm Gyre, Greater Claws, Dire Song, rare rings and life charms. Each handler
   ships with source-backed positive/negative role cases and explicit coverage gaps.
6. Publish report sections and coverage audit; retire generic tolerance only when
   replacement contracts are wired. Update the update-kb skill with generation,
   source-review, regression and atomic publication instructions.

Evaluate false expensive matches and abstentions separately. Compare against
reviewed fixtures and actual scoped fills when available, not against our own
previous estimates. No live research or market refresh is required for the design;
new numerical claims require the existing approved market-data workflow.
