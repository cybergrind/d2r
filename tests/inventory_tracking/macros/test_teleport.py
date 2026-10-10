"""The teleport step on a scripted level: a teleport as far as the screen shows, or a walk into a near door.

The character stands at world (5000, 5000), tile (1000, 1000), in an 8x8 room; the mark lies east.
In view (teleport.VIEW, the classic projection) a hop straight east reaches about 26 world units:
(dx + dy) * 8 / 600 must stay under 0.84 - 0.494 of the window height, the skill bar being the limit.
"""

import math
from dataclasses import replace

import pytest

from inventory_tracking.levels.model import Ground, Room, Target, Walkable, pack_cells, pack_tiles
from inventory_tracking.macros import teleport
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.teleport import (
    NEAR_WARP,
    Way,
    approaches,
    footing,
    hop_in_view,
    landing,
    step_toward,
)
from inventory_tracking.macros.world import Teleport
from tests.inventory_tracking.macros.fakes import KEYS, SLOTS, Game, player, world


HERE = Room(1, 996, 996, 8, 8)
EAST = tuple(Room(2 + i, 1004 + 8 * i, 996, 8, 8) for i in range(4))  # a corridor to the east
STAFF = Teleport(10, 20, True)


def keys(_world, skills):
    return {skill: KEYS[skill] for skill in skills}


def target(point, rooms=(HERE, *EAST), *, area=109, warp=False):
    return Target(area, tuple(rooms), point, 'Next level', 'stairs', warp)


def game(staff=STAFF, **changes):
    found = Game(world(**changes))
    found.staff = staff
    return found


def test_a_mark_in_sight_is_one_teleport_onto_it():
    play = game()
    step_toward(play.run(), target((1003.0, 1000.0)), keys)
    assert play.pressed() == ['t']
    assert math.dist((play.world.player.x, play.world.player.y), (5015.0, 5000.0)) < 0.5
    assert play.staff.charges == 9
    assert play.said[-2].startswith('Teleport toward Next level')  # then the key's own name


def test_a_far_mark_gets_a_hop_to_the_edge_of_the_screen_along_the_line():
    play = game()
    step_toward(play.run(), target((1031.0, 1000.0)), keys)
    assert play.pressed() == ['t']
    moved = play.world.player.x - 5000.0
    assert 24.0 < moved < 31.0  # as far east as the view shows ground, a little north to use its shape
    assert -6.0 < play.world.player.y - 5000.0 <= 0.5


def test_void_wider_than_a_teleport_sends_the_hop_toward_the_bridge_room():
    bridge, far = Room(5, 1002, 1004, 8, 8), Room(6, 1010, 996, 8, 8)  # six tiles of void straight east
    play = game()
    step_toward(play.run(), target((1014.0, 1000.0), (HERE, bridge, far)), keys)
    assert play.pressed() == ['t']
    assert play.world.player.y > 5005.0  # south-east, toward the bridge, not straight east
    assert play.world.player.x > 5005.0


def test_a_door_within_reach_is_walked_into_and_the_level_changes():
    play = game()
    play.door = (1001.5, 1000.5)  # 7.9 units away
    step_toward(play.run(), target(play.door, warp=True), keys)
    assert play.pressed() == []
    assert [event[0] for event in play.keys.events] == ['click']
    assert play.world.player.area == 110
    assert play.said == ['Walking into Next level, 8 away', 'Next level: there']


def test_a_doorway_drawn_above_its_tile_is_clicked_there_when_the_ground_does_not_take():
    # Worldstone Keep's stairs (host, 01:32 on 2026-10-10): the teleport landed on the warp tile and
    # the click on the ground under the character's feet moved nobody.
    play = game(player=player(x=5007.5, y=5002.5))
    play.door, play.door_above = (1001.5, 1000.5), 60
    step_toward(play.run(), target(play.door, warp=True), keys)
    assert [event[0] for event in play.keys.events] == ['click', 'click']
    assert play.world.player.area == 110
    assert play.said == ['Walking into Next level, 0 away', 'Next level: there']


