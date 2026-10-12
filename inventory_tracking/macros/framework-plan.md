# Combat framework and builds — staged implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development to
> implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking. Read
> [framework-plan.digest.md](framework-plan.digest.md) first; come here only for the stage in hand.

**Goal:** A build-agnostic combat framework (goals, navigation, stance, survival, buffs, drinking)
that a build submodule configures, modifies and overrides, proven by a closed-loop test arena fed
from recorded battles.

**Architecture:** `macros/` and `combat/` become the framework and name no skill; everything
Warlock or Echoing Strike moves to `inventory_tracking/builds/`. Test harness first (golden net,
arena, contracts), then the move with no change of behavior, then the safety features in the order
the user set.

**Tech stack:** Python via `uv run --offline`, pytest (plain functions), pydantic `Config` for
settings, dataclasses for records, `Protocol` for contracts.

**Spec:** [architecture.md](architecture.md) — every ruling cited below is there with its date.
[development.md](../../development.md) and [AGENTS.md](../../AGENTS.md) apply.

## Global constraints

- Stages 0–3 change no behavior in the game. A step is done when the golden net (Stage 0) reads
  the same and the full suite is green: `uv run --offline pytest tests/inventory_tracking -q`.
- Decisions stay pure (facts in, a decision out); reads of the game and inputs stay in `macros/`.
- Player input always wins; KP_3 off ends the mode; `make osd` stays independent of `make serve`.
- Settings are frozen pydantic `Config` (`with_overrides`, never `model_copy`); records are dataclasses.
- Tests mirror module paths under `tests/`; pytest functions, no unittest classes.
- `rg` needs `--no-config`. No item or skill code written from memory: read it from the code or data.
- No commits unless the user asks. A task ends at a green gate, reported with the command's output.
- Every rule that changes behavior cites its evidence (a take, a time) in `macros/plan.md`.
- **Precondition:** the working tree holds a large uncommitted change set (2026-10-12). Stage 0
  starts only after the user has committed or otherwise frozen it: the golden net must be cut
  from a known base.

## Who does what

| Mark | Model | Takes |
| --- | --- | --- |
| **H** | Haiku 5.5 sub-agent | one small pure module with its tests, or tests only; files no other running task touches; the interface given in full in its brief |
| **C** | capable sub-agent (Opus 5.5 / Sonnet 5.5) | a module that drives production code, a move across several files, anything that needs the code read first |
| **M** | the main session | stage entry (detailing the next stage), integration of the H and C results, the full suite, every gate, anything run against the game |

Rules of the split (user, 2026-10-10 and 2026-10-12): H tasks of one group run in parallel on
disjoint files, no worktrees; a brief is self-contained (files, signatures, the tests to write,
the command that proves it); M reviews every result against its brief before the next group
starts. An H task that turns out to need a decision stops and reports — it does not decide.

## Review focus

What the spec implies and no single task's tests would otherwise meet (the plan was checked
against the code by an independent reviewer on 2026-10-12; its findings are folded in below):

1. **The arena disagrees with the game.** A safety rule tuned in a world whose monsters hit
   five times too soft passes and kills in play. → Task 1.9 (calibration) gates every scene used
   for a safety verdict; uncalibrated scenes are reported, not asserted.
2. **The move changes a decision nobody was looking at.** → Task 0.2's golden net covers every
   pure decision over every in-tree fixture, not only the paths the refactor names.
3. **Timing drifts while the logic stays right.** An extra indirection per loop turn, or a
   monster read added to the hop, is a regression the goldens do not see. → Task 0.4 freezes the
   read and press *counts* of `scenarios/loop` (wall time varies ±40% and is not frozen).
4. **A build part answers with silence.** A movement set that returns nothing leaves the mode
   idle with no line in the log (Drifter Cavern, thirteen presses). → Task 2.3's contract tests.
5. **Two actors press at once.** `serve` drinking beside `make osd`, a swap beside a hop. →
   Stage 4's arena scenes with both drinkers modelled; the swap contract's tests in Stage 7.
6. **A play depends on the wall clock.** The runner expires presses by `time.monotonic()`
   while the arena runs on its own clock: a slow machine could change a result. → Task 1.6
   patches the runner's wall limits and proves determinism over ten runs.

---

## Stage map

| Stage | Delivers | Gate to leave it | Behavior in game |
| --- | --- | --- | --- |
| 0 | the golden net | goldens, loop counts and the xfail list recorded on the frozen base, suite green | none |
| 1 | the arena (on `fakes.Game` and `sim.monsters`), scenes cut from takes, calibration, the scorecard | 16 threat scenes play in the arena with production code; calibration report exists; plays are deterministic | none |
| 2 | contracts (the `Attack` surface decided), `Build`, registry, the test-only build, the ratchet | contract suite green on two builds | none |
| 3 | the Warlock moved into `builds/` | `decisions.json` byte-identical; the test build fights in the arena; ratchet list down to a residue the user has seen | none |
| 4 | safety: burst rule in osd, the price of a place, `serve` drinking | six standing xfails green in the arena; scorecard: no scene worse | yes |
| 5 | navigator behavior: rule at 15, `LowCharges`, careful landing, `eta` | navigation scenarios no worse in hops; new set scenes | yes |
| 6 | goal queue, leashes, drop lanes | TZ and route scenes in the arena; thrash tests | yes |
| 7 | swap by threat, tactics | per-tactic scenes | yes |
| 8 | buff plan features (Call to Arms, openings) | buff scenes; prebuff replay | yes |

