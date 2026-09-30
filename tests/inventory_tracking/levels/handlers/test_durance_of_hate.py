"""Durance of Hate 2: stairs down (evidence 2026-09-30, user: direction correct)."""

from inventory_tracking.levels.handlers.durance_of_hate import HANDLERS
from inventory_tracking.levels.presets import preset_name
from tests.inventory_tracking.levels.fixtures import replay


def test_stairs_down_and_the_waypoint_the_player_stands_in():
    [handler] = HANDLERS

    guidance = handler.guide(replay('durance_of_hate_2'))  # arrived by waypoint

    assert [(p.label, preset_name(p.room.preset)) for p in guidance.pois] == [
        ('Next level', 'Act 3 - Mephisto Next E'),
        ('Waypoint', 'Act 3 - Mephisto Waypoint N'),
    ]
    assert guidance.problems == ()
    assert handler.confirmed
