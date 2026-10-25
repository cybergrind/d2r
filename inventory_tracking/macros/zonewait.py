"""The wait for a terror zone the loop cannot play, filled with Worldstone Keep games (ZONE_WAIT_WSK, 2026-10-25).

At 12:04:27 on 2026-10-25 the zone turned to Act1-MooMooFarm (its only way in is the red portal Wirt's Leg opens: no
catalogue excursion), and tzloop.py `choose` left the game for the lobby to wait 1553 s for the next zone (cause
'zone', stops.py LEAVE, `Loop.cooling`): 26 minutes of no exp and no drop. The player's goal: "our goal is to have
best exp/hour we can"; asked what the loop should do while it waits, the player, ~12:06: "do worldstone keep, if we get
some shard - good, if not - next game".

A filler game is a zone game whose plan is `filler_plan`: the Act 5 waypoint to The Worldstone Keep Level 2, its level
run, the Baal route's stairs down to Level 3 and its level run, then the game's end, as any zone game played by the
graph (macros/zonenav.py): the same legs, pickup, safety and room rules. Level 3 is taken because it is the route's one
verified hop from the waypoint's level (a stage `enter Next level`, no town or waypoint connector): no travel but the
stairs, and the zone's graph climbs nothing back. Level 1 (the `Worldstone Keep 1` route's way up from Level 2's
waypoint) and the Throne and the Chamber (Baal's waves and fight: minutes a game, his kill holding the game's end,
tzloop.py BOSS_STAYS) are left out. The levels are not terrorized: their monsters are the area's own Hell level, which
the safety prices already (combat/mechanics/life.py `monster_level`); the loop's levels-left rules for a zone that
moved on (running/legs.py `_agenda_policy` ZONE_LEFT, tzloop.py ZONE_LEFT_NO_WAY, the portal's plain fight) pass the
filler's levels (`filler`).

`fill` decides a leg's plan: a filler game begins in town when the zone read has no excursion and the wait to the next
zone (tzloop.py `zone_wait`) is longer than one filler game (`game_seconds`); a shorter wait is the lobby's, as before.
The game is one of the filler till its end; when the zone read turns playable under it (the next :00/:30 turn, or a
Worldstone Shard over the limit used by actloop.py's own rules, which terrorizes its act), the filler is dropped at once
and the game plays that zone from where it stands. A game taken up after a service restart on a filler level is one
again. No shard is used here: only actloop.py's rules spend one.
"""

import functools

from inventory_tracking.common import LOG
from inventory_tracking.levels.presets import display_name
from inventory_tracking.macros import zonenav
from inventory_tracking.macros.tzroutine import Excursion, Itinerary, trip_levels, trips_said
from inventory_tracking.routes.tz_groups import ActiveZone
from inventory_tracking.routes.tz_routes import zone_route_plan


# ZONE_WAIT_WSK (2026-10-25, the player ~12:06: "do worldstone keep, if we get some shard - good, if not - next game").
# True: while the zone read is not playable and the next zone is more than `game_seconds` away, the loop plays
# Worldstone Keep games (LEVELS) instead of waiting in the lobby; each game said (FILLER_SAID). False: the game is left
# and the next zone waited for in the lobby, as before (tzloop.py `choose`, cause 'zone', stops.py LEAVE). On 2026-10-25
# ~12:55, the player's ruling ~12:06 (the coordinator's go; rca/2026-10-25/zone-wait-wsk-findings.md)
ZONE_WAIT_WSK = True
# The filler's levels (levels.txt ids): The Worldstone Keep Level 2 (its waypoint) and Level 3 (the Baal route's stairs)
LEVELS = (129, 130)
# The filler's plan's zone name: no installed zone's, so no rule for a rotating or a shard act's zone takes it
# (tzloop.py `turned_levels`, `unrun_levels`, zonenav.py `act_levels`)
NAME = 'Filler-WorldstoneKeep'
# A game's own seconds besides its levels' (zonenav.py `level_seconds`): the game made and loaded, the waypoint, Save
# and Exit. Terrorized, Levels 2 and 3 took 55-230 s together (the experience lines of 10-20..10-24)
GAME_OVERHEAD = 60.0
# The watch tools read it (d2-loop-watch logwords.py ZONE_FILLER): (the zone read, why it is not playable, the seconds
# to the next zone, the levels)
FILLER_SAID = 'Macro: zone wait: a Worldstone Keep game while %s is not playable (%s), %.0f s to the next zone: %s'
FILLER_TAKEN = 'Macro: zone wait: a Worldstone Keep game taken up in %s (%s is not playable)'
FILLER_ENDS = 'Macro: zone wait: the Worldstone Keep game ends its filler: %s is playable, played from %s'
FILLER_NOT = 'Macro: zone wait: no Worldstone Keep game: %.0f s to the next zone, one takes about %.0f s'

