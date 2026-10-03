> **FROZEN 2026-10-03 (user decision).** This document no longer drives work: its gates, queues and
> stopping rules are suspended. The active plan is [PLAN.md](PLAN.md). Kept as technical reference only.

# Deliver useful assessments before repeating global maintenance

2026-10-03. Requested after the user challenged the pace and approach.
The completion contract and SC/NL/PC/RotW scope remain unchanged. This is an
execution plan, not completion evidence or permission to discard required work.

## Primary user outcome: worth selling, with sufficient demand

User clarification 2026-10-03: the main output is something valuable to trade and
liquid enough. Group broad sets of eligible bases around good stat combinations
instead of repeating rules for each item/build. This takes precedence over earlier
execution ordering that favors exhaustive individual-item refinement.

The primary highlight is a resale recommendation. Build usefulness, baseline tier,
perfect rolls and expensive asks alone cannot produce a liquid-trade claim.
Keep four concepts separate in the result: specimen qualification, likely buyer
breadth, liquidity evidence/confidence, and supported asking-price estimate.
A useful item can have a poor resale outlook; a valuable niche item can be slow.
Unknown liquidity is not evidence of low liquidity or worthless value.

Planned concise presentation:
- KEEP TO SELL: qualifying specimen and reviewed evidence supporting the chosen
  resale-effort policy; one reason naming the decisive combination.
- NICHE / SLOW SALE: qualifying value with reviewed narrow-demand or turnover
  evidence. Do not invent slowness merely because turnover is unknown.
- SELF-USE / NICE ITEM: reviewed utility without sufficient resale justification.
  Ordinary items without supported utility or trade merit need no positive banner.
  Preserve exceptional leveling/use notes separately.
- UNRESOLVED: missing decisive facts or evidence. A candidate with unmeasured
  liquidity may retain a candidate indication, explicitly without a liquid badge.

Completed scoped trades and measured observation histories can substantiate
turnover. Mere disappearance of a listing does not prove a sale. Dated asking
cohorts can support asking interest, never a claimed selling time. Reviewed demand
can support an explicitly inferred buyer-breadth judgment, not a measured liquidity
claim. Keep evidence kind, scope, date and uncertainty machine-readable.
No universal price floor, selling-time cutoff or arbitrary liquidity score is set.
User-selected policy: broad demand and reasonable selling effort; mark niche
items separately. Separate actual resale candidates from nice/self-use items.
This calibrates the recommendation, not the market facts. No follow-up approval
is needed for this choice.

## Shared rule architecture

Reuse ItemFacts, the family/quality routing, roles/predicates.py tri-state
predicates, trade_qualification policy layer and the existing report adapter.
Do not create a parallel classifier. A shared group contains:

1. Stable group ID and eligible quality/type/base selectors. Native base catalog
   supplies mechanics; membership alone never establishes sellability.
2. Named alternative stat combinations with source-backed bounds and interactions.
   AND within a required combination, OR across genuine alternative buyer uses.
3. Variant conditions: ethereal, repairability, socket occupancy and preparation,
   skill layers and applicable Non-Ladder recipe eligibility.
4. Demand evidence and separately reviewed trade/liquidity evidence. Each assertion
   must identify the group members/variants to which it actually applies.
5. Concise verdict reason and missing decisive conditions; keep every independently
   valuable copy. No average roll score and no requirement to own only one copy.
6. Small identity/base exceptions that override only the relevant condition with
   provenance. Conflicting or unknown memberships remain visible, not default false.

Evaluate all applicable groups. One failed group must not suppress another valid
buyer use. Deduplicate the resulting explanation, retaining evidence links.
Never pool numerical prices solely because items share a group; exact comparison
contracts continue to distinguish material base/roll/socket/ethereal differences.

Initial group inventory (thresholds must come from reviewed sources, not this list):

