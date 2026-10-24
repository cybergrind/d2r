"""A service restart in the middle of a game: the KP_6 loop held at a safe point between two legs, the game's state
carried over to the new service, which goes on in the same game (no Save and Exit, no new shard). The player,
2026-10-21 ~14:50: "it would be great if we could pick new code in the middle of the act run, without save/exit, just
continue" (a shard's act game lasts ~45 min; the lobby restart waited a whole game, or cut one short).

- `refusal`: pure. Why the loop is not at a safe point now (None: it is). Safe: the lobby (as the lobby restart), or
  between two legs in a game with the character alive, no panel open, no swap of the Gheed's Fortune under way, nothing
  pending (room in the cube, an item to drop, a fight back, a game given up, a visit cut short), and, in a field level
  (`SAFE` only), no hostile within SIGHT, no valuable in the read nor remembered on the level, no package on the stack.
  `TOWN` takes towns only (a room package's town legs included: the stack is carried). `TRIP` takes a town at once,
  and in a field level its next safe moment (`SAFE`'s, and no boss alive on the level, no Herald known on it, the kind
  able to make the trip): there the loop casts Town Portal and stands in town for the restart (`restart_package`), and
  the new service goes back through the portal (the record carries the package and the portal's place).
- `snapshot` / `restore`: the game's state (`Loop`, `Agenda.state`, the route facts, the visit's put-down count),
  keyed by the game's name and the character's unit id (loop.py `GameId`), taken up at the first leg in that game; a
  new game is never matched.
- `keep` / `take_up` (RECORD): that state is the 'loop' part of the game's one record (terror/tracker.py
  RECORD_SECONDS, the store the boss book is in), written at each leg's start and where a leg spends what is never
  done twice (a shard, an overflow shard, a level run, a trip begun), so a crash costs no shard either; the
  valuables remembered are its 'sightings' part (macros/sightings.py). Re-derived from the other records, not carried:
  the bosses and the kills (the boss book and the tracker's games), the volatile cells and the loop's items (their
  files), the plan (tzloop.py `zone_of`: the agenda's acts, the book's live bosses, the zone read now), the stash
  view, the hunter's memory of the level. `migrate`: the old restart blob's 'game' and 'sightings' written into the
  record once (LEGACY_BLOB).
"""

import math
import time
from collections.abc import Iterable
from dataclasses import dataclass, replace

from inventory_tracking.common import LOG


__all__ = [
    'CANCEL',
    'CARRY_SECONDS',
    'PARK_SECONDS',
    'SAFE',
    'TOWN',
    'TRIP',
    'TRIP_BACK',
    'TRIP_PORTAL',
    'TRIP_TRIES',
    'WHENS',
    'Moment',
    'refusal',
    'restart_package',
    'restore',
    'snapshot',
]

