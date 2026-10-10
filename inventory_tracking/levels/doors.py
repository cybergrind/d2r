"""Door objects: a closed door is a wall for a shot and for a walk until it is opened.

The game keeps doors as object units (unit type 2) whose class rows in objects.txt carry
`IsDoor` and a footprint in sub-tiles (`SizeX`, `SizeY`; data/doors.json from d2data, 25
classes: wooden, gate, cathedral, tomb, desert, slime doors and the boss doors). Their mode says
whether they stand closed (CLOSED_MODE, the object's neutral mode) or have been opened. The
collision grid the level guide reads (levels/memory.py) keeps only the block-walk bit, whose
meaning for a closed door is unverified, so the hunt checks doors by their units (user,
2026-10-10: the Catacombs' attack mode shot through closed doors).
"""

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path


DATA = Path(__file__).parent / 'data' / 'doors.json'
CLOSED_MODE = 0  # object mode NU: never operated; 1 is opening, 2 opened
FOOTPRINT_SLACK = 1.0  # world units past the footprint's ends along the door: the frame
THICKNESS_SLACK = 0.5  # world units to each side of the door's thin side


@cache
def door_sizes() -> dict[int, tuple[int, int]]:
    """Object class id -> (SizeX, SizeY) of the door classes."""
    data = json.loads(DATA.read_text())['doors']
    return {int(txt): (int(row['size'][0]), int(row['size'][1])) for txt, row in data.items()}


@dataclass(frozen=True)
class Door:
    unit_id: int
    txt_id: int
    mode: int
    x: float
    y: float

    @property
    def closed(self) -> bool:
        return self.mode == CLOSED_MODE

    @property
    def radius(self) -> float:
        """Half the door's longer side with the slack: how far from it the door can matter at all."""
        return max(self.extent)

    @property
    def extent(self) -> tuple[float, float]:
        """The half extents (x, y) of what the closed door blocks: its footprint, a little longer for
        the frame and a little thicker. A door is a line across its doorway, not a square: with the
        square of its longer side every shot from 1.5 units before Andariel's door (7 x 1) read
        blocked, at monsters on the character's own side too, and attack mode stood for ten seconds
        among thirty of them (host, 21:18 on 2026-10-10, Catacombs 3)."""
        wide, deep = door_sizes().get(self.txt_id, (1, 1))
        slack = (FOOTPRINT_SLACK, THICKNESS_SLACK) if wide >= deep else (THICKNESS_SLACK, FOOTPRINT_SLACK)
        return wide / 2 + slack[0], deep / 2 + slack[1]

    def blocks(self, point: tuple[float, float]) -> bool:
        """Whether a closed door stands over `point` (world units)."""
        across, along = self.extent
        return self.closed and abs(point[0] - self.x) <= across and abs(point[1] - self.y) <= along
