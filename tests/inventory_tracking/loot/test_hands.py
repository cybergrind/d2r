"""The field routine's live hands (loot/hands.py) in the fake game: the Tome's clicks, the drop at the feet, the
put-down remembered, the player's items and the quiet rules (loot/design.md §5, M4)."""

import json
from dataclasses import replace
from pathlib import Path

from inventory_tracking.game.kept import PutDown
from inventory_tracking.game.layout import IDENTIFY_TOME
from inventory_tracking.game.records import VALUABLE, Carried, Drop, Loot, Monster, Pack
from inventory_tracking.loot.api import Field
from inventory_tracking.loot.facts import ItemFacts
from inventory_tracking.loot.hands import GameHands, waiting_valuable
from inventory_tracking.loot.shadow import Appraised, Book
from inventory_tracking.macros.cube import own_of
from inventory_tracking.macros.pickmode import MONARCH
from tests.inventory_tracking.macros.fakes import Game, player, world


BLOCKING = json.loads((Path(__file__).parent / 'fixtures' / 'field' / 'monarch-of-blocking.json').read_text())
UNIT = BLOCKING['observation']['source']['unit_id']
CATACOMBS_4 = 37
TOME = Carried(3, IDENTIFY_TOME, 9, 0, (1, 2))
WORN = Carried(4, MONARCH, 6, 0, (2, 3), 4)  # the player's own identified magic Monarch: never touched
JUNK = Carried(UNIT, MONARCH, 0, 0, (2, 3), 4, identified=False)  # picked for the field identify


class NoCopies:
    def copies(self, facts: ItemFacts) -> list[ItemFacts]:
        return []


def setup(pack: Pack, **changes) -> tuple[Game, GameHands, PutDown, list[list[int]]]:
    play = Game(world(CATACOMBS_4, player=player(CATACOMBS_4, x=5029.0, y=2860.0), **changes))
    play.pack = pack
    book, asked, put_down = Book(), [], PutDown()

    def appraise(units: list[int]) -> dict[int, str]:
        asked.append(units)
        for unit in units:
            book.put(unit, Appraised(BLOCKING['observation'], BLOCKING['result'], BLOCKING['verdict']))
        return dict.fromkeys(units, 'vendor')

    hands = GameHands(play.run(), inventory_key=lambda: 'i', own=lambda p: own_of((TOME, WORN)), appraise=appraise,
                      put_down=put_down, book=book, owned=NoCopies())  # fmt: skip
    return play, hands, put_down, asked


def looped(game: str) -> Field:
    found = Field()
    found.looping = lambda: True
    drop = Drop(UNIT, 1.0, 1.0, 'Magic Monarch', VALUABLE, (2, 3), False, 'shown', MONARCH, 4)
    assert found.pick(drop, (game, 1))
    return found


def test_the_monarch_is_identified_with_the_tome_dropped_at_the_feet_and_remembered():
    play, hands, put_down, asked = setup(Pack((TOME, WORN, JUNK), identifies=10))

    done = looped(play.world.game_name).settle(hands, 'Town Portal')

    assert asked == [[UNIT]]
    assert [item.unit_id for item in play.fallen] == [UNIT]
    assert done.dropped == 1
    assert play.pack is not None
    assert play.pack.identifies == 9
    assert [item.unit_id for item in play.pack.items] == [TOME.unit_id, WORN.unit_id]
    assert UNIT in put_down.rejected
    assert play.world.open_panels == ()
    # Streamed back on the ground: not the macro's to pick up again this game (the place kept by the first look)
    lying = Drop(UNIT, 5029.0, 2861.0, 'Monarch', VALUABLE, (2, 3), False, 'shown', MONARCH, 4)
    game = (play.world.game_name, 1)
    assert put_down.see(Loot(drops=(lying,), game=game)).drops == ()
    again = replace(lying, unit_id=UNIT + 1)
    assert put_down.see(Loot(drops=(again,), game=game, classes=((UNIT + 1, MONARCH),))).drops == ()


