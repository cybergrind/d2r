"""The KP_6 loop's terror zone kinds (TZ leveling, Full clear TZ): each leg is one agenda goal (macros/goals-plan.md).

`choose` reads the game into a `tzroutine.GameView`, derives the game-level goals (`tzroutine.produce`) and asks the
agenda for the next one (`Agenda.next`: stack, then queue, then LEAVE_GAME; in act 3 first Town Portal home and the
waypoint to the Fortress, agenda.py `game_end`, 2026-10-19). `perform` makes it one leg with the
existing routines (routines.py, waypoint.py, visit.py, portal.py, pursuit.py via `LegHands.level_run`).
Offered by three presses of KP_6 and restart.py `--kind tz` / `--kind tzclear` while `ENABLED`.
"""

import functools
import json
import math
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.game.records import World
from inventory_tracking.levels.presets import display_name, numbered_name
from inventory_tracking.macros import actloop, merc, zonenav
from inventory_tracking.macros.actuator import Abort, Hand
from inventory_tracking.macros.agenda import (
    EXCURSION,
    LEAVE_GAME,
    LEVEL,
    LOOT,
    NEW_GAME,
    NEXT_LEVEL,
    PANDEMONIUM_FORTRESS,
    PICKUP,
    PORTAL_TO_TOWN,
    STACK,
    SWAP_AWAY,
    SWAP_CHOOSE,
    SWAP_GOALS,
    SWAP_HOME,
    SWAP_PARK,
    SWAP_PICK,
    TERRORIZE,
    THROUGH_PORTAL,
    TOWN_ROUTINE,
    TOWNS,
    WALK_OUT,
    WAYPOINT,
    Agenda,
    Objective,
    gheeds_fetch,
    gheeds_package,
    room_package,
    town_of,
)
from inventory_tracking.macros.bossledger import Boss, BossLedger, said, stop_line
from inventory_tracking.macros.charms import Stats, candidates
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.loop import (
    CHOOSE,
    DROPS_AFTER_KILL,
    GHEED_CHOOSE,
    GHEED_PICK,
    GHEED_STASH,
    LEAVE,
    NEXT_GAME,
    PICK,
    REPEAT,
    ROGUE_ENCAMPMENT,
    SWAP_BACK,
    SWAP_OUT,
    TOWN,
    TZ_BACK,
    TZ_LEVEL,
    TZ_LOOT,
    TZ_NEXT_LEVEL,
    TZ_OUT,
    TZ_PICKUP,
    TZ_PORTAL,
    TZ_SHARD,
    TZ_UP,
    TZ_WAYPOINT,
    Dead,
    GameId,
    LegHands,
    Loop,
    teleports,
)
from inventory_tracking.macros.pickup import Refused
from inventory_tracking.macros.portal import to_town
from inventory_tracking.macros.repair import gold
from inventory_tracking.macros.routines import DEAD
from inventory_tracking.macros.shop import gold_cap
from inventory_tracking.macros.teleport import Untook
from inventory_tracking.macros.town import Exit
from inventory_tracking.macros.tzroutine import (
    ACT_BOSS_LEVELS,
    ON_THE_WAY,
    Excursion,
    GameView,
    Itinerary,
    itinerary,
    kept_to,
    policy_of,
    produce,
)
from inventory_tracking.macros.visit import Remembered
from inventory_tracking.macros.waypoint import travel
from inventory_tracking.native.layout import DEAD_MODES
from inventory_tracking.routes.model import FIGHT, Script
from inventory_tracking.routes.progress import Facts, Progress
from inventory_tracking.routes.tz_groups import installed_active_zones, manual_zone
from inventory_tracking.routes.zone_graph import ZoneGraph
from inventory_tracking.terror.bosses import KILLED_AT


# False: only the Lower Kurast and Andariel kinds. On since 2026-10-19 (the player: "launch tz-leveling loop after
# then next run and monitor/improve it"); goals-plan.md §9's checks are made live
ENABLED = True
# Games begun in a row with no level run, after which the loop stops (cause 'idle'): a game made and left at once, again
# and again, risks Battle.net's limit on game creation (2026-10-19, rca/2026-10-19/tz-coverage-findings.md F1)
IDLE_GAMES = 3
# The terror zones turn every ZONE_TURN s of the wall clock (01:30 to 03:30 on 2026-10-20, each on the half hour); an
# unplayable zone is waited out to ZONE_SETTLE s after the next turn (`zone_wait`)
ZONE_TURN = 1800.0
ZONE_SETTLE = 20.0
# Pickups back by the refused charm before the swap goes to town without it (`pick_new`)
PICK_TRIES = 4
# A door no click takes on the way on (teleport.py `walk_into`, `pad_door`: cause 'door') ends the trip it leads on, and
# the zone goes on with its next trip; the last trip's ends the game as the agenda ends it (`skip_door`). "No click took
# Crypt" left four games in a row (08:01-08:07 on 2026-10-21), the Mausoleum's trip never tried
# (rca/2026-10-21/crypt-door-findings.md §6). False: the stop leaves the game as any other (stops.py RECOVER). Only
# the way on's press reaches a door: a posted level run clicks none (running/execution.py `_teleport_step`)
SKIP_DOOR = True
# An object's clicks that took nothing on the way into a child (teleport.py `Untook`: a portal) under zone navigation:
# the leg made again up to USE_TRIES legs (the Throne's portal opens only once Baal walked into it), then the child is
# blocked and its parent goes on (`zone_use`). "No click took Worldstone Chamber" left the game at 17:24:39 on
# 2026-10-21 with act 5's other zones unplayed. False: the stop leaves the game as any other (stops.py RECOVER)
SKIP_USE = True
USE_TRIES = 3
# An `Untook` that says the hall is to be fought first (teleport.py `baal_gone`: a hostile in the throne hall with Baal
# on his throne) posts the level run, which fights it (hunting/throne.py `wave_goal`), instead of counting a try: games
# 4-6 at 09:13, 09:21, 09:27 on 2026-10-22 burnt USE_TRIES in 0.12 s with Lister's minions alive, nothing fought between
# them, the Chamber blocked and Baal left alive (rca/2026-10-22/baal-skipped-findings.md). At most FOUGHT_RUNS such runs
# a way, so a hall the run cannot clear still ends in the tries and the block. False: counted as any try, as before
FOUGHT_FIRST = True
FOUGHT_RUNS = 4
FOUGHT = 'fought first'  # teleport.py `baal_gone`'s word for it
# The player, 2026-10-22: "we need to kill all bosses, no exceptions to that -> they can give a very valuable drops,
# especially baal's statue"; "we should always kill act bosses, no need to kill hepasto if it is just travel through".
# The bosses are the game's ledger's (macros/bossledger.py: the route catalogue's fights and the scripts' bosses of the
# levels in the game's scope, `boss_scope`, and the super uniques their rooms place), not a list here. True: a level
# holding a boss alive (zonenav.py `boss_reach`) whose way in is spent (USE_TRIES after the FOUGHT_RUNS, zonenav.py
# WAY_TRIES, a door no click takes in USE_TRIES tries) is never blocked: the loop stops where it is for the player
# (`boss_stays`: cause 'idle', stops.py STOP, the game not left, the bosses named); and a zone game is never ended ("no
# goals left", or the way to the act's last town) with a boss of its scope alive (`boss_alive`: the same stop).
# rca/2026-10-22/boss-audit-findings.md §4 causes 1 and 2: 183 of 438 boss-game rows ended on "no goals left". False:
# blocked, the zone goes on and the game is left at its end, as before
BOSS_STAYS = True
# The act bosses' levels (tzroutine.py ACT_BOSS_LEVELS): in the game's scope whenever its plan reaches them, worked or
# only crossed (`boss_scope`); a level only crossed is no other boss's (Hephasto in the River of Flame)
ACT_BOSSES = frozenset(ACT_BOSS_LEVELS.values())
# A rotating zone that turned in this game with a boss of the ledger alive on a level of its own (and no zone of the new
# plan holding that level) is kept in the plan (`zone_of`): its levels holding a live boss are worked on the way
# (hunting/choice.py BOSS_ROTATION), the others blocked (TURNED, `turned_levels`), until those bosses are dead or their
# runs spent (zonenav.py BOSSES_HOLD). The audit's "zone rotation" cause: 72 boss-game rows in 32 games (a replanned
# zone dropped the old zone's bosses: Duriel, Andariel, the Summoner, Radament...). Each level is in one rotating zone
# only, so the zone is the ledger's, read back after a restart. False: the plan is the zones read now, as before
BOSS_ZONES = True
TURNED = 'the zone turned: no boss of the game is left there'
# No Town Portal cast in a fight (2026-10-22, rca/2026-10-22/portal-cast-findings.md): the Sling's cast was dropped in a
# block with 5 hostiles within 30 after the terror zone turned (09:30:05, The Worldstone Keep Level 3) and cut by a
# block with Fetishes striking at 3 units in a zone read as cleared (22:26:32 on 2026-10-21, Spider Forest); the rule
# lived only in the runner's stop rules (running/watch.py, recovery.py). True: with a hostile within SIGHT of the
# character the PORTAL_TO_TOWN goal posts a fight instead of the cast (its goal kept), at most PORTAL_FIGHTS times a
# goal on a level, then the cast as before (portal.py CAST_FREE's wait and second cast). On a level no longer
# terrorized the agenda's run ends at once (hunting/choice.py ZONE_LEFT), so the fight there is the plain run
# (`LegHands.fight`, past nothing); elsewhere the run against an attacker (`fight_back`). False: cast at once
PORTAL_FIGHT_FIRST = True
PORTAL_FIGHTS = 3
_portal_fights: dict[tuple, int] = {}  # (game, area, goal key) -> fights posted; only this game's kept
# A recovery's game end (`next_goal`): a stop already ruled on (stops.py), left as before
GIVEN_UP = 'the game given up (a recovery)'
# The file beside the loop's store (loop.py `Loop.store`) the zone's facts are kept in for a service restart
# (zonenav.py RESUME, 2026-10-21); the games kept, the latest last
ZONE_FILE = 'zone-facts.json'
ZONE_GAMES = 8

