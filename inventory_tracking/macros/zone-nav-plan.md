# Zone navigation: plan (2026-10-21)

The player, ~09:20 on 2026-10-21, after three small dungeons of a terrorized Act 3 (Durance of Hate 1, the Forgotten
Reliquary with 28 hostiles, the Forgotten Temple) were marked done in under a second because their level map was not
loaded on arrival (another agent is fixing that race): "I think we need some global (zone level navigation system) and
zone level goals (like `fully_explored`) / so, if we get into one smaller level, we will return back to global level,
explore it further and clear smaller dungeons (all, if there are many) / and global zone level isn't getting marked as
fully explored, until all smaller dungeons are also cleared".

Design only. Nothing here is built. Code paths are as of 2026-10-21 ~09:30. `pursuit.py`, `hunting/moves.py`,
`tzloop.py` and `runner.py` were being edited by other agents when this was written: check them again before stage 0.

## 0. Today (checked against the code and probe.log)

- A zone is a list of **excursions**: waypoint, then levels, then a terminal (`tzroutine.itinerary`, from
  `tz_routes.zone_route_plan` or an act script's `acts/engine.py act_trips`). Excursions are joined by
  `PORTAL_TO_TOWN` and then `WAYPOINT` (`tzroutine.produce`). The Act 3 plan line (probe.log 08:57:43, run
  `runs/alt-d/20261021T055642Z-49f05219`) has 15 trips from 8 waypoints. Upper Kurast (81) appears in 4 of them
  (`[81, 82, 98]`, `[81, 82, 99]`, `[81, 96]`, `[81, 97]`) and was entered from its waypoint at 09:05:31, 09:08:05,
  09:08:51 and 09:09:11.
- **"Level done" is set when the character leaves a level, not judged from what was done there.** `agenda.finish`
  is called in `tzloop.perform` on `NEXT_LEVEL` (the level left), on `PORTAL_TO_TOWN` (the excursion's end), and on
  `skip_door` (a failed door: the trip's terminal). `produce` asks for a `LEVEL` run only while
  `runs < RUNS_AN_AREA and (runs == 0 or stage in WORKED_BY_RUNS)`. So for a temple (stage `clear`, never judged),
  one run that ends for any reason ends the level. At 09:09:02 the Forgotten Reliquary's run stopped with "no level
  map for this level yet". The next goal was the Town Portal, and 96 was "done" 0.2 s after arrival. The same happened
  to 97 at 09:09:18, and Sewers 1 had the same stop at 09:11:03 (it survived only because a later run followed).
- **What a child-then-hub pattern looks like today.** The Canyon of the Magi tour (`routes/model.py tour`/`back`,
  `tzroutine.Excursion.tours`, `tzloop.tour_back`) takes each tomb by the nearest entrance not yet entered and leaves
  it by its way back (`back('Canyon of the Magi', 46)`). That is a one-hub depth-first search, special-cased for one
  route.
- **What a level remembers for the game.** The tracker (`terror/tracker.py ZoneTracker`) keeps, per area: the rooms
  of the level (`level_rooms`), the rooms explored (`explored`, read by `Hunter.explored`), and the hostiles alive and
  where they are (`positions`, `leaders`). It also has a `store` and `restored` across service restarts. On re-entry
  the tour goes on where it stopped: at 09:08:05 the log says "the tour has no stop on level 81: 80 rooms, 80
  explored". The agenda keeps per game `worked`, `finished`, `kills`, `chests` and `wayless` (`macros/agenda.py
  Agenda`). The route's stage per level is in `routes/progress.py Progress`.
- **Measured from the 8 latest runs' probe.logs:** from the Town Portal leg to the next leg in the field after the
  waypoint takes a median **8.5 s** (p25 7.3 s, p75 9.8 s, n=37). The walk across an already-explored parent to the
  next entrance adds a median **6.6 s** (n=14). So one waypoint re-entry costs about **15 s**. The in-place
  alternative (the child's way back, then a walk to the next entrance) is about 4 to 8 s for a one-floor dead end.

## 1. The design in ten lines

1. A **zone graph**: the zone's levels as nodes, rooted at waypoint levels. Edges are the static links
   (`levels/presets.py LEVEL_LINKS`, levels.txt Vis slots, which hold both directions) and borders
   (`routes/links.py BORDERS`, plus live `Room.leads_to`). Each node gets one parent, its entry (how it is entered
   from the parent) and its way back up.
2. The **roots and their order** come from the act script (`ActScript` steps give the roots, the boss first, and
   which levels a root owns) or, for a rotating zone, from `zone_route_plan`'s waypoints. The children come from the
   graph.
3. **Per-level goals, judged and not assumed:** `explored(L)` (the map is loaded and every room with a way is
   explored), `worked(L)` (the policy's targets are met: leaders, groups, super chests, the route's stages and boss),
   and `fully_explored(L) = explored ∧ worked`. Then `cleared(L) = fully_explored(L) ∧ every in-zone child
   cleared-or-blocked`. A root is done when it is cleared. The zone is done when every root is.
4. A level is **never done because it was left**. A level whose map never loaded has 0 rooms and is not explored,
   which also guards against today's race.
5. **Traversal:** depth-first from the root's waypoint. Work the parent. Go into each child not cleared (nearest
   entrance first, a boss child first), clear it and its own children, then come back up by the child's way back (the
   stairs or warp to the parent, which the static links hold for every warp). Then go on in the parent.
6. **Town Portal only for town needs** (the room package, the visit, potions), always followed by `THROUGH_PORTAL`
   back. Also at a root's end when the next root is not walkable, when the cost rule says the climb back up a deep
   chain is dearer than portal plus waypoint, and at the game's end (Act 3's way through the Fortress).
7. **The last subtree of a root goes last and ends with a Town Portal, not a climb back.** That makes deep chains
   (Sewers 92→93, Flayer Dungeon 88→89→91) cost-neutral whenever they can be put last.
8. **The act scripts keep their role** as the order of roots and the boss-first rule. The engine maps
   `Trip`/`Rest` steps onto roots and ownership, and the graph adds the children. `ActScript`, `Trip` and `Rest` are
   unchanged for the act agents.
9. It **wraps the itinerary, it does not replace the run**. A new pure `zonenav.produce` takes the place of
   `tzroutine.produce` for the kinds and acts switched on. The legs are the existing `LEVEL`, `NEXT_LEVEL`
   (into a child), a new `UP_LEVEL` (back to the parent), `PORTAL_TO_TOWN`, `WAYPOINT`, `THROUGH_PORTAL` and
   `LEAVE_GAME`. Doors still go through `teleport.walk_into`.
10. **Stage 0 is read-only logging** (`zone: <level> cleared` / `blocked by <child>` / `left unexplored`). Stage 1 is
    Act 3 behind a switch. After that come every act and the rotating zones, then walks from root to root.

## 2. The zone graph

### 2.1 What builds it (all data the repo has)

| Piece | Source | Notes |
|---|---|---|
| Nodes | the zone's levels: `tz_groups.manual_zone(act).areas` / an installed rotating zone's `areas` / the union (`match_zones`) | plus *transit* nodes for a non-terrorized level between two zone levels (policy TRANSIT, as today) |
| Warp edges | `presets.LEVEL_LINKS` (Vis0..7), `LEVEL_WARPS`, `open_passage` | both directions present: every Act 1–5 dungeon lists its parent (checked: 96→81, 93→92, 116→115, …) |
| Border edges | `links.BORDERS` (only the pairs a route uses) | **gap**: most outdoor-to-outdoor borders are missing (80–81, 79–80, 78–79, 77–78, 76–77, 106–105, 2–3–4–5–6, 41–42–43–44, 110–111, …). Live `Room.leads_to` / `exits.border_exits` gives them in game |
| Roots | waypoint levels (`links.WAYPOINTS`) in the order of the act script's steps (`act_trips` waypoints), else `zone_route_plan`'s | a town is a root when a trip walks out of it (`WALK_OUT`: Blood Moor, Rocky Waste, Outer Steppes) |
| Ownership hints | each script step's levels belong to the root of its trip (`Rest(levels=(83, 100))` puts Durance 1 under Travincal, not under Durance 2) | resolves levels linked to two roots (100: 83 and 101; 92 Sewers 1: 80 and 81) |
| Entry mark (parent side) | the parent's card: a mark whose `area`/target is the child (`exits.warp_exits` gives every warp its target; handler `PoiSpec`s such as `kurast.py`'s temples) or, failing that, the catalogue's `enter(mark, child)` label | the card knows the entrances on arrival: the client holds every Room2 preset (memory d2r-level-room2-presets) |
| Way back (child side) | the child's card: a mark targeting the parent (`kind_for` 'previous', handler `previous(...)`) or the catalogue's `back(mark, parent)` | none for a level entered by a one-way portal: Arcane Sanctuary 74, Tristram 38, Nihlathak's Temple 121 from Harrogath, the act 5 red-portal pits 125–127; for those, `back = None` and the way out is the Town Portal |
| Boss child | `tzroutine.ACT_BOSS_LEVELS`, route `FIGHT` stages (`boss_areas`) | goes first in its parent; the parent is CROSSING until the boss is dead (the act 4 "River → CS → Diablo → rest of the River" rule) |
| Route's own way out | `agenda.WAYS_OUT` (Durance 3's Red portal) | the root's end, as today |

A prototype of the builder (breadth-first from each root in script order, not passing through another root, with
ownership hints) gives these trees from today's data alone. Act 3:

```
101 Durance 2 (wp) ─ 102 Durance 3 (Mephisto, Red portal out)
 83 Travincal (wp) ─ 100 Durance 1
 81 Upper Kurast (wp) ─ 96 Forgotten Reliquary · 97 Forgotten Temple · 82 Causeway [walk] ─ 98 Ruined Fane · 99 Disused Reliquary
 80 Kurast Bazaar (wp) ─ 92 Sewers 1 ─ 93 Sewers 2 · 94 Ruined Temple · 95 Disused Fane
 79 Lower Kurast · 78 Flayer Jungle ─ 86→87→90 Swampy Pit · 88→89→91 Flayer Dungeon · 77 Great Marsh · 76 Spider Forest ─ 84 · 85
```

Act 1 groups Countess and Hole under 6; Cave, Crypt and Mausoleum under 3 (Burial Grounds 17 [walk] is the
Crypt's and the Mausoleum's parent); Pit and Jail under 27. Act 2 puts Harem 51→50 and Palace 53→54 under 52, Sewers
1 and 3 under 48, and Valley of Snakes and Ancient Tunnels under 44. Act 4: 107 with child 108 [walk]. Act 5: 129 with
128 and 130→131→132; 123 with 122→121 and 124. Orphans: 38 Tristram, 73 Duriel's Lair, 125–127 (portals). The script
is in the session scratchpad (`tree.py`). Stage 0 adds it as `routes/zone_graph.py`.

### 2.2 The shape

```python
@dataclass(frozen=True)
class Way:  # how a level is left for a neighbour
    to: int
    mark: str  # the card label to go to ('' = a border walked across: exits.through)
    kind: str  # 'warp' | 'walk' | 'portal' (one-way) | 'route' (a route's own way: Red portal)


@dataclass(frozen=True)
class Node:
    area: int
    root: int
    parent: int | None
    children: tuple[int, ...]  # in-zone, graph order; the traversal orders them live (nearest)
    entry: Way | None  # parent -> this
    back: Way | None  # this -> parent; None: Town Portal only
    worked: bool = True  # False: a transit level (not terrorized), crossed only
    boss: bool = False  # a boss child: first in its parent


@dataclass(frozen=True)
class ZoneGraph:
    zone: str
    roots: tuple[int, ...]  # in play order (the script's)
    nodes: Mapping[int, Node]
    skipped: tuple[tuple[int, str], ...]  # orphans and blocked, with why (as Itinerary.skipped)
```

Pure, cached by zone (as `tzroutine.itinerary`). Cycles (81–82–83 borders, 92 linked to 80 and 81, 113↔115 and
115↔117 warps in Act 5) are broken by breadth-first search with one parent per node. A level met from an unexpected
side, for example by a run carried across an open passage (`pursuit.carried`), is handled by its own node's goals.
Nothing assumes the entry it came by.

### 2.3 Missing data, and what stage 0 learns

- **Outdoor borders** (above). Stage 0 logs every `leads_to` pair seen. A static `BORDERS` table filled from those
  logs feeds the walks from root to root (stage 3). Stages 1–2 do not need it.
- **Ways back that are unconfirmed.** Handlers marked "unconfirmed" (Kurast temples via `exits.warp_exits`, the act
  3 dungeons) need the way back seen once. Stage 0 logs, for every level entered, whether its card has a mark
  targeting each neighbour of the graph.
- **The game's own facts about whether a level is done.** `ZoneTracker.level_rooms` is the Room2 count. The rooms
  a run can reach are the `nearest` count of `Hunter.tour` ("78 with a way from here"). Leaders alive per area
  come from `positions` and `leaders`. Super chests left come from `Agenda.chests`. One accessor exposes these
  (§4.1).

## 3. Goals per level

`LevelState` is read from the tracker, the agenda and progress whenever a goal is chosen (never kept stale):

```python
@dataclass(frozen=True)
class LevelState:
    area: int
    rooms: int  # Room2 count (tracker.level_rooms); 0 = the map never loaded
    reachable: int  # rooms with a way from the character's last stand there (hunt.py tour `nearest`)
    explored: int  # tracker.explored[area]
    leaders: int  # leaders remembered alive on it (agenda.kills / tracker.positions ∩ leaders)
    groups: int  # TZ+ groups at or over the policy's size still known
    chests: int  # closed super chests known (agenda.chests)
    stage: str | None  # route stage left (progress.step): a fight, use, stand
    runs: int  # self-ended runs (agenda.worked): the "loop never stands" cap
    entered: bool
```

| Policy (agenda.py) | `worked(L)` | `explored(L)` |
|---|---|---|
| FULL_CLEAR (tzclear) | no hostile alive known on L, route stages done | `rooms > 0 and explored ≥ reachable` |
| PLUS / COVER (TZ+, act kinds) | no leader alive, no group ≥ GROUP_MIN (BIG_GROUP on a big level), no closed super chest, route stages done | same |
| PLUS_WAY / ON_THE_WAY / CROSSING | route stages done (the boss dead), leaders near | not required: the level's own run comes after the boss (`reopen`) |
| TRANSIT | true | not required (crossed only) |

- `fully_explored(L) = explored(L) and worked(L)` (the player's word).
- `cleared(L) = fully_explored(L) and all(cleared(c) or blocked(c) for c in children(L))`.
- `blocked(c)`: the child cannot be done in this game, and the reason is said once. Causes: its door took no click
  (`cause='door'`, today's `SKIP_DOOR` generalised from a trip to a child); its entrance mark is not on the explored
  parent's card; its map never loaded after `MAP_TRIES` (2) entries; its runs reached `RUNS_AN_AREA` with rooms left
  (`exhausted`); its goal dropped by `Agenda.failed` (TRIES). A blocked child does not hold its parent forever. The
  parent becomes *cleared with gaps*, logged `zone: <parent> cleared, blocked by <child>: <why>`.
- `RUNS_AN_AREA` stays as the cap, so the loop never stands. Reaching it with rooms left is `exhausted`, said, and
  never shown as explored.
- `Agenda.finished` stays, now **derived**: the set of cleared or blocked levels. That keeps `tour_back`, `reopen`,
  `skip_door` and `excursion_of` working while the kinds without the switch still use them.

## 4. Traversal

### 4.1 The next goal: `zonenav.produce(view) -> list[Objective]` (pure, re-derived at every leg)

`ZoneView` = `GameView` plus the graph, plus `LevelState` for the current level and every level entered, plus the
game's elapsed seconds and its cap.

In town:
1. Visit due → as today (`TOWN_ROUTINE`, the Fortress).
2. A **resume mark**: the town was reached by a package's Town Portal with the zone unfinished → the package's own
   `THROUGH_PORTAL` (as today's room package).
3. Else the first root not cleared → `WAYPOINT` (or `WALK_OUT`). No root left → `[]`, which is the game's end
   (`game_end`, the leave guard).

In a level L of the graph:
1. A valuable sighted → `PICKUP` (SIGHTED, as today).
2. A boss child not cleared → `NEXT_LEVEL` into it (L is CROSSING meanwhile).
3. L not `fully_explored` (and its runs under the cap) → `LEVEL`, the run with L's policy. In stage 2 the run
   itself may stop at a child's entrance (§4.3).
4. A child not cleared and not blocked → `NEXT_LEVEL(to=child)`. Children are taken nearest entrance first by the
   card's marks from where the character stands. A child whose subtree is deepest goes last when it would be the
   root's last (rule 7 of §1).
5. L cleared and not a root → `UP_LEVEL(to=parent)` by `back`. Or, by the **cost rule**, `PORTAL_TO_TOWN` with the
   resume target = the parent's root (§4.4).
6. L cleared and a root → the next root. In stage 3, `WALK` across a border or stairs when that root is a neighbour
   and the walk is cheaper. Otherwise `PORTAL_TO_TOWN` (EXCURSION) then `WAYPOINT`. In Act 3 a route's own way to
   town (Durance 3's Red portal) counts as that portal (`WAYS_OUT`).
7. A level off the graph (the player went there) → nothing of the zone's there: the `PORTAL_TO_TOWN` for the next
   root, as today's `excursion_of is None`.

The agenda's tiers are unchanged: STACK, SIGHTED, ERRAND, WORK, LOOTING, ONWARD, EXCURSION. `UP_LEVEL` has tier
ONWARD, the same as `NEXT_LEVEL`.

### 4.2 Into a child, and back up: reuse what exists

- **Into a child.** `zonenav` writes the level's selected script for this game, as `tzloop.select` already does with
  `kept_to`: `level(L, enter(entry.mark, child))` (plus L's own route stages when it has a route: fights, chests).
  The card then leads with that mark (`progress.lead`). The leg is `tz.way_on()` → `_way_on` → the teleport step →
  `teleport.walk_into` (door learning, `KNOWN_ENTRIES` / `DOOR_SEEDS`, the controller's `pad_door`) and `note_toured`
  style bookkeeping. A failed door (`Abort cause='door'`) marks the **child** blocked instead of ending a trip
  (`skip_door`, generalised). The parent goes on.
- **Back up.** `UP_LEVEL` selects `level(child, back(back.mark, parent))` on the child, the same `back` stage the
  tombs use, and makes the same press. For a `walk` way (108→107 Chaos Sanctuary → River, 82→81 Causeway → Upper
  Kurast) the open-passage machinery applies: `exits.through`, `pursuit.through`/`carried`. On arrival the parent's
  run resumes where its tour stopped: the tracker's explored rooms, shown at 09:08:05.
- **Ways back are known for every warp child** (§2.1). When the child's card does not show the mark
  (`back.mark` not on it), use the `Town Portal` fallback, said: `zone: no way back from <child> to <parent> on its
  card: Town Portal`.

### 4.3 Parent first, or a child when passed (stage 2)

Stage 1 is **parent first**: the parent's run is today's run, unchanged. The children follow, nearest first. This
fits TZ+ (the tour explores every room) and adds no in-level change. Stage 2 adds the player's "if we get into one
smaller level, we will return back … explore it further": an in-level goal `ENTER` (agenda tier after `CHEST` and
`LEADER_NEAR`, before `ROOM`). It applies to a child not cleared whose entrance is within `CHILD_NEAR` (60 units, a
screen, as `CHEST_NEAR`) of where the run stands, and it ends the run at the entrance (`NO_WAY_TO`-style end, a new
`AT_CHILD` reason). The run is then `UP_LEVEL`ed back to the same spot, so the parent's walk back to that entrance is
saved. Measure both (§6) before picking the default.

### 4.4 The cost rule (climb back, or portal)

`climb(child→root) ≈ Σ over the levels climbed of path(arrival spot → way back) / speed`, from the levels' explored
maps, which the session holds for the game (`levels/session.py LevelMemory`, `Hunter.tour` costs), plus
`DOOR_SECONDS` per warp. That is compared with `portal = PORTAL_TO_FIELD (8.5 s measured) + path(parent's waypoint →
the next goal in the parent)`. Rule 7 of §1 first: when the subtree is the root's last, the root is done after it and
the Town Portal is taken anyway, so there is no climb. One-floor dead ends (temples, caves, tombs: way back at the
arrival spot) always climb. Start with a fixed rule (climb at most `CLIMB_FLOORS` = 1 floor back when not last) and
switch to the measured cost once stage 0 has the numbers.

### 4.5 Act scripts and boss-first

`ActScript` stays the act agents' file and the order. `acts/engine.py` gains one pure function next to `act_trips`:
`act_roots(script, zone) -> tuple[Root, ...]`, each root `(waypoint, owned levels, boss target or None, crossed)`:

- `Trip(route, target, waypoint, crossed)` is a root at the trip's waypoint, owning the trip's levels, with the
  target as its boss child. `crossed=AFTER` makes the levels on the way CROSSING until the boss dies (Act 4: 107's
  run after 108). `WORKED` works them on the way (Act 3: 101 then 102).
- `Rest(levels=…)` / `Rest(zone=…)` / `Rest(route=…)` are roots at the waypoints of the trips `zone_route_plan`
  finds for them, owning those levels. Two `Rest` steps whose trips share a waypoint merge into one root:
  `(81, 82, 98, 99)` and `(96, 97)` become root 81 with 96, 97 and 82 (98, 99) as children.
- After the steps, the act's other levels become roots by `zone_route_plan` as today. Then the rotation's zone.
- A step marked `missing`, or one with no path, is skipped and said exactly as today. Its levels become the graph's
  `skipped`.
- The Canyon tour (`tour` stage) becomes a root with seven children. `tour_back`/`Excursion.tours` stay for the
  kinds without the switch, and are retired once every kind uses the zone layer (stage 3).

## 5. How it fits the current code

| Today | With the zone layer |
|---|---|
| `tzroutine.itinerary` → `Itinerary` (excursions) | still computed (log line, kinds without the switch); `zonenav.zone_graph(itinerary's zones, roots from the act script)` beside it, cached |
| `tzroutine.produce(GameView)` | `zonenav.produce(ZoneView)` when `zonenav.on(kind, zone)`; `tzloop.choose` picks one (one `if`) |
| `agenda.finish` on leaving (`NEXT_LEVEL`, `PORTAL_TO_TOWN`, `skip_door`) | judged: `finished` = cleared ∪ blocked, recomputed from `LevelState` at each `choose`; `finish` on leave only in the old path |
| `RUNS_AN_AREA`, `WORKED_BY_RUNS` | the cap and "exhausted" only; never "done" |
| legs `TZ level`, `TZ next level`, `TZ Town Portal`, `TZ waypoint`, `TZ back through the portal` | same legs, plus `TZ up` (`UP_LEVEL`) so the watch tools count climbs apart from descents; `REPEATS[TZ_UP]` like `TZ_NEXT_LEVEL` (an act with 37 levels: count per level, not per game, or raise both) |
| `SKIP_DOOR` → a trip's terminal done | a child blocked; the parent and the zone go on |
| `tour_back`, `reopen`, `Excursion.passes` | the boss child first and the parent CROSSING (§4.5); kept for the old path |
| `KNOWN_ENTRIES`, `DOOR_SEEDS`, `teleport.walk_into`, `pad_door` | unchanged; used for both into and back up |
| Room package (`room_package`, `THROUGH_PORTAL`, `RESUME`) | unchanged; with fewer town round trips the visit falls due mid-zone, so a `visit_package` (`PORTAL_TO_TOWN`, `TOWN_ROUTINE`, `THROUGH_PORTAL`, `RESUME`) pushed at the next root boundary or child boundary when `visit_due` |
| Recovery (`running/recovery.py`, `stops.decide`) | unchanged: `RECOVER`/`LEAVE` leave the game; `FETCH`/`AGAIN`/`PACKAGE` re-derive the next goal from state ("re-plan, never resume") |

**Resume after a stop.** A new game is a new map, so the zone state is per game. That is today's agenda lifetime.
Within one game, every leg re-derives the goal from `LevelState`, so a stop that does not leave the game (the hand, a
fetch, the room package) resumes by construction. A **service restart** mid-game loses the agenda, but the tracker
keeps its per-game facts across restarts (`ZoneTracker.store`, `restored`). Stage 3 adds the zone's few facts to the
same store (blocked children and why, runs per level) so that a restart resumes the zone and does not replay
explored levels. For the act kinds this matters: a game left mid-act loses the shard (`ACT_SECONDS` 3600–3900 s).

**Loop kinds:**

| Kind | Uses it | Why |
|---|---|---|
| `act3` | stage 1 | 7 re-entries a game, the race's victims |
| `act1`, `act2`, `act4`, `act5` | stage 2 | 4, 3 (plus the tour), 1 (plus the root walks) and 6 re-entries |
| `tz` (TZ+), `tzclear` | stage 2 | rotating zones are often one parent with chains (Flayer Jungle: 2 trips from 78; Black Marsh: Tower + Hole; Glacial Trail + Drifter Cavern) |
| `lk`, `andariel` | no | one level, or one boss route with their own legs (`loop.py lk_leg`); nothing to traverse |

## 6. Measures

Per-game, from the logs (a new watch tool `tools/zones.py`, or `games.py` columns):

- **Town round trips**: `TZ Town Portal` + `TZ waypoint` legs a game, and the `TP → field` seconds (median 8.5 s
  today).
- **Re-walks**: seconds from arrival in an already-explored level to its next entrance (median 6.6 s today).
- **Climbs**: `TZ up` legs and seconds (new).
- **Levels left unexplored**: levels whose `explored < reachable` when the zone moved on, and levels blocked, with
  why. Today this is invisible: 96/97 were "done".
- **The kind's metric**: elite and Herald kills an hour (act kinds, `tzclear`: `elites.py --kind act3`); experience
  an hour (`tz`). Also kills a game and the game's length against `ACT_SECONDS`.

Expected, from today's plans (`act_trips` with the scripts ready) and the 15 s re-entry cost, assuming about 5 s for a
one-floor climb:

| Act | Trips / waypoints | Re-entries saved | Time saved a game | Plus |
|---|---|---|---|---|
| 1 | 12 / 8 | 4 (Countess+Hole; Cloisters; Crypt+Mausoleum+Cave re-cross Cold Plains and Burial Grounds) | ~40–60 s | Burial Grounds not crossed twice |
| 2 | 11 / 8 | 3 (Palace up+down, Sewers 1+3, Lost City's two) | ~30 s | the tour as one rule |
| 3 | 15 / 8 | 7 (Upper Kurast 3, Bazaar 2, Flayer Jungle 1, Spider Forest 1) | ~60–70 s | 3 dungeons that today are skipped by the race (28 hostiles in 96 alone) |
| 4 | 4 / 3 | 1 (107 after Diablo) | ~10 s; ~30 s with stage 3's walk 107→106→105→104 | |
| 5 | 14 / 8 | 6 (Baal's crossing, Halls of Pain's two) | ~50 s | |

That is **2–4 % of an act game** in time (an Act 3 game runs well past 15 minutes). The bigger gain is **correctness**:
no level counted done unexplored, so kills a game go up by every small dungeon the race or a short run skips today.
Also, each portal and waypoint leg avoided is one fewer failure point ("TZ next level again and again", the Crypt
door). Judge stage 1 on kills a game and levels left unexplored first, seconds second. Per the loop journal's rule,
use 30+ clean games per change.

## 7. Stages

**Stage 0: graph and goals, read-only, logging (no behaviour change).**
- `routes/zone_graph.py`: `Way`, `Node`, `ZoneGraph`, `zone_graph(zones, roots, owned)`. `acts/engine.py
  act_roots` (pure). `macros/zonenav.py`: `LevelState`, `explored`, `worked`, `fully_explored`, `cleared`, `blocked`
  (pure).
- One accessor hand, `LegHands.level_state(area) -> LevelState | None` (`running/legs.py`, from the tracker,
  `Hunter.tour`'s reachable count, the agenda and progress).
- Logging in `tzloop.choose`/`perform`, a few lines and no decisions:
  - `Macro: zone: graph <zone>: <roots and trees>` once a plan.
  - At every `agenda.finish`: `Macro: zone: <level> done by the old rule: explored a/b rooms (reachable r), leaders
    l, chests c: cleared | NOT explored (no map / rooms left) | blocked by <child>: <why>`.
  - At every Town Portal and waypoint pair: `Macro: zone: TP+waypoint back to <root> for <child>: a climb from
    <level> would be <n> floors`.
  - Each card's ways seen per level (`zone: <level> card: ways to [..]; graph wants [..]`) and `leads_to` pairs
    (the borders' table).
- Tests (`tests/inventory_tracking/routes/test_zone_graph.py`, `macros/test_zonenav.py`): the five act trees as in
  §2.1 (pinned); cycles and two-parent levels get one parent each; ownership hints win; orphans skipped with why;
  `cleared` false with a child unexplored, true with it blocked; a 0-room level never explored; a CROSSING parent
  not required explored.
- Exit: one evening of act3/TZ+ logs shows every "done by the old rule" with its real state; the ways-back table
  has no gap for Act 3.

**Stage 1: Act 3 behind `zonenav.ACTS = {3}` (False/empty → today's path).**
- `tzloop.choose` uses `zonenav.produce` for act 3 (the act3 kind and Act 3 terrorized by hand in TZ/TZ+).
  `UP_LEVEL` leg (`TZ up`) in `tzloop.perform`. `skip_door` blocks a child. `finished` derived. The fixed cost rule
  (`CLIMB_FLOORS` 1, the last subtree ends in a portal). Parent first.
- Tests: the act harness (`tests/inventory_tracking/macros/acts/harness.py`) needs its fakes to take an `up` move
  (the `Walk.moves` kinds gain `'up'`; the fake game links a child's way back to its parent's entrance).
  `test_act3.py`: one walk visits every level of the act. Waypoints taken drop from 15 to 8 (101, 83, 81, 80, 79,
  78, 77, 76). 96, 97, 98, 99, 94 and 95 are each left by `up`. Sewers 93 ends its root by a portal. `test_tzloop.py`
  scenarios: a child whose map is not loaded on arrival is not done (re-entered, then blocked after `MAP_TRIES`,
  said); a door with no click blocks the child, and the parent and next children go on; a child with no way-back mark
  takes the Town Portal and resumes at its root; a room package mid-child returns through the portal into the child;
  the game cap reached mid-root leaves by the leave guard. The arena is not needed (no fight change).
- Live: 30 clean act3 games watched (d2-loop-watch). Measures as §6 against the last 30 act3 games before it.

**Stage 2: every act and the rotating zones, and a child when passed.**
- `zonenav.ACTS = {1, 2, 3, 4, 5}`, `zonenav.ROTATION = True` (tz, tzclear). The Canyon tour becomes a root with
  seven children (`tour_back` stays for the old path).
- `ENTER` in-level goal (§4.3) behind `zonenav.CHILD_WHEN_NEAR`, A/B measured on Act 3 (30 games each).
- Tests: per act `test_act<N>.py` walks (waypoint counts per §6). TZ zones from the installed table: Flayer Jungle
  one root, Black Marsh one root (Tower chain plus Hole). `hunt`/agenda tests for `ENTER` (tier order; ends the run
  at the entrance; never for a cleared or blocked child).

**Stage 3: walks from root to root, the cost rule measured, resume after restart, the time budget.**
- `BORDERS` from stage 0's table. `WALK` to a neighbour root when `path < PORTAL_TO_FIELD + its waypoint walk`
  (Act 4 becomes one walk 107→108→107→106→105→104; Act 3 83→82→81; the Act 5 highland warps 113→115→117→118).
- The measured cost rule replaces `CLIMB_FLOORS`.
- The zone's facts are kept in the tracker's store for a service restart.
- **Time budget**: with `remaining < estimate(child)` (population × seconds a kill, from `elites.py`), the
  least-valued children are skipped and said, so an act is not cut mid-boss by `ACT_SECONDS`.
- Retire `Excursion.tours`/`tour_back`/`reopen` once no kind uses the old path.

## 8. Risks

- **A child with no way back known**, or a one-way portal level: fall back to the Town Portal and the waypoint to its
  root (today's behaviour). It is said, and never a stop.
- **Dead ends and deep chains**: the climb can cost more than the portal. The last-subtree rule and the cost rule
  (§4.4) bound it, and stage 0 measures it.
- **A child's entrance not found**: the parent explored and the mark not on its card (an unread preset variant:
  `warp_spots` gives `{}`) → blocked "no entrance mark", said. The parent counts cleared with a gap. No wander.
- **Cycles and two-parent levels**: one parent each from the breadth-first search with ownership hints. A level
  reached another way is judged by its own node, so there is no loop.
- **The map race** (today's bug): `rooms == 0` is never explored. Re-entry or `MAP_TRIES` then blocked, so it cannot
  repeat silently even if the race comes back.
- **The repeat guards**: more `NEXT_LEVEL` and `UP_LEVEL` legs a game (Act 1: 37 levels). `REPEATS` per leg is
  counted per game today (`TZ_NEXT_LEVEL: 30 + TOUR_WAYS`), so count per level or raise it, and pin it in a test (the
  act-3 script was already blocked once by `TZ_PORTAL` 13 < 15 trips).
- **The game cap** (`ACT_SECONDS` 3600–3900, `TZ_GAME_SECONDS` 1200): the zone does not get shorter in work, only in
  overhead. Stage 3's time budget is the remedy. Before that, the boss-first order keeps the statue chance.
- **The town visit falls due less often at a natural boundary**: the visit package at the next boundary (§5). The
  room package still covers a full inventory mid-child.
- **Shared files**: `tzloop.py`, `runner.py`, `pursuit.py` and `hunting/moves.py` are under other agents' edits now.
  Stage 0 needs only one `choose` hook and one `LegHands` field. Rebase on their fix of the map race first.
- **The watch tools** (`logwords.py` EVENT/NOW, `games.py` phases, `andy.py`) must learn `TZ up` and `zone:` lines,
  or the watch reads climbs as stalls.

## 9. Questions for the player (each with the default this plan takes)

1. **Parent first, or a child when passed?** Explore the parent, then go into its children nearest first. Or go in
   as soon as the run passes a child's entrance, then come back and go on exploring. *Default: parent first in stage
   1; "when passed" built in stage 2 and kept only if kills an hour say so.*
2. **Deep chains (2–3 floors): climb back up or Town Portal?** *Default: one-floor dead ends always climb; a deep
   chain goes last in its root and ends with the portal; otherwise climb only when measured cheaper.*
3. **Walk between waypoint levels** (Travincal → Causeway → Upper Kurast; River → City → Plains → Steppes) instead of
   Town Portal and waypoint? *Default: yes once measured cheaper (stage 3).*
4. **A child we cannot do** (no click takes its door, no entrance on the map, the map never loads): go on and call the
   parent cleared with a gap, or retry it once at the end of the zone? *Default: blocked, said, one retry after the
   last root if time remains.*
5. **"Fully explored" on a big level** (300+ hostiles, TZ+ takes groups of 8+ only): every reachable room seen, or
   only its targets met? *Default: every reachable room seen and its targets met (rooms are the tour anyway).*
6. **The game cap**: near `ACT_SECONDS`, skip the smallest children to finish the act's bigger levels, or play in
   order until the cap? *Default: in order until stage 3's time budget; the boss is first either way.*
7. **The town visit mid-zone**: with fewer portals, take the visit (identify, sell, repair) at the next root boundary
   (a portal is made there anyway), or only when the room rules call it? *Default: at the next root boundary when
   due; the room package as today when the inventory is full.*
8. **Which kinds**: Act 3 first, then every act and TZ+/Full clear TZ. Lower Kurast and Andariel stay as they are.
   *Default: as stated.*

## 10. Rulings and what is built (2026-10-21 ~09:35 onward)

The player's rulings: Q1 **enter when passing**; Q2 **climb one floor, Town Portal for deep** (a deep chain last in
its parent, ended by the Town Portal); Q4 blocked children **blocked and said, go on, no retry** until the click
failures are researched; Q5 every room seen and the targets met; Q6 in order, boss first; Q7 the visit at the next
boundary when due; Q8 **build stages 0 and 1**, acts and TZ kinds only.

Built:

- `routes/zone_graph.py`: `Chain`, `Way`, `Node`, `ZoneGraph`, `zone_graph`, `way` (the marks: catalogue, handler,
  generic). The roots come from the itinerary's trips, so an act script's order holds unchanged.
- `macros/zonenav.py`, pure: `ACTS` (the switch), `CLIMB_FLOORS`, `MAP_TRIES`, `LevelState`, `judge`, `next_child`,
  `climbs`, `above`, `scripts`, `produce`, `said`, `allowed`.
- Wiring:
  - `tzloop.choose` → `zone_choose` when `zonenav.on(plan)`. Stage 0's `zone_note` runs in the old path.
  - New leg `TZ up` (`UP_LEVEL`). A door no click takes into a child blocks it (`zone_door`). A way back that takes
    no click goes to `no_back`, then the Town Portal.
  - `runner._zone_seen` records `mapped`/`explored` from the hunter's tour at every run end.
  - `legs._trip_levels` keeps a zone run on its own level.
  - Repeat guards: `ZONE_LEVELS`, `TZ_UP`, `TZ_NEXT_LEVEL`, `TZ_BACK`.
  - The watch tools: `logwords.ZONE`, `ZONE_BLOCKED`, EVENT/NOW, `elites.py` legs.

**"Enter when passing"** (built 2026-10-21, after the coordinator cleared `hunting/choice.py`):

- `zonenav.produce` gives an unexplored level its run first (a `LEVEL` goal). The run's script ends in the next
  child's way in. `NEXT_LEVEL` comes only once the level is explored, or at once toward the boss on a level crossed
  to it.
- `zonenav.enter_at` (switch `ENTER_PASSING`, active only when `ACTS` covers the act): the route stage's `enter`
  into a child is the run's `use_at` in `hunting/choice.py`. Within USE_NEAR and nearer than the next room, the
  agenda yields (`Agenda.in_level` USE_FIRST). The run goes in, the child is cleared, `TZ up` climbs back, and the
  parent's next run finishes its rooms. A `back` stage, a tour or a pending stage never counts.
- `ENTER_PASSING = False`: the parent's rooms first, then each child from its door at the run's end.
- Logs (Act 3): `Macro: zone: Upper Kurast (81) not explored, children left [82, 96, 97]`, then a run in 81 that
  ends in 96 before its tour is done. Upper Kurast has three runs: to the Reliquary's door, to the Temple's door,
  then its rooms.

**All five acts** (2026-10-21 ~12:50; the player, ~11:30: "why we don't want to have it for all acts?"): `ACTS` is
{1, 2, 3, 4, 5}. Act 5 first lost two levels and a boss in the act harness (`tests/.../acts/test_act5_zone.py`):

- The Halls of Pain and of Anguish (123, 122) are tz+ on the way (to Nihlathak, to Pindleskin) with no stage of their
  own, so `fully_explored` called them explored on arrival and they were never run. A level on a way-on policy is
  now explored after one run, as the itinerary's rule (`runs == 0`).
- Nihlathak's Temple's (121) main script is the Nihlathak route's way down from Anya's red portal (the stairs to the
  Halls of Anguish), with no fight. The zone's scripts now come from every trip naming the level, in the trips' order
  (`tzloop.zone_script`), so the Halls of Anguish trip's Pindleskin fight is kept. The Burial Grounds (17) needs the
  same: its first trip is the Crypt's (stairs only), Blood Raven is on the Mausoleum's.
- The graph merges the Keeps' trips into root 129, so the Keep 3 and 1 come right after Baal (one waypoint), before
  the halls; the bosses keep their order.

## 11. Status, 2026-10-21 afternoon (the player: "start implementation for ready to build items without questions")

**The Causeway stop, fixed (~14:20).** At 13:48:00 Upper Kurast's run ended "Kurast Causeway leads off the trip" 30
times in 3 s and the repeat guard left the game (a shard lost): `zonenav.allowed` gave a run its own level only, and an
open passage (Upper Kurast → Causeway, River of Flame → Chaos Sanctuary) is crossed by the run itself
(`pursuit.to_the_door` → `through`). Now `allowed` is the level, its graph parent and its children (a run crosses only
toward its stage's goal, which the zone script sets). A way made `WAY_TRIES` (6) legs from one level with no arrival
now blocks the child (or makes a climb the Town Portal), said, and the zone goes on (`tzloop.way_tried`, `way_spent`).
The act harness models passages now (`harness.crossing`); with the old `allowed` both the Act 3 and Act 4 walks stop
as live did. Notes: rca/2026-10-21/zone-nav-stage2-notes.md.

**Stage 2, built; `ROTATION` on since ~14:40 (off for the 14:25 restart, its walks green after it).**
- `zonenav.ROTATION`: a plan with no act terrorized by a shard (the rotation alone) is played by the graph. A plan with
  an act keeps `ACTS`' say.
- The Canyon of the Magi is a root with seven `toured` children (`zone_graph.Node.toured`): its script's way in is the
  tour's stage over the tombs not finished (`tour('Tomb', left)`), so the nearest mark not yet gone through is taken
  (`route.note_toured`, `Progress.lead`'s skip) whichever tomb it leads into; each tomb is judged by its own node and
  climbed out of by its `back`. A tomb entered and left unfinished (back in the Canyon by a waypoint) is blocked: which
  mark leads back is not known. `tour_back`/`Excursion.tours` stay for the old path. This also fixes Act 2's tour under
  `ACTS` (live since ~12:50): before, the Canyon's script was `enter('Tomb', 66)`, and with no mark gone through noted
  the nearest 'Tomb' mark (the one just climbed out of) would have been taken again.
- A level only crossed (not terrorized) gets no route work of its own under the graph (Travincal's Council on the
  Durance of Hate zone's way), as `kept_to` in the old path.
- A town root (not worked) counts explored whether or not it was entered (no walk into a town to mark it).
- Harness walks of every installed zone, TZ+ and Full clear TZ, off and on (tests/.../acts/test_rotation_zone.py):
  the same levels and bosses, no stop (the Moo Moo Farm waits for the next zone either way), waypoints never more.

| Zone | Waypoints off → on | Climbs on |
|---|---|---|
| Act3-Kurast | 9 → 4 (80, 81, 79, the Fortress) | 5 |
| Act2-LostCity | 2 → 1 | 1 |
| Act3-SpiderForest | 3 → 2 | 1 |
| Act1-BurialGrounds | 2 → 1 | 1 |
| Act3-FlayerJungle | 3 → 3 (two deep chains, "TP for deep") | 0 |
| Act1-Tower (Black Marsh) | 2 → 2 (the Tower's chain and the Hole, both deep) | 0 |
| Act5-GlacialTrail | 1 → 1 (the Drifter Cavern last: the portal) | 0 |
| Act2-TalRashas | 1 → 1 (the tour as seven children, 6 climbs) | 6 |
| Acts 1-5 (shard kinds, `ACTS`) | 12 → 10, 11 → 9, 16 → 10, 4 → 3, 12 → 10 | |

- `ENTER` when passing (§4.3) was built at stage 1 (`ENTER_PASSING`, on).

**Stage 3, built, each behind its switch.**
- `WALK_ROOTS` (off): a root cleared walks into the next root's levels across a border or stairs when one joins it
  (`zone_graph.bordering`: the static links, `links.BORDERS`, the outdoor handlers' named exits), the root first, else
  its first level not finished; then the climbs bring it up. Act 4: 107 → 108 → 107 → 106 → 105 → 104; Act 3:
  83 → 82 → 81 (BORDERS has 82–83); Act 5's highland stairs 113 → 115 → 117 → 118. A walk that fails (a plain stop) or is
  made `WALK_TRIES` (3) times is the Town Portal instead (`Agenda.no_walk`), said. Off until the walk's own cost (from
  where the root's run ended to the border) is measured live.
- `RESUME` (on since ~14:40; off for the 14:25 restart, its test green after it): the zone's facts (entered, mapped, explored, runs, cleared, blocked,
  ways back failed) are written to `zone-facts.json` beside the loop's store when they change, keyed by the game's name
  and the character's unit id (`loop.GameId`), and taken back by the first zone leg of a game after a service restart
  (`tzloop.zone_keep`, `zone_resume`; `LevelState.kept`: a level cleared before the restart stays cleared though its
  route facts are gone). Not the tracker's store: the macro holds no tracker (service.py wiring, not this agent's).
- `TIME_BUDGET` (off: the player's Q6 ruling "in order, boss first" holds): with the game's time left (`Loop.overdue`'s
  cap) under the zone's estimate, the smallest children not on a boss's or a route fight's way are blocked, said
  (`Macro: zone: <level> (<n>) blocked: no time left for it ...`), until it fits. A level's estimate:
  `LEVEL_SECONDS` 27 + `HOSTILE_SECONDS` 0.32 × its population + `CHILD_SECONDS` 10 (fit over 797 level stays,
  `Macro: experience: <level>: ... in N s`, 2026-10-20/21).
- `CLIMB_FLOORS` stays the live rule. Measured from the 2026-10-20/21 logs: Town Portal → waypoint → the next field leg
  median **9.0 s** (p25 7, p75 10, n=77); a `TZ waypoint` leg 6.0 s (n=520); a `TZ next level` leg at the door 1.0 s
  (p75 3, n=610); `TZ up` none yet (stage 1 went live at ~13:28). So one climb saves ~9 s plus the parent's re-walk
  (6.6 s, §0) whenever its own walk is under that.
- Not done: `Excursion.tours`/`tour_back`/`reopen` are not retired (the old path still runs with the switches off).

**After the 14:25 restart (coordinator's items, rca/2026-10-21/cyberr5-findings.md), all in code, live at the next
restart:**
- `ROTATION_FIRST` (on): a shard game's rotating zone in the act of the level the character is on (the Fortress after
  the shard: the River of Flame, one waypoint away) is played before the shard's act (`zonenav.play_order`, said once:
  `Macro: zone: the rotation first: [106] before the act's roots, from ...`). cyberr5 put the River after every Act 3
  root: never reached while terrorized (a game ~48 min, the rotation turns every 30). A rotation that turned drops out by
  itself: the plan is read afresh each leg (`tzloop.zone_of`); tested.
- A run that ended on a level since the character came to it, with a one-floor child chosen next (`ENTER_PASSING`), is
  followed by that child's NEXT_LEVEL, not another LEVEL run (`ZoneView.passed`, `Agenda.zone_at`/`arrival_runs`): at
  14:10:58 Upper Kurast's run ended "at Forgotten Reliquary: going through takes a press" 6 times in 1.4 s, and the
  city's runs ran out (RUNS_AN_AREA + 2), so it was judged explored with rooms unseen.
- Duriel's Lair as the tour's **side level** (`zone_graph.Node.side`, `sources`): a level after the tour that every
  toured level leads into by a `use` stage hangs under the hub, is never gone into from it, is entered by the true
  tomb's Orifice (the tomb's `use` stage is its own work, `own_stages(sides)`, done where the mark is absent), has no way
  back (the Town Portal), and is blocked "none of its tour's levels led into it" once every tomb is done without it.
  Its policy (and every level's, under the graph) comes from the trip naming it even once the itinerary calls that trip
  over (`Itinerary.trip_of`; also `legs._agenda_policy`): the lair entered from the last tomb was TRANSIT and "explored"
  on arrival, unfought. The routes agent's strict xfail passes (marker removed). `DURIEL` stays False: turning it on
  breaks 18 tests in the routes/tour files that pin the old catalogue (tables, tour walks that never mark the Orifice
  absent) — the routes agent's change.
