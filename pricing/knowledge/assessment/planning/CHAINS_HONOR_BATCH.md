# Chains of Honor family — 2026-09-26

Second demand batch after the caster-leveling tail (first: Vipermagi). Reused
cached WP-A variants and pinned native rune tables. No new collection, extraction
or live captures. Review effort estimate: thirty minutes. Twenty-one uses across
thirteen builds; player/merc overlap contributes only one global build vote.

| Build | Variant index | Beneficiary | Base | Mercenary type |
|---|---|---|---|---|
| blessed-hammer-paladin | 3 | player | Archon Plate | — |
| echoing-strike-warlock-guide | 1 | merc | Archon Plate | Act 2 Prayer |
| echoing-strike-warlock-guide | 2 | merc | Archon Plate | Act 2 Prayer |
| enchant-sorceress | 1 | merc | Archon Plate | Act 2 Prayer |
| enchant-sorceress | 2 | merc | Archon Plate | Act 2 Prayer |
| fissure-druid | 3 | player | Archon Plate | — |
| fissure-druid | 3 | merc | Archon Plate | Act 2 Might |
| fist-of-the-heavens-paladin | 3 | merc | Sacred Armor | Act 5 Frenzy |
| lightning-fury-amazon-guide | 3 | player | Dusk Shroud | — |
| lightning-sorceress | 3 | player | Archon Plate | — |
| lightning-strike-amazon | 2 | player | Archon Plate | — |
| meteor-sorceress | 1 | player | Dusk Shroud | — |
| mirrored-blades-warlock-guide | 1 | merc | Archon Plate | Act 2 Might |
| nova-sorceress-guide | 1 | merc | Archon Plate | Act 2 Might / Act 2 Holy Freeze |
| nova-sorceress-guide | 2 | merc | Archon Plate | Act 2 Might / Act 2 Holy Freeze |
| nova-sorceress-guide | 3 | player | Wyrmhide | — |
| nova-sorceress-guide | 3 | merc | Archon Plate | Act 2 Might / Act 2 Holy Freeze |
| smite-paladin | 1 | player | Archon Plate | — |
| smite-paladin | 2 | player | Archon Plate | — |
| strafe-amazon | 1 | merc | Archon Plate | Act 2 Might |
| strafe-amazon | 2 | merc | Archon Plate | Act 2 Might |

## Shared rules and exceptions

Completed Chains of Honor, identified normal/superior armor, four filled sockets,
exact cited base. Player uses are nonethereal; mercenary uses ethereal. These are
reviewed role scopes, not claims that other bases/nonethereal merc armor are useless.
No empty base inherits completed-runeword utility or price. Native recipe source:
`third-parties/d2data/json/runes.json#/Chains of Honor`, Dol/Um/Ber/Ist.

Skills, physical damage reduction and resistances support player spell/Smite roles.
Mercenary uses also prioritize physical life leech. Ordinary leech is not annotated
for Smite/spells. Leechable targets and actual physical damage remain conditions.
Native mercenary skills can benefit from all skills; fixed item-granted aura levels
cannot. Mirrored Blades explicitly values native Might amplification from CoH plus
Andariel’s. Strafe retains the weak-Pride-damage warning and defensive alternatives.

Mercenary subtype gates: Prayer for Echoing/Enchant; Might for Fissure/Mirrored/Strafe;
Might or Holy Freeze for Nova; Act 5 Frenzy for FoH Tri-Brid Sacred Armor. No player
casting breakpoint is transferred to mercenary armor. Player Lightning Ubers105FCR;
Meteor Standard63FCR/60FHR, with105FCR an optional target. Nova Hydra is life-based.
Treachery remains a separate Fade prebuff; it is never simultaneous body armor.
Cure/Insight/Infinity, Flickering Flame, dual weapons and Life Tap/boss dependencies
are explicit qualifications, not inferred equipped companions or readiness claims.

## Deferred source uses

- `/blessed-hammer-paladin/variants/2`: ethereal Archon planner versus Sacred prose.
- `/double-throw-barbarian-guide/variants/1` and `/2`: CoH planner versus Shaftstop prose.
- `/dream-paladin/variants/2`: CoH prose versus Duress planner, base not reconciled.
- `/mirrored-blades-warlock-guide/variants/2`: Fortitude planner versus copied CoH prose.
- All Hardcore-only references excluded from Softcore promotion.
- Gear-table-only and other source contexts remain pending. Thirteen is a lower
  bound, not proof that all thirty distinct-build review leads are resolved.

## Verification

Red:22missing-role/demand failures. Green:32family/stat/source tests11.14s plus
6demand/publication checks0.07s; lint/format passed. Tests cover recipe/sockets,
quality/ethereal/base/identity, malformed or missing context, supported mercenary
alternatives, breakpoints, observed stats only, and no duplicate build votes.
Saved before/staged/published reports and matrix publication checkpoint: STATUS.md.
No numerical price policy or market observations changed. Maintenance rules/data
only; no additional worker restart. Evidence:`tmp/chains-honor-*`.

Next scheduled batch is specialist/leveling/unresolved. Review one of the explicit
source conflicts above, preserving original evidence and distinguishing alternative
gear from unresolved contradictions. All-item tiers, base preferences, affix
patterns, leveling coverage and exact scoped price cohorts remain incomplete.

Published generation: `1ca3fa379934d025f154ea584fab7c0a0303ad22265b8ab05f2dfb11308d3c9c`. 558 roles / 550 stat configurations.
