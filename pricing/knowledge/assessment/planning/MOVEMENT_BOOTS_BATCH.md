# Movement boots leveling review — 2026-09-25

Scheduled tail after Tal helm and Goldwrap demand batches. One shared movement
utility template covers Hsarus’ Iron Heel and Sander’s Riprap across all eight
cached class guides. Eight new guide recommendations; eight existing guide entries
now explicitly describe standalone movement utility. Review-effort estimate:
5 minutes for repeated movement advice and two section-context exceptions; no
speedup factor claimed. Existing extraction reused without downloading/re-extracting.

The separate transcript’s Hsarus two-piece attack-rating recommendation remains
conditional. Guide movement utility does not depend on that bonus or a second piece.
Barbarian advice retains the after-level31-respec context; Paladin retains the
after-level18-respec context. These are source contexts, not invented native equip
levels. Verified native levels are3 for Hsarus and20 for Sander; requirements come
from item facts. Set items marked ethereal and unidentified items are rejected.

Qualitative leveling priority remains Hsarus3/med and Sander1/high. No trade price,
trade tier, demand breadth or new stat annotation follows from this review.
Exact identity, source hash and source locator gates still apply; ambiguous/missing
or changed source evidence cannot produce active advice.

## Explicit reviewed membership

| Class | Item | Locator |
|---|---|---|
| assassin | Hsarus' Iron Heel | `essentials-header/item/90@(77, 1027)` |
| assassin | Sander's Riprap | `essentials-header/item/91@(77, 1103)` |
| barbarian | Hsarus' Iron Heel | `after-level-31-respec-header/item/145@(86, 2495)` |
| barbarian | Sander's Riprap | `after-level-31-respec-header/item/146@(86, 2571)` |
| druid | Hsarus' Iron Heel | `essentials-header/item/85@(79, 1593)` |
| druid | Sander's Riprap | `essentials-header/item/86@(79, 1669)` |
| paladin | Hsarus' Iron Heel | `after-level-18-respec:-header/item/101@(82, 3089)` |
| paladin | Sander's Riprap | `after-level-18-respec:-header/item/102@(82, 3165)` |
| amazon | Hsarus' Iron Heel | `essentials-header/item/104@(78, 1719)` |
| amazon | Sander's Riprap | `essentials-header/item/105@(78, 1795)` |
| sorceress | Hsarus' Iron Heel | `essentials-header/item/83@(77, 979)` |
| sorceress | Sander's Riprap | `essentials-header/item/84@(77, 1055)` |
| necromancer | Hsarus' Iron Heel | `essentials-header/item/86@(74, 1198)` |
| necromancer | Sander's Riprap | `essentials-header/item/87@(74, 1274)` |
| warlock | Hsarus' Iron Heel | `essentials-header/item/47@(90, 80)` |
| warlock | Sander's Riprap | `essentials-header/item/48@(90, 156)` |

## Source snapshots

Original guide dates are preserved from the utility manifest (2026-05-22; Warlock2026-07-14).
All eight cached file hashes verified against the current files.

- leveling-amazon: `928aa47e197f786f002ec34997219ef33228aa986090ca9281d44d322eadd749`
- leveling-assassin: `548d7b8483f02428f7ebe5be5ac8f0f2e00d10fa2387292c085bba3c4941853b`
- leveling-barbarian: `b83f0f5b1d3601577d20aa35bf285b87f9eaa700b11af922321c7de076f6c7d6`
- leveling-druid: `7b8d388deb56021c517f60d0f6385583eca5d00fe6111fecf62c433f1604760a`
- leveling-necromancer: `a447a857cfc20421a9fa6531c94b083576dd50f14d460dd549558440854ff844`
- leveling-paladin: `284adcd129cd42c0867dce4792102832b537fd2861b3a56e26e203a8af05220c`
- leveling-sorceress: `aef55f953d6e1f96d60d6479e2b94d24e8ba88f46fc5d6de1c21fa40b3707b96`
- leveling-warlock: `201e5010f374ef9126a1c3ccc62b4fe49f4f1f015935bee8713498744a8596d8`

## Validation

Eight failing adapter cases and one failing runtime case reproduced before rebuild.
394 recommendation/policy/maintenance tests pass (5.57s); Ruff/format/diff checks
pass. All18 saved report texts and price estimates remain unchanged. This batch
uses domain fixtures; no live probe or numerical market collection. See STATUS.md
for published generation and updated coverage. Evidence: tmp/boots-leveling-*.

Tail batch complete. Continue demand/family work from the full review queues.
This closes the reviewed movement-boot guide membership, not all leveling items,
all named tiers, affixed combinations, base desirability or price coverage.
