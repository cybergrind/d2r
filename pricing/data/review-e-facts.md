# Review E — fact-check lens · guides/pindle-anya.html (WP-E draft, 2026-09-18)

Reviewer: clean-context pass, 2026-09-18. Scope: every cited number/fact in the guide vs `pricing/data/wp-{a,b,c,d,f,g}*.json|md`, the cached pages under `pricing/raw/mr/` and `pricing/raw/d2io/`, `pricing/raw/d2runes-shopping.html`, plus four live Traderie re-pulls (ids 2588089657, 3707980542, 4283849324, 2221303065; 2 pages each, `--sc --nl --pc --props`, 2026-09-18 ≈15:55). No file other than this one was written. Items in the plan's "Rejected ideas" and review log were not re-opened.

Severity order: wrong number > wrong fact > missing citation > drift > style.

---

## Wrong number

**1. Preconditions ("Asks, not fills"), §5 intro, appendix ledger item 10 — "WP-B had no diablo2.io fills for these buckets … WP-F's only fills: Ber 9.3–12, Jah 10–12 Ist" / "No fills for any base bucket: spot-check … before quoting Jah-tier numbers".**
- What is wrong: stale. WP-G has since cached diablo2.io `activesold=1` searches for 12 bases (`pricing/raw/d2io/search-wpg-*.html`, 15:24–15:42) and summarised them in `pricing/data/wp-g-bases.json` (`"fills"`). Seven sold rows exist (parsed with `python3 pricing/tools/d2io_search.py --parse FILE`), and six searches returned a genuine "Found 0 matches" page (Monarch, Giant Thresher, Great Poleaxe, Thresher, Berserker Axe, Dusk Shroud, Mancatcher); the Cryptic Axe page is a flood-control error ("Sorry but you cannot use search at this time"), i.e. unverified, not "no sales".
- Fills vs the guide's asks (WP-F ladder; ratio = ask ÷ fill):
  - Sacred Targe "Perfect 45 Resist All … will get 4 sockets from Larzuk", sold 11 h ago for **1 Ber = 9.32** (`search-wpg-sacred-targe.html`, /trade/sacred-targe-t1857003.html). Guide §5 "45@ 0os normal 5.9→18.5": min 0.63×, median **2.0×**; TL;DR "45@ 4os n=26 9.3→22.8": min 1.0×, median **2.4×**.
  - Superior Archon Plate 15 ED, 0 os ("will be 4os when larzuk"), sold 23 h ago for **1 Ohm 4 Mal = 7.21** (`search-wpg-archon-plate.html`, t1859656). Guide §5/§3/TL;DR "0os Superior ≥15 ED 11.4→22.8 (n=8)": min **1.6×**, median **3.2×** above the fill.
  - Archon Plate 505 def (plain), sold 2 d ago for **1 Mal 1 Um = 1.46** (t1859310). Guide "3os normal 0.1→1.0 / 4os normal 0.08→1.0": the fill sits **above** the ask median (0.7×) — floor asks are not inflated.
  - Superior Phase Blade 15 ED / 1 AR, 6 os, sold 1 d ago for **1 Ohm = 4.05** (`search-wpg-phase-blade.html`, t1863780). Guide §5 "6os Superior ≥15 ED 8.6→9.3 (n=5)": **2.1–2.3×** above the fill.
  - Phase Blade (plain, sockets not stated), sold 2 d ago for **1 Gul = 1.43** (t1860331) vs floor asks 0.1→0.67 — fill 2.1× above the ask median.
  - Superior Grand Matron Bow +3 Bow, 3 os, sold 11 h ago for **1 Um = 0.67** (`search-wpg-grand-matron-bow.html`, t1859755) vs guide "3os normal +3 floor 0.25→0.79" — agrees.
  - Superior Mage Plate 11 % ED, 3 os, sold 2 d ago for **1 Mal = 0.79** (`search-wpg-mage-plate.html`, t1852428) vs WP-B "3os superior <15ED 0.67→0.83" — agrees (the guide quotes only the ≥15 ED bucket, whose minimum 0.79 equals this fill).
  - Jah-tier asks with **no fill in the 3-day window**: 4os 15ED Monarch (9.3→17.1), eth 4os Superior GT (57→86 / 126+), eth 4os Superior GPA (80→126), Cryptic Axe (91→108, page unverified).
