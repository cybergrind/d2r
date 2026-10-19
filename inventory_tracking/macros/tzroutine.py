"""The Terror Zone leveling routine: the game-level goals of a terror zone, for any zone (macros/goals-plan.md §4, §6).

The player, 2026-10-19: "this system with priorities will allow us to implement a generic TZ leveling loop: end goal
on the level depends on the level itself. Some levels just have one location - so we need just explore this location.
Other locations can have complex goals: TZ-Leveling explore routine -> go next level"; "levels with bosses we end with
killing the boss"; "some levels already have their goals (like killing diablo/baal). And TZLeveling will just add
another goal, before boss kill or navigating to the next level".

- `itinerary`: the active zone, matched from the levels the client lists as terrorized (routes/tz_groups.py), covered
  by catalogue excursions from waypoints (routes/tz_routes.py `zone_route_plan`, Codex's): waypoint -> its hops ->
  its terminal. An excursion with a blocked hop (a pending stage, a town connector with no stage, a tomb tour) is
  skipped and said, as is an area no excursion covers.
- `policy_of`: how an area is worked (agenda.py COVER / ON_THE_WAY / FULL_CLEAR).
- `produce`: the game-level goals wanted now (goals-plan.md §3), from a `GameView` of the facts: derived afresh at
  every leg, so a restart, a recovery or the player's hand leave nothing stale.

Pure: the views are read by macros/tzloop.py.
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


# Level runs of one area a game that end by themselves before it is taken as worked whatever its route's stage (a
# boss no run found, an object no run reached): the loop goes on rather than standing (the player, 2026-10-18: "the
# loop never stands")
RUNS_AN_AREA = 4
# Per-area overrides of the policy (goals-plan.md §6; open question 1): none yet, by the player's rulings
POLICY: dict[int, str] = {}
# The route stages a level run performs: an area at one of them is still a level's work
WORKED_BY_RUNS = frozenset((FIGHT, USE, STAND))


@dataclass(frozen=True)
class Excursion:
    """One waypoint's trip through the zone: the levels from the waypoint's on (`areas`), of which `zone` are the
    terrorized ones worked; the rest are crossed."""

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
    """The game's plan for the active zone: its name and levels, its excursions in order, what is skipped and why."""

    zone: str
    areas: frozenset[int]
    excursions: tuple[Excursion, ...]
    skipped: tuple[tuple[int, str], ...] = ()

    def excursion_of(self, area: int, finished: Iterable[int]) -> Excursion | None:
        """The excursion level `area` is on now: the first not over (`finished` holds its terminal) that has it."""
        done = set(finished)
        return next((trip for trip in self.excursions if area in trip.areas and trip.terminal not in done), None)

    def next_excursion(self, finished: Iterable[int]) -> Excursion | None:
        """The first excursion not over."""
        done = set(finished)
        return next((trip for trip in self.excursions if trip.terminal not in done), None)


@functools.cache
def itinerary(terrorized: frozenset[int]) -> Itinerary | None:
    """The itinerary of the zone whose levels are `terrorized` (the module text); None: no installed zone matches."""
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
    """How level `area` is worked (goals-plan.md §6): FULL_CLEAR for the Full clear TZ kind (Herald hunting); else
    ON_THE_WAY for a level whose excursion goes on to a boss's level, and for that level itself (the player's
    Catacombs: "we're finding each elite on the way to Andariel, kill her and start a new game"); COVER elsewhere,
    a level no route knows among them (explore to coverage, every leader found, nearest first)."""
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
    """The facts `produce` derives the game-level goals from (macros/tzloop.py reads them). `stage`, `stage_to`: the
    route's stage kind at `area` and the level it leads into (routes/progress.py `step`); `worked`: the level runs of
    each area that ended by themselves; `finished`: the areas left done; `sighted`: a valuable seen in `area` still on
    the ground (macros/sightings.py); `visit_due`: the town visit is wanted (macros/loop.py `visit_due`)."""

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
    """The game-level goals wanted now (goals-plan.md §3). Empty: none, and the agenda's next is LEAVE_GAME."""
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
