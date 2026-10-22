"""The macros' view of a game's bosses: which are in scope, where each lives, which the game has seen and killed.

The player, 2026-10-22: "we need to kill all bosses, no exceptions to that -> they can give a very valuable drops,
especially baal's statue"; "we should always kill act bosses, no need to kill hepasto if it is just travel through";
"make sure that all state is backed by files on filesystem and survives restarts/reloads. <game-id>-<level> as key";
and, of the stash, "one object that is used everywhere ... no copies, no stale records". So the agenda's goals, the
zone's judgement of a level, the way into a level, the zone's rotation, the recoveries and the game's end all ask this
one view (agenda.py `Agenda.bosses`), and it keeps no state of its own: the records are the terror tracker's boss book
(terror/tracker.py `ZoneTracker.boss_note`: '<game-id>-<level>', file-backed, written atomically on each change, read
back at the service's start), the kills its `slain` (`ZoneTracker.killed`, the same that routes/progress.py
`Progress.dead` reads). `attach` takes the tracker from that callable.

Where a boss lives, from the game data and the catalogue, no list of names here (rca/2026-10-22/boss-audit-findings.md):

- `plan(levels)`: before a level is read, the route catalogue's fights on it (routes/catalog/: the act bosses, the
  Countess, Pindleskin, the Council's Ismail...) and the bosses a script brings there (terror/data/elites.json
  `scripted`: the seal bosses, the Throne's waves), for the levels the zone works (never a level only crossed);
- `rooms(area, rooms)`: once its rooms are read (the client holds every room of the level it is in), the super uniques
  the level's presets place (terror/elites.py `fixed_groups`: elites.json `presets`, from the game's monpreset and
  tiles), each at its spot;
- `sight(area, foes)`: a super unique in the read near a boss's spot is taken for it (its unit, then where it was last
  seen, never forgotten for being far: Maffer Dragonhand, 84 units off, was dropped at 45 in 11 games).

The game id (`game_key`): the game's name and the player's unit id (macros/loop.py `GameId`, the log's `game changed:
<name> (player unit <id>)`): names come round again once the count restarts, unit ids do not.
"""

import functools
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol, cast

from inventory_tracking.common import LOG
from inventory_tracking.game.layout import SUPER_FLAG
from inventory_tracking.game.records import Monster
from inventory_tracking.levels.geometry import Point
from inventory_tracking.levels.presets import display_name


# The player, 2026-10-22: "we need to kill all bosses, no exceptions to that". True: the ledger is asked by its
# consumers (agenda.py BOSS_GOALS, zonenav.py BOSSES_HOLD, tzloop.py BOSS_STAYS, hunting/choice.py BOSS_ROTATION,
# running/recovery.py BOSS_RECOVERY). False: every consumer as before
LEDGER = True
BIND_NEAR = 40.0  # world units from a boss's spot within which a super unique in the read is taken for it


class Book(Protocol):
    """The boss book's store (terror/tracker.py `ZoneTracker`)."""

    def boss_game(self, game: str | None) -> None: ...

    def boss_note(
        self, area: int, name: str, *, place: tuple[float, float] | None = None, unit: int | None = None,
        seen: bool = False, by: str = '', tried: bool = False,
    ) -> bool: ...  # fmt: skip

    def boss_book(self) -> list[tuple[int, str, dict]]: ...

    def killed(self) -> frozenset[str]: ...


@dataclass(frozen=True)
class Boss:
    """A boss of the book: `name` (superuniques.txt, or the route's fight), its level, where it lives (its preset's
    spot, then where it was last seen; None: the route's mark is the way to it), the unit taken for it, seen, how
    known ('route', 'script' or 'rooms'), the recoveries kept for it (`BossLedger.tried`)."""

    name: str
    area: int
    place: Point | None = None
    unit: int | None = None
    seen: bool = False
    known_by: str = ''
    tries: int = 0


