"""The pickup step on a scripted level: valuables, potions the belt wants, a drink to make room, else
what it was given to do instead (the runner: a seek step).

The character stands at world (5000, 5000) in the rooms of test_teleport.py, in Durance of Hate
Level 2 (101). The belt is sixteen cells, the first four the hotkey row; 606 is a Super Healing
Potion and 531 a Full Rejuvenation Potion.
"""

import pytest

from inventory_tracking.levels.model import Level, Room
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.pickup import POTION_UNITS, Plan, choose, pick_up
from inventory_tracking.macros.world import HEALING, REJUVENATION, VALUABLE, Drop, Loot, Teleport
from tests.inventory_tracking.macros.fakes import KEYS, SLOTS, Game, world


HERE = Room(1, 996, 996, 8, 8)
EAST = tuple(Room(2 + i, 1004 + 8 * i, 996, 8, 8) for i in range(4))
LEVEL = Level(101, (HERE, *EAST), ())
HP, JUV = 606, 531
FULL = (HP, HP, JUV, JUV) * 4
SHORT_HP = (HP, HP, JUV, JUV, HP, None, JUV, JUV, *(None, None, JUV, JUV) * 2)
RUNE = Drop(50, 5008.0, 5003.0, 'Ist Rune', VALUABLE)
HP_NEAR = Drop(51, 5006.0, 4996.0, 'a healing potion', HEALING)
JUV_NEAR = Drop(52, 4995.0, 5004.0, 'a full rejuvenation potion', REJUVENATION)
ORIGIN = (5000.0, 5000.0)


def keys(_world, skills):
    return {skill: KEYS[skill] for skill in skills}


def game(*drops, belt=FULL, life=1000, max_life=1000):
    play = Game(world(area=101, slots=SLOTS))
    play.staff = Teleport(10, 20, True)
    play.loot = Loot(tuple(drops), belt, life, max_life)
    return play


def nothing():
    raise AssertionError('there was something to pick up')


# --- what a press picks ---


def test_a_valuable_comes_before_any_potion_and_the_nearest_valuable_first():
    far = Drop(60, 5060.0, 5000.0, 'Jah Rune', VALUABLE)
    assert choose(Loot((HP_NEAR, far, RUNE), SHORT_HP, 500, 1000), ORIGIN) == Plan(RUNE)


def test_a_potion_is_taken_only_when_the_belt_is_missing_its_kind():
    assert choose(Loot((HP_NEAR, JUV_NEAR), SHORT_HP, 1000, 1000), ORIGIN) == Plan(HP_NEAR)
    assert choose(Loot((JUV_NEAR,), SHORT_HP, 1000, 1000), ORIGIN) is None
    assert choose(Loot((HP_NEAR, JUV_NEAR), FULL, 1000, 1000), ORIGIN) is None


def test_nobody_walks_far_for_a_potion():
    far = Drop(61, 5000.0 + POTION_UNITS + 1, 5000.0, 'a healing potion', HEALING)
    assert choose(Loot((far,), SHORT_HP, 400, 1000), ORIGIN) is None


def test_with_a_full_belt_and_life_missing_one_is_drunk_to_make_room_for_the_one_on_the_ground():
    assert choose(Loot((HP_NEAR,), FULL, 600, 1000), ORIGIN) == Plan(HP_NEAR, '1')  # the first healing column
    assert choose(Loot((JUV_NEAR,), FULL, 600, 1000), ORIGIN) == Plan(JUV_NEAR, '3')
    assert choose(Loot((HP_NEAR,), FULL, 800, 1000), ORIGIN) is None  # not hurt enough to drink
    assert choose(Loot((HP_NEAR,), FULL, 0, 0), ORIGIN) is None  # the life unreadable


# --- the press ---


def test_a_valuable_in_view_is_clicked_and_leaves_the_ground(caplog):
    play = game(RUNE, HP_NEAR)
    with caplog.at_level('INFO'):
        assert pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ['Ist Rune']
    assert play.pressed() == []  # walked: no teleport
    assert play.said[-1] == 'Ist Rune: picked up'
    assert any('picked up Ist Rune' in r.message and '(0, -14) pixels' in r.message for r in caplog.records)


def test_a_valuable_far_off_is_hopped_toward_and_then_clicked():
    far = Drop(60, 5090.0, 5000.0, 'Jah Rune', VALUABLE)
    play = game(far)
    pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ['Jah Rune']
    assert set(play.pressed()) == {'t'}
    assert len(play.pressed()) >= 2


def test_an_aim_without_the_item_under_it_is_not_clicked_and_the_next_one_is(caplog):
    play = game(RUNE)
    play.pick_above = 24.0
    with caplog.at_level('INFO'):
        pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ['Ist Rune']
    assert play.walks == []  # no click on bare ground: the character went nowhere else
    assert any('picked up Ist Rune' in r.message and '(0, -24) pixels' in r.message for r in caplog.records)


def test_a_click_the_game_takes_nothing_from_is_made_again_on_the_same_aim(caplog):
    # Host, 18:54 on 2026-10-10: the item under the pointer, a click, and the character neither walked
    # nor picked it up (attack mode's last cast was ending).
    play = game(RUNE)
    play.deaf_picks = 1
    with caplog.at_level('INFO'):
        pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ['Ist Rune']
    assert sum('still on the ground after the click (0, -14)' in r.message for r in caplog.records) == 1
    assert any('picked up Ist Rune' in r.message and '(0, -14) pixels' in r.message for r in caplog.records)


def test_without_the_hover_record_every_aim_is_clicked_in_turn(caplog):
    play = game(RUNE)
    play.hover_known = False
    play.pick_above = 24.0
    with caplog.at_level('INFO'):
        pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ['Ist Rune']
    assert any('still on the ground after the click (0, -14)' in r.message for r in caplog.records)
    assert any('picked up Ist Rune' in r.message and '(0, -24) pixels' in r.message for r in caplog.records)


def test_a_drop_no_click_takes_is_reported():
    play = game(RUNE)
    play.pick_above = 80.0
    with pytest.raises(Abort, match='no click picked up Ist Rune'):
        pick_up(play.run(), LEVEL, keys, nothing)


def test_a_potion_is_drunk_first_when_the_belt_is_full_and_the_life_is_low():
    play = game(HP_NEAR, life=500)
    pick_up(play.run(), LEVEL, keys, nothing)
    assert play.pressed() == ['1']
    assert play.picked == ['a healing potion']
    assert play.said[0] == 'Drinking (1) to make room for a healing potion'


def test_with_nothing_to_pick_up_the_press_does_what_it_was_given_instead():
    play = game(JUV_NEAR)  # the belt is full and the life is too
    done = []
    assert pick_up(play.run(), LEVEL, keys, lambda: done.append('seek')) is False
    assert play.picked == []
    assert done == ['seek']


def test_a_far_valuable_without_a_level_map_stops_with_the_distance():
    play = game(Drop(60, 5090.0, 5000.0, 'Jah Rune', VALUABLE))
    with pytest.raises(Abort, match='Jah Rune is 90 away and there is no level map to hop by'):
        pick_up(play.run(), None, keys, nothing)
