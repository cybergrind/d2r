# Offline item assessment implementation plan

Date: 2026-09-24. Status: implementation in progress; see the verified
[coverage and remaining work](STATUS.md). Scope: Softcore / Non-Ladder / PC / RotW, Ist = 1.

**Next priority — 2026-09-25:** [offline guide-first assessment](GUIDE_FIRST.md).
Process every cached build, variant and player/mercenary item first; deduplicate
item demand across distinct builds; compile guide-derived use/stat configurations;
then publish compact grouped Build use reports. G1–G5 is the next delivery order.
Existing architecture and all-item coverage obligations remain in force.
Use the [acceleration strategy](GUIDE_FIRST.md#acceleration-strategy--complete-inventory-incremental-reviewed-rules):
complete the global inventory, deduplicate semantic rules, reuse reviewed family
templates, then deliver bounded batches with an explicit long-tail coverage queue.
Every base/use needs a rule assignment, not a separate evaluator class. Price
research does not block reviewed usefulness; partial releases do not satisfy final
all-item/tier completion gates.

## 1. Outcome and coverage contract

For an identified item, answer: what is it useful for, which builds and variants
want it, what makes this particular roll desirable, what is missing, and what can
be concluded about trade value from offline evidence? Highlight useful leveling
items even when their trade tier is low or trash. Keep price, usefulness and roll
quality separate. A perfect irrelevant stat must not make an item look expensive.

Deliver a deterministic decision tree plus composable handlers inside the existing
`pricing/knowledge/assessment/` submodule. Extend the current implementation rather
than create a second assessment engine. Every supported item resolves to one primary
policy and zero or more independent use cases. Collections are explicit named sets
of identities/types; one item can participate in several use-case collections.

Before implementation, freeze these inventories:

- Every enabled game base, named unique/set identity and runeword definition.
- Every cached build, every variant, player/mercenary slot, swap/prebuff item,
  socket filler, item alternative and generic affix pattern.
- Every curated leveling recommendation and unresolved research candidate.
- Explicit exclusions: disabled/quest-only objects, unavailable mode/version,
  unendorsed planner experiments, ambiguous identities. Exclusions need reasons.

The companion [inventory](INVENTORY.md) enumerates the current cached builds,
base families and named-item review queue. It is a source census, not a claim that
all those items already have executable rules or current prices.

Audit baseline: 33 builds, 114 planners, 719 planner profiles, 60,491 demand rows;
10,711 recommended occurrences with 3,063 unresolved occurrences / 1,406 labels.
The existing demand audit also records an unavailable planner and prose candidates.
523 weapon/armor bases: 431 unresearched, 48 with cached observations only, 44 with
historical buckets. There are 573 prepared named facts and 75 reviewed recommendations.
Counts have different denominators; none establishes complete assessment coverage.

## 2. Decision tree

The detailed [build-aware decision tree](DECISION_TREE.md) is the authoritative
routing design. [BUILD_ROLES.md](BUILD_ROLES.md) maps all 33 cached builds and 116
structured source-variant entries to its branches. These entries are not 116
independently validated setups: some are deltas, aliases, conflicts or planner-only.

```text
Known item facts (preserve unknown fields)
  → ONE mechanics policy: runeword / set / unique / base / affixed family
  → ALL applicable role candidates:
      player: spell / weapon attack / special delivery / aura-minion / support
      mercenary: Act 1 / Act 2 / Act 3 / Act 5 single-sword / Act 5 Frenzy
      swap-prebuff-charges / socket payload / MF-GF / leveling
  → actual build variant + legal slot + alternatives
  → eligibility → defining mechanism → required modifiers
  → sockets/ethereal/preparation → companion/loadout dependencies
  → relevant roll quality and suitable alternatives
  → independent usefulness, trade tier, leveling tier and offline price
```

A first-match role tree is insufficient: one item can serve several roles. Reuse
predicate nodes, preserve independent role outcomes, and never add unrelated scores.
Unknown fields defer dependent branches instead of discarding every known use.
An impossible Grief base can still be a useful socket platform or other recipe base.

The detailed tree contains player subtrees, all observed mercenary types, family
support branches, role-dependent base evaluation, named tier overlays and source
conflict handling. Numeric planner targets are not required minima until reviewed.
Hardcore-origin utility remains a separate review context; pricing stays SC/NL.

## 3. Concrete implementation architecture

[ARCHITECTURE.md](ARCHITECTURE.md) is the implementation specification: exact package
layout, existing-file migration map, typed domain contracts, handler interfaces,
predicate semantics, data authoring/compiler/publication, pipeline integration and
test boundaries. Its A1–A11 changes remain implementation units; GUIDE_FIRST G1–G5 now determines
initial delivery order. DECISION_TREE section J retains later regression slices.

Architectural decisions:

- Extend `pricing/knowledge/assessment/`; one pure assessment engine, injected
  definitions/rules/context, and an indexed multi-role evaluator.
- Frozen dataclasses/enums/Protocols in the domain; a validated typed predicate AST
  and tracked JSON for reviewed build, tier, leveling and comparison policies.
- Quality handlers compose with family strategies; complex mechanics use tested
  Python functions. Named items normally use data records, not individual classes.
- Capture adaptation, artifact loading, market SQL and presentation stay outside
  the pure engine. Existing native decoding and strict price gates are preserved.
- One versioned structured result feeds terminal and OSD. Multiple comparison
  requests retain distinct role segments; current facts and hypothetical prepared
  states never mix in price estimates.
- Compile and validate a complete artifact/index generation before atomic
  publication. Each appraisal pins one generation; caches are generation-keyed.
- Migrate in small green changes, then remove temporary compatibility facades and
  the old independent base-use path. Do not maintain two assessment implementations.

Start with GUIDE_FIRST G1–G3 using existing extraction and role infrastructure;
make only the schema/mechanics changes needed to compile reviewed guide evidence. Complete tier coverage and
all remaining build families before declaring the broader rollout finished.

## 4. Build and item inventory comes first

[GUIDE_FIRST.md](GUIDE_FIRST.md) expands this into the required G1–G5 sequence,
with deduplicated demand grading, item-centric review and compact reporting.

1. Join `wp-a-builds.json`, all `wp-a-variants/*.json`, cached guide sections,
   referenced planner profiles, `appraisal-demand.json`, base/runeword research,
   valuable-item watch records and leveling recommendations.
2. Import variant prose and slot arrays, not just planner links. Retain all
   alternatives, substitutions, mercenary act/type, starter/endgame stage, swap,
   prebuff, Ubers, farming and budget contexts. Preserve original labels.
3. Resolve decorated named items and composite labels into structured identities,
   base variants, desired mods, sockets and fillers. Keep AND vs OR choices explicit.
   Resolve generic patterns (for example a skill/FCR circlet) into family predicates.
4. Each source occurrence gets a disposition: executable reviewed role, duplicate
   of a role with retained provenance, discovery-only, excluded with reason, or
   unresolved with an owner. No dropping unknown strings or taking only top N.
5. Whole-character priorities are context; extract item-slot requirements separately.
   Planner association alone is not endorsement. Record dependencies on other gear.
6. Produce matrix: build × variant × side × slot × item alternative → policy ID.
   Track raw source occurrences separately from deduplicated executable rules.
7. Reconcile all 33 builds, including those without a dedicated variant JSON.
   Unavailable planner `1r010653` stays a visible source gap. Review existing prose
   candidates (Bane's Oathmaker, Bane's Wraithskin, Crafted Cold Rupture, Death Cleaver).

Gate: every cached occurrence accounted for; no unreviewed discovery record is
presented as a verified build requirement. Missing source downloads do not prevent
work on cached evidence and do not silently count as complete coverage.

## 5. Base and affixed-item handler inventory

The exhaustive family/base names are in INVENTORY.md. These branches require
explicit strategy or policy treatment, including every normal/exceptional/elite
member in the verified family:

| Branch | Dedicated logic / important conditions |
|---|---|
| Circlet, Coronet, Tiara, Diadem | Class/tree skills, FCR, FRW, sockets, attributes, resists; magic vs rare affix limits; low-level variants |
| Assassin claws | Base speed, staffmod eligibility, skill combinations, IAS and sockets; Greater Talons/Runic Talons/Feral Claws/Suwayyah etc. must not be interchangeable |
| Warlock daggers | Kris alias resolution, Cinquedeas, Legend Spike and all dagger bases; staffmods, physical vs caster roles, sockets, ethereal and Void variants |
| Warlock grimoires | Entire book family; inherent/staffmod combinations, block/defense/requirements and recipe eligibility |
| Sorceress orbs | Class/tree/staffmod combinations, FCR, mastery and relevant skills; separate magic/rare combinations |
| Staves | Staffmods, two-handed opportunity cost, charges/prebuff, recipe sockets and low-requirement variants |
| Wands | Staffmods, class/tree skills, charges, sockets and recipe eligibility per actual base |
| Scepters | Paladin skill combinations, aura/prebuff vs attack roles, sockets and recipe eligibility |
| Druid pelts | Class/tree plus individual skills, sockets, life/resists; physical vs caster forms |
| Barbarian helms | Warcries/prebuff vs attack roles, staffmods, sockets and requirements |
| Paladin shields | Inherent all-resist vs ED/AR branches, block, defense, strength, ethereal and socket outcomes; all 15 bases |
| Necromancer heads | Staffmods/inherent bonuses, class skills, block, sockets, recipe eligibility |
| Ordinary shields | Monarch dedicated Spirit/affix policies; Troll Nest, Ward and early shields have different requirements/socket ceilings |
| Mercenary polearms/spears | All eligible bases; elite comparison includes Thresher, Giant Thresher, Cryptic Axe, Great Poleaxe, Colossus Voulge, Ogre Axe, Mancatcher, War Pike, Ghost Spear etc.; recipe legality first |
| Amazon spears/javelins/bows | Inherent skills, exact weapon family, ethereal/replenish where applicable, socket legality, speed and player/merc equip legality |
| Ordinary bows/crossbows | Speed/damage/requirements, sockets, player vs Act 1 mercenary role; no invented ethereal variants |
| Swords | Phase Blade indestructibility and recipe sockets; Crystal/Broad/Long Sword starter roles; Act 5 and two-handed alternatives; explicit upgrade implications |
| Axes/maces/hammers/clubs | Berserker Axe vs alternatives, Flail/Knout/Scourge caster bases, physical damage/speed/requirements, indestructible/repair recipes |
| Throwing weapons | Damage, IAS, quantity/replenish and ethereal roles; no socket/runeword branch |
| Body armor | All bases; armor weight/requirements, defense roll, superior EDef, ethereal, socket potential, player vs merc use |
| Ordinary helms | Two/three-socket and other legal outcomes, requirements/defense, early player vs mercenary recipes |
| Rings | Caster vs attack combinations, FCR, AR/leech, life/mana/stats/resists; crafted fixed contributions |
| Amulets | Skill class/tree, FCR and crafted limits, requirements, life/mana/stats/resists; no universal sum-of-stats score |
| Gloves | Skill/IAS and crafted attack properties, attributes/resists; caster crafting roles separate |
| Boots | FRW/FHR/resist combinations, stats, MF/GF; kick damage and upgraded requirements |
| Belts | FHR/life/stats/resists, crafted properties, belt capacity and requirements |
| Small/Large/Grand charms | Exact size, tree/skill identity, paired affixes, resistance/life/damage/AR/MF, equip level, top-tier roll ceilings |
| Jewels | IAS/ED/damage/resist/requirements combinations, magic/rare legality, socket target and low-level use |

All 62 curated WP-A bases receive explicit records in the first base-policy pass;
this is only a seed, not the final list. Include every additional base mentioned in
variant prose/planners and every legal alternative in the definition tables.
Ordinary unmentioned bases still get a valid family assessment; absence from the
curated list is not evidence of no demand.

## 6. Socket, ethereal and preparation mechanics

- Model total, filled and empty sockets separately, with known contents. Unknown
  is distinct from zero. Runewords require the correct total and legal base/quality.
- For unsocketed items, derive Larzuk and cube outcomes from base, quality and ilvl
  caps. Show legal counts, method and sourced probability where known. Capped dice
  are not uniform over the remaining outcomes. Unknown ilvl produces conditional
  outcomes, not a guaranteed socket count. Superior and low-quality restrictions
  must be explicit; normalization recipes can change ilvl and subsequent outcomes.
- Existing socket count cannot be reduced. Clearing contents destroys the fillers;
  describe only as an optional preparation path, never modify the user's item.
- Separate ready-to-use, preparable, conditional and impossible-for-this-recipe.
  Price the observed item; do not price it as the best possible future outcome.
- Ethereal policy is per use: preferred, acceptable, detrimental, impossible or
  unknown. Include mercenary durability, self-repair/replenish, indestructibility,
  socket investment and upgrade outcomes. Sets have no natural ethereal variant.
- No universal ethereal or superior multiplier. Defense/damage calculations need
  sourced rounding, base roll and upgrade semantics; captured total is not the
  original base roll when contributions cannot be separated.
- Best-base verdict requires a named recipe and role. Compare legal alternatives
  for damage/speed, requirements, relevant staffmods/inherent bonuses and socket
  readiness. IAS/loadout-dependent winners remain conditional. Distinguish
  “perfect roll of a preferred base” from “best base for this loadout”.

Gate examples: unsocketed superior Phase Blade cannot be prepared as five-socket
Grief; four total sockets with one filled is not four empty; unknown ilvl cannot
promise four sockets; ethereal mercenary candidate differs from player caster use.

## 7. Unique/set trade tiers and dedicated strategies

Every enabled scoped unique and set item gets an explicit reviewed default tier:
**high, med, low, trash**. No missing-record-to-trash fallback. During development,
review state may be pending; complete publication requires all eligible identities
assigned, with separately counted exclusions and unresolved identity gaps.

**Mandatory exhaustive coverage (2026-09-25):** enumerate every unique item,
every set and every member piece from the complete scoped game-definition census,
including RotW additions. This is not a watchlist, build-mention sample or a review
of only valuable items. Every unique and every set piece must have a reviewed
**high / med / low / trash** trade tier and a separate **leveling** assessment
(**high / med / low / none**, with class/stage/conditions). Every set must additionally
have its overall usefulness tier and set-level leveling assessment. Leveling is
independent: an item can be trash for trade and high for leveling.

Completion requires a census-to-policy coverage check with zero missing or pending
required tier records. During work, preserve unknowns as blocking review gaps;
never fabricate trash/none to reach full coverage. Report unique, set and member-piece
coverage separately, with every excluded identity and scope reason enumerated.
The examples below are acceptance fixtures, not limits on which items get reviewed.

Tier meanings: high = premium/chase trade segment; med = established useful trade
segment; low = modest/niche trade segment; trash = reviewed negligible ordinary
trade priority. These are qualitative trade labels, not fixed Ist values. Set
numeric boundaries only if supported by reviewed NL data; never import ladder
prices or translate build tiers directly into price tiers. When evidence is too
weak, keep the record pending rather than invent a tier to pass coverage.

Each record stores default tier, conditional tier overrides, important roll IDs and
ranges, ethereal preference, sockets/upgrade conditions, build uses, leveling uses,
source dates and review rationale. Price evidence remains separately dated and may
be unavailable even when the qualitative tier is reviewed. Default trash does not
suppress leveling or set-combination highlights. A perfect/ethereal/collector
exception must be reviewed before applying an aggregate trash policy.

**Sets:** one SetHandler is sufficient, driven by per-piece data and explicit
partial/full-set rules. Distinguish standalone piece, useful combination and full
set. Sazabi mercenary, Angelic attack-rating combinations, Death's leveling pair,
Sigon's, Isenhart's and other leveling sets, Tal Rasha, Trang-Oul and other build
sets must preserve actual companion requirements. Do not infer equipped companions
from a hover. Bundled set market listings cannot price an individual piece.

**Required set and piece tiers (2026-09-25):** every eligible set item must
expose two separately reviewed assessments, linked by canonical set and piece IDs:

- **Set tier:** overall usefulness of the full set and explicitly named useful
  partial combinations, including whether and where they are used by builds or
  mercenaries. Include a separate **set leveling tier** with class, progression
  stage, equip requirements and companion conditions. Record reviewed absence of
  use separately from unknown/pending evidence; a build tier is not a trade tier.
- **Piece tier:** the individual item's trade tier, with its own standalone uses,
  contribution to useful set combinations, rarity/scarcity evidence and relevant
  roll premiums. Keep its individual leveling assessment separate from the set's
  conditional leveling value. Never copy the overall set tier or a sibling's
  price onto every piece.

The report must show both labeled tiers plus leveling context for every set item,
including low/trash pieces; missing review stays explicit. Sources and review dates
belong to each assessment. Rarity alone does not establish demand or a numeric
price, and whole-set listings cannot establish an individual-piece estimate.

**Acceptance example:** use the user's Immortal King armor example to require a
comparison of Immortal King's Soul Cage against the other pieces. The model must
preserve the armor's separately evidenced rarity/value premium instead of assigning
all pieces the same tier because they belong to one set. Review the exact tier and
any price from scoped evidence; this requirement does not assign a new market band.
Acceptance fixtures must also cover a useful leveling combination with a low-trade
piece, a standalone useful piece from a weak set, and unknown set/piece evidence.
Coverage audits count reviewed sets, set-level leveling assessments and reviewed
individual pieces separately; one complete dimension cannot hide another's gaps.

**Uniques:** start the dedicated-review queue with these collections; exact tier
assignments remain an implementation/research deliverable, not asserted here:

| Collection / identity strategies | Why ordinary generic matching is insufficient |
|---|---|
| Griffon's Eye; Death's Web; Death's Fathom; Ormus' Robes | Skill/mastery/resistance rolls and specific skill identity interact |
| Andariel's Visage; The Reaper's Toll; Vampire Gaze; Crown of Thieves | Mercenary roles, ethereal, leech/defense/damage and socket investment |
| Titan's Revenge; Thunderstroke; ethereal melee weapons | Physical vs elemental roles; replenish/repair/indestructibility differs by identity |
| Crown of Ages; Harlequin Crest; Skin of the Vipermagi; Guardian Angel | Defense/EDef, socket count and important defensive rolls; upgrading/merc roles |
| War Traveler; Chance Guards; Goldwrap; Skullder's Ire | MF priorities vs other rolls, per-level effects, ethereal/repair where applicable |
| Arachnid Mesh; Magefist; Sandstorm Trek; Waterwalk; Gore Rider | Fixed utility versus roll premiums, durability and player role |
| The Stone of Jordan; Bul-Kathos' Wedding Band; Mara's Kaleidoscope; Raven Frost; Wisp Projector | Named jewelry, important roll combinations, no raw-base jewelry pricing |
| Annihilus; Hellfire Torch; Gheed's Fortune; sunder variants; Rainbow Facet | Coupled rolls, class/element/trigger identity, penalties where lower is better |
| Demon Limb; Naj's Puzzler (via SetHandler); other charged utility items | Charges/prebuff/teleport utility independent of equipped combat stats |
| RotW identities: Sling, Opalvein, Wraithstep, Ars Dul'Mephistos, Bane items | Version-specific roles/rolls; resolve all source aliases and cached new identities |
| Other high/med identities | Identity-specific policy records; add Python strategy only for distinct mechanics |
| Reviewed low/trash identities | Shared engine with explicit tier records, roll exceptions and leveling overlay |

Expand this list from **all** named demand/watch records in INVENTORY.md and the
full game census. Do not limit bespoke review to these examples or current watch
membership. Review perfect-roll, upgraded, ethereal and socketed variants separately.

## 8. Leveling tier and reporting

Independent leveling tiers: **high, med, low, none**, scoped to class/archetype,
player/mercenary, equip requirements, progression stage and companion conditions.
High means a desirable leveling keeper; med means a useful role-specific option;
low means a temporary fallback; none means no reviewed leveling role. Pending
research is not silently none. Equip level is not the end of useful lifetime.

Seed from all 75 reviewed recommendations and then resolve the remaining candidates.
Explicit cases include Death's Guard/Hand, Angelic pieces, Sigon's pieces,
Bloodfist, Stealth/Lore starter bases, and other named recommendations. Check actual
requirements, upgrades and set conditions before asserting the item can be equipped.

Report examples (format contract, not new price claims):

- `Set tier: [reviewed usefulness] — [full set / named combination; build or mercenary role]`
- `Set leveling: [reviewed tier] — [class/stage; required companions]`
- `Piece trade tier: med — [piece-specific demand, scarcity and roll reason]`
- `Trade tier: med — [specific roll/variant reason; non-set items]`
- `Leveling: high — attack builds; [level/requirements]; needs Death's Guard`
- `Use: Echoing Strike / Ubers / Act 5 mercenary — Sazabi set; companions required`
- `Base: preferred for [recipe/role] — [ethereal/mod/socket reason]`
- `Needs: [socket outcome or important missing mod]`

Use distinct labels plus visible tones for valuable trade items, desired leveling
keepers and conditional preparation. Retain blue/green/red ethereal semantics.
Stat roll green/red remains separate from whole-item value. Terminal and OSD share
structured results; no repeated generic warnings, coverage paragraphs or boilerplate.

### 8.1 Combination-aware stat indicators — required, planned 2026-09-25

Apply this contract to every supported base, magic and rare item family. Evaluate
all captured item facts together against reviewed use configurations before assigning
stat indicators. A prioritized list of individually useful stats is insufficient:
mandatory combinations, alternatives, thresholds and disqualifiers decide whether
the item actually fits a use. Do not turn stat counts or dot colors into prices.

**Evaluator:** add a pure `StatsEvaluator`, composed into the existing role engine,
with `evaluate(item, configurations: Sequence[StatConfiguration], context)` returning
`StatEvaluation`. Reuse canonical StatKeys, typed predicates, mechanics and role
outcomes; do not implement a second predicate engine or separate presentation rules.
Family-specific evaluators are needed only for distinct mechanics; reviewed
configurations carry ordinary family/build differences. Compile/index configurations
by base/family/quality so the hot path evaluates only applicable configurations.

Each immutable, validated configuration contains:

| Field | Contract |
|---|---|
| Identity and applicability | Stable ID/version; linked role; base/family, quality, class/build, player/mercenary, stage and version selectors |
| Required combination | Typed `all` / `any` groups, required thresholds, exclusions and dependencies; each required group must pass for a confirmed match |
| Prioritized stats | Ordered priority groups of semantic stat selectors; each member is essential/desirable or supporting/good, with its own activation predicate and explanation |
| Interaction rules | Explicit conjunctions and alternatives: a stat may become desirable only with another stat or within a matched recipe/build role |
| Roll policy | Source-backed range/affix context, higher/lower/target direction, breakpoints and reviewed good/bad bands; unknown bounds remain unknown |
| Provenance | Source IDs/dates, review state and rationale; unresolved rules cannot produce confirmed indicators |

Priority orders explanations and role-relevant preferences. It never compensates
for a missing mandatory stat, silently defines a minimum, or mixes stats from
incompatible configurations. A single item may match several complete configurations;
retain each result and its reasons, including leveling roles.

**Evaluation sequence:**

1. Resolve observed base/quality, normalized modifiers, sockets/contents and other
   mechanics. Distinguish missing from unknown using capture completeness. Preserve
   per-level, skill-specific and derived-stat semantics and contribution provenance.
2. Select applicable reviewed configurations and evaluate complete combinations
   using existing true/false/unknown/not-applicable logic. Return matched,
   conditional, failed or unknown with unmet groups. A required unknown cannot pass.
3. Within each confirmed match, assign green dots to present, activated desirable
   stats and blue dots to present, activated supporting stats. A required threshold
   must actually be met. Optional preferences never rescue a failed configuration.
4. Produce a short explanation for incomplete combinations, e.g. “Needs companion
   stat Y at the configured threshold.” Do not award confirmed green/blue dots just
   because X would be valuable if Y existed. Another independently matched use can
   still justify a dot on X. Missing stats belong in the explanation, not fake rows.
5. Across matched configurations, use the strongest justified dot per displayed
   stat (green before blue), retaining every contributing configuration ID. This
   is a presentation union of valid uses, not a synthetic combined build. Show role
   labels/details when necessary to explain different uses.
6. Assign grey dots only to stats reviewed as irrelevant/trash for the evaluated
   uses with adequate configuration coverage. Failed combinations alone do not
   prove a stat worthless in every role. Unreviewed families, unknown facts or
   unresolved conditional relevance get a neutral question marker/uncolored text,
   never automatic grey. A grey stat does not imply a trash item.
7. Evaluate roll quality independently, then map semantic annotations to captured
   stat lines. Duplicate/split/combined lines retain contribution mappings; unresolved
   line attribution stays uncolored rather than assigning an unrelated dot.

**Two visual channels:** a dot before the stat conveys desirability — green
“desirable”, blue “good/supporting”, grey “irrelevant/trash for reviewed uses”. Stat
text conveys roll quality — green for a good roll, red for a bad roll, default for
intermediate/fixed/unknown. Thus a desirable stat with a poor roll can have a green
dot and red text; an irrelevant stat rolled perfectly keeps its grey dot. Prefer
coloring the numeric value/range portion to keep the stat name readable. Include
text labels/legend and plain-text equivalents; do not rely on color alone.

Roll quality must use the correct base/quality/affix/ilvl context and source-backed
bounds, not a universal percent-of-maximum formula. Respect lower-is-better values,
fixed stats, breakpoint/target behavior, upgraded bases and aggregate contributions.
Report intrinsic roll position separately from whether a build minimum is met; a
maximum roll does not satisfy a different missing requirement. An unknown range or
ambiguous contribution gets no good/bad claim. Whole-item trade/leveling tiers and
existing ethereal indicators remain independent from both stat visual channels.

**Delivery and acceptance:** first compile configuration/result contracts, then
implement the evaluator against existing role outcomes, then add terminal/OSD
rendering and migrate every base/magic/rare family. Publish source-reviewed
configurations with the existing atomic generation and cache invalidation system.
Audit family/configuration coverage; unknown families cannot inherit trash dots.
Acceptance fixtures must cover:

- Required X+Y present versus X alone, Y below minimum, and Y unknown.
- Alternative valid combinations and an exclusion that defeats otherwise good stats.
- Many supporting stats failing to compensate for a missing required stat.
- Two individually incomplete configurations never merging into a valid one;
  multiple independently matched roles retaining their own explanations.
- Preferred base/socket/staffmod combinations, including current versus hypothetical
  socket preparation; no confirmed current-state dot based only on a future item.
- Desirable stat with a poor roll, irrelevant stat with a perfect roll,
  lower-is-better and breakpoint rolls, fixed values and unknown ranges.
- Duplicate/combined display lines, incomplete capture, unknown configuration
  coverage, and consistent semantic output across terminal/OSD/plain text.

All exact game-specific thresholds and rarity/value claims need reviewed sources;
X/Y fixtures express policy behavior without inventing item requirements. This is
a planned requirement, not a claim that the current renderer/evaluator implements it.

## 9. Step-by-step delivery and acceptance gates

| Step | Deliverable | Required evidence before moving on |
|---|---|---|
| 0 | Freeze baseline and existing saved-item reports | Current targeted tests pass; record known wrong/missing assessments |
| 1 | Complete source/identity/variant inventory | Every build/variant/side/slot occurrence has a disposition; all enabled bases and named identities enumerated |
| 2 | Schema, registry and isolated module structure | Deterministic dispatch, overlap/unknown tests; existing results preserved during moves |
| 3 | Shared socket/ethereal/requirements/upgrade mechanics | Boundary-ilvl, quality, filled-socket, unknown-fact and recipe legality tests pass |
| 4 | Clean bases + recipe/role policies | All 62 seed bases plus variant additions reviewed; useful preparation and best-base claims tested against alternatives |
| 5 | Complete unique/set default tier catalog + common handlers | Every eligible identity has a reviewed tier or a blocking pending-review entry; no automatic trash assignment; set companions conditional; separate set-use, set-level leveling and piece trade assessments |
| 6 | Specialized unique collections and variant premiums | Important rolls/ethereal/sockets/upgrades change the correct segment; unrelated perfect rolls do not |
| 7 | Affixed families: class weapons, circlets, jewelry, charms/jewels, armor/accessories, remaining weapons | Each inventory branch has reviewed combinations and positive/negative examples across qualities; §8.1 evaluates mandatory groups before stat desirability |
| 8 | Build-role and leveling coverage expansion | All cached variants revisited against implemented handlers; all leveling candidates resolved or explicit source gaps |
| 9 | Family-specific market contracts | Exact identity/role/premium facets enforced; reviewed secondary-roll bands only; no generic tolerance or score-to-Ist conversion |
| 10 | Concise terminal/OSD integration | Trade/leveling/base-preparation highlights agree; desirability dots and roll text are independent and consistent under §8.1; unknown price doesn't erase useful assessment |
| 11 | Offline publication + regression audit | Full relevant suite green, all saved items replayed, deterministic artifacts, no network dependency, coverage denominators reported |

Within each step use red → green → refactor around real behavior. Each handler
needs at least a useful item, a superficially similar unsuitable item, and an unknown
required-facet case. Use captured items where available and source-backed synthetic
cases for missing variants; do not write tests that merely restate registry tables.

Regression matrix: Dread Edge, Storm Gyre, Dire Song, Greater Claws, superior Phase
Blade, Cryptic Axe, Spirit Monarch, Insight Bill, Guardian Angel, Shako, Tancred's
Crowbill, Sazabi's Mental Sheath, Hellplague, open-socket Runic Talons, Authority,
and both life charms. Preserve raw captures and separate screenshot truth.

Market tests: wrong economy, stale data, duplicate sellers, different skill identity,
extra premium affix, wrong ethereal, unknown contents, upgraded vs original base,
set bundle vs piece, and completed recipe vs empty base. Preserve existing dated
seller/dispersion gates unless a separately reviewed policy changes them. Add real
eligible matches as well as rejection tests. Thin/no data is not a trash verdict.

Completion means: every eligible identity has deterministic routing; all cached
recommended source occurrences are accounted for; every scoped unique, set and set
member has all required reviewed tiers, with no missing/pending census identities;
leveling desirability is visible; all important roll/ethereal/socket variants have
explicit policies or disclosed source blockers. Document unresolved blockers instead
of claiming universal knowledge. No live probes or market collection needed to
start; request new evidence only for a specific gap the cached sources cannot solve.

## 10. Maintenance and next session

Implement GUIDE_FIRST G1–G5 first: complete offline occurrence census, deduplicated
demand grades, item-centric guide policies, compact Build use and validation. Reuse
existing functionality; introduce schema/compiler work only as needed. The table
above is a capability/completion checklist, not a competing delivery order. Resume
DECISION_TREE section J regression slices afterward; retain all-item and leveling gates.
Extend the existing update-kb workflow to regenerate inventories, review changed
source hashes, validate tier/role completeness and atomically publish a consistent
artifact/index generation. Missing artifacts keep the last valid generation usable.
A new game item or build variant creates a review task rather than inheriting trash.
Keep a dated coverage diff and fixture results with each publication.

References: ../README.md, ../../ASSESSMENT_DESIGN.md, ../../DEMAND_AUDIT.md,
../../VALUABLE_ITEMS.md, pricing/data/appraisal-demand-audit.json,
pricing/data/appraisal-base-coverage.json and the input list in INVENTORY.md.
