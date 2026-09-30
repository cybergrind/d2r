# Caster leveling options — 2026-09-26

Scheduled leveling tail after Magefist and Fire Blast starter rings. Reused the
cached utility occurrences, pinned source hashes and native item facts; no new
extraction or market collection. Reviewed eleven uses across seven identities and
three classes. Review effort estimate: fifteen minutes; test execution: 7.27 seconds.

## Reviewed source membership

| Class | Item | Exact source locator |
|---|---|---|
| barbarian | Skin of the Vipermagi | `after-level-31-respec-header/item/141@(86, 1482)` |
| barbarian | Magefist | `after-level-31-respec-header/item/142@(86, 1635)` |
| barbarian | The Eye of Etlich | `after-level-31-respec-header/item/143@(86, 2330)` |
| barbarian | The Stone of Jordan | `after-level-31-respec-header/item/147@(86, 2851)` |
| barbarian | Arreat's Face | `after-level-31-respec-header/item/148@(86, 3173)` |
| paladin | The Eye of Etlich | `after-level-18-respec:-header/item/99@(82, 2924)` |
| paladin | The Stone of Jordan | `after-level-18-respec:-header/item/103@(82, 3445)` |
| druid | The Eye of Etlich | `essentials-header/item/83@(79, 1428)` |
| druid | The Stone of Jordan | `essentials-header/item/87@(79, 1949)` |
| druid | Lidless Wall | `essentials-header/item/89@(79, 2332)` |
| druid | Jalal's Mane | `essentials-header/item/91@(79, 2563)` |

## Mechanics and scope

Barbarian uses belong after the level 31 caster respec; Paladin jewelry after
level 18 respec. These guide stages do not replace native equip levels. Magefist
supports War Cry cast rate; its fire-skill bonus does not improve War Cry. Arreat’s
class skills and resistances remain useful, but attack rating does not improve
War Cry. Etlich is an alternative to class/tree amulets; SoJ is an option if already
available, not a required purchase or an inferred market valuation.

Druid Lidless Wall requires resistance coverage elsewhere before replacing
Ancient’s Pledge. Retain Splendor as an alternative. Jalal’s guide excerpt says
“+2 to All Skills”; native `uniqueitems:287` establishes +2 Druid skills (`dru`),
30 hit recovery and 30 all resistance. Correct the recommendation without changing
the original source excerpt. Lore/rare pelts can offer more damage depending on
their actual skills. Native records also verify Arreat’s (`279`), Magefist (`105`),
Vipermagi (`210`), Etlich (`118`), SoJ (`122`) and Lidless (`230`).

## Provenance

- leveling-barbarian: `b83f0f5b1d3601577d20aa35bf285b87f9eaa700b11af922321c7de076f6c7d6`, original date 2026-05-22T13:15:16+00:00.
- leveling-paladin: `284adcd129cd42c0867dce4792102832b537fd2861b3a56e26e203a8af05220c`, original date 2026-05-22T20:12:00+00:00.
- leveling-druid: `7b8d388deb56021c517f60d0f6385583eca5d00fe6111fecf62c433f1604760a`, original date 2026-05-22T13:15:58+00:00.

## Verification and publication

Red: three missing class groups plus the missing runtime recommendation test.
Green: 65 recommendation/runtime tests; lint, formatting and diff checks passed.
Tests preserve source invalidation, class/archetype, conditional advice, native
equip levels (including below-level rejection), and no invented prices.
All eighteen saved report texts and prices unchanged before/staged publication.
Published generation: `01012c886719ec11380a6a6ed040bcc68941b5010f1318226511fe129855f103`.

126 leveling recommendations (previously 115); role/stat configurations unchanged
(530/522). This is a maintenance adapter/data update; no new worker restart.
Evidence: `tmp/caster-leveling-*`. Final parity and matrix counts in STATUS.md.

Tail complete. Next: resume demand/family review, selecting by distinct builds
and uncovered identities per reviewed rule from the current dossiers. Reserve
another tail after two demand batches. Still pending: all-identity named tiers,
preferred-base/socket/ethereal policies, affixed combinations, further leveling
and unresolved source uses, and sufficiently matched scoped market cohorts.
