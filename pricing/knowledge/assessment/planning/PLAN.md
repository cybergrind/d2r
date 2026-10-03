# Drop assessment plan — active since 2026-10-03

This is the only active plan for item assessment. It replaces the execution rules of
COMPLETION_CONTRACT.md, IMPLEMENTATION_PLAN.md, GUIDE_FIRST.md, ROLL_VALUE_REVIEW.md and
DELIVERY_APPROACH.md, which are frozen (user decision, 2026-10-03). Their technical content
stays as reference; their gates, queues and stopping rules no longer drive work.

## 1. Goal

On a drop, say quickly whether it is worth keeping to sell. In the user's priority order:

1. Liquid items are detected first: things many people buy at a known price.
2. The answer is fast.
3. Every item type gets an answer: uniques, sets, rares, magic, crafted, charms, jewels,
   bases, runewords, runes and other commodities.
4. Uniques and sets are separated good from bad by their rolls and ethereal status.
5. Demand comes from real guides and real market data.

Scope: Softcore / Non-Ladder / PC / RotW, Ist = 1. The player is not levelling characters.

## 2. Where we are (measured 2026-10-03)

| Fact | Number |
|---|---|
| Auto-identified drops with a numeric price | 0 of 826 |
| Alt+D reports with a numeric price | 9 of 927, all on 2026-09-23 |
| Rares that got KEEP | 0 of 145 |
| Magic items that got KEEP | 0 of 531 |
| Named tiers | 455: 358 low, 86 trash, 10 med, 1 high |
| Uniques with roll-aware trade rules | about 40–47 of 418 |
| Warm lookup, live | about 0.6 s per item (0.1–0.6 s replayed offline) |

The data to do better already exists and is being thrown away by the price gate (three sellers
of the *exact variant*, under 30 days old):

| Category | Names with ≥ 3 priced, scoped sellers in `appraisal-market.jsonl` | Catalog size |
|---|---|---|
| Uniques | 115 (99 with ≥ 10 sellers) | 418 |
| Sets | 27 | 172 |
| Runewords | 85 | 101 |
| Bases | 96 | 516 |
| Runes / gems / misc | 21 / 7 / 16 | 34 / 36 / 86 |

