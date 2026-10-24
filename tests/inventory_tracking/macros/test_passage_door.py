"""A door on the level edge is the open passage's way through (levels/exits.py `door_passage`; hunting/moves.py
PASSAGE_DOOR, route.py `cross`).
17:48:34-17:49:17 on 2026-10-23 (take 20261023T144821Z-27): the Outer Cloister's way into the Monastery Gate marked
on roof at (15177.5, 5005.0); the door (class 24) stood in the edge's gap at (15141, 5002)."""

from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.exits import door_passage
from inventory_tracking.levels.model import Room


# The Outer Cloister's south rooms (tiles), each touching the Monastery Gate (26), as the take read them
ROOMS = (*(Room(166, x, 992, 8, 8, leads_to=(26,)) for x in range(3008, 3056, 8)), Room(160, 3008, 960, 48, 32))
EDGE_DOOR = Door(1454672102, 24, 0, 15141.0, 5002.0)
INNER_DOOR = Door(1294219671, 23, 0, 15200.0, 4940.0)


def doors(*found: Door) -> tuple[Door, ...]:
    return found


def test_the_door_in_the_edge_gap_is_the_passage():
    assert door_passage(doors(INNER_DOOR, EDGE_DOOR), ROOMS, (15177.5, 5005.0)) == (15141.0, 5007.0)


def test_a_door_inside_the_level_or_too_far_along_the_edge_is_not():
    assert door_passage(doors(INNER_DOOR), ROOMS, (15177.5, 5005.0)) is None
    far = Door(9, 24, 0, 15041.0, 5002.0)  # 136 units along the edge
    assert door_passage(doors(far), ROOMS, (15177.5, 5005.0)) is None


def test_an_open_door_still_leads_the_walk_through_it():
    opened = Door(EDGE_DOOR.unit_id, 24, 1, EDGE_DOOR.x, EDGE_DOOR.y)
    assert door_passage(doors(opened), ROOMS, (15177.5, 5005.0)) == (15141.0, 5007.0)


def test_no_rooms_or_a_place_inside_the_level_gives_nothing():
    assert door_passage(doors(EDGE_DOOR), (), (15177.5, 5005.0)) is None
    assert door_passage(doors(EDGE_DOOR), ROOMS, (15177.5, 4990.0)) is None
