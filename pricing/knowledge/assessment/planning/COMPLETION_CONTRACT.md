# All-item assessment: end goal and completion contract

## Current contract (2026-10-06) — read this section first; it overrides everything below

The user named this document the main driving document again on 2026-10-06. It states the end
goal, the measures that prove it and the stopping rule. [PLAN.md](PLAN.md) holds the design,
the steering history and the status (its section 8); the work queue is its newest Steering
block. The older contract text was frozen by the user on 2026-10-03 and stays frozen:
the scope manifest, coverage matrix, item bank, receipts, per-item formal reviews and the
"Mandatory final gates" table are technical reference and are not resumed or regenerated.
That text and the review machinery are archived in `pricing/archive/2026-10-19/` (2026-10-19).

### End goal

On a drop, say quickly whether it is worth keeping to sell, for every item type, in
Softcore / Non-Ladder / PC / Reign of the Warlock, Ist = 1. In priority order: liquid items
first; a fast answer; every type answered (uniques, sets, rares, magic, crafted, charms,
jewels, bases, runewords, runes, materials); uniques and sets separated by rolls and
ethereal status; demand taken from the guides and from market data. The player is not
levelling characters. Keep price: 0.25 Ist, inclusive.

### Evidence rules

- The user does not label, skim or confirm items. Never ask, and never report work as
  blocked on it.
- The guides are the answer key for patterns and demand; scoped Traderie asks are the answer
  key for price, one vote per seller. Asks are not sales; demand never creates a price.
- When a guide and later Traderie evidence disagree, the later evidence wins and the guide
  is corrected with a dated pass.
- Live pulls only through `pricing/tools/`, paced, with the scope filters. The weekly page-0
  pull is authorized; the next is due 2026-10-10 or -11.

### Measures (score files in `inventory_tracking/corpus/data/`, values of 2026-10-07)

| Measure | Target | Now |
|---|---|---|
| Guide worked examples and false-positive rows | 100% pass | 36/37 and 18/19; residual demand-unmeasured cases retained (PLAN §8) |
| Guide table rows that are verdict or own-use rows | every row classified with a reason; at least 95% pass | all classified and executing; 402 of 404 pass (99.50%); expectations unchanged |
| Listing replay, valuable seller votes flagged | at least 85% | 86.92% including demand-unmeasured slow; 69.91% excluding its 3746 votes; priced SELL/slow 74.03%; 22033 votes unchanged (PLAN §8) |
| Cheap listings flagged SELL or slow / CHECK; a cheap listing in a cohort where at least 90% of sellers ask the keep price is not a false flag | at most 10% / 25% | 11.59% (19/164) / 17.68% (29/164); unmeasured slow restores cheap flags |
| Named corpus drops that end as CHECK | at most 15% | 11.85% |
| SELL cohorts with turnover or buyers | at least 80%, over an interval of seven days or more | seven-day measure unverified; current one-day support 1/138, censored absence excluded |
| Speed | under 50 ms per item; a ten-item identify pass under 1 s | latest live one-item pass 69.0 ms; prior three-item pass 57.5 ms; required ten-item pass unverified |

A measure counts as met only from a score file produced by the current code and tables. A
number that goes down is reverted or explained in PLAN.md section 8.

### Queue

PLAN.md "Steering 15" (2026-10-07 09:45) first, then "Steering 14" with its amendments, with
the Steering 9 rules of pace:

1. Repair the demand rule: a guide row, build list or primer base entry is demand; a cohort
   with no seven-day turnover measurement is "demand unmeasured" (slow, no highlight), not
   VENDOR. Guide rows return to 402/404 or better and worked/false-positive rows to 100%
   without editing guide expectations to fit the rule.
2. Named roll placement continues from the authored file, own drops first; the Shaftstop
   captures stay VENDOR. Censored churn stays excluded from demand support.
3. Speed: record a ten-item pass by replaying captured identify items through the live
   service path; bring the one-item pass from 69.0 ms under 50 ms.
4. Rare and magic: authored patterns only, largest missed families first. The paid-property
   scorer is removed and is not rebuilt.
5. Base variants priced from existing listings.
6. Evidence-backed CHECK counts as attention for all item types (user, 2026-10-06);
   priced SELL/slow is reported separately. Whether cohorts with no demand after the
   seven-day pull of 2026-10-10 or -11 leave the "valuable" count is the user's decision.

### Stopping rule

The work is finished only when every measure above meets its target in the same score run.
A batch, a family, a passing test suite, a status update or a context compaction is not a
reason to stop, and no "continue" is requested from the user. If one item is blocked,
continue with the next; a measure that cannot be reached is reported with its number and
the evidence, never declared met. Do not add gates, manifests or per-batch artifacts to
prove progress: the score files are the proof.