# The leg each goal is made as (the HUD's and the log's `Loop: game N, <leg>`; the watch tools' phases)
LEGS = {
    NEW_GAME: NEXT_GAME,
    WAYPOINT: TZ_WAYPOINT,
    TOWN_ROUTINE: TOWN,
    PORTAL_TO_TOWN: TZ_PORTAL,
    THROUGH_PORTAL: TZ_BACK,
    LEVEL: TZ_LEVEL,
    LOOT: TZ_LOOT,
    PICKUP: TZ_PICKUP,
    NEXT_LEVEL: TZ_NEXT_LEVEL,
    zonenav.UP_LEVEL: TZ_UP,
    WALK_OUT: TZ_OUT,
    TERRORIZE: TZ_SHARD,
    LEAVE_GAME: LEAVE,
    # The Gheed's swap in Andariel's words (loop.py), for the watch tools (andy.py SWAP_LEGS)
    SWAP_AWAY: SWAP_OUT,
    SWAP_PARK: GHEED_STASH,
    SWAP_PICK: GHEED_PICK,
    SWAP_HOME: SWAP_BACK,
    SWAP_CHOOSE: GHEED_CHOOSE,
    # The merc lost or the belt empty (macros/merc.py, 2026-10-21): the routine in the Fortress, Jamella and Tyrael
    merc.MERC_ROUTINE: merc.MERC_TRIP,
}


@functools.cache
def zone_levels() -> frozenset[int]:
    """Every level of an installed Terror Zone."""
    return frozenset(area for zone in installed_active_zones() for area in zone.areas)


def zone_wait(now: float) -> float:
    """Seconds from `now` (time.time()) to ZONE_SETTLE after the next terror zone turn."""
    return ZONE_TURN - now % ZONE_TURN + ZONE_SETTLE


def leg_of(goal: Objective) -> str:
    """The leg `goal` is made as."""
    return LEGS[goal.kind]


def zone_of(tz: LegHands, acts: tuple[int, ...] = (), bosses: BossLedger | None = None) -> Itinerary | None:
    """The itinerary of the zones the tracker reads as terrorized now (tzroutine.py `itinerary`), with each of `acts`
    a shard terrorized in this game (agenda.py `Agenda.acts`): planned whether or not the client's list names it
    (rca/2026-10-20/act-terrorize-findings.md §6 check 4 is open), and played in their order (the kind's act first,
    then the acts of shards over the limit: actloop.py OVERFLOW); and the rotating zones turned with a boss of
    `bosses` alive (BOSS_ZONES, `boss_zones`)."""
    read = frozenset(area for area in zone_levels() if tz.terrorized(area))
    known = frozenset(area for act in acts if (zone := manual_zone(act)) is not None for area in zone.core)
    plan = itinerary(read | known, tuple(acts))
    kept = boss_zones(bosses, plan, tz) if bosses is not None else frozenset()
    return itinerary(read | known | kept, tuple(acts)) if kept else plan


def boss_zones(bosses: BossLedger, plan: Itinerary | None, tz: LegHands) -> frozenset[int]:
    """BOSS_ZONES: the Herald levels (`core`) of each rotating zone none of whose levels `plan` holds, none read
    terrorized, with a boss of the ledger alive on a level of its own; said when that changes."""
    if not BOSS_ZONES:
        return frozenset()
    alive = bosses.alive()
    held = plan.areas if plan is not None else frozenset()
    found: list[tuple[str, frozenset[int], list[Boss]]] = []
    for zone in installed_active_zones():
        mine = [boss for boss in alive if boss.area in zone.areas and boss.area not in held]
        if mine and not any(tz.terrorized(area) for area in zone.core):
            found.append((zone.name, zone.core, mine))
    text = '; '.join(f'{name} ({said(mine)} alive)' for name, _, mine in found)
    if _zones_kept.get(bosses.game) != text:
        _zones_kept.clear()
        _zones_kept[bosses.game] = text
        if text:
            # The watch tools may read it (d2-loop-watch logwords.py)
            LOG.info('Macro: zone: turned and kept in the plan for their bosses: %s', text)
    return frozenset(area for _, core, _ in found for area in core)


_zones_kept: dict[str | None, str] = {}  # the game's kept zones last said (`boss_zones`), the log's only


@functools.cache
def boss_scope(plan: Itinerary) -> frozenset[int]:
    """The levels whose bosses `plan`'s game kills: the levels its zone works (the graph's worked nodes, else the
    trips' terrorized levels) and the act bosses' levels it reaches (ACT_BOSSES); never another level only crossed."""
    if zonenav.on(plan):
        graph = zonenav.graph_of(plan)
        return frozenset(area for area, node in graph.nodes.items() if node.worked or area in ACT_BOSSES)
    return frozenset(area for trip in plan.excursions for area in trip.areas if area in trip.zone or area in ACT_BOSSES)


def bosses_planned(agenda: Agenda, progress: Progress | None, plan: Itinerary) -> None:
    """The game's ledger on the tracker's book (routes/progress.py `Progress.dead` is its `killed`) with the bosses
    of `plan`'s scope (`boss_scope`) known before their levels are read."""
    agenda.bosses.attach(progress.dead if progress is not None else None)
    agenda.bosses.plan(sorted(boss_scope(plan)))


def bosses_alive(agenda: Agenda, levels: frozenset[int] | None = None) -> list[Boss]:
    """BOSS_STAYS: the ledger's bosses alive in the scope of the agenda's plan (`boss_scope`), of `levels` only when
    given; none off a plan or with the switch off."""
    plan = agenda.plan
    if not BOSS_STAYS or not isinstance(plan, Itinerary):
        return []
    scope = boss_scope(plan)
    return agenda.bosses.alive(scope if levels is None else scope & levels)


def turned_levels(plan: Itinerary, wanted: Callable[[int], bool | None] | None) -> frozenset[int]:
    """The levels of `plan`'s rotating zones whose Herald levels all read not terrorized (`wanted`: the tracker's
    `terrorized`) and no zone of it still holds: a zone kept for its bosses (BOSS_ZONES)."""
    if not BOSS_ZONES or wanted is None:
        return frozenset()
    names = set(plan.zone.split(' + '))
    zones = [zone for zone in installed_active_zones() if zone.name in names]
    turned = [zone for zone in zones if all(wanted(area) is False for area in zone.core)]
    if not turned:
        return frozenset()
    live = {area for zone in zones if zone not in turned for area in zone.areas}
    for act in range(1, 6):
        if f'Act{act}-Manual' in names and (manual := manual_zone(act)) is not None:
            live |= set(manual.areas)
    return frozenset(area for zone in turned for area in zone.areas if area not in live)


