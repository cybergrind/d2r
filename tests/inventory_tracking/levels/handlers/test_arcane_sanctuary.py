"""Arcane Sanctuary replayed on two real games (Win+C dumps, 2026-09-30)."""

import pytest

from inventory_tracking.levels.geometry import pointer
from inventory_tracking.levels.handlers.arcane_sanctuary import HANDLERS
from tests.inventory_tracking.levels.fixtures import replay


@pytest.mark.parametrize(
    ('fixture', 'preset', 'arrow', 'compass'),
    [
        ('arcane_summoner_s', 527, '↗', 'north'),  # game 1: the Summoner was found there in game
        ('arcane_summoner_w', 525, '↘', 'east'),  # game 2: a fixed 527 missed it
    ],
)
def test_summoner_is_found_in_every_orientation(fixture, preset, arrow, compass):
    [handler] = HANDLERS
    snapshot = replay(fixture)

    guidance = handler.guide(snapshot)

    [poi] = guidance.pois
    assert (poi.label, poi.room.preset) == ('Summoner', preset)
    found = pointer(poi, snapshot.location)
    assert (found.arrow, found.compass) == (arrow, compass)
    assert handler.confirmed


def test_the_mark_is_a_stand_beside_the_summoner_not_the_rooms_middle():
    # 15:43 on 2026-10-11: the step stopped 11 from the room's middle, and he stood at
    # (25440.7, 5020.9), 25 from the character with the blades reaching 22. Same room as the fixture.
    # Then (user): not on the boss and his group, slightly offset: the landing below the two ramps,
    # 10 east and 15 south of his spot, 18 units from him.
    [handler] = HANDLERS
    [poi] = handler.guide(replay('arcane_summoner_s')).pois
    assert poi.room.center == (25440 + 10, 5020 + 15)
    [poi] = handler.guide(replay('arcane_summoner_w')).pois
    assert poi.room.center == (5168 * 5 + 35 + 10, 1084 * 5 + 20 + 15)
