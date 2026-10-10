"""The viewport value (macros/view.py): the projection itself, and that the older helpers in routines
and teleport, which now delegate to it, still answer as it does."""

import dataclasses
import math
import random

import pytest

from inventory_tracking.macros import routines, teleport
from inventory_tracking.macros.view import FEET, Viewport
from inventory_tracking.macros.world import Player


ASPECTS = (16 / 9, 4 / 3, 21 / 9, 1.0)
CASES = 300


def player_at(x: float, y: float) -> Player:
    return Player(1, 'X', 1, 108, x, y, None)


def random_origin(rng: random.Random) -> tuple[float, float]:
    return rng.uniform(-200, 200), rng.uniform(-200, 200)


def random_world_point(rng: random.Random, origin: tuple[float, float]) -> tuple[float, float]:
    return origin[0] + rng.uniform(-40, 40), origin[1] + rng.uniform(-40, 40)


def random_window_point(rng: random.Random) -> tuple[float, float]:
    return rng.uniform(-0.2, 1.2), rng.uniform(-0.2, 1.2)


def test_body_matches_screen_fraction() -> None:
    rng = random.Random(7)
    for aspect in ASPECTS:
        for _ in range(CASES):
            origin = random_origin(rng)
            x, y = random_world_point(rng, origin)
            expected = routines.screen_fraction(player_at(*origin), x, y, aspect)
            assert Viewport(aspect).body(origin, x, y) == pytest.approx(expected)


def test_ground_matches_ground_fraction() -> None:
    rng = random.Random(7)
    for aspect in ASPECTS:
        for _ in range(CASES):
            origin = random_origin(rng)
            x, y = random_world_point(rng, origin)
            expected = teleport.ground_fraction(player_at(*origin), x, y, aspect)
            assert Viewport(aspect).ground(origin, x, y) == pytest.approx(expected)


def test_world_matches_world_point() -> None:
    rng = random.Random(7)
    for aspect in ASPECTS:
        for _ in range(CASES):
            origin = random_origin(rng)
            across, down = random_window_point(rng)
            expected = routines.world_point(player_at(*origin), across, down, aspect)
            assert Viewport(aspect).world(origin, across, down) == pytest.approx(expected)


def test_ground_then_world_round_trips() -> None:
    rng = random.Random(7)
    for aspect in ASPECTS:
        view = Viewport(aspect)
        for _ in range(CASES):
            origin = random_origin(rng)
            point = random_world_point(rng, origin)
            assert view.world(origin, *view.ground(origin, *point)) == pytest.approx(point)


def test_on_screen_and_in_view_match_the_existing_checks() -> None:
    rng = random.Random(7)
    view = Viewport(16 / 9)
    for _ in range(CASES):
        point = random_window_point(rng)
        assert view.on_screen(point) == routines.on_screen(point)
        assert view.in_view(point) == teleport.in_view(point)


def test_hop_in_view_matches_teleport_at_the_host_aspect() -> None:
    view = Viewport(16 / 9)
    for dx in range(-6, 7):
        for dy in range(-6, 7):
            assert view.hop_in_view(dx, dy) == teleport.hop_in_view(dx, dy), (dx, dy)


def test_the_projection_is_the_classic_isometric_one_at_the_hosts_window() -> None:
    # Anchored to numbers, not to the functions that delegate here: a unit is 16 x 8 pixels of a
    # 600-pixel-high view, the feet at (0.5, 0.494), a body 0.035 of the height above its feet.
    view = Viewport(2560 / 1418)
    origin = (5000.0, 5000.0)
    assert view.ground(origin, 5010.0, 5000.0) == pytest.approx(
        (0.5 + 10 * 16 / 600 * 1418 / 2560, 0.494 + 10 * 8 / 600)
    )
    assert view.ground(origin, 5000.0, 5010.0) == pytest.approx(
        (0.5 - 10 * 16 / 600 * 1418 / 2560, 0.494 + 10 * 8 / 600)
    )
    assert view.body(origin, 5000.0, 5000.0) == pytest.approx((0.5, 0.494 - 0.035))
    assert view.aim(origin, (5008.0, 5008.0)) == pytest.approx((0.5, 0.494 + 16 * 8 / 600))
    # 16 units straight down the screen is the last an aim reaches (0.8 of the height): further is shortened.
    assert view.reachable_focal(origin, (5020.0, 5020.0)) == pytest.approx((5011.0, 5011.0))