def choose(world: World, progress: Progress | None, loop: Loop, tz: LegHands | None) -> Objective:
    """The next leg's goal. `Dead` with the character dead; `Abort` with no zone read."""
    agenda = loop.agenda
    if not world.in_game:
        return agenda.next(None, in_game=False)
    player = world.player
    if player is None:
        raise Abort('not in a game')
    if player.mode in DEAD:
        raise Dead('the character is dead')
    if tz is None:
        raise Abort('no terror zone hands')
    played = bool(agenda.worked)  # the game before had a level run (one carried on across a way out counts too)
    if agenda.begin(loop.game_id or world.game_name):
        if played:
            # The Chaos Sanctuary zone: the River of Flame's crossing carries on into the Sanctuary (seals, Diablo) in
            # one run, no LEVEL leg; two Diablo games stopped the loop as idle (08:38:04 on 2026-10-20)
            loop.idle = 0
        loop.idle += 1
        if loop.idle > IDLE_GAMES:
            loop.idle = 0  # turned on again, the loop counts afresh
            raise Abort(f'{IDLE_GAMES} games in a row with no level run: nothing to play', cause='idle')
    if (fetch := fetch_gheeds(world, loop)) is not None:
        return fetch
    if loop.abandon:
        # Left where it stands, in act 3 too: a recovery's way out is the quickest (no portal under what stopped it)
        return Objective(LEAVE_GAME, GIVEN_UP, STACK)
    if loop.agenda.holds(SWAP_GOALS):
        # The swap's package needs no zone read: the player's Gheed's Fortune is never left on its way
        top = loop.agenda.package()
        assert top is not None
        return top
    if (shard := actloop.shard_goal(world, loop)) is not None:
        return shard  # the act kind's Worldstone Shard first in a game (macros/actloop.py)
    plan = zone_of(tz, agenda.acts, agenda.bosses)
    if plan is None and not player.in_town and (left := tz.sighted(None)) is not None:
        # The zone turned under the game with a valuable still on the ground: it is picked up first, then the game's
        # end. A Set Occult Codex by Andariel, room just made in the cube, stopped the loop at the 08:30 turn
        # (08:30:01 on 2026-10-20)
        agenda.refresh(())
        return agenda.next((player.x, player.y), valuable=left, area=player.area)
    if plan is None:
        raise Abort('no terror zone is read in this game')
    if not plan.excursions and player.in_town:
        # Every way into the zone blocked (Moo Moo Farm: only the red portal the player opens with Wirt's Leg leads in;
        # Blood Moor, Rocky Waste and Outer Steppes until their towns' walks out, rca/2026-10-19/town-exit-findings.md):
        # no goals, so each game was left at once, a game a minute for the hour (F1). The player, 2026-10-19: "we need
        # to make sure that we don't stuck or die". Stopped in town only: in a field level (the zone changed under the
        # game) no goals end the game first, the ground's valuables picked up
        loop.idle = 0
        reasons = '; '.join(sorted({why for _, why in plan.skipped})) or 'none'
        wait = zone_wait(time.time())
        loop.cooling = max(loop.cooling, time.monotonic() + wait)
        raise Abort(
            f'the terror zone {plan.zone} is not playable: no excursion ({reasons}); the next zone in {wait:.0f} s',
            cause='zone',
        )
    agenda.plan = plan
    bosses_planned(agenda, progress, plan)
    if zonenav.on(plan):
        return zone_choose(world, progress, loop, tz, plan)  # macros/zonenav.py: the zone as a graph
    game, area = world.game_name, player.area
    tour_back(agenda, plan, progress, area)
    reopen(agenda, plan)
    trip = plan.excursion_of(area, agenda.finished)
    if trip is not None and area in trip.tours and area in agenda.finished:
        LOG.info('Macro: tz: tour: %s entered again: no level twice in a game, the game ends here',
                 numbered_name(area))  # fmt: skip
    if trip is not None and progress is not None:
        select(progress, game, area, trip, plan)
    step = progress.step(area) if progress is not None else None
    view = GameView(
        area,
        player.in_town,
        plan,
        stage=step.stage.kind if step is not None else None,
        stage_to=step.stage.to if step is not None else 0,
        worked=tuple((level, runs - agenda.reopened.get(level, 0)) for level, runs in agenda.worked.items()),
        finished=frozenset(agenda.finished),
        sighted=tz.sighted(area),
        visit_due=loop.visit_due(game),
    )
    agenda.refresh(produce(view))
    zone_note(progress, loop, plan)
    # No goals left in act 3: the way to the Fortress, its game ended there (agenda.py `game_end`): Durance 3's Red
    # portal with Mephisto dead, tried once (a level done is not gone through it again: the Town Portal home instead)
    dead = progress.dead() if progress is not None and progress.dead is not None else frozenset()
    dead = dead if area not in agenda.finished else frozenset()
    return agenda.next((player.x, player.y), valuable=tz.sighted(None), area=area, dead=dead)


def zone_judged(
    progress: Progress | None, loop: Loop, plan: Itinerary, area: int | None = None
) -> tuple[ZoneGraph, zonenav.Judged]:
    """The zone's graph (macros/zonenav.py `graph_of`, said once a game) and its levels judged from what this game
    knows: entered (kept by the agenda: the progress's is cut to go into a child again), the map read and the tour
    done (runner.py `_zone_seen`), the runs, the route's own stages left, the levels blocked, those cleared before a
    service restart (`Agenda.kept`). In a tour's hub (`area`), a toured level entered and left unfinished is blocked:
    the mark it was entered by was gone through, and which mark leads back into it is not known."""
    agenda = loop.agenda
    graph = zonenav.graph_of(plan)
    if area is not None:
        ordered = zonenav.play_order(graph, plan, area, {boss.area for boss in bosses_alive(agenda)})
        said_order = f'{plan.zone}: {list(ordered.roots)}'
        if ordered is not graph and agenda.zone_said.get(0) != said_order:
            agenda.zone_said[0] = said_order
            if ordered.roots[0] != graph.roots[0]:
                LOG.info("Macro: zone: the rotation first: %s before the act's roots, from %s",
                         list(ordered.roots[:1]), display_name(area))  # fmt: skip
            else:
                # zonenav.py ROTATION_BOSSES_FIRST (2026-10-22)
                LOG.info("Macro: zone: the rotation's roots holding a boss alive after the act's boss: %s, from %s",
                         list(ordered.roots), display_name(area))  # fmt: skip
        graph = ordered
    if agenda.zone_graph != plan.zone:
        agenda.zone_graph = plan.zone
        LOG.info('Macro: zone: graph %s: %s; ways not confirmed: %s', plan.zone, graph.said(),
                 ', '.join(graph.unconfirmed()) or 'none')  # fmt: skip
    facts = progress.facts if progress is not None else Facts()
    agenda.entered |= {level for level in facts.entered if level in graph.nodes}
    hub = graph.node(area)
    for child in hub.children if hub is not None else ():
        node = graph.nodes[child]
        left = child not in agenda.explored and agenda.worked[child] < zonenav.runs_allowed(node)
        if node.toured and child in agenda.entered and child not in agenda.blocked and left:
            agenda.blocked[child] = "entered and left unfinished: which of its tour's marks leads back is not known"
    dead = progress.dead() if progress is not None and progress.dead is not None else None

    sides = zonenav.sides_of(graph)

    def own(level: int) -> bool:
        found = zone_script(progress, plan, level) if progress is not None else None
        return zonenav.own_work(found[1] if found is not None else None, facts, dead, sides)

    # The bosses of the ledger alive on each level of the game's scope (zonenav.py BOSSES_HOLD), and the levels of a
    # zone kept for its bosses (BOSS_ZONES): those holding none blocked, the others worked on the way
    alive = bosses_alive(agenda)
    turned = turned_levels(plan, progress.wanted if progress is not None else None)

    def held(level: int) -> bool:
        reach = zonenav.boss_reach(graph, level)
        return any(boss.area in reach for boss in alive)

    def blocked(level: int) -> str:
        return agenda.blocked.get(level, '') or (TURNED if level in turned and not held(level) else '')

    states = {
        level: zonenav.LevelState(
            entered=level in agenda.entered,
            mapped=level in agenda.mapped,
            explored=level in agenda.explored,
            runs=agenda.worked[level],
            work=own(level),
            blocked=blocked(level),
            kept=level in agenda.kept,
            bosses=sum(1 for boss in alive if boss.area == level),
        )
        for level in graph.nodes
    }

    def how(level: int, finished: frozenset[int]) -> str:
        if level in turned:
            return ON_THE_WAY  # no longer terrorized: its bosses only (hunting/choice.py BOSS_ROTATION)
        return policy_of(level, plan.trip_of(level, finished), full_clear(loop))

    return graph, zonenav.judge(graph, states, how)


