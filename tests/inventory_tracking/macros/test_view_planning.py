"""The potential and the landing under one window's shape: the hops planned are the hops the window shows.

The open room is 40 x 40 tiles with no ground grids, so every tile is landable (the room's rectangle
counts). The mark sits in the middle, on tile (20, 20). A tile is (x, y); a point is tiles too.
"""

import math
from dataclasses import replace
from itertools import pairwise

import pytest

from inventory_tracking.levels.model import Room, Target
from inventory_tracking.macros.teleport import Way, landing, way_for
from inventory_tracking.macros.view import Viewport
from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.macros.fakes import player


ASPECTS = (4 / 3, 16 / 9, 2560 / 1418, 21 / 9)
OPEN = Room(1, 0, 0, 40, 40)
MARK = (20.5, 20.5)  # the middle of tile (20, 20)


def open_target(point=MARK):
    return Target(109, (OPEN,), point, 'Next level', 'stairs')


def on_tile(tile, **changes):
    """A player standing at the centre of `tile`, in world units."""
    return player(x=(tile[0] + 0.5) * TILE_UNITS, y=(tile[1] + 0.5) * TILE_UNITS, **changes)


@pytest.mark.parametrize('aspect', ASPECTS)
def test_the_potential_keeps_its_window_and_the_mark_costs_nothing(aspect):
    # The potential must be planned for the window the landing is chosen under, and the mark is the goal.
    view = Viewport(aspect)
    way = Way(open_target(), view)
    assert way.view == view
    assert way.cost[(20, 20)] == 0.0


@pytest.mark.parametrize('aspect', ASPECTS)
def test_every_planned_hop_is_one_the_window_shows(aspect):
    # Each tile's way must step to a closer tile by a hop the window shows, else a teleport cannot make it.
    view = Viewport(aspect)
    way = Way(open_target(), view)
    for tile, cost in way.cost.items():
        if cost == 0 or not math.isfinite(cost):
            continue
        assert any(
            way.cost.get((tile[0] + dx, tile[1] + dy), math.inf) < cost and view.hop_in_view(dx, dy)
            for dx in range(-5, 6)
            for dy in range(-5, 6)
        ), f'tile {tile} at {cost:.2f} has no closer tile reached by a hop the window shows'


def test_a_narrow_window_needs_more_hops_sideways():
    # The screen's horizontal axis is world (+1, -1): a narrow window reaches less of it per hop.
    target = open_target()
    narrow, wide = Way(target, Viewport(4 / 3)), Way(target, Viewport(21 / 9))
    assert narrow.cost[(30, 10)] >= wide.cost[(30, 10)]
    assert any(narrow.cost[tile] > wide.cost[tile] for tile in narrow.cost if tile in wide.cost)


def test_the_reach_straight_up_the_screen_does_not_depend_on_the_aspect():
    # The screen's vertical axis is world (-1, -1): the window's width does not change how far it reaches.
    target = open_target()
    narrow, wide = Way(target, Viewport(4 / 3)), Way(target, Viewport(21 / 9))
    assert narrow.cost[(12, 12)] == pytest.approx(wide.cost[(12, 12)])


def test_way_for_keeps_one_potential_per_window():
    # Presses reuse the potential of their window, and a different window gets its own.
    way_for.cache_clear()
    target = open_target()
    assert way_for(target, Viewport(16 / 9)) is way_for(target, Viewport(16 / 9))
    assert way_for(target, Viewport(4 / 3)) is not way_for(target, Viewport(16 / 9))
    assert way_for(target, Viewport(4 / 3)).view != way_for(target, Viewport(16 / 9)).view


@pytest.mark.parametrize('aspect', ASPECTS)
def test_every_landing_is_in_view_and_gains_way_under_the_same_window(aspect):
    # The landing is chosen under the window the potential was planned for: it must be drawn in view.
    view = Viewport(aspect)
    target = open_target()
    way = Way(target, view)
    for tile in ((5, 5), (33, 8), (36, 34), (8, 31), (4, 20)):
        here = on_tile(tile)
        found = landing(target, here, way, aspect)
        assert found is not None, f'no landing from {tile} under aspect {aspect:.3f}'
        spot, gain = found
        assert gain > 0
        ground = view.ground((here.x, here.y), spot[0] * TILE_UNITS, spot[1] * TILE_UNITS)
        assert view.in_view(ground), f'landing {spot} from {tile} is drawn outside the view'


