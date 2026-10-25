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
import json
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path

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
    SHORT,
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
from inventory_tracking.routes.tz_routes import RouteExcursion, nearest_excursion, route_excursion, zone_route_plan
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
# SHORT_LEVELS (2026-10-25, off until measured): the player, ~10:15, on the TZ levels under about 1,600 exp a second
# with the travel to them (rca/2026-10-25/exp-hour-findings.md: "Plains of Despair 949, Bloody Foothills 1,088, Burial
# Grounds 1,119, Blood Moor 1,192, Black Marsh 1,201"): "Shorten them: clear only the elites, bosses and big packs on
# those levels, then move on" (narrows "farm until it's done" / "kill all packs" for those levels only). True: TZ
# leveling works a weak area (`weak_areas`) it would work fully as TZ+ (agenda.py PLUS) as agenda.py SHORT instead: its
# leaders, bosses and big packs (SHORT_PACK), no room, then done; a lighter policy there (on the way, a crossing, a
# transit, COVER without TZ+) stays as it is (`shortened`). False: TZ+ as before. Measure: exphour.py, on against off.
# On from 2026-10-25 ~11:46 after the wide suite (green with it on; d2r-7e restarts the loop)
SHORT_LEVELS = True
# The weak areas (levels.txt ids) and their exp a second, made by the d2-loop-watch skill's exphour.py `--weak-out`
SHORT_LEVELS_FILE = Path(__file__).parent / 'data' / 'short_levels.json'


@functools.cache
def weak_areas() -> frozenset[int]:
    """SHORT_LEVELS: the areas of SHORT_LEVELS_FILE; none without the file."""
    if not SHORT_LEVELS_FILE.exists():
        return frozenset()
    return frozenset(int(row['area']) for row in json.loads(SHORT_LEVELS_FILE.read_text())['levels'])


# The route stages a level run performs: an area at one of them is still a level's work
WORKED_BY_RUNS = frozenset((FIGHT, USE, STAND))


