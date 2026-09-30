"""Wall library: walkable tiles learned per preset layout, so unvisited rooms get walls on entry.

The client builds collision grids only for rooms loaded around the player (levels/memory.py
loaded_walkable). A preset room's walls come from its DS1 file, so every live read is saved under
(preset, DS1 variant, chunk offset in the preset, size), and any room with the same key, in this
game or a later one, is drawn from the library. Generated terrain (preset 0) and rooms without a
readable variant are never learned. A later sighting of the same key replaces the earlier one.
"""

import json
import struct
import sys
from collections.abc import Iterable
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.levels.memory import tiles_from_mask
from inventory_tracking.levels.model import Room, Walkable
from inventory_tracking.native.layout import COLLISION_BOUNDS, COLLISION_MASK, ROOM1_COLLISION
from inventory_tracking.reports import publish


DEFAULT_WALLS = Path('inventory_tracking/runs/levels/walls.json')


def layout_key(room: Room) -> str | None:
    if not room.preset or room.variant is None:
        return None
    bx, by = (room.block[0], room.block[1]) if room.block else (room.x, room.y)
    return f'{room.preset}:{room.variant}:{room.x - bx}:{room.y - by}:{room.width}x{room.height}'


class WallLibrary:
    def __init__(self, path: Path = DEFAULT_WALLS):
        self.path = path
        try:
            self.cells: dict[str, str] = json.loads(path.read_text())['layouts']
        except FileNotFoundError:
            self.cells = {}
        except (ValueError, KeyError, TypeError) as exc:
            LOG.warning('Wall library %s unreadable, starting empty: %s', path, exc)
            self.cells = {}

    def learn(self, rooms: Iterable[Room], grids: Iterable[Walkable]) -> int:
        """Save each grid under its room's layout key; the number of grids with a learnable room."""
        by_bounds = {(r.x, r.y, r.width, r.height): r for r in rooms}
        learned, changed = 0, False
        for grid in grids:
            room = by_bounds.get((grid.x, grid.y, grid.width, grid.height))
            key = None if room is None else layout_key(room)
            if key is None:
                continue
            learned += 1
            if self.cells.get(key) != grid.cells:
                self.cells[key] = grid.cells
                changed = True
        if changed:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            publish(self.path, {'schema_version': 1, 'layouts': self.cells})
        return learned

    def known(self, rooms: Iterable[Room]) -> list[Walkable]:
        found = []
        for room in rooms:
            key = layout_key(room)
            cells = self.cells.get(key) if key else None
            if cells is not None and len(cells) == room.width * room.height:
                found.append(Walkable(room.x, room.y, room.width, room.height, cells))
        return found


# The confirmed grid among research.collision_candidates (native/layout.py): (Room1 pointer offset,
# bounds offset, mask pointer offset).
CONFIRMED_CANDIDATE = (ROOM1_COLLISION, COLLISION_BOUNDS, COLLISION_MASK)


def learn_from_dumps(library: WallLibrary, paths: Iterable[Path]) -> int:
    """Teach the library from Win+C research dumps (runs/level/<run>/level.json); grids learned."""
    learned = 0
    for path in paths:
        dump = json.loads(Path(path).read_text())
        rooms = [Room.from_row(row) for row in (dump.get('evidence') or {}).get('rooms', [])]
        grids = []
        for room1 in dump.get('room1s', []):
            for c in room1.get('collision') or []:
                if (c['room1_offset'], c['coords_offset'], c['mask_offset']) != CONFIRMED_CANDIDATE:
                    continue
                (x, y), (w, h) = c['origin'], c['size']
                mask = struct.unpack(f'<{w * h}H', bytes.fromhex(c['mask_hex']))
                grids.append(tiles_from_mask(x, y, w, h, mask))
        learned += library.learn(rooms, grids)
    return learned


def main(argv=None) -> int:
    """uv run --offline python -m inventory_tracking.levels.walls <level.json>..."""
    paths = [Path(p) for p in (sys.argv[1:] if argv is None else argv)]
    library = WallLibrary()
    count = learn_from_dumps(library, paths)
    print(f'{count} room grids learned from {len(paths)} dumps; {len(library.cells)} layouts in {library.path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
