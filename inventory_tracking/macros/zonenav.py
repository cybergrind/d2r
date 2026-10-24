"""Zone navigation: a terror zone played as a graph of levels, depth first from each waypoint, a level done only when
judged so (inventory_tracking/macros/zone-nav-plan.md). Pure: macros/tzloop.py reads the game into the views.

The player, ~09:20 on 2026-10-21: "if we get into one smaller level, we will return back to global level, explore it
further and clear smaller dungeons (all, if there are many) / and global zone level isn't getting marked as fully
explored, until all smaller dungeons are also cleared". Rulings of ~09:35: "Enter when passing" (a child is gone into
as the run passes its entrance, cleared, left by its way back, and the parent's run goes on); "Climb 1 floor, TP for
deep" (out of a one-floor child by its stairs; a deep chain last in its parent, ended by the Town Portal); a child that
cannot be done is blocked and said, no retry.

- `graph_of`: the itinerary's trips as a routes/zone_graph.py `ZoneGraph` (roots in the plan's order).
- `judge`: per level `fully_explored` (entered; its own route stages done; on a touring policy every room seen, or its
  runs spent) and `cleared` (fully explored and every child cleared or blocked); `finished` (cleared or blocked) is the
  agenda's `finished` in zone mode.
- `scripts`: each level's script for this game: its own route work (fights, objects, stands, a boss's loot), the way
  into the next child to take, then its way back up; the route's own way to a town (Durance 3's Red portal) only with
  nothing above left to do.
- `produce`: the game-level goals wanted now; `UP_LEVEL` is the climb to the parent.
- Stage 2 (2026-10-21): the rotating zones too (`ROTATION`); a tour's hub (the Canyon of the Magi) goes into its
  toured children by the tour's marks, the nearest not yet gone through (`scripts`).
- Stage 3 (2026-10-21), each behind its switch: a walk from a cleared root into the next root's levels across a border
  or stairs (`WALK_ROOTS`, `walk_to`); the zone's facts kept for a service restart (`RESUME`, `kept`, `resumed`); the
  time budget (`TIME_BUDGET`, `over_budget`).
"""

import functools
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, replace

from inventory_tracking.levels.presets import display_name
from inventory_tracking.macros.agenda import (
    COVER,
    ERRAND,
    EXCURSION,
    FULL_CLEAR,
    LEVEL,
    LOOT,
    LOOTING,
    NEXT_LEVEL,
    ONWARD,
    PANDEMONIUM_FORTRESS,
    PICKUP,
    PLUS,
    PORTAL_TO_TOWN,
    SIGHTED,
    SKIPPED,
    TOWN_ROUTINE,
    TOWNS,
    TRANSIT,
    WALK_OUT,
    WAYPOINT,
    WORK,
    Objective,
    town_of,
)
from inventory_tracking.macros.tzroutine import ACT_BOSS_LEVELS, RUNS_AN_AREA, Itinerary
from inventory_tracking.routes.model import (
    ENTER,
    FIGHT,
    LOOT as LOOT_STAGE,
    STAND,
    USE,
    Script,
    Stage,
    back,
    enter,
    tour,
    use,
)
from inventory_tracking.routes.progress import Facts, done
from inventory_tracking.routes.tz_groups import manual_zone
from inventory_tracking.routes.zone_graph import PORTAL, WARP, Chain, Node, ZoneGraph, bordering, way, zone_graph
from inventory_tracking.terror.zones import level_population


