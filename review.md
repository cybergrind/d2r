# Combat, attack control, and simulator review

Reviewed 2026-10-10 against `034f02e` and the current working tree, including the uncommitted hunt, runner, teleport, and pickup changes. Earlier context includes `90dad18` and `8eb158b`. This is a review, not an implementation change.

The most useful next step is to make the executed attack controller replayable and give scheduling, input ownership, and measurement explicit contracts. Sharing the aiming function was a useful improvement, but most of the behavior behind the recent usability problems still lives outside that shared boundary. Fixing measurement and lifecycle defects should precede further policy tuning.

Evidence includes code, tests, and the dated host observations in [the combat plan](inventory_tracking/combat/plan.md) and [the macro plan](inventory_tracking/macros/plan.md). GitHub issue retrieval failed with HTTP 401; this report does not claim to cover remote issues. No live game actions were performed. The existing deletion of `inventory_tracking/combat/review.md` was left intact.

## Findings, in priority order

### 1. P1 — Runner cancellation needs a lifecycle model: shutdown can restart attack mode

**Confirmed defect.** [runner.py](inventory_tracking/macros/runner.py), `close` at line 171 and `_guarded` at line 182.

`close()` sets the current run's cancellation event and joins its thread. It does not clear `attack_mode` or `pending`, or establish a terminal shutdown state. When a seek step ends because of that cancellation, `_guarded()` reaches its continuation logic and starts `ATTACK` with a new, unset cancellation event. A pending action can similarly survive shutdown.

A deterministic probe using injected execution and thread events produced:

```text
close during seek: attack resumed = True
routines = ['hunt elites', 'hunt any']
new cancellation set = False
```

The broader architecture encourages this: `working`, `routine`, `again`, `pending`, `attack_mode`, and `generation` are mutated by both the request thread and worker. `generation` protects only the final HUD clear. Publishing `working = False` before deciding the continuation also creates an interleaving where a new request and the old worker can both start successors; that race is a source-level risk, not a reproduced host failure.

**Change:** Give one scheduler ownership of transitions. Represent stop, pause for a step, completion, failure, and shutdown as distinct outcomes. Make shutdown terminal, clear continuations, and join the worker that owns execution. A lock around the transition plus a single worker/event queue is sufficient; a general workflow framework is unnecessary. Stop using the message text `Abort('cancelled')` as the pause protocol between `Hunter.step_aside()` and the runner.

**Verification:** Event-controlled tests for close during seek, close with pickup pending, and request arriving at worker completion. Assert that no successor starts after shutdown and at most one executor owns input. Existing runner tests cover the ordinary transitions, but not these boundaries.

### 2. P1 — The simulator scores an aim policy, not the controller used in the game

**Confirmed architectural gap.** [hunt.py](inventory_tracking/macros/hunt.py), `choose`/`fight`/`aim_in_view` at lines 530, 547, 697; [sim/engine.py](inventory_tracking/combat/sim/engine.py), lines 220–244; [sim/input.py](inventory_tracking/combat/sim/input.py), `casts_from_presses`.

The simulator asks the policy at free frames and schedules a cast directly. The live controller additionally:

- Falls back to an elite/nearest target when the policy returns `None`.
- Changes an off-screen focal point before aiming; convergence distance affects blade geometry.
- Holds and re-taps inputs, throttles decisions, waits for pointer rest, and yields to clicks.
- Replays swallowed movement clicks, casts marks/sigils, and interrupts fights for weapon swaps.

None of those controller transitions pass through `casts_from_presses` during policy comparison. Simulated marks are replayed from the recording rather than selected by the live rotation. Even the observation boundary leaks future evidence: the current policy receives `blocked_at(frame + BIRTH_LAG)` rather than the doors known at the decision frame. Future recorded motion is appropriate for an open-loop environment; future door state is not an observation the live policy has.

This connects directly to the local issues: swallowed clicks at 17:45–17:53, skill-key interruptions at 18:01/18:05, unnecessary swaps at 18:14, and near-equal lines making the pointer swing. Improving the line sweep alone cannot establish that those problems improved. The simulator's `yield` score also cannot prove movement fluency merely because it starts no cast during an already-recorded run.

**Change:** Extract an incremental attack controller: observation + player input intents + clock + controller state → requested actions and next state. Put fallback choice, feasible aiming, target retention, rotation, and yielding there. Live and replay adapters should execute the same hold/release/aim/action sequence. Keep monster motion explicitly open loop initially. Use the existing blade mechanics to evaluate emitted casts.

