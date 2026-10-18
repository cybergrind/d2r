---
name: d2-loop-watch
description: Continuous monitoring, run analysis and speed optimisation of the KP_6 Lower Kurast loop while it plays - "start monitoring", "watch the runs", "continue the improvement loop", "analyze runs", "optimize speed", "make it faster", "resume watching", "the loop is running, keep it going", "we stuck" during a watched loop. Arms a live watch on serve's log (one line per game, stalls, stops), fixes and restarts the service autonomously, analyses the runs every hour for where the time goes, tries one speed change at a time and keeps it only if the measures say so, and keeps the rounds' state in the loop's journal. Use the d2-rca skill instead for a deep analysis of one incident the player reports.
---

# The KP_6 loop: watch, fix, analyse, speed up

The player's goal is wealth for a Jah (Enigma), from the KP_6 Lower Kurast chest loop running unattended. The agent
watches whole runs, fixes what stops the loop, restarts `make serve` by itself, analyses the runs continuously to find
where the time goes, and tries speed changes one at a time, each measured. The player, 2026-10-17: "we stuck! I didn't
stop loop myself and you have all the tools to fix things and continue"; "we need it to continously analyze runs, try
to find and optimize speed".

Two loops run together: **keep it running** (the watch, Each event, Fix) and **make it faster** (Speed, every hour).
A stop always comes first.

**The measure is chests an hour of cycles** (`speed.py` CYCLES; the player, 2026-10-17: a cycle runs from one Lower
Kurast arrival to the next, everything between counted: the town, the trade, repairs, the lobby, recoveries), not game
time. Loot comes from containers: a game that opens one more chest
is longer and still better. On 2026-10-17 games went 51 → 59 s after 04:34 at the same 280 chests an hour; the median
stay opened 4 chests instead of 3.

State between rounds and sessions: [the journal](../../../inventory_tracking/routes/lower-kurast-loop-journal.md)
(baseline, queue, rulings waiting, rounds). Design: `inventory_tracking/routes/lower-kurast-loop-plan.md`. The
player's rulings: AGENTS.md, the memory `d2r-kp6-loop-rulings`, and the journal.

## Hard rules

1. **Never leave a game while a valuable the loop would pick up lies on the ground.** No restart, recovery or watchdog
   may cost loot. `runner.valuable_left` guards the loop's own exits. A restart is safe only through
   `tools/restart.py`, which waits for the lobby (the player, 2026-10-17: "that is the exact thing we want ot avoid").
2. **Gold.** Repairs and purchases use only the gold carried in the inventory. Never use the stash's gold ("I don't
   want to touch this 9M of gold atm"). `repair.py` checks the quoted cost and the stash gold after. If
   `runs/alt-d/repair-touched-stash.txt` exists, repairs are off: tell the player.