# The acts whose terrorized zone (and the rotation planned with it) is played by the graph. Empty: the itinerary's
# excursions as before, exactly. Stage 1: Act 3 (the player, 2026-10-21 ~09:35: "Build stage 0 + 1"; ~11:30: "yes,
# enable zone navigation for act3"; "why we don't want to have it for all acts?": acts 1-4 pass the act harness's
# game with it on; act 5 too since 2026-10-21 ~12:50, once its halls were run on their way and Pindleskin fought by
# the Halls of Anguish trip's script: `fully_explored`, tzloop.py `zone_script`)
ACTS: frozenset[int] = frozenset({1, 2, 3, 4, 5})
# The rotating terror zones (TZ+ and Full clear TZ with no act terrorized by a shard) played by the graph too: Kurast's
# three roots in place of eight trips, the Lost City's tunnels and temple from one waypoint, the Spider Forest's two
# caves. Stage 2, 2026-10-21 (the player: "start implementation for ready to build items without questions"): every
# installed zone walked in the act harness with no stop and no level lost (tests/.../acts/test_rotation_zone.py).
# False: the itinerary's excursions for them, exactly
ROTATION = True
# A shard game's rotating zone in the act the character is in (the Fortress, where the visit and the shard are) played
# before the shard's act: cyberr5 (14:00-14:12 on 2026-10-21) put the River of Flame's root after every Act 3 root, an
# Act 3 game takes ~48 min and the rotation turns every 30 (tzloop.py ZONE_TURN), so it was never reached while
# terrorized. The player, 14:20: "I haven't seen your visit to the rotating level (river of flame)". A rotation that
# turned drops out of the plan by itself (tzloop.py `zone_of` reads the tracker's zones at each leg). False: the act's
# roots first, the rotation's after them
ROTATION_FIRST = True
# A shard game's rotating zone's roots holding a boss alive in the game's ledger (macros/bossledger.py) are played
# right after the shard act's boss (the first root holding an act boss's level: "we want to kill act boss first for
# possible statue drop", the player, 2026-10-20), from any act, not last: Duriel was never killed in 16 TZ games, the
# Tal Rasha rotation's tombs root always last behind the shard acts' 16 roots from the Fortress and the zone turned away
# before it (cyberr14 10-21 21:40, cyberr15 22:26; rca/2026-10-22/boss-audit-findings.md, Duriel). A rotation that
# turns all the same keeps its bosses (tzloop.py BOSS_ZONES). The player, 2026-10-22: "we should always kill act
# bosses". False: the rotation's roots last but the character's act's (ROTATION_FIRST), as before
ROTATION_BOSSES_FIRST = True
# A shard game's rotating zone from any act, not only the character's (lever 3 of rca/2026-10-22/exp-hour-findings.md;
# the player, 2026-10-23: "push xp/hour"): ROTATION_FIRST put a rotation first only where `town_of(root)` was the
# character's act, so in the shard game of 2026-10-22 the River of Flame (21:30-22:00) and the Arreat Plateau
# (20:00-20:30) went unplayed while act 1's roots went on, and the rotations played late turned under the run (Far Oasis
# at 19:03, the tombs at 19:50: plain monsters, 142 exp a kill against ~1,900). True: while its slot has ROTATION_LEAST
# s left (the zones turn on :00 and :30, tzloop.py ZONE_TURN), every root of the rotation, in any act, is played right
# after the root holding the boss of the act now played (its first root not finished; the act's boss alive in the
# game's ledger: "act boss first", 2026-10-20; "we should always kill act bosses", 2026-10-22), before that act's other
# roots; the shard acts' roots stay in the plan and are owed as before (tzloop.py ACT_OWED: the game is never left with
# act 1 owed). With less left, the order of ROTATION_FIRST and ROTATION_BOSSES_FIRST. False: as before
ROTATION_ANY_ACT = True
# Seconds of the rotation's slot left under which it is not put first: the switch's waypoint there and back (~15 s
# each, a Town Portal and a waypoint, at the loop's 98.5k a minute ~50k) pays only over ~1.5 min more of its denser
# levels (176k a minute against the shard act's 139.5k); a root takes 2-8 min (the findings' level table) and the turn
# leaves the rest of it plain, so five minutes leaves about three of play after the trip
ROTATION_LEAST = 300.0
# Floors of stairs climbed back to the nearest level with work left; more and the Town Portal and its waypoint are
# taken (the player, ~09:35: "Climb 1 floor, TP for deep"). A walk across an open passage is no floor
CLIMB_FLOORS = 1
# A level whose children left are all deep (none one floor) goes into the first of them once its own run has explored
# it (`next_child`); until then its script holds no way back up (`waiting_deep`). Before, the script made at the
# level's entry, the level not explored yet, ended in the climb (`climbs`): the run went to the way back and only the
# zone's verdict after it turned round into the deep child. Flayer Dungeon 1 at 22:49:10 on 2026-10-21: 165 units to
# the stairs up to the Flayer Jungle, then 183 back to the next level. The Forgotten Tower at 23:18:58 the same night
# (one room, its child the Tower Cellar's five floors, the Black Marsh's Hole left): "route Countess: back to Black
# Marsh", a walk that did not move onto the tower's way out for 46 s and the game left
# (rca/2026-10-21/tower-stall-findings.md). False: the climb in the script, as before
DEEP_AFTER_RUN = True
# A level with a boss of the game's ledger alive on it (`LevelState.bosses`, macros/bossledger.py; the levels the zone
# works and the act bosses' levels, never a level only crossed) is not fully explored, so not cleared, while it has had
# fewer than BOSS_RUNS runs over its own allowance (the agenda's boss goals take each run to the boss at any distance,
# agenda.py BOSS_GOALS): a level explored once with its boss alive is no level done (rca/2026-10-22/boss-audit-
# findings.md §4 causes 2 and 4: Maffer Dragonhand left in Durance 3 in 11 games, one run judged enough). The player,
# 2026-10-22: "we need to kill all bosses, no exceptions to that". Those runs spent, or the level blocked, the loop
# stops for the player naming the boss, never the game left (tzloop.py BOSS_STAYS). False: as before
BOSSES_HOLD = True
# 3 from 2026-10-23 05:35: Icehawk Riftwing left in Sewers Level 1 after 2 runs, the second cut short by a false
# "blocked" (tzloop.py WAY_TRIED_AT_DOOR); the loop stopped at the shard game's end (05:32:14)
BOSS_RUNS = 3
# KEPT_HOLDS_BOSS (2026-10-23 05:35:08: after the restart Sewers Level 1 stayed cleared from the game's record
# (`Agenda.kept`) with Icehawk Riftwing alive and its BOSS_RUNS not spent, and the loop stopped at once). True: a level
# kept cleared over a restart is reopened while BOSSES_HOLD owes it runs for a live boss. False: kept wins, as before.
KEPT_HOLDS_BOSS = True
# Runs of a level whose map was never read (a run's tour saw no room) before the level is blocked: Durance 1, the
# Forgotten Reliquary and the Forgotten Temple were "done" 0.2 s after arrival, no map read (09:05-09:09 on 2026-10-21)
MAP_TRIES = 2
# The climb to the parent: its leg (loop.py TZ_UP) goes through the level's way back
UP_LEVEL = 'up level'
# A child's way in beside the level run goes before a farther room of its parent (`enter_at`, hunting/choice.py
# `use_at`, agenda.py USE_FIRST): the run goes in as it passes, climbs back and finishes the parent after. The player,
# 2026-10-21 ~09:35: "Enter when passing". Only under `ACTS`. False: the parent's rooms first, then its children
ENTER_PASSING = True
# A Town Portal goal whose trip is the town visit and back through the portal (tzloop.py pushes the room package)
VISIT = 'visit'
# The policies that tour the rooms (agenda.py `in_level`): only there is every room seen part of "fully explored"; on
# the ways on (a corridor to a boss, a stand) the route's stages are the level's work
TOURING = frozenset((COVER, PLUS, FULL_CLEAR))
# The policy a level was worked under when the game's record kept none (a record written before tzloop.py POLICY_NOW,
# macros/midgame.py POLICY_UNKNOWN): not known to have toured its rooms (`rework`)
EARLIER = 'before the record kept policies'
# Stage kinds a level's own work is made of (a `use` leading nowhere: a chest, a seal; a fight; a stand; the loot)
OWN_WORK = frozenset((FIGHT, USE, STAND, LOOT_STAGE))
# Stage 3 (2026-10-21), off: a root cleared walks into the next root's levels across a border or stairs when one of
# them joins it (routes/zone_graph.py `bordering`: Act 4's River of Flame -> City of the Damned -> Plains of Despair ->
# Outer Steppes, Act 3's Travincal -> Kurast Causeway -> Upper Kurast, Act 5's Crystalline Passage -> Glacial Trail ->
# Frozen Tundra -> Ancients' Way) in place of the Town Portal and the waypoint (~9 s measured, plan §6). Off until the
# walk's own cost is measured live: the walk from where the root's run ended to the border is not known. A walk that
# fails, or is made WALK_TRIES times with no arrival, is the Town Portal instead (`no_walk`), said
WALK_ROOTS = False
WALK_TRIES = 3
# The exit a walk's NEXT_LEVEL goal carries (tzloop.py counts its tries)
WALK = 'walk'
# Legs made into one child (NEXT_LEVEL) or up to one parent (UP_LEVEL) from one level with no arrival, after which the
# child is blocked or the climb is the Town Portal, said, instead of the loop's repeat guard leaving the game (the run
# to the door, the press, a run stopped at another door: 3 a way when all goes well). 2026-10-21, after "TZ next level
# again and again" at Upper Kurast's passage to the Causeway (13:48:00)
WAY_TRIES = 6
# The Throne of Destruction's way into the Worldstone Chamber stays the route's `use` of its portal (routes/catalog/
# act5.py), not an `enter`: the portal's gates read that stage (hunting/throne.py `wave_goal`: the hall fought, the
# stand kept until Baal is gone, the portal's foot; running/legs.py `throne_shut`: the level run, not the press, while
# the portal is shut). Under the zone's `enter` neither held: Lister died before his last minions, the way on's press
# came at once from the stand (14 from the portal), teleport.py `baal_gone` found the hall not clear, and tzloop.py's
# USE_TRIES burnt in 0.12 s: the Chamber blocked, the game left with Baal alive (games 4-6, 09:13, 09:21, 09:27 on
# 2026-10-22; rca/2026-10-22/baal-skipped-findings.md). The player, 2026-10-22: "we need to kill all bosses, no
# exceptions to that -> they can give a very valuable drops, especially baal's statue" (tzloop.py BOSS_STAYS: no game
# of the zone is left with Baal alive). False: the `enter` as before
PORTAL_USES = True
USE_WAYS = frozenset({(131, 132)})  # (level, child) whose catalogue portal stays a `use` (`way_in`)
# Stage 3 (2026-10-21), on: the zone's facts this game (levels entered, mapped, explored, runs, cleared, blocked, ways
# back failed) are the agenda's, in the game's one record (macros/midgame.py RECORD, 2026-10-22; before it a file of
# their own, zone-facts.json) and taken back by the first leg after a service restart in the same game (`kept`,
# `resumed`), so a restart does not replay the levels done. A new game is never matched: the key is the game's name
# and the character's unit id (loop.py `GameId`). False: a restart starts the zone afresh, as before
RESUME = True
# Facts older than this are not taken back (a game name and unit id come round again only by chance)
RESUME_SECONDS = 4 * 3600.0
# Stage 3 (2026-10-21), off: the time budget. With the game's time left (loop.py `overdue`: the kind's game_seconds and
# the trips') under what the zone's levels left are estimated to take, the smallest children not on the way to a boss
# are skipped (blocked, said) until it fits, so an act is not cut mid-boss by loop.py ACT_SECONDS. Off: the player's
# ruling of 2026-10-21 ~09:35 (Q6: "in order, boss first") holds until it is asked for. A level's estimate from the
# 2026-10-20/21 logs (797 level stays, `Macro: experience: <level>: ... in N s`): LEVEL_SECONDS + HOSTILE_SECONDS a
# hostile of its population (terror/zones.py `level_population`), plus CHILD_SECONDS for the way in and back up
TIME_BUDGET = False
# A valuable remembered on another level of the graph (macros/sightings.py) is fetched (2026-10-23, game cyberg66: a
# Grand Charm left with no room in Catacombs Level 3 at 23:57:39 on 2026-10-22; the trip for room was cast from
# Catacombs Level 4 after the portal's fight took the stairs, and nothing went back up for it: `sightings.fetch`
# crosses only open passages. The player: "make sure that we pick this grand charm"; "we absolutely must preserve top
# items"). True: `ZoneView.fetch` names its level; in town, on that level's tree, or where the level's own goals would
# leave it or end the game, the goals are the way to it (`fetch_way`: the waypoint to its root, the stairs down into
# the child toward it, one floor up, else the Town Portal), each level's script on the way holding that way
# (`scripts`); on its level the PICKUP goal (`sighted`) as before. False: only the open passages, as before
FETCH_ELSEWHERE = True
LEVEL_SECONDS = 27.0
HOSTILE_SECONDS = 0.32
CHILD_SECONDS = 10.0
# The one model of a level's worth playing on (`worth`, 2026-10-23, rca/2026-10-23/exp-hour-levels-findings.md; the
# player: "your goal is to maximize exp/hour", "run all the time"). A level of the zone is skipped when its expected
# exp an hour is under the game's going rate; never one of an act boss or on the way to one (`boss_way`). Its expected
# rate is its live yield: no pre-entry prior predicts one (the same level's rate on two nights r = 0.03 over 46
# levels, the population r = 0.01; replayed, skipping by either lost 0.1 M/h in levels). STALLED_SKIP: a level with no
# progress (running/watch.py's mark: no kill, no level finished or cleared) for STALL_SECONDS yields 0 M/h: skipped
# (blocked with its why, said once, its run ended at the next look by the SKIPPED policy, the levels under it left as
# `over_budget`'s are). Game cyberg46, 03:24-03:37: 314 s with no kill in Claw Viper Temple Level 1 (monster 74
# targets dropped one by one), the loop stopped by its 300 s no-progress watchdog and stood 5.7 min to a restart:
# ~9.4 min saved, nothing lost (5.90 -> ~6.19 M/h); replayed on cyberg65 a 90 s window cut 2 stays, 4.1 min, 0 exp
# lost. False: a level is played until its verdict, as before
STALLED_SKIP = True  # 2026-10-23: a level with no kill and no level done for STALL_SECONDS is skipped
STALL_SECONDS = 90.0


