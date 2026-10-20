"""The route's way on as the runner judges it (macros/running/execution.py `at_the_way_on`)."""

import threading
from pathlib import Path

from inventory_tracking.levels.model import Target
from inventory_tracking.macros.route import PERFORMED
from inventory_tracking.macros.runner import MacroRunner
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.progress import Progress
from tests.inventory_tracking.macros.fakes import player


CANYON = 46


def test_a_tour_mark_beside_the_character_is_the_way_on_and_a_far_one_is_not():
    # The Canyon's tombs (2026-10-20): the TZ loop's way on from the Canyon goes through the entrance its run ended at;
    # with only a stage's `to` counted, a tour's mark (no `to`) was never one and the way on ran the level again
    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent/Saved Games'))
    runner.progress = Progress(ROUTES, PERFORMED)
    runner.progress.note('g', CANYON)
    here = player(CANYON, x=5000.0, y=5000.0)
    tomb = Target(CANYON, (), (5003.0 / TILE_UNITS, 5000.0 / TILE_UNITS), 'Tomb', 'stairs', True)
    runner.target = lambda: tomb
    assert runner.at_the_way_on(here)
    far = Target(CANYON, (), (5300.0 / TILE_UNITS, 5000.0 / TILE_UNITS), 'Tomb', 'stairs', True)
    runner.target = lambda: far
    assert not runner.at_the_way_on(here)
    waypoint = Target(CANYON, (), tomb.point, 'Waypoint', 'waypoint')
    runner.target = lambda: waypoint
    assert not runner.at_the_way_on(here)  # not the tour's mark