# A route's excursion begun at a later waypoint of its own, the levels before it left out. Andariel from Catacombs 2:
# Inner Cloister and the Cathedral have no level handler (no card mark for the way on), and every game ended in Inner
# Cloister (08:22-08:25 on 2026-10-20). The player, 2026-10-20 ~08:24: "there are 2 options: inner cloister ->
# cathedral -> catacombs level -> kill andy / or cat2 -> cat 3 -> cat 4 -> andy"
START_AT = {'Andariel': 35}
# A zone's levels its trips leave out (START_AT's cut, a waypoint or town connector with no catalogue stage, no trip of
# the zone's plan) get a trip of a catalogue route with a script on them, from that route's nearest waypoint, after the
# zone's own trips (`skipped_trips`; the longest such trip where one covers another's levels). The player, 2026-10-22:
# "we need to kill all bosses, no exceptions to that": Bone Ash (the Cathedral, cut by START_AT: 26 games), Shenk and
# Dac Farren (Bloody Foothills), Pindleskin (Nihlathak's Temple) were never in a rotating zone's itinerary
# (rca/2026-10-22/boss-audit-findings.md §4 cause 3). The Andariel trip stays from waypoint 35 first (her kill, the
# player's 10-20 ruling), the Inner Cloister, the Cathedral and Catacombs 1 a trip from waypoint 32 after it. A level no
# route reaches unblocked stays skipped, said (Moo Moo Farm: the Cow King, the red portal Wirt's Leg opens; the red
# portals not in the map files). False: skipped, as before
SKIPPED_TRIPS = True
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
# The boss's trip from the waypoint nearest the boss, the levels it crosses (`Excursion.passes`) only crossed, and
# worked after the kill, nearest the boss first, then the rest of the boss's route, then the act's other levels. The
# player, 2026-10-20 ~21:27: "for full act TZ we must start with act boss first. In our case: we must go river of
# flame -> CS -> kill diablo -> do rest of flame river -> city of damned/planes of despair and etc". Diablo's trip had
# been begun at the City of the Damned, the City and the River worked before the Sanctuary (game 21, 21:22:18).
# False: the boss's trip `zone_route_plan` covers the most levels with, its levels worked on the way
BOSS_NEAREST = True
# How a level the boss's trip crosses is worked on it, in either kind: straight through, the leaders near only
# (agenda.py ON_THE_WAY); its own run comes after the boss, by a trip of its own
CROSSING = ON_THE_WAY
# A terrorized act played in the order its script declares (macros/acts/act<N>.py, the player, 2026-10-20 ~22:50:
# "implement shards run for every act ... act1 shard -> catacombs 2 -> 3 -> 4 -> andariel -> marsh -> tower ->
# countess -> rest of zones one by one"), once the script is `ready`. False: every act by the generic boss-first order
ACT_SCRIPTS = True
# How a level an alone act's script works whole is worked (macros/acts/engine.py `ActScript.whole`, `Excursion.whole`;
# act2.py ALONE, the player, 2026-10-25 ~17:15: "go full arcane sanctuary (+kill summoner)"): TZ+ (agenda.py PLUS)
# whatever its size or a boss on it: every room toured, every leader and the level's groups (BIG_GROUP on a big level:
# "for levels with 300+ mobs - we just clear big groups and elites/champions", 2026-10-20; "the main goal for TZ
# leveling is to kill all packs and DO NOT hunt every single enemy", 2026-10-21), its route's own work (the boss) too;
# never shortened (SHORT_LEVELS: the player named it). FULL_CLEAR: every hostile and every room, as the Full clear TZ
# kind's levels; the Full clear kind's own game is FULL_CLEAR anyway
WHOLE = PLUS


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
    # The levels crossed on the way to the boss (`BOSS_NEAREST`), worked by a later trip after the kill: never done as
    # they are left (tzloop.py `perform`), their runs here not counted against that trip (tzloop.py `reopen`)
    passes: frozenset[int] = frozenset()
    # The levels an alone act's script works whole (`WHOLE`; macros/acts/engine.py `ActScript.whole`, 2026-10-25)
    whole: frozenset[int] = frozenset()

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

    def trip_of(self, area: int, finished: Iterable[int]) -> Excursion | None:
        """The excursion `area` is worked by under zone navigation (macros/zonenav.py): the one under way
        (`excursion_of`), else the first naming it not only crossing it, over or not. A level's trip is over for the
        itinerary once its terminal is done, but the graph judges each level by itself: Duriel's Lair, entered from
        the last tomb toured, was TRANSIT (the tour over) and explored on arrival, unfought (the act harness,
        2026-10-21)."""
        found = self.excursion_of(area, finished)
        if found is not None:
            return found
        return next((trip for trip in self.excursions if area in trip.areas and area not in trip.passes), None)

    def next_excursion(self, finished: Iterable[int]) -> Excursion | None:
        """The first excursion not over."""
        done = set(finished)
        return next((trip for trip in self.excursions if not trip.over(done)), None)

    def touring(self, area: int, finished: Iterable[int]) -> bool:
        """Whether `area` is on the tour of the excursion under way (`Excursion.touring`): not done as it is left."""
        trip = self.excursion_of(area, finished)
        return trip is not None and trip.touring(area)

    def crossing(self, area: int, finished: Iterable[int]) -> bool:
        """Whether `area` is crossed on the way to the boss by the excursion under way (`Excursion.passes`): not done
        as it is left, a later trip works it."""
        trip = self.excursion_of(area, finished)
        return trip is not None and area in trip.passes

    def crossed(self, finished: Iterable[int]) -> frozenset[int]:
        """The levels an excursion over crossed on the way to its boss (`Excursion.passes`): their own trip's now."""
        done = set(finished)
        return frozenset(level for trip in self.excursions if trip.over(done) for level in trip.passes)