- Fix: replace the "no fills" sentences with "diablo2.io fills 2026-09-18 (WP-G): Archon sup 15ED 0os 7.2, Sacred Targe 45@ 0os 9.3, PB sup 15ED 6os 4.05, GMB sup +3 3os 0.67, Mage Plate sup 3os 0.79; 0 sold in 3 days for Monarch/GT/GPA/Thresher/BA/Dusk/Mancatcher", add a "fill" column to §5 for those rows, and mark the Jah-tier rows "no fill seen".

**2. TL;DR "Top-3 Anya targets" — `AN-armor-whale` "Jeweler's (4os) Archon Plate of the Whale (clvl 70 → ilvl 75; 1/473,600 per armor)".**
- What is wrong: the 1/473,600 (d2io Anya-page comment, "4 years ago") is the chance that an armor shown is "4sox 100life" on **any** base; at ilvl 75 the shown base is Ancient Armor and Archon Plate appears only on the **2.2 %** elite upgrade (same comment: "Character level (CLvl) 70 will allow item level (iLvl) 75 Ancient Armor (and 2.2 % upgraded Archon Plate) … Jeweler's armor of the whale: 4sox 100life aLvl = 55 1/473,600"). Per *Archon Plate* of the Whale the figure is ≈1/473,600 ÷ 0.022 ≈ 1 in 21.5 million per armor shown; the comment's figure is also for exactly 100 life, not the 90–100 band the guide prices. §4.1 states the 2.2 % correctly; the TL;DR drops it.
- Evidence: `pricing/raw/d2io/npc-anya.html` (html2text "473" / "2.2").
- Fix: TL;DR → "any Jeweler's armor of the Whale 1/473,600 per armor shown; Archon base on 2.2 % of those".

**3. §3 `PK-jewel` evidence — "d2io fills: Ruby Jewel of Hope 34 ED/20 life 'LF 1 Mal', 6 str/10@ → 20 PGems".**
- What is wrong: the first item is an **active ask** (activesold=2), not a fill — plan review-log item 10 lists it under "53 active magic jewels (e.g. … Ruby Jewel of Hope 34 ED/20 life 'LF 1 Mal')"; only the second is a fill ("Shimmering Jewel of Virility 6 str 10 all res … Sold 1 day ago by Knappogue for 20 Perfect Gems", `pricing/raw/d2io/search-jewel-sold-nl-sc.html`, parsed).
- Fix: "d2io ask: Ruby Jewel of Hope 34 ED/20 life 'LF 1 Mal'; d2io fill: 6 str/10@ jewel → 20 PGems (2026-09-17)".

## Wrong fact / source inconsistency

**4. §4.1 `AN-claw-traps` odds "16.8 % / 19.3 % of claws exc/elite at ilvl 80 / 99" vs §4 box "15.2 % + 2.3 % at ilvl 80, 17.7 % + 2.6 % at ilvl 99".**
- What is wrong: both are verbatim BMAY (`pricing/raw/d2io/claw-guide-bmay.html`: "15.24% … 17.67% … 2.28% … 2.58% … The total combined chance of either upgrade happening is 16.82% at ilvl80 & 19.34% at ilvl99"), but BMAY's "combined" figures do not follow from his own components (15.24 + 2.28 = 17.52, not 16.82; 17.67 + 2.58 = 20.25, not 19.34; sequential rolls give 17.2 / 19.8). The guide prints both sets without noting they disagree, so a reader who adds the §4 box gets a different number from the §4.1 row.
- Fix: quote one set and add "(BMAY's combined figures do not reproduce from his formulas; ±1 pt)".

