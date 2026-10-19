"""Door objects: a closed door is a wall for a shot and for a walk until it is opened.

Doors are object units whose objects.txt rows carry `IsDoor` and a sub-tile footprint (SizeX, SizeY;
data/doors.json from d2data, 25 classes); their mode says closed or opened. The collision grid's meaning
for a closed door is unverified, so the hunt checks door units (user, 2026-10-10: attack mode shot through
closed doors in the Catacombs).
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
        """The half extents (x, y) a closed door blocks: its footprint plus frame and thickness slack. A line
        across the doorway, not a square: a square blocked shots at monsters on the near side too
        (2026-10-10 21:18, Catacombs 3)."""
        wide, deep = door_sizes().get(self.txt_id, (1, 1))
        slack = (FOOTPRINT_SLACK, THICKNESS_SLACK) if wide >= deep else (THICKNESS_SLACK, FOOTPRINT_SLACK)
        return wide / 2 + slack[0], deep / 2 + slack[1]

    def blocks(self, point: tuple[float, float]) -> bool:
        """Whether a closed door stands over `point` (world units)."""
        across, along = self.extent
        return self.closed and abs(point[0] - self.x) <= across and abs(point[1] - self.y) <= along
