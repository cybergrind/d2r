"""Generic ways out: a room whose preset has warp tiles leads to the level in that warp slot."""

import json
import math
from dataclasses import replace

from inventory_tracking.levels.exits import (
    EDGE_SNAP,
    INWARD_STEP,
    PASSAGE_PAST,
    TOWN_WAYS_OUT,
    border_exits,
    guide_level,
    passage_of,
    poi_area,
    through,
    warp_exits,
    with_exits,
)
from inventory_tracking.levels.model import Guidance, LevelSnapshot, Location, Poi, Room, Walkable, pack_cells
from inventory_tracking.levels.presets import display_name
from inventory_tracking.levels.registry import handler_for
from tests.inventory_tracking.levels.fixtures import FIXTURES, handler_of, replay


CAVE_TREASURE_2 = 104  # 'Act 1 - Cave Treasure 2', the whole of Cave Level 2: warp slot 1 at (4.5, 5.5)
GRAVEYARD = 108  # 'Act 1 - Graveyard': warp slots 0 (Crypt) and 1 (Mausoleum)
TOWER_2 = 164  # 'Act 1 - Tower 2', the whole of the Forgotten Tower: warp slots 0 and 1
CAVE_LEVEL_2, BURIAL_GROUNDS, FORGOTTEN_TOWER = 13, 17, 20


def snapshot_of(area, *rooms):
    return LevelSnapshot(Location(area, 0, 0, 0), rooms)


def marks(pois):
    return [(poi.label, poi.kind) for poi in pois]


def test_a_level_without_a_handler_gets_its_way_out():
    room = Room(CAVE_TREASURE_2, 100, 200, 24, 24, 0, (100, 200, 24, 24))

    [poi] = warp_exits(snapshot_of(CAVE_LEVEL_2, room))

    assert (poi.label, poi.kind, poi.spot) == ('Cave 1', 'previous', (104.5, 205.5))


def test_each_warp_of_one_preset_is_named_for_its_own_level():
    room = Room(GRAVEYARD, 0, 0, 24, 32, 0, (0, 0, 24, 32))

    pois = warp_exits(snapshot_of(BURIAL_GROUNDS, room))

    assert [(poi.label, poi.kind, poi.spot) for poi in pois] == [
        ('Crypt', 'stairs', (12.5, 27.5)),
        ('Mausoleum', 'stairs', (11.5, 6.5)),
    ]


def test_the_way_on_comes_before_the_way_back():
    # The Forgotten Tower (20) is one preset with both doors: slot 0 Black Marsh, slot 1 the cellar.
    room = Room(TOWER_2, 0, 0, 8, 8, 0, (0, 0, 8, 8))

    pois = guide_level(None, snapshot_of(FORGOTTEN_TOWER, room)).pois

    assert marks(pois) == [('Tower Cellar 1', 'stairs'), ('Black Marsh', 'previous')]


def test_a_chunked_preset_is_one_way_out():
    chunks = [Room(GRAVEYARD, x, y, 8, 8, 0, (0, 0, 24, 32)) for x in (0, 8, 16) for y in (0, 8, 16, 24)]

    assert len(warp_exits(snapshot_of(BURIAL_GROUNDS, *chunks))) == 2


def test_an_unreadable_variant_gives_no_way_out():
    assert warp_exits(snapshot_of(CAVE_LEVEL_2, Room(CAVE_TREASURE_2, 100, 200, 24, 24))) == ()


def test_the_way_back_the_handler_leaves_out_is_added():
    snapshot = replay('durance_of_hate_2')
    guidance = handler_of(101).guide(snapshot)

    merged = with_exits(guidance, snapshot)

    assert marks(merged.pois) == [*marks(guidance.pois), ('Durance of Hate 1', 'previous')]
    assert merged.problems == guidance.problems


