"""Deckard Cain's Identify Items, the KP_6 loop's mass identify (macros/cain.py; routes/lower-kurast-loop-plan.md §15).
The player, 2026-10-17: "we need to perform mass identify at decard cain -> stash good -> sell junk -> return to
loop"."""

import pytest

from inventory_tracking.game.records import Carried, Monster, Pack
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cain import CAIN, identify_all
from inventory_tracking.macros.cube import CUBE_CLASS
from inventory_tracking.macros.shop import known
from tests.inventory_tracking.macros.fakes import CAIN_LINE, Game, player, world


FORTRESS = 103
START = (5048.0, 5044.0)  # where a game begins, by the waypoint
CAIN_AT = (5022.8, 5032.7)  # the take 20261017T085221Z-103
CUBE = Carried(1, CUBE_CLASS, 0, 0, (2, 2))
KRISS = Carried(11, 41, 2, 0, (1, 3), quality=4, identified=False)
CODEX = Carried(12, 510, 0, 0, (2, 2), quality=4, identified=False)  # in the cube


def fortress() -> Game:
    cain = Monster(78, CAIN, 1, *CAIN_AT, 0xFFFFFFFF)
    play = Game(world(FORTRESS, player=player(FORTRESS, x=START[0], y=START[1]), monsters=(cain,)))
    play.vendor = cain
    play.pack = Pack((CUBE, KRISS), ('...',) * 4, in_cube=(CODEX,), cube_items=frozenset({CODEX.unit_id}))
    return play


def test_cain_identifies_the_inventorys_and_the_cubes_items_at_once_and_his_line_is_learned():
    play = fortress()

    assert identify_all(play.run(), (KRISS, CODEX)) == 2

    assert play.pack is not None
    assert all(i.identified for i in (*play.pack.items, *play.pack.in_cube))
    assert known(CAIN) == pytest.approx(CAIN_LINE, abs=0.012)  # the first lift scanned that took
    assert play.world.open_panels == ()


def test_no_cain_where_he_stands_stops_the_visit():
    play = fortress()
    play.world = world(FORTRESS, player=player(FORTRESS, x=START[0], y=START[1]))
    play.vendor = None
    with pytest.raises(Abort, match='not in sight'):  # walked toward his usual place first (shop.py USUAL)
        identify_all(play.run(), (KRISS,))


def test_his_lines_are_tried_nearest_the_learned_one_first(monkeypatch):
    # 17:05:56-17:06:03 on 2026-10-17: from 0.16 up it took four tries, 8.5 s, with the learned one two steps off
    from inventory_tracking.macros import cain

    monkeypatch.setattr(cain, 'known', lambda vendor: 0.2165)
    tried = cain.lifts()
    assert tried[0] == 0.2165
    assert {round(abs(lift - 0.2165), 4) for lift in tried[1:3]} == {round(cain.LINE / 2, 4)}  # a half line either side


def test_his_line_is_clicked_at_the_middle_of_the_lifts_that_took_and_takes_at_once(caplog):
    # 2026-10-18/19: the last lift that took alone sat on an edge of his line (0.2052 and 0.2165 both took, half a
    # line apart) and missed now and then, ~4 s each (the player: "looks like we're cannot lick identify all from the
    # first attempt"); the middle of the two takes at once
    import json
    import logging

    from inventory_tracking.macros import shop

    shop.LIFTS_FILE.write_text(json.dumps({str(CAIN): [round(CAIN_LINE - 0.0113, 4), round(CAIN_LINE + 0.0113, 4)]}))
    assert known(CAIN) == pytest.approx(CAIN_LINE, abs=1e-4)
    play = fortress()
    with caplog.at_level(logging.INFO):
        assert identify_all(play.run(), (KRISS, CODEX)) == 2
    assert caplog.text.count('the Identify Items line clicked') == 1
    assert 'menu line missed' not in caplog.text
    assert 'over Deckard Cain' in caplog.text  # named, not "Jamella"


# An item's label over Cain (shop.py LABELS_OFF_AT_NPC, 2026-10-23; 16:05:00 on 2026-10-21: (4, ...) under the pointer
# at him beside the stash's junk, the click on his body opened no menu)


def labelled_cain() -> Game:
    from dataclasses import replace

    play = fortress()
    play.world = replace(play.world, show_items=True)
    play.labels_over_vendor = 4242
    return play