def on(plan: object) -> bool:
    """Whether the itinerary `plan` is played by the graph: a terrorized act of `ACTS` in it; with no act in it (the
    rotation alone), `ROTATION`."""
    if not isinstance(plan, Itinerary):
        return False
    parts = set(plan.zone.split(' + '))
    acts = {act for act in range(1, 6) if f'Act{act}-Manual' in parts}
    if acts:
        return bool(acts & ACTS)
    return ROTATION


@functools.cache
def graph_of(plan: Itinerary) -> ZoneGraph:
    """The itinerary's trips as the zone graph (routes/zone_graph.py `zone_graph`), roots in the plan's order."""
    chains = tuple(
        Chain(trip.waypoint, trip.areas, trip.zone, trip.hub, trip.tours, trip.passes) for trip in plan.excursions
    )
    return zone_graph(plan.zone, chains)


def act_levels(plan: Itinerary) -> frozenset[int]:
    """The levels of the acts a shard terrorized in `plan` (its `ActN-Manual` parts)."""
    parts = set(plan.zone.split(' + '))
    zones = [manual_zone(act) for act in range(1, 6) if f'Act{act}-Manual' in parts]
    return frozenset(level for zone in zones if zone is not None for level in zone.areas)


def any_act_order(
    graph: ZoneGraph, plan: Itinerary, bosses: Iterable[int] | None, finished: Iterable[int], left: float | None
) -> tuple[int, ...] | None:
    """ROTATION_ANY_ACT: the roots with every rotation root not `finished` right after the root holding the boss of the
    act now played (the act of the first shard root not finished; its boss level's boss among `bosses`, the levels
    with a boss alive in the game's ledger, None not known: every act boss alive until its root is finished), or before
    that act's first root left when its boss is dead; None with the switch off, no shard's act or no rotation left in
    the plan, or under ROTATION_LEAST s of the slot `left` (None: unknown)."""
    if not ROTATION_ANY_ACT or left is None or left < ROTATION_LEAST:
        return None
    act = act_levels(plan)
    if not act:
        return None
    done = frozenset(finished)
    spun = [r for r in graph.roots if r not in done and not any(level in act for level in graph.subtree(r))]
    if not spun:
        return None
    rest = [root for root in graph.roots if root not in spun]
    now = next((root for root in rest if root not in done), None)
    if now is None:
        return (*rest, *spun)
    town = town_of(now)
    boss_levels = frozenset(ACT_BOSS_LEVELS.values()) & act
    if bosses is not None:
        boss_levels &= frozenset(bosses)
    boss = next(
        (
            root
            for root in rest
            if town_of(root) == town and root not in done and set(graph.subtree(root)) & boss_levels
        ),
        None,
    )
    at = rest.index(boss) + 1 if boss is not None else rest.index(now)
    return (*rest[:at], *spun, *rest[at:])