**5. §5 blues row "Artisan's Tiara of Speed (30 FRW, 3os) · magic 30 FRW · keep · 11.4→34.3 · n=4" (also `PK-blue-circlet` "Tiara 30 FRW n=4 11.4→34.3", `AN-circlet-gamble`).**
- What is wrong: the WP-B bucket "Tiara magic 30 FRW" mixes sockets: only 2 of the 4 rows are 3os (1 Jah = 11.4, 4 Jah = 45.7); the other two are 0os and 2os Tiaras with 30 FRW + 30 all-res (22.8, 91.4). wp-b.md itself says "3os n=2 thin (11.4, 45.7), 0os+30@ 22.8". Labelling n=4 as "3os" overstates the sample for the Artisan's roll.
- Evidence: `pricing/data/wp-b-prices.json` `_blues` → "Tiara magic 30 FRW (Artisan's of Speed = 3os + 30 FRW)" rows.
- Fix: "30-FRW magic Tiara, any sockets, n=4 11.4→34.3 (Artisan's 3os only n=2, 11.4 / 45.7 — thin)".

## Missing / misattributed citation

**6. §1 "Access" row and §2 step 1 — 'after the Rescue Anya quest ("Prison of Ice") … (Pindle guide Feb 10, 2026)'.**
- The Pindle guide says "after you finish the Rescue Anya Quest" / "rescue Anya from the Frozen River"; the quest name "Prison of Ice" appears only on the diablo2.io Anya NPC page ("rescued from the Frozen River in the quest Prison of Ice"). The "SW of the waypoint" claim is correctly in the Pindle guide ("Anya, and the Portal, are located to the Southwest of the Waypoint").
- Evidence: `pricing/raw/mr/meta__pindleskin-farming-guide.html` (0 hits for "Prison of Ice"); `pricing/raw/d2io/npc-anya.html`.
- Fix: cite the d2io Anya page for the quest name, or drop the name.