Stages 0–2 are detailed below. Stages 3–8 are outlined with their interfaces and task split;
**each gets its own detailed task list at entry**, written by M from the code as it then is and
checked by a reviewer before any H task is briefed (the contracts will have been shaped by
Stages 1–2 by then; detailing them now would be guessing).

---

## Stage 0 — the golden net

Purpose: the proof that Stages 1–3 changed nothing.

### Task 0.1 (M): record the base

- [ ] Run the full suite; write the counts (passed, xfailed, skipped) and the commit hash to
  `tests/inventory_tracking/scenarios/golden/BASE.md`.
- [ ] Run `uv run --offline pytest tests/inventory_tracking/scenarios -q -rxX` and paste the
  **whole** xfail list there (62 on 2026-10-12: threat 13, navigation 20, revivers 8, loop 2, …).
  None may change state in Stages 0–3; the 13 threat ones are Stage 4's targets.

### Task 0.2 (C): decision goldens

**Files:** create `tests/inventory_tracking/scenarios/golden/{__init__,cases,build_golden,test_golden}.py`,
`tests/inventory_tracking/scenarios/golden/decisions.json`.

**The rule that makes the net survive the move:** every case goes through an entry point that
Stage 3 keeps (`Hunter`-level), and `cases.py` is the *only* adapter. When Stage 3 changes a
signature underneath, the same task may edit `cases.py`; `decisions.json` must stay
byte-identical, and M reviews any `cases.py` diff.

```python
# cases.py
@dataclass(frozen=True)
class Case:
    name: str                      # '<kind>:<fixture>:<variant>', unique
    run: Callable[[], object]      # JSON-serialisable output of one production decision
def cases() -> list[Case]
# build_golden.py:  uv run --offline python -m tests.inventory_tracking.scenarios.golden.build_golden
def main() -> int                  # writes decisions.json {name: output}, sorted, floats rounded to 3
```

The game for every case is `tests/inventory_tracking/macros/fakes.py` `Game` (its `run()`
gives the `Run`; `game.staff` and `clock.now` set the variant); a stance fixture becomes a
world as `scenarios/loop/helpers.py` `recorded_world` and `scenarios/stance/harness.py` `load`
do, with its `Ground` from the fixture's grids.

| Kind | Fixtures | Entry point | Variants |
| --- | --- | --- | --- |
| `stand` | 39 stance moments | `Hunter.better_stand` (hunt.py; `observe` + `camp(jumps=…)`) | staff: none / in hand 69 / in hand 9; warp ready / in delay |
| `step` | 39 stance moments | `Hunter.next_step` | the same, reduced to 3 |
| `aim` | 39 stance moments; 16 threat scenes via `threat.harness.records` | `Hunter.choose` | — |
| `jumps` | synthetic | `Travel.jumps` behind the adapter | staff none, in hand 69/15/14/10/9/0, not in hand; warp ready / in delay / failed |
| `landing` | navigation fixtures' start spots | one `teleport.landing(target, player, way, aspect)` each (hop-by-hop runs are already pinned by `test_routes`) | near / far way |
| `tough` | 39 stance moments | `Hunter.tough` | — |
| `due` | synthetic worlds | `Rotation.purge_due/ward_due/sigil_due/engorge_due`, `worth_a_mark`, behind the adapter | state present / absent / unknown |
| `pickup` | `tests/.../macros/test_pickup.py`'s worlds | `pickup.choose` | — |

- [ ] First check and write down in `BASE.md`: which stance fixtures give `Ground` None, and
  what `Travel.stride`/`clear_shot` do then; exclude or mark those cases.
- [ ] `test_golden.py`: `test_every_case_reads_as_recorded` (parametrized by name),
  `test_no_case_is_missing_or_stale`. Mark the module `slow` if it passes 60 s (`camp` over a
  big frame costs 0.35–0.6 s).
- [ ] Run the builder, run the test: all pass. Change `CAMP_REACH` locally and confirm cases
  fail, then restore.

### Task 0.3 (H): golden for the battle replay

**Files:** create `.../golden/test_replay_log.py`, `.../golden/tower_cellar5.log.json`.

- [ ] `test_the_replayed_battle_says_what_it_said`: run the `scenarios/battle/tower_cellar5.py`
  replay exactly as `test_tower_cellar5.py` builds it; compare the whole `list[Said]` (`at`
  rounded to 2, `text`) with the stored file; `GOLDEN_REGEN=1` rewrites it.

### Task 0.4 (H): loop counts

**Files:** create `.../golden/test_loop_counts.py`, `.../golden/loop_counts.json`.

Wall time is not frozen (the tick-cost spans vary ±40% run to run). Frozen instead, per
scenario of `scenarios/loop`: the counts on the fake clock that `helpers.Play` already keeps
(`reads`, `moved_at`, `pressed_at`). The test replays each scenario and compares with the
stored counts exactly.

### Task 0.5 (C, then M with the user): more replays, or the deviation said

architecture.md §6.2 A asks for the replay widened to a set (the death, cows, Drifter Cavern
with the staff empty, a Chaos Sanctuary run, a quiet clear). A replay needs a hand-written
`Script` per battle (`tower_cellar5.py`: presses, loot, modes, busy spans, places — typed in,
not parsed), so:

- [ ] (C) Cut two fixtures from `inventory_tracking/runs/combat` with `combat/takes.py` `trim`
  where the script is cheapest — an attack-mode-only stretch with no pickup and no teleport (a
  quiet clear; a cows stand) — and write their `Script`s and log goldens as 0.3 does.
- [ ] (M) Report to the user what each further incident's script would cost and let them decide;
  record the answer in architecture.md §6.2 A. Until then the deviation stands there in words.

### Task 0.6 (M): the combat gate's scores

- [ ] Run the gate of `combat/plan.md` over the host's takes; save its table as
  `.../golden/GATE-base.txt` (host data, so M runs it; compared by M at each stage gate).

**Stage 0 gate (M):** suite green; `decisions.json` reviewed for coverage (every production
decision of architecture.md §1 has a kind); the xfail list pinned.

---

## Stage 1 — the arena

One closed world for the whole loop (architecture.md §6.2 C), in
`tests/inventory_tracking/scenarios/arena/`. **It is built from the two fitted models that
exist, not beside them:**

- the game the macro's inputs act on is `tests/inventory_tracking/macros/fakes.py` `Game`
  (hops with charge spend, Blade Warp, Echoing Strike with the cast cadence, the Quick Cast
  queue, swallowed clicks, belt keys, swap, walks, drops, the hover record) — the one
  `test_hunt`, `test_rotation`, `test_pickup` and `scenarios/loop` already use; `Arena`
  subclasses it, as `scenarios/navigation/harness.py` `WalledGame` does for real ground;
- the monsters are `inventory_tracking/combat/sim/monsters.py` (`Walker`, `Pack`, `Blow`,
  `Traits`: the client's think cycle, speed, blows by rank, enchantment and tier with their
  elemental parts, fitted to Tower Cellar 5 by `scenarios/battle/test_monsters_fit.py`),
  extended with what it says it lacks: ranged attackers, walls, blasts, auras.

Scenes of Stage 1 are **fights**: attack mode, pickup, belt, swap, in-fight moves. The teleport
step and exploring need a level card `Target` and `Level.rooms`; `Scene` carries `rooms` so
Stage 5 can add them, and Stage 1 does not play KP_4.

**File map**

| File | Responsibility | Who |
| --- | --- | --- |
| `scene.py` | the records of a scene and their JSON | H |
| `result.py` | what a play gave; the scorecard table | H |
| `moments.py` | rules that find moments in a take | H |
| `build_scenes.py` | CLI: takes → `fixtures/*.json` | H |
| `mobs.py` | `sim.monsters` made to answer to walls, range, blasts, auras | C |
| `game.py` | `Arena(fakes.Game)`: life and damage, moving monsters, potion effects, the osd rule | C |
| `driver.py` | production runner and hunter on the arena's clock; press scripts | C |
| `cut.py` | a take and a frame → a `Scene` | C |
| `calibrate.py` | a cut scene played with the player's recorded actions, held against the take | C |
| `scenes_threat.py` | the 16 threat scenes as arena scenes | C |

### Task 1.0 (M): what the briefs need and no agent may guess

- [x] Potion values (done 2026-10-12): `arena/potions.json`, by item class id, from the d2data
  dump (`pricing/raw/d2data/misc.json`: `calc1`, `len`). Not put into `tables.build`, which
  needs the game's install and is production's. A healing potion's points are before the
  class and Vitality factor, which the dump does not hold: the arena takes it as a parameter
  and calibration (1.9) fits it from the refills in the takes.
- [x] The belt is item class ids by cell (`macros/world.py` `Loot.belt`), not codes: `Hero.belt:
  tuple[int | None, ...]`; `Result.potions` carries the class id.
- [ ] Write the data-source table of Task 1.8 against three real takes and correct it.

### Task 1.1 (H): `scene.py`

```python
Point = tuple[float, float]
@dataclass
class Mob:
    unit: int; txt: int; at: Point; level: int
    life: float; full: float                 # points
    flags: int = 0; mods: tuple[int, ...] = (); tier: int = 0   # rank, enchantments, Herald tier
    mode: int = 1                            # monmode; 12 a corpse
    owner: int | None = None; ally: bool = False   # a companion of the character's
    immune: bool = False
@dataclass
class WeaponSet:
    codes: tuple[str, ...]
    resist: Mapping[str, float]              # 'fire','cold','lightning','physical' -> share let through
    teleport_charges: int | None = None
@dataclass
class Hero:
    name: str; at: Point; area: int
    life: float; max_life: float; mana: float; max_mana: float
    belt: list[str]                          # potion codes, 16 slots, '' empty
    sets: tuple[WeaponSet, WeaponSet]; hand: int = 0
    slots: tuple[int | None, ...] = ()       # skills on keys, as World.slots
    hex_purge: bool | None = None; ward: bool | None = None; consume: bool | None = None  # as world.Player
@dataclass
class Drop:
    unit: int; code: str; at: Point; quality: int = 0; gold: int = 0
@dataclass
class Scene:
    name: str; hero: Hero; mobs: list[Mob]
    ground: list[dict]                       # Walkable grids, as stance fixtures hold them
    doors: list[list]                        # raw door rows, as stance fixtures hold them
    rooms: list[dict] = field(default_factory=list)   # level.json rooms; empty: a fight-only scene
    drops: list[Drop] = field(default_factory=list)
    assumed: tuple[str, ...] = ()            # fields the source did not hold: 'belt', 'staff', 'drops', …
    source: dict | None = None               # {'take', 'frame', 't'} when cut from a take
    def copy(self) -> Scene
def dump(scene: Scene, path: Path) -> None
def load(path: Path) -> Scene
```