**Verification:** Replay traces for click during mark, held strike plus user skill, off-screen focal, target switching, and swap interrupted by movement. Compare action traces across live and simulated adapters, then measure movement-intent delay as well as damage. Keep `NearestPolicy` as an explicitly historical comparison, not a purported implementation of today's controller.

### 3. P1 — Damage accounting rewards overkill while policy valuation caps it

**Confirmed defect in the claimed effective-damage metric.** [sim/engine.py](inventory_tracking/combat/sim/engine.py), `hurt` at line 186 and `score` at line 274; [sim/policy.py](inventory_tracking/combat/sim/policy.py), `policy_score` at line 54; [policy.py](inventory_tracking/combat/policy.py), `virtual_cast` at line 91.

`hurt()` adds the full blow to its damage bucket and `dealt_by` before reducing life. `policy_score()` sums those buckets as placement points. By contrast, `virtual_cast()` caps direct damage at remaining life. A synthetic target with 100 HP hit for 1,000 produced:

```text
simulator damage_points = 1000
virtual_cast value = 100
```

Consequently, a policy can receive extra score for a larger finishing blow without removing more life. The calibration ratio also compares simulated raw blows with recorded life loss. Health Link's documented choice to share raw damage does not require reporting raw damage as effective damage.

**Change:** Separate attempted damage, effective life removed, and damage used to calculate linked propagation. Return a small damage result from a shared resolver and use effective loss for the advertised DPS/placement metrics. Keep raw damage available as a diagnostic. Revisit calibration thresholds after the metric changes rather than silently updating pinned totals.

**Verification:** Low-life finishing hits, marked finishing hits, and linked/explosion chains. Effective loss must not exceed available life; raw link propagation must still follow the selected model. Add an example where only overkill differs between candidates and their effective scores are equal.

### 4. P1 — Holdout classification loses the recording's identity on trim or rename

**Confirmed defect, currently asserted by a test.** [scoreboard.py](inventory_tracking/combat/scoreboard.py), `build` at line 87; [takes.py](inventory_tracking/combat/takes.py), `trim` at line 206; [test_scoreboard.py](tests/inventory_tracking/combat/test_scoreboard.py), line 61.

Classification uses `path.name in fit_takes()`. The checked-in `chaos-manual` fixture identifies its source as `20261009T212147Z-108`, which is in `data/damage.json`'s fit list, but the scoreboard labels it `holdout`. The test explicitly expects both fixtures to be held out. Renaming a take has the same effect. Trimming a trim replaces the immediate parent name and can lose the original identity entirely.

**Change:** Give a take an immutable recording ID and preserve root provenance through every trim. Classify by that ID. Store the model/configuration identity and evaluation mode with each scoreboard so changes are attributable. Missing provenance should be unknown, not automatically held out.

**Verification:** Original, renamed, trimmed, and twice-trimmed versions retain the same calibration membership. Correct the existing fixture classification test; retain its useful checks for formatting and aggregation.

### 5. P2 — Live and offline metrics disagree about what a kill is

**Confirmed measurement mismatch.** [score.py](inventory_tracking/combat/score.py), `LiveScore.note` at line 32; [record.py](inventory_tracking/combat/record.py), `derive` at line 170; [compare.py](inventory_tracking/combat/compare.py), `row` at line 61.

The recorder distinguishes explicit dead modes (`kill`) from disappearance (`gone`). The live scorer treats any previously-near hostile that disappears as killed and credits its remaining life. Teleporting away or changing level between two reads can therefore add a kill without death evidence. A direct two-sample probe, with no death supplied, credited one kill and 6,260 points. When it was the final target, it credited zero combat seconds for that interval because the denominator uses only the new snapshot.

The scorer stores unit IDs without game/area identity. `GAP` suppresses long interruptions but does not distinguish a quick transition from a kill. The test `test_life_drops_and_kills_within_reach_are_scored_per_combat_second` currently makes disappearance the required behavior.

**Change:** Share a combat-event/metric reducer between recorded analysis and the HUD. Feed explicit deaths, observed life deltas, disappearance, and session transitions separately. If disappearance must remain an estimate, label and count it separately. Define interval attribution once, including the interval in which the last target dies. Centralize the repeated combat-reach and movement-mode definitions after that semantic decision.

**Verification:** Death versus despawn, teleport, same unit ID in a new game, final-target death, and temporary missing reads. Update the misleading kill assertion rather than preserving it as a regression requirement.

### 6. P2 — Replay needs a versioned timeline and explicit segment boundaries

