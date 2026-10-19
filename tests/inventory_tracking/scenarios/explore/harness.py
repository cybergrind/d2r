"""The explore step replayed on a recorded level with nothing to fight: the hunt's own choice of the
room to go to, the teleport's own landing over the read ground, and the tracker's rule for what a
place shows (the character's room and the rooms touching it).

fixtures/ holds level maps as the combat recorder kept them (runs/combat/<stamp>-<area>/level.json,
gzipped): `far-oasis-20261010T231634Z` is the Far Oasis of the run at 02:16 on 2026-10-11.
"""

import gzip
import json
import math
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.levels.model import Level, Room, Target, Walkable
from inventory_tracking.macros import teleport
from inventory_tracking.macros.game.records import Player
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.tour import Bounds
from inventory_tracking.macros.view import Viewport
from inventory_tracking.native.layout import TILE_UNITS


FIXTURES = Path(__file__).parent / 'fixtures'
RECT = (1920, 0, 2560, 1418)  # the host's game window
Point = tuple[float, float]
Pick = Callable[[Level, Player, tuple[int, int, int, int]], tuple[float, Room, tuple[int, int]] | None]


def load(name: str) -> Level:
    found = json.loads(gzip.decompress((FIXTURES / f'{name}.json.gz').read_bytes()))
    rooms = tuple(
        Room(room['preset'], room['x'], room['y'], room['width'], room['height'], room.get('variant'))
        for room in found['rooms']
    )
    ground = tuple(
        Walkable(grid['x'], grid['y'], grid['width'], grid['height'], grid['cells'], grid.get('flight', ''))
        for grid in found['ground']
    )
    return Level(found['area'], rooms, ground)


def touching(room: Bounds, rooms: list[Bounds]) -> set[Bounds]:
    x, y, width, height = room
    return {
        other
        for other in rooms
        if other[0] <= x + width and x <= other[0] + other[2] and other[1] <= y + height and y <= other[1] + other[3]
    }


class Replay:
    """A character at `start` (world units) on `level`, having seen `explored`."""

    def __init__(self, level: Level, start: Point, explored: set[Bounds] | None = None) -> None:
        self.level = level
        self.bounds = [(room.x, room.y, room.width, room.height) for room in level.rooms]
        self.explored: set[Bounds] = set(explored or ())
        self.player = Player(1, 'replay', 5, level.area, start[0], start[1], False)
        self.hunter = Hunter(lambda: level, None, lambda area: self.explored, build=ECHOING_STRIKE_BUILD)
        self.path = [start]
        self.look()

    def look(self) -> None:
        x, y = self.player.x / TILE_UNITS, self.player.y / TILE_UNITS
        for room in self.bounds:
            if room[0] <= x < room[0] + room[2] and room[1] <= y < room[1] + room[3]:
                self.explored |= touching(room, self.bounds)
                return

    def hop(self, pick: Pick | None = None) -> bool:
        """One explore hop, by `pick` or by the hunt's own choice; False when nothing is left to go to."""
        found = (pick or self.hunter.frontier)(self.level, self.player, RECT)
        if found is None:
            return False
        _, _, (x, y) = found
        target = Target(
            self.level.area, self.level.rooms, (x + 0.5, y + 0.5), 'a room', 'explore', False, self.level.ground
        )
        here = (self.player.x / TILE_UNITS, self.player.y / TILE_UNITS)
        view = Viewport.of(RECT)
        for far in (True, False):  # as `hop_toward`: the far way first, the near way when it finds no landing
            way = teleport.way_for(target, view, far)
            landing = (
                teleport.landing(target, self.player, way, RECT[2] / RECT[3])
                if way.from_here(here) < math.inf
                else None
            )
            if landing is not None:
                (x, y), _ = landing
                self.player = replace(self.player, x=x * TILE_UNITS, y=y * TILE_UNITS)
                self.path.append((self.player.x, self.player.y))
                self.look()
                return True
        return False

    def hops(self, pick: Pick | None = None, limit: int = 300) -> int:
        made = 0
        while made < limit and self.hop(pick):
            made += 1
        return made