def zone_script(progress: Progress, plan: Itinerary, level: int) -> tuple[str, Script] | None:
    """Level `level`'s catalogue (route, script) under zone navigation: the stages of every trip's route naming it, in
    the trips' order (the itinerary plays each trip's script on it), else its main script; zonenav.py takes the own
    work from it. Nihlathak's Temple's (121) main script is the Nihlathak route's way down from Anya's red portal (the
    stairs to the Halls of Anguish), the Halls of Anguish trip's has Pindleskin's fight; the Burial Grounds' (17) first
    trip is the Crypt's (its stairs), the Mausoleum's has Blood Raven's (the act harness, 2026-10-21)."""
    found: list[tuple[str, Script]] = []
    for trip in plan.excursions:
        if level not in trip.areas or any(name == trip.route for name, _ in found):
            continue
        found += [(name, script) for name, script, _ in progress.ways.get(level, ()) if name == trip.route][:1]
    if not found:
        return progress.scripts.get(level)
    stages = tuple(dict.fromkeys(stage for _, script in found for stage in script.stages))
    return found[0][0], Script(level, stages)


def zone_note(progress: Progress | None, loop: Loop, plan: Itinerary) -> None:
    """Stage 0 (macros/zone-nav-plan.md §7), the itinerary's legs playing: each level the agenda calls done said once
    with how zone navigation judges it (`Macro: zone: done by the old rule: ...`)."""
    graph, judged = zone_judged(progress, loop, plan)
    agenda = loop.agenda
    for level in sorted(agenda.finished & set(graph.nodes)):
        text = zonenav.said(graph, judged, level)
        if agenda.zone_said.get(level) != text:
            agenda.zone_said[level] = text
            LOG.info('Macro: zone: done by the old rule: %s', text)


def zone_choose(world: World, progress: Progress | None, loop: Loop, tz: LegHands, plan: Itinerary) -> Objective:
    """`choose` for a zone navigation plays (macros/zonenav.py `on`): the levels judged, the agenda's `finished` the
    zone's (cleared or blocked), each level's script for this game set (its own work, the next child's way in, its way
    back up), a child to go into again entered afresh, then the zone's goals; the town visit due at a level's boundary
    is the room package (Town Portal, the visit, back through the portal)."""
    agenda, player = loop.agenda, world.player
    assert player is not None
    area = player.area
    if zonenav.RESUME and not agenda.zone_resumed:
        agenda.zone_resumed = True
        zone_resume(loop, plan, world.game_name)
    if agenda.zone_at != area:
        agenda.zone_at, agenda.arrival_runs = area, agenda.worked[area]
    graph, judged = zone_judged(progress, loop, plan, area)
    if zonenav.TIME_BUDGET and progress is not None and zone_budget(loop, plan, progress, world, graph):
        graph, judged = zone_judged(progress, loop, plan, area)  # judged again with the children skipped blocked
    agenda.finished = set(judged.finished)
    if zonenav.RESUME:
        zone_keep(loop, plan, world.game_name, judged)
    for level in sorted(agenda.entered):
        if level not in graph.nodes or not (level in judged.explored or level in judged.finished):
            continue
        text = zonenav.said(graph, judged, level)
        if agenda.zone_said.get(level) != text:
            agenda.zone_said[level] = text
            LOG.info('Macro: zone: %s', text)
    step = None
    if progress is not None:
        found = progress

        def base(level: int) -> tuple[str, Script] | None:
            return zone_script(found, plan, level)

        progress.selected.update(zonenav.scripts(graph, judged, base, agenda.no_back, agenda.no_walk))
        child = zonenav.next_child(graph, area, judged) if graph.node(area) is not None else None
        if child is not None and child in progress.facts.entered:
            # Its way in done by the facts (entered before, left unfinished): made again
            progress.facts = replace(progress.facts, entered=progress.facts.entered - {child})
        step = progress.step(area)
    view = zonenav.ZoneView(
        area,
        player.in_town,
        graph,
        judged,
        stage=step.stage.kind if step is not None else None,
        stage_to=step.stage.to if step is not None else 0,
        sighted=tz.sighted(area),
        visit_due=loop.visit_due(world.game_name),
        no_back=frozenset(agenda.no_back),
        no_walk=frozenset(agenda.no_walk),
        passed=agenda.worked[area] > agenda.arrival_runs,
    )
    goals = zonenav.produce(view)
    if any(goal.exit == zonenav.VISIT for goal in goals):
        LOG.info('Macro: zone: the town visit is due: Town Portal from %s and back through it', display_name(area))
        agenda.push(*room_package(area))
        top = agenda.package()
        assert top is not None
        return top
    agenda.refresh(goals)
    dead = progress.dead() if progress is not None and progress.dead is not None else frozenset()
    dead = dead if area not in agenda.finished else frozenset()
    return agenda.next((player.x, player.y), valuable=tz.sighted(None), area=area, dead=dead)


def time_left(loop: Loop, game: str) -> float | None:
    """Seconds left of game `game` before the loop's game cap (loop.py `Loop.allowed_seconds`: the kind's
    game_seconds, the overflow acts' and TRIP_SECONDS a trip for room); None while the game's start is not known."""
    if loop.seen is None or loop.seen[0] != game:
        return None
    return loop.allowed_seconds(game) - (time.monotonic() - loop.seen[1])


def zone_budget(loop: Loop, plan: Itinerary, progress: Progress, world: World, graph: ZoneGraph) -> tuple[int, ...]:
    """The time budget (zonenav.py TIME_BUDGET): the children skipped for the game's time left (`over_budget`),
    blocked and said; the level the character is on, those above it, the bosses and the route fights are kept."""
    player = world.player
    remaining = time_left(loop, world.game_name)
    if player is None or remaining is None:
        return ()
    _, judged = zone_judged(progress, loop, plan, player.area)
    fights = [
        level
        for level in graph.nodes
        if (found := zone_script(progress, plan, level)) is not None
        and any(stage.kind == FIGHT for stage in found[1].stages)
    ]
    skipped = zonenav.over_budget(graph, judged, remaining, (player.area,), fights)
    wanted = zonenav.left_seconds(graph, judged)
    for level in skipped:
        why = f'no time left for it ({remaining:.0f} s left of the game, the zone wanted {wanted:.0f} s)'
        loop.agenda.blocked[level] = why
        # The watch tools read it (d2-loop-watch logwords.py ZONE_BLOCKED, EVENT, NOW)
        LOG.info('Macro: zone: %s (%d) blocked: %s', display_name(level), level, why)
    return skipped


def zone_store(loop: Loop) -> Path | None:
    """The file the zone's facts are kept in (ZONE_FILE beside the loop's store), None with no store (tests)."""
    return loop.store.parent / ZONE_FILE if loop.store is not None else None


def zone_key(loop: Loop, game: str) -> str | None:
    """The kept facts' key: the game's name and the character's unit id (loop.py `GameId`); None unread."""
    seen = loop.game_id
    if not isinstance(seen, GameId) or seen.name != game:
        return None
    return f'{seen.name}#{seen.player}'


def zone_keep(loop: Loop, plan: Itinerary, game: str, judged: zonenav.Judged) -> None:
    """The zone's facts this game written to ZONE_FILE when they changed (zonenav.py RESUME)."""
    path, key = zone_store(loop), zone_key(loop, game)
    if path is None or key is None:
        return
    agenda = loop.agenda
    facts = {
        'zone': plan.zone,
        'entered': sorted(agenda.entered),
        'mapped': sorted(agenda.mapped),
        'explored': sorted(agenda.explored),
        'runs': {str(level): runs for level, runs in sorted(agenda.worked.items())},
        'cleared': sorted(judged.cleared | agenda.kept),
        'blocked': {str(level): why for level, why in sorted(agenda.blocked.items())},
        'no_back': sorted(agenda.no_back),
    }
    text = json.dumps(facts, sort_keys=True)
    if text == agenda.zone_written:
        return
    agenda.zone_written = text
    try:
        kept = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        games = [entry for entry in kept.get('games', []) if entry.get('key') != key]
        games = [*games, {'key': key, 'at': time.time(), 'facts': facts}][-ZONE_GAMES:]
        path.write_text(json.dumps({'games': games}, separators=(',', ':')), encoding='utf-8')
    except (OSError, ValueError, AttributeError, TypeError) as error:
        LOG.info('Macro: zone: the facts are not kept in %s: %s', path, error)


