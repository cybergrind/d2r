"""Act 2 zones and sub-zones (D2MOO DrlgOutDesr/DrlgMaze, d2data; 2026-10-01; no evidence yet)."""

import pytest

from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for
from tests.inventory_tracking.levels.fixtures import replay


def rows(guidance):
    return [(p.label, p.kind, preset_name(p.room.preset)) for p in guidance.pois]


def guide(area, *rooms):
    return handler_for(area).guide(LevelSnapshot(Location(area, 0, 4, 4), rooms))


@pytest.mark.parametrize(
    ('area', 'preset', 'label'),
    [(42, 388, 'Halls of the Dead'), (43, 390, 'Maggot Lair'), (45, 389, 'Claw Viper Temple')],
)
def test_desert_levels_point_at_their_entrance(area, preset, label):
    guidance = guide(area, Room(0, 0, 0, 8, 8), Room(preset, 8, 0, 8, 8))

    assert [(p.label, p.kind, p.room.preset) for p in guidance.pois] == [(label, 'stairs', preset)]
    assert guidance.problems == ()


def test_lost_city_marks_the_ancient_tunnels_and_the_dark_elder_ruin():
    guidance = guide(44, Room(412, 0, 0, 8, 8), Room(413, 8, 0, 16, 16))

    assert rows(guidance) == [
        ('Ancient Tunnels', 'stairs', 'Act 2 - Desert Ruins Sewer'),
        ('Dark Elder', 'target', 'Act 2 - Desert Ruins Elder'),
    ]
    assert guide(44, Room(412, 0, 0, 8, 8)).problems == ()  # the Elder ruin is optional


def test_canyon_marks_every_tomb_entrance_and_the_center_warp():
    tombs = [Room(383, 16 * i, 0, 16, 8) for i in range(3)] + [Room(385, 0, 8 + 16 * i, 8, 16) for i in range(3)]
    guidance = guide(46, *tombs, Room(387, 64, 64, 16, 16), Room(394, 32, 32, 8, 8))

    assert [p.label for p in guidance.pois] == ['Tomb'] * 7 + ['Waypoint']
    assert guidance.problems == ()


def test_sewers_mark_the_ladders_waypoint_and_radament():
    level1 = guide(47, Room(333, 0, 0, 12, 12), Room(336, 12, 0, 12, 12), Room(338, 24, 0, 12, 12))
    level2 = guide(48, Room(334, 0, 0, 12, 12), Room(346, 12, 0, 12, 12), Room(340, 24, 0, 12, 12))
    level3 = guide(49, Room(332, 0, 0, 12, 12), Room(343, 12, 0, 12, 12))
    tunnels = guide(65, Room(335, 0, 0, 12, 12), Room(351, 12, 0, 12, 12))

    assert rows(level1) == [
        ('Next level', 'stairs', 'Act 2 - Sewer Next E'),
        ('Lut Gholein', 'previous', 'Act 2 - Sewer Prev E'),
        ('Lut Gholein', 'previous', 'Act 2 - Sewer Prev NS'),
    ]
    assert rows(level2) == [
        ('Next level', 'stairs', 'Act 2 - Sewer Next N'),
        ('Waypoint', 'waypoint', 'Act 2 - Sewer Waypoint E'),
        ('Sewers 1', 'previous', 'Act 2 - Sewer Prev S'),
    ]
    assert rows(level3) == [
        ('Radament', 'target', "Act 2 - Sewer Radament's Lair S"),
        ('Sewers 2', 'previous', 'Act 2 - Sewer Prev W'),
    ]
    assert rows(tunnels) == [
        ('Chest', 'target', 'Act 2 - Sewer Chest S'),
        ('Lost City', 'previous', 'Act 2 - Sewer Prev N'),
    ]
    assert all(g.problems == () for g in (level1, level2, level3, tunnels))


