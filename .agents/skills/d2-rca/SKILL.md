---
name: d2-rca
description: Root-cause analysis of a played D2R session with the macros - "new run is here", "do rca", "we got stuck", "KP_4 / attack mode did nothing", "we almost died", "why did it do that", "it was strange". Finds the session log and combat take, pins the moment, traces it to code, reproduces it in the test arena, and writes the findings and the architectural options to rca/<date>/. Use before changing macro or combat behaviour because of something seen in the game.
---

# D2R session RCA

The player reports something seen in a game. The output is a findings file under `rca/<date>/`
(git-ignored) and a short answer: what happened, why, what is verified, what a fix must keep.
**No production change comes out of this skill**: the fix is a separate, agreed step.

Framework map: `inventory_tracking/macros/README.md`. Spec and the player's rulings:
`inventory_tracking/macros/architecture-history.md` (§6.2.3: incidents). History of every fix, dated:
`inventory_tracking/macros/plan.md` (recent entries and an index into `history-through-2026-10-12.md`). Earlier analyses: `rca/*/`.

## Rules

1. **Evidence before explanation.** Every claim carries a log line (clock time), a frame fact from
   the take, or `file:line`. Mark each claim *verified* (read in code, seen in the recording, run) or
   *inferred*. A first reading of a log is a hypothesis: the seal incident of 2026-10-12 was first
   told wrongly from the log alone, and corrected by the frames.
2. **The player's words are the symptom, not the cause**, and may cover several moments. Scan the
   whole game (`session.py idle`), list every candidate, and say which one each finding explains.
3. **Find why the code is the way it is before calling it wrong.** A constant or a pause that looks
   like the bug usually fixed an earlier incident: `rg --no-config -n "<constant>|<word>" inventory_tracking/macros/plan.md inventory_tracking/macros/history-through-2026-10-12.md`,
   `git log -S <constant>` (read-only), the code comment beside it, the tests that pin it. Report
   the situation it fixed and the tests; a fix must keep that situation fixed.
4. **Compare with games where it went right.** `rg --no-config -c "<the line>" inventory_tracking/runs/alt-d/*/probe.log`
   tells whether this is new behaviour, an old gap newly exposed, or a regression of the last commits.
