import math

from inventory_tracking.macros.tour import KEEP_TILES, centre, length, shown, tour


def grid(columns, rows):
    return [(1000 + 8 * column, 1000 + 8 * row, 8, 8) for row in range(rows) for column in range(columns)]


def seen_from(rooms, stops):
    sees = dict(zip(rooms, shown(tuple(rooms)), strict=True))
    mask = 0
    for stop in stops:
        mask |= sees[stop]
    return {room for at, room in enumerate(rooms) if mask >> at & 1}


def nearest_room_hops(rooms, here, explored):
    """Tiles for the rule before: to the nearest unexplored room's nearest tile, in steps of 5.5."""
    explored, travelled = set(explored), 0.0
    while len(explored) < len(rooms):
        for room in rooms:
            if room[0] <= here[0] < room[0] + 8 and room[1] <= here[1] < room[1] + 8:
                explored |= seen_from(rooms, [room])
        left = [room for room in rooms if room not in explored]
        if not left:
            break
        edges = [(min(max(here[0], r[0] + 0.5), r[0] + 7.5), min(max(here[1], r[1] + 0.5), r[1] + 7.5)) for r in left]
        goal = min(edges, key=lambda edge: math.dist(here, edge))
        away = math.dist(here, goal)
        step = min(away, 5.5)
        here = (here[0] + (goal[0] - here[0]) * step / away, here[1] + (goal[1] - here[1]) * step / away)
        travelled += step
    return travelled


def test_a_place_shows_its_room_and_the_rooms_touching_it_corners_too():
    rooms = grid(4, 4)
    assert len(seen_from(rooms, [rooms[5]])) == 9
    assert len(seen_from(rooms, [rooms[0]])) == 4


def test_the_tour_shows_every_unexplored_room():
    rooms = grid(10, 10)
    here = centre(rooms[45])
    stops = tour(rooms, here, seen_from(rooms, [rooms[45]]))
    assert seen_from(rooms, [rooms[45], *stops]) == set(rooms)


def test_the_tour_is_shorter_than_going_to_the_nearest_room_each_time():
    rooms = grid(10, 10)
    here = centre(rooms[45])
    explored = seen_from(rooms, [rooms[45]])
    assert length(here, tour(rooms, here, explored)) < 0.85 * nearest_room_hops(rooms, here, explored)


def test_a_dead_end_is_seen_before_the_long_way_is_gone():
    # A row of ten, the character in the third room: one room to see west, six east. East first
    # would come back the whole row for the one.
    rooms = grid(10, 1)
    stops = tour(rooms, centre(rooms[2]), seen_from(rooms, [rooms[2]]))
    assert stops[0][0] < rooms[2][0]
    assert stops[-1][0] > rooms[6][0]


def test_nothing_unexplored_is_no_tour():
    rooms = grid(3, 3)
    assert tour(rooms, centre(rooms[0]), set(rooms)) == []


def test_a_room_nothing_lands_in_is_seen_from_beside_it_and_one_out_of_sight_is_left():
    rooms = [*grid(3, 1), (1100, 1000, 8, 8)]  # a row of three and a room far off
    standable = rooms[:2]
    stops = tour(rooms, centre(rooms[0]), {rooms[0], rooms[1]}, standable)
    assert stops == [rooms[1]]  # the third is seen from the second; the far one from nowhere
    assert tour(rooms, centre(rooms[0]), set(rooms[:3]), standable) == []


def test_the_tour_before_is_kept_unless_a_new_one_is_a_rooms_side_shorter():
    # The middle three of a row of five are seen: an end either side. From two tiles east of the
    # middle the east end first is shorter by four tiles, which is not worth turning around for.
    rooms = grid(5, 1)
    explored = set(rooms[1:4])
    east_of_middle = (centre(rooms[2])[0] + 2, centre(rooms[2])[1])
    fresh = tour(rooms, east_of_middle, explored)
    west_first = fresh[::-1]
    assert fresh[0][0] > west_first[0][0]
    assert length(east_of_middle, west_first) - length(east_of_middle, fresh) < KEEP_TILES
    assert tour(rooms, east_of_middle, explored, before=west_first) == west_first
    far_east = centre(rooms[3])
    assert tour(rooms, far_east, explored, before=west_first) == fresh


def test_a_stop_of_the_tour_before_that_shows_nothing_new_is_dropped():
    rooms = grid(5, 1)
    before = [rooms[1], rooms[3]]
    assert tour(rooms, centre(rooms[2]), set(rooms[:4]), before=before) == [rooms[3]]
