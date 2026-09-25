# Offline item assessment implementation

Implemented 2026-09-24. Typed runtime entry: `engine.assess_result(extraction)`,
used by `pricing.knowledge.pipeline.retrieve_draft`. The compatibility entry
`engine.assess(extraction)` and report output use the same version-1 projection.
Offline only.

The first slice replaces generic 20% nearby-roll pricing with exact variant
contracts. No price can bypass those contracts through a name/facet summary.
Prices are finalized through `assessment.pricing.finalize_assessment`; the unused
`pricing.knowledge.valuation` compatibility stub has been removed. Evidence discovery uses normalized facts through
`adapters/discovery.py`; the old label adapter has been removed.

## Responsibilities

- `domain/facts.py`, `domain/contracts.py`, `adapters/capture.py`: native stat ID + parameter, raw values, provenance,
  known/unknown identity facets, captured vs derived values and completeness gaps.
  Level formulas retain coefficients and use level 90 for comparisons, independent
  of the hovering character. Display strings are not semantic identifiers.
- `registry.py`: deterministic quality/family dispatch from local metadata item types;
  ambiguous registry matches fail explicitly, unsupported types remain unsupported.
- `profiles.py`, `build_profiles.py`: reviewed, source-backed build-role predicates.
  The portable artifact preserves source locator/hash/date and explicit conditions.
- `handlers/`: base, affixed, named and runeword comparison contracts, composing
  verified family mechanics. Remaining contribution/variant gaps stay explicit;
  family classification alone does not establish price coverage.
- `comparables.py`: strict SC/NL/PC/RotW, exact identity/quality/ethereal/socket/contents
  and symmetric modifier matching. Missing or extra listing properties reject a match.
  Every rejection has reasons; full accepted listings remain in JSON diagnostics.
- `coverage.py`: reproducible family, rule and missing-policy coverage.

Build suitability and market comparability are independent. Identical fully known
variants can supply price evidence without a guide endorsement. No guide score is
converted into Ist. Generic guide mentions remain watch/discovery context.

## Current reviewed profiles

Five rules: Echoing Strike starter dagger candidate, Abyss pre-Spirit dagger
candidate, and the three Sazabi set components for Echoing Strike Ubers mercenary.
Dagger eligibility is an explicit reviewed interpretation of the cited starter
advice and skill definitions, not a guide endorsement of every rare dagger.
A failed role predicate rejects that candidate role only, not the item's entire
usefulness. Context conditions leave these assessments partial; they do not certify
whole-build FCR, equipped set bonuses or mercenary readiness.

Sazabi reports the requested socket rune, missing set companions and Act 5 Frenzy
context. These are the specific guide setup's requirements, not claims that an
unsocketed component is worthless. No companion item is inferred from the hover.

## Price publication

Requires at least three independent sellers, known observation dates within 30 days,
and max/min ask dispersion no greater than five. These are explicit conservative
engineering defaults, not learned market rules. No arbitrary price multipliers.
One/two-seller and older cohorts remain diagnostics, not a numerical item estimate.
Missing price evidence is unknown, not zero/vendor. Asks are never labeled fills.

Base defense, completed runewords, named-item contributions, charms/jewels and other
armor slots still need dedicated contracts. Parameterized skill/proc/per-level
market mappings are also incomplete. This intentionally abstains more often than
the former matcher. Weapon affix contracts require observed ED components; missing
modifier coverage does not imply zero ED. Unknown flag/content fields cannot price.

## Maintenance and validation

```
uv run --offline python -m pricing.knowledge.assessment.build_profiles
uv run --offline python -m pricing.knowledge.assessment.coverage
uv run --offline pytest tests/pricing/knowledge/assessment tests/inventory_tracking/items/test_dread_edge.py -q
```

Artifacts: `pricing/data/appraisal-build-profiles.json` and
`pricing/data/appraisal-assessment-coverage.json`. Restore these with the other
portable KB data. Build-profile publication replaces a validated artifact atomically.
Missing/incompatible profiles yield visible coverage gaps; no network fetch occurs.
A running worker needs restarting for new Python, metadata or profile data.

Regression captures include Dread Edge and Sazabi's Mental Sheath, with screenshot
truth stored separately from raw memory. Dread Edge now decodes Warlock tree layer57,
maximum damage per level (native218/op4), and base cold duration. Native stat218 is
explicitly supported; other unverified op4/op5 effects are not generalized.

Next: implement named-item contribution/roll contracts and clean armor/shield
variants; review additional slot-specific role profiles and parameterized market
adapters. See [the full design](../ASSESSMENT_DESIGN.md). A source-specific profile
needs both a passing and failing item case before expanding live valuation coverage.

## Runeword-base utility and terminal reports

`base_use.py` evaluates clean bases independently of pricing contracts. It reads
`appraisal-utility.json` (rebuild via `pricing.knowledge.utility`), joining verified
recipe/type/socket edges with curated recommended-base rows. Those rows preserve
WP-A/WP-G/Maxroll source locators; native flags and rolls come from the capture.
No network or third-party checkout is required during appraisal.

Reviewed roles: Act 2 mercenary Insight/Infinity/Pride/Obedience; Phase Blade Grief;
Monarch/Sacred Targe Spirit; player Enigma armor and mercenary Fortitude armor.
Perfect preferred weapon bases require known empty correct sockets, ethereal status
appropriate to the role, 15% superior ED, +3 AR and complete identified capture.
This is a perfect preferred base, not a claim of universally best mercenary DPS:
IAS breakpoints, requirements and other equipment can change the optimal choice.
Armor defense perfection remains unverified; shield inherent resistance is checked
separately. Other recipes retain compatibility evidence without a quality verdict.
Unsocketed superior bases cannot use cube socketing; impossible Larzuk counts are
reported as impossible preparation. Unknown item level stays conditional.

Terminal output contains item stats, applicable build/base uses, actionable missing
properties, price or one specific price blocker, and actual unreadable fields.
Generic coverage, historical-price/methodology caveats and workflow instructions
remain in JSON rather than repeating on every item. Shared base-use notes are
printed once; perfect preferred bases are green. Numeric market valuation is unchanged.

## Completed runeword records

Run `uv run --offline python -m pricing.knowledge.runewords` before rebuilding the
index. The portable `appraisal-runewords.json` joins all 99 definitions with their
variable ranges, base codes, rune sequences, curated demand (67 identities), and
actual scoped market observation counts. The 2026-09-24 collection cached 6,642
active observations, including 4,384 scoped SC/NL/PC/RotW asks covering 98 of 99
definitions (Zephyr has none in this sample). Recipe or rune cost is not sale data.

The completed-runeword handler replaces the unconditional unsupported policy. It
requires identified complete capture, compatible base, filled recipe socket count,
all variable stats and verified property mappings. Armor/shields/helms additionally
compare total defense. Comparison contracts include base_code separately from the
runeword name; listings without an independently normalized base are rejected.
Base selector normalization is verified against cached API responses, including
case-only Hustle variant names. Omitted ethereal flags remain unknown. Strict
comparison can still abstain: listings often omit fixed/variable modifiers, and
parameterized market mappings are incomplete. Coverage of a name is not coverage
of every base/roll combination. Raw responses, fetch dates, source URLs and scope
quarantine remain available offline. Collection is resumable and stops on errors.

## Ethereal preference colors

`ethereal.py` publishes a source-tagged preference in each assessment; it does not
change a price estimate. Presentation maps preferred/no to readable blue,
preferred/yes to green, and avoid/yes to red. Avoid/no and unreviewed or unknown
items stay neutral. The same semantic tones drive Rich terminal output and GTK OSD.

Reviewed positive rules: elite recommended Act2 mercenary weapon bases with useful
socket counts, Cryptic Axe, Andariel's Visage, Titan's Revenge, Sandstorm Trek, and
The Reaper's Toll. Negative rules: ethereal War Traveler, Arachnid Mesh, Chance
Guards and Magefist for player use. Sources are WP-G/WP-I/build records, not price
multipliers. Indestructible/self-repair and incomplete capture suppress negative
rules. Other uniques, mixed-use armor, caster weapons and rare/magic bases require
reviewed rules; no blanket ethereal penalty is applied. Red means a durability
tradeoff for the reviewed use, never a zero-value/vendor verdict.

## Exact family pricing expansion — 2026-09-24

Empty-socket base comparisons now support weapons, armor, shields, helms and
accessories. Affixed comparisons additionally support charms and jewels. Armor
families require captured total defense and compare it via verified property 1855.
The named handler supports unique/set identities from offline definitions, verifies
base compatibility, requires definition stat keys including skill parameters, and
keeps exact modifiers, ethereal and socket state in the contract. Named contracts
also require an independently verified listing base; unsupported upgrades remain
explicit gaps. Set ethereal conflicts are rejected. Filled socket contribution
contracts are still pending.

These are exact comparison policies, not completed build-role/value-tier coverage.
Cached named listings frequently lack verified base, socket/ethereal facets or fetch
dates; they remain ineligible rather than being guessed. Future named normalization
must resolve these with source evidence. The report prints the actual blocker
instead of the former blanket unique/set-not-implemented message.

## Shared rule predicates and Infinity roles — 2026-09-24

Profiles can now declare validated `must` predicates with all/any/not composition,
exact native-stat thresholds, item facts and context conditions. Results retain a
structured trace; false rejects a role, missing evidence keeps it conditional.
The catalog validator checks nested native keys as well as important-roll selectors.
Eight profiles are published: the original five plus Nova player Infinity, Nova
Hydra Hybrid mercenary Infinity, and Lightning Strike player Infinity. The latter
uses the Amazon spear family; Nova uses ordinary polearm/spear candidates. Each
requires the actual Conviction aura and correct recipe/socket identity. Wearer
lightning pierce and mercenary weapon damage have distinct importance lists.
Whole-loadout fit remains conditional; these profiles do not widen price cohorts.

## Leveling assessment — 2026-09-24

`policies/leveling.py` joins the 75 reviewed recommendation records to 55 stable
named identities. The engine reports independent leveling tiers and source-specific
class/archetype/side conditions; the shared report highlights them in teal.
Existing reviewed recommendation priority 1 maps to high, 2/3 to med and 5 to low
(farming-first utility). This ordering is not a trade-price tier or multiplier.
Death's pair and other companion requirements remain conditional. Original equip
requirements are only shown for an unchanged non-ethereal unsocketed base. Missing
research is not a none/trash verdict. Unreviewed candidates and non-named leveling
policies still need expansion.

## Conditional named trade tiers — 2026-09-24

`rules/named_tiers.json` contains reviewed dated qualitative ask-segment policies;
`policies/named_tiers.py` evaluates them independently of numerical price evidence.
Initial identities: War Traveler, Titan's Revenge, Raven Frost, Sandstorm Trek and
Skin of the Vipermagi. Premiums require the actual roll/ethereal predicates; unknown
facts yield conditional tiers. The report includes the cached source date. Unreviewed
identities are pending, never automatically trash. All-definition tier completion,
set policies and further premium/upgrade variants remain outstanding.

### Expanded named segments

The reviewed catalog now covers 22 named identities. Added Arachnid Mesh,
Bul-Kathos' Wedding Band, Chance Guards, Death's Fathom, Dracul's Grasp,
Gore Rider, Herald of Zakarum, Nightwing's Veil, Shadow Dancer, Verdungo's
Hearty Cord, Waterwalk, Windforce and Wisp Projector roll segments; fixed
baseline tiers for Guillaume's Face, Tal Rasha's Adjudication, Highlord's
Wrath and The Stone of Jordan. Source High/HR segments share `high`, Mid
maps to `med`, and Low to `low`. Individual premium bands can therefore
share a tier; exact numeric estimates still require comparable evidence.

These new policies cover non-ethereal original bases. Roll-based policies
require empty sockets because captured totals cannot yet isolate inserted
jewel/rune bonuses. Unknown occupancy leaves the tier conditional; filled
sockets prevent treating augmented stats as natural premium rolls. This
restriction also applies to the initial five roll policies. Unsupported
ethereal/upgrade variants remain pending, not worthless. Set tiers describe
trade demand separately from leveling and full-set utility.

### Native market projection

`adapters/market_projection.py` supplies reviewed parameter-specific mappings
missing from decoder scalar facets. It uses native identity and decoded numeric
units, independent of tooltip wording. Class skills, skill tabs, staffmods, oskills
and equipped auras remain distinct. Conflicting decoder projections block pricing
rather than silently replacing a value. This resolves several saved rare/named
item mapping gaps; it does not bypass stat completeness or socket checks.

### Named coverage audit

Run `uv run --offline python -m pricing.knowledge.assessment.maintenance.coverage`
to enumerate every normalized unique/set identity against executable tier policies
and WP-I named market research. The audit validates source fingerprints, JSON
pointers and exact item/quality identity; stale sources do not count as reviewed.
The report distinguishes research awaiting a policy from absent WP-I research.
Absence here is not absence from other KB demand/leveling sources. Identity policy
coverage is also not proof of all-variant or numeric-price coverage. Current census:
565 identities, 22 reviewed policies, 65 WP-I research-only, 478 without WP-I rows.

### Set baseline tiers

Added 18 reviewed set baseline policies from WP-I: Aldur's Advance; Bane's
Authority/Oathmaker/Wraithskin; Horazon's Countenance/Dominion/Hold/Legacy/Secrets;
Immortal King's Detail/Forge/Pillar/Soul Cage/Will; Tal Rasha's Fine-Spun Cloth,
Horadric Crest and Lidless Eye; Trang-Oul's Claws. Source Floor maps to `trash`
trade tier, Floor–Low and Low to `low`. This is a trade segment, not vendor advice;
leveling and set-completion uses remain independent. Policies apply to original
non-ethereal bases with empty sockets, without a claimed priced premium for rolls.
Naj's Puzzler remains unreviewed because the source has only two listings. Named
policy coverage is now 40 identities (20 set), with 47 other WP-I rows pending.

### Circlet roles

Six additional rules bring the reviewed profile count to18. Rare +2 class/20FCR
candidates cover Poison Nova Standard, FoH Tri-Brid, Abyss Standard and Berserk
Max Mobility; source-specific secondary rolls and sockets are preferences.
Magic +3 Fire circlets retain separate Enchant Standard and Max Enchant roles.
The family includes Circlet, Coronet, Tiara and Diadem; exact base still matters
for pricing and requirements. Eligibility for these cited setups is independent
of numeric price and does not imply other skill/quality combinations are worthless.

### Socket preparation odds

Unsocketed normal-base reports include the cube chance of the required socket
count for each possible item-level cap. Probabilities use the cached socket-guide
six-roll/clamping rule. Unknown item level produces separate conditional outcomes,
not an averaged chance. Superior bases remain cube-ineligible, and neither cube
nor Larzuk advice suggests changing an existing socket count.

### Additional premium uniques

Named tier policies now cover45 identities: added Andariel's Visage, Griffon's Eye,
Mara's Kaleidoscope, Death's Web and Crown of Ages. These preserve joint-roll,
ethereal and socket-specific premiums. Broad high tiers can contain several asking
segments; reasons distinguish perfect combinations without inventing numeric prices.
Mara's27–29 segment retains its one-seller-dominated evidence limitation. All45
source fingerprints and exact named references pass the coverage audit;42 other
WP-I records remain pending alongside478 identities without rows in that source.

### Fixed runeword comparison fields

Completed-runeword contracts can declare proven intrinsic recipe properties.
Listings may omit these fixed bonuses, but explicitly conflicting values still
reject. The handler marks a field intrinsic only when the captured decoded value,
native ID/parameter, market projection and fixed recipe definition agree. Variable
rolls, augmented totals and other properties still compare exactly. Rune-derived
bonuses are not covered by this step; absent ethereal flags remain unknown.

### Portable rune contributions

The definition builder now compiles supported scalar rune socket effects by
weapon/shield/armor/helm destination, with source fingerprints. Intrinsic runeword
comparison combines these with recipe bonuses. Repeated runes add; variable ranges
and base-augmented observed totals remain explicit comparison fields. Unsupported
encoded effects are not inferred. Rebuild dependent artifact fingerprints and
restart long-lived workers after changing definitions (current loader caches them).

### Definition reloads

The shared definition store replaces process-lifetime caches in named assessment,
runeword assessment and runeword listing normalization. Valid file replacements
load a new immutable, content-hashed generation automatically. Unchanged files use
a metadata signature check; invalid updates are rejected and later valid updates
recover. CLI publication uses atomic replacement. This supersedes the restart note
above for these consumers; it does not yet provide a transaction across every KB
artifact and SQLite index, or change the decoder's separate metadata cache.

### Rare boot candidates

Ten boot profiles bring reviewed build coverage to28 rules. Source-specific
movement/triple-resistance, gold-find/fire-resistance, and starter movement/fire
combinations remain distinct. Lower rolls can be candidates; planner maxima,
FHR, MF, dexterity and poison-length reduction are preferences where cited.
Build fit remains conditional on the full loadout and never supplies a price by
itself. Hardcore-only and unendorsed planner-only variants were not converted to
Softcore trade demand in this slice.

### Compiled skill projections

`maintenance.market_projection` builds the portable native market-property map
for class skills, skill tabs, staffmods/oskills and equipped auras. It requires
exact scalar labels, except explicitly reviewed wording aliases, and records
ambiguous/unmatched candidates instead of guessing. Runtime projection uses native
ID/parameter and decoded units. Current artifact contains199 unambiguous mappings;
this is not a claim that every market property or skill combination is supported.

### Broader unique baselines

Twenty further source-reviewed unique baselines bring named tier coverage to65
identities. These include common caster/leveling uniques, two reviewed Ars books
and RotW socket jewels. Floor trade tiers never suppress independent leveling
recommendations; Peasant Crown is covered by regression. Baselines are restricted
to original non-ethereal bases with empty sockets. Of the87 normalized identities
in WP-I,22 still need policy review;478 others have no row in that source.

### Further roll scopes

Named policy coverage now reaches69 identities. Shako defense130+ retains an
upper-segment reason within med; Gheed MF38+ receives high. Ravenlore respects its
native20 fire-pierce maximum rather than treating cached21–25 values as natural
rolls. Eschuta coverage is deliberately restricted to the source-reviewed +3Sorc/
20lightning premium; other variants still need review. Identity coverage does not
mean complete variant coverage or an available numeric estimate.

### Shield-base intrinsic blocking

Runeword definitions now retain shield blocking by exact base code, verified from
the offline armor table/type hierarchy. Comparison combines this fixed base value
with recipe/rune effects only when the captured total agrees. Variable and augmented
values remain explicit. Saved Spirit's required listing modifiers are now its
FCR, mana, magic absorb and defense; missing scope/ethereal evidence still blocks
real cached estimates. A saved-capture test proves valid synthetic comparisons can
reach the numeric estimate path without dropping identity or scope checks.

### Named intrinsic comparison fields

Unique/set contracts now use the same fixed-property verifier as runewords.
A listing can omit a proven unchanged fixed definition bonus; explicitly different
values still reject. Variable rolls, observed armor defense, exact identity/base,
ethereal state, sockets and market scope remain required. Saved Sazabi coverage
checks its fixed all-skills bonus separately from variable resistances/defense.

### Class-skill and crafted gloves

Eight glove rules bring reviewed build coverage to36 profiles. Magic3Javelin/20IAS
and rare2Javelin/20IAS candidates stay separate; Lightning Strike's boss swap keeps
its Arachnid Mesh dependency. Crafted Knockback and Crushing Blow mechanisms use
distinct Double Throw, Smite and Dragon Talon profiles. Secondary planner maxima
are preferences; source-specific eligibility never supplies a numerical price or
rejects every other use of a glove.

### Player versus mercenary base use

Preferred mercenary bases require mercenary recommendation evidence, not merely
a matching recipe recommendation. Scythe now has a separate Nova self-wielded
Infinity use; it does not inherit physical ED/AR premiums. Archon Plate Fortitude
has independent player and mercenary advice, including opposite ethereal priorities.
Socket preparation applies to both uses; neither is a universal best-base ranking.

### RotW rings and remaining belts

Reviewed named policies now cover74 identities. Sling preserves its native3–5%
magic-pierce range and distinguishes the perfect asking segment; Opalvein requires
all four native resistances within6–8. Measured Wrath has a med baseline;
Trang-Oul's Girth and Thundergod's Vigor have low trade baselines independently of
build usefulness. Modified, unknown or out-of-range key rolls stay unresolved.
These qualitative tiers do not substitute for matched numerical comparisons.

### Random skill-tree variants

Wraithstep raises reviewed named coverage to75. Its Demon, Eldritch and Chaos
variants each retain their own asking-segment reason. A complete capture must
establish exactly one native +1 tree. Named comparisons inspect the preserved
`skilltab-war` definition separately from scalar ranges and require the selected
tree's market projection. Missing or contradictory random skills cannot silently
produce a comparison contract. No cross-tree numeric estimate is inferred.

### Equivalent resistance representations

Exact comparisons normalize an isolated All Resistances property into its four
elemental totals on both sides. This supports rare/magic comparisons and unchanged
named/runeword intrinsic bonuses without introducing roll tolerance. Mixed combined
and individual resistance fields are ambiguous and rejected. Nonfinite, boolean
and string resistance values are invalid. Original listing evidence is preserved.

### Impossible variants in non-equipment market catalogs

Verified Ring/Amulet (misc), Small/Large/Grand Charm (charms), and Jewel (jewels)
catalogs supply zero sockets, empty contents and nonethereal status when listings
omit those fields. Each derived facet records base-mechanics provenance; raw
seller properties remain intact. Explicit contradictory or malformed fields create
comparison-blocking conflicts. Armor/weapons and unknown identities retain unknown
facets. This removes impossible-variant blockers without inventing dates, scope,
rarity or price evidence.

Named unique/set jewelry, charms and jewels resolve through the shared definition
catalog before receiving the same impossible-variant facts. All legacy definition
variants must agree on one non-equipment base. The base-code provenance records
the catalog generation; explicitly different supplied bases produce a conflict.
Equipment identities never imply an original base, because upgrades may differ.

### Defensive shield and set-maul baselines

Stormshield and Immortal King's Stone Crusher bring named policy coverage to77.
Both have low broad trade tiers backed by scoped cached asks. IK's perfect40CB
is highlighted without assigning an unsupported higher tier;35–39 remain low,
and the policy requires the original two empty sockets. Stormshield's defensive
build role does not imply a high trade tier or a character-level defense premium.

