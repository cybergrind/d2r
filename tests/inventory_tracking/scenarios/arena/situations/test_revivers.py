"""The packs whose revivers raise them (revivers.py) played off and on (combat/revivers.py REVIVERS_FIRST with
macros/hunting/revive.py REVIVER_STAND, 2026-10-23): no death either way, and both on clear the level run's packs no
later where a reviver stands behind them. The 20-seed table is the module's command line (the switches' comments)."""

import pytest

from tests.inventory_tracking.scenarios.arena.situations.revivers import SITUATIONS, compare


SEEDS = (1, 2, 3)


@pytest.mark.slow
@pytest.mark.parametrize('name', list(SITUATIONS))
def test_no_death_off_or_on(name):
    off, on = compare(SITUATIONS[name], SEEDS)
    assert off.deaths == 0, off.row()
    assert on.deaths == 0, on.row()


@pytest.mark.parametrize('name', ['run: unraveler', 'run: fallen herald, shamans 5 behind'])
def test_a_run_clears_a_pack_raised_from_behind_no_later_with_the_revivers_first(name):
    off, on = compare(SITUATIONS[name], SEEDS)
    assert on.cleared >= off.cleared, (off.row(), on.row())
    assert on.lasting_minute >= off.lasting_minute, (off.row(), on.row())
