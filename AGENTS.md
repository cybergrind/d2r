# D2R appraisal repo — agent instructions (core)

Diablo II: Resurrected pricing / farming knowledge base for one player: **Softcore · Non-Ladder · PC ·
Reign of the Warlock (RotW)**, playing an **Echoing Strike Warlock**. Farming rotates between runs (bosses, Pindleskin,
Hell cows, the Anya shop…); do not assume a particular run. The farm guide covers Pindle/Anya only. Everything is quoted in **Ist = 1**. Numbers are dated snapshots (mostly 2026-09-18).

## Pick the skill for the task, then read only that file

| The user… | Read | Do not read |
|---|---|---|
| pastes a screenshot, or asks "worth?", "is it worth anything?", "does it cost anything?" | `.agents/skills/appraise/SKILL.md` | the other skills |
| explicitly requests online/live item prices or names `appraise-online` | `.agents/skills/appraise-online/SKILL.md` | no bulk refresh unless also requested |
| asks about gear, upgrades, crafts, boots, what to wear, build variants, mercenary | `.agents/skills/warlock-build/SKILL.md` | appraise (unless they also ask a price) |
| asks why the loot filter shows/hides something, or wants a filter change | `.agents/skills/lootfilter/SKILL.md` | — |
| asks to refresh prices, pull Traderie / diablo2.io, rebuild data, extend a guide, run the plan | `.agents/skills/pricing-refresh/SKILL.md` | — |
| asks to update/audit the offline KB, fold in research, or check base-variant coverage | `.agents/skills/update-kb/SKILL.md` | online refresh unless requested |
| asks to clear the shared stash, organise mules, decide what to drop or where an item goes | `.agents/skills/mules/SKILL.md` | online refresh; the guides |
| asks to list an item on Traderie, post a listing, or review their active listings | `.agents/skills/traderie-list/SKILL.md` | online refresh unless requested |

The appraise skill's report has a "why the filter shows it" part; it links to the filter skill only for the
rule table, so an appraisal never needs the whole filter skill.

## Appraisal execution order (all agents, including Pi/Kimi)

After transcribing an item screenshot, the first evidence command is
`uv run --offline python -m pricing.knowledge lookup "<item/base>" --rarity <rarity> --limit 2`.
Use `recommend` first for class-level unique/set keep lists. Read the appraise skill for
facet refinement. Guides and raw wp-* files are targeted fallbacks after the KB identifies
what is missing; do not start by scanning them. Missing/incompatible index → offline rebuild.
No online refresh during default appraisal. Live item checking requires an explicit user
request and the separate `appraise-online` skill; cache misses never trigger it.
The full image-to-report command is not implemented yet.

## Assessment engine work (all agents)

The driving document is `pricing/knowledge/assessment/planning/COMPLETION_CONTRACT.md`: its
"Current contract" section (2026-10-06) holds the end goal, measures, queue and stopping rule.
`PLAN.md` in the same directory holds the design, steering history and status. The rest of the
contract file, the coverage matrix, report receipts and per-item formal reviews are frozen: do
not resume them, do not regenerate their artifacts, and do not append to `handoff.md` or
`STATUS.md`. Measure changes with the corpus score (`inventory_tracking/corpus`).

## Rules that apply to every task

1. **The repo is the price source, not the web.** Never web-search for prices: generic price guides,
   d2jsp, diablofans, d2rgear, reddit, and "PC:" threads from other modes are a different economy.
   Outside sources are only the Traderie JSON API (asks, buy side, and the Recent Trades read through the
   player's browser by `traderie_trades.mjs`) and diablo2.io trade search, through `pricing/tools/`,
   with the scope filters (Traderie props 799 softcore / 800 Non-Ladder / 798 PC / 1854 RotW; diablo2.io
   `ladder=2 hc=2 plat_pc=1 legacy_resu=2`). Maxroll guides are the source for *demand*, never for prices.
2. **Not named in a build list ≠ worthless.** Before "vendor" on a rare, magic class item, unique or
   set, check indexed market/demand/leveling evidence; consult specific bucket/variant rows only
   when the index leaves a relevant gap (the appraise skill says where).
3. **Never write a 3-letter item code from memory**; verify against the d2data dump (the filter skill).
4. Guides are HTML. Read them as text: `python3 pricing/tools/html2text.py guides/<file>.html "keyword" 400`
   (no keyword = whole page). `rg` needs `--no-config` here (RIPGREP_CONFIG_PATH points to a missing file).
5. Date every number; say "asks" or "fills"; never quote a bucket minimum as "the price".
6. Edit guides in place (body = settled truth) and log changes as a dated pass in the guide's Review log
   (conventions in `guides/planning-with-html.html`). Do not commit unless asked.

## Development

Follow [development practices](development.md) for code changes.

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
- `guides/worldstone-shards.html` — which Hell elites drop Worldstone Shards, the per-act shard mix, where to
  farm each of the five shards, terror zones/Heralds (installed-game tables, 2026-10-05).
- `pricing/plan.html` — research plan and access cookbook; `pricing/data/wp-*.md` hand-off notes.
- `pricing/data/*.json` — ladder (`wp-f-ladder.json`), base buckets (`wp-b-prices.json`), uniques/sets/misc
  (`wp-i-uniques-misc.json`), jewels/charms (`wp-h-jewels-charms.json`), builds (`wp-a-builds.json`,
  `wp-a-blues.json`, `wp-a-variants/`), pickup rules (`wp-d-pickup.json`), session addendum.
- `pricing/tools/` — `traderie.py`, `pricecheck.py` (name → ask band in one call), `d2io_search.py`, `fetch.sh`, `html2text.py`, `tables.py`, rebuild scripts; `traderie_list.mjs` / `traderie_edit.mjs` / `traderie_listings.mjs` post, reprice and read the player's Traderie listings in their browser; `traderie_notifications.mjs` reads their notifications (`make serve` shows unread ones on the HUD, `inventory_tracking/hud/traderie.py`).
- `pricing/raw/` — cached pulls (git-ignored, ~200 MB). `lootfilter/` — in-game filter profiles.