**Confirmed defects plus an acknowledged format gap.** [record.py](inventory_tracking/combat/record.py), lines 118–164 and `run` near line 311; [takes.py](inventory_tracking/combat/takes.py), positional row decoders; [sim/situation.py](inventory_tracking/combat/sim/situation.py), `seconds` and `cut`; [combat/__main__.py](inventory_tracking/combat/__main__.py), `window`.

The recorder increments `n` once per successful sample and records lateness separately. The simulator interprets every adjacent `n` as one 25 Hz game frame. A two-sample probe separated by one real second produced `Take.seconds = 1.0` but `Situation.seconds = 0.04`. Missing/late samples therefore alter simulated cadence, travel time, and denominators. The reader also accepts other recorder rates without changing this assumption.

`--area` finds the first and last matching frame; `cut(area=...)` labels the situation but does not filter intervening frames. A synthetic sequence of areas `[108, 35, 108]` retained all three frames when requesting area 108. Applying one map and monster-level model to that interval is invalid. Current single-level recording reduces exposure, but the CLI explicitly supports older mixed-level takes.

Rows have no schema version despite historical mana-column meaning changes recorded in the plan. Trims keep original summary counts and do not reconstruct initial held-input state, so a button held before the cut can be absent from the replay's press history.

**Change:** Decode recordings into a versioned, validated timeline with source timestamps, declared rate, session/area segments, field capabilities, and initial input state. Make gaps explicit: resample under a documented rule or reject unsuitable segments. Select contiguous area visits rather than enclosing unrelated visits. Preserve legacy fixtures through a named decoder.

**Verification:** Late and missing samples, non-default recording rate, A→B→A visits, a cut beginning with the strike already held, and old mana schemas. Preserve existing trajectory fixtures as independent evidence.

### 7. P2 — Input yielding is implemented by intercepting sleeps; tests cannot establish its latency

**Architectural weakness with a concrete unguarded path.** [hunt.py](inventory_tracking/macros/hunt.py), `attack_mode`, `sense`, `nap`, `serve_move`, `fight`; [actuator.py](inventory_tracking/macros/actuator.py), `hold`; [fakes.py](tests/inventory_tracking/macros/fakes.py), `Clock`, `Game.read`, `Game.strike`.

Attack mode replaces `run.pace.sleep` with a wrapper that samples clicks. This couples input responsiveness to where unrelated helpers happen to sleep. Time spent in policy evaluation or memory reads is outside that observation loop. The retap callback releases, sleeps, and presses again without calling `guard()` or checking cancellation; a click detected by the sleep wrapper does not itself prevent that press. In `fight`, retap also occurs before the next explicit movement check.

The fake clock advances only through requested sleeps. Its game starts casts as a side effect of `read()`, and its strike model kills the nearest unit to a line rather than evaluating blades. Thus the test asserting that consecutive `sense()` calls are less than 50 ms apart cannot measure real computation/read latency. Changing read frequency can also change fake gameplay. These fakes remain useful for workflow tests, but are not evidence of real-time fluency or simulator/live equivalence.

**Change:** Make input observation and cancellation a first-class dependency, and make all outgoing presses pass through one ownership/guard boundary. Use explicit controller ticks or interruptible waits instead of mutating `Pace.sleep`. Advance the test world with time/events independently of reads. Keep small scripted fakes for orchestration and use recorded input traces plus the mechanics engine for controller behavior.

**Verification:** Click, focus loss, and cancellation during retap; slow observation/policy evaluation; release on every exit path. Assert emitted actions and movement latency, not internal polling-call counts or exact HUD strings.

### 8. P2 — Planning and execution still use different viewport geometry

**Confirmed architectural mismatch; no new host reproduction claimed.** [teleport.py](inventory_tracking/macros/teleport.py), `VIEW_ASPECT`, `hop_in_view`, `Way`, and `landing`; [hunt.py](inventory_tracking/macros/hunt.py), `aim_in_view`.

The recent fix for 22 repeated failed seek steps correctly changed the potential to use a directed, view-shaped hop graph. However, `Way` still plans with a fixed `16 / 9` aspect while landing evaluates the actual window. The graph/cache does not include viewport geometry. Resizing the window can recreate a disagreement between an apparently reachable target and executable hops. Combat separately shortens an off-screen focal after scoring it.

**Change:** Introduce an immutable viewport/projection value used by path expansion, landing, combat aim feasibility, and their cache keys. Separate ground, body, and click-target offsets explicitly. Retain the directed graph; the missing improvement is sharing its actual execution constraints.

**Verification:** The same obstacle layout under wide, narrow, and resized windows; every planned hop must have an executable landing under the same viewport. Retain the new host-derived gap regression. Re-score the actual reachable combat focal rather than silently replacing the selected focal.