def test_the_click_that_took_a_levels_door_is_tried_first_next_time():
    for _ in range(2):
        play = game()
        play.door, play.door_above = (1001.5, 1000.5), 60
        teleport.ENTRIES = teleport.Entries(None)  # the door's spot forgotten: this is about the click alone
        step_toward(play.run(), target(play.door, warp=True), keys)
    assert [event[0] for event in play.keys.events] == ['click']
    assert play.world.player.area == 110


def test_a_door_whose_aim_the_logs_gave_is_clicked_there_first():
    stairs = Room(144, 996, 996, 8, 8)  # 'Act 1 - Crypt Next E': the stairs down in the Tower Cellar
    mark = Target(21, (stairs,), (1001.5, 1000.5), 'Next level', 'stairs', True)
    assert teleport.door_aims(mark)[0] == (-50, -45)
    teleport.AIMS.learn(mark, (0, -45))  # what took it last goes before what the logs gave
    assert teleport.door_aims(mark)[:2] == ((0, -45), (0, 0))


def test_a_door_aim_with_a_monster_under_it_is_left_for_last():
    # The mercenary lands beside the character after a hop: a click on it is not a click on the door.
    play = game()
    play.door = (1001.5, 1000.5)
    run = play.run()
    looks = iter([(1, 77), (0, 0), (0, 0), (0, 0), (0, 0)])  # a monster under the first aim only
    run.hovered = lambda: next(looks)
    step_toward(run, target(play.door, warp=True), keys)
    assert play.world.player.area == 110
    assert teleport.AIMS.offset(target(play.door, warp=True)) == (0.0, -45.0)  # the next aim: the first was not clicked


def test_one_click_from_where_the_character_stands_makes_that_spot_the_doors_entry():
    # Tower Cellar: the stairs took the click from 5.6 units without a step.
    play = game()
    play.door = (1001.0, 1000.0)  # world (5005, 5000), 5 from the character
    mark = target(play.door, warp=True)
    step_toward(play.run(), mark, keys)
    assert teleport.ENTRIES.offset(mark) == (-5.0, 0.0)


def test_the_way_back_is_not_walked_into():
    # Tower Cellar 5: the stairs up to level 4 are the only mark, and the step after arriving took them.
    play = game()
    back = Target(109, (HERE,), (1001.5, 1000.5), 'Tower Cellar 4', 'previous', True)
    with pytest.raises(Abort, match='back to Tower Cellar 4'):
        step_toward(play.run(), back, keys)
    assert play.keys.events == []


def test_a_door_no_click_takes_is_reported():
    play = game()
    play.door, play.door_above = (1001.5, 1000.5), 400
    with pytest.raises(Abort, match='no click took'):
        step_toward(play.run(), target(play.door, warp=True), keys)


def test_the_last_hop_before_a_door_lands_beside_it_on_the_characters_side():
    # user, 2026-10-10: a hop onto the warp tiles put the character off to a side, and the walk in went
    # around. Solid ground to the east; the door 20 units away: the landing is about APPROACH units
    # short of it, west of it, not on its tiles.
    wide = Walkable(996, 996, 16, 8, pack_tiles('1' * 128, 16))
    play = game()
    door = (1004.0, 1000.0)
    mark = Target(109, (HERE, *EAST), door, 'Next level', 'stairs', True, (wide,))
    step_toward(play.run(), mark, keys)
    assert play.pressed() == ['t']
    landed = (play.world.player.x, play.world.player.y)
    assert teleport.WARP_TILES < math.dist(landed, (5020.0, 5000.0)) < teleport.APPROACH + 1.0
    assert landed[0] < 5020.0 - teleport.WARP_TILES  # west of the door: the side the character came from
    assert abs(landed[1] - 5000.0) < 2.5  # straight west, give or take the aim scatter


def test_a_door_further_than_a_walk_is_teleported_toward():
    play = game()
    door = (1000.0 + (NEAR_WARP + 5) / 5, 1000.0)
    step_toward(play.run(), target(door, warp=True), keys)
    assert play.pressed() == ['t']


