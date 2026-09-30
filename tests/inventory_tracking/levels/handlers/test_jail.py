"""Barracks → Jail 1-3 → Inner Cloister. Fixture: Win+C dump 20260930T091905Z-6d876f84 (Jail 1).

The user tracks three POIs per Jail level: the next level, the waypoint and the way back.
"""

from inventory_tracking.levels.geometry import pointer
from inventory_tracking.levels.guide import pointer_lines
from inventory_tracking.levels.level_map import build_map
from inventory_tracking.levels.presets import preset_name
from inventory_tracking.levels.registry import handler_for
from tests.inventory_tracking.levels.fixtures import replay


def test_jail_1_tracks_next_level_waypoint_and_barracks():
    snapshot = replay('jail_1')

    guidance = handler_for(29).guide(snapshot)

    assert [(p.label, preset_name(p.room.preset)) for p in guidance.pois] == [
        ('Next level', 'Act 1 - Jail Next N'),
        ('Waypoint', 'Act 1 - Jail Waypoint W'),
        ('Barracks', 'Act 1 - Jail Prev S'),
    ]
    assert guidance.problems == ()


def test_standing_in_the_waypoint_room_says_here_and_keeps_its_dot():
    snapshot = replay('jail_1')  # the dump was taken right after arriving by waypoint
    guidance = handler_for(29).guide(snapshot)

    lines = pointer_lines([pointer(poi, snapshot.location) for poi in guidance.pois])
    card = build_map(snapshot, guidance.pois)

    assert [line.text for line in lines] == ['←  Next level: west', '•  Waypoint: here', '↗  Barracks: north']
    assert [line.arrow for line in lines] == ['←', None, '↗']
    assert [p.label for p in card.pois] == ['Next level', 'Waypoint', 'Barracks']
    assert len(card.route) >= 2  # the route still leads to the next level


def test_deeper_jail_levels_name_where_the_stairs_up_lead():
    assert [s.label for s in handler_for(30).pois] == ['Next level', 'Waypoint', 'Jail 1']
    assert [s.label for s in handler_for(31).pois] == ['Inner Cloister', 'Waypoint', 'Jail 2']


def test_jail_2_and_3_replay_their_real_levels_and_jail_is_confirmed():
    rows = {}
    for fixture in ('jail_2', 'jail_3'):
        snapshot = replay(fixture)
        guidance = handler_for(snapshot.location.area_id).guide(snapshot)
        assert guidance.problems == ()
        rows[fixture] = [(p.label, preset_name(p.room.preset)) for p in guidance.pois]

    assert rows['jail_2'] == [('Next level', 'Act 1 - Jail Next E'), ('Jail 1', 'Act 1 - Jail Prev W')]
    assert rows['jail_3'] == [('Inner Cloister', 'Act 1 - Jail Cath W'), ('Jail 2', 'Act 1 - Jail Prev S')]
    assert all(handler_for(area).confirmed for area in (29, 30, 31))  # user checked all Jail levels 2026-09-30
    assert not handler_for(28).confirmed  # Barracks: no evidence yet
