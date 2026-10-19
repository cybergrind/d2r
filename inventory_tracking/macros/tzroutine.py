"""The Terror Zone leveling routine: the game-level goals of any terror zone (macros/goals-plan.md §4, §6). "End goal
on the level depends on the level itself"; "levels with bosses we end with killing the boss" (the player, 2026-10-19).

- `itinerary`: the active zone (routes/tz_groups.py) covered by catalogue excursions from waypoints
  (routes/tz_routes.py `zone_route_plan`); an excursion with a blocked hop, or an area none covers, is skipped and said.
- `policy_of`: how an area is worked (agenda.py COVER / ON_THE_WAY / FULL_CLEAR).
- `produce`: the goals wanted now, derived afresh from a `GameView` at every leg so nothing goes stale.

Pure: macros/tzloop.py reads the views.
"""

import functools
from collections.abc import Iterable
from dataclasses import dataclass

from inventory_tracking.common import LOG
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
    ON_THE_WAY,
    ONWARD,
    PANDEMONIUM_FORTRESS,
    PICKUP,
    PORTAL_TO_TOWN,
    SIGHTED,
    TOWN_ROUTINE,
    WAYPOINT,
    WORK,
    Objective,
)
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.model import ENTER, FIGHT, LOOT as LOOT_STAGE, STAND, USE
from inventory_tracking.routes.tz_groups import match_active_zone
from inventory_tracking.routes.tz_routes import zone_route_plan


# Self-ended level runs of one area after which it counts as worked whatever its stage ("the loop never stands",
# the player, 2026-10-18)
RUNS_AN_AREA = 4
# Per-area policy overrides (goals-plan.md §6, open question 1)
POLICY: dict[int, str] = {}
# The route stages a level run performs: an area at one of them is still a level's work
WORKED_BY_RUNS = frozenset((FIGHT, USE, STAND))


@dataclass(frozen=True)
class Excursion:
    """One waypoint's trip: `areas` from the waypoint on; `zone` the terrorized ones worked, the rest crossed."""

    route: str
    waypoint: int
    areas: tuple[int, ...]
    zone: frozenset[int]

    def after(self, area: int) -> int | None:
        """The level after `area` on the excursion; None at its end (or off it)."""
        if area not in self.areas:
            return None
        index = self.areas.index(area)
        return self.areas[index + 1] if index + 1 < len(self.areas) else None

    @property
    def terminal(self) -> int:
        return self.areas[-1]


@dataclass(frozen=True)
class Itinerary:
    """The active zone's plan: its levels, excursions in order, and what is skipped and why."""

    zone: str
    areas: frozenset[int]
    excursions: tuple[Excursion, ...]
    skipped: tuple[tuple[int, str], ...] = ()

    def excursion_of(self, area: int, finished: Iterable[int]) -> Excursion | None:
        """The first unfinished excursion (terminal not in `finished`) that has `area`."""
        done = set(finished)
        return next((trip for trip in self.excursions if area in trip.areas and trip.terminal not in done), None)

    def next_excursion(self, finished: Iterable[int]) -> Excursion | None:
        """The first excursion not over."""
        done = set(finished)
        return next((trip for trip in self.excursions if trip.terminal not in done), None)


@functools.cache
def itinerary(terrorized: frozenset[int]) -> Itinerary | None:
    """The itinerary of the zone whose levels are `terrorized`; None when no installed zone matches."""
    zone = match_active_zone(terrorized)
    if zone is None:
        return None
    plan = zone_route_plan(zone)
    group = frozenset(zone.areas)
    trips, skipped = [], [(area, 'no catalogue excursion covers it') for area in plan.uncovered]
    for trip in plan.excursions:
        if trip.blockers:
            skipped += [(area, trip.blockers[0]) for area in trip.covers]
            continue
        nodes = (trip.waypoint, *(hop.destination for hop in trip.hops))
        trips.append(Excursion(trip.route, trip.waypoint, nodes, group & frozenset(nodes)))
    covered = set().union(*(trip.zone for trip in trips)) if trips else set()
    skipped = [(area, why) for area, why in dict(skipped).items() if area not in covered]
    found = Itinerary(zone.name, group, tuple(trips), tuple(sorted(skipped)))
    LOG.info(
        'Macro: tz: zone %s: %s; skipped %s',
        zone.name,
        '; '.join(f'{trip.route} from {trip.waypoint}: {list(trip.areas)}' for trip in trips) or 'no excursion',
        [f'{area} ({why})' for area, why in found.skipped] or 'none',
    )
    return found


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


def policy_of(area: int, trip: Excursion | None, full_clear: bool = False) -> str:
    """How `area` is worked (goals-plan.md §6): FULL_CLEAR for the Full clear TZ kind; ON_THE_WAY on an excursion
    still heading to a boss ("finding each elite on the way to Andariel, kill her and start a new game"); else COVER."""
    if full_clear:
        return FULL_CLEAR
    if area in POLICY:
        return POLICY[area]
    if trip is None or area not in trip.areas:
        return COVER
    bosses = boss_areas(trip.route)
    ahead = trip.areas[trip.areas.index(area) :]
    return ON_THE_WAY if any(level in bosses for level in ahead) else COVER


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
        return [Objective(WAYPOINT, f'to {display_name(trip.waypoint)} ({trip.route})', EXCURSION, to=trip.waypoint)]
    goals: list[Objective] = []
    if view.sighted is not None:
        goals.append(Objective(PICKUP, f'{view.sighted}, still on the ground', SIGHTED, area))
    trip = plan.excursion_of(area, view.finished)
    if trip is None:
        return goals  # off the itinerary (a level the player went to): nothing more of the zone's here
    runs = dict(view.worked).get(area, 0)
    zoned = area in trip.zone
    if zoned and runs < RUNS_AN_AREA and (runs == 0 or view.stage in WORKED_BY_RUNS):
        goals.append(Objective(LEVEL, f'the {display_name(area)} run', WORK, area))
    elif zoned and view.stage == LOOT_STAGE:
        goals.append(Objective(LOOT, f'the loot of {display_name(area)}', LOOTING, area))
    else:
        onward = trip.after(area)
        if onward is not None and (view.stage != ENTER or view.stage_to in (0, onward)):
            goals.append(Objective(NEXT_LEVEL, f'on into {display_name(onward)}', ONWARD, area, to=onward))
        elif plan.next_excursion(view.finished | {trip.terminal}) is not None:
            goals.append(Objective(PORTAL_TO_TOWN, 'Town Portal for the next excursion', EXCURSION, area))
    return goals
