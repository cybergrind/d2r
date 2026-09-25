# Build-aware decision tree: executable design

2026-09-24. Refines section 2 of [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).
This is a proposed rule tree derived from cached build evidence, not implemented
assessment logic or newly verified item prices. Concrete modules, interfaces, schemas
and migration units are specified in [ARCHITECTURE.md](ARCHITECTURE.md). [BUILD_ROLES.md](BUILD_ROLES.md)
provides the full 33-build routing matrix and variant-specific source anchors.

## A. Shape of the tree

Use a **mechanics dispatch tree followed by a branching role evaluator**. A single
first-match tree would lose legitimate uses: the same Treachery can equip a mercenary
and be borrowed for Fade; an orb can be a combat weapon and Enchant prebuff tool.
Shared predicates are reusable nodes, but each terminal result retains its own
build/variant/slot and conditions. Do not combine independent roles into one score.

```text
ROOT: normalize ItemFacts
│  identity, quality, native stats/parameters, requirements, sockets/contents,
│  ethereal, original/upgraded base, ilvl and capture completeness
│
├─ N0: Is a stable identity/family known?
│  ├─ no → unresolved identity; retain known facts, no guessed tier
│  └─ yes → continue; unknown individual facets defer only dependent decisions
│
├─ N1: Choose ONE mechanics policy (ordered)
│  ├─ verified completed runeword → R[recipe, base, weapon/armor variant]
│  ├─ set identity → S[piece, set ID]
│  ├─ unique identity → U[identity, specialized collection if needed]
│  ├─ normal/superior/low quality → B[family, base]
│  ├─ magic/rare/crafted → A[family, quality-specific affix rules]
│  └─ other → material/consumable/quest policy or explicit unsupported category
│
├─ N2: Retrieve ALL indexed candidate roles for this identity/family/mod signature
│  ├─ P: player equipped roles
│  │  ├─ P1 skill-driven spell damage (element/tree-specific)
│  │  ├─ P2 weapon-driven attack damage
│  │  ├─ P3 special attack delivery (traps/kicks/javelins/Enchant/Smite)
│  │  ├─ P4 aura carrier / minion support
│  │  └─ P5 defensive, mobility and resource support
│  ├─ M: mercenary roles (act + subtype + actual legal slot)
│  │  ├─ M1 Act 1: aura bow / starter resource bow
│  │  ├─ M2 Act 2: Insight / Infinity / Pride / physical-proc weapon
│  │  ├─ M3 Act 3: spell weapon + shield + element-support armor/helm
│  │  ├─ M4 Act 5 Bash/Stun: compatible single sword / utility proc
│  │  └─ M5 Act 5 Frenzy: paired weapons / set package / utility procs
│  ├─ W: weapon swap, prebuff, charged utility or socket-filler roles
│  ├─ F: farming objective (MF, gold find, corpse preservation)
│  └─ L: leveling/temporary progression roles
│
├─ N3: Expand each role into actual build VARIANTS and item ALTERNATIVES
│  source-backed inheritance only; no generic “all Sorceresses” match
│  keep starter, standard, Ubers, MF, hybrid, support and prebuff separate
│
├─ N4: For EACH candidate, traverse its role subtree (below)
│  eligibility → core mechanism → modifiers → sockets/ethereal → dependencies
│  → current use OR legal preparation route OR mismatch/unknown
│
└─ N5: Consolidate independent conclusions
   ├─ current suitability and important rolls
   ├─ possible prepared state (separate from current state)
   ├─ trade tier / comparable segment / dated offline price
   ├─ independent leveling tier and keeper highlight
   └─ concise role-specific reasons; diagnostics retain rejected candidates
```

Candidate retrieval is an index lookup over reviewed policies, not scanning every
build on hover. Search keys include named identity, base/family, skill/tree/element,
aura/proc/charge identity, sockets, and quality. Include generic utility roles even
when an item has no exact guide mention. Never classify only for the player's own
Warlock: all cached builds can create trade demand.

## B. Exact contract for every role leaf

Each leaf has a stable `role_id`, `build_id`, `variant_id`, `side`, `slot`, stage and
source locator. It defines these decisions in order:

