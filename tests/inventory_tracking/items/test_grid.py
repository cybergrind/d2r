"""`Grid` against a brute-force model of cells on seeded random rows, unread (None) rows included. Before the move
(cleanup phase 3 step 2, 2026-10-19) the ten copies it replaced (cube `fits`/`taken`/`largest_block`, charms `_fits`,
town `_spot`/`_rows_of`, townplan `_first_fit`/`_cube_rows`, world `grid_rows`, the fakes' grid helpers) answered as
this model on the same rows; the wrappers kept for their callers are checked here too."""

import random

import pytest

from inventory_tracking.collection import capture
from inventory_tracking.game import records
from inventory_tracking.game.records import Carried, Pack, has_room
from inventory_tracking.items.grid import CUBE_SIZE, GRID_CONTAINERS, INVENTORY_SIZE, STASH_SIZE, Grid
from inventory_tracking.macros import charms, volatile


SEEDS = range(400)
SIZES = [(w, h) for w in range(1, 5) for h in range(1, 5)]


def _rows(roll: random.Random) -> tuple[str, ...]:
    width, height = roll.randint(1, 10), roll.randint(1, 10)
    density = roll.choice((0.0, 0.2, 0.5, 0.8, 1.0))
    return tuple(''.join('#' if roll.random() < density else '.' for _ in range(width)) for _ in range(height))


def _items(roll: random.Random, width: int, height: int) -> tuple[Carried, ...]:
    """Items at random cells, some overlapping or reaching past the grid's edge."""
    return tuple(
        Carried(n, 0, roll.randrange(width), roll.randrange(height), roll.choice(SIZES))
        for n in range(roll.randint(0, 8))
    )


# The model: a grid is its set of free cells


def _free(rows) -> set[tuple[int, int]]:
    return {(x, y) for y, row in enumerate(rows) for x, cell in enumerate(row) if cell == '.'}


def _block(at, size) -> set[tuple[int, int]]:
    return {(at[0] + dx, at[1] + dy) for dx in range(size[0]) for dy in range(size[1])}


def model_fits(rows, at, size) -> bool:
    return at[0] >= 0 and at[1] >= 0 and _block(at, size) <= _free(rows)


def model_spots(rows, size) -> list[tuple[int, int]]:
    width = len(rows[0]) if rows else 0
    return [(x, y) for y in range(len(rows)) for x in range(width) if model_fits(rows, (x, y), size)]


def model_take(rows, at, size) -> tuple[str, ...]:
    block = _block(at, size)
    return tuple(''.join('#' if (x, y) in block else c for x, c in enumerate(row)) for y, row in enumerate(rows))


def model_of_items(items, width, height) -> tuple[str, ...]:
    taken = set().union(*(_block((i.x, i.y), i.size) for i in items))
    return tuple(''.join('#' if (x, y) in taken else '.' for x in range(width)) for y in range(height))


def model_largest(rows) -> int:
    width = len(rows[0]) if rows else 0
    sizes = [(w, h) for w in range(1, width + 1) for h in range(1, len(rows) + 1)]
    return max((w * h for w, h in sizes if model_spots(rows, (w, h))), default=0)


def model_packed(rows, size) -> int:
    count = 0
    while spots := model_spots(rows, size):
        rows, count = model_take(rows, spots[0], size), count + 1
    return count


def _cases():
    for seed in SEEDS:
        roll = random.Random(seed)
        rows = _rows(roll)
        width, height = len(rows[0]), len(rows)
        at = (roll.randrange(width + 2), roll.randrange(height + 2))
        yield rows, at, roll.choice(SIZES), _items(roll, width, height)


CASES = list(_cases())


@pytest.mark.parametrize(('rows', 'at', 'size', 'items'), CASES[:120])
def test_a_block_fits_as_the_model_and_never_off_the_grid(rows, at, size, items):
    grid = Grid(rows)
    assert grid.fits(at, size) is model_fits(rows, at, size)
    assert grid.fits((-1, at[1]), size) is False
    assert grid.fits((at[0], -1), size) is False


