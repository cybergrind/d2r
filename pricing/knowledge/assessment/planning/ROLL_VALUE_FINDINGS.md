# Initial roll-value evidence review

Reviewed 2026-10-01. Raven Frost qualification is now implemented and published;
other item thresholds and machine-checked review closure remain pending.

## Evidence census

Count exact normalized `name` matches, then `scope_status == "verified"`.
These are cached observations, not independent sellers or confirmed sales.
Unknown ethereal status stays unknown; do not default it to nonethereal.

| Item | Cached rows | Scoped rows | Ethereal true | Ethereal false | Ethereal unknown |
|---|---:|---:|---:|---:|---:|
| War Traveler | 100 | 67 | 1 | 0 | 66 |
| Raven Frost | 100 | 43 | 0 | 43 | 0 |
| Skin of the Vipermagi | 100 | 34 | 6 | 0 | 28 |
| Titan's Revenge | 100 | 43 | 38 | 0 | 5 |
| Harlequin Crest | 150 | 83 | 0 | 0 | 83 |
| Griffon's Eye | 100 | 79 | 1 | 0 | 78 |

Input: `pricing/data/appraisal-market.jsonl`
SHA-256: `c65a97fb0768168b42086cdbf0d51352aaac416dae12cbbf358f88a3fd6e3118`.

## War Traveler

Native record: `third-parties/d2data/json/uniqueitems.json:/240`
(index `Wartraveler`, base Battle Boots). MF varies 30–50, enhanced defense
150–190 and attacker-takes-damage 5–10. Added physical damage 15–25 is a
fixed damage interval, not a random roll from 15 to 25. Native ranges alone
do not establish trade thresholds.

Cached scoped observations: 49 at 50 MF (23 sellers), 15 at 45–49 (10
sellers), 3 at 30–44 (3 sellers). These counts include unpriced observations.
All but one omit ethereal status; the explicit one is ethereal. Existing
45/50 MF tier cutoffs are qualitative research leads, not proof that 44 MF
is unsellable. Defense and reflected damage cannot independently establish
a premium. Review physical-build use separately from MF use.

Disposition: trade qualification unresolved. No exact nonethereal segment is
established by these rows. Do not manufacture a numeric value or use-only verdict.
Next: inspect any additional correctly named cached evidence and intrinsic
variant details; retain the gap if it cannot be resolved offline.

## Raven Frost

All 43 scoped rows are nonethereal by verified item mechanics. The captured
roll groups contain 25 rows from 9 sellers at 20 dexterity / 250 AR, 6 rows
from 6 sellers at 20 dexterity / lower AR, 11 rows from 6 sellers below 20
dexterity, and one row with missing rolls. These include unpriced listings.
Repeated listings from one seller are not independent evidence.

Review dexterity and AR jointly: perfect AR alone does not satisfy the
existing double-perfect condition, and 20 dexterity with lower AR remains
a separate segment. One low-dexterity listing asks as much as double-perfect
listings; an isolated high ask cannot establish premium demand. Lower-roll
asks also exist, so the double-perfect threshold cannot become a universal
minimum-to-sell threshold. Fixed CBF utility remains independent.

Disposition: implemented ordinary trade candidacy across legal native rolls,
with premium candidacy requiring **both 20 dexterity and 250 AR**. This uses the
reviewed ordinary and double-perfect asking segments; it does not establish
completed sales, liquidity or an exact specimen price. Do not reject all
nonperfect copies merely because perfect copies command a premium. Unknown or
invalid material rolls/ethereal/socket facts remain unresolved.

The rule retains 39 scoped priced observations and their original row hashes
inside the existing named-rule snapshot. Ordinary and premium segments each
require at least three independent sellers. Source correspondence, scope, identity,
seller duplication, exact premium boundaries and native report rendering have
regression checks. The runtime outcome is independent of build/loadout matching
and numerical prices. The maintenance dimension still needs a reviewed-rule and
executed-report adapter before any completion obligation can be closed.

## Other initial items

Vipermagi, Shako and Griffon have no explicit nonethereal rows in this exact
normalized-name sample. Titan has an ethereal cohort, which must retain ED
and life-leech combinations rather than merging every ethereal specimen.
Inspect their exact facets before refining existing baseline/override tiers.

An earlier text search counted 101 lines containing "War Traveler"; exact
identity matching finds 100. Do not include a mention embedded in another
record as an observation for this identity. This census uses exact names.

Final completion remains pending for all six items; Raven has runtime behavior
and targeted test evidence, but no final maintenance closure receipt. Evidence limitations are
specific findings, not permission to substitute generic build usefulness
or arbitrary percentile cutoffs for trade qualification.

## Evidence-to-segment validation follow-up

Published validation now evaluates each retained listing against the same native
roll predicates and variant conditions used for captured items. It verifies the
item/base identity and the scalar market-to-native mapping against metadata, then
checks exact ordinary/premium evidence membership. Swapped groups, missing
material rolls, unknown ethereal status and incorrect mappings fail validation.
Seller counts alone cannot certify a segment. Raven's existing thresholds and
classification output are unchanged by this validation fix.

Next item-specific lead: Titan's Revenge has38 scoped explicitly ethereal cached
rows. Native definitions give ED150–200 (paired native stats17/18) and life leech
5–9. The cache uses market property510 for ED and462 for life leech. Stat17 has
no direct scalar property_id in metadata, so do not force it through the scalar
evidence mapper or drop ED from validation. Reuse/extend the reviewed compound
projection with tests for both damage-percent components and upgraded base
identity before constructing its trade qualification. Review ED/leech combinations
and deduplicate sellers; no new Titan threshold is established by this note.

Titan cohort inspection (same pinned market snapshot): explicitly ethereal,
scoped, priced rows contain33 observations from13 sellers at ED>=190, three
below190 from only two sellers, and one with missing rolls. All three below190
rows omit the base code; the upper segment also mixes missing bases with explicit
original/upgraded bases. Therefore do not automatically assign ordinary candidacy
to all ethereal low rolls. Review supported segments separately and allow an
explicit unresolved default without mislabeling it use-only or worthless.
`inventory_tracking/items/metadata.py:combine_enhanced_damage` is the existing
source of the equal17/18 -> property510 projection; reuse that verified mechanism.
No Titan runtime rule was added in this pass.

## Titan qualification implementation

Implemented the scoped ethereal ED>=190 asking segment for original and verified
upgraded bases, using24 observations from8 independent sellers with explicit bases,
ED and life leech. Lower-roll and nonethereal specimens remain unresolved rather
than ordinary candidates/use-only. Life leech must be captured within5–9; no
independent perfect-leech premium is inferred. A9-leech roll cannot compensate
for ED below190 or unread/mismatched ED components. No numeric price is produced
by this classification.

The evidence mapper and runtime check share the existing equal17/18 enhanced
damage decoder. It requires both native components, keeps ED separate from base
physical/ethereal damage, and accepts only unambiguous named upgrade relationships
for listed bases without inventing a captured table ID. Titan's tier refinement
also requires the paired ED evidence and zero sockets; baseline tiers remain.
Unknown default outcomes may have no qualifying cohort, but cannot be relabelled
as evidence-free candidate/use-only outcomes. These rules have native item-bank
boundary tests and source-correspondence checks. Final coverage closure adapters
and live worker restart verification remain pending.

## Bul-Kathos’ Wedding Band — 2026-10-01

Reviewed explicit SC/Non-Ladder/PC/RotW asks from the same pinned market snapshot
(c65a97fb0768168b42086cdbf0d51352aaac416dae12cbbf358f88a3fd6e3118).
51 known-base/nonethereal/zero-socket/empty-content observations, 42 independent
sellers, have legal explicit life leech: 35 observations / 28 sellers at 5%;
13 / 13 at 4%; 3 / 3 at 3%. The extra scoped priced observation lacks leech and
cannot substitute character-level life for it. Original rows/hashes are retained.