def test_an_item_label_over_cain_is_hidden_for_the_click_and_shown_again(caplog):
    from tests.inventory_tracking.macros.fakes import SHOW_ITEMS_KEY

    play = labelled_cain()
    run = play.run()
    run.show_items_key = SHOW_ITEMS_KEY

    with caplog.at_level('INFO'):
        assert identify_all(run, (KRISS, CODEX)) == 2

    assert play.labelled_takes == []  # no click on the label
    assert play.world.show_items is True
    presses = [e for e in play.keys.events if e == ('key', SHOW_ITEMS_KEY)]
    assert presses
    assert len(presses) % 2 == 0  # hidden and shown again at each opening of his menu
    assert 'Deckard Cain: an item label in the way: item labels hidden by' in caplog.text


@pytest.mark.parametrize('why', ['switch off', 'no key known'])
def test_without_the_switch_or_a_key_the_label_over_cain_is_clicked_as_before(monkeypatch, why):
    import inventory_tracking.macros.shop as shop_module
    from tests.inventory_tracking.macros.fakes import SHOW_ITEMS_KEY

    play = labelled_cain()
    run = play.run()
    run.show_items_key = None if why == 'no key known' else SHOW_ITEMS_KEY
    if why == 'switch off':
        monkeypatch.setattr(shop_module, 'LABELS_OFF_AT_NPC', False)

    with pytest.raises(Abort, match='menu did not open'):
        identify_all(run, (KRISS,))

    assert play.labelled_takes  # the label clicked: its item taken up in the game
    assert ('key', SHOW_ITEMS_KEY) not in play.keys.events


# Our own Town Portal under the walk's click (shop.py WALK_OFF_WAYS; rca/2026-10-23/visit-portal-findings.md): at
# 15:31:35.8 on 2026-10-23 the first walk click toward Cain, from beside the portal the character had come through,
# had that portal under the pointer, and the character went back through it to the River of Flame


RIVER_OF_FLAME = 107
ARRIVED = (5053.5, 5048.5)  # the character as the click was made (take 20261023T123132Z-103)
CAIN_THEN = (5023.46, 5022.63)  # Cain as the take read him
OUR_PORTAL = (5048.0, 5043.0)  # the Town Portal object 2264798530, class 59, open


def beside_our_portal() -> Game:
    from dataclasses import replace

    from inventory_tracking.game.records import Thing
    from inventory_tracking.levels.model import TOWN_PORTAL

    play = fortress()
    cain = Monster(78, CAIN, 1, *CAIN_THEN, 0xFFFFFFFF)
    me = player(FORTRESS, x=ARRIVED[0], y=ARRIVED[1])
    play.world = replace(play.world, player=me, monsters=(cain,))
    play.vendor = cain
    play.thing = Thing(2264798530, TOWN_PORTAL, 2, *OUR_PORTAL)
    play.next_area = RIVER_OF_FLAME
    return play


def test_the_walk_to_cain_is_turned_off_our_town_portal_and_never_goes_through_it(caplog):
    play = beside_our_portal()

    with caplog.at_level('INFO'):
        assert identify_all(play.run(), (KRISS, CODEX)) == 2

    assert play.character.area == FORTRESS
    assert 'Deckard Cain: the Town Portal (2264798530) under the click at (5044.4, 5040.7): turned' in caplog.text


def test_with_the_switch_off_the_walk_click_takes_our_town_portal_as_on_2026_10_23(monkeypatch):
    import contextlib

    import inventory_tracking.macros.shop as shop_module

    monkeypatch.setattr(shop_module, 'WALK_OFF_WAYS', False)
    play = beside_our_portal()

    with contextlib.suppress(Abort):  # the fake's Cain stays drawn: in the game "not in sight", the tome instead
        identify_all(play.run(), (KRISS, CODEX))

    assert play.character.area == RIVER_OF_FLAME


def test_a_way_out_under_the_pointer_at_his_body_is_not_clicked():
    from dataclasses import replace

    play = fortress()
    portal = beside_our_portal().thing
    assert portal is not None
    play.thing = replace(portal, x=START[0] + 20.0, y=START[1] + 20.0)  # off every walk click
    run = play.run()
    run.hovered = lambda: (2, 2264798530)  # the game names the portal wherever the pointer is: never Cain

    with pytest.raises(Abort, match=r'the Town Portal \(2264798530\) under the pointer at her: not clicked'):
        identify_all(run, (KRISS,))

    assert play.world.open_panels == ()  # no click on him: no menu
    assert play.pack is not None
    assert not next(i for i in play.pack.items if i.unit_id == KRISS.unit_id).identified
