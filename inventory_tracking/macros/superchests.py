"""The super chests a level run opens (hunting/choice.py: the agenda's CHEST tier, a full clear's chest, and the level's
chest spots before the run's own goal).

What counts, by the game's files (third-parties/d2data/json/objects.json, objpreset.json):
- the glowing chests: objects.txt rows drawn with an overlay over a chest's drops (`Overlay` 1, `PopulateFn` 3),
  bundled in data/glowing_chests.json (`build_glowing`): ConsolationChest 397 ("sparklychest"), SpecialChest100 455
  and the quest chests (the Horadric Cube's, Scroll's, Staff of Kings', Khalim's), which drop a chest's items too.
  The Staff of Kings' chest stands on Coldworm's mark in Maggot Lair 3 ('Lair Tight Spot S', the player, 2026-10-20:
  "in coldworm's room there was a glowing chest - we always should try to open such chests whenever we encountered
  them"). It was never read before: game/decode.py `USED` left the quest chests out (build_containers.py);
- a chest the game rolls at a preset's `PlaceUniqueChest` spot (levels/model.py UNIQUE_CHEST,
  levels/data/preset_objects.json): Maggot Lair's sparkling chests stand there as TombChest1/2 (87, 88, InitFn 3, a
  plain chest's class). All 26 seen in the six Maggot Lair takes of 06:30-06:35Z on 2026-10-20 stood on such a spot
  to the unit. Lower Kurast's camp chests are JungleChest (181, 183) at the same spots (macros/shacks.py).

The level's spots are known from its rooms (every Room2 is read at entry) before a chest object loads. `LEVEL_SPOTS`:
each is gone to when the agenda has no target, before the route's own goal (rca/2026-10-20/superchest-findings.md).
A locked chest takes one of the keys carried.
"""

import json
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.game.decode import containers, glowing_chests
from inventory_tracking.game.records import Thing
from inventory_tracking.levels.geometry import Point
from inventory_tracking.levels.model import SUPER_CHEST, UNIQUE_CHEST, Room, Target
from inventory_tracking.levels.presets import display_name, object_spots
from inventory_tracking.macros.build import Intent
from inventory_tracking.macros.goals import REACH, USE_NEAR, Goal
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import USE


__all__ = [
    'BOOK',
    'ENABLED',
    'GLOWING',
    'LEVEL_SPOTS',
    'Book',
    'build_glowing',
    'is_super',
    'level_goal',
    'level_spots',
    'mark_use',
    'super_chests',
    'unique_spots',
]

# The player, 2026-10-20 ~09:35 (TZ leveling in the Maggot Lair): "we need to open superchests when we encountering
# them". False: the glowing chest 397 alone, as before.
ENABLED = True
# The player, 2026-10-20 ~09:52: "nope, in maggot layer 3 superchest wasn't opened" (the treasure room's 97 units off
# the way to Coldworm) and "we always should try to open such chests whenever we encountered them". True: every chest
# spot of the level and every super chest the read shows is gone to before the run's own goal. False: only those
# within agenda.py CHEST_NEAR.
LEVEL_SPOTS = True
GLOWING_FILE = Path(__file__).parent / 'data' / 'glowing_chests.json'
GLOWING = frozenset(glowing_chests())
SPOT = 1.0  # units: a container this near a unique-chest spot is that spot's (the takes: 0.0)
SUPER_TRIES = 3  # hunting/base.py SUPER_TRIES (a test holds them equal): a chest clicked this often is left
# Units: at a spot this near with no chest read there, the spot is empty (another player's, or none rolled). The client
# holds a room or two around the character (card_goal.py OBJECT_NEAR), so a chest there is read long before.
GONE_NEAR = 15.0
ARRIVE = 10.0  # units: a spot not read yet is gone to this near
SPOT_SECONDS = 45.0  # a spot gone for this long and not done is left: no level waits on one for ever
# A chest clicked (tried) and then out of the read is done as opened, not left by SPOT_SECONDS: at 09:07:23 on
# 2026-10-21 two Upper Kurast chests opened at 09:05:41 and 09:07:12 were logged "not done in 45 s: left" (only the
# line was wrong: nothing was lost). False: the timer says so as before
CLICKED_IS_DONE = True


