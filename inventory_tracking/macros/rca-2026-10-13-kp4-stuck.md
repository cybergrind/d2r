# RCA: repeated KP_4 stuck with no movement — Chaos Sanctuary, 2026-10-13

Status: analysis complete; fix plan proposed, not implemented.
Session: combat take `20261013T060607Z-108` (The Chaos Sanctuary, Hell), service log
`inventory_tracking/runs/alt-d/20261013T060446Z-aa50e0b0/probe.log`.

## 1. What happened

On the Diablo route the player opened Vizier seal 1 and 2 by KP_4 presses (Blade Warp hops,
09:06:39–42, working as designed). The route then reached `fight('Grand Vizier of Chaos')`
— a fight stage that names **no mark** (routes/catalog/act4.py:23). Attack mode killed the 4
monsters in reach (09:06:43–45), then reported "Nothing left in reach" and went idle:
7→5 hostiles 27–52 units away, shot clear (Echoing Strike's reach is ~22).

From **09:06:47.197 to 09:07:06.035 the player pressed KP_4 46 times in ~19 s**. Every press
produced the same three log lines and nothing else:

```
request teleport, 0 ms old, while hunt any
Attack mode paused
Diablo: Grand Vizier of Chaos, attack mode
```

No hop, no walk, no movement. The character stood at (7656, 5281) the whole window. The player
left the game at 09:07:07.

What it was **not**: the key binding worked (requests arrived "0 ms old"); the staff had charges
(the seal hops seconds earlier spent them, "4 charges kept"); reads were healthy (no read errors,
no "did not move" lines — no movement was ever *attempted*); the tracker saw the hostiles (the
idle lines name and range them).

## 2. Root cause

**The route layer refuses the hop, violating the settled KP_4 contract.**

`macros/route.py` `press()`:

```python
if found is not None and found[1].kind == FIGHT and not found[1].mark:
    run.say(f'{found[0]}: {found[1].boss}, attack mode')
    attack()
    return
```

A mark-less `fight` stage converts the press into "turn attack mode on from where the character
stands" and returns — `plain(target)` (the hop) is never reached. This contradicts the contract
recorded in architecture.md (2026-10-12): **"KP_4 always hops; it is never refused"** (§5,
"The player's hop lands with care"; question 4 answered by 4.3). The route branch predates the
contract and was never revisited.

The refusal is also **invisible**: the `say` text is identical on every one of the 46 presses,
so neither the player nor a log reader can tell a refused press from a working one without
cross-reading three lines.

## 3. Contributing causes (why nothing else rescued the situation)

1. **Attack mode cannot approach on its own once the sweep dies.** The sweep lives
   `FOLLOW_SECONDS` (8 s) past the last real step (`Sweep.start`/`spend`, hunt.py:233-243).
   The swallowed presses never start or spend the sweep, so ~8 s after the last seal hop
   (`09:06:41.8` → dead by `09:06:50`) `follow_on` returns False forever (hunt.py:856-864:
   `run.clock() > self.sweep.until` → `sweep.end()`). The hostiles at 27–52 were inside
   `SWEEP_UNITS` (60) — a live sweep would have gone to them. After that the mode idles by
   design ("attack mode does not move, so nothing happens until the player does",
   plan.md:1553), and the only key that could re-aim it is the one being swallowed.
2. **Every press paused the one mechanism that made progress.** A teleport press during attack
   mode cancels the mode ("attack mode pauses for it", runner.py:217) and the mode resumes
   `TRAVEL_QUIET` (0.5 s) later. 46 presses every 0.2–0.6 s kept the mode paused almost
   continuously (log: 66 "paused" vs 13 "on" for the whole run). During the one press lull
   (09:06:57–58) the mode immediately struck and killed a monster — proof the pause was harmful,
   not neutral.
3. **Stage completion has a single, unreachable witness.** A `fight` stage ends only when the
   boss name enters `facts.dead` (routes/progress.py `done`), fed by the monster tracker's kill
   list. The boss standing 27–52 units away in plain sight does not count, and no other fact
   (time elapsed, hostiles seen, presses refused) can advance or abandon the stage.
4. **No stuck detection anywhere.** The runner counts slow presses ("slow press" warnings) but
   has no notion of a press that changed nothing: position, stage and outcome identical to the
   previous one. Architecture.md §5 already states the principle this violates: "A mode that
   fails says why and is distrusted for its intent's time; the navigator answers with the next
   mode or with 'no way' and the reason — never silence."

## 4. Why the tests did not catch it

- `tests/inventory_tracking/macros/test_route.py:412` asserts the swallow as *correct*
  (`here.press(...) == ['attack']` for the mark-less Mephisto fight) — the contract breach is
  enshrined in a test written before the 2026-10-12 decision.
- No test presses twice against an unchanged stage; no test covers "press while attack mode is
  already on"; no replay scenario exercises a mark-less fight stage. The scenario replays
  (`tests/inventory_tracking/scenarios/`) cover navigation and battle, not the route layer's
  press semantics.
- The harness fake in test_route.py (`Here`) records `attack` as an action but cannot represent
  hostiles at known positions, so "hop toward the visible boss" was untestable there.

## 5. Fix plan

Ordered; F1 and F2 fix this incident, F3 and F4 harden the class of failure.

### F1 — A mark-less fight gets a dynamic mark; the press always hops (route.py, runner.py)

Delete the early-return special case. For `FIGHT` with no mark, derive a target from the world,
in order:

1. the boss unit, when the tracker/world knows it (name-matched superunique);
2. the nearest known hostile (the same `hostiles(world)` the idle log already ranges);
3. the level card's own first mark (today's `card()` fallback).

