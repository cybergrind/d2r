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

- **liquid**: at least 10 independent priced sellers with a listing updated within 14 days
  of the cohort evidence date;
- **thin**: at least 3 priced sellers, but fewer than 10 establish recent activity;
- **none**: fewer than 3 priced sellers.

The activity rule is provisional pending the user's labels (section 5). The Steering 2 audit
found that old inventory and undated rows incorrectly vetoed independently dated activity.
Unknown/future dates cannot establish activity; fetching old listings today cannot either.
Keep the newest-50 span as a diagnostic, not a veto. Historical bands describe activity at
their evidence date and retain the stale marker.
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

### Steering 3 (progress check, 2026-10-04 02:00) — takes precedence over everything below

Done since Steering 2: every observed type routes to triage (185 routes); explained VENDOR
corrections and the liquidity audit are written; live identify passes of six and four items
took 91 ms and 308 ms with triage lookups of 2–9 ms (speed target met when warm; cold start
after a restart is still about 18 s of background warm-up). Listing attention 52.2% → 57.9%.
Corpus (746 items): 446 VENDOR / 203 CHECK / 95 slow / 24 SELL. Labels: 1. `own.json`: empty.

1. **CHECK has become the catch-all for named items — cut it.** 178 of the 333 unique and set
   drops are CHECK (53%); before Steering 2 it was 8. Steering 2 item 2 ("no exact cohort →
   CHECK, never VENDOR") was too blunt and is replaced by this ladder, applied in order:
   - exact variant cohort with at least three sellers → its Q1 decides (as now);
   - otherwise drop the socket facet, then the base facet, keeping ethereal status; the first
     level with at least three sellers decides SELL / slow / VENDOR. Rockstopper has 31
     sellers at Q1 0.39 Ist and must not end as "no priced listings matching base, ethereal
     status and sockets" (57 drops end there today);
   - if only the name band has three sellers and its Q1 is under the keep price, and the drop
     is not an ethereal or socketed copy of an item whose ethereal/socketed cohort asks more
     → VENDOR. 87 of the 178 are in this group (Death's Touch 0.10 Ist, 10 sellers);
   - CHECK remains only for: fewer than three sellers at every level, a reference at or above
     the keep price that cannot be placed, or a capture that lacks a flag the price depends on.
   A complete paid-roll pattern on a liquid item is a price verdict, not CHECK (six Harlequin
   Crest drops, 30 sellers, Q1 0.67 Ist, are CHECK today).
   Target: at most 15% of named corpus drops are CHECK. The score report prints the CHECK
   share per rarity; a change that raises it is explained.
2. **Bands are over-split.** 15,927 of 19,566 bands have one or two sellers. Build coarse to
   fine: split a cohort by a facet (sockets, base, roll bucket) only when each part keeps at
   least three sellers and the Q1 values differ by 1.5× or more; ethereal is always split.
   Otherwise the merged cohort is the band. This removes most "none" bands and most of the
   CHECKs in item 1 at the source.
3. **Stop the micro-batches.** About twenty rule batches since Steering 2 each recovered
   20–110 listings and together moved attention by under six points; each added tests, a
   replay log and a status paragraph (287 `tmp/triage-*` artifacts). Remaining misses:
   bases 4,742, rares 4,160, magic 1,155, uniques 1,154, runewords 855. From now on a rule
   batch is taken from one miss-cause table per category, sorted by distinct sellers, and is
   worth doing only when it recovers at least 300 valuable listings or fixes a corpus drop.
4. **Count sellers, not listings.** 419 of 513 rejected rare-amulet listings come from two
   sellers. Listing recall and the cheap-flag rates are reported with one vote per seller per
   cohort or pattern; the section 5 targets apply to that figure. The per-listing figure stays
   as a secondary line.
5. **Bases: settle the missing socket property with data, once.** 1,585 valuable base listings
   carry no socket property. Compare their asks, per base, with listings that state 0 sockets
   and with those that state the usual runeword count; adopt whichever they match and record
   the result in the table. If neither, they stay excluded and the base target is measured
   without them.
6. **Fill `own.json` in one pass** from `guides/warlock.html` §0–§1 and the mercenary section
   (scope: Echoing Strike Warlock and its mercenary, the default until the user says
   otherwise). SELF-USE has never been shown.
7. **Section 8 is rewritten, not appended.** It is 340 lines of per-batch narrative. Replace it
   with at most 30 lines: current numbers, live-run facts, next three steps. History is in git.
   No status paragraph, replay log file or evidence file per batch.
8. Open rates to bring inside limits after items 1–4: cheap CHECK 29.7% (limit 25%), cheap
   SELL/slow 10.14% (limit 10%, 14 listings, audited as gem-paid asks — leave as measured).

Order: 1 → 2 → 7 → 4 → 5 → 6 → 3.

User actions outstanding: label the dispute page (`inventory_tracking/corpus/data/label.html`,
one label so far); skim `inventory_tracking/corpus/data/vendor-corrections.md`.

### Steering 2 (progress check, 2026-10-03 19:00) — items 1, 3, 4, 6 done; item 2 replaced by Steering 3 item 1

Measured since the afternoon check: listing attention 37.8% → 52.2% (SELL/slow 41.8%); bases
0.05% → 17.9%, rares 0% → 35.3% (all CHECK), magic 4% → 33.9%, runewords 35% → 69%; uniques
91% → 79% and sets 93% → 71% after listings were made to arrive like drops (the earlier figures
were inflated). Twelve types live, all niche (charms, jewels, rare boots, unique jewels/charms,
set sceptres, Amazon spears, magic Barbarian helms). Named drops: 109 "attention losses" against
legacy. Nothing has been verified in the running game.

1. **Legacy is not the truth: an evidence-backed VENDOR is a correction, not a loss.** Of the
   109 losses, 67 have real asks under the keep price (Vidala's Snare Q1 0.12 Ist, 6 sellers;
   Iratha's Collar 0.10 Ist, 5 sellers) and 6 are "below listed rolls" — legacy flagged them
   from build-list mentions, which is the false keep this plan set out to remove. This answers
   the pending question: **yes, accept them.** The routing guard becomes "no *unexplained*
   loss". A loss is explained when triage shows a cohort of at least three sellers whose Q1 is
   under the keep price, or a below-listed-rolls result with its cheapest ask. Explained losses
   are written to one review table (name, legacy verdict, triage reason, Q1, sellers) for the
   user to skim; they do not block routing.
2. **About 36 losses are real; fix those, then route uniques and sets.** 26 "no priced
   listings matching base, ethereal status and socket", 4 runewords without a base/variant
   band (Insight, Spirit), 5 captures missing the ethereal/socket flag, 1 without listings.
   For these the fallback of section 3.4 applies: no exact cohort → the name band as
   *reference* → CHECK, never VENDOR. The same holds for high asks on thin evidence
   (Fortitude, Q1 131 Ist, 2 sellers → CHECK, not VENDOR): VENDOR needs evidence that the item
   is cheap, not absence of evidence that it is dear.
3. **The 85% listing target does not fit named items as defined.** 30,956 of 34,058 priced
   listings (91%) ask at or above 0.25 Ist: the practical minimum ask is one mid rune, so "ask
   at or above the keep price" marks nearly every listing as valuable, including optimistic
   asks on items whose cohort Q1 is 0.1–0.2 Ist. For uniques, sets and runewords, measure
   recall over listings whose own cohort (name + variant) has Q1 at or above the keep price;
   report the remaining listings separately as "asks above a cheap cohort". Do not add rules
   or loosen thresholds to chase the old number (the Frostburn audit in section 8 was right).
4. **Liquidity carries the SELL verdict, so check it.** Only 626 of 11,473 bands are liquid and
   the corpus replay gives 13 SELL against 95 slow. List the 30 highest-Q1 named cohorts that
   are classed thin or none and the 30 most-listed ones; if well-known liquid items (Harlequin
   Crest was "thin" with 28 sellers) are misclassed, fix the class rule before anything else
   in this list — detecting liquid items is the first goal in section 1.
5. **Bases are now the largest miss**: 4,845 valuable base listings unflagged, more than all
   named misses together (about 2,300). After items 1–2, bases come before any further
   affixed work.
6. **Verify live today.** Restart the service once uniques and sets are routed, identify ten
   items, and record the timing and the HUD lines in section 8. Offline replay numbers do not
   replace this.
7. **Labels: use the disputes.** The most useful labelling set is no longer the 158 sampled
   items but the 109 losses plus the 48 CHECK and 13 SELL results. Rebuild `label.html` from
   those so the user's labels settle exactly the cases where legacy and triage disagree.
8. **Detail-engine edits stay minimal.** Changes under `pricing/knowledge/` are limited to
   shared normalization that triage reads; no new reviews, receipts or bank cases there.

Order: 1 → 2 → 4 → 6 → 3 → 5 → 7.

### Steering (progress check, 2026-10-03 afternoon) — done or superseded by Steering 2

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

2026-10-03 — incomplete; §4 Steering 2 governs execution.

- Corpus: 746 items: 426 VENDOR / 93 slow / 203 CHECK / 24 SELL; 248 numeric bands.
  Replay now merges new captures and retains archived cases and labels; 138
  additional captures are explicitly marked without a legacy baseline. Original
  551-item cohort verdict counts and listing metrics remain unchanged.
  185 routes enabled: all previously checked 744 saved captures use triage. The four final cases
  were compared with actual identify results in host run
  `20261003T160844Z-ce388f78`: magic head/armor stay VENDOR, Bane’s Oathmaker
  moves VENDOR → CHECK; no attention loss.
  User labelled Corruption Knot CHECK. Its FCR/two-resistance/MF combination
  now matches CHECK; all 14 rare-ring captures route without legacy calls. Observed unique/set types have
  no unexplained legacy losses. Named missing/thin comparisons remain CHECK;
  evidence-backed VENDOR corrections and liquidity audit are in the corpus data.
- Listing attention recall **57.91%**; SELL/slow recall 45.94%; cheap SELL/slow
  false positives **10.14% (14/138)** after quantity-correct scoring (see below). Named cohort recall: uniques 86.86%, sets 89.91%,
  runewords 75.22%. Base SELL/slow 19.61% (1157/5899); CHECK is separate.
  Rare attention 39.35%, crafted 42.64%, magic 40.22%. These remain below §5.
- Bases: 221 names / 913 generated base rules, including 170 market-backed
  variants with legal non-starter recipes. Of these, 108 newly admitted variants
  have two independent priced sellers: CHECK with reference asks. SELL still
  requires three. +229 base CHECK listings (214 above keep), no cheap flags or
  saved-corpus changes. Two Glorious Axe listings also become slow through
  three comparable-or-worse sellers (ethereal, six sockets, 15 ED, +2 AR).
  Native shield stats, superior modifiers, staffmods, full Void dagger line
  and possible socket preparation preserve their material distinctions.
  Unsocketed BO/trap/ES/Abyss/Bone Spear candidates never borrow socketed prices.
  Latest cause audit before the two caster additions: 2,168 missing-facet
  listings, 1,353 without matched bands, 1,172 CHECK and 66 cheap matched bands.
  No additional clean unsocketed cohort had three matched sellers above keep.
  Source recheck: 1,585 valuable base rows lack a socket property; the only
  present-but-rejected socket value is impossible (10 on a Heraldic Shield).
  These are source gaps, not a dropped parser field; do not replace them with zero.
- Rare-amulet source audit: 419/513 rejected listings belong to two sellers;
  310 lack +2 class skills and 145 lack 10 FCR (overlap). Do not relax gates
  to chase this concentration. Listings with the full 15–20 FCR / 10+ mana /
  4–10 mana-regeneration caster recipe now normalize as recipe-inferred crafted;
  preserve reported rarity and never alter captured item quality.
  128 listings reclassified; +24 valuable CHECK, unchanged corpus and cheap flags.
- Magic caster-tree circlets: seven scoped paid +3-tree/20-FCR combinations
  added as CHECK; +39 valuable listings, no corpus or cheap-flag changes.
  Magic-circlet recall 14.39% → 43.94%. Lower rolls and unreviewed trees excluded.
- Affixed additions: stacked Amazon javelins (6/40, 5/40, 6/30), Echoing throwing
  weapons, and Fist of the Heavens scepters. These routes are enabled. Javelin
  and Echoing prices preserve base/ethereal/additional-modifier facets; scepter
  evidence supports CHECK only. Three saved magic-scepter cases agree with
  legacy; no saved Echoing-family captures exist, so host verification is pending.
- Rare physical weapons: separate Fool’s pattern requires both level-scaling
  stats, 200% ED, 30 IAS, elite ethereal sword/axe/mace and durability solution.
  +21 valuable CHECK listings; ordinary damage-only thresholds unchanged.
  Enabled these three routes: one saved sword case agrees with legacy VENDOR,
  no axe/mace captures exist. Full-gate tests and scoped asks support the new
  pattern; numerical rare prices and host verification remain outstanding.
  Extended physical Fool’s recognition to class claws: +35 CHECK listings.
  Lower tiers mention upgrade costs; ethereal copies without proven repair or
  indestructibility mention repair/Zod review. No ready-to-use value is inferred.
  Two rare-claw routes enabled; one saved case agrees with legacy VENDOR.
- Supporting-roll handling now follows §3.9: required primary gates, distinct
  supporting categories and structural conditions remain strict; positive low
  supporting rolls give CHECK with readable shortfalls. +45 rare and +21 crafted
  valuable listings recovered; no SELL, cheap-flag or saved-corpus verdict changes.
  Commodity VENDOR headlines label unsupported high asks as reference evidence.
- Validation: **536 triage/appraisal/corpus tests pass**, Ruff clean. Reusing
  the existing artifact snapshot per ingestion batch reduces catalog reads and
  hashes: market ingestion 53.71 → 15.93 s. All 101,010 normalized rows and the
  catalog have identical digests before/after; next-batch freshness tested.
  Full replay **27.35 s**, `tmp/triage-throwing-replay.log`; cheap false
  positives unchanged. User ring correction is the only saved verdict change.
  All 700 captures from that replay pass guarded runtime replay with zero legacy calls; warm
  median 0.65 ms, maximum 1.23 ms.
- Host run `20261003T160844Z-ce388f78`: 53 identify passes / 93 items, median
  275 ms, first pass 17.128 s, warm maximum 1.075 s (five items). Warm named
  triage examples took 2.4–2.6 ms. Restarted run `20261003T180934Z-2b9d5565`
  exposed an 18.489 s cold Greater Talons legacy lookup. Service wiring now
  warms and refreshes all identify children. Real-process captured replay:
  background warm-up 18.406 s, subsequent lookup 142.4 ms. Host restart and
  ten-item verification are still pending; offline replay is not live proof.
  User-confirmed run now contains 19 identified items over seven passes, no
  assessment errors. Latest four-item pass: 1.177 s; Amulet legacy 1089 ms
  versus Horned Helm triage 2.5 ms. All 19 now route to triage in offline replay
  with unchanged verdicts (warm 0.8–1.6 ms). No new service run or ten-item pass
  is recorded. HUD log has one earlier surface warning; rendering not confirmed.
  New host run `20261003T202202Z-82a8f89c` records ten items in two passes:
  six in 91.0 ms, four in 308.2 ms, no assessment errors. Nine triage lookups
  took 1.8–8.7 ms; newly captured magic Sacred Rondache used legacy (183 ms).
  Its VENDOR agrees with triage; magic/ashd is now enabled. A single ten-item
  pass and actual HUD rendering remain unverified.
- 2026-10-04: fixed commodity routing beyond previously observed diamonds.
  All rune/gem families are enabled (134 total routes). A regression test
  constructs every one of the 68 local rune/gem definitions and forbids both
  legacy backends; all pass. Seven runtime tests pass, Ruff clean. This is a
  reloadable rule-table change; the earlier Python changes still need restart.
  Audit also found 52 real item-family routes with positive listing evidence
  still disabled (distinct from catalog-name/bundle rows that are not families).
  Review these next: `tmp/triage-unrouted-family-evidence.json`.
- 2026-10-04: supported fungible rune/gem lots now compare total sale value
  against 0.25 Ist; the HUD shows lot and unit asks. Singles and unmatched lot
  sizes do not borrow a bulk quote. Mixed bundles remain separate. Source
  audit: 71 qualifying lot sizes across 27 types. User chose CHECK/save toward
  a lot for single drops. Implemented with dated lot/unit asks and target
  quantity; prefer liquid evidence, then smaller supported lots. No single-unit
  sale estimate is inferred. +330 listing CHECKs, including 11 cheap units
  intended for accumulation; SELL/slow scores unchanged. 548 tests pass,
  replay 22.11 s (`tmp/triage-save-lots-replay.log`).
  Like-for-like lot-based replay: old attention 55.53%, new 56.50%; +300
  SELL/slow listings. Cheap flags unchanged at 14, but correcting quantity
  reduces the cheap denominator 634 → 138, exposing 10.14% (above target).
  This is not a new false-positive regression. Audit of all 14 found gem-paid
  asks across seven sellers on named items whose matched cohort Q1 is higher.
  Scope/status and currency conversion are valid; no parser correction proved.
  Retain these measured misses rather than altering rules just to pass the score.
  Evidence: `tmp/triage-cheap-flags-audit.json`.
  547 triage/appraisal/corpus tests pass, Ruff clean; replay 26.64 s,
  `tmp/triage-commodity-lot-replay.log`, baseline
  `tmp/triage-commodity-lot-counterfactual.json`. All 724 captures route.
- 2026-10-04: rare skill-glove bands now compare equal-or-lower lightning
  resistance (5–30, verified local prefix table), preserving skill, IAS, leech,
  base, ethereal and every other modifier. Bulk audit: 14 same-modifier-set
  affixed groups with three sellers; three groups support this one-roll
  comparison. Ten listings move CHECK → slow; no cheap flags or existing
  saved-item regressions. 224 triage tests pass; Ruff clean. Replay 25.04 s,
  `tmp/triage-rare-glove-replay.log`; scoped examples saved in
  `tmp/triage-rare-glove-priced-examples.json`. Bands total 19,271.
- 2026-10-04: captured Echoing Throwing Spear `60d2656bbc2c` (+3 Warcries,
  10 IAS) now uses same-base/ethereal comparable-or-worse IAS, with all other
  modifiers separate: slow, 0.789 Ist Q1, 11 sellers, evidence 2026-10-03.
  Missing IAS means no suffix for this explicit comparison only; unreadable
  values remain unknown. Runtime headline verified on the actual saved capture.
  New Jade Talon capture is SELL; enabled unique elite-claw route (no possible
  attention loss; no historical legacy baseline for this capture).
  Python change requires host restart. Also priced +2-Amazon/+3-Javelin/40-IAS
  Maiden and Matriarchal cohorts, separately from stacked Javelin prefixes.
  +8 valuable SELL/slow listing results, no extra cheap flags. Full replay
  25.68 s, `tmp/triage-echoing-ias-replay.log`; 545 triage/appraisal/corpus tests
  pass, Ruff clean. Broad magic-pattern audit found no other complete cohorts
  of three sellers with all material facets known.
- Magic +3-skill/20-IAS gloves now have exact family bands: skill, base,
  ethereal status, sockets/contents and full modifiers remain distinct.
  Gauntlets cohorts: Martial Arts 4.053 Ist Q1 (9 sellers), Bow 4.053 (10),
  Javelin 11.421 (3), cached asks reviewed 2026-10-03; all currently thin/slow.
  23 listings move CHECK → slow, unchanged attention recall and cheap flags.
  Existing saved verdicts unchanged; two new captures merged separately.
  Bands rebuilt (16,037 total); 221 triage tests pass, Ruff clean, replay
  23.79 s (`tmp/triage-glove-bands-replay.log`). Different bases/skills/ethereal
  status/additional modifiers cannot borrow these prices.
- Shared support groups now include mana on caster circlets and life leech on
  skill gloves. Seven and twelve independent scoped sellers respectively
  support these combinations; primary skill/speed gates remain unchanged.
  +69 valuable CHECK listings, no cheap flags or saved-corpus verdict changes.
  220 triage tests pass, Ruff clean; replay 23.50 s,
  `tmp/triage-support-affixes-replay.log`. Source audit:
  `tmp/triage-support-affix-evidence.json`. No numerical family band inferred.
- Crafted boots/belts now share reviewed rare-item combinations: 30 FRW and
  two resistances; or 24 FHR, 40 life, strength and resistance. Ten and three
  independent sellers respectively support CHECK; no pooled numerical prices.
  +28 valuable listing CHECKs, no cheap flags or existing corpus changes.
  218 triage tests pass (including four new shared-pattern cases), Ruff clean;
  replay 23.46 s, `tmp/triage-crafted-utility-replay.log`. Crafted boots enabled,
  belt already enabled; saved belt verdict remains VENDOR. Latest host pass:
  four items in 83.6 ms, all triage retrievals 1.8–2.9 ms, no errors.
- Physical throwing weapons: six shared rare patterns require ethereal,
  300 ED and 30 IAS, with upgrade review for lower-tier bases. Cached Double
  Throw guide verifies mastery replenishment; no replenish affix required for
  this Barbarian use. +40 valuable CHECK listings, no cheap flags or changes
  to existing saved verdicts. Three throwing-family routes enabled; no saved
  rare throwing captures yet. Pure CHECK rules add no numerical prices.
- `label.html` now offers CHECK and seeds saved labels. The one supplied CHECK
  label agrees (1/1); SELL recall/precision/price coverage remain unestablished.
  `own.json` remains empty.

- 2026-10-04: enabled 33 additional named-item families after replaying 4,489
  eligible listings through synthetic capture normalization without verdict or
  decision-price differences. All 66 representative synthetic examples now use
  fast triage with legacy retrieval forbidden; all 728 saved captures still do.
  Warm synthetic retrieval median 0.481 ms, maximum 0.641 ms. These are offline
  checks, not live capture proof. Evidence: `tmp/triage-named-route-review.json`.
  Enabled a further 17 base/affixed families after 3,564 matching listing/capture
  results (`tmp/triage-other-route-review.json`). Before/after runtime verification:
  all 34 examples previously called legacy; now all use triage with unchanged
  verdicts. No saved affected captures exist; all 728 corpus entries still route.
  Seven runtime tests pass; preceding combined suite: 549 pass. Both score reports
  regenerated in `tmp/triage-family-routing-replay.log`; listing attention remains
  56.50%, cheap SELL/slow 14/138 (10.14%). Routing adds no price evidence.

- 2026-10-04: fungible holdings can now supply a smaller supported sale lot.
  Reports explicitly say sell in lots of the supported quantity and quote one
  lot; no extrapolated whole-holding price. Singles retain accumulation CHECK.
  Offline audit found 248 missed splittable listings; +240 valuable SELL/slow
  results, no extra cheap flags or saved-corpus verdict changes. Rune detection
  90.62%, gems 62.14%; total attention 57.27%. Red/green regression covers larger
  holdings, insufficient/unknown quantities, mixed gems and sparse sellers.
  Replay 27.15 s (`tmp/triage-split-lots-replay.log`), 550 combined tests pass,
  Ruff clean. Python changes require host restart.

- 2026-10-04: market-backed base admission now permits the same equal-or-better
  modifiers already supported by compiled comparison bands. Exact modifier-set,
  base, quality, ethereal and socket distinctions remain. Previously exact rule
  conditions blocked superior bonuses even when a valid lower-roll band existed.
  Shared comparison bounds prevent rule/band divergence. Red/green regression;
  551 combined tests pass, Ruff clean. Rebuilt 19,273 bands; replay 26.22 s
  (`tmp/triage-base-comparison-replay.log`). Two additional valuable SELL/slow
  listings, no extra cheap flags. Four new captures merged; all 732 use fast
  retrieval with legacy forbidden. Broader cause audit retained in
  `tmp/triage-base-misses-current.json`: many missing socket/quality fields and
  unsupported combinations remain; this fix does not fill those evidence gaps.
  Latest host identify at 00:51 Minsk: four items in 78.1 ms; lookups average
  2.1 ms, maximum 2.5 ms. Same host process, no recent Python restart observed;
  single ten-item pass remains unverified.

- 2026-10-04: base importer now counts independent sellers across supported
  equal-or-lower modifier rolls before admitting a variant. Previously each
  exact roll needed two sellers, defeating the existing comparison policy.
  Comparison-pool conditions are separate from runtime CHECK patterns, so
  lower rolls cannot borrow higher-roll prices or become CHECK accidentally.
  228 market variants (+58), 234 covered base names, 19,531 bands. Listing
  replay: +13 valuable SELL/slow, +43 CHECK, no added cheap flags. 552 tests
  pass, Ruff clean; reports 25.34 s (`tmp/triage-base-cohort-replay.log`).
  Enabled base/h2h using a source-backed synthetic 15-ED/three-socket Claws
  CHECK example; all saved captures still avoid legacy retrieval.

- 2026-10-04: added magic trap-claw socket alternative: +2 Assassin or +3
  Traps, +3 Lightning Sentry and two sockets. Nine independent scoped priced
  sellers per prefix in cached 2026-10-03 data; guide body/review log updated.
  No pooled numerical price, unrelated skills and weak prefixes remain excluded.
  +29 valuable CHECK listings, no cheap flags or saved-item verdict changes.
  All 44 matching cached observations also pass through synthetic capture/fast
  retrieval. 553 tests pass, Ruff clean; reports 26.04 s
  (`tmp/triage-socket-claws-replay.log`). Magic elite-claw attention rises from
  0/84 to 29/84; other missed affixed families remain queued.

- 2026-10-04: rare caster amulets now count mana as one useful supporting
  category, retaining +2 class skills, 10 FCR and a second supporting category.
  Ten independent scoped sellers support the previously missed combinations;
  +44 valuable CHECK listings, no additional SELL/cheap flags. Caster crafts
  retain separate support rules because their recipe grants mana. Guide body
  and review log updated. 554 tests pass, Ruff clean; reports 26.66 s
  (`tmp/triage-amulet-mana-replay.log`). Eight new live captures retained.

- 2026-10-04: crafted +2 class / 15–19 FCR amulets now retain CHECK with the
  shortfall from 20 FCR. Local recipe confirms stacked 5–10 + 10 FCR; at least
  two priced scoped sellers per class support lower rolls. +111 valuable CHECK
  listings, no cheap flags. 562 combined tests pass; reports 24.95 s
  (`tmp/triage-crafted-fcr-replay.log`); guide updated.
- 2026-10-04: fixed Alt+D request-16's unsupported material widget. Runtime
  getter RVA 220b60 returns widget+608 directly; the ordinary grid selector
  cannot handle it. Added build-specific widget recognition, stable pointer and
  item-code/location checks, and existing ownerless-material decoder wiring.
  Saved initial capture resolves unit 1776519725 (`ua4`). 759 hover/appraisal/item
  tests pass; Ruff clean. Evidence and regression fixture are recorded in
  `inventory_tracking/hover_research.md`. Restart `make serve` for live verification.

- 2026-10-04: Alt+D now reads/rechecks currency-tab stack counts using the
  existing verified item-data offset. Shared decoding preserves quantity for
  collection and hover; triage retains commodity counts without treating weapon
  ammunition as a sale lot. Regression covers one/15/32 Perfect Rubies against
  a supported 15-gem lot, plus count changes during revalidation. 1,078 combined
  hover/appraisal/item/collection/triage tests pass, plus 11 focused adapter tests
  (four added after the combined run started); Ruff clean. Replay 25.21 s,
  unchanged listing metrics (`tmp/material-stack-replay.log`). Live stack capture
  still requires the host restart; no new live verification claimed.

- 2026-10-04: corrected an unreachable physical-weapon exception: Phase Blade
  intrinsically supplies durability, so the outer ethereal requirement must not
  exclude non-ethereal copies. Other melee bases still require ethereal status
  and repair/indestructibility/socket support. Required damage/IAS and Fool's
  pair are unchanged. Cached non-ethereal 288-ED/30-IAS/Fool's example now CHECK;
  one seller is not a price. +1 valuable CHECK listing, no SELL/cheap changes.
  570 combined tests pass; Ruff clean; replay 26.08 s
  (`tmp/triage-phase-replay.log`). Guide body/review log updated.
  Audit artifacts: `tmp/triage-phase-blade-audit.json`,
  `tmp/triage-circ-misses.json`. Next normalization gap identified: market names
  Mithril Point / Griffon Headdress differ from metadata Mithral Point / Griffon
  Headress, leaving those listings without a family. Verify aliases from local
  definitions before changing comparison identities and rebuilding bands.

Next:
1. Inspect the requested restart/ten-item identify run and HUD results. Allow
   roughly a minute for background warm-up; verify rather than infer success.
2. All observed types now route to triage. Continue source-led family coverage
   without inventing socket, rarity or ED values; test unseen families against
   their paid patterns. Keep both reports below one minute.
3. Then continue affixed coverage, runeword thin evidence, commodity handling
   and own-use rules; retain required primary gates.
4. Apply user labels to the dispute page and measure every §5 target, including
   live performance. Intermediate batches and green tests do not finish the goal.
