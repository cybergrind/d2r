"""The pickup step on a scripted level: valuables, potions the belt wants, a drink to make room, else
what it was given to do instead (the runner: a seek step).

The character stands at world (5000, 5000) in the rooms of test_teleport.py, in Durance of Hate
Level 2 (101). The belt is sixteen cells, the first four the hotkey row; 606 is a Super Healing
Potion and 531 a Full Rejuvenation Potion.
"""

import math
from dataclasses import replace

import pytest

from inventory_tracking.config import BeltConfig
from inventory_tracking.game.kept import BeltKept
from inventory_tracking.game.records import (
    GOLD,
    HEALING,
    REJUVENATION,
    VALUABLE,
    Drop,
    Loot,
    Player,
    Teleport,
    World,
)
from inventory_tracking.levels.model import Level, Room
from inventory_tracking.macros import pickup
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.pickup import POTION_UNITS, Plan, choose, pick_up
from inventory_tracking.models import PotionType
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


def me(seen: World) -> Player:
    """The character of a world these tests always have one in."""
    assert seen.player is not None
    return seen.player


def stood(player: Player | None) -> Player:
    """The character `standing` gave back, which the test expects it to have read."""
    assert player is not None
    return player


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


# Chaos Sanctuary, 21:50:22.3 on 2026-10-13 (rca/2026-10-13/potions-findings.md M2, take
# 20261013T184953Z-108): the drinkers emptied the healing columns 3-4, the belt read alone wanted no
# healing, and the level run warped on past two super healing potions 3.6 and 7.3 away.
CS_GAME = ('cs-2', 1770193399)
CS_ENTRY = (531, 531, 606, 606, 531, 531, 606, 606, 531, 531, None, 606, None, None, None, None)
CS_DRY = (531, 531, None, None, 531, 531, None, None, 531, 531, None, None, 531, None, None, None)
CS_HERE = (7790.8, 5545.86)
CS_NEAR = Drop(1051927826, 7793.0, 5543.0, 'a super healing potion', HEALING)
CS_FURTHER = Drop(1825735822, 7798.0, 5545.0, 'a super healing potion', HEALING)


@pytest.fixture
def learned(monkeypatch):
    """No belt layout configured: an empty column's kind is learned from the game (tracking/belt.py `remember`),
    the rule until the player set the layout (2026-10-13: "yes, use this layout")."""
    monkeypatch.setattr(pickup, 'BELT', BeltConfig(layout=None))


def kept_belt(*belts, game=CS_GAME) -> BeltKept:
    kept = BeltKept()
    for belt in belts:
        kept.see(Loot(belt=belt, game=game))
    return kept


def test_with_its_healing_columns_drunk_dry_the_belt_still_wants_a_healing_potion(learned):
    loot = kept_belt(CS_ENTRY).see(Loot((CS_FURTHER, CS_NEAR), CS_DRY, 1807, 1818, game=CS_GAME))
    assert loot.columns is not None
    assert choose(replace(loot, columns=None), CS_HERE) is None  # as it ran
    assert choose(loot, CS_HERE) == Plan(CS_NEAR)


def test_a_loot_of_no_known_game_is_passed_as_read_and_the_belt_kept_as_it_was(learned):
    kept = kept_belt(CS_ENTRY)
    before = kept.columns
    unread = Loot((CS_NEAR,), CS_DRY)
    assert kept.see(unread) is unread
    assert kept.columns is before
    # Another game: what the columns held in the last one is forgotten.
    assert choose(kept.see(Loot((CS_NEAR,), CS_DRY, 1807, 1818, game=('cs-3', 7))), CS_HERE) is None


def test_an_unread_belt_is_unknown_not_short_no_potion_is_taken_or_drunk_for_it(learned):
    # A belt item unread leaves its cell out (game/memory.py `belt_cells`; the player, 2026-10-19): the dry
    # columns may be the unread cells, so no refill starts from them and the columns learn nothing.
    kept = kept_belt(CS_ENTRY)
    before = kept.columns
    unread = Loot((CS_FURTHER, CS_NEAR), CS_DRY, 1807, 1818, game=CS_GAME, belt_read=False)
    assert kept.see(unread) is unread
    assert kept.columns is before
    assert choose(replace(unread, columns=before), CS_HERE) is None
    assert choose(replace(unread, columns=before, belt_read=True), CS_HERE) == Plan(CS_NEAR)  # read: it is short
    hurt = Loot((HP_NEAR,), FULL, 600, 1000, belt_read=False)
    assert choose(hurt, ORIGIN) is None  # no drink to make room either
    assert choose(replace(hurt, belt_read=True), ORIGIN) == Plan(HP_NEAR, '1')


def test_by_the_default_layout_a_new_games_dry_healing_columns_want_a_healing_potion():
    # The player's layout (2026-10-13): columns 3-4 are healing whatever this game has seen of them; the belt
    # carries over between games, the learned kinds do not.
    assert pickup.BELT.layout == (PotionType.REJUVENATION,) * 2 + (PotionType.HEALING,) * 2
    fresh = BeltKept().see(Loot((CS_NEAR,), CS_DRY, 1807, 1818, game=('cs-3', 7)))
    assert fresh.columns is not None
    assert fresh.columns.kinds[2:] == (None, None)  # never seen holding one this game
    assert choose(fresh, CS_HERE) == Plan(CS_NEAR)
    assert choose(replace(fresh, columns=None), CS_HERE) == Plan(CS_NEAR)