def zone_resume(loop: Loop, plan: Itinerary, game: str) -> None:
    """The zone's facts kept for this game (`zone_keep`) taken back once a game: a service restart mid-game goes
    on where it was, the levels cleared before it not played again (zonenav.py RESUME)."""
    path, key = zone_store(loop), zone_key(loop, game)
    if path is None or key is None or not path.exists():
        return
    try:
        kept = json.loads(path.read_text(encoding='utf-8'))
        entry = next((each for each in reversed(kept.get('games', [])) if each.get('key') == key), None)
        if entry is None or time.time() - float(entry['at']) > zonenav.RESUME_SECONDS:
            return
        facts = entry['facts']
        if facts['zone'] != plan.zone:
            return
        agenda = loop.agenda
        agenda.entered |= {int(level) for level in facts['entered']}
        agenda.mapped |= {int(level) for level in facts['mapped']}
        agenda.explored |= {int(level) for level in facts['explored']}
        for level, runs in facts['runs'].items():
            agenda.worked[int(level)] = max(agenda.worked[int(level)], int(runs))
        agenda.kept |= {int(level) for level in facts['cleared']}
        for level, why in facts['blocked'].items():
            agenda.blocked.setdefault(int(level), str(why))
        agenda.no_back |= {int(level) for level in facts['no_back']}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        LOG.info('Macro: zone: the kept facts in %s are not read: %s', path, error)
        return
    # The watch tools read it (d2-loop-watch logwords.py NOW)
    LOG.info('Macro: zone: %s resumed after a restart: %d levels entered, %d cleared, %d not to be done', plan.zone,
             len(facts['entered']), len(facts['cleared']), len(facts['blocked']))  # fmt: skip


def tour_back(agenda: Agenda, plan: Itinerary, progress: Progress | None, area: int) -> None:
    """In a tour's hub (the Canyon of the Magi): each toured level entered in this game (routes/progress.py `Facts`)
    is done, as it was left, whatever way (its way back, or a trip to town and the waypoint to the hub). The tour then
    goes on with the levels not entered, never one done again (the player, 2026-10-20 ~14:03: "use sub-agent, we need
    to utilize smaller tombs too"). A level is done here, not as its way back is taken: a way back tried and failed
    leaves it to do."""
    if progress is None:
        return
    for trip in plan.excursions:
        if trip.hub != area or not trip.tours:
            continue
        for level in trip.tours:
            if level in progress.facts.entered and level not in agenda.finished:
                agenda.finish(level)
                done = sum(1 for each in trip.tours if each in agenda.finished)
                LOG.info('Macro: tz: tour: %s done, back in %s: %d of %d done', numbered_name(level),
                         display_name(area), done, len(trip.tours))  # fmt: skip


def reopen(agenda: Agenda, plan: Itinerary) -> None:
    """Each level the boss's trip only crossed (tzroutine.py `Excursion.passes`: the River of Flame on Diablo's from
    its waypoint), that trip over: its own trip's from now, the runs it had not counted against it (`produce`'s
    RUNS_AN_AREA). The player, 2026-10-20 ~21:27: "kill diablo -> do rest of flame river -> city of damned"."""
    for level in sorted(plan.crossed(agenda.finished)):
        if level not in agenda.reopened:
            agenda.reopened[level] = agenda.worked[level]
            LOG.info('Macro: tz: %s was crossed to the boss: its own run now (%d run(s) on the way)',
                     display_name(level), agenda.worked[level])  # fmt: skip


def fetch_gheeds(world: World, loop: Loop) -> Objective | None:
    """The player's Gheed's Fortune parked on a shared page with no choice ahead (a new game, a restart, a recovery):
    the way to it. Given up (`abandon`): one goal by where the character is, each tried REPEAT times, then the game
    is left and the next game's town fetches it (as loop.py `gheeds_leg`); else the fetch package pushed."""
    player = world.player
    if loop.parked is None or player is None:
        return None
    area = player.area
    if loop.abandon:
        if area == PANDEMONIUM_FORTRESS:
            goal = Objective(SWAP_CHOOSE, "the better Gheed's Fortune", STACK)
        elif player.in_town:
            goal = Objective(WAYPOINT, 'to the Fortress for the choice', STACK, to=PANDEMONIUM_FORTRESS)
        else:
            goal = Objective(SWAP_HOME, "Gheed's Fortunes to compare", STACK, area, to=town_of(area))
        return goal if loop.agenda.failures[goal.key] < REPEAT else None
    if loop.agenda.holds(frozenset((SWAP_CHOOSE,))):
        return None
    LOG.info("Macro: charms: the player's Gheed's Fortune is on shared page %d: fetched first", loop.parked.page)
    loop.agenda.push(*gheeds_fetch(area))
    return loop.agenda.package()


def gheeds_swap(loop: Loop, game: str, area: int) -> None:
    """The Gheed's swap from `area` (runner.py `_gheeds_swap`): its package pushed on the agenda. The player,
    2026-10-19: a Herald's Gheed's in Spider Forest fell to the room rules and the loop stopped by it."""
    loop.agenda.begin(loop.game_id or game)
    loop.agenda.push(*gheeds_package(area))


def pick_new(loop: Loop, run: Run, tz: LegHands, agenda: Agenda) -> None:
    """SWAP_PICK, back by the refused charm with the player's parked: the pickup until the new one is carried, it is
    refused again or nothing is left (PICK_TRIES). With nothing parked the swap ends: its package dropped."""
    parked = loop.parked
    if parked is None:
        LOG.info("Macro: charms: no Gheed's Fortune of the player's on a shared page: the swap ends here")
        agenda.cut()
        return
    if loop.gheed != PICK:
        return  # already refused again: to town for theirs
    for _ in range(PICK_TRIES):
        now = run.reads.carried()
        if now is not None and candidates(now, parked, loop.swap_units):
            return
        try:
            if not tz.take_one():
                return
        except Refused as refused:
            loop.gheed = CHOOSE
            LOG.info("Macro: charms: %s; %s is still not taken with the player's Gheed's Fortune on shared page %s: "
                     'to town for theirs', refused, refused.drop.label, parked.page)  # fmt: skip
            return


def select(progress: Progress, game: str, area: int, trip: Excursion, plan: Itinerary) -> None:
    """Level `area` takes the excursion's script (a level two routes share, Burial Grounds: Crypt, then Mausoleum;
    taken before the service notes the level too, tz-coverage-findings.md F7), held to the trip (tzroutine.py
    `kept_to`: "it should run within terror zones", the player, 2026-10-19 ~21:56), said once. A level off every
    excursion its script names gets none for the game: a run that reached it all the same (an open passage,
    pursuit.py `carried`) has no route there, no seal, no boss, and ends."""
    before = progress.selected.get(area)
    if not progress.select_route(game, area, trip.route):
        mine = [(name, script) for name, script, _ in progress.ways.get(area, ()) if name == trip.route]
        if len(mine) == 1:
            progress.selected[area] = mine[0]
    chosen = progress.chosen(area)
    if chosen is None:
        return
    route, script = chosen
    on_trips = {level for each in plan.excursions for level in each.areas}
    for stage in script.stages:
        if stage.to and stage.to not in on_trips and stage.to not in TOWNS:
            progress.selected[stage.to] = (route, Script(stage.to, ()))
    kept = kept_to(script, trip)
    reenter(progress, area, trip, kept)
    if kept is script:
        return
    progress.selected[area] = (route, kept)  # this game's only (`Progress.note` clears it)
    if before != (route, kept):
        cut = [stage.text() for stage in script.stages if stage not in kept.stages]
        LOG.info('Macro: tz: %s: %s not taken: off the terror zone (the trip goes on by %s)', display_name(area),
                 ', '.join(cut), ', '.join(stage.text() for stage in kept.stages) or "the level's run")  # fmt: skip


def reenter(progress: Progress, area: int, trip: Excursion, script: Script) -> None:
    """The trip's way on from `area` into a level already entered in this game made its way on again: the Mausoleum's
    trip from the Cold Plains after the Crypt's found its stage `enter Burial Grounds` done (routes/progress.py `done`:
    entered in this game), so no way on, no card mark, and "TZ next level again and again" ended the game there (act
    1's walk, and Act 4 with the Burial Grounds in rotation, 2026-10-20). The level is noted again as it is entered. A
    tour keeps its levels entered (`tour_back` reads them)."""
    onward = trip.after(area)
    if trip.tours or onward is None or onward not in progress.facts.entered:
        return
    if any(stage.to == onward for stage in script.stages):
        progress.facts = replace(progress.facts, entered=progress.facts.entered - {onward})


