"""Door objects: a closed door is a wall for a shot and for a walk until it is opened.

Doors are object units whose objects.txt rows carry `IsDoor` and a sub-tile footprint (SizeX, SizeY;
data/doors.json from d2data, 25 classes); their mode says closed or opened. The collision grid's meaning
for a closed door is unverified, so the hunt checks door units (user, 2026-10-10: attack mode shot through
closed doors in the Catacombs).

A door can read mode 0 and still let monsters and blades through (rca/2026-10-23/jumps-findings.md case 1: a
TombDoorRight in the Halls of the Dead read 0 the whole take while pack members walked through it). Once a live
hostile or the character is read inside such a door's footprint, the door counts as passed: open for the rest of the
level (`PassedDoors`, PASSED_OPEN). A door nobody has stood in still blocks.
"""

import json
import threading
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path


DATA = Path(__file__).parent / 'data' / 'doors.json'
CLOSED_MODE = 0  # object mode NU: never operated; 1 is opening, 2 opened
FOOTPRINT_SLACK = 1.0  # world units past the footprint's ends along the door: the frame
THICKNESS_SLACK = 0.5  # world units to each side of the door's thin side
# A door read closed that a live hostile or the character stood inside is open for the rest of the level (2026-10-23,
# rca/2026-10-23/jumps-findings.md fix A: the game let a pack through a TombDoorRight read 0, and the hunt danced for
# 11 s with no strike priced through it). Off: every door read 0 is a wall, as before.
PASSED_OPEN = True
# A shot whose straight line meets a closed door's leaf is blocked, its two ends included (`Door.crosses`; 2026-10-24,
# the player ~20:35: "we were trying to attack herald through closed door"; rca/2026-10-24/closed-door-findings.md).
# The line check looks at the doors' boxes between its end margins only (macros/sight.py MARGIN 1.5), so a monster
# pressed into a closed doorway (a tier 5 Herald at 0.5 off a TombDoorLeft's anchor) read in reach from the far side,
# and 10 volleys bounced off the door (20:31:44-47, 20:32:30-33) until the player opened it. Off: the boxes between the
# margins, as before.
SHOT_LEAF = True
# World units past the anchor, across the door's thin side, where its leaf parts the two sides. A door is one sub-tile
# thick, the cell from its anchor to anchor + 1 (the TombDoorRight gap of take 20261024T173021Z-69 runs 22718-22725
# for an anchor at 22721). Of the 62 tomb takes of 2026-10-17 to 24, hostiles pressed against a door read 0 stood at
# -0.9 to +0.5 off the anchor from its low side and at +1.5 and more from its high side; blades from the low side got
# as far as +0.4 to +1.0, from the high side back to +0.1 to +0.6. 0.75 parts the pressed units of the two sides.
LEAF_ACROSS = 0.75

type Point = tuple[float, float]  # world units


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
    # Read closed, but something stood in its doorway this level (`PassedDoors`): open to every reader. The mode
    # stays the game's (a take records it as read).
    passed: bool = False

    @property
    def closed(self) -> bool:
        return self.mode == CLOSED_MODE and not self.passed

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

    def within(self, point: Point) -> bool:
        """Whether `point` lies strictly inside the door's own footprint, without the frame and thickness slack: where
        only a unit the door let through can stand. Units pressed against a shut door read in the slack, up to its
        footprint's edge (takes of 2026-10-22/23: those stood 0.5-1.0 off the door's line; the units a door read 0 let
        through crossed inside it)."""
        wide, deep = door_sizes().get(self.txt_id, (1, 1))
        return abs(point[0] - self.x) < wide / 2 and abs(point[1] - self.y) < deep / 2

    def crosses(self, start: Point, end: Point) -> bool:
        """Whether the straight line from `start` to `end` meets the closed door's leaf (LEAF_ACROSS) within its
        length and frame (FOOTPRINT_SLACK), the ends of the line included: a monster pressed into the doorway from
        the far side is behind the door, one pressed into it from the near side is not."""
        if not self.closed:
            return False
        wide, deep = door_sizes().get(self.txt_id, (1, 1))
        if wide >= deep:  # the door runs along x, its leaf across y; along it as far as its box (`extent`)
            across, along, leaf, middle, half = 1, 0, self.y + LEAF_ACROSS, self.x, wide / 2
        else:
            across, along, leaf, middle, half = 0, 1, self.x + LEAF_ACROSS, self.y, deep / 2
        before, after = start[across] - leaf, end[across] - leaf
        if (before < 0) == (after < 0):
            return False  # both ends on one side of the leaf
        at = start[along] + (end[along] - start[along]) * before / (before - after)
        return abs(at - middle) <= half + FOOTPRINT_SLACK


# (game name, character unit id, level): a door's unit id is the game's, and a level's doors are its own
type Level = tuple[str, int, int]


class PassedDoors:
    """The doors read closed that a live hostile or the character was read inside, for the level the character is in:
    the one memory every reader of the decoded doors goes through (game/memory.py `GameMemory._world` marks them
    `Door.passed`, so the shots, the walks, the safety's walls and the door openings see one fact). Forgotten on a
    level change and on a new game (a new name or character unit). A door the game reads opened is opened whatever
    the memory says."""

    def __init__(self) -> None:
        self.level: Level | None = None
        self.units: set[int] = set()
        self.lock = threading.Lock()  # the run's looks and the watchers' share one memory

    def seen(self, level: Level, doors: Sequence[Door], standing: Iterable[Point]) -> tuple[Door, ...]:
        """`doors` read on `level`, those passed marked: before or at this look, with `standing` the places of the
        live hostiles and the character. As read with PASSED_OPEN off."""
        with self.lock:
            if level != self.level:
                self.level, self.units = level, set()
            if not PASSED_OPEN:
                return tuple(doors)
            places = tuple(standing)
            for door in doors:
                if door.mode == CLOSED_MODE and door.unit_id not in self.units and any(map(door.within, places)):
                    self.units.add(door.unit_id)
            return tuple(
                replace(door, passed=True) if door.mode == CLOSED_MODE and door.unit_id in self.units else door
                for door in doors
            )

    def forget(self) -> None:
        with self.lock:
            self.level, self.units = None, set()


PASSED = PassedDoors()  # the process's one memory (each run's GameMemory reads through it)
