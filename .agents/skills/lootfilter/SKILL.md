---
name: lootfilter
description: Explain or change the D2R in-game loot filter profiles in lootfilter/ (why an item is shown or hidden, add/remove a rule, verify item codes); knows the filter's evaluation semantics and import limits.
---

# Loot filter

Profiles: `lootfilter/warlock_lean.json` (profile "Warlock Lean", 13 rules; "SHOW Craft Bases ARMOR" = craft-only fodder the player may disable),
`lootfilter/warlock_lean_v2.json` (profile "Warlock Lean2", 16 rules, 2026-10-09: Lean with uniques and sets shown **by base**;
**generated** by `uv run --offline python -m inventory_tracking.loot.build_filter`, never hand-edited — edit Lean, then regenerate;
`lootfilter/warlock_lean_v2.names.json` says per unique/set name whether it shows and why) and
`lootfilter/warlock_echoing_strike.json` (profile "General (ALL)", 23 rules, the older per-class one).
"Why is unique X hidden?" → look its name up in the names sidecar; the evidence rules are in the generator's docstring.
The rule table with the reason per rule: `guides/warlock.html` §6. Pickup rules the filter implements:
`guides/pindle-anya.html` §3 (`PK-*`) and `pricing/data/wp-d-pickup.json` (a `why` per key);
`guides/warlock.html` §5 = the subset that matters for this build.

## Semantics (verified in-game and from icy-veins / diablobytes / diablo2.io PSA, 2026-09-18)

- **Show always beats Hide; rule order is irrelevant.** Working pattern: one "HIDE All" rule plus Show
  exceptions.
  Consequence: an item kind cannot be hidden "by base" while a broad Show rule covers it; narrow the Show
  rule to a base-code list instead (Lean2 does this for uniques/sets; drop `equipmentCategory` from such a
  rule, since category OR codes would re-show everything).
- Within a rule: rarity AND quality AND (categories OR item codes).
- `filterEtherealSocketed: false` does **not** exclude ethereal items: Lean's unique rule (flag false) let
  six ethereal uniques through 2026-09-29…10-07 (collection DB: Bladebuckle, Shadow Killer, Tearhaunch…).
  The flag only adds gray items, so the filter cannot show a base non-ethereal-only or ethereal-only; eth
  vs non-eth is decided after pickup (KB: eth gloves/boots/belts price as non-eth).
- `equipmentRarity: ["normal"]` also matches gray socketed/ethereal white bases;
  `filterEtherealSocketed: true` matches gray items. "hiQuality + flag, no normal" = show Superior and gray
  bases, hide plain 0os whites.
- Category codes: `acce` rings/amulets/charms/jewels; `armo`/`weap` parents; class: `assas amazo sorce
  palad barbh necro druid warlo`; `daggs circl glove boots belts shlds`. `itemCategory`: `misc` (all
  non-equipment), `gems`, `runes`, `potis`, `uberm`, `terrt`, `absol`; `goldFilterValue` = pile threshold.
- **Import limits**: top-level `name` ≤ 13 chars or the game says "invalid profile code"; rule names
  ≤ 32 chars, characters `[A-Za-z0-9 _\-/.,]`; keep armor and weapon item codes in separate rules.
  A rule with 107 item codes imports fine (Lean2, 2026-10-09), so code-list length is not a known limit.

## Rules for changing it

1. **Never write an item code from memory.** Fetch the d2data dump
   (`https://raw.githubusercontent.com/blizzhackers/d2data/master/json/weapons.json`, `armor.json`,
   `misc.json`) and grep the code; a wrong code silently shows the wrong item and hides the right one.
   Known traps: belts vbl/zvb/uvc (not xtb/utc); Amazon javelins am5 Maiden / ama Ceremonial /
   amf Matriarchal; Ceremonial Javelin is `ama`, not `am7`.
2. **Hide by the runeword test only for white bases** (socket max / exact count). For rares and blues,
   hide only when the slot has no staff-mods and no build-named pattern. "Not named in a build list or
   thread" is not "worthless": check `pricing/data/wp-b-prices.json` rare/magic buckets and
   `wp-a-blues.json` first. Rare class items with staff-mods, rare Warlock daggers, rare Amazon
   javelins/spears and magic gloves stay shown (the 2026-09-18 audit hid them and was reverted).
   2026-10-09 audit: a rare paid pattern in `pricing/triage/import_class_rules.py` is **asks only**; before
   showing or hiding a rare family, check demand — Traderie buy side (`listings?item=<id>&selling=false`, scoped
   props) and offers received (`total_offers` in the raw pulls), plus diablo2.io `activesold=1`. Verified that day:
   normal-tier daggers (Dagger/Dirk/Poignard/Rondel), wands and the eleven non-elite Paladin shield bases have no
   rare buyers and ~0 offers → hidden; all claws (`assas`) and the elite scepters (7sc 7ws 7qs) draw offers at the
   Legend Spike rate → shown. Evidence: `pricing/raw/traderie/buy-side-20261009/`, warlock guide §6 review log.
3. After editing: keep `guides/warlock.html` §6 rule table in sync, and log a dated pass in its Review log.
4. Verify in-game with Alt after import; the game's toggle for "Show Items" resets every game (no fix).
5. Another session sometimes edits `guides/warlock.html` and `lootfilter/warlock_lean.json` concurrently;
   re-read before writing.