Then run the existing generic path: hop toward it with the runner's safety intact —
`pack_ahead` ("the fight first" branch), `boss_step`, `warp_hop` — and `attack()` as the
*arrival* action within `FIGHT_NEAR`, exactly as marked fights already do. A press with **no**
known hostile and no card mark may answer `attack()` — once (see F2). Net effect: KP_4 hops
again; the contract holds for every stage kind.

### F2 — No-op press detection and escalation (runner.py, engine press trace)

The runner remembers the last press's (routine, route stage identity, character position,
outcome). A press that ends with the character within `MOVED` of where it started, the same
stage and no world change is a **no-op press**:

- 1st no-op: allowed (arrival at a mark is legitimate), but the `say` must say what happened
  ("Grand Vizier of Chaos: attack mode — the boss is 38 away NW; the next press hops to him");
- 2nd consecutive no-op with an unchanged stage: escalate — the press must do something
  different (hop toward the nearest known hostile even past `pack_ahead`, or a walk step), and
  say why the first answer was abandoned;
- a no-op press must **not** pause attack mode (skip the cancel when the queued routine can
  provably not move — the route layer can answer this cheaply before the cancel);
- record `noop: true` in the press trace notes so the slow-press JSON and the HUD card show it.

This is the generic guard: any future stage/handler that answers a press with silence is caught
by it, not just this branch.

### F3 — Feed the sweep from mode decisions, or let the mode approach (hunt.py; design decision needed)

Two options, pick one in implementation:

- **F3a (small):** a press that turns attack mode on for a fight restarts the sweep window
  (`Sweep.start(now)`), so the mode keeps its 8 s of approach per press; combined with F1 the
  window is rarely needed.
- **F3b (larger, architecture §5 direction):** attack mode that is idle with hostiles in sight
  (clear shot, within sight range) approaches the nearest on its own after `IDLE_APPROACH`
  seconds, with `say` + trace. This changes a long-standing design ("attack mode does not
  move") and needs its own pass in plan.md; do not bundle it silently into this fix.

### F4 — Observability

- Refused/no-op presses get a distinct `say` and a `noop` field in the press notes (F2).
- The idle line already logs nearest-hostile distance; add the sweep's state (`steps`, `until`
  remaining) to it so the next incident's log shows the sweep dying instead of inferring it.
- The route's `say` for a mark-less fight includes the derived target (F1) or the reason there
  is none.

## 6. Test plan

**Unit — tests/inventory_tracking/macros/test_route.py**

