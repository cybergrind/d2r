"""The step (combat/stance.py `camp`) in the revivers' situations: asked at every decision, which is
harder on it than the game will be (there it is asked per press of the pickup request), and with the
harness's move of MOVE_FRAMES whatever the distance. What it must show: the fights today's aim never
ends are ended by a step, and no fight today's aim ends well is made slower by one.

Measured 2026-10-11 over the 17 scenarios: 12 met, none slower, one move in each of the three mended
(today's aim meets 9). The first rule (2026-10-10, a line worth STEP_GAIN times the line from here)
met 10 at 1.3 with three fights made slower, 11 at 1.5, 12 at 2.0.
"""

from functools import cache

import pytest

from inventory_tracking.combat.policy import LinePolicy
from inventory_tracking.combat.stance import camp

from ..revivers.harness import FIGHTS, Brief, Fight, Move, Result, meets, run, today
from ..revivers.scenarios import BY_NAME, SCENARIOS
from ..revivers.test_scenarios import TODAY_FALLS_SHORT


# What a step alone does not mend: a reviver no spot has a shot at, two that raise each other (the
# line through both is not the richest line), and a pack with five times the life the tables give.
STILL_SHORT = {
    'shaman_in_a_closed_cell',
    'two_shamans_cover_each_other',
    'terror_two_shamans_cover_each_other',
    'tough_unraveler_off_the_line_of_its_skeletons',
    'tough_two_shamans_cover_each_other',
}


def stepping() -> Fight:
    aim, policy = today(), LinePolicy(yields=True)

    def fight(brief: Brief):
        spots = brief.spots
        barred = None if spots is None else (lambda point: not spots(point))
        found = camp(brief.seen, policy, barred)
        return Move(found.spot) if found is not None else aim(brief)

    return fight


@cache
def outcome(name: str, fight: str) -> Result:
    return run(BY_NAME[name], stepping() if fight == 'stand' else FIGHTS[fight]())


def test_the_step_mends_the_reviver_out_of_reach_and_the_one_behind_a_wall():
    mended = {s.name for s in SCENARIOS if s.name in TODAY_FALLS_SHORT and not meets(s, outcome(s.name, 'stand'))}
    assert mended == set(TODAY_FALLS_SHORT) - STILL_SHORT
    assert {'shaman_behind_a_wall', 'shaman_out_of_reach', 'unraveler_raises_from_out_of_reach'} <= mended
    for name in mended:
        assert outcome(name, 'stand').moves == 1


@pytest.mark.parametrize('name', [s.name for s in SCENARIOS])
def test_no_fight_is_slower_or_raises_more_for_the_step(name):
    before, after = outcome(name, 'today'), outcome(name, 'stand')
    if before.seconds is not None:
        assert after.seconds is not None
        assert after.seconds <= before.seconds + 0.5
    assert after.revivals <= before.revivals


def test_a_fight_today_ends_well_is_not_stepped_in():
    for scenario in SCENARIOS:
        if scenario.name not in TODAY_FALLS_SHORT:
            assert outcome(scenario.name, 'stand').moves == 0, scenario.name
