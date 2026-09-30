"""Tower Cellar 1-4: one 'Crypt Next' room per level (evidence 2026-09-30, user: arrows correct)."""

import pytest

from inventory_tracking.levels.handlers.tower_cellar import HANDLERS
from inventory_tracking.levels.registry import handler_for
from tests.inventory_tracking.levels.fixtures import replay


@pytest.mark.parametrize(
    ('fixture', 'name'),
    [
        ('tower_cellar_1', 'Act 1 - Crypt Next W'),
        ('tower_cellar_2', 'Act 1 - Crypt Next N'),
        ('tower_cellar_3', 'Act 1 - Crypt Next N'),
        ('tower_cellar_4', 'Act 1 - Crypt Next N'),
    ],
)
def test_each_level_has_exactly_one_stairs_down(fixture, name):
    from inventory_tracking.levels.presets import preset_name

    snapshot = replay(fixture)
    handler = handler_for(snapshot.location.area_id)

    guidance = handler.guide(snapshot)

    [poi] = guidance.pois
    assert (poi.label, preset_name(poi.room.preset)) == ('Next level', name)
    assert guidance.problems == ()
    assert handler.confirmed


def test_countess_level_stays_unconfirmed():
    assert not next(h for h in HANDLERS if h.name == 'Tower Cellar 5').confirmed