1. Mark-less fight, boss visible at a known position → press hops toward the boss
   (assert the fake records `step <toward boss>`, not `['attack']` alone). Update the fake
   (`Here`) to expose hostiles with positions.
2. Mark-less fight, attack mode already on, boss in reach → press is `attack` once (arrival,
   FIGHT_NEAR semantics) — replaces the line-412 expectation with the new contract.
3. Mark-less fight, nothing known (no hostiles, no card mark) → first press `attack` + reason
   say; second identical press escalates (movement attempt or distinct say) — never the same
   no-op answer twice.
4. Unchanged: marked fights, `use`, `loot`, `leave`, border `cross` keep their behavior
   (existing tests pin this).

**Contract test (new file, e.g. tests/inventory_tracking/macros/test_press_contract.py)**

5. Property: for every stage kind in `PERFORMED` × attack mode on/off × (world with a reachable
   hop), one press produces ≥1 world-changing action (move/click/pickup/open/cross) **or** a
   say that names the reason and differs from the previous press's say. This is the
   architecture.md "always hops, never refused, never silence" rule as an executable check.

**Runner — tests/inventory_tracking/macros/test_runner.py**

6. Two consecutive no-op presses → escalation path taken, second press does not cancel attack
   mode (no pause for a press that cannot move).
7. No-op press records `noop` in the press notes.

**Sweep — tests/inventory_tracking/macros/test_hunt.py**

8. F3a: a fight-stage press that turns the mode on restarts the sweep window; or F3b: idle
   with a clear-shot hostile in range approaches after the timeout — whichever is chosen.

**Replay — tests/inventory_tracking/scenarios/**

9. Cut a fixture from take `20261013T060607Z-108` (frames/events/paths cover 09:06:42–09:07:07)
   under the battle/navigation replay harness: stage = mark-less fight, hostiles 27–52 away,
   46 teleport presses. Assert: with the fix, the character leaves (7656, 5281) within the
   first 2 presses and the stage can complete; without it, the replay reproduces the 46 no-ops
   (kept as the regression's "before" record).

**Manual verification**

10. One live Chaos run to the Vizier stage; press KP_4 repeatedly with the boss out of reach:
    first press hops (or says why), repeated presses keep hopping; probe.log shows no run of
    identical says.

## 7. Risks and open questions

- F1's fallback 2 (hop toward the *nearest hostile*) can mean hopping into a pack: `pack_ahead`
  already guards the landing, and the escalation in F2 is what may override it — decide the
  override's ceiling (e.g. only when the stage is provably unwinnable from here).
- `fight('Diablo', 'Diablo')` is marked and unaffected; the other mark-less fights in the
  catalogue (Mephisto, the Chaos seal bosses) all gain F1's behavior — audit the catalogue for
  mark-less `fight` stages and confirm each boss is name-matchable in the tracker.
- F2's "did the world change" check must tolerate knockback and being pinned (Durance of Hate 2,
  plan.md:2258: 22 s in run mode against a wall) — position delta alone is not enough; combine
  with "no input was sent" from the press trace.
- The 2026-10-12 contract ("always hops") and the route layer's "one press performs one stage
  step" both stay; F1 reconciles them by giving the stage a real destination instead of
  exempting it from the contract.

## 8. References

- Incident log: `runs/alt-d/20261013T060446Z-aa50e0b0/probe.log` lines 455–670; take
  `runs/combat/20261013T060607Z-108/`.
- Contract: `macros/architecture.md` ("KP_4 always hops; it is never refused", 2026-10-12;
  §5 "never silence"; question 4 → 4.3).
- Code: `macros/route.py` `press` (the swallow), `macros/runner.py` `staged`/`perform`/`_wait`,
  TRAVEL_QUIET; `macros/hunt.py` `attack_mode`/`follow_on`/`Sweep`; `routes/progress.py` `done`
  (fight ⇐ `facts.dead`); `routes/catalog/act4.py` (the Diablo script).
- Related history: plan.md:1553 (attack mode does not move), plan.md:2008 (three seek steps,
  nothing came), plan.md:2258 (22 s in run mode), test_route.py:412 (the swallow as a test).
