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

from inventory_tracking.common import LOG
from inventory_tracking.game.records import World
from inventory_tracking.levels.presets import display_name
from inventory_tracking.macros.actuator import Abort
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
from inventory_tracking.macros.town import Exit
from inventory_tracking.macros.tzroutine import Excursion, GameView, Itinerary, itinerary, kept_to, produce
from inventory_tracking.macros.visit import Remembered
from inventory_tracking.macros.waypoint import travel
from inventory_tracking.routes.model import FIGHT, Script
from inventory_tracking.routes.progress import Progress
from inventory_tracking.routes.tz_groups import installed_active_zones
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
    WALK_OUT: TZ_OUT,
    LEAVE_GAME: LEAVE,
    # The Gheed's swap in Andariel's words (loop.py), for the watch tools (andy.py SWAP_LEGS)
    SWAP_AWAY: SWAP_OUT,
    SWAP_PARK: GHEED_STASH,
    SWAP_PICK: GHEED_PICK,
    SWAP_HOME: SWAP_BACK,
    SWAP_CHOOSE: GHEED_CHOOSE,
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
    if agenda.begin(loop.game_id or world.game_name):
        loop.idle += 1
        if loop.idle > IDLE_GAMES:
            loop.idle = 0  # turned on again, the loop counts afresh
            raise Abort(f'{IDLE_GAMES} games in a row with no level run: nothing to play', cause='idle')
    if (fetch := fetch_gheeds(world, loop)) is not None:
        return fetch
    if loop.abandon:
        # Left where it stands, in act 3 too: a recovery's way out is the quickest (no portal under what stopped it)
        return Objective(LEAVE_GAME, 'the game given up (a recovery)', STACK)
    if loop.agenda.holds(SWAP_GOALS):
        # The swap's package needs no zone read: the player's Gheed's Fortune is never left on its way
        top = loop.agenda.package()
        assert top is not None
        return top
    plan = zone_of(tz)
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
    game, area = world.game_name, player.area
    trip = plan.excursion_of(area, agenda.finished)
    if trip is not None and progress is not None:
        select(progress, game, area, trip, plan)
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
    # No goals left in act 3: the way to the Fortress, its game ended there (agenda.py `game_end`): Durance 3's Red
    # portal with Mephisto dead, tried once (a level done is not gone through it again: the Town Portal home instead)
    dead = progress.dead() if progress is not None and progress.dead is not None else frozenset()
    dead = dead if area not in agenda.finished else frozenset()
    return agenda.next((player.x, player.y), valuable=tz.sighted(None), area=area, dead=dead)


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
    if kept is script:
        return
    progress.selected[area] = (route, kept)  # this game's only (`Progress.note` clears it)
    if before != (route, kept):
        cut = [stage.text() for stage in script.stages if stage not in kept.stages]
        LOG.info('Macro: tz: %s: %s not taken: off the terror zone (the trip goes on by %s)', display_name(area),
                 ', '.join(cut), ', '.join(stage.text() for stage in kept.stages) or "the level's run")  # fmt: skip


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
        elif goal.kind == TOWN_ROUTINE:
            exit = Exit(goal.exit or 'waypoint')
            if exit == Exit.WAYPOINT and loop.done == game:
                exit = Exit.LEAVE  # the game ends here: no walk to the waypoint (loop.py `exit_of`)
            loop.town(run, tz.visit, game, exit)
        elif goal.kind == PORTAL_TO_TOWN:
            if goal.ends and (left := loop.last_look(run, tz)) is not None:
                raise Abort(f'the game ends, but {left} lies on the ground', cause='room')  # as LEAVE_GAME's
            if not packaged:
                loop.settle(run)  # the portal's pickup (`to_town`) after a boss's drops landed
            if not packaged:
                agenda.finish(player.area)  # the excursion's end
            to_town(run, key_names, None if packaged else tz.take_one)  # a trip for room has no room to pick up
            loop.note_portal(run)
        elif goal.kind == THROUGH_PORTAL:
            loop.back_through_portal(run, game)
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
