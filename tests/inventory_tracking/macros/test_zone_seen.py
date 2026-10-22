"""A level run carried across an open passage tours two levels (2026-10-21 16:02:14-16:03:03, session
20261021T120720Z-b130b85f): Barracks' tour ended (52 of 52 rooms), the run walked into the Outer Cloister, whose tour
ended too, and only the Outer Cloister was judged explored (hunt.py `toured` names the last level). Barracks was
entered again 6 times, 6 s and +0 experience each, until zonenav.py WAY_TRIES blocked it. Every level toured to its
end in a run is explored (hunt.py `tours_done`, runner.py `_zone_seen`)."""

import threading
from pathlib import Path
from types import SimpleNamespace

from inventory_tracking.macros.loop import ACT_KINDS
from inventory_tracking.macros.runner import MacroRunner
from tests.inventory_tracking.macros.test_hunt import EAST, HERE, ROOMS
from tests.inventory_tracking.macros.test_tz_leveling import RECT, at_border, bounds


BARRACKS, OUTER_CLOISTER = 28, 27


def test_a_tour_with_no_stop_left_records_its_level_until_read():
    _, hunt, level, player = at_border([bounds(room) for room in ROOMS])
    assert hunt.frontier(level, player, RECT) is None  # every room seen: the tour has no stop
    assert hunt.tours_done == {level.area}
    _, unfinished, other, near = at_border([bounds(room) for room in (HERE, EAST[1])])
    assert unfinished.frontier(other, near, RECT) is not None
    assert unfinished.tours_done == set()  # rooms left: not toured to its end


def test_both_levels_of_a_run_carried_across_a_passage_are_explored():
    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent'))
    try:
        runner.loop.on, runner.loop.kind = True, ACT_KINDS['act1']
        hunter = SimpleNamespace(  # the run's end as the hunter leaves it
            toured=(OUTER_CLOISTER, 35, 35),
            tours_done={BARRACKS, OUTER_CLOISTER},
            ended_area=OUTER_CLOISTER,
            explored=lambda area: True,
        )
        runner.hunter = hunter  # pyrefly: ignore[bad-assignment] the fake hunter
        runner._zone_seen()
        agenda = runner.loop.agenda
        assert {BARRACKS, OUTER_CLOISTER} <= agenda.explored
        assert {BARRACKS, OUTER_CLOISTER} <= agenda.mapped
        assert hunter.tours_done == set()  # read once: the next run's end tells its own
    finally:
        runner.hunter = None
        runner.close()
