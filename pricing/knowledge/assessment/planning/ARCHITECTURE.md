# Concrete implementation architecture

2026-09-24. Implementation specification for [DECISION_TREE.md](DECISION_TREE.md)
and [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). Some interfaces remain planned;
the progress notes below and [STATUS.md](STATUS.md) distinguish implemented parts.
Runtime remains offline. Reuse the existing assessment package.

Next delivery priority (2026-09-25): [GUIDE_FIRST G1–G5](GUIDE_FIRST.md).
Reuse the occurrence ledger/compiler for item-centric demand summaries and reviewed
stat configurations. Add a shared structured BuildUseSummary projection; report
renderers consume grouped outcomes without recomputing matching or demand grades.
Identity-level demand and observed-item fit counts remain separate and traceable.

## 1. Migration baseline (2026-09-24) and required changes

| Existing code | Current responsibility | Planned destination/change |
|---|---|---|
| `assessment/models.py` | Mutable ItemFacts and one ComparableContract | Split into typed facts, policy and result contracts; keep temporary import facade |
| `assessment/normalize.py` | Capture adapter, metadata access and market-property projection | Capture adapter builds semantic facts; market projection moves to price adapter |
| `assessment/registry.py` | Broad family and quality dispatch | Resolve quality policy plus specific family; validate overlap and fallbacks |
| `assessment/handlers/exact.py` | Base/affixed price contracts only | Retain exact matching as a price-policy adapter; add mechanics analysis strategies |
| `assessment/handlers/runeword.py` | Loads definitions and constructs price contract | Inject definitions; separate recipe mechanics analysis from price-contract construction |
| `assessment/profiles.py` | Cached file loading, validation, linear role evaluation | Separate repository, compiler validation, candidate index and predicate evaluator |
| `assessment/build_profiles.py` | Publishes five hardcoded reviewed profiles | Migrate those records to reviewed rule data through compiler; preserve semantics |
| `assessment/base_use.py` | Independent runeword-base utility path | Base mechanics + preparation planner + role rules in the common engine |
| `assessment/ethereal.py` | Independent preference rules | Shared mechanical capability plus role-specific preference rules |
| `assessment/comparables.py` | SQL retrieval, matching and price summary | Split market repository I/O from pure matching/publication policy |
| `pricing/knowledge/pipeline.py` | Calls assessment, base utility and market paths separately | Application orchestration around one assessment and its comparison requests |
| `inventory_tracking/appraisal/presentation.py` | Shared plain/Rich/OSD document | Consume one versioned result via adapter; retain shared colors/renderers |

Do not replace working decoding or reimplement game tables. Native IDs, provenance,
exact comparison gates and saved-item behavior remain regression constraints.

## 2. Package structure and dependency rules

```text
pricing/knowledge/assessment/
  engine.py                      pure assessment orchestration
  registry.py                    quality/family/identity strategy resolution
  domain/
    facts.py                     immutable ItemFacts, StatKey, Fact, SocketState
    context.py                   optional player/mercenary/loadout facts
    rules.py                     selectors, predicates, roles, tier and price policies
    results.py                   analysis, role outcomes, preparation, assessments
    evidence.py                  provenance, structured issue/reason codes
  adapters/
    capture.py                   extraction → ItemFacts (current normalize.py)
    definitions.py               game definition bundle → typed lookup views
    market.py                    native facts → verified market constraints
    legacy_result.py              temporary v1 report/pipeline compatibility
  mechanics/
    stats.py                     relevant native stat access and contribution checks
    sockets.py                   legal sockets and preparation outcomes
    equipment.py                 slot/class/mercenary legality, requirements
    ethereal.py                   durability/repair/replenish/indestructibility
    upgrades.py                   legal upgrade paths and changed requirements
    derived.py                    verified damage/defense/per-level calculations
  handlers/
    protocol.py                  MechanicsHandler, FamilyStrategy interfaces
    base.py, affixed.py, unique.py, set.py, runeword.py, unsupported.py
    families/
      weapons.py, class_weapons.py, circlets.py, class_helms.py
      armor.py, shields.py, jewelry.py, accessories.py, charms.py, jewels.py
    unique_rules/                only exceptional mechanics needing Python strategies
  roles/
    candidates.py                indexed role discovery; no guide parsing
    predicates.py                typed predicate evaluation and four-state logic
    evaluate.py                  E0–E7 traversal and decision traces
    dependencies.py              companions, loadout and beneficiary conditions
    preparation.py               current item → potential legal destination states
    alternatives.py              same-role comparison and best-base proof
  policies/
    named_tiers.py               explicit default and conditional trade tiers
    leveling.py                  independent leveling outcomes
    comparison.py                semantic comparison request construction
    summarize.py                 role selection and conflict resolution for reports
  repository.py                  load one validated immutable assessment generation
  market_repository.py           local SQL market retrieval (application I/O)
  comparables.py                 pure matching and dated price publication
  maintenance/
    inventory.py                 source-occurrence census and normalization
    compile.py                   reviewed rules → validated runtime bundle
    validate.py                  schemas, IDs, legality, overlaps, source hashes
    publish.py                   generation and dependent index publication
    coverage.py                  source/rule/family/tier/comparison coverage
  rules/                         tracked reviewed source data, not generated cache
    collections.json
    roles/*.json                 grouped by build/role for review
    named/*.json                 per-identity tiers and overrides
    leveling/*.json
    comparison/*.json
  planning/                      design and source census
```

Use standard-library frozen dataclasses, enums and Protocols; JSON files at storage
boundaries. Do not add a general rule engine dependency or one class per named item.
Small stateless strategies implement mechanics; reviewed JSON describes selectors,
conditions, preferences, tiers and source-specific build roles.

Dependencies point inward: domain ← mechanics/handlers/roles/policies ← engine.
The engine takes definitions and rules as injected read-only values. It does not
import SQLite, Rich, GTK, guide parsers, filesystem loaders or worker code.
Repository/adapters/pipeline own I/O. Domain modules never import inventory_tracking.
The capture adapter may read its metadata through the existing boundary while the
migration supplies a portable definition view; no domain-to-decoder circular import.

## 3. Typed domain contracts

### Facts

