"""Per-game room memory: details read once stay known for the rest of the game."""

from inventory_tracking.levels.model import Room
from inventory_tracking.levels.session import LevelMemory, layout_key


GAP = Room(41, 0, 0, 8, 8, 3, (0, 0, 8, 8))
FIELD = Room(0, 8, 0, 8, 8)


def test_an_exit_read_once_stays_named_when_a_later_read_cannot_see_it():
    memory = LevelMemory()
    memory.merge(3, [Room(41, 0, 0, 8, 8, 3, (0, 0, 8, 8), (4,)), FIELD])

    merged = memory.merge(3, [GAP, FIELD])

    assert merged == (Room(41, 0, 0, 8, 8, 3, (0, 0, 8, 8), (4,)), FIELD)


def test_new_neighbours_are_added_to_the_known_ones():
    memory = LevelMemory()
    memory.merge(3, [Room(41, 0, 0, 8, 8, 3, None, (4,))])

    [room] = memory.merge(3, [Room(41, 0, 0, 8, 8, 3, None, (2, 4))])

    assert room.leads_to == (4, 2)


def test_an_unreadable_variant_and_bounds_are_filled_from_an_earlier_read():
    memory = LevelMemory()
    memory.merge(123, [GAP])

    assert memory.merge(123, [Room(41, 0, 0, 8, 8)]) == (GAP,)


def test_another_layout_of_the_same_area_starts_blank():
    memory = LevelMemory()
    memory.merge(3, [Room(41, 0, 0, 8, 8, 3, None, (4,))])

    assert memory.merge(3, [Room(41, 16, 0, 8, 8, 3)]) == (Room(41, 16, 0, 8, 8, 3),)


def test_reset_forgets_the_game():
    memory = LevelMemory()
    memory.merge(3, [Room(41, 0, 0, 8, 8, 3, None, (4,))])
    memory.reset()

    assert memory.merge(3, [Room(41, 0, 0, 8, 8, 3)]) == (Room(41, 0, 0, 8, 8, 3),)


def test_the_layout_key_ignores_what_loads_later():
    assert layout_key(3, [GAP]) == layout_key(3, [Room(41, 0, 0, 8, 8, None, None, (4,))])