# restart.py --when (the service's `restart.request` key `when`): TOWN a safe point in a town, SAFE in a town or a
# field level, TRIP a town, else a field level's safe moment and a Town Portal to stand in town; LOBBY is restart.py's
# own wait for the next game's leg (unchanged, the default)
LOBBY, TOWN, SAFE, TRIP = 'lobby', 'town', 'safe', 'trip'
WHENS = (TOWN, SAFE, TRIP)
# TRIP (the player, 2026-10-24 ~13:35: "we need to restart in the middle of the run (on safe spot and time, maybe
# something like -> go to town and restart -> return back)"; `town` waited ~2 min at 12:37:56 for the loop's own next
# town visit, 5-15+ min in a terror zone game): the package pushed at the field level's safe moment (loop.py
# `Loop.restart_trip`): Town Portal, the stand in town (TOWN's), back through the portal (`Loop.back_after_restart`:
# the portal found by the place the character came to in town, `Loop.portal_at` in the record; gone, the loop's own way
# back from town). TRIP_TRIES such trips a game at most (a town stand refused sends the loop back through the portal)
TRIP_PORTAL = 'Town Portal for the restart'
TRIP_BACK = 'back through the portal after the restart'
TRIP_TRIES = 2
CANCEL = 'cancel'  # restart.py gave up waiting: the hold is dropped
# Seconds the loop stands at a safe point for the service's restart (it takes it at its next tick, ~0.1 s); past them
# the hold is dropped and the loop goes on: never a stand of its own
PARK_SECONDS = 10.0
PARK_SLICE = 0.1
# A snapshot older than this is not taken up (zonenav.py RESUME_SECONDS: a game name and unit id come round again only
# by chance)
CARRY_SECONDS = 4 * 3600.0
# The game's state is its one record (`keep`, `take_up`, 2026-10-22, rca/2026-10-22/restart-zone-findings.md): written
# as it changes, read at the first leg in the game, so a restart planned or not goes on in it. False: nothing kept,
# every game begun afresh (the lobby restart's way)
RECORD = True
# The restart blob (appraisal/service.py `write_resume`) of a service before RECORD: its 'game' and 'sightings' written
# into the record when it has none (`migrate`), for the release that deploys it (game cyberg65 was played on the old
# code with a shard spent). False: not read
LEGACY_BLOB = True
# A record written before tzloop.py POLICY_NOW (2026-10-22, rca/2026-10-22/tombs-policy-findings.md) keeps no policy its
# levels were worked under (`Agenda.worked_under`): each level entered, neither explored by a tour nor cleared, is
# taken up as worked under a policy not known (zonenav.py EARLIER, `policies_unknown`), so the zone judges it afresh
# under a touring policy (tzloop.py `rework_levels`), its block for being left unfinished by the hub's rule of before
# the 20:04 fix too: game cyberg65's tombs, worked on the way for Duriel and owed again under act 2's shard (21:40:32).
# A level explored or cleared keeps its verdict. False: taken up as the policy now's, as before
POLICY_UNKNOWN = True
# The loop's fields that hold the game's name (loop.py `Loop`): carried as whether they name the game
NAMED = (
    'done',
    'visited',
    'visiting',
    'prebuffed',
    'fortressed',
    'returned',
    'trip',
    'room_tried',
    'dropped',
    'restart_trip',
)


@dataclass(frozen=True)
class Moment:
    """What the safe point is judged by, read at a leg's start (loop.py `Loop.leg`). `hostile` the nearest hostile's
    distance (None: none read); `valuable` one in the read (runner.py `valuable_left`, 'unread' when the ground was
    not read); `remembered` one of the game's sightings on this level; `stack` the package's goals (agenda.py);
    `pending` the loop's work due before its next leg (names). TRIP's: `arena` the boss alive the route fights on the
    level ('' none), `herald` one known on it, `trips` whether the kind makes the portal trip (a pushed package between
    its legs: loop.py `Kind.agenda`, `packaged`), `tripped` the portal trips made for the restart in this game."""

    in_game: bool
    in_town: bool = False
    dead: bool = False
    panels: tuple[str, ...] = ()
    hostile: float | None = None
    valuable: str | None = None
    remembered: str | None = None
    stack: tuple[str, ...] = ()
    swap: bool = False
    pending: tuple[str, ...] = ()
    arena: str = ''
    herald: str | None = None
    trips: bool = True
    tripped: int = 0


