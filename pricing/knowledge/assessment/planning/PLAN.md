# Drop assessment plan — active since 2026-10-03

This is the plan for item assessment; the end goal, measures and stopping rule are in the
"Current contract" section of COMPLETION_CONTRACT.md (2026-10-06). It replaces the older execution rules of
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

Materials-tab workstream (2026-10-06): [inventory, market collection and implementation plan](MATERIALS.md).
Covers all 33 individual/bundle entries, including bulk quantity and recipe-set distinctions.

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
Steering 4 qualifies the verdict: equipment below 1 Ist without explicit endgame variant
demand is SELL (slow), even when seller activity is liquid. Starter, budget, Hardcore and
unspecified guide mentions do not count. Demand never creates a numerical price.

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

User clarification (2026-10-04): Steering 3's supported-split requirement applies to
roll comparisons too; selection concentration alone does not authorize a price split.
When validation fails but a robust deciding-roll signal has only one or two comparable-or-worse
sellers, retain CHECK and show the name band only as reference. Do not publish the rejected
model's Q1 as an item estimate. Rusthandle +2 Vengeance / 50% ED is this acceptance case:
its diagnostic Q1 is 0.34725 Ist from two sellers, but the pooled roll model fails validation.
It is not below every listed roll, and the name band must not turn this sparse comparison into SELL.
Steering 4 below extends this selection safeguard to below-selected rolls regardless of
comparable seller count; refreshed/coarsened cohorts must not silently undo the acceptance case.

## 4. Work packages

### Steering 11 (progress check, 2026-10-06 20:00) — sets the queue; Steering 9 pace rules stand

Measured from the score files of 19:36: attention 78.29% (17,241 of 22,022; target 85%),
bases 67.4%, rare 45.1%, magic 55.9%, cheap SELL 10.37% (17 of 164), guide rows 373 of 404
(92.3%, all executing, 29 rows failing), worked 36/36, false positives 16/16, corpus CHECK
rare 3.3% and magic 2.2%, named CHECK 12.1%. Steering 10 is done: 2,616 of 2,735 learned
rules were dropped, both failing tests pass, tiers span the affix group. Run at 19:55:
2,886 tests pass in `tests/pricing/triage` and `tests/inventory_tracking`; one HUD map-slot
test fails and Ruff reports 18 errors (`hud/widgets.py` 17, `appraisal/service.py` 1), none
from this plan's files except possibly the last: check it.

The target needs 1,478 more votes. What is left, without the below-keep asks: rare, magic
and crafted 1,927; bases 1,172; named items 491; gems 130.

1. **Rare and magic: exact combinations are exhausted; score the item instead (1,927 votes).**
   After the fix the learned rules add six rare votes. A rare is a near-unique vector, so
   three sellers with the same vector will not exist. Replace the combination match with a
   count, per family: (a) the paid properties are those whose upper tiers are over-represented
   in listings at or above the keep price compared with the 872 rare and magic drops of
   the corpus; (b) a property counts when its roll is at or above the lower quartile of
   that property among the priced listings of the family; (c) the item is CHECK when its
   count reaches the family threshold, VENDOR below it. The threshold is the smallest count
   that keeps the corpus CHECK share at or under 8% for rare and for magic. The reference
   shown is the band of listings with the same count; it is never a price. Validate on
   sellers held out of the derivation (one third) and report held-out recall beside the
   replay number. The War Boots cases (fire 8, fire 9) and the two tests of Steering 10 stay
   green. One pass, one score run. Exit: rare and magic recall reported with the guard
   numbers; no hand tuning per family afterwards.
2. **Bases to 70% (115 votes) by dominance, not by exact match.** An item that is at least
   as good as a priced variant is worth at least that variant: a superior base takes the
   normal band of the same ethereal status and sockets as a floor (131 votes are
   `base_rarity_missing`); a base with ED x takes the nearest priced band with lower ED
   (99 votes). The line says "at least". Normal never borrows from superior. Then stop on
   bases: the remaining 795 are one- and two-seller staffmod variants and stay CHECK.
3. **Guide rows to 95% (11 more rows).** 29 rows fail. Work them from the list, largest
   group first: primer `#miss` (20 examples expected flagged, VENDOR "no listings"), primer
   §2 bases (12), warlock §1 and §3 own-use (15). Where the October asks contradict the
   guide row, correct the guide with a dated pass instead of bending the engine. Ten
   listed failures have an actual verdict that is among the expected ones: print the unmet
   condition in the failure, or they are not failures.