@functools.cache
def itinerary(terrorized: frozenset[int], order: tuple[int, ...] = ()) -> Itinerary | None:
    """The itinerary of the zones whose levels are `terrorized` (`MANUAL_ZONES`: routes/tz_groups.py `match_zones`, a
    terrorized act first, its boss's trip first; else the one rotating zone); None when no installed zone matches.
    `order`: the acts a shard terrorized in the order they are played (agenda.py `Agenda.acts`: the kind's act, then
    the acts of shards over the limit, actloop.py OVERFLOW); the other acts read after them, then the rotation."""
    alone = alone_act(order) if MANUAL_ZONES else None
    if MANUAL_ZONES:
        zones = played_first(match_zones(terrorized), order)
        if alone is not None and any(act_of_manual(zone) == alone for zone in zones):
            zones = tuple(zone for zone in zones if act_of_manual(zone) == alone)
            LOG.info("Macro: act: act %d alone (macros/acts/act%d.py ALONE): its script's steps only, then the "
                     "game's end: no rest of the act, no rotation, no other act", alone, alone)  # fmt: skip
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
        lone = alone is not None and act_of_manual(zone) == alone
        found_trips, uncovered = _route_trips(zone, lone)
        whole = _whole(zone) if lone else frozenset()
        skipped += [(area, 'no catalogue excursion covers it') for area in uncovered]
        for found, passes in found_trips:
            if found.blockers:
                skipped += [(area, found.blockers[0]) for area in found.covers]
                continue
            trip = replace(_excursion(found, group, skipped), passes=passes)
            trip = replace(trip, whole=whole & trip.zone - passes) if whole else trip
            if before and trip.zone <= before:
                continue  # another zone's trips cover its levels already (the union's, never one zone's own)
            trips.append(trip)
    covered = set().union(*(trip.zone for trip in trips)) if trips else set()
    if SKIPPED_TRIPS:
        trips += skipped_trips(zones, group, [area for area, _ in dict(skipped).items() if area not in covered])
        covered = set().union(*(trip.zone for trip in trips)) if trips else set()
    skipped = [(area, why) for area, why in dict(skipped).items() if area not in covered]
    name = ' + '.join(zone.name for zone in zones)
    found = Itinerary(name, group, tuple(trips), tuple(sorted(skipped)))
    stray = sorted(terrorized - group)
    LOG.info(
        'Macro: tz: zone %s: %s; skipped %s%s',
        name,
        trips_said(found.excursions),
        [f'{area} ({why})' for area, why in found.skipped] or 'none',
        f'; read terrorized in no zone: {stray}' if stray else '',
    )
    return found


def skipped_trips(zones: Iterable[ActiveZone], group: frozenset[int], left: Iterable[int]) -> list[Excursion]:
    """SKIPPED_TRIPS: the trips over the levels `left` of `zones` that no trip covers: for each, the first catalogue
    route with a script on it whose trip to it from its nearest waypoint (routes/tz_routes.py `route_excursion`) is
    unblocked; a trip whose terrorized levels another's hold is dropped (the trip to Catacombs 1 holds the
    Cathedral's)."""
    found: list[Excursion] = []
    for zone in zones:
        for area in left:
            if area not in zone.areas:
                continue
            for route in ROUTES:
                if not any(script.area == area for script in route.scripts):
                    continue
                trip = route_excursion(zone, route.name, area)
                if trip is None or trip.blockers:
                    continue
                excursion = _excursion(trip, group, [])
                if area in excursion.zone:
                    found.append(excursion)
                    break
    kept: list[Excursion] = []
    for trip in sorted(found, key=lambda each: -len(each.zone)):
        if not any(trip.zone <= other.zone for other in kept):
            kept.append(trip)
    return [trip for trip in found if trip in kept]


def alone_act(order: tuple[int, ...]) -> int | None:
    """The act a game plays alone (macros/acts/engine.py `ActScript.alone`, act2.py ALONE, 2026-10-25): the first of
    `order` (the game's own act, its kind's shard: agenda.py `Agenda.acts`) when its script is ready and has alone
    steps; None otherwise (no shard act, the scripts off, an act 2 played as another act's overflow)."""
    if not order or not (ACT_SCRIPTS and BOSS_FIRST and BOSS_NEAREST):
        return None
    from inventory_tracking.macros.acts import script_of  # late: the act scripts import this module

    script = script_of(order[0])
    return order[0] if script is not None and script.ready and script.alone is not None else None


def _whole(zone: ActiveZone) -> frozenset[int]:
    """The levels of manual zone `zone`'s act its script works whole when played alone (`ActScript.whole`)."""
    from inventory_tracking.macros.acts import script_of

    act = act_of_manual(zone)
    script = script_of(act) if act is not None else None
    return script.whole if script is not None else frozenset()


def played_first(zones: tuple[ActiveZone, ...], order: tuple[int, ...]) -> tuple[ActiveZone, ...]:
    """`zones` (`match_zones`: the acts in act order, then the rotation) with the acts of `order` first, in its order;
    the rest as they were."""

    def rank(pair: tuple[int, ActiveZone]) -> tuple[int, int]:
        act = act_of_manual(pair[1])
        return (order.index(act), 0) if act in order else (len(order), pair[0])

    return tuple(zone for _, zone in sorted(enumerate(zones), key=rank))


def trips_said(trips: Iterable[Excursion]) -> str:
    """The excursions as the plan's log line says them (`Macro: tz: zone <name>: <this>; skipped ...`)."""
    return (
        '; '.join(
            f'{trip.route} from {trip.waypoint}: {list(trip.areas)}'
            + (f', {list(trip.tours)} a tour from {trip.hub} one by one' if trip.tours else '')
            + (f', {sorted(trip.passes)} crossed to the boss, worked after it' if trip.passes else '')
            for trip in trips
        )
        or 'no excursion'
    )