def refusal(when: str, moment: Moment, sight: float) -> str | None:
    """Why `moment` is no safe point for a restart asked `when` (TOWN, SAFE, TRIP); None: it is one (for TRIP in a
    field level: the moment for the portal trip). `sight`: the hunt's SIGHT (hunting/base.py), within which a hostile
    is a fight that may come."""
    if not moment.in_game:
        return None  # the lobby: the lobby restart's own moment
    if moment.dead:
        return 'the character is dead'
    if moment.panels:
        return f'{", ".join(moment.panels)} open'
    if moment.swap:
        return "the Gheed's swap is under way"
    if moment.pending:
        return f'{", ".join(moment.pending)} due'
    if moment.in_town:
        return None  # nothing attacks in a town; the room package's legs are carried (`Agenda.state`)
    if when == TOWN:
        return 'not in a town'
    if when == TRIP and not moment.trips:
        return 'no portal trip in this kind: a town waited for'
    if when == TRIP and moment.tripped >= TRIP_TRIES:
        return f'{moment.tripped} portal trips made for the restart in this game: a town waited for'
    if moment.stack:
        return f'a package under way ({", ".join(moment.stack)})'
    if moment.hostile is not None and moment.hostile <= sight:
        return f'a hostile {moment.hostile:.0f} away'
    if moment.valuable is not None:
        return f'{moment.valuable} on the ground'
    if moment.remembered is not None:
        return f'{moment.remembered} remembered on the level'
    if when == TRIP and moment.arena:
        return f'{moment.arena} alive on the level'
    if when == TRIP and moment.herald is not None:
        return f'{moment.herald} known on the level'
    return None


def restart_package(area: int) -> tuple:
    """TRIP's package from field level `area`: Town Portal to its town, back through the portal after the restart, on
    (agenda.py `Objective`s; no visit, no waypoint: the stand is in the portal's town)."""
    from inventory_tracking.macros.agenda import PORTAL_TO_TOWN, RESUME, STACK, THROUGH_PORTAL, Objective, town_of

    return (
        Objective(PORTAL_TO_TOWN, TRIP_PORTAL, STACK, area, to=town_of(area)),
        Objective(THROUGH_PORTAL, TRIP_BACK, STACK, to=area),
        Objective(RESUME, 'continue the run', STACK, area),
    )


def sight() -> float:
    """The hunt's SIGHT (hunting/base.py): a hostile within it is a fight that may come. Late: the hunt's modules import
    macros/loop.py, which imports this one."""
    from inventory_tracking.macros.hunting.base import SIGHT

    return SIGHT


def nearest(here: tuple[float, float], places: Iterable[tuple[float, float]]) -> float | None:
    """The distance to the nearest of `places`, None with none."""
    return min((math.dist(here, place) for place in places), default=None)


def snapshot(loop, progress, now: float | None = None) -> dict | None:
    """The game's state the next service takes up (`restore`), None out of a game or with the game unread. `now`:
    time.monotonic()."""
    from inventory_tracking.macros import visit
    from inventory_tracking.macros.loop import GameId

    seen = loop.game_id
    if not isinstance(seen, GameId):
        return None
    game = seen.name
    now = time.monotonic() if now is None else now
    elapsed = now - loop.seen[1] if loop.seen is not None and loop.seen[0] == game else None
    facts = progress.facts if progress is not None and progress.game == game else None
    return {
        'game': [seen.name, seen.player],
        'at': time.time(),
        # The game's start on the wall clock (the record is written as it changes, not once at its restart)
        'began': round(time.time() - elapsed, 1) if elapsed is not None else None,
        'games': loop.games,
        'named': [name for name in NAMED if getattr(loop, name) == game],
        'trips': loop.trips if loop.trip == game else 0,
        'trip_free': loop.trip_free,
        'trip_gained': loop.trip_gained,
        # The merc's and the belt's trips (macros/merc.py `Trips`, BELT_TRIPS_BY_GAIN): a restart neither resets nor
        # loses them (2026-10-22)
        'merc_trips': loop.merc_trips.state() if loop.merc_trips.game == game else None,
        'portal_at': list(loop.portal_at) if loop.portal_at is not None else None,
        'route_visits': loop.route_visits[1] if loop.route_visits is not None and loop.route_visits[0] == game else 0,
        'visit_units': sorted(loop.visit_units[1])
        if loop.visit_units is not None and loop.visit_units[0] == game
        else None,
        'idle': loop.idle,
        'agenda': loop.agenda.state(),
        'facts': facts_state(facts) if facts is not None else None,
        'put_down': visit._down['items'] if visit._down.get('game') == game else 0,
    }