| Group | Shared combination or role | Important partitions |
|---|---|---|
| Physical charms | maximum damage + attack rating + life | size/native affix legality, meaningful joint thresholds |
| Skill charms | relevant skill tab + life/FHR/other buyer modifier | skill-tab demand, legal native ranges |
| Resistance charms | useful resistance + life/FHR/MF/gold find | size, single/all resistance, combinations |
| Socket jewels | IAS with damage/resistance; other supported modifier pairs | recipient effects, magic/rare legality, downside modifiers |
| Caster jewelry | FCR with useful skills/resources/attributes/resistances | ring vs amulet, rare vs crafted, breakpoints |
| Caster headgear | relevant skills + FCR + sockets/useful supporting stats | class, circlet family, achievable sockets |
| Skill weapons | relevant skills/staffmods + useful speed/sockets | class/skill demand, eligible base speed and affix quality |
| Physical rare weapons | damage + speed + supporting mods | base, ethereal durability/replenishment, interacting damage mods |
| Runeword bases | eligible desired base + sockets + meaningful innate mods | recipe, player/merc, ethereal, preparation outcomes |
| Boots/gloves/belts | role-specific speed/skills/resists/resources combinations | slot, affix legality, competing common alternatives |
| Named items | shared fixed-utility/roll-driven/ethereal/set-role templates | identity-specific buyer demand and meaningful thresholds |
| Completed runewords | recipe + desired base + decisive rolls | bearer, roll combinations, repairability, exact price cohort |
| Utility items | existing rune/gem/consumable handlers | single vs bulk quantity, scoped trade evidence |

First implementation group selection: choose an existing recurring combination
with reviewed evidence and several eligible members. Deliver its common evaluator,
explicit eligible collection, exceptions and reports together. Tests cover the
combination boundaries, a second eligible base/member, wrong-base exclusion,
unknown decisive stat and an important exception. Do not duplicate a full test
matrix per build reference; keep existing tests until separately reviewed.

## Why the previous approach is too slow

Small runtime changes have repeatedly triggered source repinning, publication,
thousands of tests and regenerated coverage artifacts. Source-occurrence and
validation-dimension counts are being used as work units instead of completed
item decisions. Some research stops at a new audit file without reaching Alt-D.
The same-generation final gate is necessary; rebuilding it after every small edit
is not a productive development loop. Do not weaken validators to make it cheaper.

## What counts as a delivered assessment

For a named identity or meaningful family/configuration, the report must answer:
- Is this specimen a trade candidate, premium candidate, useful only, or unresolved?
- Which actual rolls, combinations, sockets, base and ethereal conditions matter?
- Which supported player/mercenary use or exceptional leveling use applies?
- What condition is missing, and is it repairable preparation or an immutable roll?
- Is there a supported numerical estimate? Otherwise, what specific reviewed
  evidence deficit prevents it? Do not infer worthlessness from missing listings.

Qualitative value and numerical price availability are separate outcomes. A cache
miss is not a completed pricing review. Conversely, a reviewed evidence deficit
can be a valid pricing disposition without fabricating a quote or liquidity.

## One operational view, existing sources

Use existing named inventories, family/configuration reviews, item-bank targets
and rendered reports. Do not implement a second engine or another authoritative
coverage database. The operational view has one row per named identity or semantic
family/configuration and links to its existing sources and representative report.
Columns: item/configuration, current useful behavior, missing decision, evidence
readiness, next implementation, focused test, delivered generation. Preserve
unknown-demand leads and original source obligations behind these rows.

Do not derive completion percentages from test counts or the 110k dimension queue.
Separate behavioral completion, price-evidence availability and final verification.
Family rules may cover ordinary members only after an explicit reviewed disposition;
valuable exceptions must remain individually visible. Preserve universal named
baseline tiers and exceptional leveling coverage.

## Delivery order

1. Inspect representative *rendered* published reports and map missing decisions.
   Reuse saved replays and named research already collected. Check all relevant
   assessment fields: magic valuables do not necessarily use named trade_tier.
2. Finish evidence-ready trade groups spanning valuable items and bases. For each,
   use reviewed evidence to author conditions, implement them, run positive,
   near-miss and unknown item-bank examples, and inspect the actual report.
   A research-only artifact does not count as delivered behavior.
3. Apply the same process to runeword bases/completed words, charms/jewels, then
   magic/rare/crafted families. Preserve multiple valuable copies and stat synergy.
   Shared mechanics fixes should unlock multiple real configurations where safe.
4. Review ordinary long-tail dispositions, remaining discovery/scope leads and
   exceptional leveling gaps. No generic starter-equipment expansion.
5. Reconcile the original contract and final same-generation gates. No required
   pending/blocked work may be concealed by the simpler operational view.

Within each step, continue across groups. A group completion is not a stopping rule.

## Development and validation cadence

- Freeze one coherent group before coding. Specify expected reports and relevant
  boundaries from evidence; avoid automatically enumerating every Cartesian product.
- Red/green the changed behavior, then run directly affected regressions. Reuse
  existing broad tests; do not prune or weaken them as part of this plan.