| Node | Question | Outcomes |
|---|---|---|
| E0 | Is this evidence endorsed, current enough for mechanics, and legal in this game version? | reviewed / discovery-only / conflict; latter two cannot certify fit |
| E1 | Can this class/merc subtype equip this base in this slot? | eligible / reject / unknown requirements |
| E2 | Does it supply this role's defining mechanism? | e.g. actual Meditation, exact skill, Life Tap charges, or necessary set piece |
| E3 | Are required item-level predicates met? | all/any groups with native IDs; wrong skill identity is a mismatch |
| E4 | Does observed socket/ethereal/upgrade state work? | current fit / preparation candidate / unacceptable / unknown |
| E5 | What loadout dependencies remain? | companion items, IAS/FCR/FHR/block, survival, proc conflicts, charge recharge |
| E6 | How good are the relevant rolls within this role? | baseline / improved / best observed roll; no unrelated-stat reward |
| E7 | What does this establish? | exact setup component / suitable alternative / progression option / conditional candidate |

Predicates return **true, false, unknown, not-applicable**. False rejects only that
role. Unknown preserves a conditional candidate and prevents dependent claims.
An unidentified item can still have a known base preparation use, but cannot inherit
an identified named roll tier. Missing total defense should not erase a known aura.

Separate source numbers into four categories:

1. Legal game limits (from definitions).
2. Explicit guide minimums or build breakpoint requirements.
3. Planner exemplars/target rolls (not automatic minimums).
4. Reviewed assessment bands (must document the derivation and test boundaries).

For example, a planner's 45-life skiller does not mean a 30-life skiller is unusable.
A displayed perfect six-stat rare must pass affix legality before becoming a target.

## C. Player role subtrees

### P1 — skill-driven damage

```text
Matching class/tree/skill or named caster item?
├─ no → do not award caster skill value; still evaluate other roles
└─ yes
   ├─ elemental/poison spell → exact element, useful +skills, pierce/mastery
   ├─ magic spell → exact skill scaling and applicable magic modifiers
   ├─ hybrid → evaluate each supported element separately; retain opportunity cost
   └─ minion skill → summon-specific scaling/support; no generic elemental score
        ↓
   Spell delivery requires cast rate? → contribution toward this VARIANT's target
   Staffmod + affix skills combine legally? → total relevant skill contribution
   Two-handed vs one-handed+offhand? → record lost/required offhand benefits
   Resource/survival dependencies? → conditional until loadout known
```

Leaves: cold Sorceress (Blizzard/Frozen Orb), lightning caster (Lightning/Nova),
fire caster (Meteor/Hydra/Fire Wall), dual-element Sorceress, Poison Nova,
Hammer/FoH/Holy Bolt, Fissure, Warlock Abyss/fire/Blood Boil, and summon support.
Each has its own native skill/element selectors. A Fire Mastery roll does not improve
a pure Nova leaf; magic weapon damage does not automatically improve Hammer damage.

**Mandatory split: Infinity holder.** Nova Standard uses player Infinity Scythe
with mercenary Insight. Nova Hydra Hybrid uses player Eschuta's and mercenary
Infinity. Player and mercenary Infinity receive different base/roll priorities;
wearer-only modifiers must not be credited to the other character. Lightning Strike
uses player Infinity Matriarchal Spear: a third role with +Amazon skills and attack
requirements. These are separate comparable segments, not one Infinity tree leaf.

### P2 — weapon-driven attacks

```text
Attack role and legal wield configuration?
├─ ordinary melee → effective weapon damage + IAS + hit chance + sustain
├─ two-handed / dual-wield → configuration-specific damage and speed
├─ throwing → quantity/replenish, skill interactions, ethereal, IAS and damage
└─ physical bow → bow damage/speed, aura partner, pierce and attack support
     ↓
  ED + flat damage + per-level damage + base damage: compute only verified semantics
  Required repair/indestructibility? → account for ethereal usability and socket cost
  Mechanism-specific alternatives? → Grief flat damage is not comparable by ED alone
  Farm target or Ubers? → crushing blow/open wounds/procs can change priorities
```

Separate Berserk, Zeal, Whirlwind gold-find, Double Throw, Strafe and Mirrored Blades
policies. Echoing Strike gets its own scaling review; never infer its damage formula
from a generic physical weapon policy. Smite routes through P3, so attack-rating
value from ordinary melee cannot leak into its skill evaluation.