def play_order(
    graph: ZoneGraph,
    plan: Itinerary,
    area: int,
    bosses: Iterable[int] | None = (),
    finished: Iterable[int] = (),
    left: float | None = None,
) -> ZoneGraph:
    """`graph` with the rotation's roots from any act after the boss of the act now played while its slot has
    ROTATION_LEAST s `left` (`ROTATION_ANY_ACT`, `any_act_order`); else the rotation's roots in the act of `area`
    (`town_of`: the Fortress's act after the shard) played first (`ROTATION_FIRST`), and the rotation's others holding
    a level of `bosses` (the levels with a boss alive in the game's ledger) right after the first root holding a shard
    act's boss level (`ROTATION_BOSSES_FIRST`); `graph` itself with none, no shard's act in the plan, or the switch
    off."""
    if not ROTATION_FIRST:
        return graph
    act = act_levels(plan)
    if not act:
        return graph
    spun = any_act_order(graph, plan, bosses, finished, left)
    if spun is not None:
        return graph if spun == graph.roots else replace(graph, roots=spun)
    here = town_of(area)
    alive = frozenset(bosses or ()) if ROTATION_BOSSES_FIRST else frozenset()

    def rotation(root: int) -> bool:
        return not any(level in act for level in graph.subtree(root))

    first = [root for root in graph.roots if rotation(root) and town_of(root) == here]
    ordered = [*first, *(root for root in graph.roots if root not in first)]
    held = [root for root in ordered if root not in first and rotation(root) and set(graph.subtree(root)) & alive]
    if held:
        rest = [root for root in ordered if root not in held]
        bosses_of_acts = frozenset(ACT_BOSS_LEVELS.values()) & act
        at = next((i + 1 for i, root in enumerate(rest) if set(graph.subtree(root)) & bosses_of_acts), len(first))
        ordered = [*rest[:at], *held, *rest[at:]]
    if tuple(ordered) == graph.roots:
        return graph
    return replace(graph, roots=tuple(ordered))


def boss_reach(graph: ZoneGraph, area: int) -> frozenset[int]:
    """The levels whose bosses hold level `area` worked (`BOSSES_HOLD`, tzloop.py BOSS_ZONES, hunting/choice.py
    BOSS_ROTATION): it, the levels under it, and the tour side levels it is a way into with theirs (Duriel's Lair from
    each tomb: a child of the Canyon, `Node.sources` the tombs). Off the graph: `area` alone."""
    if graph.node(area) is None:
        return frozenset((area,))
    levels = set(graph.subtree(area))
    for side, node in graph.nodes.items():
        if node.side and area in node.sources:
            levels |= set(graph.subtree(side))
    return frozenset(levels)


@dataclass(frozen=True)
class LevelState:
    """What this game knows of a level: `entered`; `mapped` a run read its map (rooms); `explored` a run's tour found
    no room left (macros/hunt.py `toured`, rooms read); `runs` self-ended level runs (agenda.py `worked`); `work` a
    route stage of its own left (`own_work`); `blocked` why it cannot be done in this game ('' none); `kept` it was
    cleared before a service restart in this game (`RESUME`: its route facts are gone, the verdict is not); `bosses`
    the bosses of the game's ledger alive on it (`BOSSES_HOLD`)."""

    entered: bool = False
    mapped: bool = False
    explored: bool = False
    runs: int = 0
    work: bool = False
    blocked: str = ''
    kept: bool = False  # cleared before a service restart in this game (`RESUME`)
    bosses: int = 0  # bosses of the game's ledger alive on it, in the game's scope (`BOSSES_HOLD`)


def own_work(
    script: Script | None, facts: Facts, dead: frozenset[str] | None, sides: frozenset[int] = frozenset()
) -> bool:
    """Whether a stage of `script`'s own work (`OWN_WORK`: no way to another level but into a tour's side level of
    `sides`) is not done (routes/progress.py `done`; a fight with the dead unknown counts as left)."""
    if script is None:
        return False
    known = Facts(facts.entered, facts.used, facts.finished, dead, facts.stood, facts.looted)
    return any(done(script.area, stage, known) is not True for stage in own_stages(script, sides))


def own_stages(script: Script, sides: frozenset[int] = frozenset()) -> tuple[Stage, ...]:
    """`script`'s own work: its fights, stands, objects (a `use` into no level, or into a tour's side level of `sides`:
    the Orifice's portal into Duriel's Lair, done where the tomb has none) and, after a fight, the loot. A level's
    `clear` is its policy's (never done by the route), `leave` the game's end, its ways to levels the graph's."""
    fights = any(stage.kind == FIGHT for stage in script.stages)
    return tuple(
        stage
        for stage in script.stages
        if stage.kind in OWN_WORK
        and (not stage.to or (stage.kind == USE and stage.to in sides))
        and not stage.tours
        and not stage.pending
        and (stage.kind != LOOT_STAGE or fights)
    )


def sides_of(graph: ZoneGraph) -> frozenset[int]:
    """The graph's tour side levels (routes/zone_graph.py `Node.side`: Duriel's Lair)."""
    return frozenset(area for area, node in graph.nodes.items() if node.side)


def town_way(script: Script | None) -> Stage | None:
    """The route's own way to a town on the level (Durance 3's Red portal to the Fortress), if any."""
    if script is None:
        return None
    return next((stage for stage in script.stages if stage.to in TOWNS and not stage.pending), None)


def rework(then: str, now: str, explored: bool) -> bool:
    """Whether a level's work under policy `then` does not stand for policy `now` (tzloop.py POLICY_NOW): it toured no
    rooms (a way on, a crossing, a level only crossed, or not known: EARLIER) and `now` tours them, and no tour of its
    found every room seen (`explored`). Its verdict under `then` (cleared, its runs, a block for being left unfinished)
    is no verdict under `now`: it is judged afresh, as a level not entered (Tal Rasha's tombs worked on the way for
    Duriel, the zone turned, then act 2 terrorized by an overflow shard: game cyberg65, 2026-10-22 21:40,
    rca/2026-10-22/tombs-policy-findings.md)."""
    return then != now and then not in TOURING and now in TOURING and not explored


def runs_allowed(node: Node) -> int:
    """Self-ended runs a level may take: RUNS_AN_AREA, and one more for each child its run may stop at the door of."""
    return RUNS_AN_AREA + len(node.children)