@pytest.mark.parametrize('aspect', ASPECTS)
def test_repeated_landings_reach_the_mark_under_each_window(aspect):
    # Teleport steps in a row must bring the character to the mark: each one must gain way.
    view = Viewport(aspect)
    target = open_target()
    way = Way(target, view)
    here = on_tile((10, 10))  # about 14 tiles from the mark
    history = [way.from_here((here.x / TILE_UNITS, here.y / TILE_UNITS))]
    for _ in range(12):
        found = landing(target, here, way, aspect)
        if found is None:
            break
        spot, _ = found
        here = replace(here, x=spot[0] * TILE_UNITS, y=spot[1] * TILE_UNITS)
        history.append(way.from_here((here.x / TILE_UNITS, here.y / TILE_UNITS)))
        if history[-1] < 1.5:
            break
    assert history[-1] < 6
    assert all(later <= earlier for earlier, later in pairwise(history))


# --- the far potential: a band of no footing five tiles wide (Far Oasis's cliffs, 2026-10-11) ---


def cliff_target(mark):
    """Two plateaus of 8 x 8 tiles each side of a cliff 5 tiles wide with no footing, one room over all."""
    from inventory_tracking.levels.model import Walkable, pack_cells

    row = '1' * 40 + '0' * 25 + '1' * 40  # sub-tiles: 8 tiles of ground, 5 of cliff, 8 of ground
    cells = pack_cells(row * 40)
    room = Room(1, 1000, 1000, 21, 8)
    return Target(43, (room,), mark, 'mark', 'mark', False, (Walkable(1000, 1000, 21, 8, cells, cells),))


def test_the_far_way_hops_a_cliff_five_tiles_wide_up_the_screen_and_the_near_way_cannot():
    view = Viewport(2560 / 1418)
    west = cliff_target((1004.5, 1004.5))  # the mark on the west plateau: the hop over goes -x, up the screen
    start = (1016.5, 1004.5)
    assert Way(west, view).from_here(start) == math.inf  # no ramp in this room: no way at all
    far = Way(west, view, far=True)
    assert far.from_here(start) < 14


def test_down_the_screen_the_window_shows_too_little_for_that_hop():
    view = Viewport(2560 / 1418)
    east = cliff_target((1016.5, 1004.5))  # the hop over goes +x: 30 units down and right, 26 are shown
    assert Way(east, view, far=True).from_here((1004.5, 1004.5)) == math.inf
    assert view.hop_between(-6, 0)
    assert not view.hop_between(6, 0)
    assert not view.hop_in_view(-6, 0)  # counted from anywhere on both tiles it never was


# --- aims beside the skill bar (user, 2026-10-11: "let the macro try the corners") ---


def test_a_teleport_may_be_aimed_beside_the_skill_bar_and_not_over_it(corners):
    view = Viewport(2560 / 1418)
    assert view.hop_view((0.9, 0.93))  # the right corner
    assert view.hop_view((0.1, 0.93))
    assert not view.hop_view((0.5, 0.93))  # the bar
    assert not view.hop_view((0.75, 0.93))  # still the bar, with room to spare
    assert not view.hop_view((0.9, 0.97))  # the window's edge
    assert view.hop_view((0.5, 0.8))  # the plain view as ever
    assert not view.in_view((0.9, 0.93))  # a click on the ground or an item stays above the bar
    # Far Oasis, 02:16 on 2026-10-11: the cast at this pointer did nothing, the one further out landed.
    assert not view.hop_view((385 / 2560, 1308 / 1418))
    assert view.hop_view((2300 / 2560, 1303 / 1418))
    assert not Viewport(4 / 3).hop_view((0.97, 0.93))  # a narrow window: the bar reaches its edges


def test_with_the_corners_the_cliff_is_hopped_down_the_screen_too(corners):
    view = Viewport(2560 / 1418)
    east = cliff_target((1016.5, 1004.5))
    assert Way(east, view, far=True).from_here((1004.5, 1004.5)) < 14
    assert view.hop_between(6, 0)


def test_without_the_corners_nothing_changes():
    view = Viewport(2560 / 1418)
    assert not view.hop_view((0.9, 0.93))
    assert not view.hop_between(6, 0)
