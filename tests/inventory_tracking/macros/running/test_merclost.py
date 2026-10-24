"""The service's merc look and its trip (macros/running/merclost.py `_merc_poll`): the merc lost, a town trip at the
first safe moment, the level run ended for it. The player, 2026-10-21 ~19:00: "also, we have lost merc -> probably
better retreat to the town and refill hp potions in the belt"."""

import logging
import threading
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.game.records import Monster
from inventory_tracking.macros import merc, tzloop
from inventory_tracking.macros.agenda import PORTAL_TO_TOWN
from inventory_tracking.macros.loop import ANDARIEL, TOWN, TZ, TZ_BACK, TZ_LEVEL, TZ_PICKUP, TZ_PORTAL, TZ_WAYPOINT
from inventory_tracking.macros.runner import MacroRunner
from inventory_tracking.macros.town import Exit
from tests.inventory_tracking.macros.fakes import player, world
from tests.inventory_tracking.macros.test_tzloop import FORTRESS, GAME, ROGUE_ENCAMPMENT, Script


AREA = 128  # Worldstone Keep 1, 18:55:55 on 2026-10-21
ME = player(AREA).unit_id
MERC = Monster(377627261, 338, 1, 5002.0, 5000.0, ME, ally=True)
BELT = (606, 606, 531, 531) * 4


def look(*monsters: Monster, dead: frozenset[int] = frozenset()):
    return world(AREA, monsters=monsters, dead=dead, game_name=GAME, player=player(AREA))


DEAD = look(dead=frozenset({MERC.unit_id}))


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    monkeypatch.setattr(merc, 'LEVELS', {})
    monkeypatch.setattr(merc, 'UNREVIVED', set())
    monkeypatch.setattr(merc, 'NO_POTIONS', set())


def runner(looks: list, kind=TZ, *, on: bool = True) -> MacroRunner:
    found = MacroRunner(
        None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent'), display=lambda lines: None,
        place=lambda: (GAME, AREA),
    )  # fmt: skip
    found.loop.on, found.loop.kind = on, kind
    found.loop.seen = (GAME, 0.0)
    found.area_seen = AREA
    found.life_seen = (2907, 2907)
    found.attack_mode, found.working = True, True
    found.merc_read = lambda: (looks.pop(0), BELT, 95) if looks else None
    return found


def polls(found: MacroRunner, times) -> list[bool]:
    return [found._merc_poll(float(now)) for now in times]


def test_a_dead_merc_makes_the_town_trip_and_ends_the_level_run(caplog):
    found = runner([look(MERC), DEAD, DEAD, DEAD])
    with caplog.at_level(logging.INFO):
        made = polls(found, (0, 2, 4, 6))
    assert made == [False, False, False, True]  # the corpse read at 2, held 4 s at 6
    top = found.loop.agenda.package()
    assert top is not None
    assert top.kind == PORTAL_TO_TOWN
    assert not found.attack_mode
    assert found.cancelled.is_set()
    assert 'Macro: merc lost: a town trip to refill the belt and revive the merc (no hostile within 30)' in caplog.text


def test_one_missed_sample_makes_no_trip():
    found = runner([look(MERC), look(), look(MERC), look(), look(MERC), look(MERC)])
    assert not any(polls(found, range(0, 12, 2)))
    assert found.loop.agenda.stack == []
    assert found.attack_mode


def test_the_trip_waits_for_no_hostile_in_reach():
    foe = Monster(10, 638, 1, 5004.0, 5000.0)
    found = runner([look(MERC), DEAD, replace(DEAD, monsters=(foe,)), replace(DEAD, monsters=(foe,)), DEAD])
    assert polls(found, (0, 2, 6, 8, 10)) == [False, False, False, False, True]


@pytest.mark.parametrize(
    ('why', 'changes'),
    [('the player turned the loop off', {'on': False}), ('a kind with no package (Andariel)', {'kind': ANDARIEL})],
)
def test_no_look_and_no_trip(why, changes):
    looks = [look(MERC), DEAD, DEAD, DEAD]
    found = runner(looks, **changes)
    assert not any(polls(found, (0, 2, 4, 6))), why
    assert len(looks) == 4, why  # nothing read
    assert found.attack_mode, why


