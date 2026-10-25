"""DOOR_FIGHT (macros/hunting/moves.py; rca/2026-10-25/door-pack-findings.md, tactics/apply-door.md): a tier 4-5 pack
behind a closed door is gone to by the walk to the door (the mark first, then the door clicked open) in place of the
retreats that passed it with no strike. The player, 2026-10-25 ~11:20: "they were in closed room, behind closed door.
we didn't try to engage it by teleporting into their room or open their door".

The shape of take 20261025T081241Z-36, 11:12:54: the character 21 south of a closed DoorWoodenRight (class 16), 15
Mana Burn members north of it, every approach vetoed; the act was "retreating: every progress act is vetoed"."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from inventory_tracking.game.records import Monster
from inventory_tracking.levels.doors import Door
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.hunting import moves
from inventory_tracking.macros.pursuit import Hold, Move
from inventory_tracking.macros.travel import PRESSED
from inventory_tracking.routes.model import FIGHT
from tests.inventory_tracking.macros.fakes import player, world


ELITE = 1242939368
HERE = (22540.0, 8271.0)
DOOR = Door(77, 16, 0, 22540.0, 8250.0)  # DoorWoodenRight, closed
PACK = [
    Monster(ELITE, 7, 1, 22542.0, 8240.0, tier=5, flags=8),
    Monster(ELITE + 1, 7, 1, 22538.0, 8243.0, tier=5),
]
GOAL = Goal('full clear: the elite 7', (22542.0, 8240.0), FIGHT, 22.0, PRESSED, unit=ELITE)
RETREAT = Move(Step((22540.0, 8293.0)), GOAL, 'retreating: every progress act is vetoed')


def hunter():
    return SimpleNamespace(safety=SimpleNamespace(burn_leaving=None))


def seen(*doors):
    return replace(world(36, player=player(36, x=HERE[0], y=HERE[1])), doors=doors, monsters=tuple(PACK))


def asked(self, the_world, act=RETREAT, *, in_reach=False, hurt=False, now=10.0, foes=PACK):
    return moves.door_fight(self, the_world, foes, GOAL, act, in_reach=in_reach, hurt=hurt, now=now)


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(moves, 'DOOR_FIGHT', True)


def test_off_the_retreat_stays():
    assert asked(hunter(), seen(DOOR)) is RETREAT


def test_the_pack_behind_a_closed_door_is_gone_to_by_the_door(on):
    act = asked(hunter(), seen(DOOR))
    assert isinstance(act, Move)
    assert act.reason == moves.DOOR_SAID
    assert act.step.skill is None  # a walk: no Teleport into the room
    assert act.step.spot[1] > DOOR.y  # this side of the leaf
    assert abs(act.step.spot[1] - DOOR.y) < 2.0


def test_no_door_fight_with_the_door_open_a_shot_a_hit_or_the_mana_leave(on):
    assert asked(hunter(), seen(replace(DOOR, mode=2))) is RETREAT  # open: the fight's own rules
    assert asked(hunter(), seen(DOOR), in_reach=True) is RETREAT
    assert asked(hunter(), seen(DOOR), hurt=True) is RETREAT
    hold = Hold(GOAL)
    assert asked(hunter(), seen(DOOR), hold) is hold
    leaving = SimpleNamespace(safety=SimpleNamespace(burn_leaving='mana: leaving'))
    assert asked(leaving, seen(DOOR)) is RETREAT


def test_a_door_is_tried_for_door_seconds_then_the_budgets_as_before(on):
    self = hunter()
    assert asked(self, seen(DOOR), now=10.0).reason == moves.DOOR_SAID
    assert asked(self, seen(DOOR), now=10.0 + moves.DOOR_SECONDS - 0.1).reason == moves.DOOR_SAID
    assert asked(self, seen(DOOR), now=10.0 + moves.DOOR_SECONDS + 0.1) is RETREAT


def test_not_for_a_pack_under_tier_4(on):
    weak = [replace(m, tier=3) for m in PACK]
    assert asked(hunter(), seen(DOOR), foes=weak) is RETREAT