5. **Reproduce before fixing** (the player's ruling, 2026-10-13): an arena incident with the recorded
   presses, through the production code path, and the requirement as a strict `xfail` test.
6. **No ad-hoc fix.** Ask what the spec says (architecture-history.md §2 gaps, §4 rules, §5 answered
   questions), whether the code contradicts it or the spec contradicts a newer ruling, and give
   2–3 designs with one recommendation. A contradiction between two rulings goes to the player.
7. Report your own earlier mistakes that the session shows (a rule that did not do what was said).
8. Never ask the player to label or replay; never change game behaviour, commit, or restart
   `make serve` / `make osd` from this skill. Repo rules apply: `rg --no-config`, `uv run --offline`,
   no state-changing git, `ruff` only on the files you wrote.

## Where the data is

All under `inventory_tracking/runs/` (git-ignored). Directory names are UTC; log lines are local time.

| What | Where | Notes |
| --- | --- | --- |
| Session log of `make serve` | `alt-d/<UTC stamp>-<id>/probe.log` | `Macro:` lines; `Macro: request <routine>` is one key press (`teleport` KP_4, `hunt elites` KP_2, `hunt any` KP_3, `pickup` KP_1, `prebuff`/`macro` Mod+X); `slow press` rows carry the latency trace |
| The healer's own log | `osd/<stamp>/` | `make osd` is independent of `serve`: potions drunk for the mercenary are here |
| Combat take (one per stay in a level) | `combat/<UTC stamp>-<area>/` | `manifest.json` (`started_at`, `area`, `schema`), `frames.jsonl.gz` at 25/s, `events.jsonl.gz` (`cast`, `hit`, `kill`, `gone`), `units.jsonl.gz` (class `txt`, flags, mods), `missiles`, `paths`, `level.json` |

Frame row: `t` (monotonic s), `p` = `[unit, mode, area, x, y, left skill, right skill, life, max life, mana, max mana]`,
`m` = monsters `[unit, txt, mode, x, y, life 0–128, max, flags, owner, ally]`, `x` missiles, `r`
resistances (schema 3, at a change), `macro`, `in`. Reader: `inventory_tracking/combat/takes.py`
(`PlayerRow`, `MonsterRow`, `timeline`, `trim`). The character's mode 10 is a cast, 1 standing;
monster modes 0 and 12 are dying and dead, 4 is hit recovery. Area numbers: 107 River of Flame, 108 Chaos Sanctuary,
39 the cow level. A super unique or champion is told by `flags`/`mods` in `units.jsonl.gz`.

## Method

### 1. Locate and digest (minutes, in the main session)

```
python3 .agents/skills/d2-rca/tools/session.py find
python3 .agents/skills/d2-rca/tools/session.py log  inventory_tracking/runs/alt-d/<session>/probe.log
python3 .agents/skills/d2-rca/tools/session.py idle inventory_tracking/runs/combat/<take>
python3 .agents/skills/d2-rca/tools/session.py unit inventory_tracking/runs/combat/<take> <unit id> [--txt N]
```

- `log`: presses by routine, bursts of mashed presses, and the lines said most often with numbers
  folded. **A line said dozens of times is a loop**; start there.
- `idle`: every stretch with no move and no cast, on the log's clock, with hostiles within
  25/40/60 units. Dead time among hostiles is the defect list.
- `unit`: where a boss or a pack stood against the character, second by second.

Then read the log around each moment and name, for each press, the branch that answered it
(`rg --no-config -n "<words of the line>" inventory_tracking/macros`).

### 2. State the incident

A table: when (log clock), where (coordinates, the route stage), presses, what the character did,
what was near, life lost, potions drunk. One row per moment. This goes first in the findings file.

### 3. Split the work

Small, single-cause question: finish it in the main session. Otherwise launch the studies **in
parallel in one message**, each with a self-contained brief (paths, clock times, unit ids, the
player's words, the repo rules above, and what to return). Read-only studies never edit; only the
reproduction writes, and only under `tests/`.

| Study | Asks | Writes |
| --- | --- | --- |
| Control-flow audit | Every branch the key can take as a decision table with `file:line`; which end with no move and no strike; which loop under repeated presses; who owns movement and where the goal is lost; why the suspect rule exists (plan.md, commit, tests); what the spec says and where code and spec disagree; what a fix must keep | nothing |
| Reproduction | The moment as an arena incident with the recorded presses through production code; the requirements as strict-`xfail` tests; passing tests that the replay matches the recording; what the arena lacks | `tests/inventory_tracking/scenarios/arena/` only |
| Architecture | 2–3 different designs against the spec and the planned stages; for each: what a press means, who owns movement, the guarantees (progress, safety) and why they hold, what is deleted, migration in small steps, tests, risks; one recommendation | nothing |
| Other moments | Every idle or odd stretch the first three do not explain, each traced to code | nothing |

Give an audit or review agent the evidence, not your conclusion. Agents' reports are claims: check
the load-bearing ones (a `file:line`, a number) before repeating them to the player.

### 4. Reproduce

Arena: `tests/inventory_tracking/scenarios/arena/` (`incident.py`, `driver.py`, `game.py`, `cut.py`;
fixtures and `INCIDENTS.md` in `fixtures/incidents/`).

```
uv run --offline python -m tests.inventory_tracking.scenarios.arena.incident --seeds 30 [--cut] [--write]
```

A reproduction counts when the recording lies inside the arena's 10th–90th percentile at the marks.
Say what is simulated and what is fed in from the recording (a curse, a spawn). Where the arena
cannot play the code path yet, say exactly what blocks it; do not imitate the production code by hand.

### 5. Write the findings

`rca/<YYYY-MM-DD of the game>/<short-name>-findings.md`, one file per problem:

1. Header: the game (log, take), the player's words verbatim, the requirements they stated.
2. **What happened**: the incident table.
3. **Why**: the decision tables, the loops, why the rule exists, who owns what, code against spec.
4. **What a fix must keep**: the earlier incidents and tests the suspect rules protect.
5. **Options**: the designs, a comparison table, the recommendation and its order of work.
6. **Reproduction**: incidents, numbers over seeds against the recording, the red tests.
7. **Open**: rulings needed from the player, unknowns, what was not verified.

Mark a section "pending" while its study runs; fill it when the study reports.

### 6. Answer the player

Lead with the cause in one sentence, then the incident, what else was found, the recommendation,
and the rulings needed. Say what is verified and what is not. Point to the findings file. Offer
the fix; do not start it.

## Traps seen so far

- The log's times are local, the take directories UTC; align by `started_at`, never by eye.
- `Macro: Attack mode on` only means the mode's run started; a press 100 ms later cancels it.
  Count strikes by `cast` events and blade-missile births, not by log lines (held-button casts
  are undercounted in `cast` events).
- Monster get-hit is mode 4; mode 9 is a block.
- "None in reach" with a hostile 20–30 units away is not by itself a bug: check the attack's reach
  and the shot, then whether the mode had its licence to move (`sweep`).
- A label on the level card ("seal 1") is an order of visiting, not a property of the object; the
  object's class says which seal it is.
- A rule tested only on fakes has not been played: say so until a game confirms it.
