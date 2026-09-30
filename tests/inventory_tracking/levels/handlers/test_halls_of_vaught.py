"""Halls of Vaught: the whole level is one 84x84 preset in four DS1 variants (NihlE/N/S/W).

Fixture: Win+C dump 20260930T082410Z-54658110 (variant 3 = NihlW; entry at the level centre).
The letter names Nihlathak's side (map axes, north = -y): the user saw him west and north in
two games on 2026-09-30, and the NihlW game rules out "the side the layout opens to" (east).
"""

from inventory_tracking.levels.geometry import pointer
from inventory_tracking.levels.handlers.halls_of_vaught import HANDLERS
from inventory_tracking.levels.model import LevelSnapshot, Room
from inventory_tracking.levels.registry import handler_for
from tests.inventory_tracking.levels.fixtures import replay


def test_nihlw_points_at_the_west_side_of_the_level():
    [handler] = HANDLERS
    snapshot = replay('halls_of_vaught_nihlw')

    [poi] = handler.guide(snapshot).pois

    found = pointer(poi, snapshot.location)
    assert poi.label == 'Nihlathak'
    assert found.compass == 'west'
    assert found.arrow == '↖'
    assert handler.confirmed


def test_each_variant_points_at_its_own_side():
    [handler] = HANDLERS
    snapshot = replay('halls_of_vaught_nihlw')
    compasses = []
    for variant in range(4):
        rooms = tuple(Room(r.preset, r.x, r.y, r.width, r.height, variant, r.block) for r in snapshot.rooms)
        [poi] = handler.guide(LevelSnapshot(snapshot.location, rooms)).pois
        compasses.append(pointer(poi, snapshot.location).compass)

    assert compasses == ['east', 'north', 'south', 'west']  # lvlprest File1..4: NihlE, NihlN, NihlS, NihlW


def test_unknown_variant_is_a_problem():
    [handler] = HANDLERS
    snapshot = replay('halls_of_vaught_nihlw')
    rooms = tuple(Room(r.preset, r.x, r.y, r.width, r.height, None, r.block) for r in snapshot.rooms)

    guidance = handler.guide(LevelSnapshot(snapshot.location, rooms))

    assert guidance.pois == ()
    assert guidance.problems == ('Nihlathak: layout variant unknown',)


def test_the_marker_is_where_nihlathak_stands_so_walking_up_to_him_keeps_the_arrow():
    # Game 3 (fixture halls_of_vaught_nihle, variant 0 = NihlE): Win+C dump 20260930T144010Z-ca3068d4
    # saw Nihlathak at (12894, 5205), 94% across the 84x84 preset. With the generic 15% inset the
    # marker sat 40 units short of him, and the Win+C next to him pointed back "west".
    from inventory_tracking.levels.geometry import pointer
    from inventory_tracking.levels.model import Location
    from tests.inventory_tracking.levels.fixtures import replay

    snapshot = replay('halls_of_vaught_nihle')
    [poi] = handler_for(124).guide(snapshot).pois
    cx, cy = poi.room.center

    assert abs(cx - 12894) <= 5
    assert abs(cy - 5205) <= 25
    assert pointer(poi, snapshot.location).compass == 'east'
    assert pointer(poi, Location(124, 0, 12877, 5216)).compass == 'east'
