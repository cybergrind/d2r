"""The terror zone kinds of the KP_6 loop: TZ leveling and Full clear TZ, their legs the agenda's goals
(macros/goals-plan.md; the player, 2026-10-19).

`choose` reads the game's facts into a `tzroutine.GameView`, has the TZ leveling routine derive the game-level goals
(`tzroutine.produce`) and the agenda name the one to work now (`Agenda.next`: the package stack first, then the queue,
then LEAVE_GAME). `perform` makes it one leg, by the routines that exist: the next game and Save and Exit
(routines.py, through `Loop.next_game` and `Loop.leave`), the waypoint (waypoint.py), the town visit (visit.py through
`Loop.town`), Town Portal and back through it (portal.py), and the level run (pursuit.py, posted by the runner with
the agenda: `TzHands.level_run`), which asks `Agenda.in_level` at every look for its next target.

Off until the player promotes it (`ENABLED`): the kinds are then offered by three presses of KP_6 and restart.py
`--kind tz` / `--kind tzclear`. With it off nothing here runs.
"""

import functools
import math
import time
from collections.abc import Callable
from dataclasses import dataclass

from inventory_tracking.common import LOG
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.agenda import (
    EXCURSION,
    LEAVE_GAME,
    LEVEL,
    LOOT,
    NEW_GAME,
    NEXT_LEVEL,
    PICKUP,
    PORTAL_TO_TOWN,
    STACK,
    THROUGH_PORTAL,
    TOWN_ROUTINE,
    WAYPOINT,
    Objective,
    room_package,
)
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.loop import (
    DROPS_AFTER_KILL,
    LEAVE,
    NEXT_GAME,
    ROGUE_ENCAMPMENT,
    TOWN,
    TZ_BACK,
    TZ_CLEAR,
    TZ_LEVEL,
    TZ_LOOT,
    TZ_NEXT_LEVEL,
    TZ_PICKUP,
    TZ_PORTAL,
    TZ_WAYPOINT,
    Dead,
    Loop,
    teleports,
)
from inventory_tracking.macros.portal import through_portal, to_town
from inventory_tracking.macros.repair import gold
from inventory_tracking.macros.routines import DEAD, prebuff
from inventory_tracking.macros.shop import gold_cap
from inventory_tracking.macros.town import Exit
from inventory_tracking.macros.tzroutine import GameView, Itinerary, itinerary, produce
from inventory_tracking.macros.waypoint import travel
from inventory_tracking.macros.world import World
from inventory_tracking.routes.model import FIGHT
from inventory_tracking.routes.progress import Progress
from inventory_tracking.routes.tz_groups import installed_active_zones
from inventory_tracking.terror.bosses import KILLED_AT


# The switch (the player promotes the kinds after the checks of goals-plan.md §9): False, the KP_6 loop offers the
# Lower Kurast and Andariel kinds only, as before 2026-10-19. On since 08:58 on 2026-10-19 (the player: "launch
# tz-leveling loop after then next run and monitor/improve it"): §9's checks are made live, watched
ENABLED = True

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
    LEAVE_GAME: LEAVE,
}


@dataclass(frozen=True)
class TzHands:
    """What the runner hands the terror zone kinds (runner.py `perform`, LOOP). `level_run()` posts the level run of
    the area with the agenda (`Pursuit.agenda`, its end the next leg's); `take_one()` one pickup, else a trip back to
    a valuable seen (sightings), False with neither; `door()` the way on: at it, what lies there first and then the
    press through, else the level run to it; `sighted(area)` a valuable seen in `area` (None: in the game) still on
    the ground; `terrorized(area)` the tracker's word (terror/tracker.py); `navigate()` the means in hand set for the
    loop's moves (macros/navigation.py)."""

    level_run: Callable[[], None]
    take_one: Callable[[], bool]
    door: Callable[[], None]
    sighted: Callable[[int | None], str | None]
    terrorized: Callable[[int], bool | None]
    navigate: Callable[[], None] = lambda: None


@functools.cache
def zone_levels() -> frozenset[int]:
    """Every level of an installed Terror Zone."""
    return frozenset(area for zone in installed_active_zones() for area in zone.areas)


def leg_of(goal: Objective) -> str:
    """The leg `goal` is made as."""
    return LEGS[goal.kind]


def zone_of(tz: TzHands) -> Itinerary | None:
    """The itinerary of the zone the tracker reads as terrorized now (tzroutine.py `itinerary`)."""
    return itinerary(frozenset(area for area in zone_levels() if tz.terrorized(area)))


