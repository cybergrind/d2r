# Equipped companion checks / Fire Blast ring — 2026-09-25

Second demand batch after movement-boots leveling tail. Resolves the previously
pending Phoenix branch of Fire Blast's Stone of Jordan use. Reuses the existing
three-valued predicate evaluator and immutable item facts; no new appraisal engine
or raw guide extraction. Estimated review effort:20minutes for the reusable slot
contract, malformed/partial-input boundaries and one source-dependent configuration.
No speedup claim; test durations and publication recorded in STATUS.md.

## Source and membership

One profile: `fire-blast-standard-soj-phoenix`.
`pricing/data/wp-a-builds.json#/fire-blast-assassin/variants/1`, SHA256
8a9da0d8cdd38e74d5b03721f5cf9de78e63c17ce87170cb706a6acfa31d59a2.
Role preserves the original guide date, URL and ring/amulet/shield/prose quotes.
Required total102FCR, actual crafted identified nonethereal amulet12+FCR and equipped
identified Phoenix Monarch in normal/superior quality. Source20FCR/+2skills are
illustrative, not required minima. Captured ring must be identified, nonethereal
unique Stone of Jordan with native ring identity. Skills desirable; flat/maximum
mana supporting. No fixed-stat roll targets or lightning attack-to-spell conversion.

The two mandatory companions are evaluated independently in the exact slots;
within each slot all predicates apply to one item. A name-only Phoenix/amulet list,
main total alone, swap/mercenary equipment or separate jewelry cannot prove the
combination. Unknown slot, incomplete stat capture and malformed values retain
unknown, while explicit empty slot or proved below-threshold modifier fails.
An input snapshot is copied and frozen; replacing context preserves its facts.

This increases reviewed SoJ breadth from8 to9builds (15variant uses), still Pending.
It does not establish complete skill allocation, survival, mana sustain or market
value. Keep the Spirit/Nagelring alternative pending; the Tri-Brid Paladin's
encounter/CBF/swap-breakpoint combination remains pending too. Other source labels
and planner/prose uses remain in the full census.

## Delivery and validation

New optional equipment-map API described in assessment/README.md. No automatic host
equipment collection is claimed. Live callers without explicit equipped facts get
conditional outcomes. Existing saved-item reports/prices are compared before and
after; supplied domain fixtures verify positive, near-miss, unknown, wrong-slot,
wrong-beneficiary, mutation and publication-language constraints.

Evidence tmp/equipment-* and tmp/fire-blast-companion-*. Source rule and snapshot
copy failures were reproduced red before implementation. Next scheduled batch must
cover specialist/leveling/unresolved work. Restart the worker for Python changes.

Follow-up2026-09-25: The explicitly cited Spirit/Nagelring alternative is now
reviewed in NAGELRING_BATCH.md. Other Spirit jewelry permutations remain unreviewed.