def test_of_reads_the_window_rectangle() -> None:
    assert Viewport.of((0, 0, 2560, 1418)).aspect == 2560 / 1418


def test_of_refuses_an_empty_height() -> None:
    with pytest.raises(ValueError, match='positive size'):
        Viewport.of((0, 0, 2560, 0))
    with pytest.raises(ValueError, match='positive size'):
        Viewport.of((0, 0, 2560, -1))


def test_viewport_is_a_hashable_frozen_value() -> None:
    first = Viewport(16 / 9)
    second = Viewport.of((0, 0, 1600, 900))
    assert first == second
    assert hash(first) == hash(second)
    assert {first: 'host'}[second] == 'host'
    with pytest.raises(dataclasses.FrozenInstanceError):
        first.aspect = 4 / 3  # type: ignore[misc]


def test_a_wider_window_sees_more_across_so_a_hop_can_be_in_view_only_there() -> None:
    # Across, the hop (3, -3) is 30 world units: the ground's edges sit 2.5 units either side of it.
    # A unit is 0.0267 / aspect of the window wide, so at 21/9 the right edge is at 0.87 of the window,
    # while at 4/3 and at 16/9 it would fall past 0.97.
    assert Viewport(21 / 9).hop_in_view(3, -3)
    assert not Viewport(16 / 9).hop_in_view(3, -3)
    assert not Viewport(4 / 3).hop_in_view(3, -3)


def test_reachable_focal_keeps_a_focal_on_screen() -> None:
    view = Viewport(16 / 9)
    assert view.reachable_focal((0.0, 0.0), (1.0, 0.0)) == (1.0, 0.0)


def test_reachable_focal_shortens_an_off_screen_focal_along_its_line() -> None:
    view = Viewport(16 / 9)
    # (50, -50) is 100 units across and none down: off the screen. Share 0.25 is the furthest whose
    # ground is on it, at (12.5, -12.5).
    reachable = view.reachable_focal((0.0, 0.0), (50.0, -50.0))
    assert reachable == pytest.approx((12.5, -12.5))


def test_reachable_focal_stays_on_the_line_and_on_screen() -> None:
    rng = random.Random(7)
    for aspect in ASPECTS:
        view = Viewport(aspect)
        for _ in range(CASES):
            origin = random_origin(rng)
            focal = random_world_point(rng, origin)
            reachable = view.reachable_focal(origin, focal)
            if reachable is None:
                continue
            assert view.on_screen(view.ground(origin, *reachable))
            cross = (reachable[0] - origin[0]) * (focal[1] - origin[1]) - (reachable[1] - origin[1]) * (
                focal[0] - origin[0]
            )
            assert cross == pytest.approx(0.0, abs=1e-6)
            assert math.dist(origin, reachable) <= math.dist(origin, focal) + 1e-9


def test_reachable_focal_is_none_when_nothing_on_the_line_is_on_screen() -> None:
    # 1000 units straight down the screen: no share of that line is on screen.
    view = Viewport(16 / 9)
    assert view.reachable_focal((0.0, 0.0), (0.0, 1000.0)) is None
    assert view.aim((0.0, 0.0), (0.0, 1000.0)) is None


def test_a_focal_at_the_origin_is_the_origins_own_ground() -> None:
    view = Viewport(16 / 9)
    origin = (3.0, 4.0)
    assert view.reachable_focal(origin, origin) == origin
    assert view.aim(origin, origin) == pytest.approx(FEET)
    assert view.aim(origin, origin) == pytest.approx(view.ground(origin, *origin))