def test_a_staff_on_the_other_set_is_swapped_in_first_and_left_in_hand():
    play = game(Teleport(10, 20, False))
    step_toward(play.run(), target((1003.0, 1000.0)), keys)
    assert play.pressed() == ['c', 't']
    assert play.staff == Teleport(9, 20, True)


def test_teleport_as_a_skill_needs_no_staff():
    play = game(None)
    step_toward(play.run(), target((1003.0, 1000.0)), keys)
    assert play.pressed() == ['t']
    assert 'charges' not in play.said[-2]


@pytest.mark.parametrize(
    ('staff', 'slots', 'mark', 'message'),
    [
        (Teleport(0, 20, True), SLOTS, target((1003.0, 1000.0)), 'charges'),
        (STAFF, tuple(None if s == 54 else s for s in SLOTS), target((1003.0, 1000.0)), 'skill key'),
        (STAFF, SLOTS, target((1003.0, 1000.0), area=110), 'another level'),
        (STAFF, SLOTS, None, 'level card'),
        (STAFF, SLOTS, target((1014.0, 1000.0), (HERE,)), 'no way over the rooms'),  # the mark is off the rooms
        (STAFF, SLOTS, target((1000.5, 1000.0)), 'no footing in view brings'),  # already there, nothing to gain
    ],
)
def test_nothing_is_pressed_when_the_step_cannot_be_taken(staff, slots, mark, message):
    play = game(staff, slots=slots)
    with pytest.raises(Abort, match=message):
        step_toward(play.run(), mark, keys)
    assert play.keys.events == []


def test_an_open_panel_stops_the_step():
    play = game(open_panels=('inventory',))
    with pytest.raises(Abort, match='inventory is open'):
        step_toward(play.run(), target((1003.0, 1000.0)), keys)


def test_a_teleport_that_moves_nobody_is_reported():
    play = game()
    play.keys.on_event = lambda event: None  # the game ignores the key
    with pytest.raises(Abort, match='did not move'):
        step_toward(play.run(), target((1003.0, 1000.0)), keys)
    assert play.pressed() == ['t']


PIT = Walkable(996, 996, 8, 8, pack_tiles('11111100' * 8, 8))  # the room's two eastern tile columns are a pit
SOLID = Walkable(996, 996, 8, 8, pack_tiles('1' * 64, 8))


def test_the_landing_stops_short_of_a_pit_the_grids_know_about(caplog):
    play = game()
    mark = Target(109, (HERE, *EAST), (1002.4, 1000.0), 'Next level', 'stairs', False, (PIT,))  # in the pit
    with caplog.at_level('INFO'):
        step_toward(play.run(), mark, keys)
    assert play.pressed() == ['t']
    assert 5005.0 < play.world.player.x < 5009.5  # before the pit at x = 5010, a unit of margin kept
    [line] = [r.message for r in caplog.records if 'teleport aimed at' in r.message]
    assert 'off the way, footing True, 1 grids' in line
    assert 'landed at' in line


def test_a_chasm_in_the_way_is_crossed_where_the_view_shows_ground_beyond_it():
    beyond = Room(9, 1004, 996, 8, 8)
    chasm = Walkable(1004, 996, 8, 8, pack_tiles('01111111' * 8, 8))  # a tile column of nothing, then floor
    play = game()
    mark = Target(109, (HERE, beyond), (1011.0, 1000.0), 'Next level', 'stairs', False, (SOLID, chasm))
    step_toward(play.run(), mark, keys)
    assert play.world.player.x > 5025.5  # over the chasm (x 5020-5025), on the floor beyond, a unit in


def test_known_solid_ground_lands_on_the_mark_and_logs_the_miss(caplog):
    play = game()
    mark = Target(109, (HERE, *EAST), (1003.0, 1000.0), 'Next level', 'stairs', False, (SOLID,))
    with caplog.at_level('INFO'):
        step_toward(play.run(), mark, keys)
    [line] = [r.message for r in caplog.records if 'teleport aimed at' in r.message]
    assert 'aimed at (5015.0, 5000.0), 15.0 from (5000.0, 5000.0),' in line
    assert 'off the way, footing True, 1 grids' in line
    assert ', off by 0.' in line  # the fake lands where the pointer points, give or take the scatter


