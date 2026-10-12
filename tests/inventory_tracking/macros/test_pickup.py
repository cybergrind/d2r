"""The pickup step on a scripted level: valuables, potions the belt wants, a drink to make room, else
what it was given to do instead (the runner: a seek step).

The character stands at world (5000, 5000) in the rooms of test_teleport.py, in Durance of Hate
Level 2 (101). The belt is sixteen cells, the first four the hotkey row; 606 is a Super Healing
Potion and 531 a Full Rejuvenation Potion.
"""

import math
from dataclasses import replace

import pytest

from inventory_tracking.levels.model import Level, Room
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.pickup import POTION_UNITS, Plan, choose, pick_up
from inventory_tracking.macros.world import GOLD, HEALING, REJUVENATION, VALUABLE, Drop, Loot, Teleport
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
    play.pick_above = 14.0  # the second aim: the first looks 24 pixels up
    with caplog.at_level('INFO'):
        pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ['Ist Rune']
    assert play.walks == []  # no click on bare ground: the character went nowhere else
    assert any('picked up Ist Rune' in r.message and '(0, -14) pixels' in r.message for r in caplog.records)


def test_the_aim_24_pixels_up_is_the_first_for_a_valuable_too(caplog):
    # Every log up to 2026-10-11: the first click took the item 101 times of 111 there, 87 of 130 at 14.
    play = game(RUNE)
    play.pick_above = 19.0  # the label under both aims
    with caplog.at_level('INFO'):
        pick_up(play.run(), LEVEL, keys, nothing)
    assert any('picked up Ist Rune' in r.message and '(0, -24) pixels' in r.message for r in caplog.records)


def test_a_click_that_walked_the_character_is_not_made_again_where_the_pointer_was_left(caplog):
    # The Tower, 16:53:14 on 2026-10-11: an Eth Rune under the pointer, the click ran the character 9
    # units to the ground behind the label, and the second click on the same spot 8 more.
    play = game(RUNE)
    play.slipped_picks = 1
    with caplog.at_level('INFO'):
        pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ['Ist Rune']
    # One walk from the click that slipped; a second only as the walk up to the rune itself.
    assert all(math.dist(walk, (RUNE.x, RUNE.y)) < 2.0 for walk in play.walks[1:])
    assert len(play.walks) <= 2


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
    play.pick_above = 14.0
    with caplog.at_level('INFO'):
        pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ['Ist Rune']
    assert any('still on the ground after the click (0, -24)' in r.message for r in caplog.records)
    assert any('picked up Ist Rune' in r.message and '(0, -14) pixels' in r.message for r in caplog.records)


def test_a_drop_no_click_takes_is_reported():
    play = game(RUNE)
    play.pick_above = 300.0
    with pytest.raises(Abort, match='no click picked up Ist Rune'):
        pick_up(play.run(), LEVEL, keys, nothing)


def test_a_potion_is_drunk_first_when_the_belt_is_full_and_the_life_is_low():
    play = game(HP_NEAR, life=500)
    pick_up(play.run(), LEVEL, keys, nothing)
    assert play.pressed() == ['1']
    assert play.picked == ['a healing potion']
    assert play.said[0] == 'Drinking (1) to make room for a healing potion'


def test_a_drink_the_game_did_not_take_is_pressed_again_and_then_given_up():
    # Frigid Highlands, 03:00:04 on 2026-10-11: the belt stayed full after the key and six clicks
    # on the potion took nothing.
    play = game(HP_NEAR, life=500)
    react, lost = play.keys.on_event, [1]
    play.keys.on_event = lambda event: lost.pop() if event == ('key', '1') and lost else react(event)
    pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ['a healing potion']

    play = game(HP_NEAR, life=500)
    react = play.keys.on_event
    play.keys.on_event = lambda event: None if event == ('key', '1') else react(event)
    with pytest.raises(Abort, match='the potion on 1 was not drunk'):
        pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == []


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


# --- a pile (host, 21:10 on 2026-10-10: a press took a rejuvenation nobody wanted between two healing potions) ---


def test_in_a_pile_the_potion_not_wanted_is_never_clicked(caplog):
    juv = Drop(52, HP_NEAR.x, HP_NEAR.y, 'a full rejuvenation potion', REJUVENATION)
    play = game(juv, HP_NEAR, belt=SHORT_HP)
    play.label_above[HP_NEAR.unit_id] = 44.0  # its label is stacked above the other's
    with caplog.at_level('INFO'):
        assert pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ['a healing potion']


