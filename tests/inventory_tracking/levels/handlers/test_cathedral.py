"""Inner Cloister → Cathedral → Catacombs 1 (handlers/cathedral.py).

Rooms as the client held them on arrival (combat takes 20261019T172646Z-32 and 20261019T172708Z-33, level.json):
each level is one preset in 8x8 chunks, the Cloister's north row touching the Cathedral, its north-west chunk Jail 3
too; the Cathedral's two south rows touching the Cloister, one chunk Catacombs 1. Arrivals: by the Jail 3 stairs at
(20009.5, 5019.5) (20261017T211217Z-32), by the Catacombs 1 stairs at (20088.5, 4883.5) (20261017T210206Z-33).
"""

import pytest

from inventory_tracking.levels.exits import guide_level, in_rooms, passage_of
from inventory_tracking.levels.guide import place
from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.spots import pinpoint
from inventory_tracking.routes.catalog.act1 import ROUTES
from inventory_tracking.routes.model import ENTER
from tests.inventory_tracking.levels.fixtures import handler_of


def chunks(preset, block, leads_to) -> tuple[Room, ...]:
    x0, y0, width, height = block
    return tuple(
        Room(preset, x, y, min(8, x0 + width - x), min(8, y0 + height - y), 0, block, leads_to(x, y))
        for x in range(x0, x0 + width, 8)
        for y in range(y0, y0 + height, 8)
    )


CLOISTER = chunks(256, (4000, 1000, 18, 20), lambda x, y: ((33, 31) if x == 4000 else (33,)) if y == 1000 else ())
NAVE = chunks(257, (3996, 966, 28, 34), lambda x, y: (32,) if y >= 990 else (34,) if (x, y) == (4012, 974) else ())
FROM_JAIL = Location(32, 0, 20009, 5019)
FROM_CATACOMBS = Location(33, 0, 20088, 4883)


def card(location, rooms):
    """The marks as the level card shows them (levels/guide.py `_present`)."""
    snapshot = LevelSnapshot(location, rooms)
    guidance = guide_level(handler_of(location.area_id), snapshot)
    return guidance, tuple(pinpoint(poi) for poi in guidance.pois)


def test_the_cloister_marks_the_cathedral_doorway_its_waypoint_and_the_jail_stairs():
    guidance, pois = card(FROM_JAIL, CLOISTER)

    assert guidance.problems == ()
    assert [(p.label, p.kind, preset_name(p.room.preset), place(p), p.area) for p in pois] == [
        ('Cathedral', 'stairs', 'Act 1 - Courtyard 2', (4010.5, 1000.5), 33),
        ('Waypoint', 'waypoint', 'Act 1 - Courtyard 2', (4011.0, 1010.0), None),
        ('Jail 3', 'previous', 'Act 1 - Courtyard 2', (4002.5, 1003.5), None),  # the warp the arrival stood by
    ]


def test_the_cathedral_marks_the_catacombs_stairs_and_the_doorway_back():
    guidance, pois = card(FROM_CATACOMBS, NAVE)

    assert guidance.problems == ()
    assert [(p.label, p.kind, preset_name(p.room.preset), place(p), p.area) for p in pois] == [
        ('Catacombs 1', 'stairs', 'Act 1 - Cathedral', (4018.0, 976.5), None),  # the arrival from it: (4017.7, 976.7)
        ('Inner Cloister', 'previous', 'Act 1 - Cathedral', (4010.5, 999.5), 32),
    ]


@pytest.mark.parametrize(
    ('location', 'rooms', 'label', 'beyond', 'far'),
    [
        (FROM_JAIL, CLOISTER, 'Cathedral', NAVE, (4010.5, 998.75)),
        (FROM_CATACOMBS, NAVE, 'Inner Cloister', CLOISTER, (4010.5, 1001.0)),
    ],
)
def test_the_doorway_is_an_open_passage_walked_into_the_other_level(location, rooms, label, beyond, far):
    _, pois = card(location, rooms)
    [poi] = [p for p in pois if p.label == label]

    found = passage_of(location.area_id, rooms, poi, place(poi), ())

    assert found == far
    assert found is not None
    assert in_rooms(beyond, found)
    assert not in_rooms(rooms, found)
    # The walk from the Cathedral crossed at (20052.9, 5000.1) → (20052.5, 5000.5): tile x 4010 (20261017T210235Z-32)
    assert int(found[0]) == 4010


def test_the_stairs_are_not_passages():
    for location, rooms in ((FROM_JAIL, CLOISTER), (FROM_CATACOMBS, NAVE)):
        _, pois = card(location, rooms)
        for poi in pois:
            if poi.label in ('Jail 3', 'Catacombs 1'):
                assert passage_of(location.area_id, rooms, poi, place(poi), ()) is None


def test_the_cards_name_the_marks_the_andariel_route_enters_by():
    [route] = [route for route in ROUTES if route.name == 'Andariel']
    stages = {script.area: script.way_on for script in route.scripts if script.area in (32, 33)}
    named = {
        area: {poi.label for poi in card(location, rooms)[1]}
        for area, location, rooms in ((32, FROM_JAIL, CLOISTER), (33, FROM_CATACOMBS, NAVE))
    }

    assert {area: (stage.kind, stage.mark) for area, stage in stages.items() if stage} == {
        32: (ENTER, 'Cathedral'),
        33: (ENTER, 'Catacombs 1'),
    }
    assert all(stage and stage.mark in named[area] for area, stage in stages.items())


def test_both_levels_are_unconfirmed_until_a_run_crosses_by_these_marks():
    assert handler_of(32).labels() == {'Cathedral', 'Waypoint', 'Jail 3'}
    assert handler_of(33).labels() == {'Catacombs 1', 'Inner Cloister'}
    assert not handler_of(32).confirmed
    assert not handler_of(33).confirmed