Tests: a scene round-trips unchanged; `copy` shares no list; `load` of a file with an unknown
key fails with the key named.

### Task 1.2 (C): `mobs.py`

Wraps `combat.sim.monsters.Pack` for a `Scene`'s mobs and adds, each with its test first:
walls (a walk goes by `travel.walked_way` when the straight line is barred — today a walk is a
straight line), ranged attackers (strike within their reach while `sight.clear_shot` holds;
today they stand), blasts (a corpse within `BLAST_RADIUS` of the character), auras (`boost`).
The rates of ranged, blast and aura come from the threat table as
`scenarios/threat/harness.py` takes them; the constants are moved here with their comments,
not copied. `test_monsters_fit.py` must still pass on the wrapped pack.

```python
class Mobs:
    def __init__(self, scene: Scene, rng: random.Random) -> None
    def tick(self, hero_at: Point, companions: Sequence[Point], resist: Mapping[str, float]) -> float  # points taken this tick
    def hit(self, unit: int, points: float) -> bool      # True: it died
    def monsters(self) -> list[Monster]                   # macros/world.py records of now
    def corpses(self) -> tuple[tuple[int, float, float], ...]
```

### Task 1.3 (H): `result.py`

```python
@dataclass
class Result:
    scene: str; seconds: float
    dead_at: float | None; cleared_at: float | None
    taken: float; kills: list[int]; casts: int; moved: float
    potions: list[tuple[float, str, str]]    # (seconds, code, who: 'serve'|'osd')
    charges: int; swaps: int; said: list[tuple[float, str]]
    @property
    def alive(self) -> bool
def scorecard(results: Sequence[Result]) -> str          # fixed-width, a row a scene, a totals row
def compare(before: Sequence[Result], after: Sequence[Result]) -> str   # rows that differ, worse marked
```

Only fields stamped by the arena's clock: nothing of wall time.

### Task 1.4 (H): `moments.py`

`def moments(take: Take, probe: Sequence[str] = ()) -> list[Moment]` with
`Moment(frame, kind, note)`; `Take` is `inventory_tracking.combat.takes.Take` (the reader).
Kinds: `death`; `burst` (30% of max life within 1.0 s, as `terror/bursts.py` SHARE/WINDOW);
`potions` (3 presses of belt keys within 10 s — the take's `keys` events); `long` (hostiles
within 30 units for 20 s); `stuck` (3 routine presses in 5 s with the character moved under
`teleport.MOVED` — routine presses are lines of the probe log, so only when `probe` is given).
*As briefed 2026-10-12:* `moments(take, *, belt_keys)` with `death`, `burst`, `potions`, `long`; `stuck`
needs the probe log's format and moves to Task 1.8 (C).
A take of schema 1 (no vitals) gives no `death`, `burst` or `potions`. Tests on hand-made
frame and event lists, one per kind and one for schema 1.

### Task 1.5 (C): `game.py`

```python
class Arena(Game):                           # tests/inventory_tracking/macros/fakes.py
    def __init__(self, scene: Scene, *, seed: int = 1, osd: HealingConfig | None = None) -> None
    def result(self) -> Result
```

Added to `Game`, each with its test first: the scene's ground and doors (as `WalledGame`);
`Mobs` ticked from the clock's `sleep`, their damage off the hero's life through the set in
hand's `resist`; the strike's damage on mobs (the blades as `scenarios/revivers/harness.py`
applies them: `mechanics/echoing_strike.cast`, the contact radius, the duplicate rule); a belt
key drinks with Task 1.0's values (a rejuvenation at once, a healing potion over its frames);
death (life at 0: the world shows the dead mode, the play ends); with `osd`, the production
`HealController` rule run on the arena's life each tick, its drinks marked `'osd'`.

Tests: a held strike on one mob in the open kills it (cast count recorded, not compared with
the stance harness — that one stands still with another aim); a mob in contact takes life; a
belt key heals; under 40% with `osd` a rejuvenation goes without the macro; two arenas with
one seed and the same inputs end equal.

### Task 1.6 (C): `driver.py`

```python
@dataclass
class Press: at: float; routine: str         # runner routine names
def play(scene: Scene, presses: Sequence[Press], seconds: float, *,
         build: object | None = None, osd: HealingConfig | None = None, seed: int = 1) -> Result
```

Built from `scenarios/loop/helpers.py` (`hunter`, `attack_mode`) and the wiring of
`MacroRunner._execute` (runner.py) for ATTACK and PICKUP — not from `replay.Replay`, which is
open loop. `run.prebuff_hands`/`battle_hands` are set from `routines.CHARACTERS` (from `build`
after Stage 3). The runner's wall-clock limits are patched for the play as `Replay.run` patches
`CARD_SECONDS`/`TRAVEL_QUIET`: `EXPIRES`, `THROTTLE` and the join deadline must not decide a
result. A TELEPORT press raises `NotImplementedError('Stage 5')`.