### P3 — special delivery mechanics

| Leaf | Build evidence | Discriminating decisions |
|---|---|---|
| Trap claw, lightning | Lightning Sentry Standard | Exact Lightning Sentry/Traps skills, base speed, IAS, legal sockets; supporting Death Sentry/Weapon Block are separate bonuses |
| Trap claw, fire | Wake of Fire Standard; Fire Blast Damage is planner-only | Exact Wake of Fire/Fire Blast skills; source endorsement first; do not reward Lightning Sentry as equivalent |
| Martial-arts claw/kick | Dragon Talon Standard/Budget | Mosaic pair vs Black starter weapon; charge-retention mechanism and skill applicability; kick damage is not weapon ED |
| Lightning javelin | Lightning Fury | Relevant skills/IAS and element support; Titan's replenish/physical ethereal benefit differs from Thunderstroke pierce and Ubers role |
| Lightning spear | Lightning Strike Standard | Infinity-compatible Amazon spear, inherent skills, attack speed and actual equipment legality |
| Enchant projectile | Enchant Standard/Budget | Demon Machine/Kuko projectile mechanism, pierce and IAS; caster FCR priorities cannot replace this weapon role |
| Smite/Ubers attack | Smite; Hammer Ubers; Dream Ubers | Skill-specific damage, speed, life sustain, crushing blow/open wounds; don't apply ordinary AR scoring blindly |
| Echoing Strike | Echoing Standard/Starter | Skills/FCR and supported staffmods; physical, proc and leech contributions need verified skill mechanics |

A proc or skill modifier gets a beneficiary and trigger: on attack/on striking/when
struck/charges/aura are not interchangeable. Review whether the actual skill can
trigger it. Never recommend every chance-to-cast item for every attack build.

### P4 — aura and minion support

- Dream Paladin: helmet + shield Dream is a combination; Hand of Justice + Dragon
  is the Hybrid branch, with Act 1 Faith support. Evaluate each piece and missing
  companions without claiming the full aura package is active.
- Summoner Necromancer: Beast Damage/Ubers alternative, merc Infinity and Bramble
  have separate beneficiaries. Bramble's minion-support role is not equivalent to
  “highest mercenary defense.” Preserve curse/proc interactions as loadout checks.
- Strafe and Mirrored Blades: Pride is a support-aura mercenary weapon, with different
  aura-roll and survivability priorities from Insight. Do not pool their listings.
- Warlock summons/Blood Boil: currently broad guide mentions in the imported demand
  layer; extract exact skill scaling and variant roles before approving thresholds.

### P5 — supporting equipment, split by actual job

| Family | Role leaves and ordered decisions |
|---|---|
| Circlets | skill+FCR caster; skill+IAS/FRW attack; socket platform; low-level utility → exact class/tree → legal quality combination → relevant rate target → sockets → life/stats/resists → extras |
| Pelts / Barbarian helms | main-skill combat vs prebuff → matching staffmods + class/tree affix → sockets and supporting stats; Fissure pelt is not a generic Druid helm score |
| Rings | caster FCR+resource; attack AR+leech; hybrid FCR+AR/leech (Echoing); MF/GF; defensive absorb/CBF → evaluate each independently |
| Amulets | class/tree+FCR; attack speed/crit; charged mobility; prebuff+skills; MF/GF; leveling set component |
| Gloves | skill+IAS attack; caster utility; crushing-blow craft; MF/GF; resistance starter; kick mechanics where relevant |
| Boots | caster mana/resource; movement+resist; kick damage; attack procs; MF/GF; leveling requirements |
| Belts | cast-rate craft; attack sustain; DR/absorb; MF/GF; early capacity/life/resists |
| Shields | caster skills/FCR; block/DR; class-skill staffmods; socket platform; runeword base; aura carrier → these can overlap but cannot share one score |
| Armor | teleport enabler; FCR/skills; physical damage; resist/DR; aura/minion support; Fade prebuff; mercenary survival; early progression |
| Charms | exact skiller+secondary; physical damage/AR+life; resists+life/MF; mana+MF; GF; sunder identity+penalty; low-level variants |
| Jewels | IAS+fire resist for Andariel; IAS+ED attack; resist/requirements utility; elemental facet; MF/GF socket filler; low-level use |