def test_ways_out_the_handler_already_marks_are_not_repeated():
    snapshot = replay('catacombs_2')
    guidance = handler_of(35).guide(snapshot)

    assert with_exits(guidance, snapshot) == guidance


def test_a_target_in_the_same_preset_keeps_its_place_beside_the_way_out():
    snapshot = replay('halls_of_vaught_nihlw')
    guidance = handler_of(124).guide(snapshot)

    merged = with_exits(guidance, snapshot)

    assert marks(merged.pois) == [('Nihlathak', 'target'), ('Halls of Pain', 'previous')]


def test_no_rooms_no_ways_out():
    assert with_exits(Guidance(), snapshot_of(CAVE_LEVEL_2)) == Guidance()


DRY_HILLS, FAR_OASIS, BLOOD_MOOR = 42, 43, 2
BORDER = 400  # any room that is not a warp


def test_a_level_joined_without_a_warp_is_marked_where_the_rooms_touch_it():
    rooms = [Room(BORDER, x, 0, 8, 8, 0, None, (FAR_OASIS,)) for x in (0, 8, 16)] + [Room(0, 8, 8, 8, 8)]

    [poi] = border_exits(snapshot_of(DRY_HILLS, *rooms))

    assert (poi.label, poi.kind, poi.room.x, poi.area) == ('Far Oasis', 'stairs', 8, FAR_OASIS)


def test_a_lower_numbered_neighbour_is_the_way_back():
    [poi] = border_exits(snapshot_of(FAR_OASIS, Room(BORDER, 0, 0, 8, 8, 0, None, (DRY_HILLS,))))

    assert (poi.label, poi.kind) == ('Dry Hills', 'previous')


def test_a_neighbour_behind_a_marked_way_out_is_not_marked_twice():
    room = Room(CAVE_TREASURE_2, 100, 200, 24, 24, 0, (100, 200, 24, 24), (9,))

    assert marks(guide_level(None, snapshot_of(CAVE_LEVEL_2, room)).pois) == [('Cave 1', 'previous')]


def test_a_neighbour_the_border_gaps_will_name_is_left_to_them():
    snapshot = replay('cold_plains_two_known')
    guidance = guide_level(handler_for(3), snapshot)

    assert sorted(marks(guidance.pois)) == sorted(marks(handler_of(3).guide(snapshot).pois))


def test_a_level_without_a_handler_gets_its_borders_too():
    rooms = (Room(BORDER, 0, 0, 8, 8, 0, None, (BLOOD_MOOR,)),)

    assert marks(guide_level(None, snapshot_of(1, *rooms)).pois) == [('Blood Moor', 'stairs')]


def test_a_town_marks_only_its_way_out_to_the_wilderness():
    # User, 2026-10-06: in Lut Gholein the sewers and the Harem are noise; the gate to the Rocky
    # Waste is the one worth an arrow, since it is in one of two places.
    rooms = (
        Room(BORDER, 0, 0, 8, 8, 0, None, (47,)),
        Room(BORDER, 8, 0, 8, 8, 0, None, (50,)),
        Room(BORDER, 16, 0, 8, 8, 0, None, (41,)),
    )

    assert marks(guide_level(None, snapshot_of(40, *rooms)).pois) == [('Rocky Waste', 'stairs')]
    assert {town: display_name(next(iter(out))) for town, out in TOWN_WAYS_OUT.items()} == {
        1: 'Blood Moor',
        40: 'Rocky Waste',
        75: 'Spider Forest',
        103: 'Outer Steppes',
        109: 'Bloody Foothills',
    }