def test_no_trip_while_another_package_is_under_way():
    found = runner([look(MERC), DEAD, DEAD, DEAD, DEAD])
    found.loop.agenda.begin(GAME)
    found.loop.agenda.push(*tzloop.room_package(AREA))
    assert not any(polls(found, (0, 2, 4, 6)))


@pytest.mark.parametrize('switch', ['MERC_LOST_TRIP'])
def test_the_switch_off_makes_no_trip(monkeypatch, switch):
    monkeypatch.setattr(merc, switch, False)
    found = runner([look(MERC), DEAD, DEAD, DEAD])
    assert not any(polls(found, (0, 2, 4, 6)))


# --- the package over the scripted game (test_tzloop.py `Script`) ---------------------------------------------------


@pytest.mark.parametrize('remembered', [False, True])
def test_the_trip_back_resumes_the_level_and_its_remembered_valuable(monkeypatch, remembered):
    game = Script(36, monkeypatch)
    routines: list[int] = []
    monkeypatch.setattr(merc, 'town_routine', lambda run, trips=None: routines.append(game.area))
    if remembered:
        game.sightings[36] = 'Ist Rune at (5010, 5010)'  # seen before the trip: the runner's sightings survive it
        game.picks = [True]
    game.loop.agenda.begin(game.loop.observe(game.play.world))
    merc.trip(game.loop.agenda.push, 36, merc.WHY_MERC, 'no hostile within 30')
    exits: list[Exit] = []
    legs = [game.leg(visit=exits.append) for _ in range(7)]

    # the room trip's own legs, the shared town visit among them, then the revive (the player, 2026-10-21 ~20:36:
    # "every time we visit town and traders - we need to to the routine"; "reuse routines")
    after = TZ_PICKUP if remembered else TZ_LEVEL
    assert legs == [TZ_PORTAL, TZ_WAYPOINT, TOWN, merc.MERC_TRIP, TZ_WAYPOINT, TZ_BACK, after]
    assert exits == [Exit.PORTAL]  # the visit as the room package makes it
    assert game.loop.visited == GAME  # the game's visit: no room visit at a boundary for nothing
    assert [call for call in game.calls if call[0] != 'prebuff'] == [
        ('portal', ROGUE_ENCAMPMENT),
        ('waypoint', FORTRESS),
        ('waypoint', ROGUE_ENCAMPMENT),
        ('through', 36),  # the same portal, the same level
    ]
    assert routines == [FORTRESS]
    assert game.loop.agenda.stack == []
    assert game.loop.trips == 0  # no trip for room counted (loop.py `may_trip`)


def test_a_revive_click_that_travels_to_harrogath_still_ends_back_through_the_portal(monkeypatch):
    # Tyrael's menu may hold "Travel to Harrogath" (a character past act 4): the scan's click lands in act 5 mid-trip
    from inventory_tracking.macros import repair

    game = Script(36, monkeypatch)
    monkeypatch.setattr(repair, 'gold', lambda run, stat=14: 300_000 if stat == 14 else 9_000_000)

    def travel_to_harrogath(run):
        game.go('travel', 109)
        raise merc.LeftFortress('the click took the character to level 109')

    monkeypatch.setattr(merc, 'resurrect', travel_to_harrogath)
    monkeypatch.setattr(merc, 'travel', lambda run, to, marks=None: game.go('waypoint', to))
    game.loop.agenda.begin(game.loop.observe(game.play.world))
    merc.trip(game.loop.agenda.push, 36, merc.WHY_MERC, 'no hostile within 30')
    legs = [game.leg(visit=lambda exit: None) for _ in range(7)]

    assert legs == [TZ_PORTAL, TZ_WAYPOINT, TOWN, merc.MERC_TRIP, TZ_WAYPOINT, TZ_BACK, TZ_LEVEL]
    assert [call for call in game.calls if call[0] != 'prebuff'] == [
        ('portal', ROGUE_ENCAMPMENT),
        ('waypoint', FORTRESS),
        ('travel', 109),  # the click
        ('waypoint', FORTRESS),  # back where the package goes on from
        ('waypoint', ROGUE_ENCAMPMENT),
        ('through', 36),
    ]
    assert GAME in merc.UNREVIVED