4. **Named roll placement** (uniques 237 `roll_comparison`, 166 `no_matched_price`) after
   item 1, as in Steering 9 item 3.
5. **Cheap SELL rate: no more work until the user decides the measure.** The 17 flagged
   cheap listings are spread one or two per type inside cohorts that are otherwise valuable
   (unique Large Charm: 486 valuable sellers, one cheap listing; unique body armour: 528
   and one). That is a seller pricing low, not a wrong verdict, and no roll boundary
   separates it. It is reported as 10.37%, over the limit, with that breakdown. Proposal
   for the user: count a cheap listing as a false flag only when fewer than 90% of the
   sellers in its cohort are at or above the keep price.

Forecast, not a promise: items 1, 2 and 4 together need to recover about three quarters of
their votes to reach 85%. If the held-out number for item 1 comes in under half, report
the reachable figure with the evidence after that pass rather than adding rule batches.

Order: 1 → 2 → 4, with 3 alongside.

### Steering 10 (live finding, 2026-10-06 19:30) — done

Score files of 19:22: attention 80.25% (75.1% at Steering 9), rare 59.5% (44.9%), bases
67.4%, cheap SELL 10.37% (unchanged, still over). The pace rules worked. The rare gain comes
from the learned patterns of Steering 9 item 4, and a live drop shows that part of it is not
real.

The drop (run `20261006T161833Z-05e5e46f`, request 4): rare War Boots with 20% run/walk,
5 dexterity, 8% fire resistance, 51% defence. The HUD said "CHECK — listed stat combination;
reference asks 10.3705 Ist · 15 sellers". The cached listings say otherwise: among rare boots
with 20% run/walk and a fire resistance, the priced copies carry fire 21–39% and nearly all
a second resistance of 26–40%; one listing has fire at 15% or under and it has no price. The
verdict is VENDOR. Current tables return VENDOR for this exact item, but only by one point:
the rule {fire ≥ 9, dexterity ≥ 2, run/walk ≥ 10} with a 21 Ist reference is still in the
table, and so are {dexterity ≥ 2, property 430 ≥ 1, run/walk ≥ 20} at 34 Ist and
{defence ≥ 12%, property 430 ≥ 10, run/walk ≥ 20} at 29 Ist.

1. **A learned pattern must contain what is paid for.** `derive` accepts a signature when it
   is the intersection of the paid sellers' properties. When sellers are paid for different
   resistances, the intersection is the filler they happen to share (run/walk plus
   dexterity, defence or stamina) and the minima are the lowest filler rolls. A weak drop
   then dominates three "supporters". Fix the derivation, not the single rule: a pattern is
   kept only if listings that match the signature and have nothing else of value are
   themselves at or above the keep price with three sellers; otherwise the pattern needs
   the extra properties. Listings cannot be split that way for a signature → no pattern.
   Failing test: `tests/pricing/triage/test_learned_patterns.py::test_a_stat_pair_shared_by_sellers_priced_for_other_stats_is_not_a_pattern`.
   Add the boots to `guides/pricing.html` §9 as a false-positive row with the fire 8 and
   fire 9 variants, so the guide score and `guide_negatives` carry them.
2. **Recount the rare and magic gain after the fix.** Report attention before and after, and
   the number of learned rules dropped. Attention that falls for this reason is explained in
   section 8, not reverted. The 8% corpus guard did not catch this drop class: also report
   the corpus CHECK share for rare and magic from the same run.
3. **Affix tiers must span the affix group.** The same HUD card showed
   "+20% (20-20%) Faster Run/Walk [T1; T1: 20-20%]". Pacing 10, Haste 20 and Speed 30 are one
   magicsuffix group (35) and all three spawn on rare boots; the pool is built per property
   code (`move2`), so every such affix is its own top tier. Build the tier pool per affix
   group and base. Failing test:
   `tests/inventory_tracking/items/test_affix_ranges.py::test_rare_boot_run_walk_tiers_span_the_whole_affix_group`.
   Check the other families whose tiers use separate property codes in the same pass.