def test_the_configured_belt_layout_wins_over_what_the_columns_held(monkeypatch):
    loot = kept_belt(CS_ENTRY).see(Loot((CS_NEAR,), CS_DRY, 1807, 1818, game=CS_GAME))
    every = (PotionType.REJUVENATION,) * 4
    monkeypatch.setattr(pickup, 'BELT', BeltConfig(layout=every))
    assert choose(loot, CS_HERE) is None


# --- the press ---


def test_a_potion_is_left_on_the_ground_while_monsters_are_near_it_or_the_character_and_a_valuable_is_not():
    # Tower Cellar 5, 22:50 on 2026-10-11 (the death), and its replay with attack mode drinking: one potion
    # drunk in the fight left the belt short, and the press went for the potion 4 away among nine monsters.
    stepped = []
    play = game(HP_NEAR, belt=SHORT_HP)
    assert not pick_up(play.run(), LEVEL, keys, lambda: stepped.append(True), threat=lambda here, spot: 3)
    assert stepped == [True]  # the press goes on to what it does with nothing to pick up
    assert play.picked == []
    assert play.said[-1] == 'a healing potion left for later: 3 monsters near'

    play = game(HP_NEAR, belt=SHORT_HP)
    assert pick_up(play.run(), LEVEL, keys, nothing, threat=lambda here, spot: 0)
    assert play.picked == ['a healing potion']

    play = game(RUNE, HP_NEAR, belt=SHORT_HP)
    assert pick_up(play.run(), LEVEL, keys, nothing, threat=lambda here, spot: 3)  # what is worth a risk
    assert play.picked[0] == RUNE.label


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


@pytest.mark.parametrize('give_up', [True, False])
def test_a_potion_not_wanted_is_not_clicked_blind_either(monkeypatch, give_up):
    # No aim shows the healing potion at all: the press gives up before it takes the other one; given up for the
    # game (GIVE_UP_CHEAP, 2026-10-21), else the press stops as before
    monkeypatch.setattr(pickup, 'GIVE_UP_CHEAP', give_up)
    juv = Drop(52, HP_NEAR.x, HP_NEAR.y, 'a full rejuvenation potion', REJUVENATION)
    play = game(juv, HP_NEAR, belt=SHORT_HP)
    play.label_above[HP_NEAR.unit_id] = 400.0
    if give_up:
        assert not pick_up(play.run(), LEVEL, keys, nothing)
    else:
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
    assert wanted()['shown'][: len(pickup_rules(6))] == pickup_rules(6) != ()


def test_over_the_cell_cap_the_look_reads_only_the_magic_rare_and_white_bases_the_loop_judges(monkeypatch):
    # The player, 2026-10-20 ~11:55: "bases or blue/rare items might take much place (like spears, matron bow) -- we
    # want to check them"; ~12:00 "start all three" (loot/api.py G15, loot/ground_judge.py BASES)
    import json

    from inventory_tracking.loot import api, ground_judge
    from inventory_tracking.loot.shown import RARITIES, SIZES, pickup_rules
    from inventory_tracking.macros.pickup import shown_rules

    grand_matron_bow = 302  # amc (items/data/item_metadata.json)
    sizes = {int(k): v[0] * v[1] for k, v in json.loads(SIZES.read_text())['sizes'].items()}
    over = shown_rules()[len(pickup_rules(6)) :]
    assert over
    assert all(sizes[c] > 6 for rule in over for c in rule.classes)
    words = ('normal', 'hiQuality', 'magic', 'rare')
    assert {q for rule in over for q in rule.qualities} <= {RARITIES[w] for w in words}
    assert grand_matron_bow in {c for rule in over for c in rule.classes}
    monkeypatch.setattr(api, 'FIELD_OVERSIZE', False)
    monkeypatch.setattr(ground_judge, 'BASES', False)
    assert shown_rules() == pickup_rules(6)


def test_a_drop_no_click_picks_up_is_given_up_after_three_aims_and_left_alone_for_a_while(monkeypatch):
    # Worldstone Keep 3, 22:16 on 2026-10-10: 30 clicks in 21 s on a Large Charm that was under the
    # pointer every time, and nothing else was done meanwhile.
    from inventory_tracking.macros import pickup

    monkeypatch.setattr(pickup, 'PICK_AT_ONCE', False)  # this press's own miss path (on: the press after's, 2026-10-25)
    pickup.SHUNNED.clear()
    play = game(RUNE)
    play.deaf_picks = 999
    with pytest.raises(Abort, match='no click picked it up'):
        pick_up(play.run(), LEVEL, keys, nothing)
    # 8.5 away: the first aim's two clicks moved nobody, a hop nearer (NEARER_AFTER_STILL), then the three aims
    assert 999 - play.deaf_picks == pickup.MISSED_AIMS * pickup.CLICKS + pickup.CLICKS
    assert 't' in play.pressed()
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
    play.world = replace(play.world, player=replace(me(play.world), mode=3))
    stop = lambda: setattr(play, 'world', replace(play.world, player=replace(me(play.world), mode=1)))  # ruff: ignore[lambda-assignment]
    play.arrivals.append((0.4, stop))
    run = play.run()
    assert stood(standing(run)).mode == 1
    assert 0.4 <= play.clock.now < 0.5
    play.world = replace(play.world, player=replace(me(play.world), mode=3))
    began = play.clock.now
    assert stood(standing(run)).mode == 3  # it never stood: the aim is taken anyway after STAND_SECONDS
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