def fully_explored(node: Node, state: LevelState, policy: str) -> bool:
    """Entered, its own route stages done, and on a touring policy every room seen (or its runs spent: the loop never
    stands); on a way on (a corridor to a boss) one run made, as the itinerary's rule (tzroutine.py `produce`: a run
    at `runs == 0`); a level only crossed (not terrorized, TRANSIT) once entered. The Halls of Pain and of Anguish (123,
    122: tz+ on the way to Nihlathak and Pindleskin, no stage of their own) were explored on arrival, never run
    (the act harness, 2026-10-21)."""
    if not node.worked and node.area in TOWNS:
        return True  # a town root (the walk out of it): nothing of its own, entered or not
    if not state.entered:
        return False
    held = BOSSES_HOLD and state.bosses > 0
    owed = held and state.runs < runs_allowed(node) + BOSS_RUNS
    if state.kept and not (KEPT_HOLDS_BOSS and owed):
        return True  # cleared before a service restart in this game (`RESUME`)
    if owed:
        return False  # a boss alive on it: its runs go for it (`BOSSES_HOLD`)
    if policy == TRANSIT or not node.worked:
        return True
    if state.runs >= runs_allowed(node):
        return True  # exhausted: said by `judge`
    if state.work:
        return False
    return state.explored if policy in TOURING else state.runs > 0


@dataclass(frozen=True)
class Judged:
    """The zone judged: `explored` the levels fully explored, `cleared` those with every child cleared or blocked,
    `blocked` the levels that cannot be done (why), `exhausted` those left with rooms unseen as their runs ran out."""

    explored: frozenset[int]
    cleared: frozenset[int]
    blocked: Mapping[int, str] = field(hash=False, compare=False)
    exhausted: frozenset[int] = frozenset()
    bosses: frozenset[int] = frozenset()  # the levels with a boss of the ledger alive (`BOSSES_HOLD`)
    # The policy each level was judged under (`judge`'s `policy`; tzloop.py POLICY_NOW keeps it as `worked_under`)
    policies: Mapping[int, str] = field(default_factory=dict, hash=False, compare=False)

    @property
    def finished(self) -> frozenset[int]:
        """Cleared or blocked: nothing more to do there (the agenda's `finished` in zone mode), what the navigation
        goes by. A level with a boss alive is no level cleared while its runs for it are left (`BOSSES_HOLD`); one
        blocked with its boss alive stops the loop (tzloop.py BOSS_STAYS: `boss_stays` at the block, else the game's
        end): taken out of `finished` it was gone into again and again until the loop's repeat guard left the game."""
        return self.cleared | frozenset(self.blocked)

    def gaps(self, graph: ZoneGraph, area: int) -> tuple[int, ...]:
        """The levels under `area` blocked or exhausted: what a cleared level was cleared without."""
        return tuple(level for level in graph.subtree(area)[1:] if level in self.blocked or level in self.exhausted)


def judge(graph: ZoneGraph, states: Mapping[int, LevelState], policy: Callable[[int, frozenset[int]], str]) -> Judged:
    """Every level judged, children before parents: `policy(area, finished)` how it is worked with the levels below it
    finished so far (a level crossed to the boss is a touring one once the boss's trip is over)."""
    explored: set[int] = set()
    cleared: set[int] = set()
    blocked: dict[int, str] = {}
    exhausted: set[int] = set()
    policies: dict[int, str] = {}  # each level's, a blocked one's too (tzloop.py POLICY_NOW)

    def visit(area: int) -> None:
        node = graph.nodes[area]
        for child in node.children:
            visit(child)
        state = states.get(area, LevelState())
        how = policies[area] = policy(area, frozenset(cleared) | frozenset(blocked))
        if state.blocked:
            blocked[area] = state.blocked
            return
        if node.side and not state.entered and all(src in cleared or src in blocked for src in node.sources):
            blocked[area] = "none of its tour's levels led into it"  # every tomb done, no Orifice taken
            return
        if state.entered and node.worked and not state.mapped and state.runs >= MAP_TRIES:
            blocked[area] = f'its map was never read in {state.runs} runs'
            return
        if not fully_explored(node, state, how):
            return
        explored.add(area)
        if state.runs >= runs_allowed(node) and how in TOURING and node.worked and (state.work or not state.explored):
            exhausted.add(area)
        if all(child in cleared or child in blocked for child in node.children):
            cleared.add(area)

    for root in graph.roots:
        visit(root)
    bosses = frozenset(area for area, state in states.items() if state.bosses) if BOSSES_HOLD else frozenset()
    return Judged(frozenset(explored), frozenset(cleared), blocked, frozenset(exhausted), bosses, policies)


def floors_up(graph: ZoneGraph, area: int, to: int) -> int:
    """Stairs (warps) climbed from `area` up to its ancestor `to`; a walk across an open passage is none."""
    floors, node = 0, graph.nodes[area]
    while node.area != to and node.parent is not None:
        floors += 1 if node.back is None or node.back.kind == WARP else 0
        node = graph.nodes[node.parent]
    return floors


def above(graph: ZoneGraph, area: int, judged: Judged) -> int | None:
    """The nearest level above `area` with work left besides the way down to `area`: not fully explored, or a child
    not finished other than the one toward `area`; None when there is none (the root's tree is done but for `area`'s
    branch: the Town Portal, never a climb through levels with nothing left)."""
    came = area
    for level in graph.ancestors(area):
        node = graph.nodes[level]
        if level not in judged.explored and level not in judged.blocked:
            return level
        if any(child != came and child not in judged.finished for child in node.children):
            return level
        came = level
    return None


def climbs(graph: ZoneGraph, area: int, judged: Judged, no_back: Iterable[int] = ()) -> int | None:
    """The parent to climb to from `area` once it is done: when a level above has work left (`above`) within
    CLIMB_FLOORS stairs and the way back is known and has not failed; None: the Town Portal (or nothing is left)."""
    node = graph.nodes[area]
    target = above(graph, area, judged)
    if target is None or node.parent is None or node.back is None or area in set(no_back):
        return None
    return node.parent if floors_up(graph, area, target) <= CLIMB_FLOORS else None


def toward_boss(graph: ZoneGraph, area: int) -> tuple[int, ...]:
    """The children of `area` with a boss at or under them."""
    return tuple(
        child for child in graph.nodes[area].children if any(graph.nodes[level].boss for level in graph.subtree(child))
    )


def next_child(graph: ZoneGraph, area: int, judged: Judged) -> int | None:
    """The child of `area` to go into next: on a level crossed to its boss the child toward the boss first; else a
    one-floor child (none under it) in the trips' order, gone into as the run passes its entrance; a deep one only
    once `area` is fully explored and its one-floor children are done ("TP for deep": last in its parent)."""
    node = graph.nodes[area]
    pending = [child for child in node.children if child not in judged.finished and not graph.nodes[child].side]
    if not pending:
        return None
    toward = [child for child in pending if child in toward_boss(graph, area)]
    if node.crossed and toward:
        return toward[0]
    shallow = [child for child in pending if graph.depth(child) == 1]
    if shallow:
        return shallow[0]
    return pending[0] if area in judged.explored else None


