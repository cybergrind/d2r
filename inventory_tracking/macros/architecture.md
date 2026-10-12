# Combat macro architecture (evergreen)

How the battle behavior of the macros is organised, what it cannot do yet, and where the changes
belong. Settled truth lives in the body; the history of each rule stays in [plan.md](plan.md) as
dated entries — log a pass there when this file's facts change. Started 2026-10-12 from the user's
steer ("do not rush into implementation, do a good overview"), after the Tower Cellar 5 death
(22:50, take 20261011T195037Z-25) and the Drifter Cavern / cows positioning incidents of the same
days.

## 1. What runs today (2026-10-12)

### The five keys (input/compositor.py, the one place that names keys)

| Key | Action | Runs |
| --- | --- | --- |
| Mod+X | `macro` | `routines.run_macro`: prebuff / game cycling by place |
| KP_4 | `teleport` | `teleport.step_toward`: one hop toward the level card's mark |
| KP_2 | `hunt elites` | `Hunter.seek`: one step toward the nearest elite, attack mode follows |
| KP_3 | `hunt any` | attack mode toggle |
| KP_1 | `pickup` | `pickup.pick_up`; with nothing to take: a container to open (`opening.py`), the sweep start, or a seek step toward any hostile |

### The runner (macros/runner.py)

One working run on its own thread; a request while it works cancels it, queues behind it, or pauses
attack mode for it (`waiting.py`: one entry per routine, taken by `PRIORITY`, dropped after
`EXPIRES`). Attack mode is a *mode*: steps pause it, its end resumes it. Every press is traced
(`latency.py`). The runner knows nothing about goals: it maps presses to routines.

### Attack mode (macros/hunt.py `Hunter`)