def test_a_gold_pile_out_of_view_is_left_alone_and_the_press_goes_on(monkeypatch):
    # 18:26:19 on 2026-10-17: 5024 gold "not in view" 24 units off stopped the loop's pickup, and the loop left Lower
    # Kurast by Save and Exit: its next game began in act 3
    monkeypatch.setattr(pickup, 'in_view', lambda where: False)
    monkeypatch.setattr(pickup, 'SHUNNED', {})
    play = game(PILE)
    assert not pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == []
    assert PILE.unit_id in pickup.SHUNNED
    assert play.said[-1] == '7200 gold: not in view, left'


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
    play.world = replace(play.world, player=replace(me(play.world), mode=10))
    over = lambda: setattr(play, 'world', replace(play.world, player=replace(me(play.world), mode=1)))  # ruff: ignore[lambda-assignment]
    play.arrivals.append((0.3, over))
    assert stood(standing(play.run())).mode == 1
    assert 0.3 <= play.clock.now < 0.4


def test_in_a_big_pile_the_label_is_looked_for_further_up_and_to_the_sides(caplog, monkeypatch):
    # Arcane Sanctuary, 16:03:45 on 2026-10-11: a Flawless Diamond among 12 drops showed at none of the 16
    # aims, four presses running; the clicks made unseen had a monster under them.
    from inventory_tracking.macros import pile
    from inventory_tracking.macros.pickup import ITEM_AIMS, PILE_AIMS, PILE_MORE, pile_aims

    monkeypatch.setattr(pile, 'PILE_SWEEP', False)  # the pile's own aims (the sweep: test_pile.py)

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


def test_a_try_at_a_drop_looks_first_where_the_tries_before_did_not(caplog):
    # A Grand Charm among 9 drops, 00:04:36-41 on 2026-10-20: each level run's pickup was cut at its priced 1.5 s
    # after the same ~10 aims, and the pile's further aims were never looked at in 3 tries
    from inventory_tracking.macros import pickup

    play = game(RUNE)
    play.pick_above = 300.0
    with pytest.raises(Abort):
        pick_up(play.run(), LEVEL, keys, nothing)
    assert set(pickup.LOOK_AIMS) <= pickup.LOOKED[RUNE.unit_id]  # every aim looked at, the rune under none
    pickup.SHUNNED.clear()
    pickup.LOOKED[RUNE.unit_id] = set(pickup.LOOK_AIMS[:4])  # a try cut short after four
    play.pick_above = 64.0
    with caplog.at_level('INFO'):
        pick_up(play.run(), LEVEL, keys, nothing)
    line = next(r.message for r in reversed(caplog.records) if 'aims for Ist Rune' in r.message)
    assert line.endswith('wanted and 0 other drops: (0, -14) (0, 0); (0, -64) wanted clicked')
    assert RUNE.unit_id not in pickup.LOOKED  # picked up: forgotten


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
        play.world = replace(play.world, player=replace(me(play.world), mode=17))

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


def test_by_hand_a_low_rune_with_no_room_lets_the_press_go_on():
    # macros/lootpolicy.py (rca/2026-10-18/arch-level-behaviour.md §2.1, Q1): KP_1 by hand goes on as before the
    # player's ruling of 2026-10-18 17:50 (it is the loop's)
    rune = Drop(73, 5008.0, 5003.0, 'El Rune', VALUABLE, (1, 1), prized=False, source='rune')
    play = game(rune)
    play.loot = Loot((rune,), FULL, 1000, 1000, FULL_ROOM)
    went_on = []
    assert not pick_up(play.run(), LEVEL, keys, lambda: went_on.append(True))
    assert not pick_up(play.run(), LEVEL, keys, lambda: went_on.append(True))
    assert went_on == [True, True]


CHIPPED = Drop(74, 5008.0, 5003.0, 'Chipped Amethyst', VALUABLE, (1, 1), prized=False, source='material')


