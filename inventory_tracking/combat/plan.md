# Combat: recorded play, replay, and a scored auto-attack — plan (2026-10-09)

## Current contract (2026-10-10)

**What runs today**

- Recorder (`combat/record.py`): inside `serve`, samples the game about 25 times a second while the
  character is in a recorded area (Chaos Sanctuary, the Catacombs). One take per stay in a level.
- Takes (`combat/takes.py`): the one reader of the take files; a trim keeps its source recording.
- Mechanics (`combat/mechanics/`, `combat/data/damage.json`): blade flight, convergence and walls
  checked against recorded blades; points per contact, companions, Health Link, Hex Purge, Death
  Mark and mana.
- Simulator (`combat/sim/`): replays a take with monsters open loop on their recorded paths; the
  policy under test picks the casts. Its frames are game ticks, 25 a second, from the samples'
  timestamps (`combat/timeline.py`): a late sample takes the ticks it was late by with it. The
  `live` candidate is the aim the game's fight runs; the rest of the fight (holds, swaps, marks
  chosen live) is not replayed.
- Controller (`combat/controller.py`): the fight's decisions apart from the game: where to cast
  (`aim_choice`: the policy's line, else straight at what is in reach, always a focal point the
  window lets the pointer reach), whose the pointer is (`Aim`), the held strike input (`CastWatch`)
  and the move the player asked for (`serve`). The game's fight and the simulator both ask it.
- Shared policy (`combat/policy.py`): one decision for the simulator and the game. `LinePolicy`
  sweeps lines through the live hostiles and yields while the player moves. `NearestPolicy` is only
  the historical baseline.
- Live attack and seek (`macros/hunt.py`): attack mode holds one strike input through a fight and
  keeps the pointer on the line the controller picks. The player's left button or a walk ends the
  fight at once; a key of theirs does not (the strike stays held and the macro's own aims wait).
  Only the mode's own toggle or the macro request ends the mode. The seek step goes toward the
  nearest elite and leaves the mode on.
- Live score (`combat/score.py`): points lost per combat second and kills per minute over the last
  minute, on the HUD card. A kill is a hostile now among the dead; one that only vanishes is counted
  apart and is worth nothing.
- Scoreboard (`combat/scoreboard.py`): every take through the gate and the policies, in one file.

**How it is measured**

- Command: `uv run python -m inventory_tracking.combat gate <takes directory>`. A take passes when,
  on the blades' side (monsters no companion came within 8 units of, at least five of them): the
  life explained by each recorded kill has median 1.0 and mean at least 0.8; the simulated life
  taken is within 15% of the recorded damage; the life-curve bias is within 0.1 of a life
  (`sim/engine.py`, `verdict`).
- Takes are "fit" (three Chaos Sanctuary takes, `data/damage.json` `fit_takes`), "held out", or
  "unknown" without a recording identity.
- Latest (2026-10-10 late night, frames as game ticks): 23 of 63 takes pass (24 before the ticks,
  29 before the damage moved to life taken). Of the three fit Chaos takes one passes; their damage
  ratios are 0.81, 0.86 and 0.83. Gain over the recorded casts on passing takes: `yield` median
  +19.1% (+5.0 to +42.8%), `live` (what the game's fight aims) median +19.0%.
- Live (2026-10-10 13:57-13:59 UTC, `combat compare`, held-strike fight): Catacombs 1 stood with a
  target 29% of the frames (59% in the earlier macro takes), 3644 points per combat second (2608)
  and 79 kills a minute (58). The player's Chaos play stands 12-21%. The stage 6 bar (ten sessions
  a side in one level) is not met: no level has both sides yet.

**Unresolved**

- The simulator scores the fight's aim (the sweep, the fallback target, the window), not the rest
  of the fight: holds and retaps, the weapon swap, marks and sigils chosen live and yielding to
  clicks have traces of their own (`tests/.../combat/test_controller.py`) but are not replayed
  against recorded input. Simulated marks are still the recorded ones (review.md finding 2).
- Takes: the pointer a recorded cast took is still looked up by sample number, not by tick; a
  trim keeps the summary counts of the take it was cut from; rows of schema 1 with vitals read
  from the wrong stats are named (`takes.SCHEMAS`), not converted (review.md finding 6).
- The fakes the hunt's tests run on advance the clock only through sleeps and start casts as a
  side effect of a read, so they show the order of actions, not how long a memory read or a
  policy decision keeps a click waiting (review.md finding 7).
- Damage per contact is a mean standing in for a roll; the per-hit damage still has to be refitted
  against the life taken (night note).
- The Catacombs blades run ahead of the record by about 0.10 of a life, the companions by 0.2-0.3
  (evening gate note).
- Mana does not limit casting in the takes; its regeneration is the classic assumption, and the
  limit is off by default.
- Assist mode (the policy never moves the pointer) is not built; whether takeover with yield feels
  right in hand is the user's verdict, not yet given.

Everything below is the dated history: stages as first planned, then notes in order. Later notes supersede earlier ones.

Goal (user, 2026-10-09 night): an auto-attack that is measurably better than the player's own
Echoing Strike play and never gets in the way of moving. The way there is data: record how the
player really plays, rebuild the situations in a simulator whose Echoing Strike behaves like the
game's, score any attack policy in it by effective damage per second, and only then tune the
policy, first in the simulator, then in the game against the manual baseline.

The code lives in a new sub-module `inventory_tracking/combat/`; `macros/hunt.py` becomes a thin
client of its policy at the end. Red/green TDD throughout (development.md); every number here is
a dated snapshot; every stage ends with a dated note in this file.

## What exists and is reused

*Superseded 2026-10-10 in part: missiles are read now, from unit slots 3 and 9 (see the first takes below).*

- Memory reader (`macros/world.py`): the local player (position, mode, left/right skill, area),
  monsters (unit id, type, mode, position, owner, flags, alignment, life/max life) and items, from
  the unit table the service attached to (`table + <unit type> * 1024`; monsters are type 1,
  items type 4). Missiles are type 3 in the same table and are not read yet.
- Level maps (`levels/`): every Room2 of the level with walkable sub-tile grids (`Ground`), the
  route and the way potentials; the sight module (`macros/sight.py`) for lines of sight.
- Terror tracker (`terror/tracker.py`): kills, packs, leaders, remembered positions; the installed
  game's excel tables read by `terror/build_threats.py` (`data/global/excel/*.txt`, with
  monstats, skills, monumod already parsed), d2data JSON under `third-parties/d2data/json/`
  (missiles.json, skills.json, monstats.json) and D2MOO's reconstructed engine source for the
  classic missile and hit algorithms.
- Input (`input/keyboard.py`, `macros/actuator.py`): XTest keys, buttons and pointer; XQueryKeymap
  for keys down; the pointer position; `Actuator.hold` for a held skill input.
- The service loop and `runs/alt-d/<run>/` for per-run logs; `probe.py` style research probes.

## Stage 1 — Recorder: takes of real play

What: `combat/record.py` samples the game at the engine's rate (25 frames per second; measure
the cost of one sample first and settle for 12.5 Hz if 25 is not sustainable) and writes a
*take* per game or per hotkey start/stop under `runs/combat/<timestamp>/`:

- `frames.jsonl` (or a compact binary with a JSON index if JSONL is too large): per frame the
  monotonic clock, the player (position, mode, area, left/right skill, life, mana, the states on
  them), every monster in memory (unit id, txt id, mode, position, life, flags; level, defence and
  resistances once per unit from its stat list), every **missile** (unit id, owner, missile/skill
  id, position, per-frame velocity, age), and the player's **input**: pointer position in window
  fractions, mouse button mask (XQueryPointer), keys down (XQueryKeymap), and whether the macro
  itself was acting (so manual and macro play can be told apart in the same take).
- `manifest.json`: character, area, difficulty, the level map reference (the rooms and grids of
  the level as the guide saw them), gear and skill snapshot (skill levels from the player's
  skill list, cast rate from the measured frames per cast), game build, service version.
