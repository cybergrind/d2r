# Combat macro architecture

Current boundaries checked against code on **2026-10-13**. Start with
[the framework guide](README.md) for terminology and the code map.

## Runtime and ownership

The service injects `BUILDS` and `FALLBACK` from `builds/` into `MacroRunner`.
A run chooses its build on its first observation containing a player. Character
layers precede the general build; the generic fallback has movement and no attack.
`macros/` and `combat/` provide the framework; specific attacks, Warlock skill
logic, movement and buff rows live in `builds/`. Known remnants of build tuning
are tracked by `tests/inventory_tracking/builds/test_ratchet.py`.

The runner serializes requests with one working run and a priority/expiry queue.
Steps can pause attack mode, which resumes afterward. `Hunter` coordinates the
fight, sweep, player intervention, buffs and movement. `Run` carries observations,
clock, cancellation and callbacks; `Actuator` guards keyboard/mouse delivery.

## Decisions and execution

- Attack: `Attack.sees`, `aim` and `dealt` supply the build's combat model.
  The shared controller handles aim ownership and held-input health.
- Movement: `MoveFacts` and `Intent` feed the first applicable `MovementSet`.
  It returns `Step` or an explicit `NoWay`; `Travel` executes and observes the result.
- Position: `combat/stance.py` scores places using the supplied attack and available
  jumps, rejects unsuitable landings and supports escape from a crowd. Some timing
  and distance constants still reflect Echoing Strike; this is not a complete
  threat-based survival model.
- Buffs: build rows and custom casters use the shared executor. The plan's complete
  weapon-grouping and tactic-driven opening behavior is not implied by the contracts.
- Routes: level progress supplies stages for individual presses. The proposed goal
  queue and full/middle leash system are not implemented by the press queue.

## Potions

`macros/drinking.py` is active in `Hunter.sense`. It reads life history and belt/nearby
supply, asks the pure judgement in `combat/survival.py`, and delivers a guarded belt
key. `BuildSettings.drink` supplies its settings. Belt depletion is observed so
potions used by the player or OSD also affect its drink timing.

`make osd` remains an independent process and potion actor. It does not receive a
shared reservation from macro drinking. The old statement that macros only read
potions and never drink is superseded. Consult code/configuration for current
thresholds rather than copying numbers from incident notes.

## Planned behavior and evidence

The remaining staged work is in [framework-plan.md](framework-plan.md); use its
[short status entry](framework-plan.digest.md) first. Stage 4 behavior changes
were authorized on 2026-10-12 and are partially implemented. Tactic hooks, goal
arbitration/leashes, threat-based safety and swap/buff extensions must be checked
against their stage and current callers before treating them as live features.

The original numbered design sections, alternatives and user rulings remain in
[architecture-history.md](architecture-history.md). Existing code comments citing
old section numbers refer to that record. In particular:

- [Framework/build boundary](architecture-history.md#40-the-frame-a-framework-that-names-no-skill-and-builds-that-fill-it)
- [Buff design](architecture-history.md#42-a-battleprofile-who-the-character-is-read-once-per-game)
- [Movement design](architecture-history.md#43-one-navigator-many-movement-modes)
- [Safety design and successive potion rulings](architecture-history.md#44-safety-as-a-first-class-decision-the-survive--cleardanger-tiers)
- [Goal design](architecture-history.md#45-goals-a-queue-of-objectives-above-the-queue-of-presses)
- [Test design and dated calibration](architecture-history.md#6-tests-the-harness-comes-before-the-framework)

Recorded battle replays, golden decisions and the closed-loop arena answer different
questions. Model calibration and distributions across seeds/scenes constrain arena
claims; a passing replay is not live validation. Read the relevant incident in
[plan.md](plan.md) rather than loading the full session history.
