"""A route begun with the cube full and the loop's inventory cells partly filled starts with the town visit
(macros/loop.py `route_starts_full`; the player, 2026-10-19 21:20: "if at the beginning of route we have full cube at
least partially filled inventory - we visit town"): every route then begins with an empty cube and room."""

import pytest

from inventory_tracking.game.records import Carried, Pack
from inventory_tracking.macros import loop as loop_module
from inventory_tracking.macros.cube import CUBE_CLASS
from inventory_tracking.macros.loop import (
    ANDARIEL,
    ROUTE_VISITS,
    TO_THE_CATACOMBS,
    TO_THE_FORTRESS,
    TOWN,
    LegHands,
    Loop,
)
from inventory_tracking.macros.town import Exit
from tests.inventory_tracking.macros.fakes import Game
from tests.inventory_tracking.macros.test_loop import GAME, PANDEMONIUM_FORTRESS, at, keys, progress_in


ROGUE_ENCAMPMENT, CATACOMBS_2 = 1, 35
EL = 625  # items metadata: El Rune, a resource: the loop's at a first look
RING = 522  # an identified item at the first look: the player's
CUBE = Carried(1, CUBE_CLASS, 0, 0, (2, 2))
THEIRS = Carried(2, RING, 2, 0, (1, 1), quality=4)
RUNE = Carried(3, EL, 6, 0, (1, 1))
FULL_CUBE, ROOMY_CUBE = ('###',) * 4, ('###', '##.', '##.', '##.')  # a 1 x 3 free in the second


def pack(cube=FULL_CUBE, *items: Carried) -> Pack:
    return Pack((CUBE, THEIRS, *items), cube)


@pytest.fixture(autouse=True)
def still(monkeypatch):
    # The legs' moves are their own tests': here only which leg is made
    monkeypatch.setattr(loop_module, 'travel', lambda run, to, marks=None: None)
    monkeypatch.setattr(loop_module, 'prebuff', lambda run, **_: None)
    monkeypatch.setattr(loop_module, 'gold', lambda run: None)


def leg(loop: Loop, play: Game, area: int, visits: list[Exit]) -> str:
    return loop.leg(play.run(), keys, progress_in(area), LegHands(lambda: None, lambda: False, visit=visits.append))


def test_an_andariel_game_begun_with_the_cube_full_and_a_loop_item_carried_visits_the_fortress_first():
    play = Game(at(ROGUE_ENCAMPMENT))
    play.pack = pack(FULL_CUBE, RUNE)
    loop = Loop(on=True, kind=ANDARIEL, chosen=True, prebuffed=GAME)
    assert leg(loop, play, ROGUE_ENCAMPMENT, []) == TO_THE_FORTRESS
    assert loop.route_full


def test_room_in_the_cube_or_only_the_players_items_is_no_visit():
    play = Game(at(ROGUE_ENCAMPMENT))
    play.pack = pack(ROOMY_CUBE, RUNE)  # a Grand Charm still fits in the cube
    loop = Loop(on=True, kind=ANDARIEL, chosen=True, prebuffed=GAME)
    assert leg(loop, play, ROGUE_ENCAMPMENT, []) == TO_THE_CATACOMBS
    play = Game(at(ROGUE_ENCAMPMENT))
    play.pack = pack(FULL_CUBE)  # the cube full, the inventory only the player's: their cells never count
    loop = Loop(on=True, kind=ANDARIEL, chosen=True, prebuffed=GAME)
    assert leg(loop, play, ROGUE_ENCAMPMENT, []) == TO_THE_CATACOMBS
    assert not loop.route_full


def test_out_of_town_a_full_cube_is_no_route_start():
    play = Game(at(CATACOMBS_2))
    play.pack = pack(FULL_CUBE, RUNE)
    loop = Loop(on=True, kind=ANDARIEL, chosen=True, prebuffed=GAME)
    loop.leg(play.run(), keys, progress_in(CATACOMBS_2), LegHands(lambda: None, lambda: False, way_on=lambda: None))
    assert not loop.route_full


def test_in_the_fortress_the_visit_is_made_and_made_again_only_for_something_picked_up_since():
    play = Game(at(PANDEMONIUM_FORTRESS))
    play.pack = pack(FULL_CUBE, RUNE)
    loop = Loop(on=True, kind=ANDARIEL, chosen=True, prebuffed=GAME)
    visits: list[Exit] = []
    assert leg(loop, play, PANDEMONIUM_FORTRESS, visits) == TOWN
    assert visits == [Exit.WAYPOINT]
    # The visit left the cube full (a keeper waits there): the route goes on, no visit again for the same items
    assert leg(loop, play, PANDEMONIUM_FORTRESS, visits) == TO_THE_CATACOMBS
    assert len(visits) == 1
    # A later excursion's start with something new of the loop's carried: the visit again
    play.pack = pack(FULL_CUBE, RUNE, Carried(4, EL + 1, 7, 0, (1, 1)))
    assert leg(loop, play, PANDEMONIUM_FORTRESS, visits) == TOWN
    assert loop.route_visits == (GAME, 2)


def test_route_visits_a_game_are_bounded():
    play = Game(at(PANDEMONIUM_FORTRESS))
    loop = Loop(on=True, kind=ANDARIEL, chosen=True, prebuffed=GAME)
    visits: list[Exit] = []
    for n in range(ROUTE_VISITS):
        play.pack = pack(FULL_CUBE, RUNE, Carried(10 + n, EL + 1 + n, 7, 0, (1, 1)))
        assert leg(loop, play, PANDEMONIUM_FORTRESS, visits) == TOWN
    play.pack = pack(FULL_CUBE, RUNE, Carried(20, EL + 9, 7, 1, (1, 1)))
    assert leg(loop, play, PANDEMONIUM_FORTRESS, visits) == TO_THE_CATACOMBS
    assert len(visits) == ROUTE_VISITS