4. **A vendor reason must say why.** The current reason for these boots is "no listings",
   while 75 rare boot listings with 20% run/walk are cached. Say "below every listed copy:
   fire 8, listed 21–39 with a second resistance" or the nearest true statement.

Order: 1 → 2, then the Steering 9 queue from where it stands; 3 and 4 alongside (they do not
touch the score).

### Steering 9 (progress check, 2026-10-06 16:30; user: "achieve our goals faster") — queue stands after Steering 10 items 1–2

Measured from the score files of 16:25: attention 75.1% (75.0% at Steering 8), base recall
63.2% (62.3%), cheap SELL 10.37% (unchanged), guide tables 305 of 404 (unchanged), 99 rows
untranscribed (unchanged). Fifty minutes produced 37 seller votes and a relabelled miss
table. The base exit was then declared out of reach from an audit that counts only 256
votes as recoverable. That audit is not accepted: it sets aside 406 votes whose reason is
"no priced band" although a fallback key for the item exists in the band table.

Arithmetic for the 85% target: 2,172 more votes are needed. Bases can give about 650, named
items about 600, SELF-USE 441. That is under 2,172, so the parked rare and magic patterns
(1,935 votes) are required and Steering 7 item 3 is lifted, as one pass (item 4 below).

Rules of pace, in force from now:

- A pass ends with a changed verdict count in a score file. A pass that only renames miss
  causes, audits a ceiling or rewrites section 8 is not a pass. No new miss-cause names
  unless the fix ships in the same pass.
- Work the largest remaining vote count first; do not finish a family to 100%.
- One score run per lever, not per rule. Report votes gained per pass in one line.
- The guide transcription does not touch the engine: run it in parallel with the engine
  work (a second agent or session), not third in the queue.
- A measure is reported as unreachable only after the largest miss cause in it has been
  replayed and its number printed. Until then it is unmet.

Queue, by votes per unit of work:

1. **SELF-USE must not hide a sale price (441 votes, about 2 points, one rule).** The replay
   misses 308 unique, 62 set, 55 base and 14 runeword votes as `own_use_only`: for example
   the 20 FCR gloves listed at 57 Ist get SELF and no price. An item with a supported band
   at or above the keep price is SELL or slow with its price and the own-use note beside it.
   SELF alone is for items under the keep price.
2. **Bases to 70% (300 votes).** Replay the 406 "no priced band" votes against the band
   table and print sellers per ladder level; fix the largest cause. If the cause is that
   every level keeps `base_modifiers` exact, add one floor level: same ethereal status and
   sockets, modifiers that can only add value dropped (superior durability, attack rating,
   defence, native shield rolls), priced as the plain base and labelled "at least". Then
   the rarity (131) and ED (109) variants. Staffmod class bases (253) stay CHECK.
3. **Named roll placement (about 600 votes) with the cheap SELL fix.** 319 unique votes are
   capped at CHECK by the top-roll rule, including a roll of 289 against a listed 290. Apply
   section 3.10: place the roll among the listed rolls and price it there; the cap applies
   only when the roll is below the lowest quartile of listed copies. The 15 cheap unique
   votes flagged SELL are placed by the same code. Exit: cheap SELL at or under 10%.
4. **Rare, magic and crafted patterns in one data-driven pass (1,935 votes).** No hand-written
   pattern batches. Per family, derive patterns from the listings themselves: affix
   combinations with at least three sellers at or above the keep price become CHECK
   patterns with the listed band as reference. Largest families first: rare belts 103,
   gloves 97, swords 70, Barbarian helms 68; magic body armour 70, orbs 56. Guard against
   CHECK inflation on real drops, since the listing replay has almost no cheap rare or magic
   rows: the corpus CHECK share stays at or under 8% for rare and for magic (now 3.4% and
   2.2%, `check_share_by_rarity` in `score-triage.json`). A pattern that breaks the guard is
   dropped, not tuned.
5. **Transcribe the 99 guide rows, in parallel from now** (Steering 8 item 3 unchanged).

Order: 1 → 2 → 3 → 4, with 5 alongside. Expected after 1–3: about 82%; item 4 closes the rest.
Steering 8 item 4 stands: test counts name their directories.

### Steering 8 (progress check, 2026-10-06 15:40) — queue replaced by Steering 9; item 4 stands