def test_near_a_hostile_nothing_is_clicked():
    zombie = Monster(70, 1, 1, 5035.0, 2860.0)
    play, hands, _, asked = setup(Pack((TOME, WORN, JUNK), identifies=10), monsters=(zombie,))
    assert (hands.unquiet() or '').endswith('hostiles within 30')
    done = looped(play.world.game_name).settle(hands, 'Town Portal')
    assert done.waited is not None
    assert asked == []
    assert play.fallen == []
    assert play.pack is not None
    assert play.pack.identifies == 10  # no scroll spent


def test_a_valuable_the_loop_can_pick_up_now_holds_it_one_with_no_room_does_not():
    rune = Drop(9, 1.0, 1.0, 'Ist Rune', VALUABLE, (1, 1), True, 'rune', 640, 2)
    roomy = ('.' * 10,) * 4
    assert waiting_valuable(Loot(drops=(rune,), room=roomy)) == 'Ist Rune'
    assert waiting_valuable(Loot(drops=(rune,), room=('#' * 10,) * 4)) is None
    assert waiting_valuable(Loot(drops=(replace(rune, kind='healing'),), room=roomy)) is None


def test_in_controller_mode_or_with_a_panel_open_it_waits():
    _, hands, _, _ = setup(Pack((TOME, WORN, JUNK), identifies=10), open_panels=('stash',))
    assert hands.unquiet() == 'stash open'


def test_in_town_it_is_quiet_and_the_tome_identifies_there():
    # 11:52:48 on 2026-10-20: a magic Ring waited 'in town (Cain)' at the Save and Exit, games away from a trade visit
    play, hands, _, asked = setup(Pack((TOME, WORN, JUNK), identifies=10))
    me = play.world.player
    assert me is not None
    play.world = replace(play.world, player=replace(me, area=1))  # the Rogue Encampment
    assert hands.unquiet() is None
    done = looped(play.world.game_name).settle(hands, 'Save and Exit')
    assert asked == [[UNIT]]
    assert done.dropped == 1


def test_in_town_with_a_visit_due_cain_identifies_them_there():
    # The player, 2026-10-20: "when we visit cain it identifies all items across cube + inventory"
    play, hands, _, asked = setup(Pack((TOME, WORN, JUNK), identifies=10))
    me = play.world.player
    assert me is not None
    play.world = replace(play.world, player=replace(me, area=1))  # the Rogue Encampment
    hands.cain_ahead = lambda: True
    assert hands.unquiet() == 'in town: Cain identifies them at the visit due'
    done = looped(play.world.game_name).settle(hands, 'Save and Exit')
    assert asked == []
    assert done.dropped == 0
    assert play.pack is not None
    assert play.pack.identifies == 10  # no scroll spent


def test_a_field_item_in_the_cube_comes_out_is_identified_in_the_inventory_and_dropped_from_it():
    """The cube's items (the player, 2026-10-20 ~13:28: "like right now we have a big hammer in cube"): out by Ctrl +
    click (cube.py `unpack`), the Tome in the inventory, put down at the feet from there; the panels closed."""
    from inventory_tracking.loot.storage import CUBE_CLASS

    cube = Carried(2, CUBE_CLASS, 7, 2, (2, 2))  # the inventory's first free cell takes the 2x3 (the fake's `unpack`)
    boxed = replace(JUNK, x=0, y=0)
    # The fake's cube rows stay as given (the game reads them anew): free, so the put back finds room
    pack = Pack((TOME, WORN, cube), ('...',) * 4, frozenset({UNIT}), (boxed,), identifies=10)
    play, hands, put_down, asked = setup(pack)

    done = looped(play.world.game_name).settle(hands, 'Town Portal')

    assert asked == [[UNIT]]
    assert [item.unit_id for item in play.fallen] == [UNIT]
    assert done.dropped == 1
    assert play.pack is not None
    assert play.pack.in_cube == ()
    assert UNIT not in {item.unit_id for item in play.pack.items}
    assert UNIT in put_down.rejected
    assert play.world.open_panels == ()