`Fact[T]` contains `value: T | None`, status (`known`, `unknown`, `not_applicable`,
`conflicting`), origin (`observed`, `definition`, `derived`), and evidence references.
Known false/zero is never represented by unknown. Contradictory inputs are retained
as issues and never resolved by picking whichever adapter ran last.

`StatKey(stat_id: int, parameter: int)` is the semantic key. `StatFact` retains raw
and normalized values, unit, origin/contribution, coefficient/reference level for
per-level stats, and source references. Market property IDs and display text are
adapter fields, not rule identifiers. A skill's identity includes its parameter;
class skill, oskill, aura, charge and proc facts remain distinguishable.

`ItemFacts` contains:

- Identity: stable base/unique/set/recipe IDs, quality, type ancestry, original vs
  upgraded base, identification state, version applicability.
- State: ethereal, ilvl, requirements, durability/quantity, repair/replenish status.
- `SocketState`: total count, known ordered contents, occupied/empty counts and
  completeness; counts must agree. Unknown filler identity differs from empty.
- Immutable stat map and completeness by fact group: identity, modifiers, sockets,
  requirements, flags. Absence means zero only when that specific stat domain has
  proven complete capture and the stat semantics support absence-as-zero.
- Structured issues and source provenance. No single global gap list decides all
  usefulness; numerical pricing retains stricter completeness requirements.

`AssessmentContext` optionally supplies player class/level/attributes, equipped
items, mercenary act/subtype/level/equipment, and active loadout stats. Every field
has a known/unknown state. Absence of context is not failure to meet a requirement.
A captured historical loadout cannot establish current equipped companions.

### Policy records

`RoleDefinition`: ID/version, source review state, selector, build/variant/side/slot,
beneficiary, stage, `must`, `any_of`, `prefer`, `avoid`, `depends_on`, preparation
policy IDs, important StatKeys, alternative IDs, comparison segment IDs and sources.
All references are validated. Inheritance is explicit and resolved at compile time.

`NamedTierPolicy`: stable identity, reviewed default high/med/low/trash, ordered
conditional overrides, important rolls, source basis and review status. An omitted
tier is pending review, never trash. Trade tier has no automatic conversion to Ist.

`LevelingPolicy`: role/class/archetype/side, equip eligibility and progression stage,
high/med/low/none tier, companions/conditions and evidence. None is an explicit
reviewed result; pending is a separate review state.

`ComparisonPolicy`: segment ID/version, identity policy, hard facets, required-known
stats, permitted secondary-roll bands, premium/extra-property exclusions and evidence
publication policy. No broad numerical tolerance inherited across families.

### Planned stat desirability evaluator (2026-09-25)