def test_the_spots_room_and_largest_block_are_the_models():
    for rows, _, size, _ in CASES:
        spots = model_spots(rows, size)
        grid = Grid(rows)
        assert list(grid.spots(size)) == spots
        assert grid.first_spot(size) == (spots[0] if spots else None)
        assert grid.has_room(size) is bool(spots)
        assert records.has_room(rows, size) is bool(spots)
        assert Grid(rows).has_room(size) is bool(spots)
        assert grid.largest_block() == model_largest(rows)
        assert grid.free == len(_free(rows))
        assert (grid.width, grid.height) == (len(rows[0]), len(rows))


def test_a_take_is_the_models_and_the_grid_stays_a_grid():
    for rows, at, size, _ in CASES:
        taken = Grid(rows).take(at, size)
        assert taken == model_take(rows, at, size)
        assert isinstance(taken, Grid)


def test_every_row_builder_is_the_models():
    for rows, _, _, items in CASES:
        width, height = len(rows[0]), len(rows)
        cells = [0 if c == '.' else 0x1000 + n for n, c in enumerate(''.join(rows))]
        grid = {'width': width, 'height': height, 'cells': cells}
        assert Grid.from_cells(grid) == rows
        assert tuple(capture.grid_space(grid, 'cube')['rows']) == rows
        assert Grid.from_items(items, (width, height)) == model_of_items(items, width, height)
        inventory = tuple(i for i in items if i.x < 10 and i.y < 4)
        assert Pack(inventory).inventory == model_of_items(inventory, 10, 4)
        assert Pack(inventory).inventory == model_of_items(inventory, 10, 4)
        cubed = tuple(i for i in items if i.x < 3 and i.y < 4)
        assert Grid.from_items(cubed, CUBE_SIZE) == model_of_items(cubed, 3, 4)
        protected = frozenset(c for i in inventory for c in _block((i.x, i.y), i.size))
        assert Grid.from_taken(protected, INVENTORY_SIZE) == model_of_items(inventory, 10, 4)
        assert volatile.picture(protected) == '/'.join(model_of_items(inventory, 10, 4))


def test_the_greedy_count_is_the_models():
    for rows, _, _, _ in CASES[:100]:
        assert all(Grid(rows).packed(size) == model_packed(rows, size) for size in SIZES)
        expected = {f'{w}x{h}': model_packed(rows, (w, h)) for w, h in capture.ITEM_SIZES}
        assert capture.fits_counts(list(rows)) == expected


def test_an_item_moved_within_the_inventory_counts_its_own_cells_free():
    for _, at, _, items in CASES:
        inventory = tuple(i for i in items if i.x < 10 and i.y < 4)
        if not inventory:
            continue
        item = inventory[0]
        others = [i for i in inventory if i.unit_id != item.unit_id]
        expected = model_fits(model_of_items(others, 10, 4), at, item.size)
        assert charms._free_for(Pack(inventory), item, at) is expected
        assert charms._free_for(Pack(inventory), item, (-1, at[1])) is False


def test_unread_rows_have_room_at_the_pickup_sites_and_no_rows_have_none():
    assert records.has_room(None, (1, 1)) is True
    assert records.has_room(None, (99, 99)) is True
    assert not records.has_room((), (1, 1))
    assert not Grid(()).has_room((1, 1))
    assert Grid(()).first_spot((1, 1)) is None
    assert Grid(()).largest_block() == 0
    assert (Grid(()).width, Grid(()).free, Grid(()).packed((1, 1))) == (0, 0, 0)


def test_the_cubes_three_by_four_read_has_no_room_for_a_grand_charm_in_two_cells():
    # The Horadric Cube's grid (rca/2026-10-13/pickup-cube.md §3: grid 5, 3x4) as the inventory's is read
    taken = 0x1000
    cells = [taken, 0, taken, 0, 0, taken, taken, taken, taken, taken, taken, taken]
    rows = Grid.from_cells({'width': 3, 'height': 4, 'cells': cells})
    assert rows == ('#.#', '..#', '###', '###')
    assert has_room(rows, (1, 2))
    assert not has_room(rows, (1, 3))  # a Grand Charm


def test_the_sizes_are_the_grid_tables():
    assert Grid.empty(INVENTORY_SIZE) == ('.' * 10,) * 4
    assert Grid.empty(CUBE_SIZE) == ('...',) * 4
    assert Grid.empty(STASH_SIZE) == ('.' * 10,) * 10
    assert {g: size for g, (_, *size) in GRID_CONTAINERS.items()} == {2: [10, 4], 5: [3, 4], 6: [10, 10]}
