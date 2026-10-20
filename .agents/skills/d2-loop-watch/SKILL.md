---
name: d2-loop-watch
description: Continuous monitoring, fixing, development and speed optimisation of the KP_6 loop (the Andariel run or the Lower Kurast chests) while it plays - "start monitoring", "watch the runs", "continue the improvement loop", "analyze runs", "optimize speed", "make it faster", "resume watching", "the loop is running, keep it going", "reload/restart on the next town", "we stuck" during a watched loop. Arms a live watch on serve's log (one line per game, stalls, stops, sales), fixes and restarts the service autonomously, runs agents for larger changes, tests before every restart, analyses the runs every hour, tries one speed change at a time and keeps it only if the measures say so, and keeps the rounds' state in the loop's journal. Use the d2-rca skill instead for a deep analysis of one incident the player reports.
---

# The KP_6 loop: watch, fix, develop, analyse, speed up

The player's goal is wealth for a Jah (Enigma), from the KP_6 loop running unattended. The agent watches whole runs,
fixes what stops the loop, builds the player's rulings, restarts `make serve` by itself, analyses the runs to find where
the time goes, and tries speed changes one at a time, each measured. The player, 2026-10-17: "we stuck! I didn't stop
loop myself and you have all the tools to fix things and continue"; "we need it to continously analyze runs, try to
find and optimize speed".

Two loops run together: **keep it running** (the watch, Each event, Fix) and **make it better** (Develop, Speed). A stop
or a lost valuable always comes first.

**The loop's kinds** (macros/loop.py KINDS, three presses of KP_6; `restart.py --kind`): `andariel` (the waypoint to
Catacombs 2, the stairs down to 3 and 4, Andariel, her loot, the next game; the default since 2026-10-18) and `lk` (the
Lower Kurast chests). **The measure is the kind's yield an hour of cycles**, everything between counted (town, trade,
lobby, recoveries), not game time:
- Andariel: **kills an hour** (`andy.py`); 84/h at 17:54-18:15 on 2026-10-18 (median cycle 35.9 s).
- Lower Kurast: **chests an hour** (`speed.py` CYCLES); 422/h on 2026-10-18 01:14-01:44. A game that opens one more
  chest is longer and still better.

