# Assassin leveling pair and armor — 2026-09-25

Scheduled tail after Fire Blast affixed jewelry and Nagelring demand batches.
Three explicit class-specific recommendations reuse the cached utility extraction,
source gates and existing leveling evaluator. Review estimate: five minutes for
pair/standalone and shield distinctions; no measured speedup claim.

| Item | Source locator under essentials-header/item/ | Reviewed use |
|---|---|---|
| Death's Hand | 86@(77, 80) | Pair with Death's Guard for attack speed/resistances |
| Death's Guard | 87@(77, 149) | Same pair; Cannot Be Frozen belongs to belt itself |
| Twitchthroe | 92@(77, 1518) | Attack speed/recovery; blocking requires shield |

Source leveling-assassin dated 2026-05-22, cached assassin.html SHA256:
548d7b8483f02428f7ebe5be5ac8f0f2e00d10fa2387292c085bba3c4941853b.
Native setitems records47/48 confirm two-piece bonuses (30IAS on gloves,
15allres on belt), with nofreeze intrinsic to belt. Uniqueitems record82 confirms
Twitchthroe20IAS/20FHR/25blocking. Native equip levels6/6/16 remain independently
checked by the existing runtime. Ancient's Pledge is source-supported companion
advice, not proof that the captured item completes a loadout. The guide emphasizes
Twitchthroe for Hardcore but recommends it generally; this does not import Hardcore
market evidence into the Softcore KB.

These are high leveling priorities, not market tiers or prices. No set bonus is
synthesized into captured stats, and a missing companion remains conditional.
Other classes' pair uses and remaining Assassin leveling items stay queued.

Three failing adapter cases reproduced missing recommendations; all50 affected
recommendation/runtime-leveling/coverage tests pass. Exact locator/hash changes
remove recommendations. Unknown equip facts stay unknown; unidentified items and
impossible ethereal sets are rejected. All18 saved reports and prices unchanged.
No live probes or market requests. Evidence: tmp/assassin-leveling-*.