def choose(world: World, progress: Progress | None, loop: Loop, tz: TzHands | None) -> Objective:
    """The goal of the next leg (the module text). `Dead` with the character dead; `Abort` with no zone read."""
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
    agenda.begin(loop.game_id or world.game_name)
    if loop.abandon:
        return Objective(LEAVE_GAME, 'the game given up (a recovery)', STACK)
    plan = zone_of(tz)
    if plan is None:
        raise Abort('no terror zone is read in this game')
    agenda.plan = plan
    game, area = world.game_name, player.area
    trip = plan.excursion_of(area, agenda.finished)
    if trip is not None and progress is not None:
        # The excursion's own script for a level two routes go through (the Burial Grounds: the Crypt's, then the
        # Mausoleum's): routes/progress.py `select_route`
        progress.select_route(game, area, trip.route)
    step = progress.step(area) if progress is not None else None
    view = GameView(
        area,
        player.in_town,
        plan,
        stage=step.stage.kind if step is not None else None,
        stage_to=step.stage.to if step is not None else 0,
        worked=tuple(agenda.worked.items()),
        finished=frozenset(agenda.finished),
        sighted=tz.sighted(area),
        visit_due=loop.visit_due(game),
    )
    agenda.refresh(produce(view))
    return agenda.next((player.x, player.y), valuable=tz.sighted(None))


def trip(loop: Loop, game: str, area: int) -> None:
    """A trip to town for room from level `area` (runner.py `_loop_stopped`'s room rules): the room package onto the
    agenda's stack (agenda.py `room_package`), with the loop's trip bookkeeping as the Andariel kind's TRIP keeps it
    (`may_trip`, `tripping`, `_back_from_trip`)."""
    loop.trips = loop.trips_in(game) + 1
    loop.trip_due, loop.trip, loop.fortressed = False, game, None
    loop.trip_free, loop.trip_gained, loop.returned = loop.free, None, None
    loop.visiting = loop.visited = None  # a whole visit of its own
    loop.agenda.push(*room_package(area))


def perform(
    loop: Loop,
    run: Run,
    key_names,
    progress: Progress | None,
    goal: Objective,
    tz: TzHands | None,
    visit: Callable[[Exit], object] | None,
) -> None:
    """Make `goal` one leg (the module text); done on the agenda unless it stops (`Abort`: counted, `Agenda.failed`)."""
    agenda = loop.agenda
    packaged = bool(agenda.stack) and agenda.stack[-1] == goal
    try:
        world = run.world()
        game = world.game_name if world.in_game else ''
        player = world.player
        if goal.kind == NEW_GAME:
            loop.next_game(run, world, key_names)
        elif goal.kind == LEAVE_GAME:
            left = tz.sighted(None) if tz is not None else None
            if left is not None and not loop.abandon:
                # Never a game left with a valuable on the ground (the player, 2026-10-17): the room rules, the stop
                raise Abort(f'no goals left, but {left} lies on the ground', cause='room')
            agenda.finish(player.area if player is not None else None)
            loop.leave(run, game)
        elif tz is None or player is None:
            raise Abort('no terror zone hands, or no character read')
        elif goal.kind == WAYPOINT:
            if goal.to is None:
                raise Abort(f'{goal.label}: no level to go to')
            excursion = goal.tier == EXCURSION  # to a zone's waypoint; a package's or an errand's goes town to town
            if excursion:
                own = run.own_teleport() if run.own_teleport is not None else None
                if not own:
                    loop.teleports = teleports(gold(run), gold_cap(run), loop.teleports)
                tz.navigate()
                if loop.prebuffed != game and player.area != ROGUE_ENCAMPMENT:
                    prebuff(run)
                    loop.prebuffed = game
            travel(run, goal.to, loop.marks)
            if excursion and loop.prebuffed != game:
                prebuff(run)  # out of the Rogue Encampment, whose townsfolk Consume cannot take (routines.py TOWN_NPCS)
                loop.prebuffed = game
        elif goal.kind == TOWN_ROUTINE:
            loop.town(run, visit, game, Exit(goal.exit or 'waypoint'))
        elif goal.kind == PORTAL_TO_TOWN:
            if not packaged:
                agenda.finish(player.area)  # the excursion's end: the next one from town
            to_town(run, key_names, None if packaged else tz.take_one)  # a trip for room has no room at the portal
            here = run.world().player
            loop.portal_at = (here.x, here.y) if here is not None else None
        elif goal.kind == THROUGH_PORTAL:
            if loop.tripping(game):
                loop._back_from_trip()
            loop.returned = game
            through_portal(run, loop.portal_at)
        elif goal.kind == LEVEL:
            tz.navigate()
            tz.level_run()  # posts the run and returns: its end is the next leg's
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
            agenda.finish(player.area)
            tz.door()
        else:
            raise Abort(f'the agenda has no leg for {goal.kind}')
    except Abort:
        agenda.failed(goal)
        raise
    agenda.done(goal)


def boss_of(progress: Progress, area: int) -> str:
    """The boss the route fights on level `area` ('' with none)."""
    chosen = progress.chosen(area)
    if chosen is None:
        return ''
    return next((stage.boss for stage in chosen[1].stages if stage.kind == FIGHT), '')


def full_clear(loop: Loop) -> bool:
    """Whether the loop's kind is Full clear TZ (the Herald hunt: every hostile, every room)."""
    return loop.kind == TZ_CLEAR
