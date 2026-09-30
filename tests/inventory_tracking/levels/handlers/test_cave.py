"""Cold Plains → Cave 1 → Cave 2 (D2MOO DrlgMaze: every Act 1 cave places 'Cave Prev' and 'Cave
Down'; Cave 1 also places 'Cave Coldcrow'). Cave 2 is one fixed preset ('Cave Treasure 2',
DrlgType 2): no handler. No evidence yet.
"""

from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for


def test_cave_1_tracks_the_stairs_down_coldcrow_and_the_way_back():
    rooms = (Room(84, 0, 0, 24, 24), Room(55, 24, 0, 24, 24), Room(101, 48, 0, 24, 24), Room(94, 72, 0, 24, 24))
    guidance = handler_for(9).guide(LevelSnapshot(Location(9, 0, 60, 60), rooms))

    assert [(p.label, p.kind, preset_name(p.room.preset)) for p in guidance.pois] == [
        ('Next level', 'stairs', 'Act 1 - Cave Down N'),
        ('Coldcrow', 'target', 'Act 1 - Cave Coldcrow S'),
        ('Cold Plains', 'previous', 'Act 1 - Cave Prev E'),
    ]
    assert guidance.problems == ()


def test_real_cave_1_replays_and_is_confirmed():
    # Evidence 20260930T142203 (fixture cave_1); the user walked the whole level, 2026-09-30.
    from tests.inventory_tracking.levels.fixtures import replay

    guidance = handler_for(9).guide(replay('cave_1'))

    assert [p.label for p in guidance.pois] == ['Next level', 'Coldcrow', 'Cold Plains']
    assert guidance.problems == ()
    assert handler_for(9).confirmed


def test_cave_2_has_no_handler():
    assert handler_for(13) is None
