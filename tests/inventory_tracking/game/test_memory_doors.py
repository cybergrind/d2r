"""The look's doors go through the passed-door memory (game/memory.py `GameMemory.passed_doors`, levels/doors.py
PASSED_OPEN): a live hostile or the character inside a door read closed passes it; an ally or the mercenary does not."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.memory import GameMemory
from inventory_tracking.game.records import Monster
from inventory_tracking.levels import doors
from inventory_tracking.levels.doors import Door, PassedDoors
from tests.inventory_tracking.macros.fakes import player, world


SHUT = Door(2796749121, 92, doors.CLOSED_MODE, 15201.0, 8100.0)  # TombDoorRight, take 20261023T113952Z-57
DOORWAY = (15203.5, 8099.94)
CHARACTER = 692138421


@pytest.fixture(autouse=True)
def passed_open(monkeypatch):
    """The switch on: these tests are of it (each that wants it off says so)."""
    monkeypatch.setattr(doors, 'PASSED_OPEN', True)


def look(memory, *monsters: Monster, at=(15197.5, 8089.5), area: int = 57, name: str = 'Halls 57'):
    seen = replace(
        world(area, player=player(area, unit_id=CHARACTER, x=at[0], y=at[1]), monsters=monsters, doors=(SHUT,)),
        game_name=name,
    )
    return GameMemory.passed_doors(memory, seen)  # a memory of the doors alone


def test_a_hostile_in_the_doorway_passes_the_door_for_the_later_looks() -> None:
    memory = SimpleNamespace(passed=PassedDoors())
    returned = Monster(407027519, 744, 2, *DOORWAY)
    assert look(memory, returned).doors[0].passed
    assert look(memory).doors[0].passed
    assert look(memory, area=58).doors == (SHUT,)


def test_the_character_in_the_doorway_passes_it() -> None:
    memory = SimpleNamespace(passed=PassedDoors())
    assert look(memory, at=DOORWAY).doors[0].passed


def test_a_mercenary_or_a_summon_in_the_doorway_does_not() -> None:
    memory = SimpleNamespace(passed=PassedDoors())
    merc = Monster(3108057530, 338, 2, *DOORWAY, owner=CHARACTER, ally=True)
    summon = Monster(702758696, 361, 2, *DOORWAY, NO_OWNER, ally=True)
    seen = look(memory, merc, summon)
    assert seen.doors == (SHUT,)


def test_with_the_switch_off_the_look_is_as_read(monkeypatch) -> None:
    monkeypatch.setattr(doors, 'PASSED_OPEN', False)
    memory = SimpleNamespace(passed=PassedDoors())
    returned = Monster(407027519, 744, 2, *DOORWAY)
    assert look(memory, returned).doors == (SHUT,)
