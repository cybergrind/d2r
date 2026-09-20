---
name: lootfilter
description: Explain or change the D2R in-game loot filter profiles in lootfilter/ (why an item is shown or hidden, add/remove a rule, verify item codes); knows the filter's evaluation semantics and import limits.
---

# Loot filter

Profiles: `lootfilter/warlock_lean.json` (profile "Warlock Lean", 12 rules, the one in use) and
`lootfilter/warlock_echoing_strike.json` (profile "General (ALL)", 23 rules, the older per-class one).
The rule table with the reason per rule: `guides/warlock.html` §6. Pickup rules the filter implements:
`guides/pindle-anya.html` §3 (`PK-*`) and `pricing/data/wp-d-pickup.json` (a `why` per key);
`guides/warlock.html` §5 = the subset that matters for this build.

## Semantics (verified in-game and from icy-veins / diablobytes / diablo2.io PSA, 2026-09-18)

- **Show always beats Hide; rule order is irrelevant.** Working pattern: one "HIDE All" rule plus Show
  exceptions.
- Within a rule: rarity AND quality AND (categories OR item codes).
- `equipmentRarity: ["normal"]` also matches gray socketed/ethereal white bases;
  `filterEtherealSocketed: true` matches gray items. "hiQuality + flag, no normal" = show Superior and gray
  bases, hide plain 0os whites.
- Category codes: `acce` rings/amulets/charms/jewels; `armo`/`weap` parents; class: `assas amazo sorce
  palad barbh necro druid warlo`; `daggs circl glove boots belts shlds`. `itemCategory`: `misc` (all
  non-equipment), `gems`, `runes`, `potis`, `uberm`, `terrt`, `absol`; `goldFilterValue` = pile threshold.
- **Import limits**: top-level `name` ≤ 13 chars or the game says "invalid profile code"; rule names
  ≤ 32 chars, characters `[A-Za-z0-9 _\-/.,]`; keep armor and weapon item codes in separate rules.

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
3. After editing: keep `guides/warlock.html` §6 rule table in sync, and log a dated pass in its Review log.
4. Verify in-game with Alt after import; the game's toggle for "Show Items" resets every game (no fix).
5. Another session sometimes edits `guides/warlock.html` and `lootfilter/warlock_lean.json` concurrently;
   re-read before writing.
