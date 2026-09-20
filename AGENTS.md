# D2R appraisal repo — agent instructions (core)

Diablo II: Resurrected pricing / farming knowledge base for one player: **Softcore · Non-Ladder · PC ·
Reign of the Warlock (RotW)**, playing an **Echoing Strike Warlock**, farming Pindleskin, Hell cows and
the Anya shop. Everything is quoted in **Ist = 1**. Numbers are dated snapshots (mostly 2026-09-18).

## Pick the skill for the task, then read only that file

| The user… | Read | Do not read |
|---|---|---|
| pastes a screenshot, or asks "worth?", "is it worth anything?", "does it cost anything?" | `.agents/skills/appraise/SKILL.md` | the other skills |
| asks about gear, upgrades, crafts, boots, what to wear, build variants, mercenary | `.agents/skills/warlock-build/SKILL.md` | appraise (unless they also ask a price) |
| asks why the loot filter shows/hides something, or wants a filter change | `.agents/skills/lootfilter/SKILL.md` | — |
| asks to refresh prices, pull Traderie / diablo2.io, rebuild data, extend a guide, run the plan | `.agents/skills/pricing-refresh/SKILL.md` | — |

The appraise skill's report has a "why the filter shows it" part; it links to the filter skill only for the
rule table, so an appraisal never needs the whole filter skill.

## Rules that apply to every task

1. **The repo is the price source, not the web.** Never web-search for prices: generic price guides,
   d2jsp, diablofans, d2rgear, reddit, and "PC:" threads from other modes are a different economy.
   Outside sources are only the Traderie JSON API and diablo2.io trade search, through `pricing/tools/`,
   with the scope filters (Traderie props 799 softcore / 800 Non-Ladder / 798 PC / 1854 RotW; diablo2.io
   `ladder=2 hc=2 plat_pc=1 legacy_resu=2`). Maxroll guides are the source for *demand*, never for prices.
2. **Not named in a build list ≠ worthless.** Before "vendor" on a rare, magic class item, unique or
   set, check the Traderie buckets and the variants index (the appraise skill says where).
3. **Never write a 3-letter item code from memory**; verify against the d2data dump (the filter skill).
4. Guides are HTML. Read them as text: `python3 pricing/tools/html2text.py guides/<file>.html "keyword" 400`
   (no keyword = whole page). `rg` needs `--no-config` here (RIPGREP_CONFIG_PATH points to a missing file).
5. Date every number; say "asks" or "fills"; never quote a bucket minimum as "the price".
6. Edit guides in place (body = settled truth) and log changes as a dated pass in the guide's Review log
   (conventions in `guides/planning-with-html.html`). Do not commit unless asked.

## File map

- `guides/pricing.html` — the appraisal method (§0 currency card, §2 colour triage, §3 gates, §4 ladder
  and tiers, §5 lookup, §6 per-slot keep/sell for this build, §7 Warlock staff-mods, §8 worked examples,
  §9 false positives, §10 housekeeping).
- `guides/pricing-primer.html` — the numbers and why (§1 currency, §2 bases, §3 jewels/blues, §4 charms,
  §5 uniques/sets, §6 rares/crafts/misc, §7 refresh runbook, §8 decision table, `#miss` checklist,
  appendix B builds).
- `guides/pindle-anya.html` — farm loop, pickup rules §3 (`PK-*`), Anya shop/gamble checklist §4, value table §5.
- `guides/warlock.html` — Echoing Strike gear (§0 upgrade path, §1 list), boots §2, crafts §3, Warlock item
  values §4, pickup rules §5, loot filter rule table §6, verify-in-game §7.
- `pricing/plan.html` — research plan and access cookbook; `pricing/data/wp-*.md` hand-off notes.
- `pricing/data/*.json` — ladder (`wp-f-ladder.json`), base buckets (`wp-b-prices.json`), uniques/sets/misc
  (`wp-i-uniques-misc.json`), jewels/charms (`wp-h-jewels-charms.json`), builds (`wp-a-builds.json`,
  `wp-a-blues.json`, `wp-a-variants/`), pickup rules (`wp-d-pickup.json`), session addendum.
- `pricing/tools/` — `traderie.py`, `d2io_search.py`, `fetch.sh`, `html2text.py`, `tables.py`, rebuild scripts.
- `pricing/raw/` — cached pulls (git-ignored, ~200 MB). `lootfilter/` — in-game filter profiles.