def test_footing_needs_the_neighbours_too_and_is_unknown_off_the_grids():
    ground = Ground((PIT,))
    assert footing(ground, (1000.0, 1000.0)) is True
    assert footing(ground, (1001.9, 1000.0)) is False  # a unit from the pit's edge at x = 1002
    assert footing(ground, (1002.5, 1000.0)) is False
    assert footing(ground, (1010.0, 1000.0)) is None


def test_a_character_on_a_tile_whose_centre_is_a_pit_still_has_a_way():
    # The character stands on the walkable western edge of a tile whose centre is pit (River of Flame
    # lava edges, host 20:09 on 2026-10-09): the way starts from the landable tiles one hop away.
    rows = [
        ''.join('0' if 20 <= col < 25 and 20 <= row < 25 and (col, row) != (20, 22) else '1' for col in range(40))
        for row in range(40)
    ]
    edge = Walkable(996, 996, 8, 8, pack_cells(''.join(rows)))  # tile (1000, 1000) is pit but for one sub-tile
    play = game()
    play.world = replace(play.world, player=replace(play.world.player, x=5000.4, y=5002.5))  # on that sub-tile
    mark = Target(109, (HERE, *EAST), (1003.0, 1000.0), 'Next level', 'stairs', False, (edge,))
    step_toward(play.run(), mark, keys)
    assert play.pressed() == ['t']


def test_the_potential_plans_no_hop_the_view_cannot_show():
    # Host, 19:19 on 2026-10-10, Catacombs 1: the only way on was a landing 21 units straight down the
    # screen, below where the view ends at the skill bar; the potential counted it as one hop and twenty
    # seek steps in a row found "no footing in view".
    assert hop_in_view(-3, -3)  # 21 units straight up the screen
    assert not hop_in_view(3, 3)  # the same straight down
    assert hop_in_view(2, 2)
    assert hop_in_view(2, -3)  # and to a side
    # Two rooms a gap apart, the second straight down the screen from the first: no way from the first
    # to a mark in the second, and a way back up from the second.
    upper, lower = Room(1, 1000, 1000, 2, 2), Room(2, 1004, 1004, 2, 2)
    down = Way(Target(109, (upper, lower), (1004.5, 1004.5), 'below', 'mark', False, ()))
    up = Way(Target(109, (upper, lower), (1001.5, 1001.5), 'above', 'mark', False, ()))
    assert down.from_here((1001.5, 1001.5)) == math.inf
    assert up.from_here((1004.5, 1004.5)) < math.inf


def test_a_spot_beside_the_door_the_way_does_not_count_is_not_the_landing():
    # Host, 19:29 on 2026-10-10, Catacombs 1: the "beside the door" spot nearest the character had
    # footing but lay on a tile whose centre was wall, so the way gave it no cost; the landing came
    # out as no gain and sixteen teleport steps in a row stopped 16 units from the door.
    door = Target(109, (HERE, *EAST), (1003.5, 1000.5), 'Next level', 'stairs', True, ())
    way = Way(door)
    nearest = min(approaches(door), key=lambda spot: math.dist(spot, (1000.0, 1000.0)))
    real = way.to_go
    way.to_go = lambda point: math.inf if math.dist(point, nearest) < 0.3 else real(point)
    found = landing(door, player(), way, 2560 / 1418)
    assert found is not None
    spot, gain = found
    assert math.dist(spot, nearest) >= 0.3
    assert gain > 0.5


def test_a_pointer_found_off_the_aim_is_aimed_again_before_the_key(caplog):
    play = game()
    hand = {'drags': 3, 'reads_since_move': 0}  # the hand drags the pointer off right after each of three moves
    real_move, real_pointer = play.keys.move_pointer, play.keys.pointer

    def move_pointer(x, y):
        hand['reads_since_move'] = 0
        return real_move(x, y)

    def pointer():
        first = hand['reads_since_move'] == 0
        hand['reads_since_move'] += 1
        if first and hand['drags']:
            hand['drags'] -= 1
            return (play.keys.at[0] + 120, play.keys.at[1])
        return real_pointer()

    play.keys.move_pointer, play.keys.pointer = move_pointer, pointer
    with caplog.at_level('INFO'):
        step_toward(play.run(), target((1003.0, 1000.0)), keys)
    assert play.pressed() == ['t']
    assert sum('aiming again' in r.message for r in caplog.records) == 2