def test_in_the_loop_a_chipped_gem_with_no_room_stops_the_press_with_a_room_cause():
    # The player, 2026-10-18 17:50, on Q1: "we should stop and clear inventory with our designated town routine": the
    # loop's press (runner.py `take_one`) does not move on from it; its stop is the room rules' (the cube, a trip)
    from inventory_tracking.macros.runner import classify

    play = game(CHIPPED)
    play.loot = Loot((CHIPPED,), FULL, 1000, 1000, FULL_ROOM)
    run = play.run()
    warned = warned_by(run)
    with pytest.raises(Abort, match=r'inventory full: no room for Chipped Amethyst$') as stop:
        pick_up(run, LEVEL, keys, nothing, looped=True)
    assert stop.value.cause == 'room'
    assert classify(stop.value) == 'room'
    assert warned == ['Inventory full: Chipped Amethyst left on the ground']
    assert play.picked == []
    # By hand, the same ground: the press goes on to its seek step
    went_on = []
    assert not pick_up(play.run(), LEVEL, keys, lambda: went_on.append(True))
    assert went_on == [True]


def test_in_the_loop_gear_the_filter_shows_with_no_room_gets_the_cube_step_once_then_the_press_goes_on(monkeypatch):
    # lootpolicy.py CANDIDATE_CUBE (2026-10-23, the loot verifier: a rare Bone Knife left "no room" at 00:58:16 and the
    # game ended 1.2 s later): the press asks the loop's cube step once for it (a room cause, no trip: `trip_for`), then
    # goes on as the 2026-10-12 rule has it
    from inventory_tracking.macros import lootpolicy

    monkeypatch.setattr(lootpolicy, 'CUBE_ASKED', set())
    monkeypatch.setattr(lootpolicy, 'CUBE_PENDING', {})
    book = Drop(71, 5008.0, 5003.0, 'Superior Old Book', VALUABLE, (2, 2), prized=False, source='shown')
    play = game(book)
    play.loot = Loot((book,), FULL, 1000, 1000, FULL_ROOM, shown=frozenset((71,)))
    with pytest.raises(Abort, match=r'no room for Superior Old Book: the cube step first$') as stop:
        pick_up(play.run(), LEVEL, keys, nothing, looped=True)
    assert stop.value.cause == 'room'
    assert lootpolicy.cube_pending(71)
    went_on = []
    assert not pick_up(play.run(), LEVEL, keys, lambda: went_on.append(True), looped=True)
    assert went_on == [True]
    assert not lootpolicy.cube_pending(71)  # met again: the step was made
    monkeypatch.setattr(lootpolicy, 'CANDIDATE_CUBE', False)
    monkeypatch.setattr(lootpolicy, 'CUBE_ASKED', set())
    went_on.clear()
    assert not pick_up(play.run(), LEVEL, keys, lambda: went_on.append(True), looped=True)
    assert went_on == [True]  # the switch off: left at once, as before


def test_in_the_loop_a_chipped_gem_is_taken_once_there_is_room():
    play = game(CHIPPED)
    play.loot = Loot((CHIPPED,), FULL, 1000, 1000, ('#########.',) + ('##########',) * 3)
    assert pick_up(play.run(), LEVEL, keys, nothing, looped=True)
    assert play.picked == ['Chipped Amethyst']


def test_the_warning_is_taken_back_when_nothing_is_left_for_want_of_room():
    play = game()
    play.loot = Loot((), FULL, 1000, 1000, FULL_ROOM)
    run = play.run()
    warned = warned_by(run)
    pick_up(run, LEVEL, keys, lambda: None)
    assert warned == [None]


def test_a_valuable_clicked_and_found_carried_at_a_later_look_is_said_picked_up_late(caplog):
    # 02:10:14.70 on 2026-10-18: a magic Jewel "still on the ground after the click", off the ground 0.25 s later and
    # in the inventory at the next trade; the watch, which reads the pickups, called it missed
    import logging
    import re

    from inventory_tracking.game.records import VALUABLE, Drop, Loot
    from inventory_tracking.macros import pickup

    jewel = Drop(77, 5382.0, 3219.0, 'Jewel', VALUABLE)
    pickup.CLICKED.clear()
    pickup.CLICKED[77] = (jewel, 100.0)
    with caplog.at_level(logging.INFO):
        pickup.unshunned(Loot(carried=frozenset()), 100.5)  # not carried yet: still waited for
        assert 77 in pickup.CLICKED
        pickup.unshunned(Loot(carried=frozenset({77})), 101.3)
    assert 77 not in pickup.CLICKED
    said = [r.getMessage() for r in caplog.records if 'late' in r.getMessage()]
    assert said
    found = re.search(r'Macro: picked up (.+?) [\d.]+s after', said[0])  # the watch's PICKED
    assert found is not None
    assert found.group(1) == 'Jewel'
    pickup.CLICKED[78] = (jewel, 100.0)
    pickup.unshunned(Loot(carried=frozenset({78})), 100.0 + pickup.LATE_SECONDS + 1)  # too late to be the click's
    assert 78 not in pickup.CLICKED