5% leech supports a premium asking segment; 3–4% remain ordinary candidates.
Overlapping asks preclude a guaranteed sale/price cutoff; no numerical estimate
is introduced. Fixed skills, stamina and character-level life are not random
rolls. Missing/illegal leech, unidentified items, unknown ethereal/socket state,
ethereal rings or socketed rings do not inherit candidacy. Native stat60:0 maps
to market462. Existing universal tier policy is unchanged.

Runtime rule published in generation5e1d184da7f8eae353b8648a808cd152f40b112d5ec4d640df4822bf770eefa5. Staged/published saved replays match; native published checks and maintenance results are recorded in handoff.md. Live worker delivery is not verified.

### Next fixed-stat jewelry review leads

Exact-name scoped priced known-base/nonethereal/zero-socket/empty-content census:
The Stone of Jordan43 rows/27 sellers; Tal Rasha’s Adjudication105/73.
Most rows contain only mode and cosmetic selectors (ring1264 / amulet1265).
Do not invent variable-roll thresholds for fixed-stat items or mistake appearance
selectors for combat modifiers. Further native-definition and report review is
required before installing qualification rules; these counts alone are not prices.

Native table inspection confirms SoJ (uniqueitems.json row122) has fixed20 mana,
25% maximum mana,1 all-skills and1–12 lightning damage. Tal amulet (setitems.json
row113, native ID77) has fixed33 lightning resistance,2 Sorceress skills,50 life,
42 mana and3–32 lightning damage; that elemental interval is damage, not a
variable affix roll. Its conditional10 FCR must stay a set-activation contribution,
not an always-active amulet modifier. Sources: third-parties/d2data/json/*.json.

## Fixed-stat jewelry qualification — 2026-10-01

Published explicit trade candidates for The Stone of Jordan and Tal Rasha’s
Adjudication, with no random-roll material keys or premium band. Known identified
native identity, correct base, nonethereal, zero sockets and empty contents remain
mandatory. Both retain their existing tiers. The terminal labels these simply
“Trade: candidate”; the highlight uses their trade tier (SoJ high/green, Tal
low/blue), without an invented ordinary/perfect-roll grade. Variable-roll items
retain ordinary/premium segment labels and colors.

Important correction to coarse evidence census above: 65 of Tal’s105 otherwise
qualifying observations have no observation date and are excluded. Retained:
40 dated Tal observations/32 sellers;43 dated SoJ observations/27 sellers.
All copied fields/full normalized row hashes match the pinned market snapshot.
The rules make no sale or numeric estimate claim. No live collection performed.
Native bank covers standalone/partial-stat/unknown identification/impossible
ethereal and socket variants. Standalone Tal must not render conditional10 FCR.

### Mara follow-up census

62 dated, scoped, priced known-variant records /10 sellers:2 omit all-resist;
30res12 rows/7 sellers;29res23/2;28res18/3;27res5/1;26res2/1.
Market all-resist property441 is a compound of native elemental resistances,
not an excuse to discard unequal/missing captured components. Repeated rows
from the same seller do not strengthen independent evidence. No Mara threshold
or runtime qualification is established by this census.

## Variable jewelry execution coverage — 2026-10-01

BK and Raven trade rules are unchanged; new source-bound native report contracts
exercise12 BK cases and28 Raven cases. The scalar audit derives required native
limits and threshold-adjacent combinations, requires each missing/out-of-range
component independently, and retains legal/impossible/unknown facet checks.
Only independent plain integer native rolls are supported. Correlated properties,
shifted/encoded stats and unresolved legal branches keep a review open.

Next Mara implementation should reuse existing property_equivalence.canonical_properties
(which expands market441 and rejects ambiguous combined+individual inputs) and
maintenance/variable_jewelry_market_review.SPECS, which already declares the
correlated native39/41/43/45 axis20–30 and native property slot2/res-all. Do not
model those four resistances as independent rolls or invent a combine_resistances
decoder helper. Pricing normalization supports the representation; trade
qualification and compound execution coverage still need explicit implementation.

## Mara’s Kaleidoscope trade qualification — 2026-10-01

Native39/41/43/45 are one shared20-30 all-resistance roll. New compound mapping
uses market441; captured components must all be decoded, finite and equal.
Mixed combined+individual market resistance fields are rejected through existing
canonical_properties instead of silently overwriting/adding contributions.

Scoped dated known-base/nonethereal/zero-socket evidence retained:12 perfect30
observations/7 sellers;46 observations at27-29/3 sellers. Lower26 has only2
observations/1 seller; unnamed-roll observations also excluded. These lower and
missing-roll observations remain research context, not accepted trade bands.
30 qualifies premium;27-29 qualifies ordinary;20-26 remains unresolved, not
worthless. No numeric price or mixed-mode fills used. The previous27-29 high
tier (supported by seller-concentrated asks) is corrected to mid;30 stays high.

22 native bank cases cover limits, threshold, every missing/unequal resistance
and illegal/unknown facets. Existing four jewelry trade review receipts must be
refreshed for the new generation. Mara identity-wide completion remains open:
compound execution coverage and supported lower-roll disposition are not complete.

## Sandstorm Trek trade qualification — 2026-10-01

The previous 15 Strength/15 Vitality high-tier override ignored ethereal status.
The reviewed explicit-variant cohort only establishes ethereal asking segments:
6 complete 15/15 observations from3 sellers;4 other complete observations from4
sellers. Two additional ethereal rows lack enhanced defense and are excluded.
All rows are dated2026-09-18, scope-verified SC/NL/PC/RotW; copied source fields
and full normalized row hashes are tested. Legacy cheapest rows defaulting absent
ethereal to false cannot establish a nonethereal segment.

Ethereal15/15 is a premium attribute-roll candidate/high; other legal ethereal
rolls are ordinary candidates/mid. Enhanced defense140-170 and poison resist40-70
must also be known, alongside Strength/Vitality10-15. Perfect defense/resistance
cannot replace either attribute. Nonethereal/unknown ethereal cannot borrow the
premium; missing/illegal rolls or socket facets remain unresolved. This does not
claim that15/15 is the only valuable combination, establish a numeric price, or
prove liquidity. Nonethereal and further defense/resistance refinements remain
open, and no identity-wide completion review is added.

Red14 regression failures, then14 green; all440 policy tests pass.36 native
appraisal bank cases exercise joint attribute boundaries, defense/resistance
endpoints, each missing/illegal roll and unknown/impossible variants.

## Wisp, Atma and Highlord evidence review — 2026-10-01

The prior Wisp census was NOT sufficient to support trade qualification.
All33 complete explicit-variant dated rows use market689, labeled
`+{{value}} Lightning Absorb` (flat). Native144 is percentage lightning absorb,
whose verified metadata property is1866 (`Lightning Absorb +{{value}}%`).
No Wisp observations carry1866. Native-mapping validation rejected the proposed
qualification, correctly. Do not globally alias flat to percentage absorb, or
infer a verified alias from the item name alone. Wisp's new qualification was
withdrawn before publication; its existing tier policy is unchanged. Next work
must establish a source-backed item-specific representation or retain the gap.
The old15/20/etc market thresholds require this qualification caveat too.

Atma's Scarab:232 scope-verified observations are all undated (197 had usable
asks and known variants). No new qualification is published from these rows.
Recover authoritative capture-date provenance before using them. The earlier
candidate census omitted the date filter; it was a research lead only.

Highlord's Wrath:29 dated SC/NL/PC/RotW asks from26 sellers have original base,
explicit nonethereal, zero sockets and empty contents. Fixed native modifiers
require no random-roll threshold. Level-dependent Deadly Strike and a fixed
lightning damage interval are not random rolls. Candidate/medium tier, with
legal/unknown/impossible variant gates. Numerical pricing and complete stat
capture remain independent; partial captures may establish fixed-identity demand
without establishing an exact price. Copied fields and normalized hashes tested.

Next Gheed lead (not a completed qualification):36 dated known-variant rows from20
sellers include all three native scalar rolls (80 MF20-40 ->461,79 gold80-160 ->460,
87 vendor discount10-15 ->764). One row claims45MF, impossible under the native
range, and must be excluded. The existing high-tier rule starts at38MF, but the
sample has only one39MF row; do not automatically inherit that threshold into a
premium qualification. Inspect40MF versus lower rolls and gold/vendor-discount
combinations independently. Double listings from the same seller are not new
independent sellers. No new Gheed rule or closure is established by this census.

## Gheed’s Fortune MF trade segment — 2026-10-01

Retained35 complete legal dated known-variant rows.20 perfect40MF rows from9
sellers and15 lower-MF rows from12 sellers.
The45MF row is excluded as impossible. Gold80-160 and vendor discount10-15 are
captured alongside MF20-40; each must be decoded and legal. Mapping verified
against native metadata:80->461,79->460,87->764. No mixed-mode d2io fills used.

40MF qualifies for the premium MF segment/high. Lower MF qualifies as ordinary/
mid. The old38MF high override is removed: the dated explicit-variant sample
contains only one39MF row, insufficient to establish a separate premium segment.
Perfect gold/discount cannot substitute for MF within this reviewed MF segment.
This is not a claim that a low-MF gold/gambling collector variant lacks value;
independent collector premiums and exact roll comparisons remain open. No numeric
price or identity-wide trade-completion claim is introduced.

31 native bank cases cover MF20/38/39/40 crossed with gold/discount endpoints,
each missing/out-of-range component and impossible/unknown variants. Strict
specimen tiers now require all three material rolls, not a partial MF-only item.

Next Nagelring lead:12 dated known-variant priced rows from11 sellers; only7
carry both native attack rating50-75 (19->423) and MF15-30 (80->461). All7 have
30MF. Double-perfect75AR/30MF appears at only2 independent sellers, so do not
invent a collector premium from that pair. Five rows omit one/both rolls and
cannot supply complete-variant comparisons. Lower-MF trade qualification remains
unsupported by this cohort. This census is not yet a runtime rule or closure.

## Nagelring ordinary MF trade candidate — 2026-10-01

Seven complete dated known-variant30MF observations from6 sellers support an
ordinary candidate/low label. Both MF15-30 (native80->market461) and AR50-75
(native19->423) must be known and legal, alongside identified original Ring,
nonethereal, zero sockets and empty contents. Five incomplete priced rows were
excluded. Double-perfect75AR/30MF has only2 independent sellers, so no premium
band is inferred. The historical aggregate's cheap missing-roll rows do not
establish lower-MF sellability. Lower MF remains unresolved, not worthless.

21 native item-bank cases check legal lower/max MF, mixed attack-rating rolls,
each missing/illegal component and unknown/impossible variants. Existing low
tier is retained independently of qualification. No exact price, completed sale,
collector premium or identity-wide completion claim is introduced.

Next Dwarf Star lead:8 dated explicit-variant asks from8 sellers. Native35
magic damage reduction varies12-15 and maps to market414. Six rows explicitly
have15MDR, one13MDR, and one omits MDR. A max-roll ordinary candidate could be
supported; the lone13 row cannot establish the lower-roll band. Do not assume
15MDR is a premium or count the missing-roll row toward a complete comparison.
Native fire absorb and gold-find utility are separate fixed properties.

## Dwarf Star and Metalgrid trade qualification — 2026-10-01

Dwarf Star15MDR: ordinary/low candidate based on6 dated complete explicit-variant
asks from6 sellers. Native35 MDR12-15 maps market414. One13MDR row and one
missing-MDR row cannot establish a lower-roll segment.12-14 remains unresolved,
not worthless. No automatic premium from perfection or fixed gold/fire utility.
13 native report cases cover all legal rolls, invalid bounds, missing MDR and
unknown/impossible variants.

Metalgrid: ordinary candidate/medium for its existing supported cohort;7 dated
complete known-variant asks from7 sellers. Requires AR400-450, defense300-350 and
shared all-res25-35. Native19->423,31->399,39/41/43/45->compound441. Every captured
resistance component must agree; unequal values now also block strict specimen
tier refinement. The existing450AR/35allres joint-perfect exclusion remains
unresolved because its source cohort lacks priced evidence. No new premium or
numeric price inferred from sparse collectors or a high ask.46 native bank
cases cover joint boundaries, collector exclusion, missing/illegal components,
each unequal resistance component and unknown/impossible variants.

Neither identity-wide trade review is closed; lower Dwarf and perfect Metalgrid
research remains required. Raw observations and complete-row hashes are preserved
and tested. All evidence remains SC/NL/PC/RotW; no live collection.

Next Trang-Oul's Girth lead:23 dated explicit-variant asks. Native variable
flat defense31 is75-100; mana9 is25-50 (raw shift8, market400 decoded units).
Listings mix apparent flat defense75-100 and values136-166 in market399; some
also carry total defense1855. Do not map the larger399 values straight to native
flat defense or discard the distinction via a universal tolerance. Check native
capture/armor-defense representation and source-specific listing semantics first.
Several50mana rows omit flat defense; the complete75-100 cohort has only2 sellers
at50mana, so its premium evidence is thinner than the raw23-row count suggests.
No Girth trade qualification or new premium is established by this census.

## Trang-Oul’s Girth total defense RCA and qualification — 2026-10-01

Native captured stat31 is total armor defense, not the75-100 flat bonus. Verified
Troll Belt base59-66 plus native bonus75-100 yields total134-166. Existing decoder
intentionally leaves armor31 out of scalar market399 projection. Girth's only
conditional item property is cold resistance; full-set character defense/mana
bonuses cannot be borrowed into the item's native roll bounds.

The new reviewed representation uses explicit market1855(total Defense), not a
fallback from399. If399 is present it must be a legal75-100 bonus and total-minus-
bonus must fit59-66. Conflicting values or missing total are excluded. Captures
must be complete, identified original nonethereal unsocketed Girth with no extra
ED/per-level defense components. This mapping is scoped specifically to Girth,
not a global total/bonus alias. All other mappings remain metadata-validated.

Retained12 dated scoped explicit-total rows:5 at50mana from4 sellers and7 below50
from5 sellers.50mana=>premium qualifier/medium tier; lower legal25-49mana=>ordinary/
low. Perfect-defense collector pricing is not inferred. Report now displays total
defense134-166 and grades that total, not an invented exact bonus roll. Mana raw
shift8 is decoded before predicates. No numeric price or identity-wide closure.

29 native bank cases cover joint total/mana endpoints, invalid and missing stats,
full-set-sized totals, additional defense modifiers, allowed cold-resist item
bonus, incomplete capture and invalid/unknown variants. Existing generic mana-
only Girth tier fixture replaced with dedicated complete total-defense fixtures.
Python helper/display changes require a worker restart after publication.

Next set-piece leads (not completed reviews):Trang Claws has11 dated explicit-
variant asks/8 sellers, but mixed original Exceptional and upgraded Elite bases.
Its modifier rolls are fixed; physical base defense still varies. Fields399 again
mix fixed+30 bonus and total-looking67-97 values. Preserve upgrade/requirements
and explicit total-defense distinctions. Tal Fine-Spun Cloth has5 dated variants/
5 sellers; only variable modifier is MF10-15.15MF appears on both original and
upgraded bases; do not assume each variant independently has3 sellers. M'avina
Tenet has no dated rows passing the explicit-variant filter in this census.

### 2026-10-01 — original Trang Claws and Tal belt

Reviewed original-base cohorts only: Claws7 dated SC/NL/PC/RotW ask rows from6
sellers; Tal15MF6 rows from4 sellers. Fixed-modifier Claws is an ordinary low-tier
candidate, not a perfect-defense premium. Tal15MF is an ordinary low-tier
candidate;10–14MF has insufficient matched evidence and remains unresolved.
Upgraded versions cannot borrow these original-base claims.

The evidence helper `market_base_inference.original_base_code` accepts an explicit
original selector or a mechanically unambiguous low total1855. Native original
Claws defense37–44 plus fixed30 =>67–74; Tal35–40. Each maximum is below its legal
elite minimum. Positive conditional Tal+60 defense cannot make an elite base fall
into the original range. Unknown properties fail the reviewed native-property
allowlist. Selector930 Normal/Elite, upgraded1216, ethereal, sockets, missingtotal
or bonus399 alone cannot infer an original. Native codes/chains are read from
catalogs. Raw evidence and hashes remain unchanged; no global normalization or
numerical price matching is relaxed. Mode is opt-in per reviewed qualification.

Native bank21 cases include originals, upgrades, MF limits/missing, unknown or
illegal facets, and exact report text/blue tone. Neither identity is certified
fully reviewed: low-MF, upgraded and collector-defense markets remain open.

### 2026-10-01 — Sling complete trade qualification

All47 dated SC/NL/PC/RotW original nonethereal unsocketed Sling asks retain their
source rows/hashes and all3 variable rolls.5 magic pierce:10 rows/4 sellers,
reviewed higher asking segment;3–4 pierce:37 rows/3 sellers, ordinary candidate.
Energy10–15 and MF10–20 must be present and legal, but no independent collector
premium is inferred for their maxima. Native358->1877,1->421,80->461 mappings
validated. Existing broad high tier remains independent of the new qualifier.

42 authored native-bank cases cover joint endpoints and predicate-adjacent values,
every missing/out-of-range component, impossible/unknown variants, exact report
text and green premium/blue ordinary colors. Scalar-jewelry completion scope can
cover this identity once the published execution receipt is validated. Native
Energy metadata has op8: local D2MOO/source/D2Common/src/D2StatList.cpp case8
converts item Energy into player mana without scaling the item's integer modifier.
The completion checker now permits only stat1/propertyenr/nameenergy/op8/param0/
no opbase with zero shift, encode and parameter bits. Unrelated operations and
shifted encodings remain rejected; decoder/report behavior itself is unchanged.

Sling selected-generation validation:325 published report cases passed (42 Sling),
628 policy/review tests passed. All6 registered identity trade reviews were
accepted against generationf7649728e0ac5bccd0f411d5ee40939547217abdb4318596ce980b9e03da47cc;
Sling's qualification dimension is reviewed. This is not full all-item completion.
20 historical capture replays preserve decoding, price output and text. Evidence:
tmp/sling-{receipt,publication}-proof.json and named-jewelry-trade execution receipt.

### 2026-10-01 — Entropy Locket ordinary mixed-roll demand

The indexed unique research explicitly uses an any-roll bucket; its mixed-roll
SC/NL/PC/RotW asks establish ordinary caster-amulet demand, not a roll-specific
premium. Retained14 dated, priced, original nonethereal unsocketed observations
from8 independent sellers with allfive native variable rolls. Native357magic
skill damage5–10->1879;105FCR5–10->520;41lightningresist25–40->428;77maxmana10–15
->617;35MDR8–12->414. Every captured modifier must be present and legal.

No premium band: only4 complete top-FCR rows from2 sellers. Three additional
incomplete observations cannot establish a matched premium. Native maxima do
not imply saleability or a collector premium. The minimum observed magic-damage
roll is not used to manufacture a trading cutoff; the reviewed identity-wide
any-roll demand remains separate from exact numerical comparability. All legal
combinations are ordinary candidates; invalid/unknown variants remain unresolved.

264 authored native-bank cases cover5 independent axes at endpoints and adjacent
validity boundaries, every missing/invalid component, and all required unknown/
impossible variants. Exact ordinary-blue report text and absence of a premium
are asserted. Scalar named-jewelry review is registered but must be validated by
the selected generation's executed receipt before completion is accepted.

Completion-check RCA: native maximum-mana percentage77 has op11, which local
D2MOO D2StatList.cpp applies to player/monster totals, not item modifier encoding.
The scalar review guard now has an explicit reviewed operation map: Energy1/enr/
energy/op8 and mana77/mana%/item_maxmana_percent/op11 only, with zero shift/encode/
parameter bits/op parameter and no op base. Wrong identity/operation/scaling stays
rejected. This extends the coverage proof, not the item decoder or market mapper.

Next Opalvein implementation lead (not a completed review): existing
pricing.knowledge.property_groups.selected_ranges validates exactly one complete
scalar alternative, including equal paired ED; named handler comparison_gaps also
requires capture_complete. Reuse that native proof rather than flattening random
choices. Current complete-variant dated cohorts have fire4, cold4, lightning3
independent sellers, but magic2/physical1/poison1. Verify all fixed material rolls
before using these counts. A reviewed property-choice guard can require complete
captures, while explicit market choice fields establish listing membership.
Material mapping can cover only reviewed elemental branches; physical/magic/
poison remain unresolved, with their present native keys still checked for
contradictory multiple selections. Existing all-resistance compound proof applies.
Do not change source fields or infer a premium from 8 resistance alone.

### 2026-10-01 — Opalvein elemental trade cohorts

Fifteen complete scoped dated original/nonethereal/unsocketed listings cover
fire5rows/4sellers,cold5/4,lightning5/3 (8sellers total). Each reviewed subtype
must independently retain3sellers; aggregate popularity cannot hide a thin
subtype. All-resistance6–8 and life/mana-after-kill1–3 are required alongside
exactly one native magdam-rand modifier. Supported elemental bonuses are3–5.
Magic, physical and poison variants lack sufficient independent evidence and
cannot borrow elemental trade qualification. No perfect-roll premium inferred.

New trade_choices guard reuses selected_ranges and native definition groups.
Captures must be complete, with one valid modifier; mixed or unresolved choices
fail. Market rows must expose exactly one reviewed choice; unmapped magic/ED/
poison fields still reject contradictory listings. Existing allres compound
validation enforces equal components. Scalar mappings remain metadata-verified.
The choice guard runs only for trade qualification and listing evidence; named
tiers retain their prior resistance-based contract. Missing or unsupported random
choices do not erase that broad tier, but cannot acquire a verified elemental
trade qualifier. Complete captures are required to prove group integrity. No global normalization or numeric price relaxation.

### 2026-10-01 — Defender's Fire joint core premium

Fourteen complete dated SC/NL/PC/RotW original nonethereal unsocketed asks:
5 rows/4 independent sellers at10%fire skill damage +10%fire pierce;9 rows/3
sellers below that joint maximum. The 2026-09-18 seller-median asks separate
strongly (premium171.315–456.84Ist versus ordinary5.053–11.421Ist). These cohort
observations support qualitative qualification; no numerical sale-price estimate
is introduced. Experience3–5,MF15–35,gold25–50 must all be known and legal, but
maxima on these secondary rolls do not independently create another premium.
Native mappings329->750,333->735,85->776,80->461,79->460 remain metadata-validated.

A new scalar_colossal_jewel completion scope admits only native Colossal Jewel
bases; jewelry retains the Ring/Amulet scope. Both share the reviewed integer
boundary engine. Property-group/total-defense trade guards cannot silently use
this simple scalar proof. Cross-family scope borrowing is explicitly rejected.

Boundary proof now uses native endpoints plus threshold-1/threshold for every
integer >= predicate. These delimit all constant predicate regions, including
narrow intervals expressed with NOT/AND/OR. Threshold+1 is redundant unless a
second predicate introduces that boundary. Missing and each invalid endpoint
are separately required. This retains both sides of every decision boundary
without Cartesian products of equivalent interior values. Existing cases remain;
new independently authored Defender bank has93cases:72joint endpoints/boundary
combinations,15missing/invalid components,6unknown/impossible variants. Exact
ordinary-blue and premium-green report lines are asserted. Coverage acceptance
still requires all case assertions and a current published execution receipt.

Source granularity: the retained10/10 listings all show4% experience, with
varying MF/gold. Nonperfect-core listings include3,4,5% experience. The new
qualification is the reviewed core-roll bucket; it is not an exact-price claim
for every secondary combination. Secondary facets remain required by numerical
comparison logic. Max experience alone has no separately proved premium rule.

### 2026-10-01 — Guardian's Light and Guardian's Thunder

Reviewed independently using dated SC/NL/PC/RotW original nonethereal,
unsocketed asks dated 2026-09-18: Light has 20 complete rows / 8 sellers;
Thunder has 13 / 8.
All five native rolls are required: skill damage and pierce 5–10, experience
3–5, magic find 15–35, gold find 25–50. Cached any-roll demand supports an
ordinary candidate across legal combinations. Neither borrows Defender's Fire's
premium: complete joint 10/10 Light asks have only two sellers and Thunder one.
No numerical price or sale guarantee is introduced; broad named tiers remain.

Each item has 53 native appraisal cases: 32 joint endpoints, 15 missing/invalid
material values, and six unknown/impossible variants. Reports assert ordinary
blue text and no premium. Scalar Colossal Jewel reviews require the all-maximum
case even without a premium band. Final identity acceptance remains bound to
the selected publication and its report execution receipt.

### 2026-10-01 — Protector's Stone and equal enhanced-damage coverage

Fourteen complete scoped asks dated 2026-09-18 from six independent sellers
support ordinary physical Colossal Jewel demand. No joint 50% enhanced damage /
10% physical pierce listing supports a separately reviewed perfect-roll premium.
This is qualitative any-roll demand, not an exact numerical price for every
secondary combination. Universal high tier remains unchanged.

Native enhanced damage uses equal stats17/18, range30–50, property dmg%; the
existing compound mapping supplies market510. Physical pierce3665–10->1881,
experience853–5->776, MF8015–35->461 and gold7925–50->460 all must be known and
legal. Native dmg-norm10–30 is fixed added min/max damage, not a random roll.
No scalar alias or marketplace field normalization was introduced.

The new compound_colossal_jewel completion scope accepts only this native ED
representation: two equal range/property rows, exact metadata names/op13, no
shift/encoding/layer/parameter changes. The existing equal-pair decoder remains
the runtime validity check. Integer partitions union thresholds from either
native component and expand one correlated axis; scalar scopes remain unchanged.
Independent properties cannot borrow this proof, and additional property groups,
total defense and variant rules remain unsupported by this narrow adapter.

58 authored native report cases cover32joint endpoints,18missing/out-of-range
components,2mismatch directions and6unknown/impossible variants. Completion
requires those explicit cases; tests deny omitted mismatch cases, mismatched
metadata/bounds, duplicate raw fields and cross-family/scalar-scope borrowing.
Exact ordinary-blue text is asserted; no perfect green premium is fabricated.

### 2026-10-01 — Gheed's Fortune completion review

The existing three-roll rule and31 native report cases now have a Grand Charm
integer review scope. MF20–40 (premium40), gold80–160 and vendor discount10–15
are independent native integers; no new property alias or operation exception.
Scope tests fail when the39/40 threshold, joint minima/maxima, a missing gold
roll or unknown socket contents are omitted. Jewelry/Colossal scopes cannot
borrow this family. No runtime trade/price/tier changes and no implied collector
premium for gold or discount. Execution receipts remain mandatory for closure.

Remaining Colossal leads, not new rules: Defender's Bile has three complete
dated scoped asks / three sellers, but two are10/10core and only one is a lower
core. The source calls the market thin. Protector's Frost has no complete
normalized rows in the current census (source summary only two priced sellers).
Do not borrow other jewels' premiums or infer these are worthless. Census and
source IDs: tmp/remaining-colossal-census.json.

### 2026-10-01 — Original Flame Rift and Crack of the Heavens

Flame Rift has56 complete SC/NL/PC/RotW original nonethereal, unsocketed
asks observed2026-09-25 /33 sellers; Crack of the Heavens27/18 on the same date. Native penalties are -90..-70.
Flame perfect-70 has29rows/18sellers and other rolls27/17; Crack perfect20/13
and other7/5. These cached cohorts have a1Ist median of seller-median asks in
each segment; they do not establish a distinct perfect-penalty premium. Ordinary
qualification is separate from better mechanical rolls and exact price estimates.
One impossible magnitude69 Crack listing is excluded. Source dates remain in
the copied individual rows; no listing update date becomes an observation date.

Evidence-only trade_sunder projection explicitly checks the original catalog
identity, unique quality and sole verified material mapping, then reuses
mechanics/sunder.listing_penalties. It retains raw listing properties and their
full normalized-row hashes. Missing/wrong catalog, unknown representation, wrong
identity/mapping, missing/noninteger/outside-range penalties all fail. Positive
magnitudes and explicit negative resistance penalties are equivalent only here;
ordinary resistance bonuses are never globally negated. Native captures remain
signed and must have the legal negative value. No numeric price logic changed.

The old generic tier guard admitted ethereal and ignored socket count for these
two Grand Charms. Red/green tests now enforce nonethereal/zero/empty facts; their
legitimate low tiers remain unchanged.28 new native report cases cover each
penalty endpoint, -71, missing/outside/positive native values and all variants.
Scalar Grand Charm review validates the negative range and rejects unknown
evidence modes; registry acceptance still requires a current published receipt.

### 2026-10-01 — Horazon's Legacy native base defense and ordinary qualification

Three complete original nonethereal unsocketed asks observed2026-09-18 from
three sellers support ordinary set-boot demand; the source bucket also supplies broader
any-roll context. Strength10–15,Dexterity10–15,magic resistance20–30 and native
defense59–68 must all be legal. No separately established perfect-roll premium.
Market1855 is total defense;399 is a flat bonus and cannot substitute. Conflicting
bonus or enhanced-defense fields are rejected. Original raw rows/hashes retained.

Native armor row utb is Mirrored Boots; ultracode (not ubercode) verifies the
elite original, with no socket capacity. The item has no intrinsic defense
modifier. Its only conditional item modifier is move2; that cannot alter defense.
Global set bonuses are not attributed back to the item: totals outside native
bounds, incomplete captures and additional ED/per-level defense fields reject
qualification. No upgrade, ethereal or socket inference.

The new trade_base_defense representation is checked by trade qualification
and evidence, independently of the broad named tier. An unread defense field
therefore does not erase the previously established low item tier. The report
annotates verified native base defense59–68; other named items return unchanged.

Completion scope base_defense_set_boots admits only the reviewed original
Mirrored Boots definition and exact integer armorclass representation. Ordinary
scalar scopes still reject base-defense definitions. Joint native endpoints and
each missing/outside roll remain mandatory; incomplete and each ED/per-level
contribution case are additionally required and cannot stand in for ready cases.
The oracle retains other raw stat identities to notice forbidden contributions.
41 native report cases include conditional40FRW and out-of-range set totals.
No full-bank or full-goal completion claim follows from this identity review.


## Andariel’s Visage — material evidence reviewed 2026-10-02

Reproducible offline review:
`uv run --offline python -m pricing.knowledge.assessment.maintenance.andariel_market_review`.
Output: `pricing/data/appraisal-andariel-material-review.json`, including market,
raw response, native-table, guide and implementation SHA256 bindings.

The current cache has 39 dated, active, single-item scoped asks under the shared
scope validator (including one listing explicitly offering both LoD and RotW).
The earlier 38-count audit required the version string to be exactly RotW; this
count correction does not make its unknown variants priceable. Four Ral-insert
listings, from two sellers, prove unchanged native strength and life steal. Only
two of those also report native ED; both belong to one seller. Each complete
material-roll cohort therefore has one seller. Other socket payloads/unknown
occupancy cannot establish native perfect strength, leech or ED. No inference
from total defense is implemented in this review.

Historical WP-I eth30/10 premiums remain leads. The examined evidence establishes
neither a numeric price nor a premium cutoff or the worthlessness of lower rolls.
Build evidence separately supports ethereal mercenary helmets with IAS/fire
resistance jewels; a Ral listing is not that same configuration. Material-roll
pricing disposition is insufficient_variant_evidence. This is not full exact
comparison eligibility or machine-checked identity completion. Runtime retains
baseline tiers, build roles and the separately published intrinsic-roll fix.

19 tests cover cached cohorts, unknown variant facts, invalid native values,
unspecified jewels, foreign modes, inactive/sold/buy listings, quantity, invalid
price/date, duplicates and future cohorts requiring exact comparison review.
Do not rerun the same Andariel research until additional payload/native evidence
is available. Continue other named reviews and broader required work.

## Guardian Angel material evidence audit — 2026-10-02

Reproducible command: `uv run --offline python -m pricing.knowledge.assessment.maintenance.guardian_market_review`.
Output: `pricing/data/appraisal-guardian-material-review.json` binds market, raw
cache, implementation and native armor/unique/gem table hashes. All 81 cached
observations lack collection dates. Seller listing update dates are not substituted
for observation dates. Ten have unverified scope; 48 lack consistent complete
base/ethereal evidence; 19 lack known socket payload; three prove native ED;
one advertises impossible 2347ED with Perfect Topaz. That conflict is retained
explicitly, never repaired to an invented roll or counted as a premium sample.
Original/upgraded bases and ethereal flags are checked independently of defense;
unknown occupancy never means empty. Known single Pul contributes30ED, known
Ral/Topaz/Cham/El/Zod contributes0ED. Unspecified jewels stay unresolved.

Disposition: no dated comparable evidence. No new premium cutoff or numerical
price is established. This does not close full Guardian trade qualification,
all variants or runtime report verification. Additional material inference is
not justified merely to make the current undated cache priceable. Continue other
valuable-item reviews under the current live-collection hold. Initial tests failed
on missing module; 20 Guardian tests plus19 Andariel tests pass, with formatting
and lint clean. Unknown/boundary/conflicting values have executable checks.

## Waterwalk exact variant evidence — 2026-10-02

Added source-checked defense inference for named exact comparison only. Native
Sharkskin33..39 becomes40 with intrinsicED180..210; upgraded Scarabshell rerolls
56..65. Original observed totals can prove original/nonethereal only below both
conservative ethereal and upgraded minima. Upgraded inference requires explicit
elite identity and an attainable rounded total below its ethereal minimum.
Known contradictory facets, bonus-defense399, noninteger rolls, sockets and
changed native table hashes fail closed. Cached rows are never rewritten.

Three dated scoped independent sellers match upgraded210ED/65life/198defense:
345f52cb294a0b1a0990d487, d1c6bb74815bdb8a2cbb05ad,
28e59ed909b6fad2d7d79724. Exact comparison now reaches the existing dispersion
gate, which declines an estimate. Different defense rolls stay separate. Two
apparent original-perfect matches retain ambiguous-unit exclusions. No baseline
tier changes or trade/premium thresholds inferred from these listings.

Red two inference failures, green75 mechanics/comparison regressions; three
positive/near-miss/unknown published-bank cases pass with unchanged sources.
Receipt pricing/data/report-receipts/waterwalk-defense.json; selected generation
0b82ed14da19f338e61684e8bb8e0219c0455bd84f938be68eb30194d7d48b25.
Proof pricing/data/appraisal-waterwalk-defense-review-2026-10-02.json. Python
worker restart still required. Full Waterwalk roll-dependent trade qualification
and all-variant review remain separate work; do not mark identity complete.

## Waterwalk observed trade cohort published — 2026-10-02

The three independently dated asking sellers for upgraded nonethereal
65life/210ED/198defense now support an ordinary candidate for that exact cohort.
This does not establish liquidity, a numerical price, or a premium threshold.
Other rolls (including better underlying defense), original boots, ethereal and
unknown variants remain unresolved. No absent evidence becomes use-only/trash.
The total-defense mapping is an explicit Waterwalk mode with native-table checks,
attainable integer totals, complete captured evidence and no per-level defense.
Evidence and captured items share the same guard. Life is decoded from shifted
native stat7; total defense31 maps only to explicit1855, never bonus399.

Regression exposed trade-only total-defense validation suppressing an independent
life-based tier. Tier validation now requires that guard only when the tier's own
predicates depend on31:0. Girth defense-dependent tiers retain their guard.
Initial1375 policy passes/2 failures; both failures repaired,152 affected tests
pass. Lint/format pass. Three full published bank cases pass and all20 saved
capture extraction/price/text outputs are unchanged. Generation
6b2754eb801c2b6d79a277210e527f6d3fe488cfa31ae91842de0ad9ba08e61a;
receipt pricing/data/report-receipts/waterwalk-trade.json. Proof
pricing/data/appraisal-waterwalk-trade-publication-2026-10-02.json.
Full all-variant Waterwalk qualification and machine review closure are not claimed.

## Waterwalk boundary item bank — 2026-10-02

Expanded the three initial cases with64 independent native-boundary/unknown
scenarios. Native original40 and upgraded56/63/64/65 defense bases combine with
45/64/65life and180/209/210ED; only the observed upgraded64base/65life/210ED
cohort is expected candidate. Separate cases check illegal life/ED, impossible
197/199 totals at210ED, missing material stats, unknown ethereal/sockets/contents,
filled/socketed boots, unidentified/incomplete captures and per-level defense.
Every added case asserts the qualification and exact visible trade line/tone.

67 published full-pipeline cases pass in72.52s with unchanged source hashes,
selected generation6b2754eb801c2b6d79a277210e527f6d3fe488cfa31ae91842de0ad9ba08e61a.
Receipt pricing/data/report-receipts/waterwalk-boundaries.json; proof
pricing/data/appraisal-waterwalk-boundary-verification-2026-10-02.json.
No new runtime behavior, market threshold or price was inferred from these tests.
Machine review adapter/census and full Waterwalk scope closure remain unfinished.

## Waterwalk independent completion oracle — 2026-10-02

Added maintenance/trade_waterwalk.py with native identity/property/stat encoding
checks and an independent expected-outcome oracle for the64 boundary scenarios.
It checks fixed modifiers, shifted life, ED/total-defense identity, original and
upgraded corners, impossible/missing rolls, all required variant signatures,
complete/incomplete captures and per-level defense. Every scenario must bind the
correct report qualification/text/color. Runtime predicates are evaluated and
compared with the independent expected cohort, not used to invent expectations.
Ten tests pass, including destructive mutations of native data, mappings,
premium status, case completeness and visible color. Lint/format pass.

This module is preparatory, not registered completion: unresolved-evidence census,
registry dispatch/bindings, integration tests and renewed execution receipt are
still required. The67-case receipt predates this maintenance-code/test addition
and is historical under the broad verification input contract. Runtime generation
and behavior are unchanged. Do not mark Waterwalk or the all-item goal complete.

## Waterwalk whole-cache census — 2026-10-02

Run `uv run --offline python -m pricing.knowledge.assessment.maintenance.trade_waterwalk_evidence`.
Source-bound output pricing/data/appraisal-waterwalk-evidence-census.json accounts
for100 observations: supported upgraded cohort3sellers;20 other exact cohorts
(one seller each);19 unproven variant/material observations;54 unverified scope,
2 ambiguous units,2 invalid asking terms. Conflicting duplicate IDs fail; repeated
identical observations/sellers cannot increase counts. Active selling status,
collection date, single quantity, independent seller, asking terms and SC/NL/PC/RotW
scope are checked. Native tables and raw caches/conversion snapshot are pinned.
Ten new evidence tests plus10 independent oracle tests pass; lint/format clean.

Important next review: original boots account for18 eligible observations from
5 independent sellers, not18 independent sellers. These support a potential
ordinary-original asking band separately from exact numeric-price cohorts:
- c179efc49ffbef5866c30839:45life/195ED, seller1002488439940.
- 1cd30db255c39b2dd3c49eb4:51life/201ED, seller1002287916819.
- 756bb83b6fce7cc23f9c5757:51life/187ED, seller1770352508.
- 41de7cf59bc784c297df0bb9:65life/185ED, seller1002354667355.
- defbf8693ac3b04f357b27f7:63life/210ED, seller2491287980.
Do not pool these different rolls into an exact numeric estimate. Original
fixed20FRW/15dex/5maxFireRes and life45..65 utility requires review in deciding
ordinary interest; this census is not yet a runtime band or closure approval.
The two other upgraded cohorts each have one seller and remain unresolved.
Registry integration is deferred until the original-band evidence is addressed;
otherwise a narrow current policy would be falsely certified as whole-item review.

## Waterwalk original asking band — 2026-10-02

Published ordinary candidate support for original nonethereal legal45–65life and
180–210ED with a verified native total. Five independent dated original sellers
include45/51life; fixed20FRW/15dex/5maxFireRes explains utility below perfect life.
Upgraded65life/210ED/198defense remains separately qualified. Other upgraded
outcomes remain unresolved. No sale, liquidity, premium or numericalprice claim.
Different rolls remain separate exact price comparisons.

Updated independent oracle/bank to cover invalid/unknown variants on both bases.
79 focused tests,86 staged cases and two86-case published runs pass. All20saved
replay extraction/price/text fields unchanged. Lint/format clean.
Generation56094eb44d8c8bbfa8f345eebe9cbb41c41007178fa6272317e01aacd1105a63.
The published receipts DO NOT certify unchanged inputs: concurrent unrelated
terror-probe work changed files in both runs (last: inventory_tracking/terror/probe.py).
Preserved these edits; no repeated rerun while that work is active. Receipt
pricing/data/report-receipts/waterwalk-original-trade.json remains historical
execution evidence pending a stable-input run. Proof
pricing/data/appraisal-waterwalk-original-publication-2026-10-02.json.
Registry/evidence integration and worker restart remain open, alongside full goal.

## Waterwalk trade-review gate accepted — 2026-10-02

The previous turn published original-base qualification. This turn wired
`native_unique_waterwalk` into trade_reviews and added source-bound census checks.
The gate rejects missing/duplicate observations, insufficient independent sellers,
stale snapshots, new unsupported cohorts with >=3 sellers, failed/missing cases,
changed generation and incorrect native/report expectations.

44 focused maintenance/integration tests pass. All 86 published Waterwalk cases
pass in 67.26s, with sources_unchanged=true. The actual registry gate accepts the
83 explicit boundary report contracts and marks Waterwalk trade qualification
reviewed. Verified against selected generation:
`56094eb44d8c8bbfa8f345eebe9cbb41c41007178fa6272317e01aacd1105a63`.
Receipt: `pricing/data/report-receipts/waterwalk-registered-trade.json`.
Proof: `pricing/data/appraisal-waterwalk-registered-review-2026-10-02.json`.
Registry locator is /rows/45 (46 registered identities total). Only Waterwalk's
current receipt was loaded for this acceptance check; do not claim all 46 current.
The two other upgraded one-seller cohorts and 19 unproven observations remain
explicit in the census, not silently deemed worthless or promoted to candidates.

Executed guarded registration script `tmp/register-waterwalk-review.py`; do not
rerun. No runtime policy/publication change this turn. Lint/format clean, all
processes terminal. No live calls, restart, staging or commit. Worker restart from
the earlier Python changes remains outstanding. Full all-item goal is unfinished.


## Chance Guards material census — 2026-10-02

Added maintenance/chance_guards_market_review.py, a conservative native-defense
variant census. Verified native mgl8..9 (original ED max+1=10), xmg37..44 and
umg59..67, intrinsic ED20..30 and flat15 after percentage defense. Upgraded base
rerolls retained; original ethereal includes conservative8..10 pre-multiplier
possibilities to avoid pretending uncertain order is an exact ethereal formula.
Never reinterpret property399 as total1855. Explicit contradictory facets fail.

Artifact pricing/data/appraisal-chance-guards-material-review.json accounts for
all100 observations:82 foreign/unverified scope,1 invalid asking terms,3 ambiguous
unit,9 ambiguous variant,3 conflicting/missing variant,2 proven variants. Proven
rows199fcf7dca647f90d3b44c14 and193848714bf61d71d6f87129 are elite/nonethereal,
40MF, total99 and102 respectively; only2independent sellers, different total
rolls, so no threshold or price established. The99row has30ED;102implies maximum
nonethereal elite total. Keep remaining observations unresolved. No runtime rule
or publication changes. This is source-bound research, not formal trade closure.

Red missing-module then20newtests green;32tests including shared Waterwalk census
regressions pass. Ruff check/format pass. All processes terminal. No live calls,
staging, commit or restart. Goal remains active. Next: a different valuable named
item with usable evidence, or remaining scope migration; do not repeat this cache
research without new evidence. Global receipts remain historical after source
changes; renew together at coherent final checkpoint.


## Aldur / Horazon base-defense validation — 2026-10-02

Implemented mechanics/plain_set_defense.py and wired it into market comparison
and NamedHandler capture contracts. Aldur's Advance: xtb39..47 / utb59..68;
Horazon's Hold: xlg28..35 / ulg54..62. Native armor/setitems hashes pinned; no
standalone or partial item defense modifiers. Defense can prove missing base;
conflicting explicit tier/upgrade/base, ethereal, sockets, bonus-defense399,
enhanced-defense425 or inserts are rejected. Cached rows are not mutated.
Missing total defense cannot establish an exact numeric comparison. Existing
baseline tiers and build-use assessment remain separate. Python restart needed.

Real regression: Aldur row88e98e15926f0a530aec5b77 saysElite but defense40;
now rejected rather than accepted as upgraded equipment. Impossible captured
Mirrored Boots defense40 also rejected. Positive native totals remain accepted.
14 initial tests failed before implementation; final named regression182pass
(217.01s). Published Aldur/Horazon bank82pass (45.54s), sources_unchanged=True,
receipt pricing/data/report-receipts/plain-set-defense.json. All20saved replays
unchanged in entirety vs tmp/waterwalk-original-replays.json; current replay
 tmp/plain-set-defense-replays.json. Ruff/diff checks pass. All processes terminal.

Current generation56094eb44d8c8bbfa8f345eebe9cbb41c41007178fa6272317e01aacd1105a63
already contains pinned native inputs; strict published snapshot verified. No data
republication necessary for these Python-only changes. No restart/live collection/
staging/commit. Proof pricing/data/appraisal-plain-set-defense-review-2026-10-02.json
accounts for50cached rows each: Aldur38scope,8ambiguous/conflicting,4provenbase;
Horazon38scope,4invalidterms,7ambiguous/conflicting,1provenbase. Trade thresholds
remain unresolved; this does not mark either identity trade-reviewed. All-item
goal active. Move to remaining valuable identities or scope migration; do not
repeat these cache audits absent changed inputs. Global final gates still pending.


## Stormshield defense conventions audited — 2026-10-02

Added maintenance/stormshield_market_review.py and10tests. Red import failure,
then30tests including ChanceGuards regressions pass; final Ruff/format clean.
Artifact pricing/data/appraisal-stormshield-material-review.json source-pins
native armor/unique definitions, itemstatcost214 op4,param3,level->armorclass,
market snapshot/raw sources/currency and shared eligibility helper implementations.
Stormshield coefficient30/8 per level; Monarch133..148. Defense1855 and level
bonus436 cannot be blindly pooled or interpreted as the same underlying roll.

All100rows accounted:45unverifiedscope,5invalidterms,2ambiguousunit,7impossible
levelbonuses,1mixed/conflictingfields,8missingtotal,23base-defense-compatible,
5displayed-total-compatible,4ambiguous totals/socket contributions. The5displayed
rows use371bonus at99 and total510..517; allone seller2992509356. Native-roll
proof remainsfalse: unknowninserts may contribute to the candidate residual.
Base-compatible148 may be base-field convention or a low-level displayed total;
no implicit conversion. This is material research, NOT trade qualification,
completed pricing disposition, numerical price or runtime correction.

No runtime/publication change, livecalls, staging,commit orrestart. Allprocesses
terminal. Fullgoalactive. Next meaningful paths: underlying-item Stormshield
trade review (fixedDR/block and scoped demand, independently of premiumdefense),
or othervaluable identities with usable evidence. Do not repeat this cache audit
without new evidence. Globalfinalgates and runtime restart still pending.


## Stormshield underlying trade candidate published — 2026-10-02

Implemented policies/stormshield_trade.py, separate source-bound rule JSON,
trade dispatch, runtime input pinning and publication validation. Fixed35DR,
35FBR,30STR,25lightning/60coldres and native214coefficient30 must be decoded;
complete identified nonethereal Monarch,0/1sockets, legal captured base defense
required. Unknown/inconsistent facts unresolved. Empty defense133..148 qualifies;
filled/unknown1socket may adddefense and appends Assess inserts separately.
No defense premium, socket-price inference, numeric estimate or liquidity claim.

Evidence:3independent SC/NL/PC/RotW single-item activeasks:
b6939376ed994646925b04e4 (seller3808639742,140def),
b6cfb60a2673fb2fce45fe2f (4206826233,142def),
abaec9b00dc4bf3120fd8cbe (1002488439940,139def).
Source-pinned whole Ubers variants: lightning-fury-amazon-guide3,
lightning-sorceress3,meteor-sorceress4. Hardcore variants notused. Research
133..142 is a conservative asking cohort, not a user threshold/native-roll proof;
unknown contents remainunknown. Existing low baseline unchanged.

Red17initial failures;26policy tests green, then86shared policy/regression tests
pass211.91s.32staged and32published bankcases pass; published35.02s receipt
pricing/data/report-receipts/stormshield-underlying-trade.json has sources_unchanged
true.32cases assert qualification, exact renderedtext andblue tier_low, including
emptydefense bounds,filled/unknown inserts,missingfixedstats and variantunknowns.
20saved replays unchanged extraction/price/text vs tmp/plain-set-defense-replays.json;
new tmp/stormshield-published-replays.json. Ruffcheck/format/diffcheck clean.

Published via API validate=load_runtime WITHOUTpruning retained generations:
a3cc9193e31e26b0228d62177833884f0ecb30c7bb500b1a84f6367b38170b89 (174artifacts).
Previous56094 retained. Proof
pricing/data/appraisal-stormshield-underlying-publication-2026-10-02.json.
Allprocesses terminal. No livecalls/staging/commit/restart. Pythonworker restart
needed. Formaltrade review registry integration remains next: native independent
oracle+source context and32boundarycases binding, then realreceipt acceptance.
Do not claim full Stormshield premium/price closure or all-item completion.
Globalregistry receipts stale after source/generation changes; renew together.
Goal remains active. Broad remaining valuable items/scope/finalgates still pending.


## Stormshield formal underlying review accepted — 2026-10-02

Added maintenance/trade_stormshield.py independent native-definition/stat semantics
and report oracle; wired native_unique_underlying_stormshield into trade_reviews
context binding and scope routing. Oracle initially rejected the32-case bank for
missing zero-socket unknown/null contents and per-benefit lower/upper boundaries.
Expanded to46cases: native fixedbenefits, each missing/minus1/plus1, defensecorners,
filled/unknown/null inserts, unknown variants and incompletecapture.26previous
policytests unaffected; thisturn32maintenance/integrationtests pass6.01s. Tests
reject native coefficient/denominator/base changes, incorrect colors/verdicts,
omitted boundaries, failedexecution and stalegeneration/policy. Lint/format clean.

Executed guarded tmp/register-stormshield-review.py (do not rerun). Registrynow47
rows; Stormshield/rows/46 binds currentpublishedsourcepolicy,definitions and46explicit
trade-casecontracts. Realpublishedrun46pass37.76s withsources_unchanged=True:
pricing/data/report-receipts/stormshield-registered-trade.json.
Fullactualregistry validation accepts Stormshield currentreceipt and marks its
underlyingtradequalification reviewed. Proof
pricing/data/appraisal-stormshield-registered-review-2026-10-02.json.
OnlyStormshield receiptloaded for acceptance; other46NOT renewed or claimedcurrent.

Selectedgeneration unchanged a3cc9193e31e26b0228d62177833884f0ecb30c7bb500b1a84f6367b38170b89.
No runtimepolicy/data change or republish thisturn. No livecalls/restart/staging/
commit; allprocesses terminal. Runtime restart stillpending frompriorPythonwork.
This gate doesnotestablish defense/insertpremiums or numericalpricing.

Next: move to another valuable identity/configuration or outstanding scope migration;
do notrepeat Stormshield basequalification gate withoutchangedinputs. Preserve
source-bound material census and unresolveddefenseconventions. Globalfinalgates
and all-itemcompletion remainunfinished; keepgoalactive and renewbroadreceipts
only at coherentcheckpoint.


## Death's Fathom native cold bounds audited — 2026-10-02

Added maintenance/fathom_market_review.py, source-bound all100-row census. Verified
uniqueitems354nativeextra-cold15..30 and coldFacets393/397extra-cold3..5. Only
explicit single ColdDeath/ColdLevel-Up inserts support bounded subtraction;
unknown/Jewel/firefacet descriptions remainunknown. Emptyknown sockets use native
15..30; impossiblecount/base/upgrade/property contradictions rejected. Market517
is +ColdSkills(SorceressOnly), NOT cold-skill-damage747; do not substitute it.

Artifact pricing/data/appraisal-fathom-material-review.json:56unknownsocket,
31unverifiedscope,3boundedcoldfacet,4missingcolddamage,5invalidterms,1invalidcoldtotal.
03fc2a4225207112802f7877 total30+coldfacet impliesnative25..27;
b4019831ee92b04481bf8b5a total34 implies29..30;
c6b57e988ef4783e4bfd6279 total35 implies30+5facet. All3etherealunknown. Onlyone
perfect-native seller3007646996, so no supportedpremiumthreshold or exactprice.
Bounds interpret the declared cold-damage field as total; no implicit correction
of seller fields. Resistance/ethereal/facet-pierce/trigger comparisons remain
separate. This is materialresearch, not runtimequalification/pricingclosure.

Redmissingmodule then18newtests pass;48withStormshield/ChanceGuards audits pass.
Ruffcheck/format clean. Allprocesses terminal. No livecalls/restart/staging/commit
or runtimepublication change. Selectedgeneration remains a3cc9193e31e26b0228d62177833884f0ecb30c7bb500b1a84f6367b38170b89.
Goalactive/unfinished. Next: continuevaluableidentity/variant review orscope
migration; do not repeatthiscacheauditabsent newevidence. Formal Stormshield
underlyingreview accepted previously, no needredo. Broadreceipts/finalgatesstill
pending; sourcechanges invalidate priorglobalverification receipts.


## Named elemental-roll legality fixed — 2026-10-02

Reproduced actual pricing-contract bug: empty Death'sFathom40cold accepted.
11red/2green initialtests. Added native329..336 elemental mastery/pierce scalars
to named_rolls.BOUNDED_STATS. Variable rolls nowchecked against nativeinteger
ranges, including Eschuta fire/lightning, Fathom/Nightwing/Ormus cold and Griffon/
DeathWeb pierce. Socketadjusted facts remainseparate; known5coldfacet subtraction
35->30passes and original total35unchanged. Fixed-stat semantics notexpanded.

32focusedtests pass;158namedregressions pass185.09s.5fullpublished Fathomcases
(14,15,30,31,40cold) pass23.09s.20saved replays unchanged extraction/price/text
vs tmp/stormshield-published-replays.json; new tmp/elemental-roll-replays.json.
Ruffclean. No datarepublishneeded; currenta3cc9193... selected nativeinputsused.
Pythonrestartstillpending. No livecalls,staging,commit. Allprocesses terminal.

Receipt pricing/data/report-receipts/fathom-roll-bounds.json hadunchangedsources
DURINGrun but strictcurrentverificationfailed AFTERrun because unrelated external
edits changed inventory_tracking/terror/{chance,zones}.py,
 tests/inventory_tracking/terror/{test_chance,test_zones}.py and
 tests/terror_zones/test_game_files.py. Preserveedits. DoNOT claimcurrentwhole-repo
receipt or reruninbusyloop. Proof
pricing/data/appraisal-elemental-roll-boundary-fix-2026-10-02.json recordschanges.
Globalfinalgatesremainpending; thisisnotnewpricecoverageortradequalification.

Next: continuevaluableitemrollreview orscopeclosure; enforcelegalrolls inrelated
paths onlywhereexisting source-backed semantics justify it. Rebindreceipts at
coherentcheckpoint aftersources settle. Fullgoal active/unfinished.

