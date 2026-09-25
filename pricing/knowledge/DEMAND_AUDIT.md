# Build-demand coverage audit — 2026-09-24

Cached research coverage; not proof every current guide or valuable item is covered.

The Sazabi failure was an identity-join loss: decorated variant labels did not match canonical item names.
The importer now preserves setup text while resolving named identities. Reports retain variant/side/slot.

| Measure | Count |
| --- | ---: |
| cached builds imported | 33 |
| planners imported | 114 |
| planner profiles | 719 |
| demand occurrences | 60491 |
| recommended occurrences | 10711 |
| unresolved recommended occurrences | 3063 |
| unique unresolved recommended labels | 1406 |
| named unique set demand items | 206 |
| named demand missing watch | 0 |
| watch records | 217 |
| watch distinct names | 209 |
| planner only unendorsed occurrences | 11584 |
| historical planner occurrences | 0 |

## Remaining gaps

- Decorated named identities are resolved; composite prose and generic affix patterns still require review.
- Planner association is not endorsement: shared, testing, historical and unreferenced profiles remain candidates.
- Variant JSON files currently supply planner links; arbitrary prose in those files is not fully imported.
- Build-wide stat prose is not a reviewed slot-specific executable stat/roll rule.
- Set companions and socket upgrades are preserved as setup text, not evaluated against the captured item.
- Guide mention context can be incomplete; retained mentions are discovery evidence, not required gear.
- Missing source downloads and current guide changes cannot be resolved by an offline audit.
- Full price coverage is separate: only verified NL observations matching the actual variant may price an item.

missing_named_watch: `[]`

ledger_builds_not_imported: `[]`

variant_files_without_imported_build: `[]`

unavailable_planners: `{"1r010653": {"status": "source_download_failure404", "response": {"error": "Profile not found"}}}`

named_prose_candidates_missing_watch: `["Bane's Oathmaker", "Bane's Wraithskin", "Crafted Cold Rupture", "Death Cleaver"]`

## Per-build coverage

| Build | Occurrences | Mercenary | Unresolved |
| --- | ---: | ---: | ---: |
| abyss-warlock-build-guide | 259 | 35 | 52 |
| berserk-barbarian | 516 | 119 | 163 |
| blessed-hammer-paladin | 371 | 95 | 104 |
| blizzard-sorceress | 396 | 78 | 118 |
| blood-boil-warlock-guide | 103 | 39 | 12 |
| double-throw-barbarian-guide | 575 | 102 | 205 |
| dragon-talon-assassin | 207 | 22 | 46 |
| dream-paladin | 407 | 108 | 110 |
| echoing-strike-warlock-guide | 322 | 45 | 68 |
| enchant-sorceress | 342 | 89 | 78 |
| fire-blast-assassin | 268 | 73 | 68 |
| fire-wall-sorceress-guide | 155 | 50 | 33 |
| fire-warlock-guide | 326 | 43 | 72 |
| fissure-druid | 528 | 147 | 176 |
| fist-of-the-heavens-paladin | 361 | 91 | 94 |
| frozen-orb-meteor-sorceress | 149 | 50 | 33 |
| frozen-orb-sorceress | 151 | 50 | 34 |
| gold-find-barbarian | 294 | 63 | 102 |
| hydra-sorceress | 127 | 36 | 25 |
| lightning-fury-amazon-guide | 416 | 104 | 84 |
| lightning-sentry-assassin | 367 | 72 | 135 |
| lightning-sorceress | 518 | 112 | 161 |
| lightning-strike-amazon | 489 | 117 | 180 |
| meteor-sorceress | 401 | 81 | 132 |
| mirrored-blades-warlock-guide | 242 | 41 | 53 |
| nova-sorceress-guide | 292 | 65 | 65 |
| poison-nova-necromancer | 516 | 115 | 171 |
| smite-paladin | 268 | 25 | 79 |
| strafe-amazon | 325 | 48 | 70 |
| summoner-necromancer-guide | 327 | 96 | 127 |
| summoner-warlock-guide | 108 | 38 | 18 |
| wake-of-fire-assassin | 309 | 39 | 122 |
| zeal-paladin | 276 | 54 | 73 |

Full unresolved labels, source locators, variants and possible named matches: `pricing/data/appraisal-demand-audit.json`.
Reproduce after builds → valuable → index rebuild: `uv run --offline python -m pricing.knowledge.demand_audit`.
Classifier contract: [ASSESSMENT_DESIGN.md](ASSESSMENT_DESIGN.md).
