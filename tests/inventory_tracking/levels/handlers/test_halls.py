"""Halls of Anguish/Pain: four 40x40 Temple quadrants; the 'Down' quadrant holds the stairs.

Fixtures: Win+C dump 20260930T082324Z-9fecf33f and live evidence 20260930T084120 (Halls of
Death's Calling, 2026-09-30); the user confirmed the direction in game.
"""

import pytest

from inventory_tracking.levels.handlers.halls import HANDLERS
from tests.inventory_tracking.levels.fixtures import replay


@pytest.mark.parametrize('fixture', ['halls_of_pain_nw_down', 'halls_of_pain_live'])
def test_stairs_quadrant_is_one_poi_covering_the_whole_quadrant(fixture):
    [handler] = HANDLERS

    guidance = handler.guide(replay(fixture))

    poi, waypoint = guidance.pois
    assert (poi.label, poi.room.preset, poi.room.block) == ('Next level', 1047, (2040, 2983, 40, 40))
    assert (waypoint.label, waypoint.kind, waypoint.room.width) == ('Waypoint', 'waypoint', 40)
    assert guidance.problems == ()


def test_halls_handler_is_confirmed():
    assert HANDLERS[0].confirmed
