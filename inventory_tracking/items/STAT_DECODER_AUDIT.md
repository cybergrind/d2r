# Native-stat decoder gap audit

2026-09-25. Audit and subsequent fixes use local d2data and saved observations;
no live game probe or online lookup.

## Fix result (2026-09-25)

All eight candidates below now have reviewed handling. Replaying the same 458
saved observations leaves **zero unresolved stat IDs**, down from three.
Routing coverage is now 195/367; the remaining 172 IDs are outside this reviewed
item-effect scope. No unsupported IDs remain in the audit's explicit item/set
property-reference join. Routing coverage still does not prove all-value coverage.

- Defense accepts signed values; other totals/counters retain nonnegative guards.
- Reanimate decodes the verified Returned target (monstats hcIdx1). Unknown
  monster parameters stay unresolved rather than being mislabeled Returned.
- Quest difficulty 0/1/2 is an internal Normal/Nightmare/Hell diagnostic.
- Stat219 uses the op5 level-derived percentage, with valid viewer context. It
  is not added to displayed weapon damage as though it were a flat damage bonus.
- Magic piercing uses the local ModStrMagPierce wording and retains the native
  magnitude for range annotations. No market property ID is invented.
- Extra blood and fade are internal visual-effect diagnostics, not skill bonuses.
- The two catalog set states (175 fullsetgeneric, 176 monsterset) are internal
  diagnostics when captured. They are never inferred from item identity or used
  to assert that a full set is active; unknown states remain unresolved.

Regression coverage: tests/inventory_tracking/items/test_audited_stats.py.
The following sections preserve the before-fix evidence and scope.

## Original result

**3 distinct native stat IDs still fail on saved item observations.** Another
**5 IDs have no decoder route and are referenced by item/set definitions**, giving
**8 practical review candidates**, not eight proven item-tooltip bugs.

| ID | Meaning | Evidence | Priority / interpretation |
| --- | --- | --- | --- |
| 31 | Defense, negative values | Dimoak's Hew: layer0/raw-8 | Confirmed decoder rejection; total decoder incorrectly excludes this signed modifier. |
| 155 | Reanimate | Tomb Reaver: layer1/raw10 | Confirmed missing parameterized decoder. |
| 356 | Quest item difficulty | Wirt's Leg: layer0/raw2 | Confirmed unreadable internal metadata; should be classified, not priced as an affix. |
| 219 | Enhanced maximum damage per level | Eaglehorn, Hellslayer, Messerschmidt's Reaver definitions | Missing op5 level-formula route; not encountered in scanned captures. |
| 358 | Magic resistance piercing | Ars Dul'Mephistos, Sling, Gheed's Wager, Unique Warlock Helm source definitions | Missing template/label; not encountered in scanned captures. Source names retained verbatim. |
| 140 | Extra blood | Gorefoot, Swordback Hold definitions | Cosmetic/internal effect; prospective item-capture gap. |
| 181 | Fade | Natalya's Odium set definition | Set effect; verify whether it appears on item or player stats before adding an item decoder. |
| 98 | State | Seven set definitions | Encoded state effect; verify storage/context before adding an item decoder. |

Gameplay priorities: 31, 155, 219, 358. Internal classification candidates:
356, 140, 181, 98. Stat160 is fixed and excluded.

## Scope and method

- Bundled metadata contains 367 distinct native stat IDs.
- 188 have an explicit decoder, scalar label, supported level/proc route, or
  poison aggregation route. This is routing coverage, not exhaustive validation
  of every value, parameter, source context, or tooltip rendering.
- 179 have no such route. This broad engine catalog includes unused, player,
  skill, and internal stats; it is **not** a count of 179 broken item affixes.
- Six unsupported IDs are directly referenced through properties.json stat
  fields by spawnable unique/set items, spawnable prefix/suffix/automagic rows,
  completed runewords, gems, or set bonuses: 98, 140, 155, 181, 219, 358.
- Scanned all 467 frozen.json files under inventory_tracking/runs. 458 contain
  captured native rows in observation.decoded_stats, spanning 117 stat IDs.
  Reassembled original memory_stat/memory_stats entries and reran current
  decode_stats, retaining aggregation. Repeated captures are not unique items.
- Supplied the captured item's base and recorded viewer level. For older captures
  lacking viewer context, used level91 to isolate decoder support from missing
  context. All three failing examples have an actual recorded level91.
- This audit does not validate source extraction completeness, rolled ranges,
  price-facet mappings, live UI refresh, or every input accepted by a decoder.
  Properties implemented through implicit function semantics rather than explicit
  stat fields may add further candidates. Set effects need storage verification.

## Saved examples

- Stat31, Dimoak's Hew: `inventory_tracking/runs/alt-d/20260925T100411Z-4a74bcd3/request-1/frozen.json`
- Stat155, Tomb Reaver: `inventory_tracking/runs/alt-d/20260923T213532Z-be6ed17d/request-51/frozen.json`
- Stat356, Wirt's Leg: `inventory_tracking/runs/alt-d/20260923T213532Z-be6ed17d/request-4/frozen.json`

## Sources

- inventory_tracking/items/stats.py and stat_constants.py: dispatch and validation.
- inventory_tracking/items/metadata.py and poison.py: output and aggregation.
- inventory_tracking/items/data/item_metadata.json: current runtime catalog.
- third-parties/d2data/json/{properties,itemstatcost,uniqueitems,setitems,runes,
  magicprefix,magicsuffix,automagic,gems,sets}.json: local definition references.

Audit scratch details: /tmp/d2r-stat-audit.json; script: /tmp/d2r-stat-audit.py.