- Keep stable source data and ongoing edits separate from historical execution
  receipts. Do not claim old receipts validate changed source or a new generation.
- Publish at a useful behavior checkpoint. Check affected published reports and
  saved replay changes. Run the broader reviewed-case suite after the group settles.
- Regenerate the coverage matrix and completion manifest when needed to reconcile
  scope/status, not after each item or auxiliary maintenance script.
- Run final broad validation only against a frozen candidate generation. If it
  fails, fix the actual cause and rerun affected checks, retaining remaining gates.
- While a source-bound run is live, do read-only review or prepare isolated evidence;
  poll the same process and do not mutate its inputs or restart it on a timeout.

## First report audit: what is actually visible

Evidence: tmp/leech-published-replay.json, generation
be2859d98f3fe984d6525b3ea40e6a7a0dec4dbf21d8e4754758804ca963bdcb.
This is a 20-capture sample, not universal coverage proof.

| Item | Visible behavior | Remaining decision |
|---|---|---|
| Druid Summoning grand charm, 37 life | Valuable candidate; native tier/range shown | Exact scoped asking evidence; verify broader charm combinations separately |
| Sacred Rondache, 27 all resistances | Spirit use, desired45res, socket preparation and item-level uncertainty | Distinguish trade qualification from merely usable alternative |
| Superior Phase Blade,14ED/2AR | Grief use and why this unsocketed superior base cannot obtain5sockets | Verify other valuable socket/use configurations; do not promise Grief preparation |
| Guardian Angel,187ED/nonethereal | ED range, low baseline tier, multiple conditional builds | Clear specimen trade qualification; avoid treating build counts as sellability |
| Harlequin Crest | Underlying-item trade candidate; fixed utility independent of defense | Exact variant market price remains unavailable for this capture |
| Insight Bill | Missing captured ED prevents comparison | Resolve capture evidence; do not reconstruct an exact ED roll from rounded damage |
| Runic Talons | Unknown socket contents block comparison | Capture/occupancy evidence, separate from item demand research |

Latest checkpoint: 47 named trade reviews validated, 28 report/stat review entries;
31,751 item-bank cases,238 required targets without cases. These are distinct
measures, not a completion percentage. New weapon-leech publication is delivered;
coverage regeneration subsequently rejected stale metadata dependencies. Preserve
that failure honestly and resolve it at the next maintenance checkpoint rather
than letting it displace all item-decision work.

## Next concrete work

Map the existing valuable named inventory and affixed/base combination rules into
the shared groups above, reconcile already delivered behavior, and group gaps
by the decision needed: sufficient evidence, inferable variant with native proof,
insufficient scoped evidence, or missing demand interpretation. Produce actionable
rows, not another source census. Then choose the evidence-ready group and finish
its rules and reports before starting new research. Live collection stays within
explicit user authorization; the stopped nine-item batch is not retried implicitly.


## Concrete starting point after policy selection

Current published value-watch data contains50affixed combination rows evaluated
by policies/value_watch.py:28SmallCharm,9GrandCharm,2LargeCharm,11Jewel.
These already use native combination bounds and affix/complete-capture guards.
Reuse that machinery. Do not copy50handlers or reset the rules to one generic score.
A valuable_candidate watch is not a liquidity disposition; existing named trade
qualification also separates candidate/premium/use_only but has no buyer-breadth
or measured-turnover contract. These are the precise missing pieces.

First shared delivery group: physical charms across all three native sizes.
Review their existing damage/AR/life combinations as one group with size-specific
legal bounds and evidence-backed thresholds. Add buyer-breadth/liquidity evidence
once per applicable group/branch, not once per build mention. Keep skill charms
partitioned by the actual skill-tab demand; they cannot inherit physical-charms
liquidity. Keep native size thresholds distinct and numerical comparisons exact.

For the report, choose one resale summary across applicable qualified groups;
retain niche versus broad-demand distinctions and unresolved decisive conditions.
Never demote to self-use solely because there are no market matches. Existing
watch-only evidence must remain a candidate/uncertainty, not be silently converted
to KEEP TO SELL. A nicer owned copy cannot suppress an independently sellable copy.

Tests for this first group: one qualified representative per size, just-below
combination thresholds, high irrelevant roll, unknown decisive stat, wrong family,
normal versus better/equal owned copies, and absence of unsupported liquidity
claims. Validate through actual appraisal and terminal/OSD summary. Then extend
through the same rule structure to other evidence-ready combinations.
