"""What a fight should achieve against monsters that bring the dead back, and what today's does.

`today` is the aim the game's fight runs (harness.py). A scenario's wanted outcome is its `within`,
`raised` and `casts` (scenarios.py). Where today's fight falls short the test is a strict expected
failure with the measured numbers (2026-10-10): it starts passing, and so fails the run, the day the
fight is mended. The prototypes of the proposed changes are run through the same scenarios, so the
count of what each mends is a test too.
"""

from functools import cache

import pytest

from .harness import FIGHTS, Result, meets, run
from .scenarios import BY_NAME, SCENARIOS


# Scenario -> what today's fight does there instead (measured 2026-10-10, 30 s of game time).
TODAY_FALLS_SHORT = {
    'shaman_behind_a_wall': 'never dead: 52 casts in 30 s, 49 raised (68,870 points wasted); wanted dead within 6 s',
    'shaman_in_a_closed_cell': '52 casts in 30 s at a pack that cannot die, 49 raised; wanted at most 12 casts',
    'two_shamans_cover_each_other': 'dead at 3.1 s after 9 casts with 5 raised (7,028 points); wanted at most 2 raised',
    'shaman_out_of_reach': 'never dead: 52 casts in 30 s, 49 raised (68,870 points wasted); wanted dead within 6 s',
    'unraveler_raises_from_out_of_reach': 'never dead: 43 casts in 30 s, 19 raised (67,906 points); wanted dead in 8 s',
    'terror_two_shamans_cover_each_other': 'dead at 3.1 s after 9 casts with 5 raised (10,994 points); wanted 2 raised',
    'tough_unraveler_off_the_line_of_its_skeletons': (
        'never dead: 84 casts in 30 s, 26 raised (464,620 points wasted); wanted dead within 9 s'
    ),
    'tough_two_shamans_cover_each_other': 'dead at 7.4 s after 21 casts with 9 raised (63,248 points); wanted 6 s',
}
# Proposal -> the scenarios of TODAY_FALLS_SHORT it leaves unmended, each proposal on top of the ones before.
STILL_SHORT = {
    'flagged': {
        'shaman_behind_a_wall',
        'shaman_in_a_closed_cell',
        'shaman_out_of_reach',
        'unraveler_raises_from_out_of_reach',
        'tough_two_shamans_cover_each_other',
    },
    'reposition': {'shaman_in_a_closed_cell', 'tough_two_shamans_cover_each_other'},
    'hold': {'tough_two_shamans_cover_each_other'},
    'reference': set(),
}


@cache
def outcome(name: str, fight: str) -> Result:
    return run(BY_NAME[name], FIGHTS[fight]())


def cases():
    for scenario in SCENARIOS:
        reason = TODAY_FALLS_SHORT.get(scenario.name)
        marks = [pytest.mark.xfail(strict=True, reason=reason)] if reason else []
        yield pytest.param(scenario.name, id=scenario.name, marks=marks)


@pytest.mark.parametrize('name', list(cases()))
def test_the_fight_ends_the_pack_without_grinding_what_comes_back(name):
    result = outcome(name, 'today')
    assert meets(BY_NAME[name], result) == [], result.line()


@pytest.mark.parametrize('name', [scenario.name for scenario in SCENARIOS])
def test_the_wanted_outcome_can_be_had(name):
    result = outcome(name, 'reference')
    assert meets(BY_NAME[name], result) == [], result.line()


@pytest.mark.parametrize('fight', list(STILL_SHORT))
def test_what_each_proposal_mends(fight):
    short = {scenario.name for scenario in SCENARIOS if meets(scenario, outcome(scenario.name, fight))}
    assert short == STILL_SHORT[fight]


def test_no_proposal_is_slower_than_today_where_today_is_good_enough():
    for scenario in SCENARIOS:
        before = outcome(scenario.name, 'today')
        if scenario.name in TODAY_FALLS_SHORT or before.seconds is None:
            continue
        after = outcome(scenario.name, 'reference')
        assert after.seconds is not None
        assert after.seconds <= before.seconds + 0.5, scenario.name
        assert after.revivals <= before.revivals, scenario.name


def test_the_reviver_out_of_reach_is_the_fight_that_never_ends():
    # The measure behind the first proposals: with the reviver past the blades or behind a wall, every
    # cast of the 30 s goes into monsters that stand up again.
    for name in ('shaman_out_of_reach', 'shaman_behind_a_wall', 'unraveler_raises_from_out_of_reach'):
        before, after = outcome(name, 'today'), outcome(name, 'reference')
        assert not before.cleared
        assert before.revivals > 15
        assert before.wasted > 0.8 * before.taken
        assert after.cleared
        assert after.moves == 1
        assert after.casts < before.casts / 4