One long run until cancelled. Its loop: player input first (`sense`/`serve_move` — a left click of
the player's releases the strike and is re-clicked if a cast swallowed it); buffs due (`rotation.py`:
Hex: Purge, Psychic Ward; in-fight: Death Mark, Sigil: Lethargy, Engorge; between fights: Consume);
then nothing-in-reach → sweep step or idle log; else `fight`: one held strike input, the pointer
kept on the policy's line, broken off by the player moving, nothing left in reach, a step worth
taking, or 60 s. The sweep (`Sweep`) is the mode moving on its own after a pickup press with
hostiles near: up to FOLLOW_STEPS steps within FOLLOW_SECONDS. `gather` pauses the mode for a drop
on the way (not with a hostile within GATHER_CLEAR — the death's fix).

### The pure decision layer (combat/) — the split that already exists

- `policy.py`: *where to cast* — `LinePolicy` scores virtual casts over the observation
  (`observe()` builds it from a `World`), `NearestPolicy` is the historical baseline.
- `stance.py`: *where to stand* — `camp()` prices places within CAMP_REACH by expected damage over
  HORIZON seconds, minus walk/jump cost, rejecting spots with a hostile within KEEP_AWAY, crowds
  (CROWD_MOST within CROWD_UNITS), and landings a melee monster closes on before the first cast.
- `controller.py`: *fight mechanics* — `aim_choice`, `Aim` (whose the pointer is), `CastWatch`
  (held input health), `serve` (the player's click).
- `sim/`: replays recorded takes open-loop and scores a policy; the gate
  (`combat/plan.md`) is the measure. `hurts.py` derives who took the character's life from takes.
- The scenario replay (`tests/inventory_tracking/scenarios/battle/`): a whole recorded battle,
  production macro on the take's clock, compared line by line with the real log.

### Knowledge the behavior can already read

- `terror/tracker.py` (`ZoneTracker`): per-area kill counts vs population estimates, explored rooms,
  remembered live elites/heralds (`remembered`, `explored` are wired into `Hunter`), threat
  `traits` per unit.
- `terror/danger.py`: pack threat scores (hit × rate × reach, curses on the player). Consumed today
  only by `Hunter.tough` (swap to battle weapons) and HUD warnings — **not** by positioning.
- `levels/guide.py` + handlers: the level card's mark (boss place, door, unexplored room).
- `levels/routes.md` (phases 1–2 built 2026-10-12, not run in game): routes as chains of level
  scripts; stages `enter / use / stand / fight / clear / loot / leave`; progress as a pure function
  of facts. Execution is one press = one stage step through the existing keys.
- `macros/travel.py`: which jumps the character can make now (Blade Warp past its delay, staff
  Teleport by charges), `stride`/`around` toward a goal, `Step`.

## 2. The shape of today's behavior, honestly

The system is **press-driven stepping with one mode and an interrupt queue**. Every goal lives in
the player's head and enters through a key. Consequences:

1. **No goal memory between presses.** KP_4 hops toward the level card's mark; KP_2 seeks the
   nearest elite; KP_1 sweeps toward the nearest hostile. They share `Hunter` state but no common
   objective: the teleport step walks *past* packs it could kill, the sweep walks *away* from the
   route's mark after them. "Advance toward the goal while killing what is met" exists nowhere.
2. **Attack mode is location-reactive, not plan-reactive.** It fights what is in reach and stands
   where the fight started (plus sweep steps). It does not know the character is in a Terror Zone
   that wants a full clear, on a route whose next stage is a seal, or in a cows level where the
   right play is stand-off and distract.
3. **Safety is one-number-deep.** `GATHER_CLEAR` (fixed 12 units), stance's `KEEP_AWAY`/crowd rules
   (melee-closing only), and `tough` (swap decision) are the whole defensive model. Nothing reads
   the character's *life* during a fight, the macros drink no potion in battle (the pickup step
   drinks only to make belt room for a ground potion; the drinking that does happen is `make osd`'s
   own, apart from the macros and unknown to them — see 4.4), nothing retreats, and ranged threats (Black Souls,
   Temptress bolts — the Drifter Cavern lesson) do not shape where to stand.
4. **Movement-mode selection is scattered, not chosen.** Whether a hop is Teleport, Blade Warp or a
   walk is decided separately in `hunt.afoot` (seek), `hunt.warp_hop`/`empty_hop` (teleport step),
   and stance's jump pricing — three copies of "staff charges + warp delay + clear line" logic with
   slightly different rules (WARP_CHARGES vs LOW_CHARGES, different retry handling). A new movement
   source (Enigma, a second character with no staff) touches all three.
5. **The build is hardcoded.** Strike = Echoing Strike (`strike_input`), buffs = the Warlock
   rotation, weapons = `CHARACTERS['CybergrindAA']` with identical prebuff/battle sets. CtA on swap,
   a different class, TP-in-swap: each is a special case waiting to be written in three places.

## 3. The asks, mapped to gaps

| Ask (user, 2026-10-12) | What exists | The gap |
| --- | --- | --- |
| TZ farming = full clear to hunt Heralds | tracker counts kills/population; seek `any_hostile` exists (KP_1 fallback) | No "clear the zone" objective; nothing drives toward completion or the next Herald |
| Interweave killing with the level goal (Chaos seals → Diablo) | routes stages; sweep | Sweep/seek have no heading from the route; KP_4 and KP_1 pull in different directions |
| Safety vs efficiency: life vs threat, stand-off by threat level | danger.py scores; stance crowds | Life is not read in combat; stance has no ranged-threat or threat-scaled distance model |
| Ranged-mob positioning (Black Souls) | sight lines, hurts.py missile records | stance's `closes` models melee only; no kite/engage logic per enemy kind |
| Pluggable navigation (staff+warp+walk / Enigma+walk / walk-only / …) | travel.py `Travel` | Selection logic triplicated (seek/teleport-step/stance); no capability profile per character |
| Composable goals with priorities; TZ/level change modifies them | runner queue (per-press priority); routes progress | No goal objects; priorities are per-press, not per-objective |
| Buff maintenance by character (win-x prebuff + in-mode buffs) | routines prebuff; rotation | Hardcoded Warlock cycle; no data-driven buff plan |
| Clean separation / extensibility per player & gear | CHARACTERS loadout; skills.py key resolution | One loadout field pair; no build profile concept |

## 4. Design directions (for discussion; nothing here is decided)

### 4.0 The frame: a framework that names no skill, and builds that fill it

The requirement over everything below (user, 2026-10-12): "I prefer to have some framework
that will allow to configure every aspect of what and how we are going to do: healing, buffs,
positioning and so on. Probably a lot of things will be shared and that is good. But all
specific logic (Echoing Strike Warlock in our case) must live in the specific submodule and
modify / override / configure behaviors in the framework. Our goal is to think about such an
architecture that allows this kind of customization."

**Two sides, one direction of import.** The framework owns the loop and the contracts and
knows no class, skill or item by name; a build imports the framework and fills it. The
framework never imports a build: it is handed one.

| The framework owns (shared) | A build supplies (specific) |
| --- | --- |
| runner, press queue, goal queue, leashes (4.1, 4.5) | extra goal kinds, a changed priority |
| navigator, the `MovementSet` contract, the swap contract; the sets any class has: staff, Enigma, walk (4.3) | its own modes (Blade Warp), the order of its sets, the charge rule's number |
| the price of a place: its shape, the caution, the veto, how tactics combine (4.4) | the attack model: where to cast, what a cast does, its reach (Echoing Strike: `LinePolicy`, the blades' table); the caution's curve; its tactics |
| the buff executor, phases, grouping by weapon set (4.2) | the buff plan and the casters that are more than aim-and-key |
| the drinking judgement's inputs and shape (4.4) | its marks and slopes |
| simulator, scenario harnesses, contract tests | its scenarios and fixtures |

**Three depths of change**, the user's three words, each with its own form:

1. *Configure* — numbers. Typed, frozen settings as everywhere in this repo (`Config`,
   `with_overrides`): marks, distances, seconds, the 15 of the charge rule.
2. *Modify* — composition. Lists the build edits: add, remove or reorder a movement set, a
   buff, a tactic, a goal kind, taken from the shared library or its own.
3. *Override* — a part replaced whole behind its contract (a `Protocol`): its own attack
   model, a caster, a tactic, a movement set.

A build should need depth 3 only for what is truly its own (how it deals damage); if a
generic thing can only be had by overriding, the framework lacks a setting.

**A build is one object the framework asks**:

```
Build   applies(character) -> bool      # class, the skills on its keys
        attack       where to cast, damage, reach, the strike's input
        movement     [MovementSet, ...]
        buffs        [Buff, ...]
        tactics      [Tactic, ...]
        weapons      the sets and what each is for
        settings     stance, caution, drinking, charges: the numbers
        goals        additions to the goal kinds, if any
```

- *Choice*: the first registered build that applies; none → `Generic` (travel, pickup,
  potions, shared buffs; no fight of its own). Gear is not a build: the staff or Enigma, Call
  to Arms on the swap or not, are facts each part tests for itself (`MovementSet.applies`,
  `Buff.needs`).
- *Layers*: class before build before character — `builds/warlock/` (skill ids, Blade Warp,
  the casters of Purge, Ward, the Defiler, Consume, Engorge), `builds/warlock/echoing_strike/`
  (attack model, tactics, tuning, its scenarios), and a thin row per character for what the
  game does not tell (which set is for what). Each layer is the one below with changes.
- *Kept honest by tests*: contract tests the framework runs over every registered build (a
  movement set never answers with silence; every skill of a buff plan resolves to a key; the
  marks are ordered), and a test that no skill id or class name is spelled outside `builds/` —
  with the places that do so today listed in it, and the list only allowed to shrink.

`macros/` and `combat/` stay and *are* the framework; what is specific moves out of them into
`builds/` (today: `skills.py`'s ids, `rotation.py`, `routines.prebuff`, `CHARACTERS`,
`combat/policy.py`'s line policy and the damage table, `strike_input`, Blade Warp in
`travel.py`).

### 4.1 Keep the shape: presses ask, the mode does

The press-driven model is a safety property, not a limitation: the player is always one key away
from taking over, and every macro move traces to a press or to a mode the player toggled on
(plan.md's history is a long argument for this). The proposal is to give the *mode* goals, not to
replace presses with an autonomous agent. Concretely: the sweep already walks on its own after one
KP_1 — extend that idea so a mode, once on, pursues the current objective between fights instead of
only the nearest hostile.

**The leash: how far the mode goes on its own is set by the key that started it** (user,
2026-10-12, answering the autonomy question of §5.1: "KP_1 enables full; KP_4 / KP_3 (when
toggled on) / KP_2 enable middle"):

| Leash | Set by | The mode may, without another press |
| --- | --- | --- |
| *full* | KP_1 | pursue the top goal to its end: fight, gather, advance into empty and unexplored ground, room after room, until the goal's probe says done (zone cleared, mark reached) |
| *middle* | KP_4, KP_2, KP_3 toggled on | fight, gather, and go to what it *knows of* (hostiles seen or remembered by the tracker, drops); with nothing known it stops and says so — ground nobody has seen costs a press |

The leash is one more fact the goal queue reads (4.5), not a stored plan: the last of those
presses sets it, any input of the player's still wins over the move in hand, and KP_3 off ends
the mode whatever the leash. Today's sweep limits (FOLLOW_STEPS 12, FOLLOW_SECONDS 8) go: the
leash and the goal's probe replace them, and "progress or back off" (4.5) is what stops a mode
that gets nowhere. A press keeps its own meaning first — KP_1 picks up what lies there, KP_4
makes its hop — and sets the leash for what the mode does after.

**What the leash allows** (user, 2026-10-12):

- *Drinking and breaking off are the mode's own, on both leashes*: it may drink from the belt
  and leave a fight unpressed when the survival tiers ask (4.4). §5.2 and §5.3 are answered.
- *Objects inside the level are used on the full leash* (a seal, a chest); *a change of level
  waits for a press* — "sounds good for now, but we might need to tune it for some things (like
  Mephisto's farming, we may want to go through the red portal, but I'm not sure for now)". So
  the rule is a default a route can lift for one stage: routes.md's `leave` stage is where a
  route would say "this way out is taken unpressed". Not built until a route asks for it.
- *A goal's end stops the moves, not the mode*: the character stands, attack mode stays on, the
  end is said once ("zone cleared"); the next goal is not started unpressed.

### 4.2 A BattleProfile: who the character is, read once per game

One object, built from the game's own memory (skill slots, weapon sets, charges) plus the
character's row in a data table, answering:

- the strike: which skill, on which input (`strike_input` generalized — today it knows Echoing
  Strike only);
- the buff plan: an ordered list of (skill, condition, cooldown) — the Warlock's
  purge/ward/mark/sigil/engorge/consume cycle is one instance; CtA-on-swap is another ("swap, cast,
  swap back" as a buff step);
- movement capabilities: `[TeleportStaff(charges), BladeWarp, Walk]` today; `Enigma` and
  `WalkOnly` are other instances (see 4.3);
- battle weapons vs prebuff weapons (generalizes `CHARACTERS`);
- engagement envelope: default stand-off, preferred fight distance, how tough a pack must be
  before defensive rules tighten.

Everything in hunt/rotation/routines that currently names a Warlock skill reads the profile
instead. This is the extensibility mechanism for "per player / available gear": a new character or
a new item is a new profile row, not an `if` in the fight loop.

**Where buffs live today** (read 2026-10-12): three places, each with its own due-test, cast
and constants per skill.

| Place | When | Casts |
| --- | --- | --- |
| `routines.prebuff` (Mod+X) | a game's start, with the prebuff weapons | Summon Defiler, Consume, Hex: Purge, Psychic Ward |
| `routines.renew_consume` | between fights | Consume |
| `rotation.Rotation` | under the held strike | Hex: Purge and Psychic Ward kept up (read from the character's state), Death Mark (a target that outlives 4 casts), Sigil: Lethargy (under an elite, 10 s apart), Engorge (a demon hurt, or 15 s) |

What is already data: the key of a skill (slot from the game, key from the character's key
file, `skills.py`), and what casts Teleport (read from the worn items). What is code: the
skill ids, the one `CHARACTERS` row of two weapon sets, every condition above.

**The buff plan** (proposed): one ordered list per character, one executor.

```
Buff   skill
       phase     prebuff | upkeep (no hostile in reach) | fight | opening (before the first strike)
       due       the state is missing | so many seconds since | a target that fits
       on        self | a monster | a corpse | the ground under a monster
       needs     the weapon set it is cast with (None: whatever is in hand)
       worth     the check that it pays (Death Mark: the target outlives 4 casts)
       caster    None: aim and key, the shared one; or a named routine of its own
```

- The shared executor is what `Rotation.key`/`resume` already are: let the strike go, one aim,
  one key, the strike again. Retry and distrust (HEX_RETRY, HEX_DISTRUST) become one rule for
  every buff whose state can be read.
- Casts that are more than an aim and a key stay code and are named by `caster`: Engorge's
  look for a corpse under the pointer, the Defiler's summon spot and Consume.
- `needs` is how Call to Arms on the other set is said: Battle Command and Battle Orders are
  two entries with `needs = the prebuff set`. The plan groups what is due by `needs`, so the
  swap is paid once for all of them, and the swap itself goes through the swap contract (4.3):
  free in a prebuff and in upkeep, not in a fight.
- `opening` and the conditions may read the caution and the tactics (4.4): that is where "the
  curses before the first strike against cows" is written.

**The limit of the profile, said plainly.** A row covers *this build with other gear* (Enigma
for the staff, Call to Arms on the swap, another weapon) cheaply. Another *build* is more than
a row: where to cast (`LinePolicy`), the price of a place and the simulator are all Echoing
Strike's geometry and damage table. A second character can share travel, pickup, potions and
buffs from day one; its own fight needs its own policy and damage model behind the same
interfaces.

### 4.3 One Navigator, many movement modes

Promote `travel.py` into the single owner of "get me from A to B":

```
navigator.modes() -> list[Mode]      # applicable right now, cheapest first
mode.step(toward) -> Step | None     # None: not applicable to this leg
```

A `Mode` wraps a capability (Teleport-charges with its count, Blade Warp with its casting delay,
Enigma, walk) with its own applicability test (charges left? delay over? clear line?) and its cost
model (HOP_SECONDS vs warp time vs walk time — the numbers already measured in plan.md). Selection
is by cost with hysteresis, replacing the WARP_CHARGES/LOW_CHARGES thresholds that hunt.py and
teleport.py each half-own. Seek, the teleport step and stance's jump pricing all ask the same
navigator, so "staff ran dry mid-level" or "picked up an Enigma" changes behavior everywhere at
once. Each mode gets its own tests (the scenario replay harness is the fixture source).

**Where the mode is chosen today** (read 2026-10-12; five places, not three):

| Place | Asked by | Rule |
| --- | --- | --- |
| `Travel.jumps` | the sweep, stance pricing (`Hunter.better_stand` → `camp(jumps=)`) | Blade Warp first (delay over, not failed in JUMP_DISTRUST 30 s); Teleport only with the staff *in hand* and ≥ LOW_CHARGES (10), or as an own skill; never a weapon swap |
| `Hunter.afoot` | seek (KP_2, KP_1 fallback) | Blade Warp over a clear line whatever the staff holds, its delay waited out; a walk only under LOW_CHARGES; else falls through to a Teleport hop; at 0 charges `around` (the walked way) |
| `Hunter.warp_hop` | the teleport step (KP_4) | Teleport down to WARP_CHARGES (15), then Blade Warp where the line is clear; a failed warp is left alone 3 s (WARP_RETRY), not 30 |
| `Hunter.empty_hop` + `step_toward`'s `charges == 0` branch | KP_4, staff empty | Blade Warp, else a walk, else `around` |
| `teleport.take_teleport` | every Teleport hop | the only place that swaps to the staff |

`pickup.py` keeps its own copy of the jump reach (GOLD_UNITS = 26). There are also three *path*
planners, each tied to one way of moving: `teleport.Way` (a potential over the level's rooms and
tiles, for hops that ignore walls), `Travel.stride` (the straight line) and `travel.walked_way`
(Dijkstra over walkable cells within 70 units, written for the empty staff).

**What actually differs between those places is the caller's intent, not the capability.** The
skills, reaches and timings are the same everywhere; the differences are (a) the charges the
caller may spend — to the last for the player's own step, 15 before the step prefers the blade,
10 for a move the mode makes on its own; (b) whether a weapon swap is allowed (only the player's
step swaps); (c) whether the blade's delay is worth waiting out; (d) how long a way that failed
is distrusted. So the proposal splits three things that are tangled today:

```
Mode      what the character has: StaffTeleport(charges, in hand?), OwnTeleport (Enigma),
          BladeWarp(delay, needs a clear line), Walk.   From the profile (4.2), read per game.
            usable(facts) -> ok | why not        seconds(distance, facts) -> float
            spends: charges | mana | nothing     moves_over: anything | a clear line | ground
Intent    what the caller allows: reserve (charges to keep), may_swap, may_wait, distrust,
          shuns (places not to land: 4.4's veto).  Named constants, one per kind of caller.
Navigator leg(facts, goal, intent) -> Step | None     # the next move, by the cheapest usable mode
          eta(facts, goal, intent) -> seconds          # the same pricing without moving
```

- `leg`/`eta` are **pure** (facts in: slots, staff, clock of the last warp, failures, ground,
  doors); making the move stays where it is (`Travel.make`/`jump`, `take_teleport`,
  `step_walk`). Today `jumps`/`stride` take a `Run` only for the clock and the staff — that is the
  one seam to cut, and it makes the choice testable from recorded frames.
- The path belongs to the mode's `moves_over`, not to the caller: a hop that ignores walls plans
  over rooms (`Way`), a blade over a clear line (`stride`), a walk over ground (`walked_way`).
  The navigator asks each usable mode for its best leg and takes the least *time to the goal*
  (the leg plus what is left after it), within the intent.
- `eta` is what the goal queue's same-tier choice needs (a drop near against a Herald far, 4.5)
  and what stance already half-does through `Jump.takes`.
- A `Reposition` (4.4) is an intent like the others: no reserve, the fastest usable mode, and a
  `shuns` that bars landings near the threat.

**Rulings** (user, 2026-10-12):

- *One charge rule, at 15.* WARP_CHARGES and LOW_CHARGES collapse: with 15 or more on the staff
  Teleport is an ordinary mode for every caller; under 15 the blade and the walk come first.
  (Reading to confirm: under 15 a charge is still spent where nothing else leads and a press
  asked for the move, or the move is an escape — not for the sweep's own strides.)
- *The swap depends on what the character is doing, not on who asks.* "We have two modes: when
  we fast-travel — repeatedly press the button to reach the next destination — mobs have no time
  to engage, we teleport before they can burst us. When we are actually engaging it might be a
  different story, especially with too low health. We need something that actually feels good
  and lets us farm effectively."
- *Modes and the contracts for swapping them are an architectural requirement*, not a refactor
  detail: "architectural support to encode different modes and to define good contracts about
  how to swap them".

**Movement sets: the pluggable unit is the combination, not the single skill** (user,
2026-10-12: "for under 15 charges we may consider a separate `low charges + blade warp + walk`
that will calculate the cost to reach the next destination timewise"; the first steer listed
the same shape: "tp charges + blade warp + walk / enigma + walk / 0 tp charges + blade warp +
walk / low tp charges + blade warp + walk / tp charges + walk (another character) / only walk
— pluggable navigation classes with their specific logic and tests and logic to determine if
it is applicable; if not, choose new"). So above `Mode` sits a `MovementSet`: a class that owns
a combination of modes, its own route logic and its own tests.

```
MovementSet   applies(facts) -> bool             # is this the character's situation now?
              leg(facts, goal, intent) -> Step | None
              eta(facts, goal, intent) -> seconds
Navigator     the first set that applies, asked again at each arbitration
```

| Set | Applies | Route logic |
| --- | --- | --- |
| `Charged` | staff with 15 or more | Teleport over rooms (`Way`); the blade where it is as fast |
| `LowCharges` | staff with 1 to 14 | priced by time: the way by blade and walk against the way with a hop; a charge is spent only where it saves more than its price in seconds (a wall the walk goes far round), and for an escape |
| `Empty` | staff with 0 | blade and walk, `around` for walls (today's `empty_hop`) |
| `Enigma` | Teleport as an own skill | Teleport, no charges, no swap; mana is its limit |
| `StaffNoBlade`, `WalkOnly` | another character | the same contract, written when one exists |

The sets share the `Mode`s (one Blade Warp implementation, one walk); what each owns is how it
combines them. The contract for changing sets: `applies` is pure and re-read at each
arbitration, never mid-step; a change is logged and said once ("14 charges: by blade and walk
from here"); a set never refuses silently — `leg` gives a step or the reason there is none.
`LowCharges` answers the charge-rule reading above: the charge's price in seconds is the one
number, and an escape pays any price.

**Two regimes, and hands as state** (proposed from those rulings). The weapon set in hand is not
only a movement precondition: the teleport set leaves lightning at 8 and cold at 18 in Hell
(`Hunter.tough`), and a swap costs most of a second there and back with no strike and no move.
So "which set is in hand" is state the navigator and the fight share, and a swap is a priced,
exposed action — never a side effect of choosing a mode (today `take_teleport` swaps inside the
hop and `main_weapons` swaps back after MAIN_AFTER, each unaware of the other).

- *Travelling*: the character is being moved toward a destination, hop after hop, and nothing
  is being fought. The staff stays in hand, swaps are free, hostiles passed are not a reason to
  stop. Entered by a travel press (KP_4) or a goal's advance through empty ground.
- *Engaged*: a strike is held or a fight is about to be (hostiles in reach and the mode on). The
  battle set is wanted against anything `tough`; moves are by the modes the hand already allows
  (blade, walk; Teleport if the staff happens to be in hand).
- The regime is a pure function of facts (the last press, hostiles in reach, the strike held),
  recomputed at each arbitration like the goals (4.5), with a dwell so it does not flap.

**The swap contract** (proposed):

1. A mode declares what it needs in hand; the navigator prices a mode that needs a swap at its
   seconds *plus the swap's*, and returns the swap as an explicit first step (`Swap`, then
   `Step`) so the caller sees it, logs it and can refuse it.
2. An intent says whether a swap may be taken: always when travelling; when engaged only if the
   exposure is affordable — the swap's seconds times the damage rate being taken (4.4's pressure)
   against the life left. Low life with a pack on the character: no swap; the escape is by blade
   or walk, or by Teleport only if the staff is already in hand.
3. A swap is committed to: after one, the other direction is not taken for a dwell (the commit
   window of 4.5), unless `Survive` asks.
4. Leaving the travelling regime into a fight with the staff in hand is a decision made once, at
   the regime change — not re-asked every loop — and it is made **by the threat** (user,
   2026-10-12: "decide by threat level; sometimes it is faster to kill things than swap"). The
   rule is a comparison of life expected to be lost, not a list of monster kinds:

   ```
   stay  = rate(pack, staff set's resistances)  × seconds to kill on the staff set
   swap  = rate(pack, staff set's resistances)  × the swap's seconds
         + rate(pack, battle set's resistances) × seconds to kill on the battle set
   swap first when swap < stay by a margin; else strike first
   ```

   `rate` is danger.py's pack score, which already keeps physical and elemental damage apart;
   its `resisted` is a constant 0.25 today (the Hell cap) and has to become the resistances of
   the set in hand (danger-plan.md phase 6 names this). Seconds to kill come from the policy's
   own cast count (`Camp.casts`, the simulator's damage model) per set. A weak or nearly dead
   pack is killed on the staff; Gloams, Black Souls or a Herald at full life are swapped for
   before the first strike. This replaces `Hunter.tough`'s three hand rules and MAIN_AFTER.
5. A mode that fails says why and is distrusted for its intent's time; the navigator answers
   with the next mode or with "no way" and the reason — never silence (the thirteen "no Blade
   Warp or walk leads" presses in Drifter Cavern).

**The player's hop lands with care, and never waits for it** (user, 2026-10-12, on the
question of §5.4: "pick safer locations if you can, but note that often we will do multiple
presses to reach the destination"). KP_4 always hops; it is never refused. Among the landings
that leave about the same way to go — so that the count of presses to the mark does not rise —
the one further from what can hurt is taken. What the many presses mean for it:

- a landing in the middle of the way is left again within half a second, before a pack there
  has engaged: its safety is worth little, and nothing is paid for it in distance or time;
- the landing that matters is the one the character *stays* on: the last before the mark, or
  the one after which no press comes. The nearer the mark, the more the care weighs;
- the choice may not slow the hop. `hop_toward` reads the game lightly on purpose (no
  monsters, no doors); the care has to work from monsters already known (the tracker's, the
  last full read), not from a new read between the press and the key.

Migration, each step behavior-preserving and checked by the scenario replays
(`tests/inventory_tracking/scenarios/navigation/`, `.../battle/`): the pure choice with today's
rules as three intents (PLAYER_STEP, SEEK, OWN_MOVE) → the call sites moved one at a time →
`eta` → only then new modes and a retuned charge policy.

### 4.4 Safety as a first-class decision: the Survive / ClearDanger tiers

A small module attack mode asks every loop iteration, before any strike or step. It owns the top
two priority tiers (user's order, 2026-10-12) and chooses inside the second one whether the danger
is *cleared where it stands* or *repositioned away from*:

Two signals, answering two different questions (user, 2026-10-12: "threat level alone isn't a very
strong signal; it is mostly required to know *how to act*. When we take sustained damage and burn
potions, we must lean more into repositioning"):

1. **Threat → posture** (static, per pack): danger.py's pack score of what is engaged, ranged
   counted in full (its model already says a Black Soul's bolt lands from off screen). The score
   decides *how* to fight, not whether: a pack the character out-tanks is cleared aggressively —
   jump into it, stance prices damage dealt; one it does not is eaten gradually from a safe
   spot — stance maximising safety (distance, a wall or corner between, out of missile range).
   Cows and Black Souls then differ by data, not by code: cows = slow melee in big packs →
   stand-off, Death Mark + Lethargy and the companions work at range, never close quarters;
   souls = ranged → keep moving, fight from behind corners.
2. **Pressure → escalation** (dynamic, per second): life now vs N seconds ago (score.py already
   tracks points lost per combat second for the HUD card) and the potion burn rate (life refills
   in the life history: a rejuvenation's jump, a healing's ramp). Sustained drain with potions
   going shifts the decision toward repositioning whatever the threat score said — the fight as
   planned is not the fight as it is going. Thresholds are fitted from hurts.py rows (who burst
   the character, by pack type and the life at the time), not hand-tuned: the death in Tower
   Cellar 5 was 1051 points in under a second, but the failures before it were slow drains.
3. **Actions by severity**: keep fighting / reposition to a safe spot / break off
   (drinking is not a rung of this ladder: it runs beside it in `make osd`, below). Breaking
   off is: release the strike, step away — the runner already knows how to preempt a pickup for a
   teleport; a retreat is the same mechanism aimed at safety.

The stance side needs ranged-awareness regardless: `camp()` prices a place by damage *dealt*;
threat-aware pricing adds damage *taken* (missile range, melee closing pace — the cow fix's
`closes` generalized from monstats speed to per-threat reach).

**What is already there for this** (found 2026-10-12; the first survey missed it):

- `terror/exposure.py`: life lost per second against who stood there, from the probe logs.
  Run that day over 271 logs, 51,449 s with monsters in a screen:

  | Pack score | Seconds | Life lost a second | Worst second |
  | --- | --- | --- | --- |
  | 0–3 | 26,679 | 0.22% | 37% |
  | 3–6 | 11,846 | 0.32% | 34% |
  | 6–9 | 6,086 | 0.47% | 59% |
  | 9–12 | 2,848 | 0.65% | 43% |
  | 12–20 | 3,069 | 0.62% | 29% |
  | 20+ | 920 | 0.90% | 62% |

  The mean rises four times from the lowest band to the highest and not steadily; a second
  that takes a third of the life happens in every band. This is the user's remark measured:
  the score tells the posture, it does not tell when the fight goes wrong. Per type the model
  is off by up to five times either way (Hell Bovine 0.3 of its threat over 48,181
  unit-seconds, Black Soul 0.2 over 601, Stygian Doll and Hell Temptress about 2 when warned);
  act bosses are not in it (Diablo 2.1% a second, Baal 0.7%).
- `terror/bursts.py`: the seconds that took 30% of the life, with the packs around.
- `combat/hurts.py` over all 746 takes that day: 1855 drops of life, 1 death, 104 with one
  monster striking alone. One blow is small — median 26 to 112 points by rank and enchantment,
  the largest 320 (a plain monster), 252 for a pack leader — against a death of 1051 inside a
  second. Life goes to *several striking at once*, not to one big hit: what a place has to be
  priced by is how many can reach it together.
- `tests/inventory_tracking/scenarios/threat/`: a battlefield with incoming damage and 13
  strict xfails that state the wanted behavior with numbers. Six are about where to stand:
  the pincer (647 taken standing, 69 after 14 units north), low life in melee (dead in 0.8 s,
  alive after 7 units through the gap), low life under fire it cannot outkill, dolls on the
  character (1350 of blasts, 45 after a step back), a Herald pack of 1517 a second, a pack the
  blades cannot hurt. Seven are about which line to cast (shooters before a fat slow pack,
  immune monsters). Its `Survivor` prototype passes the standing ones by playing the fight
  ahead a few seconds and leaving through the widest gap when the character would be dead.

**One price for a place** (proposed 2026-10-12). Not a second scoring system beside `camp()`:
the same one, with what it lacks.

```
value(spot) = dealt(spot) − caution × taken(spot)          # over the same HORIZON
taken(spot) = Σ hostiles: rate × the seconds of HORIZON it can hit the spot
                melee: from when it gets there (distance over its speed; `closes` today)
                ranged: while it has a line and the range (a wall between: none)
                a corpse that explodes: its blast, if killed within its radius
veto         a spot where the fight played ahead ends with the character dead (`Survivor`)
```

`caution` is the one knob, and the two signals above set it: the posture from the threat
gives its base (a pack the character out-tanks: near 0, damage dealt decides, the jump into
the pack wins; one it does not: high, distance and cover win), the pressure raises it as life
goes and potions burn, and with nothing left to give it is all that counts — the place of
least `taken`, which is the retreat. So `ClearDanger`, `Reposition` and the last rung of
`Survive` (4.5) are one function at three settings, not three pieces of logic, and cows
against Black Souls differ by their rows (slow melee in numbers; ranged with a long reach),
as wanted. The pincer needs no rule: between two packs `taken` is the sum of both.

**Potions stay with `make osd`; the macros read them, they do not drink** (2026-10-12).
The first survey was wrong that nothing drinks in battle: `automation/heal.py` in the `make
osd` process drinks for the player below 65% (healing, 3 s apart) and below 40% (rejuvenation,
1 s apart), with retries and a ledger (`config.PLAYER_HEALING`), and does the same for the
mercenary. The user: "I would like to drink when we're not at full health, maybe the 90% mark
is good, but I don't want to waste all potions very fast; the main goal is to burst-kill
things without taking damage. Rejuvs for more severe situations. We have this code in `make
osd`; maybe we need to supersede it or make it work in parallel (I like having `make osd`
working independently to handle the hardest situations in a separate, non-lagging thread)."

**Reflex in `make osd`, judgement in `make serve`** (user, 2026-10-12: "`make osd` is always
running, but we can steer its values and do all the heavy lifting in `make serve` and keep
only urgent healing in osd"; and on what the judgement weighs: "whether we are experiencing
sustained damage or not, how bad the situation is, how many potions we have on the ground and
in the belt").

- *Corrected by the user the same day*: "I want to have the drink logic inside `make serve`
  first, and rely on `make osd` only for urgent situations." So there are two drinkers, and
  no steering between them:
- *`make serve` drinks by the judgement below*, pressing the belt keys itself (pickup.py
  already does, to make room). It is the first to act: its marks lie above osd's.
- *`make osd` stays exactly as it is*: its own process, its fixed rule (healing below 65%,
  rejuvenation below 40%), knowing nothing of `serve`. It is the backstop for when `serve`
  is busy in a step, slow, or judged wrong. One addition there (user, 2026-10-12: "for
  `make osd` 30% life sounds right"): a rejuvenation at once after a burst, 30% of the life
  gone within a second, whatever the level.
- *They meet only in the game.* `serve` sees every drink, whoever made it (the belt count
  falls, the life jumps or ramps), and counts it as its own: it does not drink on top of a
  potion still working. osd cannot see `serve`'s drinks and may add one when life goes
  under its floor right after — in the urgent case that is wanted, not waste.
- *The judgement* (`combat/survival.py`, pure, beside the caution it shares its inputs with):

  | Input | From | Moves `serve`'s marks |
  | --- | --- | --- |
  | sustained damage | life lost over the last seconds (score.py `LiveScore`) | none: the floor, life comes back by itself; sustained: healing toward 90% |
  | how bad it is | the caution, the life left, `Survive` active | bad: healing at 90% whatever the supply, the rejuvenation mark raised |
  | supply | the belt by kind, potions lying within reach (loot/ground.py) | plenty, or more on the ground: drink freely; short: back toward the floor |

  The marks and their slopes are fitted from the recordings, as the caution's are.
- The same judgement feeds the other way: potions going with the supply short raise the
  caution, and move a potion on the ground from the waypoint lane to the sub-goal lane (4.5).
- The drink is not a step of the runner's: it is a key pressed beside whatever step is in
  hand (as a strike is held while the pointer moves), so it neither waits for a step's end
  nor cancels one. `Survive`'s ladder stays reposition → break off. pickup.py's
  drink-to-make-room goes through the same judgement.
- Open: how `serve` tells a healing potion is still working (the ramp in the life history).

**Rulings on the price** (user, 2026-10-12):

- *The knob, plus tactics for some kinds*: "we need the ability to have special tactics for
  some mob types (cows / dolls / archers / nasty Heralds); otherwise we will probably be good
  with a single caution knob."
- *No fixed time at a place*: "not sure a hard cap will feel good; usually we should aim to
  deliver damage most effectively." So a move is braked by its own price only — the casts not
  made while going — plus the small margin that keeps two equal places from alternating
  (CAMP_GAIN today). No dwell timer.

**Tactics: terms added to the one price, not loops of their own** (proposed). A `Tactic` is a
small class per kind of enemy with `applies(pack) -> bool` and what it contributes:

```
Tactic   applies(pack)                      # by type, family, rank, enchantment, tier
         caution(base) -> float             # raise or lower the knob for this pack
         bars(spot) -> bool                 # places never stood at (a doll's blast radius)
         keep(pack) -> (least, most)        # the distance wanted from it
         first(targets) -> order            # who is cast at first (the dolls before they arrive)
         opens() -> skills                  # casts wanted before the first strike (see below)
```

Every tactic whose pack is in the fight contributes, and the terms combine (the bars are
united, the distances intersected, the highest caution holds): dolls among archers is both
tactics at once, where a tactic that owned the loop would have to be written for every mix.
A tactic that needs a move of its own (a Herald's mechanic) may add a goal to the queue (4.5)
like anything else; it still does not own the fight. First instances, each with its threat
scenario as the test: cows (stand off, never close quarters), dolls (not killed within their
blast), archers and souls (a wall between, or keep moving), Heralds by tier.

**Curses and the posture** (user: "not sure, what should work better?" — recommended): one
rotation, as today, with its conditions able to read the caution and the tactic. Death Mark
and Sigil: Lethargy are already cast in a fight when due; what changes is *when*: with the
caution low the strike opens (a weak pack dies sooner than a curse is cast), with it high or
a tactic asking (`opens`) they go out before the first strike and before the character steps
nearer. A second rotation per posture would be the same skills listed twice and two things to
keep right. The buff plan of the profile (4.2) is where the condition lives.

What the model cannot be trusted for, and so is not asked: the size of the next blow. The
rates are means, off by several times per type, and the death was 1051 points inside a second.
Hence the veto leans on life *seen* going (pressure), and the thresholds are fitted on
exposure.py and bursts.py rows, the per-blow sizes on hurts.py's.

Measure: the six standing xfails of the threat scenarios turn green one by one (strict: they
must be removed as they pass), the stance scenarios and the combat gate do not regress.

### 4.5 Goals: a queue of objectives above the queue of presses

Endorsed by the user (2026-10-12): "composable architecture that will use priority queue, and add
deadlines". The model generalises what `waiting.py` already is for presses: entries ranked by a
priority, each carrying a deadline, dropped or demoted when it expires, one owner of the executor
at a time.

**Two queues, one executor.**

- The *press queue* (`waiting.py`, exists): what the player asked for, ranked by `PRIORITY`, each
  press good until its `EXPIRES`. A press is the player's wish for now — it outranks any goal.
- The *goal queue* (new, `macros/goals.py`, pure): what the situation wants. The goal set is a
  pure function of (area, zone state from the tracker, route progress, life, drops): entering a
  Terror Zone pushes `ClearZone`, route progress pushes the next stage's goal, a valuable on the
  ground pushes `GatherDrop`, low life pushes `Survive`. Recomputed at every arbitration point —
  a step's end, a press, a cancel — never subscribed to events, so the simulator and the scenario
  replays can drive it from recorded frames.

**A goal is** (sketch):

```
Goal(name, priority,
     probe: Facts -> bool,            # done?
     step: (Run, Facts) -> None,      # one activation, through the routines that exist
     reaction: float,                 # may wait at most this long for its first input
     budget: float,                   # may hold the executor at most this long per arbitration
     on_expiry: drop | demote | escalate)
```

**Deadlines are two clocks, not one** (the press queue's `EXPIRES` is only the first):

- *reaction deadline*: how long the goal may wait before it acts. `Survive`: ~0.25 s (the death's
  burst took under a second). `GatherDrop`: seconds. `ClearZone`: none.
- *hold budget*: how long it may keep the executor before the queue re-arbitrates. A fight is
  interruptible by design (`Cancelled`); the budget is when the queue is *asked again*, not a hard
  cut. Expiry semantics differ per kind, unlike presses (which only drop): `Survive` escalates
  (reposition → drink → break off), `GatherDrop` demotes after holding the sweep too long,
  `ClearZone` never expires.

**Composition is opportunism, not parallelism.** The top goal runs; it may ask the queue "any
lower goal whose step is free right now?" Today's `gather` is exactly this pattern hand-rolled
(the sweep stops for a drop when no hostile is within GATHER_CLEAR): the goal queue makes it one
instance of a general mechanism. Upward preemption is the runner's cancel: `Survive` cancels a
fight step the way a teleport press cancels a pickup.

**The mode stays the substrate.** Attack mode remains the only thing that fights; goals give it
headings and interruptions, not a replacement: the top goal's heading steers `follow_on`/`toward`
(hostiles *on the way* win; empty space advances the goal instead of idling), the goal's `probe`
is the mode's termination condition, and KP_4 keeps meaning "advance the goal now, whatever it
costs" (the player's override).

The routes layer already defines the stage vocabulary the goals' `step`s call.

**Priority** (user, 2026-10-12): `Survive` > `ClearDanger` *or* `Reposition` (one tier; which of
the two is chosen from the threat — a pack the character out-tanks is cleared where it stands, one
it does not is fought from a safe spot) > `KillHerald` *or* `GatherDrop` (one tier, chosen by
closeness: a drop nearby beats a Herald far away) > `ReachMark` with clearing alongside (regular
levels) or `ClearZone` (Terror Zones) > `ReachMark` plain. Within one tier the choice is by
estimated cost — time to the drop and picked, against time to the Herald — which the Navigator's
per-mode cost model (4.3) gives for free. Both queues report through the same `say`/trace channels
as presses do today.

**No stored plans, no thrash** (user, 2026-10-12: "a responsible and interruptible loop that
adapts; it must not lag behind with stored actions or get stuck: one action interrupts another,
cannot complete, the next starts and is interrupted again"):

- *Re-plan, never resume.* The queue holds goal kinds, not plans. Every activation plans from
  facts read fresh at that arbitration; an interrupted goal re-plans from where the world is *now*
  when its tier wins again. Nothing stale can lag the loop, and an interrupted step leaves no
  half-plan.
- *Commit window.* A started step holds the executor until its budget ends or a strictly higher
  tier fires; a same-tier rival that just became cheaper does not steal mid-step (hysteresis —
  today's CAMP_GAIN/SWEEP_GAIN stance thresholds are an instance).
- *Progress or back off.* Each goal tracks progress (ground closed, life taken, kills); one that
  fails N activations or gains nothing in T is demoted for a cooldown — today's SHUN_SECONDS,
  GATHER_TRIES, WARP_RETRY and MISSES_IN_A_ROW generalised. A goal that cannot complete stops
  being re-tried instead of starving the tiers below it.
- *Escalation terminates.* `Survive`'s ladder (reposition → drink → break off) ends in leaving
  the fight; no rung loops.
- *Bounded arbitration.* The queue is re-read at a step's end, a press, a cancel, or a budget's
  expiry — not on every frame.

**Drops come in two lanes** (proposed 2026-10-12, answering "pickups as smaller goals before the
main goal — or a suggestion"):

1. *Sub-goal* — a drop worth preempting the current activity for (a rune, a unique: what
   `asked_step` stops a fight for today). It enters the queue as `GatherDrop` in the
   KillHerald tier, with a short reaction deadline, a small budget, `on_expiry=demote`, and a
   threat gate (today's GATHER_CLEAR, made threat-scaled by 4.4).
2. *Waypoint* — a drop worth a bent path but never the executor (gold, potions, medium loot). The
   stride toward the current goal is routed through it when the detour costs under a bound (the
   Navigator prices it) and the spot is safe. The teleport step's `worth_a_stop` (hop detours to a
   valuable before continuing) and the sweep's `gather` are today's hand-rolled instances. This is
   the side-action mechanism, in from day one (user, 2026-10-12).

The same drop moves between lanes with circumstance: a potion in a clear room is a waypoint; the
last rejuvenation with life low and a pack incoming is a sub-goal.

Upward preemption is the runner's cancel: `Survive` cancels a fight step the way a teleport press
cancels a pickup.

### 4.6 Where the pieces land (no new runtime layers)

| Piece | Lives in | Talks to |
| --- | --- | --- |
| BattleProfile | new `macros/profile.py` (data) | hunt, rotation, routines, travel |
| Navigator / modes | `travel.py` grown up | hunt seek, teleport step, stance pricing |
| Survival | new `combat/survival.py` (pure) + hunt loop guard | danger.py, hurts.py thresholds |
| Threat-aware stance | `combat/stance.py` | danger.py, mechanics/tables (missile ranges) |
| Goal stack | `macros/goals.py` (pure probes) + runner glue | routes progress, terror tracker, journey |
| Verification | sim gate; `tests/.../scenarios/battle/` per incident | unchanged |

The invariants to keep: player input always wins (actuator Abort, `sense`/`serve_move`, sweep
ends on the player's click); decisions pure in combat/, game reads in macros/ (the simulator and
the scenario replays stay valid); every rule cites evidence (a take, a timestamp) in plan.md.

## 5. Open questions for the user

1. **Autonomy ceiling.** *Answered 2026-10-12, with questions 2 and 3: two leashes by key,
   drinking and breaking off allowed, level changes pressed — see 4.1. Open: the potion
   threshold and column of question 2, and which routes lift the level-change rule.* The
   question as first put: With a goal stack the mode can clear a whole TZ level after one KP_3.
   Is that wanted, or should unattended advance still require presses (today's sweep is 12 steps /
   8 s)? A middle form: advance-while-fighting is free, advancing into *empty* space stops for a
   press.
2. **In-battle potions.** *Answered 2026-10-12: yes, by `make osd`, not by the macros — 4.4.*
   May the macro drink from the belt on its own (threshold? which column?),
   or only ever reposition and leave drinking to the player? The belt hotkey row is proven ground
   (pickup.py drinks to make room).
3. **Retreat authority.** May the mode break off a fight and step away without a press when the
   survival guard fires? (Recommended: yes, with `say` + trace, since every retreat is reviewable
   in probe.log and the takes.)
4. **KP_4 semantics under goals.** *Answered 2026-10-12: always hops, safer landings among equals — 4.3.* Keep KP_4 as "one hop toward the mark whatever it costs"
   (player override, as today) or let the navigator refuse a hop that lands in a pack (the death's
   scenario had teleport pressed 0.3 s before dying — it would have landed *deeper* in the pack)?
5. **Scope of the first build profile.** CybergrindAA only, with the profile seam in place, or a
   second real character at once to keep the abstraction honest?
6. **Order of work.** *Settled 2026-10-12: safety first, and before it the harness (§6)
   and then the move to framework and builds (4.0) with no change of behavior. After those:*
   (1) the burst rejuvenation in osd; (2) the price of a place with `taken`, the caution and
   the veto — the six standing xfails; (3) `serve`'s drinking; (4) the navigator: the pure
   choice and the movement sets as they behave today, then the rule at 15 and the careful
   landing; (5) the goal queue, the leashes and the two drop lanes; (6) the swap by threat
   (needs the resistances per weapon set) and the tactics; (7) the profile and buff plan.
   The first suggestion was: profile + navigator first (pure refactor, no behavior change,
   everything measurable by the existing replays), then survival (the death-prevention value),
   then goals/TZ. Confirm or reorder.

## 6. Tests: the harness comes before the framework

Ruling (user, 2026-10-12): "Framework first. But we need to have tests for it; a good test
harness that will help us to determine whether the end logic is working correctly is crucial.
Also, we will need to extract some situations from battle recordings and do simulation tests;
make sure that we keep this in mind." So the order of §5.6 gets two steps in front: the
harness, then the move to framework and builds with no change of behavior, then the safety
work in the order given.

### 6.1 What exists (read 2026-10-12): seven worlds, each with one thing in it

| Harness | The world | Monsters | Answers |
| --- | --- | --- | --- |
| `combat/sim` (the gate) | a recorded take | recorded paths, open loop | what a cast policy takes off them |
| `scenarios/stance` | 39 moments cut from takes, with the ground | stand still, do not strike | how fast a place-strategy clears |
| `scenarios/threat` | 16 scenes built by hand (13 strict xfails), open ground | walk at the character and strike at a rate | damage taken: the order of kills, leaving |
| `scenarios/revivers` | built by hand | come back | |
| `scenarios/navigation`, `explore` | recorded levels | none | hops to a mark against a reference |
| `scenarios/battle` (replay) | one whole recorded battle | as recorded, open loop | does the production macro do again what it did |
| `scenarios/loop` | — | — | tick cost, reaction time |

The gap: nowhere does the *whole* decision play against monsters that move and strike on real
ground. Stance has the ground and no danger, threat has the danger and neither ground nor
production code (its `today` stands still; its good players are prototypes), and the replay is
exact only until the macro does something new — from there the record no longer follows, so it
can show that nothing changed and cannot show that a change is better.

Two more that the first reading of 2026-10-12 missed and an independent review found: a
closed-loop fake game already exists for the macro's side — `tests/inventory_tracking/macros/fakes.py`
`Game` (hops with charges, Blade Warp, the strike's cadence, belt keys, swap, walks, drops),
which `test_hunt`, `test_pickup`, `scenarios/loop` and `scenarios/navigation` play production
code against — and monsters that walk and strike by themselves exist in production code,
`combat/sim/monsters.py`, fitted to the Tower Cellar 5 take. So the gap is narrower than "no
closed world": it is that the fake game has no damage to the character and its monsters do
not act, and the monster model has no walls and no ranged attackers. The arena below joins
the two and adds exactly that. The staged work is in [framework-plan.md](framework-plan.md).

### 6.2 Three kinds of test, for three questions

**A. Nothing changed** (the net under the move to framework and builds). The replay, widened
from one battle to a set (the death, cows, Drifter Cavern with the staff empty, a Chaos
Sanctuary run, a quiet clear), each held line by line against its recorded log; with them the
39 stance moments' results, the navigation routes' hop counts and the combat gate's scores,
frozen before the move and compared after every step of it. A step of the move is done when
all of them read the same.

**B. The contracts hold** (the framework's own). Contract tests run over every registered
build: a movement set never answers with silence, every skill of a buff plan resolves to a
key, marks are ordered, a tactic's terms combine. And a second build that exists only in the
tests — a walker with one plain bolt, a dozen lines — on which the framework's suites run too:
the cheapest proof that the framework does not lean on the Warlock.

**C. The end logic is right** (the new piece): **the arena**, one closed world for the whole
loop.

- *What is in it*: the ground with its walls and doors; monsters that behave (melee comes by
  the walkable way, ranged shoots while it has a line, corpses explode, raisers raise, auras
  boost) and strike at rates from the threat table; the character with life, the belt, the
  staff's charges, both weapon sets with their resistances; drops on the ground; time in game
  ticks.
- *What plays in it*: the production framework with a real build, through the same seam the
  replay already drives it by (the `Run`, a world that answers reads, an actuator that takes
  keys and clicks). Not prototypes beside the code: the code.
- *What it tells*: alive or not, life lost, time to clear, potions and charges spent, moves,
  casts, whether the goal was reached. Tests assert orderings and bounds against a reference
  play ("near the best wanted decision", as the threat tests do), not exact numbers.
- *Scenes from two sources*: built by hand (the 13 threat scenes move in first), and **cut
  from recordings** — the stance fixture builder made general: a take and a moment give the
  places, the life shares, the ground, the doors, the drops, the belt and the character's
  life. After the cut the monsters follow the model, not the record: that is the price of a
  world that answers to what the code does.
- *Which moments*: found by rule, not by hand — every death, every burst (30% within a
  second), runs of potions, a press that moved nothing several times, a fight over some
  length; and every incident the user reports, as plan.md already cites them by take and time.
  New sessions add candidates; a candidate becomes a test when its expectation is written.
- *Whether the arena may be believed* — **calibration tests**: each cut scene is first played
  with what the player really did, and the arena's life lost and kill times are held against
  the take's. A scene the model misses by more than a bound is marked and not used to judge
  safety. exposure.py found the threat model off by up to five times per type; the strike
  rates of the arena are fitted to the recorded blows (hurts.py), and this is the test that
  says how far that has come.

**The scorecard.** One table over all scenes — deaths, life lost, seconds to clear, potions,
charges — printed before and after a change, as the corpus score is for the appraisal engine.
The six standing xfails of the threat scenarios become arena scenes and go green one by one
(strict: removed as they pass).

### 6.3 In the game

Latency traces (latency.jsonl) for every new path that preempts: a break-off must reach its
first input as fast as a teleport press does today. The probe logs and takes of each session
feed 6.2 C's candidates.