**Every loop optimizes its own metric, and only the drops come before it** (the player, 2026-10-19 02:12: "every loop
has it's own metric, that it must optimize: boss kills/elites kill/opened chest. the only thing that has more priority -
proper interactions with drops (we cannot run without picking desired items just with killing boss alone)"):

| Loop / mode | Its metric (an hour of cycles) | Not its job |
| --- | --- | --- |
| Andariel (KP_6) | boss kills | full-clearing a level, a terror zone or not ("andy loop shouldn't focus on full clearing level") |
| Lower Kurast (KP_6) | chests opened | fights that are not in the way |
| TZ leveling | elite kills (champions, uniques, super uniques, Herald leaders) | white packs that neither block nor threaten |
| Full clear TZ | Herald hunting (a clear of everything) | — |

- Priority in every loop: 1. the drops (pick up what the pickup mode wants, never leave a valuable the loop would take
  on the ground: hard rule 1); 2. the loop's metric; 3. anything else only if it does not cost (1) or (2).
- A goal that helps another metric (XP, a terror zone's extra loot, a full clear) is a mode of its own, never folded
  into a loop. The KP_6 loops ignore the terror-zone full-clear default (`hunt.Hunter.run_mode`, `posted.looped`).
- A change is judged by the loop's own metric (`andy.py`, `speed.py`, the TZ tool); drops lost (MISSED) veto it.

State between rounds and sessions: [the journal](../../../inventory_tracking/macros/loop-journal.md)
(baseline, queue, rulings waiting, rounds). Design: `inventory_tracking/routes/lower-kurast-loop-plan.md`. The player's
rulings: AGENTS.md, the memory `d2r-kp6-loop-rulings` (every ruling, dated, verbatim), and the journal. Studies:
`rca/<date>/*-findings.md`.

## Hard rules

1. **Never leave a game while a valuable the loop would pick up lies on the ground.** No restart, recovery or watchdog
   may cost loot. `runner.valuable_left` guards the loop's own exits. A restart is safe only through
   `tools/restart.py`, which waits for the lobby (the player, 2026-10-17: "that is the exact thing we want ot avoid").
   A valuable in the read is taken **now**, not left for a trip back (the player, 2026-10-18 18:24, IMPORTANT: "we left
   Ko rune on ground and moved away"): on the loop's Teleport run a valuable Teleport reaches within
   `hunt.LOOP_PICK_SECONDS` is a side goal whatever the walk round a wall; the sightings' trip back is only the net.
2. **The item labels are on before a level run** (the player, 18:47: "we MUST check if loot toggle is enabled"):
   `routines.show_items_on` reads `World.show_items` and presses the character's Show Items key (≤3). `make osd`
   presses it at a game's start but gives up after 3 presses during the load (game 40, 18:22 on 2026-10-18).
3. **Gold.** Repairs and purchases use only the gold carried in the inventory. Never the stash's gold ("I don't want to
   touch this 9M of gold atm"). `repair.py` checks the quoted cost and the stash gold after. If
   `runs/alt-d/repair-touched-stash.txt` exists, repairs are off: tell the player.
4. **Selling** only what the appraisal calls `vendor` among the loop's own items (identified at Cain), and only surplus
   copies: `copies.py` keeps the best copy of a unique or set first ("loop should keep the best copy first"). Owned
   copies decide the verdict (identify/service.py `owned_verdict`, 2026-10-19): 1+ Ist stays as appraised, better rolls
   than every owned copy are `keep`, a rolled duplicate an owned copy rolls at least as well as is `vendor` (charms,
   jewels, runes, bases, runewords excepted; the loop's carried copies are not owned). Never the
   player's gear or anything of the player's, a potion, a rune (rune sales stopped 2026-10-18: stacks over 80 are cubed
   down instead), a gem, a set or unique charm (Sunders, Gheed's, Annihilus, Torch), anything appraised other than
   `vendor` ("do not sell own equipment or valuable items"). A rare amulet with +FCR, +2 skills or +life is kept
   (`keepers.py`, whatever the appraisal says: two were sold at 03:48 on 2026-10-19); a high vendor price alone is no
   reason to keep. Never a Ber Rune in a transmute (Enigma).
5. **The town visit** (`town visit` leg, macros/visit.py, town.py) only when the room runs low
   (`town.TRADE_ROOM`); it leaves keepers stashed, junk sold (junk may be parked on a stash page and sold after), keys
   and scrolls refilled, the staff repaired if the carried gold covers it, **the cube empty, a 2x4 block free**. The
   stash once a visit, no running back and forth. A keeper with a page but no way out waits in the cube
   (`KEEPER_IN_CUBE`); a keeper no page takes **stops the loop** (cause 'stash': "if stash is full - we need to stop
   loop"). One game may make several trips to town (`TRIPS_A_GAME`); a valuable with no room is cube, then a trip, then
   taken; a refused Gheed's charm is the Gheed's swap.
6. **The loop never stands stopped.** A stop is fixed and the loop turned back on by you, at once, before any speed
   work; a valuable on the ground at a stop is fetched by the next leg, not waited on. Only the player's own stop is
   waited on (rule 7).
7. **The player's pause wins.** `PLAYER: loop off` means the player turned the loop off with KP_6 (often to pick
   something up by hand). Never turn it back on; wait for `PLAYER: loop on`. "pause" or "stop" in chat: `restart.py
   --loop off`, stop the watch, wait for the player.
8. **Never commit** unless the player says "commit". No game memory writes. Battle.net: the player runs only `make
   serve` (and `make osd`); never the game's own files.
9. **A change that departs from a ruling needs the player's ruling.** A trade-off between speed and a ruling (a wait,
   the prebuff, the stash threshold, selling, gold) is asked, not decided. The player's rulings are kept verbatim and
   dated in the memory `d2r-kp6-loop-rulings` and the journal the moment they are given.
10. Repo rules: `uv run --offline`, `rg --no-config`, `ruff` and `pyrefly` clean on the files you wrote, item codes and
    recipes from the game data or the d2data dump (never from memory), comments dated with the player's words.

## Where the loop lives (inventory_tracking/macros/)

| Concern | Files |
| --- | --- |
| Legs, kinds, room and trade triggers | `loop.py` (`next_leg`, KINDS, TRADE_ROOM use, TRIPS_A_GAME) |
| The service's routines, stops and recoveries, watchdogs | `runner.py` (requests, the runs' lifecycle) and its parts in `running/`: `recovery.py` (`_loop_stopped`, `classify`, `_gheeds_swap`), `valuables.py` (`_fetch`, `_go_back`, `_valuable_left`), `watch.py` (`poll`: the watchdogs), `legs.py` (`_loop_hands`: the LOOP closures), `execution.py` (`perform`); the stop rules in their order: `stops.py` (`first`, `decide`, `ROOM_CAUSES`) |
| Level run, fight, side goals, pickups on the way | `hunt.py` (`Hunter`, the fight), `hunting/` (`choice.py` `side_drop`, `on_the_way`; `judging.py` `judge`), `pursuit.py` (`RUSH_THE_BOSS`), `buffs.py` (`QUIET_BY_THE_BOSS`) |
| Pickup and what is valuable | `pickup.py`, `pickmode.py`, `lootpolicy.py` (`verdict`, hold classes), `sightings.py` (remembered drops) |
| Town visit | `visit.py` (`visit`, `_cube_runes`, `JAMELLA_FIRST`, `REREAD_SECONDS`: one short stash re-read before the page-by-page scan), `town.py` (`contract`, `rune_transmutes`, `PARK_JUNK`, `KEEPER_IN_CUBE`, `RUNE_TRANSMUTES`), `visitlog.py` (snapshots in `<session>/visits/`; the shadow planner townplan.py was removed 2026-10-19) |
| Cube, stash, shop, repair, Cain | `cube.py` (`data/rune_cube.json` from `build_rune_cube.py`), `stash.py`, `shop.py`, `repair.py`, `cain.py`, `copies.py` |
| Game reads, keys, Save and Exit | `game/` (`records.py` `World`, `memory.py` `GameMemory`, `decode.py`, `layout.py`), `routines.py` (`show_items_on`, Save and Exit, prebuff), `actuator.py` (`Abort(cause=)`) |
| Log words the tools read | `.agents/skills/d2-loop-watch/tools/logwords.py`, pinned by `tests/skills/test_loop_watch_lines.py` |

Switches for a change under test are module constants with a dated comment (e.g. `RUSH_THE_BOSS = True`,
`QUIET_BY_THE_BOSS = False` until F1 is measured): flip one, restart, measure.

## Tools (`.agents/skills/d2-loop-watch/tools/`: `python3`, but `speed.py` and `andy.py` with `uv run --offline python`)

| Tool | What it does |
| --- | --- |
| `watch.py` | Follows the newest `runs/alt-d/*/probe.log` across restarts. Prints one line per game (seconds, legs over 25 s, cube/stash/shop notes), and a `MISSED:` line for each valuable of the game never picked up. At once: stops, recoveries ("the game is left"), guard stops, identify verdicts, sales, repairs, errors, tracebacks, `PLAYER: loop on/off`, and `STALL` after `--stall` s with no leg and no teleport, kill or pickup while on, or one leg past 300 s (`LONG_LEG`). A re-armed watch reads the current log quietly first. |
| `restart.py --loop on\|off\|keep [--kind andariel\|lk]` | Waits for a safe moment: at once if the loop is off, else the next `next game` leg (the lobby). Then it writes `runs/alt-d/restart.request` and confirms the new service's `resumed after a restart` line. Exit 1: no safe moment, nothing written. Exit 2: no resume seen. |
| `kind.py andariel\|lk\|tz\|tzclear` | Switches the loop's kind without a restart (`loop-kind` request, runner.py `choose_kind`): at once with the loop off, else from the next game. The card says `Loop run: <kind>[ from the next game]`; a restart keeps it. |
| `andy.py [--since ..] [--until ..] [--against SINCE UNTIL] [--no-takes] [--json]` | **Andariel kills an hour of play** and the kill-to-kill cycle by phase (loot, next game, town/prebuff, waypoint, Catacombs 2 arrival, each level's run to the stairs and press, Catacombs 4 arrival to in reach, in reach to dead, trade sessions, recoveries); walks on the down levels; the fight per take; `--against` with a 90% bootstrap interval. About 9 s for 2 h. |
| `games.py [--since 'YYYY-MM-DD HH:MM'] [--last N] [--sessions DIR...] [--json]` | Games, games an hour, median/p90, each leg, slowest games, every recovery, stop and error, what was done, **MISSED** valuables, what is left by design. |
| `speed.py [--since ..] [--until ..] [--against SINCE UNTIL] [--no-towns]` | The Lower Kurast run: chests an hour (YIELD), where a stay's time goes (standing / casting / moving, stall reasons by log line, legs against Blade Warp's pace), inactive time in town and on the level. |
| `trade.py [--since ..] [--until ..]` | Items identified by base and verdict, junk sold and its gold, gold an hour of play and a second of trade time, payback by kind (under 1 over 20+ items: leave that kind on the ground). |
| `logwords.py` | The shared log patterns of watch/games/andy (a log line changed in code is changed here, and its test). |

Deeper: `python -m inventory_tracking.takes.legs <take>...`; `.agents/skills/d2-rca/tools/session.py` (`log`, `idle`,
`unit`, `inputs`: the service's `sent` events against the player's own). Logs: `runs/alt-d/<UTC>-<id>/probe.log`
(serve, local times), `runs/combat/<UTC>-<area>/` (takes: frames at 25/s, events, `level.json`), `runs/osd/<stamp>/
osd.log` (`make osd`: healer, Show Items presses), `<session>/visits/<HHMMSS>.json` (town visit snapshots).

## Start or resume a watch

1. Read the journal: queue, rulings waiting, the last round; and the memory `d2r-kp6-loop-rulings`.
2. Check the state: `games.py --last 15` (or `andy.py --since <last restart>`) and the tail of the newest `probe.log`.
   Is serve up? Is the loop on, which kind? Who turned it off?
3. Arm the watch with the Monitor tool, `timeout_ms: 1800000`, description "KP_6 loop: games, stops, stalls":
   `cd <repo> && python3 -u .agents/skills/d2-loop-watch/tools/watch.py 2>&1`. A monitor lives at most 30 minutes; on
   its expiry notice re-arm it the same way, without asking. One watch at a time: TaskStop the old one first.
4. If the loop is off and the player asked to start it: `restart.py --loop on --kind andariel` (it needs the character
   in a game or the lobby, and the game window as the player left it).
5. Tell the player in one or two lines what is being watched, and that "pause" stops it.
6. Every 5 games check that the current round advances (an agent, a measurement, a restart due); never just narrate
   games. Speed rounds are due an hour into play.

## Each event

| Event | Action |
| --- | --- |
| `game N: ...` | Nothing, unless it is over 2× the median (Andariel ~35 s, a game with a town visit ~65-90 s), or a leg other than the chests is over 25 s: then read the log for that game; note it in the queue if it repeats. |
| `STALL` / `has not moved for 45 s` | Read the newest `probe.log` tail (the last 200 `Macro` lines) at once, then the take's frames. A focus wait or a panel the player opened is no defect. Otherwise **Fix**. Each 45 s stall is analysed on its own (the player: "we need to analyze each case"); it counts as no room only when a valuable is remembered and the inventory truly has no room for its size (`rca/2026-10-18/stalls-findings.md`). |
| The same hop again and again: `priced act expired` ×N, `Teleport on t` with no `landed at`, then `Save and Exit: still in the game` ×N | Our pointer did not reach the game (keys did): `rca/2026-10-18/freeze-findings.md`. Check the take: the first hop landing on the last clicked spot, the Defiler still moving, mana stuck below max. Not a server freeze until the frames prove it (the player: "this is something with our code, do RCA"). |
| `loop stopped` / `stops here` | **Fix** at once, ahead of everything else, then `restart.py --loop on`. A valuable on the ground at a stop is fetched by the restarted loop (the game stays open), never waited on (a Unique Brandistock stood 37 min). |
| `the game is left` (a recovery) | Note the cause. A cause seen twice goes to **Fix**. |
| `MISSED: game N, <item> ...` | Hard rule 1: trace it at once (the sighting, every `pickup:` / `aims for` / `remembered` / `gone back for it`, where the run went) and **Fix** before speed work. A MISSED right after `PLAYER: loop off` / `loop on` (`game None`) is usually the player's own pickup by hand: check the next `carried at its first look` line for the item before calling it lost. |
| `identify: appraised ...` / `copies: keep\|sell` / `shop: sold ...` | Rule 4: each sale must be `vendor` and not the best copy; check the gold goes into the carried gold (`carried gold A -> B after the sales`). |
| `ERROR Shop check failed ... Shop stock changed during scan` | Harmless: the HUD's shop card raced the loop's sale (a skip is queued). Any other `Traceback` / `ERROR` / `Macro failed`: **Fix**. |
| `trade session done[ (short of the contract: …)]` | Every part must hold (cube 0, block 2x4 free, junk left 0, keys, ground clear); "short of the contract" is a **Fix**. `stash: the view still unread: page by page` (the slow scan) should be rare; often is a finding. |
| `cube: three X Rune [and a <gem>] into a Y Rune ...`, `runes cubed`, `not cubed: ...` | Rune stacks over 80 cubed toward 80 (3 a visit, gem recipes with the gem from the Gems tab by Ctrl+Shift+left click). `not taken into the cube` or a non-empty cube after: **Fix**. |
| `Show Items was off before the level run: turned on` / `Show Items stays off` | Rule 2. The second stops the run: check `osd.log` and the key binding. |
| `PLAYER: loop off` | Rule 7. Say where any valuable lies; finish notes; keep watching. |
| `== following ...` | A new service: expect `resumed after a restart: loop on, ..., run Andariel`. |

## Fix (rounds of the improvement loop)

1. **Evidence first**: the log lines with their times, the take's frames (positions, modes, mana, the units), and the
   code branch that said them (`rg --no-config -n "<words>" inventory_tracking/macros`, or `codegraph explore`). Why is
   the code like that? The comment, plan.md, the tests near it (d2-rca rule 3). Mark claims verified or inferred. A
   first reading of a log is a hypothesis: the frames or a visit snapshot often say otherwise (the Boots "stash full"
   diagnosis of 2026-10-18 was wrong; the snapshot showed a stuck keeper).
2. **Smallest fix that keeps the old fix**: edit, then add or adjust the focused test (`tests/inventory_tracking/
   macros/test_<module>.py`, the fakes in `fakes.py`).
3. **Test** (below), then **restart** (below).
4. **Verify on the next games**: say what line or number should change, and check it on the games that follow.
5. **Journal**: a line in this round's entry (time, cause, files, tests, restart time, what the next games showed);
   a new ruling also goes to the memory `d2r-kp6-loop-rulings` at once.

## Develop (rulings and larger changes)

- **Agents for size, the main session for integration.** A change spanning several modules, a study over many takes,
  or two independent changes go to background agents (Agent tool, `run_in_background`), one per disjoint set of files,
  each with a self-contained brief: the player's words verbatim, the evidence (paths, clock times, takes), the files it
  owns and the files it must not touch, the must-keep tests, the repo rules, "no restart, no commit", and what to
  return. Read-only studies write only `rca/<date>/*-findings.md`.
- **Check what agents report** before repeating it: re-run their focused tests, read the load-bearing `file:line`, and
  check one number against the log or the take (the Ko Rune agent's "a fresh drop" was confirmed in the take's frames).
- **Relay new rulings** to the agent that owns the code (SendMessage); a ruling that contradicts an agent's design
  (the 2 s arrival wait) is removed at once, tests with it.
- **The tree is shared and live**: the service loads the code only at a restart, so any half-done edit of any agent is
  shipped by the next restart. Before a restart: no agent is mid-edit (ask it to hold production edits until you say
  the restart is done, then release it), and the wide suite is green.
- Never read an agent's output file (the JSONL transcript overflows the context); wait for its notification.
- Each speed change behind a switch, one live at a time (F1 measured ~30 games before F3 is flipped).

## Test

- Focused: `uv run --offline pytest tests/inventory_tracking/macros/test_<module>.py -q -x`, plus `uv run --offline
  ruff check <files>`, `ruff format --check <files>`, `uv run --offline pyrefly check <files>`. Pyright's "import could
  not be resolved" in the editor is noise.
- **Wide suite before every restart** (about 1 min): `uv run --offline pytest tests/inventory_tracking/macros
  tests/inventory_tracking/combat tests/inventory_tracking/builds tests/inventory_tracking/scenarios/golden
  tests/inventory_tracking/scenarios/battle tests/skills -q -p no:cacheprovider`. A red suite is no restart: it is the
  tree with someone's unfinished work, or a real break. The goldens and battle replays catch a changed decision.
- **Routine whole tree**: `uv run --offline pytest tests/inventory_tracking tests/skills -m "not slow" -q -p
  no:cacheprovider` (about 2-3 min); the full run (no `-m`, ≈ 9-10 min, in the background) after a change to combat,
  hunt or pursuit: the `slow` lane is the arena plays (tests/inventory_tracking/scenarios/conftest.py `SLOW`).
- A triage rule change (pricing): `uv run --offline pytest tests/pricing/triage -q`, then rebuild the rules
  (`pricing/data/triage/rules.json`) as the rule's importer says. The knowledge test's market-sha check is skipped
  (frozen artifacts, 2026-10-19).
- A log line changed: `tests/skills/test_loop_watch_lines.py` and `tools/logwords.py` together.
- Tests run at nice 19, one run on the host at a time (`tests/conftest.py`); `-n 6` gives workers only while the game
  is not running, so during a watched loop they are serial; never with a pipe
  in front of a restart (`pytest ... | tail && restart` restarts on a red suite: the pipe's status is `tail`'s, 13:17
  on 2026-10-17).

## Restart

`python3 .agents/skills/d2-loop-watch/tools/restart.py --loop on --kind andariel` (or `--loop keep`), from the repo
root, with `timeout 600` (TZ games run 4-7 min: pass `--wait 1200` and `timeout 1300`, the default 300 s wait gives up). It waits for the next lobby (`next game` leg) when the loop is on, so the town visit of the
game before is finished ("reload on the next town visit" means this). The watch follows the new log by itself.
After it: the journal line (time, session id, what went live, what did not), and tell the player what is live. With
the loop off by the player, a restart keeps it off (`--loop keep`) unless the player asked otherwise.

## Speed: analyse and optimise (every hour of play)

The loop is: **analyse → pick one candidate → change → measure → keep or revert → journal**. After a change, leave
the loop alone for 30+ clean cycles, then analyse; a fix for a stop or a lost valuable is the exception.

1. **Analyse.** Andariel: `uv run --offline python .agents/skills/d2-loop-watch/tools/andy.py --since '<restart>'
   --against '<the window before>'`. Lower Kurast: `speed.py` likewise. If a change is live, judge it first (step 5).
2. **Find candidates**, the most seconds a cycle first: a phase whose p90 is far over its median (Catacombs 2's run
   to the stairs: 4.6 s median, 10 s p90), stall reasons by log line, standing against casting and moving, town legs
   over their floor, the trade's payback. A deep question goes to a read-only agent.
3. **Pick one** that needs no ruling. Write down the expected saving, **the measure it should move** (a phase's
   median, a stall reason's seconds) and the guards (lowest life on the level, potions drunk, MISSED), and why the code
   is the way it is (what earlier incident it protects). A trade against a ruling goes to "Waiting for the player".
4. **Change** as in Fix, behind a switch; restart; note the clock time (the window boundary).
5. **Measure** after 30+ games: keep when the targeted measure moved (its interval excludes 0) and the yield is not
   worse; revert when either is worse or something new stalls; no evidence after 90 games: keep only if it removes
   work and nothing got worse. A 1-2 s change will not show in the yield within an hour: judge it by its measure.
6. **Journal** the round (candidate, expected, measured, verdict); a kept change adds a Baseline row.

Also every hour: `trade.py` (gold an hour, payback by kind), `games.py` (left on the ground worth a look, recoveries
and stops: a cause seen twice is a Fix ahead of speed).

## What to avoid (each one happened)

- **A wait added to look safe.** The 2 s hold before a level's first move "so the loot is read" was rejected at once
  ("that is totally wrong. we DO not need to wait"): find the real cause (the walk distance, the Show Items toggle)
  and fix that. Any added wait in a loop leg is a speed trade: ask first.
- **Blaming the outside.** "Server freeze" was the first story for the 17:58 stall; the frames showed our pointer not
  reaching the game. A cause outside the code is a claim the frames must prove.
- **Restarting on a dirty tree** (agents mid-edit, a red suite), or after a pipe hides a red suite.
- **Walking distances for a Teleport character**: a valuable 34 units away, 117 by walking round a wall, was left
  ("not on the way"); reach is judged by the means of travel.
- **Waiting for the player on a stop you can fix**, or turning the loop on after the player turned it off.
- **Selling on a price**: only `vendor` from the appraisal, best copy kept; never runes, gems, charms of worth, gear.
- **Unverified agent claims** repeated to the player; a diagnosis from the log alone.
- **Monitor noise**: re-arm one watch at a time; stop stale `until` waits and old shells (the goal check-ins list
  them); answer every event in one line unless it needs action.

## Pause and hand-off

On "pause", "stop" or the end of a session:
1. `restart.py --loop off`, unless the player already turned it off (the watch says `PLAYER: loop off`).
2. TaskStop the monitor; let running agents finish or stop them, and say which.
3. Write the round in the journal: what changed, what is live, what is unverified, the queue, the rulings waiting.
4. Answer in a few lines: kills (or chests) an hour since the last report, what was fixed or sped up (with the
   measured change), what waits for the player, and that nothing is committed.