def test_a_potion_not_wanted_is_not_clicked_blind_either():
    # No aim shows the healing potion at all: the press gives up before it takes the other one.
    juv = Drop(52, HP_NEAR.x, HP_NEAR.y, 'a full rejuvenation potion', REJUVENATION)
    play = game(juv, HP_NEAR, belt=SHORT_HP)
    play.label_above[HP_NEAR.unit_id] = 400.0
    with pytest.raises(Abort, match='no click picked up a healing potion'):
        pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == []


def test_another_potion_of_the_kind_wanted_under_the_pointer_serves_as_well():
    other = Drop(53, HP_NEAR.x, HP_NEAR.y, 'another healing potion', HEALING)
    play = game(HP_NEAR, other, belt=SHORT_HP)
    play.label_above[HP_NEAR.unit_id] = 400.0  # only the other one's label can be found
    play.belt_after = {1: FULL}
    assert pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ['another healing potion']


def test_one_press_picks_up_every_potion_the_belt_is_short_of():
    # user, 2026-10-10: two potions drunk, one press: both healing potions, not the rejuvenation between.
    second = Drop(54, 5004.0, 5005.0, 'a second healing potion', HEALING)
    play = game(HP_NEAR, JUV_NEAR, second, belt=SHORT_HP)
    play.belt_after = {2: FULL}  # the belt is full once two were picked up
    assert pick_up(play.run(), LEVEL, keys, nothing)
    assert sorted(play.picked) == ['a healing potion', 'a second healing potion']


def test_one_press_picks_up_one_valuable_when_the_next_is_a_walk_away():
    other = Drop(55, RUNE.x + 15.0, RUNE.y, 'Ber Rune', VALUABLE)
    play = game(RUNE, other)
    assert pick_up(play.run(), LEVEL, keys, nothing)
    assert len(play.picked) == 1


def test_one_press_picks_up_the_valuables_of_a_pile():
    # The Tower, 16:55:50 on 2026-10-11: three runes within 5 units took three presses.
    names = enumerate(('Tal', 'El'))
    others = [Drop(55 + n, RUNE.x + 2.0 * n, RUNE.y + 3.0, f'{name} Rune', VALUABLE) for n, name in names]
    play = game(RUNE, *others, HP_NEAR)
    assert pick_up(play.run(), LEVEL, keys, nothing)
    assert sorted(play.picked) == ['El Rune', 'Ist Rune', 'Tal Rune']


def test_the_pickup_step_wants_every_rune_and_the_essences_and_keys():
    # user, 2026-10-10 night. The HUD's marks keep their own, higher rune minimum.
    from inventory_tracking.config import APPRAISAL
    from inventory_tracking.macros.pickup import wanted

    found = wanted()
    assert found['rune_minimum'] == 'r01'
    assert APPRAISAL.rune_minimum != 'r01'
    assert {'Key of Terror', 'Festering Essence of Destruction'} <= set(found['materials'].values())


def test_the_pickup_step_wants_every_ring_jewel_and_amulet_though_the_marks_do_not_point_at_them():
    # user, 2026-10-10 night
    from inventory_tracking.config import APPRAISAL
    from inventory_tracking.loot.materials import material_classes
    from inventory_tracking.macros.pickup import wanted

    assert {'Ring', 'Jewel', 'Amulet'} <= set(wanted()['materials'].values())
    assert not {'Ring', 'Jewel', 'Amulet'} & set(material_classes(APPRAISAL.material_marks).values())


def test_the_pickup_step_wants_what_the_loot_filter_shows_the_smaller_bases_below_set_quality():
    # user, 2026-10-11
    from inventory_tracking.config import APPRAISAL
    from inventory_tracking.loot.shown import pickup_rules
    from inventory_tracking.macros.pickup import wanted

    assert APPRAISAL.pickup_shown_cells == 6
    assert wanted()['shown'] == pickup_rules(6) != ()


