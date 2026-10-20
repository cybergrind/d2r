"""Buff mode's pure rules (macros/buffmode.py): the active modes' cycle, what holds a cast back, the hand's rest and the
weapon swap's quiet."""

from dataclasses import replace

from inventory_tracking.builds.warlock.skills import HEX_PURGE
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.buffmode import (
    REST,
    SWAP_CLEAR,
    Rest,
    castable,
    held_back,
    next_active,
    swaps_weapons,
)
from inventory_tracking.macros.build import Buff, whenever
from inventory_tracking.macros.cta import ROWS as CTA_ROWS
from inventory_tracking.macros.running.base import ATTACK, BUFF
from tests.inventory_tracking.macros.fakes import player, world


LOWER_KURAST = 79


def test_a_double_press_cycles_attack_and_buff_mode():
    assert next_active(ATTACK) == BUFF
    assert next_active(BUFF) == ATTACK


def test_no_buff_is_cast_in_town_with_a_panel_open_by_the_pad_or_behind_another_window():
    out = world(LOWER_KURAST, player=player(LOWER_KURAST))
    assert held_back(out, pad=False, focused=True) is None
    assert held_back(world(109), pad=False, focused=True) == 'in town'  # Harrogath
    assert held_back(replace(out, open_panels=('inventory',)), pad=False, focused=True) == 'inventory open'
    assert held_back(out, pad=True, focused=True) == 'controller mode'
    assert held_back(out, pad=False, focused=False) == 'the game window is not in front'
    assert held_back(replace(out, in_game=False), pad=False, focused=True) == 'not in a game'


def test_the_hand_at_work_holds_the_cast_until_it_has_rested():
    rest = Rest()
    rest.look(0.0, pointer=(100, 100), pressed=False, mode=1)
    assert rest.rested(0.0)  # never seen at work
    rest.look(1.0, pointer=(140, 100), pressed=False, mode=1)  # the player moved the mouse
    assert not rest.rested(1.0 + REST - 0.1)
    assert rest.rested(1.0 + REST)
    rest.look(5.0, pointer=(140, 100), pressed=True, mode=1)  # a key or a button held
    assert not rest.rested(5.5)
    rest.look(10.0, pointer=(140, 100), pressed=False, mode=3)  # the character runs (RUN_MODES)
    assert not rest.rested(10.5)
    rest.look(20.0, pointer=(141, 101), pressed=False, mode=1)  # a hand's tremor is no move (POINTER_DRIFT)
    assert rest.rested(20.0)


def test_the_modes_own_cast_is_not_the_hand():
    rest = Rest()
    rest.cast(0.0, (500, 500))  # a cast of the mode's: its pointer and its cast mode are its own
    rest.look(0.2, pointer=(500, 500), pressed=False, mode=7)
    assert rest.rested(0.2)
    rest.look(3.0, pointer=(500, 500), pressed=False, mode=7)  # a cast long after: the player's
    assert not rest.rested(3.0)


def test_a_weapon_swap_waits_for_no_hostile_near():
    [cta] = CTA_ROWS
    purge = Buff(HEX_PURGE, 'upkeep', whenever)
    consume = Buff(HEX_PURGE, 'upkeep', whenever, needs='prebuff')
    assert swaps_weapons(cta)
    assert swaps_weapons(consume)
    assert not swaps_weapons(purge)
    out = world(LOWER_KURAST, player=player(LOWER_KURAST))
    near = Monster(9, 100, 1, 5000.0 + SWAP_CLEAR - 1, 5000.0, 0)
    far = replace(near, x=5000.0 + SWAP_CLEAR + 1)
    assert not castable(cta, out, [near])
    assert castable(cta, out, [far])
    assert castable(purge, out, [near])  # a key cast swaps nothing
