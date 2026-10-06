"""Generic ways out: a room whose preset has warp tiles leads to the level in that warp slot."""

from inventory_tracking.levels.exits import TOWN_WAYS_OUT, border_exits, guide_level, warp_exits, with_exits
from inventory_tracking.levels.model import Guidance, LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import display_name
from inventory_tracking.levels.registry import handler_for
from tests.inventory_tracking.levels.fixtures import replay


CAVE_TREASURE_2 = 104  # 'Act 1 - Cave Treasure 2', the whole of Cave Level 2: warp slot 1 at (4.5, 5.5)
GRAVEYARD = 108  # 'Act 1 - Graveyard': warp slots 0 (Crypt) and 1 (Mausoleum)
CAVE_LEVEL_2, BURIAL_GROUNDS = 13, 17


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


def test_a_chunked_preset_is_one_way_out():
    chunks = [Room(GRAVEYARD, x, y, 8, 8, 0, (0, 0, 24, 32)) for x in (0, 8, 16) for y in (0, 8, 16, 24)]

    assert len(warp_exits(snapshot_of(BURIAL_GROUNDS, *chunks))) == 2


def test_an_unreadable_variant_gives_no_way_out():
    assert warp_exits(snapshot_of(CAVE_LEVEL_2, Room(CAVE_TREASURE_2, 100, 200, 24, 24))) == ()


def test_the_way_back_the_handler_leaves_out_is_added():
    snapshot = replay('durance_of_hate_2')
    guidance = handler_for(101).guide(snapshot)

    merged = with_exits(guidance, snapshot)

    assert marks(merged.pois) == [*marks(guidance.pois), ('Durance of Hate 1', 'previous')]
    assert merged.problems == guidance.problems


def test_ways_out_the_handler_already_marks_are_not_repeated():
    snapshot = replay('catacombs_2')
    guidance = handler_for(35).guide(snapshot)

    assert with_exits(guidance, snapshot) == guidance


def test_a_target_in_the_same_preset_keeps_its_place_beside_the_way_out():
    snapshot = replay('halls_of_vaught_nihlw')
    guidance = handler_for(124).guide(snapshot)

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

    assert sorted(marks(guidance.pois)) == sorted(marks(handler_for(3).guide(snapshot).pois))


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