def test_a_drop_no_click_picks_up_is_given_up_after_three_aims_and_left_alone_for_a_while():
    # Worldstone Keep 3, 22:16 on 2026-10-10: 30 clicks in 21 s on a Large Charm that was under the
    # pointer every time, and nothing else was done meanwhile.
    from inventory_tracking.macros import pickup

    pickup.SHUNNED.clear()
    play = game(RUNE)
    play.deaf_picks = 999
    with pytest.raises(Abort, match='no click picked it up'):
        pick_up(play.run(), LEVEL, keys, nothing)
    assert 999 - play.deaf_picks == pickup.MISSED_AIMS * pickup.CLICKS
    asked = []
    assert not pick_up(play.run(), LEVEL, keys, lambda: asked.append(1))  # the next press does something else
    assert asked == [1]
    pickup.SHUNNED.clear()


def test_a_valuable_the_inventory_has_no_room_for_is_left_and_said_so():
    # user, 2026-10-10 night: with a full inventory an Ort Rune took none of 6 clicks, a Large Charm
    # none of 30. A Large Charm takes one cell across and two down.
    full = ('##########',) * 4
    one_cell = ('##########', '#####.####', '##########', '##########')
    charm = Drop(70, 5008.0, 5003.0, 'Large Charm', VALUABLE, (1, 2))
    assert choose(Loot((RUNE,), FULL, 1000, 1000, full), ORIGIN) is None
    assert choose(Loot((RUNE, charm), FULL, 1000, 1000, one_cell), ORIGIN) == Plan(RUNE)
    assert choose(Loot((charm,), FULL, 1000, 1000, one_cell), ORIGIN) is None
    assert choose(Loot((charm,), FULL, 1000, 1000, None), ORIGIN) == Plan(charm)  # unread: tried as before

    play = game(charm)
    play.loot = Loot((charm,), FULL, 1000, 1000, one_cell)
    # The press stops and says so; it does not go on to the seek step, which would leave the drop.
    with pytest.raises(Abort, match='inventory full: no room for Large Charm'):
        pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == []

    play = game(charm, HP_NEAR, belt=SHORT_HP)  # a potion the belt wants is still taken, and the room said
    play.loot = Loot((charm, HP_NEAR), SHORT_HP, 1000, 1000, one_cell)
    assert pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ['a healing potion']
    assert 'Inventory full: no room for Large Charm' in play.said


def test_a_potion_for_the_belt_is_still_taken_with_a_full_inventory():
    full = ('##########',) * 4
    assert choose(Loot((RUNE, HP_NEAR), SHORT_HP, 1000, 1000, full), ORIGIN) == Plan(HP_NEAR)


def test_a_far_drop_no_aim_shows_is_walked_up_to_before_any_aim_is_clicked_unseen():
    # Tower Cellar 4, 23:11 on 2026-10-10: a Grand Charm 16 away showed at none of the aims, and the
    # first click made anyway had a corpse under it.
    import math

    far = Drop(80, 5012.0, 5010.0, 'Grand Charm', VALUABLE, (1, 3))
    play = game(far)
    play.label_above[80] = 300  # its label is nowhere the aims look
    with pytest.raises(Abort):
        pick_up(play.run(), LEVEL, keys, nothing)
    assert math.dist(play.walks[0], (far.x, far.y)) < 1.5  # the first click: the walk up to it


def test_an_aim_is_taken_only_once_the_character_stands():
    # Black Marsh, 01:13 on 2026-10-11: a pickup begun under a walk of attack mode's sent the character
    # 18 units past a shard and back, 6 s for an item 14 away.
    from dataclasses import replace

    from inventory_tracking.macros.pickup import STAND_SECONDS, standing

    play = Game(world(area=101))
    play.world = replace(play.world, player=replace(play.world.player, mode=3))
    stop = lambda: setattr(play, 'world', replace(play.world, player=replace(play.world.player, mode=1)))  # noqa: E731
    play.arrivals.append((0.4, stop))
    run = play.run()
    assert standing(run).mode == 1
    assert 0.4 <= play.clock.now < 0.5
    play.world = replace(play.world, player=replace(play.world.player, mode=3))
    began = play.clock.now
    assert standing(run).mode == 3  # it never stood: the aim is taken anyway after STAND_SECONDS
    assert play.clock.now - began >= STAND_SECONDS


# --- gold: gone to, never clicked (user, 2026-10-11: "pickup gold >5k", "blade warp to location would be enough") ---

PILE = Drop(60, 5015.0, 5000.0, '7200 gold', GOLD, (0, 0))