# The danger package's Town Portal (running/recovery.py BOSS_RECOVERY): out of a danger to recover in town and come back
# for a boss alive; never a fight posted for it (`portal_fight`: "never fight through the danger that caused the
# recovery", the coordinator's ruling of 2026-10-22)
DANGER_PORTAL = 'Town Portal clear of the danger'
# The danger package's return (the coordinator, 2026-10-22, from rca/2026-10-22/boss-ledger-findings.md's open item):
# after the town visit, back through the portal only when the safety's gate allows (running/recovery.py
# `back_for_bosses`, macros/safety.py RETURN_GATE: life and potions restocked, no veto at the last danger pricing),
# else the loop stops in town naming the bosses; through it, Battle Orders before any fight when due or its age is not
# known (running/legs.py `orders_on_arrival`, macros/cta.py ARRIVAL_LEFT). False: back whatever, as before
DANGER_RETURN = True


def danger_trip(loop: Loop, game: str, area: int) -> None:
    """The room package from `area` with its Town Portal cast whatever stands near (DANGER_PORTAL): clear of a danger,
    the town visit (its healer, potions, repair), back through the portal for the bosses alive."""
    loop.begin_trip(game)
    loop.agenda.begin(loop.game_id or game)
    goals = room_package(area)
    loop.agenda.push(replace(goals[0], label=DANGER_PORTAL), *goals[1:])
    loop.danger_return = game  # its portal return asks the safety's gate (`perform`, macros/safety.py RETURN_GATE)


def trip(loop: Loop, game: str, area: int) -> None:
    """A trip to town for room from `area` (runner.py `_loop_stopped`): the room package pushed on the agenda, with
    the loop's trip bookkeeping. The shared no-room routine's trip for the terror zone kinds and Lower Kurast
    (`packaged`), and, in one run, for every activity by hand (`errand`)."""
    loop.begin_trip(game)
    loop.agenda.begin(loop.game_id or game)  # a kind with no agenda of its own has none begun for this game
    loop.agenda.push(*room_package(area))


def packaged(world: World, loop: Loop) -> Objective | None:
    """A kind with legs of its own (Lower Kurast): the room package's next goal while one is pushed (`trip`), before
    those legs; None out of a game, dead, leaving or with none (the kind's legs decide). The player, 2026-10-19:
    "EVERY loop and activity should have the same routines for situations when we don't have space"."""
    player = world.player
    if not world.in_game or player is None or player.mode in DEAD or loop.abandon:
        return None
    loop.agenda.begin(loop.game_id or world.game_name)  # a new game drops a package left over
    return loop.agenda.package()


def errand(loop: Loop, run: Run, key_names, progress: Progress | None, hands: LegHands, game: str, area: int) -> None:
    """The room package from `area` made goal by goal in one run (runner.py `_room_errand`: an activity by hand),
    on an agenda of its own: the loop's game agenda is not touched. `Abort` from a goal ends it there."""
    agenda = Agenda()
    agenda.begin(game)
    loop.begin_trip(game)
    agenda.push(*room_package(area))
    while (goal := agenda.package()) is not None:
        run.say(f'Room trip: {goal.label}')
        perform(loop, run, key_names, progress, goal, hands, agenda)