3. **Selling.** Full rune and material stacks (99), and the loop's junk: its own items, identified and appraised
   `vendor` (magic, rare, set, unique or crafted: the player, 2026-10-18 11:10, "we should sell junk rings and other
   junk items; imporant!: do not sell own equipment or valuable items"). Never a potion, a rune, a gem, a set or
   unique charm (the Sunders, Gheed's, Annihilus, the Torch), anything appraised other than `vendor`, or anything of
   the player's.
3b. **The trade session** (the player, 2026-10-17; loop.py TRADE_ROOM): only when the free room (inventory + cube) runs
   low; it must leave the character for Lower Kurast with keepers and resources stashed, all junk sold (never the
   player's gear, runes, gems, unique charms), keys and scrolls refilled, the staff repaired if the
   carried gold covers it, **the cube empty and inventory cells free**. Its `trade session done:` line says each; a
   gap is a Fix. No Cain, stash or Jamella between sessions (but a bare keys/scrolls refill at 3).
4. **The player's pause wins.** A `PLAYER: loop off` line means the player turned the loop off with KP_6. Never turn
   it back on; ask, or wait for `PLAYER: loop on`. The same goes for "pause" or "stop" in chat: pause through
   `restart.py --loop off`, stop the watch, and do not restart the loop until the player says so.
5. **Never commit.** The player says "commit". No game memory writes. Battle.net, the player runs only `make serve`.
6. **Speed of a fix** (memory `d2r-live-fix-cadence`): run only the focused test files for the edit, restart at once,
   and run the wide suite in the background while the loop plays. A behaviour that can lose loot is never shipped
   without its guard.
7. Repo rules: `uv run --offline`, `rg --no-config`, tests serial at nice 19 (`tests/conftest.py` does it), `ruff` and
   `pyrefly` clean on the files you wrote, item codes from the d2data dump, never from memory.

## Tools (`.agents/skills/d2-loop-watch/tools/`: `python3`, but `speed.py` with `uv run --offline python`)

| Tool | What it does |
| --- | --- |
| `watch.py` | Follows the newest `runs/alt-d/*/probe.log` across restarts. Prints one line per game (seconds, chests, legs over 25 s, stash/shop notes), and a `MISSED:` line for each valuable of the game never picked up. At once: stops, recoveries ("the game is left"), guard stops ("stops here"), full stacks, sales, repairs, errors, tracebacks, `PLAYER: loop on/off`, and `STALL` after `--stall` s with no leg while on. A re-armed watch reads the current log quietly first, so it knows the game in progress. |
| `restart.py --loop on\|off\|keep` | Waits for a safe moment: at once if the loop is off, else the next `next game` leg (lobby). Then it writes `runs/alt-d/restart.request` and confirms the new service's `resumed after a restart` line. Exit 1: no safe moment, nothing written. Exit 2: no resume seen. |
| `games.py [--since 'YYYY-MM-DD HH:MM'] [--last N] [--sessions DIR...] [--json]` | The baseline of a stretch of play: games, games an hour, median and p90 game, median of each leg, the slowest games, every recovery, stop and error, what was done (stash, repair, sales), **MISSED**: every item the census saw that the sure mode takes and no pickup took (matched by the place aimed at, then by name; a game a restart cut is checked against the next session), and what is left by design. The census's "left" / "taken (material)" words are not the pickup's decision. |
| `speed.py [--since ..] [--until ..] [--against SINCE UNTIL]` (run with `uv run --offline python`: it reads the takes) | Where the time goes in a window (default the last 2 h). Town legs (median, p90). On the level: per stay the seconds, chests and other containers, casting / moving / standing, the macro's stalls ranked by the log lines said in them (seconds a stay, times seen), the legs that lost most against Blade Warp's pace (21 u/s). **Inactive time**: seconds with the character still, neither casting nor moving and no input sent, on the level (apart from Blade Warp's delay waited out) and in the towns' takes (Kurast Docks, Pandemonium Fortress; loading screens excluded), the town's idle stretches by their log lines; **going back**: units moved away from a leg's container, and the legs that went back most. `--no-towns` skips the town takes. `--against` compares with an earlier window: **YIELD** (chests an hour, 90% bootstrap interval of the difference) and every measure's median shift, each marked better / worse / no evidence. About 0.1 s a take. |
| `trade.py [--since ..] [--until ..]` | The trading (plan §15; the player: "measure our trading efficiency time/gold, what we pickup, what we sell it for"): items identified by base and verdict, junk sold and the gold each brought, the full stacks sold, the gold carried more after the visits, the seconds of the `identify` legs and of the visits that sold, gold an hour of play and a second of trade time, and the repairs against it. **By kind** (quality and item type): cells, pickup / identify / selling seconds an item, share sold, gold a sale, an item, a cell, a second, and the **payback**: the seconds its gold buys back as Teleport charges over the seconds it cost (under 1: leave that kind on the ground). `--saved` sets the seconds a charge saves a stay. |

Deeper tools: `python -m inventory_tracking.combat.legs <take>...` (each stay's container-to-container legs, stalls,
time lost; takes are in `runs/combat/<UTC>-79`), and `.agents/skills/d2-rca/tools/session.py` (`log`, `idle`,
`inputs`).

## Start or resume a watch

1. Read the journal: queue, rulings waiting, the last round.
2. Check the state: `python3 .agents/skills/d2-loop-watch/tools/games.py --last 15` and the tail of the newest
   `probe.log`. Is serve up? Is the loop on? Who turned it off?
3. Arm the watch with the Monitor tool, `timeout_ms: 1800000`, description "KP_6 loop: games, stops, stalls":
   `uv run --offline python -u .agents/skills/d2-loop-watch/tools/watch.py` (the takes, for RATE). A monitor lives at most 30 minutes. On its expiry notice,
   re-arm it the same way, without asking. One watch at a time: TaskStop the old one first.
4. If the loop is off and the player asked to start it: `python3 .agents/skills/d2-loop-watch/tools/restart.py
   --loop on` (it needs the character in a game or the lobby, and the game window as the player left it).
5. Tell the player in one or two lines what is being watched, and that "pause" stops it.
6. Note the watch's start time: the first Speed round is due an hour into play (the second expiry of the watch).

## Each event

| Event | Action |
| --- | --- |
| `game N: ...` | Nothing, unless it is over 2× the median, or a leg other than the chests is over 25 s: then read the log for that game and note it in the queue if it repeats. |
| `STALL` | Read the newest `probe.log` tail (the last 200 `Macro` lines) at once. A focus wait or a panel the player opened is no defect. Otherwise go to **Fix**. |
| `loop stopped` / `stops here` | If a valuable is on the ground ("stops here"), the loop waits for the player: tell them what and where, and do not restart. Otherwise go to **Fix**. |
| `the game is left` (a recovery) | Note the cause. A cause seen twice goes to **Fix**. |
| `MISSED: game N, <item> at (x, y) ...` | A valuable the sure mode takes was never picked up: hard rule 1. Trace it in the log at once (the sighting, every `pickup:` / `aims for` / `picked up` of it, where the run ended) and **Fix** the cause before speed work. `on the ground at a stop` is the same at a pause or stop: tell the player where it lies. |
| `Traceback` / `ERROR` / `Macro failed` | **Fix**. |
| `PLAYER: loop off` | Rule 4. Finish the round's notes; keep watching. |
| `repair:` / `shop: sold` / `identify:` | Check the gold numbers make sense (carried gold only) and that what was sold is a full stack's item or junk appraised `vendor` (rule 3). |
| `== following ...` | A new service: expect `resumed after a restart`. |

## Fix (rounds of the improvement loop)

1. **Evidence**: the log lines with their times, and the code branch that said them
   (`rg --no-config -n "<words>" inventory_tracking/macros`). Why is the code like that? Check plan.md and the
   comment and tests near it (d2-rca rule 3). Mark claims verified or inferred.
2. **Smallest fix that keeps the old fix**: edit, then add or adjust the focused test (`tests/inventory_tracking/
   macros/test_<module>.py`, the fakes in `fakes.py`).
3. **Focused tests only**: `uv run --offline pytest tests/inventory_tracking/macros/test_<module>.py -q -x`, plus
   `uv run --offline ruff check <files>` and `uv run --offline pyrefly check <files>`.
4. **Restart** only after the focused tests passed — never chain a restart after `pytest ... | tail` with `&&`: the
   pipe's status is `tail`'s, and a failing suite restarted the service at 13:17 on 2026-10-17. `python3
   .agents/skills/d2-loop-watch/tools/restart.py --loop on` (or `keep`). Keep the watch armed.
   It follows the new log by itself.
5. **Background**: the wide suite, `uv run --offline pytest tests/inventory_tracking/macros
   tests/inventory_tracking/combat tests/inventory_tracking/builds -q` with Bash `run_in_background`. A failure there
   is fixed in the next round.
6. **Verify on the next games**: say what line or number should change, and check it on the games that follow.
7. **Journal**: a line in this round's entry (time, cause, files, tests, restart time, what the next games showed).

A rule that needs the player's choice (a trade-off between speed and their wish, anything about selling or gold) is
not changed: put it under "Waiting for the player" in the journal and ask once, at the end of the round.

## Speed: analyse and optimise (every hour of play, at every second re-arm of the watch)

The loop is: **analyse → pick one candidate → change → measure → keep or revert → journal**. **Steer only after
analysis** (the player, 2026-10-17: "yes, measuring chests per hour every 5 cycles - looks good; we should apply
steering after analysis"): after a change, leave the loop alone for 30+ clean cycles (the watch's `RATE` lines), then
analyse (`speed.py` CYCLES and the cycle's legs, `trade.py`), then the next change. A fix for a stop or a lost valuable
is the exception. Only one speed change is
live at a time, so each measurement is about one change.

1. **Analyse.** `uv run --offline python .agents/skills/d2-loop-watch/tools/speed.py --since '<the last restart>'`,
   plus `--against` the journal's baseline window. If a speed change is live, check it first (step 5).
2. **Find candidates** in the output, the most seconds a game first:
   - stall reasons ranked by seconds a stay: each names the log lines said while standing. Trace each to its branch
     (`rg --no-config -n "<words>" inventory_tracking/macros`);
   - "standing" against "casting" and "moving" in a stay. Standing is time not spent going toward a chest;
   - the legs that lost most against the pace: a big `way` / `line` is a detour, big standing is waiting;
   - town legs over their floor (p90 far over the median, or a leg that grew since the baseline);
   - per-take detail: `uv run --offline python -m inventory_tracking.combat.legs <takes> --worst 12`; frames:
     `.agents/skills/d2-rca/tools/session.py idle <take>`.
   - For a deep question (over 50 takes, or a study like `rca/2026-10-17/movement-findings.md`), give a read-only
     subagent the paths, the window, the question and the repo rules. Check its load-bearing numbers before acting.
3. **Pick one.** The largest expected seconds a game that needs no ruling (the journal's Queue, plus new findings).
   Write down the expected saving and **the measure it should move** (a stall reason's seconds a stay, a leg's
   median), and why the code is the way it is (d2-rca rule 3: what earlier incident does it protect?). A candidate
   that trades against a ruling (shack containers, prebuff, pauses, stash threshold, Teleport charges) goes to
   "Waiting for the player".
4. **Change** as in **Fix** (focused tests, restart at the lobby). Note the restart's clock time: it is the window
   boundary.
5. **Measure** after at least 30 games (about 30 minutes):
   `speed.py --since '<restart>' --against '<the window before>'`.
   - **Keep** when the targeted measure moved as expected (its interval excludes 0) and YIELD is not worse.
   - **Revert** (restart again) when YIELD or the targeted measure is worse, or something new stalls or stops.
   - **No evidence:** play 30 more games, then decide; still none after 90 games, keep it only if it removes work
     (a wait, a click) and nothing got worse.
   YIELD's interval is about ±25 chests an hour over 120 games. A change worth 1–2 s a game will not show in YIELD
   within an hour, so judge it by its targeted measure, with YIELD not worse.
6. **Journal**: the round under Rounds (candidate, expected, measured, verdict). If kept, add a Baseline row.
   Move the item out of the Queue, and add new candidates found on the way.

Also every hour:
- The trading (`trade.py`): gold an hour of play from sales against the repairs' cost, the seconds the identify
  legs and selling visits cost a game, and each kind's payback: a kind under 1 over 20+ items goes to the queue to
  drop from `pickmode.candidate`.
- "Left on the ground, worth a look" (`games.py`): a set, unique, rune, gem or charm left that the player's rules want
  (memory `d2r-kp6-loop-rulings`, `pickmode.py`) goes to the queue. Ask the appraise skill when worth is unsure.
- Recoveries and stops since the last hour (`games.py`): a cause seen twice is a **Fix** round, ahead of speed.

## Pause and hand-off

On "pause", "stop" or the end of a session:
1. `restart.py --loop off`, unless the player already turned it off (the watch says `PLAYER: loop off`).
2. TaskStop the monitor.
3. Write the round in the journal: what changed, what is unverified, the queue, the rulings waiting.
4. Answer in a few lines: games and chests an hour since the last report, what was fixed or sped up (with the
   measured change), what waits for the player, and that nothing is committed.