def waiting_deep(graph: ZoneGraph, area: int, judged: Judged) -> bool:
    """Whether `area` has a child left that `next_child` goes into once `area` is explored (a deep one: "TP for
    deep", last in its parent) and `area` is not explored yet: its run comes first and its script has no way back up
    (DEEP_AFTER_RUN)."""
    if not DEEP_AFTER_RUN or area in judged.explored or area in judged.blocked:
        return False
    return any(child not in judged.finished and not graph.nodes[child].side for child in graph.nodes[area].children)


def scripts(
    graph: ZoneGraph,
    judged: Judged,
    base: Callable[[int], tuple[str, Script] | None],
    no_back: Iterable[int] = (),
    no_walk: Iterable[tuple[int, int]] = (),
    fetch: int | None = None,
) -> dict[int, tuple[str, Script]]:
    """Each level's (route, script) for this game: its own work (`own_stages`), the way into its next child
    (`next_child`; a tour's hub its tour over the toured children left), and its way back up when the climb is the way
    on (`climbs`); the route's own way to a town only when nothing above it is left (Mephisto's Red portal ends the
    root); else, with `WALK_ROOTS`, the way across into the next root's levels (`walk_to`). `base(area)`: the
    catalogue's (route, script). `fetch`: the level of a remembered valuable to fetch (FETCH_ELSEWHERE): the levels on
    the way to it hold the way toward it instead (`fetch_child`, `fetch_up`)."""
    found: dict[int, tuple[str, Script]] = {}
    sides = sides_of(graph)
    for area, node in graph.nodes.items():
        given = base(area)
        route, script = given if given is not None else ('Zone', None)
        # A level only crossed (not terrorized) has no work of its own: Travincal's Council on the Durance of Hate
        # zone's way (tzroutine.py `kept_to`, the itinerary's rule; the rotation's harness walk, 2026-10-21)
        stages: list[Stage] = list(own_stages(script, sides)) if script is not None and node.worked else []
        toward = fetch_child(graph, area, fetch) if fetch is not None else None
        up = fetch_up(graph, area, fetch, no_back) if fetch is not None and toward is None else None
        child = next_child(graph, area, judged)
        if toward is not None and (entry := graph.nodes[toward].entry) is not None:
            # FETCH_ELSEWHERE: the way toward the remembered valuable's level first
            toured = graph.nodes[toward].toured
            stages.append(tour(entry.mark, (toward,)) if toured else way_in(area, toward, entry.mark, entry.kind))
        elif up is not None and node.back is not None:
            stages.append(back(node.back.mark, up))
        elif child is not None:
            entry = graph.nodes[child].entry
            if entry is not None and graph.nodes[child].toured:
                # A tour's hub (the Canyon of the Magi): its marks lead into its levels in an order not known, so the
                # tour's stage over those not finished, the nearest mark not yet gone through first
                # (macros/route.py `note_toured`, routes/progress.py `lead`'s skip)
                stages.append(tour(entry.mark, toured_left(graph, area, judged)))
            elif entry is not None:
                stages.append(way_in(area, child, entry.mark, entry.kind))
        elif waiting_deep(graph, area, judged):
            pass  # the level's run first, then its deep child (DEEP_AFTER_RUN): no way back up, no way on yet
        elif (parent := climbs(graph, area, judged, no_back)) is not None and node.back is not None:
            stages.append(back(node.back.mark, parent))  # the run ends at it: the climb's press is the way on
        elif (town := town_way(script)) is not None and above(graph, area, judged) is None:
            stages.append(town)
        elif above(graph, area, judged) is None and (onward := walk_to(graph, area, judged, no_walk)) is not None:
            stages.append(enter(way(area, onward).mark, onward))  # across the border into the next root's levels
        found[area] = (route, Script(area, tuple(stages)))
    return found


def way_in(area: int, child: int, mark: str, kind: str) -> Stage:
    """The stage into `child` from `area` by the way's `mark` of `kind` (routes/zone_graph.py `Way`): the catalogue's
    `use` for a portal of USE_WAYS (`PORTAL_USES`), else an `enter`."""
    if PORTAL_USES and kind == PORTAL and (area, child) in USE_WAYS:
        return use(mark, child)
    return enter(mark, child)


def toured_left(graph: ZoneGraph, area: int, judged: Judged) -> tuple[int, ...]:
    """The toured children of hub `area` not finished, in the tour's order."""
    return tuple(
        child for child in graph.nodes[area].children if graph.nodes[child].toured and child not in judged.finished
    )


def walk_to(graph: ZoneGraph, area: int, judged: Judged, no_walk: Iterable[tuple[int, int]] = ()) -> int | None:
    """With `WALK_ROOTS`, the level of the next root's tree (`next_root`) to walk or step into from `area`, done
    (`bordering`, no town between): the root itself first, else the first of its levels not finished in the tree's
    order; None with none, the switch off, or that walk failed (`no_walk`: the Town Portal then)."""
    if not WALK_ROOTS or graph.node(area) is None:
        return None
    root = next_root(graph, judged)
    if root is None or root == area:
        return None
    failed = set(no_walk)
    for level in graph.subtree(root):
        if level in judged.finished or level == area or (area, level) in failed:
            continue
        if level in TOWNS or not bordering(area, level):
            continue
        return level
    return None


def enter_at(plan: object, stage: Stage | None, place: tuple[float, float]) -> tuple[float, float] | None:
    """`place`, the door of the level run's route stage `stage`, when that stage is a child's way in the run goes into
    as it passes it (`ENTER_PASSING`, under zone navigation of `plan`): agenda.py `in_level` then yields to it before a
    farther room (USE_FIRST). None for any other stage (a way back, a tour, a pending one) or with the switches off."""
    if not ENTER_PASSING or stage is None or stage.kind != ENTER or not stage.to or not on(plan):
        return None
    return None if stage.back or stage.tours or stage.pending else place


def allowed(graph: ZoneGraph, area: int) -> frozenset[int] | None:
    """The levels a run on `area` may be carried into across an open passage (pursuit.py `Pursuit.allowed`): its own,
    its parent and its children in the graph. A run crosses a passage only toward its route stage's goal, which the
    zone's script sets to the child chosen next (`scripts`: `enter`) or to the parent (`back`), so the walk across is
    the leg's (`NEXT_LEVEL`, `UP_LEVEL`) and the run's verdict is read wherever it ends (runner.py `_zone_seen`). Its
    own only (before 2026-10-21 ~13:50) ended Upper Kurast's run "Kurast Causeway leads off the trip" 30 times in 3 s
    and the repeat guard left the game, a shard lost (13:48:00 on 2026-10-21). None off the graph."""
    node = graph.node(area)
    if node is None:
        return None
    parent = () if node.parent is None else (node.parent,)
    return frozenset((area, *parent, *node.children))