def perform(
    loop: Loop,
    run: Run,
    key_names,
    progress: Progress | None,
    goal: Objective,
    tz: LegHands | None,
    agenda: Agenda | None = None,
    *,
    item_stats: Stats | None = None,
    shown: Remembered | None = None,
) -> None:
    """Make `goal` one leg; done on the agenda (the loop's, or `agenda`) unless it aborts (`Agenda.failed`).
    `item_stats`, `shown`: the Gheed's swap's (loop.py `Loop.leg`)."""
    agenda = agenda if agenda is not None else loop.agenda
    packaged = bool(agenda.stack) and agenda.stack[-1] == goal
    try:
        world = run.world()
        game = world.game_name if world.in_game else ''
        player = world.player
        if goal.ends and game and (alive := boss_alive(agenda)) is not None:
            # The way to the act's last town ends the game (agenda.py `game_end`): not with a boss alive (BOSS_STAYS)
            LOG.info('Macro: zone: %s, but %s alive: the loop stops for the player, the game is not left', goal.label,
                     alive)  # fmt: skip
            raise Abort(f'{goal.label}, but {alive} alive: the loop stops here for the player', cause='idle')
        if goal.ends and game:
            loop.done = game  # the game's end under way, as Lower Kurast's Town Portal leg (loop.py `PORTAL`)
        if goal.kind == NEW_GAME:
            loop.next_game(run, world, key_names)
        elif goal.kind == LEAVE_GAME:
            # Never a game left with a valuable on the ground (the player, 2026-10-17): a boss's drops landed, the
            # ground read again and picked up, then the guard (loop.py `last_look`; game 30, 21:55:06)
            left = loop.last_look(run, tz) if tz is not None else None
            if left is not None:
                raise Abort(f'no goals left, but {left} lies on the ground', cause='room')
            alive = boss_alive(agenda) if goal.label != GIVEN_UP else None
            if alive is not None:
                # The player, 2026-10-22: "we need to kill all bosses, no exceptions" (BOSS_STAYS)
                LOG.info('Macro: zone: %s, but %s alive: the loop stops for the player, the game is not left',
                         goal.label, alive)  # fmt: skip
                raise Abort(f'{goal.label}, but {alive} alive: the loop stops here for the player', cause='idle')
            agenda.finish(player.area if player is not None else None)
            loop.leave(run, game)
        elif tz is None or player is None:
            raise Abort('no terror zone hands, or no character read')
        elif goal.kind == SWAP_AWAY:
            try:
                loop.swap_out(run, world, key_names, item_stats)
            except Abort:
                agenda.cut()  # no Gheed's Fortune of the player's read: no swap (the room rules after it)
                raise
        elif goal.kind == SWAP_PARK:
            loop.stash_gheeds(run, item_stats, shown)
        elif goal.kind == SWAP_PICK:
            pick_new(loop, run, tz, agenda)
        elif goal.kind in (SWAP_HOME, SWAP_CHOOSE) and loop.parked is None:
            LOG.info("Macro: charms: no Gheed's Fortune of the player's on a shared page: the swap ends here")
            agenda.cut()
        elif goal.kind == SWAP_HOME:
            loop.swap_back(run, world, key_names)
        elif goal.kind == SWAP_CHOOSE:
            loop.choose_gheeds(run, tz, item_stats, shown)
            loop.gheed = None
            if any(each.kind == THROUGH_PORTAL for each in agenda.stack):
                LOG.info('Macro: charms: back through the portal for the rest of the level')
        elif goal.kind == WAYPOINT:
            if goal.to is None:
                raise Abort(f'{goal.label}: no level to go to')
            excursion = goal.tier == EXCURSION  # to a zone's waypoint (else town to town)
            if player.in_town and loop.done != game:
                # A shard picked up over the limit used at this town stop (actloop.py PICK_OVER_LIMIT): carried only
                actloop.overflow(loop, run, tz.terrorized, tz.inventory_key(), carried_only=True)
            if excursion:
                own = run.reads.own_teleport()
                if not own:
                    loop.teleports = teleports(gold(run), gold_cap(run), loop.teleports)
                tz.navigate()
                if player.area != ROGUE_ENCAMPMENT:
                    loop.prebuff_once(run, game)
            travel(run, goal.to, loop.marks)
            if excursion:
                loop.prebuff_once(run, game)  # out of the Rogue Encampment: Consume cannot take its townsfolk
        elif goal.kind == WALK_OUT:
            # A trip that starts in this town, walked out of (macros/townexit.py; tzroutine.py `produce`)
            if goal.to is None or tz.walk_out is None:
                raise Abort(f'{goal.label}: no walk out of town')
            if not run.reads.own_teleport():
                loop.teleports = teleports(gold(run), gold_cap(run), loop.teleports)
            tz.navigate()
            if player.area != ROGUE_ENCAMPMENT:
                loop.prebuff_once(run, game)  # in town, before the field (Lut Gholein, the Fortress)
            tz.walk_out(goal.to)
            # The Rogue Encampment's prebuff fails on its start NPCs (loop.py `next_game`): at the field's edge, as a
            # waypoint excursion's arrival (the coordinator, 2026-10-19)
            loop.prebuff_once(run, game)
        elif goal.kind == TERRORIZE:
            actloop.use_shard(loop, run, tz.terrorized, tz.inventory_key())  # once a game: the outcome on the agenda
        elif goal.kind == TOWN_ROUTINE:
            # A shard over the limit (actloop.py OVERFLOW) used before the visit, once the game's own shard step is
            # made (the visit would put a carried one down, its stack full); never at the game's end
            if loop.done != game:
                actloop.overflow(loop, run, tz.terrorized, tz.inventory_key())
            exit = Exit(goal.exit or 'waypoint')
            if exit == Exit.WAYPOINT and loop.done == game:
                exit = Exit.LEAVE  # the game ends here: no walk to the waypoint (loop.py `exit_of`)
            loop.town(run, tz.visit, game, exit)
        elif goal.kind == merc.MERC_ROUTINE:
            merc.town_routine(run)  # the belt refilled, the merc revived with the carried gold (macros/merc.py)
        elif goal.kind == PORTAL_TO_TOWN:
            if portal_fight(run, tz, game, goal):
                return  # the goal kept: the fight's run is posted, the portal comes after it
            if goal.ends and (left := loop.last_look(run, tz)) is not None:
                raise Abort(f'the game ends, but {left} lies on the ground', cause='room')  # as LEAVE_GAME's
            if not packaged:
                loop.settle(run)  # the portal's pickup (`to_town`) after a boss's drops landed
            if not packaged and not zonenav.on(agenda.plan):
                agenda.finish(player.area)  # the excursion's end (zone navigation: judged, not set by leaving)
            to_town(run, key_names, None if packaged else tz.take_one)  # a trip for room has no room to pick up
            loop.note_portal(run)
        elif goal.kind == THROUGH_PORTAL:
            danger = DANGER_RETURN and loop.danger_return == game and tz is not None
            if danger:
                assert tz is not None
                refused = tz.back_for_bosses()  # after the town visit: life and potions restocked, no veto
                if refused is not None:
                    loop.danger_return = None
                    raise Abort(refused, cause='idle')  # the loop stops in town (stops.py: 'idle')
            loop.back_through_portal(run, game)
            if danger:
                assert tz is not None
                loop.danger_return = None
                # Battle Orders before any fight (no skill is cast in town); beset first, the danger pricing's
                LOG.info('Macro: zone: back from the danger: Battle Orders on the arrival: %s', tz.orders_on_arrival())
        elif goal.kind == LEVEL:
            loop.idle = 0
            if goal.to is not None:
                # The route's own way to a town (Durance 3's Red portal): the excursion ends by it, done before the run
                # so a run that does not take it is followed by the Town Portal home (tzroutine.py `produce`,
                # agenda.py `game_end`). Never with a valuable on the ground, as the Town Portal's
                if (left := tz.sighted(None)) is not None:
                    raise Abort(f'{goal.label}, but {left} lies on the ground', cause='room')
                agenda.finish(player.area)
            tz.navigate()
            tz.level_run()  # posts the run and returns
        elif goal.kind == LOOT:
            if not tz.take_one() and progress is not None:
                landing = DROPS_AFTER_KILL - (
                    time.monotonic() - KILLED_AT.get(boss_of(progress, player.area), -math.inf)
                )
                if landing > 0:
                    LOG.info("Macro: tz: the boss's drops may still be landing: %.1fs more", landing)
                    run.pace.sleep(landing)
                else:
                    progress.looted(player.area)
        elif goal.kind == PICKUP:
            if not tz.take_one():
                raise Abort(f'{goal.label}: no pickup and no trip back took it')
        elif goal.kind == NEXT_LEVEL:
            loop.settle(run)  # the way on's pickup (runner.py `_way_on`) after a boss's drops landed
            plan = agenda.plan
            zone = zonenav.on(plan)
            if not zone and not (
                isinstance(plan, Itinerary)
                and (plan.touring(player.area, agenda.finished) or plan.crossing(player.area, agenda.finished))
            ):
                # (a tour's levels are done in its hub, `tour_back`; a level crossed to the boss by its own trip after)
                agenda.finish(player.area)
            if tz.way_on is None:
                raise Abort(f'{goal.label}: no way on')
            walk = zone and goal.exit == zonenav.WALK and goal.to is not None
            tried = 0
            if zone and goal.to is not None:
                tried = way_tried(agenda, player.area, goal.to)
                if walk and tried >= zonenav.WALK_TRIES:
                    agenda.no_walk.add((player.area, goal.to))  # this try is the last
                elif not walk and way_spent(agenda, player.area, goal.to, tried):
                    agenda.done(goal)
                    return
            try:
                tz.way_on()
            except Abort as stop:
                if walk and goal.to is not None and type(stop) is Abort:
                    # A walk across into the next root's levels that failed: the Town Portal and the waypoint
                    agenda.no_walk.add((player.area, goal.to))
                    LOG.info('Macro: zone: %s: no walk from %s into %s: the Town Portal instead', stop,
                             display_name(player.area), display_name(goal.to))  # fmt: skip
                else:
                    skipped = (
                        (
                            zone_door(agenda, player.area, goal, stop, tried)
                            or zone_use(agenda, player.area, goal, stop, tried, tz.level_run)
                        )
                        if zone
                        else False
                    )
                    if not skipped and not skip_door(agenda, plan, player.area, goal, stop):
                        raise
        elif goal.kind == zonenav.UP_LEVEL:
            loop.settle(run)  # a boss's drops landed before the level is left
            if tz.way_on is None:
                raise Abort(f'{goal.label}: no way on')
            if goal.to is not None:
                tried = way_tried(agenda, player.area, goal.to)
                if tried > zonenav.WAY_TRIES:
                    agenda.no_back.add(player.area)
                    LOG.info('Macro: zone: the way up from %s to %s made %d times with no arrival: the Town Portal '
                             'instead', display_name(player.area), display_name(goal.to), tried - 1)  # fmt: skip
                    agenda.done(goal)
                    return
            try:
                tz.way_on()  # the level's script ends in its way back (zonenav.py `scripts`)
            except Abort as stop:
                if not SKIP_DOOR or stop.cause != 'door':
                    raise
                agenda.no_back.add(player.area)
                LOG.info('Macro: zone: %s: no way back up from %s: the Town Portal instead', stop,
                         display_name(player.area))  # fmt: skip
        else:
            raise Abort(f'the agenda has no leg for {goal.kind}')
    except Hand:
        # The player's own input is no failure of the leg: three mouse moves in a second dropped the town visit and
        # made a Save and Exit under the player's hand (09:54:25-09:54:28 on 2026-10-20)
        raise
    except Abort:
        agenda.failed(goal)
        raise
    agenda.done(goal)


def skip_door(agenda: Agenda, plan: object, area: int, goal: Objective, stop: Abort) -> bool:
    """Whether the way on's stop `stop` from `area` is a door no click takes (`SKIP_DOOR`) on the trip it leads on
    (`goal.to` its next level, no tour): that trip is over (`Excursion.over`), said, and the zone goes on."""
    if not SKIP_DOOR or stop.cause != 'door' or not isinstance(plan, Itinerary) or goal.to is None:
        return False
    trip = plan.excursion_of(area, agenda.finished)
    if trip is None or trip.touring(area) or trip.after(area) != goal.to:
        return False
    agenda.finish(trip.terminal)
    # The watch tools read it (d2-loop-watch logwords.py EVENT, NOW)
    LOG.info('Macro: loop: %s: the trip to %s is skipped, the game is not left and the zone goes on',
             stop, display_name(goal.to))  # fmt: skip
    return True


def way_tried(agenda: Agenda, area: int, to: int) -> int:
    """The legs made by the way from `area` to `to` since the character came to `area` (counted afresh on each new
    level: an arrival anywhere is no failure), this one counted."""
    if agenda.way_from != area:
        agenda.ways.clear()
        agenda.way_from = area
    agenda.ways[area, to] += 1
    return agenda.ways[area, to]


def way_spent(agenda: Agenda, area: int, child: int, tried: int) -> bool:
    """Whether the way from `area` into `child` was made over zonenav.WAY_TRIES legs with no arrival: the child blocked
    for the game, said, and `area` goes on (no repeat guard leaving the game: Upper Kurast's passage to the Causeway,
    "TZ next level again and again", 13:48:00 on 2026-10-21)."""
    if tried <= zonenav.WAY_TRIES:
        return False
    boss_stays(agenda, child, f'its way in from {display_name(area)} was made {tried - 1} times with no arrival')
    agenda.blocked[child] = f'its way in from {display_name(area)} was made {tried - 1} times with no arrival'
    # The watch tools read it (d2-loop-watch logwords.py ZONE_BLOCKED, EVENT, NOW)
    LOG.info('Macro: zone: %s (%d) blocked: %s', display_name(child), child, agenda.blocked[child])
    return True