`wp-i-uniques-misc.json` already holds a hand-written roll bucket and price threshold for about
90 named items (for example Andariel's Visage: ethereal, 30 str, 10 LL). KEEP on uniques and
sets currently comes mostly from "build demand" across 33 guide builds including starter setups
(Sigon's Gage, Bloodfist, Peasant Crown), which is not the question the user asks.

### 2.1 Gaps by equipment type (detail engine replayed over the 551 corpus items, 2026-10-03)

No item got a numeric price except one quest material, and no build role reached "matched" on
any item. Per group: items, items with no build rules at all, items with a trade rule.

| Group | Items | No rules | Trade rule | Typical output |
|---|---|---|---|---|
| Affixed class items: orbs, Barbarian helms, grimoires, scepters, Necromancer heads | 29 | 28 | 0 | "damage-modifier coverage is unproven" / "no listings match" |
| Affixed daggers, claws, wands, staves, Amazon javelins, pelts | 29 | 3 | 0 | rules exist but none matches; same price lines |
| Affixed rings, amulets, circlets | 38 | 0 | 0 | at most a "partial" role; never a verdict |
| Affixed gloves, boots, belts | 33 | 1 | 0 | nothing |
| Charms and jewels | 77 | 1 | 0 | 2 value-watch hits in 77 |
| Named weapons (non-class) | 93 | 84 | 0 | tier only |
| Named armour, shields, helms, belts, boots, gloves | 141 | 63 | 11 | tier, sometimes a watch |
| White and socketed bases | 63 | 35 | 0 | nothing |

Before any rule runs, 145 items stop at a capture or mapping gate ("stat capture completeness
is unknown" 121, "no verified market mapping for native stat" 20, "undecoded native stat" 4).
Part of the 121 are captures made before completeness was recorded. Triage must not stop at
these gates: it judges the stats it has and names the unreadable one in the reason.

## 3. Design decisions

### 3.1 Two tiers: fast triage and detail

- **Triage** runs on every identified drop and on vendor stock. It is table lookups only: market
  band, roll rule, own-build rule. It does not evaluate the 33 guide builds. Target: under
  50 ms per item, in the service's retrieval process.
- **Detail** is the existing Alt+D report (roles, sockets, upgrade paths, levelling). It keeps
  running on request only and shows the triage verdict at the top.

This is what makes speed a design property rather than a later optimisation: the expensive
role engine leaves the path that runs on every drop.

### 3.2 One representation for drops and listings

A captured item is already converted to Traderie property ids for comparison (`contract.properties`,
68 distinct ids seen in reports). Triage rules are written against that property dict.
Consequences:

- Every scoped listing can be run through the same rules as a drop.
- Listings become a large, free test set: priced asks say which rolls the market pays for.
- Rule thresholds can be derived from listings instead of authored one item at a time.

### 3.3 Triage inputs are small data tables, outside the publication machinery

Three files under `pricing/data/triage/`, loaded directly and reloaded when they change. No
source-hash pinning, receipts or coverage artifacts.

| Table | Key | Content |
|---|---|---|
| `bands.json` | category + name + bucket | q1 / median ask in Ist, priced sellers, listings, newest and oldest listing date, share priced in runes |
| `rules.json` | name (named items) or family (affixed, bases) | deciding properties, thresholds per bucket, ethereal effect, socket effect, default bucket |
| `own.json` | slot | what the player's Warlock (and mercenary) would use, with minimum rolls |

### 3.4 Price with fallback, always dated

For an item, the band is the most specific that exists:

1. roll bucket band (name + bucket, for example "Arachnid Mesh, 120 ED"),
2. name-level band,
3. family band (for example "caster ring, 10 FCR + two resists"),
4. none.

The report shows the band, how many sellers stand behind it and its date, for example
`asks 2.6 Ist median · 11 sellers · 09-18`. A band older than 45 days is still shown, marked stale.
Asks are asks; where diablo2.io fills exist they are shown next to the band.

### 3.5 Liquidity is a computed class, not a review

Computed per band from data a guest can pull:

- **liquid**: at least 10 priced sellers, and the newest 50 listings span less than about two weeks;
- **thin**: 3–9 priced sellers, or listings spread over a long period;
- **none**: fewer than 3 priced sellers.

The exact cut-offs are calibrated against the user's labels (section 5), not argued in documents.
The weekly page-0 pull gives a second signal over time: how many of last week's listings are gone.
Guide demand (number of builds that name the item) is shown as a hint next to the class; it
does not change the class.

### 3.6 Verdicts

User-selected keep price: **0.25 Ist**, inclusive (confirmed 2026-10-03).
Apply this threshold consistently to triage and listing replay; the cheap-listing
false-positive check therefore covers asks below **0.0625 Ist**.

| Verdict | Shown as | Comes from |
|---|---|---|
| SELL | green, on the HUD | band at or above the keep price and liquid; or a rule bucket marked premium |
| SELL (slow) | yellow, on the HUD | band at or above the keep price but thin |
| CHECK | white, on the HUD, with the missing roll | the item has the full stat pattern of a paid rule but a roll below its SELL bucket, or the pattern is paid and no price evidence exists for this roll |
| SELF-USE | blue, on the HUD | `own.json` only |
| VENDOR | counted, not listed | everything else |

CHECK was missing from the first version of this table and is required (user, 2026-10-03).
It is narrow: it needs every stat of a paid pattern to be present. One good stat alone, a
levelling use or a low tier never produces CHECK.

Levelling uses, other builds' use and "trade tier low" appear in the Alt+D detail only. The
old keep/check/vendor mapping from value watches and roles is removed from triage.

### 3.7 How each item type gets its answer

| Type | Rule source | Price source | Default when nothing matches |
|---|---|---|---|
| Runes, gems, keys, essences, tokens | none needed | rune ladder, commodity bands | band |
| Uniques, sets | `rules.json` per name: 1–3 deciding properties, ethereal, sockets | bucket band, then name band | vendor; SELL (slow) if ethereal and the base is elite, pending review |
| Completed runewords | recipe + deciding rolls + base class | name band | name band |
| White / socketed / ethereal / superior bases | runeword-base family rules (sockets, ethereal, ED, base list) | `wp-b-prices.json` buckets, base bands | vendor |
| Charms, jewels | the existing 50 value-watch combinations, as family rules | `wp-h-jewels-charms.json` buckets, family bands | vendor |
| Class items: Warlock daggers and grimoires, claws, orbs, scepters, Barbarian helms, pelts, Necromancer heads, Amazon weapons, Paladin shields | section 3.8: base line and socket count, class-skill prefix, staff-mods from the paid list, the slot's second affix | family bands per pattern where listings exist | vendor |
| Rare / magic / crafted jewelry, circlets, generic weapons, boots/gloves/belts | family combination rules from the guide tables (section 3.8) | family bands where listings exist; otherwise a class word ("premium", "tradeable") without a number | vendor |

Affixed items are judged by combination rules, not by comparables: listings of rares are too
heterogeneous for exact matching, which is why the current engine never prices them.

### 3.8 The pricing guide is the triage specification

`guides/pricing.html` already contains the decision method the triage must implement, written
and settled before the engine existed: §2 colour triage (one table per colour: the pattern that
is worth money, what one affix alone is worth, the band), §3 gates, §6 per-slot keep/sell for
the player's build, §7 Warlock staff-mods, §9 false positives, and §8 with about 30 worked
verdicts on the user's own drops. The detail engine never encoded these tables; it built a
separate role engine instead. Triage rules are a transcription of the guide tables into
`rules.json`, then calibrated on listings — not a new derivation from build profiles.

Consequences:

- The §8 worked examples are regression cases with known verdicts (Razor Bow, +1 Abyss Dirk,
  Tomb Reaver 3os, Gavel of Pain, …). They join the corpus as pre-labelled items.
- When triage and the guide disagree, one of them is fixed and the guide's review log says which.
- A rule that cannot be traced to a guide row or to priced listings is not added.

**Class items are not generic weapons.** A caster class weapon is judged by skills, sockets and
base line; its damage, speed and durability are irrelevant and are not shown in triage. Rule
shape, from the guide's blue, yellow and §7 rows:

| Field | Warlock dagger example |
|---|---|
| Base line | 3-socket line (Blade … Legend Spike), Bone Knife, Mithril Point; normal-tier Dagger / Dirk never |
| Sockets | 3 on an elite base is the price; fewer sockets on a white base is nothing |
| Class-skill line | +2 Warlock skills (magic prefix or rare affix) is the gate for magic and rare |
| Paid staff-mods | per-class list from §7 and listings: +3 Echoing Strike, +3 Abyss, +2 Chaos, +3 Eldritch Blast, …; every dagger rolls staff-mods, so an unlisted or +1 mod is no signal |
| Second affix | magic: staff-mod plus a useful suffix; rare: +max damage, life, resists, a socket; ethereal with 30–40 IAS and leech is the melee pattern |
| Default | vendor, with the missing gate as the reason |

Roll colour in the report follows demand, not the native range: +3 of an unpaid skill is not
green. Acceptance case (user, 2026-10-03): magic Stiletto, no sockets, +1 Eldritch Blast,
+3 Enhanced Entropy → VENDOR, "no +2 Warlock, no sockets; staff-mods alone are not paid"; the
old report said "Price: not assessed — weapon damage-modifier coverage is unproven".

### 3.9 Pattern first, roll second

Every rule for an affixed item, a charm, a jewel or a named item has two parts, evaluated
separately:

1. **Pattern** — which stats must be present together (Fine + of Vita: maximum damage, attack
   rating, life). Matching the pattern alone gives at least CHECK.
2. **Roll buckets** — thresholds on those stats: premium, good, low. Premium and good map to
   SELL or SELL (slow) through the band; low stays CHECK with the reason naming the stat and
   the distance, for example "max damage 2, premium needs 3".

Why: the 50 existing charm and jewel rules are single exact buckets copied from the Maxroll
"valuable magic items" rows (for example exactly 3 maximum damage and 16–20 life). An item one
point under is treated like an item with none of the stats.

Acceptance case (user, 2026-10-03): Fine Small Charm of Vita, +2 maximum damage, +18 attack
rating, +17 life → CHECK, "Paladin/physical pattern complete; max damage 2 of 3". It was shown
as VENDOR. Scoped listings hold only 3-damage copies (asks 11–34 Ist, two sellers), so there is
no price for the 2-damage roll; that is a reason for CHECK, not for VENDOR.

### 3.10 Price a drop by where its rolls sit among the listed rolls

Listed copies are not a random sample of drops: sellers list the copies worth listing. A name
median therefore prices the typical *listed* roll, and a low-rolled drop gets a price it cannot
fetch. The price of a drop must come from listings whose rolls are comparable to it.

Evidence (Rusthandle, 19 priced scoped asks, pulled 2026-10-03): 17 of the 19 listed copies have
+3 Vengeance (native range 1–3); the only +2 copy asks 0.2 Ist; the +3 copies ask 0.4–11.4 Ist,
median 0.79. Enhanced damage (50–60, shown red at 50) does not separate the asks at all. The
drop in question had +2 Vengeance and was shown "SELL — asks 0.789 Ist median · 17 sellers".

Method, per named item and per affixed pattern, computed when bands are built:

1. **Find the deciding stats from the selection itself.** For each variable stat compare the
   distribution of listed rolls with the native range. A stat whose listed rolls pile up at the
   top of the range is deciding (Vengeance above); a stat spread evenly is not (enhanced damage
   above). This needs no price regression and works with 15–20 listings. Where asks also step
   with the roll, record the step as a bucket threshold.
2. **Price from comparable-or-worse listings.** The reference for a drop is the asks of listings
   that are no better than it on every deciding stat. Report the lower quartile of those asks.
3. **Below the listed range is an answer.** When the drop is worse than every listed copy on a
   deciding stat, say so: "below listed rolls (+2 Vengeance; 17 of 19 listed have +3)". The price
   is then at most the cheapest ask; the verdict is VENDOR when that ask is under the keep price,
   otherwise CHECK. It is never SELL.
4. **Too few listings to place the drop** (fewer than three comparable-or-worse sellers and the
   drop is inside the listed range): show the name band as *reference*, verdict CHECK.
5. **Fixed-stat items** (no variable deciding stat) keep the name band, split by ethereal.

Display: the band line names the comparison it used, for example
`asks 0.2 Ist · 1 seller with +2 Vengeance · listed copies are mostly +3` — never a bare name
median. Stat colour marks deciding stats and how the drop's roll compares with listed rolls; a
minimum roll of a stat that does not decide the price is not red. When a triage verdict is
shown, the old "Trade tier" line is not shown beside it.

Check that the method works (added to the listing replay): leave each listing out, price it from
the others with this method and with the plain name median, and report the median error of
both. The roll-aware price must beat the name median, or the item keeps the name band.

Acceptance case (user clarified, 2026-10-03): Rusthandle, +2 Vengeance, 50% enhanced damage → CHECK.
Keep comparable-or-worse Q1: the +1 ask at 0.789 Ist and +2 ask at 0.2 Ist give
Q1 = 0.34725 Ist, but only two sellers. Do not substitute the cheapest exact-roll ask
or describe this copy as below every listed roll. The validation requirement above remains.

## 4. Work packages

### Steering (progress check, 2026-10-03 afternoon) — takes precedence over the order below

Measured: listing replay flags 37.8% of listings at or above the keep price (target 85%);
uniques 91%, sets 93%, misc 94%, runes 80%, runewords 35%, magic 4%, bases 0.05%, rares 0%
(1,930 CHECK), crafted 0% (188 CHECK). Triage is live for 7 types, about 16% of corpus items.
On corpus drops the triage candidate vendors 137 of 173 uniques (legacy: 32) and loses
attention on 111 uniques, 36 set items and 9 runewords. No user labels exist yet.

1. **A listing without the Ethereal flag is non-ethereal — for every equipment type.** In the
   2026-10-03 pull (first 500 item files, 21,368 listings) the flag is absent on 17,938, `true`
   on 3,401 and `false` on 29: sellers mark ethereal copies and leave the rest unmarked. Filing
   unmarked listings as "ethereal unknown" leaves non-ethereal drops with "no non-ethereal
   listings" (126 of 280 named corpus drops; Harlequin Crest has 28 sellers, all "unknown").
   Normalize absent → non-ethereal in the listing adapter for armor and weapons too; "unknown"
   remains only for a *drop* whose capture lacks the flag. Sockets: absent on a listing of a
   named item means the item's native socket count, not unknown.
2. **The drop comparison is the gate; the listing replay is second.** Listings scored against
   their own "unknown" cohort passed at 91% while the same items failed as drops. The replay
   must present each listing to the engine exactly as a drop of that item would arrive
   (explicit non-ethereal, native sockets). A type is done when its corpus drops are not worse
   than legacy *and* its replay recall meets the target.
3. **Named items go live next.** After item 1, switch uniques and sets to triage type by type
   under the existing guard. They are the largest liquid category and the user's first
   priority; they should not wait for rules work on other families.
4. **Roll-aware pricing is one generic rule, not per-item models.** Five validated models and
   none live is the old per-item pace. Apply section 3.10 to every named item with a variable
   stat directly from its listings at band-build time. The leave-one-out comparison is a
   report across all items, not a per-item admission gate; an item whose roll-aware price is
   worse than its name median is listed in the report and falls back automatically.
5. **Bases before rares.** Bases are 5,811 valuable listings with 3 flagged. Get the listing's
   socket count, ethereal flag and superior ED into the bucket predicates (after item 1 the
   absent flags are no longer "unknown"), then measure again before writing more rules.
6. **Rares, magic and crafted are scored with CHECK as a hit.** Most have no numeric band, so
   by section 3.9 CHECK is the correct outcome. The replay reports "SELL, slow or CHECK" recall
   for these three categories against the same 85% target, and separately the share of cheap
   listings that get CHECK (limit 25%), so CHECK cannot become a catch-all.
7. **Status stays short.** Section 8 holds the current numbers and the next step, replaced each
   day, not appended to.

Order: 1 → 2 → 3 → 4 → 5 → 6. User action outstanding: label the 158 items in
`inventory_tracking/corpus/data/label.html` and save `labels.json`; until then the label score
is unavailable and the drop comparison against legacy is the only drop-side measure.

### P1.5 — Immediate fixes to the live triage (before P2; about 1 day)

Triage is already wired into auto-identify and shop, and its replay over the 551 corpus items
(2026-10-03) shows it is worse than the old logic for several types. Fix in this order:

| # | Gap | Measured | Fix |
|---|---|---|---|
| 1 | Every affixed item is VENDOR, including exact matches of the existing rules | 208 of 208 affixed items vendor; 2 exact charm/jewel rule matches and 8 near misses lost | load the 50 value-watch rows as pattern + bucket rules (section 3.9); exact match → SELL class, near miss → CHECK |
| 2 | No CHECK verdict | — | add it to the engine, HUD summary and scorer |
| 3 | White and socketed bases flagged from a pooled name band | 57 of 63 bases SELL or slow | bases get a band only through a bucket (sockets, ethereal, superior ED) from `wp-b-prices.json`; no bucket → VENDOR |
| 4 | Named items flagged from a pooled name band | 205 of 280 named items SELL or slow (159 slow); Pompeii's Wrath non-ethereal priced from ethereal asks | split bands by ethereal before anything else; a pooled band that mixes variants is shown as reference only and cannot produce SELL; use the lower quartile, not the median, against the keep price |
| 4b | A drop is priced from the median of better-rolled listed copies | Rusthandle +2 Vengeance shown SELL at 0.789 Ist; 17 of 19 listed copies are +3 | section 3.10: deciding stats from the listed-roll distribution, price from comparable-or-worse listings, "below listed rolls" is never SELL |
| 5 | Class items have no rules | 29 affixed class items, 28 without any rule | the section 3.8 gates as the first family rules after charms |
| 6 | Capture gates stop the item | 145 corpus items | judge the stats present; name the unreadable stat |

Guard for every later step: a type is switched to triage only when its corpus verdicts are not
worse than the legacy verdicts for that type; until then that type keeps the legacy path. The
per-type verdict table (type × verdict, legacy against triage) is part of every score report.


Each package ends with a score report (section 5). Sizes are estimates.

### P0 — Measurement (0.5 day; tooling exists)

- `inventory_tracking/corpus`: 551 distinct Alt+D captures, a labelling page for 158 of them
  (`data/label.html`), a scorer (`score.py`).
- Add: store the full observation of every auto-identified item, so the corpus grows with play
  and gets rares and magic items (today it has 59 rares, 116 magic).
- Add: a listing replay — run triage over scoped listings and report, per category, the share
  of listings priced at or above the keep price that triage flags, and the share of cheap
  listings it wrongly flags.
- Record the baseline with the current verdict logic.

Exit: baseline numbers written in section 8.

### P1 — Bands and the triage verdict (1.5 days)

- Build `bands.json` from `appraisal-market.jsonl` plus the 2026-10-03 pull: one vote per
  seller, name-level bands for every catalog item, liquidity class.
- Triage module: band lookup, keep-price comparison, verdict table 3.6. Identify summary and
  shop use it; the Alt+D card shows it on its first line.
- Remove the strict estimate gate from the displayed price (the gate stays available as the
  "exact cohort" confidence word).

Exit: every named item and commodity in the corpus has a band or an explicit "no listings";
false keeps from "build demand" are gone; triage under 50 ms per item.

### P2 — Named rolls and ethereal (1.5 days)

- Convert the roll buckets and thresholds in `wp-i-uniques-misc.json` (about 90 items) into
  `rules.json` rows mechanically, then review the result in one pass.
- For other named items with enough listings, derive a draft: which numeric properties
  correlate with the ask, and where the price steps are. Review drafts in bulk, by table.
- Ethereal: per-item effect (better, worse, irrelevant), from listings where both variants are
  priced, otherwise from the item class (mercenary weapons and armour better; most others worse).
- Bucket bands for items whose rules split the listings into groups of at least three sellers.

Exit: on the listing replay, at least 85% of named listings priced at or above the keep price
are flagged, and the user-labelled named items score in section 5 targets.

### P3 — Affixed families (2 days)

- Port the existing charm and jewel combinations to family rules.
- Transcribe the guide's §2 blue and yellow tables, §7 and §9 into family rules: caster jewelry,
  circlets, class items (section 3.8), rare weapons, boots, gloves, belts. Build profiles and
  priced listings are used to fill a paid-skill list per class and to check thresholds, not as
  the primary rule source.
- Add the guide's §8 worked examples to the corpus with their verdicts.
- Pull listings for these families with numeric filters matching the rule combinations.

Exit: rares and magic items in the corpus reach the section 5 targets; no family is unhandled.

### P4 — Bases and runewords (1 day)

- Family rules for runeword bases from `wp-b-prices.json` buckets and the base demand list.
- Completed runewords from name bands plus deciding rolls.

### P5 — Upkeep (0.5 day, then routine)

- Weekly page-0 pull (`pricing/tools/market_pull.py`, about 75 minutes paced) and band rebuild.
- Rune ladder rebuilt from the same pull.
- Score report kept with each rebuild; a verdict that changes for a labelled item is listed.

### Housekeeping (needs the user's confirmation, destructive)

- `tmp/` is 64 GB and `pricing/data/` 18 GB, mostly frozen coverage artifacts. Proposal:
  delete `tmp/`, move frozen `appraisal-*coverage*`, `*-review*`, `*-audit*`, `*-receipt*`
  artifacts out of the working tree.
- The 135k lines of bank tests stay untouched and are not extended; they are run before a daily
  publication of the detail engine only.

### Renewed execution sequence (reviewed 2026-10-03)

Execute P0–P5 in order below. Work on the triage path, not incremental improvements to
detail-engine coverage. Existing decoder, native/property projection, scoped market
normalization and collector are reused. No new per-item handlers, receipts, source
re-pinning or item-bank expansion.

1. **P0: establish the measurement loop and retain drops.** Extend
   `inventory_tracking/corpus/score.py` to understand SELL / SELL (slow) / SELF-USE /
   VENDOR, preserve the old verdict baseline, and report sell/slow recall, SELL precision,
   and band coverage specifically among sell-labelled items. Missing labels produce
   unavailable metrics, not zero scores. Persist each complete auto-identify observation
   before assessment, including items later classified VENDOR or whose assessment fails;
   merge them into the corpus without losing existing labels. Add scoped listing replay
   with the same input adapter as drops. Record the current baseline once; do not replay
   the old expensive role engine after every triage edit.

2. **P1a: build useful bands in one bulk pass.** Add `pricing/triage/` with an offline
   band builder and three-table loader. Import existing normalized observations,
   `pricing/raw/traderie/pull-20261003/` and the successful commodity pull. Deduplicate
   repeated listing snapshots and give each seller one vote per band. Write
   `pricing/data/triage/bands.json` with category/name/bucket, quartile/median asks,
   seller/listing counts, observed dates, listing-date span, rune-priced share and
   computed liquidity. Whole sets, components and known quantity lots stay distinct.
   Use actual listing dates for the newest-50 span: fetching old listings today must
   not make them appear liquid. Missing dates cannot establish the liquid class.
   Older-than-45-day bands remain visible with a stale marker.

3. **P1b: one fast engine and one verdict across entry points.** Implement drop and
   listing adapters, table predicates, band fallback and the section 3.6 verdict table
   in `pricing/triage/`. Reuse native-to-Traderie property projection without invoking
   `assess_result`, the role engine or an exact comparison contract. Preserve decisive
   missing properties; do not turn an absent required roll into a match. Load the three
   tables once per retrieval process and reload on changes. Configuration, including
   the keep-price threshold, belongs in these tables, not scattered service constants.
   Wire auto-identify and shop to this path. Alt+D places the same verdict and dated band
   at the top; existing detail and exact-cohort confidence remain available below.
   Measure warm/cold triage separately and the actual ten-item identify path, including
   process overhead. Run both score reports after each change; fix regressions in this
   path before broadening rules.

4. **P2: named rules and own-use tables, reviewed in bulk.** Convert the existing
   WP-I roll buckets into draft rows, review ambiguous prose in a single table, then
   derive additional roll splits from the priced listings. Evaluate listings and drops
   with the same predicates and rebuild bucket bands. Encode per-name ethereal/socket
   effects and the elite-ethereal fallback from section 3.7. Populate `own.json` only
   for the Echoing Strike Warlock and its mercenary unless the user expands that scope.
   A mention in another build or a levelling setup never creates SELF-USE or SELL.

5. **P3 and P4: finish families, then bases/runewords.** Port all 50 existing charm/jewel
   combinations as data rows. Transcribe `guides/pricing.html` §2/§3/§7/§9 into the
   remaining affixed families, following §3.8 above; build profiles and listings refine
   paid-skill lists and thresholds. Keep class weapons separate from generic weapons:
   evaluate base line, sockets, class/tree prefix, paid staff-mods and supporting affixes.
   Report missing gates; do not highlight unpaid skills as valuable because their native
   roll is perfect. Add §8 worked examples and the magic Stiletto acceptance case as
   labelled regressions. Use premium/tradeable words where no numeric band exists.
   Follow with base/socket/ethereal/ED rules and completed-runeword deciding rolls.
   Use focused positive, near-miss and missing-property tests for shared mechanics;
   listing replay and user labels measure coverage instead of per-item bank growth.

6. **P5: routine refresh and calibration.** Reuse the paced page-0 collector, rebuild
   the rune ladder and bands, and retain the two score reports plus changed labelled
   verdicts. Use guest numeric-filter queries for deeper families unless the user chooses
   another access method. Inspect collector state before any resume; do not duplicate
   an active run. Compare weekly listing IDs as a turnover hint, not proof of sales.

The first delivery is P0 + P1: measured fast SELL/slow/SELF-USE/VENDOR decisions with
dated fallback bands. It is not another detail-engine publication milestone. The only
success targets remain section 5; no gates from the frozen plans are reintroduced.

## 5. Measure of success

Two automatic reports, run after every change, both under a minute:

| Report | Source of truth | Target |
|---|---|---|
| Label score | the user's labels on corpus items | recall on sell/slow ≥ 90%; precision of SELL ≥ 70%; ≥ 80% of sell-labelled items show a band |
| Listing replay | priced scoped listings | ≥ 85% of listings at or above the keep price flagged; ≤ 10% of listings under a quarter of it flagged |
| Speed | service log | triage under 50 ms per item; a 10-item identify pass under 1 s |

A change that lowers a number is reverted or explained in section 8. No other gate exists.

## 6. Rules of work

- The score is the measure; report it with every change.
- No per-change ceremony: no coverage matrix, completion manifest, receipts or hash re-pinning.
- Prefer a dated, labelled approximation over "unknown". Missing evidence means vendor for
  ordinary items; the user's labels and the listing replay catch the exceptions.
- Rules are table rows authored and reviewed in bulk. A Python handler is written only for a
  mechanic a table cannot express.
- Focused tests for behaviour; no item-bank case per item.
- Status goes into section 8, a few lines per day. Do not append to handoff.md or STATUS.md.
- Live market pulls only through `pricing/tools/`, paced, with the scope filters.

## 7. Risks and open decisions

| Risk | Effect | Handling |
|---|---|---|
| Traderie needs a login beyond the first page (since 2026-10-03) | 50 newest listings per item; deep families (rings, charms, jewels) are under-sampled | numeric-filter queries per rule combination; optionally the user's session cookie |
| Asks are not sales | bands overstate slow items | liquidity class; diablo2.io fills where present; the user's labels |
| Non-Ladder market is thin for rares | family bands may not exist | class word instead of a number; rule recall measured on labels |
| Labels are one person's judgement | targets tuned to one view | that is the intended user; labels are re-editable |
| Corpus is biased to items the user inspected | score flatters named items | capture every identified item from now on |
| Market data ages | wrong prices | weekly pull; date shown on every band |

Decisions needed from the user:

1. **Keep price — resolved.** User selected 0.25 Ist and above on 2026-10-03.
2. **Deep pulls.** Guest-only with filter queries, or provide a Traderie session cookie?
3. **Self-use scope.** Only the Echoing Strike Warlock and its mercenary, or other characters too?
4. **Housekeeping.** Delete `tmp/` and move the frozen artifacts out?

## 8. Status

2026-10-03 — implementation continues; this is not completed assessment or verified live behavior.

- P0 baseline: 551 captures, 115 KEEP / 111 CHECK / 325 VENDOR, one numeric price.
  Full auto-identify observations are persisted. User labels are still absent, so label
  recall/precision/price-coverage targets cannot yet be measured.
- Current candidate replay: {'vendor': 463, 'slow': 58, 'check': 15, 'sell': 15}; 139 price bands.
  Scoped listing SELL/slow recall 37.84% (11520/30446);
  2698 additional CHECK listings; cheap false positives 0/482.
  Report time 50.69s; warm triage remains below 1 ms. Cold startup and
  full live ten-item capture/decode/identify timing remain unverified against the target.
- Implemented: reloadable three-table triage, Q1 decisions, separate CHECK, per-type legacy
  comparison and guarded routing; 50 charm/jewel watches, 409 clean base buckets across
  28 bases, 80 initial class-rule rows and 44 wearable-rule rows. Family bands preserve
  roll values; unknown socket/ethereal variants never substitute for known variants.
- Five validated named roll models compile comparable-or-worse price cells offline.
  Validation excludes the held seller from both stat selection and price prediction.
  Models split ethereal/socket states; below-listed rolls never SELL. Shared terminal/OSD
  colors mark deciding rolls and leave unrelated minima neutral when a model applies.
- Enabled types: magic/jewl, magic/lcha, magic/mcha, magic/scha, rare/boot, misc/ques, uniques/amul. Other types retain the legacy path;
  Alt+D stores their triage candidate for evaluation. Python changes require worker restart;
  table changes reload automatically. No host restart or live end-to-end verification done.
- Latest fix: drops and listings share verified non-equipment mechanics. Missing jewelry,
  charm and jewel flags normalize to non-ethereal, zero sockets and empty contents;
  unknown armor flags remain unknown and explicit capture flags are preserved.
  Validation: 84 selected tests pass; Ruff clean; final replay has no enabled-type attention losses.
  All three saved unique amulets retain attention (SELL slow); amulet triage is restored.
  Unique bands still separate unknown/true/false ethereal states; mixed bands remain
  reference-only. Coverage gains are from mechanics parity, not borrowed variants.
- Next: finish guide-derived class/affixed rules and worked-example labels, roll-aware named
  coverage and family pricing, base/runeword coverage, own-build rules, then expand guarded
  rollout and verify live timing. Low base recall reflects missing source socket/ethereal
  fields as well as unfinished rules. Rusthandle's acceptance case is resolved: comparable-or-worse Q1 governs, giving CHECK
  with two sellers; focused regression preserves the worse-roll ask in that comparison.
- Keep working only under this plan. No item-bank expansion, publication/receipt loop,
  unrequested collection or destructive housekeeping. The old shop-catalog predicate test
  mismatch (20 versus 42) is unrelated; historical detail-engine edits remain untouched.
