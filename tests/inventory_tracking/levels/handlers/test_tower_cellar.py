"""Tower Cellar 1-4: one 'Crypt Next' room per level (evidence 2026-09-30, user: arrows correct).
Tower Cellar 5: the Countess where each layout's DS1 file places her (evidence 2026-10-10)."""

import pytest

from inventory_tracking.levels.exits import guide_level
from inventory_tracking.levels.handlers.tower_cellar import HANDLERS
from inventory_tracking.levels.model import LevelSnapshot, Room
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


@pytest.mark.parametrize(
    ('fixture', 'spot'),
    [
        ('tower_cellar_5_a', (12520, 11070)),  # variant 0: the file's (21, 70), to the nearest tile
        ('tower_cellar_5_b', (12565, 11015)),  # variant 1: (65, 15)
    ],
)
def test_level_5_leads_to_the_countess_before_the_way_back(fixture, spot):
    snapshot = replay(fixture)

    guidance = guide_level(handler_for(snapshot.location.area_id), snapshot)

    assert [(poi.label, poi.kind) for poi in guidance.pois] == [('Countess', 'target'), ('Tower Cellar 4', 'previous')]
    assert guidance.pois[0].point == spot
    assert guidance.problems == ()


def test_level_5_with_an_unread_layout_reports_it():
    snapshot = replay('tower_cellar_5_a')
    rooms = tuple(Room(r.preset, r.x, r.y, r.width, r.height, None, r.block) for r in snapshot.rooms)

    guidance = handler_for(25).guide(LevelSnapshot(snapshot.location, rooms))

    assert guidance.pois == ()
    assert guidance.problems == ('Countess: The Countess is not in the layout (variant None)',)