def build_glowing(objects: Iterable[Mapping]) -> dict[int, str]:
    """objects.txt id -> Class of each glowing chest: the rows drawn with an overlay (`Overlay` 1) that drop a chest's
    items (`PopulateFn` 3)."""
    return {
        int(row['*ID']): str(row['Class'])
        for row in objects
        if row.get('*ID') is not None and int(row.get('Overlay') or 0) == 1 and int(row.get('PopulateFn') or 0) == 3
    }


@cache
def _spots(preset: int, variant: int | None) -> tuple[tuple[int, int], ...]:
    return object_spots(preset, variant, UNIQUE_CHEST)


@cache
def _chest_spots(preset: int, variant: int | None) -> tuple[tuple[int, int], ...]:
    found = [spot for kind in (UNIQUE_CHEST, *sorted(GLOWING)) for spot in object_spots(preset, variant, kind)]
    return tuple(found)


def _placed(rooms: Iterable[Room], spots: Callable[[int, int | None], tuple[tuple[int, int], ...]]) -> frozenset[Point]:
    found: set[Point] = set()
    for room in rooms:
        placed = spots(room.preset, room.variant)
        if not placed:
            continue
        x, y = (room.block[0], room.block[1]) if room.block is not None else (room.x, room.y)
        found.update((x * TILE_UNITS + dx, y * TILE_UNITS + dy) for dx, dy in placed)
    return frozenset(found)


def unique_spots(rooms: Iterable[Room]) -> frozenset[Point]:
    """The level's unique-chest spots in world units: each preset's spots from its origin (a large preset's chunks
    share its `block`, so its spots come once)."""
    return _placed(rooms, _spots)


def level_spots(rooms: Iterable[Room]) -> frozenset[Point]:
    """Where the level's files place a super chest: the unique-chest spots and the glowing chests' (world units)."""
    return _placed(rooms, _chest_spots)


def is_super(thing: Thing, spots: frozenset[Point]) -> bool:
    """Whether `thing` is a super chest: a glowing one, or (ENABLED) a container at a unique-chest spot."""
    if thing.txt_id == SUPER_CHEST:
        return True
    if not ENABLED:
        return False
    if thing.txt_id in GLOWING:
        return True
    return thing.txt_id in containers() and any(math.dist((thing.x, thing.y), spot) <= SPOT for spot in spots)


def super_chests(things: Sequence[Thing], rooms: Sequence[Room]) -> list[Thing]:
    """The super chests among `things`, open or closed (`is_super`)."""
    spots = unique_spots(rooms) if ENABLED else frozenset()
    return [thing for thing in things if is_super(thing, spots)]


def mark_use(thing: Thing | None) -> int:
    """The `Target.use` (macros/teleport.py USES) a mark on the chest is opened by: SUPER_CHEST for the 397 one, else
    UNIQUE_CHEST, whose classes are every container, the glowing ones among them (game/decode.py `container_table`;
    one unseen now is taken by its place)."""
    if not ENABLED or (thing is not None and thing.txt_id == SUPER_CHEST):
        return SUPER_CHEST
    return UNIQUE_CHEST


@dataclass
class Book:
    """The level spots done this game (opened, tried out, empty, passed, out of time) and when the run first went for
    each, by (area, spot)."""

    game: str | None = None
    done: set[tuple[int, Point]] = field(default_factory=set)
    since: dict[tuple[int, Point], float] = field(default_factory=dict)
    said: tuple[int, Point] | None = None
    units: dict[tuple[int, Point], int] = field(default_factory=dict)  # the chest last read at each spot

    def begin(self, game: str) -> None:
        if game != self.game:
            self.game, self.done, self.since, self.said, self.units = game, set(), {}, None, {}

    def finish(self, area: int, spot: Point, why: str) -> None:
        self.done.add((area, spot))
        LOG.info('Macro: super chest at (%.0f, %.0f) on %s: %s', spot[0], spot[1], display_name(area), why)


BOOK = Book()


def _spot_of(thing: Thing, spots: Iterable[Point]) -> Point:
    return next((spot for spot in spots if math.dist(spot, (thing.x, thing.y)) <= SPOT), (thing.x, thing.y))


