"""The Warlock's casters (builds/warlock/casters.py): the Defiler's summon and its spots, Consume on a Defiler."""

import math
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock.casters import NEAR_SPOTS, SUMMON_SPOTS, open_spots, renew_consume
from inventory_tracking.levels.model import Ground, Walkable, pack_cells
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.routines import prebuff, world_point
from inventory_tracking.macros.world import Monster
from tests.inventory_tracking.macros.fakes import WINDOW, Game, world


BOUND_DEMON = Monster(50, 700, 1, 4995.0, 5003.0, 0xFFFFFFFF)  # summons carry no owner (host, 2026-10-06)
DEFILER = Monster(60, 744, 1, 5006.0, 4996.0, 0xFFFFFFFF)


def follow(game, times=99):
    """The bound demon walks onto every new Defiler, `times` times."""
    react, left = game.keys.on_event, [times]

    def on_event(event):
        react(event)
        if event == ('key', 'q') and left[0]:
            left[0] -= 1
            defiler = next(m for m in game.world.monsters if m.txt_id == 744)
            moved = tuple(
                replace(m, x=defiler.x + 1, y=defiler.y + 1) if m.txt_id == 700 else m for m in game.world.monsters
            )
            game.world = replace(game.world, monsters=moved)

    game.keys.on_event = on_event


def test_consume_is_not_pressed_while_the_bound_demon_stands_by_the_defiler():
    game = Game(world(monsters=(BOUND_DEMON,)))
    follow(game)
    with pytest.raises(Abort, match='too close'):
        prebuff(game.run())
    assert '6' not in game.pressed()
    assert 700 in [m.txt_id for m in game.world.monsters]


def test_a_defiler_the_demon_walked_up_to_is_replaced_by_one_in_the_open():
    game = Game(world(monsters=(BOUND_DEMON,)))
    follow(game, times=1)
    prebuff(game.run())
    assert game.pressed() == ['q', 'q', '6', 'q', 'g', 'r']
    assert game.character.consume
    assert sorted(m.txt_id for m in game.world.monsters) == [700, 744]


def test_a_crowded_defiler_is_replaced_at_another_spot_each_time():
    game = Game(world(monsters=(BOUND_DEMON,)))
    follow(game, times=2)
    react, summons = game.keys.on_event, []

    def on_event(event):
        if event == ('key', 'q'):
            summons.append(game.keys.fraction())
        react(event)

    game.keys.on_event = on_event
    prebuff(game.run())
    assert len({(round(x, 1), round(y, 1)) for x, y in summons[:3]}) == 3
    assert game.character.consume


def test_hostile_monsters_around_the_defiler_do_not_make_it_crowded():
    # Host, 18:48 on 2026-10-10, a prebuff in the middle of a level: the monsters beside the standing
    # Defiler had four more summoned, which ended the Consume in force, and the press stopped.
    defiler = Monster(60, 744, 1, 4997.0, 4995.0, 0xFFFFFFFF)
    hostile = Monster(61, 361, 1, 5000.0, 4996.0, 0xFFFFFFFF, life=900, max_life=900)
    game = Game(world(monsters=(BOUND_DEMON, defiler, hostile)))
    prebuff(game.run())
    assert game.pressed() == ['6', 'q', 'g', 'r']  # the standing Defiler consumed, one summoned after
    assert game.character.consume


def test_a_tall_demon_drawn_below_the_defiler_is_not_consumed_in_its_place():
    # Host, 01:46 on 2026-10-07: 8 world units apart, the demon below the Defiler on the screen.
    defiler = Monster(60, 744, 1, 4997.0, 4995.0, 0xFFFFFFFF)
    demon = replace(BOUND_DEMON, x=5001.0, y=5002.0)
    game = Game(world(monsters=(demon, defiler)))
    prebuff(game.run())
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']  # another Defiler, in the open
    assert sorted(m.txt_id for m in game.world.monsters) == [700, 744]


def test_a_defiler_is_not_summoned_next_to_the_demon():
    demon_on_the_right = replace(BOUND_DEMON, x=5004.0, y=4993.0)  # where the first summon spot is
    game = Game(world(monsters=(demon_on_the_right,)))
    prebuff(game.run())
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']
    assert sorted(m.txt_id for m in game.world.monsters) == [700, 744]


def test_townsfolk_by_the_defiler_do_not_stop_consume():
    # Host, 19:43 on 2026-10-07 (Rogue Encampment): Kashya (class 150) 8 and 12 units from the
    # Defiler was "too close" three summons in a row, and Consume was never pressed.
    game = Game(world())
    react = game.keys.on_event

    def on_event(event):  # she stands that far from every Defiler, wherever it lands
        react(event)
        if event == ('key', 'q'):
            defiler = next(m for m in game.world.monsters if m.txt_id == 744)
            kashya = Monster(8, 150, 1, defiler.x + 8, defiler.y + 12, 0xFFFFFFFF)
            others = tuple(m for m in game.world.monsters if m.txt_id != 150)
            game.world = replace(game.world, monsters=(*others, kashya))

    game.keys.on_event = on_event
    prebuff(game.run())
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']