## Cleanup that would make the next changes easier

| Location | Concrete cleanup | What to preserve |
| --- | --- | --- |
| `macros/routines.py:332`, `runner.py:264`, `world.py:539` | Move the whole-data `hover_candidates` scan behind an explicit probe/debug option. It remains wired into every Consume attempt, even though pickup now uses the small `hovered()` read. This is active diagnostic baggage, not dead code. | The research probe and crowd checks. The item hover discovery does not yet prove all monster/Consume semantics. |
| `combat/sim/engine.py:113–114` and `test_scoreboard.py:164` | Separate `mortal=False` and `link_overkill` experiments from the default evaluation contract, or retire them after preserving the experiment recipe. `mortal=False` is used by a test but no production caller; `link_overkill=False` has no checked-in caller found. | The rationale in `combat/plan.md:944–964`: recorded-lifetime scoring was intentionally tried and rejected. Its absence from the default gate is not a missing implementation. |
| `combat/policy.py` module description | Correct the claim that `NearestPolicy` is literally the live fallback: `Hunter.choose` implements another fallback and uses the live reachable set, while the historical policy has a 20-unit reach. | A named historical baseline for comparisons. Do not delete it merely because it is no longer the live controller. |
| `macros/runner.py:197`, `test_runner.py:300` | Replace obsolete “the player attacked” stop explanations. Current attack mode is intended to survive the player's own attacks. The exception-path test can use a current failure reason. | Coverage that a genuine terminal failure turns attack mode off. |
| `combat/sim/policy.py:4`, `combat/plan.md:215,581` | Repair references to the deleted local `combat/review.md`, or identify them explicitly as historical references available through git. | The decisions and experiments summarized in the plan; do not restore the deleted review implicitly. |
| `combat/plan.md`, `macros/plan.md` | Put a short current contract and unresolved-issue list before the dated history. Label original stages and superseded behavior as historical. The opening “missiles … are not read yet,” earlier toggle rules, per-monster bursts, and old pickup fallback should not look current. | Dated measurements, host evidence, and why rejected approaches failed. Archive narrative instead of erasing evidence. |
| `test_scoreboard.py:61`, `test_score.py:18` | Replace assertions that codify false holdout labeling and disappearance-as-death. These are the clearest tests to change, rather than simply adding tests beside them. | Fixture replay, aggregation, rolling-window, and explicit-death coverage. |
| `test_policy.py`, `test_shared_policy.py`, `test_hunt.py` | Rename/split by responsibility: input cadence, pure aiming, simulator scheduling, live adapter. Remove duplicate setup where useful. A similar “line through two monsters” example at each layer is not enough evidence to delete a test. | The distinct policy decision, scheduling, and executed-action contracts. Prefer one cross-adapter trace test when retiring integration cases. |

The previous cleanup already removed `hunt.ready_to_act`, `sim/situation.kills_by_type`, and `mechanics/tables.monster_name`. They are not outstanding work. The schema gap, damage-roll spread, same-level manual comparison, and Consume ordering question are still recorded as unresolved; this review does not turn historical proposals into current requirements.

## Suggested implementation sequence

1. Fix terminal shutdown and add deterministic lifecycle coverage. This can ship independently.
2. Repair recording identity, effective-damage accounting, and event semantics. Record metric-version changes and inspect score changes rather than preserving old numerical snapshots blindly.
3. Establish timeline/segment decoding and a viewport contract. These are inputs to meaningful replay.
4. Extract the attack controller incrementally, starting with hold/release and movement yielding. Run the same controller against recorded inputs and the live adapter before moving rotation and swaps.
5. Remove or isolate research-only paths and obsolete assertions, and condense the current documentation. Only then tune target retention, aim weighting, swap thresholds, or further timing constants.

Do not replace everything at once: retain the blade model, checked-in trajectory recordings, shared wall/link helpers, and ordinary workflow tests. The useful boundary change is around decisions, execution, and evidence.

## Validation performed

```sh
uv run --offline pytest tests/inventory_tracking/combat tests/inventory_tracking/macros tests/inventory_tracking/input/test_compositor.py -q
```

Result: **293 passed in 10.48 s**. This was the focused suite, not the entire repository suite.

Additional non-persistent Python probes used existing constructors/fixtures and injected execution to confirm shutdown restart, false holdout membership, raw-overkill scoring, disappearance-as-kill, compressed recording gaps, and mixed-area retention. They performed no process attachment or game input and wrote no scoreboards. The timing/focus and request-completion race risks above are distinguished from these reproduced defects. Only this review document was added.
