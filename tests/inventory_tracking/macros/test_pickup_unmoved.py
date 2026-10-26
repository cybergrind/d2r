"""pickup.py `moved_in_hand` after a hop whose Teleport moved nothing (the stop of 2026-10-26 03:03:58: the move in
hand chose a Teleport to the very spot that had just cast nothing, twice a leg, and the loop stopped)."""

from types import SimpleNamespace
from typing import Any, cast

from inventory_tracking.macros import pickup
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.skills import TELEPORT


def _moved(monkeypatch, why: Abort) -> tuple[dict, list]:
    seen: dict[int, float] = {}
    made: list = []

    class FakeTravel:
        def __init__(self, movement) -> None:
            self.jump_failed: dict[int, float] = {}

        def toward(self, run, world, ground, aspect, goal, intent, rooms):
            seen.update(self.jump_failed)
            return Step((22730.0, 9856.0), None)

        def make(self, run, found, world, aspect, key_names, ground, **_):
            made.append(found)

    monkeypatch.setattr(pickup, 'Travel', FakeTravel)
    monkeypatch.setattr(pickup, 'Ground', lambda grids: None)
    run = cast(Any, SimpleNamespace(build=SimpleNamespace(movement=()), world=lambda: object(), clock=lambda: 42.0))
    drop = cast(Any, SimpleNamespace(x=22711.0, y=9853.0, label='Large Charm'))
    level = cast(Any, SimpleNamespace(ground=(), rooms=()))
    assert pickup.moved_in_hand(run, drop, level, 16 / 9, None, why)
    return seen, made


def test_a_teleport_that_moved_nothing_is_told_to_the_move_in_hand(monkeypatch):
    seen, made = _moved(monkeypatch, Abort('Teleport: the character did not move (no charges, nowhere to land?)'))
    assert seen == {TELEPORT: 42.0}  # its set leaves Teleport alone for the intent's distrust
    assert len(made) == 1


def test_another_hop_failure_leaves_teleport_trusted(monkeypatch):
    seen, made = _moved(monkeypatch, Abort('no game window'))
    assert seen == {}
    assert len(made) == 1
