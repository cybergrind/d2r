"""Walkability of a world point from the loaded rooms' sub-tile grids."""

from inventory_tracking.levels.memory import tiles_from_mask
from inventory_tracking.levels.model import Ground, Walkable, pack_masks, pack_tiles


def test_ground_reads_sub_tiles_and_is_unknown_off_the_grids():
    ground = Ground([Walkable(0, 0, 2, 1, pack_tiles('10', 2))])  # tile (0, 0) walkable, tile (1, 0) not

    assert len(ground) == 1
    assert ground.walkable(2.5, 2.5) is True
    assert ground.walkable(4.99, 4.99) is True
    assert ground.walkable(5.0, 2.0) is False
    assert ground.walkable(12.0, 0.0) is None
    assert ground.walkable(2.0, 5.0) is None
    assert ground.walkable(-0.5, 2.0) is None
    assert Ground(()).walkable(2.0, 2.0) is None


def test_the_raw_collision_masks_ride_along_for_the_missile_bit_research():
    # 2026-10-10: the blades fly over block-walk cells, so which bit stops a missile is still to find.
    mask = ([0x0000] * 5 + [0x0001] * 5) * 5  # row by row: one tile walkable, the next blocking walking
    grid = tiles_from_mask(0, 0, 10, 5, mask)
    ground = Ground([grid])

    assert grid == Walkable(0, 0, 2, 1, pack_tiles('10', 2), flight=pack_tiles('11', 2), masks=pack_masks(mask))
    assert ground.walkable(2.0, 2.0) is True
    assert ground.mask(2.0, 2.0) == 0
    assert ground.mask(7.0, 2.0) == 1
    assert ground.mask(12.0, 2.0) is None
    assert Ground([Walkable(0, 0, 2, 1, pack_tiles('10', 2))]).mask(2.0, 2.0) is None  # no masks known


def test_the_flight_layer_says_where_a_missile_flies_and_is_unknown_without_one():
    # Block-walk (0x1) cells let a blade through; the block-missile bit (0x4) stops it (the 11:44 takes).
    mask = ([0x0001] * 5 + [0x0005] * 5) * 5
    ground = Ground([tiles_from_mask(0, 0, 10, 5, mask)])

    assert ground.walkable(2.0, 2.0) is False
    assert ground.flyable(2.0, 2.0) is True
    assert ground.flyable(7.0, 2.0) is False
    assert ground.flyable(12.0, 2.0) is None
    assert Ground([Walkable(0, 0, 2, 1, pack_tiles('10', 2))]).flyable(2.0, 2.0) is None  # an old level map