@pytest.mark.parametrize(
    ('area', 'special', 'expected'),
    [
        (56, 449, [('Next level', 'Act 2 - Tomb Next E'), ('Dry Hills', 'Act 2 - Tomb Prev NSW')]),
        (
            57,
            449,
            [
                ('Next level', 'Act 2 - Tomb Next E'),
                ('Waypoint', 'Act 2 - Tomb Waypoint N'),
                ('Halls of the Dead 1', 'Act 2 - Tomb Prev NSW'),
            ],
        ),
        (60, 457, [('Horadric Cube', 'Act 2 - Tomb Cube E'), ('Halls of the Dead 2', 'Act 2 - Tomb Prev NSW')]),
        (58, 449, [('Next level', 'Act 2 - Tomb Next E'), ('Valley of Snakes', 'Act 2 - Tomb Prev NSW')]),
    ],
)
def test_tombs_track_their_rooms(area, special, expected):
    rooms = [Room(446, 0, 0, 16, 16), Room(special, 16, 0, 16, 16)]
    if area == 57:
        rooms.append(Room(479, 32, 0, 16, 16))

    guidance = guide(area, *rooms)

    assert [(label, name) for label, _, name in rows(guidance)] == expected
    assert guidance.problems == ()


@pytest.mark.parametrize(
    ('area', 'special', 'expected'),
    [
        (62, 502, [('Next level', 'Act 2 - Lair Next E'), ('Far Oasis', 'Act 2 - Lair Prev S')]),
        (63, 502, [('Next level', 'Act 2 - Lair Next E'), ('Maggot Lair 1', 'Act 2 - Lair Prev S')]),
    ],
)
def test_maggot_lair_tracks_its_rooms(area, special, expected):
    guidance = guide(area, Room(499, 0, 0, 10, 10), Room(special, 10, 0, 10, 10))

    assert [(label, name) for label, _, name in rows(guidance)] == expected
    assert guidance.problems == ()


def test_maggot_lair_3_points_at_coldworm_where_the_user_stood():
    snapshot = replay('maggot_lair_3_coldworm')  # Win+C at Coldworm, 2026-10-01
    guidance = handler_for(64).guide(snapshot)

    assert rows(guidance) == [
        ('Coldworm', 'target', 'Act 2 - Lair Tight Spot S'),
        ('Treasure room', 'target', 'Act 2 - Lair Treasure W'),
        ('Maggot Lair 2', 'previous', 'Act 2 - Lair Prev N'),
    ]
    coldworm = guidance.pois[0].room
    x, y = snapshot.location.x / 5, snapshot.location.y / 5
    assert coldworm.x <= x < coldworm.x + coldworm.width
    assert coldworm.y <= y < coldworm.y + coldworm.height
    assert guidance.problems == ()
    assert handler_for(64).confirmed


def test_palace_cellar_1_marks_the_waypoint_room():
    guidance = guide(52, Room(358, 0, 0, 16, 16), Room(361, 16, 0, 16, 16, variant=2))

    assert rows(guidance) == [('Waypoint', 'waypoint', 'Act 2 - Basement NW')]


def test_tal_rasha_marks_kaa_and_false_tomb_chests_without_breaking_the_true_tomb():
    boss = guide(67, Room(444, 0, 0, 16, 16), Room(469, 16, 0, 16, 16))
    false = guide(68, Room(444, 0, 0, 16, 16), Room(473, 16, 0, 16, 16))
    true = handler_for(70).guide(replay('tal_rasha_true_tomb'))

    assert [p.label for p in boss.pois] == ['Ancient Kaa', 'Canyon of the Magi']
    assert [p.label for p in false.pois] == ['Chest', 'Canyon of the Magi']
    assert [p.label for p in true.pois] == ['Orifice', 'Canyon of the Magi']
    assert boss.problems == false.problems == true.problems == ()


def test_new_act2_handlers_stay_unconfirmed():
    areas = (42, 43, 44, 45, 46, 47, 48, 49, 52, 56, 57, 58, 60, 62, 63, 65)
    assert not any(handler_for(area).confirmed for area in areas)