def zone_door(agenda: Agenda, area: int, goal: Objective, stop: Abort, tried: int = USE_TRIES) -> bool:
    """Whether the way on's stop `stop` from `area` is a door no click takes (`SKIP_DOOR`) into child `goal.to` under
    zone navigation: the child blocked for the game, said, and `area` goes on. The player, 2026-10-21 ~09:35: blocked
    and said, no retry, until the click failures are researched. A door to a boss alive (BOSS_STAYS, `boss_stays`) is
    tried USE_TRIES times (`tried`: `way_tried`'s count, this leg's in it), the game kept, then the loop stops."""
    if not SKIP_DOOR or stop.cause != 'door' or goal.to is None:
        return False
    if tried < USE_TRIES and boss_held(agenda, goal.to):
        # The watch tools read it (d2-loop-watch logwords.py EVENT, NOW)
        LOG.info('Macro: zone: %s: try %d of %d into %s, a boss alive there: the game is not left', stop, tried,
                 USE_TRIES, display_name(goal.to))  # fmt: skip
        return True
    boss_stays(agenda, goal.to, f'no click took its door ({stop})')
    agenda.blocked[goal.to] = f'no click took its door ({stop})'
    # The watch tools read it (d2-loop-watch logwords.py ZONE_BLOCKED, EVENT, NOW)
    LOG.info('Macro: zone: %s: %s blocked, %s goes on', stop, display_name(goal.to), display_name(area))
    return True


def zone_use(
    agenda: Agenda,
    area: int,
    goal: Objective,
    stop: Abort,
    tried: int,
    level_run: Callable[[], None] | None = None,
) -> bool:
    """Whether the way on's stop `stop` from `area` is an object's clicks that took nothing (teleport.py `Untook`: a
    portal into child `goal.to`) under zone navigation (SKIP_USE): the leg is over and the game kept; tried
    USE_TRIES times (`way_tried`, this leg counted), the child is blocked for the game, said, and `area` goes on. The
    Worldstone Chamber's portal left the game at 17:24:39 on 2026-10-21 (rca/2026-10-21/worldstone-chamber-findings.md):
    act 5's other zones never played. One that says the hall is fought first posts `level_run` instead, the leg not
    counted (FOUGHT_FIRST, `fought_first`)."""
    if not SKIP_USE or not isinstance(stop, Untook) or goal.to is None:
        return False
    if fought_first(agenda, area, goal.to, stop, level_run):
        return True
    if tried < USE_TRIES:
        # The watch tools read it (d2-loop-watch logwords.py EVENT, NOW)
        LOG.info('Macro: zone: %s: try %d of %d into %s, the game is not left', stop, tried, USE_TRIES,
                 display_name(goal.to))  # fmt: skip
        return True
    boss_stays(agenda, goal.to, f'no click took its way in in {tried} tries ({stop})')
    agenda.blocked[goal.to] = f'no click took its way in in {tried} tries ({stop})'
    # The watch tools read it (d2-loop-watch logwords.py ZONE_BLOCKED, EVENT, NOW)
    LOG.info('Macro: zone: %s (%d) blocked: %s; %s goes on', display_name(goal.to), goal.to, agenda.blocked[goal.to],
             display_name(area))  # fmt: skip
    return True


def foes_near(world: World) -> int:
    """The live hostiles the hunt may strike within SIGHT of the character (the runner's `_attacker_near` ring)."""
    from inventory_tracking.macros.hunting.base import SIGHT, hostiles  # late: the hunt's modules import the loop's

    here = world.player
    if here is None or here.in_town:
        return 0
    return sum(
        1 for m in hostiles(world) if m.mode not in DEAD_MODES and math.dist((m.x, m.y), (here.x, here.y)) <= SIGHT
    )


def portal_fight(run: Run, tz: LegHands, game: str, goal: Objective) -> bool:
    """PORTAL_FIGHT_FIRST: with a hostile within SIGHT, the fight posted instead of the Town Portal's cast, said, up to
    PORTAL_FIGHTS times for `goal` on the character's level in `game`; whether it was (the goal is kept)."""
    from inventory_tracking.macros.hunting.base import SIGHT  # late: the hunt's modules import the loop's

    world = run.world()
    player = world.player
    if not PORTAL_FIGHT_FIRST or player is None or player.in_town or goal.label == DANGER_PORTAL:
        return False
    near = foes_near(world)
    if not near:
        return False
    key = (game, player.area, goal.key)
    for held in [k for k in _portal_fights if k[0] != game]:
        del _portal_fights[held]
    fought = _portal_fights.get(key, 0)
    if fought >= PORTAL_FIGHTS:
        LOG.info('Macro: tz: %s with %d hostiles within %.0f after %d fights: cast all the same', goal.label, near,
                 SIGHT, fought)  # fmt: skip
        return False
    turned = tz.terrorized(player.area) is False
    fight = (tz.fight if turned else tz.fight_back) or tz.level_run
    _portal_fights[key] = fought + 1
    # The watch tools may read it (d2-loop-watch logwords.py)
    LOG.info('Macro: tz: %s held: %d hostiles within %.0f, %s first (%d of %d)', goal.label, near, SIGHT,
             'the plain run fights them' if turned else 'the level run fights them', fought + 1,
             PORTAL_FIGHTS)  # fmt: skip
    fight()
    return True


def boss_held(agenda: Agenda, child: int) -> list[Boss]:
    """The bosses of the game's scope alive on the levels `child` holds (zonenav.py `boss_reach`)."""
    plan = agenda.plan
    if not isinstance(plan, Itinerary) or not zonenav.on(plan):
        return bosses_alive(agenda, frozenset((child,)))
    return bosses_alive(agenda, zonenav.boss_reach(zonenav.graph_of(plan), child))


def boss_stays(agenda: Agenda, child: int, why: str) -> None:
    """Under BOSS_STAYS, a level holding a boss of the ledger alive (`boss_held`) is never blocked for `why`: the loop
    stops where it is for the player (Abort, cause 'idle': stops.py STOP, the game not left), the bosses named."""
    alive = boss_held(agenda, child)
    if not alive:
        return
    # The watch tools read it (d2-loop-watch logwords.py EVENT, NOW)
    LOG.info('Macro: zone: %s (%d): %s, %s alive: the loop stops for the player, the game is not left',
             display_name(child), child, why, said(alive))  # fmt: skip
    raise Abort(stop_line(alive, f'{display_name(child)}: {why}'), cause='idle')


def boss_alive(agenda: Agenda) -> str | None:
    """Under BOSS_STAYS, the bosses of the game's scope alive (`bosses_alive`: the ledger's, its kills the tracker's),
    said ('Baal (The Worldstone Chamber), Maffer Dragonhand (Durance of Hate Level 3)'); None with none, off a plan,
    or the switch off."""
    alive = bosses_alive(agenda)
    return said(alive) if alive else None


def fought_first(agenda: Agenda, area: int, to: int, stop: Abort, level_run: Callable[[], None] | None) -> bool:
    """Whether the way on's `Untook` from `area` into `to` says the hall is fought first (FOUGHT_FIRST): the leg is
    uncounted (`way_tried`'s count taken back), said, and `level_run` posted to fight it, up to FOUGHT_RUNS a way."""
    if not FOUGHT_FIRST or level_run is None or FOUGHT not in str(stop):
        return False
    runs = fought_key(area, to)
    if agenda.ways[runs] >= FOUGHT_RUNS:
        return False
    agenda.ways[runs] += 1
    if agenda.ways[area, to] > 0:
        agenda.ways[area, to] -= 1  # no try of USE_TRIES or WAY_TRIES
    # The watch tools read it (d2-loop-watch logwords.py EVENT, NOW)
    LOG.info('Macro: zone: %s: the level run fights it (%d of %d), no try counted into %s, the game is not left',
             stop, agenda.ways[runs], FOUGHT_RUNS, display_name(to))  # fmt: skip
    level_run()
    return True


def fought_key(area: int, to: int) -> tuple[int, int]:
    """The key `Agenda.ways` counts the fought-first level runs from `area` into `to` by (cleared with the way's own
    count on a new level): the child's id negated, never a level's."""
    return (area, -to)


def boss_of(progress: Progress, area: int) -> str:
    """The boss the route fights on level `area` ('' with none)."""
    chosen = progress.chosen(area)
    if chosen is None:
        return ''
    return next((stage.boss for stage in chosen[1].stages if stage.kind == FIGHT), '')


def full_clear(loop: Loop) -> bool:
    """Whether the loop's kind is Full clear TZ (the Herald hunt: every hostile, every room)."""
    return loop.kind.full_clear
