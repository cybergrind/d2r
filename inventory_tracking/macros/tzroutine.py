"""The Terror Zone leveling routine: the game-level goals of any terror zone (macros/goals-plan.md §4, §6). "End goal
on the level depends on the level itself"; "levels with bosses we end with killing the boss" (the player, 2026-10-19).

- `itinerary`: the active zones (routes/tz_groups.py `match_zones`: an act a Worldstone Shard terrorized first, its
  boss's trip first, then the rotation) covered by catalogue excursions from waypoints (routes/tz_routes.py
  `zone_route_plan`); an excursion with a blocked hop, or an area none covers, is skipped and said.
- `policy_of`: how an area is worked (agenda.py COVER / ON_THE_WAY / FULL_CLEAR); `kept_to`: a script held to its trip.
- `produce`: the goals wanted now, derived afresh from a `GameView` at every leg so nothing goes stale.
- A tour (routes/model.py `tour`: the Canyon of the Magi's seven tombs) is one excursion: the hub's run, then each
  toured level by the nearest entrance not yet entered, worked and left by its way back to the hub, until every one is
  done (`Excursion.onward`; macros/tzloop.py `tour_back` marks a toured level done once the hub is stood in again).

Pure: macros/tzloop.py reads the views.
"""

import functools
from collections.abc import Iterable
from dataclasses import dataclass, replace

from inventory_tracking.common import LOG
from inventory_tracking.levels.presets import display_name, numbered_name
from inventory_tracking.macros.agenda import (
    BIG_LEVEL,
    COVER,
    ERRAND,
    EXCURSION,
    FULL_CLEAR,
    LEVEL,
    LOOT,
    LOOTING,
    NEXT_LEVEL,
    ON_THE_WAY,
    ONWARD,
    PANDEMONIUM_FORTRESS,
    PICKUP,
    PLUS,
    PLUS_WAY,
    PORTAL_TO_TOWN,
    SIGHTED,
    TOWN_ROUTINE,
    TOWNS,
    TRANSIT,
    WALK_OUT,
    WAYPOINT,
    WORK,
    Objective,
)
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.model import ENTER, FIGHT, LOOT as LOOT_STAGE, STAND, USE, Script
from inventory_tracking.routes.tz_groups import ActiveZone, act_of_manual, match_active_zone, match_zones
from inventory_tracking.routes.tz_routes import RouteExcursion, zone_route_plan
from inventory_tracking.terror.zones import level_population


# Self-ended level runs of one area after which it counts as worked whatever its stage ("the loop never stands",
# the player, 2026-10-18)
RUNS_AN_AREA = 4
# Self-ended runs of a tour's hub a toured level may take (the run to the next entrance, one more): past them the tour
# ends, never a stuck tour. The hub's first run is its own
RUNS_A_TOURED_LEVEL = 2
# Per-area policy overrides (goals-plan.md §6, open question 1)
POLICY: dict[int, str] = {}
# TZ+ (agenda.py PLUS): the TZ leveling kind's default from 2026-10-20. The player, ~18:50: "let's add another mode
# TZ+: it tries to kill slightly more mobs on levels with not so many mobs to get herald spawn ... TZ+ is default TZ
# mode from now". Every terrorized level under BIG_LEVEL is explored and its reasonable groups taken, the levels on the
# way to a boss too: under ON_THE_WAY they were left at the way on with half their rooms unseen (Outer Steppes,
# Plains of Despair, Dry Hills; rca/2026-10-20/tz-level-leave-findings.md). False: TZ leveling as before (COVER /
# ON_THE_WAY, leaders only).
TZ_PLUS = True
# The route stages a level run performs: an area at one of them is still a level's work
WORKED_BY_RUNS = frozenset((FIGHT, USE, STAND))