- `events.jsonl` derived while recording: cast start (player mode enters ACTING), cast end, hit
  (a monster's life drops: which missile was nearest and when), kill (mode to 0/12), the
  player's move intents (left button down on the ground, teleport key).

Research first: the missile unit record. Probe approach as for every layout here: cast Echoing
Strike with no monster around, dump the type 3 bucket chain, diff consecutive frames, find the
position path pointer (as for monsters), the owner unit id, the skill id, and the velocity. Cross
check with d2go/MapAssist unit structs (they describe older builds; validate on ours).

Success criteria:
- A ten minute take at the chosen rate drops under 2% of frames and costs under 20% of one core.
- Missiles appear in the frames with positions that advance smoothly; the blades of one cast are
  attributable to it (same owner, spawned within one frame).
- Kills and hits in `events.jsonl` match the terror tracker's kill count for the take.
- A `combat replay <take>` command plays a take back on the HUD canvas (or prints a timeline) so a
  take can be eyeballed for sanity.

Notes: online play is server authoritative; the client shows positions with latency, so hits and
life drops lag the missile contact by a variable amount, which the analysis must tolerate (a hit
window, not a frame). Recording must not touch the game: reads only. Keep takes out of git
(`runs/` is already ignored); check in a few trimmed takes (a few seconds each) as test fixtures.

## Stage 2 — Analysis: how the player really plays

What: `combat/analysis.py` turns takes into numbers and a report (markdown or an HTML page as
the guides are):

- Cast rate: frames between consecutive cast starts while the button is held; per gear snapshot.
- Aim geometry per cast: distance to the targeted monster, the aim point relative to it, along
  the character-monster line and across it, in world units. This gives the real "aim beyond"
  distance the player uses, and how much across-line error still hits.
- Hits per cast: how many blades hit, how many monsters per cast, damage per hit by monster type
  (life deltas), misses.
- Movement: fraction of combat time moving, move/cast interleaving (how long after a stop the
  first cast comes, how long casts pause moving), teleport use, distance kept from melee monsters.
- Rotation: when Sigil: Lethargy and Death Mark are cast relative to engagements; time from
  engagement to first cast.
- Outcome: time to kill per monster type and level, kills per minute, **effective DPS** = damage
  dealt to hostiles per second of combat time, where combat time is every second with a hostile
  within reach (the same definition the simulator and the live scorer use), damage taken.

Success criteria:
- At least ten takes of normal farming in two zones (Chaos Sanctuary and one Terror Zone), each
  five minutes or more.
- The manual baseline is a number with a spread: effective DPS, kills per minute, time to kill
  for the five most common monster types, with per-take variation shown.
- The aim-beyond and across-line tolerances are read from the data, not guessed; the current
  `AIM_BEYOND` is replaced or confirmed in a dated note.

## Stage 3 — Mechanics: an Echoing Strike that behaves like the game's

What: `combat/mechanics/` with the game tables and the emulation:

- `tables.py`: Echoing Strike, Sigil: Lethargy and Death Mark rows from the installed game's
  skills.txt, missiles.txt and skilldesc (RotW rows: the Warlock is not in d2data); monstats,
  monstats2 (sizes), monlvl and difficulty levels for the monsters' life, defence, resistances
  and sizes at the player's difficulty; the player's skill levels, +skills and damage modifiers
  from the gear snapshot.
- `echoing_strike.py`: the cast as the game does it: blade count, spawn offsets, directions
  toward the aim point and the convergence at it, velocity, range (missiles.txt: 20 frames at
  velocity 24, per the hunt docstring), collision with walls (collide type 3 over the level
  grids), the echo (whether blades return, pierce or hit twice: read from the tables, confirmed
  in recorded missiles), and what each blade does on contact with a monster of a given size.
- `hit.py` and `damage.py`: chance to hit (attack rating against defence, or the skill's own
  rule if it is a cast), damage per blade (skill damage, synergies, +% damage, the element),
  monster resistance and physical reduction, Death Mark and Sigil effects.

Validation against Stage 1 takes, as tests over the fixture takes and as a `combat validate`
report over all takes:
- Trajectories: emulated blade positions per frame against recorded missiles, root mean square
  error per cast.
- Hits: the set of (blade, monster) contacts the emulation predicts against the recorded life
  drops, as precision and recall over casts.
- Damage: predicted damage per hit against observed life deltas by monster type.

Success criteria: trajectories within one world unit over the blades' flight; predicted hits
match recorded hits on at least 90% of casts; mean predicted damage within 10% of observed per
monster type, with the spread (min-max rolls) covering the observed deltas.

Notes: RotW skill functions have no reconstructed source (D2MOO covers the classic game), so the
blade behaviour is inferred from the tables and confirmed by recordings; where the two disagree
the recording wins and the disagreement is a dated note. Expect to iterate here: this stage is
the foundation everything after stands on, and its tests are the regression guard for later
mechanics findings.

## (historical) Stage 4 — Simulator: replayable situations and a score

What: `combat/sim/`:

- A *situation* is a take cut at a time: the level's rooms and grids, the monsters with
  positions, life, modes and stats, the player with position, skills and cast rate, and the
  recorded inputs from that moment on.
- Monster motion: open loop first (monsters move along their recorded paths and die when the
  simulated damage reaches their life; after that they are gone), then a modelled approach AI
  (toward the player at monstats velocity, melee at range) for situations longer than a few
  seconds, chosen per run and labelled in the score.
- The player acts through the same interface the real actuator offers (move the pointer to a
  window fraction, press, hold, release, which key), with the measured input-to-cast latency
  and the cast rate from the manifest; the engine advances 25 frames per second.
- Missiles and hits come from Stage 3.
- `score.py`: effective DPS (the Stage 2 definition), kills per minute, time to clear the
  situation, damage taken (from the recorded or modelled monster attacks), and a movement
  fluency measure for Stage 5: how long the player's recorded move intents were delayed.

Calibration gate before any policy is scored: replay the player's *recorded inputs* through the
simulator and compare with what the take shows.

Success criteria: on the fixture situations the replayed inputs reproduce the kill order, kill
times within 20% and total damage within 15%; a `combat score <situation> <policy>` command
prints the score table; the whole fixture set runs under a minute in tests.

Notes: without the calibration gate every score is fiction; do not tune a policy on a situation
that fails it. Latency online varies by session: keep it a manifest parameter and sweep it.

## Stage 5 — Auto-attack v2: designed in the simulator

What: `combat/policy.py`, a policy that decides per frame from the simulated or live state,
scored in Stage 4 before it touches the game:

- Target and aim: evaluate candidate aim lines (a fan of directions and beyond-distances from
  the character) by the emulated damage of one cast through everything on the line, elites
  weighted; pick the best, not just the nearest monster. The aim-beyond distance comes from the
  Stage 2 data and the Stage 3 convergence.
- Rotation: Sigil: Lethargy and Death Mark when the emulated gain over the next seconds exceeds
  the cast they cost.
- Hold discipline: hold while the line keeps value, release and re-aim when a better line
  appears or the target dies; retap for a once-per-press game stays.
- **Movement coexistence** (the user's main complaint): the game has one pointer. Two modes to
  score and offer:
  - *Assist*: the policy never moves the pointer; it holds the strike input when the player's
    own pointer line scores above a threshold and releases otherwise. Movement stays entirely the
    player's. Expected to be fluent, worth less damage than takeover.
  - *Takeover with yield*: the policy aims and holds only while the player is not moving: no
    left button down, no teleport key, pointer at rest (speed under a threshold for N frames),
    character not in walk/run; the moment a move intent appears it releases and gives the pointer
    back within one frame; it resumes after the move. The thresholds come from the Stage 2
    move/cast interleaving.
  - Both report fluency in the score: the delay added to recorded move intents.

Success criteria: on the Stage 4 situation set, v2 effective DPS at least 20% above the manual
baseline replayed in the same simulator, with damage taken not worse; the move-intent delay of
takeover-with-yield is one frame or less on every fixture; assist adds zero delay by
construction. Tests pin the policy's choices on the fixture situations.

## Stage 6 — Real game, v2 against manual

What: wire the policy into `macros/hunt.py` (the actuator and runner stay), add a live scorer
to the HUD card (effective DPS over the last minute, kills per minute, fluency), record takes
of v2 sessions in the same zones as the manual takes, and compare with the Stage 2 analysis.

Success criteria: over at least ten sessions per side in the same zones, v2 effective DPS and
kills per minute above manual with damage taken not worse, and the user's own verdict on
fluency. Disagreements between simulated and live scores go back to Stage 3 or 4 as
calibration work before more tuning.

## Order and quick wins

1. Stage 1 recorder (missile layout research first), then Stage 2 analysis. These pay back
   immediately: the real aim-beyond distance, the cast rate and the move/cast pattern tune the
   current hunt code before the simulator exists.
2. Stage 3 mechanics with validation on the takes.
3. Stage 4 simulator and its calibration gate.
4. Stage 5 policy, assist mode first (cheapest, fully fluent), then takeover with yield.
5. Stage 6 live comparison.

## Module layout (as built, 2026-10-10 evening; the original sketch is superseded)

```
inventory_tracking/combat/
  plan.md            this file; review.md: an outside review of 2026-10-10 and what it changed (deleted; in git history)
  record.py          sampler, take writer (CombatRecorder in serve)
  takes.py           take format: reading (gzip too), the typed frame rows, summary, timeline, trim
  analysis.py        play metrics and the manual baseline (`combat analyse`)
  policy.py          the decision the simulator and the game share: Observation, LinePolicy, NearestPolicy
  score.py           the live scorer: damage per combat second and kills per minute from world reads
  scoreboard.py      every take through the gate and the policies, one file (`combat gate`)
  compare.py         macro against manual from the takes (`combat compare`)
  data/
    tables.json      the game rows the mechanics key on (mechanics/tables.py builds it)
    damage.json      points per blade contact by monster type, companions, Health Link, Hex Purge, mana, fit_takes
  mechanics/
    tables.py        the bundle and its lookups (monster points by area)
    damage.py        the damage model's numbers read from data/damage.json
    echoing_strike.py  the blades: spawn, convergence, range, return (cast, focal_point, errors)
    validate.py      the emulation's position error against recorded blades (`combat validate`)
    hits.py          contacts and their match to recorded drops (`combat calibrate`)
  sim/
    situation.py     a situation cut from a take: player, monsters, companions, casts, recorded kills and drops
    engine.py        simulate, score, the gate (life explained, damage ratio, life curves), replay (`combat simulate`)
    input.py         presses to casts (`combat inputs`)
    policy.py        the policies through a situation: slots, yield, free, nearest (`combat policy`)
  __main__.py        combat replay | analyse | validate | calibrate | simulate | inputs | policy | gate | compare | trim
macros/hunt.py       the policy's client in the game: one held strike on the policy's line, yielding to the player
tests/inventory_tracking/combat/  mirrors the modules; fixtures/ holds two single casts and two trimmed takes
```

## Risks and open questions

*Superseded 2026-10-10 in part: the missile layout is known now (see 'Second take and the missiles'); the other bullets stand.*

- The missile record layout on our build is unknown; Stage 1 cannot finish without it.
- RotW skill behaviour is not in any reconstructed source; the recordings are the truth.
- Online latency blurs contact and life drop; all matching uses windows and the simulator sweeps
  latency.
- Monster AI in longer situations is modelled, not real; keep situations short where it matters.
- Open for the user: which zones to record first (Chaos Sanctuary and which Terror Zone), and
  whether assist mode (the policy never moves the pointer) is an acceptable answer to fluent
  movement if takeover-with-yield still feels intrusive.

## Stage 1 progress (2026-10-09 night)

*Superseded in part: the host runs that followed (see 'First take' below).*

Zone: Chaos Sanctuary first (user). Written and tested, nothing run on the host yet:

- `combat/record.py`: `CombatRecorder` inside `serve` (config `combat_record`, `combat_areas`
  (108), `combat_rate` 25; flag `--combat-record`), on its own thread with its own memory
  handle and display connection, bound to the game by `poll` once a second. A take opens when
  the character is in a recorded area and closes 3 s after they leave it, or at once when they
  leave the game. Takes land under `inventory_tracking/runs/combat/<UTC time>-<area>/`.
- Per frame: the player (unit, mode, area, position, mouse skills), every monster with its
  life, dead ones included (`monsters(dead=True)`), every missile unit raw (unit id, txt id,
  mode, the u16 pair at 0xC4, the path record hex; the whole 0x160 record once per missile in
  `missiles.jsonl`), the pointer with its button mask (`pointer_state`), the key codes down (the
  manifest names the skill keys, KP_5 and the modifiers), the open panels and whether a macro run
  was acting. Each monster's full stat list goes to `units.jsonl` on first sight. `level.json`
  copies the guide's rooms and grids when it has them for the area.
- Derived events: cast / cast_end (player mode in ACTING), hit (a life drop, with before and
  after), kill (mode 0/12), gone (unloaded alive), button and keys changes, each with `macro`.
- Late frames are counted per frame and in the manifest; a late frame restarts the schedule
  instead of catching up.
- `uv run python -m inventory_tracking.combat replay <take>` prints the summary and a timeline.

Next on the host: one Chaos Sanctuary run with `make serve`, then the take's summary (rate seen,
late frames, missile txt ids, casts, hits) and the missile records for the layout research.

### First take (2026-10-09, 20:18-20:23 UTC, Chaos Sanctuary, manual play)

`runs/combat/20261009T201834Z-108`: 7139 frames over 288.6 s (24.7 Hz, 14 late frames, 0.2%),
240 monsters seen, 237 casts, 1098 hits, 212 kills (44 per minute). Findings, from
`python -m inventory_tracking.combat analyse`:

- **No missiles in slot 3** through 237 casts. MapAssist reads the player's own missiles from the
  "server missile" slot (9) of the same hash table and other units' from slot 3; `missiles()` now
  walks both, and the recorder logs a twelve-slot census every 30 s (the manifest keeps them).
- **Monster life is a 0-128 fraction** of the maximum in the client (every monster shows 128
  max life); damage is in 128ths of a life until monstats gives the points (stage 3). Hits of
  1-7/128 were the common sizes; 128 -> 0 in one hit happened 20 times.
- **Cadence:** the player taps the right button (hold 0.08-0.16 s) every 0.16-0.2 s; the game
  casts every 0.4 s (ten frames; the cast bouts are 0.36 s). 384 presses gave 237 cast
  animations: presses during a cast queue, they do not add casts.
- **Aim:** the hostile nearest the ground under the pointer is 5.5 / 12.5 / 21.1 units away
  (deciles). The aim lies on the character-monster line at -14 / -1.6 / +2.7 units past the
  monster (short of it at the median) and within -3.3 / +4.3 across. The current hunt code's
  STRIKE_REACH of 15 is below the median engagement distance; AIM_BEYOND = 5 is further than
  the player aims (the player's across error is small, so the line matters more than the depth).
- **Hits per press** within 0.6 s: 0 for 76 of 371, 1-3 for 145, 8 or more for 69 (packs on the
  line). First hit 0.0 / 0.16 / 0.44 s after the press.
- **Movement:** run 34% of frames, casting 45%, in bouts of 0.73 s running (0.16-1.74) and
  0.36 s casting: the fluency a policy must keep is a cast slotted between runs under a second.
- **Kills:** first hit to kill 0.04 / 0.84 / 3.6 s; 2.5 lives of damage per combat second
  (seconds with a hostile within 30 units: 200.8 of 288.6). Monster types 310, 362, 306, 312.

Open from this take: the exact cast-to-cast frame count with the button held rather than tapped
(the macro holds), and whether a press during a cast is lost or queued (the game queued here).

### Second take and the missiles (2026-10-09, 20:37-20:42 UTC, Chaos Sanctuary, manual)

`runs/combat/20261009T203733Z-108`: 7417 frames over 302 s (26 late), 289 monsters, 216 casts,
1147 hits, 256 kills (51 per minute), 2.1 lives per combat second; run 27%, casting 45%; the
aimed monster 7.8 / 13.8 / 24.5 units away. **6942 missiles**, all off slot 9 (the census found
slots 0, 1, 2, 4 and 9 in use; 3 and 5-8, 10, 11 empty through the take).

Echoing Strike, from 268 casts of five blades (`combat/mechanics/echoing_strike.py`):

- The blade is missiles.txt 706; the owner's unit id sits at offset 0xEC of the unit record;
  the path record has the usual 16.16 position at 0x00 and the spawn tile at 0x10/0x14. Each
  blade comes with a 720 effect that stands five frames at a tile centre three frames later.
- Five blades spawn 0.8 units ahead of the caster, 0.95 units apart across the aim line, and
  each flies straight at the pointer's ground point: they converge there (fitted convergence at
  0.98 of the pointer distance, spread under a unit), diverge past it, turn at frame 19 about 22
  units out, and home back on the caster's current position at the same 1.12 units per frame,
  vanishing beside them around frame 38. Hits land on both legs (434 out, 180 back among the
  hits with a blade within 3 units).
- The pointer the game used lies 6 frames before the blades' first frame (0.9 units median
  error at lags 5-6, worse either side): the cast reads the pointer at the press and the blades
  appear a quarter second later.