class BossLedger:
    """The view: no state but the book it reads (`attach`) and the game it is begun for."""

    def __init__(self, book: Book | None = None) -> None:
        self.book = book
        self.game: str | None = None

    def attach(self, source: object) -> None:
        """The book: a `Book`, or a bound method of one (routes/progress.py `Progress.dead`, the tracker's `killed`);
        anything else: none, and nothing is alive."""
        book = getattr(source, '__self__', source)
        found = all(hasattr(book, name) for name in ('boss_game', 'boss_note', 'boss_book', 'killed'))
        self.book = cast('Book', book) if found else None
        if self.book is not None:
            self.book.boss_game(self.game)

    def begin(self, game: object) -> None:
        """The game the book is written for (`game_key`)."""
        self.game = game_key(game)
        if self.book is not None:
            self.book.boss_game(self.game)

    def plan(self, levels: Iterable[int]) -> None:
        """The bosses of `levels` known before they are read (`expected`)."""
        if not LEDGER or self.book is None:
            return
        for area in levels:
            for name, how in expected(area):
                self.book.boss_note(area, name, by=how)

    def rooms(self, area: int, rooms: Sequence) -> None:
        """The super uniques `area`'s read `rooms` place (terror/elites.py `fixed_groups`), each at its spot."""
        if not LEDGER or self.book is None or not rooms:
            return
        from inventory_tracking.terror.elites import fixed_groups  # late: the terror package is heavy

        known = {name for level, name, _ in self.book.boss_book() if level == area}
        for group in fixed_groups(area, rooms):
            if group.kind != 'super' or not group.name:
                continue
            place = (group.x, group.y) if group.x is not None and group.y is not None else None
            if group.name not in known:
                LOG.info('Macro: bosses: %s lives in %s%s', group.name, display_name(area),
                         f' at ({place[0]:.0f}, {place[1]:.0f})' if place is not None else '')  # fmt: skip
            self.book.boss_note(area, group.name, place=place if group.name not in known else None, by='rooms')

    def sight(self, area: int, foes: Sequence[Monster]) -> None:
        """A super unique of `foes` (the read's hostiles of `area`) within BIND_NEAR of a live boss's place is taken
        for it; the unit taken is followed where it goes."""
        if not LEDGER or self.book is None:
            return
        units = {m.unit_id: m for m in foes}
        bosses = [boss for boss in self.alive() if boss.area == area]
        taken = {boss.unit for boss in self.bosses() if boss.unit is not None}
        for boss in bosses:
            if boss.unit is not None and boss.unit in units:
                found = units[boss.unit]
                self.book.boss_note(area, boss.name, place=(found.x, found.y), seen=True)
                continue
            if boss.place is None or boss.unit is not None:
                continue
            spot = boss.place
            near = [
                m
                for m in foes
                if m.flags & SUPER_FLAG and m.unit_id not in taken and math.dist(spot, (m.x, m.y)) <= BIND_NEAR
            ]
            if near:
                found = min(near, key=lambda m: math.dist(spot, (m.x, m.y)))
                self.book.boss_note(area, boss.name, place=(found.x, found.y), unit=found.unit_id, seen=True)
                taken.add(found.unit_id)

    def bosses(self) -> list[Boss]:
        """Every boss of this game's book, killed or not."""
        if self.book is None:
            return []
        return [
            Boss(name, area, place_of(record.get('place')), unit_of(record.get('unit')), bool(record.get('seen')),
                 str(record.get('by', '')), unit_of(record.get('tries')) or 0)
            for area, name, record in self.book.boss_book()
        ]  # fmt: skip

    def alive(self, levels: Iterable[int] | None = None) -> list[Boss]:
        """The bosses of `levels` (all: None) the tracker has not killed; none without a book or the switch off."""
        if not LEDGER or self.book is None:
            return []
        dead = self.book.killed()
        wanted = None if levels is None else frozenset(levels)
        return [boss for boss in self.bosses() if boss.name not in dead and (wanted is None or boss.area in wanted)]

    def alive_in(self, area: int) -> list[Boss]:
        return self.alive((area,))

    def tried(self, bosses: Iterable[Boss]) -> None:
        """A recovery kept the game for `bosses` (macros/running/recovery.py BOSS_RECOVERY): counted in the book."""
        if self.book is None:
            return
        for boss in bosses:
            self.book.boss_note(boss.area, boss.name, tried=True)


def place_of(found: object) -> Point | None:
    """A stored place ([x, y]) as a point; None for none or a malformed one."""
    if isinstance(found, (list, tuple)) and len(found) == 2 and all(isinstance(v, (int, float)) for v in found):
        return (float(found[0]), float(found[1]))
    return None


def unit_of(found: object) -> int | None:
    return found if isinstance(found, int) and not isinstance(found, bool) else None


def game_key(game: object) -> str | None:
    """'<name>#<player unit id>' of a macros/loop.py `GameId`, a game name as it is, None for none."""
    if game is None:
        return None
    name, player = getattr(game, 'name', None), getattr(game, 'player', None)
    if isinstance(name, str) and isinstance(player, int):
        return f'{name}#{player}'
    return str(game)


def said(bosses: Iterable[Boss]) -> str:
    """'Shenk the Overseer (Bloody Foothills), Baal (The Worldstone Chamber)'."""
    return ', '.join(f'{boss.name} ({display_name(boss.area)})' for boss in bosses)


@functools.cache
def expected(area: int) -> tuple[tuple[str, str], ...]:
    """(name, how known) of the bosses of level `area` before it is read: the route catalogue's fights on it, then
    the bosses a script brings there (terror/data/elites.json `scripted`)."""
    from inventory_tracking.routes.catalog import ROUTES  # late: the catalogue imports the macros' models
    from inventory_tracking.routes.model import FIGHT
    from inventory_tracking.terror.elites import table

    found: dict[str, str] = {}
    for route in ROUTES:
        for script in route.scripts:
            if script.area == area:
                found.update((stage.boss, 'route') for stage in script.stages if stage.kind == FIGHT and stage.boss)
    for name in table().scripted.get(area, ()):
        found.setdefault(name, 'script')
    return tuple(found.items())


def stop_line(bosses: Sequence[Boss], why: str) -> str:
    """The loop's stop line naming the bosses alive (the last resort: the loop stops where it is for the player)."""
    return f'{why}: {said(bosses)} alive: the loop stops here for the player'