def test_a_swipe_of_the_hand_across_the_screen_does_not_stop_the_step(caplog):
    # Two steps stopped "the mouse was moved" with the pointer 600 and 870 pixels off the aim (the runs
    # of 18:01 and 18:05 on 2026-10-10): the aim is made again instead.
    play = game()
    hand = {'swipes': 1, 'reads_since_move': 1}  # the swipe comes right after the macro's own move
    real_move, real_pointer = play.keys.move_pointer, play.keys.pointer

    def move_pointer(x, y):
        hand['reads_since_move'] = 0
        return real_move(x, y)

    def pointer():
        first = hand['reads_since_move'] == 0
        hand['reads_since_move'] += 1
        if first and hand['swipes']:
            hand['swipes'] -= 1
            play.keys.at = (play.keys.at[0] + 870, play.keys.at[1] - 150)  # and it stays there
        return real_pointer()

    play.keys.move_pointer, play.keys.pointer = move_pointer, pointer
    with caplog.at_level('INFO'):
        step_toward(play.run(), target((1003.0, 1000.0)), keys)
    assert play.pressed() == ['t']
    assert sum('aiming again' in r.message for r in caplog.records) == 1


def test_a_hand_that_keeps_sweeping_the_mouse_is_beaten_by_a_jump_of_the_pointer(caplog):
    # Two seek steps stopped "the mouse is being moved" after three aims in 0.4 s (host, 20:57 and 20:58
    # on 2026-10-10): the hand carries the pointer off during every pause of a move. The last try has none.
    play = game()
    sleep = play.clock.sleep

    def sweeping(seconds):
        play.keys.at = (play.keys.at[0] + 200, play.keys.at[1] + 40)  # the hand, whenever the macro waits
        sleep(seconds)

    play.clock.sleep = sweeping
    with caplog.at_level('INFO'):
        step_toward(play.run(), target((1003.0, 1000.0)), keys)
    assert play.pressed() == ['t']
    assert sum('aiming again' in r.message for r in caplog.records) == 2


# --- the door's own spot (user, 2026-10-10: the last hop left a walk round the stairs) ---


def walking_game(door, entry, *, after=(0.6, 0.9)):
    """A game whose door walks the clicked character to `entry` (world units) and then changes the level."""
    play = game()
    start = play.clock.now

    def arrive():
        play.world = replace(play.world, player=replace(play.world.player, x=entry[0], y=entry[1]))

    def change():
        play.world = replace(play.world, player=replace(play.world.player, area=110))

    play.arrivals += [(start + after[0], arrive), (start + after[1], change)]
    return play


def test_a_walk_into_a_door_is_logged_and_where_the_level_changed_is_remembered(caplog):
    door = (1001.5, 1000.5)  # the mark, at world (5007.5, 5002.5)
    play = walking_game(door, (5007.5, 5005.5))
    mark = target(door, warp=True)
    with caplog.at_level('INFO'):
        step_toward(play.run(), mark, keys)
    assert teleport.ENTRIES.offset(mark) == (0.0, 3.0)
    lines = [r.message for r in caplog.records if r.message.startswith('Macro: door')]
    assert lines[0] == (
        'Macro: door Next level marked at (5007.5, 5002.5); the character at (5000.0, 5000.0), 7.9 from the mark; '
        'entry not known yet'
    )
    assert lines[1].startswith('Macro: door Next level: in after ')
    assert ' from (5000.0, 5000.0) to (5007.5, 5005.5); ' in lines[1]  # after the seconds and the units walked
    assert lines[1].endswith('the entry at +0.0, +3.0 from the mark, 3.0 away (remembered)')


def test_a_level_change_far_from_the_mark_teaches_nothing():
    door = (1001.5, 1000.5)
    play = walking_game(door, (5000.0, 5000.0))  # the level changed where the character stood, 7.9 off
    mark = target(door, warp=True)
    step_toward(play.run(), mark, keys)
    assert teleport.ENTRIES.offset(mark) is None


