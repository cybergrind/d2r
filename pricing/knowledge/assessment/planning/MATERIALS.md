# Materials-tab market coverage

Requested 2026-10-06. Scope: Softcore / Non-Ladder / PC / RotW. Currency: Ist = 1.
This is a focused workstream under PLAN.md, not a replacement completion contract.

## Goal and completion criteria

Every Materials-tab identity has a market entry, even when the current sample has
no usable asks. Appraisal distinguishes unit price, actual sale-sized lots and
complete recipe sets. Never recommend discarding tradeable materials because the
unit price is below 0.25 Ist; use CHECK/save toward a supported sale lot where
appropriate. Keep multiple valuable copies. Seller activity is a liquidity proxy,
not proof of completed sales.

Done means all entries below are mapped to verified native/catalog identities;
listing units and stock semantics are resolved or explicitly unavailable; supported
prices reach Alt+D and automatic triage; and positive/negative quantity and set
cases pass. Fetching pages alone does not meet these criteria.

## Inventory

The machine-readable inventory is [materials-catalog.json](materials-catalog.json).
Names/codes come from local misc and English-string tables; market IDs come from
the cached Traderie catalog. The screenshot includes empty dedicated organ slots
and empty essence slots: those identities belong in scope too.

| Group | Individual entries |
|---|---|
| Pandemonium keys | Key of Terror; Key of Hate; Key of Destruction |
| Organs | Baal's Eye; Diablo's Horn; Mephisto's Brain |
| Ancient statues | Talic's Anguish; Korlic's Pain; Madawc's Ire; Bul-Kathos' Nightmare; Worusk's End |
| Worldstone shards | Western; Eastern; Southern; Deep; Northern Worldstone Shard |
| Respec materials | Twisted Essence of Suffering; Charged Essence of Hatred; Burning Essence of Terror; Festering Essence of Destruction; Token of Absolution |
| Potions | Rejuvenation Potion; Full Rejuvenation Potion |
| Additional material coverage | Standard of Heroes; Defender's Fire; Defender's Bile; Protector's Frost; Protector's Stone; Guardian's Thunder; Guardian's Light |
| Separately listed bundles | 3x3 Key Set; Statue Set; Shard Set |

Thirty individual items plus three market bundles. The six Ancient upgrade items
are listed as uniques by Traderie; preserve that identity instead of recategorizing
them as generic misc. Additional material coverage extends beyond the visible tab.
Do not price a shard set until its listing composition is verified. A 3x3 key set
contains nine keys; it is neither one key nor a one-of-each set. Whole-set quotes
must never be applied to individual components. One-of-each keys, organ sets and
four-essence recipes may have a clearly labeled component sum; that is not an
observed bundle ask and must not be presented as one.

## Execution order

1. **Inventory and collection.** Add all 33 entries; fetch one page per exact catalog
   ID, paced three seconds apart, stop on the first source error. Preserve scope,
   seller, ask alternatives, quantity, stock flags and timestamps. Resume successful
   pages without refetching. No buy-side collection or seller-listing creation.
2. **Resolve units before prices.** Implemented for 24 exact misc material identities:
   native/catalog names are reviewed in `pricing.knowledge.material_items`.
   Finite lots require explicit `stock: false`, matching catalog ID and positive
   integer quantity; their total ask is divided by lot size. Stock/unknown-stock
   offers remain ambiguous. Recipe bundles and unique-category upgrade materials
   are excluded from this blanket rule. Never divide available stock into a unit ask.
3. **Build offline bands.** Separate unit and quantity cohorts; deduplicate sellers;
   preserve source/conversion dates; show Q1 asks and activity with sample size.
   Reuse the existing commodity/triage pipeline. Verify the six unique-category
   materials use their actual identity and any applicable rolls.
4. **Keep/sell behavior.** Implemented sale-lot accumulation beyond runes/gems for reviewed
   fungible materials. A sub-threshold component may be worth accumulating. Show
   unit ask, supported sale lot and stack value; do not promise the entire stack
   will sell at one-unit pricing. Separate complete recipe-set opportunities and
   missing components. Never mark useful duplicate materials as discard candidates.
5. **Report and verify.** Both rejuvenation identities now route to misc, retain
   captured stack quantity and have their runtime route enabled. Fixtures cover
   key/shard/token/potion accumulation and split sales, stock versus finite lots,
   bundle/conflicting identities and potion capture routing. Remaining coverage:
   unknown quantities, mismatched scope, repeated sellers, key/set confusion,
   missing components and unavailable prices. Verify saved Materials-tab captures
   through Alt+D and automatic triage. Update this status with actual results.

## Collection and runtime status

- Authorized by the user's request to add listings for every Materials-tab item.
- Batch: `pricing/raw/traderie/pull-20261006-materials/`; `state.json` records targets.
- The 2026-09-23 session hold was inspected; this explicitly requested bounded
  collection is a new attempt and stops on source errors.
- Existing `pricing.tools.market_pull.pull_item` performs collection;
  `uv run --offline python -m pricing.triage.build` reads these cached pages.
- Per-entry collection and usable-band coverage: [materials-market-coverage.md](materials-market-coverage.md).
- Collection complete: 33/33 pages, 692 scoped asks, 12 entries with at least
  three usable priced sellers before material normalization. After normalization,
  30 entries have at least three priced sellers across quantities; 63 offers remain
  ambiguous (quantity-specific bands still require their own seller evidence).
- Offline triage bands rebuilt: 19,225 total / 15,242 priced; commodity cache refreshed.
  Runtime checks saved in `pricing/data/materials-runtime-check-20261006.json`: one
  Western shard CHECK/save 10; 51 shards sell in lots of 10; 96 full rejuvenations
  CHECK/save 100. Keys and tokens use supported single-item asks when available.
  423 affected triage, market, commodity, capture and reporting tests pass.
- Recorded recipe sets implemented for keys and statues, including shortages for
  the next complete set. Current collection replay: one 3x3 Key Set; next needs
  1 Terror + 2 Destruction. One Statue Set; next needs 1 Bul-Kathos' Nightmare.
  Dates come from matching material-slot observations. Gone placements and unknown
  quantities cannot manufacture complete sets; another placement's content-hash
  quantity cannot be reused. 326 appraisal/commodity tests pass.
- Pending: verified shard-set composition, unresolved stock offer units and broader
  saved-capture/UI validation. No inferred liquidity. Restart the worker for Python
  routing/lot/report changes.