def test_gold_comes_after_a_valuable_and_before_a_potion_and_only_within_a_jump():
    far = Drop(61, 5040.0, 5000.0, '9000 gold', GOLD, (0, 0))
    short = Loot((PILE, far, JUV_NEAR), (HP, HP, JUV, None) * 4, 1000, 1000)
    assert choose(short, ORIGIN) == Plan(PILE)
    assert choose(Loot((PILE, RUNE)), ORIGIN) == Plan(RUNE)
    assert choose(Loot((far,)), ORIGIN) is None


def test_gold_is_taken_with_a_full_inventory():
    assert choose(Loot((PILE,), room=('#' * 10,) * 4), ORIGIN) == Plan(PILE)


def test_a_gold_pile_is_jumped_onto_by_blade_warp_and_not_clicked():
    play = game(PILE)
    assert pick_up(play.run(), LEVEL, keys, nothing)
    assert play.pressed() == ['w']
    assert play.warps == [pytest.approx((5015.0, 5000.0), abs=1.5)]
    assert play.picked == ['7200 gold']
    assert not any(event[0] == 'click' for event in play.keys.events)
    assert play.said[-1] == '7200 gold: picked up'


def test_a_gold_pile_a_few_steps_away_is_clicked():
    play = game(Drop(60, 5004.0, 5000.0, '7200 gold', GOLD, (0, 0)))
    assert pick_up(play.run(), LEVEL, keys, nothing)
    assert play.pressed() == []
    assert play.picked == ['7200 gold']


def test_gold_the_jump_did_not_take_is_clicked_like_any_item(caplog):
    # Halls of Vaught, 13:30:30 on 2026-10-11: the jump landed 0.7 from where the pile was read to be,
    # and it stayed on the ground; a click on that ground took nothing either.
    play = game(PILE)
    play.gold_radius = 0.0
    with caplog.at_level('INFO'):
        assert pick_up(play.run(), LEVEL, keys, nothing)
    assert play.pressed() == ['w']
    assert play.picked == ['7200 gold']
    assert any('picked up 7200 gold' in r.message for r in caplog.records)


def test_a_jump_that_does_not_land_is_followed_by_a_click_on_the_gold():
    play = game(PILE)
    play.warp_lands = False
    assert pick_up(play.run(), LEVEL, keys, nothing)
    assert play.pressed() == ['w']
    assert play.picked == ['7200 gold']


def test_potions_the_belt_has_no_place_for_are_named_when_a_press_takes_nothing():
    # Halls of Vaught, 13:47:09 on 2026-10-11: three super healing potions, the belt short of one
    # rejuvenation only, the life whole; to the player the press had failed to pick them up.
    play = game(HP_NEAR, belt=(HP, HP, JUV, None) + (HP, HP, JUV, JUV) * 3)
    said = []
    assert not pick_up(play.run(), LEVEL, keys, lambda: said.extend(play.said))
    assert said[-1] == 'Not picked up: the belt has no place for a healing potion'
    assert play.picked == []


def test_an_aim_is_taken_only_once_the_cast_under_way_is_over():
    # 14:51 to 14:54 on 2026-10-11: the sweep's own pickups began under the strike's cast, and the first
    # click on a Ring and on two potions was swallowed, 0.65 s each before the miss showed.
    from dataclasses import replace

    from inventory_tracking.macros.pickup import standing

    play = Game(world(area=101))
    play.world = replace(play.world, player=replace(play.world.player, mode=10))
    over = lambda: setattr(play, 'world', replace(play.world, player=replace(play.world.player, mode=1)))  # noqa: E731
    play.arrivals.append((0.3, over))
    assert standing(play.run()).mode == 1
    assert 0.3 <= play.clock.now < 0.4