### Low-to-mid researched named cohorts

Tal Rasha's Guardianship, Bloodpact Shard, Ondal's Wisdom and Skullder's Ire
now have med baseline policies (81 reviewed identities). Bounds check their
native MF, skill or ED bonus; original nonethereal empty-content variants only.
The cached evidence does not establish separate numerical roll premiums or ethereal
Skullder pricing. Build/leveling usefulness stays separate from this trade tier.

Ormus' Robes comparisons now require exactly one native Sorceress skill in the
definition's inclusive36–60 ID range, with the fixed +3 bonus and matching market
projection. `skill-rand` min/max are IDs, not bonus ranges. Missing, partial,
out-of-range, multiple or wrongly projected skills prevent a price contract.
The shared validator also rejects extra native skill-tree choices on Wraithstep.

### Runtime tier evidence validation

Named tier assessment and coverage auditing share source fingerprint, JSON-pointer,
identity and repository-containment checks. Changed/missing evidence returns a
pending tier with a specific JSON diagnostic; it cannot continue presenting a
reviewed tier silently. Re-publishing reviewed evidence restores the tier in the
same process. Stable source documents are cached by device/inode/size/mtime/ctime;
reads verify the file signature before and after to detect concurrent replacement.

### Required skill evidence

Legacy `required_any_stats` profiles now use the same three-state native predicate
engine as newer role rules. Undecoded, malformed or conflicting bonuses remain
unknown; only a complete gap-free inventory proves absence. Semantic skills no
longer require presentation text. A `skill_trace` records individual alternatives
and the resulting decision alongside each role's main rule trace.

### Sorceress amulet roles

Ten source-specific profiles bring reviewed build roles to46. Magic amulets cover
Lightning/Nova/Blizzard starters and Enchant Budget/Max Enchant. Crafted amulets
cover Nova Standard/MF/Hydra and Enchant Standard/MF. Skill tree/class, rarity and
FCR thresholds remain distinct; planner life/mana/resistance/MF maxima are
preferences. Enchant prebuff keeps its equipment-swap condition. Whole-loadout
conditions remain visible, and these roles never convert build demand into prices.

### Rare caster-ring roles

Six Lightning/Nova/Blizzard profiles bring reviewed roles to52. Candidate checks
separate FCR/mana/fire+cold resistance, Uber lightning resistance, Nova three
resistances, Blizzard starter strength/life/cold resistance and MF setups.
Secondary planner maxima remain preferences; complete-loadout conditions stay
explicit. Nova's cached summary does not identify the three elements, so that
profile requires checking the actual resistance deficits before calling it a fit.

Build-profile publication now verifies that every source JSON pointer resolves,
in addition to its file fingerprint. Shared pointer parsing rejects negative or
noncanonical array indexes and malformed escapes; named-tier evidence uses the
same resolver. All52 published profile locators pass this check. Pointer existence
is provenance validation, not automatic proof that a rule interprets its source
correctly; semantic review remains required.

### Grand Charm skill roles

Ten profiles bring reviewed roles to62: plain starter skillers and distinct life
or12%FHR variants for Lightning, Nova, Blizzard, Poison Nova, Lightning Fury and
Blessed Hammer. Native skill-tree identity remains mandatory;45 life is a planner
preference, with lower life still a candidate. Charm inventory allocation stays a
setup condition. These source-specific roles do not pool market prices across
skill trees, suffixes or life rolls.

### Index input stability

The SQLite builder rechecks every input's content fingerprint and file signature
before replacing the published database. A change during parsing or while another
source is indexed aborts publication, preserving the previous database and cleaning
the temporary file. This closes input-read races; it is not yet a transaction that
publishes definitions, rules and SQLite as one immutable artifact generation.

### Colossal Jewel routing

Native type `cjwl` now routes to the jewel family while retaining its distinct base
identity. Reviewed misc/type records establish no durability and zero sockets at
all levels; named Colossal Jewels receive the same explicit impossible-variant
facets as ordinary non-equipment. Cached comparisons still distinguish all six
unique identities, rolls and their base from ordinary Jewels.

Crafted Sunder Charm type`csch` also dispatches as a charm, retaining the unique
quality policy and distinct crafted base. Its verified non-equipment facets apply
to the six exact native named definitions; market-name aliases are not guessed.
The family coverage artifact uses schema2 to describe implemented comparison
strategies as partial and list concrete remaining gaps rather than obsolete
blanket claims that named/runeword/armor/charm comparisons are absent.

### Insight mercenary roles

Twelve documented Insight setups bring reviewed profiles to74. Recipe identity,
four filled sockets and Meditation are required; level17 Meditation and cited
ethereal bases are preferences. Mercenary type, equip requirements, life leech,
attack speed and companion equipment remain setup conditions. The saved Insight
Bill now has role assessments while its uncaptured ED and unmapped modifiers
continue to block numerical comparison. Base damage/price equivalence is not implied.

### Build-use report deduplication

Terminal/OSD formatting groups variants with identical displayed requirements,
preferences, alternatives, side and fit status. Conditions and improvement targets
shared by all remaining groups appear once. Variant-specific differences stay
scoped under their headings; the full semantic role records are unchanged.
Saved Insight's build-use section falls from73 to56 lines without dropping its
variant-specific equipment conditions.

### Compound poison facts

Single-source poison decoding supplies typed native component values alongside
its display text: min/max rates in damage per frame, duration in seconds and
source count. Capture normalization preserves these units and raw integers.
These are semantic facts, not inferred market fields: lacking an equivalent
listing duration still prevents a complete poison comparison.

### Tal Rasha player set conditions

Three Lightning Sorceress Magic Find profiles bring reviewed roles to77. Each
piece requires the other two cited Tal Rasha pieces in player equipment; mercenary
items cannot satisfy these dependencies. Guardianship retains its Ist socket
requirement, and the complete setup still needs the guide's117% FCR breakpoint.
These are source-backed use cases, independent of market tier and numeric price.

### Additional named asking cohorts

Metalgrid's non-perfect attack-rating/resistance cohort and Guardian's Light
receive conservative medium baselines from the dated scoped Mid–High research.
Native roll bounds and impossible socket/ethereal variants are checked. Metalgrid's
joint450AR/35allres bucket has no priced sellers and remains pending; Guardian's
Light has no inferred perfect-roll premium. There are83 reviewed identity policies,
with4 research-only identities and478 absent from the supplied WP-I research.
These counts do not claim full KB absence or complete numeric price coverage.

### Typed loadout context

`domain/context.py` provides the immutable AssessmentContext boundary for optional
player/mercenary class, level and equipment facts. Predicate evaluation and legacy
companion checks normalize through it. Missing or malformed facts remain unknown;
an explicit empty equipment collection proves absence. Collections are copied,
deduplicated and sorted, so caller mutation cannot change an ongoing assessment.
Invalid mixed lists cannot crash membership traces or masquerade as valid equipment.

### Leveling requirement checks

The shared equipment mechanics compare verified level/strength/dexterity requirements
with the intended player's or mercenary's context. Leveling desirability stays
independent; reports append only concrete numeric shortfalls. Unknown, upgraded or
otherwise unverified requirements are not treated as zero. A met numeric check is
not a class/slot compatibility claim. Context now includes separate strength and
dexterity facts for both wearers; callers supply attributes available for equipping.

### Finite comparison values

Base, affixed, named and runeword contracts share defense/property validation.
Non-finite numeric modifiers and invalid defense cannot form a contract. The
listing matcher repeats the finite check for older or externally supplied
contracts, so equal infinities cannot accidentally become comparable prices.

### Source occurrence audit

Run `uv run --offline python -m pricing.knowledge.assessment.maintenance.inventory`
to enumerate demand-artifact rows plus standalone WP-A variant occurrences, with
input fingerprints. Derived variant index.json is excluded to avoid duplicating its
reverse lookup. Player, mercenary, swaps, prebuff labels and source duplicates stay
separate. Related rule/source links are review leads, never coverage certification.
The current census contains62,891 occurrences (including49,780 discovery-only),
3,995 identity-review and9,116 rule-review entries. Its34 build labels include the
shared-planner collection;591 build/variant pairs include discovery profiles and
must not be represented as591 endorsed build variants.

### Magic/rare belt roles

Eight source-specific belt roles bring the reviewed profile count to85: Hammer,
Blizzard and Wake of Fire recovery/fire-resistance belts; FoH and Holy Bolt life/
cold-resistance belts; Fury and Poison life/fire-resistance belts; and the Budget
Gold Find rare belt with recovery, cold/lightning resistance and extra gold.
Each requires the full positive stat combination; cited planner values are explicit
preference targets. Setup suitability remains conditional, including requirements,
remaining defenses and potion capacity. No numeric price follows from these roles.

### Crafted belt roles

Eight crafted-belt profiles bring reviewed roles to93: Abyss, Echoing Strike, Fire,
Fissure, Lightning, Nova and Summoner caster belts, plus the Smite Blood belt.
Source stat categories are required and numeric planner values are improvement
targets. Cited75/105/117% full-loadout cast-rate breakpoints remain conditions.
Smite retains the separate Life Tap, Cannot Be Frozen, Crushing Blow and resistance
requirements; a belt's life-leech roll does not satisfy them. Current Fire crafted
and older rare planner alternatives remain distinct. These roles do not assign prices.

### Ordinary charm market quality

Exact Small/Large/Grand Charm catalogs now derive missing magic quality from their
native type constraints and distinct market identities. Named uniques, crafted
sunders and jewels are excluded. Explicit contradictory rarity is preserved and
blocks comparisons. The627 cached ordinary-charm observations were migrated without
changing dates or seller data, followed by watchlist/index rebuild. The real7% MF
Small Charm cohort now yields2 exact matches; missing dates and insufficient sellers
still prevent a current estimate. New dated sufficient cohorts can use the same path.

### Small Charm combinations

Twenty-five explicit source combinations bring reviewed profiles to118 across
Lightning, Nova, Blizzard, Hammer and Poison variants. Seven combination shapes
cover Magic Find/resistances, recovery/resistances, life/resistances, mana/Magic
Find, lightning/Magic Find, fire/Magic Find and life/cold resistance. All-resistance
predicates require all four native resistance fields. Numeric source rolls are
targets; inventory allocation and remaining loadout needs stay conditional.
Only magic Small Charms qualify, independently of trade-price availability.

### Reviewed rule layout

Build roles live in `rules/roles/<build>.json`. `rules/reviewed_profiles.json` is the
manifest: list each file in `profile_files`, list every role ID exactly once in
`profile_order`, and update `coverage.reviewed_profiles` when adding/removing roles.
The compiler assembles all files before validating IDs, schema, native stats and
source hashes/locators. Runtime still receives the same single immutable bundle;
the initial split preserves all118 records and their order exactly. A missing file,
duplicate ID, incomplete order or path outside the rules directory blocks publication.

Profile publication uses unique temporary files in the destination directory,
flushes the complete serialized bundle before atomic replacement, and cleans up
on failure. Concurrent publishers cannot collide on one temporary path. This
protects the profile artifact; coordinated publication of all KB artifacts and
the index remains a separate unfinished architecture step.

### IAS/resistance jewel recipients

Seven socket-filler roles bring reviewed profiles to125: mercenary Andariel's
Visage fire-resistance/IAS jewels in Lightning, Blizzard and Hammer variants, plus
the Hammer Ubers player Guillaume's Face lightning-resistance/IAS jewel. Native
of Fervor data verifies a magic-only fixed15% IAS suffix. A resistance bonus is
required and30% is the cited target. Player and mercenary recipient equipment
are separate dependencies; available sockets, total attack speed and resistance
needs remain conditional. Recipient helmet use does not turn the jewel into a
helmet price comparison or imply a universal jewel price.

### Market repository boundary

`market_repository.market_rows` owns SQLite candidate retrieval. `comparables`
accepts supplied evidence and contains matching/publication policy without importing
the index. Shared identity typography normalization lives in `pricing.knowledge.names`
(and remains available through the index for existing callers). Retrieval returns
all exact-identity market rows, including incompatible scope, so policy rejection
diagnostics retain the evidence. Similar named bundles and demand rows are excluded.

### Publication uses the fresh comparable cohort

The3-seller,30-day and5x dispersion gates apply to the same dated eligible cohort.
Stale, future-dated and undated structurally matching observations remain in full
comparison diagnostics, with exclusion counts in the price result. They cannot
supply sellers, alter the median/range, or suppress an otherwise sufficient fresh
cohort. If the fresh cohort is insufficient, no price is published. This changes
mixed-age publication behavior without relaxing the scope, identity or date gates.

### Definition-level coverage

Named-tier coverage schema2 retains every definition variant behind each identity,
including table ID, base and spawn flag disposition. The573 definition records map
to565 names:538 explicit enabled flags,2 disabled flags and33 unverified flags.
Azurewrath retains its disabled legacy and enabled current records separately.
Spawnability describes drop-generation evidence, not trade value; absent flags do
not exclude RotW items, and disabled definitions are not assigned trash or removed
from the research inventory. Identity-tier and variant completeness remain distinct.

### Named variant selection

Named comparison contracts resolve definitions by captured unique/set table ID and
base. Without a table ID, only one matching base definition is accepted. Azurewrath's
Crystal Sword and Phase Blade versions remain distinct; Rainbow Facet requires its
captured table identity instead of silently using the final poison/level-up row.
Wrong table, name, base or ambiguous identity blocks comparison. This resolves
identity selection; complete trigger/property market evidence is still required.

### Facet event projections

The seven cataloged Rainbow Facet death/level-up chance fields are projected only
when the native event, packed skill/level and100% chance agree with the selected
definition. Trigger projection removes only its own verified mapping gap. Cached
sellers sometimes put the spell level in a chance-labeled field; those values are
not silently converted to100%. The Venom level-up field remains unverified, as do
any unrelated component gaps. Correct variant selection alone does not
establish a complete numeric price contract.

### Elemental scalar market projection

Capture normalization now supplies verified market fields for fire/lightning/cold
minimum and maximum damage, four elemental skill-damage bonuses, and four enemy
resistance reductions. These preserve scalar units and native parameter identity.
Generic cold duration and compound poison rate/duration fields remain separate
unsupported facets; no damage-range endpoint is collapsed into an ambiguous total field.

Fire/lightning Facet contracts now verify both fixed damage endpoints against the
selected native definition before treating them as optional listing fields. A
seller's explicit contradictory endpoint remains a rejection. Variable mastery/
piercing rolls and the event property stay mandatory, distinguishing all four
fire/lightning death/level-up variants. Controlled three-seller tests exercise the
complete capture-to-price path; these fixtures do not claim new observed prices.

Cold Facet contracts also verify fixed damage endpoints and duration. The local
`dmg-cold` parameter is measured in frames: these definitions specify 3 frames
(0.12 seconds). Both the captured raw duration and decoded seconds must agree
before its projection gap is consumed. Missing or changed duration blocks the
contract. Cold death and level-up variants have end-to-end comparison tests;
poison Facet rate/duration handling is described below.

Poison Facet comparison validates the two native damage rates, frame duration and
single-source count, including raw values and decoded units, against the selected
definition. Only then is its rounded 37 damage total projected to market field
589 as a fixed intrinsic. Listings may omit that fixed damage, but explicit
contradictions reject the comparison. Variable poison mastery/piercing and the
death event remain required. The death variant has a complete synthetic
capture-to-price regression; the Venom level-up variant still lacks a verified
market event field and cannot produce a comparison contract.

### Named tier identity and Naj's Puzzler

Trade tiers now use the same captured-table/base definition resolver as named
comparison contracts. Conflicting captured IDs cannot produce a valuable tier
merely because the display name matches a reviewed policy.

Naj's Puzzler has a reviewed low qualitative trade tier for non-ethereal items
with empty sockets. The cached source records teleport-charge swap use across
13 builds and two low asks; scarcity is not interpreted as lack of demand. Two
sellers do not meet the numeric price threshold. Named policy coverage is now
84 of 565 identities; remaining identities stay pending review.

### Ormus skill-dependent trade tier

Ormus' Robes has a medium qualitative trade tier for the reviewed +3 Nova,
Lightning, Enchant, Meteor and Blizzard variants on the original non-ethereal
base with empty sockets. Native skill validation requires a complete capture
with exactly one valid selected skill; tier assessment does not require a market
field mapping. Numeric comparison still requires that mapping.

All three elemental rolls must lie in the local definition's 10-15 range. Cached
research prose mentions 10-20, so incompatible captures remain pending until that
source discrepancy is resolved. Other skills and perfect-roll premiums are not
assigned a tier by this policy. Coverage is 85 named identity policies, not full
variant coverage or 85 numeric prices.

### Listing region metadata

Catalog field 933 (Region) is excluded from item-modifier comparison. Region is
not part of this repository's configured SC/NL/PC/RotW scope. Listings still
require all configured scope fields, exact item modifiers, dated observations
and sufficient independent sellers. The cached artifact contains 19 verified
scope rows carrying Region; removing this false extra-affix rejection does not
by itself establish a usable price for those rows.

### Verified base-tier listing fields

Comparison contracts carry the base's Normal/Exceptional/Elite tier, derived
from the offline native upgrade-chain catalog. Listing field930 (Base Tier) is
consumed as metadata only when it agrees with that verified tier. Conflicting,
malformed or unverified declarations remain rejected. An omitted tier is allowed
because exact base identity is still checked; tier is not an item rarity and
does not permit cross-base comparisons. This applies to base, affixed, named
and completed-runeword contracts. Unknown or ambiguous catalog tiers stay unset.

### Compound rune poison

Runeword definitions retain supported compound rune effects separately from
scalar ranges, including native minimum/maximum poison rates, duration in frames
and individual source count. Repeated rune effects remain separate sources.

For a single fixed poison source, runeword comparison verifies every captured
raw value and decoded unit against the compiled effect before projecting its
rounded total to market field589. Verified fixed damage may be omitted from a
listing; conflicting declared values still reject it. Facet and rune validation
share the same native poison mechanics. Mixed sources remain unsupported.

The saved Insight capture now verifies Tal's 75 poison damage over 5 seconds.
Its missing enhanced-damage capture and internal throw-damage mapping remain
pricing blockers; no numeric estimate is created by this change.

Fixed rune fire and lightning damage are compiled as paired endpoints. Their
individual rune sources are summed by element, then both native raw/decoded
endpoints and market projections must agree before becoming optional listing
fields. Missing, changed or unprojected endpoints do not receive that treatment.
The saved Insight verifies Ral's 5-30 fire damage; unknown additional effects
are not inferred from rune names. Single-source cold rune duration is verified
as described below.

Cold rune definitions retain duration in frames alongside both damage endpoints.
Runeword contracts consume the cold-duration mapping gap only after one compiled
cold source matches both endpoints and the captured raw frames/decoded seconds.
Thul's weapon effect is 3-14 damage over 75 frames (3 seconds). Contradictory
units/duration remain unresolved; multiple cold sources are not inferred.

### Naj teleport-swap demand

Fourteen source-backed roles cover Naj's Puzzler as a player weapon-swap
alternative across thirteen builds, plus the separate Fal-socketed Poison Nova
budget planner configuration. Main gear-table alternatives are not presented as every
variant's prescribed loadout. Profiles preserve their exact source locators and
check the player's class, item identity, base and non-ethereal state.

Fit remains conditional on level/equipment requirements, usable Teleport charges
and whether the current loadout already supplies Teleport. The planner-only Fal
configuration retains its socket requirement and provenance. This extends build
demand coverage, not numeric pricing or inferred early-ladder price tiers. The
reviewed profile bundle now contains 139 roles.

### Role equipment checks

Reviewed roles may declare numeric equipment requirements with an applicability
predicate. The compiler validates the three nonnegative integer requirements and
the predicate. Runtime uses the shared player/mercenary requirement evaluator,
retaining its checks and shortfalls in each role's `equipment` result. Unmet
requirements keep the role conditional and report the concrete shortfall; they
do not alter the item's trade tier.

The thirteen unsocketed Naj alternatives check level78, strength44 and dexterity37
from the named/base definitions. Socketed, ethereal or different-base variants
cannot inherit those numbers. The Fal planner role retains its separate socket
and requirement conditions until its exact variant requirements are verified.
Meeting the numeric requirements does not establish usable charges or a need for
Teleport in the current loadout.

### Captured charge availability

Charged-skill decoding now exposes remaining charges as a typed value and retains
remaining/maximum counts in normalized facts. Skill and level remain part of
the native parameter identity. All fourteen Naj roles check the level11 Teleport
charge row: zero requires recharge, positive counts satisfy charge availability,
and missing data remains unknown. The report can retain the observed charge text
as an important stat instead of repeating a permanently unresolved condition.

Charge counts are not projected to scalar market fields: market skill level,
maximum charges and remaining charges are different comparison facets. Dire
Song's saved Nova charges therefore remain a pricing mapping gap.

### Affixed Teleport alternatives

Four reviewed magic/rare staff and amulet roles preserve explicit Berserk and
Poison Nova guide recommendations. The predicate `charge_skill` selects a
captured charged spell independently of its encoded level or generated item
name. A threshold of zero tests presence, while one tests usable charges.
Complete absence fails; incomplete or malformed evidence remains unknown. Nova
charges cannot satisfy Teleport. Profiles validate charged skill IDs against
the native catalog.

Empty Teleport charges retain the utility candidate with a recharge condition;
equipment requirements and the before-Enigma/Bramble context remain explicit.
This adds build demand without a numeric price inference. Reviewed roles:143.

### Starter charged utility

Six additional source-specific Starter roles cover Lower Resist wands for
Blizzard, Fire Warlock and Lightning Fury, Life Tap wands for Smite, and Teleport
staves for Fire Warlock and Lightning Fury. Fire Warlock's inventory wand stays
distinct from its Teleport swap. Blizzard preserves the guide's condition that
the mercenary lacks Infinity.

Native affix tables permit rare versions of the same charge-bearing item types;
those are equivalent utility candidates, not separately sourced market demand
or guaranteed resale value. Empty charges require recharge; another spell fails
the role. Reviewed role count:149.

### Appraisal index snapshots

