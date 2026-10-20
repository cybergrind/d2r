# Terrorized act loop — plan (2026-10-20)

The player, ~18:50 on 2026-10-20: "terrorize with worldstone shards whole act and go whole act, zone by zone — we
probably want to do this with stones that we have most … right now let's assume that we can use any stone with 90+
quantity — we want to kill act boss first for possible statue drop (probably we will create separate mode later, for
statue farming)". ~19:00: "for TZ/TZ+ modes we want to know how to handle whole terrorized act (when we terrorized it
manually with stone)".

Mechanics, sources and the in-game checks: [act-terrorize-findings.md](../../rca/2026-10-20/act-terrorize-findings.md).
In one line: a shard is **right-clicked in the inventory** in a Hell game with Terror Zones on, costs **one shard**,
and terrorizes its act's **manual zone** (every field level of the act, the boss's included) for **that game**
(community claim), on top of the rotation. Whether the client's terror service list (the one the tracker reads)
holds the act is **not yet known** — check 4 of the findings.

Standing rules this design keeps: we must not die (the safety and the drinker act on every look, as in every kind);
no game left with a valuable on the ground (the agenda's SIGHTED tier and the leave guard); keys and clicks only, no
memory writes; never a Ber Rune in a transmute (no transmute here); repairs and purchases from carried gold only (the
town visit as today).

## 1. The design in ten lines

1. A new loop kind `act` ("Terror act", HUD word `ACT1`…`ACT5` by the act chosen), an agenda kind like TZ/TZ+:
   `Kind(agenda=True, packaged=True, swaps_gheeds=True, home=PANDEMONIUM_FORTRESS)`, its own `metric` and a longer
   `game_seconds`.
2. Each game starts in the Fortress: **choose the shard** = the most-held class among 674–678 whose Materials-tab
   stack is ≥ 90 (`StashView.count`), ties to the cheaper shard; none ≥ 90 → the kind stops, cause `shards`.
3. A new game-level goal `TERRORIZE` (tier ERRAND, in town, before any excursion): at the stash, the Materials tab,
   one shard out to the inventory, the stash closed, a right click on it.
4. **Confirm**: the shard is gone from the carried items and the stack is one lower; then the service list holds the
   act's levels (if check 4 says it does) or, failing that, the first level's plain monsters carry the forced
   modifier. Not confirmed → no run in that act (the game ends, said, one retry next game, then stop).
5. The game's itinerary is the **act's manual zone** (from `desecratedzones-game.json manual_zones`), not the
   rotation's: `tzroutine.itinerary` over a merged `ActiveZone`.
6. **The boss excursion first** (Andariel 35→37, Duriel by the Canyon's tour to the true tomb's Orifice, Mephisto
   101→102, Diablo 107→108, Baal 129→132), then the rest of the act covered by `tz_routes.zone_route_plan` over the
   levels the boss trip did not cover, in waypoint order.
7. Each area is worked by the TZ+ policy the other agent is building (reasonable groups, elites, Herald spawns; big
   levels only big groups and elite packs) — the kind reuses `policy_of`, it does not fork it.
8. Room, the Gheed's swap, the town visit and act 3's end through the Fortress are the agenda's packages as today
   (`room_package`, `gheeds_package`, `game_end`).
9. The game ends when the itinerary has no excursion left (LEAVE_GAME, the leave guard first), or at the watchdog
   (`game_seconds`); there is no terror time-out inside a game (§1 of the findings, #8).
10. TZ/TZ+ learn the same table: a terrorized act (the player's own shard) and the rotating zone are matched
    together and run as one union itinerary instead of stopping the loop (§4).

## 2. The kind

`macros/loop.py`:

```python
ACT = Kind(
    'act', 'Terror act', 0, FIELD, PANDEMONIUM_FORTRESS, metric='elite and Herald kills an hour',
    game_seconds=ACT_GAME_SECONDS, agenda=True, packaged=True, swaps_gheeds=True, word='ACT',
)
```

- `levels` FIELD (as TZ): the act is decided per game by the shard, not by the kind.
- `word`: `ACT` until the shard is chosen, then `ACT<n>` (runner.py `run_badge` reads `Kind.word`; a per-game
  suffix comes from `Loop.terror_act`, a new field reset per game).
- `ACT_GAME_SECONDS`: 2700 s to start with (Act 1 has 37 levels; TZ games are capped at 1200 s,
  `TZ_GAME_SECONDS`); measured over the first games and set from their p90.
- `loop_kinds()` offers it behind `actloop.ENABLED` (False until the stage 3 checks are made live), like
  `tzloop.ENABLED`.
- Metric: default **elite and Herald kills an hour** (the TZ kinds' tool `elites.py --kind act`), statues counted
  and reported separately (`d2-loop-finds`). Open question Q1.

## 3. The steps, and the files each touches

| Step | What | Files |
|---|---|---|
| **S1 choose** | `choose_shard(view: StashView) -> int | None`: classes 674–678 with `count ≥ SHARD_FLOOR` (90), the largest count first, ties by `SHARD_ORDER` (Western, Eastern, Southern, Deep, Northern: the cheapest first, asks of 2026-09-18). Pure. The act is `calc1` = 1…5 (class − 673). A stack read as unknown (stash unread) is no choice: the visit reads the stash first. | new `macros/terrorize.py` (pure part); `game/records.py StashView` (read only) |
| **S2 take out** | At the Fortress stash, Materials tab shown (`stash.tab_point(MATERIALS_TAB)`): one shard to the inventory by the click check 2 finds; until then the known path — Ctrl + Shift + left click on the stack (one into the cube, `_until` it is the only thing there), then the cube's shard to a free inventory cell. Needs the Materials tab's slot rectangles: `build_rune_cube.layout` extended to `/advancedstash_materials/` (the node name read from `bankexpansionlayouthd.json`) and `rune_cube.json` rebuilt — also gives the statues' and keys' slots. Fails safe: anything unexpected puts the shard back onto its stack (`_runes_back`'s Ctrl + Shift + click) and the game runs as TZ+ on the rotation (said). | `macros/terrorize.py` (hands part), `macros/build_rune_cube.py`, `macros/data/rune_cube.json`, `macros/cube.py rune_slot` (or a `material_slot` beside it), `macros/visit.py` helpers reused (`_tab`, `_until`, `_holds_only`, `_runes_back`) |
| **S3 use** | The stash closed (or open: check 3), the inventory open, a right click on the shard's cell (`cell_point(rect, INVENTORY, …)`, `actuator.tap('Button3')`, as cube.py/junk.py); `_until` the shard's unit is gone from the carried items. Never a right click on any other cell: the shard's unit id is read just before. | `macros/terrorize.py` |
| **S4 confirm** | `Confirmed` when (a) the shard is gone and the stack is one lower, and (b) within `CONFIRM_SECONDS` the service list holds the act's grouped levels (`tz_groups.manual_zone(act).core ⊆ terror_levels`) — or, if check 4 shows the list never holds manual acts, (b′) the first excursion's first level reads terrorized by its plain monsters (`ZoneTracker.terrorized` votes). (a) without (b/b′): said `Macro: act: shard used, act N not read terrorized`, the game is left at once (no run at monster levels the loop did not plan), one retry next game, then stop (cause `terrorize`). The used shard is logged (`Macro: act: <shard> used for act N (stack A -> B)`). | `macros/terrorize.py`, `terror/tracker.py` (a read `levels_listed(areas)`), `macros/tzloop.py choose` |
| **S5 itinerary** | `tz_groups.installed_manual_zones()` (five `ActiveZone`s from `manual_zones`, `core` = the levels with a `zone_data_id`); `tzroutine.act_itinerary(act)`: the boss excursion (`BOSS_TRIPS[act]`), then `zone_route_plan` over the manual areas minus the boss trip's levels, excursions in the act's waypoint order. `Itinerary` unchanged in shape; `zone` = `Act<n>-Manual`. | `routes/tz_groups.py`, `macros/tzroutine.py`, `routes/tz_routes.py` (an `order` key for the greedy choice) |
| **S6 boss** | Boss excursions: Act 1 `Andariel` from 35 (`START_AT` already cuts Inner Cloister/Cathedral: no level handler there); Act 3 `Mephisto` from 101 (Durance 2) — the Red portal to the Fortress ends that trip (`WAYS_OUT`), so the next excursion starts from the Fortress by waypoint; Act 4 `Diablo` from 107; Act 5 `Baal` from 129 (the waves, the Worldstone Chamber); Act 2 **new route** `Duriel`: the Canyon's tour (`Tal Rasha's Tombs`) ending in the tomb whose Orifice the handler marks, `use('Orifice', 73)`, `level(73, fight('Duriel', 'Duriel'), loot(), leave())`. The boss is fought with the route's own fight (RUSH_THE_BOSS as Andariel's), policy ON_THE_WAY on the corridor levels. | `macros/tzroutine.py` (`BOSS_TRIPS`), `routes/catalog/act2.py` (Duriel), `levels/handlers/tal_rasha.py` (the Orifice as a `use` mark), `levels/handlers/` for Duriel's Lair (new: its preset and Duriel), `terror/bosses.py` (Duriel 211 exists) |
| **S7 zones** | The rest, zone by zone, with the TZ+ policy (`policy_of(area, trip, …)`): what the TZ+ agent ships is what this kind uses. Excursions joined by `PORTAL_TO_TOWN` → `WAYPOINT` as today (goals-plan.md open question 7). Areas without a playable excursion (Act 5's three pits, Inner Cloister/Cathedral, the Moo Moo Farm is not in the act) are skipped and said (`Itinerary.skipped`). | `macros/tzroutine.py produce` (unchanged), `macros/agenda.py` (unchanged) |
| **S8 town and room** | Unchanged: the town visit when due (`TOWN_ROUTINE`), the room package, the Gheed's swap package, act 3's end by the Fortress (`LEFT_FROM`). The S2/S3 stash stop is folded into the game's first town visit when that visit is due (one stash stop a visit, the player's 2026-10-18 ruling). | `macros/tzloop.py perform` (the `TERRORIZE` leg), `macros/visit.py` (a hook for the visit's stash stop) |
| **S9 end** | No excursion left → LEAVE_GAME (the leave guard: a valuable sighted is picked up first); watchdog `ACT_GAME_SECONDS`; the shard floor reached for every class → stop after the game (cause `shards`, said on the HUD). | `macros/tzloop.py choose`, `macros/loop.py` |

The new leg names: `TERRORIZE = 'terrorize act'` (agenda goal kind) and its leg `ACT_SHARD = 'Worldstone Shard'`
(loop.py `REPEATS[ACT_SHARD] = 1`: one try a game).

## 4. TZ/TZ+ with a terrorized act

The player uses a shard by hand; TZ or TZ+ is on. Today this **stops the loop** (findings §4): `match_active_zone`
wants exactly one rotating zone and the observed levels are an act, or an act plus the rotation's zone.

**Change** (`routes/tz_groups.py`, `macros/tzroutine.py`, `macros/tzloop.py`):

1. `installed_manual_zones()` — the five manual zones, `core` the levels with a Herald group (`terror/zones.group_of`
   not None; the tracker cannot read the others: 20, 45, 50, 73, 132).
2. `match_zones(observed) -> tuple[ActiveZone, ...]`: first every manual zone whose `core ⊆ observed` (an act is
   terrorized); remove its areas from `observed`; then `match_active_zone` on what is left (the rotation's zone,
   unless it lay inside the act, then nothing is left). Nothing matched at all → `()` (today's `None`). A partly read
   act (core not all listed) is not an act: it falls to the rotating match, as today.
3. `itinerary(observed)` plans the **union** as one `Itinerary`: the act's excursions (boss first, as §3 S5) and the
   rotating zone's, the act's first; `zone` names both (`Act4-Manual + Act1-Catacombs`). `policy_of` is unchanged
   (an area of the trip's zone is worked; the rest crossed).
4. `tzloop.zone_of` passes the same observed set; with check 4 negative (the list never holds manual acts) the
   observed set comes from the votes alone for the act, so an act is recognised only after its monsters were seen:
   then the act kind's own knowledge (S4: it used the shard) is the source, and for a shard used by hand a request
   says it — `request.py terror-act <n>` (the player, or a skill) sets `Loop.terror_act` for the current game.
5. The tracker card stays per Herald group (`ZoneTracker.lines`), unchanged.

Code paths it touches: `terror/monsters.py terror_levels` (read only) → `terror/tracker.py ZoneTracker.terrorized`
→ `appraisal/service.py` (passes `zones.terrorized` to `routes/progress.py Progress.wanted`) → `macros/running/legs.py
terrorized` → `LegHands.terrorized` → `macros/tzloop.py zone_of` → `macros/tzroutine.py itinerary` →
`routes/tz_groups.py match_active_zone` (+ the new `match_zones`) → `routes/tz_routes.py zone_route_plan`.

**First build step**: `installed_manual_zones` and `match_zones` with red/green tests from the installed table
(`tests/inventory_tracking/routes/test_tz_groups.py`): Act 4's core alone → `(Act4-Manual,)`; Act 4's core ∪
`Act1-Catacombs` → `(Act4-Manual, Act1-Catacombs)`; Act 1's core with the Catacombs rotating inside it →
`(Act1-Manual,)`; Act 1's core minus one grouped level ∪ the Black Marsh zone → the rotating match only (today's
behaviour); then `itinerary` over the union (`tests/inventory_tracking/macros/test_tzroutine.py`). No live change
until the itinerary test is green; then in-game check 4 decides whether step 4's request is needed.

## 5. Hotkeys

- **Now**: the kind joins the KP_6 triple-press cycle (`runner.py` count == 3 → `loop_kinds()`), after TZ+/TZ;
  `restart.py --kind act` and `.agents/skills/d2-loop-watch/tools/kind.py act` select it. The shard is never chosen by
  a key (the player: "not sure if we want to configure it with hotkeys … assume any stone with 90+").
- **Later**, if the player wants a choice: `kind.py act1 … act5` (the request carries the act; `Loop.act_wanted`,
  the shard floor still applies) rather than a new key; a fourth KP_6 press is free today (`count ≥ 4` says
  "nothing switched") and could cycle the act preference, with the HUD showing `ACT<n>` — only if asked.
- The statue mode the player mentions later is another kind on the same pieces: the boss excursion only
  (`act_itinerary(act, boss_only=True)`), the act chosen by the statue missing from the set.

## 6. Switches

- `actloop.ENABLED` (False → the kind is not offered).
- `terrorize.SHARD_FLOOR = 90` (the player's number), `SHARD_ORDER` (tie order), `CONFIRM_SECONDS`.
- `tzroutine.MANUAL_ZONES = True` (TZ/TZ+ recognise an act; False → today's single-zone match).
- `ACT_GAME_SECONDS`.
- `BOSS_FIRST = True` (False → the act's excursions in waypoint order only).

## 7. Tests (red/green, development.md)

- `test_terrorize.py`: `choose_shard` (most-held ≥ 90; 89 refused; ties by order; unread stash → None; no shard ≥ 90
  → None and the stop cause); the take-out and use against the `Town`/`Run` fakes (one Ctrl + Shift + click, the
  cube holds one shard, it goes to the inventory, the right click on its cell and no other, the shard gone →
  `Confirmed`; a second item in the cube → everything back onto the stacks, no right click).
- `test_tz_groups.py`: `installed_manual_zones` (five, levels as the installed table, cores without 20/45/50/73/132),
  `match_zones` (the four cases of §4).
- `test_tzroutine.py`: `act_itinerary` for each act (boss trip first; Act 1 from 35; Act 3's next trip from the
  Fortress after the Red portal; Act 5's pits skipped and said; Act 2's Duriel trip once the route exists, skipped
  and said before); the union itinerary.
- `test_tzloop.py`: an `act` game: TERRORIZE first in the Fortress, then the boss waypoint; a failed confirm → LEAVE
  at once and the retry rule; no excursion left → LEAVE_GAME after a sighted valuable is picked up; TZ with a hand-used
  shard (the act's levels listed) runs instead of `Abort('no terror zone is read …')`.
- `test_loop.py`: `loop_kinds()` offers `act` only with `actloop.ENABLED`; the triple press cycles to it.

## 8. Build order (smallest useful first)

1. **TZ/TZ+ recognise a terrorized act** (§4 steps 1–3): the player's hand-used shard stops being a loop stop and
   becomes a union itinerary. Pure code, no new clicks. Needs in-game check 4 only to know whether step 4 is needed.
2. **The in-game test** (findings §6) by the player, ~10 minutes: the take-out click, the use, the list, the
   duration.
3. **The shard leg** (S1–S4) as a hand request first (`request.py terrorize` in the Fortress: choose, take out, use,
   confirm, say), then the `act` kind with Act 4 (5 levels, routes exist: Diablo, Izual; the loop has played the
   terrorized Chaos Sanctuary) behind `actloop.ENABLED`; 30 clean games watched before it is left alone.
4. **Acts 1, 3, 5**: routes exist (Andariel from 35, Mephisto from 101, Baal from 129); the game length measured.
5. **Act 2**: the Duriel route (Orifice `use` stage, Duriel's Lair handler), played by hand-start first.
6. **Statue mode** (later, the player's): boss trips only, the act by the missing statue.

## 9. Open questions for the player (each with the default this plan takes)

- **Q1 The metric.** Elite and Herald kills an hour (the TZ kinds' tool), statues reported separately? Or experience
  an hour (TZ leveling's)? *Default: elite and Herald kills an hour.*
- **Q2 Which shards.** "Any stone with 90+" — Northern (0.17–0.57 Ist asks) and Deep (0.12) feed the Renewed facet
  recipes; Western/Eastern are 0.03. Prefer the most-held, ties to the cheapest? Or never Northern/Deep? *Default:
  most-held ≥ 90, ties cheapest; a shard at 99 is free (a full stack's next one is dropped).*
- **Q3 Danger.** A terrorized act puts every monster at ~95–96 (character + 2), Act 1's from 67–85. The danger
  model prices threats by monster type, not level. Start with Act 4 (5 levels, the terrorized Chaos Sanctuary
  already played by the TZ kind) and Act 1 (the Andariel route is the most played)? *Default: Act 4 first, then 1,
  3, 5, and 2 last (Duriel: a melee boss with Holy Freeze in a small lair, never fought by the macros).*
- **Q4 Act 5.** Baal needs the throne waves (route `Baal` played in TZ on 2026-10-20, rca throne-waves-findings) and
  then the Worldstone Chamber; the three red-portal pits are unavailable (portals not read). OK to skip the pits
  until they are readable? *Default: skipped and said.*
- **Q5 Act 4.** Diablo needs the five seals (the route has them). Izual is on the Plains (route `Izual`, walked out
  from the Fortress). Boss first means Diablo before the Steppes — fine? *Default: yes.*
- **Q6 Act 2.** Duriel's tomb is one of seven: the tour enters tombs until the Orifice is seen, so "boss first" may
  clear several tombs before Duriel. Accept, or Duriel only after the tour? *Default: tour until the Orifice, Duriel,
  then the rest.*
- **Q7 Game length.** A whole act is long (Act 1: 37 levels; Act 3: 27). If the watchdog cuts a game, the rest of the
  act is lost with the shard. Raise the cap to what an act takes (measured), or end the act at the cap? *Default:
  2700 s, then measured.*
- **Q8 When no shard is ≥ 90.** Stop the loop, or fall back to TZ+ on the rotation? *Default: fall back to TZ+ for
  that game, said on the HUD (the loop never stands).*
- **Q9 A carried shard.** Keep one shard in a reserved inventory cell between games to skip the stash stop at a
  game's start (the town walk is the slow leg)? *Default: no; one stash stop a game, folded into the visit when due.*
- **Q10 Shard and rotation together.** When the rotating zone is in another act, run both in the same game (the
  union), or the act only? *Default: the act first, then the rotating zone if time remains (the union).*

## 10. Built (2026-10-20, evening)

The coordinator's answers, accepted by the player: Act 4 first; the most-held shard at 90+, ties to the cheaper (Act 4
takes only the Deep shard `xa4`, class 677); no shard at 90+ → TZ+ on the rotation that game; a game cap of 2700 s
(measure it); the metric is elite and Herald kills an hour, statues reported separately; Diablo with the seals first,
then the Steppes and the Plains (Izual). The kind's key is `act4` ("Shard: Act 4", HUD word `ACT4`). The KP_6 picker's
placeholder `Coming('act', …)` stays until `loop_kinds()` offers it.

1. **TZ/TZ+ with a terrorized act: live since the 19:49 restart.**
   - `routes/tz_groups.py installed_manual_zones()`, `manual_zone(act)`, `act_of_manual`, `match_zones(observed)`:
     every act whose core is all read (the core is the levels with a Herald group; 20, 45, 50, 73 and 132 are never
     read), then every rotating zone whose core is all read among the levels left.
   - A partly read act is no act. Its groups wholly read are played meanwhile; a stray level is left out and logged
     (`read terrorized in no zone`).
   - `macros/tzroutine.py itinerary` plans the union: the act first and its boss's trip first (`BOSS_FIRST`,
     `ACT_BOSS_LEVELS`), then the act's levels that trip does not reach, then the rotation. `zone` names both
     (`Act4-Manual + Act1-Catacombs`).
   - Act 4: Diablo from 106 (106, 107, 108), then Izual walked out of the Fortress (104, 105). Act 1: Andariel from 35,
     then Outer Cloister 27 → Catacombs 1 (the cathedral handler, "unconfirmed" in its docstring), then the rest.
   - Switch `MANUAL_ZONES = True` (False: one rotating zone, as before). `tz_routes.zone_route_plan`'s tie-break no
     longer fails on a terminal outside a sub-zone.
   - The old stop `Abort('no terror zone is read in this game')` now comes only when nothing at all is read.
2. **The shard step** (`macros/terrorize.py`, switch `CLICKS = False`):
   - `choose_shard(view, act)`: pure. `terrorize(run, key, act, terrorized)`: at the stash (opened if shut), the
     Materials tab, one shard out by `TAKE_OUT` (`ctrl`: Ctrl + left click on the stack; `cursor`: a plain click,
     then a free inventory cell). Then a right click on its cell only (`USE_WITH_STASH_OPEN`), and the confirm: the
     unit is gone and the stack is one lower. Also read: whether the act's levels read terrorized within
     `CONFIRM_SECONDS`.
   - Stacks under 90 are never touched. A shard left on the pointer goes back onto its stack.
   - With CLICKS off it only reads the stacks and says what it would use.
   - The Materials tab's slots are in `macros/data/rune_cube.json` (`build_rune_cube.py` reads
     `/advancedstash_materials/`; the rune and gem slots are unchanged).
   - The request: `request.py terrorize` → `appraisal/service.py MACRO_ROUTINES` → routine `TERRORIZE`
     (`running/base.py`) → `running/execution.py perform`. Send it with the loop off: like any request, it cancels a
     run that is working.
3. **The `act4` kind** (`macros/actloop.py`, switch `ENABLED = False`; `loop.py ACT4`, `ACT_GAME_SECONDS = 2700`;
   offered by `loop_kinds()` only with `tzloop.ENABLED and actloop.ENABLED`).
   - Each game: the visit first when it is due (it makes room), then the waypoint to the Fortress if needed, then the
     `TERRORIZE` goal (leg `Worldstone Shard`, once a game).
   - A confirmed use adds the act to `Agenda.acts`. `tzloop.zone_of` plans that act's core whatever the client's list
     reads, because check 4 is still open.
   - From there on it plays as TZ+: Diablo's trip, then the Steppes and the Plains, with town visits and the room
     package as today. The game ends with no level left (after the leave guard) or at 2700 s.
   - No Deep shard at 90+, CLICKS off, or a use that did not take → TZ+ on the rotation that game. After
     `SHARD_FAILURES` (2) failed games in a row, the shard is not tried again until the service restarts (said each
     game).
   - A game joined in a field level (a restart) plays the zones read.
   - Log lines: `Macro: terrorize: …`, `Macro: act: …` (no watch tool reads them yet).
4. Tests: `tests/inventory_tracking/routes/test_tz_groups.py`, `macros/test_tzroutine.py`, `macros/test_tzloop.py`
   (the union, the partial read, the act4 games, the kind's registration), `macros/test_terrorize.py`,
   `test_request.py`.

To do after the in-game test:
- set `TAKE_OUT` and `USE_WITH_STASH_OPEN` from checks 2–3, then `CLICKS = True`, then `ENABLED = True`.
- If check 3 needs the stash shut, the leg needs the inventory key from the hands (`running/legs.py`, one line).
- Fold the shard into the start visit's stash stop.
- Acts 1, 3 and 5 as kinds (`ACTS`). Act 1's 37 levels pass `REPEATS[TZ_LEVEL] = 40`, so check that first.

## 11. Act scripts: one kind per act, its order as data (2026-10-20 ~23:00)

The player, ~22:50: "could you implement shards run for every act: act1: act1 shard -> catacombs 2 -> 3 -> 4 ->
andariel -> marsh -> tower -> countess -> rest of zones one by one; act2: act2 shard -> canyon of the magi -> tombs ...
-> duriel -> rest of tombs -> arcane sanctuary -> summoner -> rest of arcane sanctuary -> rest of zones one by one;
act5: act5 shard -> throne -> baal -> halls -> nihlathak -> rest of zones; act3: act3 shard -> durance -> mephisto ->
rest of zones ... we probably can separate some high level architecture into reusable framework, that will allow some
specialization and concrete points/steps to scripting".

1. **An act's order is data** (`macros/acts/act<N>.py`, one file per act): `SCRIPT = ActScript(act, steps, ready)`.
   The steps (`macros/acts/engine.py`):
   - `Trip(route, target, waypoint=None, crossed=AFTER)`: a catalogue route's trip to level `target` (the boss's), from
     `waypoint` or, by default, the route's waypoint nearest it. `crossed=AFTER`: the levels on the way are only
     crossed (ON_THE_WAY) and get their own trip right after, nearest the target first (`BOSS_NEAREST`'s rule);
     `WORKED`: worked on the way. `missing='why'`: the catalogue lacks the route; the step is skipped and said.
   - `Rest(levels=…, zone=…, route=…)`: the levels of a list, of an installed rotating zone (`Act1-Tower`), or of a
     route's scripts that no earlier step works, covered by `zone_route_plan` as today.
   - Then, always, by the engine: the rest of the act's levels, then the rotation (`itinerary`'s union, unchanged).
   - A step is any object with `label` and `plan(act: ActPlan)`: an act file may define its own step class (Act 2's
     tomb tour with Duriel inside) with the builder's helpers (`add`, `rest`, `skip`), never editing the engine.
2. **The engine** (`acts/engine.py act_trips`) gives what `tzroutine._route_trips` gives (catalogue trips, each with
   its crossed levels; the levels none covers), so `itinerary`, `Excursion`, `produce`, `policy_of` and the agenda
   are unchanged. `tzroutine._route_trips` takes a manual zone's trips from its act's script when the script is
   `ready` and `ACT_SCRIPTS`, `BOSS_FIRST` and `BOSS_NEAREST` are on; otherwise the generic boss-first plan as before.
   The scripts serve the act kinds and TZ/TZ+ with a hand-used shard alike.
3. **One kind per act** (`loop.py act_kind(n)`, `ACT_KINDS` act1…act5, "Shard: Act N", word `ACTN`, all on
   `actloop`): `loop_kinds()` offers an act's kind only when its script is `ready` (and `tzloop.ENABLED`,
   `actloop.ENABLED`); the KP_6 picker shows the others as `coming`. `actloop.ACTS` maps act1…act5; the shard is the
   act's (`terrorize.SHARDS`). restart.py and elites.py take act1…act5.
4. **Act 4** is `acts/act4.py`: `Trip('Diablo', 108)`, `Rest(route='Diablo')`; its plan line is pinned by
   `tests/inventory_tracking/macros/acts/test_act4.py` (the live plan of 22:00-22:39).
5. **The harness** (`tests/inventory_tracking/macros/acts/harness.py`): `plan_of(monkeypatch, act, rotation)` (the
   script forced ready) and `ActGame(act, monkeypatch, rotation).play()` → `Walk` (waypoints, level runs, kills, the
   shard, the legs) over test_tzloop's scripted game. The act agents write `test_act<N>.py` with it.
6. **How to add an act**: `macros/acts/README.md`. An act agent owns `acts/act<N>.py`, its test, and any new route
   (`routes/catalog/act<N>.py`) or level handler it needs; it sets `ready = True` when its test walks the act.
