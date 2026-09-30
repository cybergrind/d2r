# Fortitude armor family — 2026-09-26

Second demand batch after Hammerdin MF reconciliation (first: Shaftstop). Reused
cached WP-A variants and pinned native Fortitude recipe; no fresh collection,
re-extraction or live captures. Estimated review effort: thirty minutes.
Twenty-five configurations across fourteen distinct builds.

| Build | Variant index | Beneficiary | Base | Mercenary type |
|---|---|---|---|---|
| abyss-warlock-build-guide | 1 | merc | Sacred Armor | Act 2 Might |
| abyss-warlock-build-guide | 2 | merc | Sacred Armor | Act 2 Might |
| blessed-hammer-paladin | 1 | merc | Sacred Armor | Act 2 Holy Freeze |
| blessed-hammer-paladin | 3 | merc | Sacred Armor | Act 2 Holy Freeze |
| blizzard-sorceress | 1 | merc | Sacred Armor | Act 2 Might |
| blizzard-sorceress | 3 | merc | Sacred Armor | Act 2 Might |
| double-throw-barbarian-guide | 1 | player | Archon Plate | — |
| fire-blast-assassin | 1 | merc | Sacred Armor | Act 2 Might |
| fire-warlock-guide | 1 | merc | Archon Plate | Act 2 Might |
| fire-warlock-guide | 2 | merc | Archon Plate | Act 2 Might |
| fist-of-the-heavens-paladin | 2 | merc | Sacred Armor | Act 2 Might |
| fist-of-the-heavens-paladin | 4 | merc | Sacred Armor | Act 2 Holy Freeze |
| lightning-fury-amazon-guide | 1 | merc | Sacred Armor | Act 2 Might |
| lightning-fury-amazon-guide | 2 | merc | Sacred Armor | Act 2 Might |
| lightning-sentry-assassin | 1 | merc | Sacred Armor | Act 2 Holy Freeze |
| lightning-sentry-assassin | 2 | merc | Sacred Armor | Act 2 Holy Freeze |
| lightning-sorceress | 1 | merc | Sacred Armor | Act 2 Might |
| lightning-sorceress | 2 | merc | Sacred Armor | Act 2 Might |
| meteor-sorceress | 1 | merc | Sacred Armor | Act 2 Might |
| meteor-sorceress | 3 | merc | Sacred Armor | Act 2 Might |
| poison-nova-necromancer | 1 | merc | Sacred Armor | Act 2 Might |
| poison-nova-necromancer | 2 | merc | Sacred Armor | Act 2 Might |
| strafe-amazon | 1 | player | Archon Plate | — |
| strafe-amazon | 2 | player | Archon Plate | — |
| wake-of-fire-assassin | 1 | merc | Sacred Armor | Act 2 Might |

## Shared rules and retained distinctions

Completed, identified normal/superior armor; four filled sockets; exact named base;
nonethereal player versus ethereal mercenary scope. Mercenary type gates retain
the reviewed source subtype. Other bases/statuses remain outside these narrow
configurations, not a universal negative appraisal. Weapon Fortitude is explicitly
excluded from these armor uses despite sharing the recipe name.

Native El/Sol/Dol/Lo recipe,300%ED,200%enhanced defense and25–30resistance range
verified in `third-parties/d2data/json/runes.json#/Fortitude`. Observed physical ED
(native17/18) desirable; defense16 and resistances39/41/43/45 supporting. This is
off-weapon physical damage support, not spell/trap damage or a multiplier of total
damage.25FCR is not physical attack speed. Minimum resistance rolls remain useful;
no perfect defense/life/roll requirement or price premium inferred.

Preserve complete weapon/helmet/IAS/leech/equip requirements. Insight/Infinity
mana or immunity support comes from the weapon; armor alone does not establish
it. Poison Nova mercenary physical damage helps create a first corpse, while
Infinity supports Corpse Explosion’s fire component. Strafe keeps Faith/Hustle/IAS
qualifications. Double Throw keeps weapon-swap casting separate from main attacks.

Blizzard Standard armor utility is independently supported while its Insight versus
Infinity weapon conflict remains explicit; Set Build retains the Cold Rupture /
Insight alternative. Historical ebug descriptions remain original evidence but
cannot prove extra captured defense or a price premium. FoH Holy Bolt Support is
specifically referenced by guide prose; this does not endorse arbitrary planners.

Deferred: Fissure Standard/MF Might-versus-Holy-Freeze discrepancy, Mirrored Ubers
Fortitude-versus-CoH discrepancy, unendorsed planner-only Fire Blast Damage,
Poison Nova Max Damage and Wake Sunder examples, Hardcore-only uses and remaining
gear-table leads. Fourteen reviewed builds is a disclosed lower bound, not closure.

## Verification

Red:26missing role/demand tests. Green:42family/stat/source/demand/publication checks
in14.30seconds; lint/format passed. Tests exercise both qualities, exact armor/weapon
distinction, identity/recipe/sockets/base/ethereal/mercenary boundaries, observed-only
annotations, no attack benefit from FCR, and distinct-build counting. Existing roll
ranges and price semantics are unchanged. Saved replay/publication checkpoint in
STATUS.md. Evidence:`tmp/fortitude-*`.

589roles /581stat configurations;126leveling recommendations retained. Data-only;
no new worker restart. Next must be specialist/leveling/unresolved tail. Review a
specific deferred source discrepancy rather than silently broadening rules. Full
named tiers, base desirability, affixed/leveling closure and exact prices remain
unfinished.