# A route's excursion begun at a later waypoint of its own, the levels before it left out. Andariel from Catacombs 2:
# Inner Cloister and the Cathedral have no level handler (no card mark for the way on), and every game ended in Inner
# Cloister (08:22-08:25 on 2026-10-20). The player, 2026-10-20 ~08:24: "there are 2 options: inner cloister ->
# cathedral -> catacombs level -> kill andy / or cat2 -> cat 3 -> cat 4 -> andy"
START_AT = {'Andariel': 35}
# A whole act terrorized (a Worldstone Shard's, routes/tz_groups.py `match_zones`) is planned with the rotation in one
# itinerary, the act first. The player, 2026-10-20 ~19:00: "for TZ/TZ+ modes we want to know how to handle whole
# terrorized act (when we terrorized it manually with stone)": before, the act matched no single zone and the loop
# stopped ("no terror zone is read in this game"). False: one rotating zone only, as before
MANUAL_ZONES = True
# A terrorized act's boss trip first (the player, ~18:50: "we want to kill act boss first for possible statue drop"):
# the act's boss level (rca/2026-10-20/act-terrorize-findings.md §5, the installed manual zones): Andariel on Catacombs
# Level 4, Duriel's Lair, Durance of Hate Level 3, the Chaos Sanctuary, the Worldstone Chamber. False: the act's
# excursions in `zone_route_plan`'s order
BOSS_FIRST = True
ACT_BOSS_LEVELS = {1: 37, 2: 73, 3: 102, 4: 108, 5: 132}


@dataclass(frozen=True)
class Excursion:
    """One waypoint's trip: `areas` from the waypoint on; `zone` the terrorized ones worked, the rest crossed.
    `hub`, `tours`: a tour's level and the levels its marks lead into, one by one (routes/model.py `tour`), each left
    by its way back to the hub; the trip is over once each is done (`ends`). The player, 00:45 on 2026-10-18: "for
    canyon of the magi loop: we should go through every tomb one by one"; "Canyon first, then tombs"."""

    route: str
    waypoint: int
    areas: tuple[int, ...]
    zone: frozenset[int]
    hub: int | None = None
    tours: tuple[int, ...] = ()

    def after(self, area: int) -> int | None:
        """The level after `area` on the excursion; None at its end (or off it)."""
        if area not in self.areas:
            return None
        index = self.areas.index(area)
        return self.areas[index + 1] if index + 1 < len(self.areas) else None

    def onward(self, area: int, finished: Iterable[int]) -> int | None:
        """The level `area` goes on into: from a tour's hub the first toured level not done (which one the press
        enters is the tour's: the nearest entrance not yet entered), from a toured level the hub while another is left
        (None after the last: the game ends there); else `after`."""
        done = set(finished)
        if self.tours and area == self.hub:
            return next((level for level in self.tours if level not in done), None)
        if area in self.tours:
            return self.hub if any(level not in done for level in self.tours if level != area) else None
        return self.after(area)

    def touring(self, area: int) -> bool:
        """Whether `area` is the tour's hub or one of its levels: done only when left for good (`ends`)."""
        return bool(self.tours) and (area == self.hub or area in self.tours)

    @property
    def terminal(self) -> int:
        return self.areas[-1]

    @property
    def ends(self) -> frozenset[int]:
        """The levels whose being done ends the excursion: each toured level, else the terminal."""
        return frozenset(self.tours) if self.tours else frozenset((self.terminal,))

    def over(self, finished: Iterable[int]) -> bool:
        return self.ends <= set(finished)


@dataclass(frozen=True)
class Itinerary:
    """The active zone's plan: its levels, excursions in order, and what is skipped and why."""

    zone: str
    areas: frozenset[int]
    excursions: tuple[Excursion, ...]
    skipped: tuple[tuple[int, str], ...] = ()

    def excursion_of(self, area: int, finished: Iterable[int]) -> Excursion | None:
        """The first unfinished excursion (`Excursion.over`: its terminal, or each toured level, not in `finished`)
        that has `area`."""
        done = set(finished)
        return next((trip for trip in self.excursions if area in trip.areas and not trip.over(done)), None)

    def next_excursion(self, finished: Iterable[int]) -> Excursion | None:
        """The first excursion not over."""
        done = set(finished)
        return next((trip for trip in self.excursions if not trip.over(done)), None)

    def touring(self, area: int, finished: Iterable[int]) -> bool:
        """Whether `area` is on the tour of the excursion under way (`Excursion.touring`): not done as it is left."""
        trip = self.excursion_of(area, finished)
        return trip is not None and trip.touring(area)


