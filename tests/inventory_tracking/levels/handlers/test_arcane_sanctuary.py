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
