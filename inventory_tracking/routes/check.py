"""Offline validation of the route catalogue against the level tables and the handlers.

`problems` returns what is wrong, as text; an empty list is a sound catalogue:
- complete: every level has one main script, or is exempt with a reason, never both;
- well formed: a script ends by leaving the game or by its one way on; a route's scripts follow
  each other through those ways on; a route starts at a waypoint;
- linked: a way on by `enter` goes to a level the game joins to this one (routes/links.py);
- acted on: an `enter` or `stand` names a mark the level's handler gives (or the level's own way
  out to that level, which every level gets: levels/exits.py), a `use` a mark that sits on an
  object, a `fight` a boss the game has; a stage that cannot be is `pending`, and a pending stage
  that can be is an error too;
- ending: from every level, following the main scripts' ways on reaches `leave` without a loop.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping

from inventory_tracking.levels.exits import short_name
from inventory_tracking.levels.presets import LEVEL_NAMES
from inventory_tracking.levels.registry import handler_for
from inventory_tracking.routes.links import TOWNS, WAYPOINTS, linked
from inventory_tracking.routes.model import ENTER, FIGHT, LEAVE, STAND, USE, Route, Script, Stage
from inventory_tracking.terror import elites


# Bosses the elite table does not list: they are monsters of their own, not super uniques.
ACT_BOSSES = frozenset(('Andariel', 'Blood Raven', 'Duriel', 'Mephisto', 'Izual', 'Diablo', 'Baal'))


def bosses() -> frozenset[str]:
    return ACT_BOSSES | frozenset(elites.table().supers.values())


def main_scripts(routes: Iterable[Route]) -> dict[int, Script]:
    """Level -> its main script (the first, when the catalogue wrongly holds several)."""
    found: dict[int, Script] = {}
    for route in routes:
        for script in route.scripts:
            if not script.alternate:
                found.setdefault(script.area, script)
    return found


def unmet(area: int, stage: Stage) -> str | None:
    """Why the stage cannot be acted on in `area` with the marks the level has; None when it can."""
    handler = handler_for(area)
    labels = handler.labels() if handler is not None else frozenset()
    if stage.kind == ENTER:
        if stage.mark in labels or stage.mark == short_name(stage.to):
            return None
        return f'no mark {stage.mark!r}'
    if stage.kind == USE:
        spec = handler.spec(stage.mark) if handler is not None else None
        if spec is None:
            return f'no mark {stage.mark!r}'
        return None if spec.thing or spec.use else f'the mark {stage.mark!r} is not on an object'
    if stage.kind in (STAND, FIGHT) and stage.mark and stage.mark not in labels:
        return f'no mark {stage.mark!r}'
    return None


def problems(routes: Iterable[Route], exempt: Mapping[int, str]) -> list[str]:
    routes = tuple(routes)
    found: list[str] = []
    known = bosses()
    mains = defaultdict(list)
    for route in routes:
        areas = [script.area for script in route.scripts]
        for start in route.starts:
            if start not in WAYPOINTS:
                found.append(f'{route.name}: start {short_name(start)} has no waypoint')
            elif start not in areas and start not in TOWNS:
                found.append(f'{route.name}: start {short_name(start)} is not on the route')
        if not route.starts:
            found.append(f'{route.name}: no start')
        for script, after in zip(route.scripts, (*route.scripts[1:], None), strict=True):
            where = f'{route.name}, {short_name(script.area)}'
            if not script.alternate:
                mains[script.area].append(route.name)
            if script.area not in LEVEL_NAMES:
                found.append(f'{where}: level {script.area} is not in the levels table')
            found.extend(shape(where, script, after))
            for stage in script.stages:
                found.extend(stage_problems(where, script.area, stage, known))
    for area, names in sorted(mains.items()):
        if len(names) > 1:
            found.append(f'{short_name(area)} has {len(names)} main scripts: {", ".join(names)}')
        if area in exempt:
            found.append(f'{short_name(area)} is exempt and has a script')
    found.extend(
        f'{short_name(area)} ({area}) has no script and no exemption'
        for area in sorted(LEVEL_NAMES)
        if area not in mains and area not in exempt
    )
    found.extend(endings(main_scripts(routes)))
    return found


def shape(where: str, script: Script, after: Script | None) -> list[str]:
    """A script ends by `leave` or by its way on; in a route, the way on is the next script's level."""
    found = []
    kinds = [stage.kind for stage in script.stages]
    ways = [stage for stage in script.stages if stage.to or stage.tours]
    if len(ways) > 1:
        found.append(f'{where}: {len(ways)} ways on')
    last = script.stages[-1] if script.stages else None
    if last is None:
        found.append(f'{where}: no stages')
    elif LEAVE in kinds[:-1]:
        found.append(f'{where}: stages after leave')
    elif (
        ways
        and ways[0] is not last
        and not ways[0].tours
        and not (ways[0].to in TOWNS and script.stages[-2] is ways[0])
    ):
        found.append(f'{where}: stages after the way on')
    elif not ways and last.kind != LEAVE:
        found.append(f'{where}: ends without leaving the level or the game')
    elif ways and ways[0].to in TOWNS and last.kind != LEAVE:
        found.append(f'{where}: goes to town without leaving the game')
    # A tour leads into each of its levels, and a way back (`back`) is a branch's end: the next script is another branch
    leads = bool(ways) and (ways[0].to == after.area or after.area in ways[0].tours or ways[0].back) if after else True
    if after is not None and not leads:
        found.append(f'{where}: does not lead to {short_name(after.area)}, the next level of the route')
    return found


def stage_problems(where: str, area: int, stage: Stage, known: frozenset[str]) -> list[str]:
    found = []
    what = f'{where}: {stage.text()}'
    if stage.kind == ENTER and not linked(area, stage.to):
        found.append(f'{what}: {short_name(stage.to)} is not joined to this level')
    if stage.kind == FIGHT and stage.boss not in known:
        found.append(f'{what}: the game has no boss of that name')
    reason = unmet(area, stage)
    if reason is not None and not stage.pending:
        found.append(f'{what}: {reason}')
    if reason is None and stage.pending:
        found.append(f'{what}: is pending, but the level has what it needs')
    return found


def endings(mains: Mapping[int, Script]) -> list[str]:
    """From every level with a main script: the levels its ways on lead through, to `leave`."""
    found = []
    for start in sorted(mains):
        seen, area = [start], start
        while True:
            script = mains[area]
            way = script.way_on
            if way is None or way.to in TOWNS:
                break  # `shape` has checked that this script ends by leaving the game
            if way.to in seen:
                names = ' -> '.join(short_name(a) for a in (*seen, way.to))
                found.append(f'{short_name(start)}: the route never ends: {names}')
                break
            if way.to not in mains:
                found.append(f'{short_name(start)}: the route stops at {short_name(way.to)}, which has no script')
                break
            seen.append(way.to)
            area = way.to
    return found


def pending(routes: Iterable[Route]) -> list[tuple[str, int, Stage]]:
    """(route, level, stage) of every stage that cannot be acted on yet."""
    return [
        (route.name, script.area, stage)
        for route in routes
        for script in route.scripts
        for stage in script.stages
        if stage.pending
    ]
