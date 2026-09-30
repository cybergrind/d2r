# Stone of Jordan skills/mana template — 2026-09-25

First demand batch after the movement-boots leveling tail. One fixed-modifier
utility template,14 variant uses across8 distinct builds. Review-effort estimate:
10minutes for the shared utility, explicit cast-rate gates and source exceptions;
not a measured speedup. Existing structured extraction reused; no online collection.

Source: pricing/data/wp-a-builds.json, SHA256
8a9da0d8cdd38e74d5b03721f5cf9de78e63c17ce87170cb706a6acfa31d59a2.
Original guide dates, exact variant locators and quotes retained in each role.
Native unique definition122: Ring,1all-skills/20mana/25%mana and1–12lightning attack
damage, all fixed. No roll target, ethereal premium or numerical price inferred.

## Shared applicability and exceptions

Identified, nonethereal unique Stone of Jordan in native ring base; cited player
class. Skills desirable, flat and percentage mana supporting. Only captured stats
receive annotations. Lightning attack damage does not acquire spell priority.
Total main-loadout FCR is required only where the selected source states it. Missing
numbers stay unknown, never inherited from another variant. Mana capacity does not
prove sustain or Energy Shield defense. One hovered ring does not prove two rings
or the complete damage/survival setup. Native equip requirements remain separate.

Enchant explicitly requires105FCR on weapon swap; do not substitute the main-loadout
FCR value. Nova Hydra Hybrid explicitly uses life-based defenses and has harder mana
management. These conditions remain in the role evidence and report qualification.

## Explicit template membership

| Profile | Source locator | Required main FCR | Ring mentions in source |
|---|---|---|---|
| blizzard-sorceress-1-soj | `/blizzard-sorceress/variants/1` | 105 | 2 |
| enchant-sorceress-1-soj | `/enchant-sorceress/variants/1` | Unspecified | 1 |
| fissure-druid-1-soj | `/fissure-druid/variants/1` | 99 | 1 |
| fissure-druid-2-soj | `/fissure-druid/variants/2` | Unspecified | 1 |
| fissure-druid-3-soj | `/fissure-druid/variants/3` | Unspecified | 1 |
| lightning-sentry-assassin-1-soj | `/lightning-sentry-assassin/variants/1` | 65 | 2 |
| lightning-sorceress-1-soj | `/lightning-sorceress/variants/1` | 117 | 2 |
| nova-sorceress-guide-1-soj | `/nova-sorceress-guide/variants/1` | 105 | 2 |
| nova-sorceress-guide-2-soj | `/nova-sorceress-guide/variants/2` | Unspecified | 2 |
| nova-sorceress-guide-3-soj | `/nova-sorceress-guide/variants/3` | Unspecified | 2 |
| poison-nova-necromancer-1-soj | `/poison-nova-necromancer/variants/1` | 125 | 1 |
| poison-nova-necromancer-2-soj | `/poison-nova-necromancer/variants/2` | 125 | 1 |
| summoner-necromancer-guide-1-soj | `/summoner-necromancer-guide/variants/1` | 125 | 1 |
| summoner-necromancer-guide-2-soj | `/summoner-necromancer-guide/variants/2` | 75 | 2 |

Duplicate ring mentions and repeated variants do not add independent build votes.
Reviewed breadth is8, Pending/High lower bound, not a trade tier or confirmed fit.

## Remaining identities/configurations

The16 exact positive non-planner-only/non-Hardcore ring entries in consolidated
variants include two configurations outside this template:

- fire-blast-assassin/variants/1: needs crafted caster amulet12+FCR and total102FCR;
  distinguish the Phoenix and Spirit alternatives. A total breakpoint alone cannot
  certify the required amulet. Add typed companion-item facts/predicates and tests.
- fist-of-the-heavens-paladin/variants/3: Tri-Brid uses75mainFCR/125swapFCR/48FHR,
  and a Cannot Be Frozen source for Baal/Diablo. Needs encounter/gear-dependent ring
  alternatives, not an unconditional SoJ match.

Decorated labels, prose-only contexts and remaining raw planner leads also remain
in the complete review queue. Deferral is not no-use or worthless evidence.

## Validation

14 missing-role failures before implementation.16 focused checks pass after adding
rules; initial test breadth expectation corrected from9 to8 after inspecting the
actual eight member build IDs. Tests cover every member's gates, unknown/wrong class,
malformed/below-threshold FCR, fixed modifiers, missing observed stats and impossible
ethereal rings. Full affected and publication results are recorded in STATUS.md.
All18 saved report texts and prices unchanged in staging. New cases use domain
fixtures; no new live capture. Evidence tmp/soj-*.

Follow-up2026-09-25: Fire Blast Phoenix branch is now reviewed; see
FIRE_BLAST_COMPANION_BATCH.md. Spirit/Nagelring and Tri-Brid remain pending.
