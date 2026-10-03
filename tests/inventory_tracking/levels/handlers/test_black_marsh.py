"""Black Marsh: the Forgotten Tower entrance and the exits. Fixture black_marsh (evidence 2026-09-30); the user
confirmed the direction. Outdoor room lists hold 8x8 chunks named 'Wild Border N', feature presets
and 'preset 0' (generated terrain)."""

from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for
from tests.inventory_tracking.levels.fixtures import replay


def test_tower_entrance_is_found_in_the_outdoor_room_list():
    snapshot = replay('black_marsh')
    handler = handler_for(6)

    guidance = handler.guide(snapshot)

    assert [(p.label, preset_name(p.room.preset)) for p in guidance.pois] == [
        ('Exit', 'Act 1 - Wild Border 2'),  # two gaps; the fixture predates Room.leads_to
        ('Exit', 'Act 1 - Wild Border 3'),
        ('Forgotten Tower', 'Act 1 - Tower 1'),
    ]
    assert guidance.problems == ()
    assert handler.confirmed


def test_black_marsh_names_its_gaps_once_they_are_seen():
    rooms = (
        Room(4, 0, 0, 8, 8, 3, (0, 0, 8, 8), (5,)),  # seen from the Dark Wood side
        Room(6, 80, 0, 8, 8, 3),  # Tamoe Highland by elimination
        Room(163, 40, 40, 8, 8),
    )
    guidance = handler_for(6).guide(LevelSnapshot(Location(6, 0, 4, 4), rooms))

    assert [(p.label, p.kind) for p in guidance.pois] == [
        ('Tamoe Highland', 'stairs'),
        ('Dark Wood', 'previous'),
        ('Forgotten Tower', 'stairs'),
    ]
    assert guidance.problems == ()
