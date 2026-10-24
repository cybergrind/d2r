"""The look of 14:40:39.06 in take 20261023T113952Z-57 (Halls of the Dead Level 2, rca/2026-10-23/jumps-findings.md
case 1), priced with the door the game let the pack through (levels/doors.py PASSED_OPEN).

The TombDoorRight 2796749121 read mode 0 the whole take. At 14:40:12.918 the Returned 407027519 stood in its doorway;
at 14:40:39.06 the character stood north of it with four members of the Herald pack 15.2-17.6 off south of it, and the
look priced no Hold: every shot crossed the door. With the door passed the look has a member in reach and prices a
Hold; with the switch off it prices none, as the game did.

The looks are priced as hunting/judging.py `safety_priced` and `Hunter.pursue` price them: the reach over the frame's
ground and doors (sight.in_reach), the observation with the walls and the doors, the build's attack and settings.
"""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.combat.policy import observe
from inventory_tracking.combat.survival import CALM
from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.records import Loot, Monster
from inventory_tracking.levels import doors
from inventory_tracking.levels.doors import Door, PassedDoors
from inventory_tracking.levels.model import Ground, Walkable
from inventory_tracking.macros import pursuit as p, safety as module
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.sight import in_reach
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import STANDING
from tests.inventory_tracking.macros.fakes import player, world


FIXTURE = Path(__file__).parent / 'fixtures' / 'door-passed-halls.json'
NOW = 10.0
FULL_BELT = (1,) * 16


@pytest.fixture(autouse=True)
def passed_open(monkeypatch):
    """The switch on: these tests are of it (each that wants it off says so)."""
    monkeypatch.setattr(doors, 'PASSED_OPEN', True)


def monsters_of(rows: list[dict]) -> tuple[Monster, ...]:
    return tuple(
        Monster(
            m['unit'], m['txt'], m['mode'], m['x'], m['y'], m['owner'], flags=m['flags'], ally=m['ally'],
            life=m['life'], max_life=m['max_life'], modifiers=tuple(m['mods']), tier=m['tier'],
        )
        for m in rows
    )  # fmt: skip


def hostile(monsters) -> list[Monster]:
    return [m for m in monsters if not m.ally and m.owner == NO_OWNER]


def look_doors(snap: dict) -> tuple[Door, ...]:
    """The look's doors through the level's memory: the frame of 14:40:12.918 first, then the look's."""
    door = Door(*snap['door'])
    memory, level = PassedDoors(), ('Halls 57', snap['player']['unit'], snap['area'])
    before = snap['before']
    standing = [tuple(before['player']), *((m.x, m.y) for m in hostile(monsters_of(before['monsters'])))]
    memory.seen(level, [door], standing)
    here = (snap['player']['x'], snap['player']['y'])
    return memory.seen(level, [door], [here, *((m.x, m.y) for m in hostile(monsters_of(snap['monsters'])))])


def priced() -> tuple[bool, dict]:
    """(a hostile in the strike's reach, the decision record) at the look."""
    snap = json.loads(FIXTURE.read_text(encoding='utf-8'))
    ground = Ground(Walkable(**g) for g in snap['ground'])
    seen_doors = look_doors(snap)
    monsters = monsters_of(snap['monsters'])
    here = player(snap['area'], x=snap['player']['x'], y=snap['player']['y'])
    alive = world(snap['area'], player=here, monsters=monsters, doors=seen_doors)
    foes, companions = hostile(monsters), [m for m in monsters if m.ally or m.owner != NO_OWNER]
    build = ECHOING_STRIKE_BUILD
    attack, settings = build.attack, build.settings.safety
    assert attack is not None
    at = (here.x, here.y)
    reach = any(in_reach(ground, at, (m.x, m.y), attack.reach, seen_doors) for m in foes)
    seen = attack.sees(observe(here, foes, companions, ground, seen_doors), companions)
    loot = Loot(
        life=snap['player']['life'],
        max_life=snap['player']['max_life'],
        stats=tuple((stat, value) for stat, value in snap['stats']),
        belt=FULL_BELT,
    )
    safety = module.Safety()
    safety.draw_lands = snap['draw_lands']
    look = safety.look(alive, loot, 'battle', seen.blocked, build.shield, settings, now=NOW, draw=build.draw)
    goal = Goal('the fight', seen.origin, 'fight', attack.reach, STANDING)
    facts = replace(
        p.Facts(NOW, goal, reach, reach, True, lambda: Step(goal.place), snap['area']), near=True, quiet=0.2
    )
    safety.price(
        facts, None, look, loot, CALM, settings, seen, attack, lambda point: Step(point),
        options=lambda point: (Step(point, TELEPORT), Step(point)), teleport_hands='battle',
    )  # fmt: skip
    return reach, safety.decision


def holds(decision: dict) -> list[dict]:
    return [c for c in decision['candidates'] if c['act'] == 'Hold']


def test_with_the_door_passed_the_look_has_a_member_in_reach_and_prices_a_hold() -> None:
    reach, decision = priced()
    assert reach
    assert holds(decision), decision['candidates']
    assert holds(decision)[0]['veto'] is None


def test_with_the_switch_off_the_look_prices_no_hold_as_the_game_did(monkeypatch) -> None:
    monkeypatch.setattr(doors, 'PASSED_OPEN', False)
    reach, decision = priced()
    assert not reach
    assert not holds(decision)