def test_a_town_marks_its_waypoint_where_the_layout_puts_it():
    # User, 2026-10-07. 'Act 1 - Town 1' (preset 1) has four layouts, each with its own waypoint;
    # the town is read as 8x8 chunks sharing the preset's bounds.
    def town(variant):
        block = (5000, 5000, 56, 40)
        return snapshot_of(1, Room(1, 5000, 5000, 8, 8, variant, block), Room(1, 5008, 5000, 8, 8, variant, block))

    def waypoints(snapshot):
        return [(poi.label, poi.spot) for poi in guide_level(None, snapshot).pois if poi.kind == 'waypoint']

    assert waypoints(town(0)) == [('Waypoint', (5022.8, 5001.8))]
    assert waypoints(town(2)) == [('Waypoint', (5023.8, 5018.8))]
    assert waypoints(town(None)) == []  # the layout is not read yet: no guess
    lut_gholein = snapshot_of(40, Room(301, 5000, 5000, 8, 8, None, (5000, 5000, 56, 56)))
    assert waypoints(lut_gholein) == [('Waypoint', (5013.8, 5016.8))]  # both layouts agree
    assert waypoints(snapshot_of(13, Room(CAVE_TREASURE_2, 100, 200, 24, 24, 0))) == []  # towns only


def test_an_open_passages_far_place_is_a_tile_past_the_levels_edge():
    """`through`: a mark beyond the level's rooms (the River of Flame's bridge end, half a tile past the last Bridge 2)
    is crossed from the rooms' nearest point toward it, PASSAGE_PAST on; a mark in a border's room goes the way the
    level touches the next one to where its rooms end, then PASSAGE_PAST on."""
    bridge = (Room(856, 1548, 1120, 8, 8), Room(856, 1556, 1120, 8, 8), Room(856, 1564, 1120, 8, 8))
    assert through(bridge, (1560.0, 1119.5), 108) == (1560.0, 1120.0 - PASSAGE_PAST)
    east = (Room(1, 100, 100, 8, 8), Room(1, 108, 100, 8, 8, leads_to=(3,)))
    assert through(east, (112.0, 104.0), 3) == (116.0 + PASSAGE_PAST, 104.0)
    # No room known to touch level 4 yet: the mark's side of the level's middle (Upper Kurast's Kurast Causeway on its
    # north edge, 2026-10-20 01:36:23); a mark at the middle has no side
    assert through(east, (112.0, 104.0), 4) == (116.0 + PASSAGE_PAST, 104.0)
    north = (Room(644, 968, 496, 8, 8), Room(1, 968, 504, 8, 8), Room(1, 968, 512, 8, 8))
    assert through(north, (968.0, 496.0), 82) == (968.0, 496.0 - PASSAGE_PAST - INWARD_STEP)
    assert through(east, (108.0, 104.0), 4) is None
    assert through((), (112.0, 104.0), 3) is None


def test_only_a_way_out_with_no_warp_has_a_far_place():
    """`passage_of`: a way out to a level joined with no warp; not a warp's (stairs), an object's (a portal), a
    waypoint, nor a mark that names no level."""
    room = Room(856, 1556, 1120, 8, 8)
    sanctum = Poi('Chaos Sanctum', room, 'stairs', (1560.0, 1119.5), 108)
    assert passage_of(107, (room,), sanctum, (1560.0, 1119.5)) == (1560.0, 1120.0 - PASSAGE_PAST)
    assert passage_of(106, (room,), replace(sanctum, area=107), (1560.0, 1119.5)) is None  # a warp joins them
    assert passage_of(107, (room,), replace(sanctum, use=1), (1560.0, 1119.5)) is None
    assert passage_of(107, (room,), replace(sanctum, kind='waypoint'), (1560.0, 1119.5)) is None
    assert passage_of(107, (room,), replace(sanctum, area=None), (1560.0, 1119.5)) is None


def test_a_handlers_way_out_names_its_level_by_its_label():
    # The Kurast handler's 'Kurast Causeway' (2026-10-20 01:47:26) named no level: no passage, taken for a door
    north = (Room(644, 968, 496, 8, 8), Room(1, 968, 504, 8, 8))
    causeway = Poi('Kurast Causeway', north[0], 'stairs', (968.0, 496.0))
    assert poi_area(causeway) == 82
    assert passage_of(81, north, causeway, (968.0, 496.0)) == (968.0, 496.0 - PASSAGE_PAST - INWARD_STEP)
    assert poi_area(replace(causeway, label='Sewers')) is None  # several levels' name
    assert poi_area(replace(causeway, kind='target')) is None  # not a way out


