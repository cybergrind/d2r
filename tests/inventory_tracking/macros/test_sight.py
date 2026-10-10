"""Lines of sight for Echoing Strike over the walkable sub-tiles: a wall between stops a shot."""

import math

from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.model import Ground, Walkable, pack_cells
from inventory_tracking.macros.sight import clear_shot, firing_spots, in_reach


def grid(rows: list[str], x: int = 0, y: int = 0) -> Walkable:
    """A room from sub-tile rows ('#' wall, '.' floor); 5 sub-tiles make a tile."""
    width, height = len(rows[0]) // 5, len(rows) // 5
    return Walkable(x, y, width, height, pack_cells(''.join('0' if c == '#' else '1' for row in rows for c in row)))


# Two tiles by one: a wall one sub-tile thick down the middle (x = 5), with a doorway at rows 3 and 4.
WALLED = grid([
    '.....#....',
    '.....#....',
    '.....#....',
    '..........',
    '..........',
])  # fmt: skip
OPEN = grid(['.' * 10] * 5)


def test_a_wall_between_blocks_the_shot_and_a_doorway_lets_it_through():
    ground = Ground((WALLED,))
    assert clear_shot(ground, (1.5, 1.5), (8.5, 1.5)) is False  # through the wall
    assert clear_shot(ground, (1.5, 3.5), (8.5, 3.5)) is True  # through the doorway
    assert clear_shot(ground, (1.5, 1.5), (4.5, 1.5)) is True  # same side of the wall


def test_the_monster_may_stand_on_the_wall_itself():
    ground = Ground((WALLED,))
    assert clear_shot(ground, (1.5, 1.5), (5.5, 1.5)) is True  # within MARGIN of the wall sub-tile
    assert clear_shot(ground, (1.5, 1.5), (1.5, 1.5)) is True


def test_unknown_ground_counts_as_clear_only_while_no_wall_is_known():
    assert clear_shot(Ground(()), (0.0, 0.0), (30.0, 40.0)) is True
    # Off the grid beyond x = 10: a room not read on a level whose walls are read is no place to shoot into
    # (the Catacombs runs of 2026-10-10 fired into unread rooms).
    assert clear_shot(Ground((OPEN,)), (1.0, 1.0), (40.0, 1.0)) is False
    assert clear_shot(Ground((OPEN,)), (1.0, 1.0), (9.0, 1.0)) is True


def test_a_closed_door_blocks_the_shot_and_an_opened_one_does_not():
    ground = Ground((OPEN,))
    closed = Door(1, 15, 0, 5.0, 1.5)  # DoorWoodenLeft, 1 x 3 sub-tiles, never operated
    opened = Door(1, 15, 2, 5.0, 1.5)
    assert clear_shot(ground, (1.0, 1.5), (9.0, 1.5), (closed,)) is False
    assert clear_shot(ground, (1.0, 1.5), (9.0, 1.5), (opened,)) is True
    assert clear_shot(ground, (1.0, 4.5), (9.0, 4.5), (closed,)) is True  # three sub-tiles south of it
    assert in_reach(ground, (1.0, 1.5), (9.0, 1.5), 10.0, (closed,)) is False
    assert in_reach(ground, (1.0, 1.5), (9.0, 1.5), 10.0, (opened,)) is True
    # Firing spots are chosen with the doors too: none west of a closed door whose line crosses it.
    west = [s for s in firing_spots(ground, (8.0, 1.5), 10.0, (1.0, 1.5), (closed,)) if s[0] < 5.0]
    assert all(not clear_shot(ground, s, (8.0, 1.5)) or clear_shot(ground, s, (8.0, 1.5), (closed,)) for s in west)
    assert not [s for s in west if abs(s[1] - 1.5) < 1.0]  # straight through the door: never a spot


def test_in_reach_needs_both_the_distance_and_the_shot():
    ground = Ground((WALLED,))
    assert in_reach(ground, (1.5, 3.5), (8.5, 3.5), 10.0) is True
    assert in_reach(ground, (1.5, 3.5), (8.5, 3.5), 5.0) is False
    assert in_reach(ground, (1.5, 1.5), (8.5, 1.5), 10.0) is False


def test_firing_spots_ring_the_monster_where_the_shot_is_clear_nearest_first():
    # A 4x4-tile room (20 sub-tiles) with a wall across the middle row 10 but for a two-sub-tile door.
    rows = ['.' * 20] * 10 + ['#' * 9 + '..' + '#' * 9] + ['.' * 20] * 9
    ground = Ground((grid(rows),))
    mob, player = (10.0, 15.0), (10.0, 2.0)  # the monster south of the wall, the character north
    spots = firing_spots(ground, mob, 10.0, player)
    assert spots
    assert all(clear_shot(ground, spot, mob) for spot in spots)
    assert math.dist(spots[0], player) <= math.dist(spots[-1], player)
    north = [spot for spot in spots if spot[1] < 10.0]
    assert north  # through the door, from the character's side of the wall
    assert all(abs(spot[0] - 10.0) < 2.0 for spot in north)  # only in line with the door
    assert all(4.0 - 1e-9 <= math.dist(spot, mob) <= 7.0 + 1e-9 for spot in spots)


def test_no_grid_means_every_ring_point_is_a_spot():
    spots = firing_spots(Ground(()), (100.0, 100.0), 15.0, (80.0, 100.0))
    assert len(spots) == 16 * 3  # radii 12, 9, 6
    assert spots[0] == (88.0, 100.0)  # the point nearest the character


def test_the_flight_layer_decides_the_shot_where_a_grid_has_one():
    from inventory_tracking.levels.memory import tiles_from_mask

    # Ten tiles east to west, one wall of block-walk cells (0x1) at tile 4 a blade flies over, one of
    # block-missile cells (0x5) at tile 7 it does not; a grid without the layer falls back to the walk bit.
    mask = [0x0001 if 20 <= c < 25 else 0x0005 if 35 <= c < 40 else 0 for _ in range(5) for c in range(50)]
    flown = Ground((tiles_from_mask(0, 0, 50, 5, mask),))
    assert clear_shot(flown, (1.0, 2.0), (30.0, 2.0)) is True
    assert clear_shot(flown, (1.0, 2.0), (45.0, 2.0)) is False
    walked = Ground((Walkable(0, 0, 10, 1, flown.grids[0].cells),))  # an old grid: cells only
    assert clear_shot(walked, (1.0, 2.0), (30.0, 2.0)) is False