_games: dict[object, str] = {}  # the filler game (`Agenda.game`) -> the zone it fills for; the current game's only


def game_seconds() -> float:
    """One filler game's estimated seconds: its levels' (zonenav.py `level_seconds`) and GAME_OVERHEAD."""
    return sum(zonenav.level_seconds(level) for level in LEVELS) + GAME_OVERHEAD


@functools.cache
def filler_plan() -> Itinerary | None:
    """The filler's itinerary: the catalogue's trips over LEVELS (routes/tz_routes.py `zone_route_plan`), each level
    worked; None when a level has no unblocked trip (no filler then: the wait, as before)."""
    zone = ActiveZone(NAME, LEVELS, frozenset(LEVELS))
    found = zone_route_plan(zone)
    trips = tuple(
        Excursion(trip.route, trip.waypoint, nodes, frozenset(nodes) & zone.core)
        for trip in found.excursions
        if not trip.blockers and (nodes := trip_levels(trip))
    )
    covered = frozenset(level for trip in trips for level in trip.zone)
    if covered != zone.core:
        LOG.info('Macro: zone wait: no Worldstone Keep plan: %s not covered by a trip',
                 sorted(zone.core - covered))  # fmt: skip
        return None
    return Itinerary(NAME, frozenset(level for trip in trips for level in trip.areas), trips)


def filler(plan: object) -> bool:
    """Whether `plan` is the filler's (`filler_plan`): its levels are worked though not terrorized."""
    return isinstance(plan, Itinerary) and plan.zone == NAME


def fill(game: object, read: Itinerary, in_town: bool, area: int, wait: float) -> Itinerary | None:
    """The plan of this leg of `game` in place of the zone `read` (the tracker's, tzloop.py `zone_of`): the filler's
    while `read` has no excursion and the game is a filler game, begun here in town with `wait` s (tzloop.py
    `zone_wait`) to the next zone over `game_seconds`, or taken up on a filler level (a restart); said once a game.
    None: `read` as before (the switch off, `read` playable, the wait too short, a field level of another game)."""
    if not ZONE_WAIT_WSK:
        return None
    filling = _games.get(game)
    if read.excursions:
        if filling is not None:
            del _games[game]
            # The watch tools may read it (d2-loop-watch logwords.py ZONE_FILLER_ENDS)
            LOG.info(FILLER_ENDS, read.zone, display_name(area))
        return None
    plan = filler_plan()
    if plan is None:
        return None
    if filling is None:
        if in_town and wait <= game_seconds():
            LOG.info(FILLER_NOT, wait, game_seconds())
            return None
        if not in_town and area not in plan.areas:
            return None  # the zone moved on under another game: its end, as before
        _games.clear()
        _games[game] = read.zone
        reasons = '; '.join(sorted({why for _, why in read.skipped})) or 'none'
        if in_town:
            LOG.info(FILLER_SAID, read.zone, reasons, wait, trips_said(plan.excursions))
        else:
            LOG.info(FILLER_TAKEN, display_name(area), read.zone)
    return plan
