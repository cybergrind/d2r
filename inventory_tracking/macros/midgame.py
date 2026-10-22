"""A service restart in the middle of a game: the KP_6 loop held at a safe point between two legs, the game's state
carried over to the new service, which goes on in the same game (no Save and Exit, no new shard). The player,
2026-10-21 ~14:50: "it would be great if we could pick new code in the middle of the act run, without save/exit, just
continue" (a shard's act game lasts ~45 min; the lobby restart waited a whole game, or cut one short).

- `refusal`: pure. Why the loop is not at a safe point now (None: it is). Safe: the lobby (as the lobby restart), or
  between two legs in a game with the character alive, no panel open, no swap of the Gheed's Fortune under way, nothing
  pending (room in the cube, an item to drop, a fight back, a game given up, a visit cut short), and, in a field level
  (`SAFE` only), no hostile within SIGHT, no valuable in the read nor remembered on the level, no package on the stack.
  `TOWN` takes towns only (a room package's town legs included: the stack is carried).
- `snapshot` / `restore`: the game's state (`Loop`, `Agenda.state`, the route facts, the visit's put-down count),
  keyed by the game's name and the character's unit id (loop.py `GameId`), taken up at the first leg in that game; a
  new game is never matched. Re-derived, not carried: the zone's levels (zonenav.py RESUME's own file), the bosses
  killed and the zone's reads (terror/tracker.py's store), the volatile cells and the loop's items (their files), the
  sightings (runner.py `resume_state`), the plan, the stash view, the hunter's memory of the level.
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
    'WHENS',
    'Moment',
    'refusal',
    'restore',
    'snapshot',
]

# restart.py --when (the service's `restart.request` key `when`): TOWN a safe point in a town, SAFE in a town or a
# field level; LOBBY is restart.py's own wait for the next game's leg (unchanged, the default)
LOBBY, TOWN, SAFE = 'lobby', 'town', 'safe'
WHENS = (TOWN, SAFE)
CANCEL = 'cancel'  # restart.py gave up waiting: the hold is dropped
# Seconds the loop stands at a safe point for the service's restart (it takes it at its next tick, ~0.1 s); past them
# the hold is dropped and the loop goes on: never a stand of its own
PARK_SECONDS = 10.0
PARK_SLICE = 0.1
# A snapshot older than this is not taken up (zonenav.py RESUME_SECONDS: a game name and unit id come round again only
# by chance)
CARRY_SECONDS = 4 * 3600.0
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
)


@dataclass(frozen=True)
class Moment:
    """What the safe point is judged by, read at a leg's start (loop.py `Loop.leg`). `hostile` the nearest hostile's
    distance (None: none read); `valuable` one in the read (runner.py `valuable_left`, 'unread' when the ground was
    not read); `remembered` one of the game's sightings on this level; `stack` the package's goals (agenda.py);
    `pending` the loop's work due before its next leg (names)."""

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


def refusal(when: str, moment: Moment, sight: float) -> str | None:
    """Why `moment` is no safe point for a restart asked `when` (TOWN, SAFE); None: it is one. `sight`: the hunt's
    SIGHT (hunting/base.py), within which a hostile is a fight that may come."""
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
    if moment.stack:
        return f'a package under way ({", ".join(moment.stack)})'
    if moment.hostile is not None and moment.hostile <= sight:
        return f'a hostile {moment.hostile:.0f} away'
    if moment.valuable is not None:
        return f'{moment.valuable} on the ground'
    if moment.remembered is not None:
        return f'{moment.remembered} remembered on the level'
    return None


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
        'elapsed': elapsed,
        'games': loop.games,
        'named': [name for name in NAMED if getattr(loop, name) == game],
        'trips': loop.trips if loop.trip == game else 0,
        'trip_free': loop.trip_free,
        'trip_gained': loop.trip_gained,
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
        loop.agenda = agenda
        for field_name in state.get('named', ()):
            if field_name in NAMED:
                setattr(loop, field_name, name)
        loop.trips = int(state.get('trips') or 0)
        loop.trip_free, loop.trip_gained = state.get('trip_free'), state.get('trip_gained')
        at = state.get('portal_at')
        loop.portal_at = (float(at[0]), float(at[1])) if at else None
        if state.get('route_visits'):
            loop.route_visits = (name, int(state['route_visits']))
        if state.get('visit_units') is not None:
            loop.visit_units = (name, frozenset(int(unit) for unit in state['visit_units']))
        loop.idle = int(state.get('idle') or 0)
        loop.games = max(loop.games, int(state.get('games') or 0))
        elapsed = state.get('elapsed')
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
