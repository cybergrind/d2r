"""The reference planner and the walled game of the route situations: that they count what they say.

The small level here is two rooms of 8 x 8 tiles, 40 world units a side, at tile (100, 100): a hop
reaches from one into the other. Positions are world units.
"""

import math
import time
from collections import deque
from itertools import pairwise

import pytest

from inventory_tracking.levels.model import Ground, Walkable, pack_cells
from inventory_tracking.macros.teleport import footing
from inventory_tracking.macros.view import Viewport
from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.macros.fakes import KEYS, WINDOW
from tests.inventory_tracking.scenarios.navigation.harness import (
    HOST_ASPECT,
    Footing,
    HopField,
    Situation,
    WalledGame,
    field_of,
    footing_of,
    load,
    names,
    reach_box,
)


HOST = Viewport(HOST_ASPECT)
SIDE = 8 * TILE_UNITS


def room(tile_x: int, tile_y: int, wall=lambda x, y: False) -> Walkable:
    """An 8 x 8 tile room, walkable but for the sub-tiles `wall` names (room-relative world units)."""
    bits = ''.join('0' if wall(x, y) else '1' for y in range(SIDE) for x in range(SIDE))
    return Walkable(tile_x, tile_y, 8, 8, pack_cells(bits))


def block(x: int, y: int) -> bool:
    """A block of wall in the first room, from its top edge most of the way down."""
    return 18 <= x < 30 and y < 34


def two_rooms(wall=lambda x, y: False) -> Ground:
    return Ground((room(100, 100, wall), room(108, 100)))


def by_brute_force(ground: Ground, start, mark, view: Viewport, arrive: float) -> int | None:
    """Breadth first over single sub-tiles, each hop and each landing tested by the production functions."""
    hops = [
        (dx, dy)
        for dx in range(-40, 41)
        for dy in range(-40, 41)
        if (dx or dy) and view.in_view(view.ground((0.0, 0.0), dx, dy))
    ]
    standing = {
        (x + 0.5, y + 0.5)
        for x in range(500, 500 + 2 * SIDE)
        for y in range(500, 500 + SIDE)
        if footing(ground, ((x + 0.5) / TILE_UNITS, (y + 0.5) / TILE_UNITS))
    }
    seen, queue = {start: 0}, deque([start])
    while queue:
        here = queue.popleft()
        if math.dist(here, mark) <= arrive:
            return seen[here]
        for dx, dy in hops:
            there = (here[0] + dx, here[1] + dy)
            if there in standing and there not in seen:
                seen[there] = seen[here] + 1
                queue.append(there)
    return None


def test_the_hop_box_is_what_the_window_shows_of_the_ground():
    # 0.47 of the window to a side, 0.444 up and 0.346 down from the feet, at 16 x 8 pixels a unit.
    assert reach_box(HOST) == (-31, 31, -33, 25)
    low, high, up, down = reach_box(HOST)
    for across, lower in ((high, 0), (low, 0), (0, down), (0, up)):
        inside = ((across + lower) / 2, (lower - across) / 2)
        beyond = (
            inside[0] * (1 + 1 / max(abs(across), abs(lower))),
            inside[1] * (1 + 1 / max(abs(across), abs(lower))),
        )
        assert HOST.in_view(HOST.ground((0.0, 0.0), *inside))
        assert not HOST.in_view(HOST.ground((0.0, 0.0), *beyond))


def test_a_narrow_window_reaches_less_to_the_sides_and_the_same_up_and_down():
    assert reach_box(Viewport(4 / 3)) == (-23, 23, -33, 25)
    assert reach_box(Viewport(21 / 9))[2:] == (-33, 25)
    assert reach_box(Viewport(21 / 9))[1] > 31


@pytest.mark.parametrize('name', ['corner-east', 'up-the-screen', 'u-detour'])
def test_the_footing_bits_are_the_production_footing(name):
    # Every sub-tile of a strip across the level, and a margin beyond its edge.
    ground = Ground(load(name).ground)
    found = Footing(ground)
    for y in range(found.y - 2, found.y + found.height + 2, 7):
        for x in range(found.x - 2, found.x + found.width + 2):
            spot = (x + 0.5, y + 0.5)
            assert found.has(spot) == bool(footing(ground, (spot[0] / TILE_UNITS, spot[1] / TILE_UNITS))), spot