Circlet examples must branch by legality before desirability: a magic skill/FCR
circlet and a rare multi-affix circlet use different pools. The cached Echoing
“Forbidden Diadem of the Magus” description mixes several target properties; it is
a source requiring affix review, not an executable all-required magic-item rule.

### P5a — circlet subtree, worked family design

```text
Circlet / Coronet / Tiara / Diadem
├─ named unique/set → identity policy first, then applicable roles
└─ magic/rare/crafted policy as legally supported by definitions
   ├─ class/tree skills + FCR present?
   │  ├─ matching caster/hybrid class → candidate for that class's source variants
   │  │  ├─ required rate contribution met → assess sockets and survival/attributes
   │  │  ├─ lower than explicit role minimum → reject that exact setup, try progression
   │  │  └─ planner target only → compare target; do not invent a minimum
   │  └─ wrong skill class → reject this class role, query matching other classes
   ├─ class/tree skills without FCR?
   │  └─ evaluate builds not requiring FCR in this slot, prebuff and leveling uses
   ├─ socket platform / movement / attack combination?
   │  └─ evaluate reviewed attack/farming collections; verify affix/socket legality
   └─ no reviewed combination → ordinary utility or explicit unreviewed pattern
```

Within a matched role, evaluate sockets, life/mana, strength/dexterity, resists and
FRW according to that variant's needs. Extra sockets are not universally more useful
than a required FCR contribution; a skill/FCR circlet is not automatically superior
to the named unique used by that build. Compare against source-backed alternatives.
The exact base still affects legal affix generation, requirements and preparation.
A Diadem name alone must not trigger a valuable-item highlight.

### P5b — ring subtree, overlapping combinations

```text
Ring
├─ named unique → named identity, rolls and build roles
└─ magic/rare/crafted
   ├─ FCR → caster candidate; life/mana/resist/attributes assessed per variant
   ├─ AR + leech → supported attack candidate; which leech and damage beneficiary?
   ├─ FCR + AR + leech → hybrid candidate (Echoing source example)
   ├─ MF/GF → farming candidate independent of combat fit
   └─ defensive/resource/leveling utility → contextual use
```

Evaluate these branches independently. A ring lacking leech may fail the Echoing
hybrid target while remaining useful for a spellcaster. Two crafted/fixed and affix
contributions must be decoded without counting the same stat twice. Do not use the
planner's perfect AR/life rolls as minimum entry gates. The comparable segment
must preserve valuable extra properties in either direction.

## D. Mercenary tree — full cached scope

First choose act/subtype and legal equipment; then choose the mercenary's **job**.
Do not infer a universal ethereal preference from side=merc.

```text
MERC
├─ Act 1 Rogue → supported bow + aura/resource role
│  ├─ Faith: Dream Hybrid/Ubers, Lightning Strike Standard, Double Throw
│  └─ Insight: Enchant Budget
├─ Act 2 Desert → polearm/spear legality + aura/job
│  ├─ Insight: mana support; Prayer/Cure synergy depends on actual setup
│  ├─ Infinity: conviction support + merc damage/survival
│  ├─ Pride: concentration support + explicit survivability tradeoffs
│  ├─ Reaper's Toll: physical/decrepify support; curse interactions
│  └─ physical kill engine: Gold Find merc Breath of the Dying War Pike
├─ Act 3 Iron Wolf Fire → spell-support weapon + shield
│  └─ Dragon Talon: Hexfire, Ormus, Flickering Flame, Lidless/Spirit
├─ Act 5 Bash/Stun → compatible single-sword role
│  └─ Berserk Chaos Prep: Lawbringer Legend Sword
└─ Act 5 Frenzy → two compatible weapons, their roles separately
   ├─ Echoing Ubers: Sazabi package + Malice second weapon
   ├─ Lightning Fury/Strike Ubers: paired Plague proc support
   └─ FoH Tri-Brid: Lawbringer + Death support/damage package
```

Armor/helm subnodes are evaluated inside each job:

1. What sustain source exists? Leech is not generically useful to spell-only damage;
   Insight+Cure+Prayer or other regeneration depends on the actual hireling/setup.
