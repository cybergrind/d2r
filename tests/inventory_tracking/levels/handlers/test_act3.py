"""Act 3 zones and sub-zones (D2MOO DrlgOutPlace/DrlgOutJung/DrlgMaze, d2data; 2026-10-01).

Lower Kurast's gates and waypoint are checked against its two real fixtures; everything else
comes from synthetic snapshots until evidence exists.
"""

import pytest

from inventory_tracking.levels.exits import with_exits
from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for
from tests.inventory_tracking.levels.fixtures import replay


def rows(guidance):
    return [(p.label, p.kind, preset_name(p.room.preset)) for p in guidance.pois]


def guide(area, *rooms, at=(4, 4)):
    return handler_for(area).guide(LevelSnapshot(Location(area, 0, *at), rooms))


@pytest.mark.parametrize('fixture', ['lower_kurast_camp', 'lower_kurast_game2'])
def test_lower_kurast_marks_both_gates_and_the_waypoint_in_real_games(fixture):
    guidance = handler_for(79).guide(replay(fixture))

    assert [row for row in rows(guidance) if row[0] != 'Super chests'] == [
        ('Kurast Bazaar', 'stairs', 'Act 3 - Slums Gate N'),
        ('Waypoint', 'waypoint', 'Act 3 - Burbs Waypoint'),
        ('Flayer Jungle', 'previous', 'Act 3 - Slums Gate S'),
    ]
    assert guidance.problems == ()


def test_kurast_bazaar_marks_gates_temples_sewers_and_waypoint():
    guidance = guide(
        80,
        Room(627, 0, 0, 8, 8),  # Burbs Gate N
        Room(628, 8, 0, 8, 8),  # Burbs Gate S
        Room(630, 16, 0, 16, 16, variant=0),  # Burbs Temple, file 0
        Room(630, 32, 0, 16, 16, variant=1),
        Room(629, 48, 0, 8, 8, variant=0),  # Burbs Sewer
        Room(629, 56, 0, 8, 8, variant=1),
        Room(631, 64, 0, 8, 8),
    )

    assert rows(guidance) == [
        ('Upper Kurast', 'stairs', 'Act 3 - Burbs Gate N'),
        ('Ruined Temple', 'target', 'Act 3 - Burbs Temple'),
        ('Disused Fane', 'target', 'Act 3 - Burbs Temple'),
        ('Sewers', 'stairs', 'Act 3 - Burbs Sewer'),
        ('Sewers', 'stairs', 'Act 3 - Burbs Sewer'),
        ('Waypoint', 'waypoint', 'Act 3 - Burbs Waypoint'),
        ('Lower Kurast', 'previous', 'Act 3 - Burbs Gate S'),
    ]
    assert [p.room.x for p in guidance.pois[1:3]] == [16, 32]
    assert guidance.problems == ()


def test_upper_kurast_marks_gates_temples_sewers_and_waypoint():
    guidance = guide(
        81,
        Room(644, 0, 0, 16, 16),  # Metro Gate N
        Room(645, 16, 0, 8, 8),
        Room(647, 24, 0, 16, 16, variant=1),  # MetroTemple, file 1
        Room(647, 40, 0, 16, 16, variant=0),
        Room(646, 56, 0, 8, 8, variant=0),
        Room(646, 64, 0, 8, 8, variant=1),
        Room(631, 72, 0, 8, 8),
    )

    assert [(label, kind) for label, kind, _ in rows(guidance)] == [
        ('Kurast Causeway', 'stairs'),
        ('Forgotten Reliquary', 'target'),
        ('Forgotten Temple', 'target'),
        ('Sewers', 'stairs'),
        ('Sewers', 'stairs'),
        ('Waypoint', 'waypoint'),
        ('Kurast Bazaar', 'previous'),
    ]
    assert [p.room.x for p in guidance.pois[1:3]] == [40, 24]
    assert guidance.problems == ()


def test_travincal_points_at_the_north_temple_block():
    guidance = guide(83, Room(653, 0, 0, 16, 32), Room(654, 16, 0, 32, 32), Room(657, 16, 32, 32, 32))

    assert rows(guidance) == [('Durance of Hate', 'stairs', 'Act 3 - Travincal N')]


def test_great_marsh_marks_every_clearing():
    guidance = guide(77, Room(530, 0, 0, 32, 32), Room(585, 32, 0, 32, 32), Room(586, 0, 32, 32, 32))

    assert [(p.label, p.kind, p.room.x, p.room.y) for p in guidance.pois] == [
        ('Clearing', 'target', 32, 0),
        ('Clearing', 'target', 0, 32),
    ]
    assert guidance.problems == ()


@pytest.mark.parametrize(
    ('area', 'preset', 'caves'),
    [(76, 575, ['Arachnid Lair', 'Spider Cavern']), (78, 595, ['Swampy Pit 1', 'Flayer Dungeon 1'])],
)
def test_jungle_names_the_caves_and_takes_the_third_clearing_for_the_waypoint(area, preset, caves):
    rooms = [Room(preset + i, 32 * i, 0, 32, 32, i, (32 * i, 0, 32, 32)) for i in range(3)]
    snapshot = LevelSnapshot(Location(area, 0, 0, 0), tuple(rooms))

    guidance = with_exits(handler_for(area).guide(snapshot), snapshot)

    assert [(p.label, p.kind, p.room.x) for p in guidance.pois] == [
        ('Waypoint', 'waypoint', 64),
        (caves[0], 'stairs', 0),
        (caves[1], 'stairs', 32),
    ]
    assert guidance.problems == ()


@pytest.mark.parametrize(('area', 'label', 'chest'), [(84, 'Chest', 664), (85, "Khalim's Eye", 663)])
def test_spider_caves_mark_their_chest_room(area, label, chest):
    guidance = guide(area, Room(659, 0, 0, 16, 16), Room(chest, 16, 0, 16, 16))

    assert [(p.label, p.room.preset) for p in guidance.pois] == [(label, chest)]


@pytest.mark.parametrize(
    ('area', 'back'),
    [(86, 'Flayer Jungle'), (87, 'Swampy Pit 1'), (88, 'Flayer Jungle'), (89, 'Flayer Dungeon 1')],
)
def test_dungeons_track_the_stairs_down_and_the_way_back(area, back):
    guidance = guide(area, Room(679, 0, 0, 14, 14), Room(700, 14, 0, 14, 14), Room(697, 28, 0, 14, 14))

    assert rows(guidance) == [
        ('Next level', 'stairs', 'Act 3 - Dungeon Next E'),
        (back, 'previous', 'Act 3 - Dungeon Prev S'),
    ]


def test_sewers_1_marks_the_drain_the_chest_and_every_way_up():
    guidance = guide(
        92,
        Room(719, 0, 0, 12, 12),
        Room(740, 12, 0, 12, 12),  # Drain E
        Room(745, 24, 0, 12, 12),  # Chest S
        Room(735, 36, 0, 12, 12),  # Prev SW
        Room(738, 48, 0, 12, 12),  # Prev NE
    )

    assert rows(guidance) == [
        ('Sewers 2', 'stairs', 'Act 3 - Sewer Drain E'),
        ('Chest', 'target', 'Act 3 - Sewer Chest S'),
        ('Way up', 'previous', 'Act 3 - Sewer Prev SW'),
        ('Way up', 'previous', 'Act 3 - Sewer Prev NE'),
    ]
    assert guidance.problems == ()


def test_new_act3_handlers_stay_unconfirmed():
    assert not any(handler_for(area).confirmed for area in (76, 77, 78, 80, 81, 83, 84, 85, 86, 87, 88, 89, 92))
