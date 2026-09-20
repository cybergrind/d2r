---
name: warlock-build
description: Gear, upgrade, craft, boots, mercenary and variant advice for the player's Echoing Strike Warlock (D2R RotW); use for "what should I wear / upgrade / craft / farm next", not for pricing a drop.
---

# Echoing Strike Warlock — build advice

## Sources, in order

1. `guides/warlock.html` — §0 upgrade path from the 2026-09-19 gear check (what the player wears now),
   §1 gear list (maxroll Echoing Strike Warlock guide, S tier, updated 2026-08-26), §2 boots decision,
   §3 crafting (recipes, magic base codes, ilvl rule, shopping list per Pindle/Anya run), §4 Warlock-specific
   item values, §7 "verify in-game" (claims with no source yet — do not present them as settled).
2. `pricing/data/wp-a-builds.json` — the 26 S/A builds' main-slot gear; `pricing/data/wp-a-variants/`
   (`index.json` item → builds/variants/merc slots; `SCHEMA.md`; `new-demand.md`) — the guides' Starter /
   Standard / Magic Find / Ubers / Set variants and mercenary loadouts, extracted from the embedded
   d2planner profiles on 2026-09-20 via `pricing/tools/wp_a_variants.py`.
3. `guides/pricing.html` §6 — per slot: what the build wants, "wear it if", "sell it if".
4. `guides/pindle-anya.html` §4 — Anya shop and gamble checklist (what to buy for this build).
5. Live: `https://maxroll.gg/d2/guides/echoing-strike-warlock-guide` (prose is often stale against the
   planner; the planner JSON at `https://planners.maxroll.gg/profiles/d2/<data-d2-id>` has every loadout).

## Rules

- **Ground in the current state first.** Read `warlock.html` §0 before suggesting an upgrade; a
  suggestion that repeats what the player already wears, or skips the step they are on (e.g. FRW boots
  before Enigma), is wrong.
- **Recipes and item codes are looked up, never recalled.** Cube crafts: diablo2.io recipe pages or
  d2runewizard (maxroll/purediablo are blocked from here). Codes: the d2data dump (see the lootfilter
  skill). Caster Belt = Light Belt line (vbl/zvb/uvc), Caster Boots = Boots line (lbt/xlb/ulb),
  Caster Gloves = Leather Gloves line (lgl/xlg/ulg); crafted ilvl = ⌊clvl/2⌋ + ⌊ilvl/2⌋, 71+ = 4 affixes.
- **Merc and variant gear counts.** Appendix B and `wp-a-builds.json` list player main slots only; the
  Uber Tristram / Colossal Ancients variant puts a full Sazabi's set on an Act 5 Frenzy merc.
- **Keep vs sell** is a pricing question: if the answer needs a band, use the appraise skill's data files
  for the number and quote it dated.
- Another session sometimes edits `guides/warlock.html` and `lootfilter/warlock_lean.json` concurrently;
  re-read before writing.

## Answer shape

Lead with the recommendation for the slot asked about (one line), then the reason (guide row + the
player's current item), then what it costs or what drop/craft produces it. Bullets, not prose blocks.