Trips = tuple[tuple[tuple[RouteExcursion, frozenset[int]], ...], tuple[int, ...]]


def _route_trips(zone: ActiveZone, alone: bool = False) -> Trips:
    """The catalogue's trips covering `zone` (routes/tz_routes.py `zone_route_plan`), each with the levels it only
    crosses to its boss (none but the boss's), and the levels none covers. A terrorized act's: its script's order when
    the script is ready (`_scripted`, macros/acts/); else (`BOSS_FIRST`) the trip to its boss first (`_boss_trip`),
    then the trips of its levels that trip does not work: with `BOSS_NEAREST` the levels it crossed (nearest the boss
    first), the rest of the boss's route, then the others. `alone`: the script's alone steps only (`alone_act`)."""
    act = act_of_manual(zone)
    if act is not None and (scripted := _scripted(act, zone, alone)) is not None:
        return scripted
    plan = zone_route_plan(zone)
    boss = ACT_BOSS_LEVELS.get(act) if act is not None and BOSS_FIRST else None
    first = _boss_trip(zone, plan.excursions, boss) if boss is not None else None
    if first is None or boss is None:
        return tuple((trip, frozenset()) for trip in plan.excursions), plan.uncovered
    nodes = trip_levels(first)
    reached = set(nodes)
    start = START_AT.get(first.route)
    if start is not None and start in nodes:
        reached = set(nodes[nodes.index(start) :])  # the levels before its start are another trip's
    passes = frozenset(crossed_levels(first, boss, zone)) if BOSS_NEAREST else frozenset()
    left = [area for area in zone.areas if area not in reached or area in passes]
    if not left or not zone.core - (reached - passes):
        return ((first, passes),), ()
    route = next((found for found in ROUTES if found.name == first.route), None)
    own = {script.area for script in route.scripts} if route is not None else set()
    parts = (
        [[area for area in reversed(nodes) if area in passes], [area for area in left if area in own - passes]]
        if BOSS_NEAREST
        else []
    )
    parts.append([area for area in left if not any(area in part for part in parts)])
    trips: list[tuple[RouteExcursion, frozenset[int]]] = [(first, passes)]
    uncovered: list[int] = []
    for part in parts:
        if not part:
            continue
        rest = zone_route_plan(replace(zone, areas=tuple(part), core=zone.core & frozenset(part), unreported=()))
        trips += [(trip, frozenset()) for trip in rest.excursions]
        uncovered += rest.uncovered
    return tuple(trips), tuple(uncovered)


def _scripted(act: int, zone: ActiveZone, alone: bool = False) -> Trips | None:
    """Act `act`'s trips by its script (macros/acts/act<N>.py, `ACT_SCRIPTS`), the boss-first order it declares (its
    alone steps only with `alone`); None while the script is not ready, or with `BOSS_FIRST` or `BOSS_NEAREST` off (the
    generic order then)."""
    if not (ACT_SCRIPTS and BOSS_FIRST and BOSS_NEAREST):
        return None
    from inventory_tracking.macros.acts import script_of  # late: the act scripts import this module
    from inventory_tracking.macros.acts.engine import act_trips

    script = script_of(act)
    return act_trips(script, zone, alone) if script is not None and script.ready else None


def _boss_trip(zone: ActiveZone, planned: Iterable[RouteExcursion], boss: int) -> RouteExcursion | None:
    """The trip to level `boss`: from the waypoint nearest it (`BOSS_NEAREST`: routes/tz_routes.py
    `nearest_excursion`), else the first of `planned` that reaches it; None when none is playable."""
    if BOSS_NEAREST:
        nearest = nearest_excursion(zone, boss)
        if nearest is not None and not nearest.blockers and nearest.terminal == boss:
            return nearest
    return next((trip for trip in planned if not trip.blockers and boss in trip_levels(trip)), None)


def crossed_levels(trip: RouteExcursion, boss: int, zone: ActiveZone) -> tuple[int, ...]:
    """The levels of `zone` boss trip `trip` only crosses before `boss`: neither a fight nor a stand on the way (the
    Throne's waves, Durance 3's portal stand are the trip's own work), nearest the boss first."""
    nodes = trip_levels(trip)
    worked = boss_areas(trip.route) | stand_areas(trip.route)
    return tuple(area for area in reversed(nodes[: nodes.index(boss)]) if area in zone.areas and area not in worked)


