---
name: appraise
description: Price a D2R item from a pasted screenshot or tooltip ("worth?", "is it worth anything?"), SC/NL/PC/RotW, Ist = 1; produces the three-part report (price as is · what would make it worth more · why the loot filter shows it).
---

# Appraise an item

Scope: Softcore · Non-Ladder · PC · RotW, Ist = 1, player = Echoing Strike Warlock. Price from the repo,
never from web search (core rule 1 in `AGENTS.md`).

## Procedure — stop at the first step that settles it

1. **Transcribe the tooltip** before pricing: colour/rarity, base name, Superior/Ethereal, socket count,
   every affix with its number, required level, durability (3× normal = failed unique). Say what you read
   if the screenshot is ambiguous.
2. **Triage by colour** with `guides/pricing.html` §2 (white/gray → runeword base test; blue → pattern
   table; yellow → slot must-affix table; gold/green → primer §5 table, then appendix B; orange → the two
   sellable crafts), then the gates checklist §3 (exact sockets, ≥15 % ED for "Superior", 45@, +2 class,
   5/5 facet, +life on a skiller). A failed gate = floor or vendor whatever the rest says.
3. **Worked examples first**: `guides/pricing.html` §8 holds a verdict for every item the player already
   asked about; the primer's `#miss` checklist is the one-screen "looks like junk / is not" table. Reuse
   and cite the row when the item is there.
4. **Band from the data files** (asks pulled 2026-09-18 unless dated otherwise):
   - bases, rare/magic class items, gloves, circlets, grimoires, daggers →
     `pricing/data/wp-b-prices.json[<slug>]['buckets']`, keys `<n>os/<eth|noneth>/<rarity>[/15ed][/filled]`,
     fields `min_ist / median_ist / max_ist / n_priced / thin / cheapest[]`; `_blues` = build-named magic patterns.
   - uniques, sets, keys/essences/shards → `pricing/data/wp-i-uniques-misc.json` (`UQ-*`, `ST-*`, `MS-*`:
     `our_tier`, `roll_bucket`, `threshold`).
   - jewels, charms, facets, sunders, torch/anni → `pricing/data/wp-h-jewels-charms.json`.
   - runes, gems, currency → `pricing/data/wp-f-ladder.json` (field `ist`) or the card in `pricing.html` §0.
   - session verdicts, grimoire/staff-mod rankings → `pricing/data/addendum-2026-09-18-session.json`.
5. **Not in a data file ≠ worthless.** Before "vendor" on a rare, magic class item, unique or set: check
   the base's rare/magic buckets in `wp-b-prices.json`, `wp-a-blues.json`, and
   `pricing/data/wp-a-variants/index.json` (item name → builds / variants / merc slots; appendix B lists
   player main-slot gear only). Rare class items with staff-mods, rare Warlock daggers, rare Amazon
   javelins and magic gloves all have real buckets (eth rare +2 Warlock Mithril Points ask 171 Ist median;
   Sazabi's set is the S-tier guide's uber-merc kit).
6. **Recompute from the cache** when no bucket matches the roll: `pricing/raw/traderie/<slug>.json`
   (a bare list, or `{"listings": [...]}` for `wpi-*` / `wph-*`). Keep property 799 = "softcore",
   800 = false, 798 = "PC", 1854 not "lord of destruction"/"classic"; price = cheapest OR-group of
   `prices[]` (different `group` = alternatives, same group = summed); convert with the ladder; **one vote
   per `seller_id`** (its cheapest); report min → median and the seller count; rune/gem asks are per stack.
7. **Pull live only for Top tier (≥ 8 Ist) or when the cache has no file** — commands in
   `.agents/skills/pricing-refresh/SKILL.md`. diablo2.io fills (`activesold=1`) are the only fill source
   and the only source for rares and crafts; the Traderie rare ring/amulet/circlet feeds are one-seller walls.

## Converting to a verdict

