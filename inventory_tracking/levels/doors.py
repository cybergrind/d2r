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
FOOTPRINT_SLACK = 1.0  # world units around the footprint's half extent


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
        size = door_sizes().get(self.txt_id, (1, 1))
        return max(size) / 2 + FOOTPRINT_SLACK

    def blocks(self, point: tuple[float, float]) -> bool:
        """Whether a closed door stands over `point` (world units)."""
        return self.closed and abs(point[0] - self.x) <= self.radius and abs(point[1] - self.y) <= self.radius