def test_consume_is_aimed_where_the_defiler_stands_after_it_walked():
    # User, 2026-10-07: the summoned Defiler moves, and Consume pressed where it was misses.
    game = Game(world())
    react, walked = game.keys.on_event, []

    def on_event(event):
        react(event)
        if event == ('key', 'q') and not walked:  # it walks off as soon as it has landed
            walked.append(True)
            moved = tuple(replace(m, x=m.x - 9, y=m.y + 2) if m.txt_id == 744 else m for m in game.world.monsters)
            game.world = replace(game.world, monsters=moved)

    game.keys.on_event = on_event
    steps, move = [], game.keys.move_pointer

    def move_pointer(x, y):  # and takes two more steps while the pointer is on its way to it
        steps.append((x, y))
        if len(walked) < 3 and len(steps) % 3 == 0 and '6' not in game.pressed() and game.pressed() == ['q']:
            walked.append(True)
            moved = tuple(replace(m, x=m.x + 3) if m.txt_id == 744 else m for m in game.world.monsters)
            game.world = replace(game.world, monsters=moved)
        return move(x, y)

    game.keys.move_pointer = move_pointer
    prebuff(game.run())
    assert len(walked) == 3
    assert game.pressed() == ['q', '6', 'q', 'g', 'r']
    assert game.character.consume


def test_consume_is_not_pressed_at_a_defiler_that_never_stands_still():
    # The pointer would be where the Defiler was, and the bound demon may stand there (user,
    # 2026-10-07: the demon must never be consumed by accident).
    game = Game(world(monsters=(BOUND_DEMON,)))
    run = game.run()
    move, steps = run.actuator.move, [3.0, -3.0]

    def restless(x, y, **scatter):  # three units to and fro, once per pointer move
        move(x, y, **scatter)
        steps.reverse()
        walked = tuple(replace(m, x=m.x + steps[0]) if m.txt_id == 744 else m for m in game.world.monsters)
        game.world = replace(game.world, monsters=walked)

    run.actuator.move = restless
    with pytest.raises(Abort, match='keeps walking'):
        prebuff(run)
    assert '6' not in game.pressed()
    assert 700 in [m.txt_id for m in game.world.monsters]


def deaf_to_consume(game, times):
    """The game does nothing on the first `times` Consume keys."""
    react, left = game.keys.on_event, [times]

    def on_event(event):
        if event == ('key', '6') and left[0]:
            left[0] -= 1
            return
        react(event)

    game.keys.on_event = on_event


def test_a_consume_that_changed_nothing_is_pressed_again():
    # Host, 20:04 on 2026-10-07: the key went down on a still Defiler, which stood on with no buff.
    game = Game(world(monsters=(BOUND_DEMON,)))
    deaf_to_consume(game, 1)
    prebuff(game.run())
    assert game.pressed() == ['q', '6', '6', 'q', 'g', 'r']
    assert game.character.consume
    assert sorted(m.txt_id for m in game.world.monsters) == [700, 744]


def test_consume_gives_up_after_three_presses_that_changed_nothing():
    game = Game(world())
    deaf_to_consume(game, 99)
    with pytest.raises(Abort, match='Consume: not seen'):
        prebuff(game.run())
    assert game.pressed() == ['q', '6', '6', '6']


# --- summon spots on ground a Defiler can stand on (2026-10-12) ---


def cave(walkable):
    """The level around the character (world 5000, 5000): one room of 16 x 16 tiles, each sub-tile
    walkable where `walkable(x, y)` says so."""
    cells = ''.join('1' if walkable(992 * 5 + x, 992 * 5 + y) else '0' for y in range(80) for x in range(80))
    return Ground((Walkable(992, 992, 16, 16, pack_cells(cells)),))


def test_summon_spots_off_the_walkable_ground_are_left_out():
    # Cave Level 1, 02:43 on 2026-10-12: nothing was summoned at three spots in 5 s.
    game = Game(world())
    run, me = game.run(), game.character
    aspect = WINDOW[2] / WINDOW[3]
    run.ground = lambda: cave(lambda x, y: x - y <= 4)  # a wall along the right of the view
    spots = open_spots(run, game.world)
    assert spots
    assert all(spot[0] <= 0.56 for spot in spots)
    assert SUMMON_SPOTS[0] not in spots
    assert SUMMON_SPOTS[1] in spots
    # A wall between the character and the ground behind it: the spot there is not open either.
    run.ground = lambda: cave(lambda x, y: not 3 <= me.y - y <= 4)
    points = [world_point(me, *spot, aspect) for spot in open_spots(run, game.world)]
    assert points
    assert all(me.y - y < 3 or me.x - x > 20 for x, y in points)


def test_in_a_narrow_place_the_near_spots_are_tried():
    game = Game(world())
    run, me = game.run(), game.character
    run.ground = lambda: cave(lambda x, y: math.dist((x, y), (me.x, me.y)) <= 7)
    spots = open_spots(run, game.world)
    assert spots
    assert set(spots) <= set(NEAR_SPOTS)


def test_no_ground_known_or_none_to_stand_on_leaves_the_spots_as_they_were():
    game = Game(world())
    run = game.run()
    assert open_spots(run, game.world) == list(SUMMON_SPOTS)
    run.ground = lambda: None
    assert open_spots(run, game.world) == list(SUMMON_SPOTS)
    run.ground = lambda: cave(lambda x, y: False)
    assert open_spots(run, game.world) == list(SUMMON_SPOTS)


def test_consume_is_cast_anew_on_a_defiler_summoned_for_it_and_another_summoned():
    # Not on the standing one: it follows the character, the bound demon beside it (09:58 on 2026-10-12).
    standing = Monster(900, 744, 1, 5010.0, 5000.0, 0xFFFFFFFF)
    game = Game(world(monsters=(standing,)))
    renew_consume(game.run())
    assert game.pressed() == ['q', '6', 'q']
    assert game.character.consume
    assert len([m for m in game.world.monsters if m.txt_id == 744]) == 1