def test_a_valuable_a_moves_click_took_is_said_picked_up(caplog):
    # 23:42:53 on 2026-10-19, Halls of the Dead 1: the level run's walk toward Tal Rune clicked its label; it left the
    # ground into the inventory (a 1x1 cell filled at the next read) and no line said so: the watch called it MISSED
    import logging
    import re

    from inventory_tracking.game.records import VALUABLE, Drop, Loot
    from inventory_tracking.macros import pickup

    rune = Drop(4258176654, 15126.0, 6757.0, 'Tal Rune', VALUABLE, source='rune')
    amulet = Drop(3445073849, 15104.0, 6762.0, 'Amulet', VALUABLE, source='material')
    pickup.CLICKED.clear()
    pickup.SEEN.clear()
    with caplog.at_level(logging.INFO):
        pickup.unshunned(Loot(drops=(rune, amulet)), 465333.29)  # on the ground
        pickup.unshunned(Loot(drops=(amulet,), carried=frozenset({rune.unit_id})), 465333.67)  # carried now
        pickup.unshunned(Loot(drops=(amulet,), carried=frozenset({rune.unit_id})), 465334.0)  # said once
    said = [r.getMessage() for r in caplog.records if 'picked up' in r.getMessage()]
    assert len(said) == 1
    found = re.search(r'Macro: picked up (.+?) [\d.]+s after', said[0])  # the watch's PICKED
    assert found is not None
    assert found.group(1) == 'Tal Rune'
    assert amulet.unit_id in pickup.SEEN  # still on the ground: nothing said


def test_a_valuable_seen_long_ago_or_said_by_its_click_is_not_said_again(caplog):
    import logging

    from inventory_tracking.game.records import VALUABLE, Drop, Loot
    from inventory_tracking.macros import pickup

    jewel = Drop(79, 5382.0, 3219.0, 'Jewel', VALUABLE)
    pickup.CLICKED.clear()
    pickup.SEEN.clear()
    with caplog.at_level(logging.INFO):
        pickup.unshunned(Loot(drops=(jewel,)), 100.0)
        pickup.unshunned(Loot(carried=frozenset({79})), 100.0 + pickup.LATE_SECONDS + 1)  # another game's, by now
        pickup.unshunned(Loot(drops=(jewel,)), 200.0)
        pickup.CLICKED[79] = (jewel, 200.1)  # the pickup's own click: its `late` line says it
        pickup.unshunned(Loot(carried=frozenset({79})), 200.5)
    said = [r.getMessage() for r in caplog.records if 'picked up' in r.getMessage()]
    assert len(said) == 1
    assert 'after the click, late' in said[0]
    assert 79 not in pickup.SEEN


# --- a unique Grand Charm refused for the Gheed's Fortune carried (macros/pickup.py `Refused`) ---


def gheeds_game(drop: Drop, *, gheeds: bool = True) -> Game:
    """A press by `drop` within NEAR_UNITS whose every click the game refuses, the player's Gheed's Fortune carried
    (`gheeds`) or none."""
    from inventory_tracking.game.records import Carried, Pack
    from inventory_tracking.macros.charms import GHEEDS_FORTUNE, UNIQUE, grand_charm

    play = game(drop)
    play.deaf_picks = 999
    theirs = Carried(1, grand_charm(), 0, 0, (1, 3), quality=UNIQUE, unique=GHEEDS_FORTUNE)
    play.pack = Pack((theirs,) if gheeds else (), ('..........',) * 4)
    return play


def unique_charm() -> Drop:
    from inventory_tracking.macros.charms import UNIQUE, grand_charm

    return Drop(60, 5004.0, 5003.0, "Unique Grand Charm (Gheed's Fortune?)", VALUABLE, (1, 3), txt=grand_charm(),
                quality=UNIQUE)  # fmt: skip


def test_a_unique_grand_charm_refused_with_a_gheeds_carried_stops_at_the_first_click(caplog):
    # 13:34:48.1-13:34:53.8 on 2026-10-18: five clicks at three aims, two trips back, then the stop and the swap; the
    # first click that leaves it on the ground is the sign (the player, 13:41: "you cannot pickup another gheed if you
    # have another in inventory/private tab")
    from inventory_tracking.macros.pickup import Refused

    charm = unique_charm()
    play = gheeds_game(charm)
    caplog.set_level('INFO')
    with pytest.raises(Refused, match="another Gheed's Fortune is carried") as stop:
        pick_up(play.run(), LEVEL, keys, nothing)
    assert stop.value.drop == charm
    assert 999 - play.deaf_picks == 1  # no second click, no further aim
    assert charm.unit_id in pickup.SHUNNED  # the next press does something else, as after the three aims
    assert "refused at the first click: a Gheed's Fortune is carried" in caplog.text


@pytest.mark.parametrize('which', ['a rune', 'no gheeds carried'])
def test_a_refused_click_on_anything_else_keeps_the_three_aims(which):
    # Not the carry-one sign: a click a cast swallowed is tried again, up to MISSED_AIMS aims (unchanged)
    from inventory_tracking.macros.pickup import Refused

    near_rune = replace(RUNE, x=5004.0)
    play = gheeds_game(near_rune) if which == 'a rune' else gheeds_game(unique_charm(), gheeds=False)
    with pytest.raises(Abort, match='under the pointer at 3 aims and no click picked it up') as stop:
        pick_up(play.run(), LEVEL, keys, nothing)
    assert not isinstance(stop.value, Refused)
    assert 999 - play.deaf_picks == pickup.MISSED_AIMS * pickup.CLICKS