**7. §4 box — "Greater Talons qlvl 50 … Runic Talons qlvl 81 need ilvl ≥ 81 → clvl ≥ 76 (qlvl ≤ ilvl rule, Hastmannen; derived)" and `AN-claw-traps` "Runic base needs 76+".**
- The qlvl values are sourced (purediablo's alvl/qlvl list: "… Greater Talons 50 … Runic Talons 81 …", `pricing/raw/d2io/purediablo-claw-guide.html`; diablo2.io Greater Talons base page "Quality level: 50") but the guide names no source for them — WP-C says "purediablo table", which is the qlvl list, not the claw stat table (that one has no qlvl column). The qlvl ≤ ilvl rule is verbatim Hastmannen ("items will only appear when the qlvl of the item type is less than or equal to the ilvl of the shopped items").
- Fix: add "(qlvl per purediablo qlvl list 2023-02-22; d2io base page)".

**8. Links table — 'diablo2.io Anya NPC page … pre-RotW ("Missing v0.3 Data")'.**
- The "Missing v0.3 Data" tag is on the NPC index page, not on the Anya page. Evidence: `grep 'Missing v0.3' pricing/raw/d2io/npc-anya.html` = 0 hits; `pricing/raw/d2io/npcs-index.html` shows it next to the Anya entry.
- Fix: "(NPC index flags the entry 'Missing v0.3 Data')".

**9. §3 `PK-runes` — 'El–Fal bulk (Spirit sets, Ral for caster crafts, "40× Hel/Sol") … maxroll Runes (Feb 10, 2026) "Trading Runes"'.**
- The Spirit-set and Ral-craft examples are on the Runes page (verified). The "40× Hel / 40× Sol" line is not — WP-F took it from maxroll **Rune Value** ("40x Hel / 40x Sol = High", `pricing/data/wp-f.md`), a page dated March 6, 2024 (pre-RotW, `pricing/raw/mr/items__rune-value.html` dateModified).
- Fix: attribute the "40×" example to "maxroll Rune Value (Mar 6, 2024, pre-RotW) via WP-F".

**10. §4.1 / §4.2 tables — no "asks, not fills" label.**
- TL;DR, §3 header and §5 header carry the label; the §4.1/§4.2 "Value pointer" columns quote WP-B asks (e.g. "3os staff-mod claws ask 22.8→114", "Tiara 30 FRW n=4 11.4→34.3") next to undated d2runes rune counts without saying they are asks.
- Fix: rename the column "Value pointer (asks; d2runes/d2io = orientation)".

## Drift (data ↔ guide)

**11. Live Traderie spot-check (4 items, 2026-09-18 ≈15:55) — no number contradicted, but two buckets moved.**
- Sacred Targe (2588089657, 100 pulled, 88 in scope): a single-seller wall of ~20 "3os 45@" listings (ids 1002446553271–1002446570263, absent from the cached pull) now asks 2–5 Jah (22.8–57.1) — same band as cached "3os 45@ normal n=8 22.8→43.4", but n has tripled; the cheapest 4os 45@ normal is now 1 Ohm = 4.05 (id 1002507509759) vs the guide's 9.3 minimum. Listings with amount x3/x5 and x40/x49 confirm base asks are **per unit** (quantity = stock), not per stack.
- Archon Plate (3707980542): 3os ≥15 ED rows 2 Jah (superior) / 5 Jah / 5 Jah / offer → matches "22.8→45.7". Monarch (4283849324): 4os sup 15ED 1 Ber / 2 Jah / 3 Sur / 2 Jah / 4 Jah → 9.3→22.8 vs cached 9.3→17.1 (n=4). Giant Thresher (2221303065): eth 4os normal 1 Lo–1 Jah (5.9–11.4) ✓; eth 4os superior 14 ED now asks 7–15 Jah (80–171) vs cached "<15 ED n=10 57→86" — the live 2-page sample sits above the cached median; ≥15 ED superiors ask 110–130 Jah (matches "126→799, offer-heavy").
- Fix: none required for the numbers; add "asks move within hours; a single seller can be the whole bucket" to §5's "Reading this table", and keep the pull timestamp.

**12. Preconditions "Asks, not fills" — "(cheapest OR-alternative of the listing, per stack)".**
- "Per stack" is WP-F's rune/gem rule (divide by `amount`). WP-B reads base asks per listing and did not divide (`wp-b.md` "asks read per listing"); the live pull above shows per-unit pricing on multi-quantity base listings. As written, the sentence would tell a reader to divide base asks by the quantity.
- Fix: "per listing; rune/gem stacks per stack (WP-F)".

**13. Keys — no drift found.** All 24 `PK-…` keys in §3 exist in `wp-d-pickup.json` with the same action (keep/sell/leave) and the same condition text; all 12 `AN-…` keys in §4 exist in `wp-c-anya.json` with the same clvl/odds/sources. `AN-mechanics` and `AN-refresh-loop` (WP-C) are folded into the §2/§4 boxes without their key — acceptable, but a one-word key mention would make the hand-off traceable.

## Style / precision

**14. TL;DR ② — "Giant Thresher n=10 57→86".**
- That bucket is eth 4os **Superior <15 ED** (§5 says so); the other three items in the same sentence are the ≥15 ED buckets. The ≥15 ED GT bucket asks 126→799 (4 of 8 priced).
- Fix: "Giant Thresher sup <15ED n=10 57→86 (≥15ED asks 126+, offer-heavy)".

**15. Header "RotW, patch 3.1.x" — ledger item 25 already flags patch numbering; add the maxroll evidence.**
- The Dragon Talon guide (May 22, 2026) says "The Mosaic Runeword is disabled for Patch 3.2 / Season 14 on Ladder"; diablo2.io's Mania/Hysteria pages say "As of patch 3.3 … can be made in Non-Ladder on RotW". Both are later than 3.1.2 (1 Apr 2026).
- Fix: header → "RotW (3.1.2 notes dated 2026-04-01; sites cite 3.2/3.3)" or resolve the number.

**16. §5 RotW row — "Blasphemous all offer … 2" and `PK-rotw-daggers-grimoires`.**
- The cached pull has three white-labelled 2os Blasphemous rows (2 unset-rarity affixed + 1 superior affixed), all "make offer"; WP-B/guide say n=2. Trivial count slip; the conclusion (all offer) holds.

---

## What was verified and holds (not findings)

- **Dates**: every "Last Updated" the guide cites matches the cached page's `dateModified` — Pindle guide 2026-02-10, Sockets 2026-06-16, Base Items 2024-05-12, Gold/MF 2026-02-11, VMI 2024-03-06, Runewords 2026-06-02, New Items 2026-02-19, Runeword tier list 2026-02-18, Overall tier list 2026-05-22, Runes/Gems/Trade/Staff Mods 2026-02-10, Tips & Tricks 2023-11-22, Warlock Overview 2026-02-18, 26 build guides May 22–Aug 26, 2026 (Strafe Jul 18, Echoing Strike Aug 26); purediablo `dateModified` 2023-02-22; Hastmannen/BMAY "5 years ago"; Anya comment "4 years ago"; Grimoire entry "7 months ago"; patch thread "1 Apr 2026"; d2io guide "revised 28 Aug 2026".
- **Game facts**: TC 87 / mlvl 86 "both he and his minions"; the 3 undroppable items; "2 items of Magic quality or higher (Unless they drop a Rune or Gem)"; "useful for Experience even at Level 96"; ilvl-from-monster rule and the Cow King 28/31 example; "Hell Difficulty does not have a Socket limit"; 1/3 socket chance and the gray-colour sentence; cube socket odds (4os 50 % at max 4, 5os 33.33 % at max 5, 16.67 % each at max 6, not on Superior/Low Quality); Larzuk "maximum possible number of Sockets … Any Monarch always receives 4", magic 1–2, rare/unique 1; every socket maximum in §1.1 against the "ilvl 41+" column (incl. Monarch 3|3|4, Mage Plate 3|3|3, Death Mask 2|2|3, no Mask/Grimoire row); Low Quality 75 % / no eth / no sockets; Superior eth+sockets; MF no effect on tier, runes, gambling; failed set/unique durability tell; VMI 41–45-life GC rule and "most valuable Magic Item"; Tips "no longer disappears" / "reset the shops"; alvl formula; Hastmannen ilvl = clvl+5, no eth, magic-only after ilvl 25 (clvl 20), no refresh with another player in town, "hell upgrade" tag, qlvl ≤ ilvl, "Elite items can first spawn in A3 Hell", Lancer's javelin at Malah, gloves 55/68–74/75+; BMAY formulas, 1:41,118 / 1:328,947, 1,756 claws / 500 refreshes, 20 checks/min, dex 55/Simplicity; purediablo NM formula, "at least 1,000,000", staff mods only on exc/elite, "capped at 99", claw classes; d2runes clvl rows, 1 in 11,305, gamble odds, Edge+Gheed's 30 %, ~50,000 per ring, and the rune icons behind "~5 Ber / 20–30 Jah / 10–20 Jah / 1 Lo / ~1 Ist"; d2io Anya "Sells Armor, Weapons (Katars, Throwing Weapons), Keys and Arrows"; Grimoire qlvl 24 / max 2 sockets; Kris Warlock mods; "Updated the number of daggers that can be found on vendors"; Mania/Hysteria = Hustle; warlock-overview "0–3 Staff mods … +1–3"; New Items "5 new Runewords" and the 15 grimoire bases; every build-guide string cited by name (Cunning Greater Talons of Quickness, Lancer's Chain Gloves of Alacrity, Lancer's Matriarchal Javelin of Quickness, Archer's Gloves of Alacrity, Echoing Balanced Knife, Arch-Devil's Kris of Lower Resistance, "All Resistance on a Magic Grimoire", "Void Legend Spike is used for four reasons", Coven Diadem, Ethereal Spirit Monarch, "Ethereal for style", "Ethereal Superior Giant Thresher", Shadow Mark Amulet).
- **Prices**: every §3/§5/TL;DR bucket (≈120 numbers: n, min, median) matches `wp-b-prices.json`; the merged buckets the guide quotes that are not single JSON buckets were recomputed from the raw pulls with the tool's own functions and hold exactly — Sacred Targe 45@ 4os n=26 9.32→22.84, 0os n=24 4.05→39.97, 3os n=12 22.8→45.7, eth n=9 45.7→62.8; Flail white 4/5os non-eth n=53 0.083→0.67; Archon 3os ≥15ED n=5 (4 priced) 22.8→45.7; Archon 4os magic n=29; Rondache 4os n=34 0.5→2.58 and 45@ n=6 2.6→45.7. Blues (Jeweler's Monarch n=17 74.6→114, Archon of the Whale n=10 57→343, six glove bases, Mat Jav n=13 0.4→57) match `_blues`. WP-F ladder (Pul .57 … Zod 13.7, Cham 8.57), Ber/Jah fills 9.3–12, "1 Ber = 100 pskull" WTB, Lem 0.2 midpoint, PGem 1/40, PAmethyst 1/12, 7,778 / 4,981 listings, 91.8 / 2.7 / 4.9 % game-version split, d2io bands (bases, blues, skillers, jewels) all match their sources.
- **WP-A**: every char/merc count and weight in §6 (25/22 (41), 19/25 (41), 5/19 (32), 25/2 (39), 18/14 (37), BA 9/21 (39), CB 3/0 (6), polearms 3–5/25 (40), Mancatcher 2/17 (27), Mat 12/25 (40), GMB 1/3 (4), CS 26/5, Flail 26/0, Diadem 24/24, Talons 4/2 (5), Legend Spike 1/0 (2), Bone Shield/Head/Targe 19/18/19) matches `wp-a-bases.json`; blue weights (Rare Ring 37/23 builds, Rare Boots 29, Rare Gloves 16, Fortuitous 16/9, Rare Diadem 9 builds, 169 patterns) match `wp-a-blues.json`.
- **Internal consistency**: TL;DR numbers equal the body numbers; the ladder stated is the WP-F ladder used by WP-B/WP-D; "asks, not fills" is present on the TL;DR, §3 and §5 (see #10 for §4).

## Count and verdict

**16 findings**: 3 wrong number (1 stale "no fills" claim now contradicted by seven WP-G fills, 1 odds figure conflated in the TL;DR, 1 ask labelled as a fill), 2 wrong fact/source inconsistency, 5 missing or misattributed citations, 3 drift notes (2 substantive, 1 "none found"), 3 style.

Verdict: the guide's numbers are sound — every Traderie ask, ladder value, WP-A weight, socket maximum, page date and quoted game fact checked against the cached sources and the JSON hand-offs reproduces, including the merged buckets that had to be recomputed from the raw pulls and the four live re-pulls, which contradict nothing. The one material gap is chronological, not arithmetic: the guide still asserts that no base fills exist, while WP-G's cached diablo2.io searches now show five items with fills (asks 1.6–3.2× above the fill on the 15ED Archon and 6os PB chase rolls, at parity on floor items) and zero sales in three days for the Jah-tier Monarch/GT/GPA buckets — the reader should see that before acting on §5. The remaining items are a TL;DR odds conflation (#2), an ask mislabelled as a fill (#3), a BMAY arithmetic inconsistency the guide inherits (#4), a mislabelled n=4 Tiara bucket (#5) and citation hygiene; none changes a keep/sell/leave verdict. No key drift between the guide and WP-C/WP-D.