def test_a_kept_item_taken_out_of_the_cube_goes_back_into_it():
    from inventory_tracking.loot.storage import CUBE_CLASS

    cube = Carried(2, CUBE_CLASS, 7, 2, (2, 2))  # the inventory's first free cell takes the 2x3 (the fake's `unpack`)
    boxed = replace(JUNK, x=0, y=0)
    # The fake's cube rows stay as given (the game reads them anew): free, so the put back finds room
    pack = Pack((TOME, WORN, cube), ('...',) * 4, frozenset({UNIT}), (boxed,), identifies=10)
    play, hands, _, _ = setup(pack)
    hands.appraiser = lambda units: {}  # no appraisal: kept (S8)

    looped(play.world.game_name).settle(hands, 'Town Portal')

    assert play.fallen == []
    assert play.pack is not None
    assert [item.unit_id for item in play.pack.in_cube] == [UNIT]
    assert play.world.open_panels == ()


def test_a_field_identify_the_runner_cancels_half_way_leaves_no_panel_open():
    """15:21:38 on 2026-10-20 (game 6 of 20261020T115501Z-4b07df55): a fight back cancelled the field identify at once
    after the inventory opened; the panels stayed open, read as the player's hand, the character hit for 60 s."""
    import pytest

    from inventory_tracking.macros.actuator import Cancelled

    play, hands, _, _ = setup(Pack((TOME, WORN, JUNK), identifies=10))
    run = hands.run
    run.actuator.cancelled = run.cancelled  # the runner's one cancel, as execution.py binds it
    tapped = run.actuator.tap

    def tap(*names: str) -> None:
        tapped(*names)
        if names == ('Button3',):
            run.cancelled.set()  # the tome armed: the fight back's cancel

    run.actuator.tap = tap  # type: ignore[method-assign]
    with pytest.raises(Cancelled):
        looped(play.world.game_name).settle(hands, 'at once')
    assert play.world.open_panels == ()
    assert play.fallen == []


def test_a_rare_belt_short_of_its_combination_is_dropped_at_the_feet_and_a_really_good_one_kept():
    """G22 (the player, 2026-10-20 ~19:25, on rare boots and belts: "we can keep really good ones"): two rare Mithril
    Coils identified with the Tome in the fake game; the 17 FHR one is put down (keep.py K8), the 24 FHR / 40 life /
    two resistances one stays (loot/build_wants.py rare-belt-24fhr-life-res-extra)."""
    from tests.inventory_tracking.loot.test_valuables import observation

    coil = 462  # items metadata class of umc, 2x1 (sizes.json)
    good, near = Carried(80, coil, 0, 0, (2, 1), 6, identified=False), Carried(81, coil, 0, 1, (2, 1), 6, False)
    rolls = {80: {'99:0': 24, '7:0': 40 * 256, '39:0': 25, '41:0': 22}, 81: {'99:0': 17, '7:0': 45 * 256, '39:0': 30}}
    play = Game(world(CATACOMBS_4, player=player(CATACOMBS_4, x=5029.0, y=2860.0)))
    play.pack = Pack((TOME, WORN, good, near), identifies=10)
    book, put_down = Book(), PutDown()

    def appraise(units: list[int]) -> dict[int, str]:
        for unit in units:
            spec = {'base': 'Mithril Coil', 'code': 'umc', 'quality': 'rare', 'rolls': rolls[unit]}
            book.put(unit, Appraised(observation(spec, unit), {'triage': {'verdict': 'check'}}, 'check'))
        return dict.fromkeys(units, 'check')

    hands = GameHands(play.run(), inventory_key=lambda: 'i', own=lambda p: own_of((TOME, WORN)), appraise=appraise,
                      put_down=put_down, book=book, owned=NoCopies())  # fmt: skip
    field = Field()
    field.looping = lambda: True
    for item in (good, near):
        drop = Drop(item.unit_id, 1.0, 1.0, 'Rare Mithril Coil', VALUABLE, (2, 1), False, 'shown', coil, 6)
        assert field.pick(drop, (play.world.game_name, 1))

    done = field.settle(hands, 'Town Portal')

    assert [item.unit_id for item in play.fallen] == [81]
    assert done.dropped == 1
    assert 81 in put_down.rejected
    assert play.pack is not None
    assert play.pack.identifies == 8
    assert [item.unit_id for item in play.pack.items] == [TOME.unit_id, WORN.unit_id, 80]