def trip_levels(trip: RouteExcursion) -> tuple[int, ...]:
    """The levels of catalogue trip `trip`: its waypoint, then each hop's destination."""
    return (trip.waypoint, *(hop.destination for hop in trip.hops))


def _excursion(trip: RouteExcursion, group: frozenset[int], skipped: list[tuple[int, str]]) -> Excursion:
    """Catalogue trip `trip` as an excursion over the terrorized `group` (`START_AT` cuts its start: those levels are
    added to `skipped`)."""
    nodes = trip_levels(trip)
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
    boss ("finding each elite on the way to Andariel, kill her and start a new game"); else COVER. SHORT_LEVELS: PLUS
    on a weak area is SHORT (`shortened`). A level an alone act's trip works whole (`Excursion.whole`): WHOLE."""
    if trip is None or area not in trip.zone:
        return TRANSIT
    if area in trip.passes:
        return CROSSING  # crossed to the boss: its own run after it (`BOSS_NEAREST`)
    if full_clear:
        return FULL_CLEAR
    if area in POLICY:
        return POLICY[area]
    if area in trip.whole:
        return WHOLE  # an alone act's level worked whole (2026-10-25, act2.py ALONE: "full arcane sanctuary")
    bosses = boss_areas(trip.route)
    ahead = trip.areas[trip.areas.index(area) :]
    if trip.touring(area):
        # A tour's side level (Duriel's Lair, levels/handlers/tal_rasha.py DURIEL, 2026-10-21) is no boss ahead of the
        # toured levels: entered mid-tour from whichever holds its way, the tour's rest after it
        ahead = tuple(level for level in ahead if trip.touring(level))
    on_the_way = any(level in bosses for level in ahead)
    if not (TZ_PLUS if plus is None else plus):
        return ON_THE_WAY if on_the_way else COVER
    population = level_population(area)
    if population is not None and population >= BIG_LEVEL:
        return shortened(area, PLUS_WAY if on_the_way else PLUS)
    return shortened(area, PLUS_WAY if area in stand_areas(trip.route) else PLUS)


def shortened(area: int, policy: str) -> str:
    """SHORT_LEVELS: SHORT for a weak area (`weak_areas`) worked fully as PLUS, else `policy`. Only PLUS: its goals
    are SHORT's and more (the same leaders, chests and bosses; groups of GROUP_MIN, the rooms). Never a lighter one:
    PLUS_WAY and ON_THE_WAY leave the far leaders SHORT goes for, COVER (TZ leveling without TZ+) takes no group,
    TRANSIT, CROSSING and BOSS_WAY work less still, FULL_CLEAR is the Full clear kind's own."""
    return SHORT if SHORT_LEVELS and policy == PLUS and area in weak_areas() else policy


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
        if trip is not None and side_done(trip, view):
            trip = plan.next_excursion(view.finished | trip.ends)  # its tour all run, its side level left: over
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
    elif plan.next_excursion(view.finished | trip.ends) is not None or (
        # A tour's side level (Duriel's Lair off the true tomb, routes/tz_routes.py `_sides`) with a toured level not
        # run yet: home by the Town Portal, then its hub's waypoint for the tombs left (2026-10-21)
        trip.tours and area != trip.hub and area not in trip.tours and not toured_out(trip, view)
    ):
        goals.append(Objective(PORTAL_TO_TOWN, 'Town Portal for the next excursion', EXCURSION, area))
    return goals


def toured_out(trip: Excursion, view: GameView) -> bool:
    """Whether every level of `trip`'s tour is done or has had its run (a toured level is done only in the hub again,
    macros/tzloop.py `tour_back`)."""
    runs = dict(view.worked)
    return all(level in view.finished or runs.get(level) for level in trip.tours)


def side_done(trip: Excursion, view: GameView) -> bool:
    """Whether `trip`'s tour went on into a side level after its toured levels (Duriel's Lair off the true tomb,
    routes/tz_routes.py `_sides`, 2026-10-21), that level is done and the tour is all run: the trip is over, its hub not
    gone to again for nothing (the levels after it in the itinerary next)."""
    return (
        bool(trip.tours)
        and trip.terminal not in trip.tours
        and trip.terminal in view.finished
        and toured_out(trip, view)
    )


def toured(trip: Excursion, area: int, finished: frozenset[int]) -> str:
    """' (tomb N of 7)' for a toured level of `trip`, by the levels done before it; '' for any other."""
    if area not in trip.tours:
        return ''
    done = sum(1 for level in trip.tours if level in finished)
    return f' (toured level {done + 1} of {len(trip.tours)})'
