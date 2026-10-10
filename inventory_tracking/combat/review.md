# Combat simulator — code and plan review (2026-10-10)

Scope: `combat/plan.md`, `combat/sim/engine.py`, `combat/sim/situation.py`, the mechanics
modules they depend on (`echoing_strike.py`, `hits.py`, `validate.py`), `combat/__main__.py`
and `tests/inventory_tracking/combat/`. Verified by running the tests (21 pass) and
`combat simulate` on take 20261009T210919Z-108 (2.7 s; gate numbers match the plan's latest
table).

## Bug: return-leg blades home on the wrong player position

`sim/engine.py` passes `situation.player_at` straight into `cast()`:

```python
for blade, path in enumerate(cast(origin, focal, situation.player_at)):
```

`cast()` (mechanics/echoing_strike.py) calls `player_at(k)` with `k` the blade's **path index**
(0-37), but `Situation.player_at` expects an **absolute take frame**. Both other call sites
wrap it correctly — `validate.py` and `hits.py` use `lambda k: player_at(n + k)`; the engine
does not. Every cast's return leg therefore homes toward the player's position at frames
~20-37 of the take (the situation start) instead of at cast frame + k.

Confirmed empirically: player stands at x=0, moves to x=1000 at frame 100, casts at frame 150
at a monster beside him — the current code produces **zero** return-leg contacts; with the
wrap, all five blades re-hit on the way back. Return-leg contacts are ~1/3 of all contacts in
the calibration and the player runs ~30% of the time, so the plan's gate numbers (damage ratio
0.85-0.89) were computed with return legs partially misplaced; they should move upward once
fixed. Fix:

```python
for blade, path in enumerate(cast(origin, focal, lambda k, f=frame: situation.player_at(f + k))):
```

The tests miss it because every test situation has a stationary player
(`dict.fromkeys(..., origin)`). Add a moving-player test asserting return-leg contacts land
near the player's *current* position. Re-run the gate before building stage 5 baselines on the
current numbers.

## Code notes (minor)

- `engine.py` `DUPLICATE = 0.1` is hardcoded to five blades; the tables say the share is
  `(100/count)/2`, i.e. `1/(2*BLADES)`. Derive it from `echoing_strike.BLADES` so a Mirrored
  Blades level change does not silently stale it.
- `engine.py` `hurt()`: Health Link propagates **overkill** — the killing blow shares its full
  damage through the link, not just the remainder of the victim's life. Consistent as a
  modelling choice, but worth a dated note since linked damage is already the largest single
  term.
- `engine.py` `gate()`: kill-order concordance compares `recorded <` with `simulated <=`; ties
  in simulated deaths count as agreeing with either recorded order. Symmetric `<`/`<` would be
  cleaner.
- `situation.py`: `life_first` is dead code (written once, only copied into
  `track.life_at_start` in the same block).
- `situation.py`: an unknown monster type gives `points = 0`, so `alive()` is False from frame
  one — the monster can never be hit, damaged or killed, silently. Fine for Chaos Sanctuary
  (all rows present); elsewhere a missing monstats row would vanish a monster without a trace.
  Consider a default-points fallback or a warning in `describe()`.
- `situation.cut(..., area=108)`: the area is hardcoded; the take's manifest carries it.
- No test covers companion damage being shared through Health Link (the
  `bag is not outcome.linked_damage` path for `companion_damage`) — intended per the engine
  docstring, untested.
- Performance is a non-issue at this scale (2.7 s per take). If policies later call
  `player_at` per frame, replace the linear `known = [n for n in self.player if n <= frame]`
  scan with `bisect` over sorted keys.

## Plan notes

The methodology is sound: dated numbers throughout, calibration before tuning, "where the
tables and the recording disagree the recording wins", and honest gate reporting (the
kill-time bound failing on take 212147 is stated, not hidden).

1. **Stale module layout.** The plan's "Module layout" section still lists `sim/world.py`,
   `sim/monsters.py`, `sim/player.py`, `sim/score.py`, `mechanics/hit.py`,
   `mechanics/damage.py`. Reality is `sim/situation.py` + `sim/engine.py` (score/gate live in
   the engine) and `mechanics/hits.py`. Update it so stage 5 starts from the truth.
2. **The stage-4 gate criterion needs rewording, not just more model.** "Kill times within
   20%" is structurally capped by open-loop replay: a monster whose recorded path ends at its
   recorded death can never be killed later in sim, and `kills_only_recorded` is 108/192 on
   210919 even at damage ratio 0.85. `life_explained_at_recorded_kill` is the right metric
   under open loop; promote it into the formal success criteria (median 1.0, mean >= 0.8, say)
   and demote kill-count matching to a diagnostic.
3. **Policy metric.** `score()`'s `damage_per_second` includes companion damage, which is
   policy-independent; for stage 5 A/B comparisons the discriminating terms are blade + linked
   (the link amplifies blade placement). The fields are all in the score — name which one the
   stage-5 "20% above baseline" bar applies to before tuning starts.
4. **Reproducibility.** The radius/share sweep table in the plan came from ad-hoc runs;
   `combat simulate` exposes no `--radius/--share` flags, so those rows are not re-runnable.
   Cheap to add, and it makes the next calibration pass (fitting link count/share to Summon
   Defiler's real level) verifiable.
5. **Open items are the right ones.** Hex Purge's explosion trigger and fitting link
   count/share to the real Summon Defiler level are correctly identified as the remaining
   damage gap (12-16% unexplained drops, half within 10 units of a kill in the previous twelve
   frames, fits the explosion-on-death hypothesis).

## Verdict

The plan is in good shape and the code matches it closely, but fix the `player_at`
frame-index bug and re-run the gate before building on the current damage-ratio numbers —
they should move upward, and stage 5's baseline should be measured against the corrected
simulator.
