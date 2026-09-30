# Opalvein random modifier — unresolved source gap

Reviewed 2026-09-28 during Abyss ring-table assessment. This is required range
work, not a completed review of every Opalvein variant.

Native `third-parties/d2data/json/uniqueitems.json`, entry 416, uses
`magdam-rand` with min=max=1. That value selects a randomized property; it must
not become a fixed +1 damage annotation. The local `properties.json` does not
contain its implementation. Current named metadata therefore has no complete
range model for this modifier.

Observed cached planner examples (under `pricing/raw/mr/planners/`):

| File / item | Selector | Observed modifier |
| --- | --- | --- |
| gsg0p0l0.json / 160 | 0 | Magic Skill Damage 5 |
| 300106ye.json / 81 | 0 | Magic Skill Damage 3 |
| uuleu0ob.json / 134 | 2 | Fire Skill Damage 5 |
| tbaq40od.json / 54 | 3 | Cold Skill Damage 5 |
| rg2je0ld.json / 149 | 1 | Enhanced weapon damage 40 |
| ucgz20le.json / 148 | missing | No resolved random modifier |

These samples establish observed types/values, not complete roll bounds. Do not
infer maximum/minimum values, full selector coverage or probabilities from them.

The Abyss role credits observed magic damage only. Fire and physical variants
retain FCR, resistance and recovery utility without receiving magic-damage credit.
An unread random variant does not imply the magic variant. The item bank exercises
all three states. These runtime contributions do not discharge this range gap.

Remaining work: locate authoritative local selector implementation or verified
complete game definitions, enumerate all legal variants and bounds, add independent
native-stat/range tests, regenerate metadata and publication, and review other
caster roles (including Fire Warlock) against the observed damage type.

Separately verified: native `att-skill` function 11 uses min as chance and max as
level: 2% chance to cast level 15 Flame Wave on attack. The cached planner reverses
chance and level; preserve the original cache while decoding native semantics.
