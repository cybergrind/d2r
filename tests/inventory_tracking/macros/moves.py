"""What the tests of a choice of a move share: facts with no game behind them, and a room with a wall."""

from dataclasses import replace

from inventory_tracking.levels.model import Ground, Walkable, pack_cells
from inventory_tracking.macros.build import MoveFacts
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.world import Teleport


ASPECT = 2560 / 1418
NOW = 100.0
HERE = (5000.5, 5000.5)
IN_HAND = Teleport(69, 69, True)


# The character at HERE on a level with no wall read, Teleport on a key, no staff worn
AT_REST = MoveFacts(here=HERE, now=NOW, slots=(None, TELEPORT), staff=None, ground=Ground(()), doors=(), aspect=ASPECT)


def facts(**changes) -> MoveFacts:
    """The character at rest (AT_REST), with what a test changes of it."""
    return replace(AT_REST, **changes)


def walled(walkable) -> Ground:
    """One room of 32 x 32 tiles round the character (world 5000, 5000), walkable where `walkable(x, y)` says so."""
    cells = ''.join('1' if walkable(4920 + x, 4920 + y) else '0' for y in range(160) for x in range(160))
    return Ground((Walkable(984, 984, 32, 32, pack_cells(cells)),))


def wall_with_a_gap(x, y) -> bool:
    """A wall two units thick east of the character, from far north to 12 units south of it."""
    return not (5008 <= x < 5010 and y < 5012)


def skills(found) -> list[int]:
    return [jump.skill for jump in found]
