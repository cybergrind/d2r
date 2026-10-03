"""Act 1 and Act 5 zones and sub-zones (D2MOO DrlgOutWild/DrlgOutSiege/DrlgMaze, d2data; 2026-10-01)."""

import pytest

from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for


def rows(guidance):
    return [(p.label, p.kind, preset_name(p.room.preset)) for p in guidance.pois]


def guide(area, *rooms):
    return handler_for(area).guide(LevelSnapshot(Location(area, 0, 4, 4), rooms))


def test_blood_moor_marks_the_den_and_names_the_gap_by_elimination():
    guidance = guide(2, Room(52, 40, 40, 8, 8), Room(5, 0, 8, 8, 8, 3, (0, 8, 8, 8), (1,)), Room(6, 72, 8, 8, 8, 3))

    assert rows(guidance) == [
        ('Cold Plains', 'stairs', 'Act 1 - Wild Border 3'),
        ('Rogue Encampment', 'previous', 'Act 1 - Wild Border 2'),
        ('Den of Evil', 'stairs', 'Act 1 - DOE Entrance'),
    ]
    assert guidance.problems == ()


def test_burial_grounds_marks_the_graveyard_and_the_way_back():
    guidance = guide(17, Room(108, 8, 8, 24, 32), Room(4, 0, 0, 8, 8, 4))

    assert rows(guidance) == [
        ('Cold Plains', 'previous', 'Act 1 - Wild Border 1'),
        ('Graveyard', 'target', 'Act 1 - Graveyard'),
    ]


def test_act1_caves_and_crypts():
    den = guide(8, Room(85, 0, 0, 24, 24), Room(96, 24, 0, 24, 24))
    passage = guide(10, Room(85, 0, 0, 24, 24), Room(92, 24, 0, 24, 24), Room(90, 48, 0, 24, 24))
    hole = guide(11, Room(85, 0, 0, 24, 24), Room(93, 24, 0, 24, 24))
    crypt = guide(18, Room(141, 0, 0, 8, 8), Room(148, 8, 0, 8, 8))
    mausoleum = guide(19, Room(141, 0, 0, 8, 8), Room(152, 8, 0, 8, 8))

    assert [p.label for p in den.pois] == ['Corpsefire', 'Blood Moor']
    assert [p.label for p in passage.pois] == ['Level 2', 'Dark Wood', 'Stony Field']
    assert [p.label for p in hole.pois] == ['Next level', 'Black Marsh']
    assert [p.label for p in crypt.pois] == ['Bonebreak', 'Burial Grounds']
    assert [p.label for p in mausoleum.pois] == ['Chest', 'Burial Grounds']
    assert all(g.problems == () for g in (den, passage, hole, crypt, mausoleum))


def test_bloody_foothills_marks_both_ends():
    guidance = guide(110, Room(865, 0, 0, 16, 48), Room(879, 200, 0, 16, 48))

    assert rows(guidance) == [
        ('Frigid Highlands', 'stairs', 'Act 5 - Siege To Barricade'),
        ('Harrogath', 'previous', 'Act 5 - Siege To Town'),
    ]


@pytest.mark.parametrize(
    ('area', 'rooms', 'expected'),
    [
        (
            111,
            (Room(880, 0, 0, 16, 32), Room(909, 32, 0, 32, 16), Room(955, 64, 0, 16, 16)),
            [
                ('Exit', 'Act 5 - Barricade Exit 32x16'),
                ('Abaddon', 'Act 5 - Barricade Hell Portal N'),
                ('Bloody Foothills', 'Act 5 - Barricade To Siege'),
            ],
        ),
        (
            112,
            (Room(913, 0, 0, 32, 16), Room(953, 32, 0, 8, 8), Room(907, 48, 0, 16, 32)),
            [
                ('Crystalline Passage', 'Act 5 - Barricade To Cave 32x16'),
                ('Exit', 'Act 5 - Barricade Entrance 16x32'),
                ('Waypoint', 'Act 5 - Barricade Waypoint Dirt'),
            ],
        ),
        (
            117,
            (Room(985, 0, 0, 32, 16), Room(984, 32, 0, 16, 32), Room(954, 64, 0, 8, 8), Room(956, 80, 0, 16, 16)),
            [
                ("Ancients' Way", 'Act 5 - Barricade To Cave 32x16 Snow'),
                ('Infernal Pit', 'Act 5 - Barricade Hell Portal W'),
                ('Waypoint', 'Act 5 - Barricade Waypoint Snow'),
                ('Glacial Trail', 'Act 5 - Barricade From Cave 16x32 Snow'),
            ],
        ),
    ],
)
def test_barricade_levels(area, rooms, expected):
    guidance = guide(area, *rooms)

    assert [(label, name) for label, _, name in rows(guidance)] == expected
    assert guidance.problems == ()


def test_ancients_way_tracks_summit_icy_cellar_waypoint_and_way_back():
    rooms = (Room(1025, 0, 0, 16, 16), Room(1028, 16, 0, 16, 16), Room(1036, 32, 0, 16, 16), Room(1018, 48, 0, 16, 16))
    guidance = guide(118, *rooms)

    assert [p.label for p in guidance.pois] == ['Arreat Summit', 'Icy Cellar', 'Waypoint', 'Frozen Tundra']
    assert guidance.problems == ()


def test_new_act1_act5_handlers_stay_unconfirmed():
    assert not any(handler_for(area).confirmed for area in (2, 8, 10, 11, 17, 18, 19, 110, 111, 112, 117, 118))
