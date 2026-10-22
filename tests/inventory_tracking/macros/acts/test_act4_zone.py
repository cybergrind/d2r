"""Act 4 played by zone navigation (macros/zonenav.py): the River of Flame crossed to the Chaos Sanctuary and walked
back up across the same open passage (zonenav.py `allowed`: a run may cross into its graph parent and children)."""

import pytest

from inventory_tracking.macros import zonenav
from inventory_tracking.macros.loop import LEAVE, TZ_UP
from tests.inventory_tracking.macros.acts.harness import ActGame, crossing


KILLS = {'Grand Vizier of Chaos', 'Lord De Seis', 'Infector of Souls', 'Diablo', 'Izual', 'Andariel'}


@pytest.fixture
def zone(monkeypatch):
    monkeypatch.setattr(zonenav, 'ACTS', frozenset((4,)))


@pytest.mark.usefixtures('zone')
def test_the_river_is_walked_into_the_sanctuary_and_back_up_across_its_open_passage(monkeypatch):
    walk = crossing(ActGame(4, monkeypatch)).play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.legs[-1] == LEAVE
    assert set(walk.kills) == KILLS
    assert walk.moves[:3] == [('waypoint', 107), ('walk', 108), ('walk', 107)]  # Diablo, then the River's own run
    assert TZ_UP in walk.legs
    # was [107, 107, 106, 35]; the rotation's Andariel right after Diablo (zonenav.py ROTATION_BOSSES_FIRST), then the
    # Cathedral's trip (tzroutine.py SKIPPED_TRIPS)
    assert walk.waypoints == [107, 35, 32, 106]


def test_with_the_switch_off_act_4_goes_back_to_the_river_by_its_waypoint(monkeypatch):
    walk = crossing(ActGame(4, monkeypatch)).play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.waypoints == [107, 107, 106, 35, 32]
