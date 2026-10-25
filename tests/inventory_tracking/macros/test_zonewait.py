"""The wait for a terror zone the loop cannot play, filled with Worldstone Keep games (macros/zonewait.py
ZONE_WAIT_WSK, 2026-10-25; the player: "do worldstone keep, if we get some shard - good, if not - next game"), over
test_tzloop.py's scripted game: the switch off keeps the lobby's wait; on, WSK games are played until the zone turns."""

import logging
import time
from types import SimpleNamespace

import pytest

from inventory_tracking.macros import actloop, tzloop, tzroutine, zonenav, zonewait
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.agenda import TRANSIT, ZONE_LEFT
from inventory_tracking.macros.loop import LEAVE, TZ, TZ_LEVEL, TZ_NEXT_LEVEL, TZ_PORTAL, TZ_WAYPOINT, Loop
from inventory_tracking.macros.running import legs
from tests.inventory_tracking.macros.test_tzloop import CATACOMBS, ROGUE_ENCAMPMENT, Script


MOO_MOO = frozenset((39,))  # Act1-MooMooFarm: only the red portal Wirt's Leg opens leads in, no excursion
WSK2, WSK3 = 129, 130
LONG, SHORT = 1553.0, 100.0  # seconds to the next zone: 12:04:27 on 2026-10-25, and one under a filler game


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    monkeypatch.setattr(zonewait, '_games', {})


@pytest.fixture(autouse=True)
def live_navigation(zone_navigation_off, monkeypatch):
    """The zones played by the graph, as the live loop plays them (zonenav.py ACTS, ROTATION; off under test)."""
    monkeypatch.setattr(zonenav, 'ACTS', frozenset(range(1, 6)))
    monkeypatch.setattr(zonenav, 'ROTATION', True)


def waiting(monkeypatch, seconds: float, on: bool = True) -> None:
    monkeypatch.setattr(zonewait, 'ZONE_WAIT_WSK', on)
    monkeypatch.setattr(tzloop, 'zone_wait', lambda now: seconds)


def played(game: Script, count: int = 8) -> list[str]:
    legs_made = [game.leg() for _ in range(count) if game.play.world.in_game]
    return legs_made[: legs_made.index(LEAVE) + 1] if LEAVE in legs_made else legs_made


def test_off_an_unplayable_zone_is_waited_for_in_the_lobby_as_before(monkeypatch):
    waiting(monkeypatch, LONG, on=False)
    game = Script(ROGUE_ENCAMPMENT, monkeypatch, zone=MOO_MOO)
    with pytest.raises(Abort, match='Act1-MooMooFarm is not playable: no excursion') as stop:
        game.leg()
    assert stop.value.cause == 'zone'
    assert game.loop.cooling > time.monotonic()
    assert game.calls == []


def test_on_the_wait_is_a_worldstone_keep_game_levels_2_and_3_then_the_next_game(monkeypatch, caplog):
    waiting(monkeypatch, LONG)
    game = Script(ROGUE_ENCAMPMENT, monkeypatch, zone=MOO_MOO)
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        legs_made = played(game)

    # The waypoint to Level 2, its run, the Baal route's stairs, Level 3's run, Save and Exit: no Throne, no Baal
    assert legs_made == [TZ_WAYPOINT, TZ_LEVEL, TZ_NEXT_LEVEL, TZ_LEVEL, LEAVE]
    assert game.runs == [WSK2, WSK3]
    assert [call for call in game.calls if call[0] != 'prebuff'] == [('waypoint', WSK2), ('door', WSK3)]
    assert game.loop.cooling < time.monotonic()  # no lobby wait
    assert 'Save and Exit' in game.play.said
    said = [r.getMessage() for r in caplog.records if 'zone wait: a Worldstone Keep game while' in r.getMessage()]
    assert said == [
        'Macro: zone wait: a Worldstone Keep game while Act1-MooMooFarm is not playable (no catalogue excursion '
        'covers it), 1553 s to the next zone: Baal from 129: [129, 130]'
    ]
    # Not one of its levels blocked as a level the zone left (tzloop.py ZONE_LEFT_NO_WAY)
    assert game.loop.agenda.blocked == {}


def test_the_next_game_with_the_zone_still_unplayable_is_another_worldstone_keep_game(monkeypatch):
    waiting(monkeypatch, LONG)
    first = Script(ROGUE_ENCAMPMENT, monkeypatch, zone=MOO_MOO)
    assert played(first)[-1] == LEAVE
    second = Script(ROGUE_ENCAMPMENT, monkeypatch, zone=MOO_MOO)
    second.loop.agenda.begin('cyber33')  # another game's agenda
    assert played(second) == [TZ_WAYPOINT, TZ_LEVEL, TZ_NEXT_LEVEL, TZ_LEVEL, LEAVE]


