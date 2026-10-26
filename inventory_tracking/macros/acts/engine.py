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
- `ActScript.alone` (2026-10-25): the act played by itself as its kind's game's own act, its `alone` steps only (no
  rest of the act, no rotation: macros/tzroutine.py `alone_act`, macros/actloop.py `alone`); its `whole` levels toured
  whole (tzroutine.py WHOLE). None: as before. `ActScript.extras` (2026-10-26): the other acts that game plays after
  its own when a shard of theirs is over the limit, each an act's script of its own alone steps (Act 2 TZ leveling's
  act 4 and act 5, macros/acts/act2.py TZ_LEVELING_EXTRAS); no other act.

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
# diablo -> do rest of flame river"); WORKED on the way (the player's "catacombs 2 -> 3 -> 4 -> andariel"); ONLY only
# crossed, no trip of theirs (2026-10-26, Act 2 TZ leveling's act 4: "act 4 terrorized: run full CS + Diablo", the
# River of Flame its way in only; a later step or the act's rest may still take them)
AFTER, WORKED, ONLY = 'after', 'worked', 'only'
Crossed = Literal['after', 'worked', 'only']


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
    # The act played alone (2026-10-25, the Act 2 TZ leveling kind, loop.py ACT2_TZ): in that kind's game (its shard's
    # act played first: tzroutine.py `alone_act`) only these steps, then the acts of `extras` a shard over the limit
    # terrorized, then the game's end: no rest of the act, no rotation, no other act (actloop.py `alone`). Every other
    # kind plays `steps`, the act's rest and the rotation
    alone: tuple[Step, ...] | None = None
    # The levels the alone game works whole: every room toured whatever the level's size or a boss on it (tzroutine.py
    # WHOLE, `Excursion.whole`)
    whole: frozenset[int] = frozenset()
    # The other acts the alone game plays after its own when a shard of theirs is over the limit (2026-10-26, actloop.py
    # `extra_acts`): each a script of that act whose `alone` steps and `whole` levels are played, in the game's order
    # (agenda.py `Agenda.acts`). Not the acts' own scripts: their kinds and every other game play those as before
    extras: tuple[ActScript, ...] = ()

    def extra(self, act: int | None) -> ActScript | None:
        """The script `extras` holds for act `act`; None with none."""
        return next((script for script in self.extras if script.act == act), None)


@dataclass(frozen=True)
class Trip:
    """Route `route`'s trip to level `target` (its boss's), from `waypoint` (None: the route's waypoint nearest it).
    `crossed`: AFTER, WORKED or ONLY (above). `missing`: why the catalogue cannot play it yet (the route to add):
    skipped."""

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
        passes = crossed_levels(trip, self.target, act.zone) if self.crossed in (AFTER, ONLY) else ()
        act.add(trip, frozenset(passes))
        if self.crossed == AFTER:
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


def act_trips(script: ActScript, zone: ActiveZone, alone: bool = False) -> Trips:
    """`script`'s trips over its act's manual zone `zone`, in the shape of tzroutine.py `_route_trips`: each trip with
    the levels it only crosses, then the levels no trip covers. The steps in order, then the act's other levels;
    `alone` (with `ActScript.alone`): its alone steps only, no other level of the act."""
    act = ActPlan(script, zone)
    alone = alone and script.alone is not None
    steps = script.alone if alone and script.alone is not None else script.steps
    for number, step in enumerate(steps, 1):
        act.step = number
        step.plan(act)
    if alone:
        return tuple(act.trips), tuple(act.uncovered)
    act.step = len(steps) + 1
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
    for extra in script.extras:
        if extra.act == act or extra.alone is None or extra.extras:
            problems.append(f'extra act {extra.act}: another act, with alone steps and no extras of its own')
        problems += [f'extra act {extra.act}: {problem}' for problem in check(extra, extra.act)]
    names = {route.name for route in ROUTES}
    if any(area not in zone.areas for area in script.whole):
        problems.append(f'whole levels outside act {act}')
    for number, step in enumerate((*script.steps, *(script.alone or ())), 1):
        if isinstance(step, Trip):
            if step.route not in names and not step.missing:
                problems.append(f'step {number}: no catalogue route {step.route!r} (mark it missing)')
            if step.target not in zone.areas:
                problems.append(f'step {number}: target {step.target} is not in act {act}')
        if isinstance(step, Rest) and any(area not in zone.areas for area in step.levels):
            problems.append(f'step {number}: levels outside act {act}')
    return problems