def test_a_unique_grand_charm_with_no_room_for_it_is_no_refusal():
    # A full inventory is the room rules' (runner.py `_loop_stopped`), not the Gheed's swap's
    from inventory_tracking.macros.pickup import refusal

    charm = unique_charm()
    play = gheeds_game(charm)
    run = play.run()
    player = run.world().player
    assert refusal(run, charm, player) is not None
    play.loot = replace(play.loot, room=('#.........', '#.........', '##########', '##########'))
    assert refusal(run, charm, player) is None
    far = replace(charm, x=5020.0)  # a click that did not bring the character up to it
    play.loot = replace(play.loot, room=None)
    assert refusal(run, far, player) is None


def test_an_item_picked_for_the_field_identify_comes_after_every_other_valuable_in_sight(monkeypatch):
    # The player, 2026-10-20 ~11:55 (big items checked in the field): a big one never takes a valuable's room
    from inventory_tracking.loot.api import FIELD

    monkeypatch.setattr(FIELD, 'looping', lambda: True)
    bow = Drop(60, 5001.0, 5001.0, 'Rare Grand Matron Bow', VALUABLE, (2, 4), False, 'shown', 302, 6)
    assert FIELD.pick(bow, ('game-1', 7))
    try:
        nearer_first = Loot((bow, RUNE), FULL, 1000, 1000, game=('game-1', 7))
        assert choose(nearer_first, ORIGIN) == Plan(RUNE)
        assert choose(Loot((bow,), FULL, 1000, 1000, game=('game-1', 7)), ORIGIN) == Plan(bow)
    finally:
        FIELD.picked.clear()


# --- the label guard (pickup.py LABEL_GUARD; the player, 2026-10-21 ~00:55: "not always clicking correct object (we
# often can pickup hp/rejuv potion) that we wanted") ---


def test_a_blind_click_is_not_made_on_an_item_that_serves_nothing():
    # An item under the pointer that is no drop of the press's (a junk label in the pile, a potion no list named): the
    # game takes the item under the pointer, so a blind click there picks it up into the inventory
    wanted = Drop(60, 5004.0, 5002.0, 'Ist Rune', VALUABLE)
    junk = Drop(61, 5004.0, 5002.0, 'a super healing potion', HEALING)
    play = game(wanted, junk)
    play.label_above[wanted.unit_id] = 400.0  # its label is nowhere an aim looks
    play.label_above[junk.unit_id] = 24.0
    with pytest.raises(Abort, match='no click picked up Ist Rune'):
        pickup.take(play.run(), wanted)  # `others` empty: the potion is in no list of the press's
    assert play.picked == []


def test_the_walk_up_to_a_far_drop_is_not_clicked_on_another_items_label(caplog):
    # The walk up clicks the drop's ground: a potion's label stacked there took the click (the walk picks it up)
    far = Drop(80, 5012.0, 5010.0, 'Grand Charm', VALUABLE, (1, 3))
    potion = Drop(81, far.x + 14 / 16, far.y + 14 / 16, 'a super healing potion', HEALING)
    play = game(far, potion)
    play.label_above[80] = 300  # its label is nowhere the aims look
    with caplog.at_level('INFO'), pytest.raises(Abort):
        pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == []
    assert math.dist(play.walks[0], (far.x, far.y)) < 1.5  # walked up to it all the same, off the label
    assert 'the walk up to Grand Charm: a label (4, 81) under its ground; clicked (0, 10) pixels below' in caplog.text


@pytest.mark.parametrize('guard', [True, False], ids=['guarded', 'the switch off'])
def test_the_switch_off_clicks_blind_and_walks_up_on_any_label_as_before(monkeypatch, guard):
    monkeypatch.setattr(pickup, 'LABEL_GUARD', guard)
    far = Drop(80, 5012.0, 5010.0, 'Grand Charm', VALUABLE, (1, 3))
    potion = Drop(81, far.x + 14 / 16, far.y + 14 / 16, 'a super healing potion', HEALING)
    play = game(far, potion)
    play.label_above[80] = 300
    with pytest.raises(Abort):
        pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ([] if guard else ['a super healing potion'])


# --- clicks from afar that move nobody (rca/2026-10-21/potion-click-findings.md) ---

FAR_POTION = Drop(80, 5019.0, 5000.0, 'a super healing potion', HEALING)


@pytest.fixture(autouse=True)
def fresh():
    """The pickup's memories of drops empty before and after each test (module-level, kept across presses in a game):
    a drop given up for the game in one test is no drop of the next."""
    for memory in (pickup.SHUNNED, pickup.UNMOVED, pickup.GIVEN_UP, pickup.LOOKED):
        memory.clear()
    yield
    for memory in (pickup.SHUNNED, pickup.UNMOVED, pickup.GIVEN_UP, pickup.LOOKED):
        memory.clear()


