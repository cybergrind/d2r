---
name: d2-loop-finds
description: The most valuable finds of the KP_6 loop over its last games, from serve's logs, priced offline - "most expensive findings", "best finds", "what did we find", "top loot in the last N games", "anything good dropped". Default the last 200 games and the top 5; the query may set other numbers ("last 500 games", "top 10", "today until 14:00"). Reports each find with its game, time, stats, ask band and the appraisal's verdict, the appraised items the knowledge base could not price, and what was left on the ground. Not for one item's screenshot (appraise) or the loop's speed (d2-loop-watch).
---

# The loop's best finds

The player, 2026-10-17: "check logs and bring 5 most expensive findings in the last 200 games"; "by default 200
games 5 positions, user can override in query".

## Run

```
python3 .agents/skills/d2-loop-finds/tools/finds.py [--games 200] [--top 5] [--until 'YYYY-MM-DD HH:MM'] [--json]
```

Take the numbers from the query: "last 500 games" → `--games 500`, "top 10" / "10 most expensive" → `--top 10`,
"up to 14:00" → `--until`. Otherwise the defaults. It takes about 15 s and only reads (logs, the offline knowledge base);
it is safe while the loop plays. The window is the last N games found in the last 7 days of logs (`LOOKBACK_DAYS`).

**One run, then the report.** The text output has everything the report needs: dated finds, the unpriced items, the
rest (materials by name, appraised items by verdict), and each missed item with what explains it (`outside a loop game`
= a restart or the player's own play, not a loop miss; `LOOP DEFECT, the loop stopped: …` = the stop that named it).
Do not run it again with `--json` or a large `--top`, and do not grep the logs to explain the ground (the player,
2026-10-24: "why we're struggling with providing reports fast?"). Open a log only for a miss the output leaves
unexplained and that the report would call a defect, and then only the lines around its time.

What it reads, in `inventory_tracking/runs/alt-d/*/probe.log` (the docstring has the details):

- **appraised items**: every item Cain identified, from `Identify assessment:`, with the triage's verdict, band and stats;
- **materials**: runes, gems, shards, essences, keys and tokens picked up, priced by `pricing.knowledge lookup`;
- **the ground**: `games.py` (the d2-loop-watch skill's reader) for what the sure mode missed and the sets and uniques
  left by design.

The rank is the value a trade can count on: an appraised item's `decision_ist` (its band's lower quartile of asks), a
material's ladder Ist value, or its median ask when the ladder has none.

## Report

A table of the top N: rank, the find and its stats, time and game (its place in the window, 1 the oldest: the
loop's own count starts anew at each restart), value, the evidence (asks q1 / median, sellers, date), and what the
loop did with it (verdict `vendor` = sold to a vendor; `sell`, `slow`, `check`, `keep` = stashed). Then, in a few
lines:

- **unpriced, worth a look**: appraised items not judged `vendor` that have no supported price. The tool can't rank
  them, and one may be worth more than the whole top N. Say what each is and suggest an appraisal from a screenshot
  (the appraise skill). Give a knowledge-base bucket only when one plainly fits (for example `wp-h-jewels-charms.json`
  for jewels), and call it asks, not a price;
- **the rest**: summarise the small finds (low runes, gems, shards) in one line;
- **the ground**: missed items (a valuable left behind is a loop defect: say so; a Worldstone Shard is always picked
  since 2026-10-22, so a missed one is a defect too) and the count of sets and uniques left by design.

Rules (AGENTS.md): the repo is the price source, never a web search; date every number and say "asks"; an item's
"verdict" is the triage's, not a price. The appraisal of a magic or rare item reads only what the log printed (stats);
when a stat looks impossible for the item, say the log may have misread it instead of guessing.