Measured from the score files of 2026-10-06 15:36: seller-weighted attention 75.0% (70.5% at
Steering 7), base recall 62.3% (40.1%), guide rows classified 408 verdict / 49 own-use /
39 pickup / 70 context, table score 305 of 404 (75.5%), corpus CHECK share 12.3%. The base
work moved the main measure by 4.5 points in ninety minutes; the direction is right and the
queue stays. Four corrections:

1. **Bases: finish to 70%, then stop.** The exit needs 335 more seller votes. Take them from
   `base_bucket_missing` (564 votes: Sacred Rondache 76, Archon Staff 59, Cuirass 41, Grand
   Scepter 35, Ancient Axe 34), `base_rarity_missing` (131) and `base_enhancement_missing`
   (126). Do not chase `base_variant_price_missing` (455): those are staffmod class bases
   (Cinquedeas, Greater Talons, Grimoire, Bone Wand) where fewer than three sellers list a
   comparable roll, so they stay CHECK. Do not chase `below_keep_price` (286) either. The
   replay credits CHECK as attention only for rare, magic and crafted items; the 576 valuable
   base votes that end as CHECK are not counted and that rule is not changed to reach the exit.
2. **Bases cannot reach 85% alone; name the next lever now.** The target needs 2,208 more
   votes and all chaseable base misses together are about 820. After the base exit the queue
   is named items, not affixed patterns: uniques `roll_comparison` (333) and
   `no_matched_price` (166), then sets and runewords (129). The 15 cheap unique votes flagged
   SELL (15 of 57 cheap unique listings) are the same roll-placement problem seen from the
   other side: work both in one pass. That pass is also what returns the cheap SELL rate
   (10.37%, 17 of 164, limit 10%) under its limit; no per-item VENDOR exception. If named
   items do not reach 85%, the remaining gap is the 1,799 rare and magic `no_paid_pattern`
   votes and item 3 of Steering 7 is reopened then, with that number as the reason.
3. **The guide score is still "zero failures" because 99 rows are not cases.** 49 own-use
   rows are classified and none executes; 50 verdict rows wait for an item and an expected
   outcome. The 95% target cannot be met at 305 of 404. Transcribe all 99 in one pass after
   the base exit: own-use rows as SELF-USE cases against `own.json` (warlock §0–§3, pricing
   §6), verdict rows from the guide text (primer `#miss` 14, warlock §4 8, pricing §3 6).
   Rows that then fail are listed under `failures` and fixed from that list. The three rows
   with a real reason (unnamed staffmods, of Thawing, mixed aggregates) move to context.
4. **Status lines must come from a run, and name its scope.** Section 8 reports "469 passed,
   Ruff clean". A run of `tests/pricing/triage` and `tests/inventory_tracking` at 15:35 gave
   2742 passed and 5 failed, and Ruff reported 17 errors, all in `inventory_tracking/hud/widgets.py`
   (invalid suppression codes). Three failures are the terror danger work in progress and one
   is the HUD map slot (0.15 against 0.03): not this plan's. One is this plan's:
   `tests/inventory_tracking/shop/test_catalog.py::test_all_reviewed_magic_profiles_keep_their_item_predicates`
   fails after the rule rebuild (a profile threshold of 20 where the shop profile says 42).
   Fix it before the next score run and report test counts with the directories they cover.

Order: 1 → 2 → 3; Steering 7 item 5 (two worked cases) inside pass 3; demand at the weekly pull.

### Steering 7 (progress check, 2026-10-06 14:00) — queue refined by Steering 8; Steering 6 evidence rules stand

Measured from the score files of 2026-10-06: seller-weighted attention 70.5% (target 85%;
72.6% at Steering 4), SELL/slow 62.8%; guide tables 260 of 493 rows executed; corpus 1453
drops: 1144 VENDOR / 166 slow / 100 CHECK / 20 SELL / 23 SELF-USE; 674 tests pass. Two days
of charm, jewel, jewelry and equipment patterns moved attention by under one point and the
table score by a few rows per batch. That is the micro-batch pace Steering 3 item 3 stopped.