2. What speed target applies to the actual weapon, aura and jewels? Unknown other
   equipment means contribution only, not “breakpoint achieved.”
3. Does the role need resist/DR/CBF, aura support, damage, MF/GF or set completion?
4. Is the item shared with the player? **Smite Standard/High Investment explicitly
   asks for non-ethereal Treachery**, so the generic merc-armor ethereal preference
   must be overridden in that role. Preserve the guide's reason during review.
5. Compare base strength/level requirements to hireling eligibility. Highest defense
   is not best if the intended mercenary cannot equip it at the relevant stage.

This adds Act 3 and Act 5 single-sword coverage missing from the previous broad
plan. Cached mercenary type/prose conflicts remain conditional until reconciled.

## E. Swap, prebuff and farming trees

```text
UTILITY (evaluate even if combat role fails)
├─ skill buff → Call to Arms / +Warcries weapons / Memory / Enchant orb / Demon Limb
│  └─ exact skill level + charges if relevant + legal equip requirements
├─ mobility → Teleport charges / Naj's Puzzler / Harmony movement
│  └─ charges remaining, recharge access/cost context, weapon-swap constraints
├─ curse/debuff → Lower Resist or Life Tap charges
│  └─ exact skill and level; charges differ from chance-to-cast
├─ triggered defense → Treachery Fade prebuff
│  └─ player equip usability and durability; not an armor-defense contest
└─ socket platform → rune/jewel payload rather than runeword
   ├─ Gold Find: six-Lem sword / Ali Baba sockets
   ├─ Fissure Ubers: six-facet Crystal Sword
   └─ lightning/Fissure shield: legal magic Monarch with sockets/block modifiers
```

A six-socket Crystal Sword must therefore reach three independent branches: legal
six-rune recipe candidate, GF payload platform, and facet platform. A magic Monarch
cannot be a Spirit base, but may be valuable as a facet/block platform. Filled
non-runeword items must not be lost between “empty base” and “completed runeword.”

Farming overlays are variant-specific: MF, GF, mobility, clear speed and corpse
preservation can conflict. Gold Find Leap Only and War Cry let the mercenary kill;
Standard/Whirlwind use different player weapon roles. Cold/corpse effects require
review where Find Item or Corpse Explosion is part of the actual farming loop.
Do not penalize those effects globally on unrelated builds.

## F. Base tree driven by build destination

```text
BASE (including unsocketed or currently gemmed normal/superior items)
├─ Q: quality allows destination?
│  ├─ recipe: verified runeword-capable quality/type only
│  ├─ gem/rune payload: legal socket platform, including suitable magic items
│  └─ leveling/crafting/other utility: separate policy
├─ D: enumerate destination recipe × role from reviewed build evidence
│  ├─ Infinity → Nova self-wield / Lightning Strike player / Act 2 merc
│  ├─ Insight → Act 2 resource / Act 1 starter bow / player alternatives
│  ├─ Void → Abyss caster dagger / Echoing dagger / other reviewed uses
│  ├─ Spirit → sword starter / player shield / swap shield / Act 3 shield
│  ├─ armor → player equipped / merc equipped / player-borrowed prebuff
│  └─ remaining recipes → exact role records, not a generic recipe score
├─ S: sockets now?
│  ├─ exact total + empty → ready
│  ├─ exact total + filled → clearing needed, contents destroyed
│  ├─ zero → Larzuk/cube outcome tree (quality + ilvl + version)
│  ├─ wrong nonzero count → impossible for this destination
│  └─ unknown → conditional, no readiness claim
├─ V: role-specific base advantages?
│  ├─ inherent resists / skills / staffmods
│  ├─ weapon speed/damage/reach where mechanics require them
│  ├─ defense/weight/requirements
│  └─ ethereal, superior ED/EDef/AR and repair/durability implications
└─ O: compare legal alternatives under the SAME role assumptions
   preferred / viable / progression / dominated-for-this-role / unknown
```

Do not prune other destinations when one recipe is impossible. Superior unsocketed
Phase Blade failing Grief preparation may still have other legal uses.

