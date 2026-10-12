"""The belt key pressed beside the fight (macros/drinking.py): what is kept between looks, and what stops a key."""

from dataclasses import replace

import pytest

from inventory_tracking.combat.survival import DrinkSettings
from inventory_tracking.macros.actuator import Cancelled
from inventory_tracking.macros.drinking import EVERY, Drinker, key_of, on_belt
from inventory_tracking.macros.world import HEALING, Drop, Loot
from inventory_tracking.models import PotionType
from tests.inventory_tracking.macros.fakes import SLOTS, Game, world


HP, JUV = 606, 531
FULL = (HP, HP, JUV, JUV) * 4
HERE = (5000.0, 5000.0)


def game(life: int, belt=FULL, drops=()) -> Game:
    play = Game(world(area=101, slots=SLOTS))
    play.loot = Loot(tuple(drops), belt, life, 1000)
    return play


def looks(play: Game, drinker: Drinker, *lives: int) -> list[PotionType | None]:
    """A look at each life, EVERY apart; the potion each drank."""
    run, found = play.run(), []
    for life in lives:
        play.loot = replace(play.loot, life=life)
        found.append(drinker.look(run, HERE))
        play.clock.now += EVERY
    return found


def test_the_belt_is_counted_by_kind_and_a_kinds_key_is_its_hotkey_cells():
    belt = (None, HP, JUV, JUV, HP, HP, JUV, None, *(None,) * 8)
    assert on_belt(Loot(belt=belt)) == {PotionType.HEALING: 3, PotionType.REJUVENATION: 3}
    assert key_of(Loot(belt=belt), PotionType.HEALING) == '2'
    assert key_of(Loot(belt=belt), PotionType.REJUVENATION) == '3'
    assert key_of(Loot(belt=(None, None, JUV, JUV) * 4), PotionType.HEALING) is None


def test_life_lost_under_the_mark_presses_the_healing_key_once_and_not_again_within_its_time():
    play = game(1000)
    drinker = Drinker()
    assert looks(play, drinker, 1000, 850, 850, 840) == [None, PotionType.HEALING, None, None]
    assert play.pressed() == ['1']
    assert play.said == ['Healing potion']


def test_two_looks_closer_than_the_pace_are_one():
    play = game(1000)
    drinker, run = Drinker(), play.run()
    drinker.look(run, HERE)
    play.loot = replace(play.loot, life=600)
    assert drinker.look(run, HERE) is None  # the same instant: not looked at
    play.clock.now += EVERY
    assert drinker.look(run, HERE) == PotionType.HEALING


def test_a_potion_gone_from_the_belt_was_drunk_by_someone_and_counts():
    play = game(1000)
    drinker = Drinker()
    looks(play, drinker, 1000, 900)
    play.loot = replace(play.loot, belt=(None, HP, JUV, JUV, *FULL[4:]))  # `make osd`, or the player
    assert looks(play, drinker, 850, 840) == [None, None]
    assert play.pressed() == []


def test_a_rejuvenation_when_the_life_is_running_out():
    play = game(1000)
    assert looks(play, Drinker(), 1000, 700, 450)[-1] == PotionType.REJUVENATION
    assert play.pressed()[-1] == '3'


def test_an_unread_life_and_marks_turned_off_drink_nothing():
    play = game(0)
    assert looks(play, Drinker(), 0, 0) == [None, None]
    play = game(1000)
    assert looks(play, Drinker(DrinkSettings(enabled=False)), 1000, 500) == [None, None]
    assert play.pressed() == []


def test_a_key_of_the_players_held_stops_the_drink_and_not_the_mode():
    play = game(1000)
    drinker = Drinker()
    looks(play, drinker, 1000)
    play.keys.press(play.keys.keycodes([b'x'])[0])  # the player's key, down
    assert looks(play, drinker, 800) == [None]
    assert play.pressed() == []


def test_nothing_is_drunk_under_shift_which_would_give_the_potion_to_the_mercenary():
    play = game(1000)
    drinker = Drinker()
    looks(play, drinker, 1000)
    play.keys.press(play.keys.keycodes([b'Shift_L'])[0])
    assert looks(play, drinker, 800) == [None]


def test_a_run_asked_to_stop_is_not_swallowed():
    play = game(1000)
    drinker, run = Drinker(), play.run()
    drinker.look(run, HERE)
    play.clock.now += EVERY
    play.loot = replace(play.loot, life=800)
    run.actuator.cancelled = type('Set', (), {'is_set': staticmethod(lambda: True)})()
    with pytest.raises(Cancelled):
        drinker.look(run, HERE)


def test_the_last_potions_are_drunk_when_more_lie_near():
    few = (HP, HP, JUV, JUV, *(None, None, JUV, JUV) * 3)
    play = game(1000, belt=few)
    assert looks(play, Drinker(), 1000, 850) == [None, None]
    near = Drop(51, 5006.0, 4996.0, 'a healing potion', HEALING)
    play = game(1000, belt=few, drops=(near,))
    assert looks(play, Drinker(), 1000, 850) == [None, PotionType.HEALING]