def test_a_drop_whose_clicks_from_afar_move_nobody_is_hopped_nearer_and_taken(monkeypatch, fresh, caplog):
    # Travincal, 13:37:16-24 on 2026-10-21: a super healing potion 18.6 away under the pointer at every aim, 11 clicks
    # in 8 s and the character never moved; the game was left for it
    monkeypatch.setattr(pickup, 'NEARER_AFTER_STILL', True)
    play = game(FAR_POTION, belt=SHORT_HP)
    play.far_refused = 15.0
    with caplog.at_level('INFO'):
        assert pick_up(play.run(), LEVEL, keys, nothing)
    assert play.picked == ['a super healing potion']
    assert 't' in play.pressed()  # a hop beside it
    assert any('moved nobody from 19 away' in r.message and 'gone nearer' in r.message for r in caplog.records)


def test_without_the_switch_the_clicks_from_afar_go_on_as_before(monkeypatch, fresh):
    monkeypatch.setattr(pickup, 'NEARER_AFTER_STILL', False)
    play = game(FAR_POTION, belt=SHORT_HP)
    play.far_refused = 15.0
    assert pick_up(play.run(), LEVEL, keys, nothing)
    assert 't' not in play.pressed()  # no hop: the other aims from afar, then the walk up by its ground (the fake's
    assert play.walks  # ground click walks; in the game it had the potion under it too and walked nobody)


def test_a_later_try_at_a_drop_whose_clicks_moved_nobody_goes_nearer_before_its_first_click(monkeypatch, fresh):
    # A level run's pickup is cut at its priced 1.5 s: the next try starts with the remedy, not the same clicks
    monkeypatch.setattr(pickup, 'NEARER_AFTER_STILL', True)
    play = game(FAR_POTION, belt=SHORT_HP)
    play.far_refused = 15.0
    run = play.run()
    pickup.UNMOVED[FAR_POTION.unit_id] = run.clock() + pickup.UNMOVED_SECONDS
    assert pick_up(run, LEVEL, keys, nothing)
    assert play.picked == ['a super healing potion']
    assert play.pressed()[0] == 't'  # the hop before any click


def test_a_potion_no_click_takes_is_given_up_for_the_game_and_the_press_goes_on(monkeypatch, fresh, caplog):
    monkeypatch.setattr(pickup, 'PICK_AT_ONCE', False)  # this press's own miss path (on: the press after's, 2026-10-25)
    # The player, 2026-10-21 ~13:40: the loop left a shard's act for a potion no click took
    monkeypatch.setattr(pickup, 'GIVE_UP_CHEAP', True)
    play = game(HP_NEAR, belt=SHORT_HP)
    play.deaf_picks = 999
    with caplog.at_level('INFO'):
        assert not pick_up(play.run(), LEVEL, keys, nothing)
    assert dict(pickup.GIVEN_UP) == {HP_NEAR.unit_id: None}
    assert any('given up for this game' in r.message and 'the game is kept' in r.message for r in caplog.records)
    pickup.SHUNNED.clear()  # past its 30 s: still given up for the game
    asked = []
    assert not pick_up(play.run(), LEVEL, keys, lambda: asked.append(1))
    assert asked == [1]


def test_without_the_switch_a_potion_no_click_takes_stops_the_press_as_before(monkeypatch, fresh):
    monkeypatch.setattr(pickup, 'PICK_AT_ONCE', False)  # this press's own miss path (on: the press after's, 2026-10-25)
    monkeypatch.setattr(pickup, 'GIVE_UP_CHEAP', False)
    play = game(HP_NEAR, belt=SHORT_HP)
    play.deaf_picks = 999
    with pytest.raises(pickup.Missed, match='no click picked it up') as stop:
        pick_up(play.run(), LEVEL, keys, nothing)
    assert stop.value.cause == 'pickup'
    assert pickup.GIVEN_UP == {}


def test_a_valuable_no_click_takes_still_stops_the_press_with_the_pickup_cause(monkeypatch, fresh):
    monkeypatch.setattr(pickup, 'PICK_AT_ONCE', False)  # this press's own miss path (on: the press after's, 2026-10-25)
    monkeypatch.setattr(pickup, 'GIVE_UP_CHEAP', True)
    play = game(RUNE)
    play.deaf_picks = 999
    with pytest.raises(pickup.Missed, match='no click picked it up') as stop:
        pick_up(play.run(), LEVEL, keys, nothing)
    assert stop.value.cause == 'pickup'
    assert stop.value.drop.unit_id == RUNE.unit_id
    assert pickup.GIVEN_UP == {}


def test_gold_no_click_takes_is_given_up_and_never_stops_the_press(monkeypatch, fresh):
    monkeypatch.setattr(pickup, 'PICK_AT_ONCE', False)  # this press's own miss path (on: the press after's, 2026-10-25)
    monkeypatch.setattr(pickup, 'GIVE_UP_CHEAP', True)
    play = game(PILE)
    play.gold_radius = 0.0
    play.warp_lands = False
    play.deaf_picks = 999
    assert not pick_up(play.run(), LEVEL, keys, nothing)
    assert PILE.unit_id in pickup.GIVEN_UP