Best-base proof requires: recipe legal, achievable sockets, critical inherent mods,
relevant best rolls, correct ethereal policy, equip requirements, and comparison
against the role's eligible alternatives. Without loadout-dependent attack-speed
information, say “preferred base; best choice depends on IAS,” not universally best.
Caster/prebuff roles can prioritize requirements over damage. Perfect superior ED
is a physical premium candidate; it is not automatically important for a buff stick.

## G. Named-item tier tree

```text
Exact unique/set identity
├─ load explicit reviewed default trade tier and independent leveling profiles
├─ choose specialized mechanical collection or generic named strategy
├─ evaluate each build/variant role through E0–E7
├─ evaluate tier overrides for THIS identity
│  ├─ important roll combination / perfect relevant roll
│  ├─ ethereal usable/preferred vs detrimental for the actual role
│  ├─ socket count / contents / upgrade state
│  └─ source-backed niche/collector exception
├─ set piece? → standalone use + companion-dependent uses (common SetHandler)
└─ produce trade tier + useful roles + leveling tier + separate price evidence
```

Collections are implementation reuse, not equal market value. Example specialization:
Tomb Reaver for Mirrored Blades needs ethereal/three-socket/indestructibility investment
review; ordinary ED-only unique weapon assessment misses its defining setup.
Demon Machine needs an Enchant projectile-role strategy; high caster skills alone
would never discover it. Ormus needs skill identity, elemental rolls and player vs
Act 3 beneficiary review. Titan's and Thunderstroke share a family but not a premium
policy. Sazabi can be low general trade priority while important for Echoing Ubers.

Tier override rules must be ordered and mutually consistent. Unknown premium facts
produce conditional tier bounds/review, never silently select the cheapest tier.
Every identity gets high/med/low/trash after review; missing evidence remains pending.
Leveling high/med/low/none is evaluated separately, including partial-set conditions.

## H. Concrete source-to-rule examples

These are proposed decisions anchored in cached sources; planner numbers remain
examples until the stated predicate review passes.

| Source (variant JSON pointer) | Proposed leaf / required distinction | Roll priorities and remaining dependencies |
|---|---|---|
| nova-sorceress-guide `/variants/1/player/Weapon` | `P1.nova.infinity_self` — Infinity, player polearm | Scythe/requirements and applicable wearer modifiers; no merc physical-base premium by default |
| nova-sorceress-guide `/variants/3/merc/Weapon` | `M2.infinity.conviction` — Act 2 Infinity | Ethereal physical base, damage/speed/survival; wearer-only pierce not assigned to player |
| lightning-strike-amazon `/variants/1/player/Weapon` | `P3.lightning_strike.infinity` | Amazon spear + inherent skills, attack mechanics; different cohort from both above |
| lightning-sentry-assassin `/variants/1/player/Weapon` | `P3.trap.lightning_claw` | Traps + Lightning Sentry, IAS/base speed, sockets; 40 IAS/+3 staffmods are target exemplars |
| wake-of-fire-assassin `/variants/1/player/Weapon` | `P3.trap.fire_claw` | Wake of Fire/Fire Blast instead; Plague is an alternative, not the same item contract |
| enchant-sorceress `/variants/3/player/Weapon` | `W.enchant.prebuff_orb` | Fire tree + Enchant + Fire Mastery; combat physical damage not its job |
| enchant-sorceress `/variants/1/player/Weapon` | `P3.enchant.projectile` | Demon Machine projectile mechanism and IAS; distinct from orb leaf |
| dream-paladin `/variants/1/merc/Weapon` | `M1.faith.aura` | Rogue legal bow, aura and speed; no ethereal bow expectation |
| dragon-talon-assassin `/variants/1/merc` | `M3.fire.spell_support` | Hexfire/Ormus/Flickering Flame/Spirit; no generic attack leech assessment |
| smite-paladin `/variants/1/merc/Body Armor` | `M2.armor.shared_treachery` | Explicit non-ethereal preference; do not apply blanket green ethereal |
| echoing-strike-warlock-guide `/variants/3/merc` | `M5.echoing_ubers.sazabi` | Three pieces, configured fillers, Malice second sword; ownership of companions unknown |
| gold-find-barbarian `/variants/4/player/Weapon` | `F.gold_find.lem_platform` | Six sockets and payload, requirements; raw sword damage irrelevant to Leap Only job |
| mirrored-blades-warlock-guide `/variants/1/player/Weapon` | `P2.mirrored.tomb_reaver` | Ethereal + three sockets + Zod/payload constraints; source skill scaling review required |
| fissure-druid `/variants/2/player/Off-Hand` | `F.magic_find.monarch_platform` | Magic block/socket shield with Ist payload, not Spirit base |