@functools.cache
def itinerary(terrorized: frozenset[int]) -> Itinerary | None:
    """The itinerary of the zones whose levels are `terrorized` (`MANUAL_ZONES`: routes/tz_groups.py `match_zones`, a
    terrorized act first, its boss's trip first; else the one rotating zone); None when no installed zone matches."""
    if MANUAL_ZONES:
        zones = match_zones(terrorized)
    else:
        zone = match_active_zone(terrorized)
        zones = (zone,) if zone is not None else ()
    if not zones:
        return None
    group = frozenset(area for zone in zones for area in zone.areas)
    trips: list[Excursion] = []
    skipped: list[tuple[int, str]] = []
    for zone in zones:
        before = set().union(*(trip.zone for trip in trips)) if trips else set()
        found_trips, uncovered = _route_trips(zone)
        skipped += [(area, 'no catalogue excursion covers it') for area in uncovered]
        for found in found_trips:
            if found.blockers:
                skipped += [(area, found.blockers[0]) for area in found.covers]
                continue
            trip = _excursion(found, group, skipped)
            if before and trip.zone <= before:
                continue  # another zone's trips cover its levels already (the union's, never one zone's own)
            trips.append(trip)
    covered = set().union(*(trip.zone for trip in trips)) if trips else set()
    skipped = [(area, why) for area, why in dict(skipped).items() if area not in covered]
    name = ' + '.join(zone.name for zone in zones)
    found = Itinerary(name, group, tuple(trips), tuple(sorted(skipped)))
    stray = sorted(terrorized - group)
    LOG.info(
        'Macro: tz: zone %s: %s; skipped %s%s',
        name,
        '; '.join(
            f'{trip.route} from {trip.waypoint}: {list(trip.areas)}'
            + (f', {list(trip.tours)} a tour from {trip.hub} one by one' if trip.tours else '')
            for trip in trips
        )
        or 'no excursion',
        [f'{area} ({why})' for area, why in found.skipped] or 'none',
        f'; read terrorized in no zone: {stray}' if stray else '',
    )
    return found


def _route_trips(zone: ActiveZone) -> tuple[tuple[RouteExcursion, ...], tuple[int, ...]]:
    """The catalogue's trips covering `zone` (routes/tz_routes.py `zone_route_plan`) and the levels none covers. A
    terrorized act's (`BOSS_FIRST`): the trip to its boss first, then the trips of its levels that trip does not
    reach."""
    plan = zone_route_plan(zone)
    act = act_of_manual(zone)
    boss = ACT_BOSS_LEVELS.get(act) if act is not None and BOSS_FIRST else None
    first = next(
        (trip for trip in plan.excursions if not trip.blockers and boss in (trip.waypoint, *_nodes(trip))), None
    )
    if first is None:
        return plan.excursions, plan.uncovered
    reached = set(_nodes(first)) | {first.waypoint}
    start = START_AT.get(first.route)
    if start is not None and start in _nodes(first):
        reached = set(_nodes(first)[_nodes(first).index(start) :])  # the levels before its start are another trip's
    areas = tuple(area for area in zone.areas if area not in reached)
    if not areas or not zone.core - reached:
        return (first,), ()
    rest = zone_route_plan(replace(zone, areas=areas, core=zone.core - reached, unreported=()))
    return (first, *rest.excursions), rest.uncovered


def _nodes(trip: RouteExcursion) -> tuple[int, ...]:
    """The levels of catalogue trip `trip`: its waypoint, then each hop's destination."""
    return (trip.waypoint, *(hop.destination for hop in trip.hops))


def _excursion(trip: RouteExcursion, group: frozenset[int], skipped: list[tuple[int, str]]) -> Excursion:
    """Catalogue trip `trip` as an excursion over the terrorized `group` (`START_AT` cuts its start: those levels are
    added to `skipped`)."""
    nodes = _nodes(trip)
    start = START_AT.get(trip.route)
    if start is not None and start in nodes[1:]:
        skipped += [(area, f'the {trip.route} trip starts at waypoint {start}') for area in nodes[: nodes.index(start)]]
        nodes = nodes[nodes.index(start) :]
    toured = [hop for hop in trip.hops if hop.kind == 'tour']
    hub = toured[0].source if toured else None
    tours = tuple(hop.destination for hop in toured)
    return Excursion(trip.route, nodes[0], nodes, group & frozenset(nodes), hub, tours)


