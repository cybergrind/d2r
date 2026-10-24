"""The late bind's targets (macros/binding.py; actuator.py LATE_BIND, 2026-10-23, realtime-3-findings.md)."""

import pytest

from inventory_tracking.game.records import Monster, World
from inventory_tracking.game.view import Viewport
from inventory_tracking.macros import actuator, binding
from tests.inventory_tracking.macros.fakes import player


VIEW = Viewport(2560 / 1418)


class Plain:
    """An actuator that knows no bind (a test's, a harness's): `aim(x, y, scatter)` only."""

    def __init__(self) -> None:
        self.aims: list[tuple] = []

    def aim(self, x: float, y: float, scatter: tuple[int, int] = (0, 0)) -> None:
        self.aims.append((x, y, scatter))


class Binding(Plain):
    def aim(self, x: float, y: float, scatter: tuple[int, int] = (0, 0), bind=None) -> None:  # type: ignore[override]
        self.aims.append((x, y, scatter, bind))


class Run:
    def __init__(self, world: World, kind=Plain) -> None:
        self.now, self.actuator = world, kind()

    def world(self) -> World:
        return self.now


def world_with(here, *monsters: Monster) -> World:
    return World(True, (), 'game', (), player=player(x=here[0], y=here[1]), monsters=monsters)


def bind():
    return (0.5, 0.5)


def test_with_the_switch_off_the_aim_is_asked_without_a_bind(monkeypatch):
    monkeypatch.setattr(actuator, 'LATE_BIND', False)
    run = Run(world_with((5000.0, 5000.0)))

    binding.aim(run, (0.4, 0.6), scatter=(3, 3), bind=bind)

    assert run.actuator.aims == [(0.4, 0.6, (3, 3))]


def test_with_the_switch_on_the_aim_carries_the_bind(monkeypatch):
    monkeypatch.setattr(actuator, 'LATE_BIND', True)
    run = Run(world_with((5000.0, 5000.0)), Binding)

    binding.aim(run, (0.4, 0.6), scatter=(3, 3), bind=bind)

    assert run.actuator.aims == [(0.4, 0.6, (3, 3), bind)]


def test_the_strike_follows_the_prey_and_the_character_since_the_fights_look(monkeypatch):
    monkeypatch.setattr(binding, 'STRIKE_FOLLOWS', True)
    prey = Monster(7, 19, 1, 5010.0, 5000.0)
    focal = (5012.0, 5000.0)  # the line's spot, 2 beyond the prey
    run = Run(world_with((5001.0, 5000.0), Monster(7, 19, 1, 5010.0, 5004.0)))  # it moved 4 down, the character 1

    found = binding.newest_strike(run, prey, focal, VIEW)

    assert found == pytest.approx(VIEW.aim((5001.0, 5000.0), (5012.0, 5004.0)))
    assert found != pytest.approx(VIEW.aim((5000.0, 5000.0), focal))


def test_without_following_the_focal_stays_and_only_the_window_moves(monkeypatch):
    monkeypatch.setattr(binding, 'STRIKE_FOLLOWS', False)
    prey = Monster(7, 19, 1, 5010.0, 5000.0)
    run = Run(world_with((5001.0, 5000.0), Monster(7, 19, 1, 5010.0, 5004.0)))

    found = binding.newest_strike(run, prey, (5012.0, 5000.0), VIEW)

    assert found == pytest.approx(VIEW.aim((5001.0, 5000.0), (5012.0, 5000.0)))


def test_a_prey_not_in_the_newest_look_gives_no_bind():
    prey = Monster(7, 19, 1, 5010.0, 5000.0)
    run = Run(world_with((5000.0, 5000.0), Monster(8, 19, 1, 5010.0, 5000.0)))

    assert binding.newest_strike(run, prey, (5012.0, 5000.0), VIEW) is None


def test_no_character_gives_no_bind():
    prey = Monster(7, 19, 1, 5010.0, 5000.0)
    run = Run(World(True, (), 'game', (), player=None, monsters=(prey,)))

    assert binding.newest_strike(run, prey, (5012.0, 5000.0), VIEW) is None