1. **Bases are the queue.** 2,599 of the 6,481 missed valuable seller votes are bases (recall
   40.1%); rares 1,228, uniques 1,213 (714 of them asks above a cheap cohort, which are not
   chased), magic 590. Recovering bases alone lifts attention to about 82%. About 59 of the
   unresolved guide rows are base rows too (primer §2, §2-why, §2.1–2.4, pricing §2 gray).
   Work the two causes in the miss table in order: `base_bucket_missing` (1,158 votes) and
   `base_variant_price_missing` (872). Use the named-item ladder of Steering 3 item 1 for
   bases: exact bucket → drop superior ED → drop the socket facet, ethereal always kept; the
   first level with at least three sellers decides. A guide-listed runeword base with no
   level of three sellers is CHECK with the missing facet named, not VENDOR.
   Exit: base recall at least 70% seller-weighted, cheap rates inside their limits, the base
   guide rows executed.
2. **Give the guide score an honest denominator, in one pass.** All 235 unresolved rows lack
   an item and an expected verdict, and 231 carry no reason. Many are not sell-verdict rows:
   Warlock gear, boots, crafts and filter rows (about 75), pickup rules (pindle §3, 23),
   primer context tables (`#s2-why`, `#twin`, `#d0`–`#d6`). Classify every row once:
   *verdict* (executable sell case), *own-use* (executes as a SELF-USE case against
   `own.json`), *pickup* (decided before identification; outside the triage score, counted
   on its own line) or *context*, each with a one-line reason. No row stays unresolved
   without a reason. The 95% target applies to verdict plus own-use rows; the report prints
   the four counts instead of "260/493".
   A row becomes a case when it is transcribed, whether or not triage passes it: "zero
   executable failures" in every report means failing rows are being left unresolved.
   Failing rows are listed as failures and fixed from there.
3. **Affixed and charm patterns are parked again** (Steering 4 item 2). A new pattern is
   added only to make a guide row from item 2 execute, or to fix a drop in the corpus. The
   1,816 `no_paid_pattern` votes on rares and magic items stay as measured.
4. **The demand measure is not measured; say so.** `sell_supported_share` is 1.0, but 181 of
   182 SELL cohorts are supported only by censored page-0 absence, and one cohort (Jah) has
   strong turnover. Report the demand row as "unmeasured: one-day interval", not as passed.
   No more work on turnover until the weekly pull already authorized by Steering 6 (due
   2026-10-10 or -11) gives a seven-day interval.
5. **Close the two incomplete worked cases**: fix them, or move each to context with its
   reason. 36/38 has been carried since 2026-10-04 against a 100% target.
6. **Materials** continues under MATERIALS.md's own done criteria; its UI work comes after
   item 1. The live speed line is still unrecorded: take it from the next service log that
   has an identify pass, without asking for one.
7. **Section 8 is a status again, not a changelog.** Keep current numbers, live facts and the
   next three steps; delete bullets for finished batches (facets, socketed magic armour,
   jewels, set labels). History is in git.

Order: 2 → 1 → 5; item 4 at the next pull.

### Steering 6 (user directive, 2026-10-04 14:00) — evidence rules stand; queue set by Steering 7

**The user does not label or assess items. Progress comes solely from the guides and from
Traderie.** Do not ask for labels, skims, reviews of lists or verdict confirmations, and do not
report work as blocked on them. `label.html`, `labels.json` and the label score are retired as
measures; the Alt+Shift+D flag built just before this directive stays as an optional tool that
is never requested; the one existing label stays as a regression case only.

Ground truth is now two sources, both already in the repo's rules of evidence:

1. **Guides are the answer key for patterns and demand.** `guides/pricing.html` §2, §3, §6,
   §7, §8, §9, `guides/pricing-primer.html` (§2–§6, the `#miss` checklist, the decision table
   §8), `guides/warlock.html` and `guides/pindle-anya.html` §3/§5. Every worked example, every
   keep/sell/vendor row and every listed false positive becomes an acceptance case: item
   description → expected verdict class. These are built once, mechanically, into a guide case
   file and scored by the same scorer that scored labels. Where a guide states a verdict and
   triage disagrees, triage is wrong unless Traderie evidence dated later than the guide row
   contradicts it; then the guide is corrected with a dated pass (AGENTS.md rule 6).
