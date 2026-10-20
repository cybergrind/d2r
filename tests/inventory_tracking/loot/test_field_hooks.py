"""The field identify's hooks, one call each (loot/api.py, M4 of inventory_tracking/loot/design.md): the GOOD pickup
takes the classes with the loop on (macros/pickmode.py `kept`) and no game is kept or trip made for them
(`is_candidate`, macros/lootpolicy.py); the routine runs before the Town Portal (macros/portal.py `to_town`) and Save
and Exit (macros/loop.py `Loop.leave`); the visit's contract misses a tome under its reserve (macros/town.py); the
put-down is the loop's own (game/kept.py `PutDown.reject`)."""

from contextlib import nullcontext
from dataclasses import replace

import pytest

from inventory_tracking.game.kept import PutDown
from inventory_tracking.game.records import VALUABLE, Drop, Loot, Pack
from inventory_tracking.loot import api
from inventory_tracking.macros import loop as loop_module, portal
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.loop import Loop
from inventory_tracking.macros.lootpolicy import trip_for
from inventory_tracking.macros.pickmode import MONARCH, MOST, SURE, is_candidate, kept
from inventory_tracking.macros.town import Needs, contract


GAME = ('game-1', 7)
MAGIC_MONARCH = Drop(10, 100.0, 100.0, 'Magic Monarch', VALUABLE, (2, 3), False, 'shown', MONARCH, 4)
IST = Drop(11, 101.0, 100.0, 'Ist Rune', VALUABLE, (1, 1), True, 'rune', 640, 2)


@pytest.fixture
def looping(monkeypatch):
    monkeypatch.setattr(api.FIELD, 'looping', lambda: True)
    monkeypatch.setattr(api.FIELD, 'picked', {})
    return api.FIELD


def test_the_good_pickup_takes_a_magic_monarch_only_with_the_loop_on(looping, monkeypatch):
    look = Loot(drops=(MAGIC_MONARCH, IST), game=GAME)
    assert kept(look, SURE).drops == (MAGIC_MONARCH, IST)
    assert looping.class_of(MAGIC_MONARCH.unit_id, GAME[0]) == 'G6'
    assert looping.class_of(IST.unit_id, GAME[0]) is None  # a sure valuable: today's pickup, today's town path
    assert kept(look, MOST).drops == (MAGIC_MONARCH, IST)
    monkeypatch.setattr(api.FIELD, 'looping', lambda: False)
    assert kept(look, SURE).drops == (IST,)  # by hand: the GOOD pickup as before


def test_a_magic_monarch_holds_no_game_and_makes_no_trip(looping, monkeypatch):
    assert is_candidate(MAGIC_MONARCH)
    assert not trip_for(MAGIC_MONARCH, shown=True)
    assert not is_candidate(IST)
    monkeypatch.setattr(api.FIELD, 'looping', lambda: False)
    assert not is_candidate(MAGIC_MONARCH)  # as before by hand


def test_the_contract_misses_a_tome_under_its_reserve():
    assert 'identifies 4' in contract(Pack(identifies=4), frozenset(), Needs()).misses
    assert not any(miss.startswith('identifies') for miss in contract(Pack(identifies=5), frozenset(), Needs()).misses)
    assert not any(miss.startswith('identifies') for miss in contract(Pack(), frozenset(), Needs()).misses)


class Stopped(Abort):
    """The cast's own work, not made in these tests."""


def test_the_town_portal_makes_the_field_routine_first(monkeypatch):
    order: list[str] = []

    class Run:
        def field(self, when: str) -> None:
            order.append(f'field {when}')

        def lightly(self) -> nullcontext[None]:
            return nullcontext()

    def ready(run):
        order.append('cast')
        raise Stopped('no game in the test')

    monkeypatch.setattr(portal, 'ready_world', ready)
    with pytest.raises(Stopped):
        portal.to_town(Run(), lambda world, skills=None: {})  # pyrefly: ignore[bad-argument-type] # a stub run
    assert order == ['field Town Portal', 'cast']


@pytest.mark.parametrize(('abandon', 'expected'), [(False, ['field Save and Exit', 'leave']), (True, ['leave'])])
def test_save_and_exit_makes_the_field_routine_first_unless_the_game_is_given_up(monkeypatch, abandon, expected):
    order: list[str] = []

    class Run:
        def field(self, when: str) -> None:
            order.append(f'field {when}')

    monkeypatch.setattr(loop_module, 'leave_game', lambda run: order.append('leave'))
    found = Loop()
    found.abandon = abandon
    found.leave(Run(), 'game-1')  # pyrefly: ignore[bad-argument-type] # a stub run
    assert order == expected
    assert found.games == 1


def test_the_loops_own_put_down_is_said_as_its_own_and_never_picked_again(caplog):
    put_down = PutDown()
    put_down.see(Loot(game=GAME, carried=frozenset((10,))))
    put_down.reject(10, 'in the field: K8 worthless')
    caplog.set_level('INFO')
    lying = replace(MAGIC_MONARCH, x=200.0)
    assert put_down.see(Loot(drops=(lying,), game=GAME)).drops == ()
    assert "the loop's own field drop (in the field: K8 worthless)" in caplog.text
    assert 'the player put it down' not in caplog.text
    assert put_down.at(200.0, 100.0)
    fresh = Loot(drops=(lying,), game=('game-2', 7))
    assert put_down.see(fresh).drops == (lying,)  # another game: forgotten