@dataclass(frozen=True)
class ZoneView:
    """What `produce` reads: the level (`area`, `in_town`), the graph and its judgement, the route stage on the level
    (its zone script's, routes/progress.py `step`: `stage`, `stage_to`), a valuable `sighted` here, the town visit
    due, the levels whose way back failed (`no_back`), the walks across that failed (`no_walk`, (from, to))."""

    area: int
    in_town: bool
    graph: ZoneGraph
    judged: Judged
    stage: str | None = None
    stage_to: int = 0
    sighted: str | None = None
    visit_due: bool = False
    no_back: frozenset[int] = frozenset()
    no_walk: frozenset[tuple[int, int]] = frozenset()
    passed: bool = False  # a run on `area` ended since the character came to it (at a child's door, as it passed)
    # FETCH_ELSEWHERE: (level, label) of a valuable remembered on another level of the graph (`fetch_way`)
    fetch: tuple[int, str] | None = None


def next_root(graph: ZoneGraph, judged: Judged) -> int | None:
    """The first root, in play order, not finished."""
    return next((root for root in graph.roots if root not in judged.finished), None)


def fetch_child(graph: ZoneGraph, area: int, to: int | None) -> int | None:
    """FETCH_ELSEWHERE: the child of `area` whose levels hold level `to` (the stairs down toward it); None when `to`
    is `area`, not under it, or off the graph."""
    if not FETCH_ELSEWHERE or to is None or to == area or graph.node(area) is None or graph.node(to) is None:
        return None
    return next((child for child in graph.nodes[area].children if to in graph.subtree(child)), None)


def fetch_up(graph: ZoneGraph, area: int, to: int | None, no_back: Iterable[int] = ()) -> int | None:
    """FETCH_ELSEWHERE: the parent of `area` to climb to toward level `to` on the same tree: `to` not under `area`,
    the level above both within CLIMB_FLOORS stairs, `area`'s way back known and not failed; None otherwise (the Town
    Portal and the waypoint instead)."""
    if not FETCH_ELSEWHERE or to is None or to == area or graph.node(area) is None or graph.node(to) is None:
        return None
    node = graph.nodes[area]
    if node.root != graph.nodes[to].root or node.parent is None or node.back is None or area in set(no_back):
        return None
    if to in graph.subtree(area):
        return None
    common = next((level for level in graph.ancestors(area) if to in graph.subtree(level)), None)
    if common is None or floors_up(graph, area, common) > CLIMB_FLOORS:
        return None
    return node.parent


def fetch_way(view: ZoneView) -> list[Objective] | None:
    """FETCH_ELSEWHERE: the goal toward `view.fetch`'s level from `view.area` (the switch's text); None with none,
    the switch off, or its level the character's or off the graph."""
    if not FETCH_ELSEWHERE or view.fetch is None:
        return None
    graph, area = view.graph, view.area
    to, label = view.fetch
    node = graph.node(to)
    if node is None or to == area or to in view.judged.blocked:
        return None  # a level blocked for the game: no way in (the guard keeps the game at its end, as before)
    what = f'{label} in {display_name(to)}'
    if view.in_town:
        root = node.root
        if root == area:
            child = fetch_child(graph, root, to)
            if child is None:
                return None
            label = f'out of {display_name(area)} into {display_name(child)} to fetch {what}'
            return [Objective(WALK_OUT, label, EXCURSION, area, to=child)]
        tier = ERRAND if root in TOWNS else EXCURSION  # town to town, else to the zone's waypoint
        return [Objective(WAYPOINT, f'to {display_name(root)} to fetch {what}', tier, to=root)]
    child = fetch_child(graph, area, to)
    if child is not None:
        return [Objective(NEXT_LEVEL, f'on into {display_name(child)} to fetch {what}', ONWARD, area, to=child)]
    parent = fetch_up(graph, area, to, view.no_back)
    if parent is not None:
        return [Objective(UP_LEVEL, f'up into {display_name(parent)} to fetch {what}', ONWARD, area, to=parent)]
    return [Objective(PORTAL_TO_TOWN, f'Town Portal to fetch {what}', EXCURSION, area)]


def produce(view: ZoneView) -> list[Objective]:
    """The game-level goals wanted now; empty means the game's end next (agenda.py `game_end`). A valuable remembered
    on another level (FETCH_ELSEWHERE): the way to it in town, on its tree, or where these goals would leave the level
    or end the game; never with one on this level (its PICKUP first), the town visit due or a boss's loot here."""
    goals = _produce(view)
    if not FETCH_ELSEWHERE or view.fetch is None or view.sighted is not None or view.visit_due:
        return goals
    if any(goal.exit == VISIT or goal.kind == LOOT for goal in goals):
        return goals  # the visit's portal, a boss's drops first
    node, there = view.graph.node(view.area), view.graph.node(view.fetch[0])
    on_tree = node is not None and there is not None and node.root == there.root
    leaving = not any(goal.kind in (LEVEL, LOOT) for goal in goals)
    if view.in_town or on_tree or leaving:
        way = fetch_way(view)
        if way is not None:
            return way
    return goals