def test_a_wait_shorter_than_one_worldstone_keep_game_is_the_lobbys(monkeypatch, caplog):
    waiting(monkeypatch, SHORT)
    assert zonewait.game_seconds() > SHORT
    game = Script(ROGUE_ENCAMPMENT, monkeypatch, zone=MOO_MOO)
    with caplog.at_level(logging.INFO, logger='inventory_tracking'), pytest.raises(Abort) as stop:
        game.leg()
    assert stop.value.cause == 'zone'
    assert game.calls == []
    assert any('no Worldstone Keep game: 100 s to the next zone' in r.getMessage() for r in caplog.records)


def test_the_zone_turning_playable_under_the_game_ends_the_filler_at_once(monkeypatch, caplog):
    waiting(monkeypatch, LONG)
    game = Script(ROGUE_ENCAMPMENT, monkeypatch, zone=MOO_MOO)
    assert [game.leg() for _ in range(2)] == [TZ_WAYPOINT, TZ_LEVEL]
    # The :30 turn: the Catacombs read terrorized
    game.zone = CATACOMBS
    game.progress.wanted = lambda area: area in CATACOMBS
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        legs_made = [game.leg() for _ in range(2)]

    assert legs_made == [TZ_PORTAL, TZ_WAYPOINT]  # Town Portal off the filler, the waypoint to the new zone
    assert game.calls[-1] == ('waypoint', 35)
    assert any('the Worldstone Keep game ends its filler: Act1-Catacombs is playable' in r.getMessage()
               for r in caplog.records)  # fmt: skip


def test_a_shard_over_the_limit_used_at_the_waypoint_terrorizes_its_act_and_the_game_plays_it(monkeypatch, caplog):
    # actloop.py OVERFLOW_KINDS: a TZ leveling game uses a carried shard over the limit at a town's waypoint leg. A
    # Northern one terrorizes act 5: the filler's levels are then the act's own, and the act is played as any shard's
    waiting(monkeypatch, LONG)
    game = Script(ROGUE_ENCAMPMENT, monkeypatch, zone=MOO_MOO)

    def used(loop, run, terrorized, key, *, carried_only=False):
        loop.agenda.acts = (5,)  # a confirmed use (actloop.py `overflow`)

    monkeypatch.setattr(actloop, 'overflow', used)
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        assert game.leg() == TZ_WAYPOINT
        game.leg()

    plan = game.loop.agenda.plan
    assert isinstance(plan, tzroutine.Itinerary)
    assert 'Act5-Manual' in plan.zone
    assert any('ends its filler: Act5-Manual' in r.getMessage() for r in caplog.records)


def test_a_restart_on_a_filler_level_takes_the_worldstone_keep_game_up(monkeypatch, caplog):
    waiting(monkeypatch, LONG)
    game = Script(WSK3, monkeypatch, zone=MOO_MOO)
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        assert game.leg() == TZ_LEVEL
    assert game.runs == [WSK3]
    assert any('a Worldstone Keep game taken up in The Worldstone Keep Level 3' in r.getMessage()
               for r in caplog.records)  # fmt: skip


def test_a_field_level_of_another_game_ends_it_as_before(monkeypatch):
    waiting(monkeypatch, LONG)
    field = Script(3, monkeypatch, zone=MOO_MOO)
    assert field.leg() == LEAVE


def test_a_filler_level_is_worked_though_not_terrorized_and_a_zones_own_level_is_still_left():
    loop = Loop(on=True, kind=TZ, chosen=True)
    loop.agenda.begin('cyber32')
    runner = SimpleNamespace(loop=loop, progress=SimpleNamespace(wanted=lambda area: False), valuable_left=lambda: None)
    loop.agenda.plan = zonewait.filler_plan()
    policy = legs._agenda_policy(runner, WSK2)  # pyrefly: ignore[bad-argument-type]  # the runner's fields only
    assert policy not in (ZONE_LEFT, TRANSIT)
    loop.agenda.plan = tzroutine.itinerary(frozenset((128, 129, 130, 131)))  # the Act5-WorldstoneKeep zone, turned
    assert legs._agenda_policy(runner, WSK2) == ZONE_LEFT  # pyrefly: ignore[bad-argument-type]  # as above


def test_the_filler_plan_is_levels_2_and_3_by_the_baal_routes_stairs():
    plan = zonewait.filler_plan()
    assert plan is not None
    assert [(trip.route, trip.waypoint, trip.areas, trip.zone) for trip in plan.excursions] == [
        ('Baal', WSK2, (WSK2, WSK3), frozenset((WSK2, WSK3)))
    ]
    assert not zonewait.filler(tzroutine.itinerary(frozenset((128, 129, 130, 131))))
