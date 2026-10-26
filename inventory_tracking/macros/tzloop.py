"""The KP_6 loop's terror zone kinds (TZ leveling, Full clear TZ): each leg is one agenda goal (macros/goals-plan.md).

`choose` reads the game into a `tzroutine.GameView`, derives the game-level goals (`tzroutine.produce`) and asks the
agenda for the next one (`Agenda.next`: stack, then queue, then LEAVE_GAME; in act 3 first Town Portal home and the
waypoint to the Fortress, agenda.py `game_end`, 2026-10-19). `perform` makes it one leg with the
existing routines (routines.py, waypoint.py, visit.py, portal.py, pursuit.py via `LegHands.level_run`).
Offered by three presses of KP_6 and restart.py `--kind tz` / `--kind tzclear` while `ENABLED`.
"""

import functools
import math
import time
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace

from inventory_tracking.common import LOG
from inventory_tracking.game.records import World
from inventory_tracking.levels.presets import display_name, numbered_name
from inventory_tracking.macros import actloop, merc, zonenav, zonewait
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
    RESUME,
    SKIPPED,
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
    FOLD_ROOM,
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
from inventory_tracking.macros.threat import watched_sleep
from inventory_tracking.macros.town import Exit
from inventory_tracking.macros.travel import cut
from inventory_tracking.macros.tzroutine import (
    ACT_BOSS_LEVELS,
    ON_THE_WAY,
    Excursion,
    GameView,
    Itinerary,
    alone_act,
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
# STOPS_FOR_ACT_BOSSES (the player, 2026-10-23 ~08:50, the loop stood 05:32-08:50 for Icehawk Riftwing in Sewers
# Level 1, its runs spent: "follow your goals. Icehawk isn't act boss"; the goals: "run all the time, without dying and
# good exp/hour"). True: BOSS_STAYS stops the loop only for an act boss (ACT_BOSSES' levels) alive; another boss is
# still hunted with its level's BOSS_RUNS (zonenav.py BOSSES_HOLD), then left alive, said, and the game goes on.
# False: any boss of the ledger stops it, as before.
STOPS_FOR_ACT_BOSSES = True
# A rotating zone that turned in this game with a boss of the ledger alive on a level of its own (and no zone of the new
# plan holding that level) is kept in the plan (`zone_of`): its levels holding a live boss are worked on the way
# (hunting/choice.py BOSS_ROTATION), the others blocked (TURNED, `turned_levels`), until those bosses are dead or their
# runs spent (zonenav.py BOSSES_HOLD). The audit's "zone rotation" cause: 72 boss-game rows in 32 games (a replanned
# zone dropped the old zone's bosses: Duriel, Andariel, the Summoner, Radament...). Each level is in one rotating zone
# only, so the zone is the ledger's, read back after a restart. False: the plan is the zones read now, as before
BOSS_ZONES = True
TURNED = 'the zone turned: no boss of the game is left there'
# MANUAL_TURNED (2026-10-24, rca/2026-10-24/route-spin-findings.md): a level of a shard act's zone (Act<N>-Manual, kept
# in the plan all game: ACT_OWED, `zone_of`) read not terrorized has a level run that ends at once and goes to nothing
# (hunting/choice.py ZONE_LEFT) unless a ledger boss holds it (BOSS_ROTATION), so travelling to it gives nothing: the
# waypoint back to Black Marsh at 12:06:11 on 2026-10-24 (the Countess killed 12:05:07, the rotating zone turned at
# 12:00) cost 43 s for 724 exp, The Worldstone Keep Level 2's at 04:04:53 on 2026-10-23 14 s for 0. True: such a level
# of the trip's own zone is blocked as TURNED is (judged each leg, not kept), so the zone navigation never goes there;
# the act's levels still read terrorized stay owed. False: owed and gone to, as before (ZONE_LEFT_NO_WAY then blocks
# each child at its first leg). On since 2026-10-24 (the player's ruling, relayed by the coordinator:
# "maybe we need to mark them internaly as finished? why do we think that we have to do something there if there is
# clearly nothing left?"; again at 12:45: the Forgotten Tower and Hole Level 1 blocked after their spin): such a level
# is in the zone's `finished` (Judged: cleared or blocked), so ACT_OWED owes it no more (`levels_owed`, `blocked_said`,
# running/recovery.py), the rotation's order passes it (zonenav.py `play_order`) and the game's end is not held for it;
# it is no `Agenda.blocked` of the game's record.
MANUAL_TURNED = True
MANUAL_TURNED_SAID = 'nothing left there: read not terrorized, no boss of the game held (finished)'
# WAYLESS_BLOCKS (2026-10-24, rca/2026-10-24/no-goals-stop-findings.md; game cybergg10, 19:32:37): a level whose run
# ended with no way on (agenda.py `no_way_on`: "no way to Plains of Despair: the fight first") has its NEXT_LEVEL goals
# dropped for the game (`Agenda.refresh`), but the zone's judge still took its child for work left, so zonenav.py
# `_produce` gave only "on into Plains of Despair", the refresh dropped it, and the empty queue was "no goals left" with
# Andariel, Duriel and Mephisto alive in the plan: the loop stopped (BOSS_STAYS). True: a child of such a level is
# blocked (judged each leg from `Agenda.wayless`, the game's record's, never kept in `Agenda.blocked`), so the zone
# goes on to its next root. False: as before
WAYLESS_BLOCKS = True
WAYLESS_SAID = 'no way on from {} in this game: its way in is dropped'
# UNROUTED_AFTER_BOSSES (2026-10-24, the same stop): `unrouted` blocked every shard act's level still owed "at the
# game's end" (60 levels, Andariel's, Duriel's and Mephisto's among them), then the act bosses alive stopped the loop
# (BOSS_STAYS) and the game did not end; those blocks stayed (the game's record) and the loop turned on again judged
# every root finished: "no goals left" at once (19:34:01). True: no level is blocked as unrouted while an act boss of
# the plan is alive (the game cannot end then), and such blocks already made (an old service's, a record's) are dropped
# at the next leg (`reroute`), so the zone routes to the bosses and the owed levels again. False: as before
UNROUTED_AFTER_BOSSES = True


def unrun_levels(
    plan: Itinerary, wanted: Callable[[int], bool | None] | None, finished: frozenset[int]
) -> frozenset[int]:
    """MANUAL_TURNED: the levels of `plan`'s shard acts (its `Act<N>-Manual` zones) whose run ends at once, the zone
    left (running/legs.py `_agenda_policy`): in their trip's zone and read not terrorized (`wanted`, the tracker's
    `terrorized`); no town. A rotating zone's are `turned_levels`'."""
    if not MANUAL_TURNED or wanted is None:
        return frozenset()
    names = set(plan.zone.split(' + '))
    acts = [zone for act in range(1, 6) if f'Act{act}-Manual' in names and (zone := manual_zone(act)) is not None]
    found = set()
    for level in {area for zone in acts for area in zone.areas} & plan.areas:
        if level in TOWNS or wanted(level) is not False:
            continue
        trip = plan.trip_of(level, finished)
        if trip is not None and level in trip.zone:
            found.add(level)
    return frozenset(found)


# The ledger's book attached before the zone is read (`book_first`, 2026-10-22,
# rca/2026-10-22/restart-zone-findings.md): after a service restart the agenda's ledger had no book until
# `bosses_planned`, after `zone_of`, so the first plan lacked the zones kept for their bosses (Act2-FarOasis,
# Act2-TalRashas in game cyberg65, 19:49:43): "Town Portal: off the zone" from Maggot Lair, the kept zones read back
# only in town. False: attached after the plan, as before
BOOK_FIRST = True
# A shard's act owed (2026-10-22; the player: "make sure that we don't leave the game if TZ is rotated but we still have
# act1 to run"; "no save/exits on games with worldstone shards spent! you must finish the game correctly => all levels +
# use all overflow shards => maybe more acts + rotating TZ"): the levels the plan works of each act a shard terrorized
# this game (`Agenda.acts`: the kind's own and the overflow acts, the game's record's) are owed until run
# (`levels_owed`), as its live bosses are (BOSS_STAYS). A rotation adds zones (`zone_of`'s `known`: the acts' zones
# always planned, first) and never drops these, so the plan routes to them. A recovery's leave (running/recovery.py
# BOSS_RECOVERY) keeps the game for them BOSS_KEEPS times. At the game's end (LEAVE_GAME, the way to the act's last
# town) a level still owed has no goal of the plan to reach it: the plan's gap, blocked with its why (`unrouted`), as
# one blocked after its bounded tries (a door no click takes, a portal that never opens) and those behind it are; all
# said at the end (`blocked_said`), kept in the game's record (`Agenda.blocked`), and the game ends: the loop never
# stands stopped for what it cannot do (off for the 20:26 and 20:42 restarts, when such a level held the game). False:
# only the bosses hold the game
ACT_OWED = True
# A level's verdict is the policy's it is worked under now (2026-10-22, rca/2026-10-22/tombs-policy-findings.md; the
# player: "make correct architectural fix, no ad-hoc solutions"). Game cyberg65: Tal Rasha's tombs worked on the way
# for Duriel as the rotation turned (19:53-19:59), then act 2 terrorized by an overflow Eastern shard (21:40:32) and
# owed under the act's policy, which tours the rooms; the tombs' state from the way on (entered, one run, never toured,
# five blocks "entered and left unfinished" by the hub's rule of before the 20:04 fix) read as the verdict under the
# new policy, so ACT_OWED dropped them and the act's tombs would go unplayed. True: each leg keeps the policy each
# entered level is judged under (`Agenda.worked_under`); a level whose work under the policy before does not stand for
# the one now (zonenav.py `rework`: no room toured, now a touring policy) is judged afresh, as a level not entered
# (`rework_levels`): its runs counted from here (`Agenda.reopened`), its clear and its block for being left unfinished
# dropped, entered again (a tour's marks gone through again: which leads into it is not known), its map read and the
# tracker's explored rooms kept. A block by the hub's rule under the policy it was set under stays. False: the state
# read as it is under any policy, as before
POLICY_NOW = True
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
# The held fight bounded (2026-10-24, rca/2026-10-24/route-spin-findings.md "Portal hold"): the belt-low trip at
# 15:26:21 (8 hostiles within 30, none within 12) posted the agenda's level run, which is the level's whole run: the
# portal waited 358 s, through the level's clear and a tier 5 Herald pack, life down to 2097/2943 on ground potions;
# 14 holds of 91 lasted over 20 s on 10-21..24 (9 over 60 s). True: the held run (`fight_back`) is the fight for at
# most PORTAL_FIGHT_SECONDS: then its looks read SKIPPED (`worth_skip`, running/legs.py `_agenda_policy`), so the run
# fights only what attacks in reach (pursuit.py FIGHT_BEFORE_END) and ends, and the portal is asked again: none within
# SIGHT, it is cast; else the next fight, PORTAL_FIGHTS at most as before. The held fight is no run of its level: its
# count is taken back (`Agenda.worked`, `ended_empty`, `wayless`). A level no longer terrorized keeps the plain run
# (`LegHands.fight`, no agenda policy to end it): PORTAL_FIGHT_PLAIN's. False: the level run, as before. On from the
# restart after 16:05 on 2026-10-24 (12 replay tests; macros+skills 10172 passed with the switches on).
PORTAL_FIGHT_NEAR = True
PORTAL_FIGHT_SECONDS = 8.0
PORTAL_FIGHT_OVER = 'Macro: tz: %s: the held fight is over after %.0f s: the portal is asked again'
# The held plain run bounded too (2026-10-24, the coordinator's go): on a level no longer terrorized the held fight is
# the plain run (`LegHands.fight`), which has no agenda policy to end it (52 s at 22:01:10 on 2026-10-23). True: its
# hold is kept as the agenda run's (`PortalHold.plain`), and the runner ends the attack mode after
# PORTAL_FIGHT_SECONDS when the same run is still on (running/legs.py `_plain_over`, as merclost.py ends a run for its
# trip), then the portal is asked again. A run cut so fights nothing more in reach: the next ask holds again while a
# hostile is within SIGHT, PORTAL_FIGHTS at most. False: the plain run as long as it lasts, as before
PORTAL_FIGHT_PLAIN = False


@dataclass
class PortalHold:
    """A fight held for a Town Portal (PORTAL_FIGHT_NEAR): its game, goal and start (time.monotonic), the agenda's
    run counts then (taken back after it), whether its seconds are up."""

    game: object  # the agenda's (`Agenda.game`)
    key: tuple
    label: str
    started: float
    worked: Counter
    ended_empty: Counter
    wayless: frozenset[int]
    plain: bool = False  # the plain run's (PORTAL_FIGHT_PLAIN): ended by the runner, not by a policy
    over: bool = False


_portal_hold: PortalHold | None = None
# A trip's packages folded into one (2026-10-24, the same session): the belt-low package held its Town Portal at
# 15:26:21; the room package pushed over it at 15:32:19 went to town and back, and then the belt package's own portal
# made a second trip at 15:32:56 (22 s, 0 items: the belt was refilled by the first visit); the same at 22:00:21 on
# 2026-10-22 (37 s). True: as a package's Town Portal is cast, the trip packages under it whose own portal is not made
# yet (their first goal on the stack, of TRIP_KINDS only) are folded in: their town goals this trip lacks (the merc's
# revive) put after its town visit, the rest dropped, said. False: each package its own trip, as before
# On from the restart after 16:05 on 2026-10-24, with PORTAL_FIGHT_NEAR.
PORTAL_TRIPS_FOLD = True
TRIP_KINDS = frozenset({PORTAL_TO_TOWN, WAYPOINT, TOWN_ROUTINE, merc.MERC_ROUTINE, THROUGH_PORTAL, RESUME})
# A recovery's game end (`next_goal`): a stop already ruled on (stops.py), left as before
GIVEN_UP = 'the game given up (a recovery)'
# The alone kind's game ended unplayed (actloop.py `alone_end`, 2026-10-25, the player: "no other levels, no other
# shards"): left as GIVEN_UP's (no carried shard used at the end, no level or boss owed: none of the game's is its own),
# the ground's valuables picked up first (`last_look`)
ALONE_ENDS = 'the game ends unplayed: its kind plays no other level'
UNPLAYED = frozenset((GIVEN_UP, ALONE_ENDS))

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


def slot_left() -> float:
    """Seconds left in the terror zones' slot now (they turn every ZONE_TURN s, on :00 and :30)."""
    return ZONE_TURN - time.time() % ZONE_TURN


def leg_of(goal: Objective) -> str:
    """The leg `goal` is made as."""
    return LEGS[goal.kind]


def zone_of(
    tz: LegHands, acts: tuple[int, ...] = (), bosses: BossLedger | None = None, alone: bool = False
) -> Itinerary | None:
    """The itinerary of the zones the tracker reads as terrorized now (tzroutine.py `itinerary`), with each of `acts`
    a shard terrorized in this game (agenda.py `Agenda.acts`): planned whether or not the client's list names it
    (rca/2026-10-20/act-terrorize-findings.md §6 check 4 is open), and played in their order (the kind's act first,
    then the acts of shards over the limit: actloop.py OVERFLOW); and the rotating zones turned with a boss of
    `bosses` alive (BOSS_ZONES, `boss_zones`). `alone`: an alone kind's game (loop.py `Kind.alone`, Act 2 TZ leveling,
    2026-10-25): its act alone, no rotation (tzroutine.py `itinerary`)."""
    read = frozenset(area for area in zone_levels() if tz.terrorized(area))
    known = frozenset(area for act in acts if (zone := manual_zone(act)) is not None for area in zone.core)
    plan = itinerary(read | known, tuple(acts), alone)
    if alone and alone_act(tuple(acts)) is not None:
        return plan  # no rotating zone is played: none kept for its bosses
    kept = boss_zones(bosses, plan, tz) if bosses is not None else frozenset()
    return itinerary(read | known | kept, tuple(acts), alone) if kept else plan


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


def book_first(agenda: Agenda, progress: Progress | None) -> None:
    """BOOK_FIRST: the game's ledger on the tracker's book (its file-backed records, read back after a restart)
    before the zone is read (`zone_of`), so the zones kept for their bosses are in the first plan."""
    if BOOK_FIRST and agenda.bosses.book is None and progress is not None:
        agenda.bosses.attach(progress.dead)


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
    # A boss never seen on a level every room of which was seen is not there (bossledger.py BOSS_UNSEEN); an act boss
    # is settled by its kill alone (terror/tracker.py BOOK_KILLS, BOOK_RECALL)
    agenda.bosses.unseen(agenda.explored & scope, ACT_BOSSES)
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
        if (why := actloop.alone_stop(loop)) is not None:
            raise Abort(why, cause='idle')  # stops.py: STOP, in the lobby
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
    if (why := actloop.alone_end(loop)) is not None:
        # The watch tools may read it (d2-loop-watch logwords.py)
        LOG.info('Macro: act: %s: the game ends, no zone of it played', why)
        return Objective(LEAVE_GAME, ALONE_ENDS, STACK)
    book_first(agenda, progress)
    plan = zone_of(tz, agenda.acts, agenda.bosses, getattr(loop.kind, 'alone', False))
    if plan is None and not player.in_town and (left := tz.sighted(None)) is not None:
        # The zone turned under the game with a valuable still on the ground: it is picked up first, then the game's
        # end. A Set Occult Codex by Andariel, room just made in the cube, stopped the loop at the 08:30 turn
        # (08:30:01 on 2026-10-20)
        agenda.refresh(())
        return agenda.next((player.x, player.y), valuable=left, area=player.area)
    if plan is None:
        raise Abort('no terror zone is read in this game')
    # ZONE_WAIT_WSK (macros/zonewait.py, 2026-10-25, the player: "do worldstone keep, if we get some shard - good, if
    # not - next game"): the wait for a zone the loop cannot play filled with Worldstone Keep games, the zone read
    # played again as soon as it is playable; off, or with the next zone nearer than one such game, the wait below
    alone = actloop.alone(loop.kind)  # no filler game: its kind plays no other level
    filled = None if alone else zonewait.fill(agenda.game, plan, player.in_town, player.area, zone_wait(time.time()))
    if filled is not None:
        plan = filled
    elif not plan.excursions and player.in_town:
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
    reroute(agenda)  # UNROUTED_AFTER_BOSSES: no game's-end verdict while an act boss is alive
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
        visit_due=visit_wanted(world, loop, plan.next_excursion(frozenset(agenda.finished)) is not None),
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
        # The bosses alive, None not known (BOSS_STAYS off: no ledger read); the rotation's slot (ROTATION_ANY_ACT)
        living = {boss.area for boss in bosses_alive(agenda)} if BOSS_STAYS else None
        left = slot_left()
        ordered = zonenav.play_order(graph, plan, area, living, agenda.finished, left)
        said_order = f'{plan.zone}: {list(ordered.roots)}'
        if ordered is not graph and agenda.zone_said.get(0) != said_order:
            agenda.zone_said[0] = said_order
            if zonenav.any_act_order(graph, plan, living, agenda.finished, left) is not None:
                # zonenav.py ROTATION_ANY_ACT (2026-10-23); the watch tools may read it
                LOG.info("Macro: zone: the rotation from any act: %s after the act's boss, %.0f s left in its slot, "
                         'from %s', list(ordered.roots), left, display_name(area))  # fmt: skip
            elif ordered.roots[0] != graph.roots[0]:
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
    dead = progress.dead() if progress is not None and progress.dead is not None else None

    sides = zonenav.sides_of(graph)

    def own(level: int) -> bool:
        found = zone_script(progress, plan, level) if progress is not None else None
        return zonenav.own_work(found[1] if found is not None else None, facts, dead, sides)

    # The bosses of the ledger alive on each level of the game's scope (zonenav.py BOSSES_HOLD), and the levels of a
    # zone kept for its bosses (BOSS_ZONES): those holding none blocked, the others worked on the way
    alive = bosses_alive(agenda)
    turned = turned_levels(plan, progress.wanted if progress is not None else None)
    unrun = unrun_levels(plan, progress.wanted if progress is not None else None, frozenset(agenda.finished))
    unrun -= agenda.cleared  # a level cleared before the zone left it keeps its verdict (the last leg's judge)

    def held(level: int) -> bool:
        reach = zonenav.boss_reach(graph, level)
        return any(boss.area in reach for boss in alive)

    def blocked(level: int) -> str:
        if (found := agenda.blocked.get(level, '')) or (level in turned and not held(level)):
            return found or TURNED
        parent = graph.nodes[level].parent
        if WAYLESS_BLOCKS and parent is not None and parent in agenda.wayless:
            return WAYLESS_SAID.format(display_name(parent))
        return MANUAL_TURNED_SAID if level in unrun and not held(level) else ''

    def states() -> dict[int, zonenav.LevelState]:
        return {
            level: zonenav.LevelState(
                entered=level in agenda.entered,
                mapped=level in agenda.mapped,
                explored=level in agenda.explored,
                runs=agenda.worked[level] - (agenda.reopened.get(level, 0) if POLICY_NOW else 0),
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

    found = states()
    judged = zonenav.judge(graph, found, how)
    if area is not None and rework_levels(agenda, progress, graph, judged, area):
        found = states()
        judged = zonenav.judge(graph, found, how)
    # In a tour's hub, a toured level entered and left with the zone's own verdict unfinished (not fully explored by
    # its policy) is blocked: its mark was gone through and which mark leads back is not known. Judged first: the
    # agenda's tour flag alone (`explored`) is never set on a way on, so the Canyon's tombs turned under the game and
    # worked on the way for Duriel, each "cleared", were all said blocked (cyberg65 2026-10-22 19:54-19:58,
    # rca/2026-10-22/tombs-findings.md). A level entered under another policy is judged afresh before it
    # (`rework_levels`): entered again under this one, then left unfinished, it is blocked
    hub = graph.node(area)
    left = [
        child
        for child in (hub.children if hub is not None else ())
        if graph.nodes[child].toured
        and child in agenda.entered
        and child not in agenda.blocked
        and child not in judged.explored
        and child not in judged.finished
    ]
    if not left:
        return graph, judged
    for child in left:
        agenda.blocked[child] = LEFT_UNFINISHED
        found[child] = replace(found[child], blocked=agenda.blocked[child])
    return graph, zonenav.judge(graph, found, how)


LEFT_UNFINISHED = "entered and left unfinished: which of its tour's marks leads back is not known"


def rework_levels(
    agenda: Agenda, progress: Progress | None, graph: ZoneGraph, judged: zonenav.Judged, here: int
) -> bool:
    """POLICY_NOW: each level of the zone entered in this game noted with the policy `judged` judged it under
    (`Agenda.worked_under`); one whose work under the policy noted before does not stand for it (zonenav.py `rework`)
    judged afresh, as a level not entered: its runs counted from here (`Agenda.reopened`), its clear dropped (`kept`,
    `cleared`) and its block for being left unfinished (`LEFT_UNFINISHED`, the rule's under the policy before), entered
    again (out of `Agenda.entered` and the route facts', but the level `here`, the character's) and, a toured level, its
    hub's tour marks gone through again (which of them leads into it is not known: one into a level done is a way in and
    straight back up). Its map read (`mapped`) and the tracker's explored rooms (hunt.py's tour, `visited_rooms`) are
    kept: its hostiles seen and left are remembered, and a touring policy goes for them (hunting/choice.py). Whether
    any was; said."""
    if not POLICY_NOW:
        return False
    reworked: list[int] = []
    for level in sorted(agenda.entered & graph.nodes.keys()):
        now = judged.policies.get(level)
        if now is None:
            continue
        then = agenda.worked_under.get(level)
        agenda.worked_under[level] = now
        if then is None or not zonenav.rework(then, now, level in agenda.explored):
            continue
        reworked.append(level)
        agenda.reopened[level] = agenda.worked[level]
        agenda.kept.discard(level)
        agenda.cleared.discard(level)
        agenda.finished.discard(level)
        if agenda.blocked.get(level) == LEFT_UNFINISHED:
            del agenda.blocked[level]
        if level != here:
            agenda.entered.discard(level)
        # The watch tools may read it (d2-loop-watch logwords.py)
        LOG.info('Macro: zone: %s (%d) was worked %s, now %s: judged afresh (%d run(s) before, not counted)',
                 display_name(level), level, then, now, agenda.worked[level])  # fmt: skip
    if not reworked or progress is None:
        return bool(reworked)
    hubs = {
        (parent, entry.mark)
        for level in reworked
        if (node := graph.nodes[level]).toured and (parent := node.parent) is not None and (entry := node.entry)
    }
    facts = progress.facts
    progress.facts = replace(
        facts,
        entered=facts.entered - (frozenset(reworked) - {here}),
        used=frozenset(fact for fact in facts.used if (fact[0], fact[1]) not in hubs),
        finished=facts.finished - hubs,
    )
    return True


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
    if agenda.zone_at != area:
        agenda.zone_at, agenda.arrival_runs = area, agenda.worked[area]
    graph, judged = zone_judged(progress, loop, plan, area)
    if zonenav.TIME_BUDGET and progress is not None and zone_budget(loop, plan, progress, world, graph):
        graph, judged = zone_judged(progress, loop, plan, area)  # judged again with the children skipped blocked
    agenda.finished = set(judged.finished)
    if zonenav.RESUME:
        agenda.cleared = set(judged.cleared)  # in the game's record (macros/midgame.py RECORD) as 'kept'
    for level in sorted(agenda.entered):
        if level not in graph.nodes or not (level in judged.explored or level in judged.finished):
            continue
        text = zonenav.said(graph, judged, level)
        if agenda.zone_said.get(level) != text:
            agenda.zone_said[level] = text
            LOG.info('Macro: zone: %s', text)
    fetch = fetch_of(graph, area, tz.remembered()) if zonenav.FETCH_ELSEWHERE else None
    step = None
    if progress is not None:
        found = progress

        def base(level: int) -> tuple[str, Script] | None:
            return zone_script(found, plan, level)

        progress.selected.update(
            zonenav.scripts(graph, judged, base, agenda.no_back, agenda.no_walk, fetch[0] if fetch else None)
        )
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
        visit_due=visit_wanted(world, loop, zonenav.next_root(graph, judged) is not None),
        no_back=frozenset(agenda.no_back),
        no_walk=frozenset(agenda.no_walk),
        passed=agenda.worked[area] > agenda.arrival_runs,
        fetch=fetch,
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


def visit_wanted(world: World, loop: Loop, going_on: bool) -> bool:
    """The town visit wanted where the character stands: due (`Loop.visit_due`), or, in a town with the zone going on
    (`going_on`: a root or an excursion left), folded into the root change (loop.py FOLD_AT_ROOT, `Loop.fold_due`):
    the visit there, not a trip for room later. Said once a fold."""
    game = world.game_name
    if loop.visit_due(game):
        return True
    if not going_on or not loop.fold_due(world):
        return False
    said = (game, loop.free, loop.gainable)  # the act's town and the Fortress after it: one line
    if _folds_said.get(game) != said:
        _folds_said.clear()
        _folds_said[game] = said
        LOG.info('Macro: zone: the town visit on the way to the next root: %s cells free (under %d), %d cells to take '
                 'away', loop.free, FOLD_ROOM, loop.gainable)  # fmt: skip
    return True


_folds_said: dict[str | None, tuple] = {}  # `visit_wanted`'s line, once a fold (the game's last said)


def fetch_of(graph: ZoneGraph, area: int, remembered: Iterable[tuple[int | None, str]]) -> tuple[int, str] | None:
    """zonenav.py FETCH_ELSEWHERE: (level, label) of the valuable remembered on another level of `graph` to fetch
    next: one on the tree of `area` first, then in the graph's order; None with none (one on `area` is its PICKUP)."""
    here = graph.node(area)
    order = {level: index for index, level in enumerate(level for root in graph.roots for level in graph.subtree(root))}
    found = [
        (level, label)
        for level, label in remembered
        if level is not None and level != area and graph.node(level) is not None
    ]
    if not found:
        return None
    return min(
        found,
        key=lambda each: (here is None or graph.nodes[each[0]].root != here.root, order.get(each[0], len(order))),
    )


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


def worth_skip(loop: Loop, area: int, now: float, valuable: Callable[[], str | None] = lambda: None) -> bool:
    """zonenav.py STALLED_SKIP: whether the level run on `area` ends as the level is not worth playing on
    (`zonenav.worth`): skipped once, the agenda's block with its why (said: `Macro: zone: <level> (<id>) skipped:
    ...`), the zone's next goal then leaving it. The stall's seconds are the watchdog's (loop.py `progress_seen`: the
    kills, the levels finished and cleared, the level; running/watch.py), the loop's own wait (`cooling`) not counted;
    the going rate is the game's (experience.py `Ledger.game_rate`). A level blocked otherwise is not this one's, nor
    one with a boss of the ledger alive on it, nor while `valuable` (asked only then: a read of the ground) names one
    lying in sight: a stand by it is no stall. A fight held for a Town Portal whose seconds are up ends so too
    (PORTAL_FIGHT_NEAR, `portal_hold_over`), with no block."""
    agenda = loop.agenda
    if portal_hold_over(agenda, now):
        return True
    blocked = agenda.blocked.get(area)
    if blocked is not None:
        return blocked.startswith(SKIPPED)
    plan = agenda.plan
    if not zonenav.STALLED_SKIP or not loop.on or not isinstance(plan, Itinerary) or not zonenav.on(plan):
        return False
    seen = loop.progressed
    if seen is None or seen[0] is None or now < loop.cooling or loop.abandon:
        return False
    mark = seen[2]
    if not mark or mark[-1] != area:
        return False  # the watchdog's clock is another level's
    why = zonenav.worth(zonenav.graph_of(plan), area, now - seen[1], loop.experience.game_rate())
    if why is None or agenda.bosses.alive_in(area):
        return False  # a boss of the ledger on it: a long fight with it is no stall (zonenav.py BOSSES_HOLD's runs)
    if valuable() is not None:
        return False  # never left with a valuable on the ground (the player: "we absolutely must preserve top items")
    agenda.blocked[area] = why
    # The watch tools may read it (d2-loop-watch logwords.py)
    LOG.info('Macro: zone: %s (%d) %s', display_name(area), area, why)
    return True


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
    portal_hold_done(agenda)  # PORTAL_FIGHT_NEAR: the next leg after a held fight, whatever its goal
    try:
        world = run.world()
        game = world.game_name if world.in_game else ''
        player = world.player
        if goal.ends and game:
            unrouted(agenda, goal.label)
        if goal.ends and game and (held := owed(agenda)) is not None:
            # The way to the act's last town ends the game (agenda.py `game_end`): not with a boss alive (BOSS_STAYS)
            # nor a shard act's level owed (ACT_OWED)
            LOG.info('Macro: zone: %s, but %s: the loop stops for the player, the game is not left', goal.label,
                     held)  # fmt: skip
            raise Abort(f'{goal.label}, but {held}: the loop stops here for the player', cause='idle')
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
            if (
                goal.label not in UNPLAYED
                and tz is not None
                and player is not None
                and end_use(loop, run, key_names, tz)
            ):
                return  # a carried shard over the limit used: the game goes on with its act (actloop.py END_USE)
            if goal.label not in UNPLAYED:
                unrouted(agenda, goal.label)
            held = owed(agenda) if goal.label not in UNPLAYED else None
            if held is not None:
                # The player, 2026-10-22: "we need to kill all bosses, no exceptions" (BOSS_STAYS); a shard's act is
                # finished, every level (ACT_OWED)
                LOG.info('Macro: zone: %s, but %s: the loop stops for the player, the game is not left',
                         goal.label, held)  # fmt: skip
                raise Abort(f'{goal.label}, but {held}: the loop stops here for the player', cause='idle')
            if (blocked := blocked_said(agenda)) is not None:
                # The watch tools may read it (d2-loop-watch logwords.py EVENT)
                LOG.info('Macro: zone: the game ends with the shard acts %s: %s', list(agenda.acts), blocked)
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
            # made (the visit would put a carried one down, its stack full); at the game's end a carried one, the game
            # then going on (actloop.py END_USE)
            on = False
            if loop.done != game:
                actloop.overflow(loop, run, tz.terrorized, tz.inventory_key())
            else:
                on = actloop.use_at_end(loop, run, tz.terrorized, tz.inventory_key())
            exit = Exit(goal.exit or 'waypoint')
            if on and exit == Exit.LEAVE:
                exit = Exit.WAYPOINT  # the game goes on: its new act's levels
            if exit == Exit.WAYPOINT and loop.done == game:
                exit = Exit.LEAVE  # the game ends here: no walk to the waypoint (loop.py `exit_of`)
            loop.town(run, tz.visit, game, exit)
            if not agenda.holds(frozenset({merc.MERC_ROUTINE})):
                merc.revive_after_visit(run)  # a dead merc revived on the way (merc.py MERC_AT_ANY_VISIT)
        elif goal.kind == merc.MERC_ROUTINE:
            merc.town_routine(run, loop.merc_trips)  # the belt refilled, the merc revived (macros/merc.py)
        elif goal.kind == PORTAL_TO_TOWN:
            if portal_fight(run, tz, game, goal, agenda):
                return  # the goal kept: the fight's run is posted, the portal comes after it
            fold_trips(agenda, goal)  # PORTAL_TRIPS_FOLD: the trips under it made by this one
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
                    watched_sleep(run, landing, "the boss drops' wait")  # a hostile hitting the character ends it
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
            if zone and goal.to is not None and (why := way_unrun(agenda, plan, player.area, goal.to, tz)):
                left_unrun(agenda, player.area, goal.to, why, walk)
                agenda.done(goal)
                return
            tried = 0
            if zone and goal.to is not None:
                tried = way_tried(agenda, player.area, goal.to, counted=tried_here(tz))
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


def end_use(loop: Loop, run: Run, key_names, tz: LegHands) -> bool:
    """Save and Exit's leg with a carried shard over the limit (actloop.py END_USE, `end_due`): from a field level the
    Town Portal home first (a cast that fails is said, and the game is left as before), then the shard used in town;
    whether one was (the game goes on with its act)."""
    world = run.world()
    player = world.player
    if player is None:
        return False
    if not player.in_town:
        due = actloop.end_due(loop, run)
        if not due:
            return False
        LOG.info('Macro: act: the game ends with a carried shard over the limit (%s): Town Portal home to use it',
                 actloop.played_said(due))  # fmt: skip
        try:
            to_town(run, key_names, None)
        except Abort as stop:
            if cut(run, stop):
                raise
            LOG.info('Macro: act: no Town Portal home for the shard (%s): the game is left, the shard carried', stop)
            return False
        loop.note_portal(run)
        player = run.world().player
        if player is None or not player.in_town:
            return False
    return actloop.use_at_end(loop, run, tz.terrorized, tz.inventory_key())


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


# WAY_TRIED_AT_DOOR (2026-10-23, cyberg46: Swampy Pit Level 3 "blocked: its way in from Swampy Pit Level 2 was made
# 6 times with no arrival" within 2 s at 05:23:17-19, as Sewers Level 2, Worldstone Keep 1 and 3 before it: each "TZ
# next level" leg's level run toward the stairs ended at once (a potion's pickup, the sweep, 13 hostiles near) and was
# counted a failed way in). True: a leg is a try of the way when it starts at the way on, where the press is made
# (legs.py `_way_on`, LegHands.at_way); WAY_RUNS_A_TRY level runs toward it make one more (the bound on a way never
# reached: "TZ next level again and again", 13:48:00 on 2026-10-21). False: every leg counts, as before.
WAY_TRIED_AT_DOOR = True
WAY_RUNS_A_TRY = 5
_way_runs: Counter[tuple[int, int]] = Counter()  # the level runs toward a way on this level (`way_tried`)


# ZONE_LEFT_NO_WAY (2026-10-24, rca/2026-10-24/route-spin-findings.md): a level the zone left with no boss of the ledger
# held under it (hunting/choice.py ZONE_LEFT, BOSS_ROTATION) has a level run that ends at once and goes to nothing, its
# way on included, so a "TZ next level" leg into a child also not terrorized, made away from the way on, never moves:
# the route's step took the press, the pickup started the sweep, the run ended "nothing is left to go to" and the next
# leg cut the sweep's jump. Black Marsh at 12:06:14-12:06:47 on 2026-10-24: 70 legs in 33 s, the character still, then
# the Forgotten Tower and Hole Level 1 blocked "made 6 times with no arrival" (WAY_RUNS_A_TRY level runs a try);
# The Worldstone Keep Level 2 (04:04:55 on 2026-10-23) and Swampy Pit Level 2 (05:23:17) the same. True: such a child is
# blocked (a walk into the next root: no walk, the Town Portal) at the first leg, said, no level run posted. False:
# the legs are made until WAY_TRIES, as before. On since 2026-10-24 with MANUAL_TURNED (the coordinator; the spin
# again at 12:45 after the restart): a rotating zone's level the zone left, or a shard act's with MANUAL_TURNED off.
ZONE_LEFT_NO_WAY = True
ZONE_LEFT_SAID = 'the zone left {parent}: its level run goes to nothing, its way in included'


def way_unrun(agenda: Agenda, plan: object, area: int, child: int, tz) -> str:
    """ZONE_LEFT_NO_WAY: why the way from `area` into `child` is never gone to by a level run ('' when it is, or at
    the way on, where the leg presses through itself): `area` worked as the zone left (running/legs.py
    `_agenda_policy`: in its trip's zone, read not terrorized) with no ledger boss held (hunting/choice.py
    `boss_held`), and `child` not read terrorized."""
    if not ZONE_LEFT_NO_WAY or not isinstance(plan, Itinerary) or tz.terrorized is None:
        return ''
    if tz.at_way is not None and tz.at_way():
        return ''
    from inventory_tracking.macros.hunting import choice  # the level run's own rules (an import cycle at load)

    trip = plan.trip_of(area, frozenset(agenda.finished))
    if trip is None or area not in trip.zone or tz.terrorized(area) is not False or tz.terrorized(child) is True:
        return ''
    if zonewait.filler(plan):
        return ''  # a Worldstone Keep filler game's levels are worked, not terrorized (zonewait.py ZONE_WAIT_WSK)
    if choice.BOSS_ROTATION and choice.boss_held(agenda, area):
        return ''
    return ZONE_LEFT_SAID.format(parent=display_name(area))


def left_unrun(agenda: Agenda, area: int, child: int, why: str, walk: bool) -> None:
    """ZONE_LEFT_NO_WAY: `child`'s way in from `area` given up for the game, said as a block (the watch tools'
    ZONE_BLOCKED) or, for a walk into the next root, as no walk (the Town Portal and the waypoint instead)."""
    if walk:
        agenda.no_walk.add((area, child))
        LOG.info('Macro: zone: %s: no walk from %s into %s: the Town Portal instead', why, display_name(area),
                 display_name(child))  # fmt: skip
        return
    boss_stays(agenda, child, why)
    agenda.blocked[child] = why
    # The watch tools read it (d2-loop-watch logwords.py ZONE_BLOCKED, EVENT, NOW)
    LOG.info('Macro: zone: %s (%d) blocked: %s', display_name(child), child, why)


def tried_here(tz) -> bool:
    """WAY_TRIED_AT_DOOR: whether this leg starts at the way on (a try of the way)."""
    at_way = getattr(tz, 'at_way', None)
    return not WAY_TRIED_AT_DOOR or at_way is None or at_way()


def way_tried(agenda: Agenda, area: int, to: int, *, counted: bool = True) -> int:
    """The legs made by the way from `area` to `to` since the character came to `area` (counted afresh on each new
    level: an arrival anywhere is no failure), this one counted: at the way on (`counted`), else each WAY_RUNS_A_TRY
    level runs toward it (WAY_TRIED_AT_DOOR)."""
    if agenda.way_from != area:
        agenda.ways.clear()
        _way_runs.clear()
        agenda.way_from = area
    if not counted:
        _way_runs[area, to] += 1
        counted = _way_runs[area, to] % WAY_RUNS_A_TRY == 0
    if counted:
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


def portal_fight(run: Run, tz: LegHands, game: str, goal: Objective, agenda: Agenda | None = None) -> bool:
    """PORTAL_FIGHT_FIRST: with a hostile within SIGHT, the fight posted instead of the Town Portal's cast, said, up to
    PORTAL_FIGHTS times for `goal` on the character's level in `game`; whether it was (the goal is kept). Under
    PORTAL_FIGHT_NEAR each fight bounded (`PortalHold`), the counts of one it ended taken back on `agenda`."""
    from inventory_tracking.macros.hunting.base import SIGHT  # late: the hunt's modules import the loop's

    global _portal_hold
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
    # A Worldstone Keep filler game's level is worked, not one the zone left (zonewait.py ZONE_WAIT_WSK)
    turned = tz.terrorized(player.area) is False and not (agenda is not None and zonewait.filler(agenda.plan))
    fight = (tz.fight if turned else tz.fight_back) or tz.level_run
    _portal_fights[key] = fought + 1
    # The watch tools may read it (d2-loop-watch logwords.py)
    LOG.info('Macro: tz: %s held: %d hostiles within %.0f, %s first (%d of %d)', goal.label, near, SIGHT,
             'the plain run fights them' if turned else 'the level run fights them', fought + 1,
             PORTAL_FIGHTS)  # fmt: skip
    if agenda is not None and (PORTAL_FIGHT_PLAIN if turned else PORTAL_FIGHT_NEAR):
        _portal_hold = PortalHold(
            agenda.game, goal.key, goal.label, time.monotonic(), Counter(agenda.worked), Counter(agenda.ended_empty),
            frozenset(agenda.wayless), plain=turned,
        )  # fmt: skip
    fight()
    return True


def portal_hold_done(agenda: Agenda) -> None:
    """The leg after a fight held for a Town Portal (PORTAL_FIGHT_NEAR), the portal's or any other: the hold
    dropped, so no later run is ended by it; the counts of a run its bound ended taken back (`taken_back`)."""
    global _portal_hold
    hold, _portal_hold = _portal_hold, None
    if hold is not None and hold.over and hold.game == agenda.game:
        taken_back(agenda, hold)


def portal_hold_over(agenda: Agenda, now: float) -> bool:
    """PORTAL_FIGHT_NEAR: whether the fight held for a Town Portal (`portal_fight`) is over at `now`, its seconds up
    (said once), while its goal is still to make in its game: the level run's looks then end it (`worth_skip`); the
    plain run's (PORTAL_FIGHT_PLAIN) the runner's timer (running/legs.py `_plain_over`)."""
    hold = _portal_hold
    if hold is None or not (PORTAL_FIGHT_PLAIN if hold.plain else PORTAL_FIGHT_NEAR) or hold.game != agenda.game:
        return False
    if not hold.over:
        if now - hold.started < PORTAL_FIGHT_SECONDS:
            return False
        if not any(goal.key == hold.key for goal in agenda.stack) and hold.key not in agenda.queue:
            return False  # its goal gone (a new package, a cut): the run is the run
        hold.over = True
        # The watch tools may read it (d2-loop-watch logwords.py)
        LOG.info(PORTAL_FIGHT_OVER, hold.label, now - hold.started)
    return True


def plain_fight_bound() -> float | None:
    """PORTAL_FIGHT_PLAIN: the seconds the plain run just posted for a held Town Portal may fight
    (running/legs.py `fight`), None when it is no such run."""
    hold = _portal_hold
    if not PORTAL_FIGHT_PLAIN or hold is None or not hold.plain or hold.over:
        return None
    return max(0.0, PORTAL_FIGHT_SECONDS - (time.monotonic() - hold.started))


def taken_back(agenda: Agenda, hold: PortalHold) -> None:
    """The level run a held fight's bound ended (`portal_hold_over`) is no run of its level: the agenda's counts it
    added (`Agenda.ran`, `nothing_left`, `no_way_on`: runner.py `_run_over`) taken back."""
    for area in [area for area, runs in agenda.worked.items() if runs > hold.worked.get(area, 0)]:
        agenda.worked[area] = hold.worked.get(area, 0)
    for area in [area for area, ends in agenda.ended_empty.items() if ends > hold.ended_empty.get(area, 0)]:
        agenda.ended_empty[area] = hold.ended_empty.get(area, 0)
    agenda.wayless &= set(hold.wayless)


def fold_trips(agenda: Agenda, goal: Objective) -> None:
    """PORTAL_TRIPS_FOLD: as `goal`, the stack's top, a package's Town Portal, is cast, the trip packages under its
    package whose own portal is not made yet folded into this trip: their town goals it lacks after its town visit,
    the rest dropped, said. A package of other kinds (the Gheed's swap) is left, and all under it."""
    stack = agenda.stack
    if not PORTAL_TRIPS_FOLD or not stack or stack[-1] is not goal or goal.kind != PORTAL_TO_TOWN:
        return
    ends = [index for index, each in enumerate(stack) if each.kind == RESUME]
    if not ends:
        return
    top = ends[-1]  # this package: stack[top:], its RESUME at the bottom
    mine = stack[top:]
    visit = next((index for index, each in enumerate(mine) if each.kind == TOWN_ROUTINE), None)
    if visit is None:
        return
    kinds = {each.kind for each in mine}
    folded: list[Objective] = []
    while ends[:-1]:
        below = ends[-2]
        package = stack[below:top]  # the package under, its first goal last
        if not package or package[-1].kind != PORTAL_TO_TOWN or any(each.kind not in TRIP_KINDS for each in package):
            break
        extra = [each for each in package if each.kind not in kinds and each.kind not in (WAYPOINT, THROUGH_PORTAL)]
        kinds |= {each.kind for each in extra}
        folded += package
        mine[visit:visit] = extra  # below the visit on the stack: made after it
        del stack[below:top]
        ends.pop()
        top = below
    if not folded:
        return
    stack[top:] = mine
    # The watch tools may read it (d2-loop-watch logwords.py)
    LOG.info('Macro: agenda: %s: the trip folded in %s', goal.label,
             [each.label for each in reversed(folded) if each.kind != RESUME])  # fmt: skip


def boss_held(agenda: Agenda, child: int) -> list[Boss]:
    """The bosses of the game's scope alive on the levels `child` holds (zonenav.py `boss_reach`)."""
    plan = agenda.plan
    if not isinstance(plan, Itinerary) or not zonenav.on(plan):
        return bosses_alive(agenda, frozenset((child,)))
    return bosses_alive(agenda, zonenav.boss_reach(zonenav.graph_of(plan), child))


def boss_stays(agenda: Agenda, child: int, why: str) -> None:
    """Under BOSS_STAYS, a level holding a boss of the ledger alive (`boss_held`) is never blocked for `why`: the loop
    stops where it is for the player (Abort, cause 'idle': stops.py STOP, the game not left), the bosses named."""
    alive = stopping(boss_held(agenda, child))
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
    everyone = bosses_alive(agenda)
    alive = stopping(everyone)
    left = [boss for boss in everyone if boss not in alive]
    if left and agenda.zone_said.get(-1) != said(left):
        agenda.zone_said[-1] = said(left)
        LOG.info('Macro: zone: %s left alive: not act bosses, their runs spent (STOPS_FOR_ACT_BOSSES)', said(left))
    return said(alive) if alive else None


def stopping(alive: list[Boss]) -> list[Boss]:
    """STOPS_FOR_ACT_BOSSES: the bosses of `alive` the loop stops for (the act bosses')."""
    return [boss for boss in alive if boss.area in ACT_BOSSES] if STOPS_FOR_ACT_BOSSES else alive


def act_levels(agenda: Agenda) -> frozenset[int]:
    """The levels of the shard acts (`Agenda.acts`) the agenda's plan works (`boss_scope`); none off a plan."""
    plan = agenda.plan
    if not isinstance(plan, Itinerary) or not agenda.acts:
        return frozenset()
    acts = frozenset(area for act in agenda.acts if (zone := manual_zone(act)) is not None for area in zone.areas)
    return boss_scope(plan) & acts


def levels_owed(agenda: Agenda) -> list[int]:
    """ACT_OWED: the shard acts' levels (`act_levels`) still to run: never entered nor run this game (`Agenda.entered`,
    `worked`: the game's record's), not finished by the zone's verdict (with zone navigation `Agenda.finished` is the
    judge's at each leg; `kept` from before a restart), and not out of reach (`out_of_reach`: blocked after its bounded
    tries, or behind such a level). A level entered and left open by the zone's verdict is said at the game's end
    (`blocked_said`), not owed: the loop never stands stopped for what its zone no longer plans. None with no shard act
    or the switch off."""
    if not ACT_OWED:
        return []
    reworked = agenda.reopened if POLICY_NOW else {}
    run = agenda.entered | {level for level, runs in agenda.worked.items() if runs > reworked.get(level, 0)}
    return sorted(act_levels(agenda) - agenda.finished - agenda.kept - out_of_reach(agenda) - run)


UNROUTED = "no goal of the plan reaches it at the game's end"


def unrouted(agenda: Agenda, end: str) -> None:
    """ACT_OWED: at the game's end (`end`: its goal's label), each shard act's level still owed has no goal of the plan
    to reach it: the plan's gap, blocked with its why as a door no click takes is (said, in the game's record), so the
    loop never stands stopped for it (the coordinator, 2026-10-22 20:42). The plan routes to every level it can. None
    while an act boss of the plan is alive (UNROUTED_AFTER_BOSSES): the game does not end then."""
    if UNROUTED_AFTER_BOSSES and stopping(bosses_alive(agenda)):
        return
    for level in levels_owed(agenda):
        agenda.blocked[level] = f'{UNROUTED} ({end})'
        # The watch tools read it (d2-loop-watch logwords.py ZONE_BLOCKED, EVENT, NOW)
        LOG.info('Macro: zone: %s (%d) blocked: %s', display_name(level), level, agenda.blocked[level])


def reroute(agenda: Agenda) -> None:
    """UNROUTED_AFTER_BOSSES: with an act boss of the plan alive, the levels blocked as unrouted (`unrouted`, an old
    service's or the game's record's) unblocked, said: the game did not end, so no verdict of its end stands."""
    if not UNROUTED_AFTER_BOSSES or not any(why.startswith(UNROUTED) for why in agenda.blocked.values()):
        return
    alive = stopping(bosses_alive(agenda))
    if not alive:
        return
    levels = sorted(level for level, why in agenda.blocked.items() if why.startswith(UNROUTED))
    for level in levels:
        del agenda.blocked[level]
    # The watch tools may read it (d2-loop-watch logwords.py)
    LOG.info('Macro: zone: %s alive: the levels blocked as unrouted are routed again: %s', said(alive), levels)


def out_of_reach(agenda: Agenda) -> frozenset[int]:
    """The levels blocked (`Agenda.blocked`) and, with zone navigation, those under them in the zone's graph (no way in
    but through a blocked level: Kurast Causeway's temples)."""
    blocked = frozenset(agenda.blocked)
    plan = agenda.plan
    if not blocked or not isinstance(plan, Itinerary) or not zonenav.on(plan):
        return blocked
    graph = zonenav.graph_of(plan)
    return blocked | frozenset(level for area in blocked if area in graph.nodes for level in graph.subtree(area))


def blocked_said(agenda: Agenda) -> str | None:
    """ACT_OWED: the shard acts' levels not done that do not hold the game, said at its end: blocked after their
    bounded tries ('Tristram (38) blocked (why)'), behind a blocked one, or entered and left open by the zone's verdict;
    None with none."""
    if not ACT_OWED:
        return None
    levels = act_levels(agenda)
    reach = out_of_reach(agenda)
    blocked = sorted(levels & agenda.blocked.keys())
    behind = sorted(levels & reach - agenda.blocked.keys())
    left = sorted(levels - agenda.finished - agenda.kept - reach - frozenset(levels_owed(agenda)))
    parts = [owed_said(agenda, blocked)] if blocked else []
    if behind:
        parts.append(f'behind it {behind}')
    if left:
        parts.append(f'left open by the zone {left}')
    return '; '.join(parts) or None


def owed_said(agenda: Agenda, levels: Iterable[int]) -> str:
    """'Catacombs Level 2 (35) not done, Tal Rasha's Tomb (66) blocked (its why)'."""
    return ', '.join(
        f'{display_name(level)} ({level}) blocked ({agenda.blocked[level]})'
        if level in agenda.blocked
        else f'{display_name(level)} ({level}) not done'
        for level in levels
    )


def owed(agenda: Agenda) -> str | None:
    """What holds the game (BOSS_STAYS, ACT_OWED), said: '<bosses> alive' and '<the shard acts' levels owed>' (the
    acts named); None with nothing owed."""
    parts = []
    if (alive := boss_alive(agenda)) is not None:
        parts.append(f'{alive} alive')
    if levels := levels_owed(agenda):
        acts = ', '.join(str(act) for act in agenda.acts)
        parts.append(f'the shard act{"s" if len(agenda.acts) > 1 else ""} {acts} owed: {owed_said(agenda, levels)}')
    return '; '.join(parts) or None


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