All source files above live in `pricing/data/wp-a-variants/`. BUILD_ROLES.md includes
source paths and exact unabridged variant names for the full branch inventory.

## I. Evidence conflicts the compiler must detect

- Empty slot arrays in a **delta variant** mean unspecified, not necessarily unequipped.
  Explicit “none — two-handed Infinity” means absence. Inherit only from an explicit
  parent; a starter must never inherit endgame armor because a slot is missing.
- “Unchanged mercenary” requires a known parent. A prose alternative and planner
  example are separate alternatives, not a required simultaneous combination.
- Duplicate/old planner versions, `ebug` annotations, impossible affix combinations,
  inconsistent slot placement and disputed hireling subtypes are review flags.
  A carried Lower Resist wand under a Charms array is utility, not a charm identity.
- FoH Tri-Brid lists a second sword both in Weapon text and Off-Hand: normalize
  dual-wield positions without double-counting demand or treating it as a shield.
- Build-wide +skills/FCR/resist prose cannot become a universal rare-item threshold.
- Whole set bundles and socket fillers are distinct components with independent
  item identities; do not price the bundle as the hovered piece.
- Seven cached builds currently have only Guide mention demand contexts. They get
  discovery branches and extraction work, not invented Standard/Ubers assignments.

## J. Build vertical slices after the guide-first pass

Priority revised 2026-09-25: complete [GUIDE_FIRST G1–G5](GUIDE_FIRST.md) first.
The slices below remain integration/regression coverage after the offline census,
item-centric demand grading, guide-derived configurations and compact report pass;
they no longer determine the first work package.

1. Compile source branch ledger: variant inheritance, alternatives, beneficiary,
   quality legality and conflicts. Freeze exact source locators and review states.
2. Implement role graph schema and E0–E7 evaluator alongside existing mechanics
   dispatch. A role gets `must`, `any_of`, `prefer`, `avoid`, `depends_on`,
   `preparation`, `comparison_segment` and provenance; no numeric total score.
3. Deliver **Nova Infinity / Act 2 Infinity / Lightning Strike Infinity** together.
   This proves role-aware base choice, ethereal semantics and separate comparisons.
4. Deliver **Echoing Starter/Standard/MF/Ubers**, including crafted ring, prebuffs,
   Act 2 Prayer setup and Act 5 Sazabi package; reuse the saved dagger/Sazabi fixtures.
5. Deliver **trap claws + Enchant prebuff/projectile + Fissure pelt/platform**. This
   proves exact skill combinations, legal affixes, alternate uses and socket payloads.
6. Deliver **Smite + Dream + FoH mercenary variants**, including non-ethereal shared
   armor, Act 1/3/5 equipment legality and paired-weapon/companion dependencies.
7. Deliver **Gold Find + Strafe + Mirrored Blades + summon support** for competing
   damage, aura, farming and proc priorities. Complete remaining caster branches
   from the 33-build crosswalk and extract the seven guide-only variant gaps.
8. Fill every named default trade tier and leveling record; specialize value-sensitive
   identities encountered above. Generic low/trash policy stays per-identity data.
9. Audit all source occurrences against executable leaves, then enable reviewed
   market segments. Existing strict price contracts stay in place during expansion.

For each slice, test one qualifying item, a nearby wrong-role item, unknown critical
facts, unmet companion/loadout conditions, and useful preparation. Replay captured
items through the real report path. Specific acceptance pairs: Nova vs merc Infinity;
lightning vs fire claw; combat vs prebuff orb; empty vs filled magic Monarch; ordinary
merc armor vs Smite shared Treachery; standalone Sazabi vs conditional full package;
45-life target vs lower-life useful skiller; GF sword vs physical attack sword.

Completion gate: every proposed branch in BUILD_ROLES.md either maps to reviewed
executable leaves or has a precise unresolved source/mechanics gap. Broad class
coverage and item-name counts alone cannot pass the gate.
