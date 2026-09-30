"""Rocky Waste → Stony Tomb 1 → Stony Tomb 2 (D2MOO DrlgOutDesr/DrlgMaze; no evidence yet).

Rocky Waste's only exit preset is 'Desert Tomb 1'. Stony Tomb 1 places 'Tomb Next'; Stony
Tomb 2 places the Treasure room (super chest), the Leatherarm room (Creeping Feature) and a Chest
room. Both start in a 'Tomb Prev' room (the way back).
"""

from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for


def test_rocky_waste_points_at_the_tomb_entrance():
    rooms = (Room(0, 0, 0, 8, 8), Room(364, 8, 0, 8, 8), Room(388, 40, 16, 8, 8))
    guidance = handler_for(41).guide(LevelSnapshot(Location(41, 0, 20, 20), rooms))

    assert [(p.label, preset_name(p.room.preset)) for p in guidance.pois] == [('Stony Tomb', 'Act 2 - Desert Tomb 1')]
    assert guidance.problems == ()


def test_stony_tomb_1_tracks_the_stairs_down_and_the_way_back():
    rooms = (Room(444, 0, 0, 16, 16), Room(416, 16, 0, 16, 16), Room(449, 32, 0, 16, 16))
    guidance = handler_for(55).guide(LevelSnapshot(Location(55, 0, 40, 40), rooms))

    assert [(p.label, preset_name(p.room.preset)) for p in guidance.pois] == [
        ('Next level', 'Act 2 - Tomb Next E'),
        ('Rocky Waste', 'Act 2 - Tomb Prev SEW'),
    ]
    assert guidance.problems == ()


def test_stony_tomb_2_tracks_the_super_chest_creeping_feature_and_the_way_back():
    rooms = (
        Room(445, 0, 0, 16, 16),
        Room(453, 16, 0, 16, 16),
        Room(466, 32, 0, 16, 16),
        Room(475, 48, 0, 16, 16),
    )
    guidance = handler_for(59).guide(LevelSnapshot(Location(59, 0, 40, 40), rooms))

    assert [(p.label, preset_name(p.room.preset)) for p in guidance.pois] == [
        ('Treasure', 'Act 2 - Tomb Treasure E'),
        ('Creeping Feature', 'Act 2 - Tomb Leatherarm S'),
        ('Stony Tomb 1', 'Act 2 - Tomb Prev NEW'),
    ]
    assert guidance.problems == ()


def test_handlers_stay_unconfirmed_without_evidence():
    assert not any(handler_for(area).confirmed for area in (41, 55, 59))
