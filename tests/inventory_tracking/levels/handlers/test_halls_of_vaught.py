"""Halls of Vaught: the whole level is one 84x84 preset in four DS1 variants (NihlE/N/S/W).

Fixture: Win+C dump 20260930T082410Z-54658110 (variant 3 = NihlW; entry at the level centre).
The letter names Nihlathak's side (map axes, north = -y): the user saw him west and north in
two games on 2026-09-30, and the NihlW game rules out "the side the layout opens to" (east).
"""

from inventory_tracking.levels.geometry import pointer
from inventory_tracking.levels.handlers.halls_of_vaught import HANDLERS
from inventory_tracking.levels.model import LevelSnapshot, Room
from tests.inventory_tracking.levels.fixtures import handler_of, replay


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


def test_the_marker_is_a_stand_beside_nihlathaks_pavilion_and_walking_up_to_him_keeps_the_arrow():
    # Game 3 (fixture halls_of_vaught_nihle, variant 0 = NihlE): Win+C dump 20260930T144010Z-ca3068d4
    # saw Nihlathak at (12894, 5205), 94% across the 84x84 preset. With the generic 15% inset the
    # marker sat 40 units short of him, and the Win+C next to him pointed back "west".
    from inventory_tracking.levels.geometry import pointer
    from inventory_tracking.levels.model import Location
    from tests.inventory_tracking.levels.fixtures import replay

    snapshot = replay('halls_of_vaught_nihle')
    [poi] = handler_of(124).guide(snapshot).pois
    cx, cy = poi.room.center

    # user, 2026-10-11: the last jump lands off the main pack. The mark is 3 tiles east and 1 north of
    # the side's spot (12895, 5210): east of the pavilion he stands in, 15.5 units from him here.
    assert (cx, cy) == (12910, 5205)
    assert pointer(poi, snapshot.location).compass == 'east'
    assert pointer(poi, Location(124, 0, 12877, 5216)).compass == 'east'


def test_the_stand_is_the_same_way_from_the_spot_in_every_layout():
    # The pavilion lies the same way round in all four layouts (takes of 2026-10-11), so the stand does too.
    [handler] = HANDLERS
    snapshot = replay('halls_of_vaught_nihlw')
    block = next(r.block for r in snapshot.rooms if r.block)
    centre = ((block[0] + block[2] / 2) * 5, (block[1] + block[3] / 2) * 5)
    stands = []
    for variant in range(4):
        rooms = tuple(Room(r.preset, r.x, r.y, r.width, r.height, variant, r.block) for r in snapshot.rooms)
        [poi] = handler.guide(LevelSnapshot(snapshot.location, rooms)).pois
        stands.append((poi.room.center[0] - centre[0], poi.room.center[1] - centre[1]))
    assert stands == [(200, -5), (15, -190), (15, 180), (-170, -5)]
