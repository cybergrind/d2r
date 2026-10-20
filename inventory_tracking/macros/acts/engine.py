"""The act script engine: a terrorized act's ordered steps (an `ActScript`, one file per act: macros/acts/act<N>.py)
turned into the catalogue trips `tzroutine.itinerary` plays (routes/act-terrorize-plan.md §11). The player, 2026-10-20
~22:50: "we probably can separate some high level architecture into reusable framework, that will allow some
specialization and concrete points/steps to scripting".

- `Trip`: a catalogue route's trip to a target level (the boss's), from a waypoint or the route's nearest one; the
  levels crossed on the way worked right after it (`AFTER`, nearest the target first) or on the way (`WORKED`).
- `Rest`: the levels of a list, a rotating zone or a route's scripts that no earlier step works.
- After the steps, always: the rest of the act's levels (`zone_route_plan`), then the rotation (`itinerary`'s union).
- A step the catalogue cannot play (no route, no path, a pending stage, or marked `missing`) is skipped and said
  (`Macro: act: act N step K (<label>): <why>: skipped`); its levels fall to the later steps or the itinerary's skipped.
- Any object with `label` and `plan(ActPlan)` is a step: an act file may define its own (`ActPlan.add`, `rest`,
  `skip`, `route_trip`), never editing this module.

Pure: the catalogue and the installed zone table only. Reuses routes/tz_routes.py and macros/tzroutine.py.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from typing import Literal, Protocol

from inventory_tracking.common import LOG
from inventory_tracking.macros.tzroutine import START_AT, Trips, crossed_levels, trip_levels
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.tz_groups import ActiveZone, installed_active_zones
from inventory_tracking.routes.tz_routes import RouteExcursion, route_excursion, zone_route_plan


# How a trip's levels on the way to its target are worked: AFTER only crossed (agenda.py ON_THE_WAY), each with its
# own trip right after the target, nearest it first (the player, 2026-10-20 ~21:27: "river of flame -> CS -> kill
# diablo -> do rest of flame river"); WORKED on the way (the player's "catacombs 2 -> 3 -> 4 -> andariel")
AFTER, WORKED = 'after', 'worked'
Crossed = Literal['after', 'worked']


class Step(Protocol):
    """One point of an act's order: `plan` adds its trips to the act's plan (or skips, said)."""

    @property
    def label(self) -> str: ...

    def plan(self, act: ActPlan) -> None: ...


@dataclass(frozen=True)
class ActScript:
    """Act `act`'s order: `steps`, then the act's other levels, then the rotation. `ready`: its kind is offered
    (loop.py `loop_kinds`) and its order played (tzroutine.py `_scripted`); before, the generic boss-first order."""

    act: int
    steps: tuple[Step, ...] = ()
    ready: bool = False


@dataclass(frozen=True)
class Trip:
    """Route `route`'s trip to level `target` (its boss's), from `waypoint` (None: the route's waypoint nearest it).
    `crossed`: AFTER or WORKED (above). `missing`: why the catalogue cannot play it yet (the route to add); skipped."""

    route: str
    target: int
    waypoint: int | None = None
    crossed: Crossed = AFTER
    missing: str = ''

    @property
    def label(self) -> str:
        start = f' from {self.waypoint}' if self.waypoint is not None else ''
        return f'{self.route} to {self.target}{start}'

    def plan(self, act: ActPlan) -> None:
        if self.missing:
            act.skip(self, self.missing)
            return
        trip = act.route_trip(self.route, self.target, self.waypoint)
        if trip is None:
            return  # said by `route_trip`
        if trip.blockers:
            act.skip(self, trip.blockers[0])
            act.add(trip)  # its levels are the itinerary's skipped, with the blocker, unless a later step covers them
            return
        passes = crossed_levels(trip, self.target, act.zone) if self.crossed == AFTER else ()
        act.add(trip, frozenset(passes))
        act.rest(passes, f'the levels {self.route} crossed')


@dataclass(frozen=True)
class Rest:
    """The levels no earlier step works, of `levels`, of rotating zone `zone` (its name in the installed table:
    'Act1-Tower'), or of route `route`'s scripts; each in its own order (the act's for a route's)."""

    levels: tuple[int, ...] = ()
    zone: str = ''
    route: str = ''

    @property
    def label(self) -> str:
        return f'the rest of {self.zone or self.route or list(self.levels)}'

    def plan(self, act: ActPlan) -> None:
        if self.zone:
            found = next((zone for zone in installed_active_zones() if zone.name == self.zone), None)
            if found is None:
                act.skip(self, f'no installed zone {self.zone!r}')
                return
            levels = found.areas
        elif self.route:
            route = next((found for found in ROUTES if found.name == self.route), None)
            if route is None:
                act.skip(self, f'no catalogue route {self.route!r}')
                return
            own = {script.area for script in route.scripts}
            levels = tuple(area for area in act.zone.areas if area in own)
        else:
            levels = self.levels
        act.rest(levels, self.label)


@dataclass
class ActPlan:
    """The plan being built for `script` over its act's manual zone: the trips in order, each with the levels it only
    crosses; `covered` the levels a trip works; `uncovered` the levels a rest found no trip for."""

    script: ActScript
    zone: ActiveZone
    trips: list[tuple[RouteExcursion, frozenset[int]]] = field(default_factory=list)
    covered: set[int] = field(default_factory=set)
    uncovered: list[int] = field(default_factory=list)
    step: int = 0  # the step being planned, 1-based, for the log

    def left(self, levels: Iterable[int]) -> tuple[int, ...]:
        """`levels` of the act no trip works yet, in their order, once each."""
        return tuple(dict.fromkeys(area for area in levels if area in self.zone.areas and area not in self.covered))

    def add(self, trip: RouteExcursion, passes: frozenset[int] = frozenset()) -> None:
        """`trip` next, `passes` only crossed on it; its other levels of the act worked (a blocked trip works none)."""
        self.trips.append((trip, passes))
        if trip.blockers:
            return
        nodes = trip_levels(trip)
        start = START_AT.get(trip.route)
        if start is not None and start in nodes:
            nodes = nodes[nodes.index(start) :]  # the levels before its start are another trip's (tzroutine.py)
        self.covered |= {area for area in nodes if area in self.zone.areas} - passes

    def rest(self, levels: Iterable[int], label: str) -> None:
        """The trips covering `levels` not worked yet (routes/tz_routes.py `zone_route_plan` over them, in their
        order); the ones no trip covers are `uncovered`."""
        part = self.left(levels)
        if not part:
            return
        sub = replace(self.zone, areas=part, core=self.zone.core & frozenset(part), unreported=())
        found = zone_route_plan(sub)
        for trip in found.excursions:
            if trip.blockers:
                LOG.info('Macro: act: act %d %s: %s from %d blocked: %s', self.script.act, label, trip.route,
                         trip.waypoint, trip.blockers[0])  # fmt: skip
            self.add(trip)
        self.uncovered += [area for area in found.uncovered if area not in self.uncovered]

    def route_trip(self, route: str, target: int, waypoint: int | None = None) -> RouteExcursion | None:
        """Route `route`'s trip to `target` (routes/tz_routes.py `route_excursion`); None, said and skipped, when the
        catalogue has no such route or no path."""
        if not any(found.name == route for found in ROUTES):
            self._said(f'{route} to {target}', f'no catalogue route {route!r}')
            return None
        trip = route_excursion(self.zone, route, target, waypoint)
        if trip is None:
            start = f'waypoint {waypoint}' if waypoint is not None else 'a waypoint of its'
            self._said(f'{route} to {target}', f'route {route!r} has no path from {start} to {target}')
        return trip

    def skip(self, step: Step, why: str) -> None:
        """Step `step` not played: said (its levels fall to the later steps)."""
        self._said(step.label, why)

    def _said(self, label: str, why: str) -> None:
        LOG.info('Macro: act: act %d step %d (%s): %s: skipped', self.script.act, self.step, label, why)


def act_trips(script: ActScript, zone: ActiveZone) -> Trips:
    """`script`'s trips over its act's manual zone `zone`, in the shape of tzroutine.py `_route_trips`: each trip with
    the levels it only crosses, then the levels no trip covers. The steps in order, then the act's other levels."""
    act = ActPlan(script, zone)
    for number, step in enumerate(script.steps, 1):
        act.step = number
        step.plan(act)
    act.step = len(script.steps) + 1
    act.rest(zone.areas, 'the rest of the act')
    return tuple(act.trips), tuple(act.uncovered)


def check(script: ActScript, act: int) -> list[str]:
    """What is wrong with `script` as act `act`'s: its number, a step's route the catalogue lacks and not marked
    `missing`, a target or level outside the act (tests/inventory_tracking/macros/acts/test_engine.py)."""
    from inventory_tracking.routes.tz_groups import manual_zone

    zone = manual_zone(act)
    problems = [] if script.act == act else [f'the script says act {script.act}']
    if zone is None:
        return [*problems, f'no act {act}']
    names = {route.name for route in ROUTES}
    for number, step in enumerate(script.steps, 1):
        if isinstance(step, Trip):
            if step.route not in names and not step.missing:
                problems.append(f'step {number}: no catalogue route {step.route!r} (mark it missing)')
            if step.target not in zone.areas:
                problems.append(f'step {number}: target {step.target} is not in act {act}')
        if isinstance(step, Rest) and any(area not in zone.areas for area in step.levels):
            problems.append(f'step {number}: levels outside act {act}')
    return problems