def test_a_remembered_entry_is_hopped_onto_and_the_door_clicked_from_there():
    # The stairs' mark sits in a block of walls; the spot the game walks to is 3 units south of it.
    door = (1003.0, 1000.0)  # world (5015, 5000): 15 away, a walk by the old rule would not start, a hop would
    mark = target(door, warp=True)
    teleport.ENTRIES.learn(mark, (0.0, 3.0))
    play = game()
    step_toward(play.run(), mark, keys)
    assert play.pressed() == ['t']
    landed = (play.world.player.x, play.world.player.y)
    assert math.dist(landed, (5015.0, 5003.0)) < 1.5  # on the door's spot, inside WARP_TILES of the mark
    play.door = door
    step_toward(play.run(), mark, keys)  # from the spot: the click, no second hop
    assert play.pressed() == ['t']
    assert play.world.player.area == 110


def test_a_door_within_a_walk_but_off_its_remembered_spot_is_hopped_onto_first():
    door = (1001.5, 1000.5)  # 7.9 away: walked into before the spot was known
    mark = target(door, warp=True)
    teleport.ENTRIES.learn(mark, (0.0, 3.0))
    play = game()
    step_toward(play.run(), mark, keys)
    assert play.pressed() == ['t']
    assert math.dist((play.world.player.x, play.world.player.y), (5007.5, 5005.5)) < 1.5


def test_a_remembered_spot_a_few_steps_off_over_open_ground_is_walked_to_by_the_click():
    # user, 2026-10-10: "we have jumped twice around the entrance": a hop beside the door, a hop onto its
    # spot 6 units on, then the click. The click walks those steps itself.
    door = (1001.3, 1000.3)  # world (5006.5, 5001.5); its spot 3 south of it, 7.9 from the character
    mark = replace(target(door, warp=True), ground=(SOLID,))
    teleport.ENTRIES.learn(mark, (0.0, 3.0))
    play = game()
    play.door = door
    step_toward(play.run(), mark, keys)
    assert play.pressed() == []  # no hop
    assert play.world.player.area == 110


def test_a_remembered_spot_behind_a_wall_is_still_hopped_onto():
    door = (1001.3, 1000.3)
    rows = ''.join('0' if 23 <= col <= 24 else '1' for col in range(40)) * 40  # a wall at world x 5003-5004
    mark = replace(target(door, warp=True), ground=(Walkable(996, 996, 8, 8, pack_cells(rows)),))
    teleport.ENTRIES.learn(mark, (0.0, 3.0))
    play = game()
    step_toward(play.run(), mark, keys)
    assert play.pressed() == ['t']
    assert math.dist((play.world.player.x, play.world.player.y), (5006.5, 5004.5)) < 1.5


def test_door_entries_are_kept_in_a_file_across_games(tmp_path):
    mark = target((1001.5, 1000.5), warp=True, area=36)
    first = teleport.Entries(tmp_path / 'macros' / 'door-entries.json')
    first.learn(mark, (0.04, 2.96))
    again = teleport.Entries(tmp_path / 'macros' / 'door-entries.json')
    assert again.offset(mark) == (0.0, 3.0)
    # The same stairs preset on another level has the same spot; another preset (another orientation) has none.
    assert again.offset(target((1001.5, 1000.5), warp=True, area=37)) == (0.0, 3.0)
    # Another preset on the level it was learned on falls back on the level's spot (the Catacombs' stairs
    # presets share one shape); another preset on another level has none.
    assert again.offset(target((1005.5, 1000.5), warp=True, area=36)) == (0.0, 3.0)
    assert again.offset(target((1005.5, 1000.5), warp=True, area=38)) is None
    assert teleport.Entries.key(target((1001.5, 1000.5), warp=True)) == 'preset 1:stairs'
    assert teleport.Entries.key(target((900.0, 900.0), warp=True, area=36)) == 'area 36:stairs'  # on no room
    (tmp_path / 'broken.json').write_text('{')
    assert teleport.Entries(tmp_path / 'broken.json').offset(mark) is None