2. **Traderie is the answer key for price and demand.**
   - price: the listing replay, one vote per seller (as now);
   - demand: **turnover**. A second page-0 pull through `pricing/tools/market_pull.py` (paced,
     scope filters) is authorized by this directive and runs now; then weekly. Per cohort:
     share of 2026-10-03 listing ids gone, new sellers, and whether the gone listings were the
     cheap ones. A cohort with many sellers and no turnover is supply, not demand;
   - buy-side listings: one test request through `pricing/tools/traderie.py` to learn whether
     the API returns them; if it does, buyers per cohort join the demand evidence.
   Maxroll build data in the repo stays the demand source for *which* items builds use; it is
   never a price.

Decision rules that no longer wait for the user:

- **Decision 5 (cheap asks without demand evidence)** is decided by data: after Steering 5
  item 1 (wider demand table) and the turnover measurement, a cohort under 1 Ist with no build
  use, no turnover and no buyers is VENDOR with the ask as a note; with any one of them it is
  slow; SELL needs the keep price plus demand evidence.
- **Explained VENDOR corrections** stand without a skim.
- **Disagreements between guide and Traderie** are listed in section 8 with both dates; the
  later evidence wins and the guide is edited.

Measures (replace the label row of section 5):

| Report | Source | Target |
|---|---|---|
| Guide cases | acceptance cases extracted from the guides | 100% of worked examples and false-positive rows; ≥ 95% of keep/sell/vendor table rows |
| Listing replay | Traderie asks, one vote per seller | as section 5 and Steering 3 item 4 |
| Demand agreement | turnover between pulls | ≥ 80% of SELL cohorts show turnover or buyers; ≤ 10% of VENDOR-by-rule cohorts show strong turnover |
| Speed | service log, from whatever identify passes occur in normal play | as section 5 |

The live ten-item check is no longer a request: record it from the next service log that
contains an identify pass.

Order: guide case file and its score → second pull and turnover → Steering 5 item 1 →
decision 5 rule → fix what the guide cases and turnover expose. Steering 5 item 4 changes
accordingly: work is driven by guide-case failures and Traderie evidence.

### Steering 5 (progress check, 2026-10-04 13:30) — items 1, 3, 5 stand; user-action paragraph void

Done since Steering 4: Rusthandle +2 is CHECK with the "mostly +3" line; socket contents no
longer form price bands (Harlequin Crest 0.65 Ist); demand table of 130 named items from
resolved endgame variants; green SELL 66 → 34. Corpus 777: 540 VENDOR / 135 slow / 63 CHECK /
34 SELL / 5 SELF-USE. Host run 20261004T090422Z had HUD, Alt+D and a shop scan but no identify
events, so the ten-item check is still open. Labels: 1.

1. **The demand table is too narrow to carry a VENDOR decision.** 117 of the 135 slow drops
   are under 1 Ist without demand evidence, and that group contains Rainbow Facet, Atma's
   Scarab, Jade Talon, Leviathan and Arkaine's Valor. Rainbow Facet is "High, 7 builds" in the
   repo's own `appraisal-value-watch.json` (277 items); it is missing because facets and jewels
   are socket inserts, not gear slots. Extend demand evidence to the union of:
   resolved endgame gear variants (as now); value-watch entries whose priority is a valuable
   candidate or whose local tier is above Floor; socket inserts and mercenary gear named in
   those variants. Print the list of sub-1-Ist cohorts with at least 10 sellers and no demand
   evidence — that list, not a rule, is what the user decides on (decision 5).
2. **Decision 5 recommendation withdrawn for now.** Until item 1 is done and a turnover
   measurement exists, "no demand evidence" keeps the verdict at slow; it does not produce
   VENDOR.