@pytest.mark.parametrize(
    ('start', 'mark'),
    [
        ((502.5, 502.5), (575.5, 535.5)),  # from the level's first corner across both rooms
        ((575.5, 535.5), (505.5, 505.5)),  # and back: the window shows more up the screen than down
        ((520.5, 520.5), (521.5, 522.5)),  # already there
    ],
)
def test_the_field_counts_what_a_search_hop_by_hop_counts(start, mark):
    ground = two_rooms(block)
    field = HopField(Footing(ground), mark, HOST)
    assert field.hops(start) == by_brute_force(ground, start, mark, HOST, 5.0)


def test_every_spot_of_the_level_has_its_count():
    # The corners too: a spot's hop box hangs over the level's edge there.
    found = Footing(two_rooms())
    field = HopField(found, (540.5, 520.5), HOST)
    assert all(field.at(spot) is not None for spot in found.near((540.5, 520.5), 60.0))


def test_a_route_is_made_of_hops_in_view_onto_footing_and_ends_at_the_mark():
    ground = two_rooms(block)
    found = Footing(ground)
    field = HopField(found, (575.5, 535.5), HOST)
    route = field.route((502.5, 502.5))
    assert len(route) - 1 == field.hops((502.5, 502.5)) == 4
    assert all(HOST.in_view(HOST.ground(a, *b)) for a, b in pairwise(route))
    assert all(found.has(spot) for spot in route[1:])
    assert math.dist(route[-1], (575.5, 535.5)) <= 5.0


def test_the_start_needs_no_footing():
    ground = two_rooms(lambda x, y: x < 6)  # the character stands in the wall's edge, as on a lava bank
    field = HopField(Footing(ground), (540.5, 520.5), HOST)
    assert not Footing(ground).has((503.5, 520.5))
    assert field.hops((503.5, 520.5)) == 2


def test_a_void_wider_than_a_hop_is_no_way():
    ground = Ground((room(100, 100), room(120, 100)))  # sixty units of nothing between the rooms
    field = HopField(Footing(ground), (620.5, 520.5), HOST)
    assert field.hops((520.5, 520.5)) is None
    assert field.route((520.5, 520.5)) is None


def test_other_ends_than_the_marks_own_surroundings():
    # A hunt ends wherever the monster can be struck from: the field takes the spots that end the route.
    found = Footing(two_rooms())
    near = HopField(found, (575.5, 520.5), HOST, ends=found.near((575.5, 520.5), 20.0))
    assert near.hops((505.5, 520.5)) == 2
    assert HopField(found, (575.5, 520.5), HOST).hops((505.5, 520.5)) == 3


@pytest.mark.parametrize('name', names())
def test_the_reference_answers_within_a_second(name):
    situation = load(name)
    footing_of.cache_clear()
    field_of.cache_clear()
    began = time.perf_counter()
    field = field_of(situation)
    route = field.route(situation.start)
    assert time.perf_counter() - began < 1.0
    assert route is not None
    assert len(route) - 1 == field.hops(situation.start)


def walled(start=(520.5, 520.5)) -> WalledGame:
    ground = (room(100, 100, lambda x, y: x >= 30), room(108, 100))
    return WalledGame(Situation('walled', 109, (), ground, start, (575.5, 520.5)))


def aim(game: WalledGame, spot) -> None:
    here = game.world.player
    across, down = HOST.ground((here.x, here.y), *spot)
    game.keys.move_pointer(round(WINDOW[0] + across * WINDOW[2]), round(WINDOW[1] + down * WINDOW[3]))


def test_a_teleport_lands_on_the_centre_of_the_sub_tile_aimed_at():
    game = walled()
    aim(game, (510.2, 512.8))
    game.react(('key', KEYS[54]))
    assert (game.world.player.x, game.world.player.y) == (510.5, 512.5)
    assert game.refused == []


def test_a_teleport_at_a_wall_moves_nobody_and_is_counted():
    game = walled()
    aim(game, (535.5, 520.5))
    game.react(('key', KEYS[54]))
    assert (game.world.player.x, game.world.player.y) == (520.5, 520.5)
    assert len(game.refused) == 1
