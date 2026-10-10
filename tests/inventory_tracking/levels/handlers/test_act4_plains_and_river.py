"""Plains of Despair (Izual) and River of Flame (Hephasto at the Hellforge); no evidence yet.

From D2MOO (2026-10-01): the Plains spawn one 'Act 4 - Mesa 2 Izual' preset (DrlgOutdoors) and
link to Outer Steppes and City of the Damned through open 'Mesa Border 1-4' gaps (file 3).
River of Flame (DRLGMAZE_PlaceAct4Lava) is a Lava maze with 'Lava Warp N' (up to City of the
Damned), 'Bridge 1' toward the Chaos Sanctum and one 'Lava Forge W/E' (the Hellforge).
"""

from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for


def rows(guidance):
    return [(p.label, p.kind, preset_name(p.room.preset)) for p in guidance.pois]


def test_plains_mark_izual_and_both_gaps():
    rooms = (
        Room(0, 8, 8, 8, 8),
        Room(799, 0, 8, 8, 8, variant=3, leads_to=(104,)),
        Room(800, 40, 0, 8, 8, variant=3),  # unread: the city by elimination
        Room(801, 16, 0, 8, 8, variant=1),  # closed border
        Room(822, 24, 24, 8, 8),
    )
    guidance = handler_for(105).guide(LevelSnapshot(Location(105, 0, 60, 60), rooms))

    assert rows(guidance) == [
        ('City of the Damned', 'stairs', 'Act 4 - Mesa Border 2'),
        ('Outer Steppes', 'previous', 'Act 4 - Mesa Border 1'),
        ('Izual', 'target', 'Act 4 - Mesa 2 Izual'),
    ]
    assert guidance.problems == ()


def test_plains_without_the_izual_preset_report_it():
    guidance = handler_for(105).guide(LevelSnapshot(Location(105, 0, 60, 60), (Room(0, 8, 8, 8, 8),)))

    assert guidance.problems == ('Izual: no room matches',)


def test_river_of_flame_marks_hephasto_the_sanctum_and_the_way_back():
    rooms = (
        Room(836, 0, 0, 24, 24),  # Lava X
        Room(853, 24, 0, 24, 24),  # Forge W
        Room(855, 48, 0, 24, 24),  # Bridge 1
        Room(856, 72, 0, 24, 24),  # Bridge 2 (twice in the game)
        Room(852, 96, 0, 24, 24),  # Warp N
    )
    guidance = handler_for(107).guide(LevelSnapshot(Location(107, 0, 40, 40), rooms))

    assert rows(guidance) == [
        ('Chaos Sanctum', 'stairs', 'Act 4 - Bridge 2'),  # first: KP_4 points at it
        ('Hephasto', 'target', 'Act 4 - Lava Forge W'),
        ('City of the Damned', 'previous', 'Act 4 - Lava Warp N'),
    ]
    assert guidance.pois[0].spot == (96.5, 12.0)  # beyond the far (east) edge of the bridge laid out eastward
    assert guidance.pois[0].area == 108
    assert guidance.problems == ()
    assert not any(handler_for(area).confirmed for area in (105, 107))


def test_the_chaos_sanctum_mark_is_beyond_the_north_end_of_the_bridge_as_in_the_game():
    # The 2026-10-09 evidence: Bridge 1 at row 1168, Bridge 2 at 1144 and 1120 (chunks of 24x24 presets),
    # the player entered the Sanctum at row 1111.
    def chunks(preset, bx, by):
        return [Room(preset, bx + 8 * i, by + 8 * j, 8, 8, 0, (bx, by, 24, 24)) for i in range(3) for j in range(3)]

    rooms = (
        *chunks(855, 1548, 1168),
        *chunks(856, 1548, 1144),
        *chunks(856, 1548, 1120),
        Room(853, 1500, 1200, 24, 24),
    )
    guidance = handler_for(107).guide(LevelSnapshot(Location(107, 0, 7800, 5900), rooms))

    chaos = guidance.pois[0]
    assert (chaos.label, chaos.kind, chaos.spot) == ('Chaos Sanctum', 'stairs', (1560.0, 1119.5))
    assert (chaos.room.x, chaos.room.y, chaos.room.width, chaos.room.height) == (1548, 1120, 24, 24)


def test_without_the_bridge_the_river_still_marks_hephasto_and_says_so():
    rooms = (Room(836, 0, 0, 24, 24), Room(853, 24, 0, 24, 24), Room(852, 96, 0, 24, 24))
    guidance = handler_for(107).guide(LevelSnapshot(Location(107, 0, 40, 40), rooms))

    assert rows(guidance)[0] == ('Hephasto', 'target', 'Act 4 - Lava Forge W')
    assert guidance.problems == ('Chaos Sanctum: no bridge found',)