- Emulation error over the take: 0.87 units outbound and 1.22 on the return with the focal point
  fitted from the blades; 2.2 / 2.5 with the pointer six frames earlier as the focal point
  (the pointer and the fitted focal point lie 2.3 units apart on average: the hand moves between
  the press and the spawn). `python -m inventory_tracking.combat validate <take>` prints these.
- Damage per blade cannot be read from the client: life updates arrive batched (a frame's drop
  mixes several blades, 533 of 1147 hits had no blade within 3 units at the frame), and life is
  a 128th fraction. Stage 3's damage model needs monstats points and the skill's damage rows.

Applied to the hunt code the same night: STRIKE_REACH 15 -> 20 (the blades reach 22, the
player engages at 14 median) and AIM_BEYOND 5 -> 1 (the blades converge at the pointer within a
unit; the player aims on the monster or short of it). The recorder now also dumps 0x80 bytes of
each missile's data record on first sight (`MISSILE_DATA`), for the skill id and velocity fields.

### Third take and the blade's data record (2026-10-09, 21:09-21:13 UTC, manual)

`runs/combat/20261009T210919Z-108`: 6208 frames over 250 s (7 late), 230 casts, 902 hits, 194
kills (46.5 per minute), 1.53 lives per combat second; run 31%, casting 48%; the aimed monster
7.2 / 13.5 / 24.8 units away, aim -0.4 past it at the median. Emulation over its 229 full casts:
0.92 / 1.44 units with the fitted focal point, 2.5 / 3.0 with the pointer six frames earlier.

The blade's data record (`MISSILE_DATA`, 0x80 bytes at the unit's pUnitData), 1425 blades:

- 0x0C: u16 skill id 388 (Echoing Strike) and u16 13, the skill level the cast was made at
  (the character's level in it with +skills): the field the damage model keys on.
- 0x3C: u32 0-4, the blade's index within its cast, left to right.
- 0x10: 20 and 0x38: 10, constant (missiles.txt parameters; 20 matches the turning frame).
- 0x14: f32 800.0 constant; 0x18 and 0x78: 0x7FFFFFFF sentinels; 0x24, 0x2C: 0xFFFFFFFF
  (no target unit: the blades fly at a point).
- 0x40: 0x20000 for blade 0, 0x60000 for the others (flags); 0x60: a heap pointer; 0x68-0x78:
  per-blade pairs such as (170, 12), (195, 12), (388, 13) with small counters: sub-skill
  references, not needed yet.
- No owner id in the record: the owner stays at unit record offset 0xEC.

### Stage 3: the game's rows and the damage per hit (2026-10-10)

`combat/mechanics/tables.py` bundles the rows into `combat/data/tables.json` from the install
(skills 388/392/390/393/375, missiles 706/720, every monster's Hell row, monlvl, the areas'
Hell monster levels). What they say:

- **Echoing Strike is a weapon attack**, not a spell: SrcDam 116 (116/128 of the weapon's
  damage) plus 8-12 flat damage with per-level steps, Damage % = 30 + 5/level (calc1), to-hit
  lvl*10 against the monster's defence (AC(H) percent of monlvl AC(H): 1403 at level 85), mana
  14 + 1/level. Synergies: Mirrored Blades and Blade Warp 5% damage per level.
- **Mirrored Blades sets the blade count**: 1 + its level / 5 (calc5), so the five recorded blades
  mean Mirrored Blades at 20. **Duplicates deal (100 / count) / 2 percent** (calc6): with five
  blades the first does 100%, each other 10%, so a stack of five on one monster is 1.4 blades
  of damage and a line through five monsters is five. The hunt's "aim beyond" converges them;
  the policy should rather lay the line through the pack with the focal point short of it, as
  the player does (aim -0.4 to -1.6 units at the median in the three takes).
- **The missile**: Vel 24 and Range 20 frames (the recorded 1.12 units per frame and 19-frame
  turn), ReturnFire 1 (the return leg), NextDelay 20 (a monster can be hit by the same blade
  again after twenty frames: the return), CollideType 3 (walls stop it), Size 1; 720 is its
  detonation effect (Explosion, Range 6). The damage calc note says "chance of pulling targets on
  the return trip".
- **Sigil: Lethargy** (393): radius 7, aura length 12, -50% speed, -33% -1/level damage dealt,
  attack rate and defence down (ln78, ln56). **Death Mark** (375): the pet teleports (38
  units) and the target takes -5% -2/level damage reduction (more damage received) for 125 +
  13/level frames.
- **Monster points in the Chaos Sanctuary** (area 108, Hell monster level 85, monlvl HP(H)
  4637): Doom Knight 5564-6955, Oblivion Knight 5564-6955, Venom Lord 9737-11592, Storm Caster
  3709-5100; Diablo 73125.

Damage per hit event in points (the 128th drops scaled by the mean points), three takes: Doom
Knight median 1565 (p25 245, p75 2739), Venom Lord 1666, Oblivion Knight 929, Storm Caster
516; the client batches life updates, so an event mixes blades and the server's timing. Diablo
was killed five times (138 hit events, 2285 median). Stage 3's damage model will be empirical per
monster type and blade count from these events, calibrated as more takes come, rather than the
full weapon formula (which needs the weapon, the character's stats and the to-hit roll). The
recorder now leaves the pets and the mercenary out of the hit and kill events (the bound demon
361 took 232 "hits" in the takes).

### Fourth take, robust validation and the hit model's calibration (2026-10-10)

`runs/combat/20261009T212147Z-108`: 7926 frames over 320 s (13 late), 233 casts, 1174 hits, 268
kills (50 per minute), 7294 missiles. Two of its casts carried a blade track that jumped
thousands of units (a reused unit id): the root mean square error of the return leg read 28.
`validate` now reports per-cast medians and leaves casts with a jump over 5 units per frame out
(`corrupt_casts`): 0.81 / 0.95 units (out / back) with the fitted focal point, 1.62 / 1.83 with
the pointer six frames earlier, on 229 casts (3 corrupt); the third take 0.84 / 0.95 and 1.56 /
1.74 on 228 (1 corrupt).

**Hit model** (`mechanics/hits.py`, `combat calibrate <take>`): a contact is a blade's emulated
position within 2.0 units of a live hostile's recorded position, once per blade, monster and
leg; a life drop may follow within 20 frames (the server's batches). Over every five-blade cast
of the two takes, with the focal point from the pointer (what a policy knows) and fitted from the
blades (the mechanics alone):

| take | focal | contacts (out / back) | contact -> drop | drop <- contact |
|---|---|---|---|---|
| 212147 | pointer | 2111 (1369 / 742) | 0.83 | 0.49 |
| 212147 | fitted | 1862 (1300 / 562) | 0.88 | 0.56 |
| 210919 | pointer | 1428 (996 / 432) | 0.90 | 0.47 |
| 210919 | fitted | 1573 (1156 / 417) | 0.96 | 0.62 |

So when the emulation says a blade touches a monster, a life drop follows nine times in ten;
half of the recorded drops have no emulated contact: the mercenary and the pets (their damage
is in the same stat), Death Mark, drops batched past 20 frames, and casts whose aim the pointer
six frames earlier misses by 2.4 units. A third of the contacts come on the return leg. The
stage 3 gate asked for 90% of casts' hits matched; the contact precision is there, the recall is
bounded by what the client can tell apart, so the simulator will score damage from contacts
with the empirical points per contact rather than from matched drops.

Where "checking a run on the simulator" stands: the simulator proper (stage 4: a situation
replayed with a policy) is not built; what runs on a take today is the emulation's position
error (`validate`), the hit model's agreement with the recorded drops (`calibrate`) and the play
metrics (`analyse`). The next piece is the situation cutter and the open-loop replay of the
recorded inputs, whose kill order and times against the take are the calibration gate.

### (historical) Stage 4: the simulator and its first gate run (2026-10-10)

*Superseded 2026-10-10: kill counts and kill times are diagnostics, not criteria (see the review note below).*

`combat/sim/situation.py` cuts a situation from a take (the character's recorded positions, the
hostiles' recorded paths open loop, each monster's points from the tables and its life fraction
at the start, the recorded casts with pointer and fitted focal points, the recorded kills and
drop points); `combat/sim/engine.py` runs casts through it: blades from the emulation, contacts
within 2 units of the recorded monster positions, damage per contact from
`combat/data/damage.json` (points per full contact by monster type, matched drops over contact
weights from three takes: Doom Knight 1772, Venom Lord 2585, Storm Caster 1334, Oblivion Knight
1222, Diablo 2295, default 1700) with the duplicate rule (a cast's blades after the first on a
monster and leg deal 10%), deaths when the points run out, a dead monster takes nothing after.
`score` gives damage per second and kills per minute; `gate` compares with the recorded kills;
`combat simulate <take>` replays the recorded casts with both focal points.

Cast animation to blade birth is 4-5 frames (13-15 when casts chain without a neutral frame), so
the pointer six frames before the birth is the pointer at the press.

Gate on the whole takes (recorded casts replayed, fitted focal / pointer focal):

| take | recorded kills, damage | simulated kills | matched | kill time diff (frames) | within tolerance | order | damage ratio |
|---|---|---|---|---|---|---|---|
| 212147 | 268, 1.93 M points | 53 / 60 | 52 / 59 | -17 / -16 | 0.71 / 0.75 | 0.99 / 0.99 | 0.56 / 0.51 |
| 210919 | 192, 1.50 M points | 36 / 36 | 36 / 36 | -11 / -13 | 0.94 / 1.00 | 1.00 / 1.00 | 0.55 / 0.48 |

What it says: the blades' share is reproduced in order (0.99-1.0 agreement) and the simulated
kills come 11-17 frames before the recorded kill events, the server's batch lag seen in the hit
model. The simulator deals half the recorded damage and a fifth to a quarter of the kills
because only the blades are modelled: attributing the recorded drops, 65-74% of the points
follow a blade contact, 13-20% fall on monsters within 8 units of the mercenary or a pet with no
blade near, 12-16% have neither (late batches, misplaced blades). The missing kills are the
monsters the mercenary, the bound demon, the Defiler and Death Mark finish, and every monster
whose recorded path ends at its recorded death before the simulated blades alone would have
killed it (open loop cannot kill later than the record shows the monster).

The gate's 15% damage and 20% kill-time bounds are therefore not met by a blades-only
simulator and cannot be: the next model is the companions' damage as a rate on monsters within
their reach (from the unmatched drops near them), then Death Mark's and the sigil's multipliers.
For comparing two policies the blade share alone is a fair yardstick, since the companions'
damage is the same under both; for absolute kill counts it is not.

### The companions' damage (2026-10-10)

From the three takes, the recorded drops no blade explains, attributed to the nearest companion
within its reach and divided by the frames that companion had a live hostile within reach:
the bound demon (Pit Lord, 361) 72 points per frame, the Act 2 mercenary (338) 104, the
Defiler (744) 15, at a reach of 6 units (their unmatched drops lie 3-9 units from them at the
quartiles). `combat/data/damage.json` `companions` holds them; the situation keeps the
companions' recorded paths; each frame the engine applies a companion's rate to the nearest live
hostile within its reach, after the blades' contacts of that frame. The gate gained
`life_explained_at_recorded_kill`: per recorded kill, the share of the monster's life the
simulation had taken by the recorded death frame, which open-loop replay can measure where kill
counts cannot (a monster's recorded path ends at its recorded death).

Gate with the companions (fitted / pointer focal):

| take | sim kills | blade points | companion points | kill time diff | within | order | damage ratio | life explained (median) |
|---|---|---|---|---|---|---|---|---|
| 212147 | 78 / 85 | 1.04 M / 0.96 M | 0.26 M | -16 | 0.79 / 0.80 | 0.99 | 0.68 / 0.63 | 0.68 / 0.62 |
| 210919 | 50 / 50 | 0.81 M / 0.70 M | 0.18 M | -8.5 / -11.5 | 0.94 / 0.98 | 1.00 | 0.66 / 0.59 | 0.75 / 0.55 |

The companions add 13-14% of the recorded damage (the attribution found 13-20% near them) and
the damage ratio moves from 0.55 to 0.66-0.68 with the fitted focal point. What is still missing
is a third of the damage: the 12-16% of drops with neither a blade nor a companion near (late
batches, blades the emulation misplaces by a unit or two, Death Mark's and the sigil's
multipliers), and blade damage calibrated on matched drops only (a contact that lands and whose
drop arrives past the 20-frame lag counts as unexplained in the calibration, so the per-contact
points run low). Next: Death Mark (-5% -2/level damage reduction on the marked monster) and the
sigil (-33% damage dealt by the monster, not to it: no effect on this score) as multipliers, and
a damage calibration that fits the per-contact points to the whole life explained rather than to
matched drops.

### Hex Purge and Health Link (user, 2026-10-10)

*Superseded 2026-10-10: Hex Purge's explosion is modelled now (see the next section).*

The user named two more sources of damage: Hex Purge (a buff the prebuff casts, "doing AoE
damage") and the companion's aura "that makes mobs share a portion of damage".

**Hex Purge** (skills.txt 389): a self-buff state `hexpurge` on the character while a weapon is
held (ln34 frames); its events `domeleedamage`, `domissiledamage` (func 36) put the debuff
`hexpurgedebuff` on monsters the blades hit, and `hextrigger` fires "Hex Purge Explosion"
(skill 404, an empty row: the explosion's magic damage sits on 389 itself, EMin/EMax 10-15 with
per-level steps, EType mag, aura range par7/100 = 4). When the trigger fires (another hex on the
monster, or its death) is not in the tables. Not modelled yet: of the drops with neither a blade
nor a companion near, half lie within 10 units of a kill of the previous twelve frames, which
fits an explosion on death, but most of them are explained first by the link below.

**Health Link** (skills.txt 405): the Defiler's own skill (Summon Defiler `sumskill1`, cast at
the Defiler's level). Aura range 25, length 500 frames, up to calc2 linked monsters (about five at
Summon Defiler 20), "Damage % Linked" calc1 = 110 L (60 - 20) / (100 (L + 6)) + 20, 54% at L =
20. The takes agree: drops with no blade contact that coincide with a blade drop on a monster 5-10
units away take a third to a half of that drop (median 0.33-0.5; within 5 units they take the
whole drop, which is a contact the 2-unit radius missed; beyond 10 units a tenth), and the
Defiler stands 15-28 units from them. Modelled in `sim/engine.py`: each frame the five live
hostiles nearest the Defiler within 25 units are linked; any damage to a linked monster (blades
or companions) is dealt again at `share` to every other linked one (`data/damage.json`
`health_link`: range 25, links 5, share 0.5).

Gate on the two takes (recorded casts, fitted focal; blade / companion / linked points):

| take | radius | share | blade | companion | linked | damage ratio | life explained median / mean | sim kills (rec.) | within | dt |
|---|---|---|---|---|---|---|---|---|---|---|
| 212147 | 2.0 | 0 | 1.04 M | 0.26 M | 0 | 0.68 | 0.68 / 0.64 | 78 (268) | 0.79 | -16 |
| 212147 | 2.0 | 0.5 | 0.74 M | 0.19 M | 0.72 M | 0.86 | 1.00 / 0.81 | 157 | 0.68 | -20 |
| 212147 | 2.5 | 0.5 | 0.81 M | 0.18 M | 0.72 M | 0.89 | 1.00 / 0.84 | 180 | 0.68 | -19 |
| 210919 | 2.0 | 0 | 0.81 M | 0.18 M | 0 | 0.66 | 0.75 / 0.65 | 50 (192) | 0.94 | -8.5 |
| 210919 | 2.0 | 0.5 | 0.61 M | 0.12 M | 0.54 M | 0.85 | 1.00 / 0.84 | 118 | 0.91 | -14 |
| 210919 | 2.5 | 0.5 | 0.68 M | 0.12 M | 0.55 M | 0.89 | 1.00 / 0.87 | 131 | 0.92 | -15.5 |

With the link the simulator explains the whole life of the median recorded kill by its recorded
death, 81-84% on average, and 85-86% of the recorded damage; the blades' own points fall as
monsters die sooner. The simulated deaths run 14-20 frames ahead of the recorded kill events, the
server's lag seen throughout. The contact radius stays 2.0 (the hit model and the per-contact
points were calibrated at it); 2.5 would add three points of damage ratio. The gate's damage bound
(15%) is met on both takes; its kill-time bound (20%) holds on 210919 (0.91) and not yet on
212147 (0.68), where the sharing kills monsters the record shows dying later: the link count and
share deserve a fit against Summon Defiler's real level, and Hex Purge's explosion is the next
source to add.

### Hex Purge's explosion in the simulator (2026-10-10)

Trigger and size from the takes: of the drops no blade, companion or link explains (3-8% of
the recorded damage), a fifth fall within 12 units of a kill of the previous 15 frames, three
times what position alone gives (4-7% of live hostiles have such a kill near them), 6 units from
the corpse at the median, 1-13 frames after it, 300-1000 points per victim on average. The rest
of the residual is small ticks (50-250 points) far from everything, 3-6% of the damage, left
unexplained (a damage over time on hexed monsters, or life rounding in the client's 128ths).

Modelled (`sim/engine.py`, `data/damage.json` `hex_purge`: radius 8, points 400): a monster a
blade has hit carries the hex; when it dies, every live hostile within the radius takes the points
(through the link if linked; a chain of explosions is allowed). Gate (fitted / pointer focal):

| take | blade | companion | linked | explosion | damage ratio | life explained median / mean | sim kills (rec.) | within | order | dt |
|---|---|---|---|---|---|---|---|---|---|---|
| 212147 | 0.69 / 0.67 M | 0.18 M | 0.69 / 0.67 M | 0.09 M | 0.86 / 0.84 | 1.00 / 0.81, 1.00 / 0.79 | 167 / 157 (268) | 0.67 / 0.63 | 0.98 | -20.5 / -24.5 |
| 210919 | 0.59 / 0.55 M | 0.12 / 0.14 M | 0.53 / 0.47 M | 0.06 / 0.05 M | 0.86 / 0.80 | 1.00 / 0.85, 0.98 / 0.78 | 123 / 96 (192) | 0.91 / 0.95 | 0.99 | -14 / -19 |

The explosion adds 3-5% of the recorded damage; the damage ratio holds at 0.86 because the blades'
and the link's points fall as monsters die sooner (open loop: a monster's recorded path ends at
its recorded death, so earlier simulated deaths cost later contacts). Simulated kills reach 62-64%
of the recorded ones, up from 20-26% with the blades alone. The simulated deaths run 14-24 frames
ahead of the recorded kill events (the server's lag), which is also why `kills_within_tolerance`
reads low on 212147 (0.67): a fixed offset, not disorder (order 0.98-0.99). The next calibration
step is to subtract that lag in the gate and to fit the link share and the per-contact points
jointly on the life explained, then Death Mark.

### Review of 2026-10-10 (`review.md`) (deleted; in git history) and what it changed

The review found one bug and several fair points; taken, with the numbers rerun:

- **Return legs homed on the wrong position.** The engine passed the situation's `player_at`
  (take frames) to `cast`, which asks for the caster at path index k (0-37): every return leg
  flew toward where the character stood at frames 20-37 of the take. Fixed with the cast frame
  added; a test with a character who moves before the cast asserts the blades come back
  through the monster beside the new position. The gate moved little, because the character
  mostly stands while casting: damage ratio 0.86 -> 0.87 (212147) and 0.86 -> 0.88 (210919),
  simulated kills 167 -> 173 and 123 -> 124, order 0.98 -> 0.99.
- `DUPLICATE` is now derived from the blade count (1 / (2 BLADES)); the kill-order agreement
  leaves tied simulated deaths out instead of counting them as agreeing; `life_first` is gone;
  a monster without a monstats row gets the area level's points at 100% and is counted in
  `describe` as `unknown_types`; `cut` takes the area from the take's manifest; `player_at`
  uses bisect; companion damage sharing through the link has a test; `combat simulate` takes
  `--radius`, `--share`, `--links` and `--blast` so a sweep is re-runnable.
- **Overkill through the link** stays as modelled: the killing blow shares its whole damage,
  not the victim's remaining life. Dated choice; the tables do not say.
- **The stage 4 gate is reworded.** Under open-loop replay a monster cannot die later than the
  record shows it, so kill counts and kill times are diagnostics, not criteria. The criterion
  is `life_explained_at_recorded_kill`: median 1.0 and mean at least 0.8 on every take, with
  the damage ratio within 15%. As of this note both takes pass with the fitted focal point
  (median 1.0, mean 0.81 and 0.86; ratio 0.87 and 0.88); with the pointer focal point 210919
  reads mean 0.76 and ratio 0.79.
- **The stage 5 bar** is on the policy-dependent terms: blade plus linked points per combat
  second (the link amplifies blade placement); companion and explosion points are reported but
  not compared.

Not taken: the `kills_within_tolerance` reading stays as is (the fixed 14-24 frame lead of the
simulated deaths is the server's lag; a lag-corrected variant is a later refinement).

### Death Mark in the simulator (2026-10-10)

skills.txt 375: the marked monster's normal and magic damage reduction fall by 5 + 2 per level
points for 125 + 13 per level frames; at level 13 (the level the blades' data record shows for
Echoing Strike, taken for Death Mark too until the character's skill list is read) that is 31%
more damage taken from every source for 294 frames. `data/damage.json` `death_mark` holds it;
the situation reads the marks from the take's key events (Death Mark's key `d` in the manifest's
key names) and targets the live hostile nearest the unit under the pointer within 4 units; the
engine multiplies every hit on a marked monster while the mark lasts and books the extra as
`death_mark_points` (the link shares the unmultiplied damage; each linked monster applies its own
mark).

The takes hold 11-30 presses of `d` each, but the pointer sits within 4 units of a hostile's body
at only 4-12 of them (the rest 9-19 units from any hostile: casts that found no target, or the
pet's teleport used as a move). The marks found add 1% of the recorded damage (19-22 k points);
the gate is unchanged to two decimals: damage ratio 0.88 / 0.86 (212147, fitted / pointer) and
0.88 / 0.79 (210919), life explained median 1.0 and mean 0.81 / 0.86 with the fitted focal
point.

### Stage 5: the input model and the first policy (2026-10-10)

*Superseded 2026-10-10: mana and walls are in the model now (see 'Link-aware weighting' and 'Walls and closed doors').*

**Input model** (`sim/input.py`): a press casts at once when the character is free, a press
during a cast queues one more, a held button casts again as soon as the cast ends; the cast
occupies CAST_FRAMES, the blades appear BIRTH_LAG = 5 frames after the cast starts, and the focal
point is the pointer POINTER_LEAD = 1 frame before the start. Validated on the recorded right
button presses against the recorded blade births (`combat inputs <take>`): with a cadence of 9
frames (the 0.36 s cast bouts) and a 3-frame match, precision 0.81 / recall 0.93 (212147) and
0.70 / 0.82 (210919); 10 frames gave 0.78 / 0.84 and 0.73 / 0.78, 11 frames worse. The misses
are casts the model places a few frames off (chained casts, the server's acceptance).

**Policy v1, the line sweep** (`sim/policy.py` `LinePolicy`): at each frame the character is
free, for every live hostile within the blades' reach (22) a virtual cast is scored along the
line from the character with the focal point 3 short of, on, and 4 past the monster: the blade
points the emulated blades would deal to the monsters where they stand (out and back, the
duplicate rule, and each linked monster's points counted again at the share for every other
linked one). The best line is cast when it is worth MIN_SCORE. Modes: SLOTS casts exactly at the
recorded cast frames with the policy's aim (the aim alone); YIELD casts whenever free except while
the recorded character ran (the player keeps the mouse while moving); FREE casts whenever free.
`combat policy <take>` scores each against the recorded casts on the same situation by the stage
5 yardstick, blade plus linked points per combat second (`--budget manual` caps the casts at the
recorded count).

| take | mode | casts | placement / combat s | blade | linked | sim kills | casts while the record ran |
|---|---|---|---|---|---|---|---|
| 212147 | manual (recorded casts) | 291 | 6869 | 0.71 M | 0.69 M | 174 | - |
| 212147 | slots | 264 | 7383 (+7%) | 0.83 M | 0.67 M | 194 | 29 |
| 212147 | yield | 412 | 7677 (+12%) | 0.92 M | 0.65 M | 205 | 0 |
| 212147 | free | 509 | 8122 (+18%) | 1.01 M | 0.65 M | 230 | 118 |
| 210919 | manual | 284 | 6634 | 0.59 M | 0.55 M | 125 | - |
| 210919 | slots | 232 | 6943 (+5%) | 0.68 M | 0.51 M | 144 | 14 |
| 210919 | yield | 345 | 7485 (+13%) | 0.82 M | 0.46 M | 162 | 0 |
| 210919 | free | 427 | 7904 (+19%) | 0.91 M | 0.44 M | 174 | 104 |

Reading: the aim alone (slots) is worth 5-7% and 15-20 kills with fewer casts (the policy
skips slots with no line worth casting); casting in every stop (yield) 12-13% and 30-37 kills,
with no cast while the record ran; free casting 18-19% but 104-118 casts where the player was
running. The policy raises the blades' points and lowers the linked ones: it aims at the most
blade damage now, while the player's casts fell more often on linked groups; a link-aware target
weighting is the first thing to tune. At the recorded cast count (`--budget manual`, the first N
opportunities) yield reads -4.5% / -0.5%: the budget truncates late fights, so the fair equal-cast
comparison is slots. Mana and walls are not in the model: a policy that casts freely spends mana
the player did not, and a line through a wall is not a line.

The stage 5 bar (20% above manual in the simulator) is not met by v1; its value is in showing
where the gain is: more casts in the stops (yield) and better lines (slots), each worth about half
of it. Next: the link-aware weighting, a mana budget per situation from the character's mana
pool and regeneration, walls from the level grids, and then the live scorer (stage 6).

### Link-aware weighting, closed loop, mana (2026-10-10)

*Superseded 2026-10-10: the recorded pool (503) replaces the 800 placeholder; see 'Three single-level Catacombs takes'.*

The policy now runs inside the engine's frame loop (`simulate(..., policy=)`, a callable from a
`View`: the live hostiles with their remaining points as the simulation has them, the linked
set, the marked set, the mana) instead of planning on the record: it sees monsters die as the
simulation kills them. `virtual_cast` caps every contact by the monster's remaining points (no
credit for overkill) and adds, for a hit on a linked monster, the share spread to each other
linked monster capped by its own points; duplicates after a killing blade find a corpse. The
engine books every cast's birth and focal (`cast_frames`).

Mana: Echoing Strike costs (14 + 1 per level above 1) x 2^7 / 256 = 13 at level 13. The pool and
its regeneration are not in the takes yet (the recorder writes the character's life and mana
into `p` from 2026-10-10 on: stats 6, 7, 9, 11). `data/damage.json` `mana` holds a placeholder
pool of 800 with the classic 120 s full regeneration and is marked `assumed`; with it the
recorded play itself goes 1100-1400 points negative on both takes, so the player's real economy
(potions, Hex Siphon's mana after kill, gear) is far richer. `combat policy --mana fit` keeps the
pool and fits the least regeneration that keeps the recorded casts affordable (0.43 and 0.50
points per frame on the two takes): the policy then has the economy the player actually had.

| take | mode | casts | placement / combat s | blade | linked | sim kills | mana low | refused | casts while the record ran |
|---|---|---|---|---|---|---|---|---|---|
| 212147 | manual | 291 | 6868 | 0.71 M | 0.69 M | 174 | 0 | - | - |
| 212147 | slots | 179 | 7308 (+6%) | 0.85 M | 0.64 M | 183 | 606 | 0 | 22 |
| 212147 | yield | 238 | 7928 (+15%) | 0.99 M | 0.62 M | 208 | 411 | 0 | 0 |
| 212147 | free | 289 | 8295 (+21%) | 1.08 M | 0.61 M | 241 | 0 | 68 | 91 |
| 210919 | manual | 284 | 6634 | 0.59 M | 0.55 M | 125 | -68 | - | - |
| 210919 | slots | 146 | 6763 (+2%) | 0.66 M | 0.50 M | 137 | 712 | 0 | 10 |
| 210919 | yield | 219 | 7564 (+14%) | 0.83 M | 0.46 M | 167 | 336 | 0 | 0 |
| 210919 | free | 253 | 7886 (+19%) | 0.91 M | 0.44 M | 174 | 53 | 0 | 74 |

Reading: with the simulation's own deaths in view the policy casts less (179 / 146 at the
recorded slots, where the record's monsters are often already dead in the simulation) and
still gains: the aim alone +2-6%, the stops +14-15% within the fitted mana and without a cast
while the record ran, free +19-21% at the mana's edge (68 refused casts) and 74-91 casts into
runs. The linked points stay below the record's under every mode even with the link-aware
weighting: the policy's targets die sooner, so fewer linked monsters are alive to share, and the
blades' own points carry the gain. The stage 5 bar (20%) is reached only by free casting, which
breaks the fluency rule; yield at 14-15% is the candidate to take live. The classic regen
assumption and the `fit` are stopgaps until the recorded mana replaces them.

### Walls and closed doors (user, 2026-10-10: the Catacombs runs shot through walls and closed doors; KP_2 landed where nothing could be shot)

*Superseded 2026-10-10: the live line of sight tests the flight layer, not the walk bit (see 'The missile bit').*

The live hunt's line of sight (`macros/sight.py`) read only the block-walk bit of the loaded rooms'
collision grids and counted every cell no grid covers as clear. Three changes, live and in the
simulator:

- **Closed doors are walls.** Doors are object units (type 2) whose classes carry `IsDoor` and a
  footprint in objects.txt; `levels/data/doors.json` bundles the 25 door classes with their
  sizes, `levels/doors.py` reads them (`Door`, closed while in the object's neutral mode 0; the
  footprint's half extent plus a unit of slack around the unit's static position), `world.doors`
  streams them with every world read, and `clear_shot`, `in_reach` and `firing_spots` take them.
  Attack mode and KP_2 pass the current doors at every check. The collision bits a closed door
  sets are still unverified; the units need no such knowledge.
- **Unread cells count as blocked once the level has walls.** The rooms around the character are
  the loaded ones and have grids; a cell on the way with no grid is a room not read, no place to
  shoot into or to teleport toward for a shot. With no grid at all every cell stays clear.
- **The simulator's blades stop at walls** (missiles.txt CollideType 3): `cast(..., blocked)` ends
  a blade's path at the first wall, out or back, with no return; the situation builds the test
  from the take's `level.json` (the recorder now copies the guide's rooms and grids at the take's
  close as well as its open) and the door units the frames carry (`d`, new); the engine and the
  policy's virtual casts use it, so a line through a wall is worth nothing to the policy either.
- The recorder records the Catacombs (areas 35-38) with the Chaos Sanctuary.

The Catacombs run of 2026-10-10 00:49-01:16 UTC had no take (only area 108 was recorded) and the
existing takes carry neither walls nor doors, so the gate and the policy numbers stand; the next
Catacombs take will be the first with walls in the simulator. The run's log shows 288 bursts, 250
ending with the target gone and 11 with its life unchanged (a wall between, most likely), and the
idle line reporting the shot blocked often: the grid walls worked where they were read; the doors
and the unread rooms were the gap.

### The first Catacombs take (2026-10-10 06:30 UTC, `20261010T063034Z-35`)

The take is attack mode's own, not manual play: all 116 casts are the macro's (0 manual), 95 kills in
130 s (44 per minute). It ran through Catacombs 1-3 as one take, so the guide's level (level 3 by
the close, then forgotten on leaving the game) never matched its area and no `level.json` was
written; the door units (`d`) are there in 3203 of 3207 frames. Fixed in the recorder: one take
per stay in a level (a new recorded area closes the take with reason `changed level` and opens the
next), and the level map is copied again every LEVEL_SECONDS (5) while it says more than the copy
(more grids read), never less. `--area` on `simulate`, `policy` and `inputs` cuts a take that
spans levels to one of them. `blades_walled` (new in the score) counts blades a wall or closed door
stopped on the way out.

Gate per level (fitted focal, doors but no walls):

| level | s | monsters | recorded kills | casts | sim kills | matched | life explained med / mean | order | damage ratio | blades walled |
|---|---|---|---|---|---|---|---|---|---|---|
| Catacombs 1 (35) | 60.0 | 122 | 59 | 36 | 60 | 52 | 1.0 / 0.95 | 0.97 | 1.15 | 13 of 180 |
| Catacombs 2 (36) | 45.5 | 89 | 17 | 15 | 13 | 13 | 1.0 / 0.89 | 0.87 | 1.09 | 0 |
| Catacombs 3 (37) | 39.7 | 53 | 31 | 29 | 24 | 24 | 1.0 / 0.88 | 0.95 | 0.98 | 0 |
| whole take | 128.2 | 208 | 95 | 72 | 87 | 79 | 1.0 / 0.92 | 0.98 | 1.09 | 13 |

The gate holds on the first Catacombs take with no change to the model (Catacombs 1's damage
ratio 1.15 is at the edge: the sim deals more than the record, the Chaos takes dealt less). The
closed doors stopped 13 of the 180 blades of the live macro in Catacombs 1: with the door fix
live, attack mode still put blades into doors (the outer blades of a line past a monster in a
doorway, or the footprint slack; to check against the frames).

Policy per level, mana off (placement points per combat second; casts):

| level | manual (= the macro) | slots | yield | free |
|---|---|---|---|---|
| Catacombs 1 | 3288 (36) | 3133 (-5%, 17) | 4146 (+26%, 46) | 4180 (+27%, 43) |
| Catacombs 2 | 1950 (15) | 2536 (+30%, 12) | 3837 (+97%, 23) | 3837 (+97%, 23) |
| Catacombs 3 | 3296 (29) | 4203 (+28%, 19) | 5310 (+61%, 28) | 5310 (+61%, 28) |
| whole take | 3076 (72) | 3282 (+7%, 43) | 4437 (+44%, 87) | 4456 (+45%, 84) |

With the fitted mana on the whole take: slots 3282 (+7%), yield 3871 (+26%, 287 casts refused),
free 4131 (+34%). The recorded mana is flat at 503 through all 116 casts (one -10 step, one glitch)
while the recorded life moves with every hit, so the player's stat 9 in the stat list read is not
the mana the casts spend (or the casts cost nothing here); mana did not limit this run and the
fitted model (pool 800 spread over 72 casts, regeneration near zero) is wrong for it. The
comparison here is the policy against the live attack mode, not against the player's hand: the
closed-loop policy with no cast while the record ran (yield) beats the macro by a quarter to
double, mostly where the macro cast little (Catacombs 2: 15 casts in 45 s). Found (2026-10-10 10:00 UTC): the recorder read itemstatcost ids 9 and 11 for mana and max mana;
those are `maxmana` and `maxstamina` (8 is `mana`, 9 `maxmana`): the flat 503 is the character's
maximum mana and 476 the maximum stamina. Fixed to (6, 7, 8, 9); the mana columns of the takes
before the fix hold the maxima, so the recorded-mana model waits for the next take. The next
single-level take is also the first with walls in the simulator.

### Three single-level Catacombs takes (2026-10-10 11:23-11:26 UTC, `20261010T1123..1124Z-35/36/37`)

The recorder fix held: one take per level (56.8, 18.6 and 68.3 s; reasons `changed level`,
`changed level`, `left the game`), each with its level map (14, 16 and 12 grids), door units in
every frame and the live mana. All casts are attack mode's again (25, 19 and 44; 0 manual).

**Mana is live and not a limit.** Maximum 503; every cast -13; gains of 4-22 points at hits and
kills (mana per hit, mana after kill) refill the pool within frames: never below 472 in levels 2
and 3, from 354 back to 503 in level 1. `data/damage.json` now carries the recorded pool (503);
the regeneration stays the classic assumption (the fit gives 0.17 per frame) and the gains per hit
are not modelled, so the model is strict, not loose. The fitted and the no-mana policies agree.

**The block-walk bit is not the missile's wall.** With the walk-bit walls the simulator walled 27
of 90, 4 of 45 and 63 of 200 blades, and the gate broke (level 1: 6 contacts from 18 casts).
The recorded blades say otherwise: they crossed block-walk cells at 13, 13 and 170 positions
(2.3% of level 3's) and flew on, in runs of up to 16 frames (18 units) inside such cells; only
2-5 blades per take ended early away from the character. The grids are aligned (the character is
on a walkable cell in every frame, the monsters in 99.9%). So walking and flying are different
bits of the collision mask: the simulator's wall test now blocks a blade at unread cells (a room
not loaded) and closed doors only, `Walkable.masks` (new, `pack_masks`) records the raw u16 mask
per sub-tile in every grid the guide reads (level.json from the next take on), and `Ground.mask`
reads it back: the next take tells which bits the blades cross and where they die. The live hunt's
line of sight still uses the walk bit, which over-blocks shots over such cells (the opposite of the
complaint it fixed); it moves to the missile bit once found. Emulated against recorded blades with
the same contact rule, level 1 gives 24 against 20 contacts: the blade model agrees with the
record, and its few contacts there are attack mode's casts at points no monster was within 2
units of when the blades passed (the hit model's recall of 0.5 is the known limit).

Gate per take (fitted focal, unread cells and doors as walls):

| take | s | monsters | recorded kills | casts | sim kills | matched | life explained med / mean | order | damage ratio | blades walled |
|---|---|---|---|---|---|---|---|---|---|---|
| Catacombs 1 | 56.4 | 51 | 24 | 18 | 27 | 22 | 1.0 / 0.98 | 0.85 | 1.26 | 5 of 90 |
| Catacombs 2 | 18.4 | 43 | 9 | 9 | 9 | 9 | 1.0 / 1.0 | 0.94 | 1.05 | 0 of 45 |
| Catacombs 3 | 67.7 | 63 | 52 | 40 | 39 | 35 | 1.0 / 0.80 | 0.91 | 0.91 | 18 of 200 |

Levels 2 and 3 pass (level 3 at the mean's edge, 17 kills only recorded); level 1 fails the damage
ratio: a sparse level where the companion and link models deal more than the record shows (blade
points 10 k of 78 k). Policy per take with the recorded mana (placement points per combat second):

| take | manual (= the macro) | slots | yield | free |
|---|---|---|---|---|
| Catacombs 1 | 2036 (18 casts) | 2758 (+35%, 7) | 3202 (+57%, 19) | 3262 (+60%, 19) |
| Catacombs 2 | 4991 (9) | 4931 (-1%, 4) | 5922 (+19%, 8) | 5922 (+19%, 8) |
| Catacombs 3 | 3761 (40) | 4514 (+20%, 32) | 5217 (+39%, 51) | 5217 (+39%, 51) |

Yield casts nothing while the record ran in any take. Open: the missile collision bit from the
next take's masks; the companion model in sparse levels; the hit model's recall.

### The missile bit, and three more takes (2026-10-10 11:44-11:47 UTC, `20261010T1144..1146Z-35/36/37`)

*Superseded 2026-10-10: the attack-mode toggle works both ways, and the live fight aims by the line policy, not the nearest monster (see 'Architecture check').*

The first takes with raw masks. Per cell value, the recorded blades crossed cells of 0x0001 alone
(block walk, 931 cells) 148 times and flew on; cells with 0x0004 set (26.8k, mostly 0x0005) 26
times, 17 of them with the blade living 10 more frames, 7 within 6 units of a door unit whose state
had changed since the masks were copied; 0x0010 (alternate floor, 2302 cells) 766 times, 0x0400
(objects) 73 times, the unit bits (0x0080 player, 0x0100 monster, 0x1000, 0x2000) freely. Only a
dozen blades ended early away from the character, too few to say more. So the block-missile bit is
0x0004 (D2MOO COLLIDE_BLOCK_MISSILE; the mask layout matches D2MOO's throughout: 0x0010 alternate
floor, 0x0400 object, 0x0800 door, 0x0100 monster, 0x0080 player). `native/layout.py` names it,
every grid read from the game carries a `flight` layer beside `cells` (`Walkable.flight`,
`Ground.flyable`), the wall library learns it per layout with door cells left open (the door units
say when one is shut), `sight.clear_shot` tests the flight layer (the walk bit where a grid has
none: the library's old layouts) and the simulator blocks a blade where the flight layer says so,
at unread cells and at closed doors. A level map without the layer stops no blade in the simulator.

Gate per take (fitted focal, flight walls and doors; all casts attack mode's, 49 / 28 / 31):

| take | s | monsters | recorded kills | casts | sim kills | matched | life explained med / mean | order | damage ratio | blades walled |
|---|---|---|---|---|---|---|---|---|---|---|
| Catacombs 1 | 72.4 | 105 | 46 | 23 | 45 | 40 | 1.0 / 0.89 | 0.95 | 1.02 | 14 of 115 |
| Catacombs 2 | 46.8 | 59 | 28 | 16 | 27 | 25 | 1.0 / 0.96 | 0.98 | 1.11 | 0 of 80 |
| Catacombs 3 | 32.8 | 56 | 49 | 30 | 43 | 40 | 1.0 / 0.90 | 0.95 | 0.92 | 6 of 150 |

All three pass. Policy per take (placement points per combat second; casts):

| take | manual (= the macro) | slots | yield | free |
|---|---|---|---|---|
| Catacombs 1 | 1970 (23) | 1984 (+1%, 8) | 3021 (+53%, 28) | 3021 (+53%, 28) |
| Catacombs 2 | 3222 (16) | 3179 (-1%, 10) | 4181 (+30%, 29) | 4220 (+31%, 27) |
| Catacombs 3 | 5285 (30) | 5336 (+1%, 18) | 5892 (+11%, 24) | 5888 (+11%, 24) |

Yield gains most where attack mode cast least (level 1: 23 full casts in 72 s with 105 monsters
about) and little where it was already busy (level 3). The live hunt still aims at the nearest
monster and waits for a clear shot on the walk bit where no flight layer is known; the policy's
gain says where the next live change is: casting during stops at the line worth most, not at the
nearest monster.

Live changes the same day (user): KP_3 only turns attack mode on (never off); Win+X ends it and
then runs the macro as it does otherwise (runner.py); the last teleport hop before a door lands
APPROACH (6.5) units beside it on the character's side, never on the warp's own tiles
(teleport.py `approaches`): a hop onto the tiles had put the character off to a side and the walk
in went around.

### Architecture check and the steer to the end of the plan (user, 2026-10-10 afternoon)

Asked whether the code can carry the plan to its end. The measuring side can (small modules;
`simulate` 0.7-4 s per take, `policy` 2-24 s, the combat tests 0.2 s, one policy decision at most
about 50 ms). Three things had to change before more tuning, and the user asked for all of them and
for the plan's end:

1. **One decision function for the simulator and the game.** `macros/` imported nothing from
   `combat/`: the policy was written against the simulator's `View` and read the record to yield,
   the live `Hunter.fight` was another algorithm (nearest monster, one unit past), so the simulated
   gain belonged to code that never ran in the game and the live rule was never scored as a policy.
   Steer: `combat/policy.py` with one `Observation` (the character, the live hostiles with the
   points they have left, the linked set, the walls, the mana, whether the player is moving), built
   from a take frame by the engine and from `World` by the hunt; the line sweep and the hunt's own
   rule (nearest, elite first) are two policies over it, compared on the same takes; the hunt asks
   the policy where to aim.
2. **A gate that can fail both ways.** `life_explained` is capped at 1.0 and under open loop a
   monster cannot die later than recorded, so a simulator that deals too much passed; the damage
   ratio summed blades, companions, link and explosion (blades 10 k of 78 k in the sparse Catacombs
   take) while the policy is scored on the blade and linked points. Steer: a blade-side gate over
   the monsters no companion stood near, uncapped (the simulated monsters live as long as the
   recorded ones), failing above as well as below; takes marked as fitted on or held out.
3. **A regression harness.** The gate numbers lived in this file's tables, rerun by hand. Steer:
   `combat gate` over every take writes one scoreboard (pass or fail per take, the change since the
   last run); trimmed situations from real takes are checked in and tests pin the gate and the
   policy's choices on them.

Smaller: the frames were read by position in four modules (one typed reader in `takes.py`); stage 6
needs the live scorer on the HUD card and a per-level comparison of macro and manual takes.

#### What was built (2026-10-10 evening)

**One decision** (`combat/policy.py`). `Observation` (origin, foes with points left and the elite
flag, linked set and share, walls, moving, mana) and `Choice` (focal point, the monster the line
went through, worth). `LinePolicy` is the line sweep, yielding while the player moves; `NearestPolicy`
is the hunt's rule of 2026-10-09. The engine builds the observation per frame (moving = the recorded
character walks or runs), `observe` builds it from the game's records; `walls` and `linked_set` are
shared by both. The sweep's ties go to the focal point on the monster (offsets 0, -3, +4) and a point
off an elite counts twice (ELITE_WEIGHT 2: the user's "the elite first").

**The live fight** (`macros/hunt.py`). The takes said where the macro lost: of the frames with a
target in reach it stood idle 17-66% (the player's own play: 12-21%), because each monster got its
own burst (ready wait, press, up to three casts, release, 0.1 s polls). And in the simulator the
hunt's own nearest-monster rule, cast at every free frame, scores about what the line sweep does in
the Catacombs: the loss was cadence, not aim. `Hunter.fight` is now one hold of the strike input
through the whole fight, looked at every frame (0.04 s), the pointer kept on the policy's line (asked
again every 0.12 s and when its monster is gone; aimed again when the focal point moves a unit or the
pointer strays 25 pixels), Death Mark and the sigil as before. A monster in reach for which the
sweep finds no line gets the old rule. **Yield**: a key of the player's down, the left mouse button
down, or the character walking or running ends the fight at once ("Yielded (...)") and the mode
waits; it is not a stopped fight.

**The gate, two-sided** (`sim/engine.py` `curves`, `verdict`). Per monster the simulated and recorded
cumulative life loss are compared over its engaged frames: `ahead` is the simulated loss above the
recorded loss 20 frames later, `behind` the recorded loss above the simulated one, `bias` their
difference, each a share of a life, averaged over the monsters no companion came within 8 units of
(the blades' side) and over the rest. A take passes with life explained median 1.0 and mean >= 0.8,
damage ratio within 15%, and |bias| <= 0.1 on the blades' side (five monsters or more). What was
tried first and dropped: monsters that live as long as the record (`simulate(mortal=False)`, kept as
an option): the totals then measure overkill, not the model (a blade's 1700 points on a 1400-point
Dark One, the link's share on monsters already dying), 1.0-3.7 times the record.

What the gate says now: Chaos Sanctuary blades' side has no bias (-0.02) with scatter of about 0.09
of a life each way; near the companions the model runs ahead by 0.08. In the Catacombs the blades'
side runs ahead by about 0.10 and the companions' side by 0.2-0.3. Halving the companions' rates, the
link share at 0.3, the link without overkill and no explosion each move that by 0.01-0.03 only
(`link_overkill` is a `simulate` option; the rest are the existing ones). The contacts themselves are
right (contact -> drop within 20 frames 0.85-0.99 by type, Arach 0.66; the first drop after a first
contact on a fresh Doom Knight is 0.41 of its life, on a Dark One 0.93, as the model has it). The
lead left is the mean damage standing in for a roll: a monster with about one blade's worth of life
dies of every first contact in the simulator and of most in the game. It is the same for every
policy on a take, so the comparisons stand; the kills of weak monsters are a little early.

**The harness** (`scoreboard.py`, `combat gate <takes>`, 80 s for the ten takes with casts; `--quick`
for the gate alone). `data/damage.json` `fit_takes` names the three Chaos takes the numbers were
fitted on; every other take is held out. Scoreboard of 2026-10-10 evening (gain = blade plus linked
points per combat second over the recorded casts):

| take | side | gate | explained | ratio | bias (monsters) | slots | yield | free | nearest |
|---|---|---|---|---|---|---|---|---|---|
| 203733 Chaos | fit | fail: ratio | 1.0 / 0.81 | 0.84 | -0.02 (90) | +6% | +14% | +21% | +12% |
| 210919 Chaos | fit | pass | 1.0 / 0.86 | 0.88 | -0.02 (72) | +1% | +14% | +20% | +14% |
| 212147 Chaos | fit | pass | 1.0 / 0.81 | 0.87 | -0.02 (126) | +6% | +15% | +20% | +11% |
| 063034 Catacombs 1-3 | held out | fail: ahead | 1.0 / 0.92 | 1.09 | +0.13 (50) | +5% | +44% | +45% | +34% |
| 112329 Catacombs 1 | held out | fail: ratio, ahead | 1.0 / 0.98 | 1.26 | +0.51 (6) | +36% | +61% | +60% | +51% |
| 112426 Catacombs 2 | held out | pass | 1.0 / 1.0 | 1.05 | none away | -1% | +23% | +23% | +28% |
| 112444 Catacombs 3 | held out | pass | 1.0 / 0.80 | 0.91 | -0.00 (21) | +19% | +40% | +40% | +34% |
| 114436 Catacombs 1 | held out | pass | 1.0 / 0.89 | 1.02 | +0.01 (21) | +1% | +59% | +59% | +61% |
| 114549 Catacombs 2 | held out | pass | 1.0 / 0.96 | 1.11 | +0.05 (2) | -1% | +29% | +31% | +25% |
| 114636 Catacombs 3 | held out | pass | 1.0 / 0.90 | 0.92 | +0.10 (17) | +1% | +11% | +11% | +6% |

Seven of ten pass (five of seven held out). On the passing takes yield gains +23% at the median
(+11% to +59%); on the player's own play (Chaos) +14-15% without one cast into a recorded run, against
+11-14% for the nearest-monster rule casting through the runs: the stage 5 bar (20%) is met against
the macro and not against the player. Two things the first scoreboard run caught: the mana pool of
503 with the classic regeneration starved every policy on the long takes (yield -11% where it had
been +15%; the recorded mana never limited casting, so the pool is off by default now, `limits` in
the data file, `combat policy --mana` turns one on), and the nearest rule's score in the Catacombs.

Tests: two trimmed takes are checked in (`combat trim <take> --frames A B --to <dir>`: gzipped,
136 KB and 176 KB): `chaos-manual` (212147, frames 2750-3250) and `catacombs-macro` (114636, frames
1-420, with walls). `test_scoreboard.py` pins their gate numbers, the yield gain and the policy's
first casts; `test_shared_policy.py`, `test_score.py`, `test_compare.py` cover the new modules.

**Stage 6, what is in place.** The live scorer (`score.py` `LiveScore`, fed by attack mode's reads):
points the hostiles lost per combat second and kills per minute over the last minute, said after
each fight ("Last minute: ...") so it stands on the HUD card. `combat compare <takes>`: per take and
per level and side (macro when most casts were a macro run's), points per combat second, kills per
combat minute, and the casting / moving / standing shares of the frames with a target. As of this
evening:

| level, side | takes | combat s | points / s | kills / min | standing with a target |
|---|---|---|---|---|---|
| Chaos Sanctuary, manual | 6 | 1093 | 10774 (9373-14511) | 71 (60-81) | 12% (12-21%) |
| Catacombs 1, macro | 4 | 186 | 2608 (1864-3817) | 58 (36-66) | 61% (33-92%) |
| Catacombs 2, macro | 1 | 38 | 3813 | 45 | 60% |
| Catacombs 3, macro | 2 | 58 | 6580 (5474-7686) | 111 (84-138) | 28% (17-39%) |

All macro takes are from before the held-strike fight. **Open, and only the game can close it:**
stage 6's criterion is ten sessions a side in the same levels. There is no level yet with both
sides: it needs manual takes in the Catacombs (or macro takes in the Chaos Sanctuary) and macro takes
with the new fight; `combat compare` then says whether the standing share fell toward the player's
12-21% and what the points per second did. Also open: the fluency of the yield in the hand (the
user's verdict), the frame reader has no schema version (rows are positional in the file, named in
`takes.py`), and the roll's spread in the damage model.

Same evening (user): KP_2 left the character beside the elite it found until KP_3 was pressed (the
latest take: standing 92% of the frames with a target). KP_2 now leaves attack mode on after its
step, and KP_3 toggles the mode again (macros/runner.py).

### The first takes with the held-strike fight (2026-10-10 13:57-13:59 UTC, `20261010T1357..1359Z-35/36/37`)

All attack mode's. `combat compare`: Catacombs 1 stood 29% of the frames with a target (59% at the
median of the earlier macro takes there, 33-92%), 3644 points per combat second (2608 before) and 79
kills a minute (58); Catacombs 2 stood 21% (60% in the one take before), 4790 points (3813), 84 kills
(45). The player's own Chaos play stands 12-21%. Scoreboard: on levels 1 and 2 the simulated yield
policy now gains +14% and +9% over what the macro did (+23% to +59% on the takes before), so most of
the headroom is taken; level 1 fails the gate (ratio 1.24, blades ahead by 0.21) and the short level 3
take fails low (ratio 0.67), level 2 passes.

What the session's log showed, fixed the same evening (macros/hunt.py):
- **Attack mode ended itself three times** ("5 fights stopped in a row ... is out of view"): the
  policy's focal point may lie off the screen (a line 22 units long, the screen shorter up and down),
  and a focal point off the screen stopped the fight. The pointer now goes on the same line as far as
  the screen reaches (`aim_in_view`); with nothing of the line in view the fight ends quietly, not as a
  stopped one. This was the "KP_2 teleported near monsters and nothing attacked".
- **A stopped fight after every KP_2 hop** ("Echoing Strike is on no skill key ... right Teleport"):
  the right button still holds Teleport (or Death Mark) for a moment after the macro's own cast. The
  mode now waits up to INPUT_SECONDS (1 s) for the skill to come back before that counts.
- The line's log line was written every frame for a monster beyond STRIKE_REACH; once per monster now.

### The review of 2026-10-10 evening (`review.md` at the repository root) and what was taken from it

The earlier `combat/review.md` (deleted; in git history) named above was deleted; its findings are in this plan and in git.
The new review (eight findings, a cleanup table, a sequence) was read against the code; findings 1,
3, 4 and 5 were checked and hold as written. Done from it so far:

- **Finding 1, shutdown restarting attack mode:** `MacroRunner.close` is final (`closed`: nothing
  pending, no attack mode resumed, no request starts a run). The single-owner scheduler it proposes
  is not built.
- **Finding 4, fit or held out by the recording:** `Take.recording` (a trim's manifest carries it
  through further trims; a recorder's directory is named by its start), and the scoreboard sides by
  it: the `chaos-manual` fixture is `fit`, a take that does not say where it came from `unknown`.
- Cleanup: the stale "the player attacked" reason, the `NearestPolicy` description, a dangling
  `review.md` reference.

Open, in the review's order: effective damage against raw blows in the score (3), deaths against
disappearances in the live score (5), the versioned timeline and area segments (6), the controller
shared by the game and the replay (2), input ownership and yielding (7), one viewport for planning
and aiming (8). Findings 3 and 5 move pinned numbers and the gate's thresholds, so they wait for a
decision rather than being slipped in.

### Review findings 3 and 5: the life taken, and kills that are kills (2026-10-10 night, user: "go ahead")

**Finding 3, effective damage.** `sim/engine.hurt` still records each blow as struck (the bags per
source, `dealt_by` for the life curves, the amount Health Link shares), and beside it the life the
blow took off the monster: `Outcome.removed` per source (`BLADES`, `COMPANIONS`, `LINK`,
`EXPLOSIONS`; Death Mark's share is inside its source), `effective_damage`, `placement`. The score's
`damage_points`, `damage_per_second` and the per-source points, the policy yardstick
(`placement_per_combat_second`) and the gate's `damage_ratio` are the life taken;
`raw_damage_points` keeps the blows. Thresholds are unchanged.

The scoreboard over the 63 takes in `runs/combat`, before and after (same takes, same model):

| | blows (before) | life taken (after) |
|---|---|---|
| takes passing the gate | 29 | 24 |
| fit takes passing (3 Chaos) | 2 | 0 (ratios 0.81, 0.85, 0.83) |
| damage ratio, change per take | | median -0.07 (-0.23 to -0.03) |
| yield gain on passing takes | median +19.3% (4.2 to 65.3) | median +19.6% (4.6 to 43.5) |
| yield gain on the three manual Chaos takes | 13.8, 13.8, 15.1% | 12.6, 10.1, 13.3% |

Nine takes changed sides: seven now fail on a damage ratio of 0.80-0.85 (the two Chaos fit takes
among them), two that failed on too much damage now pass. Read plainly: about seven points of the
simulated damage were overkill, and without them the model deals 15-19% less than the record in the
Chaos Sanctuary, at the edge of the 15% band it was fitted to sit inside. The policy's gain over the
recorded casts held on the manual takes (a tenth to an eighth) and lost its largest values (65% to
40%, 59% to 44%): those were finishing blows counted at full size. The fixtures' pinned numbers
moved with it (ratios 0.92 to 0.87 and 1.01 to 0.94, yield gains 13.1 to 9.8% and 18.1 to 8.7%).

Not done, and the next thing the numbers ask for: the damage per hit refitted against the life
taken (and the roll spread the plan already lists), then the thresholds looked at again. Until then
"24 of 63 pass" is the honest count.

**Finding 5, kills.** `World.dead` (macros/world.py) carries the unit ids of the monsters lying in a
dead mode, from the same walk of the unit table. `LiveScore.note(..., dead)` counts a hostile that
was near and is now among them as a kill with the life it had left; one that only left memory is
`gone`, counted beside the kills and worth nothing (the recorder's `kill` and `gone`). An interval
is combat when a live hostile was near at its start, so the interval the last monster dies in
counts. Another level or another character unit starts from nothing. The HUD's "Last minute" line
will read lower than before where teleports used to add kills.

Tests: `test_a_finishing_blow_scores_the_life_it_took_not_its_size`,
`test_a_marked_finishing_blow_takes_no_more_than_the_life_left`, and in `test_score.py` the death
against the disappearance, the last monster's interval, the new level or game. The assertion that a
disappearance is a kill is gone. Full suite 2740 passed.

### The rest of the review: lifecycle, timeline, window, controller (2026-10-10 late night)

`review.md` findings 2, 6, 7 and 8, the rest of 1, and its cleanup table. Small pieces (the timeline
and viewport modules, the tests of each change, the contract sections at the top of both plans) were
written by helper agents from written briefs; the integration, the live fight loop and the scoreboard
were done in the main session. 2862 tests pass (2740 before); nothing was run in the game.

- **Timeline (finding 6).** `combat/timeline.py`: `ticks` maps a take's sample numbers to game ticks
  from the timestamps (a sample advances one tick, plus one per whole tick it is late by beyond 0.75
  of a tick, so an evenly sampled take keeps its numbers). `sim/situation.cut` builds the situation
  in ticks (`in_ticks`): what a sample showed is held through the ticks the next one skipped, 12 at
  most, a monster only when the next sample still has it. Frames of another level than the
  situation's are left out; the CLI's `--area` takes the longest stay; the strike button held at
  the first frame is a press there; a take recorded faster than 25 a second is refused. The
  recorder writes `schema: 2` and `Take.load` refuses a schema it does not know (`takes.SCHEMAS`).
  The 63 scored takes held 4069 ticks without a sample; the worst single-level take ran 10% short
  before (51.3 s on the clock, 46.6 s of frames).
- **Window (finding 8).** `macros/view.py` `Viewport(aspect)` owns the projection, the two screen
  limits, `hop_in_view` and the focal point the pointer can reach. `teleport.Way` and `way_for`
  take it (the way is planned for the window the hop is made in, the cache keyed by it); the
  routines' and teleport's helpers delegate to it. On the host's 2560 x 1418 window the way was
  planned for 16:9 (1.778) before and is planned for 1.805 now: marginally more reach sideways.
- **Controller (findings 2 and 7).** `combat/controller.py`: `aim_choice` (the policy's line, else
  the elite or the nearest in reach, through `Observation.aimable`), `Aim`, `CastWatch`, `serve` and
  `Move`, moved out of `Hunter.fight`, `choose` and `serve_move` with their constants. `LinePolicy`
  scores a line with the focal point the window lets the pointer reach (16 units straight down the
  screen at most), not one the aim shortened after the choice. The simulator's new `live`
  candidate (`LiveAim`) is that decision; the observation it and every policy get holds the doors
  of the decision frame, not of five frames later. `Pace.watched` replaces the overwritten
  `pace.sleep`; the idle hold is pressed again only after the look at the player's move; the
  actuator's re-press checks the focus first and presses nothing into another window.
- **Lifecycle (finding 1).** The runner's transitions (a request, a run's end and its successor,
  shutdown) are made under one lock; `Cancelled(Abort)` replaces the `'cancelled'` message text as
  the pause protocol. A test with the hand-over slowed down fails without the lock.
- **Cleanup.** `link_overkill` is gone from `simulate` (no caller; the experiment is the note
  above); the hover scan at each Consume runs only with `D2R_MACRO_RESEARCH` set; two timeline
  helpers nothing used were dropped.

Scoreboard, the same 63 takes, against the run after findings 3 and 5:

| | Before | After |
| --- | --- | --- |
| Takes passing | 24 | 23 |
| Fit takes passing | 0 of 3 | 1 of 3 (ratios 0.81, 0.86, 0.83) |
| `yield` gain on passing takes, median | +19.6% | +19.1% (+5.0 to +42.8%) |
| `live` gain on passing takes, median | not scored | +19.0% |

One fit take passes now and two Catacombs takes fail now ("blades run ahead" by 0.108 and 0.11
against the 0.1 bar). Twenty-two yield gains moved by two points or more, both ways (+26% to +44%
on the take that ran 10% short; +42% to +22% on the mixed-level take of 06:30, which is now its
Catacombs 1 frames only). `live` differs from `yield` on 21 takes, by -2.6 to +1.9 points: the
fallback and the window change little of what the sweep scores. Fixtures: Chaos yield 0.099 (0.098),
Catacombs yield 0.038 (0.087: 0.042 from the ticks, the rest from the doors of the decision frame),
Catacombs ratio 0.96 (0.94).

Not done, and why: the fight's loop is not replayed against recorded input (holds, swaps, marks
chosen live: the pieces have traces, the loop does not); the hunt's fakes still advance the clock
only through sleeps; the test files were not split or renamed; the damage per hit was not refitted
(the fit takes read 14-19% low) and the gate's bars were left alone.

## Note, 2026-10-10 late night: the replay viewer

Built (user: "wire simulator into visualization ... use godot ... visually see played games and check
some places where things were improved"):

- `combat/viz.py` exports a take as one JSON file for the viewer: the situation per game tick (the
  character, monsters with their recorded life, companions, doors, the pointer, the wall grid), the
  recorded casts and each policy's (`live` and `yield` by default) through `simulate` with their
  blades (`echoing_strike.cast`), simulated life curves, deaths and scores, and per policy the
  moments where it and the recorded play differ most (`combat/viz_moments.py`: 3 second windows by
  life taken either way, policy casts while the player did not cast, recorded casts that touched
  nothing, elites dying a second or more apart). `make combat-viz` exports every take with five or
  more full casts to `runs/combat/viz/` with an `index.json`: 71 takes, 13 MB, 42 s; the largest
  file is 1.18 MB (20261009T212147Z-108, 7992 ticks, 287 monsters).
- `combat_viewer/` is a Godot 4.7 project (GDScript only) that reads those files: a take list with
  each policy's gain, the level in the game's isometric projection, the recorded run (orange) and a
  policy run (blue) side by side or overlaid, playback 0.25x to 8x with a scrub bar marking casts,
  kills and moments, running totals with their difference, and the moments list to jump to and loop.
  `make combat-view` opens it; the file layout and the keys are in `combat_viewer/README.md`.

Verified: `tests/.../combat/test_viz.py` and `test_viz_moments.py` (63 tests: the schema, ticks and
tracks against `Situation`, scores against `compare`, deaths and life, blades against the mechanics,
walls and doors against the level map, moments, determinism); the gains in the index equal the
scoreboard's; every script parses in Godot 4.7.2; `make combat-view-check` opened all 71 takes headless
and pressed every key with no script error; six pictures of the real window (the list, side by side,
overlaid, a level with walls, a level without, fitted) were looked at.

Not verified: nobody has watched it play or used the mouse in it (wheel zoom, drag pan, clicking the
scrub bar and the moments list, the folder dialog are untested by hand); the pictures were taken in
a 1280 x 1422 window, not at 2560 x 1440. The viewer shows what the simulator says: on a take whose
gate fails (46 of the 71) the comparison is only as good as the model, and the side panel says so.
A monster's simulated life rounds up to one thousandth while it lives, so a bar never reads empty
before its death tick.