@functools.cache
def boss_areas(route: str) -> frozenset[int]:
    """The levels of route `route` whose script fights a boss."""
    return frozenset(
        script.area
        for found in ROUTES
        if found.name == route
        for script in found.scripts
        if any(stage.kind == FIGHT for stage in script.stages)
    )


@functools.cache
def stand_areas(route: str) -> frozenset[int]:
    """The levels of route `route` whose script stands for what comes (Durance 3's Mephisto, the Throne's waves)."""
    return frozenset(
        script.area
        for found in ROUTES
        if found.name == route
        for script in found.scripts
        if any(stage.kind == STAND for stage in script.stages)
    )


def policy_of(area: int, trip: Excursion | None, full_clear: bool = False, plus: bool | None = None) -> str:
    """How `area` is worked (goals-plan.md §6): TRANSIT on a level of no excursion under way or not terrorized on it
    (crossed), for both kinds ("when we're running tz leveling loop - it should run within terror zones", the player,
    2026-10-19 ~21:56); FULL_CLEAR for the Full clear TZ kind. TZ leveling with `plus` (default TZ_PLUS): PLUS on a
    level under BIG_LEVEL, PLUS_WAY on one whose script stands (`stand_areas`); on a big level PLUS_WAY on the way to a
    boss, else PLUS (its big groups only, agenda.py BIG_GROUP). Without: ON_THE_WAY on an excursion still heading to a
    boss ("finding each elite on the way to Andariel, kill her and start a new game"); else COVER."""
    if trip is None or area not in trip.zone:
        return TRANSIT
    if full_clear:
        return FULL_CLEAR
    if area in POLICY:
        return POLICY[area]
    bosses = boss_areas(trip.route)
    ahead = trip.areas[trip.areas.index(area) :]
    on_the_way = any(level in bosses for level in ahead)
    if not (TZ_PLUS if plus is None else plus):
        return ON_THE_WAY if on_the_way else COVER
    population = level_population(area)
    if population is not None and population >= BIG_LEVEL:
        return PLUS_WAY if on_the_way else PLUS
    return PLUS_WAY if area in stand_areas(trip.route) else PLUS


def kept_to(script: Script, trip: Excursion) -> Script:
    """`script` held to `trip` ("it should run within terror zones", the player, 2026-10-19 ~21:56): on a level not
    terrorized on it (crossed, or off it) only the way on to the trip's next level (no boss: Travincal's Council on the
    Durance trip); on a terrorized one no way into a level off the trip. An agenda run walks an open passage and goes
    on in the level it leads into (pursuit.py `carried`): the River of Flame's run explored the non-terror Chaos
    Sanctuary, its seals and Diablo too (game 30, 21:51-21:55; tz-coverage-findings.md F5). The level's run then ends
    by itself (no route stage left). A route's own way to a town (Durance 3's Red portal) and a pending way (the act 5
    red portals: no run performs it) are kept. `script` itself when nothing is cut."""
    area = script.area
    if area not in trip.zone:
        onward = trip.after(area)
        kept = tuple(stage for stage in script.stages if onward is not None and stage.to == onward)
    else:
        kept = tuple(
            stage for stage in script.stages if not (stage.kind == ENTER and stage.to and stage.to not in trip.areas)
        )
    return script if len(kept) == len(script.stages) else replace(script, stages=kept)


@dataclass(frozen=True)
class GameView:
    """The facts `produce` reads. `stage`, `stage_to`: the route's stage kind at `area` and where it leads
    (routes/progress.py `step`); `worked`: self-ended level runs per area; `finished`: areas done; `sighted`: a
    valuable still on the ground here; `visit_due`: the town visit is wanted."""

    area: int
    in_town: bool
    itinerary: Itinerary | None
    stage: str | None = None
    stage_to: int = 0
    worked: tuple[tuple[int, int], ...] = ()
    finished: frozenset[int] = frozenset()
    sighted: str | None = None
    visit_due: bool = False


