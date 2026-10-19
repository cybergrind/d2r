"""An item grid's occupancy (the carried inventory, the Horadric Cube, a stash page) and the one table of their sizes.

A `Grid` is its rows, '.' a free cell and '#' a taken one, so it stands wherever rows are held (`Pack.cube`,
`Page.rows`, `Loot.room`). Unread rows are the caller's None: a Grid never answers for a grid it was not given.
"""

from collections.abc import Collection, Iterable, Iterator, Mapping
from typing import Any, Protocol, Self


Size = tuple[int, int]  # (across, down)
Cell = tuple[int, int]

# A player's grids by their index, the inventory page + 2 (hover/selection.py); sizes host-verified
INVENTORY_GRID = 2
CUBE_GRID = 5
STASH_GRID = 6  # the personal stash page's (a shared page's is the same size)
GRID_CONTAINERS = {INVENTORY_GRID: ('inventory', 10, 4), CUBE_GRID: ('cube', 3, 4), STASH_GRID: ('stash', 10, 10)}


def _size(grid: int) -> Size:
    _, across, down = GRID_CONTAINERS[grid]
    return across, down


INVENTORY_SIZE = _size(INVENTORY_GRID)
CUBE_SIZE = _size(CUBE_GRID)
STASH_SIZE = _size(STASH_GRID)


class Placed(Protocol):
    """An item lying on a grid: its top-left cell and its size."""

    @property
    def x(self) -> int: ...
    @property
    def y(self) -> int: ...
    @property
    def size(self) -> Size: ...


class Grid(tuple[str, ...]):
    """A grid's rows, '.' a free cell and '#' a taken one; equal to the plain tuple of its rows."""

    __slots__ = ()

    @classmethod
    def empty(cls, size: Size) -> Self:
        return cls(('.' * size[0],) * size[1])

    @classmethod
    def from_taken(cls, taken: Collection[Cell], size: Size) -> Self:
        """`size` with the cells of `taken` taken."""
        return cls(''.join('#' if (x, y) in taken else '.' for x in range(size[0])) for y in range(size[1]))

    @classmethod
    def from_items(cls, items: Iterable[Placed], size: Size) -> Self:
        """`size` with each item's block taken (the part of it inside the grid)."""
        return cls.from_taken({c for i in items for c in _block((i.x, i.y), i.size)}, size)

    @classmethod
    def from_cells(cls, grid: Mapping[str, Any]) -> Self:
        """A grid as memory holds it (collection/capture.py `read_owner_grids`): a cell taken where it holds an item."""
        width, cells = grid['width'], grid['cells']
        return cls(''.join('#' if cells[y * width + x] else '.' for x in range(width)) for y in range(grid['height']))

    @property
    def width(self) -> int:
        return len(self[0]) if self else 0

    @property
    def height(self) -> int:
        return len(self)

    @property
    def free(self) -> int:
        return sum(row.count('.') for row in self)

    def fits(self, at: Cell, size: Size) -> bool:
        """Whether the block of `size` with its top-left at `at` is free and inside the grid."""
        x, y = at
        across, down = size
        if x < 0 or y < 0 or y + down > len(self) or x + across > self.width:
            return False
        return all(self[y + dy][x + dx] == '.' for dy in range(down) for dx in range(across))

    def spots(self, size: Size) -> Iterator[Cell]:
        """The cells, row by row, whose block of `size` is free: the first is where the game's Ctrl + click puts it."""
        return ((x, y) for y in range(len(self)) for x in range(self.width) if self.fits((x, y), size))

    def first_spot(self, size: Size) -> Cell | None:
        return next(self.spots(size), None)

    def has_room(self, size: Size) -> bool:
        return self.first_spot(size) is not None

    def take(self, at: Cell, size: Size) -> Grid:
        """The grid with the block of `size` at `at` taken (the part of it inside the grid)."""
        x, y = at
        across, down = size
        return Grid(
            ''.join('#' if y <= row < y + down and x <= col < x + across else cell for col, cell in enumerate(line))
            for row, line in enumerate(self)
        )

    def largest_block(self) -> int:
        """The cells of the largest free rectangle."""
        height, width = len(self), self.width
        return max(
            (
                across * down
                for y in range(height)
                for x in range(width)
                for down in range(1, height - y + 1)
                for across in range(1, width - x + 1)
                if self.fits((x, y), (across, down))
            ),
            default=0,
        )

    def packed(self, size: Size) -> int:
        """How many blocks of `size` fit, each into the first free one in turn: a lower bound on what still fits."""
        used = [list(row) for row in self]
        across, down = size
        count = 0
        for y in range(len(self) - down + 1):
            for x in range(self.width - across + 1):
                if all(used[y + dy][x + dx] == '.' for dy in range(down) for dx in range(across)):
                    for dy in range(down):
                        used[y + dy][x : x + across] = '#' * across
                    count += 1
        return count


def _block(at: Cell, size: Size) -> Iterator[Cell]:
    return ((at[0] + dx, at[1] + dy) for dx in range(size[0]) for dy in range(size[1]))