- Ladder (Ist): Lem 0.20 · Pul 0.57 · Um 0.67 · Mal 0.79 · Ist 1 · Gul 1.43 · Vex 2.59 · Ohm 4.05 ·
  Lo 5.89 · Sur 8.23 · Cham 8.57 · Ber 9.32 · Jah 11.4 · Zod 13.7; P.Amethyst 0.10 · P.Skull 0.12 ·
  other P.gems 0.06; keys ≈ 0.45–0.51. Never the cube 2:1 ladder.
- Tiers: Top ≥ 8 (sell as "offer"; chase rolls fill at 32–63 % of the ask median) · High 2.5–8 and
  Mid 0.8–2.5 (sell at the bucket median) · Low 0.2–0.8 (bulk lots or self-use) · Floor < 0.2 (vendor).
- "Keep" has a second meaning for this player: `guides/pricing.html` §6 lists per slot what the Echoing
  Strike Warlock wears and when a drop beats it; `guides/warlock.html` §3 lists craft bases to keep.

## Report

**A pasted screenshot with no question, or just "worth?", means all three parts.** A specific question
("why is this in the filter?", "should I wear it?") gets only the part it asks for.

### 1 · Price as is (four lines, then at most three bullets)

```
Verdict: VENDOR | SELL <band> | KEEP (<why>) | LIST AS OFFER   — tier
Band: <min → median Ist> (<runes>), <n sellers>, asks <date>[; fills: <what was seen>]
Deciding step: pricing.html §<n> — <one sentence: the gate or pattern that decided it>
Source: <file and bucket key / example row / tool command used>
```
Say plainly when the verdict rests on asks with no observed fill, a thin bucket (`thin: true`, < 5
sellers), or a recompute you did yourself.

### 2 · What would make it worth more

One to three bullets, each "<roll> → <band>": the missing gate (sockets, ≥15 % ED, 45@, +2 class,
20 FCR, +life on a skiller), the chase roll (eth, perfect ED, 5/5, 2os) or the second affix the slot's
buyers demand, with the band it would reach from the neighbouring buckets or the primer's thresholds
(`pricing.html` §2 tables, §6 per-slot wants, §7 staff-mod ranking; primer §2.1 "how value multiplies",
§5 roll thresholds). If nothing can rescue the base (wrong socket count, normal-tier generic base) or the
item is at its ceiling, say that instead.

### 3 · Why the filter shows it, and what we hunt for

Find the rule in `lootfilter/warlock_lean.json` (profile "Warlock Lean", 12 named rules such as
"SHOW Rare WEAPONS", "SHOW Magic ARMOR", "SHOW Bases WEAPONS Gray"; match on `equipmentItemCode`,
`equipmentCategory`, `equipmentRarity`, `filterEtherealSocketed`). The reason per rule is the table in
`guides/warlock.html` §6; the pickup rules are `guides/pindle-anya.html` §3 (`PK-*`, with a `why` per key
in `pricing/data/wp-d-pickup.json`). Then two or three sentences: which rule matched (base / rarity /
eth-or-socketed flag), what pattern on this item type is the actual target (e.g. "rare Warlock daggers
are shown because eth Mithril Points with +2 Warlock or 40 IAS + leech ask Jah+"; "magic Amazon javelins
are shown for Lancer's … of Quickness, +6 Jav / 40 IAS"; "gray Kris is a 3os Void base"), and whether this
drop is that target, a near miss, or the price of casting the net. If the type has no sellable pattern,
say the rule is over-broad and name the narrower condition — but do not edit the filter unless asked.

### Fold-back

If nothing in the repo covers the item, say so in one line and offer to add the verdict to
`guides/pricing.html` §8 and `pricing/data/addendum-2026-09-18-session.json` as a dated pass.

## Mistakes already made once

- Calling a rare/class item, unique or set "vendor" because no build list or thread named it (step 5).
- Pricing from Ladder, Hardcore, console or pre-RotW listings, or from shop/forum prices on the web.
- Treating "blue" or "no FCR" as automatic vendor for Warlock daggers/grimoires: `pricing.html` §7 decides
  (+2 Warlock skills or a paid +3 staff-mod on the right base sells; +1 anything, Blood Oath, Levitation,
  Demonic Mastery do not).
- Quoting a Traderie bucket minimum, or a single seller's wall, as the price.