# Lost City to Valley of Snakes, 2026-10-20 01:09 (take 20261019T220930Z-44; rca/2026-10-20/valley-of-snakes-findings.md
# §1): the border mark is the centre of room 379 'Desert Cliff Left Ends', all cliff; the canyon reaches the north
# edge at tile (807, 1000), 21 tiles west.
CLIFF_MARK = (828.0, 1004.0)
VALLEY_OF_SNAKES = 45


def lost_city() -> tuple[tuple[Room, ...], tuple[Walkable, ...]]:
    """The take's rooms and the grids of its two north rows (the fixture is trimmed to those)."""
    data = json.loads((FIXTURES / 'lost_city_valley_border.json').read_text())
    return tuple(Room.from_row(row) for row in data['rooms']), tuple(Walkable(*grid) for grid in data['ground'])


def test_a_border_mark_on_a_cliff_crosses_at_the_open_edge_tile():
    rooms, grids = lost_city()
    assert through(rooms, CLIFF_MARK, VALLEY_OF_SNAKES) == (828.0, 1000.0 - PASSAGE_PAST - 0.25)  # unread: as before
    assert through(rooms, CLIFF_MARK, VALLEY_OF_SNAKES, grids) == (807.5, 1000.0 - PASSAGE_PAST - 0.25)
    poi = Poi('Valley of Snakes', rooms[0], 'stairs', area=VALLEY_OF_SNAKES)
    assert passage_of(44, rooms, poi, CLIFF_MARK, grids) == (807.5, 998.75)


def test_the_open_edge_is_an_outer_tile_with_footing_within_edge_snap_of_the_mark():
    """Two rows of seven rooms, the middle top room touching level 3 to the north; the grids are wall but where
    given as floor. Only a top-row tile within EDGE_SNAP of the mark moves it; a mark beyond the rooms never moves."""
    floor, wall = pack_cells('1' * 1600), pack_cells('0' * 1600)
    rooms = tuple(
        Room(1, x, y, 8, 8, leads_to=(3,) if (x, y) == (124, 100) else ())
        for y in (100, 108)
        for x in range(100, 156, 8)
    )
    mark = (128.0, 104.0)

    def grids(*floors):
        return tuple(Walkable(room.x, room.y, 8, 8, floor if (room.x, room.y) in floors else wall) for room in rooms)

    straight = (128.0, 100.0 - PASSAGE_PAST - 0.25)
    assert through(rooms, mark, 3, grids()) == straight  # no open tile read
    assert through(rooms, mark, 3, grids((124, 108))) == straight  # floor below the mark: no edge tile
    assert through(rooms, mark, 3, grids((148, 100))) == (148.5, 100.0 - PASSAGE_PAST - 0.25)
    assert math.dist(mark, (148.5, 100.5)) <= EDGE_SNAP
    wide = (*rooms, Room(1, 156, 100, 8, 8))
    beyond = (*grids(), Walkable(156, 100, 8, 8, floor))
    assert math.dist(mark, (156.5, 100.5)) > EDGE_SNAP
    assert through(wide, mark, 3, beyond) == straight
    # A mark beyond the rooms (the River of Flame's bridge end) is crossed as before, whatever the grids
    bridge = (Room(856, 1548, 1120, 8, 8), Room(856, 1556, 1120, 8, 8), Room(856, 1564, 1120, 8, 8))
    floors = tuple(Walkable(room.x, room.y, 8, 8, floor) for room in bridge)
    assert through(bridge, (1560.0, 1119.5), 108, floors) == (1560.0, 1120.0 - PASSAGE_PAST)