def test_a_drop_given_up_in_another_game_is_looked_at_again():
    pickup.GIVEN_UP.clear()
    pickup.GIVEN_UP[HP_NEAR.unit_id] = ('cyber1', 7)
    loot = Loot((HP_NEAR,), SHORT_HP, 1000, 1000, game=('cyber1', 7))
    assert pickup.unshunned(loot, 0.0).drops == ()
    assert pickup.unshunned(replace(loot, game=('cyber2', 7)), 0.0).drops == (HP_NEAR,)
    assert pickup.GIVEN_UP == {}


# --- a drop whose label the game never draws (WAIVE_UNLABELLED; rca/2026-10-22/hidden-staff-findings.md) ---

STAFF = Drop(90, 5003.0, 5002.0, 'Superior Gothic Staff', VALUABLE, (1, 4))
STAFF_GAME = ('cyberg13', 13)


def hidden(play, *, nothing=True, show_items=True):
    """A run on `play` whose hover record reads nothing under the pointer at every aim (`nothing`; else unread), the
    game's Show Items toggle at `show_items`, and every click taking nothing: the loot filter hides the drop."""
    play.deaf_picks = 999
    play.world = replace(play.world, show_items=show_items)
    run = play.run()
    run.hovered = lambda: None
    run.hover_nothing = lambda: nothing
    return run


def staff_game():
    play = game(STAFF)
    play.loot = Loot((STAFF,), FULL, 1000, 1000, game=STAFF_GAME)
    return play


def test_a_valuable_with_no_label_is_tried_once_more_then_given_up_for_the_game(fresh, caplog):
    # 08:30:44-08:33:11 on 2026-10-22: four presses, every aim "unread or nothing [flag 0x0 ...]", the loop stopped
    play = staff_game()
    with pytest.raises(pickup.Unlabelled, match='no click picked up Superior Gothic Staff: its label') as stop:
        pick_up(hidden(play), LEVEL, keys, nothing)
    assert stop.value.cause == 'pickup'  # the first: the loop's rules go back for it (stops.py FETCH), as before
    assert pickup.GIVEN_UP == {}
    assert pickup.WAIVED == {}
    pickup.SHUNNED.clear()
    with caplog.at_level('INFO'):
        assert not pick_up(hidden(play), LEVEL, keys, nothing)  # the second: waived, the press goes on
    assert dict(pickup.GIVEN_UP) == dict.fromkeys([STAFF.unit_id], STAFF_GAME)
    assert dict(pickup.WAIVED) == dict.fromkeys([STAFF.unit_id], STAFF_GAME)
    assert any('given up for this game' in r.message and 'the loot filter hides it' in r.message
               for r in caplog.records)  # fmt: skip
    assert play.picked == []
    # Out of what the loop guards in this game, and back in the next
    assert pickup.waived(play.loot).drops == ()
    assert pickup.waived(replace(play.loot, game=('cyberg14', 14))).drops == (STAFF,)


@pytest.mark.parametrize(
    'why', ['an unread hover record', 'Show Items off', 'Show Items unread', 'the switch off', 'no game read']
)
def test_a_valuable_with_no_label_is_never_waived_without_the_proof(why, fresh, monkeypatch):
    play = staff_game()
    if why == 'the switch off':
        monkeypatch.setattr(pickup, 'WAIVE_UNLABELLED', False)
    if why == 'no game read':
        play.loot = replace(play.loot, game=None)
    for _ in range(3):
        pickup.SHUNNED.clear()
        run = hidden(
            play, nothing=why != 'an unread hover record',
            show_items={'Show Items off': False, 'Show Items unread': None}.get(why, True),
        )  # fmt: skip
        with pytest.raises(pickup.Missed, match='no click picked up Superior Gothic Staff') as stop:
            pick_up(run, LEVEL, keys, nothing)
        assert isinstance(stop.value, pickup.Unlabelled) == (why == 'no game read')
    assert pickup.WAIVED == {}
    assert pickup.GIVEN_UP == {}


def test_a_valuable_whose_label_was_under_the_pointer_is_never_waived(fresh, monkeypatch):
    # The clicks took nothing with the label there (2026-10-10 22:16, the Large Charm): the loop's rules, as before
    play = staff_game()
    play.deaf_picks = 999
    play.world = replace(play.world, show_items=True)
    for _ in range(3):
        pickup.SHUNNED.clear()
        pickup.UNMOVED.clear()
        with pytest.raises(pickup.Missed) as stop:
            pick_up(play.run(), LEVEL, keys, nothing)
        assert not isinstance(stop.value, pickup.Unlabelled)
    assert pickup.WAIVED == {}


def test_the_loop_reads_no_waived_drop_so_its_guard_keeps_no_game_for_it(fresh):
    import threading
    from pathlib import Path

    from inventory_tracking.macros.runner import MacroRunner

    found = MacroRunner(None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent'), display=lambda _: None)
    found.loop.on = True
    loot = Loot((STAFF, RUNE), FULL, 1000, 1000, game=STAFF_GAME)
    before = {drop.unit_id for drop in found._picked(loot).drops}
    assert STAFF.unit_id in before
    pickup.WAIVED[STAFF.unit_id] = STAFF_GAME
    assert {drop.unit_id for drop in found._picked(loot).drops} == before - {STAFF.unit_id}