`retrieve_draft` opens one read-only SQLite transaction before assessment and
uses the same connection for identity, prepared-item, skill and market queries.
Nested repositories borrow it without committing or closing it. Atomic index
replacement therefore cannot mix old identity evidence with new market prices
inside one appraisal; later appraisals see the replacement. The outer context
closes the connection on success and failure.

A regression publishes a replacement between identity and market queries and
proves the original appraisal keeps its original prices. This pins SQLite only;
standalone definition/rule generations still need coordinated validation.

Definition catalogs are now pinned with an assessment-local context alongside
the SQLite snapshot. Nested named/runeword consumers reuse the same immutable
catalog even if a newer artifact is published. Context is restored on success
and failure, so later appraisals can load the new generation. The assessment JSON
records `definition_generation`.

When the index manifest includes the configured definition artifact, its hash
must equal the pinned catalog generation. A mismatch raises an actionable
offline-rebuild error before retrieval can publish a price. Observation-only
partial indexes contain no indexed definition copy to reconcile. This does not
yet coordinate publication of the whole KB. Additional pinned inputs are listed
below.

The base-tier catalog now uses immutable artifact bytes pinned for each
assessment. `artifact_snapshot` preserves nested snapshots, checks file stability
while reading, and restores context after failures. Base-tier lookups use the
pinned bytes; appraisal JSON records their hashes in `artifact_generations`.
The index manifest must agree whenever it includes that catalog. A changed
catalog with an old index is rejected until rebuild. Other standalone policy
files have not yet been migrated to this artifact snapshot mechanism.

`assessment.inputs.artifact_inputs()` now centralizes the participating artifact
paths and diagnostic labels for engine and pipeline. Leveling recommendations
and item facts join the base catalog in the snapshot; the leveling policy reads
the pinned bytes. Both leveling artifacts are independently reconciled with
the pinned index manifest, and both fingerprints appear in assessment JSON.
A paired refresh cannot remove or change a recommendation midway through an
appraisal. Other rule/profile inputs remain outside this mechanism for now.

Runeword-base utility recipes also participate in this snapshot and index-hash
check. Their parsed catalog is immutable and cached by content, replacing the
old process-lifetime cache. Existing assessments keep their recipes across file
replacement or deletion; the next assessment loads the newly published recipes.
This prevents socket preparation and preferred-base advice from silently using
an older utility KB after a refresh.

### Additional curse-charge utility roles

Eight reviewed wand roles cover Fissure Druid (Starter inventory/Cube utility and
Ubers swap), Lightning Sorceress (Starter and Ubers), Lightning Strike Amazon
(Starter and Ubers), Dragon Talon Assassin (Budget), and Dream Paladin (Ubers).
They accept magic/rare wands with the captured Lower Resist or Life Tap skill.
Empty charges preserve a recharge candidate; another spell does not satisfy it.

Dream's Life Tap wand depends on lacking both Last Wish and Dracul's Grasp.
Lightning Sorceress Ubers retains the Infinity mercenary dependency and the
explicit Uber Mephisto exception. Lightning Strike's Ubers wand is an optional
manual alternative to relying on Plague procs. These source-specific roles do
not imply that any charge level breaks every immunity, or establish trade prices.
The reviewed bundle now contains 157 profiles; complete build/variant coverage
remains unfinished.

### Variant-specific Teleport staves

Thirteen additional staff roles cover twelve builds: Abyss/Echoing/Mirrored Blades
Warlock, Dragon Talon/Fire Blast/Lightning Sentry Assassin, Fissure Druid, FoH
Paladin (separate FoH and Holy Bolt starters), Lightning Strike Amazon, Poison
Nova/Summoner Necromancer, and Standard Smite Paladin. Dragon Talon's Budget
staff remains inventory utility alongside its Life Tap swap. Smite's travel
staff is conditional on not already wearing Enigma. Lightning Strike preserves
the farm-dependent choice among staff, curse wand and Harmony.

The roles assess Teleport utility on magic/rare staves, independently of incidental
planner resistance rolls, base choices and maximum charge counts. Equipment
requirements remain a separate check, and jewelry cannot satisfy a staff role.
Wrong spells and wrong wearers fail; empty charges retain a recharge candidate.
The reviewed bundle now has 170 profiles. These additions do not supply new market
observations or imply complete rare/magic price coverage.

### Skill-affix circlets and amulets

Ten roles bring the reviewed bundle to 180 profiles. Lightning Sentry and Wake of
Fire each gain Cunning circlet of the Magus (+3 Traps / 20 FCR), amulet of the
Apprentice (+3 Traps / 10 FCR), and amulet of the Whale (+3 Traps / 81–100 life).
The Whale role marks 100 life as a preference. Berserk and Double Throw gain
Berserker's/Magus circlet candidates (+2 Barbarian / 20 FCR), accepting magic or
rare items because both native affixes permit rares. Poison Nova gains distinct
Starter and planner-only Budget Venomous amulet roles (+3 Poison and Bone).

Cunning and Venomous are magic-only; skill-tab identities use native layers,
not displayed item names. Table alternatives remain labeled Main alternatives,
and the Budget source retains its planner-only qualifier. Circlet sockets are a
separate setup condition. These useful combinations do not establish a numeric
price or imply that every secondary roll suits every loadout.

### Empty Jeweler's Monarch of Deflecting preparation

Twelve source-specific profiles bring the bundle to 192: seven builds' main
shield alternatives, two separate swap alternatives, Blizzard Standard's swap,
Fissure Magic Find, and Lightning Fury Ubers. They require a non-ethereal magic
Monarch, four empty sockets, 20 increased blocking and 30 faster block rate.
Unknown socket contents remain unverified. Filled shields are excluded from this
empty-base branch because captured block totals can include socket contributions.

Reports retain the required facet payload, or four Ist runes for Fissure Magic
Find, as preparation work. Lightning Fury Ubers retains Stormshield as the cited
alternative. Matching this base never establishes a finished setup, perfect
facet rolls, or a numeric price. Finished socketed magic shields still need a
contribution-aware role and comparison policy.

### Other empty magic socket bases

Ten additional roles bring the reviewed bundle to 202. Berserk gains a three-socket
Luck Tiara; Double Throw gains Speed, Nirvana and Luck Diadem alternatives;
Strafe gains Nirvana/Speed Diadem and Stability/Precision Dusk Shroud alternatives;
Lightning Strike gains separate Crown setups for Perfect Topazes or Ral/Ort/Thul.
The profiles use the exact cited base, non-ethereal magic quality and existing
empty sockets, with native suffix minima. Variable suffix maxima are preferences.

Diadem and Tiara capacity is three even for a Jeweler's item; Dusk Shroud uses
four. Current torso Stability is 24 FHR. Nirvana spans 21–30 Dexterity, Luck 26–35
magic find, and torso Precision 10–15 Dexterity. These candidate checks do not
promise that socketing an unsocketed magic item will yield the needed count.
Inserted jewels/runes, equipment requirements and complete setup targets remain
separate work; filled items do not enter this empty-base branch.

### Fixed elemental effects on named items

The definition compiler now preserves compound dmg-fire/dmg-ltng/dmg-cold
properties as fixed endpoints (and cold duration in native frames), after
checking their PropertyFunc15/16/17 mappings. Separate cold-min/max/len properties
remain variable ranges; the Eye of Etlich's duration is not treated as fixed.
The portable bundle contains these effects for 89 definition records.

Named comparison contracts require captured raw/decoded endpoints to match the
compiled effects before allowing market listings to omit those fixed stats.
Cold additionally requires the matching frame count and decoded seconds. Raven
Frost's 15–45 cold damage / 100-frame duration can therefore be verified without
a separate cold-duration market field; Dexterity and Attack Rating remain exact
required listing rolls. Missing/changed components fail the contract. Facets
retain their existing variant-specific event and elemental checks. This adds
comparison support, not market evidence or an unconditional price estimate.

### Fixed poison ranges on named items

The compiler preserves one fixed poison source from either dmg-pois or a complete
fixed pois-min/pois-max/pois-len group, after checking native property functions.
Variable components, duplicate/mixed sources and incomplete groups are excluded.
There are 26 definition records with a compiled fixed poison source.

Comparison verifies raw rates, decoded damage-per-frame units, frame duration,
seconds and a source count of one. Hellplague's fixed 48/96 rates over 150 frames
therefore clear the unmapped component gaps while retaining the 28–56 damage
range. No single market poison value is invented for unequal endpoints; a scalar
projection conflicts with that range. Equal-rate effects can use the established
scalar poison-total field. Socket contributions and variable/multiple-source
poison remain outside this policy, and facets retain their dedicated event checks.

### Named chance-to-cast properties

Proc decoding now retains a numeric chance with unit `percent_chance`, alongside
its existing text and packed native event/skill/level identity. The definition
compiler preserves fixed triggers whose native PropertyFunc11, skill ID, level
and positive chance are verified (89 definition records). Named contracts reject
missing or changed compiled triggers even when a capture claims completeness.

Atma's Scarab's 5% level-2 Amplify Damage on striking is verified against the saved
capture and mapped to market field543. Listings may omit this verified fixed
property; an explicit value2 (spell level instead of chance) or the when-struck
field812 fails comparison. Other trigger projections remain unsupported until
reviewed; no generic mapping by skill name is used. Facets retain their existing
event-specific comparison rules. Synthetic three-seller tests exercise the price
path; they do not add or establish a real market price.

The fixed-proc market map now covers 55 exact event/skill combinations from the
offline property catalog. Regression checks require unchanged chance/level label
structure and unambiguous native skill names. Dedicated cases cover Reaper's
Toll, Dracul's Grasp, Stormlash, Wisp Projector and Lacerator. On-attack,
on-striking, when-struck, kill, death and level-up events remain distinct.
Miasma Chain, Sigil: Lethargy, Burst of Speed and Sigil: Death labels do not have
exact matching native skill names in this catalog; malformed Mind Blast and
Delirium labels also remain unmapped. This map applies only after named fixed
skill/level/chance verification, not to arbitrary magic/rare procs or charges.

### Fixed procs on completed runewords

Runeword definitions now compile fixed triggers from the recipe's T1Code/Param/
Min/Max fields, preserving chance and skill level as separate quantities. Forty-
three runeword definitions have compiled procs; nineteen have reviewed market
fields for every compiled proc. Other fields remain explicit comparison gaps.

The runeword handler requires each compiled proc to match the captured native
identity, raw chance and typed decoded chance. Verified mapped procs become fixed
properties that listings may omit. Conflicting explicit market values fail.
Treachery regressions verify on-striking level-15 Venom at25% and when-struck
level-15 Fade at5%, including missing/changed evidence and a synthetic price
cohort. Base, ethereal state, sockets, defense and variable recipe rolls retain
their existing checks. Proc coverage is not complete item pricing coverage.

### Recipe plus rune elemental totals

Nine runeword definitions now carry elemental recipe effects compiled from their
T1 fields. Fixed elemental verification combines them with the destination's rune
effects before checking captured endpoints. Faith's120 fire damage and
Lawbringer's150–210 fire damage can be treated as fixed when verified. Holy Thunder
requires21–110 lightning damage (recipe20–60 plus Ort1–50), rather than incorrectly
accepting Ort alone; Ral's5–30 fire remains a separate verified pair.

Two recipe cold effects omit duration. Their source remains in the compiled
list with unknown duration, preventing rune-only cold totals from being accepted.
No cold duration is guessed, and multiple cold sources remain unverified. Missing
or changed endpoints do not become fixed properties that listings may omit.

Proc skill-name resolution accepts unambiguous case-only variants in native
records. Obedience uses lowercase `enchant`; it now compiles and requires its
30% level-21 Enchant-on-kill proc, mapped to field874. Conflicting IDs under the
same case-insensitive name remain unresolved. Runeword proc coverage is now44
recipes, with all compiled proc fields mapped for20.

Cold-duration investigation: local D2MOO ItemMods.cpp PropertyFunc17 does not
supply a universal duration when the parameter is zero/absent. Its fallback
rolls between the property's minimum and maximum. This is legacy implementation
evidence, not a captured modern duration for Lawbringer or Voice of Reason;
those recipe durations remain unresolved rather than receiving a fixed default.

### Fixed per-level coefficients

Thirty-six named definition records now preserve fixed per-level coefficients
from PropertyFunc17 with native level-based operation metadata. The compiler
retains ValShift as well as the operation divisor: Guardian Angel is5/2 attack
rating against demons per level, while Shako's life/mana native coefficient is
3072/2048. Random coefficient ranges are not promoted to fixed values.

The capture adapter retains viewer level. Comparison verifies raw coefficient,
formula, viewer level and displayed total together before consuming the unmapped
native-stat gap. It does not project a character's displayed total as an item
roll; viewer-dependent market projections are rejected. Missing/changed evidence
blocks comparison. Saved Guardian Angel and Shako tests cover this path, including
Shako at levels62/91/99. Guardian Angel's saved socket uncertainty still blocks its
contract independently of the now-verified per-level stat.

### Runeword per-level bonuses and variable coefficients