Tests: one mob and `Press(0, ATTACK)` ends cleared and alive; no press, nothing cast; two plays
with one seed give equal `Result`s, run ten times in a loop (the determinism test).

### Task 1.7 (C): `scenes_threat.py`

- [ ] Port the 16 scenes of `scenarios/threat/scenes.py` to arena `Scene`s on open ground.
- [ ] `test_scenes_threat.py` asserts only: each plays to its horizon with `[Press(0, ATTACK)]`,
  casts > 0, no `Abort`; its `Result` goes into the scorecard. The 13 behaviors stay strict
  xfails **on the threat harness**; whether production in the arena shows the same failures is
  written per scene in `fixtures/THREAT-in-arena.md` — where it does not, that is a finding
  for M, not something to make pass.

### Task 1.8 (C, then H): scenes cut from takes

What a take holds, and what a scene does without (Task 1.0 corrects this table first):

| Scene field | From | Otherwise |
| --- | --- | --- |
| mobs: place, txt, flags, life share, mode | the frame's monster rows | — |
| mob level, mods, tier | `combat/hurts.py`'s lookup (probe log `--probe` for takes before 2026-10-12) | level from the area; `assumed` |
| hero place, life, max life | the frame's `p` row (schema 2; 74 of 746 takes are schema 1) | schema 1: not cut |
| ground, rooms | the take's `level.json` | not cut |
| doors | the frame's `d` rows | — |
| belt, staff charges, hands, slots, drops | not in a take | defaults (belt full of the character's usual, staff 69, no drops), named in `assumed` |
| the player's casts, moves, key presses | `combat/sim/situation.py` `cut`; belt keys from `keys` events | — |

- (C) `cut.py`: `def cut(take: Take, frame: int, *, defaults: Hero) -> Scene`, the general
  form of `scenarios/stance/build_fixtures.build`.
- (H) `build_scenes.py`: CLI over `inventory_tracking/runs/combat` using `moments` and `cut` →
  `fixtures/<take>-<frame>-<kind>.json`, 20 per kind at most, deterministic. M runs it on the
  host and keeps what it keeps (a fixture is some 10 K; the set stays under 2 MB).

### Task 1.9 (C): calibration

```python
def calibrate(scene: Scene, take: Take, seconds: float) -> Fit
@dataclass
class Fit:
    scene: str; taken_arena: float; taken_take: float; kills_arena: int; kills_take: int
    @property
    def trusted(self) -> bool                # both ratios within TRUST = (0.5, 2.0)
```

The arena played open loop for the hero — its casts, moves and drinks are the take's — with
the mobs the model's. `test_calibration.py` writes the table to `fixtures/CALIBRATION.md` and
asserts only that it ran. **A scene with `trusted` false is never used for a safety
assertion**: the marker `needs_trust` skips it and says why.

**Stage 1 gate (M):** arena tests green; the determinism test green over 10 runs; the
calibration table read and its misses written into architecture.md §6 with what they imply
for `sim.monsters` (a C task to fit it further if the trusted share is under half);
`fixtures/SCORE-base.txt` saved; the arena suite's runtime measured and, over two minutes,
marked `slow` with a fast subset named.

---

## Stage 2 — contracts, the build object, the ratchet

**Files:** create `inventory_tracking/macros/build.py` (contracts and `Build`),
`inventory_tracking/builds/{__init__,generic}.py`, `tests/inventory_tracking/builds/dummy.py`,
`tests/inventory_tracking/builds/test_contracts.py`, `tests/inventory_tracking/builds/test_ratchet.py`.

### Task 2.1 (C): the contracts

```python
# inventory_tracking/macros/build.py — imports nothing from builds/
@dataclass(frozen=True)
class MoveFacts:
    here: Point; now: float; slots: tuple[int | None, ...]
    staff: Teleport | None; ground: Ground | None; doors: tuple; aspect: float
    last_used: Mapping[int, float]; failed: Mapping[int, float]   # skill -> clock time
@dataclass(frozen=True)
class Intent:
    name: str; reserve: int; may_swap: bool; may_wait: bool; distrust: float
    shuns: Callable[[Point], bool] = lambda spot: False
@dataclass(frozen=True)
class NoWay: reason: str
Leg = Step | NoWay                                  # travel.Step; never None
class MovementSet(Protocol):
    name: str
    def applies(self, facts: MoveFacts) -> bool: ...
    def leg(self, facts: MoveFacts, goal: Point, intent: Intent) -> Leg: ...
    def eta(self, facts: MoveFacts, goal: Point, intent: Intent) -> float: ...   # inf: no way
class Attack(Protocol):
    reach: float
    def policy(self) -> Policy: ...                 # combat/policy.py: Callable[[Observation], Choice | None]
    def dealt(self, origin: Point, focal: Point, foes: Sequence[Foe]) -> Mapping[int, float]: ...
                                                    # points one cast takes off each foe: what stance prices a place by
    def skills(self) -> tuple[int, ...]: ...        # what must be on keys for the mode to fight
@dataclass(frozen=True)
class Buff:
    skill: int; phase: Literal['prebuff', 'upkeep', 'fight', 'opening']
    due: Callable[[World, float], bool]
    on: Literal['self', 'monster', 'corpse', 'ground']
    needs: frozenset[str] | None = None
    worth: Callable[[World, Monster | None], bool] = lambda world, target: True
    caster: str | None = None                       # a name in Build.casters
class Tactic(Protocol):
    name: str
    def applies(self, pack: Pack) -> bool: ...      # terror/danger.py Pack
    def caution(self, base: float) -> float: ...
    def bars(self, spot: Point, pack: Pack) -> bool: ...
    def keep(self, pack: Pack) -> tuple[float, float]: ...
    def opens(self) -> tuple[int, ...]: ...
@dataclass(frozen=True)
class Build:
    name: str
    applies: Callable[[World], bool]
    attack: Attack | None                           # None: the build does not fight on its own
    movement: tuple[MovementSet, ...]
    buffs: tuple[Buff, ...] = ()
    tactics: tuple[Tactic, ...] = ()
    weapons: Loadout | None = None                  # routines.Loadout, moved here in Stage 3
    casters: Mapping[str, Callable] = field(default_factory=dict)
    settings: BuildSettings = BuildSettings()       # a pydantic Config; fields added by the stage that needs them
def choose(builds: Sequence[Build], world: World, fallback: Build) -> Build
```

`Tactic.first` (target order) is left out until Stage 7 names its shape; nothing in Stages 3–6
needs it.

**The attack surface is decided here, not in Stage 3.** Today the framework-to-be leans on
Echoing Strike in three places the contract has to cover: `controller.aim_choice` special-cases
`isinstance(policy, LinePolicy)`; `Hunter.better_stand` puts a `LinePolicy()` in place of any
other policy; `stance.taken` prices a place by `virtual_cast`'s blades. Task 2.1 lists each such
place (file, line) in a table in this plan and says which method of `Attack` replaces it in
Stage 3. Its proof is Task 2.5.

### Task 2.2 (H): `builds/generic.py` and the test build

- `generic.py`: `GENERIC = Build(name='generic', applies=lambda world: True, attack=None,
  movement=())` — sets are added in Stage 3 when `Walk` exists; until then the movement
  contract tests are vacuous for it and say so in their ids.
- `tests/.../builds/dummy.py`: `DUMMY` — a walker (`movement=(DummyWalk(),)` returning a straight
  `Step` of at most 16 units or `NoWay('too far')`) with `attack=DummyBolt()` (reach 20, a
  `NearestPolicy`).

### Task 2.3 (H): contract tests

`test_contracts.py`, parametrized over `[GENERIC, DUMMY]` now and every registered build later:

- `test_a_movement_set_answers_with_a_step_or_a_reason` — over a grid of `MoveFacts` (staff
  matrix × ground open / walled × goal near / far): `leg` returns `Step` or `NoWay` with a
  non-empty reason, never None, never raises;
- `test_eta_is_inf_exactly_where_leg_has_no_way`;
- `test_every_buff_skill_has_a_name_and_a_phase`; `test_a_caster_named_exists`;
- `test_settings_are_frozen_and_valid`;
- `test_choose_takes_the_first_that_applies_and_the_fallback_else`.

### Task 2.4 (H): the ratchet

`test_ratchet.py`: `test_nothing_specific_is_named_outside_builds`. By AST, not text (comments
and docstrings do not count): every `ast.Name`/`ast.Attribute`/import alias in
`inventory_tracking/macros/**.py` and `inventory_tracking/combat/**.py` whose identifier is in
`SPECIFIC`. `SPECIFIC` is derived, not typed: the module-level int constants of
`macros/skills.py` minus the generic `TELEPORT`, `ATTACK`, `SWAP_WEAPONS`, plus the names M
lists by hand with a reason each (`LinePolicy`, `virtual_cast`, `BLADES`, `BLADES_A_CAST`,
`DUPLICATE`, `CHARACTERS`, …) and any import of `combat.mechanics.echoing_strike`. The found
set of `(file, identifier)` is compared with `ALLOWED` in the test file: a pair not allowed
fails; an allowed pair no longer found fails too ("remove it from the list"). M fills
`ALLOWED` with today's findings.

### Task 2.5 (C): the second build fights in the arena

- [ ] `test_dummy_in_arena.py`: `play(scene, [Press(0, ATTACK)], 20, build=DUMMY)` on a
  one-mob scene — xfail, strict, with the reason naming what stops it today (the three places
  of Task 2.1's table). It goes green in Stage 3.7 and is that task's proof that the framework
  no longer positions every build by Echoing Strike's blades.

**Stage 2 gate (M):** contract suite green on both builds; ratchet green with today's list;
goldens unchanged; Task 2.1's table of the three places reviewed with the user if it shows the
`Attack` contract needs more than `policy` and `dealt`.

---

### Stage 2 results (2026-10-12), to be used when Stage 3 is detailed

- The contracts are `inventory_tracking/macros/build.py`; where they differ from the sketch above
  and why, and every place today's code leans on the Warlock (file, line, the method that
  replaces it, the risk), is in [framework-stage3-inventory.md](framework-stage3-inventory.md).
  `Attack` is `skill`, `reach`, `sees`, `aim`, `dealt`; `MovementSet` also has `jumps` and `wait`.
- The ratchet starts at 67 pairs (`tests/inventory_tracking/builds/test_ratchet.py`).
- What writing a second build showed the contract leaves open — each to be settled in the
  Stage 3 task that first meets it, by changing `build.py` and its contract test together:
  1. `eta` and `leg` are two calls that must agree; nothing makes them. Give sets one shared
     decision (a base class or a function both derive from) in 3.2.
  2. `NoWay` says "arrived" and "blocked" the same way; a caller that tries the next set on a
     block and stops on arrival has to tell them apart: a kind on `NoWay`, in 3.1.
  3. Whether `leg` may be asked of a set whose `applies` is false: say no, and have the
     navigator hold to it (3.2).
  4. A goal nearer than `Intent.short`: `NoWay` (arrived), not a step back (3.1).
  5. `Build.applies` with no character in the world (a loading screen): false, by contract
     and by `choose` (3.9).
  6. `Attack.sees` returning a changed `Observation`: a copy, never the one given (3.7).
  7. The buff contract test has run against no `Buff` yet; a caster's "ask again in N seconds"
     (five back-dated timestamps today) needs a field or a return value (3.5).

## Stage 3 — the Warlock moves into `builds/` (outline)

No change of behavior: after *every* task `decisions.json` is byte-identical (a task may edit
the adapter `golden/cases.py`, reviewed by M) and the pinned xfail list is unchanged; after the
last, the arena's `SCORE-base.txt` and the gate's `GATE-base.txt` read the same. Target layout:

```
inventory_tracking/builds/
  warlock/skills.py            the ids and names now in macros/skills.py (key resolution stays in macros/)
  warlock/movement.py          BladeWarp mode
  warlock/casters.py           summon_defiler, consume, engorge (from routines.py, rotation.py)
  warlock/buffs.py             the Buff rows that reproduce rotation.py's due-tests and routines.prebuff
  warlock/echoing_strike/attack.py    LinePolicy, virtual_cast, the blade constants, strike input
  warlock/echoing_strike/mechanics.py combat/mechanics/echoing_strike.py, moved
  warlock/echoing_strike/build.py     ECHOING_STRIKE = Build(...)
  characters.py                the CHARACTERS rows (Loadout)
```

| Task | Who | What | Depends on |
| --- | --- | --- | --- |
| 3.1 | C | pure movement choice: `Travel.jumps/stride/around` take `MoveFacts` instead of `Run`; callers build the facts; `golden/cases.py` adapted in the same task | 2.1 |
| 3.2 | C | the shared sets `StaffTeleport`, `OwnTeleport`, `Walk` and three intents `PLAYER_STEP`, `SEEK`, `OWN_MOVE` that reproduce today's five call sites exactly (architecture.md §4.3 table) | 3.1 |
| 3.3 | H | `warlock/movement.py` `BladeWarp` behind `MovementSet`, tests lifted from `test_travel.py` | 3.2 |
| 3.4 | H | `warlock/skills.py`: move ids; re-exports left in `macros/skills.py`, listed in the ratchet | 2.4 |
| 3.5 | C | the buff executor in `macros/` (from `Rotation.key/resume`, the retry rule) and `warlock/buffs.py` rows reproducing every due-test | 3.4 |
| 3.6 | C, then H | C moves Engorge, the Defiler's summon and Consume into `warlock/casters.py` in one change (they share `rotation.py`, `routines.py`, `hunt.py`); then H × 3 move and extend the tests, one test file each | 3.5 |
| 3.7 | C | `echoing_strike/attack.py`; `Hunter`, `controller.aim_choice` and `stance.taken` ask `Attack` (`policy`, `dealt`) at the three places Task 2.1 listed; Task 2.5's xfail goes green | 3.2, 3.5 |
| 3.8 | C | `combat/mechanics/echoing_strike.py` moved under the build; `combat/sim/` takes the cast model as a parameter | 3.7 |
| 3.9 | M | wire `choose()` into the runner; remove re-exports; the ratchet's residue listed with a reason each and shown to the user | all |

Order as run (2026-10-12): 3.1 → 3.2 + 3.3 (one task: the same files) → 3.5 + 3.6 → 3.7 → 3.4 (the
ids can leave `macros/skills.py` only when their last user in the framework is gone) → 3.8 → 3.9.
Done: 3.1 (`9f4fc28`), 3.2 + 3.3 (ratchet 67 → 64).

What may honestly remain outside `builds/` after Stage 3 (the residue, to be confirmed then):
`combat/hurts.py` and `combat/__main__.py` reports that name the strike in their output, and
data files under `combat/data/`.

## Stage 3½ — the arena's monsters refitted (before any safety verdict)

Added 2026-10-12 from Stage 1's calibration (architecture.md §6.2.1): 1 scene of 72 trusted.
Not needed by Stage 3, whose judge is the golden net; needed before Stage 4, whose judge is the
arena. `combat/sim/monsters.py` is production code that nothing in play calls yet, so a refit
changes no behavior in the game; the combat gate's table and `test_monsters_fit.py` are its
guards.

| Task | Who | What | Measure |
| --- | --- | --- | --- |
| R.1 | C | the ranged attacker: a missile with a flight and a chance to miss, a rate per type from the takes (`hurts.py` rows with a missile near) | Black Soul, Dark Archer, Temptress scenes' ratios |
| R.2 | C | melee: a chance to hit (`A1TH` against the character's defence and block), the main set's physical resistance read or fitted | Ice Spawn, Blood Clan scenes |
| R.3 | C | whom a monster goes for: the character against its companions, from the takes' path records (`TARGET_UNIT`) | the scenes under half |
| R.4 | C | the big single blows: an elite's and a Herald's reach and top blow, death novas of enchanted monsters | the 8 scenes with a drop the arena cannot deal; the death scene dies |
| R.5 | C | the arena's own: a walk, a hop and a warp take their time and the character can be hit on the way (`Arena.act`) | stance scenes replayed |
| R.6 | M | calibration rerun; the trusted share and what is still off written to architecture.md | more than half of the scenes with a ratio trusted, or the user decides what Stage 4 may be judged on |

## Stage 4 — safety (outline)

| Task | Who | What | Measure |
| --- | --- | --- | --- |
| 4.1 | C | osd burst rule (30% of the life within 1.0 s → a rejuvenation at once). `HealController.step` sees one `State` and keeps no history, and `PotionsController` runs under a ledger: where the life history lives is this task's decision, made with the user's rule that osd stays independent | `tests/.../automation/test_heal.py`; arena scene of the death with `osd` on |
| 4.2 | H | `combat/survival.py` (pure; the module architecture.md §4.4 names), first part: life lost per second over a window, refill events from a life history, belt supply → `Pressure` | unit tests on synthetic histories |
| 4.3 | C | `taken(spot)` in `combat/stance.py`: melee arrival, ranged line and range, blasts; `value = dealt − caution × taken`; `BuildSettings.caution` curve | goldens change only where `caution > 0`; with 0 they are identical |
| 4.4 | C | the veto: play ahead `DIE_SECONDS` with `combat/sim/monsters.py` (production code already) as the look-ahead — the threat harness's `Survivor`, on production records | the six standing xfails, one by one |
| 4.5 | C | the fight loop asks survival before each strike and step: reposition, break off (`Cancelled`-style preemption); latency trace of the break | arena; `scenarios/loop` reaction bound |
| 4.6 | C | `serve` drinking: the judgement in `combat/survival.py` (pure, from `Pressure`, caution, supply) + a key pressed beside the step in hand | arena scenes with both drinkers; potions row of the scorecard |
| 4.7 | M | host run with the user; fold evidence into `plan.md` | takes of the session cut into new scenes |

## Stages 5–8 (outline)

- **5 Navigator behavior.** The arena learns the teleport step first (C: a `Target` built from `Scene.rooms`, the
  TELEPORT branch of `MacroRunner._execute` in `driver.play`). Then `LowCharges` (C: time-priced, `BuildSettings.charge_seconds`), the
  rule at 15 replacing `WARP_CHARGES`/`LOW_CHARGES` (H: constants and tests), careful landing in
  `teleport.landing` from known monsters only (C), `Navigator.eta` (H), `Enigma` scenes (H).
- **6 Goals.** `macros/goals.py` pure: `Goal`, `arbitrate(facts, leash) -> Goal`, two clocks,
  commit window, progress-or-back-off (C for the design-carrying core; H for each goal kind's
  probe: `ClearZone`, `ReachMark`, `KillHerald`, `GatherDrop`); leash set by key in the runner
  (C); drop lanes (C); thrash tests as arena scenes where a goal cannot complete (H).
- **7 Swap and tactics.** Resistances per weapon set read from the game (C); the swap decision
  (H: pure comparison); `Swap` as an explicit leg (C); tactics cows / dolls / archers / Heralds
  (H each, one file and one arena scene each), their combination rule (C).
- **8 Buff plan features.** `needs` grouping and Call to Arms rows (C), `opening` phase reading
  caution and tactics (H), upkeep recast between fights (H).

---

## Self-review and review (2026-10-12)

- Spec coverage: §4.0 → Stages 2–3; §4.1 leashes → 6; §4.2 → 3.5, 8; §4.3 → 3.1–3.3, 5, 7; §4.4
  → 4, 7; §4.5 → 6; §6 → 0–1. Deliberately not planned: the route-level `leave` opt-in
  (Mephisto portal; architecture.md: "not built until a route asks for it").
- **Deviation from the spec, for the user:** §6.2 A asks for the replay widened to five
  incidents; Task 0.5 adds two cheap ones and prices the rest instead, because each needs a
  hand-written script.
- An independent review (Fable 5.1, read-only, 37 checks against the code) changed the plan in
  these places: the goldens go through `Hunter`-level entry points behind one adapter, so the
  move cannot break the net that judges it; the arena is built on `macros/fakes.py` `Game` and
  `combat/sim/monsters.py`, which the first draft did not know of, not as a third fake game and
  a third monster model; the ratchet works by AST and Stage 3 ends on a named residue, with
  `combat/mechanics/echoing_strike.py` and the simulator's cast model moved too; the `Attack`
  contract gains `dealt` and is proved by the test build fighting in the arena; wall-time
  bounds became counts; four tasks changed from H to C (1.2, 1.7, 3.6's cut, 4.1); the potion
  table and the take's data sources are settled by M before any brief is written.
- Still soft, to settle at each stage's entry: whether `cut.py`'s defaults for belt and staff
  are good enough for the potion scenes of Stage 4 (else the recorder has to start writing the
  belt), and how much of `sim.monsters` needs refitting once calibration has run.