Implement `StatsEvaluator` as a pure component over existing role outcomes and the
predicate/mechanics infrastructure, accepting the item, an indexed sequence of
reviewed `StatConfiguration` records and optional context. Configurations carry
applicability, mandatory combinations, prioritized essential/supporting stats,
interaction predicates, roll policies and provenance. `StatEvaluation` retains
per-configuration match status, unmet/unknown requirements and per-StatKey
annotations with separate desirability and roll-quality results plus source/line
mappings. Include these annotations in the shared versioned assessment result;
renderers consume them without re-evaluating combinations. Publish configurations
with the existing rules generation. The complete planned behavior and acceptance
matrix are in [implementation plan §8.1](IMPLEMENTATION_PLAN.md#81-combination-aware-stat-indicators--required-planned-2026-09-25).

### Result contracts

| Type | Required fields |
|---|---|
| `MechanicsAnalysis` | policy/family IDs, verified capabilities, derived facts, issues |
| `PredicateResult` | rule/node ID, true/false/unknown/not-applicable, observed/expected values, source/reason codes |
| `RoleOutcome` | role/build/variant/side/slot, matched/conditional/failed/unknown, important rolls, missing dependencies, trace references |
| `PreparationOption` | destination role/recipe, actions, preconditions, possible outcomes/probabilities, destroyed contents, feasibility |
| `BaseComparison` | role, eligible alternatives, comparison criteria, dominance evidence, unresolved loadout dependencies |
| `TierOutcome` | reviewed default, effective tier or conditional candidates, applied override IDs, reasons |
| `ComparisonRequest` | request/segment IDs, applicable roles, current-state semantic constraints, evidence policy version |
| `AssessmentResult` | schema/rules/generation IDs, facts, mechanics, roles, preparation, tiers, leveling, ethereal preferences, comparison requests, diagnostics |
| `PriceResult` | request ID, dated asks/fills, seller count, estimate/band or blocker, accepted/rejected evidence references |

Keep `AssessmentResult` distinct from the existing presentation class named
`ItemAssessment`. Rendered lines do not become domain contracts.

## 4. Runtime interfaces and flow

Proposed Python interfaces (type contracts, not implementation):

```python
class MechanicsHandler(Protocol):
    def analyze(self, facts: ItemFacts, definitions: Definitions) -> MechanicsAnalysis: ...

class FamilyStrategy(Protocol):
    def analyze(self, facts: ItemFacts, definitions: Definitions) -> FamilyAnalysis: ...

class RuleRepository(Protocol):
    def snapshot(self) -> AssessmentBundle: ...

# Application boundary; only this layer loads artifacts and market rows.
normalize_capture(extraction, definitions) -> ItemFacts
assess(facts, *, bundle, context) -> AssessmentResult
fetch_market_candidates(database, requests) -> Mapping[RequestId, Sequence[Listing]]
match_comparables(request, policy, listings, *, as_of) -> ComparableResult
publish_price(comparables, publication_policy) -> PriceResult
serialize_assessment(result, prices) -> dict
```

Each call follows this order:

1. Pipeline obtains one bundle snapshot and normalizes capture once.
2. Registry chooses one quality handler, one family strategy, and optional explicit
   identity specialization. The specialization extends/overrides named behavior
   through declared fields; no implicit merge of arbitrary dictionaries.
3. Mechanics analysis computes legal capabilities. Stat access and socket mechanics
   are shared services, not repeated in each build handler.
4. Candidate index retrieves every possibly applicable role. Cheap selectors narrow
   identity/family/quality; unknown stat fields must not exclude a role prematurely.
5. Evaluate current-state role predicates and dependencies; build legal preparation
   options separately. Evaluate alternatives only inside the same role assumptions.
6. Resolve named tiers, independent leveling, and role-specific ethereal preferences.
7. Build comparison requests from observed current-state facts. No market price for
   an imagined socket/upgrade outcome. Exact-variant requests can exist without a
   guide role; a build endorsement is not a prerequisite for valid market evidence.
8. Pipeline batches local market queries, applies pure comparables and price policy.
9. Serializer produces versioned JSON; presentation maps selected structured results
   to concise labels and semantic colors. Diagnostics never become blanket warnings.

For several roles sharing identical constraints, deduplicate the comparison request
by canonical contract fingerprint and retain all role references. Keep different
segments separate. Never sum role prices or automatically select the highest ask
band. Prefer the exact current-variant result; if several conflicting valid segment
estimates remain, report that ambiguity instead of manufacturing a single price.

## 5. Predicate language and decision semantics

Use a small typed AST, not executable Python strings or free-form expressions.
Allowed primitives initially:

- `fact_known`, `fact_eq`, `fact_in`, `stat_at_least`, `stat_between`.
- `identity_is`, `type_is`, `skill_bonus` with explicit native stat/parameter selector.
- `equip_legal`, `socket_state`, `recipe_compatible`, `companion_present`.
- `loadout_target`, `beneficiary_is`, and named verified mechanics predicates.
- Composition: `all`, `any`, `not`. No arbitrary arithmetic in rule JSON; complex
  calculations use a named, tested mechanics function registered by ID.

`all`: false dominates; otherwise unknown dominates; otherwise true when at least
one applicable child is true; all not-applicable yields not-applicable.
`any`: true dominates; otherwise unknown dominates; otherwise false when at least
one applicable child is false; all not-applicable yields not-applicable.
`not` flips true/false and preserves unknown/not-applicable. Empty groups are invalid.
A required predicate evaluating not-applicable is a policy applicability problem,
not a successful requirement. The compiler rejects avoidable cases; runtime records
an unknown/invalid-policy outcome rather than silently passing the role.

`must` determines role fit. `prefer` orders relevant advantages but never substitutes
for a failed requirement. `avoid` records role-specific disadvantages; a hard ban
must be in `must`. `depends_on` records loadout/companion conditions. `prefer` and
`avoid` do not generate a universal numeric score or an Ist multiplier.

Example reviewed-rule shape (illustrative IDs, compiled against verified catalogs):

```json
{
  "id": "nova.standard.player.infinity",
  "schema_version": 1,
  "review_status": "pending_review",
  "selector": {"recipe_names": ["Infinity"], "side": "player"},
  "build": "nova-sorceress-guide",
  "variant": "Standard",
  "slot": "Weapon",
  "beneficiary": "wearer",
  "must": {"all": [
    {"op": "recipe_compatible"},
    {"op": "equip_legal", "subject": "player"}
  ]},
  "prefer": [{"policy": "nova_self_wield_requirements"}],
  "depends_on": [{"policy": "nova_standard_loadout"}],
  "comparison_policy": "infinity.player_nova.v1",
  "source": {
    "path": "pricing/data/wp-a-variants/nova-sorceress-guide.json",
    "locator": "/variants/1/player/Weapon"
  }
}
```

Authoring names resolve to stable definition IDs during compilation. Source date/hash,
reviewed predicates and all referenced policies must exist before publication;
this abbreviated pending example itself cannot become an executable rule.

## 6. Registry, conflicts and preparation

Registry keys: quality policy + verified type ancestry; optional named identity
specialization. Priority is explicit: exact identity > specific type > ancestor >
unsupported fallback. Quality dispatch prioritizes verified completed runeword over
normal rarity. Sets and uniques remain distinct policies. Equal-priority matches
are compile errors. Type ancestry must be acyclic and sourced from game tables.

Collections (e.g. charged utility, mercenary sustain helmets) contain explicit IDs
or validated type selectors. They select multiple roles; they do not cause multiple
primary mechanics handlers to run. Additional family predicates cannot bypass
quality restrictions such as magic items not being runeword bases.

Preparation is a bounded action graph, not a generic search over hypothetical gear:
allow only verified socket quest, cube socketing, content removal, low-quality
normalization and supported upgrades. Each action declares input eligibility,
changed facts, preserved facts, costs/destruction and outcome distribution. Reject
cycles; evaluate only paths ending in a requested destination. Derived hypothetical
states retain their parent and never overwrite observed facts or enter current-item
comparison requests. Missing ilvl leaves conditional outcomes, not guessed odds.

Alternatives compare vectors relevant to one role: requirements, socket feasibility,
staffmods/inherent stats, damage/speed/defense and durability. Dominance requires no
worse relevant dimensions under the same assumptions. If alternatives trade speed
for damage, return alternatives/conditional preference rather than a universal best.

## 7. Data authoring, compilation and storage

Tracked `rules/` contains curated decisions and provenance references. Large cached
research stays in existing ignored `pricing/data/` and `pricing/raw/`. Generated
bundles must be restorable with the offline KB snapshot; git checkout alone does
not imply the evidence cache exists.

Compiler stages:

1. Inventory every source occurrence: source hash + pointer, original label,
   build/variant/side/slot, normalization and disposition. Retain rejected/conflicting
   evidence in a review ledger; only reviewed rules enter the executable bundle.
2. Resolve identities, aliases, explicit variant parents, slot aliases, AND/OR item
   combinations, beneficiaries and quantity. Detect inheritance cycles and conflicts.
3. Validate JSON schema and typed AST; resolve catalog IDs and reject illegal
   quality/mod/slot combinations. Validate tier completeness against enabled IDs.
4. Compile selectors into immutable postings by identity/type/quality/semantic tags.
   Intersect safe selectors; union multi-role collections. Full predicates still run.
5. Package definitions needed at runtime, rules, source manifest, coverage and
   comparison policies. Compute content hashes and a generation ID.
6. Build the dependent SQLite read model and validate references/counts before
   publishing. Do not execute arbitrary cached prose as a rule.

Concrete runtime artifact contract:

- `assessment-manifest.json`: schema version, rules version, generation ID, required
  engine version, input hashes, artifact hashes and reviewed/pending/excluded counts.
- `assessment-definitions.json`: normalized runtime identity/mechanics views.
- `assessment-rules.json`: reviewed collections, roles, tier, leveling and comparison
  policies with compiled IDs and source references.
- `assessment-coverage.json`: census dispositions and precise unresolved branches.
- Existing `appraisal.sqlite3`: add generation metadata and indexed policy/role
  references used by retrieval; retain existing market evidence tables.

Use a staged immutable generation directory containing the artifacts and dependent
SQLite file, validate it, then atomically replace a small current-generation pointer.
Readers pin a generation for the whole appraisal. Integrate this into existing KB
publication rather than independently swapping JSON and SQLite in place. During
migration, existing callers use a repository path resolver; legacy paths remain
read-only compatibility inputs until all writers/readers use the resolver.

Validation failure keeps the prior generation active. If no compatible bundle exists,
return supported legacy behavior or explicit unavailable rules according to the
migration flag; never combine partial v2 files with v1 rules. Cache definitions,
roles and candidate indexes by generation, not indefinitely by filename. Old pinned
generations remain usable until readers release them; cleanup is maintenance work.

Source hashes establish provenance, not automatic expiry. Changed sources create
review tasks and require revalidation before republishing dependent rules. Market
freshness is evaluated separately against the assessment's explicit `as_of` date.

## 8. Pipeline and report integration

`retrieve_draft` remains the public orchestration entry during migration. Add an
injected assessment service/bundle provider rather than global caches in handlers.
Its v2 payload includes `assessment.schema_version = 2`, generation ID, structured
role/tier/preparation results and per-request prices. Old top-level base-use,
ethereal and single-contract fields come from a **single compatibility adapter**;
there is no second assessment pass to populate them.

Presentation consumes a compact summary produced from structured outcomes:
identity/stats → important use and tier → leveling keeper → actionable preparation
or missing requirement → price or specific blocker. It does not inspect native stat
IDs or reproduce mechanics. Keep existing plain/Rich/OSD shared rendering.

When ethereal preferences conflict across valid uses, attach the preference to each
use and leave the global ethereal line neutral or explicitly mixed. Do not make an
item globally red because one role dislikes ethereal while another prefers it.
Distinguish trade-value highlights, leveling highlights and per-stat roll colors.
Conditional set use remains conditional even if the tier catalog knows the set.

Large traces and rejected roles stay in JSON, referenced by stable reason IDs.
Messages format known observed/required values; no generic coverage boilerplate.
Unknown prices do not suppress useful base/build/leveling conclusions.

## 9. Migration as concrete implementation changes

| Change | Files / work | Exit gate |
|---|---|---|
| A1 | Add domain contracts and capture adapter; `models.py`/`normalize.py` delegate temporarily | Existing saved normalized facts equivalent; unknown/zero and native parameters preserved |
| A2 | Add bundle loader/compiler and migrate five current profiles unchanged | Offline bundle validates; missing/mismatched artifact and cache-isolation cases pass |
| A3 | Add registry composition and handler protocols; wrap existing exact/runeword contracts | Existing numerical matching does not broaden; runeword precedence and overlaps tested |
| A4 | Add predicate AST/evaluator, candidate index and dependency results | Current dagger/Sazabi behavior preserved; false/unknown/NA composition and recall tests pass |
| A5 | Move socket/base-use/ethereal logic behind shared mechanics and preparation | One evaluation source; Phase Blade/Sazabi/merc armor regressions pass |
| A6 | Deliver first three Infinity roles and source-reviewed policies | Correct player/merc/Amazon split; separate contracts and meaningful alternate-base outcomes |
| A7 | Add explicit named tier and leveling policy engines; populate reviewed identities in slices | Missing record is pending; overrides and companion conditions cannot become automatic trash/fit |
| A8 | Split market I/O from pure comparisons; support request sets and v2 pipeline payload | Exact-contract equivalence, no cross-segment pooling, no hypothetical-state prices |
| A9 | Integrate summary adapter and shared terminal/OSD presentation | Existing stat lines retained; actionable role/tier/leveling outputs; no duplicate base logic |
| A10 | Expand remaining build slices from DECISION_TREE section J; complete catalogs | All source occurrences have dispositions; eligible named identities have reviewed tiers |
| A11 | Switch default to v2, remove migration flag/facades after consumers migrate | Full suite/replays and offline restore pass; only one runtime evaluator remains |

Keep these changes reviewable and green; do not perform the entire directory move
and behavior rollout in one patch. Start with stable interfaces and preserve existing
import paths briefly. No permanent legacy/future parallel engines or per-item switch
sprawl. Compatibility removal is part of completion, not an indefinite TODO.

## 10. Test and operational contracts

Tests mirror package paths. Use plain pytest tests and source-backed fixtures.

- Domain/adapter: unknown vs zero, conflicting identity, partial socket contents,
  duplicate/contributed stats, exact native parameters, per-level coefficients.
- Predicate/registry: truth composition, false required vs missing context, illegal
  family-quality rules, overlap, explicit delta inheritance, candidate recall.
- Mechanics: socket boundaries and distributions, superior restrictions, preparation
  provenance, merc equip legality, shared non-ethereal Treachery, repair exceptions.
- Tier/role: wrong skill or beneficiary, unmet set companions, default vs override,
  low-trade/high-leveling item, conflicting ethereal roles, no perfect-roll inflation.
- Market: unchanged exact baseline, symmetric premiums, wrong scope/base/ethereal,
  stale evidence, seller deduplication, request deduplication without cohort pooling.
- Publication: deterministic generation, invalid source/ID references, atomic swap
  failure, pinned readers, cold offline restore, no raw-guide access on hover.
- End-to-end: existing saved items and the role-distinguishing pairs in DECISION_TREE.
  Compare expected source/screenshot facts, not only old output snapshots.

Inject date, bundle and context for deterministic tests. Engine tests require no
network, SQLite or GTK. Pipeline integration tests use the real local SQL schema.
Measure cold initialization separately from warm assessment; report candidate counts,
role-evaluation time, market time and p50/p95 against the frozen baseline. Do not
invent a latency target before measurement; prevent a full 60k-row demand scan on
hover by asserting indexed retrieval and checking candidate recall.

No new live probes are required for this architecture. Keep source gaps explicit;
only request a targeted capture when a mechanics assumption cannot be resolved from
existing fixtures and local definitions.

## Implementation progress — 2026-09-24

- A1 foundation implemented: immutable detached ItemFacts, typed Fact/StatKey,
  capture adapter and compatibility facades; explicit socket occupancy with unknown
  partial contents and conflict detection. Full structured issue/completeness and
  context/result contracts remain to be integrated.
- A2 initial profile path implemented: tracked reviewed JSON, source-fingerprint
  compiler, immutable content-hash snapshots, safe reload and last-good fallback.
  Five existing rules preserve their output. Whole artifact/index generation and
  expanded policy schemas remain planned.
- Validation at this checkpoint: 864 tests passed, 3 skipped; ten saved captures
  replayed. No additional pricing families have been enabled at this checkpoint.

### A5/A9 integration checkpoint — 2026-09-24

Runeword-base suitability now runs inside `_assess` against its normalized
`ItemFacts`. The structured result owns `base_uses`; retrieval copies that result
into the existing `base_assessment.uses` report field without a second evaluator
or normalization pass. The base-use function now accepts facts directly; internal
test callers migrated rather than adding another compatibility dispatch path.
Historical base-market context remains separate retrieval work. Typed preparation
results and removal of the report compatibility field remain unfinished.

Validation:1930 tests passed,3 skipped;18 saved replays produced identical report
text. Engine-only assessments now include the same merc/player base judgments.

### Use-specific ethereal aggregation — 2026-09-24

The engine combines explicit viable role/base-use preferences with general named
item guidance. Conflicting preferences remain attached to their uses and produce
`mixed` globally, which the existing shared terminal/OSD renderer leaves neutral.
Failed/unknown roles and unusable preparations do not affect global coloring.
Fortitude player/mercenary and Nova caster/mercenary cases have regression coverage.
This does not complete the per-build preference catalog or imply price multipliers.

### A8 request-set integration — 2026-09-24

Added immutable ComparisonRequest with request/segment IDs, role references,
observed/prepared state and policy version. Pure request-set evaluation deduplicates
identical contracts only within the same segment/state/version, merging role and
request references. Different segments and modifier cohorts retain separate seller
counts and estimates. Prepared states cannot produce current-item prices.

Engine emits the existing exact current-variant contract as a request. The market
repository reads each normalized observed name once, skips prepared names, then
invokes the pure evaluator with one as-of date. Pipeline exposes request results
and selects only request current for existing comparison/price report fields.
Unclassified items retain their previous unavailable diagnostics. No highest-band
selection, cross-segment seller pooling or speculative preparation pricing.

1968 tests passed,3 skipped;18 replays retain identical report text and prices.
Reviewed alternative comparison policies, full v2 result migration and removal of
compatibility fields are still outstanding; this is not completion of A8–A11.

### A5 preparation result foundation — 2026-09-24

Socket preparation moved from base-use report logic into mechanics/preparation.py.
It returns immutable SocketPreparation/PreparationOption records, serialized per
base use with destination, action, target count, feasibility, preconditions,
cap-conditional success weights and destruction. Existing messages are produced
by that same evaluator. No action mutates ItemFacts or enters a current-price
request. Conflicting socket facts reject preparation. This is the socket subset;
resource costs, explicit bounded action chains, upgrades and low-quality
normalization remain unfinished, as does the full v2 result/publication migration.

### A5 preparation resource requirements — 2026-09-25

Structured socket options now include immutable consumed-resource quantities and
explicit cube/ingredient or unused socket-reward preconditions. The four equipment
cube recipes and clear-socket recipe carry pinned source locators and table-backed
regressions. Resource ownership is not inferred from mechanical feasibility; no
resource cost becomes an item price. Bounded action chains, low-quality repair and
upgrades remain unfinished. Runtime requires no reference-checkout reads.

### Publication storage foundation — 2026-09-25

`pricing.knowledge.publication` stages a SQLite backup and every indexed source,
verifies source hashes against index metadata, captures explicit non-indexed inputs,
and hashes a manifest. Optional semantic validation runs before promotion. Generation
directories are never overwritten or removed; an atomic current.json replacement
selects a complete candidate. Existing reader handles keep their original directory.
Manifest/artifact/index corruption rejects opening, and publication failure leaves
the previous pointer intact.

The maintenance CLI packages current runtime artifact inputs, reviewed profiles and
item metadata in addition to index sources. It verifies storage/index consistency;
it does not yet replace the existing semantic compiler gates. Runtime path resolver,
metadata/definition-provider injection, automatic last-good selection and default
pipeline migration remain unfinished. The live appraisal pipeline still reads the
existing paths. Do not claim a fully generation-pinned runtime from this storage step.

### Pinned bundle runtime adapter — 2026-09-25

Added published_snapshot and retrieve_published: require all declared runtime inputs,
pin their bytes to original logical repository paths, inject definitions/native
metadata, then reuse the existing pipeline with the bundle index. Strict artifact
contexts forbid working-tree fallback. Metadata-derived base indexes cache by
content generation; default reader contexts restore after exit. Publication CLI and
runtime share one required-input list. Default worker selection, semantic promotion
gates, last-good handling and cached bundle loading remain unfinished.

### Cached runtime / last-good provider — 2026-09-25

PublicationRepository serializes loads, validates a new selected generation and
retains parsed runtime artifacts. Warm access avoids artifact reads and metadata
parsing. Failed pointer/publication updates return explicit issues with the last
good runtime only while its index fingerprint remains unchanged. No initial valid
runtime or a mutated old index means unavailable. Isolated profile validation
prevents cross-generation fallback. Default worker/cache lifecycle and full semantic
promotion checks remain incomplete.

### Worker request lifecycle integration — 2026-09-25

Optional --publication-store warms a PublicationRepository and pins PublishedAppraisal
request state before capture. Context propagation carries the same artifact/metadata/
definition snapshot through asynchronous retrieval, cache-hit completion and hover
rechecks. Cache keys include generation, pinned UTC date and publication issues.
The backend verifies the retained index fingerprint before retrieval and records
publication generation/issues in structured diagnostics. Default --database behavior
remains available; default switch and complete semantic promotion gates are pending.

### Staged semantic validation — 2026-09-25

Appraisal publication CLI passes load_runtime as its pre-promotion validator. New
runtime loads also validate metadata/definition content agreement, named-tier
schemas/native IDs/source identity and hashes, isolated profiles, supporting loader
schemas and reviewed generic-leveling fingerprint. Old policy validation caches are
bypassed for publication. Failure occurs before pointer selection; existing runtime
fallback behavior applies. Full external profile-source materialization and all
upgrade-derived metadata checks remain pending, so this is not the final complete
publication audit or default migration.

### Profile evidence materialization — 2026-09-25

Publication now packages all26 referenced profile source documents. Dependency
discovery during loading uses the bundled profile document. Compilation and staged
validation share path containment, fingerprint and JSON-pointer checks with injected
byte readers; runtime validation reads strict pinned artifacts. All249 reviewed
profiles' references resolve offline from the generation. This proves integrity of
reviewed evidence, not coverage of all unreviewed build occurrences. Remaining
publication work includes upgrade-derived metadata validation and default migration.

### Derived upgrade metadata gate — 2026-09-25

Publication now validates the complete upgrade_variants map for every unique/set
definition against mutually verified ascending base-catalog chains and target
defense ranges. Builder/validator share the extracted pure named_upgrades helper.
Conflicting catalog entries, missing targets, extra/original targets and changed
defense intervals reject the bundle. Regenerated metadata is byte-identical to the
prior output. This closes the previously excluded upgrade_variants field check;
default migration, skill runbook updates and broader appraisal scope remain pending.

### Default publication selection — 2026-09-25

Alt+D service now defaults to pricing/data/generations. Explicit --database retains
legacy/test-index operation and is mutually exclusive with --publication-store.
No initial valid publication fails with the offline publication command; there is no
silent working-tree fallback. Current45-artifact bundle was validated and published
to the default store. Maintenance replay accepts --publication-store to verify that
selected generation, and update-kb now documents publish/replay/worker lifecycle.
This changes runtime selection, not research coverage or completion of v2 results.

### Typed assessment outcome — 2026-09-25

`engine.assess_result` returns an immutable `AssessmentResult` containing normalized
facts, role/base/leveling judgments, tier and ethereal policies, gaps, typed comparison
requests and generation provenance. `adapters.assessment.legacy_payload` owns the
version-1 dictionary projection; `engine.assess` remains compatible. Retrieval uses
the typed requests directly instead of serializing and reconstructing them.
ComparableContract now freezes caller-owned property mappings and socket payloads;
use its `to_dict()` for mutable JSON fixtures and consumers.

This is the result-model foundation, not the completed v2 model: individual role
and policy judgments still use frozen mappings, and broader pricing coverage remains
incomplete. All18 saved replay objects are identical. Red-green isolation tests and
the full suite pass (2016 passed,3 skipped). No data rebuild or publication required;
the running worker needs a restart to load these Python changes.

### Low-quality normalization routes — 2026-09-25

Unsocketed low-quality bases now have bounded normalization → Larzuk/cube routes.
The first step consumes Eld + chipped gem for weapons or El + chipped gem for armor,
then sets normal quality/item level 1. Socketing uses only the lowest level bracket,
with exact cube weights and separately recorded step resources/preconditions.
Sources: pinned d2data cubemain127/128 and D2MOO PlrTrade.cpp level calculation.
No source checkout is read at runtime. PreparationOption.steps is optional, leaving
existing single-action serialized reports unchanged.

The model does not copy observed defense/staffmods/inherent bonuses/ethereal state
into the regenerated item, create speculative comparison requests, or claim the
current low-quality item is a perfect base. General ethereal premium coloring no
longer applies to low-quality bases. Socketed/unknown/conflicting low-quality state
still needs review. An impossible normalization route is explicitly labeled as such;
this does not establish that every other possible direct low-quality route is illegal.
Direct low-quality socket quest use and broader upgrade chains remain unreviewed.

Behavioral cases: Archon Plate → Enigma gets3 sockets via Larzuk or4/6 cube odds;
Monarch → Spirit and Phase Blade → Grief cannot obtain their target count after
normalization. Original facts remain immutable. Normalization outcomes require a
new capture before judging the resulting item's rolls or trade value.

### Unique/set/rare upgrade preparation — 2026-09-25

The engine now returns immutable UpgradePath records in AssessmentResult.upgrades;
the compatibility report contains upgrade_paths only when legal routes exist.
Routes cover verified ascending normal→exceptional→elite chains, at most two
steps, with per-step recipe resources, source rows and added level-requirement
penalties (+5 then +7). Already-upgraded unique/set items need a captured matching
table identity; they receive only the remaining route. Elite, magic, crafted,
unidentified, incompatible and ambiguous identities receive no route.

Recipes are reviewed constants from d2data fc469993502d cubemain129-136/151-154.
Rare weapons/armor have their own recipes. Set Non-Ladder availability is confirmed
by Blizzard Patch2.6 article23899624:
https://news.blizzard.com/en-gb/article/23899624/diablo-ii-resurrected-ladder-season-three-has-concluded
This is mechanics research, not new market collection.

Paths record changed base/mechanics/requirements and retained identity/modifiers/
ethereal/socket state without replacing captured facts. They require Cube resources
and checking wearer requirements; recipe penalties are not final required levels.
No random defense/damage outcome, total requirement or prepared-item price is
invented. Current-item comparison requests remain unchanged. These are structured
legal capabilities, not automatic recommendations or new terminal report lines.
Build-specific upgrade preference and prepared-state market comparisons remain work.

### Build-specific upgrade dependencies — 2026-09-25

Reviewed direct base-code dependencies now link to a matching legal UpgradePath.
The engine computes paths once and passes them to role evaluation. This connects
both Death's Guard starter profiles (Strafe Amazon and Double Throw Barbarian)
to the cited Demonhide Sash upgrade, without recommending the unrequested elite
upgrade. Terminal build-use details include the actual Tal + Shael + Perfect
Diamond recipe; structured dependencies retain the path and source steps.

Observed dependency status remains false and the role remains partial until the
item is actually upgraded and the remaining setup conditions are met. Failed or
unknown mandatory role properties, unknown identity state and unreachable
destinations produce no action. Compound predicates are deliberately not solved
by substituting a hypothetical base: defense and wearer requirements may change.
Other dependencies remain independent and retain their own statuses; their order
does not change whether a legal route is attached. Current-item pricing requests
and facts are unchanged. Broader prepared-state role evaluation and comparisons
remain unfinished.

### Executable loadout breakpoints — 2026-09-25

AssessmentContext accepts optional player_total_fcr: a nonnegative integer percent
for the assessed loadout. Missing values, booleans, strings, floats and negatives
stay unknown. This value is never inferred from the hovered item's native FCR stat.
Callers must supply the total for the loadout being assessed; capture/worker code
does not discover it automatically or assume replacing equipment preserves it.

The context_at_least predicate supports validated numeric context fields, keeping
known-below, known-met and unknown distinct. Numeric field definitions are shared
by context normalization and predicate validation, including context_eq typing.
Ten reviewed profiles now use explicit75/105/117FCR dependencies: Hydra Standard
facet, Echoing starter dagger, five caster-belt profiles, and three Lightning Tal
Rasha profiles. Source thresholds and other requirements are unchanged. Unknown
unquantified whole-loadout prose remains prose; no default breakpoint is inferred.

Meeting FCR removes only that missing dependency. Recipient, wearer, companion and
survivability conditions remain independent. Current-item numeric estimates and
stat roles remain separate. The nine existing-profile migrations and Hydra's
integration have red-green tests, including malformed totals and exact boundaries.

### Typed build-role results — 2026-09-25

RoleAssessment now owns build/variant/slot identity, status, source evidence,
requirement/dependency traces, preferences, equipment findings and preparation
links. It freezes nested containers on construction. assess_role_results returns
these immutable outcomes; engine comparison-request role IDs use attributes and
AssessmentResult retains the typed roles. The existing assess_roles API projects
plain dictionaries through adapters.roles, also used by the final report adapter.

Ethereal aggregation accepts typed roles via a small policy view containing only
identity/status/source/preference fields. It does not serialize full traces and
upgrade evidence merely to compute coloring. Legacy dictionary role inputs remain
accepted. There is no rule, tier, market matching or presentation change.

Red-green tests verify detached source inputs, immutable nested upgrade evidence,
independent mutable report projections and typed engine retention. Nested traces
and other policy outcomes still contain frozen mappings; the broader v2 result
migration and pricing/build research coverage are not complete.

### Exact-market tier overlay — 2026-09-25

The pipeline applies policies.market_tiers after comparison evaluation, because
the typed engine result precedes market retrieval. It may replace only a pending
unique/set tier using the observed current-item named estimate. Reviewed policies
retain precedence; boundary-spanning ask bands stay conditional. The overlay is
market evidence for that variant, not a reviewed identity-wide default. See the
assessment README for thresholds and provenance. The v2 result migration still
needs to encompass these post-retrieval outcomes.

### Deterministic preparation comparisons — 2026-09-25

mechanics.prepared_comparisons derives additional ComparisonRequests from an
existing base contract and reviewed socket preparations. The first supported
transformation changes only the empty socket count after deterministic Larzuk.
Optional immutable preparation evidence distinguishes this request from the
previous unannotated hypothetical placeholder. Request grouping includes that
evidence; current and prepared cohorts remain separate. The repository reads
each name once. evaluate_requests keeps price_estimate unavailable for prepared
items and writes separate outcome_ask_estimate/outcome_comparisons. Presentation
labels those as after-action asks; pipeline selection still requires the observed
current request. Additional transformations remain planned.

### Cube outcome comparison extension — 2026-09-25

The socket comparison builder also accepts ordinary normal-quality cube actions,
preserving every cap-dependent success weight and item-level uncertainty. Request
identity includes the action and target count, keeping Larzuk and cube routes
distinct even when they reach the same market variant. The prepared_prices
presenter owns action-specific labels, costs and probabilities; sections delegates
to it. The exact outcome contract changes only empty sockets. Successful-outcome
asks never become an expected value, current price, or profit estimate.

### Clearing base sockets — 2026-09-25

mechanics.cleared_comparisons builds a prepared contract from the existing bounded
compare_equipment_sockets contribution proof. It projects the adjusted native
values into outcome market properties without modifying observed facts or their
raw/value provenance. A zero residual removes only that affected property; other
rolls remain exact. Socket count is conserved, contents and payload become empty.
Preparation evidence retains resources and destroyed filler identities. This
branch is restricted to normal/superior bases with a valid current contract;
runewords and named/affixed transformations require their own handling.

### Named and affixed clearing — 2026-09-25

cleared_item_request now selects the existing contribution proof by policy:
base/affixed equipment comparison, or named-definition socket comparison. Named
identity resolution and the original current-contract gates precede projection.
For named items, fixed_properties runs against the derived innate values and
updated market properties to restore intrinsic bonus evidence obscured by fillers.
The original raw capture is not rewritten. Affixed outcomes retain their residual
rolls. Base, affixed and named price requests all remain prepared; the root price
and tier selection still require an observed request. Runewords are excluded.

### Item-level preparation input — 2026-09-25

The capture adapter passes explicit item_level into ItemFacts, whose constructor
normalizes invalid values to unknown. Preparation selects a bracket from the
existing pinned recipe caps before creating action records. Derived normalization
facts explicitly carry item_level1. Native extraction of this field is still
unimplemented; current captures preserve their conditional socket analysis.

### Conditional Larzuk requests — 2026-09-25

The prepared request builder accepts conditional Larzuk actions when at least one
reviewed cap gives the target count. The full outcome alternatives and item-level
precondition stay attached. Presentation explicitly marks a conditional quote and
lists possible counts; it does not average them or treat them as random odds.
Impossible targets remain excluded. Native item-level offset research remains
unresolved, so current capture uncertainty is preserved.

### Quality-specific quest socket requests — 2026-09-25

mechanics.quality_sockets handles unsocketed named/affixed contracts separately
from runeword-base routes. It resolves exactly one portable socket_potential rule
for the base code, applies item level and quality caps, and emits a request per
possible empty socket count. larzuk_magic distinguishes random quality outcomes
from cap uncertainty; immutable preparation evidence retains odds and resources.
The existing evaluator and repository keep these cohorts separate from the current
item and from one another.

### Immutable market-result boundary — 2026-09-25

The market repository now exposes compare_request_results, backed by pure
evaluate_request_results. ComparisonResult is a frozen domain object for grouped
requests and separate current/prepared estimates. The dictionary compatibility
APIs and pipeline serialization share adapters.comparisons. The pipeline selects
current observed evidence from typed state/IDs, retaining the existing mutable
report aliasing only within that detached projection. This removes result mutation
from domain evidence; nested price-policy details and the combined post-market
assessment still need full v2 types.

### Weapon upgrade contracts — 2026-09-25

mechanics.upgrade_comparisons consumes the engine's verified UpgradePaths and
existing complete weapon contract. It preserves roll/payload constraints while
changing the market base identity, yielding one request per target with immutable
ordered preparation evidence. Named and rare paths keep their respective recipe
IDs. The market pipeline prices the target state independently; it never promotes
an outcome quote to the observed item's estimate. Armor needs a rolled-defense
outcome model and is not projected by this builder.

### Combined post-market boundary — 2026-09-25

Pricing finalization has moved out of pipeline dictionary assembly into pure
assessment.pricing.finalize_assessment. Domain PricedAssessment combines the
updated typed assessment and comparison results with immutable selected price
evidence. adapters.priced owns the report projection. Original inputs are retained
unchanged; current comparison notes are replaced immutably in the finalized
comparison tuple. Prepared-outcome estimates never enter current-price selection
or the named tier fallback. Nested policy details remain mappings.

### Finite armor defense outcomes — 2026-09-25

`mechanics.upgrade_defense.with_defense_outcomes` enriches immutable UpgradePaths
after the current comparison contract is validated. It combines published target
base bounds with preserved named-item modifiers, retaining every reachable total
after integer rounding. The optional frozen `defense_outcome` field is omitted
from legacy projections when unsupported. No observed facts or current contract
are changed. Armor market comparison builders must consume these outcomes as
hypothetical states; they are not implemented yet. Ethereal and variable/per-level
flat-defense calculations still require additional mechanics evidence.

### Armor upgrade market requests — 2026-09-25

`mechanics.armor_comparisons` consumes verified finite UpgradePath outcomes. Each
reachable defense receives a separate immutable prepared request and segment.
The shared upgrade_action builder retains ordered steps and cumulative resource
costs for weapon and armor requests. The existing evaluator reads cached rows
once per name and applies exact contracts independently, with hypothetical
estimates isolated from observed current pricing. Presentation names the target
and exact defense roll. It does not pool the range or compute expected value.

### A9 base suitability presentation boundary — 2026-09-25

New reports render base suitability and its semantic colors from
assessment.base_uses. Retrieval no longer duplicates those results under
base_assessment.uses. The engine remains the sole evaluator; the integration test
checks one call and one serialized suitability location.

base_summary bridges current reports and archives: an explicitly empty current
base_uses cannot revive an obsolete suitability claim. Reports without that field
retain their older presentation. Generic base_assessment.recipes remain separate
recipe evidence, not suitability: the saved Runic Talons still lists conditional
recipe options despite unverified socket contents and no reviewed base-use role.
This preserves known utility while refusing stale fit judgments. Text, Rich, OSD
and compatibility tone lookup use the same selector. Broader v2 schema/facade
migration and all-item coverage are still incomplete.

### A8/A9 normalized discovery facets — 2026-09-25

Pipeline identity/property discovery now uses the already-normalized assessment
facts through adapters.discovery. Native class/tree/staffmod/oskill/element/aura
queries use decoded native identity and its verified market property, independent
of display labels. Unresolved rows and conflicting native projections do not
supply search facets. Conflicts remain explicit assessment gaps; the original
extraction retains supplied properties for review. OCR without native stats keeps
its supplied candidate facets and class-only discovery, but cannot form a native
comparison contract or promote search candidates to prices.

Removed pricing/knowledge/comparisons.py after migrating its last production
caller. This eliminates the direct mutable appraisal-properties.json read and
process-wide display-label cache from live discovery. The native projection
catalog continues through the pinned artifact snapshot. No extra normalization
or alternative price evaluator was added. Remaining v2/facade and all-item
coverage work is not claimed complete.

### A1/A11 import facade removal — 2026-09-25

Migrated all39 Python caller files (6 production,33 test files) away from the
assessment.models and assessment.normalize compatibility modules. Contracts/facts
now import directly from domain.contracts/domain.facts; normalization and base
metadata helpers import from adapters.capture. Removed both re-export-only files.
Repository-wide Python/import-reference audit finds no remaining consumers.

Existing capture/runeword regression collection first failed on the removed paths,
then passed after migration; no substitute test-only facade was added. This is
import-boundary cleanup, not a change to mechanics, market rules or capture
normalization. Runtime report-schema compatibility and the unused valuation stub
remain separate migration work. The full A1–A11 and all-item policy rollout are
not complete merely because these two facades are gone.

### A11 unused valuation entry removal — 2026-09-25

Removed pricing.knowledge.valuation.estimate_price after verifying it had no
production callers. It was a disabled compatibility stub that always returned
no estimate; its tests did not exercise current pricing. The migrated guards now
use retrieve_draft with real SQLite evidence and an exact three-seller positive
control, then reject name-only asks, facet summary rows and incomplete native
capture. The existing historical-base pipeline regression now explicitly asserts
no numerical estimate. The unrelated same-base price display guard moved to the
appraisal text suite unchanged.

No price policy was loosened or replaced. Assessment contracts, scoped comparisons
and finalization remain the active pricing path. Code-reference audit finds no
remaining import or caller of the removed API. Report-schema compatibility,
remaining architectural gates and full item/build/market coverage are separate
unfinished work.