def test_in_a_big_pile_the_label_is_looked_for_further_up_and_to_the_sides(caplog):
    # Arcane Sanctuary, 16:03:45 on 2026-10-11: a Flawless Diamond among 12 drops showed at none of the 16
    # aims, four presses running; the clicks made unseen had a monster under them.
    from inventory_tracking.macros.pickup import ITEM_AIMS, PILE_AIMS, PILE_MORE, pile_aims

    more = pile_aims(11)
    assert (0, -174) in more
    assert (0, -184) not in more
    assert (-40, -34) in more
    assert not set(more) & {*ITEM_AIMS, *PILE_AIMS}
    assert len(more) <= PILE_MORE

    diamond = Drop(70, 5005.0, 5003.0, 'Flawless Diamond', VALUABLE)
    crowd = [Drop(80 + i, 5004.0 + i % 3, 5002.0 + i // 3, f'potion {i}', HEALING) for i in range(6)]
    play = game(diamond, *crowd)
    play.label_above[70] = 104  # its label, pushed up by the pile
    with caplog.at_level('INFO'):
        assert pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ['Flawless Diamond']
    assert any('(0, -104) pixels' in r.message for r in caplog.records)


def test_a_drop_no_click_took_is_left_for_the_next_press_which_takes_what_lies_beside_it():
    # The same pile: four presses went to the diamond while a Ring and a rune lay beside it.
    diamond = Drop(70, 5003.0, 5002.0, 'Flawless Diamond', VALUABLE)
    ring = Drop(71, 5009.0, 5006.0, 'Ring', VALUABLE)
    play = game(diamond, ring)
    play.label_above[70] = 400  # nowhere an aim looks
    with pytest.raises(Abort, match='no click picked up Flawless Diamond'):
        pick_up(play.run(), LEVEL, keys, nothing)
    assert pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ['Ring']


def test_every_aim_of_a_pickup_is_logged_with_what_was_under_it(caplog):
    # user, 2026-10-11: "log all failed attempts": the aims only looked at left no trace.
    play = game(RUNE)
    play.pick_above = 14.0
    run = play.run()
    run.hover_note = lambda: 'flag 0x1'
    with caplog.at_level('INFO'):
        pick_up(run, LEVEL, keys, nothing)
    line = next(r.message for r in caplog.records if 'aims for Ist Rune' in r.message)
    seen = '; '.join(f'(0, {down}) (0, 0) [flag 0x1]' for down in (-24, -54, -34, -44))
    assert line.endswith(seen + '; (0, -14) wanted [flag 0x1] clicked')


def test_the_aims_are_logged_when_the_pickup_fails_too(caplog):
    play = game(RUNE)
    play.pick_above = 300.0
    with caplog.at_level('INFO'), pytest.raises(Abort):
        pick_up(play.run(), LEVEL, keys, nothing)
    line = next(r.message for r in caplog.records if 'aims for Ist Rune' in r.message)
    assert line.count('blind') == 7


def test_a_teleport_step_stops_for_a_valuable_in_reach_and_for_gold_but_not_for_a_potion():
    # Tower Cellar, 17:35:18 on 2026-10-11: teleport steps passed 6.5 from a Ring and left the level.
    from inventory_tracking.macros.pickup import STOP_TRIES, STOP_UNITS, STOPPED, worth_a_stop

    STOPPED.clear()
    ring = Drop(70, 5029.0, 5004.0, 'Ring', VALUABLE)
    assert worth_a_stop(game(ring, HP_NEAR, belt=SHORT_HP).run()) is ring
    assert worth_a_stop(game(HP_NEAR, belt=SHORT_HP).run()) is None
    far = Drop(71, 5000.0 + STOP_UNITS + 5, 5000.0, 'Ring', VALUABLE)
    assert worth_a_stop(game(far).run()) is None
    gold = Drop(72, 5010.0, 5000.0, '6000 gold', GOLD)
    assert worth_a_stop(game(gold).run()) is gold
    # One no click takes does not hold the step: after STOP_TRIES steps for it the step hops.
    STOPPED.clear()
    play = game(ring)
    assert [worth_a_stop(play.run()) is ring for _ in range(STOP_TRIES + 1)] == [True] * STOP_TRIES + [False]
    STOPPED.clear()


def test_a_valuable_with_no_room_for_it_is_not_clicked_in_place_of_the_one_wanted():
    # Tower Cellar 5, 19:03:28 on 2026-10-11: a Rare Horned Helm with no room for it lay beside an Ith
    # Rune and took four clicks, 3.5 s.
    helm = Drop(81, RUNE.x, RUNE.y, 'Rare Horned Helm', VALUABLE, (2, 2))
    play = game(RUNE, helm)
    play.loot = replace(play.loot, room=('#.##', '####'))
    play.label_above[RUNE.unit_id] = 44.0  # the helm's label lies where the rune's would
    pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ['Ist Rune']  # the scripted game would hand the helm over to a click on it


def test_the_label_of_a_pile_30_pixels_higher_is_the_second_place_looked_at(caplog):
    # 71 pickups, 17:20 to 19:11 on 2026-10-11: the label was 24 pixels up 62 times and 54 up 5 times.
    play = game(RUNE)
    play.pick_above = 54.0
    with caplog.at_level('INFO'):
        pick_up(play.run(), LEVEL, keys, nothing)
    line = next(r.message for r in caplog.records if 'aims for Ist Rune' in r.message)
    assert line.endswith('(0, -24) (0, 0); (0, -54) wanted clicked')
    assert play.walks == []  # seen from where the character stood: no walk up to it first


def test_a_label_44_pixels_up_is_seen_from_afar_without_a_walk_past_the_item(caplog):
    # Tower Cellar 5, 19:38:29 on 2026-10-11: a Sol Rune's label at 44 pixels up was the fifteenth aim.
    play = game(RUNE)
    play.pick_above = 44.0
    with caplog.at_level('INFO'):
        pick_up(play.run(), LEVEL, keys, nothing)
    line = next(r.message for r in caplog.records if 'aims for Ist Rune' in r.message)
    assert line.endswith('(0, -34) (0, 0); (0, -44) wanted clicked')
    assert play.walks == []


def test_the_clicks_stop_when_the_character_is_dead():
    # Tower Cellar 5, 22:51:00 on 2026-10-11: the pickup clicked on for 4.7 s over the body.
    play = Game(world())
    play.loot = replace(play.loot, drops=(Drop(60, 5004.0, 5002.0, 'Ist Rune', VALUABLE, (1, 1)),))
    play.deaf_picks = 100

    def dies():
        play.world = replace(play.world, player=replace(play.world.player, mode=17))

    play.arrivals.append((0.3, dies))
    with pytest.raises(Abort, match='the character is dead'):
        pick_up(play.run(), LEVEL, keys, nothing)


# --- a full inventory: what stops the press and what only warns (user, 2026-10-12) ---------------------
# Drifter Cavern, 20:00 that day: the inventory full, a Superior Old Book on the ground, 13 hostiles 38
# away, and 37 presses in a row ended "inventory full: no room for Superior Old Book" (user: "KP_1 stops
# moving the character from time to time at all and does nothing"; "we should give an active warning that
# must be visible to the user, but allow moving when the item isn't very valuable").
FULL_ROOM = ('##########',) * 4


def warned_by(run) -> list:
    warned = []
    run.warn = warned.append
    return warned


def test_gear_the_filter_shows_with_no_room_for_it_is_warned_of_and_the_press_goes_on():
    book = Drop(71, 5008.0, 5003.0, 'Superior Old Book', VALUABLE, (2, 2), prized=False)
    play = game(book)
    play.loot = Loot((book,), FULL, 1000, 1000, FULL_ROOM)
    went_on = []
    run = play.run()
    warned = warned_by(run)
    assert not pick_up(run, LEVEL, keys, lambda: went_on.append(True))
    assert went_on == [True]  # the seek step, or the sweep: the press is not a dead key
    assert warned == ['Inventory full: Superior Old Book left on the ground']
    assert play.picked == []


def test_a_prized_drop_with_no_room_for_it_still_stops_the_press_and_is_warned_of():
    rune = Drop(72, 5008.0, 5003.0, 'Ist Rune', VALUABLE, (1, 1))
    book = Drop(71, 5010.0, 5003.0, 'Superior Old Book', VALUABLE, (2, 2), prized=False)
    play = game(rune, book)
    play.loot = Loot((rune, book), FULL, 1000, 1000, FULL_ROOM)
    run = play.run()
    warned = warned_by(run)
    with pytest.raises(Abort, match=r'inventory full: no room for Ist Rune$'):
        pick_up(run, LEVEL, keys, nothing)
    assert warned == ['Inventory full: Ist Rune, Superior Old Book left on the ground']


def test_the_warning_is_taken_back_when_nothing_is_left_for_want_of_room():
    play = game()
    play.loot = Loot((), FULL, 1000, 1000, FULL_ROOM)
    run = play.run()
    warned = warned_by(run)
    pick_up(run, LEVEL, keys, lambda: None)
    assert warned == [None]
