"""Routes over recorded levels: the production planner asked hop by hop, held against the fewest hops.

Each fixture is a whole recorded level with a start and a mark (build_fixtures.py says where each is
from). The tests say what is wanted of a route: it arrives, no teleport is spent on a wall, it takes
no more hops than the reference (harness.py), and it is not much longer in units. Where the planner
of today does not, the test is an expected failure with the numbers measured on 2026-10-10: a change
that mends one turns it into an error until its mark is taken off.

    uv run --offline python -m tests.inventory_tracking.scenarios.navigation.benchmark   # the table
"""

from functools import cache

import pytest

from inventory_tracking.levels import model
from inventory_tracking.macros import teleport
from tests.inventory_tracking.macros.fakes import player
from tests.inventory_tracking.scenarios.navigation.harness import (
    Trip,
    field_of,
    footing_of,
    load,
    names,
    run_production,
)


# The fewest hops of each route by the reference planner: a change here is a change of the harness.
REFERENCE = {
    'across-and-back': 10,
    'around-the-void': 16,
    'corner-east': 7,
    'corner-west': 7,
    'dead-end': 11,
    'down-the-screen': 6,
    'down-the-screen-narrow': 6,
    'last-hop-short': 2,
    'recorded-door-1658': 13,
    'recorded-door-1725': 11,
    'recorded-door-1837': 3,
    'recorded-hunt-1848': 6,
    'recorded-hunt-2124': 3,
    'u-detour': 15,
    'unloaded-room': 13,
    'up-the-screen': 4,
}
STUCK = {
    'unloaded-room': 'five hops, then two teleports at the wall of a room whose walls were not read, the same '
    'spot both times: stopped 179 units short of the mark (the reference: 13 hops)',
}
# Routes that take two or more hops over the reference.
# Since the far potential (teleport.FAR_TILES, 2026-10-11): across-and-back 13 -> 11 hops, down-the-screen
# 8 -> 6 (the band without footing 20 units deep is hopped over); recorded-door-1725 12 -> 13.
FAR_OVER = {
    'recorded-door-1725': '13 hops against 11 (11 recorded): the far way finds no landing once, the near takes over',
    'down-the-screen-narrow': '10 hops against 6 in a 4:3 window: the same band, a longer way round',
    **STUCK,
}
# Routes that take one hop over the reference.
ONE_OVER = {
    'across-and-back': '11 hops against 10',
    'around-the-void': '17 hops against 16: hop 11 takes nothing off the count',
    'corner-west': '8 hops against 7: hop 6 takes nothing off the count',
    'last-hop-short': '3 hops against 2: the second lands 8 units short of the mark, the third is 5 units long',
    'recorded-door-1837': '4 hops against 3 (4 recorded): the third lands short of the mark',
    'recorded-hunt-1848': '7 hops against 6 (7 recorded): the first goes 21 units down the screen, 25 are shown',
    'recorded-hunt-2124': '4 hops against 3 (4 recorded): the first takes nothing off the count',
    'up-the-screen': '5 hops against 4: the fourth lands short of the mark',
}
LONGER = {
    'down-the-screen-narrow': '182 units against 132',
    **STUCK,
}
WORSE_THAN_RECORDED = {'recorded-door-1725': '13 hops; the macro made 11 on 2026-10-10 at 17:25'}
STRETCH = 1.15  # a route may be this many times the reference route's length


def routes(failing: dict[str, str], only: str = ''):
    """Every fixture as a test case, the ones in `failing` as expected failures with their numbers."""
    return [
        pytest.param(name, marks=pytest.mark.xfail(strict=True, reason=failing[name])) if name in failing else name
        for name in names()
        if name.startswith(only)
    ]


@cache
def trip(name: str) -> Trip:
    return run_production(load(name))


def test_every_fixture_has_its_reference_count():
    assert sorted(REFERENCE) == names()


@pytest.mark.parametrize('name', names())
def test_the_reference_counts_the_same_hops_as_when_the_route_was_cut(name):
    situation = load(name)
    assert field_of(situation).hops(situation.start) == REFERENCE[name]


@pytest.mark.parametrize('name', routes(STUCK))
def test_the_route_arrives_and_every_teleport_lands_on_footing(name):
    made = trip(name)
    footing = footing_of(made.situation.ground)
    assert made.refused == [], f'{len(made.refused)} teleports aimed at a wall'
    assert made.arrived, f'stopped short: {made.stopped}'
    assert all(footing.has(spot) for spot in made.spots[1:])


@pytest.mark.parametrize('name', routes(FAR_OVER))
def test_the_route_takes_at_most_one_hop_more_than_the_reference(name):
    made = trip(name)
    assert made.arrived
    assert made.presses <= REFERENCE[name] + 1, made.line()


@pytest.mark.parametrize('name', routes(FAR_OVER | ONE_OVER))
def test_the_route_takes_the_fewest_hops(name):
    made = trip(name)
    assert made.arrived
    assert made.presses <= REFERENCE[name], f'{made.line()}; hops that took nothing off the count: {made.lost()}'


@pytest.mark.parametrize('name', routes(LONGER))
def test_the_route_is_not_much_longer_than_the_reference_route(name):
    made = trip(name)
    assert made.arrived
    assert made.distance <= STRETCH * made.reference_distance, made.line()


@pytest.mark.parametrize('name', routes(WORSE_THAN_RECORDED, only='recorded-'))
def test_the_planner_of_today_needs_no_more_hops_than_the_macro_made_on_the_day(name):
    made = trip(name)
    assert made.arrived
    assert made.presses <= made.situation.recorded_hops, made.line()


@pytest.mark.xfail(strict=True, reason='137 hops against 120 over the fifteen routes with every wall read: 14% over')
def test_the_routes_together_take_the_fewest_hops():
    made = [trip(name) for name in names() if name not in STUCK]
    assert all(one.arrived for one in made)
    assert sum(one.presses for one in made) <= sum(REFERENCE[one.situation.name] for one in made)


def test_one_landing_is_chosen_over_one_reading_of_the_ground(monkeypatch):
    # The choice of a landing is part of every hop's time: the level's grids need indexing once for it.
    situation = load('corner-east')
    target = situation.target
    way = teleport.way_for(target, situation.view)
    built = []

    class Counted(model.Ground):
        def __init__(self, grids) -> None:
            built.append(1)
            super().__init__(grids)

    monkeypatch.setattr(teleport, 'Ground', Counted)
    here = player(situation.area, x=situation.start[0], y=situation.start[1])
    assert teleport.landing(target, here, way, situation.window[2] / situation.window[3]) is not None
    assert len(built) <= 1