def produce(view: GameView) -> list[Objective]:
    """The game-level goals wanted now (goals-plan.md §3); empty means LEAVE_GAME next."""
    plan, area = view.itinerary, view.area
    if plan is None:
        return []
    if view.in_town:
        if view.visit_due:
            if area != PANDEMONIUM_FORTRESS:
                return [Objective(WAYPOINT, 'to the Fortress for the visit', ERRAND, to=PANDEMONIUM_FORTRESS)]
            return [Objective(TOWN_ROUTINE, 'the town visit', ERRAND, exit='waypoint')]
        trip = plan.next_excursion(view.finished)
        if trip is None:
            return []
        onward = trip.after(area) if trip.waypoint == area else None
        if onward is not None:
            # The trip starts in this town and leaves it on foot (Blood Moor, Rocky Waste, Outer Steppes: no waypoint):
            # a waypoint to the town it stands in was the goal before (rca/2026-10-19/town-exit-findings.md)
            label = f'out of {display_name(area)} into {display_name(onward)}'
            return [Objective(WALK_OUT, label, EXCURSION, area, to=onward)]
        return [Objective(WAYPOINT, f'to {display_name(trip.waypoint)} ({trip.route})', EXCURSION, to=trip.waypoint)]
    goals: list[Objective] = []
    if view.sighted is not None:
        goals.append(Objective(PICKUP, f'{view.sighted}, still on the ground', SIGHTED, area))
    trip = plan.excursion_of(area, view.finished)
    if trip is None:
        return goals  # off the itinerary (a level the player went to): nothing more of the zone's here
    runs = dict(view.worked).get(area, 0)
    zoned = area in trip.zone
    onward = trip.onward(area, view.finished)
    if area in trip.tours and area in view.finished:
        # A toured level done and entered again (its entrance not seen gone through: macros/route.py `note_toured`):
        # no level twice in a game, and no way back to an entrance the tour still leads to: the game ends here
        return goals
    if area == trip.hub and runs > 1 + RUNS_A_TOURED_LEVEL * len(trip.tours):
        onward = None  # the tour's runs spent: it ends, never a stuck tour
    if view.stage == USE and view.stage_to in TOWNS and view.stage_to != onward:
        # A route's own way to a town leaves the excursion: no level work, the excursion's end (no Town Portal spent).
        # As a level run, Durance 3's Red portal took the run to the Fortress with the trip unfinished, and the trip
        # was made again (2026-10-19, rca/2026-10-19/tz-coverage-findings.md F4). Pending ways (the act 5 red portals)
        # are not performed by a run, and stay the level's work.
        label = f'to {display_name(view.stage_to)} by the route: the excursion ends'
        goals.append(Objective(LEVEL, label, WORK, area, to=view.stage_to))
    elif zoned and runs < RUNS_AN_AREA and (runs == 0 or view.stage in WORKED_BY_RUNS):
        goals.append(Objective(LEVEL, f'the {numbered_name(area)} run{toured(trip, area, view.finished)}', WORK, area))
    elif zoned and view.stage == LOOT_STAGE:
        # (A crossed level's loot is none: its script is its way on only, `kept_to`; Travincal's Council on the Durance
        # trip left its loot stage and spun "next level" 30 times, F3)
        goals.append(Objective(LOOT, f'the loot of {display_name(area)}', LOOTING, area))
    elif onward is not None and area == trip.hub and trip.tours:
        # Which level the press enters is the tour's (the nearest entrance not yet entered): no level named ahead
        left = sum(1 for level in trip.tours if level not in view.finished)
        label = f'on into the nearest {display_name(onward)} not entered ({left} of {len(trip.tours)} left)'
        goals.append(Objective(NEXT_LEVEL, label, ONWARD, area))
    elif onward is not None and (view.stage != ENTER or view.stage_to in (0, onward)):
        goals.append(Objective(NEXT_LEVEL, f'on into {display_name(onward)}', ONWARD, area, to=onward))
    elif plan.next_excursion(view.finished | trip.ends) is not None:
        goals.append(Objective(PORTAL_TO_TOWN, 'Town Portal for the next excursion', EXCURSION, area))
    return goals


def toured(trip: Excursion, area: int, finished: frozenset[int]) -> str:
    """' (tomb N of 7)' for a toured level of `trip`, by the levels done before it; '' for any other."""
    if area not in trip.tours:
        return ''
    done = sum(1 for level in trip.tours if level in finished)
    return f' (toured level {done + 1} of {len(trip.tours)})'