def level_goal(
    game: str,
    area: int,
    here: Point,
    rooms: Sequence[Room],
    things: Sequence[Thing],
    tries: Mapping[int, int],
    passed: Callable[[Point, int | None], bool],
    now: float,
    spend: Intent,
    route: str = '',
    book: Book | None = None,
) -> Goal | None:
    """The nearest super chest of the level not done yet (LEVEL_SPOTS): a chest read closed, to open; a spot of the
    level's files not read yet, to go to. `tries`: clicks by chest unit (the Hunter's `shack_tries`); `passed`: the
    run's passed goals (place, unit). None: none left, or the switch off."""
    if not (ENABLED and LEVEL_SPOTS):
        return None
    book = book if book is not None else BOOK
    book.begin(game)
    spots = set(level_spots(rooms))
    read: dict[Point, Thing] = {}
    for thing in super_chests(things, rooms):
        spot = _spot_of(thing, spots)
        spots.add(spot)
        if spot not in read or thing.mode == 0:
            read[spot] = thing
    left: list[tuple[Point, Thing | None]] = []
    for spot in spots:
        key = (area, spot)
        if key in book.done:
            continue
        thing = read.get(spot)
        if thing is not None:
            book.units[key] = thing.unit_id
        clicked = book.units.get(key)
        if thing is not None and (thing.mode != 0 or thing.selectable is False):
            book.finish(area, spot, f'class {thing.txt_id} open')
        elif thing is not None and tries.get(thing.unit_id, 0) >= SUPER_TRIES:
            book.finish(area, spot, f'class {thing.txt_id} not opened in {SUPER_TRIES} tries: left')
        elif CLICKED_IS_DONE and thing is None and clicked is not None and tries.get(clicked, 0) > 0:
            book.finish(area, spot, 'clicked, then out of the read: opened')
        elif thing is None and math.dist(here, spot) <= GONE_NEAR:
            book.finish(area, spot, 'no chest read there: none to open')
        elif passed(spot, thing.unit_id if thing is not None else None):
            book.finish(area, spot, 'no progress toward it: passed')
        elif key in book.since and now - book.since[key] > SPOT_SECONDS:
            book.finish(area, spot, f'not done in {SPOT_SECONDS:.0f} s: left')
        else:
            left.append((spot, thing))
    if not left:
        return None
    spot, thing = min(left, key=lambda found: math.dist(here, found[0]))
    key = (area, spot)
    book.since.setdefault(key, now)
    if book.said != key:
        book.said = key
        LOG.info(
            'Macro: super chest: going for the %s at (%.0f, %.0f), %.0f away (%d left on %s)',
            f'chest of class {thing.txt_id}' if thing is not None else 'spot',
            spot[0], spot[1], math.dist(here, spot), len(left), display_name(area),
        )  # fmt: skip
    if thing is None:
        return Goal('agenda: a super chest spot', spot, REACH, ARRIVE, spend, route=route, clearing=True)
    mark = Target(area, (), (thing.x / TILE_UNITS, thing.y / TILE_UNITS), 'Super chest', 'target', use=mark_use(thing))
    return Goal('agenda: Super chest', (thing.x, thing.y), USE, USE_NEAR, spend, unit=thing.unit_id, mark=mark,
                route=route, clearing=True)  # fmt: skip


def main() -> None:
    """Regenerate data/glowing_chests.json from the d2data checkout (third-parties/README.md)."""
    source = Path(__file__).parents[2] / 'third-parties' / 'd2data' / 'json' / 'objects.json'
    rows = json.loads(source.read_text())
    found = build_glowing(rows.values() if isinstance(rows, dict) else rows)
    data = {'source': 'd2data json/objects.json: Overlay 1 and PopulateFn 3 (macros/superchests.py build_glowing)'}
    GLOWING_FILE.write_text(
        json.dumps({**data, 'chests': {str(k): v for k, v in sorted(found.items())}}, indent=1) + '\n'
    )
    print(f'{len(found)} glowing chests -> {GLOWING_FILE}')


if __name__ == '__main__':
    main()
