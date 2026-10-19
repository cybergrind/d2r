"""The KP_6 loop's terror zone kinds (TZ leveling, Full clear TZ): each leg is one agenda goal (macros/goals-plan.md).

`choose` reads the game into a `tzroutine.GameView`, derives the game-level goals (`tzroutine.produce`) and asks the
agenda for the next one (`Agenda.next`: stack, then queue, then LEAVE_GAME). `perform` makes it one leg with the
existing routines (routines.py, waypoint.py, visit.py, portal.py, pursuit.py via `LegHands.level_run`).
Offered by three presses of KP_6 and restart.py `--kind tz` / `--kind tzclear` while `ENABLED`.
"""

import functools
import math
import time

from inventory_tracking.common import LOG
from inventory_tracking.game.records import World
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
    TZ_LEVEL,
    TZ_LOOT,
    TZ_NEXT_LEVEL,
    TZ_PICKUP,
    TZ_PORTAL,
    TZ_WAYPOINT,
    Dead,
    LegHands,
    Loop,
    teleports,
)
from inventory_tracking.macros.portal import to_town
from inventory_tracking.macros.repair import gold
from inventory_tracking.macros.routines import DEAD
from inventory_tracking.macros.shop import gold_cap
from inventory_tracking.macros.town import Exit
from inventory_tracking.macros.tzroutine import GameView, Itinerary, itinerary, produce
from inventory_tracking.macros.waypoint import travel
from inventory_tracking.routes.model import FIGHT
from inventory_tracking.routes.progress import Progress
from inventory_tracking.routes.tz_groups import installed_active_zones
from inventory_tracking.terror.bosses import KILLED_AT


# False: only the Lower Kurast and Andariel kinds. On since 2026-10-19 (the player: "launch tz-leveling loop after
# then next run and monitor/improve it"); goals-plan.md §9's checks are made live
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


@functools.cache
def zone_levels() -> frozenset[int]:
    """Every level of an installed Terror Zone."""
    return frozenset(area for zone in installed_active_zones() for area in zone.areas)


def leg_of(goal: Objective) -> str:
    """The leg `goal` is made as."""
    return LEGS[goal.kind]


def zone_of(tz: LegHands) -> Itinerary | None:
    """The itinerary of the zone the tracker reads as terrorized now (tzroutine.py `itinerary`)."""
    return itinerary(frozenset(area for area in zone_levels() if tz.terrorized(area)))


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
        # A level two routes share (Burial Grounds: Crypt, then Mausoleum) takes the excursion's script
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
    """A trip to town for room from `area` (runner.py `_loop_stopped`): the room package pushed on the agenda, with
    the loop's trip bookkeeping."""
    loop.begin_trip(game)
    loop.agenda.push(*room_package(area))


def perform(
    loop: Loop,
    run: Run,
    key_names,
    progress: Progress | None,
    goal: Objective,
    tz: LegHands | None,
) -> None:
    """Make `goal` one leg; done on the agenda unless it aborts (`Agenda.failed`)."""
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
                # Never a game left with a valuable on the ground (the player, 2026-10-17)
                raise Abort(f'no goals left, but {left} lies on the ground', cause='room')
            agenda.finish(player.area if player is not None else None)
            loop.leave(run, game)
        elif tz is None or player is None:
            raise Abort('no terror zone hands, or no character read')
        elif goal.kind == WAYPOINT:
            if goal.to is None:
                raise Abort(f'{goal.label}: no level to go to')
            excursion = goal.tier == EXCURSION  # to a zone's waypoint (else town to town)
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
        elif goal.kind == TOWN_ROUTINE:
            loop.town(run, tz.visit, game, Exit(goal.exit or 'waypoint'))
        elif goal.kind == PORTAL_TO_TOWN:
            if not packaged:
                agenda.finish(player.area)  # the excursion's end
            to_town(run, key_names, None if packaged else tz.take_one)  # a trip for room has no room to pick up
            loop.note_portal(run)
        elif goal.kind == THROUGH_PORTAL:
            loop.back_through_portal(run, game)
        elif goal.kind == LEVEL:
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
            agenda.finish(player.area)
            if tz.way_on is None:
                raise Abort(f'{goal.label}: no way on')
            tz.way_on()
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
    return loop.kind.full_clear