def facts_state(facts) -> dict:
    """The route facts (routes/progress.py `Facts`) as JSON; `dead` is the tracker's (its own store)."""
    return {
        'entered': sorted(facts.entered),
        'used': sorted([area, mark, list(place)] for area, mark, place in facts.used),
        'finished': sorted([area, mark] for area, mark in facts.finished),
        'stood': sorted([area, mark] for area, mark in facts.stood),
        'looted': sorted(facts.looted),
    }


def restore(loop, world, progress, state: dict, now: float | None = None) -> bool:
    """`state` (`snapshot`) taken up at the loop's first leg after a restart when `world` is the same game (its name
    and the character's unit id), not older than CARRY_SECONDS; whether it was. `now`: time.monotonic()."""
    from inventory_tracking.macros import visit
    from inventory_tracking.macros.agenda import Agenda
    from inventory_tracking.macros.loop import GameId

    player = world.player
    if not world.in_game or player is None:
        return False
    try:
        name, unit = str(state['game'][0]), int(state['game'][1])
        if (name, unit) != (world.game_name, player.unit_id) or time.time() - float(state['at']) > CARRY_SECONDS:
            return False
        game = GameId(name, unit)
        now = time.monotonic() if now is None else now
        agenda = Agenda()  # a malformed state leaves the loop's own as it was
        agenda.take_up(state['agenda'], game)
        if POLICY_UNKNOWN and 'worked_under' not in state['agenda']:
            policies_unknown(agenda)
        loop.agenda = agenda
        for field_name in state.get('named', ()):
            if field_name in NAMED:
                setattr(loop, field_name, name)
        loop.trips = int(state.get('trips') or 0)
        loop.trip_free, loop.trip_gained = state.get('trip_free'), state.get('trip_gained')
        if state.get('merc_trips') is not None:
            loop.merc_trips.take_up(name, state['merc_trips'])  # in place: the merc watch counts in the same object
        at = state.get('portal_at')
        loop.portal_at = (float(at[0]), float(at[1])) if at else None
        if state.get('route_visits'):
            loop.route_visits = (name, int(state['route_visits']))
        if state.get('visit_units') is not None:
            loop.visit_units = (name, frozenset(int(unit) for unit in state['visit_units']))
        loop.idle = int(state.get('idle') or 0)
        loop.games = max(loop.games, int(state.get('games') or 0))
        began = state.get('began')
        elapsed = time.time() - float(began) if began is not None else state.get('elapsed')  # the old blob's
        if elapsed is not None:
            # The game's clock goes on (loop.py `overdue`, ACT_SECONDS): the cap counts from the game's start
            loop.seen = (name, now - float(elapsed))
        if progress is not None and state.get('facts') is not None:
            take_facts(progress, name, player.area, state['facts'])
        if state.get('put_down'):
            visit._down['game'], visit._down['items'] = name, int(state['put_down'])
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as error:
        LOG.info('Macro: loop: the game kept over the restart is not taken up: %s', error)
        return False
    # The watch tools read it (d2-loop-watch logwords.py CARRIED)
    LOG.info(
        'Macro: loop: game %s taken up after a restart: %.0f s into it, levels done %s, shard %s (acts %s%s), '
        'trips %d, package %s',
        game,
        float(elapsed) if elapsed is not None else -1.0,
        sorted(agenda.finished),
        agenda.shard,
        list(agenda.acts),  # in their order (actloop.py OVERFLOW: the kind's act first)
        f'; over the limit {dict(sorted(agenda.overflow.items()))}' if agenda.overflow else '',
        loop.trips,
        [goal.label for goal in reversed(agenda.stack)] or 'none',
    )
    return True


def policies_unknown(agenda) -> None:
    """POLICY_UNKNOWN: each level of `agenda` (a record's, kept with no `worked_under`) entered, neither explored nor
    cleared before the restart (`kept`), noted as worked under a policy not known (zonenav.py EARLIER); said."""
    from inventory_tracking.macros.zonenav import EARLIER

    levels = sorted(agenda.entered - agenda.explored - agenda.kept)
    for level in levels:
        agenda.worked_under.setdefault(level, EARLIER)
    if levels:
        # The watch tools may read it (d2-loop-watch logwords.py)
        LOG.info('Macro: loop: the record kept no policy: levels %s taken up as worked under one not known', levels)