def _produce(view: ZoneView) -> list[Objective]:
    """`produce`'s goals of the zone itself."""
    graph, judged, area = view.graph, view.judged, view.area
    root = next_root(graph, judged)
    if view.in_town:
        if view.visit_due:
            if area != PANDEMONIUM_FORTRESS:
                return [Objective(WAYPOINT, 'to the Fortress for the visit', ERRAND, to=PANDEMONIUM_FORTRESS)]
            return [Objective(TOWN_ROUTINE, 'the town visit', ERRAND, exit='waypoint')]
        if root is None:
            return []
        if root == area:
            child = next_child(graph, root, judged) or next(
                (each for each in graph.nodes[root].children if each not in judged.finished), None
            )
            if child is not None:
                label = f'out of {display_name(area)} into {display_name(child)}'
                return [Objective(WALK_OUT, label, EXCURSION, area, to=child)]
            return []
        return [Objective(WAYPOINT, f'to {display_name(root)} (zone)', EXCURSION, to=root)]
    goals: list[Objective] = []
    if view.sighted is not None:
        goals.append(Objective(PICKUP, f'{view.sighted}, still on the ground', SIGHTED, area))
    node = graph.node(area)
    if node is None:
        if root is not None:
            goals.append(Objective(PORTAL_TO_TOWN, 'Town Portal: off the zone', EXCURSION, area))
        return goals
    if view.stage == USE and view.stage_to in TOWNS:
        label = f'to {display_name(view.stage_to)} by the route: the root ends'
        goals.append(Objective(LEVEL, label, WORK, area, to=view.stage_to))
        return goals
    if view.stage == LOOT_STAGE:
        # A boss's drops before anything else of the level's (the stage after its fight)
        goals.append(Objective(LOOT, f'the loot of {display_name(area)}', LOOTING, area))
        return goals
    child = next_child(graph, area, judged)
    unexplored = area not in judged.explored and area not in judged.blocked
    passing = (
        ENTER_PASSING
        and view.passed
        and child is not None
        and not graph.nodes[child].toured
        and graph.depth(child) == 1
        and graph.nodes[child].entry is not None
    )
    if (
        unexplored
        and not passing
        and not (child is not None and graph.nodes[area].crossed and child in toward_boss(graph, area))
    ):
        # The level's run first: its script ends in the child's way in, taken as the run passes it (ENTER_PASSING,
        # hunting/choice.py) or once its rooms are seen; a level crossed to its boss goes on toward the boss at once.
        # A run that ended since the character came here ended at that child's door (`passing`): the press into it
        # next, not a run again (6 runs of Upper Kurast in 1.4 s, each "at Forgotten Reliquary: going through takes
        # a press", and the city judged explored as its runs ran out: 14:10:58 on 2026-10-21)
        goals.append(Objective(LEVEL, f'the {display_name(area)} run (zone)', WORK, area))
        return goals
    if child is not None:
        if graph.nodes[child].toured:
            left = len(toured_left(graph, area, judged))
            label = f'on into the nearest toured level not entered ({left} left, zone)'
        else:
            label = f'on into {display_name(child)} (zone)'
        goals.append(Objective(NEXT_LEVEL, label, ONWARD, area, to=child))
        return goals
    parent = climbs(graph, area, judged, view.no_back)
    if parent is not None:
        if view.visit_due:
            goals.append(Objective(PORTAL_TO_TOWN, 'Town Portal for the visit, then back', ERRAND, area, exit=VISIT))
        else:
            goals.append(Objective(UP_LEVEL, f'up into {display_name(parent)} (zone)', ONWARD, area, to=parent))
        return goals
    onward = walk_to(graph, area, judged, view.no_walk) if above(graph, area, judged) is None else None
    if onward is not None:
        label = f'walk on into {display_name(onward)} (zone: the next root, no Town Portal)'
        goals.append(Objective(NEXT_LEVEL, label, ONWARD, area, to=onward, exit=WALK))
        return goals
    if above(graph, area, judged) is not None or root is not None:
        goals.append(Objective(PORTAL_TO_TOWN, 'Town Portal for the next part of the zone', EXCURSION, area))
    return goals


def level_seconds(area: int) -> float:
    """A level's estimated seconds (`TIME_BUDGET`): LEVEL_SECONDS, HOSTILE_SECONDS a hostile of its population, and
    CHILD_SECONDS for its way in and back up."""
    return LEVEL_SECONDS + HOSTILE_SECONDS * (level_population(area) or 0) + CHILD_SECONDS


def left_seconds(graph: ZoneGraph, judged: Judged, levels: Iterable[int] | None = None) -> float:
    """The estimated seconds of the levels (all the graph's by default) not finished and worked."""
    found = graph.nodes if levels is None else levels
    return sum(level_seconds(level) for level in found if level not in judged.finished and graph.nodes[level].worked)


def over_budget(
    graph: ZoneGraph, judged: Judged, remaining: float | None, keep: Iterable[int], protected: Iterable[int] = ()
) -> tuple[int, ...]:
    """With `TIME_BUDGET` and `remaining` seconds of the game left under what the zone's levels left take
    (`left_seconds`), the children to skip: the smallest first (by the population of what is left under them), never a
    root, a level of `keep` (where the character is) or above it, nor a subtree with a boss (`Node.boss`) or a level of
    `protected` (a route fight: the Countess, the Summoner), until the rest fits. () when it fits or with the switch
    off."""
    if not TIME_BUDGET or remaining is None:
        return ()
    total = left_seconds(graph, judged)
    if total <= remaining:
        return ()
    held = set(keep)
    for level in tuple(held):
        if graph.node(level) is not None:
            held |= set(graph.ancestors(level))
    guarded = set(protected)
    candidates = [
        level
        for level, node in graph.nodes.items()
        if node.parent is not None
        and node.worked
        and level not in judged.finished
        and level not in held
        and not any(graph.nodes[under].boss or under in guarded for under in graph.subtree(level))
    ]

    def value(level: int) -> float:
        return sum(level_population(under) or 0 for under in graph.subtree(level) if under not in judged.finished)

    skipped: list[int] = []
    gone: set[int] = set()
    for level in sorted(candidates, key=lambda each: (value(each), each)):
        if total <= remaining:
            break
        if level in gone:
            continue
        under = [each for each in graph.subtree(level) if each not in gone]
        total -= left_seconds(graph, judged, under)
        gone |= set(under)
        skipped.append(level)
    return tuple(skipped)


def boss_way(graph: ZoneGraph, area: int) -> bool:
    """Whether level `area` holds an act boss (tzroutine.py ACT_BOSS_LEVELS) or is on the way to one: it, a level under
    it, or a tour side level it leads into (`boss_reach`: Duriel's Lair from each tomb)."""
    acts = frozenset(ACT_BOSS_LEVELS.values())
    return area in acts or bool(boss_reach(graph, area) & acts)


def worth(graph: ZoneGraph, area: int, stalled: float | None, going: float | None) -> str | None:
    """Whether level `area` of the zone is worth playing on (STALLED_SKIP): the why of its skip, None to play it. Its
    expected exp an hour is its live yield: `stalled` seconds with no progress on it (None not known) of STALL_SECONDS
    and more yield none; `going` the game's exp an hour (None unread). Never a level off the graph or not worked (a
    town, a level only crossed), nor one of an act boss or on the way to one (`boss_way`)."""
    node = graph.node(area)
    if not STALLED_SKIP or node is None or not node.worked or boss_way(graph, area):
        return None
    if stalled is None or stalled < STALL_SECONDS:
        return None
    expected = 0.0
    if going is not None and expected >= going:
        return None  # the game yields no more elsewhere
    against = f"the game's {going / 1e6:.1f} M/h" if going is not None else "the game's rate unread"
    stall = f'no kill and no level done for {stalled:.0f} s'
    return f'{SKIPPED}: {stall}, expected {expected / 1e6:.1f} M/h against {against}'


def said(graph: ZoneGraph, judged: Judged, area: int) -> str:
    """How level `area` stands, for the log: cleared (with what it was cleared without), blocked and why, or what holds
    it."""
    name = f'{display_name(area)} ({area})'
    if area in judged.blocked:
        return f'{name} blocked: {judged.blocked[area]}'
    if area in judged.cleared:
        gaps = judged.gaps(graph, area)
        unseen = ', rooms left unseen as its runs ran out' if area in judged.exhausted else ''
        return f'{name} cleared{unseen}' + (f', without {list(gaps)}' if gaps else '')
    held = [child for child in graph.nodes[area].children if child not in judged.finished]
    if area in judged.explored:
        return f'{name} explored, held by {held}'
    return f'{name} not explored' + (f', children left {held}' if held else '')
