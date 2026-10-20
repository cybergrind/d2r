"""Pure catalog graph for a current active TZ group's guarded travel legs.

Each leg names the exact route and hops from an available waypoint. A hop whose
catalog stage is pending, is a tomb tour, or is only inferred from a level link
is reported as blocked until the runner has a verified handler for it. An excursion
that tours every level of a tour (`_whole_tour`: the Canyon of the Magi's seven tombs)
is not blocked by it: the tour goes through the nearest entrance not yet entered and
reads the level on arrival, so no entrance needs to be designated ahead.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from itertools import count
from typing import Literal

from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.links import WAYPOINTS, linked
from inventory_tracking.routes.model import FIGHT, USE, Route, Stage
from inventory_tracking.routes.tz_groups import ActiveZone, installed_active_zones


Status = Literal['ready', 'needs-played-check', 'unavailable']


@dataclass(frozen=True)
class Capability:
    area: int
    route: str
    waypoint: int | None
    target: Literal['boss', 'chest', 'object'] | None
    status: Status
    reason: str = ''
    entry: str = 'unmapped'
    exit: str = 'unmapped'


def route_inventory() -> dict[int, Capability]:
    """Conservative catalog audit of every installed TZ level, including no-Herald transit levels."""
    found: dict[int, Capability] = {}
    for zone in installed_active_zones():
        for area in zone.areas:
            if area in found:
                continue
            options = [(route, script) for route in ROUTES for script in route.scripts if script.area == area]
            if not options:
                found[area] = Capability(area, '', None, None, 'unavailable', 'no route script')
                continue
            route, script = options[0]
            waypoint = next((start for start in route.starts if start in WAYPOINTS), None)
            leading = next(
                (stage for prior in route.scripts for stage in prior.stages if stage.to == area or area in stage.tours),
                None,
            )
            entry = (
                leading.text()
                if leading is not None
                else (f'waypoint {area}' if area in WAYPOINTS else 'route entry needs played check')
            )
            leaving = next((stage for stage in script.stages if stage.to), None)
            exit_stage = leaving or next((stage for stage in script.stages if stage.kind == 'leave'), None)
            exit_text = exit_stage.text() if exit_stage is not None else 'route exit needs played check'
            target = (
                'boss'
                if any(stage.kind == FIGHT for stage in script.stages)
                else (
                    'chest'
                    if any(stage.kind == USE and 'chest' in stage.mark.lower() for stage in script.stages)
                    else ('object' if any(stage.kind == USE and not stage.to for stage in script.stages) else None)
                )
            )
            pending = next((stage.pending for stage in script.stages if stage.pending), '')
            if waypoint is None or pending:
                reason = pending or 'no entry waypoint'
                found[area] = Capability(area, route.name, waypoint, target, 'unavailable', reason, entry, exit_text)
            else:
                found[area] = Capability(
                    area, route.name, waypoint, target, 'needs-played-check', entry=entry, exit=exit_text
                )
    return found


@dataclass(frozen=True)
class RouteHop:
    source: int
    destination: int
    route: str
    kind: Literal['stage', 'tour', 'connector']
    stage: Stage | None = None

    @property
    def blocker(self) -> str | None:
        if self.kind == 'connector':
            return f'town or waypoint connector {self.source}→{self.destination} has no catalog stage'
        if self.kind == 'tour':
            return f'tour {self.source}→{self.destination} cannot designate one entrance'
        if self.stage is not None and self.stage.pending:
            return f'pending stage {self.source}→{self.destination}: {self.stage.pending}'
        return None


@dataclass(frozen=True)
class RouteLeg:
    area: int
    route: str
    waypoint: int
    hops: tuple[RouteHop, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class RouteExcursion:
    """One waypoint-to-terminal catalog path, followed by a town reset before another trip."""

    route: str
    waypoint: int
    terminal: int
    hops: tuple[RouteHop, ...]
    covers: tuple[int, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class ZoneRoutePlan:
    zone: ActiveZone
    legs: dict[int, RouteLeg]
    missing: tuple[tuple[int, str], ...]
    blockers: tuple[tuple[int, str], ...]
    excursions: tuple[RouteExcursion, ...]
    uncovered: tuple[int, ...]

    @property
    def ready(self) -> bool:
        return not self.blockers and not self.uncovered and all(not trip.blockers for trip in self.excursions)


def _edges(route: Route) -> dict[int, tuple[RouteHop, ...]]:
    found: dict[int, list[RouteHop]] = {}
    for script in route.scripts:
        for stage in script.stages:
            if stage.to and not stage.back:
                found.setdefault(script.area, []).append(RouteHop(script.area, stage.to, route.name, 'stage', stage))
            for area in stage.tours:
                found.setdefault(script.area, []).append(RouteHop(script.area, area, route.name, 'tour', stage))
    for start in route.starts:
        if start not in WAYPOINTS:
            continue
        for script in route.scripts:
            if script.area != start and linked(start, script.area):
                found.setdefault(start, []).append(RouteHop(start, script.area, route.name, 'connector'))
    return {source: tuple(hops) for source, hops in found.items()}


def _path(edges: dict[int, tuple[RouteHop, ...]], start: int, destination: int) -> tuple[RouteHop, ...] | None:
    order = count()
    queue: list[tuple[int, int, int, int, tuple[RouteHop, ...]]] = [(0, 0, next(order), start, ())]
    best: dict[int, tuple[int, int]] = {}
    while queue:
        blocked, distance, _, area, path = heapq.heappop(queue)
        cost = blocked, distance
        if area in best and best[area] <= cost:
            continue
        best[area] = cost
        if area == destination:
            return path
        for hop in edges.get(area, ()):
            next_cost = blocked + (hop.blocker is not None), distance + 1
            if hop.destination not in best or next_cost < best[hop.destination]:
                heapq.heappush(queue, (*next_cost, next(order), hop.destination, (*path, hop)))
    return None


def _whole_tour(edges: dict[int, tuple[RouteHop, ...]], path: tuple[RouteHop, ...]) -> tuple[RouteHop, ...]:
    """`path` ending in a tour's hop goes on through every level of that tour, in the catalogue's order (the order a
    game takes them in is the tour's own: the nearest entrance not yet entered first). The player, 2026-10-20 ~14:03:
    "we need to utilize smaller tombs too - it gives a great ext/hour rate"; 00:45 on 2026-10-18: "Canyon first, then
    tombs"."""
    if not path or path[-1].kind != 'tour':
        return path
    last = path[-1]
    tour = tuple(hop for hop in edges.get(last.source, ()) if hop.kind == 'tour' and hop.stage == last.stage)
    return (*path[:-1], *tour)


def _trip_blockers(path: tuple[RouteHop, ...]) -> tuple[str, ...]:
    """The blockers of an excursion's hops; a tour's hops are none when the excursion takes the whole tour."""
    tours = [hop for hop in path if hop.kind == 'tour']
    stage = tours[0].stage if tours else None
    whole = stage is not None and {hop.destination for hop in tours} == set(stage.tours)
    return tuple(blocker for hop in path if not (whole and hop.kind == 'tour') and (blocker := hop.blocker) is not None)


def route_leg(area: int, route_name: str | None = None) -> RouteLeg | None:
    """Best catalog path to an area, preferring verified stages over implicit links."""
    options = [route for route in ROUTES if any(script.area == area for script in route.scripts)]
    if route_name is not None:
        options = [route for route in options if route.name == route_name]
    if not options:
        return None
    route = options[0]
    edges = _edges(route)
    candidates = []
    for start in route.starts:
        if start not in WAYPOINTS:
            continue
        path = _path(edges, start, area)
        if path is None:
            continue
        blockers = tuple(blocker for hop in path if (blocker := hop.blocker) is not None)
        candidates.append((len(blockers), len(path), start, path, blockers))
    if not candidates:
        start = next((area for area in route.starts if area in WAYPOINTS), None)
        if start is None:
            return None
        return RouteLeg(area, route.name, start, (), ('no catalog path from a route waypoint',))
    _, _, start, path, blockers = min(candidates)
    return RouteLeg(area, route.name, start, path, blockers)


def zone_route_plan(zone: ActiveZone, capabilities: dict[int, Capability] | None = None) -> ZoneRoutePlan:
    """Audit every level and cover reachable ones with catalog trips from waypoints.

    Separate trips require a town return and waypoint travel. This is structural
    coverage, not authorization to run unplayed stages or pending handlers.
    """
    caps = route_inventory() if capabilities is None else capabilities
    legs: dict[int, RouteLeg] = {}
    missing = []
    blockers = []
    for area in zone.areas:
        capability = caps.get(area)
        leg = route_leg(area, capability.route if capability is not None and capability.route else None)
        if leg is None:
            missing.append((area, 'no route script'))
            blockers.append((area, 'no route script'))
            continue
        legs[area] = leg
        blockers.extend((area, reason) for reason in leg.blockers)
        if capability is None:
            blockers.append((area, 'no route capability'))
        elif capability.status != 'ready':
            blockers.append((area, capability.reason or capability.status))
    candidates = []
    group = set(zone.areas)
    routes = {route.name: route for route in ROUTES}
    for leg in legs.values():
        route = routes[leg.route]
        edges = _edges(route)
        for start in route.starts:
            if start not in WAYPOINTS:
                continue
            path = _path(edges, start, leg.area)
            if path is None:
                continue
            path = _whole_tour(edges, path)  # a tour's level: the trip tours them all (one leg each would be 7 trips)
            nodes = (start, *(hop.destination for hop in path))
            covers = tuple(dict.fromkeys(area for area in nodes if area in group))
            terminal = path[-1].destination if path else leg.area
            candidates.append(RouteExcursion(route.name, start, terminal, path, covers, _trip_blockers(path)))
    remaining = group.copy()
    excursions = []
    while remaining:
        useful = [trip for trip in candidates if remaining.intersection(trip.covers)]
        if not useful:
            break
        # A trip that can be played first: a blocked one covering more took every level from it (Act2-ArcaneSanctuary,
        # 2026-10-19: Lut Gholein's unscripted walk to the Harem left no trip from the Palace Cellar waypoint)
        chosen = max(
            useful,
            key=lambda trip: (
                not trip.blockers,
                len(remaining.intersection(trip.covers)),
                -len(trip.blockers),
                -len(trip.hops),
                # (a terminal off the zone, a tour's last level of an act's part planned alone, is last: no error)
                -(zone.areas.index(trip.terminal) if trip.terminal in zone.areas else len(zone.areas)),
            ),
        )
        excursions.append(chosen)
        remaining.difference_update(chosen.covers)
    return ZoneRoutePlan(
        zone,
        legs,
        tuple(missing),
        tuple(blockers),
        tuple(excursions),
        tuple(area for area in zone.areas if area in remaining),
    )