3. **Slow must not drown SELL on the HUD.** 135 slow against 34 SELL. The identify summary
   lists SELL, SELF-USE and CHECK lines; slow items are one count line ("7 slow, cheapest
   asks 0.3–0.8 Ist") expandable in Alt+D. If the summary already does this, record it in
   section 8 and skip.
4. **The offline phase is closed.** Named, commodity and routing work are at the point where
   more offline effort does not change what the user sees. Open work is only:
   item 1 above; the ten-item identify check; fixes for labels, disagreements and live
   findings as they arrive. No new rule families, audits or refactors without one of those.
5. **Own-use check:** Gheed's Fortune matches an own-use row yet shows slow. Confirm whether
   the row's conditions exclude it or the verdict order is wrong (SELF-USE precedes slow).

User actions that now gate progress: identify ten items in one pass with the service
restarted; answer decision 6 (second pull, disagree hotkey); label or skim
`inventory_tracking/corpus/data/label.html` and `vendor-corrections.md`.

### Steering 4 (progress check, 2026-10-04 10:30) — done; item 3 continued by Steering 5

Done since Steering 3: named CHECK 53% → 12.9% (uniques 8.9%, sets 19.2%); seller-weighted
scores (attention 72.6%, SELL/slow 65.7%); `own.json` has 75 rows and SELF-USE appears;
section 8 is short. Corpus 768: 529 VENDOR / 107 slow / 66 SELL / 61 CHECK / 5 SELF-USE.
Named misses are small now (uniques 226 seller votes, sets 11, runewords 35). The work reports
itself blocked on two policy questions; both are answered here.

1. **Rusthandle: the acceptance case wins.** It is SELL again at the name band because the
   roll model lost the held-out price comparison and fell back. Two different things were
   tied together. The *selection signal* (at least 15 sellers, at least 75% of listed copies
   at the top roll) says which stat buyers select on; it does not need a price model. When it
   holds and the drop is below that roll, the verdict is capped at CHECK and the line says
   "listed copies are mostly +3 Vengeance; this has +2" — whatever the price validation says.
   The held-out comparison only chooses which *number* is printed (roll-aware or name band).
2. **Batch floor.** The 300-listing floor was meant to stop ceremony, not to block work. It
   does not apply to a fix for a corpus drop, a user label or a live-run finding. Listing-led
   affixed rule batches are **parked**: 72.6% seller-weighted is accepted for now, and the
   remaining rare/magic/base misses are worked only from drops the user actually sees.
3. **SELL must mean demand; today it means supply.** Green SELL in the corpus includes
   Hellmouth, Stealskull, Goldwrap, Pierre Tombale Couant, Fleshrender and Wall of the Eyeless
   at 0.26–0.36 Ist; 139 of the 173 SELL/slow drops are priced under 1 Ist and 101 sit at
   0.5–1 Ist, the one-mid-rune minimum ask. "At least 10 recent sellers" measures how many
   people are trying to get rid of an item. This is the first goal of section 1 and it is not
   met. Add demand evidence, cheapest first:
   - endgame build use already in the repo (`wp-a-builds.json`, `wp-a-variants/`, the value
     watch) — levelling and budget mentions do not count;
   - turnover: a second page-0 pull at least a day after 2026-10-03, then per cohort the share
     of listing ids that disappeared and the number of new sellers (needs the user's go-ahead);
   - buy-side listings, if the Traderie API returns them (one test request through
     `pricing/tools/traderie.py`; unverified);
   - diablo2.io fills where present.
   Until a decision on the rule (section 7, decision 5), a cohort whose Q1 is under 1 Ist and
   that has no demand evidence is shown as **slow**, not SELL.
4. **Socket contents are part of the price, not of the item.** Harlequin Crest drops with a
   filled socket are priced 7.7 Ist from three listings whose socket holds a high rune. A
   named item with a filled socket is priced as the unsocketed item, with the content named
   beside it; the "filled" cohort is not a band.
5. **Collect labels where the user already is.** One label in a day: the HTML page is not
   being used. Proposal (section 7, decision 6): a "disagree" hotkey that marks the last HUD
   verdict as wrong and stores the capture id; the next session's work list is exactly those.
6. **Live check still pending**: restart `make serve`, wait for the warm-up, identify ten items
   in one pass, record time and HUD lines.

Order: 1 → 4 → 3 (repo build evidence first) → 6. Nothing else until labels, disagreements or
live findings arrive.

### Steering 3 (progress check, 2026-10-04 02:00) — items 1, 2, 4, 5, 6, 7 done; item 3 refined by Steering 4 item 2

Done since Steering 2: every observed type routes to triage (185 routes); explained VENDOR
corrections and the liquidity audit are written; live identify passes of six and four items
took 91 ms and 308 ms with triage lookups of 2–9 ms (speed target met when warm; cold start
after a restart is still about 18 s of background warm-up). Listing attention 52.2% → 57.9%.
Corpus (768 items): 446 VENDOR / 203 CHECK / 95 slow / 24 SELL. Labels: 1. `own.json`: empty.

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

User clarification (2026-10-04): the remaining guide-backed gaps may be fixed in one combined
coverage pass even when each recovers fewer than 300 listings. This replaces item 3's numerical
batch floor for that pass; retain guide/market evidence, scoped comparisons and both score reports.

Historical execution note: Steering 3 items 4–6 are implemented. Steering 4 now controls
the queue; the authorized combined guide-gap pass is complete. Do not resume listing-led
affixed batches. Preserve Rusthandle CHECK, normalize socket-content prices, qualify SELL
with endgame demand, then verify the live ten-item identify run.

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

### Historical execution sequence (reviewed 2026-10-03; order superseded)

Steering 5 controls the remaining work: demand union/review list, slow HUD summary, own-use precedence, then live findings and labels.
The P0–P5 sequence below is implementation reference, not the current work queue.
Work on the triage path, not incremental improvements to
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
- Rewrite section 8 in at most 30 lines: current numbers, live facts, next three steps. No per-batch status paragraphs, replay logs or evidence files; do not append to handoff.md or STATUS.md.
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
3. **Self-use scope — resolved by Steering 3.** Echoing Strike Warlock and its mercenary; no further confirmation needed.
4. **Housekeeping.** Delete `tmp/` and move the frozen artifacts out?
5. **Cheap asks without demand evidence.** An item listed at 0.25–1 Ist by many sellers with no
   endgame build use, turnover, buy request or fill: show as slow (current default), or VENDOR
   with the ask as a note? Recommendation withdrawn (Steering 5): keep slow until demand
   coverage is extended and turnover is measured; then decide from the printed list.
6. **Resolved by Steering 6:** second pull authorized; hotkey and labels retired. Original text:
   **Second market pull and a "disagree" hotkey.** Authorize a second page-0 pull (about 75
   minutes, paced) to measure turnover? Add a hotkey that marks the last verdict as wrong?

## 8. Status
2026-10-06 — Current contract and Steering 11 govern; completion unproven.
- Steering 10 paid-combination fix: 119 learned rules retained, 2616 dropped.
  Every supporter retains its complete potentially valuable numeric-affix signature;
  unrelated valuable extras cannot establish a price for common filler stats.
- Same listing replay: attention 80.25% → 78.29% (17241/22022), net -432 votes.
  Rare attention 59.50% → 45.13% (1005/2227); magic 56.90% → 55.89% (721/1290).
  The loss corrects unsupported learned combinations and is retained, not tuned away.
- Base recall remains 67.38% (2946/4372; target 70%). Its 308 clean misses have
  one usable seller (131), two (171), none (5), or a supported below-keep floor (1).
  Normal bases cannot borrow superior premiums; staffmod combinations stay distinct.
- Cheap SELL/slow remains 10.37% (17/164; limit 10%, FAIL); CHECK 17.68%.
  Alternative supported roll boundaries did not validate another cheap-item split.
- Guide rows 373/404 (92.33%): verdict 338/355, own-use 35/49; all execute.
  Worked 36/36; false positives 16/16, including rare War Boots at fire 8 and 9.
  One table-row pass was lost with removal of unsupported combinations; remains open.
- Same-run corpus CHECK: rare 3.28% (9/274), magic 2.17% (13/598); limits 8%.
  Named CHECK 12.11%; three-seller support remains mandatory.
- Earlier retained corrections: normal/superior AR/durability lost eight votes;
  Horazon lost three; smaller validated roll cohorts lost fifteen on below-keep asks.
- Tests: triage/appraisal 857 passed; item/definition suite 426 passed plus three
  generation failures fixed and rerun green. Publication/tier tests 21 passed; lint clean.
- Bands 64,902; 105 roll models. Warm median 0.462 ms; first call 166.545 ms.
  Live 4-item pass 208 ms (Oct 6 15:33 UTC); ten-item timing remains unrecorded.
- Demand unmeasured; authorized weekly pull October 10–11 (current interval one day).
- Steering 10 tiers fixed: native group/base pools for FRW, IAS, FHR and FCR;
  saved boots T2 / 10–30%; published generation f7fde48dff09.
- Vendor reasons now explain the nearest reviewed combination; 1497 saved verdicts
  unchanged, warm median 0.129 ms / max 2.155 ms. Python worker restart loads this code.
- Next: resume Steering 9 coverage, guide failures and Materials UI verification.
Every Current contract measure must pass together before completion.
