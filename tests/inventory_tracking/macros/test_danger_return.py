"""A beset recovery's portal return (macros/tzloop.py DANGER_RETURN; the coordinator, 2026-10-22): after the town
visit, back through the portal only when the safety's gate allows (macros/safety.py RETURN_GATE via
running/recovery.py `back_for_bosses`), then Battle Orders on the arrival before any fight (running/legs.py
`orders_on_arrival`, macros/cta.py `arrival_due`); refused, the loop stops in town naming the bosses."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from inventory_tracking.macros import cta, tzloop
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.agenda import STACK, THROUGH_PORTAL, Objective
from inventory_tracking.macros.running import legs
from inventory_tracking.macros.stops import Remedy, first
from tests.inventory_tracking.macros.test_tzloop import GAME, KURAST_DOCKS, TRAVINCAL, Script, keys


BACK = Objective(THROUGH_PORTAL, 'back through the portal', STACK, to=TRAVINCAL)
REFUSED = (
    'not back through the portal: life 900/1896, under 90%: Ismail Vilehand (Travincal) alive: the loop stops here'
)


def danger_game(monkeypatch, refused: str | None):
    game = Script(KURAST_DOCKS, monkeypatch, zone=frozenset((TRAVINCAL,)))
    game.portal_from = TRAVINCAL
    game.loop.danger_return = GAME  # tzloop.py `danger_trip` pushed this package
    asked: list[str] = []

    def gate() -> str | None:
        asked.append('gate')
        return refused

    def orders() -> str:
        asked.append(f'orders in {game.area}')
        return 'cast'

    hands = replace(game.hands(), back_for_bosses=gate, orders_on_arrival=orders)
    return game, hands, asked


def test_allowed_goes_back_through_the_portal_then_battle_orders_on_the_arrival(monkeypatch) -> None:
    game, hands, asked = danger_game(monkeypatch, None)
    tzloop.perform(game.loop, game.play.run(), keys, game.progress, BACK, hands)
    assert game.calls[-1] == ('through', TRAVINCAL)
    assert asked == ['gate', f'orders in {TRAVINCAL}']  # the gate in town, the cast in the level
    assert game.loop.danger_return is None


def test_refused_stops_in_town_naming_the_bosses(monkeypatch) -> None:
    game, hands, asked = danger_game(monkeypatch, REFUSED)
    with pytest.raises(Abort) as stopped:
        tzloop.perform(game.loop, game.play.run(), keys, game.progress, BACK, hands)
    assert stopped.value.cause == 'idle'
    assert 'Ismail Vilehand' in str(stopped.value)
    assert first('idle', on=True, dead=False) is Remedy.STOP  # the loop stops where it is: in town
    assert ('through', TRAVINCAL) not in game.calls
    assert game.area == KURAST_DOCKS
    assert asked == ['gate']


def test_a_room_trip_s_return_is_not_gated(monkeypatch) -> None:
    game, hands, asked = danger_game(monkeypatch, REFUSED)
    game.loop.danger_return = None  # a trip for room, no beset recovery
    tzloop.perform(game.loop, game.play.run(), keys, game.progress, BACK, hands)
    assert game.calls[-1] == ('through', TRAVINCAL)
    assert asked == []


def test_with_the_switch_off_the_return_is_as_before(monkeypatch) -> None:
    monkeypatch.setattr(tzloop, 'DANGER_RETURN', False)
    game, hands, asked = danger_game(monkeypatch, REFUSED)
    tzloop.perform(game.loop, game.play.run(), keys, game.progress, BACK, hands)
    assert game.calls[-1] == ('through', TRAVINCAL)
    assert asked == []


class Buffs:
    """The attack mode's executor as `orders_on_arrival` asks it: the Call to Arms row due or not."""

    def __init__(self, due: bool) -> None:
        self.row = SimpleNamespace(caster='cta')
        self.is_due, self.cast_with = due, []

    def rows(self, phase: str):
        return (SimpleNamespace(caster=None), self.row) if phase == 'upkeep' else ()

    def facts(self, run, world, foes, ahead=0.0):
        return SimpleNamespace(ahead=ahead)

    def due(self, run, row, facts):
        assert row is self.row
        assert facts.ahead == cta.ARRIVAL_LEFT  # the arrival's rule: under ARRIVAL_LEFT s in the quiet
        return 'due' if self.is_due else None

    def cast(self, run, due, key_names):
        self.cast_with.append(due)


def arrival_run():
    return SimpleNamespace(world=lambda: SimpleNamespace(monsters=(), player=None))


def test_battle_orders_on_the_arrival_when_due_or_its_age_not_known(monkeypatch) -> None:
    monkeypatch.setattr(cta, 'arrival_due', lambda run, world: True)  # not shown, under 60 s, or its cast not known
    monkeypatch.setattr(legs, 'hostiles', lambda world: [])
    buffs = Buffs(due=True)
    assert legs.orders_on_arrival(SimpleNamespace(buffs=buffs), arrival_run(), keys) == 'cast'  # type: ignore[arg-type]
    assert buffs.cast_with == ['due']
    near = Buffs(due=False)  # a hostile within 10: REBUFF's retreat first, the danger pricing's
    said = legs.orders_on_arrival(SimpleNamespace(buffs=near), arrival_run(), keys)  # type: ignore[arg-type]
    assert said.startswith('not cast now')
    assert near.cast_with == []


def test_no_cast_when_the_arrival_s_swap_cast_it_or_time_enough_is_left(monkeypatch) -> None:
    monkeypatch.setattr(cta, 'arrival_due', lambda run, world: False)
    buffs = Buffs(due=True)
    said = legs.orders_on_arrival(SimpleNamespace(buffs=buffs), arrival_run(), keys)  # type: ignore[arg-type]
    assert said.startswith('not due')
    assert buffs.cast_with == []


def test_the_arrival_rule_is_due_for_an_unknown_age_and_under_60_s(monkeypatch) -> None:
    # cta.py `arrival_due`, the rule the arrival's swap and `orders_on_arrival` cast by
    run = SimpleNamespace(clock=lambda: 1000.0, lasting={})
    monkeypatch.setattr(cta, 'orders_shown', lambda world: True)
    assert cta.arrival_due(run, None)  # type: ignore[arg-type]  # shown, its cast not known (a restart)
    run.lasting[cta.BATTLE_ORDERS] = 1000.0 - cta.ORDERS_LASTS + 50.0  # 50 s left
    assert cta.arrival_due(run, None)  # type: ignore[arg-type]
    run.lasting[cta.BATTLE_ORDERS] = 1000.0 - 30.0  # most of it left
    assert not cta.arrival_due(run, None)  # type: ignore[arg-type]
    monkeypatch.setattr(cta, 'orders_shown', lambda world: False)
    assert cta.arrival_due(run, None)  # type: ignore[arg-type]  # run out