The coefficient compiler also reads recipe T1 fields. It distinguishes a fixed
parameter, a fixed min=max fallback (Leaf's defense), and a variable fallback
range (Fortitude's life). Eleven runeword definitions have supported fixed effects;
Fortitude has a variable effect. Fixed named coverage rises to51 records through
fixed fallback handling and the reviewed native operation4 for flat defense and
maximum damage per level. Operation4 reads the wielder's level; Leaf's native
coefficient16/8 produces182 defense at level91. Other operation4 stats are not
implicitly accepted.

Enigma's strength and magic-find coefficients are checked against the captured
formula and viewer level before clearing their unmapped-stat gaps. Missing fixed
coefficients block comparison. Fortitude's raw life coefficient must lie from2048
to3072 in steps of256 with divisor2048; its displayed total is not the roll.
Absent, invalid or unverified coefficients cannot silently pass comparison.
The same variable-coefficient guard applies to named definitions.

Fortitude's coefficient now projects to market field438, independently of viewer
level. The cached 2026-09-24 Fortitude pages under
`pricing/raw/traderie/runeword-refresh/` identify this as a decimal-enabled life
per character level field. Observed values include1,1.125,1.25,1.375,1.5; native
recipe steps verify these five possibilities. Other observations include rounded
values and character totals; exact comparison rejects them, missing fields and
different coefficients. The variable coefficient is never intrinsic/optional.
Conflicting pre-existing projections block comparison. Other variable effects
retain a review gap.

### Fixed native procs without market fields

The definition's fixed event/skill/level/chance can establish a native invariant
even when sellers have no corresponding market field. The proc must be captured,
decoded and match both raw and typed chance exactly. Only that verified key's
projection gap is consumed; no synthetic market field is created. An existing
unreviewed market projection blocks comparison, and unknown extra listing fields
remain subject to exact rejection. Mapped procs retain their explicit fixed
market values. Rainbow Facets retain their separate variant-specific policy.

This removes Fortitude's Chilling Armor projection gap. An integration test with
decoded native life coefficient, Chilling Armor, defense and explicitly projected
resistances accepts an exact synthetic three-seller cohort; missing proc or life
evidence still blocks. This is comparison-policy coverage, not a newly observed
market price or proof of complete capture of every possible Fortitude variant.

### Variable runeword roll bounds

A decoded finite value alone is insufficient for comparison. The runeword handler
now delegates variable-roll checks to `mechanics/runeword_rolls.py`. Reviewed
native integer modifiers (including mana, leech, cast/attack/hit-recovery speed,
oskills, auras, absorption, crushing blow and elemental skill modifiers) must lie
inside their recipe range plus the appropriate family's rune contribution.
Spirit cannot compare with36 cast rate or fractional30.5; Call to Arms cannot
compare with5 Battle Command; Last Wish crushing blow is60–70 including Ber20.
Missing/nonfinite variable values retain the existing capture gap.

The explicit supported-stat set excludes defense, enhanced damage/defense,
staffmods, resistances and attack rating: their observed totals can contain
additional base contributions. Those fields still require capture and exact
listing comparison but do not yet receive this bounds validation. This is not
complete recipe/base decomposition or proof of captured modifier completeness.

### Generic affixed leveling utility

`policies/generic_leveling.py` adds three reviewed conditional patterns from the
cached MrLlamaSC 2025-04-24 transcript and fingerprinted leveling-candidate artifact:
early movement boots (04:23), cast-rate rings when a breakpoint is needed
(24:19–24:32), and resistance charms covering a current shortfall (33:07).
Identified, non-ethereal magic/rare items must have a decoded finite positive
native modifier in the matching slot. Named-item recommendations remain separate.
These receive ordinary/medium leveling utility, not a trade tier or price. No
item equip level or present upgrade is inferred from an affix alone. The shared
report carries the conditions; it does not recommend permanent retention.

The source participates in assessment artifact snapshots; a changed fingerprint
requires review. Other transcript patterns, current-class leveling guides and
all named trade tiers remain incomplete. The two WP-I research-only named records
still have thin evidence; absence from a build is not used to assign trash.

The generic leveling policy now covers seven of the thirteen extracted source
patterns. Additional reviewed cases are early magic-find rings/gloves/boots
(07:59), attack-speed gloves with a useful secondary attribute/life/attack-rating/
resistance stat (10:36), crafted cast-rate belts when needed for a breakpoint
(14:16), life/mana/resistance rings (24:19), and defensive life/fire/lightning/
hit-recovery belts (32:33). IAS alone does not satisfy the compound glove rule.
The caster-belt rule admits crafted quality only; this does not automatically
extend all generic recommendations to crafts. Ring caster and defensive use share
one source row; the caster condition takes priority to avoid repeated advice.

Each pattern declares item types, allowed qualities, required groups of positive
native stats, archetype and condition in a small immutable definition. Matching
requires every group, with alternatives inside a group. Socket preparation,
crushing-blow weapon/mercenary use and named socket customization still need
separate reviewed mechanics/context handling and are not claimed as covered.

### Runeword resistance totals

Variable resistance checks now use compiled `base_resistance_options`, drawn from
native base `auto prefix` groups and spawnable automagic rows. No automatic group
means zero base resistance; supported all-resistance groups retain their discrete
values plus zero only when a non-resistance alternative exists. Missing groups,
individual-element automods or unsupported combinations remain unverified.
The compiler records its automagic source fingerprint with other definition inputs.

For variable recipe resistance stats, subtract the family's fixed rune bonuses,
then require one possible shared base bonus to explain every observed value.
Recipe `res-all` components must agree after subtraction. Sanctuary permits up
to70 on a Monarch or115 on a suitable Paladin shield, but not71/116 respectively.
Cure/Ground/Hearth/Temper permit40–60 total on their variable elemental resistance,
including the socketed rune's30. Impossible fractional values also fail.

These are possible-total constraints, not reconstruction of the original base
roll or its item-level eligibility. The resistance/damage automod branch is not
yet jointly constrained with enhanced-damage/attack-rating evidence. Fixed-only
resistance recipes and other base-dependent modifier types need further work.

Resistance validation also covers captured fixed recipe bonuses, rune-only
bonuses, and observed base-only resistance. Spirit's rune contributions35 to
cold/lightning/poison combine with one possible base bonus;45/80/80/80 on a suitable
Paladin shield is consistent,44/80/80/80 is not. A Monarch cannot have80 poison
resistance from Spirit. Rhyme's fixed25 is checked the same way. Invalid or
undecoded observed resistance values block this check. Absent fields remain
absent: this bounds validation does not infer zero or prove capture completeness.

### Named-tier snapshot consistency

Named tier rules and their current WP-I evidence are registered appraisal artifact
inputs. Tier evaluation and source-fingerprint validation both use pinned bytes;
source parsing is cached by content rather than a separate live file stat/read.
An in-flight assessment keeps its original rules/evidence across replacement or
deletion. The next assessment observes the new publication. All policy source
paths are checked against the explicit input registry by a coverage test; adding
a source requires registering it. Artifact generation hashes include these inputs.
This extends snapshot consistency, not the number of reviewed tier policies or
market observations. Full coordinated publication and other unmigrated readers
remain separate work.

The native-to-market projection catalog now uses the same artifact snapshot. A
mapping removed or changed during appraisal cannot change subsequent projection
reads in that appraisal; the next appraisal sees the new catalog and reports
removed native mappings as unresolved. Content-keyed parsing remains in use and
the projection catalog generation is recorded with assessment inputs. Static
reviewed code mappings are unchanged. ProfileRepository and decoder metadata
still have separate lifecycles requiring further architecture work.

### Build-profile assessment snapshots

ProfileRepository now pins its immutable BundleLoad in a context-local snapshot.
Nested snapshots reuse the same generation and update diagnostics. Assessments
enter the profile snapshot before normalizing capture facts, so publication during
capture/role evaluation cannot switch the selected bundle. The next assessment
reloads changed bytes. Reads use the shared stable artifact reader, while invalid
or missing publications preserve the repository's last-valid fallback and issues.
A missing first publication still yields no profiles plus a coverage diagnostic.

Reports include `profile_generation` for disk-backed profiles; explicitly injected
profiles have no disk generation. The profile bundle is deliberately not a
mandatory file in the generic artifact registry because that would bypass its
last-valid fallback. Coordinating its publication with all KB/index generations
remains separate from this per-assessment consistency guarantee.

### Thin exact-comparable asks in the report

One or two fresh, scoped, exact comparable sellers now produce `comparable_asks`
without an `estimate_ist`. Each seller contributes its cheapest eligible ask,
retaining listing ID, observation date, source and conversion provenance. The
shared terminal/OSD price section shows those individual dated Ist asks under a
SC/NL/PC/RotW “not an estimate” heading. It does not average them into a price.
Unclassified, mismatched, undated, stale and future observations cannot enter
this display. The three-seller estimate threshold and dispersion checks remain.
This implements the design's thin-evidence reporting branch; it does not turn
same-base references or unsupported item contracts into comparables.

### Lightning Fury Starter magic javelin

Reviewed profiles now total203. The Lightning Fury Starter source explicitly names
Lancer's Matriarchal Javelin of Quickness. The new Amazon weapon candidate requires
that verified base, magic quality, non-ethereal,40 IAS and4–6 native Javelin/Spear
skills (188:2); +6 is preferred. Native magicprefix supplies+3 while the base's
spawnable auto-prefix302 supplies+1..3; Quickness supplies40 IAS. A total matching
the combination is a candidate, not proof of which underlying prefix rolled.
Full setup conditions preserve the source's52 total IAS target and equipment/
quantity checks, so an item match alone does not claim a completed setup or price.
Source: wp-a-variants/lightning-fury-amazon-guide.json /variants/0/player/Weapon;
local magicprefix/magicsuffix/automagic/weapons tables verify the native semantics.

### Mirrored Blades Starter Grimoire

Reviewed profiles now total205. The first Grimoire family roles cover the cited
Mirrored Blades Starter Rhyme Grimoire and its empty two-socket preparation base.
Both require normal/superior non-ethereal Grimoire, Warlock context, and at least+1
native107:392 Mirrored Blades,107:389 Hex Purge and107:377 Summon Defiler. The
completed role also requires Rhyme identity and filled sockets; preparation
requires empty sockets and explicitly says to insert Shael then Eth. Hex Purge
Explosion404 is not interchangeable with389. Equipment/full-setup suitability
remains conditional and no numeric price is inferred from this build role.
Source: wp-a-variants/mirrored-blades-warlock-guide.json /variants/0/player/Off-Hand,
June6,2026; local metadata/recipe definitions verify skills, base and legality.

### Double Throw Starter crafted axes

Reviewed profiles now total207. Separate Weapon and Off-Hand roles cover the
cached Starter planner's Blood Crafted Balanced Axe. Require crafted quality,
non-ethereal verified Balanced Axe, Barbarian context, and positive native class
skills83:4, IAS93, both ED17/18, life leech60 and flat life7. Planner10IAS/80ED/
4leech/20life values are improvement targets, not universal price thresholds.
Observed cold damage fails this Find Item-oriented role, reflecting the cached
guide's explicit corpse-shattering warning. Total damage, requirements, attack
speed and quantity sustain remain conditional full-setup checks. Main-table rare
throwing weapons and their ethereal/premium conditions are not claimed covered.
Source: wp-a-variants/double-throw-barbarian-guide.json /variants/0/player/Weapon
and /variants/0/player/Off-Hand; May22,2026. No market value is inferred.

### Double Throw Cruel magic alternatives

Reviewed profiles now total209. Both-hand Starter alternatives recognize the
main table's Cruel Elite Throwing Weapon and Starter prose's Malah-shopping
option. Enumerated unrestricted elite bases from native weapons `ultracode`:
Winged Axe, Winged Knife, Ghost Glaive, Hyperion Javelin, Stygian Pilum, Balrog
Spear, Flying Axe, Flying Knife and Winged Harpoon. Require magic/nonethereal,
Barbarian context and201–300 on both native ED components. Cold damage fails
this Find Item role.300 ED and IAS are preferences; actual damage, breakpoints,
requirements and quantity sustain remain conditional. This does not generalize
the source's magic-shop option to rare or ethereal premium weapons.
Sources: wp-a-builds.json Double Throw Weapon22/Off-Hand21, cached Starter prose,
and local native magicprefix/weapons tables. No numerical price inferred.

### Double Throw rare planner targets

Reviewed profiles now total 211. Two hand-specific main-alternative roles cover
ethereal rare Ghost Glaive, Winged Axe and Flying Axe matching cached planner
items 77/76/79: 450 ED on both native components, 40 IAS, 250 AR, +2 Barbarian
Combat Skills, 5% level 1 Amplify Damage on striking and quantity replenish
rate 10. These are explicit premium planner targets, not minimum viable rolls;
lesser rolls are not classified as worthless. Full setup, requirements, damage,
attack speed and quantity sustain still need comparison. No market value inferred.

Source: pricing/raw/mr/planners/db0106mf.json, fingerprinted /data JSON string,
with item IDs retained in source metadata. Planner date 2023-02-16 is deliberately
kept distinct from the linking guide's May 22, 2026 date. Flying Knife and imbue
examples have different combinations and are not covered by these rules.

Native stat 253 now decodes as “Replenishes quantity”, preserving its coefficient
with unit replenishment_rate. Local D2MOO regeneration code verifies the rate
semantics; no exact modern interval or unverified market-property value is
invented. Zero/negative rates and nonzero layers remain unresolved.

### Double Throw imbue alternatives

Reviewed profiles now total 216. Five slot-specific rules cover the cached
planner's ethereal rare imbue examples: Flying Axe in both hands (150 ED,
20 IAS, +2 Combat, 20 fire resistance, quantity replenishment); Flying Knife
in both hands (200 ED, +2 Combat, 121 AR, 6 mana leech, Amplify on striking,
quantity replenishment); Winged Harpoon main hand only (200 ED, 20 IAS,
+2 Combat, 9 life leech, quantity replenishment). Native ED components must
both meet the cited target. Cold damage conflicts with the Find Item setup.
These are concrete example targets, not guaranteed imbue outcomes, universal
minimum rolls or market prices. Source planner IDs80/81/143 in db0106mf retain
the planner2023 date separately from the linking guideMay2026.

The separate premium Flying Knife example78 remains unimplemented: its +20
minimum damage affix must not be confused with the captured total minimum
weapon damage. That distinction needs verified modifier provenance first.

### Typed native thresholds

Stat predicates can require a reviewed unit (`replenishment_rate` or
`percent_chance`). Incompatible/missing units propagate unknown, including
under negation and absent-is-zero rules. The seven rare Double Throw profiles
now require these units for quantity sustain and Amplify chance. A numeric10
in seconds cannot satisfy native replenish rate10. Profiles remain216.

Market mapping for native253 remains deliberately unresolved. The offline audit
pricing/data/appraisal-replenishment-market-audit.json records84 property563
observations across two cached files, with source hashes and listing timestamps.
Values include1,10,20,66,99,100,120,999 and11 for the same tooltip-only property.
These observations do not establish one reliable native-to-market conversion;
no numeric price or boolean normalization is inferred from them.

### Named tier review evidence

The named coverage audit now joins resolved, recommended build occurrences and
leveling recommendations alongside the market-research status for every identity.
Quality and name must match; leveling additionally resolves its item_id through
item facts. Discovery-only and unresolved guide mentions are counted separately.
Build/variant/player-or-mercenary/slot/source locators remain attached to leads.
None of these joins upgrades a row to reviewed tier coverage or assigns a price.

Current audit:565 identities,85 reviewed policies,146 additional identities with
build or leveling leads. Prioritize these leads before collecting more research.
The existing missing_research count still refers only to the supplied WP-I
market-research file; it does not mean the item is absent from the full KB.

### Annihilus trade tier

Named tier policies now86/565. The September18 WP-H research supports a high
Annihilus tier when all captured attribute and resistance components are19+;
other valid rolls receive low. Perfect20/20/10 remains high with a further
within-tier premium. Validity requires captured attributes/resistances10–20,
experience5–10, nonethereal and no sockets. Missing rolls remain conditional;
out-of-range or impossible ethereal/socket states remain pending review.

Annihilus WP-H records now carry explicit unique/name identity metadata for
source validation. WP-H participates in assessment artifact snapshots. These
historical ask/fill buckets do not supply exact numeric prices; scoped matched
comparisons remain the price source. Build usefulness is independent of tier.

### Random class bonuses

Named comparison validation now handles native `randclassskill` in addition to
random skills and skill trees. For Hellfire Torch, the definition selects class
IDs0–7 and native properties func36/val1 supplies exactly+3 class skills. Require
one decoded selected class in a complete capture; market comparison additionally
requires that class's matching property. Missing, multiple, outside-range or
wrong-valued class bonuses cannot establish a comparable or a definite trade tier.
The same guard is shared by named contracts and trade-tier assessment.

### Hellfire Torch premium tiers

Named identity policies now87/565; this does not mean every covered identity's
variants have tiers. Torch high tier applies to20/20 attributes/resistances
across all eight classes and18+/18+ Warlock/Sorceress/Amazon/Druid/Assassin.
Warlock20/20 is explicitly a qualitative inference from its documented18+
premium and improved rolls; the cached perfect bucket is empty, so no perfect
price is claimed. Other class/roll combinations remain pending where the cached
research is thin or contradictory. Exactly one valid+3 class bonus is required,
alongside valid10–20 attribute/resistance bounds, nonethereal and no sockets.
Missing roll evidence remains conditional. Historical buckets never substitute
for exact scoped numeric price comparisons.

### Guardian Angel ethereal perfect premium

Named policies now88/565. Explicit SC/NL/PC/RotW cached asks from two independent
sellers support a qualitative high tier for ethereal200ED Guardian Angel in its
original Templar Coat base. Source evidence is retained in
pricing/data/appraisal-named-tier-research.json, including raw-file hash, row
locators, original ask terms and listing-update dates. Socket state was omitted,
so this evidence does not establish an exact comparison or numeric estimate.
Nonethereal, lower ED and upgraded variants remain pending. The source artifact
participates in assessment snapshots. A guide mention alone did not set the tier.

### Listing direction

Market normalization now preserves active/selling/completed flags and separates
explicit buy offers and inactive/completed listings from asks. Watch summaries
and classifier comparisons exclude those evidence kinds. Existing legacy rows
with omitted status flags retain prior behavior; this does not prove their
current availability. The offline rebuild reclassified96 imported buy offers
(97 raw occurrences before import filtering/deduplication). No online refresh.

### Authorized mercenary market collection

The six-item batch authorized on2026-09-24 collected600 listings in12pages:
Vampire Gaze, Shaftstop, Stealskull, Crown of Thieves, Duriel's Shell and Kira's
Guardian.237 observations have verified SC/NL/PC/RotW scope;236 are seller asks,
158 have convertible asking prices. These counts are not independent sellers or
exact comparables. Many omit ethereal/socket details. Raw responses and fetch
timestamps are cached under appraisal-research-mercenary-20260924; the batch plan
and appraisal-mercenary-market-review.json preserve scope counts. No rate limit
recurred. Market artifacts, watchlist and index were rebuilt offline afterward.

Newer inactive observations now supersede older asks in watch summaries before
filtering; runeword imports retain inactive/unknown-status evidence so completed
listings cannot silently leave their old asks eligible. Unknown runeword listing
status remains unverified, preserving the prior active-seller requirement.

### Verified unique upgrades and Shaftstop

Named unique resolution accepts an upgraded base only when the capture supplies
a matching unique table ID and both base catalog rows agree on the same ascending
normal/exceptional/elite chain. Name-only claims, downgrades, unrelated bases and
conflicting table IDs remain rejected. Contracts still use the observed target
base and actual defense; this does not merge original/upgraded price cohorts.
Set upgrades are not enabled by this change.

Named policies now89/565. The new mercenary batch supports a qualitative high tier
for ethereal220ED Shaftstop in Boneweave, with three independent scoped seller
asks retained in appraisal-named-tier-research.json. Defense differs and socket
details are missing, so no numerical same-variant price is inferred. Nonethereal,
lower rolls and original Mesh Armor remain outside this reviewed premium rule.

### Crown of Thieves gold-find premium

Named policies now cover 90/565 identities, still only conditional variants.
Two independent scoped seller asks support an ethereal Crown of Thieves premium
with 100% gold find and 12% life leech: original Grand Crown at 198 ED and upgraded
Corona at 200 ED. The original branch accepts 198–200 ED, explicitly treating
199–200 as better-roll inference. The upgraded branch requires 200 ED and the
verified table identity used by unique-upgrade resolution. Missing rolls remain
conditional; lower rolls and nonethereal examples remain pending. Different
bases and incomplete socket information prevent pooling these asks into an exact
numeric estimate. Original terms, fetch dates and source hashes are retained.

### Named equipment market bases

Named equipment listings with explicit property930 base tier now resolve their
actual base code through the named definition and native upgrade chain. Both
chain rows must agree; downgrades and ambiguous/impossible tiers are flagged.
Missing tiers remain unknown rather than assuming the original base. This
complements captured unique-upgrade support and closes a missing normalization
step that prevented otherwise complete named equipment comparisons. It does not
supply absent defense, sockets or ethereal flags. Named non-equipment mechanics
remain separate and do not lend their zero-socket/nonethereal defaults to armor.

### Upgrade flags in named comparisons

Market property1216 (`Upgraded`) is now validated against the resolved named base
chain. The flag is treated as identity metadata only when its boolean value agrees
with that chain and carries normalization provenance. Contradictory or malformed
flags remain comparison conflicts. This removes a false extra-modifier rejection
for upgraded listings without relaxing variable-roll equality. An end-to-end test
starts with native Shaftstop stats, creates the upgraded comparison contract and
matches a fully specified listing with fixed bonuses omitted; changed defense/ED
and incorrect upgrade flags fail.

### Named variable-roll bounds

Named contracts validate captured variable integer bonuses against the selected
unique/set definition before market matching. `mechanics/named_rolls.py` owns
capture checks and the explicit list of modifiers whose standalone bounds can
be checked without base contributions. This includes enhanced defense/damage,
leech, damage reduction, gold/magic find and selected speed/utility modifiers.
It rejects nonfinite, boolean, fractional and out-of-range values. Empty sockets
remain required independently. Out-of-range set totals require contribution
review; they are not automatically a standalone comparable.

Defense31 is a total and is not constrained to a flat-added-defense roll range.
Base-dependent damage, durability, resistances and staffmods need their own
contribution checks. Fixed rolls retain existing verification paths. The new
variable-bound check applies to 297 unique and 9 set identities in the current
named-definition map; this count is validation coverage, not price coverage.

### Captured set upgrades

Named definition resolution accepts verified set-table identities on ascending
base chains, matching the existing unique-upgrade policy. The original named
definition still supplies modifiers; the contract retains the captured base code,
base tier and actual total defense. Original and upgraded listings cannot mix.
Missing/wrong table identities, downgrades and unrelated chains reject. Ethereal
sets remain rejected. Existing leveling policy requires the original base before
using original-level recommendations.

Local mechanics evidence: `third-parties/d2data/json/cubemain.json` records151-154
at the checkout pinned in `third-parties/repos.json`, with weapon/armor set inputs
and `useitem,mod,exc` / `useitem,mod,eli` outputs. This recognizes an already
captured upgraded item; it does not claim recipe availability in every mode or
supply a market premium from upgrade cost. Synthetic comparison regressions cover
Sazabi's Mental Sheath (Giant Conch) and Tancred's Crowbill (Crowbill/War Spike).

### Leveling identity and variant requirements

Named leveling recommendations now resolve the same unique/set table identity and
base chain as trade assessment. A familiar name on a different same-slot base,
conflicting captured table ID, or unverified upgrade no longer inherits a leveling
recommendation. Verified upgrades retain their reviewed utility but show a
conditional recommendation when the variant's equip requirements are unknown.
Original requirements are never copied to an upgrade or socket-modified variant.
The terminal/OSD conditions retain both set-companion needs and the specific
requirement-verification condition. Normal original-base recommendations with
known requirements remain unchanged.

### Display names and Hellwarden tier

Definition maintenance supplements missing planner strings with the pinned
`third-parties/d2data/json/allstrings-eng.json`, recording its fingerprint in
inputs. Existing planner translations retain precedence. Fourteen unique names
now resolve to their English display names, including Hellwarden's Will,
Ars Al'Diabolos and the Latent/Renewed Sunder variants. Table IDs and original
`game_definition.index` values are unchanged. Bundled memory metadata uses the
same generated definitions.

Named tier policies now cover91/565 identities. Hellwarden's Will uses the dated
WP-I enemy fire/magic resistance buckets: both8 means high; other reviewed rolls
mean med. This applies to the original nonethereal empty-socket Death Mask with
valid resistance/ED ranges. Unknown rolls stay conditional and other variants
pending. This is qualitative historical evidence, not an exact current price.

### Native capture of named upgrades

The bundled metadata builder now publishes verified ascending `upgrade_variants`
for unique/set records. Both original and target raw base rows must agree on the
normal/exceptional/elite chain. `resolve_identity` accepts these variants only
for named set/unique tables after validating quality, identified flag and table
ID. Rare and runeword resolution are unchanged; no runtime pricing-catalog read
is introduced. The named definition remains original, while captured item facts
retain their actual base for assessment and comparison.

For items with unmodified base defense, each upgrade carries its target base's
range. A synthetic upgraded Aldur's Advance uses Mirrored Boots59-68, not Battle
Boots39-47. Modified-defense items remain under their existing contribution rules.
A saved Tancred capture with the base deliberately changed to War Spike tests the
full decode-to-assessment identity path; it is not evidence of a live host capture
or an exact priced cohort. Restart the worker to load the rebuilt metadata/code.

### Class-specific skill rolls and Ars Al'Diabolos

The range compiler now handles property `skill` (native function22,
item_singleskill), alongside aura/oskill. String and numeric parameters must
resolve to an ID in the pinned skill table. Parameterized107 entries are retained
in definitions and bundled metadata, so named capture checks and range displays
can require the correct skill layer. This covers43 unique and1 set identities in
the current named map, including Ars Al'Diabolos Apocalypse401 at3-5.

Ars Al'Diabolos has a high qualitative tier from dated WP-I research across varied
rolls. The policy requires valid ED, fire damage, mana-after-kill, fire resistance
and Apocalypse rolls on the original nonethereal unfilled base. Unknown rolls
remain conditional. This does not assign a roll premium or use the historical
mixed-roll median as a current price. Reviewed named policies now92/565.

### Named elite listings without a tier selector

Market normalization can resolve an omitted930 tier when every named variant
identifies the same original base and the pinned catalog marks it Elite. Such a
base cannot upgrade further. Provenance records tier_source=sole_elite_definition;
no synthetic930 property is inserted. Missing tiers remain unresolved for normal/
exceptional bases, ambiguous legacy/current names, or incomplete definitions.
Explicit conflicting tiers and claimed upgrade flags still reject. Socket,
contents and ethereal absence remain unknown for equipment.

Offline reimport resolved1,919 scope-verified observations with this evidence.
This is identity coverage, not1,919 priced variants or independent sellers.

### Impossible equipment facets

Recognized named set equipment can infer nonethereal status when738 is omitted;
ITEMS_MakeEthereal excludes set quality in the pinned D2MOO reference. Explicit
contradictions stay in the source properties and block comparisons. Recognized
named gloves/boots/belts can infer zero sockets and empty contents only when every
same-name definition has the appropriate native type and gemsockets=0. This does
not infer ethereal status for unique equipment or an original base for an item
that might be upgraded. Unknown names get no such facts.

The adapter shares the existing non-equipment facet validation helper, retaining
original listing fields and provenance per inferred facet. Offline reimport adds
zero-socket facts to1,474 scoped observations and nonethereal set facts to634;
these may overlap and do not establish full exact-price eligibility.

### Base/affixed equipment catalog facts

`market_base_catalog.py` resolves exact normalized names within the explicit base
listing category against native armor/weapon catalog rows. Unknown/generic names,
wrong categories and conflicting duplicate definitions are not guessed. Existing
conflicting base codes are preserved with comparison-blocking diagnostics. The
catalog is read through the artifact snapshot mechanism and its generation is
recorded in inferred facet provenance.

Normal/superior/magic/rare/crafted listings preserve their supplied quality and
ethereal state. Native glove/boot/belt types with explicit zero capacity can infer
zero sockets/empty contents; other equipment retains missing socket information.
Reimport resolved7,567 scoped observations to base codes and supplied socket facts
to1,283 of them. These counts describe normalization coverage, not independent
sellers or exact price coverage.

### Explicit unsocketed listings

A valid numeric402=0 establishes empty contents when934 is omitted or null. The
normalizer records `explicit_socket_count` provenance and preserves raw properties;
it never inserts a seller-provided contents field. Nonzero/missing/invalid counts
remain unknown. A listed insert with zero sockets is a mechanics conflict and
cannot become a comparable. Null contents also remain compatible with separately
proven nonsocketable base mechanics.

A three-seller synthetic regression reaches the exact-price path with otherwise
matching unsocketed asks and no934 field. It does not imply that a missing socket
count means zero or that real cohorts have sufficient complete comparisons.

### Fire Warlock grimoire variants

Two reviewed Ars Al'Diabolos off-hand candidates preserve Standard's Um socket
and Magic Find's Ist socket from their individual guide-extraction rows. Native
Chaos skills188:58, FCR105, fire damage329 and Apocalypse107:401 establish relevant
functionality. Max25 fire damage and +5 Apocalypse are definition-based preferences,
not guide-mandated viability or price thresholds. Missing rune remains a setup
condition; player class, nonethereal use and full equip/breakpoint/resistance checks
are retained. Hardcore alternatives are not folded into these Softcore profiles.

The build importer also supplements planner strings with pinned English strings,
preserves internal-name aliases, and fingerprints the added source. All11 cached
Ars and21 Hellwarden demand occurrences now resolve to named identities. Reviewed
profiles total218; these occurrence counts are not complete reviewed role coverage.

### Shared display-name import policy

Definitions, build demand and item facts now use `localization.merge_game_strings`:
valid planner translations retain precedence and pinned English translations fill
missing keys. Item-facts adapter3 records the correct per-name source and includes
the English table fingerprint in its input manifest. Internal aliases and item IDs
remain stable. Offline rebuild confirms Ars Al'Diabolos, Hellwarden's Will and
Renewed Cold Rupture join their market catalog entries through display names.
Facts/recommendations, demand, watchlist and SQLite were rebuilt together; no
additional pricing tier is inferred merely from a successful identity join.

### Echoing Ubers Hellwarden role

The reviewed Ubers player-helmet profile preserves Hellwarden's Will with
Guardian's Light and the Sling/Renewed Black Cleft companions from the dated
Echoing Strike guide extraction. Native magic-pierce, all-skills, IAS and FCR
establish relevant functionality;8% magic-pierce is a definition-based preference.
Missing companions or insert remain explicit setup conditions. Equip requirements,
resistances, bound Pit Lord and Enchant/Fade prebuff checks remain with the full
setup rather than promising a damage multiplier from the helmet alone.

Profiles now accept one `required_socket_item` name for jewels/gems as well as
the existing `required_rune` field. Empty/invalid values or both fields together
reject during validation. Existing rune profiles retain their behavior. Reviewed
build profiles total219; named trade tier and numeric comparison remain separate.

### Attribute representation and publication reconciliation

Exact comparisons expand market727 (all Attributes) into verified strength437,
dexterity429, vitality582 and energy421 fields. This is lossless representation
normalization, not a roll tolerance. Combined-plus-individual overlap is rejected
because contribution semantics are ambiguous; invalid values are rejected. Both
sides use the same canonical form, alongside existing all-resistance expansion.
A native20/20/10 Annihilus regression verifies the path through named contracts.

An audit exposed refresh overwriting inferred empty socket contents after normal
listing normalization. The final publication reconciliation now reapplies game
mechanics after rebuilding raw properties/scope/contents, before runeword handling.
Regression tests specifically cover this publication stage. Earlier inference
counts based on facet provenance alone did not prove final persisted contents;
verify actual serialized values after refresh. Source properties stay unchanged.

### Dragon Talon budget Cannot Be Frozen alternatives

Reviewed the explicit `/variants/0/quotes/1` alternatives in the cached Dragon
Talon Assassin guide: Kira's Guardian in Helmet and Duriel's Shell in Body Armor.
These are player alternatives, not the variant's Act 3 mercenary equipment.
Rules require Assassin context, non-ethereal durability, captured Cannot Be Frozen
(native153) and positive elemental resistances. The report retains full-loadout
Crushing Blow, Attack Rating, resistance, equip-requirement and level-90 guide
conditions; item eligibility does not establish Uber readiness or a price.
Absent stats fail complete captures and remain unknown for incomplete captures.
The source quote and fingerprint are retained in the profile bundle.

### Angelic set companions and duplicate equipment

Ten reviewed player roles cover Angelic Wings/Halo for Double Throw, Strafe,
Echoing Strike, Dragon Talon and Berserk Starter/Budget variants. The cited
Double Throw and Strafe setups require two Halo rings; the other three cite one.
Dependencies preserve the exact source combination, wearer class and player side.
Missing companions are not silently assumed from a hover. Set activation is not
required in the hovered stat array; no bonus or numeric price is synthesized.
Mirrored Blades' planner-only occurrence remains outside reviewed coverage.

`AssessmentContext` retains duplicate names in sequence inputs as immutable
tuples. Set/frozenset inputs remain membership-only, represented as frozensets.
`context_count_at_least` checks positive integral counts on player/mercenary
collections. Membership-only inputs can prove absence or presence of one copy,
but cannot prove or disprove a larger count when the item is present. Unknown
or malformed loadouts remain unknown. Context sequences describe the actual
loadout, including equipped copies of the hovered item; they are not a list of
additional companions. Runtime and compiler share predicate validation.

### Starter set combinations and belt preparation

Thirteen additional roles preserve the source-specific Sigon combinations for
Strafe, Double Throw and Berserk, and the Death's Hand/Guard pair for Budget
Enchant. The exact other pieces must be on the player; a mercenary wearing them
cannot satisfy player set dependencies. Unidentified or absent equipment does not
establish set activation. The Strafe Visor requires its cited Ort socket; the
Double Throw Visor's 15% IAS jewel remains a visible verification condition, not
a claim derived from any filled socket.

Separate Death's Guard roles for Strafe/Double Throw require captured native153
Cannot Be Frozen. The cited Demonhide Sash upgrade is a preparation dependency,
not a requirement for the normal Sash's CBF utility. Upgraded equip requirements
remain conditional. No equipped set bonus or guide-derived price is synthesized.
Planner-only Mirrored Blades Sigon entries remain outside reviewed coverage.

### Captured socket-jewel properties

Linked socket children now retain bounded native stat-array reads, with the same
second-read checks as parent item stats and final linkage/field verification.
Child total stats are decoded separately into each socket item's own native
stat map; absent historical child arrays remain incomplete, never parent-derived.
The `socket_jewel_stat_at_least` predicate checks one actual jewel, never sums
multiple jewels or borrows the parent's total. Conflicting occupancy, missing
child evidence and invalid values remain unknown; complete known non-matches fail.

Double Throw Starter Sigon's Visor now has an executable 15% IAS jewel dependency
instead of its permanent textual payload condition. Other build breakpoints stay
conditional. This does not enable filled-socket price comparisons or infer socket
contributions to all parent stats. Restart the worker for new child evidence;
old saved captures remain readable with unknown payload stats. Validation uses
synthetic memory/decoder evidence plus existing item replays, not a new live probe.

### Compound socket-jewel requirements

`socket_jewel_matches` validates a nonempty map of native stat thresholds and
requires all of them on one captured jewel. It shares evaluation with the scalar
IAS predicate; the compiler validates every referenced native stat/parameter.
Two separate jewels cannot satisfy one combined jewel requirement. Known
shortfalls dominate unknown fields for that jewel, while unknown eligible child
evidence prevents an unsupported negative result. Parent totals are never used.

Dragon Talon Budget Guillaume's Face now preserves its cited 15 IAS / 30 lightning
resistance jewel target with this executable dependency. That target describes
the specific guide setup, not a universal minimum for viable Guillaume's Face or
a numeric price rule. Full-loadout requirements remain visible conditions.

### Named base resolution from explicit upgrade flags

Market1216 is the cached boolean Upgraded selector. When tier930 is omitted and
the named definition has one original equipment base, an explicit false flag
selects that original tier. An explicit true flag selects an upgraded tier only
when the verified native chain has one possible higher outcome. Thus exceptional
Shaftstop can resolve to elite Boneweave; normal Magefist with Upgraded=true stays
ambiguous between exceptional and elite. Missing/malformed flags and multiple
original identities never default to an original base. An explicit tier still
takes precedence and contradictory flags remain conflicts.

Provenance records `explicit_upgrade_flag`; raw properties are unchanged and no
930 selector is fabricated. The exact comparison contract still checks actual
base, ethereal, sockets/contents, defense and complete modifiers. Synthetic dated
three-seller regression verifies the price gate, not a real market-price claim.

### Named market evidence readiness audit

Run `uv run --offline python -m pricing.knowledge.assessment.maintenance.market_readiness --as-of 2026-09-24`
to generate a deterministic research queue from the cached market JSONL. It
removes superseded/duplicate snapshots, verifies scope and counts missing base,
ethereal, socket count/contents, units, seller, price, dates and mechanics
conflicts per identity, retaining bounded source examples. Filled socket policy
gaps remain distinct from unknown contents. This measures prerequisites only;
it does not validate every modifier or prove comparable seller coverage.

The 2026-09-24 publication has 6,665 scoped current observations across151 named
identities, with zero passing every prerequisite. All237 scoped rows in the
six-item mercenary batch lack explicit socket counts. Most older cache dates
are unverified; missing facets must not default to non-ethereal/unsocketed.
Vampire Gaze also has seller rows using flat damage reduction413 where its native
percentage reduction projects to1865; those are distinct properties and cannot
be aliased globally. No new Vampire Gaze trade tier was assigned from this sample.
Use `pricing/data/appraisal-market-readiness.json` to target evidence work rather
than repeat broad collection or claim that catalog/listing coverage means prices.

### Intrinsic unique ethereal mechanics

Named market normalization reads fixed native unique properties across every
same-name definition. An explicit fixed `ethereal=1` property establishes true;
otherwise intrinsic fixed `indestruct=1` establishes false. The local native
reference applies unique properties before the final random ethereal pass, which
requires durability and excludes the indestructible stat. Forced ethereal
properties take priority (Ethereal Edge, Ghostflame and Shadow Killer also have
indestructibility). Wraith Flight supplies the fourth forced-ethereal identity.

This is definition evidence, never inference from an item's title, an inserted
Zod or self-repair/replenishment. Conflicting/incomplete definition variants do
not resolve a state. Explicit contradictory listing flags remain visible
mechanics conflicts; no raw738 field is fabricated. The snapshot generation
and local reference paths are retained in facet provenance.

### Throwing-weapon socket eligibility

Market normalization now establishes zero sockets and empty contents for exact
throwing-weapon catalog identities (`jave`, `ajav`, `tkni`, `taxe`). The pinned
item-type table explicitly gives MaxSockets1/2/3=0 for these families; omitted
`gemsockets` on a weapon base is not itself interpreted as zero. Every same-name
unique/set definition must agree with the supported nonsocketable family, and
contradictory positive base capacities prevent inference.

The rule applies equally to named and exact base/affixed listings. Explicit seller
claims of sockets or contents are preserved and flagged as conflicts. Ethereal
status is independent; javelins are not generalized to spears, throwing knives to
daggers or throwing axes to ordinary axes. Raw property402/934 fields are not
fabricated. Other exact-comparison and publication gates remain unchanged.

### Bow-family ethereal eligibility

The base catalog now preserves the native `nodurability` field as
`no_durability`, retaining missing as unknown. Verified bow/abow/xbow identity
plus explicit integer1 establishes non-ethereal eligibility, using the pinned
ITEMS_MakeEthereal / ITEMS_HasDurability rule. All42 current bow/crossbow bases
have this flag. Named uniques require every same-name definition to agree and
exclude any explicit ethereal property. Set items retain their separate quality
rule. Socket count and contents stay independent and unknown when omitted.

The rule does not extend to Phase Blades, arbitrary indestructible bases,
javelins or missing durability flags. Conflicting seller ethereal=true remains
a conflict with the original flag intact. No market738 property is fabricated.

### Completed bow runewords

Runeword normalization now applies the verified bow-family non-ethereal rule
after an explicit base selector matches both the recipe's allowed base codes
and the compiled equipment catalog. Word identity alone is insufficient.
Missing/conflicting/incompatible selectors or unavailable base mechanics leave
the field unknown. Non-bow recipes keep their existing ethereal requirements.
Contradictory seller flags remain conflicts, with raw properties unchanged.
Recipe socket count/contents and all roll/base comparison gates are preserved.

### Ordinary Phase Blade bases and completed recipes

Nondurable sword mechanics now establish non-ethereal state only for explicitly
normal/superior/low-quality base listings or verified completed runewords. The
compiled native catalog currently has one nondurable sword: Phase Blade. Native
random ethereal generation requires durability; pinned cube upgrade recipes
129–136 and151–154 apply to unique/rare/set qualities, not ordinary bases.

Rare, unique, magic and unknown-quality base listings do not inherit this rule;
upgrade-derived ethereal Phase Blades are not rejected merely for their base.
Completed recipes first require an allowed, exact base selector. Missing socket
counts remain unknown for ordinary bases, and explicit conflicting ethereal
flags remain visible. Dimensional Blades and Berserker Axes are unaffected.

### Completed runeword base quality

Contracts retain base_rarity separately from completed recipe rarity. Explicit
Traderie property1281 must be normal, superior or low quality and match the
captured native quality. Omitted or malformed selectors remain unresolved; raw
properties are preserved. Matching base quality does not waive exact roll,
defense, ethereal, socket or market-evidence requirements.

### Runeword enhancement totals

Weapon, body-armor and helm variable recipe enhancement rolls are bounded using recipe
ranges plus rune contributions. Superior quality allows the optional bonus from
the compiled quality definition (currently 5–15), as well as zero when another
quality modifier was selected. Captured totals remain exact comparison values;
no ambiguous recipe roll is inferred by subtracting a guessed quality bonus.
Captured fixed recipe enhancement values use the same contribution checks. Missing
fixed values are not invented; existing capture and comparison gates still apply.
Shield automods need separate validation.

### Demon Limb prebuff utility

Four reviewed player profiles cover Echoing Strike Standard/Ubers, Strafe Standard
and Dream Ubers. They use native Enchant charge availability and preserve
Strafe's Lava Gout alternative. Prebuff placement is separate from combat weapon
selection; equip requirements and recharge eligibility remain conditions. Empty
or unknown charges do not imply available Enchant. Planner-only Double Throw
cube mentions were not promoted by this review.

### Affixed Crushing Blow leveling utility

Reviewed generic pattern6 (source timestamp17:42) now recognizes positive native
Crushing Blow on magic/rare/crafted weapons as conditional player attack-build
boss utility. It does not establish weapon damage, speed, equip readiness, mercenary
compatibility or trade value. Duplicate/conflicting native stats cannot satisfy
any generic leveling pattern; independently verified utility remains available.

Charged-skill role checks use semantic native-stat validity. Duplicate/conflicting
charge pools remain unknown and cannot prove availability or exhaustion; an
independently verified pool for the requested skill can still establish utility.

### Saved-item regression command

Run `uv run --offline python -m pricing.knowledge.assessment.maintenance.replay`
to replay18 historical captures through the current decoder, offline retrieval
and shared text report. Optional positional item stems select a subset. JSON
output includes source fixture, extraction, assessment, price evidence and text.
Four archived snapshots preserve the original context missing from compact
Shako/Atma/life-charm stat fixtures; their report envelopes are reconstructed from
the successful frozen capture's recorded identity, fingerprint and timestamp.
This performs no live process reads and does not claim current inventory state.
Hellplague and Runic Talons are included. The historical Runic Talons capture
lacks verified socket contents: its three sockets remain unknown rather than
being inferred empty from the screenshot. Hellplague fire-skill text and native126:1 now have a verified definition and
all-class Fire Skills market mapping (586); matching price evidence is separate.

### All-class Fire Skills

The pinned fireskill property (function21, item_elemskill, layer1) now compiles
into definition range126:1. Ten named/set/runeword records gain this definition.
Comparison projection uses market586, distinct from Sorceress-only Fire skill
tab188:8. Named bonuses must fall within their definition range, including fixed
bonuses. Hellplague's saved capture now produces a comparison contract; it still
has no sufficiently matched numerical price cohort.

### Nonsocketable captured item families

Decoder mechanics establish zero sockets/empty contents for verified jewelry,
charm, jewel, glove, boot, belt and throwing-weapon types with explicit zero capacity in all pinned itemtypes bands.
This can resolve old captures without a child scan. Missing flags, a socketed
flag, any captured socket stat, child items or conflicting already-known socket
state prevent inference. Source.socket_mechanics records the derivation; ordinary
socketable equipment keeps its capture requirements. Atma and both life-charm
replays now produce comparison contracts without inventing numerical prices.

Socket comparison diagnostics distinguish unknown contents from verified filled
sockets. Missing contents produce one shared evidence gap, not an additional
filled-socket claim. Filled items still require contribution-aware comparison.

### Topaz socket leveling utility

Reviewed generic pattern1 (timestamp07:47) supports early magic-find helm/body
armor setups. A verified topaz base code, consistent filled-socket state and
positive nonconflicting native MF are required. Rune recipes, unknown payloads,
wrong equipment types and conflicting socket states do not qualify. This is a
conditional use, not an equip-readiness or price claim; compare against Stealth
and stronger equipment and preserve survival. Named-item leveling evidence is
retained alongside applicable socket utility.

### Three-diamond shield leveling utility

Reviewed generic pattern7 (20:49) recognizes the three-perfect-diamond alternative
to Ancient's Pledge. It requires three distinct verified gem children in a
consistent three-socket shield and at least57 in all four native resistances
(pinned gems.json:19 all resistance per Perfect Diamond). Partial child lists,
duplicate identities and wrong gems do not qualify. Equipment requirements,
blocking and current survival needs remain conditions; no market value follows
from the recipe or gem cost.

### Resistance and life socket customization

Reviewed patterns5/9/10 now cover three resistance-rune helms, Moser's Blessed
Circle with diamonds/resistance runes, and Rockstopper with rubies/resistance
runes. Distinct complete child identities, valid named identity where applicable
and observed totals consistent with filler bonuses are required. Named minimum
innate rolls are included in those checks. Pinned gems.json validates diamond,
ruby and rune amounts. Socket checks live in policies/socket_leveling.py, separate
from generic affix patterns; source fingerprint and report assembly remain shared.
These are conditional customization uses, not complete loadout or price claims.

### Magic-find fillers in armor comparisons

A named helm/body armor filled with verified Perfect Topazes and/or Ist runes can produce
an exact contract. Built-in socket ranges come from its named definition; other
named items remain limited to one socket. Every child must be distinct and captured. Socket occupancy and gem identity must be complete; native
MF raw/decoded/projected values agree. Subtract24 per Perfect Topaz and25 per Ist rune only for checking the named
item's own MF range, while retaining total MF and all other captured properties
in the market contract. The contract's socket_payload requires an explicit
matching934 description. Missing, different or multi-filler listings are rejected.
Payload matching ignores order but preserves filler identity and multiplicity.
Partially filled named items are supported only when occupied and empty counts
are known and all occupied child identities are captured. Total sockets plus
explicit filler multiplicity remain separate comparison facets. This does not
support arbitrary jewels; the fixed survival fillers below are also supported.
Armor Ist25 is verified independently of weapon Ist30. Existing seller/scope/date/dispersion gates are unchanged.


Base, magic, rare and crafted helm/body armor comparisons also accept verified
Perfect Topaz/Ist payloads. Exact compiled base identity supplies the physical
socket maximum. Base items must have zero MF left after the fixed socket bonus;
affixed items may retain nonnegative innate MF. This does not certify affix roll
legality. Contracts retain observed total MF, actual defense, rarity, ethereal
status, socket count/payload and all other captured modifiers. They cannot borrow
prices from empty bases or other qualities. Unknown partial occupancy, incompatible
families, excessive socket counts and unexplained base MF remain rejected.


### Fixed survival socket comparisons

The shared socket_fillers handler additionally supports Ruby grades for flat life
in helms/body armor, Diamond grades for shield all-resistance, and Ral/Ort/Thul/Tal
resistance in both destinations (30 armor versus 35 shield). Constants are shared
with leveling utility and checked against pinned gems/properties/itemstatcost.
Life raw values use the native fixed-point scale. Every affected observed stat
must agree with its raw and projected market values. Named innate bonuses are
checked after subtracting the fixed fillers; actual totals remain in the market
contract and cannot be omitted as intrinsic named bonuses.

Built-in socket counts encoded as the named definition's fixed sock parameter
are recognized, including Moser's two sockets. Other counts still use the named
socket range or one added socket. Tests cover Rockstopper Ruby/Ral, Moser Diamond/
Ort, three-rune helms, diamond shields and mixed life/MF. Base shield comparisons use the catalog
automagic resistance choices and require the same residual across all four
resistances. Other base filler-related innate bonuses must remain zero. Affixed residual bonuses
remain exact captured comparisons, not proof of legal affix generation. Arbitrary
jewels, unsupported fillers and missing child identities still withhold comparison.


### Base shield resistance contributions

Catalog maintenance compiles base_resistance_options from each native auto-prefix
group and the pinned automagic table, retaining its source hash. Missing tables or
unsupported resistance patterns produce an unknown option set, not a zero bonus.
Filled base shield comparisons subtract the verified Diamond/rune contributions
and require one shared allowed innate roll across fire/lightning/cold/poison.
All four stats must be captured for bases that can carry nonzero all-resistance;
missing components never imply zero. Exact market properties remain the totals,
including filler bonuses. Normal and superior Paladin shields are supported;
ordinary shields cannot inherit their automods. This does not assign a market
price without a matching scoped cohort or prove item-level eligibility.

### Engine-owned base suitability

`assess` returns `base_uses` alongside roles, leveling and price policy. The shared
base-use evaluator consumes the engine's normalized facts. Retrieval reuses these
results in the current terminal/OSD report envelope; it no longer normalizes and
evaluates runeword-base suitability independently. Market-history lookup remains
outside the engine and does not alter usefulness judgments.


### Ethereal preferences across uses

Base-use results carry an explicit ethereal preference per wearer. Mercenary
weapon/armor uses prefer ethereal; player armor/shield uses avoid it; Nova casting
and the durability-free Phase Blade branch are neutral. The engine combines
these with viable reviewed role preferences and the existing named/base evidence.
Conflicting directions produce `mixed`, leaving the global terminal/OSD color
neutral while preserving each use and its explanation in structured evidence.
Failed/unknown roles and impossible socket preparations cannot change the color.
This is utility guidance, not an ethereal price multiplier or a worthless verdict.

### Indexed base recipe lookup

`mechanics/recipe_index.py` compiles immutable base-name candidate lists and
per-runeword recommended mercenary alternatives. Base suitability and generic
ethereal guidance use these lookups rather than rescanning the full utility
catalog. Cache keys include artifact bytes and native base-type identities;
existing artifact snapshots preserve in-flight generations. No filtering decision
moves into the index: candidate order, provenance and all base-rule rows survive.
Full-catalog recall is tested against the scan reference.

Local 40-sample engine benchmark (Giant Thresher, explicit empty role profiles):
warm p50 42.6→18.7ms, p95 46.7→20.2ms. Single cold initialization measurements
627→794ms include added index construction and are not a statistically established
cold regression. These measure engine assessment, not capture, SQLite or UI latency.


### Defensive rune fillers

Fixed-contribution comparisons additionally support Um (15 armor/22 shield all
resistance), Shael (20 armor hit recovery/20 shield block rate), and Ber (8 physical
damage reduction). Source checks resolve native stat IDs from the pinned property
table. Named innate rolls are validated after subtraction; listing comparisons
still require exact observed totals and filler identities. Moser with Um/Shael
accepts a47-allres listing and rejects its unmodified25-allres total or wrong fillers.

For class shields, totals can admit a different valid innate roll:60 allres with
Um can be22+38. Without independent pre-socket evidence, the engine does not claim
that this is an incorrect45+15 combination. It only compares the observed total,
base, quality and actual filler. Ordinary shields cannot inherit that ambiguity.


### Cham and Cannot Be Frozen comparisons

Single verified Cham fillers are supported in helm/body armor/shield contracts when
native153 has decoded/raw value1 and the innate contribution is consistent with the
named definition or base policy. Zero, stacked and unresolved flag payloads remain
unsupported; the capture decoder's flag semantics are not broadened.

Market591 is a verified boolean field. Comparison canonicalization equates true
with native1 (and false with0), rejecting strings, floats and other integer values.
The rule applies to innate Cannot Be Frozen as well as socketed items. Other market
properties retain their strict types, so a numeric MF field cannot become1 merely
because a listing contains true. Exact filler identities and all other modifiers
remain required, with no new price inference from Cham cost.

### Zod and indestructible variants

Verified single-Zod payloads now work for weapons as well as helm/body armor/shield
comparisons. Weapon effects are verified separately; armor rune
bonuses are never reused for weapon destinations. Indestructible market432 is a
verified boolean representation of native152=1, with the same strict normalization
as Cannot Be Frozen. False, malformed and stacked raw flags remain distinct or
unsupported. Ethereal status, empty remainder, actual modifiers and Zod identity
remain exact comparison facets; prices are not inferred from Zod cost.

Pinned properties.json routes indestructibility through function20 rather than a
stat column. The local D2MOO implementation explicitly adds native indestructible1;
the source audit covers that special route. Tests include an ethereal Rune Master
with Zod plus two verified empty sockets, rare weapons and base/affixed armor.

### Fixed weapon socket contributions

Weapon comparisons also support Shael20IAS, Ber20Crushing Blow, Um25Open Wounds and
Ist30Magic Find, including mixed payloads and verified empty remainder. Pinned
weapon property tables independently verify these effects; armor recovery,
resistance, physical reduction and25MF bonuses do not transfer to weapons.
Named innate bonuses are range-checked after subtracting fillers; exact listing
comparisons retain full observed modifiers, identity, quality and socket payload.
Empty bases, different fillers and altered total modifiers remain separate cohorts.

### Comparison request sets

Structured assessment includes comparison_requests and retrieval adds
comparison_results. Runtime currently emits one exact_current_variant request;
reviewed role-specific comparison policies can add separate requests without
pooling their sellers or prices. Requests detach immutable contract/role data.
Identical requests merge references only within the same segment/state/version.
Duplicate request IDs fail instead of overwriting results. Prepared requests skip
market retrieval and never receive a current-item estimate. Existing report fields
select request current explicitly; they do not choose the highest segment price.

### Explicit loadout and appraisal date

`retrieve_draft(extraction, database, loadout=..., as_of=date(...))` now accepts the
same immutable AssessmentContext fields as the engine and an explicit date for
market publication. Missing context stays unknown. Known companions/mercenary type
resolve their own conditions without erasing socket or other setup requirements.
Context does not modify item facts or substitute build demand for market evidence.
The default date remains the current UTC date, pinned before retrieval; all request
results and unclassified fallback diagnostics use that same date. Invalid date
arguments fail before opening the index. `extract_and_retrieve` accepts these
options separately from OCR arguments. The host worker still uses unknown loadout
unless its caller supplies context; automatic live-loadout capture is not added.

### Market evidence readiness

The offline `maintenance.market_readiness --as-of YYYY-MM-DD` audit recognizes
explicit supported socket fillers using the same destination-specific effects as
the comparison handlers. Missing/unknown payloads, contents exceeding socket count,
and unsupported stacked boolean effects remain research gaps. Structural readiness
does not prove captured modifier equivalence, innate roll legality, seller coverage
or a price. Captured contribution validation still runs in the item handler.

### Structured socket preparation

Each `base_uses` result now includes `preparation` options for its destination
runeword and role. Immutable PreparationOption records expose the action, target
socket count, feasibility, preconditions, conditional success weights and whether
contents are destroyed. Larzuk and cube distributions remain conditional on the
unknown item-level socket cap; they are not pooled into an unconditional chance.
Superior bases have no cube action. Clearing known filled sockets records destruction;
unknown/conflicting socket captures and unreviewed low-quality repair paths do not
produce actionable options. The same evaluation supplies existing report wording.
Observed facts and current-item comparison requests are never rewritten with a
possible prepared result. Explicit action chains and low-quality normalization/upgrades remain unfinished.
Preparation options include consumed resources and their quantities, cube/ingredient
availability or unused Larzuk reward prerequisites, and cube recipe source locators.
The four equipment socket recipes and removal recipe are reviewed against pinned
cubemain/misc tables; runtime does not read third-party files. Mechanical feasibility
is distinct from resource ownership. Resource requirements never imply an Ist price.

### Colossal Jewel fixed triggers

The definition compiler normalizes native property-code capitalization before
matching chance-to-cast functions. Six unique Colossal Jewels use `Gethit-skill`
in the pinned source, while the property table uses lowercase. Their fixed 1%
when-struck event, skill and level now participate in named comparisons. Four
have verified market fields; the other two remain identity-fixed invariants with
no invented market mapping. Missing/changed native triggers block the comparison.
This fixes mechanics coverage, not the thin Defender's Bile/Protector's Frost
trade-tier evidence; those policies remain pending.

### Generation publication storage

`uv run --offline python -m pricing.knowledge.publication --store <directory>`
stages the index and indexed sources plus current runtime rules/profiles/metadata.
It checks byte/index consistency before atomically selecting a generation. The Python
API additionally accepts a semantic validation callback; failed validation preserves
the prior pointer. `current_generation` verifies hashes and returns a stable directory
handle. Generation cleanup is deliberately separate maintenance work.

`published_runtime.retrieve_published(extraction, bundle)` appraises
against one validated PublishedGeneration. Its context pins artifact bytes, definitions
and native metadata, rejects absent runtime inputs and never falls back to working-tree
artifacts. Base metadata indexes are keyed by metadata generation. It uses the existing
pipeline once and adds publication_generation to the structured result. The lower-level
published_snapshot context also supports decoding a capture with the bundle metadata.
The worker now selects the default publication store unless --database is explicit.
Semantic publication gates run before promotion and on cold runtime loading; these
checks alone do not prove research coverage or correctness.

### Cached publication repository

`PublicationRepository(store).load()` returns a cached LoadedRuntime plus explicit
update issues. Warm loads read the small pointer and stat the retained index; artifact
bytes and parsed definitions/metadata are reused. Only runtime inputs are retained,
not copied market/source documents already served by SQLite. A malformed or missing
new publication retains the last valid runtime, provided its index file is unchanged.
No initial generation or a changed/deleted retained index returns unavailable.
Restoring the valid pointer clears update issues. Profile validation uses an isolated
repository so malformed profiles cannot inherit a different generation's cache.
The worker uses this provider by default; explicit --database retains legacy/test operation.

The host worker can select this provider with `serve --publication-store <directory>`.
It warms the bundle before ready, pins one generation/date per request and propagates
that context through capture, executor work, cached completion and hover checks.
Generation/date/update diagnostics participate in cache keys. A changed index after
capture is rejected before retrieval. The default store is pricing/data/generations;
--publication-store overrides it, and --database explicitly selects legacy/test mode.

### Semantic publication validation

The publication CLI validates the staged runtime before selecting it. The runtime
loader repeats these checks on a newly selected generation. Decoder identities,
affixes, pools, staffmods, rare names and superior definitions must equal their
compiled definition counterparts, not merely share source fingerprints. Named-tier
policies require valid tiers/predicates/native stat IDs and matching bundled evidence
hashes/identity locators. Reviewed profiles validate in isolation; projection, base,
recipe and leveling loaders check their supported schemas, and generic leveling
requires its reviewed source fingerprint.

These checks establish supported input consistency, not complete research coverage.
Upgrade target/defense metadata is also checked against the bundled base catalog. The low-level publish API still allows a caller-
provided validator for non-appraisal bundles; the appraisal CLI uses load_runtime.

### Bundled profile source evidence

Runtime publication includes every source path referenced by its reviewed profile
document (currently26 files for249 profiles). Paths must stay inside the repository.
The runtime discovers dependencies from the bundle's own profile bytes, never the
working-tree profile document. Shared compiler/publication validation checks each
recorded SHA-256 and JSON pointer against pinned source bytes. Missing, changed or
invalid source evidence rejects publication/loading; warm retained runtimes do not
re-read source files. Older publications lacking these dependencies need republishing.

### Upgrade metadata consistency

Publication reconstructs named unique/set upgrade variants from the bundled base
catalog and checks the complete variant maps. Only mutually agreeing ascending
normal/exceptional/elite chains are eligible. Defense intervals must match the
target base when a base-defense interval applies; missing and extra targets reject
the bundle. The metadata builder and validator share the pure named_upgrades
calculation, while publication translates the independent catalog into its inputs.
Conflicting catalog entries reject validation. This does not change upgrade recipe
availability, wearer requirements or price policies.

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

### Original ethereal Duriel's Shell tier — 2026-09-25

Reviewed four independent SC/NL/PC/RotW seller asks from the authorized six-item
batch (fetched2026-09-24). Explicit Exceptional base and ethereal flag,183/190/196/197
ED: asks1Ist,2Pul,1Gul-or2Ist,1Vex-or2Ist. A bounded183–197ED original Cuirass segment
now receives qualitative med, representing its central asking segment and including
a lower-priced observation. This is not an ED-to-price curve or numeric quote.
Unreported listing sockets still prohibit exact numerical comparisons.

Runtime policy requires original base, ethereal,183–197ED and empty socket contents.
Missing facets stay conditional; nonethereal, upgraded, filled and outside-span
items remain pending. Evidence with source file hashes, row locators, raw asks,
seller IDs and scope is in appraisal-named-tier-research.json. Existing references
to that document were updated to its new fingerprint; their underlying rows did
not change. Coverage93/565 reviewed,2research-only,470missing,0invalidsources.
This leaves the other thin mercenary segments and most named-item research incomplete.

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

### Hydra Standard fire-facet demand — 2026-09-25

Added the first reviewed Hydra Sorceress role from cached Standard-variant prose.
It accepts unique fire Rainbow Facets with native fire skill damage and fire pierce
in the3–5 range;5/5 rolls are preferences, not minimum usefulness. It keeps socket
recipient,105% total FCR and survivability conditional. Wrong elements, impossible
rolls and known missing fire bonuses fail; incomplete capture remains unknown.
Proc-on-death versus proc-on-level-up is not assigned a preference by this source.

The reviewed excerpt is recorded in appraisal-reviewed-guide-excerpts.json with
the cached HTML fingerprint, source date, section and short exact quotes. The new
per-build rule is roles/hydra-sorceress.json. This adds demand, not a qualitative
market tier or numerical quote. Broad equipment-table magic/rare mentions were
not promoted into slot-level thresholds. Profile coverage is now250 reviewed
rules; many build variants and named-item price policies remain incomplete.

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

### Market-supported named tiers — 2026-09-25

When a unique/set tier is pending, the pipeline can derive a current-variant tier
from an already approved exact ask band. This uses WP-I's dated Ist boundaries:
trash below0.2, low from0.2, med from0.8, high from2.5 (including the HR band).
A band crossing boundaries remains conditional and lists the possible tiers.
Existing reviewed policies, including conditional policies, retain precedence.

Only the observed current-item request with the named contract and verified
SC/NL/PC/RotW price estimate is eligible. The existing minimum-seller, freshness,
dispersion and variant checks remain authoritative. Prepared or other-role
comparisons cannot supply this fallback. No price is synthesized; missing prices
leave the tier pending. A trash trade band does not suppress leveling/build roles.

These runtime results have status market_supported and retain ask dates, band,
seller count and threshold provenance. They do not fill the reviewed default-tier
catalog or increase its coverage count. The complete catalog remains required.

### Socket-outcome asks — 2026-09-25

Unsocketed normal/superior bases with a complete exact contract can request
comparisons for an empty Larzuk outcome when the reviewed socket mechanic gives
one certain count without an item-level condition. The request retains the
preparation action, resources and source information. Normal-quality bases also
receive cube outcome requests when at least one reviewed socket cap can produce
the required count. All cap-dependent success weights remain attached, including
zero-chance caps when item level is unknown. Base properties, ethereal
state and quality are unchanged; it does not assume creation of a runeword.

Prepared requests retain an unavailable current price. Their independently gated
market evidence is exposed as outcome_comparisons/outcome_ask_estimate, never
selected for the root price or named-item tier. Reports show an After Larzuk ask
band only when existing scope, exact-roll, seller and freshness gates pass; the
quest cost and observation dates are included. Queries reuse the current base's
cached rows; there is no live lookup. Unannotated prepared requests remain skipped.

Reports label cube quotes "If cube gives N empty sockets", followed by each
cap-dependent probability and the consumed recipe ingredients. A quoted successful
outcome is not an expected value or guaranteed current-item value. Superior and
low-quality items never use this ordinary cube transformation. Recipe rows123–126
in the pinned d2data cubemain specify useitem and socket rolls1–6.

Low-quality normalization and upgrades still need transformation-specific
contracts. Item-level-dependent Larzuk can quote a conditional successful outcome.
No estimated profit or completed-runeword price is inferred.

### Clearing known fillers from equipment — 2026-09-25

Normal/superior bases, magic/rare/crafted equipment and unique/set equipment
with a valid current contract can compare the empty result of the Hel/Scroll of Town Portal recipe. The bounded socket-effect
checker must prove every inserted identity and effect. Only changed filler stats
are subtracted from the outcome properties; zero residuals are removed and valid
inherent resistance rolls are preserved. Base defense, ethereal state, quality
and socket count remain unchanged. Captured facts and the current contract retain
their original total stats and contents.

The prepared request carries the consumed recipe resources and every destroyed
filler. Presentation labels the quote After clearing and lists destroyed contents
with multiplicity. Partial occupancy is allowed only when occupied/empty counts
and identities agree. Unknown jewels, unsupported effects, inconsistent counts,
unexplained totals and completed runewords cannot use this transformation.
Named outcomes retain exact table/base identity and roll bounds. Their fixed
property evidence is rebuilt from the contribution-adjusted view, so a Shako
regains its intrinsic50MF comparison rule after removing a Topaz. Magic/rare/
crafted outcomes retain the residual affix roll. These outcome contracts do not
change the current item tier or price. Completed runewords remain excluded.

### Explicit item-level socket mechanics — 2026-09-25

ItemFacts accepts optional item_level from extraction.item, normalized to an
integer1–99; booleans, floats, strings and out-of-range values remain unknown.
Known levels choose the reviewed <=25 /26–40 /41+ socket cap before generating
Larzuk and cube actions. This removes the item-level precondition and narrows
probabilities to the actual cap. A valid deterministic Larzuk outcome can then
request its independent empty-base comparison. If every action is impossible,
the base is reported as cannot prepare this base.

Low-quality normalization resets the derived item level to1; the observed facts
remain unchanged. Missing levels retain all cap alternatives. The current native
capture does not supply item_level, so automatic capture still follows the unknown
path; no character level, required level or drop location is substituted. Missing
optional levels remain omitted from the legacy facts dictionary.

### Conditional Larzuk references — 2026-09-25

When the item level is unknown, a Larzuk target with at least one feasible cap can
receive a prepared-outcome comparison. Reports say "If Larzuk gives N empty
sockets", list every possible count and require confirmation of the socket cap
before spending the reward. They assign no probability to unknown item levels.
Known deterministic results keep the After Larzuk wording. Impossible target
counts still receive no comparison, and root current prices remain separate.

Native item-level extraction remains unverified. The local legacy D2MOO layout
places it at0x2C, but verified D2R identity/affix offsets differ; MapAssist's local
D2R struct does not identify an item-level field. Sample saved metadata headers
do not establish a reliable alternative. No offset inference was added.

### Quest sockets for named and affixed equipment — 2026-09-25

quality_sockets uses portable base/type socket caps and the reviewed quality
rule from pinned D2MOO SUnitNpc.cpp2273–2291. Unsocketed rare/crafted/unique/set
equipment receives a one-socket outcome. Magic equipment rolls uniformly from1
to min(base/type cap,2); separate requests retain each outcome and its chance.
Known item level selects its cap; unknown levels preserve cap alternatives.
Non-socketable bases, existing sockets and incomplete contracts are excluded.

Prepared contracts retain quality, identity, ethereal state, defense, affixes and
intrinsic properties. Their asks remain separate from current-item prices. Magic
quotes explicitly show random quest chances and the consumed reward, rather than
mislabeling randomness as unknown item level. No cube socket recipe is offered
for these qualities.

The cached mercenary tier audit is recorded in appraisal-mercenary-tier-review.json
with raw source hashes/locators. Missing explicit ethereal/base fields and
inconsistent property inputs leave the three additional default tiers pending;
the audit adds no pricing policy or current numeric estimate.

### Typed comparison results — 2026-09-25

ComparisonResult owns each grouped request's identity, role references, observed/
prepared state, comparison evidence, current estimate and optional prepared-outcome
estimate. Construction detaches and freezes nested containers, including seller
rows and preparation resources. evaluate_request_results and compare_request_results
return tuples of these immutable objects. Existing dictionary APIs project through
adapters.comparisons for compatibility.

The pipeline selects its main price using ComparisonResult.is_current, then uses
a detached mutable report projection. Prepared outcomes cannot become the main
price via report mutation. Market policy, cohort matching and report wording are
unchanged. Nested evidence remains frozen mappings; a complete typed post-market
assessment object and typed price-policy details remain future migration work.

### Upgraded-weapon outcome quotes — 2026-09-25

Complete unique/set/rare weapon contracts can now compare each verified upgrade
path as a separate prepared outcome. Named identities remain unchanged with the
target base code/tier; rare contracts use the target base name. Modifiers,
ethereal state and sockets/contents remain exact. Each path carries its ordered
recipes, cumulative consumed resources and wearer-requirement precondition.

Only scoped listings for that target variant can supply its quote. Reports label
it After upgrading to the target base, include costs and require checking new
strength/dexterity/level requirements. No profit or rune-cost-to-value conversion
is made. Current prices and named tiers remain independent. Incomplete source
contracts cannot acquire an upgrade price; armor outcomes remain unquoted because
base defense can reroll and requires a separate outcome model.

### Combined priced assessment — 2026-09-25

PricedAssessment holds the finalized AssessmentResult, immutable comparison
results, selected current comparison evidence and price estimate. Pure
finalize_assessment resolves the current-item market-tier fallback and diagnostic
notes without changing the initial assessment or comparison inputs. Missing
contracts use unavailable-price diagnostics; prepared quotes stay independent.

The pipeline now projects this complete result through adapters.priced after
evaluation. Tier policy accepts a small typed comparison view without serializing
seller traces. The report remains the existing JSON shape. Snapshot provenance,
build roles and preparation evidence remain attached to the finalized assessment.
Nested tier/price-policy details are still frozen mappings; their further typing
and incomplete market/build coverage are separate remaining work.

### Armor upgrade defense outcomes — 2026-09-25

Verified non-ethereal named armor upgrade paths now include `defense_outcome`:
target base bounds, preserved enhanced/flat defense, and the finite set of possible
totals. The target base rolls within its normal range; it does not inherit the
original item's max-plus-one generation rule. Integer rounding is applied before
fixed added defense. Guardian Angel at 187% ED can produce 1208–1521 defense in a
Hellforge Plate; Sazabi's fixed +100 defense produces 210–254 in a Giant Conch.

This structured evidence requires a complete current contract. Unknown sockets,
ethereal outcomes, and variable/per-level added defense remain unmodeled. Current
stats and prices remain unchanged. Armor upgrade market requests are still pending:
they must retain distinct possible defense outcomes rather than reuse current
defense or pool all upgraded listings into one exact comparison.

### Exact armor-upgrade outcome quotes — 2026-09-25

Named armor with a verified finite defense model now emits a separate prepared
comparison for each reachable target defense. The target code/tier and defense
change; identity, other rolls, ethereal state, sockets and payload stay fixed.
Each cohort still requires three independent scoped sellers and passes the normal
age/dispersion gates. The repository reads each item's cached listings once.

Reports say `If upgrading to Giant Conch rolls 254 defense`, give the possible
defense range and recipe cost, and require checking wearer requirements. They
do not present this as a guaranteed result, expected profit, or the current
item's price. Unsupported armor outcomes remain unpriced; no matching listing
is not evidence that an upgrade is worthless.

### Demand-prioritized named market review — 2026-09-25

`python -m pricing.knowledge.assessment.maintenance.coverage --as-of 2026-09-25`
now joins named policies, build/leveling occurrences and cached market readiness.
Schema3 includes a review_queue ranked by recommended build occurrences, leveling
recommendations, then structurally ready rows. Per-item market details retain
missing facets and example listing locators. Actions distinguish absent scoped
evidence, incomplete listing facets, exact-comparison review and broken sources.

Ready is structural only, never proof of a price or tier. Unknown market audit
is distinct from an audited empty cache. Existing reviewed policy counts retain
their meaning; no new tiers are assigned by this maintenance report. The current
queue is saved at pricing/data/appraisal-named-review-queue.json.

### Fixed named charged skills — 2026-09-25

NamedHandler now verifies charged skills declared in the item definition before
forming a price contract. ITEMMODS_PropertyFunc19 fixes positive max as skill
level and min as capacity (including its zero/negative capacity formulas and
255 cap). Captured packed identity, raw charge payload, decoded remaining uses
and maximum must agree. Missing or changed charges block the contract.

Cached charge property labels represent skill level, not remaining uses. Verified
fixed levels are intrinsic named properties: a listing may omit them but cannot
contradict them. Remaining uses on non-ethereal rechargeable items do not change
the skill roll, just as ordinary repairable durability does not change a roll.
Ethereal charge depletion requires listing-side evidence and remains excluded.

Variable magic/rare charge comparisons remain unsupported. Dire Song has level7
Nova with47/56charges; the cached generic Nova field450 carries skill level and
a format template, not trustworthy per-item remaining/capacity evidence. Never
project its47 remaining uses as level47 or discard its capacity distinction.

### Completed runeword charges — 2026-09-25

The definition compiler now records `charged_skills` for every completed recipe,
including an explicit empty list when the recipe has none. All21 charged recipes
resolve native skill parameters against the pinned skills table and verify
PropertyFunc19. Unsupported dynamic levels or unknown skills fail compilation.

RunewordHandler applies the same captured-payload validation as named items.
Harmony's level20 Revive with25charge capacity becomes an intrinsic skill-level
market property, never its remaining-use count. Contradictory listing levels
are rejected; other rolled properties and base/socket restrictions still apply.
Missing charge records block a contract even if generic projection gaps are
absent. Older runeword definition bundles lacking the reviewed declaration
require an offline rebuild. Ethereal charge depletion still requires listing-side
evidence; this change does not assume those charges can be replenished.

### Fixed physical rune entries — 2026-09-25

Rune compilation now retains the fixed physical damage entries produced by
PropertyFunc05/06: Sol's minimum and Ith's maximum modifier. These native159/160
entries are retained separately from actual weapon damage and elemental effects.
For a complete nonthrowing runeword weapon capture, exact raw/decoded equality
with the summed fixed rune contributions resolves the redundant stat's market
projection gap. Changed values, incomplete captures and throwing bases remain
unresolved. This does not assign a scalar market price to total weapon damage.

The saved Insight Bill's159:0=9 is now explained by Sol, while its absent17/18
enhanced-damage evidence still prevents an estimate. Do not derive230ED from
the user's screenshot or damage totals to fill the capture. A test with explicit
ED evidence verifies that this independent barrier can be removed when captured.

### Owned weapon ED replay and superior-base gate — 2026-09-25

Saved replay now derives both weapon ED and enhanced defense from verified owned
modifier chains, matching the live capture checks. A precomputed damage_modifiers
copy is not required when complete ownership evidence is available. Wrong-owner
chains remain rejected. Saved Insight has no owned ED record and stays unpriced.

Superior weapon base contracts now require native17/18 coverage, as affixed
weapon contracts already did. A capture missing owned ED must not be compared
as an attack-rating-only or lower-roll base. This does not infer zero ED from
absence: legitimate superior weapons with no ED bonus still need explicit
coverage evidence before that absence can be treated as zero. Build utility
remains separate from whether a price contract can be formed.

### Selected superior-quality identity — 2026-09-25

Superior metadata retains the individual qualityitems rows as `patterns`. The
revalidated ItemData file index at0x34 identifies the selected row; the saved
Phase Blade carries row3 (AR+ED), matching its captured rolls. Pinned
ItemsMagic.cpp968–998 selects and applies exactly one row. Decoder source
evidence now retains the selected index/category when its quality and flags
agree, without changing the item title or inventing native stats.

For empty superior weapon bases, AR-only, durability-only and AR+durability
rows can prove no ED when their required native rolls match the definition.
Unknown indices, out-of-range rolls and an ED-bearing row with missing ED stay
unpriced. The comparison contract requires explicit ED0 from listings; missing
listing ED is not interpreted as zero. Native75 durability percentage is now
projected to the reviewed cached numeric field937 and remains an exact roll.
The facts retain absent17/18 rather than synthesizing observed zero values.

### Superior armor enhancement coverage — 2026-09-25

Superior armor, helmets, shields and accessories require captured native16
enhanced-defense coverage, or a verified selected durability-only pattern proving
no enhancement. That latter contract requires explicit market425=0, alongside
total defense and the actual durability roll. Missing listing enhancement is
not zero. Normal and affixed armor retain their existing separate policies.

When selected-quality identity is available, base contracts now validate every
declared modifier (AR, durability, enhanced damage or enhanced defense) against
its native integer range and raw value. Missing secondary bonuses and invalid
rows block comparison. Verified socket contributions are subtracted before
checking standalone quality rolls. Base/affixed contracts also retain base_code,
so conflicting or absent listing base codes cannot silently match by title alone.

Superior weapon enhanced damage must also agree between native17 and18: the
quality property writes one rolled value to both fields (primary ItemMods.cpp
PropertyFunc07). Independently in-range but unequal values block pricing.

### Superior flat-damage fallback — 2026-09-25

Primary PropertyFunc07 substitutes +1 maximum damage when superior ED would add
zero damage. Complete identified, nonethereal empty bases can now compare that
variant using explicit market510=0 and448=1. Captured damage endpoints must match
the catalog's physical modes with exactly +1 to each maximum. No percentage roll
is invented. A selected quality row must declare dmg%, with all other bonuses
validated as before.

If every possible selected ED roll rounds to zero, that row and matching totals
prove the fallback. Otherwise matching totals are ambiguous: the decoder must
supply owned +1 maximum modifier evidence from a complete, stable, owner-validated
0xD0 chain containing no17/18 percent entries. Missing, duplicate, changed-owner,
unstable or percent-bearing chains cannot provide that evidence. Native facts
remain physical totals; derived comparison fields are separate. Ethereal,
throwing and filled-socket fallback variants still require further mechanics.

### Magic and rare charged skills — 2026-09-25

Affixed contracts now compare verified rechargeable charges by skill level,
using the same reviewed scalar charge fields as named items. Remaining uses stay
in native facts and the report; they are never projected as skill level. A charge
can be the only comparable affix, including Teleportation amulets.

Eligibility comes from the bundled prefix/suffix/automod definitions for the
actual base and rarity. Native PropertyFunc19 formulas enumerate possible skill
levels over item levels1–99; captured level must be possible and must imply one
capacity across all eligible definitions. Capacity is checked against packed raw
charges, decoded remaining/maximum counts and units. Ambiguous capacities,
unmapped skills, conflicting projections and ethereal depletion block pricing.
All eligible tiers are considered; the capture's affix identity never supplies
missing listing capacity where another eligible affix could produce it.

Skill metadata now retains required/max skill levels from the pinned skills
export. Rebuild item metadata and publish before using this policy with an older
bundle. Existing weapon, socket, identity and modifier coverage gates still apply.

### Farming mercenary helmets — 2026-09-25

Seven explicit variant helmet roles extend reviewed build coverage to257:
Stealskull for Hammer/Blizzard/Meteor Magic Find mercenaries, and Crown of Thieves
for Gold Find Barbarian Standard/War Cry/Whirlwind/Leap Only. Each preserves its
Ist/Lem payload and mercenary type; ethereal is preferred rather than a universal
price multiplier. Definition-minimum life leech and farming bonuses establish
functionality, with IAS also required for Stealskull. Crown's cited Corona upgrade
is a separate dependency, so a Grand Crown remains a usable candidate without
being reported as the exact upgraded setup. Full equipment/attack-speed/survival
conditions remain unresolved until the loadout is supplied. These source-specific
roles do not establish new trade tiers or numerical prices.

### Verified required socket items — 2026-09-25

Role requirements for a specific rune or named socket item now require a filled
state and known, consistent total/occupied counts before a matching child name
satisfies the setup. Contradictory zero/empty/overfull captures and unknown counts
remain missing setup evidence. A positively identified required child can still
satisfy this presence requirement when unrelated child identities are incomplete,
provided occupancy itself is known. This does not prove the entire payload or
relax pricing contracts' complete-content comparisons.

### All-item market readiness audit — 2026-09-25

`uv run --offline python -m pricing.knowledge.assessment.maintenance.market_readiness --all-items --as-of 2026-09-25`
adds base, affixed (magic/rare/crafted), runeword and unclassified equipment cohorts
to the named audit. It preserves supersession/scope/date checks and reports
per-policy scoped observation and structurally-ready counts. Currency categories
are excluded. Missing or category-conflicting rarity is a gap. Runewords require
known base quality and filled sockets; recipe contents do not need the ordinary
named-item filler-description field. Modifier/recipe/base equivalence and price
cohorts still require runtime contracts; this audit never grants an estimate.

The dated snapshot in appraisal-all-market-readiness.json contains168 structurally
ready observations:17affixed,20base,1named,130runeword. These are observations, not
independent sellers or priced variants. Major gaps are undated legacy observations,
unknown ethereal/socket facets, and runeword base quality. A preliminary empty-item
scan found no three-seller group differing only in one numeric modifier, so no
secondary-roll band or tolerance was approved from that evidence.

### Crafted catalog normalization — 2026-09-25

Market normalization now verifies crafted catalog ID/name pairs before supplying
crafted rarity. Conflicting explicit rarity is retained as a mechanics conflict.
The eight Blood/Caster/Safety/Hit Power Ring/Amulet catalog entries normalize to
their single native jewelry base, retaining catalog_name and source hashes. Known
jewelry mechanics establish nonethereal, zero sockets and empty contents; contrary
explicit facets remain conflicts. Recipe equipment categories (e.g.Blood Gloves)
establish quality only: their normal/exceptional/elite bases are not guessed.

This lets the ordinary exact affixed contract retrieve and compare crafted
jewelry by base name/code and every declared modifier. It does not infer economy,
observation dates, omitted modifiers or a numerical price from the recipe name.

### Reconciliation discards stale variant facts — 2026-09-25

Fresh normalization and cached-row reconciliation share normalize_facets.
Reconciliation clears prior rarity, sockets, ethereal, base selectors/upgrade,
facet provenance and mechanics conflicts before rebuilding from raw properties
and verified catalog mechanics. A removed selector cannot leave a previous
runeword base eligible; repaired raw evidence does not retain an obsolete conflict.
Crafted canonical names restore the catalog recipe identity before resolving
again, making repeated import stable. Ask/conversion and observation-date evidence
remain separate and are not inferred or replaced by facet reconciliation.

### Vampire Gaze mercenary variants — 2026-09-25

Six explicit profiles extend reviewed build coverage to263. Dream Hybrid/Ubers
and Lightning Strike Standard use an Act1 Cold Rogue and require one captured
jewel combining15IAS with15to each elemental resistance; parent totals or separate
jewels cannot satisfy that socket. Lightning Fury Ubers and Lightning Sorceress
Uber Mephisto use Act5 Frenzy withUm. Lightning Strike Ubers names no filler,
so none is invented. Ethereal preferences apply where the cited setup specifies
ethereal. Definition-minimum6life leech/15physical reduction accept useful low
rolls; full mercenary equipment and survival remain conditional. The Sorceress
profile retains the guide's different Standard Infinity mercenary for other Ubers.
No trade-tier or numerical-price inference follows from these build roles.

### Crafted equipment base tiers — 2026-09-25

Definitions and bundled metadata now compile24concrete crafted armor recipe chains
from enabled cube rows using `usetype,crf` and a concrete `mag,upg` input. Each
normal/exceptional/elite member must mutually agree on the chain. The `upg` input
semantics are verified in D2Common HoradricCube.cpp and D2Game PlrTrade.cpp.
Publication validates that compiled metadata and definitions agree.

A verified crafted catalog identity plus explicit Normal/Exceptional/Elite Base
Tier selects the corresponding base name/code, retaining catalog_name and recipe
provenance. This also enables existing nonsocketable glove/boot/belt mechanics.
No tier default is supplied; invalid/unknown tiers and type-wide weapon recipes
remain unresolved. Other missing item modifiers are not inferred.

Verified standard crafting recipes resolve missing market ethereal fields to
nonethereal, including equipment whose precise base tier is still unknown.
The compiled recipe map accepts only unambiguous enabled `usetype,crf` outputs:
the cube creation path sets `ITEMDROPFLAG_NEVERETH` without an `eth` modifier.
Explicit contradictory listings retain their supplied value and a conflict.
This does not infer socket state or choose a base from a weapon family.

Dragon Talon Budget roles include Goblin Toe's Mirrored Boots preparation and the
Fire Iron Wolf's Hexfire, Ormus' Robes and transitional Lidless Wall. Fire jewel
requirements inspect the socketed child; parent stat totals do not establish the
filler. These mercenary items supply pre-fight Enchant, with the source's explicit
lack of Uber survival retained. Build usefulness does not create a trade tier.

Crafted charged-skill affixes use the same exact comparison policy as rechargeable
magic/rare affixes, with the rare-eligible suffix pool enforced. Skill level must
uniquely establish the captured maximum capacity; remaining uses may differ on
nonethereal items. Crafted rarity and all other captured modifiers still have to
match. Ethereal, ambiguous-capacity or inconsistent packed charges remain gaps.

Empty magic/rare items can compare chance-to-cast affixes when eligible native
affixes uniquely determine spell level for the observed event, skill and chance.
For example, 5% Amplify Damage on striking and 10% level-3 Nova on striking have
verified projections. Equal-chance Chain Lightning affixes at levels 3 and 5
remain ambiguous because the market field records chance alone. Independent
validation rejects malformed trigger rows even without an adapter warning.
Multiple contributing affix groups and filled socket proc
contributions remain unresolved; named/runeword trigger rules are separate.

Crafted trigger comparisons now combine verified recipe eligibility with the
rare affix pool. Compiled cube metadata enumerates concrete bases and recipe
proc effects. Hit Power rings can compare their fixed 5% level-4 Frost Nova;
amulets remain ambiguous because a random affix uses the same chance at level 3.
Recipe/affix contributions to the same event and skill remain blocked until those
combinations can be represented. Unsupported recipe/base semantics fail compilation.

Magic/rare empty weapons can compare verified fractional maximum-damage and
Attack Rating per-level coefficients using market fields 535/536. The offline
cache contains mixed total/rate conventions; only exact noninteger coefficients
are accepted, because rounded tooltip totals are integers. Native raw coefficient,
scaling, viewer level, displayed total and eligible affix must agree. A listing
with Dread Edge's 45/1501 totals does not match its 0.5/16.5 rates. Integer-valued
conventions, other per-level effects and contributions from filled sockets remain
unresolved. This resolves Dread Edge's two per-level projection gaps.


For empty magic/rare items, cold damage endpoints can establish duration when all
eligible affix combinations agree. The evaluator includes prefix/suffix groups,
quality-specific affix counts and summed endpoint/duration ranges, with bounded
combination search. It excludes zero-frequency legacy rows as the native modern
online affix roller does. Dread Edge's 1–3 cold damage proves 75 frames, matching
the captured three seconds; all its modifiers can now form an exact contract.
A 2–4 cold Small Charm can instead have 25 or 50 frames, so endpoints alone do
not establish a price comparison. No missing duration is fabricated, and crafted
or socketed cold contributions remain unsupported by this rule. Forming a contract
still requires sufficient fully matched, dated independent sellers for a price.

Poison comparisons for empty magic/rare items enumerate eligible fixed-rate
prefix/suffix combinations with normal affix-count limits. Market field589 is
accepted only when the rounded total identifies one native rate/duration tuple.
Both summed and count-averaged durations are considered to avoid conflating
source states. The capture must independently validate both rates, duration and
native count1; primary save/load code preserves summed stats and restores count1.
This supports Toxic100/5s and combined451/12s Small Charms after that verification.
50/4s and50/6s collide and remain unresolved. Crafted, socketed, ranged-rate and
automagic contributions, and captures with count greater than1 remain gaps.

### Shared affix generation gate — 2026-09-25

Charge, proc, per-level, cold and poison comparison proofs now share
`mechanics.affix_pool.can_generate`. A candidate must be spawnable on the base,
have a positive integer generation frequency, and permit the item's rarity;
rare/crafted items cannot use magic-only affixes. This follows the local
`ITEMS_RollMagicAffixesNew` reference (ItemsMagic.cpp:311–328). Missing/zero
frequency legacy rows cannot establish a current-generation comparison or create
false ambiguity with a valid charged-skill capacity/proc level. Each effect still
owns its item-level, grouping and contribution rules; the shared gate alone is
not proof that a complete affix combination is possible. Historical affix pricing
needs a separate policy rather than treating obsolete rows as current outcomes.

### Explicit legacy collection days — 2026-09-25

The offline cache importer now retains a canonical `pulled: YYYY-MM-DD` field
from a cache wrapper as day-precision observation evidence. Each normalized row
records `cache_pulled` provenance, the raw file path/hash and `/pulled` locator.
Bare listing arrays remain undated; neither filenames, filesystem times nor
listing update dates supply observation dates. Invalid collection days or listing
updates after the claimed collection day invalidate the file's date evidence and
produce a manifest diagnostic. Dated and undated copies of the same listing are
retained separately, so an alphabetically earlier bare cache cannot erase a dated
observation. Existing listing/seller deduplication and freshness rules still apply.
This restores evidence already in the cache, without refreshing its age or scope.

### Named scalar roll projection consistency — 2026-09-25

`mechanics.named_rolls.variable_projection_gaps` checks variable named bonuses
against their final market constraints. The captured projection, or the standard
layer-zero metadata mapping when it is missing, must carry the same decoded
value. This prevents a native roll such as Mara's resistance from being present
in facts but silently omitted or changed in its price contract. Structural total
defense and socket count retain their dedicated handling; compound effects and
parameterized skills still require their existing specialized proofs. This gate
does not create missing mappings or make unsupported variants comparable.

### Crafted cold comparison — 2026-09-25

`crafting_cold.crafting_affix_only_cold` compiles the concrete crafted bases whose
enabled recipes cannot contribute cold damage or duration. It shares verified
recipe-to-base resolution with the recipe proc compiler. Properties using reviewed
native scalar/armor/enhanced-damage/proc functions are checked for cold components;
unknown effects block the affected base. One incompatible recipe is enough to
block it even if another recipe for that base is safe. The definition and bundled
metadata copies are checked together on publication.

The cold comparator now accepts crafted items only with this recipe proof, using
the rare-eligible affix pool and at most four random affixes (three per side).
Cold endpoints must still establish one duration and agree with the raw capture.
Other recipe modifiers remain exact comparison properties. The current compiled
proof covers182 bases; it does not prove every cold roll or complete item price.
Crafted poison now has an analogous recipe proof; unresolved ranged poison rates remain unsupported.

### Base-specific automod groups — 2026-09-25

Definition compilation now requires both allowed item type and the base's positive
`auto prefix` group to match an automagic record. This follows ItemMode.cpp:6288–6290
and ItemsMagic.cpp:327 in the local D2MOO reference. Type compatibility alone had
assigned class-base automods to unrelated equipment, polluting tier candidates and
blocking ordinary weapon poison comparisons with impossible poison ranges.

The correction reduces compiled automod/base associations from23,012 to570 while
preserving original affix table IDs (including skipped-row gaps). Legitimate orb,
shield and head automods remain subject to their group. Ordinary rare Axe poison
now forms an exact rate/duration contract for the tested6-damage/2-second affix;
real automod contributions still require their existing dedicated handling.

### Current-generation affix tier ladders — 2026-09-25

The definition compiler's magic and rare tier pools now use the same positive
frequency, spawnability, base and rarity gate as comparison effect proofs. Old
zero/missing-frequency rows remain available as identity/range evidence but cannot
set current T1 ceilings or introduce unavailable brackets. This removes 194 such
records from tier-pool contributions. Saved Dread Edge now shows +4 Strength as T3
(T1: 10–15) and 1–3 cold damage endpoints as T3; the previous T6/T4 ranks counted legacy
brackets. Other 17 saved report texts and all 18 price results are unchanged.

The saved rare-ring decoder fixture also exposes a corrected ceiling: fire
resistance now spans 5–30%, with 21–30% at T1. The old 31–50% Ruby record has frequency 0;
it no longer makes the observed +28% look like T2. Magic-only and rare-eligible pools
remain separate, as verified by the ring mana-tier regression.

### Crafted poison comparison — 2026-09-25

Cold and poison recipe exclusion now share `crafting_elements.affix_only_bases`.
The poison compiler separately checks minimum/maximum rates, duration and source
count, publishing `crafting_affix_only_poison` in definitions and item metadata.
Publication validates both copies. Any unknown recipe effect or possible recipe
poison contribution excludes that base from this comparison policy.

The poison comparator accepts a crafted item only with this proof, rare-eligible
random affixes and at most four contributing random affixes. Its scalar market
total must still imply one exact native rate/duration combination; other recipe
properties remain mandatory. Unsupported bases, altered rates/duration, unknown
recipe evidence and genuine automod/ranged-rate ambiguity remain blocked. Current
compiled recipe proof covers182 bases, not182 guaranteed price estimates.

### Original Sunder market aliases — 2026-09-25

`market_named_aliases` maps six reviewed original Sunder catalog IDs from Traderie's
leading-"The" names to their game-definition identities. Both exact catalog ID and
original name are required, in the unique category. The raw catalog name and
reviewed identity provenance remain in normalized evidence; reconciliation resets
and revalidates the alias rather than retaining stale derived facts. This enables
existing named-charm mechanics and canonical index retrieval. Renewed/Latent
variants retain their separate identities. No generic article stripping or fuzzy
identity match was added.

### Sunder decoding and exact penalty comparisons — 2026-09-25

Native Sunder stats 187/189–193 carry magnitude 300, as verified in the local
itemstatcost, properties and uniqueitems tables. A dedicated decoder now preserves
that magnitude and renders the text-only effect; it no longer mistakes these
stats for boolean flags. Unverified magnitudes/layers remain unresolved.

`assessment.mechanics.sunder` translates positive penalty magnitudes only for the
six reviewed original market catalog identities. Definition bounds, exact rolled
values and all existing variant/scope gates remain required. Bone Break's Damage
Increased field maps to negative physical resistance; conflicting representations
are rejected. Ordinary resistances and Renewed/Latent identities are unaffected.
The adapter works on a comparison copy, preserving raw listing properties.

Verification: 27 focused regressions; full suite 2334 passed, 3 skipped. All 18
saved reports/prices unchanged. Actual cached evidence supplies 148 exact-variant
matches across the six originals (of 333 scoped observations); all are undated and
produce no published price. Details: `tmp/sunder-cached-comparisons.json`.
Python-only change: generation 63c4c059 remains selected; restart a running worker
to load the decoder/comparator changes. This does not finish named tier/build or
market coverage. No live collection performed.

### Named charm roll integrity — 2026-09-25

Comparison contracts now validate all standalone scalar definition bounds for
Annihilus, Hellfire Torch, Gheed's Fortune and the six original Sunders, including
fixed bonuses. Previously Annihilus +21 Strength, Gheed's 16% vendor reduction,
and out-of-range Sunder penalties could form contracts. The shared all-attributes
and all-resistances properties also require equal component values; legal values
inside each individual interval are insufficient if the components disagree.

Source proof: local properties.json all-stats/res-all use func1=1 followed by
func3=3; D2MOO ItemMods.cpp ITEMMODS_PropertyFunc03 reuses nValue. This rule is
limited to reviewed standalone charms; it does not collapse independent elemental
rolls or apply original-charm assumptions to Renewed variants. Torch class/proc/
charge checks remain independently required.

Red: 10 failures reproduced in tmp/named-charm-rolls-red.log. Green: 14 new cases,
48 focused tests, full suite 2348 passed/3 skipped. All 18 saved text/price outputs
unchanged; staged and published replays agree. Ruff/format/diff checks pass.
Python-only change; generation 63c4c059 remains selected. Restart the worker for
these code changes. Full build/tier/price coverage remains incomplete.

### Named required-level comparisons — 2026-09-25

ComparableContract now carries optional verified required_level. Named original
bases with empty sockets derive it from max(named definition, base requirement,
class-specific skill requirements). Oskills are only accepted when even their
+6 off-class requirement cannot raise the shared baseline. Missing skill metadata,
filled/unknown sockets, upgrades, native item_levelreq/item_levelreqpct adjustments
and incomplete captures produce no proof. Source: D2MOO Items.cpp
ITEMS_GetRequiredLevel plus bundled game/base/skill definitions.

Traderie property796 is Required Level. Comparisons consume it as an envelope
field only when it exactly matches the proven integer level. Missing listing
level is harmless for this proven fixed property; conflicting/unverified levels
remain rejection reasons. The raw row is not modified. No general property ignore
or price/roll tolerance was introduced.

Red: one new positive listing regression failed before implementation; 14 focused
cases now pass. Full suite:2362 passed/3 skipped. All18 saved reports/prices
unchanged, with staged/published agreement. Ruff/format/diff checks passed.
Actual cached Gheed comparison observations increased79→85 of95 scoped, retaining
all three variable rolls. No cohort reaches the current dated three-seller gate;
no new numerical price claimed. Details:tmp/named-required-level-gheed.json.
Python-only change; generation63c4c059 remains selected. Restart a running worker
for the new contract/requirement comparator. No live collection this turn.

### Fissure endgame mercenary roles — 2026-09-25

Four source-specific profiles cover Standard/Magic Find Fortitude armor, Ubers
Chains of Honor armor and Ubers Flickering Flame helm. Each requires the completed
recipe and socket count, the Druid context and mercenary companion dependencies.
The Ubers pair retains Infinity plus its partner: Chains of Honor provides life
leech alongside Flickering Flame's Resist Fire aura. Standard/Magic Find retain
both Act2 Might prose and Holy Freeze planner alternatives; Ubers requires Might.
Ethereal examples supply preferences, not mandatory gates or price multipliers.
Weapon Fortitude and class-specific helms are excluded from these equipment roles.
Wearer requirements/full-loadout survival remain conditional.

Source: wp-a-builds.json /fissure-druid/variants/1, /2 and /3; exact quotes and hash
retained. Red5 failures before rules; green6 focused cases. Full2368 passed/3 skipped.
Reviewed profiles273→277; source census related links807→815, direct links249→253.
All18 saved reports/prices unchanged. Broad build/variant and named-tier coverage
remains incomplete; these utility rules do not establish numerical trade values.

### Fissure Andariel mercenary roles — 2026-09-25

Two reviewed candidate profiles cover the Standard and Magic Find Andariel's
Visage setups. Both preserve Druid context, Act2 Might/Holy Freeze source conflict,
Infinity/Fortitude companions, ethereal preference, variable leech/strength/defense
importance and full-loadout survival requirements. An unsocketed helmet remains a
candidate with an unmet preparation dependency.

Standard keeps the planner's15IAS/40ED jewel target. Magic Find uses the prose
Ruby Jewel of Fervor with the planner's damage-prefix disambiguation: local
magicprefix198 dmg%31–40, not magicprefix376 res-fire16–30; magicsuffix171 IAS15.
The dependency requires IAS plus both damage components on the same actual jewel.
Upper bounds reject ED>40/IAS>15; names, parent totals, split children and incomplete
socket capture cannot prove the requirement. No trade price inferred from fit.

Red10 missing-rule cases, then one failing upper-bound regression; green11 cases.
Full suite2379 passed/3 skipped; all18 saved reports/prices unchanged. Reviewed
profiles277→279; related source links815→819; direct links253→255. Rebuilt coverage
and published46-artifact generation
bf2c747a8e8af9a508bb910f9540b516834f07443d5188fe9c7eabc5e91aac56.
Logs/replays:tmp/fissure-andariel-*. No live calls. Rule-only publication is selected
at the next worker request; earlier Python updates still require a restart.

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

### Fissure magic pelts — 2026-09-25

Standard and Magic Find profiles accept magic Druid pelts with +3 Elemental Skills
and +3 Fissure. They retain variant source locators and exclude other skill tabs,
non-pelts and ethereal player equipment from this documented setup. Dream Spirit
is the planner's base choice; Antlers and other pelt bases can satisfy the skill
role. Standard +3 Hurricane and +3 Summon Grizzly are separate preferences, not
mandatory properties or numerical price multipliers.

The socket setup requires two filled sockets, Defender's Fire by captured child
identity, and a named Rainbow Facet child with both native fire bonus and enemy
fire-resistance reduction in the 3–5 range. Parent totals, cold facets, child names
without stats and contradictory socket occupancy do not establish the payload.
`socket_jewel_matches` supports an optional exact child name in addition to its
existing conjunction of native stat thresholds. An unsocketed core pelt remains a
candidate; the report identifies the two-socket Larzuk outcome as preparation,
not a guaranteed upgrade. Existing exact affixed comparable and socket-outcome
policies continue to govern prices independently of this build match.

### Fissure player helmet alternatives — 2026-09-25

Four further profiles cover Starter Lore (+3 Fissure pelt), Standard Flickering
Flame, and Standard/Ubers Ravenlore. Completed runeword identity, socket count,
filled state, normal/superior quality and nonethereal player use are explicit.
Lore allows other pelt bases besides the planner's Antlers. Flickering Flame
allows generic helmets/circlets and Druid pelts; Barbarian class helms are excluded
using the local item-type class restriction. Its prose says “ideal Base” without
quantifying staffmods, so the rule does not invent a best-base threshold.

Ravenlore's Fire Rainbow Facet dependency belongs only to Ubers. The Standard
alternative does not inherit it. Important native rolls include fire pierce,
resistances and energy; Flickering Flame also records Resist Fire aura and mana.
Existing named/runeword comparison policies still determine numeric estimates.
The Hardcore planner's older helmet mentions remain outside this source-specific
SC rollout. Coverage285 profiles; broad build and named-tier coverage remains open.

### Intrinsic socketed Ravenlore tier — 2026-09-25

Ravenlore's reviewed native fire-pierce tier can now use a complete parent capture
and complete linked jewel payloads. Native333 is an unscaled additive scalar
(op0, shift0 in item metadata). The helper subtracts each captured jewel's fire
pierce from the parent total, evaluates the existing10–20 bounds and perfect20
rule on a private facts copy, and retains observed/socket/intrinsic evidence.
The report labels the result “before socket additions.” Market comparison facts,
properties and numerical estimates retain the original socketed item.

This was initially enabled for Ravenlore's333:0 policy. Unknown/conflicting
occupancy, missing child identities, incomplete or unreadable jewel stats and
unverified fixed socket definitions remain pending. Complete jewel absence of333 means
zero contribution. Do not generalize this subtraction to armor defense, weapon
damage or other compound/scaled effects.

The same reviewed mechanism now covers Griffon's Eye (330/334 lightning bonuses),
Death's Fathom (331 cold skill damage), and Nightwing's Veil (331 plus dexterity2).
All five supported native stats have op0/shift0/no parameter in the local metadata.
Every stat used by an enabled tier's validity or override predicates must be listed
for adjustment; policy validation rejects partial coverage. Existing intrinsic
ranges, thresholds and ethereal restrictions remain in force. Jewel additions do
not create a perfect native roll, and the tier still excludes the jewel's value.

### Intrinsic roll display — 2026-09-25

Named tier results now carry the definition bounds alongside their intrinsic
socket-roll evidence. Shared plain/Rich/OSD presentation keeps captured values
and native stats intact, but ranks verified intrinsic values for perfect/low colors.
For example: `-25% to Enemy Fire Resistance — item roll: 20 (10-20), sockets: +5`.
A total20 made from native15 plus jewel5 is no longer displayed as perfect20.

Filled unique/set scalar lines lose unverified total-based range/color annotations
when no intrinsic proof is available. Independently verified base defense retains
its range: the decoder's `unmodified non-ethereal base defense` scope means the
owned and total defense arrays agree. This preserves the saved Um-socketed Shako's
98–141 range. Presentation uses copied rows and result-carried bounds, without
reloading definitions from a different generation or changing appraisal facts.

### Fixed rune/gem contributions — 2026-09-25

Bundled item metadata now includes recipient-specific contributions from all68
cached gems.json definitions for the reviewed intrinsic scalar set (dexterity and
cold/lightning skill damage/fire-lightning pierce). Maintenance compiles effects
from gems/properties/stat metadata. Unknown property functions, variable or
parameterized target effects fail the build; they cannot become assumed zeros.
Known implicit physical-damage and indestructibility functions do not affect this
scalar set. Existing definition-input hashes cover the gems/properties sources.

Runtime uses the captured child code/name/type together and the recipient's
verified base code/type and gemapplytype. A Ko rune or Perfect Emerald adds10
dexterity in a helmet; the emerald contributes zero dexterity in a weapon/shield.
An Um rune contributes zero fire pierce. Fixed effects do not require a child
native stat array (rune/gem effects are applied to the recipient); jewel effects
still require complete child stats. Identity conflicts remain unresolved.
No new numeric market prices are inferred from these contribution proofs.

### Fixed dexterity socket comparisons — 2026-09-25

Exact comparison payloads now support Ko (+10 dexterity in equipment) and all
five emerald grades in helmets/body armor (+3/+4/+6/+8/+10). These recipient
rules are checked against the pinned gems/properties/stat definitions by the
socket-effects source test. Emerald weapon/shield effects are not dexterity and
are not enabled by this change.

The named handler validates the intrinsic dexterity against the definition after
subtracting the fixed contribution, while its contract keeps the captured total
and exact socket payload. Thus Ko and Perfect Emerald cannot be merged despite
the same +10 bonus. Existing linkage, occupancy, raw/value/projection consistency,
seller/date/scope and complete-property gates remain active. Base, magic/rare and
set paths share these fixed effects. Synthetic cohorts exercise the three-seller
estimate gate; no fresh listing or market price is asserted by these tests.

### Remaining attribute socket comparisons — 2026-09-25

A shared attribute-rune table now covers Fal strength10, Lum energy10, Ko dexterity10
and Io vitality10 across armor/helm/shield/weapon recipients. Amethyst grades add
3/4/6/8/10 strength only in helmet/body-armor comparisons. Their weapon attack-rating
and shield-defense effects are separate and are not enabled by this change.

The existing source test checks each effect against pinned gems/properties/stat
rows. D2StatList.cpp op8/op9 applies energy/vitality-derived mana/life only when the
owner is UNIT_PLAYER; item comparison retains the direct native attribute bonus.
Named tests cover Fal/amethyst Guillaume's Face, Lum Kira's Guardian and Io
Rockstopper, including coherent but impossible intrinsic totals. Base/magic/rare
cases retain the exact filler and observed stats. Existing seller/scope/date and
socket linkage gates continue to apply; these rules add no market observations.

### Compiled comparison fillers — 2026-09-25

Fixed filler amounts now come from metadata `comparison_socket_effects`, compiled
by `maintenance/comparison_fillers.py` from pinned game tables. The recipient/name
whitelist remains explicitly reviewed; adding an unreviewed function, variable
value, parameterized or empty property fails compilation. Runtime uses the
request-pinned bundle, including an empty result when the bundle is absent.
The 30 helm, 30 armor, 18 shield and 9 weapon entries preserve the previous exact
effects and comparison contracts; this change adds no listings or pricing claims.

### Fissure named gloves and boots — 2026-09-25

Five reviewed roles cover Magefist in Standard/Magic Find/Ubers and War Traveler
in Standard/Magic Find. Cached variant slot entries provide direct source
locators. The roles require identified nonethereal unique items on their actual
base/upgrade chains and Druid context. Standard/Magic Find accept original or
upgraded bases without inventing roll thresholds; Ubers retains the documented
Crusader Gauntlets destination as an actionable upgrade dependency. Requirements
and full-loadout fit remain conditional. Trade tiers and numerical prices are
unchanged by these demand rules.

### Ist-filled shield comparisons — 2026-09-25

Reviewed fixed shield fillers now include Ist:25 magic find per rune, compiled
from the shield column of gems.json (weapon bonus30 remains distinct). Base,
magic/rare, unique and set shield contracts preserve captured total magic find
and exact rune multiplicity. Empty shields, different payloads, incomplete
occupancy and unexplained base magic find do not become comparable. This supports
the fixed contribution in Magic Find shields without adding market observations
or assigning an empty-base/rune-cost price to the completed item.

### Unknown socket occupancy and roll highlights — 2026-09-25

Unique/set report rows now use the shared SocketState validation before presenting
intrinsic roll bounds or colors. Unknown occupancy and contradictory empty/child
evidence no longer bypass socket-contribution handling or reuse tier proof.
Known-empty/unsocketed items retain their ordinary ranges, and independently
verified unmodified base-defense ranges remain visible. Captured totals and
source evidence are unchanged. Known definition bounds remain as an uncolored
“item range” suffix, separate from a verified intrinsic rating. This preserves
Guardian Angel's 180–200 enhanced-defense context when socket occupancy is unknown.

### Lem-filled equipment comparisons — 2026-09-25

Fixed gold-find contributions now include Lem in all four equipment families:
75 per weapon socket, 50 per helm/body armor/shield socket, compiled from the
pinned recipient columns. Native stat79 is a direct unshifted scalar. Base and
affixed contracts retain captured totals and exact rune multiplicity; named
contracts also bound the intrinsic gold roll after subtraction (including Crown
of Thieves). Different contents, missing links and wrong recipient bonuses do
not match. No rune-cost substitution or generic gold-find price premium is used.

### Exact rune payload roles — 2026-09-25

`socket_runes_equal` validates a bounded list of known rune names and compares
the complete captured multiset. Unknown/conflicting occupancy, missing identities,
duplicate child IDs, bad positions or code/name disagreements remain unknown.
A complete but different payload is false; one matching rune is insufficient.
Seven Gold Find Barbarian roles cover Standard off-hand, War Cry/Whirlwind swaps
and Leap Only main hands with six Lem runes. Standard preserves both Phase Blade
and the table's Crystal Sword alternative; other slots preserve Crystal Sword.
Ethereal non-attacking use and full-loadout requirements remain conditional.
No price or damage premium is inferred from this demand. Budget Ali Baba's
gold-find jewels are separate; these profiles do not substitute Lem for them.

### Guide-first inventory checkpoint — 2026-09-25

Run `python -m pricing.knowledge.assessment.maintenance.guide_inventory` to rebuild
the maintenance-only item-centric index from existing structured occurrences and
cached variant slots. It includes catalog identities without mentions, original
occurrence details, source hash checks, unresolved review buckets, and semantic
configuration fingerprints with all attached profile provenance. Duplicate
configuration sources do not create extra configurations; different predicates,
stages, sides or dependencies remain separate. No demand votes, grades, matching
or prices are inferred. See planning/GUIDE_FIRST.md and planning/STATUS.md for
remaining census gates; the checkpoint is not a runtime publication.

### Reviewed guide demand

`rules/guide_use_reviews.json` holds explicit identity endorsements linked to
reviewed profile IDs and complete profile fingerprints. `build_profiles` validates
those links and embeds reviewed uses and deduplicated demand summaries into the
profile artifact. A changed profile requires review before recompilation succeeds.
Publication recomputes the summary from embedded uses and rejects mismatches.

Runtime reads the prepared summary from the pinned profile artifact. Legacy bundles
without this field make no demand claim and cannot read newer working-tree reviews.
Incomplete corpus review renders Pending and a distinct-build lower bound; it does
not change captured-item role matching, trade tiers or prices. Insight is the first
reviewed batch, not a claim of complete demand coverage.

Reviewed guide-use records may include `presentation.progression` (`Starter`,
`Budget`, `Endgame`, `Ubers`). This is display metadata, not an equip predicate.
The compact formatter can group variants only when this reviewed stage and the
full evaluated rule/skill, dependency, base alternative and equipment signatures
agree. Unreviewed variants retain their original names. Full role records and
variant names remain available in the detailed view.

Unnamed base/affixed configurations may use `pattern` instead of `item` in a
reviewed use. Its value must equal the exact executable profile ID, with the same
source and complete-profile fingerprint checks. Prepared summaries use a separate
`pattern:` namespace. Named profiles cannot be registered as unnamed patterns;
changing a required combination invalidates the review.

`demand_for_item` preserves identity-level demand for named items. Otherwise it
selects prepared pattern summaries only for evaluated roles with a true item rule
and matched/conditional status. False, unknown and absent rule traces add no votes.
The union counts each recommending build once even when several configurations
match. No common base, rare title, skill label or partial modifier match supplies
that vote. Reports label this scope “matching configurations”; unknown live
loadout conditions remain separate in the evaluated roles. This selection does
not parse guides, alter item matching or supply numerical price evidence.

### Base coverage matrix

Run `uv run --offline python -m pricing.knowledge.assessment.maintenance.base_matrix
> pricing/data/appraisal-base-matrix.json` as one shell command. This maintenance
artifact enumerates every native weapon/armor base in normal, superior and
low-quality states. It retains source hashes, native socket limits, cached recipe
links, potential type/quality profile links and base-level market evidence.
Each dimension carries an independent state and reason. Candidate profile links
are not validated template membership; base-level observations are not matched
prices. Recipe/mode eligibility, usefulness, annotations and report validation
remain pending until their exact membership is audited. This is the base portion
of GUIDE_FIRST's coverage matrix; named and affixed configurations still need to
be integrated. It is not a runtime artifact or an appraisal decision source.

The matrix's `type_capacity_eligibility` dimension independently compares cached
edges with completed native `runes.json` recipes: both type parents, excluded
types, socket capacity, rune order and count. It records missing/unexpected edges
and blocks conclusions from absent native catalogs or incomplete type ancestry.
An excluded base has no fitting completed native recipe; this says nothing about
other uses or value. Non-Ladder availability and quality-specific preparation
remain in the separate pending `recipe_eligibility` dimension.

### Prepared stat evaluation

`rules/stat_use_reviews.json` holds explicitly reviewed priorities, not an automatic
conversion from `important_stats`. The maintenance compiler binds each review to
its exact role fingerprint and unchanged source bytes. `build_profiles` embeds the
reviews and immutable configuration data in the existing profile artifact.
Publication and repository validation recompute the prepared configuration and
reject mismatches. Older bundles make no stat claim; runtime never reads a newer
working-tree review. Quality/type indexing limits per-item configuration selection.

`StatsEvaluator` uses existing typed predicates and supplied role outcomes.
Mandatory combinations precede stat activation. Missing, failed and unknown roles
cannot produce confirmed markers. A conditional role permits local stat annotations
only when its remaining notes are explicitly reviewed as advisory and every typed
rule, skill, dependency and equipment gate passes. The overall role stays conditional. Results retain complete role
and activation traces, source provenance and separate configuration contributions.
Only independently matched uses can produce `desirable` or `supporting` annotations.
No default grey/trash inference exists; roll quality stays a separate unassessed
channel. `AssessmentResult.stat_evaluation` and its JSON projection carry this
immutable result when applicable. Explicit caller-supplied profiles do not inherit
unrelated bundled stat configurations.

The first three amulet configurations explicitly classify the whole-loadout reminder
as advisory for their local skill/FCR annotations. The reminder and conditional
build fit remain in the result. Advisory text must exactly match a reviewed role
condition; changed role/source fingerprints invalidate the configuration. Scalar lines now render independent desirability markers and roll text in terminal
and OSD when a prepared positive annotation exists. Lines with multiple semantic
stat keys remain unmarked pending contribution-level attribution. Full §8.1 also requires reviewed roll policies,
coverage-aware irrelevance, split/combined line attribution and all-family migration.

Six rare-ring configurations also carry explicit stat priorities for Lightning,
Nova and Blizzard variants. Supporting modifiers are scoped to the cited ring
combination; unrelated modifiers do not inherit desirability. Nova's unresolved
resistance mix and the Uber loadout condition remain mandatory gates. These ring reviews are incremental coverage, not all-family completion.

Seven six-Lem sword configurations now annotate verified 450% gold find for the
reviewed Barbarian roles. Exact socket payload, base, quality and class checks must
pass; unknown or mismatched fillers cannot inherit a marker from a stat total.
Preparation/durability reminders remain in the conditional role assessment.
There are 16 prepared stat configurations in total; the all-item coverage matrix,
roll policies and broader family annotation work remain incomplete.

### Unified maintenance coverage matrix

Run `uv run --offline python -m pricing.knowledge.assessment.maintenance.coverage_matrix`
to emit the union of guide identities, base-quality mechanics, named tiers and
reviewed use-quality assignments. Refresh guide_inventory and base_matrix first
when their input hashes are stale. Each row has independent states/reasons/source
locators; counts remain separated by row kind. Source validation rejects stale
snapshots. This is a maintenance ledger, not an appraisal runtime artifact.
Leveling and valuable-item records now retain exact identity links and full conditional
evidence. Imported saved captures now enter a durable review ledger and dimension queues.
Automatic discovery ingestion and reviewed template membership still need completion; matrix presence never establishes all-item coverage.

Import fresh saved replay output with:
`uv run --offline python -m pricing.knowledge.assessment.maintenance.observed_review <replay.json>`.
This preserves assessment history and unknown facets in
`pricing/data/appraisal-observed-review.json`. Rebuild the coverage matrix afterward
to refresh its independent review queues. The ledger consumes supplied historical
replays; it does not watch live inventory or initiate market research.

The generic-leveling audit confirms executable policies for all 13 cached patterns;
the matrix now links each pattern to its source-bound policy applicability.
Topaz armor utility requires complete distinct child linkage and observed magic
find at least equal to the verified Topaz contribution. Remaining empty sockets
are allowed. This establishes conditional leveling utility, not a price.

Generic leveling policy links are built by maintenance.leveling_links from exact
cached recommendation fields and reviewed source hashes. They preserve shared
identity guards and separate alternatives, and do not turn conditional leveling
utility into trade tiers or complete stat-annotation coverage. Changed recommendation
text stays in the review queue until its policy link is reviewed.

Named listing normalization can establish one filled socket from an explicit known
rune/gem payload when all definitions of that identity lack native socket modifiers.
The proof records definition generation and the quest socket cap. It never treats
omitted socket fields as zero or infers ethereal state/base upgrades. Intrinsic
socket-roll items and ambiguous/multiple filler descriptions remain unresolved.

Prepared named definitions also expose native socket ranges after capacity and
item-level clamping. Market normalization can supply a fixed count only if every
variant/bracket agrees. Missing contents remain unknown; a count alone never
establishes an empty or fully occupied item. Explicit contradictions are rejected.

The base coverage audit uses runtime candidate selectors and evaluates required
guards with partial catalog facts. It records excluded and unknown assignments
with profile fingerprints and predicate traces. Routing coverage is separate from
actual desirability, recipe legality, preparation and price coverage; omitted item
rolls and flags are not zero/false defaults.

Perfect base-use status requires complete identified capture and conflict-free
required evidence. Superior roll strengths require superior quality; native stat
conflicts are checked before any raw roll claim. Missing evidence preserves an
unverified/conditional assessment rather than a perfect or worthless conclusion.

Base coverage includes separate runtime base-use routes and build-role profile
assignments. The CLI supplies the base-use evaluator; callers omitting it get a
pending audit dimension. Full route evidence is retained in the unified matrix,
while item-specific suitability and market pricing remain independent.