def take_facts(progress, game: str, area: int | None, kept: dict) -> None:
    """The route facts kept (`facts_state`) merged into `progress`'s for `game` (its own note first: the poll's may
    not have come yet)."""
    if progress.game != game:
        progress.note(game, area)
    facts = progress.facts
    progress.facts = replace(
        facts,
        entered=facts.entered | {int(level) for level in kept['entered']},
        used=facts.used | {(int(a), str(m), (float(p[0]), float(p[1]))) for a, m, p in kept['used']},
        finished=facts.finished | {(int(a), str(m)) for a, m in kept['finished']},
        stood=facts.stood | {(int(a), str(m)) for a, m in kept['stood']},
        looted=facts.looted | {int(level) for level in kept['looted']},
    )


def key_of(game) -> str | None:
    """The record's key of `game` (loop.py `GameId`): macros/bossledger.py `game_key`, the boss book's."""
    from inventory_tracking.macros.bossledger import game_key
    from inventory_tracking.macros.loop import GameId

    return game_key(game) if isinstance(game, GameId) else None


def keep(loop, progress=None) -> None:
    """RECORD: the game's state (`snapshot`) as its record's 'loop' part, written when it changed (its 'at' aside).
    `progress`: the route facts' (the leg's, else the one the loop's last leg had: `Loop.facts_from`)."""
    records = getattr(loop, 'records', None)
    if not RECORD or records is None:
        return
    progress = progress if progress is not None else getattr(loop, 'facts_from', None)
    state = snapshot(loop, progress)
    key = key_of(loop.game_id)
    if state is None or key is None:
        return
    records.record_note(key, 'loop', {name: value for name, value in state.items() if name != 'at'})


def take_up(loop, world, progress) -> bool:
    """RECORD: at the loop's first leg in a game (its key not yet looked at by this loop: `Loop.recorded`), the game's
    record taken up (`restore`), before the agenda's `begin` would start the game afresh (a second shard for an act
    terrorized); whether it was."""
    records = getattr(loop, 'records', None)
    key = key_of(loop.game_id)
    if not RECORD or records is None or key is None or key == loop.recorded:
        return False
    loop.recorded = key
    entry = records.record(key)
    part = entry.get('loop')
    if not isinstance(part, dict):
        return False
    return restore(loop, world, progress, {**part, 'at': entry['at']})


def migrate(records, blob: dict) -> None:
    """LEGACY_BLOB: the old restart blob's 'game' (`snapshot`, its clock 'elapsed' at 'at') and 'sightings'
    (macros/sightings.py `Sightings.state`) written into the game's record when it has no such part."""
    if not (RECORD and LEGACY_BLOB) or records is None:
        return
    game, found = blob.get('game'), blob.get('sightings')
    try:
        if isinstance(game, dict) and game.get('game'):
            key = f'{game["game"][0]}#{int(game["game"][1])}'
            if 'loop' not in records.record(key):
                state = {name: value for name, value in game.items() if name not in ('at', 'elapsed')}
                elapsed = game.get('elapsed')
                state['began'] = round(float(game['at']) - float(elapsed), 1) if elapsed is not None else None
                records.record_note(key, 'loop', state)
                # The watch tools may read it (d2-loop-watch logwords.py CARRIED)
                LOG.info("Macro: loop: game %s: the old restart blob's state written into its record", key)
        if isinstance(found, dict) and found.get('game'):
            key = f'{found["game"][0]}#{int(found["game"][1])}'
            if 'sightings' not in records.record(key):
                records.record_note(key, 'sightings', found)
                LOG.info("Macro: loop: game %s: the old restart blob's sightings written into its record", key)
    except (KeyError, TypeError, ValueError, IndexError) as error:
        LOG.info("Macro: loop: the old restart blob's game is not taken: %s", error)
