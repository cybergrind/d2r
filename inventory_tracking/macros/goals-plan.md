# Goal queue and the Terror Zone leveling loop — the contract (2026-10-19)

Written for the player's request of 2026-10-19 ~01:57 ("spawn sub-agent that will carefully implement tz-leveling
loop … right now, I'm thinking that we can create some kind prioritized goals queue"). Code:
[agenda.py](agenda.py) (queue, stack, in-level choice), [tzroutine.py](tzroutine.py) (the TZ leveling routine: the
zone's itinerary and the goals of each area), [navigation.py](navigation.py) (the means in hand), [tzloop.py](tzloop.py)
(the KP_6 kind that executes the agenda). All of it is behind `tzloop.ENABLED` (False): the Andariel and Lower Kurast
loops run as before. Offline fakes are no proof of game behaviour: §9 lists what live play must check first.

## 1. What the player asked for

- **Metric**: elite kills per hour of play — champions, uniques, super uniques, Heralds (and act bosses, which the
  shard watch counts as uniques) killed per wall-clock hour of the loop, town, lobby and travel included.
- **Two terror zone modes** (ruling of 2026-10-19 ~02:12: "andy loop shouldn't focus on full clearing level. we're
  going to have separate mods: - full clear tz : for herald hunting - tz leveling: clear only elites/champs"): two
  KP_6 kinds, `tz` **TZ leveling** (leaders only: champions, uniques, super uniques, bosses, Heralds; white packs only
  where they block, guard a drop or hurt) and `tzclear` **Full clear TZ** (every hostile and every room: the Heralds
  come of the group's kills). The KP_6 loops (Andariel, Lower Kurast) never full-clear a terror zone: a `looped`
  run ignores the terror default (`Hunter.run_mode`, the main session's change of 02:12, kept here); the terror
  zone modes are explicit kinds, not the terror default. KP_1 by hand keeps its terror full clear.
- **Each kind has its own metric, and drops come first** (same ruling: "every loop has it's own metric, that it must
  optimize: boss kills/elites kill/opened chest. the only thing that has more priority - proper interactions with
  drops (we cannot run without picking desired items just with killing boss alone)"): `Kind.metric` — Lower Kurast
  chests opened an hour, Andariel kills an hour, TZ leveling elite kills an hour, Full clear TZ Herald and elite kills
  an hour (open question 8). Every drop tier is above every metric tier in the queue (§3), tested
  (test_agenda.py `test_drops_come_before_every_goal_of_the_metric…`, `test_a_pickup_near_a_pack…`).
- **Any terror zone**, with a generic adaptation: per-level knowledge where it exists, sound defaults where not.
- **A prioritized goal queue**: navigation, killing, exploration, pickups as goals of their own priority; a
  **package** of goals on a **stack** (LIFO) that is worked from the top until empty, then the queue resumes;
  "no goals left" is the explicit end of a game (Save and Exit, then the next game).

## 2. The model

Two granularities, one agenda per game (`agenda.Agenda`, reset when the game changes):

| Granularity | Who performs it | Goals |
| --- | --- | --- |
| **game level**: one KP_6 leg each | the loop (`tzloop.perform`) through the existing routines | `NEW_GAME`, `WAYPOINT`, `TOWN_ROUTINE`, `PORTAL_TO_TOWN`, `THROUGH_PORTAL`, `LEVEL` (work this area), `LOOT`, `PICKUP` (a remembered valuable), `NEXT_LEVEL`, `LEAVE_GAME`, `RESUME` |
| **in level**: one target per look of attack mode | the level run (`pursuit.py`/`hunt.py`), which asks `Agenda.in_level` at each look | `KILL` (an elite/champion/unique/Herald, a pickup's guard), `PICKUP` (the side drop), `EXPLORE` (an unexplored room), `NAVIGATE` (the stand for a Herald coming) |

A `LEVEL` leg posts the KP_1 level run for the area (`Pursuit.agenda`). At every look the hunter builds a
`LevelView` (leaders in sight and remembered alive, the omens, the side drop and the hostiles by it, the frontier
asked lazily, the passed goals) and the agenda answers with its target, which the hunter turns into the navigator's
place-goal (`goals.rest_of_level`: a `KILL` is a fight on its unit, an `EXPLORE`/`NAVIGATE` a place). With no
in-level target left, the area's **end goal** is the route's own stage (`goals.route_goal`: the boss, the object,
the door), which the hunter already pursues; the run ends at the door, after the boss (LOOT), or with nothing left,
and the loop's next leg comes from the agenda again.

**Queue + stack** (`Agenda.next`):

1. The stack's top, if the stack is non-empty. A `RESUME` on top is the package's end: popped and said, the queue
   follows at once (no leg is spent on it). The player's room example is one package:
   `push(PORTAL_TO_TOWN, WAYPOINT(Fortress), TOWN_ROUTINE(exit portal), WAYPOINT(the portal's town), THROUGH_PORTAL,
   RESUME)` — pushed in reverse, popped in this order (`agenda.room_package`). In act 4 the two waypoints drop out.
2. Else the queue's best goal valid in the view: the lowest tier, then the least cost (units from the character).
   The game-level part of the queue is **re-derived from the facts at every leg** (`tzroutine.produce` →
   `Agenda.refresh`): what the loop wants is a function of where the character is, the route's progress, the
   areas worked, the sightings and the room — the architecture's "re-plan, never resume" (architecture-history.md
   §4.5, 2026-10-12). Only what cannot be re-read is remembered: the stack, the areas worked, the in-level `KILL`
   goals of leaders seen (with their last place), the failures.
3. Else **`LEAVE_GAME`**: no goals left. It is never given while a valuable the loop would take lies on the
   ground (the sightings, `View.valuables`): that is a `PICKUP` goal first, and a `LEAVE_GAME` leg refuses to leave
   with one (`Abort`, cause 'room', and the runner's room rules: cube, trip, drop, then the stop for the player).
   Out of a game the only goal is `NEW_GAME`.

A goal is finished when its leg ends without a stop (`Agenda.done`: popped from the stack, dropped from the queue).
A leg that stops leaves its goal where it was; `Agenda.failed` counts it, and a goal failed `TRIES` times is
dropped and said (progress-or-back-off: no goal is retried forever, none starves those after it). The loop's own
`REPEATS` and the recoveries bound what is left.

**Safety is not a goal in the queue.** Survival, drinking, the arbiter's pricing and the veto act inside every look
of every leg (combat/harm.py, macros/drinking.py): a goal gives the heading, never permission to die. The player's
hand pauses the level run as today; KP_6 off stops the loop at once.

## 3. Priorities and preemption

In level (`Agenda.in_level`, first match wins; within a tier the nearest):

| Tier | Target | Why |
| ---: | --- | --- |
| 0 | a live Herald | "a Herald first, wherever the others stand" (hunt.py `rest_of`, HERALD_OMEN) |
| 1 | a pending Herald omen: the hostile nearest the spot within `omen_near`, else the stand by it | rca/2026-10-17/herald-findings.md |
| 2 | the side drop's guards: hostiles within `GUARD_NEAR` (12) of the drop or of the character, nearest first | **a pickup near a pack is ordered after the kill near it** (the player's example) |
| 3 | the side drop itself (the pickup rules' choice: a valuable within PICK_NEAR walked or LOOP_PICK_SECONDS by Teleport, gold, a potion) | "picking up items — goes into their own priority": before any travel to a farther pack; the drop tiers (2–3) are above every metric tier (the 02:12 ruling) |
| 4 | a live leader in the read (ON_THE_WAY: within `WAY_UNITS` 90 of the character; FULL_CLEAR: every hostile) | "KillGoal for every elite/champ that it discovers with priority for nearest" |
| 5 | CHEST: a closed super chest (objects.txt 397 `ConsolationChest`, "sparklychest"; levels/model.py `SUPER_CHEST`) in the read, or seen on this level and not yet opened, within `CHEST_NEAR` (60, the full clear's `SUPER_NEAR`), every policy; opened as the full clear's is (`Hunter.agenda_chest`: a USE of a `SUPER_CHEST` mark, a clearing goal); one seen open or tried `SUPER_TRIES` times is never a target again in the game | 2026-10-19: "we don't open intermediate goals, like superchests. probably we should add superchests to intemediate goals and open them along the way". After the leaders in the read (the metric; they come at a character standing at a chest), before the rest; the bound keeps a chest seen far off from sending the run across the level; its spill is then tiers 2–3 |
| 6 | a leader remembered alive within `REMEMBERED_NEAR` (45) | no back-and-forth across the level (the player, 2026-10-18 00:10) |
| 7 | COVER: the nearest unexplored room (`frontier`) | "exploration: acts as a target … exploration handler can add some points" |
| 8 | COVER: the leaders remembered farther, once the tour is over | |
| — | none: the area's end goal (the route's stage: boss, object, door) | "levels with bosses we end with killing the boss" |

Preemption that the hunter already owns and keeps: what is in the strike's reach is held (`pursuit.decide` `Hold`);
a pack that **blocks a passage** or stands where a goal's act is made is the fight first (`goals.first_fight`,
`clear_way` for leaders within CLEAR_WAY 30 with a clear line); a valuable Teleport reaches within
LOOP_PICK_SECONDS is a side drop taken now (`hunt.teleport_reach`); a goal with no strike and no progress for
CLEAR_SECONDS is passed for PASS_SECONDS (`goes_on`), and a goal left for another is not taken back for TAKE_BACK.
The agenda's targets go through that same machinery (`Hunter.cleared`), so nothing of it is lost.

Game level (`tzroutine.produce`, lower tier first):

| Tier | Goal | When |
| ---: | --- | --- |
| 0 | the stack | always first |
| 10 | `PICKUP` | a valuable seen in this area and still on the ground (sightings), the level run over |
| 20 | `WAYPOINT(Fortress)` then `TOWN_ROUTINE(exit waypoint)` | in a town at a game's start, the visit due (`Loop.visit_due`: room low with something to take away, keys/scrolls short, a repair) — "only in such cases" (the player, 2026-10-19) |
| 30 | `LEVEL(area)` | an itinerary area not worked yet, or whose route stage still is a fight/use/stand |
| 40 | `LOOT(area)` | the route's stage is `loot` (the boss dead): the pickup until nothing, then marked looted |
| 50 | `NEXT_LEVEL(area → to)` | the area worked, the excursion goes on: the route's `enter` stage into the next area |
| 60 | `PORTAL_TO_TOWN`, then `WAYPOINT(next excursion)` | the excursion is over and another remains (from town: the waypoint alone) |
| — | `LEAVE_GAME` | nothing left (and no valuable on the ground) |

## 4. Producers: who adds goals

- **The TZ leveling routine** (`tzroutine`): the itinerary of the active zone, the game-level goals of §3, the area
  policy (COVER / ON_THE_WAY) and, through `Agenda.observe`, a `KILL` goal for every leader the level run sees
  (kept with its last place until it is dead or gone where it was seen).
- **Level handlers and route stages** (`levels/handlers/*`, `routes/catalog`, `routes/progress.py`): an area's end
  goal and its way on. "Some levels already have their goals (like killing diablo/baal). And TZLeveling will just add
  another goal, before boss kill or navigating to the next level": the route's stage is the end goal, the routine's
  kills come before it (tiers 0–8 are all before "none").
- **Sightings** (`macros/sightings.py`): `PICKUP` goals for valuables seen this game and not off the ground; the
  `LEAVE_GAME` guard.
- **Room-making** (`runner._loop_stopped`'s room rules): the cube first (as today), then the room package on the
  stack (`tzloop.trip`, up to `TRIPS_A_GAME` a game, each only after one that made room: `Loop.may_trip`), then an
  item to identify dropped, then the stop for the player.
- **Supplies and repairs**: `Loop.visit_due` at a game's start in town.

## 5. The navigation controller

`navigation.means(Abilities)` names the class a far goal is planned by and the loop's move intent, from what the
character has: Teleport of its own (Enigma: every move, no charge) → staff charges while the carried gold pays for
them (`loop.teleports`: TELEPORT_ON 35% / TELEPORT_OFF 15% of the gold cap) and the staff holds more than
LOW_CHARGES → a free jump on a key (the Warlock's Blade Warp, from the build's movement sets: the framework names no
skill) → walking. The answer is `LOOPED_TELEPORT` or `LOOPED` (travel.py) with the class (HOPS / WARPS / WALKS)
for the log and the HUD. It wraps, it does not replace: every move is still the movement set's (`Ways.means`,
`Ways.leg`), which may walk where a hop cannot be made now. Sorceress Teleport is "Teleport of its own" (a skill on
a key with no staff); a class with neither walks.

## 6. Any terror zone

**The itinerary** (`tzroutine.itinerary`): the active zone is matched from the levels the client lists as
terrorized (`tz_groups.match_active_zone` over `ZoneTracker.terrorized`), then covered by catalogue excursions from
waypoints (`tz_routes.zone_route_plan`: waypoint → hops → terminal). An excursion with a blocked hop (a pending
stage such as act 5's red portals, a town connector with no stage, a tomb tour) is skipped and said; so is an
uncovered area. Areas on an excursion's way that are not terrorized are transit: only their `NEXT_LEVEL`.

**The area policy** (`tzroutine.policy_of`, the defaults, overridable per area in `POLICY`):

- **FULL_CLEAR** on every area for the Full clear TZ kind: every hostile is a target (tier 4/6/8), then every room.

- **ON_THE_WAY** for an area whose route leads on to a fight in the same excursion (a corridor to the boss) and for
  the boss's own level: leaders in the read and remembered near, then the end goal. Catacombs 1–3, Inner Cloister,
  Cathedral, Catacombs 4; Durance 1–2; Worldstone Keep 1–3.
- **COVER** everywhere else: explore to coverage (the frontier until none), every leader found, nearest first, then
  the end goal or the way on. This is the default for a level no handler knows: with no route script, no end goal,
  the area is over once the level run finds nothing left, and the excursion ends there.

**What per-level knowledge exists today**: route scripts for every terror-zone level in the catalogue (route
inventory: tz-leveling-route-inventory.md; three act 5 levels unavailable: their red portals are not read), level
handlers for exits, presets and bosses (levels/handlers/*), the open passage of the River of Flame into the Chaos
Sanctuary (`presets.open_passage`, carried by `pursuit.carried`), the Arcane Sanctuary's arm and the Chaos seals, the
Canyon's tomb tour (no single entrance: skipped by the itinerary until a tour is a goal of its own).

### Example: Catacombs terrorized (Inner Cloister, Cathedral, Catacombs 1–4)

1. New game in the Rogue Encampment; the visit not due. Queue: `WAYPOINT(Inner Cloister)` (the excursion's
   waypoint 32), prebuff on arrival.
2. Inner Cloister: `LEVEL(32)` ON_THE_WAY. The level run asks the agenda at each look: a champion pack in the read →
   `KILL` (tier 4); a Herald omen → its stand (tier 1); none left → the route's goal, the door to the Cathedral; the
   run ends there ("going through takes a press"). `NEXT_LEVEL(32 → 33)`: the press through.
3. Cathedral, Catacombs 1, 2, 3 likewise.
4. Catacombs 4: `LEVEL(37)`: the leaders in the read first, then Andariel (the route's fight, `RUSH_THE_BOSS` as
   the Andariel loop), then her stage is `loot`: `LOOT(37)` until nothing is left; then the stage is `leave`, the
   excursion is over, no other: **no goals** → `LEAVE_GAME` (sightings clear) → lobby → `NEW_GAME`.
5. The inventory full by a valuable on Catacombs 3: the cube first; then the package: Town Portal to the Rogue
   Encampment, waypoint to the Fortress, the visit (exit by the portal), waypoint back to the Rogue Encampment,
   through the portal, `RESUME`; the queue resumes with `LEVEL(36)`, the valuable taken by the level run.

### Example: Chaos Sanctuary terrorized (the zone `Act4-ChaosSanctuary`: level 108 alone)

The installed table makes the City of the Damned and the River one zone (106, 107) and the Sanctuary another (108).
The Sanctuary's excursion is the waypoint of the River (107), crossed (not terrorized: no `LEVEL` there), its open
passage walked by the level run itself (`pursuit.carried`: the run carried into 108), and 108 worked ON_THE_WAY, the
boss level's policy: the leaders seen first, each seal's boss is a leader (super unique) and so a `KILL` as it comes,
the seals and Diablo are the route's stages — the routine adds goals before them, it does not replace them. Diablo
dead → `LOOT` → no goals → leave. The River zone (106, 107) is COVER: no boss ahead on its excursion.

### Example: Worldstone Keep and Throne terrorized

Waypoint to WSK 2 (129); the route's way on through WSK 3 to the Throne. The waves are the route's
(levels/handlers/worldstone_keep.py); their leaders are `KILL` goals as they come. Baal, the Worldstone Chamber:
the route's last stage ("use Worldstone Chamber"), then no goals.

## 7. The existing pieces in the new model

| Today | In the model | What wraps what |
| --- | --- | --- |
| `pursuit.Pursuit` (the level run, leash FULL) | the executor of a `LEVEL` goal | `Pursuit.agenda` makes the run ask `Agenda.in_level` (via `Hunter.agenda_target`) instead of `rest_of` |
| `goals.Goal`, `goal_of`, `route_goal` | the navigator's place-goal for one move; the area's end goal | agenda targets become `goals.Goal` through `rest_of_level`, `first_fight` |
| `card_goal.CardGoals` | unchanged: the card's arrow follows the route's goal | a later change may show the agenda's top |
| `Hunter.side_drop`, `on_the_way`, `stay_by`, `restock`, `scarce` | the in-level pickup tier (2–3) | the agenda decides guards-first; the hunter still chooses the drop |
| `Hunter.rest_of` with `leaders_only` (Codex's `elite_hunt`) | the in-level choice for COVER | replaced by `Agenda.in_level` on an agenda run; kept for KP_1/TZ elite hunt |
| `loop.next_leg` legs (LK, Andariel) | each a game-level goal: NEXT_GAME = `NEW_GAME`, TO_THE_* = `WAYPOINT`, CHESTS/DOWN/FIGHT_ANDARIEL = `LEVEL`, PICK_UP = `LOOT`, PORTAL = `PORTAL_TO_TOWN`, TO_THE_FORTRESS = `WAYPOINT(103)`, TOWN = `TOWN_ROUTINE`, LEAVE = `LEAVE_GAME` | not migrated: LK and Andariel keep `next_leg` until the TZ kind is proven |
| `TRIP`, TO_THE_ENCAMPMENT, THROUGH_PORTAL | the room package on the stack | `tzloop.trip` pushes it; the same `Loop` trip bookkeeping (`trips`, `may_trip`, `_back_from_trip`) |
| the Gheed's swap (SWAP_OUT … GHEED_CHOOSE) | a two-trip package: [portal, Fortress, park the player's, back, through, pick the new one, portal, Fortress, Cain, choose, back, through, RESUME] | not migrated; on the TZ kind a refused charm falls to the room rules (open question 4) |
| `runner._loop_stopped` room rules | the producer of the room package | unchanged for LK/Andariel; the TZ branch pushes the package |
| `sightings.Sightings` | `PICKUP` producer and the `LEAVE_GAME` guard | unchanged |
| `levels/handlers`, `routes/progress` | per-area end goals and ways on | unchanged |
| `routes/tz_groups.py`, `tz_routes.py` (Codex) | the zone and its excursions | **kept** and used by `tzroutine.itinerary` |
| `routes/tz_leveling.py` (Codex) `FreshTerror`, `route_inventory`, `Metrics`, `choose_hunt`, `Coordinator` | — | `route_inventory` (via `tz_routes`) kept; the rest **left unused**: `next_area` picks one area, not an itinerary; `choose_hunt` is replaced by `Agenda.in_level`; `Metrics` by the log-based tool (§8) |
| `routes/tz_execution.py` `Slice`, `tz_runtime.py` `TzRuntime`, runner `tz_start`/`TZ_*` routines, KP_7 | — | **left unused** (still gated off): an external coordinator ticking one guarded action at a time fights the one-agenda-per-loop design and duplicates the KP_6 loop's game/town/trip handling; its town visit uses the pickup ledger (`TAKEN`), which the player ruled out on 2026-10-19 (volatile cells only) |

## 8. The metric

`.agents/skills/d2-loop-watch/tools/elites.py`: elite kills (terror-probe.jsonl `elite_kill`, once per unit and
session) over the hours of play of the loop of a kind (probe.log: on/off, the kind from `Loop run:` / the resume
line / the legs, the restarts' gaps and the stalls cut as andy.py cuts them). By kind of kill (champion, unique,
super, Herald), by area, by phase (lobby, town, travel, level, loot, trip) and per game; `--against SINCE UNTIL`
compares two windows with a 90% bootstrap interval over games. The default kind is `tz`; `--kind andariel` gives the
Andariel loop's elite kills an hour for a baseline; `--runs DIR` reads another checkout's sessions. Baseline, read
from the live logs on 2026-10-19: the Andariel loop 18:00–22:20 on 2026-10-18, **213.6 elite kills an hour** over
3.20 h of play (684 kills: 501 uniques, 182 champions, 1 Herald; 679 of them on Catacombs 4), 210.5 in 15:00–18:00
(no evidence of a difference). A TZ kind has to beat that on the same zone to be worth its longer games.

## 9. Before promotion (`tzloop.ENABLED = True`): checks in live play

Offline fakes prove the order of the goals, not the game. Before the first unattended TZ game:

1. **The zone read**: in town and on the first level of a game, `Macro: tz: zone …` must name the group the client
   lists (`terror_levels`), with no stale read from the game before; check across a rotation (the hour).
2. **One excursion by hand-start (KP_6 with the kind chosen)** on a zone whose route stages are played: the
   Catacombs (32→37) first — the Andariel loop played 35→37 for days. Check the waypoint 32 row, the doors 32→33
   (Cathedral), 33→34 (Catacombs 1), and that each `NEXT_LEVEL` press goes through.
3. **The level run with the agenda**: `Macro: agenda: target …` lines name leaders in sight and remembered; a
   champion pack 60–90 units off the way is gone for on ON_THE_WAY; the run ends at the door with no leader left;
   no stand longer than STILL_SECONDS.
4. **A COVER area** (Cold Plains, Black Marsh, Dark Wood: outdoors) for the frontier's cost: the tour's rooms, the
   kills/hour of the area; the Pit/Hole/Cave levels for a dead end with no way on (the excursion's end).
5. **The room package**: force a full inventory in act 1 and act 4; the order must read portal → Fortress → visit
   → back → through → `RESUME` in `Macro: agenda:` lines, and the valuable taken after.
6. **The leave guard**: a valuable left on purpose (out of the read) must keep the game (`PICKUP`, then the stop).
7. **The game watchdog**: TZ games are longer; `TZ.game_seconds` (1200 s) has to be measured against real games.
8. **The metric**: `elites.py --kind tz` against `--kind andariel` over the same day.
9. **Super chests** (tier 5, 2026-10-19): on a level with one (the Act 1 caves and crypts, the Spider Cave, the Act 2
   sewers, the Act 5 Ice Pool/Lava), `Macro: agenda: target Super chest (open, tier 5 …` once, then the open
   (`Opening Super chest` / `: opened`) and the spill picked up as side drops, with no second target line for that
   chest. The open is the full clear's routine (`super_chest_goal`, live since 2026-10-18) but has not yet run on an
   agenda run: a chest whose mark finds no object stops the leg (`Abort`, "… is not here"), counted in `SUPER_TRIES`.

## 10. Open questions for the player (defaults chosen, marked in code)

1. **ON_THE_WAY vs COVER for corridor levels** (Catacombs 1–3, Durance 1–2, WSK): default ON_THE_WAY ("finding each
   elite on the way to Andariel"); COVER may pay more elites an hour in a dense zone. Measure with `elites.py`.
2. **Ordinary monsters**: default only leaders are gone for; trash is fought where it is in reach or hurts (the
   arbiter's pricing). XP an hour may want more.
3. **After the boss**: default loot and leave, no full clear of the boss level after the boss (the Andariel loop's
   ruling, rca/2026-10-19/andariel-terror-phase-findings.md).
4. **A refused Gheed's Fortune** on the TZ kind: default the room rules, no swap (the swap is the Andariel loop's).
5. **The game's length cap**: default 1200 s (`TZ.game_seconds`), the watchdog's leave; the Andariel loop's 240 s
   would cut every zone.
8. **Full clear TZ's metric**: Herald kills an hour, elite kills an hour, or the Herald group's completion? Default:
   both reported (`elites.py --kind tzclear`, the `herald` column), the kind tuned by neither until ruled.
9. **Boss drops while the boss is in reach**: the hunter takes no side drop but potions while the run's boss is in
   reach (`buffs.QUIET_BY_THE_BOSS`, F3 of 2026-10-18), the drops after her death. The 02:12 ruling puts drops above
   the metric: default the boss's own fight keeps that exception (the drops are never left, only taken after).
6. **Rotation mid-game**: default the itinerary is planned once a game; a rotation mid-game finishes the game's
   itinerary (the draft plan's default) and the next game plans the new zone.
7. **Multi-excursion zones** (a zone covered by two waypoints): default Town Portal and the next waypoint; a Save
   and Exit and a new game may be faster for short excursions.
